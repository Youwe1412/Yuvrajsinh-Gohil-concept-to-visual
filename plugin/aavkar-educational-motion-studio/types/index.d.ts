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

declare module 'claude-code' {
  interface PluginState {
    'aavkar-educational-motion-studio': { view: AemView }
  }
}
