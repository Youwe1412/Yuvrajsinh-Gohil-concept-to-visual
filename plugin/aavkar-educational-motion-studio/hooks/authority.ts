// Feature "authority" (0.9.0): the operator's own message stands for its turn.
//
// AEM allows whatever the operator asks for in chat; the guard and the operator-only commands exist only to
// stop the agent acting on its own authority. So when a turn begins with a prompt from an operator origin
// (the composer, the Remote Control bridge or the SDK host; never a plugin, a peer, a schedule or the agent),
// the plugin asks `aem authority open` for a turn authority, with the prompt's exact text, and puts the nonce
// it returns in AEM_OPERATOR_TURN for everything the turn starts. The CLI records the prompt
// (`operator_prompt` in events.jsonl), lets the guard allow and log what it would have denied, and accepts
// operator commands on it, each recorded via "chat". When the turn ends, `aem authority close` ends it.
// A turn that no operator prompt started has no authority, and AEM applies unchanged.
import type { PluginOptions, PromptSubmitInput, TurnCompleteInput } from 'claude-code'

import type { AemAuthority } from '../types'
import { cli, errorOf, isOperator } from './aem'
import type { Io } from './aem'

export const EMPTY_AUTHORITY: AemAuthority = { active: false, promptId: null, turnId: null, excerpt: null, usesSeen: 0, pending: [] }

type Opened = { nonce?: string; prompt_id?: string; excerpt?: string }
type Use = { n: number; action: string; excerpt: string }

async function open(io: Io, options: PluginOptions, text: string, origin: string, turnId: string, promptId: string | null): Promise<string | null> {
  const session = await io.sessionId()
  const argv = ['authority', 'open', '--session', session, '--turn', turnId, '--origin', origin]
  let r = await cli(io, options, promptId ? [...argv, '--prompt-id', promptId] : argv, { stdin: text })
  // A queued prompt whose first turn ran where no project resolved has no event to reuse: open it afresh.
  if (r.code !== 0 && promptId) r = await cli(io, options, argv, { stdin: text })
  const d = r.data as Opened
  if (r.code !== 0 || typeof d.nonce !== 'string') {
    io.toast(`AEM could not open your message's authority for this turn, so the usual checks apply: ${errorOf(r)}`, 8000)
    return null
  }
  await io.setTurnEnv(d.nonce)
  await io.patchAuthority(a => ({ ...a, active: true, promptId: d.prompt_id ?? null, turnId, excerpt: d.excerpt ?? null, usesSeen: 0 }))
  return d.prompt_id ?? null
}

// The turn ended (or a turn the operator did not start is beginning): every authority of this session ends.
export async function closeAuthority(io: Io, options: PluginOptions): Promise<void> {
  const a = await io.getAuthority()
  await io.setTurnEnv(undefined)
  if (!a.active) return
  await io.patchAuthority(x => ({ ...x, active: false, promptId: null, turnId: null, excerpt: null, usesSeen: 0 }))
  await cli(io, options, ['authority', 'close', '--session', await io.sessionId()])
}

// Runs before the prompt enters (`next`), because a prompt typed while the session is idle starts its turn
// inside `next`, and that turn's first tool call must already carry the authority.
export async function authorityPrompt(io: Io, options: PluginOptions, e: PromptSubmitInput): Promise<void> {
  if (!isOperator(e.origin)) {
    // Delivered into a running turn (a task notification, a peer): that turn keeps what it had. Starting a
    // turn of its own: no operator started it, so nothing of an earlier turn may carry over.
    if (e.turnId === undefined) await closeAuthority(io, options)
    return
  }
  if (!e.text.trim()) return
  if (e.turnId !== undefined) {
    // Typed during a running turn: it may be delivered into that turn, so it stands for it now; it may instead
    // wait and start the next turn, so it is kept to stand for that one too if its text starts it.
    const promptId = await open(io, options, e.text, e.origin.kind, e.turnId, null)
    await io.patchAuthority(a => ({ ...a, pending: [...a.pending, { text: e.text, origin: e.origin.kind, idle: false, promptId }] }))
    return
  }
  await closeAuthority(io, options)
  await io.patchAuthority(a => ({ ...a, pending: [{ text: e.text, origin: e.origin.kind, idle: true, promptId: null }] }))
}

// Another plugin or a settings hook dropped the prompt: it starts no turn.
export async function authorityDropped(io: Io): Promise<void> {
  await io.patchAuthority(a => ({ ...a, pending: a.pending.filter(p => !p.idle) }))
}

// A fresh load with no authority open: nothing a crashed or earlier session left may stand.
export async function authorityStart(io: Io): Promise<void> {
  if (!(await io.getAuthority()).active) await io.setTurnEnv(undefined)
}

export async function authorityTurnStart(io: Io, options: PluginOptions, turnId: string, text: string): Promise<void> {
  const { pending } = await io.getAuthority()
  if (pending.length === 0) return
  await io.patchAuthority(a => ({ ...a, pending: [] }))
  const p = pending.find(x => x.text === text) ?? pending.find(x => x.idle)
  if (p) await open(io, options, p.text, p.origin, turnId, p.idle ? null : p.promptId)
}

export async function authorityTurnComplete(io: Io, options: PluginOptions, e: TurnCompleteInput): Promise<void> {
  if (e.agentId !== undefined) return // a subagent's turn: the operator's turn is still running
  await closeAuthority(io, options)
}

// After a shell call in an operator turn: every operator command that succeeded on the authority is toasted,
// so the operator sees each thing their message caused, as it happens.
export async function authorityAfterTool(io: Io, options: PluginOptions, tool: string): Promise<void> {
  if (tool !== 'Bash') return
  const a = await io.getAuthority()
  if (!a.active) return
  const r = await cli(io, options, ['authority', 'uses', '--after', String(a.usesSeen)])
  const uses = ((r.data as { uses?: Use[] }).uses ?? []).filter(u => typeof u.n === 'number')
  if (uses.length === 0) return
  for (const u of uses) io.toast(`${u.action} via chat: '${u.excerpt}'`, 8000)
  const last = Math.max(...uses.map(u => u.n))
  await io.patchAuthority(x => ({ ...x, usesSeen: Math.max(x.usesSeen, last) }))
}
