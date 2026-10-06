// Calls the aem CLI. Every decision AEM makes is the CLI's; this file only runs it.
import type { PluginOptions, ProcessRunInit, ProcessRunResult, PromptOrigin } from 'claude-code'

import type { AemLedger, AemStatusParts, AemView } from '../types'

export const PLUGIN = 'aavkar-educational-motion-studio'

export type Json = { [key: string]: unknown }

export type AemResult = {
  code: number
  data: Json
  text: string
}

export type RunInit = { stdin?: string; timeoutMs?: number; json?: boolean }

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
      const ran = await run(argv, { stdin: init.stdin, timeoutMs: init.timeoutMs ?? 120_000 })
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

export const EMPTY_VIEW: AemView = { active: false, parts: null, contextText: '', error: null }

export function viewFrom(status: AemResult, context: AemResult): AemView {
  if (status.code === 127 || status.data.ok === false) {
    return { active: false, parts: null, contextText: '', error: errorOf(status) }
  }
  const active = status.data.active === true
  return {
    active,
    parts: active ? (status.data.statusline_parts as AemStatusParts) : null,
    contextText: typeof context.data.text === 'string' ? context.data.text : '',
    error: null,
  }
}

function elapsed(since: string, nowMs: number): string {
  const s = Math.max(0, Math.floor((nowMs - Date.parse(since)) / 1000))
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  return `${h}:${String(m).padStart(2, '0')}`
}

// AEM · client · project · gate · stage time
export function statusLine(v: AemView, nowMs: number): string {
  if (v.error) return `AEM · ${v.error.slice(0, 60)}`
  if (!v.active || !v.parts) return 'AEM · no active project · /aem use <client>/<project>'
  const p = v.parts
  const bits = ['AEM', p.client, p.project ?? '-']
  if (p.gate && p.since) {
    let t = elapsed(p.since, nowMs)
    if (p.paused) t += ' paused'
    if (p.waiting) t += ` ${p.waiting.replace(/_/g, ' ')}`
    bits.push(p.scene ? `${p.gate} ${p.scene}` : p.gate, t)
  } else {
    bits.push('no gate')
  }
  if (p.stale > 0) bits.push(`${p.stale} stale`)
  return bits.join(' · ')
}


// --- io: what features may do, as closures over the hook's `$` built in register.ts ---
// The engine follows `$` only within the file that holds it, so features never see `$`.

export type CommandSpecLite = { name: string; description: string; argumentHint?: string }

export type Io = {
  run: ProcessRun
  home: () => Promise<string | undefined>
  toast: (text: string, timeoutMs?: number) => void
  status: (text: string | undefined) => void
  now: () => Promise<number>
  sessionId: () => Promise<string>
  registerCommand: (spec: CommandSpecLite) => Promise<void>
  getView: () => Promise<AemView>
  setView: (v: AemView) => Promise<void>
  getLedger: () => Promise<AemLedger>
  patchLedger: (fn: (l: AemLedger) => AemLedger) => Promise<void>
}

export async function cli(io: Io, options: PluginOptions, args: readonly string[], init?: RunInit): Promise<AemResult> {
  return runAem(io.run, await io.home(), options, args, init)
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
