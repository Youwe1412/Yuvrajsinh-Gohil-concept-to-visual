// Feature "observe": every Bash, Read, Write, Edit, MultiEdit and NotebookEdit call, the agent's and its
// subagents', goes to `aem observe` before it runs. AEM records it with the files it names and never refuses it,
// with one exception, the only interruption AEM makes: a delivery of media that has no current approval. The
// operator answers a dialog (Deliver records the approval and lets the call run; Stop refuses it). Where no dialog
// can be shown (a -p run) the call is refused once with the /approve command to type, and the same call, repeated,
// goes through and is recorded as delivered without approval. If aem cannot run, every call goes through.
import type { PluginOptions } from 'claude-code'

import { cli, errorOf, refresh } from './aem'
import type { Io } from './aem'

export const OBSERVED_TOOLS: ReadonlySet<string> = new Set(['Bash', 'Read', 'Write', 'Edit', 'MultiEdit', 'NotebookEdit'])

// A broken install should be said once in a while, not on every call.
const FAIL_TOAST_MS = 60_000
let lastFailToast = -Infinity

type Unapproved = { item: string; path: string; state: string }
type Delivery = { question?: string; unapproved?: Unapproved[]; approve?: string[][]; slash?: string[] }
type Observed = { observed?: boolean; inferred?: { gate?: string; note?: string } | null; delivery?: Delivery | null }

export type ObserveVerdict = { deny?: string }

type Call = { tool: string; input: Record<string, unknown>; cwd: string; session: string; agent: unknown }

async function outcome(io: Io, options: PluginOptions, call: Call, what: 'stopped' | 'held' | 'unconfirmed', note: string): Promise<void> {
  await cli(io, options, ['observe'], { stdin: JSON.stringify({ ...call, outcome: what, note }) })
}

const items = (d: Delivery): string => (d.unapproved ?? []).map(u => u.item).join(', ')

export async function observeCall(io: Io, options: PluginOptions, tool: string, args: Record<string, unknown>): Promise<ObserveVerdict> {
  if (!OBSERVED_TOOLS.has(tool)) return {}
  const { tool_use_id: _id, agentId, tool: _tool, ...input } = args
  const call: Call = { tool, input, cwd: await io.cwd(), session: await io.sessionId(), agent: agentId }
  const r = await cli(io, options, ['observe'], { stdin: JSON.stringify(call), timeoutMs: 60_000 })
  if (r.code !== 0) {
    const now = await io.now()
    if (now - lastFailToast >= FAIL_TOAST_MS) {
      lastFailToast = now
      io.toast(`AEM could not record this call (it ran anyway): ${errorOf(r)}`, 8000)
    }
    return {}
  }
  const d = r.data as Observed
  if (d.inferred?.gate) {
    io.toast(`AEM: no stage was open, so ${d.inferred.gate} is inferred (${d.inferred.note ?? ''})`, 8000)
    await refresh(io, options)
  }
  const delivery = d.delivery
  if (!delivery?.question || !delivery.unapproved?.length) return {}
  return confirmDelivery(io, options, call, delivery)
}

// The key of a call for the fallback: the same tool, arguments and folder.
const keyOf = (c: Call): string => JSON.stringify([c.tool, c.input, c.cwd])

async function confirmDelivery(io: Io, options: PluginOptions, call: Call, d: Delivery): Promise<ObserveVerdict> {
  const question = d.question ?? 'Deliver anyway?'
  if ((await io.surfaces()).length === 0) {
    // No one can be asked here: refuse once, saying exactly what to type; the identical call next time goes through.
    const key = keyOf(call)
    if ((await io.getHeld()).includes(key)) {
      await io.patchHeld(h => h.filter(k => k !== key))
      await outcome(io, options, call, 'unconfirmed', 'repeated after AEM held it once with no dialog to ask: delivered without approval')
      io.toast(`AEM: delivered without approval (repeated after notice): ${items(d)}`, 10_000)
      return {}
    }
    await io.patchHeld(h => [...h.filter(k => k !== key), key].slice(-20))
    await outcome(io, options, call, 'held', 'no dialog could be shown: held once with the /approve command')
    return { deny: `AEM: ${question} No one could be asked here, so this call was held once. To approve, the operator ` +
      `types ${(d.slash ?? []).join(' and ')}, and then the call is repeated. Repeated as it is, it goes through and is ` +
      'recorded as delivered without approval.' }
  }
  let answer: string | undefined
  try {
    answer = await io.ask(question, { options: ['Deliver', 'Stop'], header: 'AEM delivery' })
  } catch {
    answer = undefined // dismissed: not a Deliver
  }
  if (answer === 'Deliver') {
    // The operator's answer, so the approval is the operator's: each runs with a one-time nonce, via the confirmation.
    const failed: string[] = []
    for (const argv of d.approve ?? []) {
      if (argv[0] !== 'approve') continue
      const a = await cli(io, options, argv)
      if (a.code !== 0) failed.push(`${argv[1]}: ${errorOf(a)}`)
    }
    if (failed.length) {
      await outcome(io, options, call, 'unconfirmed', `Deliver pressed, but the approval could not be recorded: ${failed.join('; ')}`)
      io.toast(`AEM: delivered on your Deliver, but no approval was recorded: ${failed[0]}`, 12_000)
    } else {
      io.toast(`AEM: Deliver pressed; ${items(d)} approved through the confirmation`, 8000)
    }
    await refresh(io, options)
    return {}
  }
  const why = answer === undefined ? 'the dialog was dismissed' : answer === 'Stop' ? 'Stop pressed' : `answered "${answer}"`
  await outcome(io, options, call, 'stopped', why)
  io.toast(`AEM: delivery stopped (${items(d)})`, 8000)
  return { deny: `AEM: the operator stopped this delivery (${question.replace(/ Deliver anyway\?$/, '')}; ${why}). ` +
    'Do not repeat it or deliver another way; ask the operator what they want.' }
}
