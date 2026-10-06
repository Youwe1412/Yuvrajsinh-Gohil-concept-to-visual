// Feature "render sentinel": after a shell call finishes, `aem rendered` decides whether it was
// a render, finds the files it wrote, runs `aem check-render` on each and builds its evidence
// (`aem evidence`: poses, phone crops, a strip, sync, facts and evidence.md). The operator gets a
// toast per check and per evidence, the agent reads the result and the evidence.md paths after the
// command's output, and the status line's stale approval count is redrawn. Advisory: never blocks.
import type { PluginOptions } from 'claude-code'

import { cli, errorOf, refresh } from './aem'
import type { Io } from './aem'

// A render check scans every frame; a batch of 4K renders can take minutes.
export const SENTINEL_TIMEOUT_MS = 600_000

type Rendered = { render?: boolean; toast?: string; text?: string; failed?: number; evidence_toasts?: string[] }

// Every Bash call is watched: the CLI knows whether a project is active (the plugin's view can lag).
export async function sentinelBefore(io: Io, tool: string): Promise<number | undefined> {
  if (tool !== 'Bash') return undefined
  return io.now()
}

// Returns text for the agent to read after the command's output, or nothing.
export async function sentinelAfter(io: Io, options: PluginOptions, args: Record<string, unknown>,
  startedAt: number | undefined, isError: boolean): Promise<string | undefined> {
  if (startedAt === undefined) return undefined
  const command = String(args.command ?? '')
  if (args.run_in_background === true) {
    // The render finishes after this call returns; nothing here sees it end.
    const r = await cli(io, options, ['rendered'], { stdin: JSON.stringify({ command, probe_only: true }) })
    if ((r.data as Rendered).render) {
      io.toast('AEM: a render started in the background is not checked automatically', 8000)
      return 'AEM does not check renders run in the background. When it finishes, run `aem check-render <path>` on each output.'
    }
    return undefined
  }
  const r = await cli(io, options, ['rendered'], {
    stdin: JSON.stringify({ command, cwd: await io.cwd(), started_at: startedAt / 1000, exit_code: isError ? 1 : 0 }),
    timeoutMs: SENTINEL_TIMEOUT_MS,
  })
  const d = r.data as Rendered
  if (r.code !== 0) {
    io.toast(`AEM render sentinel could not run: ${errorOf(r)}`, 8000)
    return undefined
  }
  if (!d.render) return undefined
  if (d.toast) io.toast(d.toast, d.failed ? 12000 : 6000)
  for (const t of d.evidence_toasts ?? []) io.toast(t, 8000)
  await refresh(io, options)
  return d.text || undefined
}
