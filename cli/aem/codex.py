"""aem codex-hook: the same record for OpenAI Codex, through its command hooks. It never denies a call.

Codex (0.146 and later, feature `hooks`) runs a command for each hook event with one JSON object
on stdin and reads one JSON object from stdout. This module answers every event AEM uses with the
code the Claude Code plugin calls, so both agents leave the same record:

  SessionStart      the AEM context text (principle, project, recall) as additionalContext;
                    session_start in events.jsonl
  UserPromptSubmit  prompt and turn_start
  PreToolUse        aem observe on Bash and apply_patch: an `observed` event with the files the call
                    names, and an inferred stage when none is open. Never a denial, and no delivery
                    confirmation: a delivery of unapproved media is recorded, not asked about.
  PostToolUse       the render sentinel after Bash (aem rendered), as additionalContext; a
                    tool_call event for calls of 30 s or more
  Stop              turn_end
  SessionEnd        session_end (and the end of any stage AEM inferred)

What Codex cannot do here: there are no slash commands, so the operator types `aem approve`,
`aem stage` and the rest in their own terminal; there is no timer, so idle time is not detected live
(gaps show in the report as unobserved); there is no status line, toast, pane or dialog. A hook that
fails or cannot start leaves the call alone, as the plugin does.
"""
from __future__ import annotations

import argparse
import json
import re
import time

from . import context, ledger, observe, registry, sentinel
from .util import AemError, aem_home, read_json, write_json_atomic

LONG_TOOL_S = 30.0


def _ctx(reg_path: str | None, cwd: str | None = None):
    try:
        return registry.context(argparse.Namespace(registry=reg_path), cwd=cwd)
    except AemError:
        return None


def _pending(tool_use_id: str):
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", tool_use_id or "none")[:120]
    return aem_home() / "codex" / "pending" / f"{safe}.json"


def _context_out(event: str, text: str) -> dict:
    return {"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}}


EVENTS = {  # event: (matcher, timeout in seconds)
    "SessionStart": (None, 30),
    "UserPromptSubmit": (None, 10),
    "PreToolUse": ("^(Bash|apply_patch|Edit|Write)$", 60),
    "PostToolUse": ("^Bash$", 600),
    "Stop": (None, 10),
    "SessionEnd": (None, 3),
}


def config(command: str, fmt: str = "toml") -> str:
    """The hook configuration for ~/.codex/config.toml ([hooks] tables) or ~/.codex/hooks.json."""
    if fmt == "json":
        hooks = {}
        for ev, (matcher, timeout) in EVENTS.items():
            group = {"hooks": [{"type": "command", "command": command, "timeout": timeout}]}
            if matcher:
                group = {"matcher": matcher, **group}
            hooks[ev] = [group]
        return json.dumps({"hooks": hooks}, indent=2) + "\n"
    q = json.dumps  # a JSON string is a valid TOML basic string
    lines = ["# Aavkar Educational Motion Studio (AEM) hooks for Codex. Add to ~/.codex/config.toml.", "[hooks]"]
    for ev, (matcher, timeout) in EVENTS.items():
        m = f"matcher = {q(matcher)}, " if matcher else ""
        lines.append(f'{ev} = [{{ {m}hooks = [{{ type = "command", command = {q(command)}, timeout = {timeout} }}] }}]')
    return "\n".join(lines) + "\n"


def handle(req: dict, reg_path: str | None = None) -> dict:
    """One Codex hook event in, the JSON Codex reads back out ({} for nothing to say)."""
    event = req.get("hook_event_name") or ""
    cwd = req.get("cwd")
    ctx = _ctx(reg_path, cwd)
    session = req.get("session_id")
    turn = req.get("turn_id")

    def auto(name, **extra):
        if ctx is not None:
            ledger.record(ctx, name, source="aem codex-hook", agent="codex", session=session,
                          **{k: v for k, v in extra.items() if v is not None})

    if event == "SessionStart":
        if ctx is None:
            return _context_out(event, CODEX_INACTIVE)
        if req.get("source") in (None, "startup", "resume", "clear"):
            auto("session_start", note=req.get("source"))
        text = context.build(ctx)["text"] + CODEX_NOTE
        return _context_out(event, text)

    if event == "UserPromptSubmit":
        auto("prompt", origin="codex user")
        auto("turn_start", turn=turn)
        return {}

    if event == "PreToolUse":
        tool = str(req.get("tool_name") or "")
        tin = req.get("tool_input") or {}
        tin = tin if isinstance(tin, dict) else {"command": str(tin)}
        if tool in ("Edit", "Write") and not tin.get("file_path"):
            tool = "apply_patch"  # Codex reports apply_patch under these names too, with the patch as input
        if ctx is not None and tool in ("Bash", "apply_patch"):
            observe.observe({"tool": tool, "input": tin, "cwd": cwd, "session": session, "agent": "codex"},
                            reg_path=reg_path)
        if tool == "Bash" and ctx is not None:
            write_json_atomic(_pending(req.get("tool_use_id") or ""), {"started_at": time.time(), "tool": tool})
        return {}

    if event == "PostToolUse":
        tool = str(req.get("tool_name") or "")
        pending = _pending(req.get("tool_use_id") or "")
        started = (read_json(pending) or {}).get("started_at") if pending.exists() else None
        if pending.exists():
            pending.unlink()
        if ctx is None or tool != "Bash":
            return {}
        if started is not None and time.time() - started >= LONG_TOOL_S:
            auto("tool_call", tool=tool, duration_s=round(time.time() - started, 1), turn=turn)
        tin = req.get("tool_input") or {}
        command = str(tin.get("command") or "") if isinstance(tin, dict) else str(tin)
        r = sentinel.rendered(ctx, command, cwd, started)
        if r["render"] and r["text"]:
            return _context_out(event, r["text"])
        return {}

    if event == "Stop":
        auto("turn_end", turn=turn)
        return {}

    if event == "SessionEnd":
        auto("session_end", note=req.get("reason"))
        if ctx is not None:
            ledger.close_inferred(ctx, "inferred stage ended with the session")
        return {}

    return {}


CODEX_INACTIVE = (
    "# Aavkar Educational Motion Studio (AEM)\n\n"
    "AEM's hooks are installed but no project is resolved here: the working folder is not a registered project "
    "and AEM_PROJECT is not set, so AEM records nothing. If the work is for an AEM client, ask the operator to "
    "start Codex in the project's folder."
)

CODEX_NOTE = (
    "\n\nIn Codex: AEM has no slash commands here. Where this text names /approve, /reject, /client-said or "
    "/stage, ask the operator to run `aem approve`, `aem reject`, `aem client-said` or `aem stage` in their own "
    "terminal. Codex shows no delivery confirmation: run `aem check-approval <render>` before any delivery; AEM "
    "records every delivery and the approval state of what it names."
)


def main_json(raw: str, reg_path: str | None = None) -> str:
    try:
        req = json.loads(raw or "{}")
    except json.JSONDecodeError as exc:
        raise AemError(f"codex-hook reads one JSON object on stdin ({exc.msg})")
    return json.dumps(handle(req, reg_path), ensure_ascii=False)
