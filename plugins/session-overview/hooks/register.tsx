import { atom, read, update } from 'claude-code'
import type { Register } from 'claude-code'

import type { Session } from '../types'

const PANE = 'sessions'
const ORDER = ['waiting', 'running', 'idle', 'ended'] as const
const COLOR = {
  running: 'success',
  waiting: 'warning',
  idle: 'subtle',
  ended: 'inactive',
} as const

const GLYPH = { running: '●', waiting: '◆', idle: '○', ended: '✕' } as const

const sessions = atom({ plugin: 'session-overview', key: 'sessions' } as const, [] as Session[])
const starred = atom({ plugin: 'session-overview', key: 'starred' } as const, [] as string[])
const hiddenTypes = atom({ plugin: 'session-overview', key: 'hiddenTypes' } as const, [] as string[])

type Entry = {
  pid: number
  sessionId: string
  cwd: string
  status: string
  waitingFor?: string | null
  kind?: string
  entrypoint?: string
  name?: string
  nameSource?: string
  tmux?: string
  updatedAt?: number
}

export const stateOf = (entry: Pick<Entry, 'status'>, alive: boolean): Session['state'] =>
  !alive ? 'ended' : entry.status === 'busy' ? 'running' : entry.status === 'waiting' ? 'waiting' : 'idle'

export const typeOf = (e: Pick<Entry, 'kind' | 'entrypoint'>) =>
  e.kind === 'bg' ? 'bg' : (e.entrypoint ?? e.kind ?? 'unknown')

export const projectOf = (cwd: string, home: string) => {
  const m = /^(.*)\/\.claude\/worktrees\/([^/]+)/.exec(cwd)
  const dir = m?.[1] ?? cwd
  const path = dir === home ? '~' : home && dir.startsWith(home + '/') ? '~' + dir.slice(home.length) : dir
  return { path, worktree: m?.[2] }
}

export const transcriptPath = (home: string, cwd: string, id: string) =>
  `${home}/.claude/projects/${cwd.replace(/[^A-Za-z0-9]/g, '-')}/${id}.jsonl`

export const groupSessions = (list: Session[], hidden: string[], home: string, stars: string[] = []) => {
  const groups = new Map<string, Session[]>()
  for (const s of list) {
    if (hidden.includes(s.type)) continue
    const { path } = projectOf(s.cwd, home)
    groups.set(path, [...(groups.get(path) ?? []), s])
  }
  // Starred sessions lead their project, then waiting/running above idle/ended.
  const rank = (s: Session) => (stars.includes(s.sessionId) ? 0 : ORDER.length) + ORDER.indexOf(s.state)
  // Most recently updated project first.
  const latest = (rows: Session[]) => Math.max(...rows.map(s => s.updatedAt))
  return [...groups]
    .map(([path, rows]) => ({ path, rows: rows.sort((a, b) => rank(a) - rank(b)) }))
    .sort((a, b) => latest(b.rows) - latest(a.rows) || a.path.localeCompare(b.path))
}

const none = { stdout: '' }

// updatedAt is epoch ms; 0 means unknown. "Today" is the viewer's local calendar day.
export const activeToday = (updatedAt: number, now = Date.now()) =>
  updatedAt > 0 && new Date(updatedAt).toDateString() === new Date(now).toDateString()

// Registry and transcript text is untrusted: drop control chars (ANSI/OSC escapes) and cap length.
export const clean = (v: unknown, max = 200) =>
  (typeof v === 'string' ? v : '').replace(/[\u0000-\u001f\u007f-\u009f\u2028\u2029]/g, ' ').slice(0, max)

// sessionId becomes a filename and pid an ps argv entry: reject anything else.
export const validEntry = (e: any): e is Entry =>
  !!e && typeof e === 'object' && Number.isInteger(e.pid) && e.pid > 0 &&
  typeof e.sessionId === 'string' && /^[A-Za-z0-9_-]{1,100}$/.test(e.sessionId) &&
  typeof e.cwd === 'string'

// tmux target "<session>:@<win>.%<pane>"; the pane id alone is unique on the server.
export const tmuxPane = (v: unknown) => (typeof v === 'string' && /:@\d+\.(%\d+)$/.exec(v)?.[1]) || null

const firstLine = (s: string) => s.trim().split('\n')[0] ?? ''

export const GOAL_TTL_MS = 30_000

const TITLE_SYSTEM =
  'Write a title of 3 to 6 words for a coding session that starts with the message below. ' +
  'Sentence case, no quotes, no trailing period. Reply with the title only.'

// One line, no quotes or trailing period, capped: the model reply goes straight into the session title.
export const toTitle = (reply: string) =>
  clean(reply.trim().split('\n')[0] ?? '', 60).replace(/^["'`]+|["'`.]+$/g, '').trim()

type GoalDeps = {
  home: string
  now: () => number
  exists: (path: string) => Promise<boolean>
  run: (argv: string[]) => Promise<{ stdout: string }>
}

// Goal lookup with a per-session 30s re-grep throttle and a per-session transcript-path cache.
export const makeGoalLookup = (d: GoalDeps) => {
  const goals = new Map<string, { at: number; goal: string }>()
  const found = new Map<string, string | null>() // sessionId -> located transcript (null = not found)
  const parse = (l: string) => { try { return JSON.parse(l) } catch { return undefined } }

  const locate = async (e: Entry) => {
    const derived = transcriptPath(d.home, e.cwd, e.sessionId)
    if (await d.exists(derived)) return derived
    if (!found.has(e.sessionId)) {
      // sessionId is validated by validEntry, so it is safe as a -name pattern.
      const r = await d.run(['find', `${d.home}/.claude/projects`, '-maxdepth', '2', '-name', `${e.sessionId}.jsonl`]).catch(() => none)
      found.set(e.sessionId, firstLine(r.stdout) || null)
    }
    return found.get(e.sessionId) ?? undefined
  }

  const goalOf = async (e: Entry) => {
    // A title the person set with /rename wins over the AI title.
    if (e.nameSource === 'user' && e.name) return e.name
    const hit = goals.get(e.sessionId)
    if (hit && d.now() - hit.at < GOAL_TTL_MS) return hit.goal
    const path = await locate(e)
    if (!path) return e.name ?? ''
    const titles = await d.run(['grep', '-e', '"type":"ai-title"', '--', path]).catch(() => none)
    let goal: string = parse(titles.stdout.trim().split('\n').pop() ?? '')?.aiTitle ?? ''
    if (!goal) {
      const users = await d.run(['grep', '-m', '5', '-e', '"type":"user"', '--', path]).catch(() => none)
      for (const l of users.stdout.split('\n')) {
        const c = parse(l)?.message?.content
        if (typeof c === 'string' && c.trim() && !c.trimStart().startsWith('<')) { goal = firstLine(c); break }
      }
    }
    goal ||= e.name ?? ''
    goals.set(e.sessionId, { at: d.now(), goal })
    return goal
  }

  // Drop cache entries for sessions no longer in the registry.
  const prune = (ids: Iterable<string>) => {
    const keep = new Set(ids)
    for (const m of [goals, found]) for (const k of m.keys()) if (!keep.has(k)) m.delete(k)
  }

  return { goalOf, prune, size: () => goals.size + found.size }
}

let timer: { cancel: () => void } | undefined
const stop = () => {
  timer?.cancel()
  timer = undefined
}

const openPane = async ($: any, focus: boolean) => {
  const home = (await $.env.get('HOME')) ?? ''

  const { goalOf, prune } = makeGoalLookup({
    home,
    now: Date.now,
    exists: p => $.fs.stat(p).then(() => true, () => false),
    run: argv => $.process.run(argv),
  })

  let busy = false
  const refresh = async () => {
    if (busy) return
    busy = true
    try {
      await loadSaved($)
      const files = (await $.fs.list(`${home}/.claude/sessions`)).filter((f: { name: string }) => f.name.endsWith('.json'))
      const entries: Entry[] = []
      for (const f of files) {
        try { const e = JSON.parse(await $.fs.read(`${home}/.claude/sessions/${f.name}`) as string); if (validEntry(e)) entries.push(e) } catch { /* half-written file */ }
      }
      prune(entries.map(e => e.sessionId))
      const ps = entries.length
        ? await $.process.run(['ps', '-p', entries.map(e => e.pid).join(','), '-o', 'pid=']).catch(() => none)
        : undefined
      const live = new Set(ps?.stdout.split('\n').map((s: string) => Number(s.trim())))
      const list = await Promise.all(entries.map(async (e): Promise<Session> => ({
        pid: e.pid,
        sessionId: e.sessionId,
        cwd: clean(e.cwd, 500),
        type: clean(typeOf(e), 40),
        state: stateOf(e, live.has(e.pid)),
        waitingFor: e.waitingFor ? clean(e.waitingFor) : null,
        goal: clean(await goalOf(e)),
        pane: tmuxPane(e.tmux),
        updatedAt: Number.isFinite(e.updatedAt) ? e.updatedAt! : 0,
      })))
      await update($, sessions, () => list)
    } catch { /* keep the last list; try again next tick */ } finally { busy = false }
  }

  const res = await $.ui.open({ id: PANE, title: 'Sessions', ...(focus ? { focus: true as const } : {}) })
  stop()
  await refresh()
  // shortcut: pid reuse after a crash could show a dead session as live; compare procStart if it shows up.
  timer = $.clock.every(3000, () => void refresh())
  return res
}


// Other open sessions may have changed these; re-read on session.start and on every pane refresh.
const loadSaved = async ($: any) => {
  const saved = await $.store.get('hiddenTypes').catch(() => undefined)
  if (Array.isArray(saved)) await update($, hiddenTypes, () => saved as string[])
  const savedStars = await $.store.get('starred').catch(() => undefined)
  if (Array.isArray(savedStars)) await update($, starred, () => savedStars as string[])
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({ name: 'sessions', description: 'Show every open Claude Code session in a pane (`/sessions auto on|off` opens it on every new session)' })
    await loadSaved($)
    // Also fires on /clear, so the pane comes back after it. Not focused: don't steal the prompt's keys.
    if (e.isInteractive && (await $.store.get('autoOpen')) === true) await openPane($, false).catch(() => undefined)
    return next(e)
  })

  // Name a session that has no title yet from its first prompt, with Haiku.
  on('classic.UserPromptSubmit', async ($, e, next) => {
    const result = await next(e)
    const prompt = e.prompt.trim()
    if (e.session_title || result.block || (e.source && e.source !== 'user') || !prompt || prompt.startsWith('/')) return result
    const reply = await $.model
      .complete({ model: 'haiku', system: TITLE_SYSTEM, prompt: prompt.slice(0, 4000), maxTokens: 30, timeoutMs: 5000 })
      .catch(() => undefined)
    const title = reply?.isAnswered ? toTitle(reply.text) : ''
    return title ? { ...result, sessionTitle: title } : result
  })

  on('command.run', { command: 'sessions' }, async ($, e) => {
    const arg = e.args.trim().toLowerCase()
    if (arg === 'auto on' || arg === 'auto off') {
      await $.store.set('autoOpen', arg === 'auto on')
      return { text: arg === 'auto on' ? 'Sessions pane will open on every new session.' : 'Sessions pane will no longer open automatically.' }
    }
    const res = await openPane($, true)
    return { text: res.isPlaced ? 'Sessions pane opened.' : `Sessions pane open but not placed: ${res.reason}` }
  })

  on('ui.close', { id: PANE }, async ($, e, next) => {
    stop()
    return next(e)
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text, Button } = $.ui.resolve(e)
    const home = (await $.env.get('HOME')) ?? ''
    const current = await Promise.resolve().then(() => $.session.id()).catch(() => '')
    const list = await read($, sessions)
    const hidden = await read($, hiddenTypes)
    const stars = await read($, starred)
    const types = [...new Set(list.map(s => s.type))].sort()
    const groups = groupSessions(list, hidden, home, stars)

    // Non-zero exit resolves (does not reject), so check exitCode as well as catching a failed start.
    const jump = async (pane: string) => {
      const r = await $.process.run(['tmux', 'switch-client', '-t', pane]).catch(() => undefined)
      if (r?.exitCode !== 0) $.ui.toast("Couldn't switch to that tmux pane")
    }

    const toggle = async (t: string) => {
      await loadSaved($) // start from what other sessions saved, not this pane's up-to-3s-old copy
      const h = await read($, hiddenTypes)
      const next = h.includes(t) ? h.filter(x => x !== t) : [...h, t]
      await $.store.set('hiddenTypes', next) // store first: a refresh between the two would otherwise revert the atom
      await update($, hiddenTypes, () => next)
    }

    const toggleStar = async (id: string) => {
      await loadSaved($)
      const cur = await read($, starred)
      const next = cur.includes(id) ? cur.filter(x => x !== id) : [...cur, id]
      await $.store.set('starred', next) // store first: a refresh between the two would otherwise revert the atom
      await update($, starred, () => next)
    }

    const shown = groups.flatMap(g => g.rows)
    const count = (state: Session['state']) => shown.filter(x => x.state === state).length
    const summary = [
      [count('waiting'), 'need you', COLOR.waiting],
      [count('running'), 'running', COLOR.running],
      [count('idle'), 'idle', undefined],
      [count('ended'), 'ended', undefined],
    ].filter(([n]) => n) as [number, string, string | undefined][]
    const title = (s: Session) => (
      <Text>
        <Text weight={s.sessionId === current ? 'bold' : undefined} color={s.sessionId === current ? 'claude' : undefined}>
          {s.goal || 'Untitled session'}
        </Text>
        {s.sessionId === current && <Text dimColor> (this one)</Text>}
        {activeToday(s.updatedAt) && <Text dimColor> today</Text>}
      </Text>
    )
    const split = (path: string) => {
      const cut = path.lastIndexOf('/')
      return cut > 0 ? { name: path.slice(cut + 1), parent: path.slice(0, cut) } : { name: path, parent: '' }
    }

    return (
      <Box flexDirection="column">
        <Text>
          {summary.length === 0 && <Text dimColor>No sessions open.</Text>}
          {summary.map(([n, label, color], i) => (
            <Text key={label} color={color} dimColor={!color}>
              {i ? '   ' : ''}{n} {label}
            </Text>
          ))}
        </Text>
        {groups.map(g => (
          <Box key={g.path} flexDirection="column" marginTop={1}>
            <Text wrap="truncate-end">
              <Text weight="bold">{split(g.path).name}</Text>
              <Text dimColor>  {split(g.path).parent}</Text>
            </Text>
            {g.rows.map(s => {
              const worktree = projectOf(s.cwd, home).worktree
              return (
                <Box key={s.sessionId} flexDirection="column" paddingLeft={2}>
                  <Box>
                    <Button key={`star-${s.sessionId}`} plain onPress={() => toggleStar(s.sessionId)}>
                      <Text color={stars.includes(s.sessionId) ? 'warning' : undefined} dimColor={!stars.includes(s.sessionId)}>
                        {stars.includes(s.sessionId) ? '★' : '☆'}{' '}
                      </Text>
                    </Button>
                  {s.pane && s.state !== 'ended' ? (
                    <Button key={`jump-${s.sessionId}`} plain onPress={() => jump(s.pane!)}>
                      <Text wrap="truncate-end">
                        <Text color={COLOR[s.state]}>{GLYPH[s.state]}</Text> {title(s)}
                      </Text>
                    </Button>
                  ) : (
                    <Text wrap="truncate-end">
                      <Text color={COLOR[s.state]}>{GLYPH[s.state]}</Text> {title(s)}
                    </Text>
                  )}
                  </Box>
                  {s.state === 'waiting' && (
                    <Text color={COLOR.waiting} wrap="truncate-end">  waiting: {s.waitingFor || 'your reply'}</Text>
                  )}
                  {s.state === 'ended' && <Text dimColor>  ended</Text>}
                  {worktree && <Text dimColor wrap="truncate-end">  worktree {worktree}</Text>}
                </Box>
              )
            })}
          </Box>
        ))}
        <Box marginTop={1}>
          {types.slice(0, 9).map((t, i) => (
            <Button key={`type-${t}`} plain hotkey={String(i + 1)} dimColor={hidden.includes(t)} onPress={() => toggle(t)}>
              {t}{hidden.includes(t) ? ' (hidden)' : ''}{'  '}
            </Button>
          ))}
        </Box>
        <Text dimColor>
          {e.props.isFocused ? 'Click ☆ to star a session, a title to jump to it (tmux only). "today" marks sessions active today. Number keys hide a type. Esc returns.' : 'Press ctrl+x tab to use the number keys.'}
        </Text>
      </Box>
    )
  })
}
