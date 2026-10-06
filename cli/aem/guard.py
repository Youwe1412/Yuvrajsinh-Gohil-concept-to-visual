"""aem guard: the decision behind every tool call the plugin checks.

Input (stdin, JSON): {"tool": "Bash", "input": {...the tool's arguments...}, "cwd": "/session/cwd"}
Output: {"decision": "allow" | "deny", "rule": "AEM-G0n", "reason": ..., "how": ...}

These are recorded checks inside Claude Code, not security boundaries. Paths are compared after
resolving symbolic links, but a shell command is read as text: a path built at run time, an
alias or a script that touches a file is not seen.

Rules
  AEM-G01  the agent writes a protected file (approvals, events, the client's decisions,
           rules, labelled cases, AEM's own active-project file and registry)
  AEM-G02  the agent reads or writes outside the active client's design system and projects,
           the AEM repo and shared tools
  AEM-G03  a command the client's registry entry blocks
  AEM-G04  the agent runs an operator-only aem command (including inbox accept and dismiss)
  AEM-G05  a placement, FCPXML or delivery step names a render without a standing approval
"""
from __future__ import annotations

import argparse
import os
import re
import shlex
from pathlib import Path

from . import approvals, clients, ledger, registry
from .registry import Context
from .util import AemError, CheckFailed, aem_home, expand

RULES = {
    "AEM-G01": "protected file",
    "AEM-G02": "outside the client's folders",
    "AEM-G03": "blocked command",
    "AEM-G04": "operator-only aem command",
    "AEM-G05": "render not approved",
}

OPERATOR_ONLY = ("approve", "reject", "client-said", "allow", "use", "new-client", "stage", "guard")
WRITE_TOOLS = {"Write": "file_path", "Edit": "file_path", "MultiEdit": "file_path", "NotebookEdit": "notebook_path"}
READ_TOOLS = {"Read": "file_path", "Glob": "path", "Grep": "path", "LS": "path"}

# Folders every command needs whatever the client: system tools and temporary space.
SYSTEM_PATHS = ("/usr", "/bin", "/sbin", "/opt/homebrew", "/usr/local", "/System", "/Library/Developer",
                "/dev/null", "/dev/stdin", "/dev/stdout", "/dev/stderr", "/tmp", "/private/tmp",
                "/var/folders", "/private/var/folders", "/Applications")

AEM_CMD = re.compile(
    r"(?:^|[\s;&|()`$])(?:\S*/)?(?:aem|bin/aem)\s+(?P<sub>[a-z-]+)"
    r"|python3?\s+(?:-m\s+aem|\S*/cli/bin/aem)\s+(?P<sub2>[a-z-]+)"
)

DEFAULT_GATES = {
    "command_patterns": [r"\bfcpxml\b", r"\bplacement\b", r"\bplace\b", r"\bdeliver(?:y)?\b"],
    "write_extensions": [".fcpxml"],
    "media_extensions": [".mp4", ".mov", ".m4v", ".mxf"],
}


def _real(p: str | Path, cwd: str | None = None) -> Path:
    p = expand(p)
    if not p.is_absolute():
        p = Path(cwd or os.getcwd()) / p
    # realpath resolves symlinks and .. even when the file does not exist yet.
    return Path(os.path.realpath(p))


def _under(p: Path, roots) -> bool:
    for r in roots:
        try:
            p.relative_to(r)
            return True
        except ValueError:
            continue
    return False


def protected_paths(ctx: Context) -> list[Path]:
    out = [_real(ctx.client.design_system / f) for f in ctx.client.protected["design_system"]]
    if ctx.project_dir:
        out += [_real(ctx.project_dir / f) for f in ctx.client.protected["project"]]
    out += [_real(aem_home() / "active.json"), _real(ctx.registry_path)]
    return out


def allowed_roots(ctx: Context | None, reg: dict) -> list[Path]:
    roots = [_real(p) for p in SYSTEM_PATHS]
    roots += [_real(p) for p in reg.get("shared_paths", [])]
    roots.append(_real(Path(__file__).resolve().parents[2]))  # the AEM repo
    if ctx:
        roots += [_real(ctx.client.design_system), _real(ctx.client.projects_root)]
        if ctx.project_dir:
            roots.append(_real(ctx.project_dir))
        for lib in ctx.client.raw.get("audio_libraries", []):
            if lib.get("path"):
                roots.append(_real(lib["path"]))
    return roots


def _tokens(command: str) -> list[str]:
    try:
        return shlex.split(command, posix=True)
    except ValueError:
        return command.split()


def bash_paths(command: str, cwd: str | None) -> list[Path]:
    """Path-like words in a shell command: absolute, ~, ./ and ../ forms, including after = and :."""
    out = []
    for tok in _tokens(command):
        for part in re.split(r"[=:]", tok) if not tok.startswith(("/", "~")) else [tok]:
            if part.startswith(("/", "~/", "./", "../")) or part == "~":
                out.append(_real(part, cwd))
    return out


def _deny(rule: str, reason: str, how: str, **extra) -> dict:
    return {"decision": "deny", "rule": rule, "rule_name": RULES[rule], "reason": reason, "how": how, **extra}


def _allow_for(ctx: Context | None, denial: dict, subject: str) -> dict | None:
    """An operator override that covers this denial: by rule ID, by command text, or by path."""
    if ctx is None:
        return None
    for a in clients.active_allows(ctx):
        t = (a.get("target") or "").strip()
        if not t:
            continue
        if t.upper() == denial["rule"] or (len(t) >= 3 and t in subject):
            return a
    return None


def check(tool: str, args: dict, cwd: str | None, *, reg_path: str | None = None) -> dict:
    """Decide one tool call. Never raises for a missing project: no project, no scope."""
    try:
        ctx = registry.context(argparse.Namespace(registry=reg_path))
    except AemError:
        ctx = None
    reg = ctx.registry if ctx else registry.load_registry(registry.registry_path(reg_path))
    subject = args.get("command") if tool == "Bash" else (args.get(WRITE_TOOLS.get(tool, "")) or args.get(READ_TOOLS.get(tool, "")) or "")
    subject = str(subject or "")
    denial = _decide(ctx, reg, tool, args, cwd)
    if denial is None:
        return {"decision": "allow"}
    override = _allow_for(ctx, denial, subject)
    if override:
        if override["once"]:
            clients.consume_allow(ctx, override["allow_id"], subject=f"{tool}: {subject}", rule=denial["rule"])
        else:
            ledger.record(ctx, "allow_used", note=f"{tool}: {subject}"[:500], allow_id=override["allow_id"],
                          rule=denial["rule"], source="aem guard")
        return {"decision": "allow", "overridden": denial, "allow_id": override["allow_id"], "once": override["once"]}
    if ctx:
        ledger.record(ctx, "denial", note=denial["reason"][:500], rule=denial["rule"], tool=tool,
                      subject=subject[:500], source="aem guard")
    return denial


def _decide(ctx: Context | None, reg: dict, tool: str, args: dict, cwd: str | None) -> dict | None:
    # AEM-G04 holds with or without an active project.
    if tool == "Bash":
        command = str(args.get("command") or "")
        for m in AEM_CMD.finditer(command):
            sub = m.group("sub") or m.group("sub2")
            if sub == "inbox" and re.match(r"\s+(?:accept|dismiss)\b", command[m.end():]):
                return _deny("AEM-G04", "`aem inbox accept` and `aem inbox dismiss` are the operator's commands, not the agent's.",
                             "Ask the operator to answer it in the review inbox (/inbox).", command="inbox")
            if sub in OPERATOR_ONLY:
                slash = {"use": "/aem use", "new-client": "/aem new-client", "stage": "/stage, /pause, /resume or /wait",
                         "guard": "nothing (the plugin runs it)"}.get(sub, f"/{sub}")
                return _deny("AEM-G04", f"`aem {sub}` is the operator's command, not the agent's.",
                             f"Ask the operator to type {slash}.", command=sub)
    if ctx is None:
        return None

    protected = protected_paths(ctx)
    roots = allowed_roots(ctx, reg)
    gates = {**DEFAULT_GATES, **(ctx.client.raw.get("approval_gates") or {})}

    if tool in WRITE_TOOLS:
        target = _real(str(args.get(WRITE_TOOLS[tool]) or ""), cwd)
        if target in protected:
            return _deny("AEM-G01", f"{target} is protected: only the operator's commands write it.",
                         "Ask the operator to run the matching command (/stage, /approve, /reject, /client-said), "
                         "or to type /allow AEM-G01 <reason> for a one-time exception.", path=str(target))
        if not _under(target, roots):
            return _out_of_scope(ctx, target, "write")
        if target.suffix.lower() in gates["write_extensions"]:
            return _gate_media(ctx, _media_in_text(str(args.get("content") or args.get("new_string") or ""), gates, cwd),
                               f"writing {target.name}", gates, require=False)
        return None

    if tool in READ_TOOLS:
        raw = args.get(READ_TOOLS[tool])
        if raw:
            target = _real(str(raw), cwd)
            if not _under(target, roots):
                return _out_of_scope(ctx, target, "read")
        return None

    if tool == "Bash":
        command = str(args.get("command") or "")
        for blocked in ctx.client.blocked_commands:
            if blocked and blocked in command:
                return _deny("AEM-G03", f"`{blocked}` is blocked for {ctx.client.name} in the AEM registry.",
                             f"The operator can type /allow \"{blocked}\" <reason> for one run.", blocked=blocked)
        mentioned = set(bash_paths(command, cwd))
        names = {p.name for p in protected} | {p.relative_to(_real(ctx.client.design_system)).as_posix()
                                                for p in protected if _under(p, [_real(ctx.client.design_system)])}
        hit = [p for p in protected if p in mentioned]
        words = set(_tokens(command))
        # Names are searched in the raw text too, so a path inside a quoted script is still seen.
        hit += [Path(n) for n in names if re.search(r"(?:^|[^\w.-])" + re.escape(n) + r"(?:$|[^\w.-])", command)]
        if hit and not re.match(r"^\s*aem\s+(status|context|check-render|check-approval|drift|report|import-review)\b", command):
            return _deny("AEM-G01", f"this command names a protected file ({hit[0].name}). The agent does not write "
                                    "AEM ledgers or the client's records, and reads them with the Read tool.",
                         "Use the Read tool to read it. To change it, ask the operator to run the matching command, "
                         "or to type /allow AEM-G01 <reason>.", path=str(hit[0]))
        outside = [p for p in mentioned if not _under(p, roots)]
        if outside:
            return _out_of_scope(ctx, outside[0], "use")
        if any(re.search(p, command, re.I) for p in gates["command_patterns"]):
            media = [p for p in mentioned if p.suffix.lower() in gates["media_extensions"]]
            names_fcpxml = any(w.lower().endswith(".fcpxml") for w in words)
            return _gate_media(ctx, media, "this placement or delivery step", gates, require=names_fcpxml)
    return None


def _out_of_scope(ctx: Context, target: Path, verb: str) -> dict:
    return _deny("AEM-G02", f"{target} is outside {ctx.client.name}'s design system and projects, the AEM repo and "
                            "the shared tools in the registry.",
                 f"If this {verb} is needed, the operator can type /allow AEM-G02 <reason> (one time), or add the "
                 "folder to shared_paths in the AEM registry.", path=str(target))


def _media_in_text(text: str, gates: dict, cwd: str | None) -> list[Path]:
    exts = "|".join(re.escape(e.lstrip(".")) for e in gates["media_extensions"])
    found = re.findall(r"(?:file://)?((?:/|~/)[^\"'<>\n]*?\.(?:" + exts + r"))\b", text, re.I)
    from urllib.parse import unquote
    return [_real(unquote(f), cwd) for f in found]


def _gate_media(ctx: Context, media: list[Path], what: str, gates: dict, *, require: bool) -> dict | None:
    if not media:
        if require:
            return _deny("AEM-G05", f"{what} names no render, so AEM cannot check its approvals.",
                         "Name each render on the command line so `aem check-approval` can check it, or the operator "
                         "can type /allow AEM-G05 <reason>.")
        return None
    for m in media:
        try:
            approvals.check(ctx, str(m))
        except CheckFailed as exc:
            item = exc.data.get("scene") or m.stem
            return _deny("AEM-G05", f"{what}: {exc.message}",
                         f"Review the render, then type /approve {item} (or /allow AEM-G05 <reason> for one run).",
                         path=str(m), stale=bool(exc.data.get("stale")))
    return None
