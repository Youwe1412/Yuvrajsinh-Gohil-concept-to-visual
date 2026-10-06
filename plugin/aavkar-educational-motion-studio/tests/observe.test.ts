import { describe, expect, test } from 'claude-code/testing'

import { INACTIVE, START, active, floor } from './fake-aem'
import type { Reply, Router } from './fake-aem'

// What the agent ran in the P2 session of 6 October 2026 and AEM (then a guard) denied. aem observe records each and
// answers that none is a delivery (tests/test_observe.py checks that answer against Joel's registry entry); the
// plugin runs each with no question.
const P2_DENIED = [
  `unzip -p "/var/folders/yh/753jqf190vv2h597rcd4025h0000gp/T/com.anthropic.claudefordesktop/zip_cache/5CFFB904" "P2 - Claude Code - New Rough Cut - Oct 5.fcpxmld/Info.fcpxml"`,
  'cat "XML/P2 - Claude Code - New Rough Cut - Oct 5.fcpxml"',
  'which hyperframes whisper-cli mfa ffmpeg sox 2>&1; ls ~/Tools/fcp-edit-workflow 2>&1 | head; ls ~/Tools 2>&1',
  'cd ~/Tools/fcp-edit-workflow; head -5 fcp-workflow; ls -a | head -40; grep -iE "venv|python" README.md | head -15',
  'grep -n "grade" "/Volumes/T7 Red/Yuvraj Folder/Freelance Work/Joel Belton - MergeToMaster/00 - MergeToMaster Design System/joel-decisions.md"',
]

const UNAPPROVED = {
  kinds: ['copy'], gate: 'G6', question: 'fd_S01 was re-rendered after you approved it. Deliver anyway?',
  unapproved: [{ item: 'fd_S01', path: 'renders/fd_S01_v02.mp4', state: 'stale' }],
  approve: [['approve', 'fd_S01', '/p/renders/fd_S01_v02.mp4', '--gate', 'G6', '--delivery-confirmation']],
  slash: ['/approve fd_S01 renders/fd_S01_v02.mp4 G6'],
}

type Req = { tool: string; input: { command?: string }; outcome?: string; note?: string }

// aem observe as the CLI answers it: copies into delivery/ name an unapproved render, approved.mp4 is approved.
function observeReply(stdin: string | undefined): Reply {
  const req = JSON.parse(stdin ?? '{}') as Req
  if (req.outcome) return { json: { ok: true, observed: true } }
  const command = req.input.command ?? ''
  if (command.includes('delivery/') && command.includes('approved.mp4')) {
    return { json: { ok: true, observed: true, delivery: { kinds: ['copy'], gate: 'G6', unapproved: [], media: [{ item: 'a', state: 'approved' }] } } }
  }
  if (command.includes('delivery/')) return { json: { ok: true, observed: true, delivery: UNAPPROVED } }
  if (command.includes('shotlist.md')) {
    return { json: { ok: true, observed: true, delivery: null, inferred: { gate: 'G2', note: 'a plan file changed: shotlist.md' } } }
  }
  return { json: { ok: true, observed: true, delivery: null } }
}

const withObserve = (base: Router): Router => (args, stdin) => (args[0] === 'observe' ? observeReply(stdin) : base(args, stdin))

const observes = (w: ReturnType<typeof floor>) =>
  w.calls.map((c, i) => ({ c, req: JSON.parse(w.stdins[i] ?? '{}') as Req })).filter(x => x.c[1] === 'observe')

const DELIVER = 'cp renders/fd_S01_v02.mp4 delivery/'

describe('observe', () => {
  test('every Bash, Read, Write and Edit call is recorded before it runs; other tools are not', async ($, on) => {
    const w = floor(on, withObserve(active()))
    await $.session.start(START)
    await $.tool.call({ tool: 'Bash', command: 'ls renders' })
    await $.tool.call({ tool: 'Read', file_path: '/projects/P1/brief.md' })
    await $.tool.call({ tool: 'Write', file_path: '/projects/P1/a.md', content: 'x' })
    await $.tool.call({ tool: 'Edit', file_path: '/projects/P1/a.md', old_string: 'x', new_string: 'y' })
    await $.tool.call({ tool: 'TaskList' } as never)
    expect(w.toolsRun).toEqual(['Bash', 'Read', 'Write', 'Edit', 'TaskList'])
    const sent = observes(w).map(x => x.req)
    expect(sent.map(r => r.tool)).toEqual(['Bash', 'Read', 'Write', 'Edit'])
    expect(sent[0]).toEqual({ tool: 'Bash', input: { command: 'ls renders' }, cwd: '/projects/P1', session: 'sess-1' })
    expect(w.asked).toEqual([])
  })

  test("the calls AEM denied in the P2 session run with no interruption and are recorded", async ($, on) => {
    const w = floor(on, withObserve(active()))
    await $.session.start(START)
    for (const command of P2_DENIED) {
      const r = await $.tool.call({ tool: 'Bash', command })
      expect('deny' in r && r.deny !== undefined).toBe(false)
    }
    await $.tool.call({ tool: 'Read', file_path: '/Volumes/T7/P2 - Claude Code/XML/P2 - Claude Code - New Rough Cut - Oct 5.fcpxml' })
    expect(w.toolsRun).toEqual([...P2_DENIED.map(() => 'Bash'), 'Read'])
    expect(observes(w).map(x => x.req.input.command ?? 'Read')).toEqual([...P2_DENIED, 'Read'])
    expect(w.asked).toEqual([])
    expect(w.toasts.some(t => t.includes('denied'))).toBe(false)
  })

  test('a stage AEM inferred is toasted', async ($, on) => {
    const w = floor(on, withObserve(active()))
    await $.session.start(START)
    await $.tool.call({ tool: 'Bash', command: 'cp draft.md shotlist.md' })
    expect(w.toasts).toContain('AEM: no stage was open, so G2 is inferred (a plan file changed: shotlist.md)')
  })

  test('if aem cannot run, every call runs and the toast says so at most once a minute', async ($, on) => {
    const w = floor(on, INACTIVE, { cannotStart: true })
    await $.session.start(START)
    await $.tool.call({ tool: 'Bash', command: 'ls' })
    await $.tool.call({ tool: 'Read', file_path: '/x' })
    expect(w.toolsRun).toEqual(['Bash', 'Read'])
    expect(w.toasts.filter(t => t.startsWith('AEM could not record this call'))).toHaveLength(1)
    await w.clock.advance(61_000)
    await $.tool.call({ tool: 'Read', file_path: '/x' })
    expect(w.toasts.filter(t => t.startsWith('AEM could not record this call'))).toHaveLength(2)
  })
})

describe('delivery confirmation', () => {
  test('a delivery of an unapproved render asks; Deliver records the approval through the confirmation and runs it', async ($, on) => {
    const w = floor(on, withObserve(active()), { answer: 'Deliver' })
    await $.session.start(START)
    const r = await $.tool.call({ tool: 'Bash', command: DELIVER })
    expect(w.asked).toEqual([{ question: 'fd_S01 was re-rendered after you approved it. Deliver anyway?', options: ['Deliver', 'Stop'] }])
    const i = w.calls.findIndex(c => c[1] === 'approve')
    expect(w.calls[i]).toEqual(['aem', 'approve', 'fd_S01', '/p/renders/fd_S01_v02.mp4', '--gate', 'G6', '--delivery-confirmation', '--json'])
    expect(w.envs[i]?.AEM_OPERATOR_NONCE).toMatch(/^[0-9a-f]{64}$/) // the operator's answer: a one-time nonce
    expect(w.toolsRun).toEqual(['Bash'])
    expect('deny' in r && r.deny !== undefined).toBe(false)
    expect(w.toasts).toContain('AEM: Deliver pressed; fd_S01 approved through the confirmation')
  })

  test('a delivery of an approved render does not ask', async ($, on) => {
    const w = floor(on, withObserve(active()), { answer: 'Deliver' })
    await $.session.start(START)
    await $.tool.call({ tool: 'Bash', command: 'cp renders/approved.mp4 delivery/' })
    expect(w.asked).toEqual([])
    expect(w.calls.some(c => c[1] === 'approve')).toBe(false)
    expect(w.toolsRun).toEqual(['Bash'])
  })

  test('Stop refuses the call, tells the agent, and records it', async ($, on) => {
    const w = floor(on, withObserve(active()), { answer: 'Stop' })
    await $.session.start(START)
    const r = await $.tool.call({ tool: 'Bash', command: DELIVER })
    expect(w.toolsRun).toEqual([])
    expect('deny' in r ? r.deny : '').toContain('the operator stopped this delivery')
    expect(w.calls.some(c => c[1] === 'approve')).toBe(false)
    const out = observes(w).map(x => x.req).filter(q => q.outcome)
    expect(out).toEqual([{ tool: 'Bash', input: { command: DELIVER }, cwd: '/projects/P1', session: 'sess-1', outcome: 'stopped', note: 'Stop pressed' }])
  })

  test('a dismissed dialog is a Stop', async ($, on) => {
    const w = floor(on, withObserve(active()), { answer: null })
    await $.session.start(START)
    const r = await $.tool.call({ tool: 'Bash', command: DELIVER })
    expect(w.toolsRun).toEqual([])
    expect('deny' in r ? r.deny : '').toContain('the dialog was dismissed')
  })

  test('with no dialog (a -p run): held once with the /approve command, the same call repeated goes through', async ($, on) => {
    const w = floor(on, withObserve(active()), { surfaces: [] })
    await $.session.start(START)
    const first = await $.tool.call({ tool: 'Bash', command: DELIVER })
    expect(w.asked).toEqual([])
    expect('deny' in first ? first.deny : '').toContain('types /approve fd_S01 renders/fd_S01_v02.mp4 G6')
    expect(w.toolsRun).toEqual([])
    const other = await $.tool.call({ tool: 'Bash', command: `${DELIVER} # another call` })
    expect('deny' in other && other.deny !== undefined).toBe(true) // a different call is held on its own
    await $.tool.call({ tool: 'Bash', command: DELIVER })
    expect(w.toolsRun).toEqual(['Bash'])
    expect(observes(w).map(x => x.req.outcome).filter(Boolean)).toEqual(['held', 'held', 'unconfirmed'])
    expect(w.toasts).toContain('AEM: delivered without approval (repeated after notice): fd_S01')
  })

  test('Deliver whose approval cannot be recorded still delivers, and says so', async ($, on) => {
    const failing: Router = (args, stdin) => (args[0] === 'approve' ? { code: 2, json: { ok: false, error: 'disk full' } } : withObserve(active())(args, stdin))
    const w = floor(on, failing, { answer: 'Deliver' })
    await $.session.start(START)
    await $.tool.call({ tool: 'Bash', command: DELIVER })
    expect(w.toolsRun).toEqual(['Bash'])
    expect(observes(w).map(x => x.req.outcome).filter(Boolean)).toEqual(['unconfirmed'])
    expect(w.toasts.some(t => t.includes('no approval was recorded: fd_S01: disk full'))).toBe(true)
  })
})
