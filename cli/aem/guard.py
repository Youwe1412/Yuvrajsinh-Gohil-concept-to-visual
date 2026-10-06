"""aem guard: the decision behind every tool call the plugin checks.

Input (stdin, JSON): {"tool": "Bash", "input": {...the tool's arguments...}, "cwd": "/session/cwd"}
Output: {"decision": "allow" | "deny", "rule": "AEM-G0n", "reason": ..., "how": ...}

These are recorded checks inside Claude Code, not security boundaries. Paths are compared after
resolving symbolic links, but a shell command is read as text: a path built at run time, an
alias or a script that touches a file is not seen.

Rules
  AEM-G01  the agent writes a protected file (approvals, events, the client's decisions,
           rules, labelled cases, the registry, and the operator-nonce folder)
  AEM-G02  the agent reads or writes outside the client's design system and projects,
           the AEM repo and shared tools
  AEM-G03  a command the client's registry entry blocks
  AEM-G05  a placement, FCPXML or delivery step names a render without a standing approval

With a turn authority (the operator's own message started this turn, see authority.py) the guard never denies:
a call that would have been denied is allowed and logged as `allowed_by_operator_prompt`, naming the rule it
would have hit and the prompt. Without one (an autonomous, looped or scheduled turn, or any turn an operator
prompt did not start) every rule applies unchanged.

There is no AEM-G04 any more (the number is not reused). The operator-only aem commands (approve,
reject, stage, ...) are refused by the CLI itself, at their entry, whoever spells them and however
(see operator.py), so the guard no longer reads shell text for them: a commit message, a heredoc or a
grep that mentions one is just text.

The client's project comes from where the call runs (AEM_PROJECT, the plugin's session pin, or the
call's working folder), never from stored state.
"""
from __future__ import annotations

import argparse
import os
import re
import shlex
from pathlib import Path

from . import approvals, clients, integrity, ledger, operator, registry
from .registry import Context
from .util import AemError, CheckFailed, aem_home, expand

RULES = {
    "AEM-G01": "protected file",
    "AEM-G02": "outside the client's folders",
    "AEM-G03": "blocked command",
    "AEM-G05": "render not approved",
}

WRITE_TOOLS = {"Write": "file_path", "Edit": "file_path", "MultiEdit": "file_path", "NotebookEdit": "notebook_path"}
READ_TOOLS = {"Read": "file_path", "Glob": "path", "Grep": "path", "LS": "path"}

# Folders every command needs whatever the client: system tools and temporary space.
SYSTEM_PATHS = ("/usr", "/bin", "/sbin", "/opt/homebrew", "/usr/local", "/System", "/Library/Developer",
                "/dev/null", "/dev/stdin", "/dev/stdout", "/dev/stderr", "/tmp", "/private/tmp",
                "/var/folders", "/private/var/folders", "/Applications")

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
    out += [_real(ctx.registry_path)]
    # Each ledger's integrity manifest is protected like the ledger.
    out += [_real(integrity.manifest_path(p)) for p in integrity.tracked_files(ctx)]
    return out


def nonce_dir() -> Path:
    """~/.aem/nonces: the plugin writes the hash of a one-time operator nonce here. The agent's
    Write and Edit tools may not touch it (cooperative: a shell still could)."""
    return _real(aem_home() / "nonces")


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


# Shell control characters that end a word even with no space around them: `ls ~/x;` is the word `~/x` and a `;`.
_PUNCT = ";&|<>()`"
_CONTROL = {";", "&", "&&", "||", "|", "|&", ";;", "(", ")", "`", ";&", ";;&"}


def _tokens(command: str) -> list[str]:
    try:
        lex = shlex.shlex(command, posix=True, punctuation_chars=_PUNCT)
        lex.whitespace_split = True
        lex.commenters = ""
        return list(lex)
    except ValueError:
        return command.split()


def bash_paths(command: str, cwd: str | None) -> list[Path]:
    """Path-like words in a shell command: absolute, ~, ./ and ../ forms, including after = and :.
    Words are split the way a shell splits them, so a path followed by `;`, `|`, `&&`, `)` or `>` is the path."""
    out = []
    for tok in _tokens(command):
        if not tok or set(tok) <= set(_PUNCT + "&"):
            continue
        for part in re.split(r"[=:]", tok) if not tok.startswith(("/", "~")) else [tok]:
            if part.startswith("//"):  # an XPath (//asset) or what follows a URL's scheme: not a file
                continue
            if part.startswith(("/", "~/", "./", "../")) or part == "~":
                out.append(_real(part, cwd))
    return out


def bash_media(command: str, cwd: str | None, exts: list[str]) -> list[Path]:
    """Renders a command names: path words, bare relative words (renders/x.mp4) and paths inside quoted code."""
    exts = [e.lower() for e in exts]
    found = {p for p in bash_paths(command, cwd) if p.suffix.lower() in exts}
    for tok in _tokens(command):
        if not tok.startswith(("/", "~", "-")) and Path(tok).suffix.lower() in exts and "://" not in tok:
            found.add(_real(tok, cwd))
    found.update(_media_in_text(command, {"media_extensions": exts}, cwd))
    return sorted(found)


# --- reads -----------------------------------------------------------------------------------------
# AEM-G05 stops a placement or delivery of a render nobody approved. It is not for looking: a command made only
# of programs that read (cat, grep, unzip, ffprobe, a script that only parses) is never a placement.

READ_ONLY_PROGRAMS = frozenset("""
cat head tail less more nl tac rev grep egrep fgrep rg ag ls ll file stat wc du df sort uniq cut tr column
paste join comm diff cmp md5 shasum sha1sum sha256sum cksum base64 strings od xxd hexdump jq xmllint xmlstarlet
unzip zipinfo zcat ffprobe mediainfo exiftool realpath readlink basename dirname which type command whereis
date echo printf pwd cd pushd popd true false test [ [[ : set export unset read wait sleep env-free
""".split())
READ_ONLY_AEM = frozenset(["status", "context", "check-approval", "check-render", "report", "drift", "import-review",
                           "integrity", "codex-config"])
INLINE_CODE_PROGRAMS = frozenset(["python", "python3", "node", "ruby", "perl"])
CODE_WRITES = re.compile(
    r"open\([^)]*,\s*['\"][^'\"]*[wax+]|\.write\(|write_text|write_bytes|\bshutil\b|\bsubprocess\b|os\.(?:system|popen|remove|"
    r"rename|replace|unlink|symlink|link|mkdir|makedirs)|\.save\(|copyfile|\.to_csv|\.dump\(|fs\.(?:write|append|unlink|rename|copy|mkdir)|"
    r"writeFile|createWriteStream|\bunlink\b|File\.(?:write|open\([^)]*['\"][wa])", re.S)
ENV_ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")


def _heredocs(command: str) -> tuple[str, list[str]]:
    """The command with heredoc bodies removed, and the bodies."""
    lines = command.split("\n")
    kept, bodies, i = [], [], 0
    while i < len(lines):
        line = lines[i]
        kept.append(line)
        m = re.search(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1", line)
        i += 1
        if m:
            body = []
            while i < len(lines) and lines[i].strip() != m.group(2):
                body.append(lines[i])
                i += 1
            i += 1
            bodies.append("\n".join(body))
    return "\n".join(kept), bodies


def _writes_redirect(tokens: list[str]) -> bool:
    for i, t in enumerate(tokens):
        if t in (">", ">>", ">|", ">&") or (t.endswith((">", ">>")) and t[:-1].isdigit()):
            nxt = tokens[i + 1] if i + 1 < len(tokens) else ""
            if t == ">&" and (nxt.isdigit() or nxt == "-"):
                continue
            if nxt in ("/dev/null", "/dev/stdout", "/dev/stderr"):
                continue
            return True
    return False


def command_reads_only(command: str) -> bool:
    """True when every program the command runs only reads (by name and flags; a script file is unknown, so not)."""
    text, bodies = _heredocs(command)
    code = bodies[:]
    any_command = False
    for logical in text.split("\n"):
        if not logical.strip() or logical.strip().startswith("#"):
            continue
        toks = _tokens(logical)
        if not toks:
            continue
        if _writes_redirect(toks):
            return False
        simple, groups = [], []
        for t in toks:
            if t in _CONTROL:
                if simple:
                    groups.append(simple)
                simple = []
            else:
                simple.append(t)
        if simple:
            groups.append(simple)
        for g in groups:
            words, skip = [], False
            for w in g:  # input redirections and their targets are not arguments
                if skip:
                    skip = False
                elif w in ("<", "<<", "<<-", "<<<") or (w.endswith(">") and w[:-1].isdigit()):
                    skip = w != "<<"  # a heredoc's marker word was already consumed with its body
                    if w == "<<":
                        skip = True
                else:
                    words.append(w)
            while words and ENV_ASSIGN.match(words[0]):
                words = words[1:]
            if not words:
                continue
            any_command = True
            prog = os.path.basename(words[0])
            args = words[1:]
            if prog == "aem":
                if not args or args[0] not in READ_ONLY_AEM:
                    return False
            elif prog in INLINE_CODE_PROGRAMS:
                if "-c" in args or "-e" in args:
                    flag = "-c" if "-c" in args else "-e"
                    k = args.index(flag)
                    code.append(" ".join(args[k + 1:]))
                elif "-" in args or (not args and bodies):
                    pass  # code from stdin: the heredoc body
                elif not args:
                    return False
                else:
                    return False  # a script file: not known to be read-only
            elif prog == "sed":
                if any(a.startswith("-i") or a == "--in-place" or re.fullmatch(r"-[a-zA-Z]*i[a-zA-Z]*", a) for a in args):
                    return False
            elif prog == "find":
                if any(a in ("-delete", "-exec", "-execdir", "-ok", "-okdir") or a.startswith("-fprint") for a in args):
                    return False
            elif prog in ("sort",):
                if any(a == "-o" or a.startswith("--output") for a in args):
                    return False
            elif prog in ("xmllint", "xmlstarlet"):
                if any(a in ("--output", "-o") or a.startswith("--output=") or a == "ed" for a in args):
                    return False
            elif prog == "awk":
                if any(a in ("-i", "--in-place") for a in args):
                    return False
            elif prog not in READ_ONLY_PROGRAMS:
                return False
    if not any_command:
        return False
    return not any(CODE_WRITES.search(c) for c in code)


def _deny(rule: str, reason: str, how: str, **extra) -> dict:
    return {"decision": "deny", "rule": rule, "rule_name": RULES[rule], "reason": reason, "how": how, **extra}


def _allow_for(ctx: Context | None, denial: dict, subject: str) -> dict | None:
    """An operator override that covers this denial: by rule ID, by command text, or by path."""
    if ctx is None or ctx.project_dir is None:
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
        # The project comes from where the call runs (AEM_PROJECT, the plugin's session pin, or cwd),
        # never from stored state. A client-only context (cwd in a design system) still guards that
        # client's files.
        ctx = registry.context(argparse.Namespace(registry=reg_path), require_project=False, cwd=cwd)
    except AemError:
        ctx = None
    reg = ctx.registry if ctx else registry.load_registry(registry.registry_path(reg_path))
    subject = args.get("command") if tool == "Bash" else (args.get(WRITE_TOOLS.get(tool, "")) or args.get(READ_TOOLS.get(tool, "")) or "")
    subject = str(subject or "")
    denial = _decide(ctx, reg, tool, args, cwd)
    if denial is None:
        return {"decision": "allow"}
    # The operator's own message started this turn: the guard exists to stop the agent acting on its own
    # authority, and here the operator has asked. Allow, and log what would have been denied.
    auth, auth_problem = operator.turn_authority()
    if auth is not None:
        operator.set_authority(auth)
        if ctx and ctx.project_dir:
            ledger.record(ctx, "allowed_by_operator_prompt", note=denial["reason"][:500], rule=denial["rule"],
                          rule_name=denial["rule_name"], tool=tool, subject=subject[:500], prompt_id=auth.prompt_id,
                          prompt_excerpt=auth.excerpt, source="aem guard")
        return {"decision": "allow", "allowed_by_operator_prompt": {
            "rule": denial["rule"], "rule_name": denial["rule_name"], "reason": denial["reason"],
            "prompt_id": auth.prompt_id, "prompt_excerpt": auth.excerpt, "logged": bool(ctx and ctx.project_dir)}}
    override = _allow_for(ctx, denial, subject)
    if override:
        if override["once"]:
            clients.consume_allow(ctx, override["allow_id"], subject=f"{tool}: {subject}", rule=denial["rule"])
        else:
            ledger.record(ctx, "allow_used", note=f"{tool}: {subject}"[:500], allow_id=override["allow_id"],
                          rule=denial["rule"], source="aem guard")
        return {"decision": "allow", "overridden": denial, "allow_id": override["allow_id"], "once": override["once"]}
    if ctx and ctx.project_dir:
        ledger.record(ctx, "denial", note=denial["reason"][:500], rule=denial["rule"], tool=tool,
                      subject=subject[:500], source="aem guard")
    return denial


def _decide(ctx: Context | None, reg: dict, tool: str, args: dict, cwd: str | None) -> dict | None:
    # The operator-nonce folder is protected whatever the project (or none).
    if tool in WRITE_TOOLS and _under(_real(str(args.get(WRITE_TOOLS[tool]) or ""), cwd), [nonce_dir()]):
        return _deny("AEM-G01", f"{nonce_dir()} is protected: the plugin writes the operator's one-time nonces there.",
                     "Ask the operator to run the command in their own terminal.", path=str(nonce_dir()))
    if ctx is None:
        return None

    protected = protected_paths(ctx)
    roots = allowed_roots(ctx, reg)
    gates = {**DEFAULT_GATES, **(ctx.client.raw.get("approval_gates") or {})}

    if tool in WRITE_TOOLS:
        target = _real(str(args.get(WRITE_TOOLS[tool]) or ""), cwd)
        if target in protected or integrity.MANIFEST_DIR in target.parts:
            return _deny("AEM-G01", f"{target} is protected: only the operator's commands write it.",
                         "Ask the operator to run the matching command (/stage, /approve, /reject, /client-said), "
                         "or to type /allow AEM-G01 <reason> for a one-time exception.", path=str(target))
        if not _under(target, roots):
            return _out_of_scope(ctx, target, "write")
        if target.suffix.lower() in gates["write_extensions"]:
            return _gate_media(ctx, _media_in_text(str(args.get("content") or args.get("new_string") or ""), gates, cwd),
                               f"writing {target.name}", gates)
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
        names = ({p.name for p in protected} | {p.relative_to(_real(ctx.client.design_system)).as_posix()
                                                 for p in protected if _under(p, [_real(ctx.client.design_system)])}
                 | {integrity.MANIFEST_DIR})
        names -= {p.name for p in protected if integrity.MANIFEST_DIR in p.parts}  # their folder name covers them
        hit = [p for p in protected if p in mentioned]
        # Names are searched in the raw text too, so a path inside a quoted script is still seen.
        hit += [Path(n) for n in names if re.search(r"(?:^|[^\w.-])" + re.escape(n) + r"(?:$|[^\w.-])", command)]
        if hit and not re.match(r"^\s*aem\s+(status|context|check-render|check-approval|drift|report|import-review|integrity|accept-edit)\b", command):
            return _deny("AEM-G01", f"this command names a protected file ({hit[0].name}). The agent does not write "
                                    "AEM ledgers or the client's records, and reads them with the Read tool.",
                         "Use the Read tool to read it. To change it, ask the operator to run the matching command, "
                         "or to type /allow AEM-G01 <reason>.", path=str(hit[0]))
        outside = [p for p in mentioned if not _under(p, roots)]
        if outside:
            return _out_of_scope(ctx, outside[0], "use")
        if any(re.search(p, command, re.I) for p in gates["command_patterns"]) and not command_reads_only(command):
            return _gate_media(ctx, bash_media(command, cwd, gates["media_extensions"]), "this placement or delivery step", gates)
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


def _gate_media(ctx: Context, media: list[Path], what: str, gates: dict) -> dict | None:
    if ctx.project_dir is None or not media:  # a client-only context has no approvals; no render named, nothing to check
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
