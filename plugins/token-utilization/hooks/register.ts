import type { Hook, PromptOrigin, Register } from 'claude-code'

type $ = Parameters<Hook<'turn.start'>>[0]
type Kind = 'five_hour' | 'seven_day'
type Limit = { kind: Kind; percent: number }
type Reading = { kind: string; percentUsed: number }
// Per session, in the store, so a reload keeps it.
type State = {
  limits: Limit[]
  mode: 'immediate' | 'wrap-up'
  phase: 'armed' | 'wrapping' | 'stopped'
  ceiling?: Limit // the window that tripped, at percent + 5 (max 100); cleared when it fires
  wrapTurnId?: string // the main turn whose final message is the handoff
  inject?: string // main-agent wrap-up text, attached to the main loop's next tool result
  warned?: boolean // the "no reading" warning was written
  stoppedIds?: string[] // subagents this mod stopped: their notifications are dropped
  messagedIds?: string[] // subagents sent the wrap-up text: their reports pass
}

const NAME: Record<Kind, string> = { five_hour: 'session', seven_day: 'weekly' }
const TOKEN = String.raw`(?<![\w./-])\/(session|weekly)-token-utilization(?![\w-])`
// "until /session-token-utilization gets to 90%": "until" through the percentage, within one sentence.
const CLAUSE = new RegExp(String.raw`(?:\buntil\s+)?${TOKEN}(?:[^\n/%.;!?]*?(\d+(?:\.\d+)?)\s*%)?`, 'gi')
const FORM = 'token-utilization: name a percentage from 1 to 100, e.g. "until /session-token-utilization gets to 90%". Prompt not sent.'
const IMMEDIATE = 'Stop immediately'
const WRAP = 'Wrap up first'
const YES = 'Yes, run it'
const ACTIVE = ['pending', 'running', 'waiting']
// In the main wrap-up prompt only. Its turn is the one whose turn.start text, framed by the engine
// as "The token-utilization plugin sent a message:\n<prompt>…", holds this; text that merely quotes
// the sentence (a task notification, a peer message) lacks the frame.
const WRAP_MARK = 'End with handoff notes as your final message'

function parse(text: string) {
  const limits: Limit[] = []
  let bad = false
  const marked = text.replace(CLAUSE, (_m, window: string, n?: string) => {
    const percent = Number(n)
    if (!n || !(percent >= 1 && percent <= 100)) bad = true
    limits.push({ kind: window.toLowerCase() === 'session' ? 'five_hour' : 'seven_day', percent })
    return '\0'
  })
  const rest = marked
    .replace(/\0(?:\s*,?\s*(?:\bor\b|\band\b)?\s*\0)+/gi, '\0') // "… or /weekly-…": one gap
    .replace(/\s*\0\s*([.,;:!?])/g, '$1')
    .replace(/\0/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
  return { limits, rest, bad }
}

const now = (readings: Reading[], kind: string) => readings.find(w => w.kind === kind)?.percentUsed
const at = (l: Limit, readings: Reading[]) => {
  const p = now(readings, l.kind)
  return `${NAME[l.kind]} ${l.percent}% (${p === undefined ? 'no reading yet' : `now ${p}%`})`
}

function statusText(s: State | undefined, readings: Reading[]) {
  if (!s) return undefined
  if (s.phase === 'armed') return `stop at ${s.limits.map(l => at(l, readings)).join(' or ')}, ${s.mode}`
  if (s.phase === 'wrapping') return `wrapping up, cut off at ${at(s.ceiling!, readings)}`
  return s.ceiling ? `stopped, subagents cut off at ${at(s.ceiling, readings)}` : 'stopped at the usage limit'
}

const stateKey = async ($: $) => `s:${await $.session.id()}`
const turnKey = async ($: $) => `t:${await $.session.id()}`
const readingsOf = async ($: $) => (await $.session.usage()).rateLimits as Reading[]
const debug = ($: $, text: string) => $.ui.log(`token-utilization: ${text}`, { to: 'debug' })
const handoffPath = async ($: $) => `.claude/handoffs/HANDOFF-${(await $.session.id()).slice(0, 8)}.md`

async function load($: $) {
  return (await $.store.get(await stateKey($))) as State | undefined
}

let queue: Promise<unknown> = Promise.resolve()
// Runs each read-modify-write of the state one at a time, so no hook saves a stale copy over
// another's write. fn must not wait on anything that runs this mod's hooks (abort, TaskStop,
// send, submit): it returns those as an effect for the caller to run after.
function change<T>(fn: () => Promise<T>): Promise<T> {
  const r = queue.then(fn)
  queue = r.catch(() => undefined)
  return r
}
type Effect = (() => Promise<void>) | undefined

async function save($: $, s: State | undefined, readings?: Reading[]) {
  const key = await stateKey($)
  if (s) await $.store.set(key, s)
  else await $.store.delete(key)
  $.ui.status(statusText(s, readings ?? (await readingsOf($))))
}

const activeAgents = async ($: $) => (await $.agent.list()).filter(a => ACTIVE.includes(a.status))

// Saves the stop and returns the effect that cancels the main turn and stops every running
// subagent; the state is saved first, so the notifications those stops raise are recognised as
// the mod's own.
async function stopAll($: $, s: State, readings: Reading[], log: string): Promise<Effect> {
  const agents = await activeAgents($)
  Object.assign(s, { phase: 'stopped', ceiling: undefined, inject: undefined, wrapTurnId: undefined })
  s.stoppedIds = [...(s.stoppedIds ?? []), ...agents.map(a => a.id)]
  await save($, s, readings)
  return async () => {
    const turnId = (await $.store.get(await turnKey($))) as string | undefined
    if (turnId) await $.turn.abort({ turnId }).catch(err => debug($, `abort failed: ${err}`))
    for (const a of agents) {
      const r = await $.tool.call({ tool: 'TaskStop', task_id: a.id }).catch(err => ({ deny: String(err) }))
      if ('deny' in r && r.deny !== undefined) debug($, `TaskStop ${a.id} failed: ${r.deny}`)
    }
    $.ui.log(log)
  }
}

const cap = (t: string) => t.charAt(0).toUpperCase() + t.slice(1)

function mainText(label: string, interrupted: boolean, subagents: boolean, path: string, cutoff: number) {
  const first = interrupted
    ? `You were interrupted because ${label}, the limit set for this task.`
    : `${cap(label)}, the limit set for this task.`
  return [
    `${first} Wrap up now:`,
    '',
    '- If only a little work is left, finish it.',
    '- Otherwise stop here and leave the work easy to continue.',
    '',
    `Do not start new work.${subagents ? ' Subagents received the same instruction; collect what they report.' : ''}`,
    `${WRAP_MARK}: what is done, what is in progress, what is left,`,
    `and the exact next step. That message is saved to ${path}; to resume later, read that file first. Usage is cut off at ${cutoff}%.`,
  ].join('\n')
}

const subText = (label: string, cutoff: number) =>
  `${cap(label)}, the limit set for this task. Wrap up now: if only a little work is ` +
  'left, finish it. Otherwise stop here and report what is done, what is in progress and what is ' +
  `left. Do not start new work. Usage is cut off at ${cutoff}%.`

// Saves the tripped state and returns the effect that acts on it.
async function trip($: $, s: State, limit: Limit, readings: Reading[]): Promise<Effect> {
  const label = `${NAME[limit.kind]} usage reached ${limit.percent}%`
  if (s.mode === 'immediate') return stopAll($, s, readings, `token-utilization: ${label}, stopped`)
  const ceiling = { kind: limit.kind, percent: Math.min(100, limit.percent + 5) }
  const turnId = (await $.store.get(await turnKey($))) as string | undefined
  const agents = await activeAgents($)
  const path = await handoffPath($)
  if (!agents.length) {
    if (!turnId) {
      await save($, { ...s, phase: 'stopped' }, readings)
      $.ui.log(`token-utilization: ${label}, stopped`)
      return undefined
    }
    await save($, { ...s, phase: 'wrapping', ceiling }, readings)
    return async () => {
      await $.turn.abort({ turnId }).catch(err => debug($, `abort failed: ${err}`))
      // Not awaited inside the measure hook. If the prompt never enters, stop instead of waiting
      // for a wrap-up turn that never comes.
      void $.prompt.submit({ text: mainText(label, true, false, path, ceiling.percent) })
        .then(r => { if (r.drop !== undefined) throw r.drop })
        .catch(async err => {
          $.ui.log(`token-utilization: wrap-up prompt not sent (${err}), stopped`)
          await change(async () => {
            const cur = await load($)
            if (cur?.phase === 'wrapping' && !cur.wrapTurnId) await save($, { ...cur, phase: 'stopped', ceiling: undefined })
          })
        })
      $.ui.log(`token-utilization: ${label}, wrapping up; cut off at ${ceiling.percent}%`)
    }
  }
  // Subagents running: message everyone, interrupt nobody.
  const next: State = { ...s, ceiling, messagedIds: [...(s.messagedIds ?? []), ...agents.map(a => a.id)] }
  if (turnId) Object.assign(next, { phase: 'wrapping', wrapTurnId: turnId, inject: mainText(label, false, true, path, ceiling.percent) })
  else next.phase = 'stopped'
  await save($, next, readings)
  return async () => {
    for (const a of agents) {
      const r = await $.session.send({ to: { agentId: a.id }, text: subText(label, ceiling.percent) }).catch(err => ({ isDelivered: false, reason: String(err) }))
      if (!r.isDelivered) debug($, `wrap-up message to ${a.id} not delivered: ${r.reason}`)
    }
    $.ui.log(`token-utilization: ${label}, ${turnId ? 'wrapping up' : 'stopped; subagents wrapping up'}; cut off at ${ceiling.percent}%`)
  }
}

// A prompt or command line naming a limit: undefined when it names none, else the text without
// the limit phrase, or the reason to refuse it.
async function arm($: $, text: string): Promise<{ rest: string } | { drop: string } | undefined> {
  const { limits, rest, bad } = parse(text)
  if (!limits.length) return undefined
  if (bad) return { drop: FORM }
  const readings = await readingsOf($)
  for (const l of limits) {
    const p = now(readings, l.kind)
    if (p !== undefined && p >= l.percent) {
      return { drop: `token-utilization: ${NAME[l.kind]} usage is already at ${p}%, past the ${l.percent}% limit. Prompt not sent.` }
    }
  }
  const answer = await $.ui.ask('What should happen when the limit is reached?', [IMMEDIATE, WRAP]).catch(() => undefined)
  if (answer !== IMMEDIATE && answer !== WRAP) return { drop: 'token-utilization: no stop mode chosen. Prompt not sent.' }
  await change(() => save($, { limits, mode: answer === IMMEDIATE ? 'immediate' : 'wrap-up', phase: 'armed' }, readings))
  return { rest }
}

const isTyped = (o: PromptOrigin) => o.kind === 'composer' || o.kind === 'bridge'
// A -p prompt naming a limit is handled like a typed one (and dropped, as nobody can be asked).
const mayArm = (o: PromptOrigin) => isTyped(o) || o.kind === 'sdk'

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'token-utilization',
      description: 'Show the usage limit set for this session, or remove it with off',
      argumentHint: '[off]',
    })
    await change(async () => save($, await load($))) // redraw the status after a reload or a resume
    return next(e)
  })

  on('turn.start', async ($, e, next) => {
    if (e.agentId === undefined) {
      await $.store.set(await turnKey($), e.turnId)
      // Only the mod's own wrap-up prompt starts the wrap-up turn; a turn queued ahead of it
      // (a task notification, a scheduled prompt) leaves the state waiting.
      if (e.text.startsWith(`The ${$.plugin.name} plugin sent a message:`) && e.text.includes(WRAP_MARK)) {
        await change(async () => {
          const s = await load($)
          if (s?.phase === 'wrapping' && !s.wrapTurnId) await save($, { ...s, wrapTurnId: e.turnId })
        })
      }
    }
    return next(e)
  })

  on('turn.complete', async ($, e, next) => {
    const r = await next(e)
    if (e.agentId !== undefined) return r
    const key = await turnKey($)
    if ((await $.store.get(key)) === e.turnId) await $.store.delete(key)
    const wrapped = await change(async () => {
      const s = await load($)
      if (s?.wrapTurnId === e.turnId) {
        await save($, { ...s, phase: 'stopped', wrapTurnId: undefined, inject: undefined })
        return true
      }
      if (s?.phase === 'armed' && !s.warned) {
        const readings = await readingsOf($)
        const missing = s.limits.filter(l => now(readings, l.kind) === undefined)
        if (missing.length) {
          $.ui.log(`token-utilization: no ${missing.map(l => NAME[l.kind]).join(' or ')} usage reading yet, so the limit cannot take effect`)
          await save($, { ...s, warned: true }, readings)
        }
      }
      return false
    })
    if (wrapped) {
      const path = await handoffPath($)
      const root = await $.session.root()
      try {
        if (e.reason !== 'answer') throw new Error(`the wrap-up turn ended with ${e.reason}`)
        // A repository can commit any of these as a symbolic link; writing through one would land
        // outside the project, so a link anywhere below the root refuses the save.
        for (const p of ['.claude', '.claude/handoffs', '.claude/handoffs/.gitignore', path]) {
          if (await $.fs.stat(`${root}/${p}`).then(s => s.isLink, () => false)) throw new Error(`${p} is a symbolic link`)
        }
        await $.fs.write(`${root}/${path}`, e.answer)
        await $.fs.write(`${root}/.claude/handoffs/.gitignore`, '*\n')
        $.ui.log(`token-utilization: handoff notes saved to ${path}`)
      } catch (err) {
        $.ui.log(`token-utilization: handoff notes not saved to ${path}: ${err}`)
      }
    }
    return r
  })

  // The main agent's wrap-up text while subagents run: read with its next tool result, once.
  on('tool.call', async ($, e, next) => {
    const r = await next(e)
    if (e.agentId !== undefined || e.tool === 'AskUserQuestion' || ('deny' in r && r.deny !== undefined)) return r
    const inject = await change(async () => {
      const s = await load($)
      if (s?.inject) await save($, { ...s, inject: undefined })
      return s?.inject
    })
    if (!inject) return r
    return { ...r, context: [...(r.context ?? []), inject] } as typeof r
  })

  on('prompt.submit', async ($, e, next) => {
    const o = e.origin
    if ((o.kind === 'plugin' && o.name === $.plugin.name) || e.command?.name === 'token-utilization') return next(e)
    // A slash command's limit is handled at command.run, which runs first.
    if (!e.command && mayArm(o)) {
      const r = await arm($, e.text)
      if (r && 'drop' in r) return { drop: r.drop }
      if (r) return next({ ...e, text: r.rest })
    }
    const s = await load($)
    if (!s) return next(e)
    if (isTyped(o)) {
      // A typed prompt ends the wrap-up or the stop.
      if (s.phase !== 'armed') await change(async () => { if ((await load($))?.phase !== 'armed') await save($, undefined) })
      return next(e)
    }
    if (s.phase !== 'stopped') return next(e)
    if (o.kind === 'task-notification') {
      // ponytail: reads the id from the notification's text format; if that format changes, these
      // notifications fall back to the restart question. Use a structured task id if the event gains one.
      const id = /<task-id>([^<]+)<\/task-id>/.exec(e.text)?.[1]
      if (id && s.stoppedIds?.includes(id)) return { drop: 'token-utilization: dropped the notification of a subagent it stopped.' }
      if (id && s.messagedIds?.includes(id)) return next(e)
    }
    try {
      const sent = await $.ui.notify('An automatic prompt is waiting for your answer', { title: 'token-utilization' })
      if (!sent.isSent) debug($, `notification not sent: ${sent.reason}`)
    } catch (err) {
      debug($, `notification not sent: ${err}`)
    }
    const answer = await $.ui.ask('The usage limit was reached. Run this automatic prompt?', [YES, 'No']).catch(() => undefined)
    if (answer !== YES) return { drop: 'token-utilization: automatic prompt not run, the usage limit was reached.' }
    await change(() => save($, undefined))
    return next(e)
  })

  on('command.run', async ($, e, next) => {
    if (e.command === 'token-utilization') {
      const arg = e.args.trim().toLowerCase()
      if (arg === 'off') {
        await change(() => save($, undefined))
        return { text: 'token-utilization: limit removed.' }
      }
      if (arg) return { text: 'Usage: /token-utilization [off]' }
      const s = await load($)
      if (!s) return { text: 'token-utilization: no limit is set.' }
      const readings = await readingsOf($)
      return { text: `token-utilization: ${s.limits.map(l => at(l, readings)).join(' or ')}, mode ${s.mode}, ${s.phase}.` }
    }
    if (mayArm(e.origin)) {
      const r = await arm($, e.args)
      if (r && 'drop' in r) return { text: r.drop }
      if (r) return next({ ...e, args: r.rest })
    }
    return next(e)
  })

  on('session.measure', async ($, e, next) => {
    const readings = e.rateLimits as Reading[]
    const reached = (l: Limit) => (now(readings, l.kind) ?? -1) >= l.percent
    const effect = await change(async (): Promise<Effect> => {
      const s = await load($)
      const hit = s?.phase === 'armed' ? s.limits.find(reached) : undefined
      if (s && hit) return trip($, s, hit, readings)
      if (s?.ceiling && reached(s.ceiling)) {
        return stopAll($, s, readings, `token-utilization: ${NAME[s.ceiling.kind]} usage reached ${s.ceiling.percent}% during the wrap-up, stopped`)
      }
      if (s) $.ui.status(statusText(s, readings)) // nothing changed but the readings
      return undefined
    })
    await effect?.()
    return next(e)
  })
}
