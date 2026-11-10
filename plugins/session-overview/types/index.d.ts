export type Session = {
  pid: number
  sessionId: string
  cwd: string
  type: string
  state: 'running' | 'waiting' | 'idle' | 'ended'
  waitingFor: string | null
  goal: string
  pane: string | null
  updatedAt: number
}

declare module 'claude-code' {
  interface PluginState {
    'session-overview': { sessions: Session[]; hiddenTypes: string[]; starred: string[] }
  }
}
