import { describe, expect, test } from 'claude-code/testing'

import { INACTIVE, NOW, PARTS, START, active, floor } from './fake-aem'
import type { Reply, Router } from './fake-aem'

const ALLOW: Reply = { json: { ok: true, decision: 'allow' } }

// aem rendered as the CLI answers it: hyperframes renders are renders; one failed with a flash.
function renderedReply(stdin: string | undefined): Reply {
  const req = JSON.parse(stdin ?? '{}') as { command: string; probe_only?: boolean }
  if (!req.command.includes('hyperframes render')) return { json: { ok: true, render: false, outputs: [], text: '' } }
  if (req.probe_only) return { json: { ok: true, render: true, outputs: [], text: '' } }
  return { json: { ok: true, render: true, passed: 0, failed: 1, stale: 1,
    toast: 'AEM render check FAIL: a_v02.mp4: flash at frame 10 (00:00:00:10), 1 frame(s); 1 approval(s) now stale',
    text: 'AEM checked 1 render(s) this command wrote:\n- FAIL renders/a_v02.mp4 (a)' } }
}

const withRendered = (base: Router): Router => (args, stdin) =>
  args[0] === 'guard' ? ALLOW : args[0] === 'rendered' ? renderedReply(stdin) : base(args, stdin)

const renderedCalls = (calls: string[][]) => calls.filter(c => c[1] === 'rendered')

describe('render sentinel', () => {
  test('after a render: aem rendered checks it, the operator gets a toast, the agent reads the result', async ($, on) => {
    const w = floor(on, withRendered(active()), { toolMs: { Bash: 90_000 } })
    await $.session.start(START)
    const before = w.calls.length
    const r = await $.tool.call({ tool: 'Bash', command: 'npx hyperframes render . -o renders/a_v02.mp4' })
    expect(w.toolsRun).toEqual(['Bash'])
    const i = w.calls.findIndex((c, n) => n >= before && c[1] === 'rendered')
    expect(w.calls[i]).toEqual(['aem', 'rendered', '--json'])
    expect(JSON.parse(w.stdins[i] ?? '{}')).toEqual({
      command: 'npx hyperframes render . -o renders/a_v02.mp4', cwd: '/projects/P1', started_at: NOW / 1000, exit_code: 0,
    })
    expect(w.toasts).toContain('AEM render check FAIL: a_v02.mp4: flash at frame 10 (00:00:00:10), 1 frame(s); 1 approval(s) now stale')
    expect('context' in r ? r.context : undefined).toEqual(['AEM checked 1 render(s) this command wrote:\n- FAIL renders/a_v02.mp4 (a)'])
    // The status line is redrawn after the check, so its stale count is current.
    expect(w.calls.slice(i + 1).some(c => c[1] === 'status')).toBe(true)
  })

  test('a command that is not a render adds nothing', async ($, on) => {
    const w = floor(on, withRendered(active()))
    await $.session.start(START)
    const toasts = w.toasts.length
    const r = await $.tool.call({ tool: 'Bash', command: 'ls renders' })
    expect(renderedCalls(w.calls).length).toBe(1)
    expect(w.toasts.length).toBe(toasts)
    expect('context' in r ? r.context : undefined).toBeUndefined()
  })

  test('other tools are not watched; Bash is, and the CLI says when no project is active', async ($, on) => {
    const none: Reply = { json: { ok: true, render: false, outputs: [], text: '', note: 'no active project' } }
    const w = floor(on, (args, stdin) => (args[0] === 'guard' ? ALLOW : args[0] === 'rendered' ? none : INACTIVE(args, stdin)))
    await $.session.start(START)
    const toasts = w.toasts.length
    await $.tool.call({ tool: 'Read', file_path: '/projects/P1/renders/a.mp4' })
    expect(renderedCalls(w.calls)).toEqual([])
    const r = await $.tool.call({ tool: 'Bash', command: 'npx hyperframes render .' })
    expect(renderedCalls(w.calls).length).toBe(1)
    expect(w.toasts.length).toBe(toasts)
    expect('context' in r ? r.context : undefined).toBeUndefined()
  })

  test('a render run in the background is flagged as not checked', async ($, on) => {
    const w = floor(on, withRendered(active()))
    await $.session.start(START)
    const r = await $.tool.call({ tool: 'Bash', command: 'npx hyperframes render .', run_in_background: true })
    const i = w.calls.findIndex(c => c[1] === 'rendered')
    expect(JSON.parse(w.stdins[i] ?? '{}')).toEqual({ command: 'npx hyperframes render .', probe_only: true })
    expect(w.toasts).toContain('AEM: a render started in the background is not checked automatically')
    expect(JSON.stringify('context' in r ? r.context : [])).toContain('aem check-render <path>')
  })

  test('a denied call is never watched', async ($, on) => {
    const deny: Reply = { code: 1, json: { ok: true, decision: 'deny', rule: 'AEM-G03', rule_name: 'blocked command', reason: 'x', how: 'y' } }
    const w = floor(on, (args, stdin) => (args[0] === 'guard' ? deny : withRendered(active())(args, stdin)))
    await $.session.start(START)
    await $.tool.call({ tool: 'Bash', command: 'npx hyperframes render .' })
    expect(renderedCalls(w.calls)).toEqual([])
  })

  test('a re-render that makes an approval stale shows on the status line at once', async ($, on) => {
    let rendered = false
    const router: Router = (args, stdin) => {
      if (args[0] === 'rendered') {
        rendered = true
        return renderedReply(stdin)
      }
      if (args[0] === 'status') {
        return { json: { ok: true, active: true, statusline_parts: { ...PARTS, gate: 'G4', stale: rendered ? 1 : 0 } } }
      }
      return withRendered(active())(args, stdin)
    }
    const w = floor(on, router)
    await $.session.start(START)
    expect(w.statuses.at(-1)).not.toContain('stale')
    await $.tool.call({ tool: 'Bash', command: 'npx hyperframes render . -o renders/a_v02.mp4' })
    expect(w.statuses.at(-1)).toContain('· 1 stale')
    expect(w.toasts.at(-1)).toContain('1 approval(s) now stale')
  })
})
