"""Operator-only commands: the CLI itself refuses them unless the operator is the one running them.

The commands that change what the operator owns (approvals, rulings, overrides, the stage ledger, the
registry, the last-used hint) are:

    use  stage (every action, including the plugin's `stage auto`)  approve  reject  client-said
    allow  new-client  inbox accept  inbox dismiss

They run when ONE of these holds, checked at the entry of the command, so how the command was spelled
(a path, a wrapper, a script, `python3 -m aem`) does not matter:

  (a) Terminal. stdin and stdout are a terminal, /dev/tty can be opened, and none of the agent markers
      (CLAUDECODE, CODEX_CI, ...) is in the environment. The first two alone are not enough: an agent's
      shell can allocate a pseudo-terminal (`script`, Python's pty), and then both are true. The markers
      are what that process inherits from the agent that started it. For `client-said`, whose quote
      arrives on stdin, stdin need not be a terminal; /dev/tty and the markers still decide.
  (b) Plugin. The plugin's slash-command handler makes a random one-time nonce, writes only its SHA-256 to
      <AEM_HOME>/nonces/ with a 60-second expiry, and passes the nonce in AEM_OPERATOR_NONCE to that one
      aem call. aem checks the hash, deletes the file (so it works once), and removes the variable from
      its own environment so nothing it starts inherits it. The nonce is never written, logged or printed.

  (c) Chat. The operator's own message authorises it. When a turn begins with a prompt from an operator origin
      (the composer, the bridge or the SDK host; never a plugin, a peer agent or the agent itself) the plugin
      asks `aem authority open` for a turn authority: a random nonce whose SHA-256 is written to
      <AEM_HOME>/nonces/ with the prompt's exact text, the session and turn, expiring when the turn ends or
      after 60 minutes, whichever is first. The plugin puts the nonce in AEM_OPERATOR_TURN in the environment
      of everything the turn starts. Unlike (b) it is not used up: every operator command in that turn works,
      and each record it writes carries via "chat", the prompt's id and an excerpt of the prompt. The
      authority is never accepted for `authority` itself (only the plugin's one-time nonce or a terminal may
      open or close one), so the agent cannot mint a prompt of its own.

This is cooperative, not a security boundary. An agent that strips the markers from its environment and
allocates a terminal, or that writes a hash file itself (the guard denies its Write and Edit tools there,
its shell is not stopped), passes. The ledgers are append-only with hashes, and Phase 4's integrity check
is what catches the result.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from .util import AemError, aem_home

NONCE_VAR = "AEM_OPERATOR_NONCE"
NONCE_TTL_S = 60
TURN_VAR = "AEM_OPERATOR_TURN"
TURN_TTL_S = 3600

# The commands only the operator runs. `inbox` and `authority` are operator-only for these actions; the rest
# of their actions (listing the inbox, reading an authority's uses) are open.
OPERATOR_COMMANDS = ("use", "stage", "approve", "reject", "client-said", "allow", "new-client", "accept-edit")
OPERATOR_INBOX_ACTIONS = ("accept", "dismiss")
OPERATOR_AUTHORITY_ACTIONS = ("open", "close")
# Never accepted on a turn authority, only on the plugin's one-time nonce or a terminal: an authority that
# could open authorities would let the agent write the prompt that authorises it.
PLUGIN_ONLY = ("authority open", "authority close")

# Set in the environment of a process that an AI agent started: Claude Code's Bash tool and Codex's shell.
# The operator's own terminal (including the Claude desktop app's terminal panel) has none of these.
AGENT_MARKERS = ("CLAUDECODE", "AI_AGENT", "CLAUDE_CODE_ENTRYPOINT", "CLAUDE_CODE_SESSION_ID",
                 "CODEX_CI", "CODEX_THREAD_ID", "CODEX_SANDBOX")

# Commands whose input arrives on stdin, so stdin cannot be required to be the terminal.
STDIN_IS_DATA = ("client-said",)

USES_SUFFIX = ".uses"

_checked = False
_authority: "Authority | None" = None


class OperatorOnly(AemError):
    """The command is the operator's and this process is not shown to be the operator."""


def command_name(cmd: str, action: str | None = None) -> str | None:
    """The operator-only command this invocation is, as the operator would type it; None if it is open."""
    if cmd in OPERATOR_COMMANDS:
        return cmd
    if cmd == "inbox" and action in OPERATOR_INBOX_ACTIONS:
        return f"inbox {action}"
    if cmd == "authority" and action in OPERATOR_AUTHORITY_ACTIONS:
        return f"authority {action}"
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
            if p.suffix == USES_SUFFIX:
                if not p.with_suffix("").exists():  # the authority is gone, so are its uses
                    p.unlink(missing_ok=True)
                continue
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
        if record.get("kind") == "turn":
            return "that is a turn authority, which belongs in AEM_OPERATOR_TURN, not the one-time nonce"
        path.unlink()  # one use: gone before anything else runs
    except (OSError, ValueError):
        return "the operator nonce is unknown or already used"
    finally:
        _purge_expired(now)
    if float(record.get("expires_at", 0)) <= now:
        return "the operator nonce expired (they last 60 seconds)"
    return None


@dataclass
class Authority:
    """A turn authority that was checked and found valid: the operator's own message, standing for its turn."""
    nonce_hash: str
    prompt_id: str
    prompt_text: str
    prompt_sha256: str
    excerpt: str
    session: str | None
    turn: str | None
    origin: str | None
    expires_at: float
    recorded: set = field(default_factory=set)  # events files that already hold this prompt's operator_prompt event

    @property
    def path(self) -> Path:
        return nonce_dir() / self.nonce_hash


def excerpt_of(text: str, limit: int = 100) -> str:
    one = re.sub(r"\s+", " ", text).strip()
    return one if len(one) <= limit else one[: limit - 1].rstrip() + "…"


def turn_authority() -> tuple[Authority | None, str | None]:
    """(authority, problem) for the turn authority in AEM_OPERATOR_TURN, without using it up. (None, None)
    when the variable is not set: an autonomous turn, a terminal, a script."""
    nonce = os.environ.get(TURN_VAR)
    if not nonce:
        return None, None
    digest = nonce_hash(nonce)
    path = nonce_dir() / digest
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None, "the turn authority is unknown, or its turn has ended"
    if record.get("kind") != "turn":
        return None, "AEM_OPERATOR_TURN does not hold a turn authority"
    if float(record.get("expires_at", 0)) <= time.time():
        _purge_expired(time.time())
        return None, "the turn authority expired (it lasts until the turn ends, at most 60 minutes)"
    text = str(record.get("prompt_text") or "")
    return Authority(digest, str(record.get("prompt_id") or ""), text, str(record.get("prompt_sha256") or ""),
                     excerpt_of(text), record.get("session"), record.get("turn"), record.get("origin"),
                     float(record["expires_at"])), None


def current_authority() -> Authority | None:
    """The turn authority this process is acting under, if the command that is running was accepted on one."""
    return _authority


def set_authority(a: Authority | None) -> None:
    global _authority
    _authority = a


def provenance() -> dict:
    """The fields every record written on a turn authority carries."""
    a = _authority
    return {} if a is None else {"via": "chat", "prompt_id": a.prompt_id, "prompt_excerpt": a.excerpt}


def log_use(action: str) -> None:
    """Note that an operator command succeeded on this turn authority; the plugin reads these to toast them."""
    a = _authority
    if a is None:
        return
    line = json.dumps({"ts": time.time(), "action": action, "prompt_id": a.prompt_id, "excerpt": a.excerpt},
                      ensure_ascii=False) + "\n"
    try:
        with open(a.path.with_name(a.path.name + USES_SUFFIX), "a", encoding="utf-8") as f:
            f.write(line)
    except OSError:
        pass


def require(cmd: str, action: str | None = None) -> None:
    """Entry check for an operator-only command. Raises OperatorOnly unless (a), (b) or (c) holds."""
    global _checked, _authority
    name = command_name(cmd, action)
    if name is None:
        return
    nonce_set = bool(os.environ.get(NONCE_VAR))
    nonce = nonce_problem() if nonce_set else None  # consumes it, valid or not
    if nonce_set and nonce is None:
        _checked = True
        return
    chat_problem = None
    if not nonce_set:
        turn_set = bool(os.environ.get(TURN_VAR))
        if turn_set and name in PLUGIN_ONLY:
            chat_problem = "turn authority is not accepted for this command"
            os.environ.pop(TURN_VAR, None)
        elif turn_set:
            auth, chat_problem = turn_authority()
            os.environ.pop(TURN_VAR, None)  # nothing this process starts inherits it
            if auth is not None:
                _authority = auth
                _checked = True
                return
    tty = terminal_problem(name)
    if tty is None:
        _checked = True
        return
    raise OperatorOnly(
        f"`aem {name}` is the operator's command and this process is not shown to be the operator: "
        f"{nonce if nonce_set else (chat_problem or tty)}",
        hint="Type it in your own terminal, or use its slash command in Claude Code (/approve, /stage, /allow, ...). "
             "If you are an agent: it runs only when the operator's latest message in this chat asks for it; "
             "in an autonomous turn ask the operator, and do not look for another way to run it.",
        data={"operator_only": True, "command": name})


def assert_checked(what: str) -> None:
    """Library-level backstop: the operator-writing functions refuse a caller that did not come through
    main() and its entry check (a script that imports aem and calls them directly)."""
    if not _checked:
        raise OperatorOnly(f"{what} writes the operator's records and may only run through an `aem` command "
                           "that passed the operator check",
                           hint="Type the command in your own terminal, or use its slash command in Claude Code.")
