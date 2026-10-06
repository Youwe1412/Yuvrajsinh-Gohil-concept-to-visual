"""aem codex-hook: the same checks, context and ledger for OpenAI Codex, through its command hooks.

Codex (0.146 and later, feature `hooks`) runs a command for each hook event with one JSON object
on stdin and reads one JSON object from stdout. This module answers every event AEM uses with the
code the Claude Code plugin calls, so the two agents get the same decisions:

  SessionStart      the AEM context text as additionalContext; session_start in events.jsonl
  UserPromptSubmit  prompt and turn_start
  PreToolUse        aem guard on Bash and apply_patch (each file the patch touches); a denial is
                    {"hookSpecificOutput": {"permissionDecision": "deny", ...}}
  PostToolUse       the render sentinel after Bash (aem rendered), as additionalContext; a
                    tool_call event for calls of 30 s or more
  Stop              turn_end
  SessionEnd        session_end

What Codex cannot do here, and so AEM does not do in Codex: there are no slash commands, so the
operator types `aem approve`, `aem stage` and the rest in their own terminal; there is no timer,
so idle time is not detected live (gaps show in the report as unobserved); there is no status
line, toast or pane. Codex runs a hook that fails or cannot start as if it allowed the call
(fail open), as the plugin does.
"""
from __future__ import annotations

import argparse
import json
import re
import time

from . import context, guard, ledger, registry, sentinel
from .util import AemError, aem_home, read_json, write_json_atomic

LONG_TOOL_S = 30.0
PATCH_FILE = re.compile(r"^\*\*\* (?:Add|Update|Delete) File: (.+)$|^\*\*\* Move to: (.+)$", re.M)


def _ctx(reg_path: str | None):
    try:
        return registry.context(argparse.Namespace(registry=reg_path))
    except AemError:
        return None


def _pending(tool_use_id: str):
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", tool_use_id or "none")[:120]
    return aem_home() / "codex" / "pending" / f"{safe}.json"


def _context_out(event: str, text: str) -> dict:
    return {"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}}


def patch_calls(patch: str) -> list[dict]:
    """The files an apply_patch touches, each as a Write the guard can judge (with its added lines)."""
    calls = []
    blocks = re.split(r"(?m)^(?=\*\*\* (?:Add|Update|Delete) File: )", patch or "")
    for block in blocks:
        added = "\n".join(l[1:] for l in block.splitlines() if l.startswith("+") and not l.startswith("+++"))
        for m in PATCH_FILE.finditer(block):
            path = (m.group(1) or m.group(2) or "").strip()
            if path:
                calls.append({"tool": "Write", "input": {"file_path": path, "content": added}})
    return calls


def guard_calls(tool_name: str, tool_input: dict) -> list[dict]:
    if tool_name == "Bash":
        return [{"tool": "Bash", "input": {"command": str(tool_input.get("command") or "")}}]
    if tool_name in ("apply_patch", "Edit", "Write"):
        return patch_calls(str(tool_input.get("command") or tool_input.get("patch") or tool_input.get("input") or ""))
    return []  # MCP and other tools are not checked, as in the plugin


def deny_text(d: dict) -> str:
    return (f"AEM denied this call ({d['rule']}, {d['rule_name']}): {d['reason']} How to proceed: {d['how']} "
            "(In Codex there are no slash commands: the operator runs the matching `aem` command, such as "
            "`aem approve` or `aem allow`, in their own terminal.) "
            "Do not try another route to the same effect; tell the operator what was denied.")


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
    ctx = _ctx(reg_path)
    session = req.get("session_id")
    turn = req.get("turn_id")

    def auto(name, **extra):
        if ctx is not None:
            ledger.record(ctx, name, source="aem codex-hook", agent="codex", session=session,
                          **{k: v for k, v in extra.items() if v is not None})

    if event == "SessionStart":
        if ctx is None:
            return _context_out(event, context.INACTIVE_TEXT.replace("/aem use", "aem use (in your own terminal)"))
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
        for call in guard_calls(tool, tin if isinstance(tin, dict) else {"command": str(tin)}):
            d = guard.check(call["tool"], call["input"], cwd, reg_path=reg_path)
            if d.get("decision") == "deny":
                return {"hookSpecificOutput": {"hookEventName": event, "permissionDecision": "deny",
                                               "permissionDecisionReason": deny_text(d)}}
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
        return {}

    return {}


CODEX_NOTE = (
    "\n\nIn Codex: AEM has no slash commands here. Where this text says /approve, /reject, /stage, "
    "/allow or /client-said, ask the operator to run `aem approve`, `aem reject`, `aem stage`, "
    "`aem allow` or `aem client-said` in their own terminal."
)


def main_json(raw: str, reg_path: str | None = None) -> str:
    try:
        req = json.loads(raw or "{}")
    except json.JSONDecodeError as exc:
        raise AemError(f"codex-hook reads one JSON object on stdin ({exc.msg})")
    return json.dumps(handle(req, reg_path), ensure_ascii=False)
