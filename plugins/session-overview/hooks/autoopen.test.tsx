import { expect, mock, test } from 'claude-code/testing'

// Answers the nouns openPane touches; records every ui.open.
const world = ($: any, on: any, store: Record<string, unknown> = {}, live = false) => {
  const opens: { focus?: boolean }[] = []
  // live: read the object on every get (mock.store snapshots it), so a test can change it mid-run.
  if (live) on('store.get', async (_$: any, e: any) => ({ value: store[e.key] }) as never)
  else mock.store(on, store)
  mock.env(on, { HOME: '/H' })
  mock.clock(on)
  on('session.start', async (_$: any, e: any) => ({ cwd: e.cwd }))
  on('command.register', async () => ({ value: {} }) as never)
  on('fs.list', async () => ({ value: [] }) as never)
  on('ui.open', async (_$: any, e: any) => { opens.push(e); return { value: { isPlaced: true } } as never })
  return opens
}

test('session.start opens the pane unfocused only when interactive and autoOpen is true', async ($, on) => {
  const opens = world($, on, { autoOpen: true })
  await $.session.start({ cwd: '/p', surface: 'terminal', isInteractive: false })
  expect(opens.length).toBe(0)
  await $.session.start({ cwd: '/p', surface: 'terminal', isInteractive: true })
  expect(opens.length).toBe(1)
  expect(opens[0]?.focus).toBeUndefined() // the host accepts focus: true or none
})

const closed = (name: string, store: Record<string, unknown>) =>
  test(name, async ($, on) => {
    const opens = world($, on, store)
    await $.session.start({ cwd: '/p', surface: 'terminal', isInteractive: true })
    expect(opens.length).toBe(0)
  })
closed('session.start leaves the pane closed when autoOpen is unset', {})
closed('session.start leaves the pane closed when autoOpen is false', { autoOpen: false })

test('/sessions auto on|off stores autoOpen; plain /sessions opens focused', async ($, on) => {
  const opens = world($, on)
  const start = () => $.session.start({ cwd: '/p', surface: 'terminal', isInteractive: true })
  await $.command.run({ command: 'sessions', args: 'auto on' })
  await start()
  expect(opens.length).toBe(1)
  expect(opens[0]?.focus).toBeUndefined() // the host accepts focus: true or none
  await $.command.run({ command: 'sessions', args: ' AUTO OFF ' })
  await start()
  expect(opens.length).toBe(1)
  await $.command.run({ command: 'sessions', args: '' })
  expect(opens.length).toBe(2)
  expect(opens[1]?.focus).toBe(true)
})

// In-memory state noun: the harness has no mock.state.
const memState = (on: any) => {
  const m = new Map<string, { value: unknown; version: number }>()
  const k = (e: any) => `${e.plugin}/${e.key}`
  on('state.get', async (_$: any, e: any) => ({ value: m.get(k(e)) ?? { value: undefined, version: 0 } }) as never)
  on('state.set', async (_$: any, e: any) => {
    const v = (m.get(k(e))?.version ?? 0) + 1
    m.set(k(e), { value: e.value, version: v })
    return { value: { isSet: true, version: v } } as never
  })
  return (key = 'starred') => m.get(`session-overview/${key}`)?.value
}

test('session.start restores persisted stars and ignores a malformed value', async ($, on) => {
  const starsNow = memState(on)
  world($, on, { starred: ['a', 'b'] })
  await $.session.start({ cwd: '/p', surface: 'terminal', isInteractive: false })
  expect(starsNow()).toEqual(['a', 'b'])
})

test('session.start leaves stars empty when the stored value is not an array', async ($, on) => {
  const starsNow = memState(on)
  world($, on, { starred: 'oops' })
  await $.session.start({ cwd: '/p', surface: 'terminal', isInteractive: false })
  expect(starsNow()).toBeUndefined() // nothing written: atom keeps its [] default
})

test('the pane refresh re-reads stars and hidden types saved by another session', async ($, on) => {
  const stateNow = memState(on)
  const store: Record<string, unknown> = { starred: ['a'], hiddenTypes: [] }
  world($, on, store, true)
  await $.session.start({ cwd: '/p', surface: 'terminal', isInteractive: false })
  expect(stateNow('starred')).toEqual(['a'])
  Object.assign(store, { starred: ['a', 'b'], hiddenTypes: ['bg'] })
  await $.command.run({ command: 'sessions', args: '' })
  expect(stateNow('starred')).toEqual(['a', 'b'])
  expect(stateNow('hiddenTypes')).toEqual(['bg'])
})
