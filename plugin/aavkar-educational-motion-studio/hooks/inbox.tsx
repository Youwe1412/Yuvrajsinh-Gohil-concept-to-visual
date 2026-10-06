// Feature "review inbox" (off unless the reviewInbox setting is on): /inbox opens a pane listing
// what waits on the operator. `aem inbox` decides what is listed and hands each item the exact aem
// commands its buttons run (approve, reject, allow, inbox accept/dismiss, with --label so the
// ruling also lands in the client's labelled cases); the pane only runs them. Reject asks for a
// reason first.
import type { CommandRunInput, CommandRunResult, ElementTable, PluginOptions } from 'claude-code'

import type { AemInbox, AemInboxAction, AemInboxItem } from '../types'
import { cli, errorOf, isOperator, refresh, refusedText } from './aem'
import type { CommandSpecLite, Io } from './aem'

export const INBOX_PANE = 'aem-inbox'
export const INBOX_TITLE = 'AEM inbox'
export const INBOX_COMMANDS: readonly CommandSpecLite[] = [
  { name: 'inbox', description: 'AEM: open the review inbox (what waits on you, with approve and reject)' },
]
export const EMPTY_INBOX: AemInbox = { items: [], summary: '', reasonFor: null, message: null, busy: false }

// The only commands an inbox button may run: the operator's own.
const RUNNABLE: ReadonlySet<string> = new Set(['approve', 'reject', 'allow', 'inbox'])

export function inboxOn(options: PluginOptions): boolean {
  return options.reviewInbox === true
}

export async function loadInbox(io: Io, options: PluginOptions): Promise<string> {
  const r = await cli(io, options, ['inbox'])
  if (r.code !== 0) {
    const msg = `aem inbox failed: ${errorOf(r)}`
    await io.patchInbox(b => ({ ...b, items: [], summary: msg, busy: false }))
    return msg
  }
  const items = (r.data.items ?? []) as AemInboxItem[]
  const summary = String(r.data.summary ?? '')
  await io.patchInbox(b => ({ ...b, items, summary, busy: false,
    reasonFor: b.reasonFor && items.some(i => i.id === b.reasonFor?.id) ? b.reasonFor : null }))
  return summary
}

export async function inboxCommand(io: Io, options: PluginOptions, e: CommandRunInput): Promise<CommandRunResult> {
  if (!isOperator(e.origin)) return { text: refusedText(e.command, e.origin) }
  if (!(await io.getView()).active) return { text: 'AEM: no project resolved here. Start the session in the project folder, or run /aem use <client>/<project> first.' }
  const summary = await loadInbox(io, options)
  await io.openPane(INBOX_PANE, INBOX_TITLE)
  return { text: `AEM inbox: ${summary}` }
}

// A button: run its command; a reason-taking one first asks for the reason.
export async function pressAction(io: Io, options: PluginOptions, item: AemInboxItem, action: AemInboxAction): Promise<void> {
  if (action.needs_reason) {
    await io.patchInbox(b => ({ ...b, reasonFor: { id: item.id, label: action.label }, message: null }))
    return
  }
  await runAction(io, options, item, action, undefined)
}

export async function submitReason(io: Io, options: PluginOptions, reason: string): Promise<void> {
  const b = await io.getInbox()
  const want = b.reasonFor
  const item = want && b.items.find(i => i.id === want.id)
  const action = item?.actions.find(a => a.label === want?.label)
  if (!item || !action) return
  if (!reason.trim()) {
    await io.patchInbox(x => ({ ...x, message: 'A reason is needed to reject.' }))
    return
  }
  await runAction(io, options, item, action, reason.trim())
}

export async function cancelReason(io: Io): Promise<void> {
  await io.patchInbox(b => ({ ...b, reasonFor: null, message: null }))
}

async function runAction(io: Io, options: PluginOptions, item: AemInboxItem, action: AemInboxAction, reason: string | undefined): Promise<void> {
  const [first] = action.argv
  if (!first || !RUNNABLE.has(first)) {
    io.toast(`AEM inbox: refused to run "${action.argv.join(' ')}"`, 8000)
    return
  }
  await io.patchInbox(b => ({ ...b, busy: true }))
  const argv = reason === undefined ? action.argv : [...action.argv, '--reason', reason]
  const r = await cli(io, options, argv)
  const done = r.code === 0
  const message = done ? `${action.label}: ${item.title}` : `${action.label} failed: ${errorOf(r)}`
  io.toast(`AEM inbox: ${message}`, 8000)
  await io.patchInbox(b => ({ ...b, reasonFor: done ? null : b.reasonFor, message }))
  await loadInbox(io, options)
  await refresh(io, options)
}

export type InboxHandlers = {
  press: (item: AemInboxItem, action: AemInboxAction) => void
  reason: (text: string) => void
  cancel: () => void
  reload: () => void
}

const KIND_NAMES: Record<string, string> = {
  plan_row: 'Plan row', still: 'Still', render: 'Render', override: 'Guard denial', client_comment: 'Client comment',
}

// The mobile app draws no text field (its table has no Input), so there Reject only says where to go.
export function drawInbox(els: ElementTable, surface: string, b: AemInbox, on: InboxHandlers, rows: number) {
  const { Box, Text, Button } = els
  const asking = b.reasonFor
  const room = Math.max(1, Math.floor((rows - 4) / 3))
  return (
    <Box flexDirection="column" gap={1}>
      <Box flexDirection="row" gap={2}>
        <Text bold>{b.summary || 'Loading…'}</Text>
        <Button key="aem-inbox-reload" label="Reload" dimColor onPress={() => on.reload()} />
      </Box>
      {b.message !== null && <Text dimColor>{b.message}</Text>}
      {asking !== null && (
        <Box flexDirection="column">
          <Text>Reason for "{asking.label}" on {asking.id}:</Text>
          {surface !== 'mobile' && 'Input' in els ? (
            <Box flexDirection="row" gap={1}>
              <els.Input key="aem-inbox-reason" placeholder="why (kept with the ruling)" submitLabel="reject"
                autoFocus onSubmit={text => on.reason(text)} />
              <Button key="aem-inbox-cancel" label="Cancel" onPress={() => on.cancel()} />
            </Box>
          ) : (
            <Text dimColor>This surface has no text field: reject from a terminal or desktop with /reject.</Text>
          )}
        </Box>
      )}
      {b.items.slice(0, room).map(item => (
        <Box key={`row-${item.id}`} flexDirection="column">
          <Text>
            <Text bold>{KIND_NAMES[item.kind] ?? item.kind}</Text>
            {item.gate ? ` · ${item.gate}` : ''} · {item.title}
            {item.note ? ` (${item.note})` : ''}
          </Text>
          {item.detail !== null && <Text dimColor wrap="truncate-end">{item.detail}</Text>}
          <Box flexDirection="row" gap={1}>
            {item.actions.map(a => (
              <Button key={`${item.id}::${a.label}`} label={a.label} variant={a.needs_reason ? 'secondary' : 'primary'}
                onPress={() => on.press(item, a)} />
            ))}
          </Box>
        </Box>
      ))}
      {b.items.length > room && <Text dimColor>…and {b.items.length - room} more (aem inbox lists all)</Text>}
    </Box>
  )
}
