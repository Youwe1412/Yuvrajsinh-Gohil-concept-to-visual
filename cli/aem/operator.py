"""Operator-only commands: the CLI refuses them unless the operator is the one running them.

These are the commands that write the record, and the only commands an agent cannot run:

    approve  reject  client-said  stage (every action, including the plugin's `stage auto`)
    accept-edit  accept-video  new-client  inbox accept  inbox dismiss

They are what makes the record the operator's: an approval, a rejection, the client's words, a stage, an
accepted ledger edit. Everything else (reading, checking, rendering, recording what the agent did) is open.

One of these must hold, checked at the entry of the command, so how it is spelled (a path, a wrapper, a
script, `python3 -m aem`) does not matter:

  (a) Terminal. stdin and stdout are a terminal, /dev/tty can be opened, and none of the agent markers
      (CLAUDECODE, CODEX_CI, ...) is in the environment. The first two alone are not enough: an agent's
      shell can allocate a pseudo-terminal (`script`, Python's pty), and then both are true. The markers
      are what that process inherits from the agent that started it. For `client-said`, whose quote
      arrives on stdin, stdin need not be a terminal; /dev/tty and the markers still decide.
  (b) Plugin slash command. The plugin's slash-command handler (and its delivery confirmation) makes a random
      one-time nonce, writes only its SHA-256 to <AEM_HOME>/nonces/ with a 60-second expiry, and passes the
      nonce in AEM_OPERATOR_NONCE to that one aem call. aem checks the hash, deletes the file (so it works
      once), and removes the variable from its own environment so nothing it starts inherits it. The nonce
      is never written, logged or printed.

When an agent runs one, the refusal is one line, and the agent asks the operator to run it.

This is not a lock. An agent that strips the markers and allocates a terminal, or writes a nonce hash file
itself, passes: AEM does not stop an agent that wants to misbehave. It makes it visible: every tool call the
agent makes is recorded (`aem observe`), records carry how they were made (`via`), and `aem integrity` shows any
ledger line written outside `aem`.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

from .util import AemError, aem_home

NONCE_VAR = "AEM_OPERATOR_NONCE"
NONCE_TTL_S = 60

# The commands that write the record. `inbox` is operator-only for these actions; listing it is open.
OPERATOR_COMMANDS = ("stage", "approve", "reject", "client-said", "accept-edit", "accept-video", "new-client")
OPERATOR_INBOX_ACTIONS = ("accept", "dismiss")

# Set in the environment of a process that an AI agent started: Claude Code's Bash tool and Codex's shell.
# The operator's own terminal (including the Claude desktop app's terminal panel) has none of these.
AGENT_MARKERS = ("CLAUDECODE", "AI_AGENT", "CLAUDE_CODE_ENTRYPOINT", "CLAUDE_CODE_SESSION_ID",
                 "CODEX_CI", "CODEX_THREAD_ID", "CODEX_SANDBOX")

# Commands whose input arrives on stdin, so stdin cannot be required to be the terminal.
STDIN_IS_DATA = ("client-said",)

_checked = False
_via: str | None = None


class OperatorOnly(AemError):
    """The command is the operator's and this process is not shown to be the operator."""


def command_name(cmd: str, action: str | None = None) -> str | None:
    """The operator-only command this invocation is, as the operator would type it; None if it is open."""
    if cmd in OPERATOR_COMMANDS:
        return cmd
    if cmd == "inbox" and action in OPERATOR_INBOX_ACTIONS:
        return f"inbox {action}"
    return None


def nonce_dir() -> Path:
    return aem_home() / "nonces"


def nonce_hash(nonce: str) -> str:
    return hashlib.sha256(nonce.encode("utf-8")).hexdigest()


def terminal_problem(name: str) -> str | None:
    """Why this process is not the operator's terminal, or None if it is."""
    need_stdin = name not in STDIN_IS_DATA
    if not sys.stdout.isatty() or (need_stdin and not sys.stdin.isatty()):
        return "its " + ("stdin and stdout are not" if need_stdin else "stdout is not") + " a terminal"
    try:
        os.close(os.open("/dev/tty", os.O_RDWR))
    except OSError as exc:
        return f"it has no controlling terminal (/dev/tty: {exc.strerror})"
    for marker in AGENT_MARKERS:
        if os.environ.get(marker):
            return f"{marker} is set, so it runs under an AI agent even though it has a terminal"
    return None


def _purge_expired(now: float) -> None:
    try:
        for p in nonce_dir().iterdir():
            try:
                if json.loads(p.read_text(encoding="utf-8")).get("expires_at", 0) <= now:
                    p.unlink()
            except (OSError, ValueError):
                continue
    except OSError:
        pass


def nonce_problem() -> str | None:
    """Verify and consume the plugin's nonce. None if it was valid (and is now spent)."""
    nonce = os.environ.pop(NONCE_VAR, None)  # never inherited by anything this process starts
    if not nonce:
        return "no operator nonce was given"
    path = nonce_dir() / nonce_hash(nonce)
    now = time.time()  # the real clock: AEM_FIXED_NOW is for tests of the ledger, not of this check
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
        path.unlink()  # one use: gone before anything else runs
    except (OSError, ValueError):
        return "the operator nonce is unknown or already used"
    finally:
        _purge_expired(now)
    if record.get("kind"):  # a record an older plugin wrote for something else (0.9's turn authority)
        return "that is not a one-time operator nonce"
    if float(record.get("expires_at", 0)) <= now:
        return "the operator nonce expired (they last 60 seconds)"
    return None


def require(cmd: str, action: str | None = None) -> None:
    """Entry check for an operator-only command. Raises OperatorOnly unless (a) or (b) holds."""
    global _checked, _via
    name = command_name(cmd, action)
    if name is None:
        return
    nonce_set = bool(os.environ.get(NONCE_VAR))
    nonce = nonce_problem() if nonce_set else None  # consumes it, valid or not
    if nonce_set and nonce is None:
        _checked, _via = True, "slash command"
        return
    tty = terminal_problem(name)
    if tty is None:
        _checked, _via = True, "terminal"
        return
    # One line, so an agent reads it whole: whose command it is, why this process is not them, what to do.
    raise OperatorOnly(
        f"`aem {name}` is the operator's command, run from their terminal or its slash command, and this process "
        f"is neither ({nonce if nonce_set else tty}): ask the operator to run it.",
        data={"operator_only": True, "command": name})


def via() -> str | None:
    """How the operator ran the command that is running: "terminal" or "slash command" (None: not checked)."""
    return _via


def assert_checked(what: str) -> None:
    """Library-level backstop: the functions that write the record refuse a caller that did not come through
    main() and its entry check (a script that imports aem and calls them directly)."""
    if not _checked:
        raise OperatorOnly(f"{what} writes the operator's records and may only run through an `aem` command "
                           "that passed the operator check",
                           hint="Type the command in your own terminal, or use its slash command in Claude Code.")
