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

// How aem resolved the project: env, session pin, folder, folder (design system), flag or none.
export type AemResolution = { source: string; detail: string }

export type AemView = {
  active: boolean
  parts: AemStatusParts | null
  contextText: string
  error: string | null
  resolution: AemResolution | null
  client: string | null
  project: string | null
}

// The session pin: <client>/<project> set by /aem use for this session only, handed to every aem call as
// AEM_PROJECT. Nothing global stores a project; the folder the session runs in is the default.
// The ledger feature's memory across hot reloads: which session and project its
// session_start went to, the last activity, an open idle span and the running turn.
export type AemLedger = {
  recordedFor: string | null
  lastActivity: number
  idleSince: number | null
  turnId: string | null
  idleMinutes: number
}

// The review inbox: what `aem inbox` lists, each item carrying the exact aem commands its
// buttons run, and the pane's own state (which item is asking for a reason, the last result).
export type AemInboxAction = { label: string; argv: string[]; needs_reason: boolean }

export type AemInboxItem = {
  id: string
  kind: string
  item: string
  gate: string | null
  title: string
  detail: string | null
  note?: string
  check?: string
  actions: AemInboxAction[]
}

export type AemInbox = {
  items: AemInboxItem[]
  summary: string
  reasonFor: { id: string; label: string } | null
  message: string | null
  busy: boolean
}

declare module 'claude-code' {
  interface PluginState {
    'aavkar-educational-motion-studio': { view: AemView; ledger: AemLedger; inbox: AemInbox; pin: string | null }
  }
}
