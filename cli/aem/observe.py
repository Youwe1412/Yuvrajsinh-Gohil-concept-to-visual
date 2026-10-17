"""aem observe: every tool call the agent makes, recorded; and the one question AEM ever asks.

The Claude Code plugin sends each Bash, Read, Write, Edit, MultiEdit and NotebookEdit call here before it runs
(Codex's hook sends Bash and apply_patch). AEM appends one `observed` event to the project's events.jsonl naming
the files the call reads, writes or mentions, parsed cheaply from its arguments (a shell command is split the
way a shell splits it), and answers. It never refuses a call. Two things can follow from one:

  stage_inferred  No stage is open and the call writes a plan file, a still, a scene source (under src/ or
                  compositions/) or a render. AEM opens the gate that file belongs to (plan files G2, stills G3,
                  scene sources and renders G4, from the client's review_inbox gates), flagged as inferred, so a
                  forgotten /stage loses no time. It lasts until the operator opens a stage or the session ends.
                  The render sentinel does the same when a command writes a render.
  delivery        The call writes an FCPXML that names media, copies or moves media into a delivery folder, or
                  matches one of the client's placement or delivery patterns (approval_gates), and some of the
                  media it names has no current approval (none, re-rendered since, or rejected). The answer
                  carries the question the plugin puts to the operator ("fd_S01 was re-rendered after you
                  approved it. Deliver anyway?") and the approval that Deliver records. That confirmation is the
                  only interruption AEM makes. Codex records the delivery and asks nothing.

Input (stdin, JSON): {"tool", "input", "cwd", "session", "agent"}. With "outcome" (stopped, held, unconfirmed)
and an optional "note", it records what became of a delivery the plugin asked about, instead of a new
observation. With no project resolved nothing is recorded and nothing is asked.

Parsing is text, and cheap: a path built at run time, a script that writes files it does not name, or media a
placement tool reads from a manifest is not seen. The record shows the command itself, so a person can.
"""
from __future__ import annotations

import argparse
import os
import re
import shlex
from pathlib import Path

from . import approvals, ledger, registry
from .registry import Context
from .util import AemError, CheckFailed, expand, rel_to

OBSERVED_TOOLS = {"Bash": "command", "Read": "file_path", "Write": "file_path", "Edit": "file_path",
                  "MultiEdit": "file_path", "NotebookEdit": "notebook_path"}
WRITE_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit")
OUTCOMES = {"stopped": "delivery_stopped", "held": "delivery_held", "unconfirmed": "delivery_unconfirmed"}
MAX_LISTED = 20
COMMAND_CHARS = 500

DEFAULT_GATES = {
    "command_patterns": [r"\bfcpxml\b", r"\bplacement\b", r"\bplace\b", r"\bdeliver(?:y)?\b"],
    "write_extensions": [".fcpxml"],
    "media_extensions": [".mp4", ".mov", ".m4v", ".mxf"],
}
DEFAULT_SCENE_DIRS = ["src", "compositions"]
PLAN_EXTRA = ["style-guide.md"]


def gate_settings(ctx: Context) -> dict:
    g = {**DEFAULT_GATES, **(ctx.client.raw.get("approval_gates") or {})}
    g["media_extensions"] = [e.lower() for e in g["media_extensions"]]
    g.setdefault("delivery_patterns", list(g["command_patterns"]))
    return g


# --- splitting a shell command -------------------------------------------------------------------

# Shell control characters that end a word even with no space around them: `ls ~/x;` is the word `~/x` and a `;`.
_PUNCT = ";&|<>()`"
_CONTROL = {";", "&", "&&", "||", "|", "|&", ";;", "(", ")", "`", ";&", ";;&", "<(", ">(", "$("}
_OUT = {">", ">>", ">|", "&>", "&>>", ">&"}
_IN = {"<", "<<<"}
_HEREDOC = {"<<", "<<-"}
_QUIET = {"/dev/null", "/dev/stdout", "/dev/stderr"}


def _real(p: str | Path, cwd: str | None = None) -> Path:
    """The path as the call named it, made absolute and normalized (.. folded), symbolic links kept: the record
    shows what the agent named. Matching against the project tries the resolved form too (_within)."""
    p = expand(p)
    if not p.is_absolute():
        p = Path(cwd or os.getcwd()) / p
    return Path(os.path.normpath(p))


def _within(p: Path, root: Path) -> Path | None:
    """p relative to root, as named or with symbolic links resolved on both sides; None when outside."""
    for a, b in ((p, Path(os.path.normpath(root))), (Path(os.path.realpath(p)), Path(os.path.realpath(root)))):
        try:
            return a.relative_to(b)
        except ValueError:
            continue
    return None


def _tokens(command: str) -> list[str]:
    try:
        lex = shlex.shlex(command, posix=True, punctuation_chars=_PUNCT)
        lex.whitespace_split = True
        lex.commenters = ""
        return list(lex)
    except ValueError:
        return command.split()


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


def _strip_comment(line: str) -> str:
    """The line without its comment: a # that starts a word outside quotes, as the shell reads it."""
    quote, i = None, 0
    while i < len(line):
        ch = line[i]
        if quote:
            if ch == quote:
                quote = None
            elif ch == "\\" and quote == '"':
                i += 1
        elif ch in "'\"":
            quote = ch
        elif ch == "\\":
            i += 1
        elif ch == "#" and (i == 0 or line[i - 1].isspace() or line[i - 1] in ";&|()"):
            return line[:i]
        i += 1
    return line


def simple_commands(command: str) -> list[list[str]]:
    """Each simple command's words, heredoc bodies and comments left out, split at ; & && || | ( ) and backquotes."""
    text, _ = _heredocs(command)
    out: list[list[str]] = []
    for logical in text.split("\n"):
        logical = _strip_comment(logical)
        if not logical.strip():
            continue
        cur: list[str] = []
        for t in _tokens(logical):
            if t in _CONTROL:
                if cur:
                    out.append(cur)
                cur = []
            else:
                cur.append(t)
        if cur:
            out.append(cur)
    return out


ENV_ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
WRAPPERS = {"sudo", "command", "exec", "nohup", "time", "env", "nice", "caffeinate"}


def split_redirects(words: list[str]) -> tuple[list[str], list[str]]:
    """(the words without redirections, the files written by `>`, `>>`, `&>` and the like)."""
    args, outs, i = [], [], 0
    while i < len(words):
        w = words[i]
        nxt = words[i + 1] if i + 1 < len(words) else None
        if w in _OUT:
            if nxt is not None and not (w == ">&" and (nxt.isdigit() or nxt == "-")) and nxt not in _QUIET:
                outs.append(nxt)
            i += 2
            continue
        if w in _IN or w in _HEREDOC:
            i += 2
            continue
        if w.isdigit() and nxt in _OUT | _IN:  # the file descriptor before a redirection
            i += 1
            continue
        args.append(w)
        i += 1
    return args, outs


def program(words: list[str]) -> tuple[str, list[str]]:
    """The program a simple command runs, past environment assignments and wrappers (`sudo x`, `time x`; not
    `command -v`), and its arguments."""
    w = list(words)
    while w:
        if ENV_ASSIGN.match(w[0]):
            w = w[1:]
        elif os.path.basename(w[0]) in WRAPPERS and len(w) > 1 and not w[1].startswith("-"):
            w = w[1:]
        else:
            break
    return (os.path.basename(w[0]), w[1:]) if w else ("", [])


OUTPUT_FLAGS = ("-o", "--output", "--out")
COPY_PROGRAMS = {"cp", "mv", "rsync", "ditto", "install", "ln", "scp"}


def writes_and_copies(command: str) -> tuple[list[str], list[tuple[list[str], str]]]:
    """The words a command writes to (redirections, -o values, copy destinations, tee, touch, rm, sed -i) and
    its copy or move operations as (sources, destination)."""
    writes: list[str] = []
    copies: list[tuple[list[str], str]] = []
    for words in simple_commands(command):
        args, outs = split_redirects(words)
        writes += outs
        prog, rest = program(args)
        for i, a in enumerate(rest):
            if a in OUTPUT_FLAGS and i + 1 < len(rest):
                writes.append(rest[i + 1])
            elif a.startswith(("--output=", "--out=")):
                writes.append(a.split("=", 1)[1])
        files = [a for a in rest if a and not a.startswith("-")]
        if prog in COPY_PROGRAMS:
            if "-t" in rest and rest.index("-t") + 1 < len(rest):
                dest = rest[rest.index("-t") + 1]
                srcs = [f for f in files if f != dest]
            elif len(files) >= 2:
                dest, srcs = files[-1], files[:-1]
            else:
                continue
            copies.append((srcs, dest))
            writes.append(dest)
        elif prog in ("tee", "touch", "rm", "unlink", "truncate"):
            writes += files
        elif prog == "sed" and any(a == "--in-place" or re.fullmatch(r"-[a-zA-Z]*i\S*", a) for a in rest):
            scripted = any(a in ("-e", "-f") or a.startswith(("--expression", "--file")) for a in rest)
            writes += files if scripted else files[1:]
    return [w for w in writes if w and w not in _QUIET], copies


# A word with these in it is inline code or text (python -c "...", a message), not a file name.
_CODE = re.compile(r"[\n;'\"(){}<>|`]")


def named_paths(command: str) -> list[str]:
    """Words that name files: absolute, ~, ./ and ../ forms (also after = or :), relative words with a /, and
    names with an extension. An XPath (//asset) or a URL is not a file."""
    out: list[str] = []
    for words in simple_commands(command):
        args, outs = split_redirects(words)
        for tok in args + outs:
            if not tok or set(tok) <= set(_PUNCT) or "://" in tok or _CODE.search(tok):
                continue
            if tok.startswith("-"):  # a flag names a file only after = (--output=renders/x.mp4)
                if "=" not in tok:
                    continue
                tok = tok.split("=", 1)[1]
            parts = [tok] if tok.startswith(("/", "~")) else re.split(r"[=:]", tok)
            for part in parts:
                if not part or part.startswith("//"):
                    continue
                if (part.startswith(("/", "~/", "./", "../")) or part == "~" or "/" in part
                        or re.search(r"[^./]\.[A-Za-z][A-Za-z0-9]{0,7}$", part)):
                    out.append(part)
    return out


def bash_paths(command: str, cwd: str | None) -> list[Path]:
    """The named paths as real paths (a word built at run time, with $ or a glob, is left out)."""
    return [_real(p, cwd) for p in named_paths(command) if not re.search(r"[$*?{]", p)]


def _media_in_text(text: str, gates: dict, cwd: str | None) -> list[Path]:
    exts = "|".join(re.escape(e.lstrip(".")) for e in gates["media_extensions"])
    found = re.findall(r"(?:file://)?((?:/|~/)[^\"'<>\n]*?\.(?:" + exts + r"))\b", text, re.I)
    from urllib.parse import unquote
    return [_real(unquote(f), cwd) for f in found]


def bash_media(command: str, cwd: str | None, gates: dict) -> list[Path]:
    """Media a command names: path words, bare relative words (renders/x.mp4) and paths inside quoted code."""
    exts = tuple(gates["media_extensions"])
    found = {p for p in bash_paths(command, cwd) if p.suffix.lower() in exts}
    found.update(_media_in_text(command, gates, cwd))
    return sorted(found)


# --- reads: never a delivery ------------------------------------------------------------------------
# A command made only of programs that read (cat, grep, unzip, ffprobe, a script that only parses) is never a
# placement or a delivery, whatever it names.

READ_ONLY_PROGRAMS = frozenset("""
cat head tail less more nl tac rev grep egrep fgrep rg ag ls ll file stat wc du df sort uniq cut tr column
paste join comm diff cmp md5 shasum sha1sum sha256sum cksum base64 strings od xxd hexdump jq xmllint xmlstarlet
unzip zipinfo zcat ffprobe mediainfo exiftool realpath readlink basename dirname which type command whereis
date echo printf pwd cd pushd popd true false test [ [[ : set export unset read wait sleep find
""".split())
READ_ONLY_AEM = frozenset(["status", "context", "recall", "check-approval", "check-render", "report", "drift",
                           "import-review", "integrity", "codex-config", "rounds", "chose"])
INLINE_CODE_PROGRAMS = frozenset(["python", "python3", "node", "ruby", "perl"])
CODE_WRITES = re.compile(
    r"open\([^)]*,\s*['\"][^'\"]*[wax+]|\.write\(|write_text|write_bytes|\bshutil\b|\bsubprocess\b|os\.(?:system|popen|remove|"
    r"rename|replace|unlink|symlink|link|mkdir|makedirs)|\.save\(|copyfile|\.to_csv|\.dump\(|fs\.(?:write|append|unlink|rename|copy|mkdir)|"
    r"writeFile|createWriteStream|\bunlink\b|File\.(?:write|open\([^)]*['\"][wa])", re.S)


def command_reads_only(command: str) -> bool:
    """True when every program the command runs only reads (by name and flags; a script file is unknown, so not)."""
    _text, bodies = _heredocs(command)
    code = bodies[:]
    any_command = False
    for words in simple_commands(command):
        args, outs = split_redirects(words)
        if outs:
            return False
        prog, rest = program(args)
        if not prog:
            continue
        any_command = True
        if prog == "aem":
            if not rest or (rest[0] not in READ_ONLY_AEM and not (rest[0] == "inbox" and rest[1:2] in ([], ["list"]))):
                return False
        elif prog in INLINE_CODE_PROGRAMS:
            if "-c" in rest or "-e" in rest:
                flag = "-c" if "-c" in rest else "-e"
                code.append(" ".join(rest[rest.index(flag) + 1:]))
            elif "-" in rest or (not rest and bodies):
                pass  # code from stdin: the heredoc body
            else:
                return False  # a script file, or an interactive interpreter: not known to only read
        elif prog == "sed":
            if any(a.startswith("-i") or a == "--in-place" or re.fullmatch(r"-[a-zA-Z]*i[a-zA-Z]*", a) for a in rest):
                return False
        elif prog == "find":
            if any(a in ("-delete", "-exec", "-execdir", "-ok", "-okdir") or a.startswith("-fprint") for a in rest):
                return False
        elif prog == "sort":
            if any(a == "-o" or a.startswith("--output") for a in rest):
                return False
        elif prog in ("xmllint", "xmlstarlet"):
            if any(a in ("--output", "-o") or a.startswith("--output=") or a == "ed" for a in rest):
                return False
        elif prog not in READ_ONLY_PROGRAMS:
            return False
    if not any_command:
        return False
    return not any(CODE_WRITES.search(c) for c in code)


# --- what a call names ------------------------------------------------------------------------------

def _show(p: Path | str, ctx: Context) -> str:
    """A path as the record shows it: relative to the project inside it, ~/… under the home folder."""
    if isinstance(p, str):
        return p
    rel = _within(p, ctx.project_dir) if ctx.project_dir else None
    if rel is not None:
        return rel.as_posix()
    try:
        return "~/" + p.relative_to(Path.home()).as_posix()
    except ValueError:
        return p.as_posix()


def _listed(items, ctx: Context) -> list[str]:
    out: list[str] = []
    for p in items:
        s = _show(p, ctx)
        if s not in out:
            out.append(s)
    return out[:MAX_LISTED]


PATCH_FILE = re.compile(r"^\*\*\* (?:Add|Update|Delete) File: (.+)$|^\*\*\* Move to: (.+)$", re.M)


def patch_files(patch: str) -> tuple[list[str], str]:
    """The files a Codex apply_patch adds, updates, deletes or moves to, and the lines it adds."""
    files = [(m.group(1) or m.group(2) or "").strip() for m in PATCH_FILE.finditer(patch or "")]
    added = "\n".join(l[1:] for l in (patch or "").splitlines() if l.startswith("+") and not l.startswith("+++"))
    return [f for f in files if f], added


def parse_call(tool: str, args: dict, cwd: str | None) -> dict:
    """What one call reads, writes and names, as real paths (a word built at run time stays as written)."""
    if tool == "apply_patch":
        files, added = patch_files(str(args.get("command") or args.get("patch") or args.get("input") or ""))
        return {"command": None, "paths": [], "writes": [_real(f, cwd) for f in files], "copies": [], "reads": [],
                "added": added}
    if tool == "Bash":
        command = str(args.get("command") or "")
        writes, copies = writes_and_copies(command)

        def real(w: str):
            return w if re.search(r"[$*?{]", w) else _real(w, cwd)
        return {"command": command, "paths": bash_paths(command, cwd), "writes": [real(w) for w in writes],
                "copies": [([real(s) for s in srcs], real(dest)) for srcs, dest in copies], "reads": []}
    key = OBSERVED_TOOLS.get(tool)
    target = str(args.get(key) or "") if key else ""
    path = [_real(target, cwd)] if target else []
    if tool in WRITE_TOOLS:
        return {"command": None, "paths": [], "writes": path, "copies": [], "reads": []}
    return {"command": None, "paths": [], "writes": [], "copies": [], "reads": path}


# --- stage inference ------------------------------------------------------------------------------

def inference_settings(ctx: Context) -> dict:
    from . import inbox, sentinel
    ri = inbox.settings(ctx)
    own = {**(ctx.client.raw.get("stage_inference") or {}), **(ctx.project_settings().get("stage_inference") or {})}
    gates = ri["gates"]
    return {
        "plan_files": list(own.get("plan_files") or (list(ri["plan_files"]) + PLAN_EXTRA)),
        "stills_dirs": list(own.get("stills_dirs") or ri["stills_dirs"]),
        "scene_dirs": list(own.get("scene_dirs") or DEFAULT_SCENE_DIRS),
        "render_dirs": list(own.get("render_dirs") or sentinel.settings(ctx)["output_dirs"]),
        "media_extensions": gate_settings(ctx)["media_extensions"],
        "gates": {"plan": gates["plan_row"], "still": gates["still"], "scene": gates["render"],
                  "render": gates["render"], **(own.get("gates") or {})},
    }


def gate_for_file(ctx: Context, path: Path, cfg: dict | None = None) -> tuple[str, str] | None:
    """(gate, why) for a file the work changed, or None: plan files, stills, scene sources and renders."""
    if not ctx.project_dir or not isinstance(path, Path):
        return None
    rel = _within(path, ctx.project_dir)
    if rel is None or not rel.parts:
        return None
    cfg = cfg or inference_settings(ctx)
    top = rel.parts[0] if len(rel.parts) > 1 else ""
    suffix = path.suffix.lower()
    if rel.name in cfg["plan_files"]:
        kind = "plan"
    elif top in cfg["stills_dirs"] or (top in cfg["scene_dirs"] and suffix in approvals.STILL_EXTENSIONS):
        kind = "still"
    elif suffix in cfg["media_extensions"] and top in cfg["render_dirs"]:
        kind = "render"
    elif top in cfg["scene_dirs"]:
        kind = "scene"
    else:
        return None
    gate = cfg["gates"].get(kind)
    if not gate or gate not in ctx.client.gates:
        return None
    names = {"plan": "a plan file", "still": "a still", "scene": "a scene source", "render": "a render"}
    return gate, f"{names[kind]} changed: {rel.as_posix()}"


def infer_stage(ctx: Context, events: list[dict], path: Path, *, session: str | None = None,
                source: str = "aem observe", render: bool = False) -> dict | None:
    """Open the gate a changed file belongs to, flagged as inferred, when no stage is open. render=True: the file
    is a render a render command wrote, wherever it is."""
    if ledger.current_stage(events):
        return None
    if render:
        gate = inference_settings(ctx)["gates"]["render"]
        hit = (gate, f"a render changed: {_show(path, ctx)}") if gate in ctx.client.gates else None
    else:
        hit = gate_for_file(ctx, path)
    if not hit:
        return None
    gate, why = hit
    return ledger.record(ctx, "stage_inferred", gate=gate, scene=None, note=why, fill_stage=False, inferred=True,
                         inferred_from=_show(path, ctx), session=session, source=source)


# --- delivery ---------------------------------------------------------------------------------------

def delivery_gate(ctx: Context, events: list[dict] | None = None) -> str:
    """The gate a delivery approval is recorded at: the client's deliver gate (Joel's G6), else the open stage's,
    else the last gate."""
    named = next((g for g, name in ctx.client.gates.items() if "deliver" in str(name).lower()), None)
    if named:
        return named
    cur = ledger.current_stage(events if events is not None else ledger.read_events(ctx))
    return cur[0] if cur else list(ctx.client.gates)[-1]


def _text_of(args: dict) -> str:
    edits = args.get("edits") or []
    parts = [str(args.get(k) or "") for k in ("content", "new_string", "new_source")]
    parts += [str(e.get("new_string") or "") for e in edits if isinstance(e, dict)]
    return "\n".join(parts)


def find_delivery(ctx: Context, tool: str, args: dict, cwd: str | None, parsed: dict) -> dict | None:
    """The media a delivery names and the kinds of delivery it is, or None when the call is not one."""
    g = gate_settings(ctx)
    if tool in WRITE_TOOLS or tool == "apply_patch":
        exts = [e.lower() for e in g["write_extensions"]]
        if not any(isinstance(t, Path) and t.suffix.lower() in exts for t in parsed["writes"]):
            return None
        text = parsed.get("added") if tool == "apply_patch" else _text_of(args)
        media = [m for m in _media_in_text(text or "", g, cwd) if m.is_file()]
        return {"kinds": ["fcpxml"], "media": sorted(set(media))} if media else None
    if tool != "Bash":
        return None
    command = parsed["command"] or ""
    if command_reads_only(command):
        return None
    outputs = {w for w in parsed["writes"] if isinstance(w, Path)}
    media = [m for m in bash_media(command, cwd, g) if m.is_file() and m not in outputs]
    if not media:
        return None
    kinds = []
    if re.search(r"\.fcpxmld?\b", command, re.I):
        kinds.append("fcpxml")
    for srcs, dest in parsed["copies"]:
        if any(isinstance(s, Path) and s in media for s in srcs) and any(
                re.search(p, str(dest), re.I) for p in g["delivery_patterns"]):
            kinds.append("copy")
            break
    if not kinds and any(re.search(p, command, re.I) for p in g["command_patterns"]):
        kinds.append("placement")
    return {"kinds": kinds, "media": media} if kinds else None


def _state(ctx: Context, path: Path) -> dict:
    try:
        r = approvals.check(ctx, str(path))
        return {"path": _show(path, ctx), "abs": str(path), "item": r.get("scene"), "state": "approved", "why": r["reason"]}
    except CheckFailed as exc:
        d = exc.data
        return {"path": _show(path, ctx), "abs": str(path), "item": d.get("scene") or approvals.item_from_path(path),
                "state": d.get("state") or "none", "why": exc.message}


def question(unapproved: list[dict]) -> str:
    def one(u: dict) -> str:
        if u["state"] == "stale":
            return f"{u['item']} was re-rendered after you approved it"
        if u["state"] == "rejected":
            return f"{u['item']} was rejected"
        return f"{u['item']} has no approval"
    if len(unapproved) == 1:
        return one(unapproved[0]) + ". Deliver anyway?"
    return "; ".join(one(u) for u in unapproved[:4]) + (f"; and {len(unapproved) - 4} more" if len(unapproved) > 4 else "") \
        + ". Deliver anyway?"


def _slash_word(s: str) -> str:
    return f'"{s}"' if re.search(r"\s", s) else s


def delivery_check(ctx: Context, found: dict, events: list[dict]) -> dict:
    states = [_state(ctx, m) for m in found["media"]]
    unapproved = [s for s in states if s["state"] != "approved"]
    gate = delivery_gate(ctx, events)
    out = {"kinds": found["kinds"], "media": [{k: s[k] for k in ("path", "item", "state")} for s in states],
           "unapproved": [{k: s[k] for k in ("path", "item", "state", "why")} for s in unapproved], "gate": gate}
    if unapproved:
        out["question"] = question(unapproved)
        out["approve"] = [["approve", s["item"], s["abs"], "--gate", gate, "--delivery-confirmation"] for s in unapproved]
        out["slash"] = [f"/approve {_slash_word(s['item'])} {_slash_word(s['path'])} {gate}" for s in unapproved]
    return out


# --- the command --------------------------------------------------------------------------------------

def observe(req: dict, *, reg_path: str | None = None) -> dict:
    """Record one tool call (or what became of a delivery) and say whether it needs the operator's confirmation."""
    tool = str(req.get("tool") or "")
    args = dict(req.get("input") or {})
    cwd = req.get("cwd")
    try:
        ctx = registry.context(argparse.Namespace(registry=reg_path), cwd=cwd)
    except AemError:
        return {"observed": False, "delivery": None, "note": "no project resolved"}
    if tool not in OBSERVED_TOOLS and tool != "apply_patch":
        return {"observed": False, "delivery": None, "note": f"{tool or 'this tool'} is not observed"}
    events = ledger.read_events(ctx)
    parsed = parse_call(tool, args, cwd)
    found = find_delivery(ctx, tool, args, cwd, parsed)
    delivery = delivery_check(ctx, found, events) if found else None
    who = {"session": req.get("session"), "agent": req.get("agent")}

    outcome = req.get("outcome")
    if outcome:
        if outcome not in OUTCOMES:
            raise AemError(f"outcome must be one of {', '.join(OUTCOMES)}")
        ev = ledger.record(ctx, OUTCOMES[outcome], note=req.get("note"), fill_stage=True, tool=tool,
                           command=(parsed["command"] or "")[:COMMAND_CHARS] or None,
                           media=(delivery or {}).get("media"), source="aem observe", **who)
        return {"observed": True, "event": ev, "delivery": delivery}

    inferred = None
    for w in parsed["writes"]:
        if isinstance(w, Path):
            inferred = infer_stage(ctx, events, w, session=who["session"])
            if inferred:
                break
    fields = {"tool": tool, "command": (parsed["command"] or "")[:COMMAND_CHARS] or None,
              "reads": _listed(parsed["reads"], ctx) or None,
              "writes": _listed(parsed["writes"], ctx) or None,
              "paths": _listed(parsed["paths"], ctx) or None}
    if parsed["command"] and len(parsed["command"]) > COMMAND_CHARS:
        fields["command_chars"] = len(parsed["command"])
    if delivery:
        fields["delivery"] = {k: delivery[k] for k in ("kinds", "media")}
    gate, scene = (inferred["gate"], None) if inferred else (ledger.current_stage(events) or (None, None))
    ev = ledger.record(ctx, "observed", gate=gate, scene=scene, note=None, fill_stage=False,
                       source="aem observe", **fields, **who)
    return {"observed": True, "event": ev, "inferred": inferred, "delivery": delivery}
