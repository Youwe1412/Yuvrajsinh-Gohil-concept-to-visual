// Calls the aem CLI. Every decision AEM makes is the CLI's; this file only runs it.
import type { AskOptions, PluginOptions, ProcessRunInit, ProcessRunResult, PromptOrigin, RenderSurface } from 'claude-code'

import type { AemHeld, AemInbox, AemLedger, AemStatusParts, AemView } from '../types'
import { sha256Hex } from './sha256'

export const PLUGIN = 'aavkar-educational-motion-studio'
export const PLUGIN_VERSION = '1.1.0'

export type Json = { [key: string]: unknown }

export type AemResult = {
  code: number
  data: Json
  text: string
}

export type RunInit = { stdin?: string; timeoutMs?: number; json?: boolean; env?: Record<string, string> }

// The aem commands that write the record, the only ones the operator alone runs. The CLI refuses them unless the
// operator is shown to be running them (cli/aem/operator.py); this plugin is how a slash command (and the delivery
// confirmation's Deliver) shows it: a one-time nonce.
const OPERATOR_COMMANDS: ReadonlySet<string> = new Set(['stage', 'approve', 'reject', 'client-said', 'new-client', 'accept-edit', 'accept-video'])

export function isOperatorCommand(args: readonly string[]): boolean {
  const [cmd, action] = args
  if (cmd === undefined) return false
  return OPERATOR_COMMANDS.has(cmd) || (cmd === 'inbox' && (action === 'accept' || action === 'dismiss'))
}

export const NONCE_TTL_MS = 60_000

const hex = (bytes: Uint8Array): string => Array.from(bytes, b => b.toString(16).padStart(2, '0')).join('')

// A random one-time nonce. Only its SHA-256 is written, to <AEM_HOME>/nonces/<hash>, with an expiry; the nonce
// itself goes to the one aem call in AEM_OPERATOR_NONCE and is never written, logged or shown.
export async function makeNonce(io: Io): Promise<{ nonce: string } | { error: string }> {
  try {
    const nonce = hex(crypto.getRandomValues(new Uint8Array(32)))
    const file = `${await io.aemHome()}/nonces/${sha256Hex(Uint8Array.from(nonce, c => c.charCodeAt(0)))}`
    await io.writeFile(file, JSON.stringify({ expires_at: ((await io.now()) + NONCE_TTL_MS) / 1000 }))
    return { nonce }
  } catch (err) {
    return { error: String(err) }
  }
}

// The host's process runner, handed in by each feature as a closure over its own `$`
// (the engine follows `$` only within the file that holds it).
export type ProcessRun = (argv: readonly string[], init: ProcessRunInit) => Promise<ProcessRunResult>

function candidates(options: PluginOptions, home: string | undefined): string[] {
  const configured = typeof options.aemPath === 'string' && options.aemPath !== '' ? options.aemPath : 'aem'
  const list = [configured]
  if (configured === 'aem' && home) list.push(`${home}/.local/bin/aem`)
  return list
}

// Runs `aem <args> --json` (or plain text with json: false) and never throws.
export async function runAem(
  run: ProcessRun,
  home: string | undefined,
  options: PluginOptions,
  args: readonly string[],
  init: RunInit = {},
): Promise<AemResult> {
  const asJson = init.json !== false
  let failure = ''
  for (const bin of candidates(options, home)) {
    try {
      const argv = asJson ? [bin, ...args, '--json'] : [bin, ...args]
      const ran = await run(argv, { stdin: init.stdin, timeoutMs: init.timeoutMs ?? 120_000, env: init.env })
      const text = (ran.stdout + (ran.stderr ? `\n${ran.stderr}` : '')).trim()
      if (!asJson) return { code: ran.exitCode, data: {}, text }
      let data: Json
      try {
        data = JSON.parse(ran.stdout) as Json
      } catch {
        data = { ok: false, error: text || `aem exited ${ran.exitCode}` }
      }
      return { code: ran.exitCode, data, text }
    } catch (err) {
      failure = String(err)
    }
  }
  const error = `aem could not start (${failure}). Install it (cli/install.sh) or set this plugin's aemPath option.`
  return { code: 127, data: { ok: false, error }, text: error }
}

export function errorOf(r: AemResult): string {
  const e = r.data.error
  const hint = r.data.hint
  return `${typeof e === 'string' ? e : r.text}${typeof hint === 'string' ? ` (${hint})` : ''}`
}

// Who typed a command: the person at the prompt, the Remote Control bridge, or
// the SDK host (the desktop app, `claude -p`). A model or a plugin never is.
export const OPERATOR_ORIGINS: readonly PromptOrigin['kind'][] = ['composer', 'bridge', 'sdk']

export function isOperator(origin: PromptOrigin): boolean {
  return OPERATOR_ORIGINS.includes(origin.kind)
}

// Splits command arguments like a shell would for quotes, without expanding anything.
export function splitArgs(input: string): string[] {
  const out: string[] = []
  let cur = ''
  let quote: '"' | "'" | null = null
  let started = false
  for (const ch of input) {
    if (quote) {
      if (ch === quote) quote = null
      else cur += ch
    } else if (ch === '"' || ch === "'") {
      quote = ch
      started = true
    } else if (/\s/.test(ch)) {
      if (started || cur) out.push(cur)
      cur = ''
      started = false
    } else {
      cur += ch
    }
  }
  if (started || cur) out.push(cur)
  return out
}

// --- the view every feature shows: pure, built from `aem status` and `aem context` ---

export const EMPTY_VIEW: AemView = { active: false, parts: null, contextText: '', error: null, resolution: null, client: null, project: null }

export function viewFrom(status: AemResult, context: AemResult): AemView {
  if (status.code === 127 || status.data.ok === false) {
    return { ...EMPTY_VIEW, error: errorOf(status) }
  }
  const active = status.data.active === true
  const res = status.data.resolution as { source?: unknown; detail?: unknown } | undefined
  return {
    active,
    parts: active ? (status.data.statusline_parts as AemStatusParts) : null,
    contextText: typeof context.data.text === 'string' ? context.data.text : '',
    error: null,
    resolution: res && typeof res.source === 'string' ? { source: res.source, detail: typeof res.detail === 'string' ? res.detail : '' } : null,
    client: typeof status.data.client === 'string' ? status.data.client : null,
    project: typeof status.data.project === 'string' ? status.data.project : null,
  }
}

// The toast every session shows at start. No toast at all means the plugin is not loaded.
export function startToast(v: AemView): string {
  const head = `AEM ${PLUGIN_VERSION}`
  if (v.error) return `${head} · ${v.error.slice(0, 120)}`
  if (v.active && v.client && v.project) return `${head} · ${v.client}/${v.project} · resolved from ${v.resolution?.source ?? 'unknown'}`
  if (v.client) return `${head} · ${v.client} (design system, no project) · resolved from ${v.resolution?.source ?? 'folder'}`
  return `${head} · no project (folder not registered)`
}

function elapsed(since: string, nowMs: number): string {
  const s = Math.max(0, Math.floor((nowMs - Date.parse(since)) / 1000))
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  return `${h}:${String(m).padStart(2, '0')}`
}

// AEM · client · project · gate (inferred) · stage time · stale · ledger edits
export function statusLine(v: AemView, nowMs: number): string {
  if (v.error) return `AEM · ${v.error.slice(0, 60)}`
  if (!v.active || !v.parts) return 'AEM · no project here · start in its folder or /aem use <client>/<project>'
  const p = v.parts
  const bits = ['AEM', p.client, p.project ?? '-']
  if (p.gate && p.since) {
    let t = elapsed(p.since, nowMs)
    if (p.paused) t += ' paused'
    if (p.waiting) t += ` ${p.waiting.replace(/_/g, ' ')}`
    bits.push((p.scene ? `${p.gate} ${p.scene}` : p.gate) + (p.inferred ? ' (inferred)' : ''), t)
  } else {
    bits.push('no gate')
  }
  if (p.stale > 0) bits.push(`${p.stale} stale`)
  if ((p.integrity ?? 0) > 0) bits.push(`${p.integrity} ledger edit${p.integrity === 1 ? '' : 's'} to review`)
  if (p.moments) bits.push(`${p.moments.moments} moments`, `${p.moments.approved} approved`, `${p.moments.ruled} ruled`)
  return bits.join(' · ')
}


// --- io: what features may do, as closures over the hook's `$` built in register.ts ---
// The engine follows `$` only within the file that holds it, so features never see `$`.

export type CommandSpecLite = { name: string; description: string; argumentHint?: string }

export type Io = {
  run: ProcessRun
  home: () => Promise<string | undefined>
  aemHome: () => Promise<string>
  writeFile: (path: string, text: string) => Promise<void>
  toast: (text: string, timeoutMs?: number) => void
  status: (text: string | undefined) => void
  now: () => Promise<number>
  sessionId: () => Promise<string>
  cwd: () => Promise<string>
  selection: () => Promise<string | undefined>
  registerCommand: (spec: CommandSpecLite) => Promise<void>
  getView: () => Promise<AemView>
  setView: (v: AemView) => Promise<void>
  getPin: () => Promise<string | null>
  setPin: (pin: string | null) => Promise<void>
  getLedger: () => Promise<AemLedger>
  patchLedger: (fn: (l: AemLedger) => AemLedger) => Promise<void>
  getInbox: () => Promise<AemInbox>
  patchInbox: (fn: (b: AemInbox) => AemInbox) => Promise<void>
  openPane: (id: string, title: string) => Promise<void>
  // The engine's own dialog (AskUserQuestion); rejects when dismissed or where no one can be asked.
  ask: (question: string, options: AskOptions) => Promise<string>
  // Where the session draws: empty in a plain -p run, where no dialog can be shown.
  surfaces: () => Promise<readonly RenderSurface[]>
  // A dim line in the transcript, for the operator only (not sent to the model).
  log: (text: string) => void
  getHeld: () => Promise<AemHeld>
  patchHeld: (fn: (h: AemHeld) => AemHeld) => Promise<void>
}

// The session pin reaches every aem call as AEM_PROJECT (with AEM_PROJECT_SOURCE saying it is a pin), so the
// CLI resolves the same project the operator pinned; with no pin the CLI uses the session's working folder.
export async function cli(io: Io, options: PluginOptions, args: readonly string[], init?: RunInit): Promise<AemResult> {
  const pin = await io.getPin()
  let env: Record<string, string> | undefined = pin ? { AEM_PROJECT: pin, AEM_PROJECT_SOURCE: 'session-pin', ...init?.env } : init?.env
  // Every call here comes from a slash command the operator typed or from the plugin's own events, never from
  // the model, so an operator command gets its one-time nonce. If it cannot be made the CLI refuses and says why.
  if (isOperatorCommand(args)) {
    const n = await makeNonce(io)
    if ('nonce' in n) env = { ...env, AEM_OPERATOR_NONCE: n.nonce }
  }
  return runAem(io.run, await io.home(), options, args, { ...init, env })
}

// Reads status and context from the CLI into state, then redraws the status line.
export async function refresh(io: Io, options: PluginOptions): Promise<{ view: AemView; status: AemResult }> {
  const [status, ctx] = await Promise.all([cli(io, options, ['status']), cli(io, options, ['context'])])
  const v = viewFrom(status, ctx)
  await io.setView(v)
  const idle = status.data.idle_minutes
  if (typeof idle === 'number') await io.patchLedger(l => ({ ...l, idleMinutes: idle }))
  io.status(statusLine(v, await io.now()))
  return { view: v, status }
}

export const EMPTY_LEDGER: AemLedger = { recordedFor: null, lastActivity: 0, idleSince: null, turnId: null, idleMinutes: 10 }

export function refusedText(command: string, origin: PromptOrigin): string {
  return `AEM: /${command} can only be typed by the operator (this run came from ${origin.kind}).`
}

// Reads leading words and flags off a command's arguments and keeps the rest exactly as typed
// (a reason or the client's words must not be re-spaced). Quotes group a word.
export type Leading = { words: string[]; flags: Record<string, string | true>; rest: string }

export function leading(input: string, opts: { words: number; valueFlags?: readonly string[]; boolFlags?: readonly string[] }): Leading {
  const out: Leading = { words: [], flags: {}, rest: '' }
  let i = 0
  const readWord = (): string | null => {
    while (i < input.length && /\s/.test(input[i] ?? '')) i++
    if (i >= input.length) return null
    const q = input[i]
    if (q === '"' || q === "'") {
      const end = input.indexOf(q, i + 1)
      const word = end === -1 ? input.slice(i + 1) : input.slice(i + 1, end)
      i = end === -1 ? input.length : end + 1
      return word
    }
    const start = i
    while (i < input.length && !/\s/.test(input[i] ?? '')) i++
    return input.slice(start, i)
  }
  for (;;) {
    const save = i
    const w = readWord()
    if (w === null) break
    if (w.startsWith('--') && opts.valueFlags?.includes(w.slice(2))) {
      out.flags[w.slice(2)] = readWord() ?? ''
    } else if (w.startsWith('--') && opts.boolFlags?.includes(w.slice(2))) {
      out.flags[w.slice(2)] = true
    } else if (out.words.length < opts.words) {
      out.words.push(w)
    } else {
      i = save
      break
    }
  }
  out.rest = input.slice(i).replace(/^[ \t]+/, '').replace(/^\n/, '')
  return out
}
