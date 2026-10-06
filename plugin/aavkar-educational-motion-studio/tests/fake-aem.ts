// A fake `aem` and engine floor for tests: answers $.process.run beneath the plugin,
// records every argv, and captures toasts, the status line, transcript lines and dialogs.
import { mock } from 'claude-code/testing'
import type { On } from 'claude-code'

export type Reply = { code?: number; json?: unknown; text?: string }
export type Router = (args: readonly string[], stdin: string | undefined) => Reply

export type World = {
  calls: string[][]
  stdins: (string | undefined)[]
  envs: (Record<string, string> | undefined)[]
  files: { path: string; text: string }[]
  toasts: string[]
  statuses: (string | undefined)[]
  clock: ReturnType<typeof mock.clock>
  toolsRun: string[]
  commands: string[]
  panes: string[]
  logs: string[]
  // Every question put to the operator in the engine's dialog, with its options.
  asked: { question: string; options: string[] }[]
}

export const NOW = Date.parse('2026-10-06T10:05:00+05:30')

export type FloorOptions = {
  cannotStart?: boolean
  toolMs?: Record<string, number>
  selection?: string
  env?: Record<string, string>
  failWrite?: boolean
  // Where the session draws; [] is a plain -p run, where no dialog can be shown. Default: the terminal.
  surfaces?: readonly ('terminal' | 'desktop' | 'mobile' | 'vscode')[]
  // The operator's answer to a dialog: a label, or null to dismiss it.
  answer?: string | null
}

export function floor(on: On, route: Router, opts: FloorOptions = {}): World {
  const w: World = { calls: [], stdins: [], envs: [], files: [], toasts: [], statuses: [], clock: mock.clock(on, { now: NOW }), toolsRun: [], commands: [], panes: [], logs: [], asked: [] }
  mock.env(on, { HOME: '/Users/test', ...opts.env })
  mock.store(on)
  on('process.run', ($, e) => {
    w.calls.push([...e.argv])
    w.stdins.push(e.init?.stdin)
    w.envs.push(e.init?.env)
    if (opts.cannotStart) throw new Error(`spawn ${e.argv[0]} ENOENT`)
    const args = e.argv.slice(1).filter(a => a !== '--json')
    const r = route(args, e.init?.stdin)
    const stdout = r.json !== undefined ? JSON.stringify(r.json) : (r.text ?? '')
    return { value: { exitCode: r.code ?? 0, stdout, stderr: '', isStdoutTruncated: false, isStderrTruncated: false } }
  })
  on('fs.write', ($, e) => {
    if (opts.failWrite) throw new Error('EACCES')
    w.files.push({ path: e.path, text: e.text })
    return { value: undefined }
  })
  on('ui.toast', ($, e) => {
    w.toasts.push(e.text)
    return { value: undefined }
  })
  on('ui.status', ($, e) => {
    w.statuses.push(e.text)
    return { value: undefined }
  })
  on('ui.log', ($, e) => {
    w.logs.push(e.text)
    return { value: undefined }
  })
  on('session.surfaces', () => ({ value: opts.surfaces ?? ['terminal'] }))
  on('command.register', ($, e) => {
    w.commands.push(e.name)
    return { value: { command: e.name } }
  })
  on('ui.open', ($, e) => {
    w.panes.push(e.id)
    return { value: { isPlaced: true } }
  })
  on('session.start', ($, e) => ({ cwd: e.cwd }))
  on('session.id', () => ({ value: 'sess-1' }))
  on('session.end', ($, e) => ({ sessionId: e.sessionId }))
  on('prompt.submit', ($, e) => ({ text: e.text }))
  on('turn.start', ($, e) => ({ turnId: e.turnId }))
  on('turn.complete', ($, e) => ({ text: e.answer }))
  on('ui.selection', () => ({ value: opts.selection === undefined ? undefined : { text: opts.selection } }))
  on('session.cwd', () => ({ value: '/projects/P1' }))
  on('tool.call', async ($, e) => {
    if (e.tool === 'AskUserQuestion') {
      // The engine's dialog: the operator picks a label, or dismisses it.
      const q = e.questions[0]
      w.asked.push({ question: q?.question ?? '', options: (q?.options ?? []).map(o => o.label) })
      if (opts.answer === null || q === undefined) return { deny: 'The user dismissed the dialog' }
      return { result: { questions: e.questions, answers: { [q.question]: opts.answer ?? 'Deliver' } } }
    }
    w.toolsRun.push(String(e.tool))
    const ms = opts.toolMs?.[String(e.tool)] ?? 0
    if (ms > 0) await w.clock.advance(ms)
    return { result: 'done' }
  })
  return w
}

export const INACTIVE: Router = args => {
  if (args[0] === 'status') return { json: { ok: true, active: false, message: 'no project resolved', resolution: { source: 'none', detail: '' } } }
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
    if (args[0] === 'status') return { json: { ok: true, active: true, client: 'joel', project: 'P1', statusline_parts: PARTS, resolution: { source: 'folder', detail: 'the working folder is inside registered project joel/P1' } } }
    if (args[0] === 'context') return { json: { ok: true, active: true, text: 'CONTEXT FOR JOEL P1' } }
    if (args[0] === 'drift') return { json: { ok: true, findings: [] } }
    return { json: { ok: true, args, stdin } }
  }
}

export const COMPOSER = { kind: 'composer' } as const
export const PRESENTATION = { isFullscreen: false, columns: 120 }
export const START = { cwd: '/tmp/project', surface: 'terminal', isInteractive: true } as const

// The `stage auto` calls made, as [event, ...extra] with the session flag dropped.
export function autos(w: World): string[][] {
  return w.calls
    .filter(c => c[1] === 'stage' && c[2] === 'auto')
    .map(c => c.slice(3).filter((a, i, all) => a !== '--json' && a !== '--session' && all[i - 1] !== '--session'))
}
