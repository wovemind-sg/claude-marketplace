import type { On } from 'claude-code'
import { expect, mock, test } from 'claude-code/testing'
import type { Engine } from 'claude-code/testing'

const SID = 'e139ab55-3e32-4e78-886d-36c3bdebb864'
const HANDOFF = '/proj/.claude/handoffs/HANDOFF-e139ab55.md'
type Window = { kind: 'five_hour' | 'seven_day'; percentUsed: number; resetsAt: string }
type Agent = { id: string; description: string; type: string; status: string }

// The engine beneath the mod: one session, its usage readings, its subagents, the person's
// answers to the question dialog, and a record of everything the mod asked of it.
function engine(on: On) {
  mock.store(on)
  const w = {
    readings: [{ kind: 'five_hour', percentUsed: 50, resetsAt: '' }] as Window[],
    agents: [] as Agent[],
    answers: [] as (string | undefined)[], // undefined: the dialog is dismissed
    notifyFails: false,
    dropPluginPrompts: false, // another hook refuses the mod's own prompts
    sent: [] as { text: string; origin?: unknown }[],
    ran: [] as { command: string; args: string }[],
    aborted: [] as string[],
    stopped: [] as string[],
    messages: [] as { to: unknown; text: string }[],
    asked: [] as string[],
    notified: [] as string[],
    written: {} as Record<string, string>,
    links: [] as string[], // paths that are symbolic links

    logs: [] as string[],
    status: undefined as string | undefined,
    gate: undefined as Promise<void> | undefined, // while set, session.usage waits on it
  }
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  on('session.id', () => ({ value: SID }))
  on('session.root', () => ({ value: '/proj' }))
  on('command.register', (_, e) => ({ value: { command: e.name } }))
  on('ui.status', (_, e) => ((w.status = e.text), { value: undefined }))
  on('ui.log', (_, e) => (e.to === 'transcript' && w.logs.push(e.text), { value: undefined }))
  on('ui.notify', (_, e) => {
    if (w.notifyFails) throw new Error('no channel')
    w.notified.push(e.text)
    return { value: { isSent: true, channel: 'iterm2' } }
  })
  on('session.usage', async () => {
    await w.gate
    return { value: { startedAt: 0, context: { used: 0, total: 1 } as never, rateLimits: w.readings } }
  })
  on('agent.list', () => ({ value: w.agents as never }))
  on('turn.abort', (_, e) => (w.aborted.push(e.turnId), { value: undefined }))
  on('session.send', (_, e) => (w.messages.push({ to: e.to, text: e.text }), { isDelivered: true }))
  on('fs.write', (_, e) => ((w.written[e.path] = e.text), { value: undefined }))
  on('fs.stat', (_, e) => {
    if (!w.links.includes(e.path)) throw new Error('ENOENT')
    return { value: { kind: 'other', size: 0, mtimeMs: 0, isLink: true } }
  })
  on('tool.call', (_, e) => {
    if (e.tool === 'AskUserQuestion') {
      const q = (e as never as { questions: { question: string }[] }).questions[0]!.question
      w.asked.push(q)
      const a = w.answers.shift()
      if (a === undefined) return { deny: 'dismissed' }
      return { result: { questions: [], answers: { [q]: a } } as never }
    }
    if (e.tool === 'TaskStop') w.stopped.push((e as never as { task_id: string }).task_id)
    return { result: {} as never }
  })
  on('prompt.submit', (_, e) => {
    if (w.dropPluginPrompts && e.origin?.kind === 'plugin') return { drop: 'blocked' }
    w.sent.push({ text: e.text, origin: e.origin })
    return { text: e.text }
  })
  on('command.run', (_, e) => (w.ran.push({ command: e.command, args: e.args }), { text: '' }))
  on('turn.start', (_, e) => ({ turnId: e.turnId }))
  on('turn.complete', (_, e) => ({ text: e.answer }))
  on('session.measure', (_, e) => ({ changed: e.changed }))
  return w
}

const composer = { kind: 'composer' } as const
const start = ($: Engine) => $.session.start({ cwd: '/proj', surface: 'terminal', isInteractive: true })
const say = ($: Engine, text: string, origin: object = composer) => $.prompt.submit({ text, wait: false, origin } as never)
const run = ($: Engine, command: string, args = '') => $.command.run({ command, args, origin: composer } as never)
const turn = ($: Engine, turnId: string, text = '') => $.turn.start({ text, turnId })
// The wrap-up prompt's turn, its text framed as the engine frames a plugin's prompt.
const wrapTurn = ($: Engine, w: ReturnType<typeof engine>, turnId: string) =>
  turn($, turnId, `The token-utilization plugin sent a message:\n${w.sent.at(-1)!.text}\n\nThis is how Claude Code surfaces a prompt a plugin submits.`)
const end = ($: Engine, turnId: string, answer = 'notes') => $.turn.complete({ turnId, answer, durationMs: 1, reason: 'answer', isAborted: false })
const tool = ($: Engine, agentId?: string) => $.tool.call({ tool: 'Bash', command: 'ls', ...(agentId ? { agentId } : {}) } as never)
function measure($: Engine, w: ReturnType<typeof engine>, five: number, seven?: number) {
  w.readings = [{ kind: 'five_hour', percentUsed: five, resetsAt: '' }]
  if (seven !== undefined) w.readings.push({ kind: 'seven_day', percentUsed: seven, resetsAt: '' })
  return $.session.measure({ context: { used: 0, total: 1 }, rateLimits: w.readings, changed: ['rateLimits'] } as never)
}
const running = (id: string): Agent => ({ id, description: id, type: 'general-purpose', status: 'running' })
const notification = (id: string) => `<task-notification>\n<task-id>${id}</task-id>\n<status>killed</status>\n</task-notification>`

test('T1: stop immediately: the prompt arrives stripped, a reading at the limit aborts the turn', async ($, on) => {
  const w = engine(on)
  await start($)
  w.answers = ['Stop immediately']
  await say($, 'Count files until /session-token-utilization gets to 90%')
  expect(w.sent.map(s => s.text)).toEqual(['Count files'])
  expect(w.asked).toEqual(['What should happen when the limit is reached?'])
  expect(w.status).toBe('stop at session 90% (now 50%), immediate')

  await turn($, 't1')
  await measure($, w, 89)
  expect(w.aborted).toEqual([])
  await measure($, w, 90)
  expect(w.aborted).toEqual(['t1'])
  expect(w.sent.length).toBe(1)
  expect(w.logs).toContain('token-utilization: session usage reached 90%, stopped')
})

test('T2: wrap up first, no subagents: abort, wrap-up prompt, handoff saved; idle trip sends nothing', async ($, on) => {
  const w = engine(on)
  await start($)
  w.answers = ['Wrap up first']
  await say($, 'Do XXX until /session-token-utilization gets to 90%')
  await turn($, 't1')
  await measure($, w, 91)
  expect(w.aborted).toEqual(['t1'])
  const wrap = w.sent.at(-1)!
  expect(wrap.origin).toEqual({ kind: 'plugin', name: 'token-utilization' })
  expect(wrap.text).toMatch(/^You were interrupted because session usage reached 90%, the limit set for this task\. Wrap up now:/)
  expect(wrap.text).toContain('.claude/handoffs/HANDOFF-e139ab55.md')
  expect(wrap.text).toContain('Usage is cut off at 95%.')
  expect(wrap.text).not.toContain('Subagents')

  await end($, 't1') // the aborted turn
  await wrapTurn($, w, 't2')
  await end($, 't2', 'Done: A. Next: B.')
  expect(w.written[HANDOFF]).toBe('Done: A. Next: B.')
  expect(w.written['/proj/.claude/handoffs/.gitignore']).toBe('*\n')
  expect(w.logs).toContain('token-utilization: handoff notes saved to .claude/handoffs/HANDOFF-e139ab55.md')
  expect((await run($, 'token-utilization')).text).toMatch(/stopped\.$/)

  // A new limit, the agent idle when it is reached: stopped, nothing sent.
  w.answers = ['Wrap up first']
  await measure($, w, 10)
  await say($, 'More until /session-token-utilization gets to 20%')
  const before = w.sent.length
  await measure($, w, 20)
  expect(w.sent.length).toBe(before)
  expect(w.aborted).toEqual(['t1'])
  expect((await run($, 'token-utilization')).text).toMatch(/stopped\.$/)
})

test('T3: below the limit nothing happens; a typed follow-up keeps it; off removes it', async ($, on) => {
  const w = engine(on)
  await start($)
  w.answers = ['Stop immediately']
  await say($, 'Task until /session-token-utilization gets to 90%')
  await turn($, 't1')
  await measure($, w, 80)
  await say($, 'also do this')
  expect(w.sent.at(-1)!.text).toBe('also do this')
  expect(w.status).toBe('stop at session 90% (now 80%), immediate')
  expect(w.aborted).toEqual([])

  expect((await run($, 'token-utilization', 'off')).text).toBe('token-utilization: limit removed.')
  expect(w.status).toBeUndefined()
  await measure($, w, 95)
  expect(w.aborted).toEqual([])
  expect((await run($, 'token-utilization')).text).toBe('token-utilization: no limit is set.')
})

test('T4: the weekly limit reads seven_day; two limits trip on the first reached', async ($, on) => {
  const w = engine(on)
  await start($)
  w.answers = ['Stop immediately']
  await say($, 'Do YYY until /weekly-token-utilization gets to 70%')
  expect(w.sent.at(-1)!.text).toBe('Do YYY')
  expect(w.status).toBe('stop at weekly 70% (no reading yet), immediate')
  await turn($, 't1')
  await measure($, w, 95, 69) // the session window does not count
  expect(w.aborted).toEqual([])
  await measure($, w, 95, 70)
  expect(w.aborted).toEqual(['t1'])

  await measure($, w, 10, 10)
  w.answers = ['Stop immediately']
  await say($, 'Do Z until /session-token-utilization gets to 80% or /weekly-token-utilization gets to 60%.')
  expect(w.sent.at(-1)!.text).toBe('Do Z.')
  await turn($, 't2')
  await measure($, w, 50, 60)
  expect(w.aborted).toEqual(['t1', 't2'])
})

test('T5: dismissed dialog, a limit already passed, and a bad percentage drop the prompt', async ($, on) => {
  const w = engine(on)
  await start($)
  w.answers = [undefined]
  expect(await say($, 'A until /session-token-utilization gets to 90%')).toEqual({ drop: 'token-utilization: no stop mode chosen. Prompt not sent.' })

  w.readings = [{ kind: 'five_hour', percentUsed: 92, resetsAt: '' }]
  expect(await say($, 'B until /session-token-utilization gets to 90%')).toEqual({
    drop: 'token-utilization: session usage is already at 92%, past the 90% limit. Prompt not sent.',
  })
  const form = /name a percentage from 1 to 100/
  expect((await say($, 'C until /session-token-utilization is high')).drop).toMatch(form)
  expect((await say($, 'D until /session-token-utilization gets to 150%')).drop).toMatch(form)
  // A percentage in a later sentence is not the limit.
  expect((await say($, 'F until /session-token-utilization is nearly full. Then raise coverage to 80%.')).drop).toMatch(form)
  expect(w.sent).toEqual([])
  expect(w.asked.length).toBe(1)
  // A -p prompt naming a limit is handled like a typed one: nobody answers, so it is dropped.
  w.readings = []
  w.answers = [undefined]
  expect((await say($, 'E until /session-token-utilization gets to 90%', { kind: 'sdk' })).drop).toMatch(/no stop mode chosen/)
  // A token inside a word is not a limit.
  expect((await say($, 'see docs/session-token-utilization.md')).drop).toBeUndefined()
})

test('T6: a reading at limit + 5 during the wrap-up stops everything; a typed prompt removes the ceiling', async ($, on) => {
  const w = engine(on)
  await start($)
  w.answers = ['Wrap up first']
  await say($, 'Task until /session-token-utilization gets to 90%')
  await turn($, 't1')
  await measure($, w, 90)
  await end($, 't1')
  await wrapTurn($, w, 't2')
  w.agents = [running('a1')]
  await measure($, w, 94)
  expect(w.aborted).toEqual(['t1'])
  await measure($, w, 95)
  expect(w.aborted).toEqual(['t1', 't2'])
  expect(w.stopped).toEqual(['a1'])
  expect(w.logs).toContain('token-utilization: session usage reached 95% during the wrap-up, stopped')

  // Again, but the person types during the wrap-up: the ceiling goes with the state.
  w.agents = []
  await measure($, w, 10)
  w.answers = ['Wrap up first']
  await say($, 'Task until /session-token-utilization gets to 20%')
  await turn($, 't3')
  await measure($, w, 20)
  await say($, 'keep going, I will watch it')
  await turn($, 't4')
  await measure($, w, 30)
  expect(w.aborted).toEqual(['t1', 't2', 't3'])
  expect(w.status).toBeUndefined()
})

test('T7: after a stop, automatic prompts notify and ask; typed prompts run', async ($, on) => {
  const w = engine(on)
  await start($)
  w.answers = ['Stop immediately']
  await say($, 'Task until /session-token-utilization gets to 90%')
  await measure($, w, 90)
  const loop = { kind: 'scheduled-trigger' } as const

  w.answers = ['No']
  expect((await say($, 'say hi', loop)).drop).toMatch(/automatic prompt not run/)
  expect(w.notified).toEqual(['An automatic prompt is waiting for your answer'])
  expect(w.asked.at(-1)).toBe('The usage limit was reached. Run this automatic prompt?')
  w.answers = [undefined] // dismissed: dropped, the next one asks again
  expect((await say($, 'say hi', loop)).drop).toMatch(/automatic prompt not run/)
  w.notifyFails = true // a failed notification still asks
  w.answers = ['Yes, run it']
  expect((await say($, 'say hi', loop)).text).toBe('say hi')
  expect(w.asked.length).toBe(4)
  await say($, 'say hi', loop) // no question any more
  expect(w.asked.length).toBe(4)

  for (const origin of [composer, { kind: 'bridge' }]) {
    w.answers = ['Stop immediately']
    await measure($, w, 10)
    await say($, 'Task until /session-token-utilization gets to 20%')
    await measure($, w, 20)
    const asked = w.asked.length
    expect((await say($, 'go on', origin)).text).toBe('go on')
    expect(w.asked.length).toBe(asked)
    expect((await say($, 'say hi', loop)).text).toBe('say hi') // the typed prompt cleared the stop
  }
})

test('T8: a slash command with a limit is armed at command.run and gets clean args', async ($, on) => {
  const w = engine(on)
  await start($)
  w.answers = ['Wrap up first']
  await run($, 'plan-tools:plan-implement-complete', 'plan.md until /session-token-utilization gets to 90%')
  expect(w.ran.at(-1)).toEqual({ command: 'plan-tools:plan-implement-complete', args: 'plan.md' })
  expect(w.status).toBe('stop at session 90% (now 50%), wrap-up')
  // The engine then submits the command's line; the limit stays set.
  await $.prompt.submit({ text: '/plan-tools:plan-implement-complete plan.md', command: { name: 'plan-tools:plan-implement-complete', args: 'plan.md' }, wait: false, origin: composer } as never)
  expect(w.status).toBe('stop at session 90% (now 50%), wrap-up')

  // A refused one does not run the command.
  w.readings = [{ kind: 'five_hour', percentUsed: 95, resetsAt: '' }]
  const ran = w.ran.length
  expect((await run($, 'review', 'x until /session-token-utilization gets to 90%')).text).toMatch(/already at 95%/)
  expect(w.ran.length).toBe(ran)
})

test('T9: immediate mode with running subagents aborts the turn and stops each; their notifications drop silently', async ($, on) => {
  const w = engine(on)
  await start($)
  w.answers = ['Stop immediately']
  await say($, 'Task until /session-token-utilization gets to 90%')
  await turn($, 't1')
  w.agents = [running('a1'), running('a2'), { ...running('a3'), status: 'completed' }]
  await measure($, w, 90)
  expect(w.aborted).toEqual(['t1'])
  expect(w.stopped).toEqual(['a1', 'a2'])

  const asked = w.asked.length
  const r = await say($, notification('a1'), { kind: 'task-notification' })
  expect(r.drop).toBe('token-utilization: dropped the notification of a subagent it stopped.')
  expect(w.asked.length).toBe(asked)
  expect(w.notified).toEqual([])
  // Any other automatic prompt still asks.
  w.answers = ['No']
  await say($, notification('zz'), { kind: 'task-notification' })
  expect(w.asked.length).toBe(asked + 1)
})

test('T10: wrap-up with running subagents: each is messaged, the main loop reads its text once, the handoff is saved', async ($, on) => {
  const w = engine(on)
  await start($)
  w.answers = ['Wrap up first']
  await say($, 'Task until /session-token-utilization gets to 90%')
  await turn($, 't1')
  w.agents = [running('a1'), running('a2')]
  await measure($, w, 90)
  expect(w.aborted).toEqual([])
  expect(w.stopped).toEqual([])
  expect(w.messages.map(m => m.to)).toEqual(['a1', 'a2']) // the engine spells { agentId } as the id
  expect(w.messages[0]!.text).toBe(
    'Session usage reached 90%, the limit set for this task. Wrap up now: if only a little work is left, finish it. ' +
      'Otherwise stop here and report what is done, what is in progress and what is left. Do not start new work. Usage is cut off at 95%.',
  )

  // A subagent's tool call does not take the main text; the main loop's next one does, once.
  expect((await tool($, 'a1')).context).toBeUndefined()
  const first = await tool($)
  expect(first.context).toHaveLength(1)
  expect(first.context![0]).toMatch(/^Session usage reached 90%, the limit set for this task\. Wrap up now:/)
  expect(first.context![0]).toContain('Subagents received the same instruction; collect what they report.')
  expect((await tool($)).context).toBeUndefined()

  // A messaged subagent's report passes without a question.
  const asked = w.asked.length
  expect((await say($, notification('a1'), { kind: 'task-notification' })).text).toContain('a1')
  await end($, 't1', 'Handoff: A done, B left.')
  expect(w.written[HANDOFF]).toBe('Handoff: A done, B left.')
  expect((await say($, notification('a2'), { kind: 'task-notification' })).text).toContain('a2')
  expect(w.asked.length).toBe(asked)
})

test('T12: idle trip with running subagents messages them, and the ceiling stops them', async ($, on) => {
  const w = engine(on)
  await start($)
  w.answers = ['Wrap up first']
  await say($, 'Task until /session-token-utilization gets to 90%')
  await turn($, 't1')
  await end($, 't1') // idle; a background subagent keeps working
  w.agents = [running('bg')]
  await measure($, w, 90)
  expect(w.messages.map(m => m.to)).toEqual(['bg'])
  expect(w.sent.length).toBe(1)
  expect(w.status).toBe('stopped, subagents cut off at session 95% (now 90%)')
  await measure($, w, 95)
  expect(w.stopped).toEqual(['bg'])
  expect(w.aborted).toEqual([])
  expect(w.status).toBe('stopped at the usage limit')
})

test('T11: armed with no reading: the status says so, and the warning is written once', async ($, on) => {
  const w = engine(on)
  w.readings = []
  await start($)
  w.answers = ['Stop immediately']
  await say($, 'Task until /session-token-utilization gets to 90%')
  expect(w.status).toBe('stop at session 90% (no reading yet), immediate')
  const warning = 'token-utilization: no session usage reading yet, so the limit cannot take effect'
  await turn($, 't1')
  await end($, 't1')
  await turn($, 't2')
  await end($, 't2')
  expect(w.logs.filter(l => l === warning)).toHaveLength(1)
})

test('T13: a refused wrap-up prompt stops; an interrupted wrap-up turn saves no handoff', async ($, on) => {
  const w = engine(on)
  await start($)
  w.answers = ['Wrap up first']
  await say($, 'Task until /session-token-utilization gets to 90%')
  await turn($, 't1')
  w.dropPluginPrompts = true
  await measure($, w, 90)
  await new Promise(r => setTimeout(r, 0))
  expect(w.logs).toContain('token-utilization: wrap-up prompt not sent (blocked), stopped')
  expect(w.status).toBe('stopped at the usage limit')

  w.dropPluginPrompts = false
  await measure($, w, 10)
  w.answers = ['Wrap up first']
  await say($, 'Task until /session-token-utilization gets to 20%')
  await turn($, 't2')
  await measure($, w, 20)
  await wrapTurn($, w, 't3')
  await $.turn.complete({ turnId: 't3', answer: 'half a', durationMs: 1, reason: 'aborted', isAborted: true })
  expect(w.written[HANDOFF]).toBeUndefined()
  expect(w.logs.at(-1)).toMatch(/handoff notes not saved .*ended with aborted/)
})

test('T14: a turn queued ahead of the wrap-up prompt is not the wrap-up turn', async ($, on) => {
  const w = engine(on)
  await start($)
  w.answers = ['Wrap up first']
  await say($, 'Task until /session-token-utilization gets to 90%')
  await turn($, 't1')
  await measure($, w, 90)
  await end($, 't1')
  // A background task's notification, queued during t1, runs before the wrap-up prompt.
  await turn($, 'tn', notification('bash1'))
  await end($, 'tn', 'The background command finished.')
  // Text that quotes the wrap-up prompt without the engine's frame is not it either.
  await turn($, 'tq', `<task-notification>\n<result>${w.sent.at(-1)!.text}</result>\n</task-notification>`)
  await end($, 'tq', 'quoted')
  expect(w.written[HANDOFF]).toBeUndefined()
  expect(w.status).toBe('wrapping up, cut off at session 95% (now 90%)')
  await wrapTurn($, w, 't2')
  await end($, 't2', 'Done: A. Next: B.')
  expect(w.written[HANDOFF]).toBe('Done: A. Next: B.')
  expect((await run($, 'token-utilization')).text).toMatch(/stopped\.$/)
})

test('T15: a stop saved by session.measure is not overwritten by a slower hook holding an old copy', async ($, on) => {
  const w = engine(on)
  await start($)
  w.answers = ['Stop immediately']
  await say($, 'Task until /session-token-utilization gets to 90% or /weekly-token-utilization gets to 70%')
  await turn($, 't1')
  // turn.complete reads the armed state, then waits on session.usage for its no-reading warning.
  let release!: () => void
  w.gate = new Promise(r => (release = r))
  const ending = end($, 't1')
  await new Promise(r => setTimeout(r, 0))
  const measuring = measure($, w, 90) // trips while turn.complete is still waiting
  await new Promise(r => setTimeout(r, 0))
  release()
  w.gate = undefined
  await Promise.all([ending, measuring])
  expect((await run($, 'token-utilization')).text).toMatch(/stopped\.$/)
  expect(w.status).toBe('stopped at the usage limit')
})

test('T16: a symbolic link under the project root refuses the handoff save', async ($, on) => {
  const w = engine(on)
  w.links = ['/proj/.claude/handoffs/.gitignore']
  await start($)
  w.answers = ['Wrap up first']
  await say($, 'Task until /session-token-utilization gets to 90%')
  await turn($, 't1')
  await measure($, w, 90)
  await end($, 't1')
  await wrapTurn($, w, 't2')
  await end($, 't2', 'notes')
  expect(w.written).toEqual({})
  expect(w.logs.at(-1)).toBe('token-utilization: handoff notes not saved to .claude/handoffs/HANDOFF-e139ab55.md: Error: .claude/handoffs/.gitignore is a symbolic link')
})

test('the state survives a reload', async ($, on) => {
  const w = engine(on)
  await start($)
  w.answers = ['Stop immediately']
  await say($, 'Task until /session-token-utilization gets to 90%')
  await turn($, 't1')
  await start($) // the reload
  expect(w.status).toBe('stop at session 90% (now 50%), immediate')
  await measure($, w, 90)
  expect(w.aborted).toEqual(['t1'])
})

test('T17: a decimal limit, a Remote Control prompt arms, a new limit replaces the old, a bad argument shows the usage', async ($, on) => {
  const w = engine(on)
  await start($)
  w.answers = ['Stop immediately']
  await say($, 'Task until /session-token-utilization gets to 89.5%', { kind: 'bridge' })
  expect(w.sent.at(-1)!.text).toBe('Task')
  expect(w.status).toBe('stop at session 89.5% (now 50%), immediate')
  w.answers = ['Wrap up first']
  await say($, 'Other until /weekly-token-utilization gets to 60%')
  expect(w.status).toBe('stop at weekly 60% (no reading yet), wrap-up')
  await turn($, 't1')
  await measure($, w, 99, 59) // the replaced session limit no longer counts
  expect(w.aborted).toEqual([])
  expect((await run($, 'token-utilization', 'now')).text).toBe('Usage: /token-utilization [off]')

  w.answers = ['Stop immediately']
  await say($, 'Again until /session-token-utilization gets to 99.5%')
  await measure($, w, 99)
  expect(w.aborted).toEqual([])
  await measure($, w, 100)
  expect(w.aborted).toEqual(['t1'])
})

test('T18: another mod\'s prompt after a stop asks; a typed limit during the wrap-up sets it; an idle immediate trip stops background subagents', async ($, on) => {
  const w = engine(on)
  await start($)
  w.answers = ['Wrap up first']
  await say($, 'Task until /session-token-utilization gets to 90%')
  await turn($, 't1')
  await measure($, w, 90)
  expect(w.status).toBe('wrapping up, cut off at session 95% (now 90%)')
  w.answers = ['Stop immediately']
  await say($, 'Keep going until /session-token-utilization gets to 97%')
  expect(w.status).toBe('stop at session 97% (now 90%), immediate')
  await end($, 't1')

  w.agents = [running('bg')]
  await measure($, w, 97) // idle: no turn to abort, the background subagent is stopped
  expect(w.aborted).toEqual(['t1'])
  expect(w.stopped).toEqual(['bg'])

  w.answers = ['No']
  const asked = w.asked.length
  expect((await say($, 'continue', { kind: 'plugin', name: 'auto-resume' })).drop).toMatch(/automatic prompt not run/)
  expect(w.asked.length).toBe(asked + 1)
})

test('a reload during the wrap-up keeps the ceiling and the wrap-up turn', async ($, on) => {
  const w = engine(on)
  await start($)
  w.answers = ['Wrap up first']
  await say($, 'Task until /session-token-utilization gets to 90%')
  await turn($, 't1')
  await measure($, w, 90)
  await end($, 't1')
  await wrapTurn($, w, 't2')
  await start($) // the reload
  expect(w.status).toBe('wrapping up, cut off at session 95% (now 90%)')
  await end($, 't2', 'Done: A.')
  expect(w.written[HANDOFF]).toBe('Done: A.')
})

test('T19: limit 0 is refused, 100 is accepted; the ceiling is capped at 100', async ($, on) => {
  const w = engine(on)
  await start($)
  expect((await say($, 'A until /session-token-utilization gets to 0%')).drop).toMatch(/name a percentage/)
  w.answers = ['Wrap up first']
  await say($, 'B until /session-token-utilization gets to 98%')
  await turn($, 't1')
  await measure($, w, 98)
  expect(w.aborted).toEqual(['t1'])
  expect(w.status).toBe('wrapping up, cut off at session 100% (now 98%)')
  expect(w.sent.at(-1)!.text).toContain('Usage is cut off at 100%.')
  w.answers = ['Stop immediately']
  await say($, 'C until /session-token-utilization gets to 100%')
  expect(w.status).toBe('stop at session 100% (now 98%), immediate')
})
