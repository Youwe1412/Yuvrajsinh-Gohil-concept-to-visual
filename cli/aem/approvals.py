"""approvals.jsonl: approvals tied to the exact render, rejections, and stale marks.

The skill's line (references/project-ledgers.md) is kept field for field:

    {"gate", "scene", "render", "render_sha256", "source_revision", "approver", "date"}

AEM adds "type" ("approval" when absent, "rejection", "stale"), "ts", "via" (how the operator made it:
"terminal", "slash command" or "delivery confirmation") and a few context fields. "item_kind" says what was
reviewed: "render" when absent (the skill's lines), "still" for an
image at G3, "plan_row" for one row of a plan table at G2 (with "plan_file", "plan_row" and
"plan_row_sha256"). Approvals, rejections and stale marks only act on lines of the same kind. A line is never rewritten: staleness is a new "stale" line naming the approval's
SHA-256 and the render that replaced it.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from . import ledger, operator
from .registry import Context
from .util import AemError, CheckFailed, append_jsonl, read_jsonl, rel_to, sha256_file, sha256_text, strip_private, today, ts

VERSION_SUFFIX = re.compile(r"(?:[_-]v\d+)$", re.I)


def read(ctx: Context) -> list[dict]:
    return read_jsonl(ctx.approvals_path)


def kind(line: dict) -> str:
    return line.get("type") or "approval"


def item_kind(line: dict) -> str:
    return line.get("item_kind") or "render"


STILL_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff")


def kind_for_path(path: Path) -> str:
    return "still" if path.suffix.lower() in STILL_EXTENSIONS else "render"


def plan_rows(path: Path) -> list[dict]:
    """Rows of the Markdown tables in a plan file: the first cell names the row (a shot)."""
    rows, header = [], None
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines() if path.is_file() else []
    for i, line in enumerate(lines):
        t = line.strip()
        if not t.startswith("|"):
            header = None
            continue
        cells = [c.strip() for c in t.strip("|").split("|")]
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
            continue
        nxt = lines[i + 1].strip() if i + 1 < len(lines) else ""
        if header is None and re.fullmatch(r"\|?\s*:?-{2,}.*", nxt):
            header = cells
            continue
        # Markdown emphasis or code around the name is not part of it; underscores inside are.
        name = re.sub(r"^[`*_]+|[`*_]+$", "", cells[0].strip()) if cells else ""
        if not name or header is None:
            continue
        text = " | ".join(cells)
        rows.append({"row": name, "text": text, "sha256": sha256_text(text), "line": i + 1,
                     "cells": dict(zip(header, cells))})
    return rows


def find_plan_row(path: Path, row: str) -> dict:
    hits = [r for r in plan_rows(path) if r["row"] == row]
    if not hits:
        raise AemError(f"no row {row!r} in {path.name}", hint="The row is named by its first cell.")
    if len(hits) > 1:
        raise AemError(f"{len(hits)} rows named {row!r} in {path.name}; name rows uniquely")
    return hits[0]


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


def last_checked_render(ctx: Context, item: str) -> str | None:
    for ev in reversed(ledger.read_events(ctx)):
        if ev.get("event") == "render_check" and ev.get("scene") == item and ev.get("render"):
            return ev["render"]
    return None


DELIVERY_NOTE = "Deliver pressed in AEM's delivery confirmation: approved as it was being delivered"


def approve(ctx: Context, item: str, path: str | None, gate: str | None, *, note=None, revision=None,
            row: str | None = None, delivery_confirmation: bool = False) -> dict:
    operator.assert_checked("approve")
    via = "delivery confirmation" if delivery_confirmation else operator.via()
    if delivery_confirmation:
        from . import observe
        gate = gate or observe.delivery_gate(ctx)
        note = note or DELIVERY_NOTE
    if not path:
        path = last_checked_render(ctx, item)
        if not path:
            raise AemError(f"no render given and none checked for {item}",
                           hint=f"Run aem check-render on it first, or pass the path: aem approve {item} <path> --gate G4")
        path = str(ctx.project_dir / path) if not Path(path).is_absolute() else path
    if not gate:
        cur = ledger.current_stage(ledger.read_events(ctx))
        if not cur:
            raise AemError("no gate given and no stage open", hint="Pass --gate G4 (or start a stage with /stage).")
        gate = cur[0]
    gate = gate.upper()
    if gate not in ctx.client.gates:
        raise AemError(f"unknown gate {gate!r}", hint=f"Gates: {', '.join(ctx.client.gates)}")
    p = resolve_path(ctx, path)
    if not p.is_file():
        raise AemError(f"render not found: {p}")
    if row:
        r = find_plan_row(p, row)
        rec = {
            "gate": gate, "scene": item, "render": None, "render_sha256": None, "source_revision": None,
            "approver": ctx.client.operator, "date": today(), "type": "approval", "ts": ts(),
            "item_kind": "plan_row", "plan_file": rel_to(p, ctx.project_dir), "plan_row": r["text"],
            "plan_row_sha256": r["sha256"], "via": via,
        }
        if note:
            rec["note"] = note
        append_jsonl(ctx.approvals_path, rec, track=True, by="aem approve")
        ledger.record(ctx, "approval", gate=gate, scene=item, note=note, fill_stage=False, item_kind="plan_row",
                      plan_file=rec["plan_file"], plan_row_sha256=r["sha256"], source="aem approve")
        return rec
    sha = sha256_file(p)
    rev, rev_how = source_revision(ctx, item, revision)
    ik = kind_for_path(p)
    rec = {
        "gate": gate, "scene": item, "render": rel_to(p, ctx.project_dir), "render_sha256": sha,
        "source_revision": rev, "approver": ctx.client.operator, "date": today(),
        "type": "approval", "ts": ts(), "source_revision_from": rev_how,
        "render_check": last_render_check(ctx, sha) if ik == "render" else "not a render", "via": via,
    }
    if ik != "render":
        rec["item_kind"] = ik
    if note:
        rec["note"] = note
    append_jsonl(ctx.approvals_path, rec, track=True, by="aem approve")
    ledger.record(ctx, "approval", gate=gate, scene=item, note=note, fill_stage=False,
                  render=rec["render"], render_sha256=sha, item_kind=rec.get("item_kind"), via=via,
                  source="aem approve")
    return rec


def reject(ctx: Context, item: str, reason: str, *, gate=None, path: str | None = None, row: str | None = None) -> dict:
    operator.assert_checked("reject")
    """Reject an item: the file given (or, with row, one plan row), else the item's latest approved render."""
    if not reason or not reason.strip():
        raise AemError("a rejection needs a reason")
    extra: dict = {}
    if path:
        p = resolve_path(ctx, path)
        if not p.is_file():
            raise AemError(f"file not found: {p}")
        if row:
            r = find_plan_row(p, row)
            ik, render, sha = "plan_row", None, None
            extra = {"plan_file": rel_to(p, ctx.project_dir), "plan_row": r["text"], "plan_row_sha256": r["sha256"]}
        else:
            ik, render, sha = kind_for_path(p), rel_to(p, ctx.project_dir), sha256_file(p)
        latest = latest_approval(read(ctx), item, of_kind=ik)
    else:
        ik = "render"
        latest = latest_approval(read(ctx), item)
        render, sha = (latest or {}).get("render"), (latest or {}).get("render_sha256")
    rec = {
        "gate": (gate or (latest or {}).get("gate") or (ledger.current_stage(ledger.read_events(ctx)) or (None,))[0]),
        "scene": item, "render": render, "render_sha256": sha, "source_revision": None,
        "approver": ctx.client.operator, "date": today(), "type": "rejection", "ts": ts(),
        "reason": reason.strip(), **({"item_kind": ik} if ik != "render" else {}), **extra,
        "via": operator.via(),
    }
    append_jsonl(ctx.approvals_path, rec, track=True, by="aem reject")
    ledger.record(ctx, "rejection", gate=rec["gate"], scene=item, note=reason.strip(), fill_stage=False,
                  render=render, render_sha256=sha, item_kind=rec.get("item_kind"), via=operator.via(),
                  source="aem reject")
    return rec


def latest_approval(lines: list[dict], item: str, gate: str | None = None, of_kind: str = "render") -> dict | None:
    for line in reversed(lines):
        if (kind(line) == "approval" and line.get("scene") == item and item_kind(line) == of_kind
                and (gate is None or line.get("gate") == gate)):
            return line
    return None


def _after(a: dict, b: dict) -> bool:
    """True when line b was written after line a."""
    return b.get("_line", 0) > a.get("_line", 0)


def approval_state(lines: list[dict], approval: dict) -> dict:
    """Whether an approval still stands: not rejected after, not marked stale after."""
    for line in lines:
        if (not _after(approval, line) or line.get("scene") != approval.get("scene")
                or item_kind(line) != item_kind(approval)):
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
        if kind(line) != "approval" or line.get("scene") != item or item_kind(line) != "render":
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
        append_jsonl(ctx.approvals_path, rec, track=True, by="aem check-render")
        marked.append(rec)
        done.add(sha)
    return marked


def check(ctx: Context, path: str, *, item: str | None = None, gate: str | None = None) -> dict:
    """Pass only if this exact file's SHA-256 has a standing approval. `state` says which: approved, stale (the
    file changed after its approval, or the approval was marked stale), rejected, none, or missing."""
    p = resolve_path(ctx, path)
    if not p.is_file():
        raise CheckFailed(f"render not found: {p}", data={"ok": False, "path": str(p), "reason": "missing file",
                                                          "state": "missing"})
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
            result.update(ok=True, state="approved",
                          reason=f"approved at {a.get('gate')} on {a.get('date')} by {a.get('approver')}")
            return result
        result["reason"] = f"approval for this render is no longer standing: {st['why']}"
        result["stale"] = True
        result["state"] = "rejected" if (st["why"] or "").startswith("rejected") else "stale"
    else:
        prev = latest_approval(lines, it, gate.upper() if gate else None)
        rejected = next((l for l in reversed(lines) if kind(l) == "rejection" and l.get("scene") == it
                         and item_kind(l) == "render"), None)
        if prev:
            result["reason"] = (f"stale: {it} was approved at {prev.get('gate')} on {prev.get('date')} for "
                                f"SHA-256 {prev.get('render_sha256', '')[:12]}…, this file is {sha[:12]}…")
            result["stale"] = True
            result["state"] = "stale"
            result["approved_sha256"] = prev.get("render_sha256")
        elif rejected and rejected.get("render_sha256") == sha:
            result["reason"] = f"{it} was rejected on {rejected.get('date')}: {rejected.get('reason')}"
            result["stale"] = False
            result["state"] = "rejected"
        else:
            result["reason"] = f"no approval recorded for {it} (SHA-256 {sha[:12]}…)"
            result["stale"] = False
            result["state"] = "none"
    result["how_to_fix"] = f"Review the render, then type /approve {it} [gate] (or run: aem approve {it} {result['path']} --gate G4)"
    raise CheckFailed(result["reason"], data=result)


def summary(ctx: Context) -> dict:
    """Per scene: latest approval and whether it stands; counts of stale and standing."""
    lines = read(ctx)
    scenes = {}
    for line in lines:
        if line.get("scene") and item_kind(line) == "render":
            scenes.setdefault(line["scene"], None)
    out = {}
    standing = stale = 0
    for s in scenes:
        a = latest_approval(lines, s)
        if not a:
            out[s] = {"state": "rejected" if any(kind(l) == "rejection" and l.get("scene") == s and item_kind(l) == "render"
                                                 for l in lines) else "none"}
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
