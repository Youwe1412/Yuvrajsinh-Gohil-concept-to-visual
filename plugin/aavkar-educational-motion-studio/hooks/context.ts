// Feature "context": the active project in the system prompt and the status line,
// drift toasts at session start, and /aem use | status | new-client.
import type { CommandRunInput, CommandRunResult, PluginOptions, PromptComposeSection } from 'claude-code'

import { cli, errorOf, isOperator, refresh, refusedText, splitArgs, statusLine } from './aem'
import type { CommandSpecLite, Io } from './aem'

export const SECTION_ID = 'aavkar-educational-motion-studio:context'

export const CONTEXT_COMMANDS: readonly CommandSpecLite[] = [
  { name: 'aem', description: 'Aavkar Educational Motion Studio: use, status, new-client', argumentHint: 'use <client>/<project> | status | new-client <id>' },
]

const HELP = [
  'Usage:',
  '  /aem use <client>/<project> [--path DIR] [--fps N/D]   make a project active',
  '  /aem status                                          active project, gate, approvals',
  '  /aem new-client <id> --name NAME --design-system DIR --projects-root DIR [--contact NAME]',
].join('\n')

type Finding = { check?: string; file?: string; problem?: string }

async function toastDrift(io: Io, options: PluginOptions): Promise<void> {
  const drift = await cli(io, options, ['drift'])
  if (drift.code === 0 || drift.code === 127) return
  const findings = Array.isArray(drift.data.findings) ? (drift.data.findings as Finding[]) : []
  if (findings.length === 0) {
    io.toast(`AEM drift check failed: ${errorOf(drift)}`, 8000)
    return
  }
  for (const f of findings.slice(0, 3)) {
    io.toast(`AEM drift [${f.check}] ${f.file ?? ''} ${f.problem ?? ''}`.replace(/\s+/g, ' ').trim(), 10_000)
  }
  if (findings.length > 3) io.toast(`AEM drift: ${findings.length - 3} more; run aem drift`, 10_000)
}

export async function contextStart(io: Io, options: PluginOptions): Promise<void> {
  const { view } = await refresh(io, options)
  if (view.error) io.toast(`AEM: ${view.error}`, 10_000)
  else if (!view.active) io.toast('AEM: no active project. Run /aem use <client>/<project>', 8000)
  else await toastDrift(io, options)
}

// Every 30 s: stage time ticks locally; every sixth tick the CLI is read again for outside changes.
// Every tick (30 s) re-reads `aem status`: the active project, stage and approvals can change from
// another session, the operator's terminal or Codex, and the status line should follow within a tick.
export async function contextTick(io: Io, options: PluginOptions, _tick: number): Promise<void> {
  await refresh(io, options)
}

export async function contextCompose(io: Io, sections: readonly PromptComposeSection[]): Promise<PromptComposeSection[]> {
  const text = (await io.getView()).contextText
  const rest = sections.filter(s => s.id !== SECTION_ID)
  return text ? [...rest, { id: SECTION_ID, text, scope: 'session' }] : rest
}

export async function contextCommand(io: Io, options: PluginOptions, e: CommandRunInput): Promise<CommandRunResult> {
  const args = splitArgs(e.args)
  const sub = args[0]
  if (sub === 'use' || sub === 'new-client') {
    if (!isOperator(e.origin)) return { text: refusedText(`aem ${sub}`, e.origin) }
    let rest = args.slice(1)
    if (sub === 'use') {
      // A project name with spaces may be typed unquoted: join the words before the first flag.
      const flagAt = rest.findIndex(a => a.startsWith('--'))
      const words = flagAt === -1 ? rest : rest.slice(0, flagAt)
      rest = [words.join(' '), ...(flagAt === -1 ? [] : rest.slice(flagAt))]
    }
    const r = await cli(io, options, [sub, ...rest], { json: false })
    const { view } = await refresh(io, options)
    if (r.code === 0 && sub === 'use') {
      io.toast(statusLine(view, await io.now()))
      await toastDrift(io, options)
    }
    return { text: r.text || `aem ${sub} exited ${r.code}` }
  }
  if (sub === 'status' || sub === undefined) {
    const r = await cli(io, options, ['status'], { json: false })
    await refresh(io, options)
    return { text: r.text }
  }
  return { text: HELP }
}
