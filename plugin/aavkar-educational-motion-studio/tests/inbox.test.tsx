import { describe, expect, test } from 'claude-code/testing'

import { COMPOSER, PRESENTATION, START, active, floor } from './fake-aem'
import type { Reply, Router } from './fake-aem'

const PLUGIN = 'aavkar-educational-motion-studio'
const ON = { options: { reviewInbox: true } }

const ITEMS = [
  { id: 'render:fd_S01_next-token', kind: 'render', item: 'fd_S01_next-token', gate: 'G4', title: 'renders/fd_S01_next-token_v08.mp4',
    detail: 'check passed', actions: [
      { label: 'Approve', argv: ['approve', 'fd_S01_next-token', '/p/renders/fd_S01_next-token_v08.mp4', '--gate', 'G4', '--label'], needs_reason: false },
      { label: 'Reject', argv: ['reject', 'fd_S01_next-token', '--path', '/p/renders/fd_S01_next-token_v08.mp4', '--gate', 'G4', '--label'], needs_reason: true },
    ] },
  { id: 'comment:2026-10-06-labelled-cases.draft.jsonl#1', kind: 'client_comment', item: 'teach-opening', gate: null,
    title: 'teach-opening: Joel Belton said', detail: 'Can we lose the caption?', actions: [
      { label: 'Change', argv: ['inbox', 'accept', 'comment:2026-10-06-labelled-cases.draft.jsonl#1', '--ruling', 'change', '--label'], needs_reason: false },
      { label: 'Reject', argv: ['inbox', 'dismiss', 'comment:2026-10-06-labelled-cases.draft.jsonl#1', '--label'], needs_reason: true },
    ] },
  { id: 'evil', kind: 'render', item: 'x', gate: 'G4', title: 'bad argv', detail: null, actions: [
      { label: 'Approve', argv: ['use', 'other/P9'], needs_reason: false },
    ] },
]

const inboxReply: Reply = { json: { ok: true, items: ITEMS, summary: '3 waiting: 2 renders, 1 client comment' } }
const router: Router = (args, stdin) => (args[0] === 'inbox' && args.length === 1 ? inboxReply : active()(args, stdin))
const PANE_PROPS = { title: 'AEM inbox', isFocused: true, bodyColumns: 100, placement: 'inline', scroll: { offset: 0, bodyRows: 30 }, view: {} } as const

const run = (calls: string[][], from: number) => calls.slice(from).map(c => c.slice(1).filter(a => a !== '--json'))

describe('review inbox', () => {
  test('off by default: no /inbox command and nothing drawn', async ($, on) => {
    const w = floor(on, router)
    await $.session.start(START)
    expect(w.commands).not.toContain('inbox')
    expect(w.commands).toContain('approve')
  })

  test('/inbox lists from aem inbox and opens the pane; only the operator may', ON, async ($, on) => {
    const w = floor(on, router)
    await $.session.start(START)
    expect(w.commands).toContain('inbox')
    const r = await $.command.run({ command: 'inbox', args: '', origin: COMPOSER, presentation: PRESENTATION } as never)
    expect(r.text).toBe('AEM inbox: 3 waiting: 2 renders, 1 client comment')
    expect(w.panes).toEqual(['aem-inbox'])
    const before = w.calls.length
    const refused = await $.command.run({ command: 'inbox', args: '', origin: { kind: 'plugin', plugin: 'x' }, presentation: PRESENTATION } as never)
    expect(refused.text).toContain('can only be typed by the operator')
    expect(w.calls.length).toBe(before)
  })

  for (const surface of ['terminal', 'desktop'] as const) {
    test(`${surface}: Approve runs the item's command; Reject asks for a reason, then runs it`, ON, async ($, on) => {
      const w = floor(on, router)
      await $.session.start(START)
      await $.command.run({ command: 'inbox', args: '', origin: COMPOSER, presentation: PRESENTATION } as never)
      const ui = await $.ui.mount({ plugin: PLUGIN, surface, component: 'Pane', requestId: 'aem-inbox', props: PANE_PROPS })
      expect((await ui.find({ type: 'Text', text: /3 waiting/ }))).toBeDefined()
      expect((await ui.find({ type: 'Text', text: /Can we lose the caption\?/ }))).toBeDefined()

      let from = w.calls.length
      await ui.press({ key: 'render:fd_S01_next-token::Approve' })
      const ran = run(w.calls, from)
      expect(ran[0]).toEqual(['approve', 'fd_S01_next-token', '/p/renders/fd_S01_next-token_v08.mp4', '--gate', 'G4', '--label'])
      expect(ran.slice(1).map(c => c[0])).toEqual(expect.arrayContaining(['inbox', 'status']))
      expect(w.toasts.at(-1)).toBe('AEM inbox: Approve: renders/fd_S01_next-token_v08.mp4')

      from = w.calls.length
      await ui.press({ key: 'comment:2026-10-06-labelled-cases.draft.jsonl#1::Reject' })
      expect(w.calls.length).toBe(from)
      expect(await ui.find({ key: 'aem-inbox-reason' })).toBeDefined()
      await ui.input({ key: 'aem-inbox-reason', text: '   ' })
      expect(w.calls.length).toBe(from)
      expect(await ui.find({ type: 'Text', text: /A reason is needed/ })).toBeDefined()
      await ui.input({ key: 'aem-inbox-reason', text: 'mapped to the wrong shot' })
      expect(run(w.calls, from)[0]).toEqual(['inbox', 'dismiss', 'comment:2026-10-06-labelled-cases.draft.jsonl#1', '--label',
        '--reason', 'mapped to the wrong shot'])
      expect(await ui.find({ key: 'aem-inbox-reason' })).toBeUndefined()

      // Cancel closes the reason field and runs nothing.
      await ui.press({ key: 'render:fd_S01_next-token::Reject' })
      from = w.calls.length
      await ui.press({ key: 'aem-inbox-cancel' })
      expect(w.calls.length).toBe(from)
      expect(await ui.find({ key: 'aem-inbox-reason' })).toBeUndefined()
      await ui.unmount()
    })
  }

  test('a button whose command is not an approval command is refused', ON, async ($, on) => {
    const w = floor(on, router)
    await $.session.start(START)
    await $.command.run({ command: 'inbox', args: '', origin: COMPOSER, presentation: PRESENTATION } as never)
    const ui = await $.ui.mount({ plugin: PLUGIN, surface: 'terminal', component: 'Pane', requestId: 'aem-inbox', props: PANE_PROPS })
    const from = w.calls.length
    await ui.press({ key: 'evil::Approve' })
    expect(w.calls.length).toBe(from)
    expect(w.toasts.at(-1)).toBe('AEM inbox: refused to run "use other/P9"')
  })

  test('mobile has no text field: Reject says where to reject instead', ON, async ($, on) => {
    const w = floor(on, router)
    await $.session.start(START)
    await $.command.run({ command: 'inbox', args: '', origin: COMPOSER, presentation: PRESENTATION } as never)
    const ui = await $.ui.mount({ plugin: PLUGIN, surface: 'mobile', component: 'Pane', requestId: 'aem-inbox', props: PANE_PROPS })
    await ui.press({ key: 'render:fd_S01_next-token::Reject' })
    expect(await ui.find({ type: 'Text', text: /no text field/ })).toBeDefined()
    expect(w.calls.some(c => c[1] === 'reject')).toBe(false)
  })
})
