export type AemStatusParts = {
  client: string
  project: string | null
  gate: string | null
  scene: string | null
  since: string | null
  paused: boolean
  waiting: string | null
  stale: number
}

export type AemView = {
  active: boolean
  parts: AemStatusParts | null
  contextText: string
  error: string | null
}

// The ledger feature's memory across hot reloads: which session and project its
// session_start went to, the last activity, an open idle span and the running turn.
export type AemLedger = {
  recordedFor: string | null
  lastActivity: number
  idleSince: number | null
  turnId: string | null
  idleMinutes: number
}

declare module 'claude-code' {
  interface PluginState {
    'aavkar-educational-motion-studio': { view: AemView; ledger: AemLedger }
  }
}
