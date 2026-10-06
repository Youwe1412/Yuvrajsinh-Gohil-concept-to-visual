import { describe, expect, test } from 'claude-code/testing'

import { sha256Hex } from '../hooks/sha256'
import { COMPOSER, PRESENTATION, START, active, floor } from './fake-aem'

// Phase 2 (0.8.0): the CLI refuses operator-only commands unless the operator is shown to be running them.
// This plugin shows it with a one-time nonce: a random value passed to the one aem call, of which only the
// SHA-256 is written, with a 60-second expiry. The nonce is never written, logged or shown.

const ascii = (s: string): Uint8Array => Uint8Array.from(s, c => c.charCodeAt(0))
const sha256 = (s: string): string => sha256Hex(ascii(s))

const approve = ($: Parameters<Parameters<typeof test>[1]>[0], args = 'shot', command = 'approve', origin: object = COMPOSER) =>
  $.command.run({ command, args, origin, presentation: PRESENTATION } as never)

// The CLI hashes the nonce with Python's hashlib; the plugin must produce the same file name.
describe('sha256', () => {
  test('known answers, including a two-block message and a 64-character hex nonce', () => {
    expect(sha256('')).toBe('e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855')
    expect(sha256('abc')).toBe('ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad')
    expect(sha256('abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq')).toBe('248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1')
    expect(sha256('0123456789abcdef'.repeat(4))).toBe('a8ae6e6ee929abea3afcfc5258c8ccd6f85273e0d4626d26c7279f3250f77c8e')
  })
})

describe('operator nonce', () => {
  test('an operator command gets a fresh nonce; only its hash and expiry are written', async ($, on) => {
    const w = floor(on, active())
    await $.session.start(START)
    w.files.length = 0
    w.calls.length = 0
    w.envs.length = 0
    const out = await approve($)
    const at = w.calls.findIndex(c => c[1] === 'approve')
    expect(at).toBeGreaterThanOrEqual(0)
    const nonce = w.envs[at]?.AEM_OPERATOR_NONCE ?? ''
    expect(nonce).toMatch(/^[0-9a-f]{64}$/)
    expect(w.files).toHaveLength(1)
    const file = w.files[0]!
    expect(file.path).toBe(`/Users/test/.aem/nonces/${sha256(nonce)}`)
    expect(JSON.parse(file.text)).toEqual({ expires_at: (Date.parse('2026-10-06T10:05:00+05:30') + 60_000) / 1000 })
    // The nonce itself is nowhere the operator, the model or a log would see it.
    for (const seen of [file.path, file.text, JSON.stringify(out), ...w.toasts, ...w.calls.flat(), ...w.stdins.filter(Boolean) as string[]]) {
      expect(seen).not.toContain(nonce)
    }
  })

  test('every call gets its own nonce', async ($, on) => {
    const w = floor(on, active())
    await $.session.start(START)
    w.envs.length = 0
    w.calls.length = 0
    await approve($, 'one')
    await approve($, 'two')
    await approve($, 'one', 'reject')
    const nonces = w.calls.map((c, i) => (['approve', 'reject'].includes(c[1] ?? '') ? w.envs[i]?.AEM_OPERATOR_NONCE : undefined)).filter(Boolean)
    expect(nonces).toHaveLength(2)
    expect(new Set(nonces).size).toBe(2)
  })

  test('commands that are open to everyone carry no nonce and write nothing', async ($, on) => {
    const w = floor(on, active())
    await $.session.start(START)
    w.files.length = 0
    w.calls.length = 0
    w.envs.length = 0
    await $.tool.call({ tool: 'Read', file_path: '/x' }) // aem guard
    await $.command.run({ command: 'aem', args: 'status', origin: COMPOSER, presentation: PRESENTATION })
    expect(w.calls.some(c => c[1] === 'guard')).toBe(true)
    expect(w.calls.some(c => c[1] === 'status')).toBe(true)
    expect(w.envs.every(e => e?.AEM_OPERATOR_NONCE === undefined)).toBe(true)
    expect(w.files).toHaveLength(0)
  })

  test("the plugin's own automatic ledger events are operator commands too, so they carry a nonce", async ($, on) => {
    const w = floor(on, active())
    await $.session.start(START)
    const auto = w.calls.map((c, i) => ({ c, i })).filter(({ c }) => c[1] === 'stage' && c[2] === 'auto')
    expect(auto.length).toBeGreaterThan(0)
    for (const { i } of auto) expect(w.envs[i]?.AEM_OPERATOR_NONCE).toMatch(/^[0-9a-f]{64}$/)
  })

  test('a refused origin makes no nonce and runs nothing', async ($, on) => {
    const w = floor(on, active())
    await $.session.start(START)
    w.files.length = 0
    w.calls.length = 0
    const out = await approve($, 'shot', 'approve', { kind: 'plugin', name: 'other' })
    expect(out.text).toContain('can only be typed by the operator')
    expect(w.files).toHaveLength(0)
    expect(w.calls).toHaveLength(0)
  })

  test('the nonce folder follows AEM_HOME', async ($, on) => {
    const w = floor(on, active(), { env: { AEM_HOME: '/work/aemhome' } })
    await $.session.start(START)
    w.files.length = 0
    await approve($)
    expect(w.files[0]?.path.startsWith('/work/aemhome/nonces/')).toBe(true)
  })

  test('if the nonce cannot be written the call still runs without one, so the CLI refuses and says why', async ($, on) => {
    const w = floor(on, active(), { failWrite: true })
    await $.session.start(START)
    w.calls.length = 0
    w.envs.length = 0
    await approve($)
    const at = w.calls.findIndex(c => c[1] === 'approve')
    expect(at).toBeGreaterThanOrEqual(0)
    expect(w.envs[at]?.AEM_OPERATOR_NONCE).toBeUndefined()
  })
})
