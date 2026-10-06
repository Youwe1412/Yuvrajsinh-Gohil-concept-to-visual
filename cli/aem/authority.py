"""aem authority: the operator's own message, standing for its turn.

AEM's first principle: it allows whatever the operator asks for in chat. The guard and the operator-only
commands exist to stop the agent acting on its own authority; when the operator has asked, the decision is
the operator's, and AEM records it and never blocks it.

How a turn gets an authority (the plugin does this; the agent never does):

  prompt.submit from an operator origin (composer, bridge or SDK host; never a plugin, a peer agent, a
  scheduled trigger or the agent itself)  ->  `aem authority open --session S --turn T` with the prompt's
  exact text on stdin. That writes a random nonce's SHA-256 to <AEM_HOME>/nonces/ (kind "turn", the prompt
  text, session, turn, expiry now + 60 minutes), records an `operator_prompt` event in the project's
  events.jsonl (the exact text, its SHA-256, session, turn), and prints the nonce once for the plugin to put
  in AEM_OPERATOR_TURN for everything the turn starts.

  turn.complete  ->  `aem authority close --session S`: every authority of that session is deleted. After
  that, the turn's nonce opens nothing. Without a turn authority (autonomous, loop, scheduled, or any turn
  an operator prompt did not start) the guard and the operator-only commands apply unchanged.

`open` and `close` are operator-only, and never accepted on a turn authority (operator.PLUGIN_ONLY): the
plugin runs them with its one-time nonce. `uses` is open: it lists what operator commands succeeded on the
authority in AEM_OPERATOR_TURN, so the plugin can toast each one.

Limits: this is cooperative. The agent shares the operator's disk, so an agent that writes a nonce file by
hand can forge an authority; what shows it is the log (every call the guard would have denied is an
`allowed_by_operator_prompt` event naming the prompt, every command carries via "chat" and the prompt's id)
and the ledger integrity check (`aem integrity`).
"""
from __future__ import annotations

import json
import os
import secrets
import time
from pathlib import Path

from . import ledger, operator, registry
from .operator import TURN_TTL_S, USES_SUFFIX, excerpt_of, nonce_dir, nonce_hash
from .registry import Context
from .util import AemError, now, sha256_text, ts


def _write_record(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def prompt_id_of(session: str, when: str, text: str) -> str:
    return "p-" + sha256_text(f"{session}|{when}|{text}")[:10]


def _find_prompt_event(ctx: Context, prompt_id: str) -> dict | None:
    for ev in ledger.read_events(ctx):
        if ev.get("event") == "operator_prompt" and ev.get("prompt_id") == prompt_id:
            return ev
    return None


def record_prompt_event(ctx: Context, *, prompt_id: str, text: str, session: str | None, turn: str | None,
                        origin: str | None, late: bool = False) -> dict:
    """The operator_prompt event: the exact text of the operator's message, its SHA-256, session, turn and time.
    Written by this command, which the plugin runs; the agent's own call to `authority open` is refused."""
    return ledger.record(ctx, "operator_prompt", fill_stage=True, note=excerpt_of(text), prompt_id=prompt_id,
                         prompt_text=text, prompt_sha256=sha256_text(text), session=session, turn=turn,
                         origin=origin, recorded_late=True if late else None, source="aem authority")


def ensure_prompt_event(ctx: Context, a: "operator.Authority") -> None:
    """A command ran on a turn authority in a project whose events.jsonl has no operator_prompt event for it
    (the prompt was submitted where no project resolved): write it now, marked late."""
    key = str(ctx.events_path)
    if key in a.recorded:
        return
    a.recorded.add(key)
    if _find_prompt_event(ctx, a.prompt_id) is None:
        record_prompt_event(ctx, prompt_id=a.prompt_id, text=a.prompt_text, session=a.session, turn=a.turn,
                            origin=a.origin, late=True)


def open_authority(args, text: str) -> dict:
    """Make a turn authority for the operator's prompt (text) and record it. Returns the nonce, once."""
    operator.assert_checked("authority open")
    if not args.session:
        raise AemError("authority open needs --session")
    if not text.strip():
        raise AemError("authority open reads the operator's exact prompt on standard input")
    t = now()
    when = ts(t)
    nonce = secrets.token_hex(32)
    prompt_id = args.prompt_id or prompt_id_of(args.session, when, text)
    project = None
    ctx = None
    try:
        ctx = registry.context(args, require_project=True)
        project = f"{ctx.client.id}/{ctx.project}"
    except AemError:
        ctx = None  # no project here: the authority is still made; the event is written where it is used
    recorded = False
    if args.prompt_id:
        # The same prompt starting a later turn (it was typed while the last one ran, and queued): it must be
        # a prompt this project already holds, with this exact text.
        if ctx is None:
            raise AemError("--prompt-id needs a project: the prompt's event is looked up there")
        prior = _find_prompt_event(ctx, args.prompt_id)
        if prior is None or prior.get("prompt_sha256") != sha256_text(text):
            raise AemError(f"no operator_prompt event {args.prompt_id} with this text in this project")
        ledger.record(ctx, "operator_turn", fill_stage=True, note="the prompt began this turn", prompt_id=prompt_id,
                      session=args.session, turn=args.turn, source="aem authority")
        recorded = True
    elif ctx is not None:
        record_prompt_event(ctx, prompt_id=prompt_id, text=text, session=args.session, turn=args.turn,
                            origin=args.origin)
        recorded = True
    record = {"kind": "turn", "opened_at": t.timestamp(), "expires_at": t.timestamp() + TURN_TTL_S,
              "session": args.session, "turn": args.turn, "origin": args.origin, "prompt_id": prompt_id,
              "prompt_text": text, "prompt_sha256": sha256_text(text), "project": project}
    _write_record(nonce_dir() / nonce_hash(nonce), record)
    operator._purge_expired(time.time())
    return {"ok": True, "nonce": nonce, "prompt_id": prompt_id, "expires_at": record["expires_at"],
            "project": project, "event_recorded": recorded, "excerpt": excerpt_of(text)}


def close_authority(args) -> dict:
    """The turn ended: every authority of this session is gone."""
    operator.assert_checked("authority close")
    if not args.session:
        raise AemError("authority close needs --session")
    closed = []
    try:
        entries = list(nonce_dir().iterdir())
    except OSError:
        entries = []
    for p in entries:
        if p.suffix == USES_SUFFIX:
            continue
        try:
            rec = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if rec.get("kind") == "turn" and rec.get("session") == args.session:
            p.unlink(missing_ok=True)
            p.with_name(p.name + USES_SUFFIX).unlink(missing_ok=True)
            closed.append(rec.get("prompt_id"))
    return {"ok": True, "closed": closed}


def uses(args) -> dict:
    """What succeeded on the authority in AEM_OPERATOR_TURN since use number `after` (open: it only reads)."""
    nonce = os.environ.get(operator.TURN_VAR)
    if not nonce:
        return {"ok": True, "uses": [], "count": 0, "active": False}
    path = nonce_dir() / (nonce_hash(nonce) + USES_SUFFIX)
    rows = []
    try:
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.strip():
                row = json.loads(line)
                row["n"] = n
                rows.append(row)
    except (OSError, ValueError):
        pass
    after = int(args.after or 0)
    return {"ok": True, "uses": [r for r in rows if r["n"] > after], "count": len(rows), "active": True}
