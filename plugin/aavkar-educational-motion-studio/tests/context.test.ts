import { describe, expect, test } from 'claude-code/testing'

import { COMPOSER, INACTIVE, PRESENTATION, START, active, floor } from './fake-aem'

const COMPOSE = { model: 'm', promptModel: 'm', surfaces: ['terminal'], tools: [], outputStyle: null, traits: [] } as const

describe('context', () => {
  test('no active project: toast, status line and the inactive prompt section', async ($, on) => {
    const w = floor(on, INACTIVE)
    on('prompt.compose', () => ({ sections: [{ id: 'intro', text: 'engine intro', scope: 'shared' as const }] }))
    await $.session.start(START)
    expect(w.toasts.some(t => t.includes('no active project'))).toBe(true)
    expect(w.toasts.some(t => t.includes('/aem use'))).toBe(true)
    expect(w.statuses.at(-1)).toBe('AEM · no active project · /aem use <client>/<project>')
    expect(w.calls.some(c => c[1] === 'drift')).toBe(false)
    const composed = await $.prompt.compose(COMPOSE)
    expect(composed.sections.at(-1)).toEqual({ id: 'aavkar-educational-motion-studio:context', text: 'AEM inactive text', scope: 'session' })
  })

  test('active project: status line, prompt section from aem context, drift toasts', async ($, on) => {
    const w = floor(on, active({
      drift: { code: 1, json: { ok: false, findings: [
        { check: 'skill', file: 'SKILL.md', problem: 'installed copy differs from the master' },
        { check: 'text-export', file: 'text/Motion.md', problem: 'page changed since the export' },
      ] } },
    }))
    on('prompt.compose', () => ({ sections: [{ id: 'intro', text: 'engine intro', scope: 'shared' as const }] }))
    await $.session.start(START)
    expect(w.statuses.at(-1)).toBe('AEM · MergeToMaster · P1 - Test · G1 · 0:05')
    expect(w.toasts).toContain('AEM drift [skill] SKILL.md installed copy differs from the master')
    expect(w.toasts).toContain('AEM drift [text-export] text/Motion.md page changed since the export')
    expect(w.calls.map(c => c[1])).toEqual(expect.arrayContaining(['status', 'context', 'drift']))
    expect(w.calls.every(c => c.at(-1) === '--json')).toBe(true)
    const composed = await $.prompt.compose(COMPOSE)
    expect(composed.sections[0]?.id).toBe('intro')
    expect(composed.sections.at(-1)).toEqual({ id: 'aavkar-educational-motion-studio:context', text: 'CONTEXT FOR JOEL P1', scope: 'session' })
    // A second render does not add the section twice.
    const again = await $.prompt.compose(COMPOSE)
    expect(again.sections.filter(s => s.id === 'aavkar-educational-motion-studio:context')).toHaveLength(1)
  })

  test('stage time ticks on the status line', async ($, on) => {
    const w = floor(on, active())
    await $.session.start(START)
    await w.clock.advance(30 * 60_000)
    expect(w.statuses.at(-1)).toBe('AEM · MergeToMaster · P1 - Test · G1 · 0:35')
  })

  test('/aem use runs the CLI with the project name joined and refreshes', async ($, on) => {
    const w = floor(on, active({ use: { text: 'Active: joel/P1 - Frontend Design' } }))
    await $.session.start(START)
    const out = await $.command.run({ command: 'aem', args: 'use joel/P1 - Frontend Design --fps 24000/1001', origin: COMPOSER, presentation: PRESENTATION })
    expect(out.text).toBe('Active: joel/P1 - Frontend Design')
    expect(w.calls).toContainEqual(['aem', 'use', 'joel/P1 - Frontend Design', '--fps', '24000/1001'])
    expect(w.toasts.at(-1)?.startsWith('AEM · MergeToMaster')).toBe(true)
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
