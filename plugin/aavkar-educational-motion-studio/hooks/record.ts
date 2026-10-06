// Feature "record": the slash commands that write the record, which only the operator types: /approve, /reject,
// /client-said, /accept-video, /accept-edit (/stage and the time commands are in ledger.ts). Each runs its aem command with a
// one-time nonce, which is how the CLI knows the operator ran it; the agent cannot.
import type { CommandRunInput, CommandRunResult, PluginOptions } from 'claude-code'

import { cli, isOperator, leading, refresh, refusedText } from './aem'
import type { CommandSpecLite, Io } from './aem'

const SCOPES: readonly string[] = ['channel', 'video', 'instance']

export const RECORD_COMMANDS: readonly CommandSpecLite[] = [
  { name: 'approve', description: 'AEM: approve the exact render of an item (its last checked render, the open gate)', argumentHint: '<item> [path] [gate]' },
  { name: 'reject', description: 'AEM: reject an item, with a reason', argumentHint: '<item> <reason>' },
  { name: 'client-said', description: "AEM: record the client's exact words in their decisions file (and, with --about, as their ruling)", argumentHint: '<channel|video|instance> | --about <moment|video|channel> [--ruling keep|change|remove] [--source S] [--item SHOT] <their words, or select them first>' },
  { name: 'accept-video', description: 'AEM: the client accepted the delivered video: an implicit acceptance for each moment they did not comment on', argumentHint: '<version> <source, e.g. Frame.io, 12 Oct 2026>' },
  { name: 'accept-edit', description: 'AEM: accept the ledger edits `aem integrity` found (all, or one file), with a reason', argumentHint: '[--file NAME] <reason>' },
]

async function run(io: Io, options: PluginOptions, argv: string[], stdin?: string): Promise<CommandRunResult> {
  const r = await cli(io, options, argv, { json: false, stdin })
  await refresh(io, options)
  const first = r.text.split('\n')[0] ?? ''
  io.toast(`AEM ${argv[0]}: ${r.code === 0 ? first : `failed: ${first}`}`, 8000)
  return { text: r.text || `aem ${argv[0]} exited ${r.code}` }
}

export async function recordCommand(io: Io, options: PluginOptions, e: CommandRunInput): Promise<CommandRunResult> {
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
    // The scope word is optional once --about names what the words are about (it implies the scope).
    const spec = { words: 1, valueFlags: ['source', 'item', 'about', 'ruling'] }
    let a = leading(e.args, { ...spec, words: 0 })
    if (!a.flags.about || SCOPES.includes(a.rest.split(/\s+/)[0] ?? '')) a = leading(e.args, spec)
    const scope = a.words[0]
    const about = typeof a.flags.about === 'string' && a.flags.about ? a.flags.about : undefined
    let quote = a.rest
    let from = 'typed with the command'
    if (!quote.trim()) {
      quote = (await io.selection()) ?? ''
      from = 'the selected text'
    }
    if ((!scope && !about) || !quote.trim()) {
      return { text: 'Usage: /client-said <channel|video|instance> [--source S] [--item SHOT] <their exact words>\n'
        + '   or: /client-said --about <moment|video|channel> [--ruling keep|change|remove] [--source S] <their exact words>\n'
        + '(or select their words in the transcript first)' }
    }
    const source = typeof a.flags.source === 'string' ? a.flags.source : `pasted in Claude Code (${from})`
    const item = typeof a.flags.item === 'string' ? ['--item', a.flags.item] : []
    const ruling = typeof a.flags.ruling === 'string' ? ['--ruling', a.flags.ruling] : []
    return run(io, options, ['client-said', ...(scope ? ['--scope', scope] : []), '--source', source, ...item,
      ...(about ? ['--about', about] : []), ...ruling], quote)
  }
  if (e.command === 'accept-video') {
    const a = leading(e.args, { words: 1, valueFlags: ['source'] })
    const version = a.words[0]
    const source = typeof a.flags.source === 'string' && a.flags.source ? a.flags.source : a.rest.trim()
    if (!version || !source) {
      return { text: 'Usage: /accept-video <version> <where the acceptance came from, e.g. Frame.io, 12 Oct 2026>' }
    }
    return run(io, options, ['accept-video', version, '--source', source])
  }
  if (e.command === 'accept-edit') {
    const a = leading(e.args, { words: 0, valueFlags: ['file'] })
    const file = typeof a.flags.file === 'string' ? ['--file', a.flags.file] : []
    const reason = a.rest.trim()
    return run(io, options, ['accept-edit', ...file, ...(reason ? ['--reason', reason] : [])])
  }
  return { text: `unknown command ${e.command}` }
}
