// Feature "ledger": time events with clock timestamps, all written by `aem stage`, so
// events.jsonl keeps one format. Commands /stage, /pause, /resume, /wait, /report.
import type { CommandRunInput, CommandRunResult, PluginOptions, PromptOrigin, SessionEndInput, TurnCompleteInput } from 'claude-code'

import { cli, isOperator, refresh, refusedText, splitArgs } from './aem'
import type { CommandSpecLite, Io } from './aem'

export const LONG_TOOL_MS = 30_000

export const LEDGER_COMMANDS: readonly CommandSpecLite[] = [
  { name: 'stage', description: 'AEM: start a gate (finishing the one open for the same scene), or end it', argumentHint: '<gate> [scene] | end [gate [scene]]' },
  { name: 'pause', description: 'AEM: pause the current stage' },
  { name: 'resume', description: 'AEM: resume the current stage (also ends a wait)' },
  { name: 'wait', description: 'AEM: the current stage waits on someone', argumentHint: '<who>' },
  { name: 'report', description: 'AEM: write reports/time.md and show it' },
]

// One automatic event through `aem stage auto`; none while no project is active. Failures are silent.
async function auto(io: Io, options: PluginOptions, event: string, extra: readonly string[] = []): Promise<boolean> {
  if (!(await io.getView()).active) return false
  const r = await cli(io, options, ['stage', 'auto', event, '--session', await io.sessionId(), ...extra])
  return r.code === 0
}

// session_start once per session and project: a hot reload or a repeat does not start a
// second session in the ledger; a new session id (after /clear) or project gets its own.
async function ensureSession(io: Io, options: PluginOptions): Promise<void> {
  const v = await io.getView()
  if (!v.active || !v.parts) return
  const key = `${await io.sessionId()}|${v.parts.client}|${v.parts.project}`
  if ((await io.getLedger()).recordedFor === key) return
  if (await auto(io, options, 'session_start')) await io.patchLedger(l => ({ ...l, recordedFor: key }))
}

// Input or agent activity: closes an open idle span, then notes the time.
async function touch(io: Io, options: PluginOptions): Promise<void> {
  await ensureSession(io, options)
  const now = await io.now()
  if ((await io.getLedger()).idleSince !== null) await auto(io, options, 'idle_end')
  await io.patchLedger(l => ({ ...l, lastActivity: now, idleSince: null }))
}

export async function ledgerStart(io: Io, options: PluginOptions): Promise<void> {
  await touch(io, options)
}

// Every 30 s: idle starts once idle_minutes pass with no input and no running turn.
// It is recorded when noticed, with the last activity's time as inactive_since.
export async function ledgerTick(io: Io, options: PluginOptions): Promise<void> {
  const l = await io.getLedger()
  const v = await io.getView()
  if (!v.active || l.turnId !== null || l.idleSince !== null || l.lastActivity === 0) return
  if ((await io.now()) - l.lastActivity < l.idleMinutes * 60_000) return
  if (await auto(io, options, 'idle_start', ['--since', new Date(l.lastActivity).toISOString()])) {
    await io.patchLedger(s => ({ ...s, idleSince: l.lastActivity }))
  }
}

export async function ledgerEnd(io: Io, options: PluginOptions, e: SessionEndInput): Promise<void> {
  if ((await io.getLedger()).recordedFor?.startsWith(`${e.sessionId}|`)) {
    await auto(io, options, 'session_end', ['--note', e.reason])
    await io.patchLedger(l => ({ ...l, recordedFor: null, idleSince: null, turnId: null }))
  }
}

export async function ledgerPrompt(io: Io, options: PluginOptions, origin: PromptOrigin): Promise<void> {
  if (!isOperator(origin)) return
  await touch(io, options)
  await auto(io, options, 'prompt', ['--origin', origin.kind])
}

export async function ledgerTurnStart(io: Io, options: PluginOptions, turnId: string): Promise<void> {
  await touch(io, options)
  await auto(io, options, 'turn_start', ['--turn', turnId])
  await io.patchLedger(l => ({ ...l, turnId }))
}

export async function ledgerTurnComplete(io: Io, options: PluginOptions, e: TurnCompleteInput): Promise<void> {
  if (e.agentId !== undefined) return // a subagent's turn: the main turn is still running
  await auto(io, options, 'turn_end', ['--turn', e.turnId, ...(e.isAborted ? ['--note', 'aborted'] : [])])
  await io.patchLedger(l => ({ ...l, turnId: null }))
  await touch(io, options)
}

export async function ledgerToolDone(io: Io, options: PluginOptions, tool: string, startedAt: number, endedAt: number): Promise<void> {
  const ms = endedAt - startedAt
  if (ms >= LONG_TOOL_MS) await auto(io, options, 'tool_call', ['--tool', tool, '--duration-s', (ms / 1000).toFixed(1)])
  await io.patchLedger(l => ({ ...l, lastActivity: endedAt }))
}

export async function ledgerCommand(io: Io, options: PluginOptions, e: CommandRunInput): Promise<CommandRunResult> {
  const name = e.command
  if (!isOperator(e.origin)) return { text: refusedText(name, e.origin) }
  await touch(io, options)
  const args = splitArgs(e.args)
  let argv: string[]
  if (name === 'stage') {
    if (args.length === 0) return { text: 'Usage: /stage <gate> [scene] | /stage end [gate [scene]]' }
    argv = args[0] === 'end' ? ['stage', 'end', ...args.slice(1)] : ['stage', 'start', ...args, '--switch']
  } else if (name === 'wait') {
    if (args.length === 0) return { text: 'Usage: /wait <who>' }
    argv = ['stage', 'wait', ...args]
  } else if (name === 'report') {
    argv = ['report']
  } else {
    argv = ['stage', name, ...args]
  }
  const r = await cli(io, options, argv, { json: false })
  await refresh(io, options)
  if (name === 'report' && r.code === 0) io.toast('AEM: reports/time.md written')
  return { text: r.text || `aem ${argv.join(' ')} exited ${r.code}` }
}
