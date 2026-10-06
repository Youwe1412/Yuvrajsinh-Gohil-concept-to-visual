import { describe, expect, test } from 'claude-code/testing'

import { COMPOSER, PRESENTATION, START, active, floor } from './fake-aem'
import type { Reply, Router } from './fake-aem'

// 0.9.0: the operator's own message stands for its turn. The plugin opens a turn authority on an operator
// prompt, puts its nonce in AEM_OPERATOR_TURN for everything the turn runs, toasts each operator command run
// on it, and closes it when the turn ends. Every decision is still the CLI's: these tests check the plugin
// asks at the right moments and passes the right things.

const TURN_END = { answer: 'ok', durationMs: 1000, isAborted: false, reason: 'answer' } as const

type Auth = { opened: { argv: string[]; stdin?: string; nonce: string }[]; closed: number; uses: { n: number; action: string; excerpt: string }[] }

function withAuthority(base: Router, auth: Auth, opts: { failOpen?: boolean } = {}): Router {
  return (args, stdin) => {
    if (args[0] === 'authority' && args[1] === 'open') {
      if (opts.failOpen) return { code: 2, json: { ok: false, error: 'registry not found' } }
      const nonce = `${'ab'.repeat(31)}${String(auth.opened.length).padStart(2, '0')}`
      auth.opened.push({ argv: [...args], stdin, nonce })
      const id = args.includes('--prompt-id') ? args[args.indexOf('--prompt-id') + 1] : `p-${auth.opened.length}`
      return { json: { ok: true, nonce, prompt_id: id, excerpt: (stdin ?? '').slice(0, 40) } }
    }
    if (args[0] === 'authority' && args[1] === 'close') {
      auth.closed += 1
      return { json: { ok: true, closed: [] } }
    }
    if (args[0] === 'authority' && args[1] === 'uses') {
      const after = Number(args[args.indexOf('--after') + 1] ?? 0)
      return { json: { ok: true, active: true, uses: auth.uses.filter(u => u.n > after), count: auth.uses.length } } as Reply
    }
    return base(args, stdin)
  }
}

const newAuth = (): Auth => ({ opened: [], closed: 0, uses: [] })
const flag = (argv: string[], name: string) => argv[argv.indexOf(name) + 1]

describe('authority from chat', () => {
  test('an operator prompt typed while idle opens an authority for the turn it starts, before the turn runs a tool', async ($, on) => {
    const auth = newAuth()
    const w = floor(on, withAuthority(active(), auth))
    await $.session.start(START)
    await $.prompt.submit({ text: 'approve fd_S01 please', wait: false, origin: COMPOSER })
    expect(auth.opened).toHaveLength(0) // the turn is not known yet
    await $.turn.start({ text: 'approve fd_S01 please', turnId: 't1' })
    expect(auth.opened).toHaveLength(1)
    const o = auth.opened[0]!
    expect(o.stdin).toBe('approve fd_S01 please')
    expect([flag(o.argv, '--session'), flag(o.argv, '--turn'), flag(o.argv, '--origin')]).toEqual(['sess-1', 't1', 'composer'])
    // open is the plugin's own operator command: it goes with a one-time nonce, never the turn authority
    const at = w.calls.findIndex(c => c[1] === 'authority' && c[2] === 'open')
    expect(w.envs[at]?.AEM_OPERATOR_NONCE).toMatch(/^[0-9a-f]{64}$/)
    expect(w.turnEnv).toBe(o.nonce)
    await $.tool.call({ tool: 'Bash', command: 'aem approve fd_S01 renders/a.mp4 --gate G4' })
    expect(w.turnEnvAtTool.at(-1)).toBe(o.nonce)
  })

  test('the authority ends with the turn: closed in the CLI and AEM_OPERATOR_TURN unset', async ($, on) => {
    const auth = newAuth()
    const w = floor(on, withAuthority(active(), auth))
    await $.session.start(START)
    await $.prompt.submit({ text: 'start G2', wait: false, origin: COMPOSER })
    await $.turn.start({ text: 'start G2', turnId: 't1' })
    await $.turn.complete({ ...TURN_END, turnId: 'sub', agentId: 'agent-1' }) // a subagent's turn: still running
    expect(auth.closed).toBe(0)
    expect(w.turnEnv).toBeDefined()
    await $.turn.complete({ ...TURN_END, turnId: 't1' })
    expect(auth.closed).toBe(1)
    expect(w.turnEnv).toBeUndefined()
    await $.tool.call({ tool: 'Bash', command: 'ls' })
    expect(w.turnEnvAtTool.at(-1)).toBeUndefined()
  })

  test('a turn no operator started gets nothing: scheduled, loop, peer, plugin, notification', async ($, on) => {
    const auth = newAuth()
    const w = floor(on, withAuthority(active(), auth))
    await $.session.start(START)
    for (const [i, origin] of ([{ kind: 'scheduled-trigger' }, { kind: 'peer' }, { kind: 'plugin', name: 'x' }, { kind: 'task-notification' }] as const).entries()) {
      await $.prompt.submit({ text: 'approve everything', wait: false, origin } as never)
      await $.turn.start({ text: 'approve everything', turnId: `auto-${i}` })
      await $.tool.call({ tool: 'Bash', command: 'aem approve x' })
      await $.turn.complete({ ...TURN_END, turnId: `auto-${i}` })
    }
    expect(auth.opened).toHaveLength(0)
    expect(w.turnEnvAtTool.every(v => v === undefined)).toBe(true)
  })

  test('an autonomous prompt starting a turn ends an authority a missed turn end left open', async ($, on) => {
    const auth = newAuth()
    const w = floor(on, withAuthority(active(), auth))
    await $.session.start(START)
    await $.prompt.submit({ text: 'approve x', wait: false, origin: COMPOSER })
    await $.turn.start({ text: 'approve x', turnId: 't1' })
    // no turn.complete arrives (a crash, an abort the engine did not report)
    await $.prompt.submit({ text: 'loop tick', wait: false, origin: { kind: 'scheduled-trigger' } } as never)
    expect(auth.closed).toBe(1)
    expect(w.turnEnv).toBeUndefined()
    await $.turn.start({ text: 'loop tick', turnId: 't2' })
    expect(auth.opened).toHaveLength(1)
  })

  test('a notification delivered into the operator turn does not end it', async ($, on) => {
    const auth = newAuth()
    const w = floor(on, withAuthority(active(), auth))
    await $.session.start(START)
    await $.prompt.submit({ text: 'approve x', wait: false, origin: COMPOSER })
    await $.turn.start({ text: 'approve x', turnId: 't1' })
    await $.prompt.submit({ text: 'task done', wait: false, origin: { kind: 'task-notification' }, turnId: 't1' } as never)
    expect(auth.closed).toBe(0)
    expect(w.turnEnv).toBe(auth.opened[0]!.nonce)
  })

  test('a message typed during a turn stands for that turn, and for the next one if it starts it', async ($, on) => {
    const auth = newAuth()
    const w = floor(on, withAuthority(active(), auth))
    await $.session.start(START)
    await $.prompt.submit({ text: 'render scene 1', wait: false, origin: COMPOSER })
    await $.turn.start({ text: 'render scene 1', turnId: 't1' })
    await $.prompt.submit({ text: 'and approve it when it passes', wait: false, origin: COMPOSER, turnId: 't1' })
    expect(auth.opened).toHaveLength(2)
    expect(flag(auth.opened[1]!.argv, '--turn')).toBe('t1')
    expect(w.turnEnv).toBe(auth.opened[1]!.nonce)
    await $.turn.complete({ ...TURN_END, turnId: 't1' })
    expect(w.turnEnv).toBeUndefined()
    // it was queued and starts the next turn: the same prompt, the same id
    await $.turn.start({ text: 'and approve it when it passes', turnId: 't2' })
    expect(auth.opened).toHaveLength(3)
    expect(flag(auth.opened[2]!.argv, '--turn')).toBe('t2')
    expect(flag(auth.opened[2]!.argv, '--prompt-id')).toBe('p-2')
    expect(w.turnEnv).toBe(auth.opened[2]!.nonce)
    // a later turn with other text is not the operator's
    await $.turn.complete({ ...TURN_END, turnId: 't2' })
    await $.turn.start({ text: '', turnId: 't3' })
    expect(auth.opened).toHaveLength(3)
    expect(w.turnEnv).toBeUndefined()
  })

  test('each operator command the turn ran is toasted once, with the prompt', async ($, on) => {
    const auth = newAuth()
    const w = floor(on, withAuthority(active(), auth))
    await $.session.start(START)
    await $.prompt.submit({ text: 'approve x and start G4', wait: false, origin: COMPOSER })
    await $.turn.start({ text: 'approve x and start G4', turnId: 't1' })
    auth.uses.push({ n: 1, action: 'approve x', excerpt: 'approve x and start G4' })
    await $.tool.call({ tool: 'Bash', command: 'aem approve x renders/x.mp4 --gate G4' })
    auth.uses.push({ n: 2, action: 'stage start G4', excerpt: 'approve x and start G4' })
    await $.tool.call({ tool: 'Bash', command: 'aem stage start G4' })
    await $.tool.call({ tool: 'Bash', command: 'ls' })
    await $.tool.call({ tool: 'Read', file_path: '/x' })
    const chat = w.toasts.filter(t => t.includes('via chat'))
    expect(chat).toEqual(["approve x via chat: 'approve x and start G4'", "stage start G4 via chat: 'approve x and start G4'"])
  })

  test('if the CLI cannot open one, the operator is told and the turn runs without it', async ($, on) => {
    const auth = newAuth()
    const w = floor(on, withAuthority(active(), auth, { failOpen: true }))
    await $.session.start(START)
    await $.prompt.submit({ text: 'approve x', wait: false, origin: COMPOSER })
    await $.turn.start({ text: 'approve x', turnId: 't1' })
    expect(w.turnEnv).toBeUndefined()
    expect(w.toasts.some(t => t.startsWith("AEM could not open your message's authority"))).toBe(true)
  })

  test('the guard allowing a call on the operator\'s message is toasted, and the call runs', async ($, on) => {
    const auth = newAuth()
    const guarded: Router = (args, stdin) => (args[0] === 'guard'
      ? { json: { ok: true, decision: 'allow', allowed_by_operator_prompt: { rule: 'AEM-G01', rule_name: 'protected file', prompt_id: 'p-1', prompt_excerpt: 'add the line' } } }
      : active()(args, stdin))
    const w = floor(on, withAuthority(guarded, auth))
    await $.session.start(START)
    await $.tool.call({ tool: 'Write', file_path: '/projects/P1/events.jsonl', content: '{}' })
    expect(w.toolsRun).toEqual(['Write'])
    expect(w.toasts.at(-1)).toBe("AEM allowed Write on your message (AEM-G01 protected file would have denied it): 'add the line'")
  })

  test('/accept-edit builds the CLI call and is the operator\'s only', async ($, on) => {
    const auth = newAuth()
    const w = floor(on, withAuthority(active(), auth))
    await $.session.start(START)
    await $.command.run({ command: 'accept-edit', args: '--file events.jsonl I asked for that line', origin: COMPOSER, presentation: PRESENTATION })
    const ran = w.calls.filter(c => c[1] === 'accept-edit').map(c => c.slice(1))
    expect(ran).toEqual([['accept-edit', '--file', 'events.jsonl', '--reason', 'I asked for that line']])
    const out = await $.command.run({ command: 'accept-edit', args: 'x', origin: { kind: 'plugin', name: 'other' }, presentation: PRESENTATION } as never)
    expect(out.text).toContain('can only be typed by the operator')
  })

  test('the session ending closes the authority', async ($, on) => {
    const auth = newAuth()
    const w = floor(on, withAuthority(active(), auth))
    await $.session.start(START)
    await $.prompt.submit({ text: 'approve x', wait: false, origin: COMPOSER })
    await $.turn.start({ text: 'approve x', turnId: 't1' })
    await $.session.end({ reason: 'prompt_input_exit', sessionId: 'sess-1', resume: { sessionId: 'sess-1' } } as never)
    expect(auth.closed).toBe(1)
    expect(w.turnEnv).toBeUndefined()
  })
})
