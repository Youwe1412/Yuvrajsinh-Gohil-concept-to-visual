import { describe, expect, test } from 'claude-code/testing'

import { COMPOSER, PRESENTATION, START, active, floor } from './fake-aem'

// The slash commands that write the record: only the operator types them, and each runs its aem command
// with a one-time nonce (operator.test.ts), which is how the CLI knows the operator ran it.
const run = (cmdRun: (e: never) => Promise<{ text?: string }>, command: string, args: string, origin: object = COMPOSER) =>
  cmdRun({ command, args, origin, presentation: PRESENTATION } as never)

describe('record commands', () => {
  test('/approve, /reject, /client-said, /accept-video and /accept-edit build the CLI call exactly', async ($, on) => {
    const w = floor(on, active(), { selection: 'I really liked\n  the "first" one' })
    await $.session.start(START)
    const cmd = (c: string, a: string) => run($.command.run as never, c, a)
    await cmd('approve', 'fd_S01_next-token G4')
    await cmd('approve', 'fd_S01_next-token renders/v09/fd_S01_next-token_v09.mp4')
    await cmd('approve', 'fd_S01 "renders/v09/fd S01.mp4" G6')
    await cmd('reject', 'shot  the caption repeats   the demo')
    await cmd('client-said', 'video --source Frame.io Could you leave the grade?\nIt is "a bit more natural"')
    await cmd('client-said', 'channel')
    await cmd('client-said', '--about channel --source "WhatsApp, 5 Oct 2026" I really liked what you did')
    await cmd('client-said', '--about fd_S04_50ms --ruling change --source Frame.io take the flash out')
    await cmd('accept-video', 'v08 Frame.io, 14 Sep 2026')
    await cmd('accept-video', 'latest --before "Done/P2 - Claude Code Done.mov" WhatsApp, 19 Oct 2026')
    await cmd('accept-edit', '--file events.jsonl I added that line')
    const ran = w.calls.filter(c => c.at(-1) !== '--json').map(c => c.slice(1))
    expect(ran).toEqual([
      ['approve', 'fd_S01_next-token', '--gate', 'G4'],
      ['approve', 'fd_S01_next-token', 'renders/v09/fd_S01_next-token_v09.mp4'],
      ['approve', 'fd_S01', 'renders/v09/fd S01.mp4', '--gate', 'G6'],
      ['reject', 'shot', '--reason', 'the caption repeats   the demo'],
      ['client-said', '--scope', 'video', '--source', 'Frame.io'],
      ['client-said', '--scope', 'channel', '--source', 'pasted in Claude Code (the selected text)'],
      ['client-said', '--source', 'WhatsApp, 5 Oct 2026', '--about', 'channel'],
      ['client-said', '--source', 'Frame.io', '--about', 'fd_S04_50ms', '--ruling', 'change'],
      ['accept-video', 'v08', '--source', 'Frame.io, 14 Sep 2026'],
      ['accept-video', 'latest', '--source', 'WhatsApp, 19 Oct 2026', '--before', 'Done/P2 - Claude Code Done.mov'],
      ['accept-edit', '--file', 'events.jsonl', '--reason', 'I added that line'],
    ])
    const stdinOf = (i: number) => w.stdins[w.calls.indexOf(w.calls.filter(c => c.at(-1) !== '--json')[i] as string[])]
    expect(stdinOf(4)).toBe('Could you leave the grade?\nIt is "a bit more natural"')
    expect(stdinOf(5)).toBe('I really liked\n  the "first" one')
    expect(stdinOf(6)).toBe('I really liked what you did')
    expect(stdinOf(7)).toBe('take the flash out')
    expect(w.toasts.some(t => t.startsWith('AEM approve:'))).toBe(true)
  })

  test('the commands refuse anyone but the operator and run nothing', async ($, on) => {
    const w = floor(on, active())
    await $.session.start(START)
    const before = w.calls.length
    for (const [c, a] of [['approve', 'x G4'], ['reject', 'x no'], ['client-said', 'video hi'], ['accept-video', 'v08 Frame.io'], ['accept-edit', 'ok']]) {
      const out = await run($.command.run as never, c as string, a as string, { kind: 'plugin', name: 'other' })
      expect(out.text).toContain('can only be typed by the operator')
    }
    expect(w.calls.slice(before).filter(c => c.at(-1) !== '--json')).toEqual([])
  })

  test('there is no /allow any more', async ($, on) => {
    const w = floor(on, active())
    await $.session.start(START)
    expect(w.commands).toEqual(expect.arrayContaining(['aem', 'stage', 'approve', 'reject', 'client-said', 'accept-video', 'accept-edit', 'report']))
    expect(w.commands).not.toContain('allow')
  })

  test('usage text for missing arguments', async ($, on) => {
    floor(on, active())
    await $.session.start(START)
    expect((await run($.command.run as never, 'approve', '')).text).toContain('Usage')
    expect((await run($.command.run as never, 'reject', 'onlyitem')).text).toContain('Usage')
    expect((await run($.command.run as never, 'client-said', 'video')).text).toContain('Usage')
    expect((await run($.command.run as never, 'accept-video', 'v08')).text).toContain('Usage')
  })
})
