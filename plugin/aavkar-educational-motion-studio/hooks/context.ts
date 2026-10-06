// Feature "context": the active project in the system prompt and the status line,
// drift toasts at session start, and /aem use | status | new-client.
import { atom, read, update } from 'claude-code'
import type { EngineInterface, On, PluginOptions } from 'claude-code'

import type { AemView } from '../types'
import { EMPTY_VIEW, PLUGIN, errorOf, isOperator, runAem, splitArgs, statusLine, viewFrom } from './aem'
import type { AemResult, RunInit } from './aem'

const view = atom({ plugin: 'aavkar-educational-motion-studio', key: 'view' } as const, EMPTY_VIEW)

const SECTION_ID = `${PLUGIN}:context`

const HELP = [
  'Usage:',
  '  /aem use <client>/<project> [--path DIR] [--fps N/D]   make a project active',
  '  /aem status                                          active project, gate, approvals',
  '  /aem new-client <id> --name NAME --design-system DIR --projects-root DIR [--contact NAME]',
].join('\n')

type Finding = { check?: string; file?: string; problem?: string }

async function cli($: EngineInterface, options: PluginOptions, args: readonly string[], init?: RunInit): Promise<AemResult> {
  return runAem((argv, i) => $.process.run(argv, i), await $.env.get('HOME'), options, args, init)
}

// Reads status and context from the CLI into state, then redraws the status line.
async function refresh($: EngineInterface, options: PluginOptions): Promise<AemView> {
  const [status, ctx] = await Promise.all([cli($, options, ['status']), cli($, options, ['context'])])
  const next = viewFrom(status, ctx)
  await update($, view, () => next)
  $.ui.status(statusLine(next, await $.clock.now()))
  return next
}

async function toastDrift($: EngineInterface, options: PluginOptions): Promise<void> {
  const drift = await cli($, options, ['drift'])
  if (drift.code === 0 || drift.code === 127) return
  const findings = Array.isArray(drift.data.findings) ? (drift.data.findings as Finding[]) : []
  if (findings.length === 0) {
    $.ui.toast(`AEM drift check failed: ${errorOf(drift)}`, { timeoutMs: 8000 })
    return
  }
  for (const f of findings.slice(0, 3)) {
    $.ui.toast(`AEM drift [${f.check}] ${f.file ?? ''} ${f.problem ?? ''}`.replace(/\s+/g, ' ').trim(), { timeoutMs: 10_000 })
  }
  if (findings.length > 3) $.ui.toast(`AEM drift: ${findings.length - 3} more; run aem drift`, { timeoutMs: 10_000 })
}


export function context(on: On, options: PluginOptions): void {
  on('session.start', async ($, e, next) => {
    const started = await next(e)
    await $.command.register({
      name: 'aem',
      description: 'Aavkar Educational Motion Studio: use, status, new-client',
      argumentHint: 'use <client>/<project> | status | new-client <id>',
    })
    const v = await refresh($, options)
    if (v.error) $.ui.toast(`AEM: ${v.error}`, { timeoutMs: 10_000 })
    else if (!v.active) $.ui.toast('AEM: no active project. Run /aem use <client>/<project>', { timeoutMs: 8000 })
    else await toastDrift($, options)
    // Stage time ticks locally every 30 s; the CLI is asked again every 3 minutes for outside changes.
    let ticks = 0
    $.clock.every(30_000, () => {
      ticks += 1
      if (ticks % 6 === 0) {
        void refresh($, options)
        return
      }
      void (async () => $.ui.status(statusLine(await read($, view), await $.clock.now())))()
    })
    return started
  })

  on('prompt.compose', async ($, e, next) => {
    const composed = await next(e)
    const text = (await read($, view)).contextText
    if (!text) return composed
    return {
      sections: [...composed.sections.filter(s => s.id !== SECTION_ID), { id: SECTION_ID, text, scope: 'session' as const }],
    }
  })

  on('command.run', { command: 'aem' }, async ($, e) => {
    const args = splitArgs(e.args)
    const sub = args[0]
    if (sub === 'use' || sub === 'new-client') {
      if (!isOperator(e.origin)) {
        return { text: `AEM: /aem ${sub} can only be typed by the operator (this run came from ${e.origin.kind}).` }
      }
      let rest = args.slice(1)
      if (sub === 'use') {
        // A project name with spaces may be typed unquoted: join the words before the first flag.
        const flagAt = rest.findIndex(a => a.startsWith('--'))
        const words = flagAt === -1 ? rest : rest.slice(0, flagAt)
        rest = [words.join(' '), ...(flagAt === -1 ? [] : rest.slice(flagAt))]
      }
      const r = await cli($, options, [sub, ...rest], { json: false })
      const v = await refresh($, options)
      if (r.code === 0 && sub === 'use') {
        $.ui.toast(statusLine(v, await $.clock.now()))
        await toastDrift($, options)
      }
      return { text: r.text || `aem ${sub} exited ${r.code}` }
    }
    if (sub === 'status' || sub === undefined) {
      const r = await cli($, options, ['status'], { json: false })
      await refresh($, options)
      return { text: r.text }
    }
    return { text: HELP }
  })
}
