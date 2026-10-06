// A fake `aem` and engine floor for tests: answers $.process.run beneath the plugin,
// records every argv, and captures toasts and the status line.
import { mock } from 'claude-code/testing'
import type { On } from 'claude-code'

export type Reply = { code?: number; json?: unknown; text?: string }
export type Router = (args: readonly string[], stdin: string | undefined) => Reply

export type World = {
  calls: string[][]
  stdins: (string | undefined)[]
  toasts: string[]
  statuses: (string | undefined)[]
  clock: ReturnType<typeof mock.clock>
}

export const NOW = Date.parse('2026-10-06T10:05:00+05:30')

export function floor(on: On, route: Router, opts: { cannotStart?: boolean } = {}): World {
  const w: World = { calls: [], stdins: [], toasts: [], statuses: [], clock: mock.clock(on, { now: NOW }) }
  mock.env(on, { HOME: '/Users/test' })
  mock.store(on)
  on('process.run', ($, e) => {
    w.calls.push([...e.argv])
    w.stdins.push(e.init?.stdin)
    if (opts.cannotStart) throw new Error(`spawn ${e.argv[0]} ENOENT`)
    const args = e.argv.slice(1).filter(a => a !== '--json')
    const r = route(args, e.init?.stdin)
    const stdout = r.json !== undefined ? JSON.stringify(r.json) : (r.text ?? '')
    return { value: { exitCode: r.code ?? 0, stdout, stderr: '', isStdoutTruncated: false, isStderrTruncated: false } }
  })
  on('ui.toast', ($, e) => {
    w.toasts.push(e.text)
    return { value: undefined }
  })
  on('ui.status', ($, e) => {
    w.statuses.push(e.text)
    return { value: undefined }
  })
  on('command.register', ($, e) => ({ value: { command: e.name } }))
  on('session.start', ($, e) => ({ cwd: e.cwd }))
  return w
}

export const INACTIVE: Router = args => {
  if (args[0] === 'status') return { json: { ok: true, active: false, message: 'no active project' } }
  if (args[0] === 'context') return { json: { ok: true, active: false, text: 'AEM inactive text' } }
  return { code: 2, json: { ok: false, error: 'no active project' } }
}

export const PARTS = {
  client: 'MergeToMaster', project: 'P1 - Test', gate: 'G1', scene: null,
  since: '2026-10-06T10:00:00+05:30', paused: false, waiting: null, stale: 0,
}

export function active(over: Partial<Record<string, Reply>> = {}): Router {
  return (args, stdin) => {
    const hit = over[args[0] ?? '']
    if (hit) return hit
    if (args[0] === 'status') return { json: { ok: true, active: true, statusline_parts: PARTS } }
    if (args[0] === 'context') return { json: { ok: true, active: true, text: 'CONTEXT FOR JOEL P1' } }
    if (args[0] === 'drift') return { json: { ok: true, findings: [] } }
    return { json: { ok: true, args, stdin } }
  }
}

export const COMPOSER = { kind: 'composer' } as const
export const PRESENTATION = { isFullscreen: false, columns: 120 }
export const START = { cwd: '/tmp/project', surface: 'terminal', isInteractive: true } as const
