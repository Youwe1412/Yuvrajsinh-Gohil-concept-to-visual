// Feature "context": the active project in the system prompt and the status line,
// drift toasts at session start, and /aem use | status | new-client.
import type { CommandRunInput, CommandRunResult, PluginOptions, PromptComposeSection } from 'claude-code'

import { cli, errorOf, isOperator, refresh, refusedText, splitArgs, startToast, statusLine } from './aem'
import type { CommandSpecLite, Io } from './aem'

export const SECTION_ID = 'aavkar-educational-motion-studio:context'

export const CONTEXT_COMMANDS: readonly CommandSpecLite[] = [
  { name: 'aem', description: 'Aavkar Educational Motion Studio: use, status, new-client', argumentHint: 'use <client>/<project> | use --clear | status | new-client <id>' },
]

const HELP = [
  'Usage:',
  '  /aem use <client>/<project>   pin a project to THIS session (nothing global is written)',
  '  /aem use --clear              drop the pin; the session goes back to resolving from its folder',
  '  /aem status                   the project, how it was resolved, gate, approvals',
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
  // Always shown, so no toast means the plugin is not loaded in this session.
  io.toast(startToast(view), 10_000)
  if (view.active && !view.error) await toastDrift(io, options)
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
  if (sub === 'use' && args[1] === '--clear' && args.length === 2) {
    if (!isOperator(e.origin)) return { text: refusedText('aem use --clear', e.origin) }
    const was = await io.getPin()
    await io.setPin(null)
    const { view } = await refresh(io, options)
    io.toast(startToast(view))
    return { text: `${was ? `Session pin ${was} dropped.` : 'This session had no pin.'}\n${startToast(view)}` }
  }
  if (sub === 'use' || sub === 'new-client') {
    if (!isOperator(e.origin)) return { text: refusedText(`aem ${sub}`, e.origin) }
    let rest = args.slice(1)
    if (sub === 'use') {
      // A project name with spaces may be typed unquoted: join the words before the first flag.
      const flagAt = rest.findIndex(a => a.startsWith('--'))
      const words = flagAt === -1 ? rest : rest.slice(0, flagAt)
      rest = [words.join(' '), ...(flagAt === -1 ? [] : rest.slice(flagAt))]
    }
    const r = await cli(io, options, [sub, ...rest], { json: sub === 'use' })
    if (sub === 'use') {
      // `aem use` checks the project resolves, has a frame rate and may be used. Only then is it pinned,
      // to this session: other sessions and the terminal are not touched.
      const client = r.data.client
      const project = r.data.project
      if (r.code !== 0 || typeof client !== 'string' || typeof project !== 'string') {
        return { text: `Not pinned: ${errorOf(r)}` }
      }
      await io.setPin(`${client}/${project}`)
      const { view } = await refresh(io, options)
      io.toast(startToast(view), 8000)
      await toastDrift(io, options)
      const f = r.data.fps as { num?: number; den?: number; source?: string } | undefined
      const lines = [`Pinned ${client}/${project} to this session (no other session or terminal is changed).`, `  folder ${String(r.data.project_dir)}`]
      if (f) lines.push(`  fps ${f.num}/${f.den} (from ${f.source})`)
      return { text: lines.join('\n') }
    }
    await refresh(io, options)
    return { text: r.text || `aem ${sub} exited ${r.code}` }
  }
  if (sub === 'status' || sub === undefined) {
    const r = await cli(io, options, ['status'], { json: false })
    await refresh(io, options)
    return { text: r.text }
  }
  return { text: HELP }
}
