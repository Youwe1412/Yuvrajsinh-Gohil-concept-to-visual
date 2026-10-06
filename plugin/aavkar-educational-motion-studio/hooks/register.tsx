// Aavkar Educational Motion Studio (AEM): one plugin, one hooks module.
//
// The engine takes one hook per event per module (without a matcher) and follows `$` only
// inside the file that holds it. So this file owns every `on(...)`, builds an `io` of
// closures over the hook's `$`, and hands it to the features, which never see `$`.
// Every decision is the aem CLI's; the features only run it and show what it says.
import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import { EMPTY_LEDGER, EMPTY_VIEW } from './aem'
import type { Io } from './aem'
import { CONTEXT_COMMANDS, contextCommand, contextCompose, contextStart, contextTick } from './context'
import { GUARD_COMMANDS, guardCall, guardCommand } from './guard'
import { EMPTY_INBOX, INBOX_COMMANDS, INBOX_PANE, cancelReason, drawInbox, inboxCommand, inboxOn, loadInbox, pressAction, submitReason } from './inbox'
import {
  LEDGER_COMMANDS,
  ledgerCommand,
  ledgerEnd,
  ledgerPrompt,
  ledgerStart,
  ledgerTick,
  ledgerToolDone,
  ledgerTurnComplete,
  ledgerTurnStart,
} from './ledger'
import { sentinelAfter, sentinelBefore } from './sentinel'

const view = atom({ plugin: 'aavkar-educational-motion-studio', key: 'view' } as const, EMPTY_VIEW)
const ledger = atom({ plugin: 'aavkar-educational-motion-studio', key: 'ledger' } as const, EMPTY_LEDGER)
const inbox = atom({ plugin: 'aavkar-educational-motion-studio', key: 'inbox' } as const, EMPTY_INBOX)
const pin = atom({ plugin: 'aavkar-educational-motion-studio', key: 'pin' } as const, null as string | null)

const TICK_MS = 30_000

function io($: EngineInterface): Io {
  return {
    run: (argv, init) => $.process.run(argv, init),
    home: () => $.env.get('HOME'),
    aemHome: async () => (await $.env.get('AEM_HOME')) ?? `${(await $.env.get('HOME')) ?? ''}/.aem`,
    writeFile: (path, text) => $.fs.write(path, text),
    toast: (text, timeoutMs) => $.ui.toast(text, timeoutMs === undefined ? undefined : { timeoutMs }),
    status: text => $.ui.status(text),
    now: () => $.clock.now(),
    sessionId: () => $.session.id(),
    cwd: () => $.session.cwd(),
    selection: async () => (await $.ui.selection())?.text,
    registerCommand: async spec => {
      await $.command.register(spec)
    },
    getView: () => read($, view),
    setView: async v => {
      await update($, view, () => v)
    },
    getPin: () => read($, pin),
    setPin: async v => {
      await update($, pin, () => v)
    },
    getLedger: () => read($, ledger),
    patchLedger: async fn => {
      await update($, ledger, fn)
    },
    getInbox: () => read($, inbox),
    patchInbox: async fn => {
      await update($, inbox, fn)
    },
    openPane: async (id, title) => {
      await $.ui.open({ id, title })
    },
  }
}

export const register: Register = (on, options) => {
  on('session.start', async ($, e, next) => {
    const started = await next(e)
    const x = io($)
    const commands = [...CONTEXT_COMMANDS, ...LEDGER_COMMANDS, ...GUARD_COMMANDS, ...(inboxOn(options) ? INBOX_COMMANDS : [])]
    for (const c of commands) await x.registerCommand(c)
    await contextStart(x, options)
    await ledgerStart(x, options)
    let tick = 0
    $.clock.every(TICK_MS, () => {
      tick += 1
      const n = tick
      void (async () => {
        await contextTick(x, options, n)
        await ledgerTick(x, options)
      })()
    })
    return started
  })

  on('session.end', async ($, e, next) => {
    await ledgerEnd(io($), options, e)
    return next(e)
  })

  on('prompt.compose', async ($, e, next) => {
    const composed = await next(e)
    return { sections: await contextCompose(io($), composed.sections) }
  })

  on('prompt.submit', async ($, e, next) => {
    await ledgerPrompt(io($), options, e.origin)
    return next(e)
  })

  on('turn.start', async ($, e, next) => {
    await ledgerTurnStart(io($), options, e.turnId)
    return next(e)
  })

  on('turn.complete', async ($, e, next) => {
    await ledgerTurnComplete(io($), options, e)
    return next(e)
  })

  on('tool.call', async ($, e, next) => {
    const x = io($)
    const verdict = await guardCall(x, options, String(e.tool), e as unknown as Record<string, unknown>)
    if ('deny' in verdict) return { deny: verdict.deny }
    const startedAt = await $.clock.now()
    const watching = await sentinelBefore(x, String(e.tool))
    const ran = await next(e)
    await ledgerToolDone(x, options, String(e.tool), startedAt, await $.clock.now())
    if ('deny' in ran && ran.deny !== undefined) return ran
    const note = await sentinelAfter(x, options, e as unknown as Record<string, unknown>, watching, ran.isError === true)
    if (note === undefined || ran.isError === true) return ran
    return { ...ran, context: [...(ran.context ?? []), note] }
  })

  for (const c of CONTEXT_COMMANDS) {
    on('command.run', { command: c.name }, async ($, e) => contextCommand(io($), options, e))
  }
  for (const c of LEDGER_COMMANDS) {
    on('command.run', { command: c.name }, async ($, e) => ledgerCommand(io($), options, e))
  }
  for (const c of GUARD_COMMANDS) {
    on('command.run', { command: c.name }, async ($, e) => guardCommand(io($), options, e))
  }
  if (!inboxOn(options)) return
  for (const c of INBOX_COMMANDS) {
    on('command.run', { command: c.name }, async ($, e) => inboxCommand(io($), options, e))
  }

  on('ui.render', { component: 'Pane', requestId: INBOX_PANE }, async ($, e) => {
    const x = io($)
    const b = await read($, inbox)
    return drawInbox($.ui.resolve(e), e.surface, b, {
      press: (item, action) => void pressAction(x, options, item, action),
      reason: text => void submitReason(x, options, text),
      cancel: () => void cancelReason(x),
      reload: () => void loadInbox(x, options),
    }, e.viewport?.rows ?? 24)
  })
}
