import type { On } from 'claude-code'
import { expect, mock, test } from 'claude-code/testing'
import type { Engine } from 'claude-code/testing'

const NOW = Date.parse('2026-11-13T12:00:00Z')
const RESET = '2026-11-13T15:00:00Z'
const MIN = 60_000

// The engine beneath the mod: one session, a usage reading, and a record of what it submitted.
function engine(on: On, percentUsed = 100) {
  const clock = mock.clock(on, { now: NOW })
  mock.store(on)
  const sent: string[] = []
  const ran: { command: string; args: string }[] = []
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  on('session.id', () => ({ value: 'S1' }))
  on('command.register', (_, e) => ({ value: { command: e.name } }))
  on('ui.status', () => ({ value: undefined }))
  on('session.usage', () => ({
    value: {
      startedAt: NOW,
      context: { used: 0, total: 1 } as never,
      rateLimits: [{ kind: 'five_hour', percentUsed, resetsAt: RESET }],
    },
  }))
  on('prompt.submit', (_, e) => (sent.push(e.text), { text: e.text }))
  on('command.run', (_, e) => (ran.push({ command: e.command, args: e.args }), { text: '' }))
  on('turn.start', (_, e) => ({ turnId: e.turnId }))
  on('classic.StopFailure', () => ({}) as never)
  return { clock, sent, ran }
}

const start = ($: Engine) => $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
const limit = ($: Engine, extra = {}) => $.classic.StopFailure({ error: 'rate_limit', ...extra })
const composer = { kind: 'composer' } as const

test('a prompt with /auto-resume continues after the reset, the token stripped', async ($, on) => {
  const { clock, sent } = engine(on)
  await start($)
  await $.prompt.submit({ text: 'do the thing /auto-resume', wait: false, origin: composer })
  expect(sent).toEqual(['do the thing'])

  await limit($)
  await clock.advance(3 * 60 * MIN) // reset time reached, buffer not yet
  expect(sent.length).toBe(1)
  await clock.advance(4 * MIN)
  expect(sent).toEqual(['do the thing', 'continue'])
})

test('/plan-implement-complete /auto-resume arms it and the command gets clean args', async ($, on) => {
  const { clock, sent, ran } = engine(on)
  await start($)
  await $.command.run({ command: 'plan-tools:plan-implement-complete', args: 'plan.md /auto-resume', origin: composer } as never)
  expect(ran.at(-1)).toEqual({ command: 'plan-tools:plan-implement-complete', args: 'plan.md' })

  await limit($)
  await clock.advance(4 * 60 * MIN)
  expect(sent).toEqual(['continue'])
})

test('without arming, nothing is sent; /auto-resume on arms every session, off disarms', async ($, on) => {
  const { clock, sent } = engine(on)
  await start($)
  await limit($)
  await clock.advance(4 * 60 * MIN)
  expect(sent).toEqual([])

  await $.command.run({ command: 'auto-resume', args: 'on', origin: composer } as never)
  await limit($)
  await $.command.run({ command: 'auto-resume', args: 'off', origin: composer } as never)
  await clock.advance(4 * 60 * MIN)
  expect(sent).toEqual([])

  await $.command.run({ command: 'auto-resume', args: 'on', origin: composer } as never)
  await limit($)
  await clock.advance(4 * 60 * MIN)
  expect(sent).toEqual(['continue'])
})

test('a main-loop turn before the reset cancels; a subagent turn or limit does not', async ($, on) => {
  const { clock, sent } = engine(on)
  await start($)
  await $.command.run({ command: 'auto-resume', args: 'on', origin: composer } as never)

  await limit($, { agent_id: 'a1' }) // a subagent's limit: ignored
  await clock.advance(4 * 60 * MIN)
  expect(sent).toEqual([])

  await limit($)
  await $.turn.start({ text: '', turnId: 't1', agentId: 'a1' })
  await clock.advance(10 * MIN)
  await $.turn.start({ text: '', turnId: 't2' }) // the built-in auto-continue ran
  await clock.advance(4 * 60 * MIN)
  expect(sent).toEqual([])
})

test('no exhausted window reported: retry in 30 minutes', async ($, on) => {
  const { clock, sent } = engine(on, 40)
  await start($)
  await $.command.run({ command: 'auto-resume', args: 'on', origin: composer } as never)
  await limit($)
  await clock.advance(29 * MIN)
  expect(sent).toEqual([])
  await clock.advance(2 * MIN)
  expect(sent).toEqual(['continue'])
})

test('a new prompt typed by the person ends the one-task arming', async ($, on) => {
  const { clock, sent } = engine(on)
  await start($)
  await $.prompt.submit({ text: 'task /auto-resume', wait: false, origin: composer })
  await $.prompt.submit({ text: 'something else', wait: false, origin: composer })
  await limit($)
  await clock.advance(4 * 60 * MIN)
  expect(sent).toEqual(['task', 'something else'])
})

const run = ($: Engine, args = '') => $.command.run({ command: 'auto-resume', args, origin: composer } as never)

test('bare /auto-resume reports off, on for the task, on for every session, and the next send', async ($, on) => {
  engine(on)
  await start($)
  expect((await run($)).text).toBe('Auto-resume is off.')

  await $.prompt.submit({ text: 'task /auto-resume', wait: false, origin: composer })
  expect((await run($)).text).toBe('Auto-resume is on for the current task.')

  await run($, 'on')
  expect((await run($)).text).toBe('Auto-resume is on for every session.')

  await limit($)
  expect((await run($)).text).toMatch(/^Auto-resume is on for every session\. Next "continue" at .+\.$/)
})

test('on/off confirm and are case-insensitive; an invalid arg shows usage and changes nothing', async ($, on) => {
  const { clock, sent } = engine(on)
  await start($)
  expect((await run($, ' ON ')).text).toBe('Auto-resume is on for every session.')
  expect((await run($, 'maybe')).text).toBe('Usage: /auto-resume on | off, or add /auto-resume to a prompt.')
  expect((await run($)).text).toBe('Auto-resume is on for every session.') // still on
  await limit($)
  await clock.advance(4 * 60 * MIN)
  expect(sent).toEqual(['continue'])
})

test('/auto-resume typed alone as a prompt does not arm', async ($, on) => {
  const { clock, sent } = engine(on)
  await start($)
  await $.prompt.submit({ text: '/auto-resume', command: { name: 'auto-resume', args: '' }, wait: false, origin: composer } as never)
  expect((await run($)).text).toBe('Auto-resume is off.')
  await limit($)
  await clock.advance(4 * 60 * MIN)
  expect(sent).toEqual(['/auto-resume'])
})

test('a token inside a word is not a token', async ($, on) => {
  const { clock, sent } = engine(on)
  await start($)
  await $.prompt.submit({ text: 'see docs/auto-resume.md and x/auto-resume', wait: false, origin: composer })
  await limit($)
  await clock.advance(4 * 60 * MIN)
  expect(sent).toEqual(['see docs/auto-resume.md and x/auto-resume'])
})

test('a StopFailure that is not rate_limit is ignored', async ($, on) => {
  const { clock, sent } = engine(on)
  await start($)
  await run($, 'on')
  await $.classic.StopFailure({ error: 'server_error' } as never)
  await clock.advance(4 * 60 * MIN)
  expect(sent).toEqual([])
  expect((await run($)).text).toBe('Auto-resume is on for every session.') // nothing scheduled
})

test('a second StopFailure reschedules instead of doubling the send', async ($, on) => {
  const { clock, sent } = engine(on)
  await start($)
  await run($, 'on')
  await limit($)
  await clock.advance(60 * MIN)
  await limit($) // same reset time again: still one send
  await clock.advance(4 * 60 * MIN)
  expect(sent).toEqual(['continue'])
  await clock.advance(4 * 60 * MIN)
  expect(sent).toEqual(['continue'])
})

test('a pending send is restored after a reload (session.start again, same store)', async ($, on) => {
  const { clock, sent } = engine(on)
  await start($)
  await run($, 'on')
  await limit($)
  await clock.advance(60 * MIN)
  await start($) // the reload
  expect((await run($)).text).toMatch(/Next "continue" at/)
  await clock.advance(4 * 60 * MIN)
  expect(sent).toEqual(['continue'])
})

test('/auto-resume off cancels a pending send', async ($, on) => {
  const { clock, sent } = engine(on)
  await start($)
  await run($, 'on')
  await limit($)
  await run($, 'off')
  expect((await run($)).text).toBe('Auto-resume is off.')
  await clock.advance(4 * 60 * MIN)
  expect(sent).toEqual([])
})
