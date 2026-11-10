import { expect, test } from 'claude-code/testing'

import { GOAL_TTL_MS, activeToday, clean, toTitle, groupSessions, makeGoalLookup, projectOf, stateOf, tmuxPane, transcriptPath, validEntry } from './register'

test('stateOf maps the four states', () => {
  expect(stateOf({ status: 'busy' }, true)).toBe('running')
  expect(stateOf({ status: 'waiting' }, true)).toBe('waiting')
  expect(stateOf({ status: 'idle' }, true)).toBe('idle')
  expect(stateOf({ status: 'busy' }, false)).toBe('ended')
})

test('projectOf merges worktrees and shortens home', () => {
  expect(projectOf('/home/a/ws/x/.claude/worktrees/w1', '/home/a')).toEqual({ path: '~/ws/x', worktree: 'w1' })
  expect(projectOf('/home/a', '/home/a')).toEqual({ path: '~', worktree: undefined })
  expect(projectOf('/opt/y', '/home/a').path).toBe('/opt/y')
})

test('transcriptPath encodes every non-alphanumeric as dash', () => {
  expect(transcriptPath('/H', '/home/a/ws/x/.claude/worktrees/w', 'id')).toBe(
    '/H/.claude/projects/-home-a-ws-x--claude-worktrees-w/id.jsonl',
  )
})

test('groupSessions hides a type and groups by project', () => {
  const s = (type: string, cwd: string) => ({ pid: 1, sessionId: 'i', cwd, type, state: 'idle', waitingFor: null, goal: '', updatedAt: 0 }) as const
  const g = groupSessions([s('cli', '/p'), s('sdk-cli', '/p'), s('cli', '/p/.claude/worktrees/w')], ['sdk-cli'], '/H')
  expect(g.length).toBe(1)
  expect(g[0]?.rows.length).toBe(2)
})

test('groupSessions orders projects by latest session update', () => {
  const s = (cwd: string, updatedAt: number, state = 'idle') => ({ pid: 1, sessionId: 'i', cwd, type: 'cli', state, waitingFor: null, goal: '', updatedAt }) as const
  const g = groupSessions([s('/old', 1, 'waiting'), s('/new', 9), s('/mid', 5)], [], '/H')
  expect(g.map(x => x.path)).toEqual(['/new', '/mid', '/old'])
})

test('groupSessions ties on equal updatedAt by path and ignores hidden types', () => {
  const s = (cwd: string, updatedAt: number, type = 'cli') => ({ pid: 1, sessionId: 'i', cwd, type, state: 'idle', waitingFor: null, goal: '', updatedAt }) as const
  const g = groupSessions([s('/b', 5), s('/a', 5), s('/c', 1), s('/c', 99, 'sdk-cli')], ['sdk-cli'], '/H')
  expect(g.map(x => x.path)).toEqual(['/a', '/b', '/c'])
})

test('clean strips escapes; validEntry rejects traversal and bad pids', () => {
  expect(clean('a\u001b]0;x\u0007b')).toBe('a ]0;x b')
  const ok = { pid: 1, sessionId: 'abc-1', cwd: '/p', status: 'idle' }
  expect(validEntry(ok)).toBe(true)
  expect(validEntry({ ...ok, sessionId: '../../x' })).toBe(false)
  expect(validEntry({ ...ok, pid: '1 -A' })).toBe(false)
  expect(validEntry(null)).toBe(false)
})

const jsonl = (...o: object[]) => o.map(x => JSON.stringify(x)).join('\n')

const fake = (files: Record<string, string>, finds: Record<string, string> = {}) => {
  let t = 0
  const calls: string[][] = []
  const g = makeGoalLookup({
    home: '/H',
    now: () => t,
    exists: async p => p in files,
    run: async argv => {
      calls.push(argv)
      if (argv[0] === 'find') return { stdout: finds[argv[argv.length - 1]!] ?? '' }
      const text = files[argv[argv.length - 1]!] ?? ''
      const pat = argv[argv.indexOf('-e') + 1]!.replace(/^"|"$/g, '').replace(/\\"/g, '"')
      return { stdout: text.split('\n').filter(l => l.includes(pat)).join('\n') }
    },
  })
  return { g, calls, tick: (ms: number) => { t += ms } }
}
const entry = { pid: 1, sessionId: 'abc', cwd: '/p', status: 'idle' }
const path = transcriptPath('/H', '/p', 'abc')

test('goalOf skips tag-wrapped prompts and uses the next plain one', async () => {
  const { g } = fake({
    [path]: jsonl(
      { type: 'user', message: { content: '<local-command-caveat>x</local-command-caveat>' } },
      { type: 'user', message: { content: 'fix the bug\nmore' } },
    ),
  })
  expect(await g.goalOf(entry)).toBe('fix the bug')
})

test('goalOf re-greps at most every 30s', async () => {
  const { g, calls, tick } = fake({ [path]: jsonl({ type: 'ai-title', aiTitle: 'T' }) })
  expect(await g.goalOf(entry)).toBe('T')
  const n = calls.length
  tick(GOAL_TTL_MS - 1)
  await g.goalOf(entry)
  expect(calls.length).toBe(n)
  tick(1)
  await g.goalOf(entry)
  expect(calls.length).toBeGreaterThan(n)
})

test('prune evicts sessions that left the registry', async () => {
  const { g } = fake({ [path]: jsonl({ type: 'ai-title', aiTitle: 'T' }) })
  await g.goalOf(entry)
  expect(g.size()).toBe(1)
  g.prune(['other'])
  expect(g.size()).toBe(0)
})

test('goalOf finds a transcript outside the derived dir once, and caches a miss', async () => {
  const alt = '/H/.claude/projects/-odd/abc.jsonl'
  const hit = fake({ [alt]: jsonl({ type: 'ai-title', aiTitle: 'Alt' }) }, { 'abc.jsonl': alt })
  expect(await hit.g.goalOf(entry)).toBe('Alt')
  const miss = fake({})
  expect(await miss.g.goalOf({ ...entry, name: 'n' })).toBe('n')
  miss.tick(GOAL_TTL_MS)
  await miss.g.goalOf(entry)
  expect(miss.calls.filter(c => c[0] === 'find').length).toBe(1)
  miss.g.prune([])
  await miss.g.goalOf(entry)
  expect(miss.calls.filter(c => c[0] === 'find').length).toBe(2)
})

test('goalOf prefers a title set with /rename over the AI title', async () => {
  const { g } = fake({ [path]: jsonl({ type: 'ai-title', aiTitle: 'AI' }) })
  expect(await g.goalOf({ ...entry, name: 'Mine', nameSource: 'user' })).toBe('Mine')
  expect(await g.goalOf({ ...entry, name: 'derived-1', nameSource: 'derived' })).toBe('AI')
})

test('toTitle keeps one clean line from the model reply', () => {
  expect(toTitle('"Fix login redirect."\nextra')).toBe('Fix login redirect')
  expect(toTitle('  Add pricing page  ')).toBe('Add pricing page')
  expect(toTitle('x'.repeat(100)).length).toBe(60)
})

test('tmuxPane extracts the pane id and rejects anything else', () => {
  expect(tmuxPane('similarshed:@28.%28')).toBe('%28')
  for (const v of [':.', null, 'x; rm -rf', 'a:@1.%2 extra']) expect(tmuxPane(v)).toBe(null)
})

test('UserPromptSubmit titles an untitled user prompt and skips the rest', async ($, on) => {
  let calls = 0
  on('classic.UserPromptSubmit', async () => ({}) as never)
  on('model.complete', async () => {
    calls++
    return { value: { isAnswered: true, text: '"Fix login."', usage: { input_tokens: 0, output_tokens: 0 } } } as never
  })
  const r = await $.classic.UserPromptSubmit({ prompt: 'fix the login redirect' })
  expect(r.sessionTitle).toBe('Fix login')
  expect(calls).toBe(1)
  await $.classic.UserPromptSubmit({ prompt: 'x', session_title: 'Named' })
  await $.classic.UserPromptSubmit({ prompt: '/sessions' })
  await $.classic.UserPromptSubmit({ prompt: '   ' })
  expect(calls).toBe(1)
})

test('activeToday compares the local calendar day and ignores unknown times', () => {
  const now = new Date(2026, 10, 6, 12).getTime()
  expect(activeToday(new Date(2026, 10, 6, 0, 1).getTime(), now)).toBe(true)
  expect(activeToday(new Date(2026, 10, 5, 23, 59).getTime(), now)).toBe(false)
  expect(activeToday(0, now)).toBe(false)
})

test('groupSessions puts starred sessions first inside a project', () => {
  const s = (id: string, state: 'idle' | 'waiting') => ({ pid: 1, sessionId: id, cwd: '/p', type: 'cli', state, waitingFor: null, goal: '', updatedAt: 1 }) as const
  const rows = groupSessions([s('a', 'waiting'), s('b', 'idle')], [], '/h', ['b'])[0]!.rows
  expect(rows.map(r => r.sessionId)).toEqual(['b', 'a'])
})

test('starred sessions: several stars keep state order among themselves, then the rest; unknown ids are ignored', () => {
  const s = (id: string, state: 'running' | 'waiting' | 'idle' | 'ended') => ({ pid: 1, sessionId: id, cwd: '/p', type: 'cli', state, waitingFor: null, goal: '', updatedAt: 1 }) as const
  const list = [s('a', 'idle'), s('b', 'waiting'), s('c', 'ended'), s('d', 'running'), s('e', 'idle')]
  const ids = (stars: string[]) => groupSessions(list, [], '/h', stars)[0]!.rows.map(r => r.sessionId)
  const base = ids([])
  const starred = ids(['c', 'a', 'gone'])
  expect(starred.slice(0, 2).sort()).toEqual(['a', 'c'])
  expect(starred.slice(0, 2)).toEqual(base.filter(x => x === 'a' || x === 'c'))
  expect(starred.slice(2)).toEqual(base.filter(x => x !== 'a' && x !== 'c'))
  expect(ids(['gone'])).toEqual(base)
  expect(ids(['a', 'b', 'c', 'd', 'e'])).toEqual(base)
})

test('starring never moves a session across projects', () => {
  const s = (id: string, cwd: string, updatedAt: number) => ({ pid: 1, sessionId: id, cwd, type: 'cli', state: 'idle', waitingFor: null, goal: '', updatedAt }) as const
  const g = groupSessions([s('a', '/x', 9), s('b', '/y', 1)], [], '/h', ['b'])
  expect(g.map(x => x.path)).toEqual(['/x', '/y'])
})

test('activeToday edges: future time, exact midnight, negative, now itself', () => {
  const now = new Date(2026, 10, 6, 12).getTime()
  expect(activeToday(new Date(2026, 10, 6, 0, 0, 0, 0).getTime(), now)).toBe(true)
  expect(activeToday(new Date(2026, 10, 6, 23, 59, 59).getTime(), now)).toBe(true)
  expect(activeToday(new Date(2026, 10, 7, 0, 0, 0).getTime(), now)).toBe(false)
  expect(activeToday(now, now)).toBe(true)
  expect(activeToday(-5, now)).toBe(false)
  expect(activeToday(NaN, now)).toBe(false)
})
