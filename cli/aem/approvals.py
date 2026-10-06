"""approvals.jsonl: approvals tied to the exact render, rejections, and stale marks.

The skill's line (references/project-ledgers.md) is kept field for field:

    {"gate", "scene", "render", "render_sha256", "source_revision", "approver", "date"}

AEM adds "type" ("approval" when absent, "rejection", "stale"), "ts" and a few context
fields. A line is never rewritten: staleness is a new "stale" line naming the approval's
SHA-256 and the render that replaced it.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from . import ledger
from .registry import Context
from .util import AemError, CheckFailed, append_jsonl, read_jsonl, rel_to, sha256_file, strip_private, today, ts

VERSION_SUFFIX = re.compile(r"(?:[_-]v\d+)$", re.I)


def read(ctx: Context) -> list[dict]:
    return read_jsonl(ctx.approvals_path)


def kind(line: dict) -> str:
    return line.get("type") or "approval"


def item_from_path(path: Path) -> str:
    """fd_S01_next-token_v08.mp4 -> fd_S01_next-token."""
    return VERSION_SUFFIX.sub("", path.stem)


def resolve_path(ctx: Context, path: str) -> Path:
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = (ctx.project_dir / p) if not Path.cwd().joinpath(p).exists() else Path.cwd() / p
    return p.resolve()


def item_for(ctx: Context, path: Path, item: str | None = None) -> str:
    if item:
        return item
    rel = rel_to(path, ctx.project_dir)
    for line in reversed(read(ctx)):
        if line.get("render") == rel and line.get("scene"):
            return line["scene"]
    return item_from_path(path)


def _git_revision(project_dir: Path) -> str | None:
    try:
        head = subprocess.run(["git", "-C", str(project_dir), "rev-parse", "HEAD"],
                              capture_output=True, text=True, timeout=10)
        if head.returncode != 0:
            return None
        dirty = subprocess.run(["git", "-C", str(project_dir), "status", "--porcelain"],
                               capture_output=True, text=True, timeout=10)
        return head.stdout.strip() + ("-dirty" if dirty.stdout.strip() else "")
    except (OSError, subprocess.SubprocessError):
        return None


def scene_source(ctx: Context, item: str) -> Path | None:
    """The scene's source file: aem.project.json scenes.<item>.composition, else a matching composition."""
    spec = (ctx.project_settings().get("scenes") or {}).get(item) or {}
    if spec.get("composition"):
        p = ctx.project_dir / spec["composition"]
        return p if p.exists() else None
    comps = ctx.project_dir / "compositions"
    if comps.is_dir():
        for c in sorted(comps.glob("*.html")):
            if c.stem == item or item.endswith("_" + c.stem):
                return c
    return None


def source_revision(ctx: Context, item: str, explicit: str | None = None) -> tuple[str | None, str]:
    if explicit:
        return explicit, "given"
    rev = _git_revision(ctx.project_dir)
    if rev:
        return rev, "git"
    src = scene_source(ctx, item)
    if src:
        return "sha256:" + sha256_file(src), f"SHA-256 of {rel_to(src, ctx.project_dir)}"
    return None, "unknown (no git repository and no scene source found)"


def last_render_check(ctx: Context, sha: str) -> str:
    for ev in reversed(ledger.read_events(ctx)):
        if ev.get("event") == "render_check" and ev.get("render_sha256") == sha:
            return ev.get("result", "unknown")
    return "none"


def approve(ctx: Context, item: str, path: str, gate: str, *, note=None, revision=None) -> dict:
    gate = gate.upper()
    if gate not in ctx.client.gates:
        raise AemError(f"unknown gate {gate!r}", hint=f"Gates: {', '.join(ctx.client.gates)}")
    p = resolve_path(ctx, path)
    if not p.is_file():
        raise AemError(f"render not found: {p}")
    sha = sha256_file(p)
    rev, rev_how = source_revision(ctx, item, revision)
    rec = {
        "gate": gate, "scene": item, "render": rel_to(p, ctx.project_dir), "render_sha256": sha,
        "source_revision": rev, "approver": ctx.client.operator, "date": today(),
        "type": "approval", "ts": ts(), "source_revision_from": rev_how,
        "render_check": last_render_check(ctx, sha),
    }
    if note:
        rec["note"] = note
    append_jsonl(ctx.approvals_path, rec)
    ledger.record(ctx, "approval", gate=gate, scene=item, note=note, fill_stage=False,
                  render=rec["render"], render_sha256=sha, source="aem approve")
    return rec


def reject(ctx: Context, item: str, reason: str, *, gate=None) -> dict:
    if not reason or not reason.strip():
        raise AemError("a rejection needs a reason")
    latest = latest_approval(read(ctx), item)
    rec = {
        "gate": (gate or (latest or {}).get("gate") or (ledger.current_stage(ledger.read_events(ctx)) or (None,))[0]),
        "scene": item, "render": (latest or {}).get("render"),
        "render_sha256": (latest or {}).get("render_sha256"), "source_revision": None,
        "approver": ctx.client.operator, "date": today(), "type": "rejection", "ts": ts(),
        "reason": reason.strip(),
    }
    append_jsonl(ctx.approvals_path, rec)
    ledger.record(ctx, "rejection", gate=rec["gate"], scene=item, note=reason.strip(), fill_stage=False,
                  source="aem reject")
    return rec


def latest_approval(lines: list[dict], item: str, gate: str | None = None) -> dict | None:
    for line in reversed(lines):
        if kind(line) == "approval" and line.get("scene") == item and (gate is None or line.get("gate") == gate):
            return line
    return None


def _after(a: dict, b: dict) -> bool:
    """True when line b was written after line a."""
    return b.get("_line", 0) > a.get("_line", 0)


def approval_state(lines: list[dict], approval: dict) -> dict:
    """Whether an approval still stands: not rejected after, not marked stale after."""
    for line in lines:
        if not _after(approval, line) or line.get("scene") != approval.get("scene"):
            continue
        if kind(line) == "rejection":
            return {"standing": False, "why": f"rejected on {line.get('date')}: {line.get('reason')}"}
        if kind(line) == "stale" and line.get("render_sha256") == approval.get("render_sha256"):
            return {"standing": False, "why": f"stale since {line.get('ts') or line.get('date')}: "
                                               f"{line.get('reason', 'the render changed')}"}
    return {"standing": True, "why": None}


def mark_stale(ctx: Context, item: str, new_sha: str, render_rel: str, reason: str) -> list[dict]:
    lines = read(ctx)
    marked = []
    done = set()
    for line in lines:
        if kind(line) != "approval" or line.get("scene") != item:
            continue
        sha = line.get("render_sha256")
        if sha == new_sha or sha in done:
            continue
        if not approval_state(lines, line)["standing"]:
            continue
        rec = {
            "gate": line.get("gate"), "scene": item, "render": line.get("render"), "render_sha256": sha,
            "source_revision": line.get("source_revision"), "approver": line.get("approver"),
            "date": today(), "type": "stale", "ts": ts(),
            "superseded_by_sha256": new_sha, "superseded_by_render": render_rel, "reason": reason,
        }
        append_jsonl(ctx.approvals_path, rec)
        marked.append(rec)
        done.add(sha)
    return marked


def check(ctx: Context, path: str, *, item: str | None = None, gate: str | None = None) -> dict:
    """Pass only if this exact file's SHA-256 has a standing approval."""
    p = resolve_path(ctx, path)
    if not p.is_file():
        raise CheckFailed(f"render not found: {p}", data={"ok": False, "path": str(p), "reason": "missing file"})
    sha = sha256_file(p)
    lines = read(ctx)
    it = item_for(ctx, p, item)
    matches = [l for l in lines if kind(l) == "approval" and l.get("render_sha256") == sha
               and (gate is None or l.get("gate") == gate.upper())]
    result = {"ok": False, "path": rel_to(p, ctx.project_dir), "render_sha256": sha, "scene": it}
    if matches:
        a = matches[-1]
        st = approval_state(lines, a)
        result.update(scene=a.get("scene"), approval={k: a.get(k) for k in ("gate", "scene", "render", "date", "approver")})
        if st["standing"]:
            result.update(ok=True, reason=f"approved at {a.get('gate')} on {a.get('date')} by {a.get('approver')}")
            return result
        result["reason"] = f"approval for this render is no longer standing: {st['why']}"
        result["stale"] = True
    else:
        prev = latest_approval(lines, it, gate.upper() if gate else None)
        if prev:
            result["reason"] = (f"stale: {it} was approved at {prev.get('gate')} on {prev.get('date')} for "
                                f"SHA-256 {prev.get('render_sha256', '')[:12]}…, this file is {sha[:12]}…")
            result["stale"] = True
            result["approved_sha256"] = prev.get("render_sha256")
        else:
            result["reason"] = f"no approval recorded for {it} (SHA-256 {sha[:12]}…)"
            result["stale"] = False
    result["how_to_fix"] = f"Review the render, then type /approve {it} [gate] (or run: aem approve {it} {result['path']} --gate G4)"
    raise CheckFailed(result["reason"], data=result)


def summary(ctx: Context) -> dict:
    """Per scene: latest approval and whether it stands; counts of stale and standing."""
    lines = read(ctx)
    scenes = {}
    for line in lines:
        if line.get("scene"):
            scenes.setdefault(line["scene"], None)
    out = {}
    standing = stale = 0
    for s in scenes:
        a = latest_approval(lines, s)
        if not a:
            out[s] = {"state": "rejected" if any(kind(l) == "rejection" and l.get("scene") == s for l in lines) else "none"}
            continue
        st = approval_state(lines, a)
        if st["standing"]:
            standing += 1
            out[s] = {"state": "approved", "gate": a.get("gate"), "sha256": a.get("render_sha256"), "date": a.get("date")}
        else:
            stale += 1 if "stale" in (st["why"] or "") else 0
            out[s] = {"state": "stale" if "stale" in (st["why"] or "") else "rejected", "why": st["why"],
                      "gate": a.get("gate")}
    return {"scenes": out, "standing": standing, "stale": stale}


def public(lines):
    return [strip_private(l) for l in lines]
