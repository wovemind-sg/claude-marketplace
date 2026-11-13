import type { Hook, Register } from 'claude-code'

type $ = Parameters<Hook<'turn.start'>>[0]
// Per session: armed for one task (`once`) and when to send "continue" (`resetAt`, epoch ms).
type Pending = { once: boolean; resetAt: number | null }

const TOKEN = /(^|\s)\/auto-resume(?=\s|$)/g
const BUFFER = 3 * 60_000 // let the built-in auto-continue go first
const RETRY = 30 * 60_000 // no reset time reported: try again in 30 minutes
const TICK = 60_000 // compare wall clock each minute, so a sleeping laptop catches up

const strip = (text: string) => text.replace(TOKEN, ' ').replace(/\s+/g, ' ').trim()
const hasToken = (text: string) => new RegExp(TOKEN.source).test(text)
const time = (ms: number) => new Date(ms).toLocaleString([], { weekday: 'short', hour: '2-digit', minute: '2-digit' })

async function load($: $): Promise<Pending> {
  const v = (await $.store.get(`s:${await $.session.id()}`)) as Pending | undefined
  return { once: v?.once ?? false, resetAt: v?.resetAt ?? null }
}

async function save($: $, p: Pending) {
  const key = `s:${await $.session.id()}`
  if (!p.once && p.resetAt === null) await $.store.delete(key)
  else await $.store.set(key, p)
  $.ui.status(p.resetAt === null ? undefined : `auto-resume at ${time(p.resetAt)}`)
}

async function patch($: $, change: Partial<Pending>) {
  await save($, { ...(await load($)), ...change })
}

const isAlways = async ($: $) => (await $.store.get('always')) === true

// Latest reset among the exhausted windows; a retry when the API reported none.
async function resetTime($: $): Promise<number> {
  const now = await $.clock.now()
  const { rateLimits } = await $.session.usage()
  const times = rateLimits
    .filter(w => w.percentUsed >= 100 && w.resetsAt)
    .map(w => Date.parse(w.resetsAt as string))
    .filter(t => t > now)
  return times.length ? Math.max(...times) + BUFFER : now + RETRY
}

async function tick($: $) {
  const p = await load($)
  if (p.resetAt === null || (await $.clock.now()) < p.resetAt) return
  await save($, { ...p, resetAt: null })
  await $.prompt.submit({ text: 'continue' })
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'auto-resume',
      description: 'Send "continue" when a usage limit resets: on, off, or add /auto-resume to a prompt for that task only',
      argumentHint: '[on|off]',
    })
    await save($, await load($)) // redraw the status after a reload or a resume
    $.clock.every(TICK, () => void tick($))
    return next(e)
  })

  on('command.run', async ($, e, next) => {
    if (e.command === 'auto-resume') {
      const arg = e.args.trim().toLowerCase()
      if (arg === 'on' || arg === 'off') {
        await $.store.set('always', arg === 'on')
        if (arg === 'off') await save($, { once: false, resetAt: null })
        return { text: `Auto-resume is ${arg} for every session.` }
      }
      if (arg) return { text: 'Usage: /auto-resume on | off, or add /auto-resume to a prompt.' }
      const p = await load($)
      const mode = (await isAlways($)) ? 'on for every session' : p.once ? 'on for the current task' : 'off'
      return { text: `Auto-resume is ${mode}.${p.resetAt ? ` Next "continue" at ${time(p.resetAt)}.` : ''}` }
    }
    // `/some-command … /auto-resume`: arm for this task and keep the token out of the command's args.
    if (!hasToken(e.args)) return next(e)
    await patch($, { once: true })
    return next({ ...e, args: strip(e.args) })
  })

  on('prompt.submit', async ($, e, next) => {
    if (e.command?.name === 'auto-resume') return next(e)
    if (hasToken(e.text)) {
      await patch($, { once: true })
      // A slash command's line can't be rewritten here; command.run strips its args.
      return next(e.command ? e : { ...e, text: strip(e.text) })
    }
    // A new prompt typed by the person starts a new task: the one-task arming ends.
    if (e.origin.kind === 'composer') await patch($, { once: false })
    return next(e)
  })

  on('turn.start', async ($, e, next) => {
    // Any main-loop turn means the session moved on (our "continue", the built-in
    // auto-continue, or the person): drop the pending send.
    if (e.agentId === undefined) await patch($, { resetAt: null })
    return next(e)
  })

  on('classic.StopFailure', async ($, e, next) => {
    if (e.error === 'rate_limit' && !e.agent_id && ((await isAlways($)) || (await load($)).once)) {
      await patch($, { resetAt: await resetTime($) })
    }
    return next(e)
  })
}
