import { describe, expect, test } from 'claude-code/testing'

import { COMPOSER, INACTIVE, NOW, PRESENTATION, START, active, autos, floor } from './fake-aem'

const TURN_END = { answer: 'ok', durationMs: 1000, isAborted: false, turnId: 't1', reason: 'answer' } as const

describe('ledger', () => {
  test('session, prompt, turns and long tool calls go through aem stage auto', async ($, on) => {
    const w = floor(on, active(), { toolMs: { Bash: 45_000, Read: 5_000 } })
    await $.session.start(START)
    expect(autos(w)).toEqual([['session_start']])
    expect(w.calls.find(c => c[2] === 'auto')).toContain('sess-1')

    await $.prompt.submit({ text: 'render it', wait: false, origin: COMPOSER })
    await $.prompt.submit({ text: 'note', wait: false, origin: { kind: 'plugin', name: 'other' } })
    await $.turn.start({ text: 'render it', turnId: 't1' })
    await $.tool.call({ tool: 'Bash', command: 'hyperframes render .' })
    await $.tool.call({ tool: 'Read', file_path: '/tmp/x' })
    await $.turn.complete({ ...TURN_END, turnId: 'sub', agentId: 'agent-7' })
    await $.turn.complete(TURN_END)
    expect(autos(w).slice(1)).toEqual([
      ['prompt', '--origin', 'composer'],
      ['turn_start', '--turn', 't1'],
      ['tool_call', '--tool', 'Bash', '--duration-s', '45.0'],
      ['turn_end', '--turn', 't1'],
    ])
  })

  test('idle starts after idle_minutes with no activity, measured from the last activity', async ($, on) => {
    const w = floor(on, active({ status: { json: { ok: true, active: true, idle_minutes: 10, statusline_parts: {
      client: 'MergeToMaster', project: 'P1 - Test', gate: 'G1', scene: null, since: '2026-10-06T10:00:00+05:30',
      paused: false, waiting: null, stale: 0 } } } }))
    await $.session.start(START)
    await w.clock.advance(9 * 60_000)
    expect(autos(w).map(a => a[0])).not.toContain('idle_start')
    await w.clock.advance(90_000)
    expect(autos(w)).toContainEqual(['idle_start', '--since', new Date(NOW).toISOString()])
    await w.clock.advance(5 * 60_000)
    expect(autos(w).filter(a => a[0] === 'idle_start')).toHaveLength(1)
    await $.prompt.submit({ text: 'back', wait: false, origin: COMPOSER })
    const names = autos(w).map(a => a[0])
    expect(names.slice(-2)).toEqual(['idle_end', 'prompt'])
  })

  test('no idle while a turn runs', async ($, on) => {
    const w = floor(on, active())
    await $.session.start(START)
    await $.turn.start({ text: '', turnId: 'long' })
    await w.clock.advance(20 * 60_000)
    expect(autos(w).map(a => a[0])).not.toContain('idle_start')
  })

  test('a reload does not record a second session_start; session.end records the end', async ($, on) => {
    const w = floor(on, active())
    await $.session.start(START)
    await $.session.start(START)
    expect(autos(w).filter(a => a[0] === 'session_start')).toHaveLength(1)
    await $.session.end({ reason: 'prompt_input_exit', sessionId: 'sess-1', resume: { sessionId: 'sess-1' } } as never)
    expect(autos(w).at(-1)).toEqual(['session_end', '--note', 'prompt_input_exit'])
  })

  test('nothing is recorded while no project is active', async ($, on) => {
    const w = floor(on, INACTIVE)
    await $.session.start(START)
    await $.prompt.submit({ text: 'hi', wait: false, origin: COMPOSER })
    await $.turn.start({ text: 'hi', turnId: 't1' })
    await $.turn.complete(TURN_END)
    expect(autos(w)).toEqual([])
  })

  test('/stage, /pause, /resume, /wait and /report call the CLI; only the operator may', async ($, on) => {
    const w = floor(on, active({ stage: { text: 'start G1 at 2026-10-06T10:05:00+05:30' }, report: { text: '# Time report' } }))
    await $.session.start(START)
    const run = (command: string, args = '', origin: object = COMPOSER) =>
      $.command.run({ command, args, origin: origin as never, presentation: PRESENTATION })
    expect((await run('stage', 'G1')).text).toBe('start G1 at 2026-10-06T10:05:00+05:30')
    await run('stage', 'G4 fd_S01_next-token')
    await run('stage', 'end')
    await run('pause')
    await run('resume')
    await run('wait', 'joel')
    const report = await run('report')
    expect(report.text).toBe('# Time report')
    expect(w.toasts).toContain('AEM: reports/time.md written')
    const ran = w.calls.filter(c => c.at(-1) !== '--json').map(c => c.slice(1))
    expect(ran).toEqual([
      ['stage', 'start', 'G1', '--switch'],
      ['stage', 'start', 'G4', 'fd_S01_next-token', '--switch'],
      ['stage', 'end'],
      ['stage', 'pause'],
      ['stage', 'resume'],
      ['stage', 'wait', 'joel'],
      ['report'],
    ])
    const before = w.calls.length
    const refused = await run('stage', 'G2', { kind: 'plugin', name: 'x' })
    expect(refused.text).toContain('can only be typed by the operator')
    expect(w.calls.slice(before).some(c => c[2] === 'start')).toBe(false)
    expect((await run('stage')).text).toContain('Usage')
  })
})
