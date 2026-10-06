// Feature "guard": every file and shell tool call is put to `aem guard`, which decides; a
// denial tells the agent why and how the operator can approve or override. Commands only the
// operator can type: /approve, /reject, /client-said, /allow.
import type { CommandRunInput, CommandRunResult, PluginOptions } from 'claude-code'

import { cli, errorOf, isOperator, leading, refresh, refusedText } from './aem'
import type { CommandSpecLite, Io } from './aem'

// Tools whose arguments name files or run commands. Others are not file access.
export const GUARDED_TOOLS: ReadonlySet<string> = new Set(['Bash', 'Read', 'Write', 'Edit', 'MultiEdit', 'NotebookEdit', 'Glob', 'Grep', 'LS'])

export const GUARD_COMMANDS: readonly CommandSpecLite[] = [
  { name: 'approve', description: 'AEM: approve the exact render of an item (its last checked render, the open gate)', argumentHint: '<item> [path] [gate]' },
  { name: 'reject', description: 'AEM: reject an item, with a reason', argumentHint: '<item> <reason>' },
  { name: 'client-said', description: "AEM: record the client's exact words in their decisions file", argumentHint: '<channel|video|instance> [--source S] [--item SHOT] <their words, or select them first>' },
  { name: 'allow', description: 'AEM: let one blocked call through (add --standing to keep it)', argumentHint: '<rule-or-command> <reason> [--standing]' },
]

export type GuardVerdict = { deny: string } | { allowNote?: string }

type Decision = { decision?: string; rule?: string; rule_name?: string; reason?: string; how?: string; allow_id?: string; once?: boolean; overridden?: { rule?: string } }

export async function guardCall(io: Io, options: PluginOptions, tool: string, args: Record<string, unknown>): Promise<GuardVerdict> {
  if (!GUARDED_TOOLS.has(tool)) return {}
  // With no project active only AEM-G04 (operator-only aem commands) applies, and only to Bash.
  if (tool !== 'Bash' && !(await io.getView()).active) return {}
  const { tool_use_id: _id, agentId: _agent, tool: _tool, ...input } = args
  const r = await cli(io, options, ['guard'], { stdin: JSON.stringify({ tool, input, cwd: await io.cwd() }), timeoutMs: 60_000 })
  if (r.code === 127) {
    io.toast(`AEM guard could not run, so this call was not checked: ${errorOf(r)}`, 8000)
    return {}
  }
  const d = r.data as Decision
  if (d.decision === 'deny') {
    const msg = `AEM denied this call (${d.rule}, ${d.rule_name}): ${d.reason} How to proceed: ${d.how} ` +
      'Do not try another route to the same effect; tell the operator what was denied.'
    io.toast(`AEM denied ${tool}: ${d.rule} ${d.rule_name}`, 8000)
    return { deny: msg }
  }
  if (d.decision === 'allow' && d.allow_id) {
    const note = `AEM: ${d.once ? 'one-time' : 'standing'} /allow ${d.allow_id} let a ${d.overridden?.rule ?? ''} call through`
    io.toast(note, 8000)
    return { allowNote: note }
  }
  if (d.decision !== 'allow') io.toast(`AEM guard gave no decision: ${errorOf(r)}`, 8000)
  return {}
}

async function run(io: Io, options: PluginOptions, argv: string[], stdin?: string): Promise<CommandRunResult> {
  const r = await cli(io, options, argv, { json: false, stdin })
  await refresh(io, options)
  const first = r.text.split('\n')[0] ?? ''
  io.toast(`AEM ${argv[0]}: ${r.code === 0 ? first : `failed: ${first}`}`, 8000)
  return { text: r.text || `aem ${argv[0]} exited ${r.code}` }
}

export async function guardCommand(io: Io, options: PluginOptions, e: CommandRunInput): Promise<CommandRunResult> {
  if (!isOperator(e.origin)) return { text: refusedText(e.command, e.origin) }
  if (e.command === 'approve') {
    const a = leading(e.args, { words: 3 })
    const [item, ...more] = a.words
    if (!item) return { text: 'Usage: /approve <item> [path] [gate]' }
    const gate = more.find(w => /^G\d+$/i.test(w))
    const path = more.find(w => w !== gate)
    return run(io, options, ['approve', item, ...(path ? [path] : []), ...(gate ? ['--gate', gate] : [])])
  }
  if (e.command === 'reject') {
    const a = leading(e.args, { words: 1, valueFlags: ['gate'] })
    const item = a.words[0]
    if (!item || !a.rest.trim()) return { text: 'Usage: /reject <item> <reason>' }
    const gate = typeof a.flags.gate === 'string' ? ['--gate', a.flags.gate] : []
    return run(io, options, ['reject', item, '--reason', a.rest.trim(), ...gate])
  }
  if (e.command === 'client-said') {
    const a = leading(e.args, { words: 1, valueFlags: ['source', 'item'] })
    const scope = a.words[0]
    let quote = a.rest
    let from = 'typed with the command'
    if (!quote.trim()) {
      quote = (await io.selection()) ?? ''
      from = 'the selected text'
    }
    if (!scope || !quote.trim()) {
      return { text: 'Usage: /client-said <channel|video|instance> [--source S] [--item SHOT] <their exact words>\n(or select their words in the transcript first)' }
    }
    const source = typeof a.flags.source === 'string' ? a.flags.source : `pasted in Claude Code (${from})`
    const item = typeof a.flags.item === 'string' ? ['--item', a.flags.item] : []
    return run(io, options, ['client-said', '--scope', scope, '--source', source, ...item], quote)
  }
  if (e.command === 'allow') {
    const a = leading(e.args, { words: 1, boolFlags: ['standing', 'once'] })
    const target = a.words[0]
    let reason = a.rest.trim()
    let standing = a.flags.standing === true
    if (/\s--standing$/.test(` ${reason}`)) {
      standing = true
      reason = reason.replace(/\s*--standing$/, '').trim()
    }
    if (!target || !reason) return { text: 'Usage: /allow <rule-or-command> <reason> [--standing]' }
    return run(io, options, ['allow', target, '--reason', reason, ...(standing ? [] : ['--once'])])
  }
  return { text: `unknown command ${e.command}` }
}
