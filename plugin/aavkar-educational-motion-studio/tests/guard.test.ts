import { describe, expect, test } from 'claude-code/testing'

import { COMPOSER, INACTIVE, PRESENTATION, START, active, floor } from './fake-aem'
import type { Reply, Router } from './fake-aem'

// aem guard as the CLI answers it: deny a placement of an unapproved render (G05) and writes to events.jsonl (G01).
function guardReply(stdin: string | undefined): Reply {
  const req = JSON.parse(stdin ?? '{}') as { tool: string; input: { command?: string; file_path?: string }; cwd: string }
  if (req.input.command?.includes('place.py')) {
    return { code: 1, json: { ok: true, decision: 'deny', rule: 'AEM-G05', rule_name: 'render not approved',
      reason: 'renders/a.mp4 has no standing approval.', how: 'Review the render, then type /approve a.' } }
  }
  if (req.input.file_path?.endsWith('events.jsonl')) {
    return { code: 1, json: { ok: true, decision: 'deny', rule: 'AEM-G01', rule_name: 'protected file',
      reason: 'events.jsonl is protected.', how: 'Ask the operator, or /allow AEM-G01 <reason>.' } }
  }
  if (req.input.command?.includes('snapshot --describe')) {
    return { json: { ok: true, decision: 'allow', allow_id: 'allow-1234', once: true, overridden: { rule: 'AEM-G03' } } }
  }
  return { json: { ok: true, decision: 'allow' } }
}

const withGuard = (base: Router): Router => (args, stdin) => (args[0] === 'guard' ? guardReply(stdin) : base(args, stdin))

const run = (cmdRun: (e: never) => Promise<{ text?: string }>, command: string, args: string, origin: object = COMPOSER) =>
  cmdRun({ command, args, origin, presentation: PRESENTATION } as never)

describe('guard', () => {
  test('a denied tool call never runs; the agent is told why and how; a toast shows', async ($, on) => {
    const w = floor(on, withGuard(active()))
    await $.session.start(START)
    const r = await $.tool.call({ tool: 'Bash', command: 'python3 place.py renders/a.mp4' })
    expect(w.toolsRun).toEqual([])
    expect(JSON.stringify(r)).toContain('AEM denied this call (AEM-G05, render not approved)')
    expect(JSON.stringify(r)).toContain('Review the render, then type /approve a.')
    expect(w.toasts.at(-1)).toBe('AEM denied Bash: AEM-G05 render not approved')
    const g = w.calls.find(c => c[1] === 'guard')
    expect(g).toEqual(['aem', 'guard', '--json'])
    const sent = JSON.parse(w.stdins[w.calls.indexOf(g as string[])] ?? '{}')
    expect(sent).toEqual({ tool: 'Bash', input: { command: 'python3 place.py renders/a.mp4' }, cwd: '/projects/P1' })
  })

  test('protected write denied; ordinary edit allowed and run', async ($, on) => {
    const w = floor(on, withGuard(active()))
    await $.session.start(START)
    const denied = await $.tool.call({ tool: 'Write', file_path: '/projects/P1/events.jsonl', content: '{}' })
    expect(JSON.stringify(denied)).toContain('AEM-G01')
    await $.tool.call({ tool: 'Edit', file_path: '/projects/P1/brief.md', old_string: 'a', new_string: 'b' })
    expect(w.toolsRun).toEqual(['Edit'])
  })

  test('a one-time /allow that lets a call through is toasted', async ($, on) => {
    const w = floor(on, withGuard(active()))
    await $.session.start(START)
    await $.tool.call({ tool: 'Bash', command: 'npx hyperframes snapshot --describe .' })
    expect(w.toolsRun).toEqual(['Bash'])
    expect(w.toasts.at(-1)).toContain('one-time /allow allow-1234')
  })

  test('unguarded tools are not checked; guarded ones are, even while the view says no project', async ($, on) => {
    const w = floor(on, withGuard(INACTIVE))
    await $.session.start(START)
    await $.tool.call({ tool: 'TaskList' } as never)
    expect(w.calls.some(c => c[1] === 'guard')).toBe(false)
    // The view is refreshed on a timer and can lag a project made active elsewhere: the CLI decides.
    await $.tool.call({ tool: 'Read', file_path: '/anywhere/x.md' })
    expect(w.calls.filter(c => c[1] === 'guard').length).toBe(1)
    const r = await $.tool.call({ tool: 'Bash', command: 'python3 place.py renders/a.mp4' })
    expect(JSON.stringify(r)).toContain('AEM-G05')
  })

  test('if aem cannot run, the call is allowed and a toast says it was not checked', async ($, on) => {
    const w = floor(on, INACTIVE, { cannotStart: true })
    await $.session.start(START)
    await $.tool.call({ tool: 'Bash', command: 'ls' })
    expect(w.toolsRun).toEqual(['Bash'])
    expect(w.toasts.some(t => t.startsWith('AEM guard could not run'))).toBe(true)
  })

  test('/approve, /reject, /client-said and /allow build the CLI call exactly', async ($, on) => {
    const w = floor(on, withGuard(active()), { selection: 'I really liked\n  the "first" one' })
    await $.session.start(START)
    const cmd = (c: string, a: string) => run($.command.run as never, c, a)
    await cmd('approve', 'fd_S01_next-token G4')
    await cmd('approve', 'fd_S01_next-token renders/v09/fd_S01_next-token_v09.mp4')
    await cmd('reject', 'shot  the caption repeats   the demo')
    await cmd('client-said', 'video --source Frame.io Could you leave the grade?\nIt is "a bit more natural"')
    await cmd('client-said', 'channel')
    await cmd('allow', '"snapshot --describe" need one look at layout')
    await cmd('allow', 'AEM-G02 shared font folder --standing')
    const ran = w.calls.filter(c => c.at(-1) !== '--json').map(c => c.slice(1))
    expect(ran).toEqual([
      ['approve', 'fd_S01_next-token', '--gate', 'G4'],
      ['approve', 'fd_S01_next-token', 'renders/v09/fd_S01_next-token_v09.mp4'],
      ['reject', 'shot', '--reason', 'the caption repeats   the demo'],
      ['client-said', '--scope', 'video', '--source', 'Frame.io'],
      ['client-said', '--scope', 'channel', '--source', 'pasted in Claude Code (the selected text)'],
      ['allow', 'snapshot --describe', '--reason', 'need one look at layout', '--once'],
      ['allow', 'AEM-G02', '--reason', 'shared font folder'],
    ])
    const stdinOf = (i: number) => w.stdins[w.calls.indexOf(w.calls.filter(c => c.at(-1) !== '--json')[i] as string[])]
    expect(stdinOf(3)).toBe('Could you leave the grade?\nIt is "a bit more natural"')
    expect(stdinOf(4)).toBe('I really liked\n  the "first" one')
    expect(w.toasts.some(t => t.startsWith('AEM approve:'))).toBe(true)
  })

  test('the four commands refuse anyone but the operator and run nothing', async ($, on) => {
    const w = floor(on, withGuard(active()))
    await $.session.start(START)
    const before = w.calls.length
    for (const [c, a] of [['approve', 'x G4'], ['reject', 'x no'], ['client-said', 'video hi'], ['allow', 'AEM-G01 why']]) {
      const out = await run($.command.run as never, c as string, a as string, { kind: 'plugin', name: 'other' })
      expect(out.text).toContain('can only be typed by the operator')
    }
    expect(w.calls.slice(before).filter(c => c.at(-1) !== '--json')).toEqual([])
  })

  test('usage text for missing arguments', async ($, on) => {
    floor(on, withGuard(active()))
    await $.session.start(START)
    expect((await run($.command.run as never, 'approve', '')).text).toContain('Usage')
    expect((await run($.command.run as never, 'reject', 'onlyitem')).text).toContain('Usage')
    expect((await run($.command.run as never, 'client-said', 'video')).text).toContain('Usage')
    expect((await run($.command.run as never, 'allow', 'AEM-G01')).text).toContain('Usage')
  })
})
