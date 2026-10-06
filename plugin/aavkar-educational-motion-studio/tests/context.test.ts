import { describe, expect, test } from 'claude-code/testing'

import { COMPOSER, INACTIVE, PARTS, PRESENTATION, START, active, floor } from './fake-aem'

const PARTS_G2 = { ...PARTS, gate: 'G2' }

const COMPOSE = { model: 'm', promptModel: 'm', surfaces: ['terminal'], tools: [], outputStyle: null, traits: [] } as const

describe('context', () => {
  test('no project resolved: the start toast says so, the status line and the inactive prompt section', async ($, on) => {
    const w = floor(on, INACTIVE)
    on('prompt.compose', () => ({ sections: [{ id: 'intro', text: 'engine intro', scope: 'shared' as const }] }))
    await $.session.start(START)
    expect(w.toasts).toContain('AEM 1.1.0 · no project (folder not registered)')
    expect(w.statuses.at(-1)).toBe('AEM · no project here · start in its folder or /aem use <client>/<project>')
    expect(w.calls.some(c => c[1] === 'drift')).toBe(false)
    expect(w.calls.some(c => c[1] === 'recall')).toBe(false)
    expect(w.logs).toEqual([])
    const composed = await $.prompt.compose(COMPOSE)
    expect(composed.sections.at(-1)).toEqual({ id: 'aavkar-educational-motion-studio:context', text: 'AEM inactive text', scope: 'session' })
  })

  test('active project: status line, prompt section from aem context, the recall in the transcript, drift toasts', async ($, on) => {
    const w = floor(on, active({
      recall: { json: { ok: true, text: 'AEM recall · MergeToMaster (joel) · Joel Belton\nStanding preferences: …' } },
      drift: { code: 1, json: { ok: false, findings: [
        { check: 'skill', file: 'SKILL.md', problem: 'installed copy differs from the master' },
        { check: 'text-export', file: 'text/Motion.md', problem: 'page changed since the export' },
      ] } },
    }))
    on('prompt.compose', () => ({ sections: [{ id: 'intro', text: 'engine intro', scope: 'shared' as const }] }))
    await $.session.start(START)
    expect(w.statuses.at(-1)).toBe('AEM · MergeToMaster · P1 - Test · G1 · 0:05')
    // Every session starts with one toast naming the version, the project and how it was resolved.
    expect(w.toasts[0]).toBe('AEM 1.1.0 · joel/P1 · resolved from folder')
    expect(w.toasts).toContain('AEM drift [skill] SKILL.md installed copy differs from the master')
    expect(w.toasts).toContain('AEM drift [text-export] text/Motion.md page changed since the export')
    expect(w.calls.map(c => c[1])).toEqual(expect.arrayContaining(['status', 'context', 'recall', 'drift']))
    // The operator sees at session start what the agent was given about the client.
    expect(w.logs).toEqual(['AEM recall · MergeToMaster (joel) · Joel Belton\nStanding preferences: …'])
    expect(w.calls.every(c => c.at(-1) === '--json')).toBe(true)
    const composed = await $.prompt.compose(COMPOSE)
    expect(composed.sections[0]?.id).toBe('intro')
    expect(composed.sections.at(-1)).toEqual({ id: 'aavkar-educational-motion-studio:context', text: 'CONTEXT FOR JOEL P1', scope: 'session' })
    // A second render does not add the section twice.
    const again = await $.prompt.compose(COMPOSE)
    expect(again.sections.filter(s => s.id === 'aavkar-educational-motion-studio:context')).toHaveLength(1)
  })

  test('a stage AEM inferred says so on the status line', async ($, on) => {
    const w = floor(on, active({ status: { json: { ok: true, active: true, client: 'joel', project: 'P1',
      statusline_parts: { ...PARTS_G2, inferred: true, integrity: 2 } } } }))
    await $.session.start(START)
    expect(w.statuses.at(-1)).toBe('AEM · MergeToMaster · P1 - Test · G2 (inferred) · 0:05 · 2 ledger edits to review')
  })

  test('the status line counts moments, approvals and rulings; /aem moments prints the table', async ($, on) => {
    const w = floor(on, active({
      status: { json: { ok: true, active: true, client: 'joel', project: 'P1',
        statusline_parts: { ...PARTS, moments: { moments: 58, approved: 1, ruled: 3 } } } },
      moments: { text: 'P1 · 58 moments · direction: full notes' },
    }))
    await $.session.start(START)
    expect(w.statuses.at(-1)).toBe('AEM · MergeToMaster · P1 - Test · G1 · 0:05 · 58 moments · 1 approved · 3 ruled')
    const out = await $.command.run({ command: 'aem', args: 'moments', origin: COMPOSER, presentation: PRESENTATION })
    expect(out.text).toBe('P1 · 58 moments · direction: full notes')
    expect(w.calls).toContainEqual(['aem', 'moments'])
  })

  test('/aem calibrate prints the CLI text and writes nothing', async ($, on) => {
    const w = floor(on, active({ calibrate: { text: 'AEM calibrate · MergeToMaster (joel)' } }))
    await $.session.start(START)
    const out = await $.command.run({ command: 'aem', args: 'calibrate joel', origin: COMPOSER, presentation: PRESENTATION })
    expect(out.text).toBe('AEM calibrate · MergeToMaster (joel)')
    expect(w.calls).toContainEqual(['aem', 'calibrate', 'joel'])
    const at = w.calls.findIndex(c => c[1] === 'calibrate')
    expect(w.envs[at]?.AEM_OPERATOR_NONCE).toBeUndefined()
  })

  test('/aem recall prints the CLI text', async ($, on) => {
    const w = floor(on, active({ recall: { text: 'AEM recall · Acme' } }))
    await $.session.start(START)
    const out = await $.command.run({ command: 'aem', args: 'recall acme', origin: COMPOSER, presentation: PRESENTATION })
    expect(out.text).toBe('AEM recall · Acme')
    expect(w.calls).toContainEqual(['aem', 'recall', 'acme'])
  })

  test('stage time ticks on the status line', async ($, on) => {
    const w = floor(on, active())
    await $.session.start(START)
    await w.clock.advance(30 * 60_000)
    expect(w.statuses.at(-1)).toBe('AEM · MergeToMaster · P1 - Test · G1 · 0:35')
  })

  test('/aem use checks with the CLI, then pins the project to this session', async ($, on) => {
    const used = { ok: true, client: 'joel', project: 'P1', project_dir: '/Volumes/T7/P1', fps: { num: 24000, den: 1001, source: 'frame.md' } }
    const w = floor(on, active({ use: { json: used } }))
    await $.session.start(START)
    expect(w.envs.every(e => e?.AEM_PROJECT === undefined)).toBe(true) // no pin yet: the folder decides
    const out = await $.command.run({ command: 'aem', args: 'use joel/P1 - Frontend Design', origin: COMPOSER, presentation: PRESENTATION })
    expect(w.calls).toContainEqual(['aem', 'use', 'joel/P1 - Frontend Design', '--json'])
    expect(out.text).toContain('Pinned joel/P1 to this session')
    expect(out.text).toContain('fps 24000/1001 (from frame.md)')
    // From now on every aem call carries the pin, and says it is a pin.
    const before = w.calls.length
    await $.tool.call({ tool: 'Read', file_path: '/x' })
    const after = w.envs.slice(before)
    expect(after.length).toBeGreaterThan(0)
    expect(after.every(e => e?.AEM_PROJECT === 'joel/P1' && e?.AEM_PROJECT_SOURCE === 'session-pin')).toBe(true)
  })

  test('/aem use that the CLI refuses pins nothing', async ($, on) => {
    const w = floor(on, active({ use: { code: 2, json: { ok: false, error: 'refusing project joel/P9: under /tmp' } } }))
    await $.session.start(START)
    const out = await $.command.run({ command: 'aem', args: 'use joel/P9', origin: COMPOSER, presentation: PRESENTATION })
    expect(out.text).toContain('Not pinned: refusing project joel/P9')
    const before = w.calls.length
    await $.tool.call({ tool: 'Read', file_path: '/x' })
    expect(w.envs.slice(before).every(e => e?.AEM_PROJECT === undefined)).toBe(true)
  })

  test('/aem use --clear drops the pin without any CLI call; other calls go back to the folder', async ($, on) => {
    const used = { ok: true, client: 'joel', project: 'P2', project_dir: '/Volumes/T7/P2', fps: { num: 24000, den: 1001, source: 'aem.project.json' } }
    const w = floor(on, active({ use: { json: used } }))
    await $.session.start(START)
    await $.command.run({ command: 'aem', args: 'use joel/P2', origin: COMPOSER, presentation: PRESENTATION })
    const before = w.calls.length
    const out = await $.command.run({ command: 'aem', args: 'use --clear', origin: COMPOSER, presentation: PRESENTATION })
    expect(out.text).toContain('Session pin joel/P2 dropped')
    expect(w.calls.slice(before).some(c => c[1] === 'use')).toBe(false) // the plugin owns the pin: nothing to tell the CLI
    expect(w.envs.slice(before).every(e => e?.AEM_PROJECT === undefined)).toBe(true)
  })

  test('/aem use --clear from a plugin or a model is refused', async ($, on) => {
    const w = floor(on, active())
    await $.session.start(START)
    const out = await $.command.run({ command: 'aem', args: 'use --clear', origin: { kind: 'plugin', name: 'other' }, presentation: PRESENTATION })
    expect(out.text).toContain('can only be typed by the operator')
    expect(w.calls.some(c => c[1] === 'use')).toBe(false)
  })

  test('/aem use from a plugin is refused and runs nothing', async ($, on) => {
    const w = floor(on, active())
    await $.session.start(START)
    const before = w.calls.length
    const out = await $.command.run({ command: 'aem', args: 'use joel/P2', origin: { kind: 'plugin', name: 'other' }, presentation: PRESENTATION })
    expect(out.text).toContain('can only be typed by the operator')
    expect(w.calls.slice(before).some(c => c[1] === 'use')).toBe(false)
  })

  test('/aem status prints the CLI text; unknown subcommand prints help', async ($, on) => {
    floor(on, active({ status: { text: 'AEM · MergeToMaster · P1 - Test · G1 · 0:00:05' } }))
    await $.session.start(START)
    const out = await $.command.run({ command: 'aem', args: 'status', origin: COMPOSER, presentation: PRESENTATION })
    expect(out.text).toBe('AEM · MergeToMaster · P1 - Test · G1 · 0:00:05')
    const help = await $.command.run({ command: 'aem', args: 'frobnicate', origin: COMPOSER, presentation: PRESENTATION })
    expect(help.text).toContain('/aem use <client>/<project>')
    expect(help.text).toContain('/aem use --clear')
  })

  test('aem missing: one clear toast', async ($, on) => {
    const w = floor(on, INACTIVE, { cannotStart: true })
    await $.session.start(START)
    expect(w.calls.map(c => c[0])).toEqual(expect.arrayContaining(['aem', '/Users/test/.local/bin/aem']))
    expect(w.toasts).toHaveLength(1)
    expect(w.toasts[0]).toContain('aem could not start')
    expect(w.statuses.at(-1)?.startsWith('AEM · aem could not start')).toBe(true)
  })
})
