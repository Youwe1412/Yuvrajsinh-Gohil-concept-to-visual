"""aem rendered: after a shell command finishes, check the renders it produced.

Input (stdin, JSON): {"command": "...", "cwd": "/session/cwd", "started_at": <epoch seconds>,
                      "exit_code": 0, "probe_only": false}
Output: {"render": bool, "outputs": [...one check-render result each...], "passed": n, "failed": n,
         "stale": n, "text": "..."}

A command is a render when it matches a render pattern: the defaults below, the client's
`render_sentinel.command_patterns` in the registry and the project's
`render_sentinel.command_patterns` in aem.project.json. Its outputs are found three ways and
merged: media paths after -o/--output/--out, other media paths named on the command line, and
media files under the output folders (default `renders/`) changed since the command started.
That last one catches scripts whose output names are built inside them (bin/r.sh) and batch
renders whose names come from a data file.
"""
from __future__ import annotations

import os
import re
import shlex
from pathlib import Path

from . import approvals, render
from .registry import Context
from .util import AemError, CheckFailed, rel_to

DEFAULT_PATTERNS = [r"\bhyperframes\s+render\b", r"\bnpx\s+hyperframes\s+render\b", r"\bremotion\s+render\b"]
DEFAULT_OUTPUT_DIRS = ["renders"]
OUTPUT_FLAGS = ("-o", "--output", "--out")
# File times on some disks (exFAT keeps 2 s) and clocks between processes are not exact.
MTIME_SLACK_S = 2.0


def settings(ctx: Context) -> dict:
    client = ctx.client.raw.get("render_sentinel") or {}
    project = ctx.project_settings().get("render_sentinel") or {}
    gates = {**{"media_extensions": [".mp4", ".mov", ".m4v", ".mxf"]}, **(ctx.client.raw.get("approval_gates") or {})}
    return {
        "command_patterns": DEFAULT_PATTERNS + list(client.get("command_patterns", [])) + list(project.get("command_patterns", [])),
        "output_dirs": list(project.get("output_dirs") or client.get("output_dirs") or DEFAULT_OUTPUT_DIRS),
        "media_extensions": [e.lower() for e in (project.get("media_extensions") or client.get("media_extensions")
                                                  or gates["media_extensions"])],
        "max_outputs": int(project.get("max_outputs") or client.get("max_outputs") or 100),
    }


def is_render(command: str, cfg: dict) -> str | None:
    for p in cfg["command_patterns"]:
        if re.search(p, command):
            return p
    return None


def _tokens(command: str) -> list[str]:
    try:
        return shlex.split(command, posix=True)
    except ValueError:
        return command.split()


def _abs(p: str, base: Path) -> Path:
    q = Path(os.path.expanduser(p))
    return q if q.is_absolute() else base / q


def find_outputs(ctx: Context, command: str, cwd: Path, started_at: float | None, cfg: dict) -> tuple[list[Path], list[str]]:
    """Render files this command wrote, and how each was found."""
    exts = tuple(cfg["media_extensions"])
    bases = [cwd] + ([ctx.project_dir] if ctx.project_dir and ctx.project_dir != cwd else [])
    found: dict[Path, str] = {}
    dirs: list[Path] = []
    toks = _tokens(command)
    for i, t in enumerate(toks):
        value, how = None, None
        if t in OUTPUT_FLAGS and i + 1 < len(toks):
            value, how = toks[i + 1], f"{t} on the command line"
        elif any(t.startswith(f + "=") for f in OUTPUT_FLAGS if f.startswith("--")):
            value, how = t.split("=", 1)[1], "--output on the command line"
        elif t.lower().endswith(exts):
            value, how = t, "named on the command line"
        if value is None:
            continue
        if "$" in value or "{" in value:
            # Built at run time or a batch pattern: look in its folder for what changed.
            head = value.split("$")[0].split("{")[0]
            folder = head if head.endswith("/") else os.path.dirname(head)
            if folder:
                dirs += [_abs(folder, b) for b in bases]
            continue
        for b in bases:
            p = _abs(value, b)
            if p.is_file() and p.suffix.lower() in exts and _changed(p, started_at):
                found.setdefault(p.resolve(), how)
                break
    for d in cfg["output_dirs"]:
        dirs += [_abs(d, b) for b in bases]
    for d in dict.fromkeys(dirs):
        if not d.is_dir():
            continue
        for p in d.rglob("*"):
            if p.is_file() and p.suffix.lower() in exts and not p.name.startswith(".") and _changed(p, started_at):
                found.setdefault(p.resolve(), f"changed in {rel_to(d, ctx.project_dir)}/ since the command started")
    paths = sorted(found, key=lambda p: (p.stat().st_mtime, str(p)))
    return paths, [found[p] for p in paths]


def _changed(p: Path, started_at: float | None) -> bool:
    if started_at is None:
        return True
    try:
        return p.stat().st_mtime >= started_at - MTIME_SLACK_S
    except OSError:
        return False


def rendered(ctx: Context, command: str, cwd: str | None, started_at: float | None, exit_code: int | None = None,
             *, probe_only: bool = False) -> dict:
    """Check what a finished render command wrote. probe_only: only say whether it is a render."""
    cfg = settings(ctx)
    pattern = is_render(command, cfg)
    if not pattern or probe_only:
        return {"render": bool(pattern), "pattern": pattern, "outputs": [], "passed": 0, "failed": 0, "text": ""}
    base = Path(cwd).resolve() if cwd else (ctx.project_dir or Path.cwd())
    paths, hows = find_outputs(ctx, command, base, started_at, cfg)
    skipped = []
    if len(paths) > cfg["max_outputs"]:
        skipped = [str(p) for p in paths[:-cfg["max_outputs"]]]
        paths, hows = paths[-cfg["max_outputs"]:], hows[-cfg["max_outputs"]:]
    outputs = []
    for p, how in zip(paths, hows):
        try:
            r = render.check_render(ctx, str(p))
        except CheckFailed as exc:
            r = exc.data if exc.data.get("checks") else {"ok": False, "result": "fail", "path": str(p),
                                                          "failures": [exc.message]}
        except AemError as exc:
            r = {"ok": False, "result": "error", "path": str(p), "failures": [exc.message]}
        outputs.append({"path": r.get("path") or str(p), "scene": r.get("scene"), "result": r.get("result"),
                        "found_by": how, "failures": r.get("failures") or [],
                        "flashes": [f for f in r.get("flashes", []) if f.get("severity") == "fail"],
                        "minor_flashes": len([f for f in r.get("flashes", []) if f.get("severity") != "fail"]),
                        "render_sha256": r.get("render_sha256"), "stale_marked": len(r.get("stale_marked") or [])})
    passed = sum(1 for o in outputs if o["result"] == "pass")
    failed = len(outputs) - passed
    stale = approvals.summary(ctx)["stale"]
    out = {"render": True, "pattern": pattern, "exit_code": exit_code, "outputs": outputs, "passed": passed,
           "failed": failed, "stale": stale, "skipped": skipped}
    out["toast"], out["text"] = _texts(out)
    return out


def _reason(o: dict) -> str:
    if o["flashes"]:
        f = o["flashes"][0]
        return f"flash at frame {f['frame']} ({f.get('timecode', '?')}), {f['length']} frame(s)"
    return o["failures"][0] if o["failures"] else "failed"


def _texts(r: dict) -> tuple[str, str]:
    outs = r["outputs"]
    stale = f"; {r['stale']} approval(s) now stale" if r["stale"] else ""
    if not outs:
        why = f" (the command exited {r['exit_code']})" if r.get("exit_code") not in (None, 0) else ""
        return (f"AEM render check: no new render found{why}",
                "AEM saw a render command but found no new render file under the output folders"
                f"{why}. If it wrote one elsewhere, run `aem check-render <path>`.")
    if len(outs) == 1:
        o = outs[0]
        toast = (f"AEM render check PASS: {Path(o['path']).name}" if o["result"] == "pass"
                 else f"AEM render check FAIL: {Path(o['path']).name}: {_reason(o)}") + stale
    else:
        bad = [o for o in outs if o["result"] != "pass"]
        toast = f"AEM render check: {r['passed']} passed, {r['failed']} failed" + \
                (f" (first: {Path(bad[0]['path']).name}: {_reason(bad[0])})" if bad else "") + stale
    lines = [f"AEM checked {len(outs)} render(s) this command wrote (aem check-render, recorded in events.jsonl):"]
    for o in outs:
        line = f"- {o['result'].upper()} {o['path']} ({o['scene']})"
        if o["result"] != "pass":
            line += ": " + "; ".join(o["failures"]) if o["failures"] else ""
            for f in o["flashes"]:
                line += f"\n  flash at frame {f['frame']} ({f.get('timecode', '?')}), {f['length']} frame(s), {f['plane']}, {f['area_pct']}% of frame"
        if o["stale_marked"]:
            line += f"\n  this render changed, so {o['stale_marked']} earlier approval(s) of {o['scene']} are stale"
        lines.append(line)
    if r["failed"]:
        lines.append("Fix the failures before asking the operator to approve. `aem check-render <path>` shows every check.")
    if r.get("skipped"):
        lines.append(f"{len(r['skipped'])} older changed file(s) were not checked (max_outputs).")
    return toast, "\n".join(lines)
