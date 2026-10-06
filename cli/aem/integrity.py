"""Ledger integrity: anything written to a record outside AEM is detected.

AEM's ledgers (events.jsonl, approvals.jsonl, the client's decisions file and critic/labelled-cases.jsonl)
are written only by `aem` commands. Next to each, in a hidden `.aem-integrity/` folder, AEM keeps a manifest
of the lines it wrote: one short hash per line, appended in the same locked write. `aem integrity` compares
the file with what AEM wrote and reports every line that is not AEM's (inserted or hand-written), every AEM
line that was changed or removed, and whether the guard let the write through on an operator's message
(`allowed_by_operator_prompt`: the prompt that asked for it is named) or nothing recorded it at all.

A finding stays until the operator runs `aem accept-edit`, which records the acceptance (who, when, what,
and the prompt if it was given in chat) as an `edit_accepted` event and re-baselines the manifest.

The first time AEM writes a file with no manifest, it records the lines already there as the baseline,
trusted as they stand: AEM cannot know whether an older line was written by hand. Until then `aem integrity`
says "no baseline yet" rather than guessing.

Limits (cooperative, like the rest of AEM): the manifest sits beside the ledger, so an agent that can write
one can write the other; the guard protects both from the agent's Write and Edit tools and from shell
commands that name them, and denies those unless the operator asked in chat. What this adds is that a write
which bypasses `aem` leaves a visible difference, not that it cannot be made.
"""
from __future__ import annotations

import difflib
import fcntl
import hashlib
import json
from pathlib import Path

from . import ledger
from .registry import Context
from .util import AemError, ts

MANIFEST_DIR = ".aem-integrity"
HASH_LEN = 16


def manifest_path(path: Path) -> Path:
    return path.parent / MANIFEST_DIR / (path.name + ".jsonl")


def tracked_files(ctx: Context) -> list[Path]:
    out = []
    if ctx.project_dir:
        out += [ctx.events_path, ctx.approvals_path]
    out += [ctx.client.decisions_path, ctx.client.labelled_cases_path]
    return out


def line_hash(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()[:HASH_LEN]


def file_lines(path: Path) -> list[tuple[int, str]]:
    """(physical line number, text) of every non-blank line."""
    try:
        raw = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    return [(i, t) for i, t in enumerate(raw, 1) if t.strip()]


def _append_manifest(path: Path, record: dict) -> None:
    mp = manifest_path(path)
    mp.parent.mkdir(parents=True, exist_ok=True)
    with open(mp, "a", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            f.flush()
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def expected(path: Path) -> list[str] | None:
    """The hashes of the lines AEM wrote, in order; None when the file has no manifest yet."""
    mp = manifest_path(path)
    if not mp.exists():
        return None
    seq: list[str] = []
    for raw in mp.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            r = json.loads(raw)
        except ValueError:
            continue
        if r.get("t") in ("baseline", "set"):
            seq = list(r.get("hashes") or [])
        elif r.get("t") == "append" and r.get("sha"):
            seq.append(r["sha"])
        elif r.get("t") == "splice":
            at = max(0, min(int(r.get("at", len(seq))), len(seq)))
            seq[at:at] = list(r.get("hashes") or [])
    return seq


def ensure_baseline(path: Path, *, by: str = "first write") -> None:
    """Called before AEM's first write to a file: the lines already there become the baseline."""
    if manifest_path(path).exists():
        return
    _append_manifest(path, {"t": "baseline", "ts": ts(), "by": by, "file": path.name,
                            "hashes": [line_hash(t) for _, t in file_lines(path)],
                            "note": "lines already in the file when AEM first wrote it; trusted as they stood"})


def note_append(path: Path, line: str, *, by: str | None = None) -> None:
    """AEM appended `line` to `path` (the caller holds the file's lock)."""
    _append_manifest(path, {"t": "append", "ts": ts(), "sha": line_hash(line), **({"by": by} if by else {})})


def snapshot(path: Path, *, by: str, accepted: dict | None = None) -> None:
    """AEM rewrote `path` itself (the decisions file) or the operator accepted its present content: what is
    in the file now is what AEM stands behind."""
    _append_manifest(path, {"t": "set", "ts": ts(), "by": by, "file": path.name,
                            "hashes": [line_hash(t) for _, t in file_lines(path)],
                            **({"accepted": accepted} if accepted else {})})


def note_insert(path: Path, before_text: str, at_line: int, block: list[str], *, by: str) -> None:
    """AEM inserted `block` into `path` after the first `at_line` lines of `before_text` (the file as it stood
    just before). The insertion goes into the manifest where those lines are in what AEM wrote, so a hand edit
    elsewhere in the file is not silently accepted by it."""
    before = [t for t in before_text.splitlines()[:at_line] if t.strip()]
    m = len(before)
    cur_all = [line_hash(t) for t in before_text.splitlines() if t.strip()]
    exp = expected(path)
    at = m
    if exp is not None and exp != cur_all:
        at = len(exp)
        for op, a0, a1, b0, b1 in difflib.SequenceMatcher(None, exp, cur_all, autojunk=False).get_opcodes():
            if b0 <= m <= b1:
                at = a0 + (m - b0) if op == "equal" else a0
                break
    _append_manifest(path, {"t": "splice", "ts": ts(), "by": by, "file": path.name, "at": at,
                            "hashes": [line_hash(t) for t in block if t.strip()]})


def _short(text: str, n: int = 140) -> str:
    text = " ".join(text.split())
    return text if len(text) <= n else text[: n - 1] + "…"


def check_file(path: Path) -> dict:
    """Compare one ledger with its manifest."""
    exp = expected(path)
    if exp is None:
        return {"file": str(path), "name": path.name, "exists": path.exists(), "baseline": False, "findings": []}
    cur = file_lines(path)
    cur_hashes = [line_hash(t) for _, t in cur]
    findings = []
    if cur_hashes != exp:
        sm = difflib.SequenceMatcher(None, exp, cur_hashes, autojunk=False)
        for op, a0, a1, b0, b1 in sm.get_opcodes():
            if op == "equal":
                continue
            inserted = [{"line": cur[k][0], "text": _short(cur[k][1])} for k in range(b0, b1)]
            kind = {"insert": "inserted", "delete": "removed", "replace": "edited"}[op]
            findings.append({"kind": kind, "lines": [x["line"] for x in inserted], "now": inserted[:10],
                             "removed_count": a1 - a0,
                             "after_line": cur[b0 - 1][0] if b0 > 0 and b0 - 1 < len(cur) else 0})
    return {"file": str(path), "name": path.name, "exists": path.exists(), "baseline": True, "findings": findings}


def allowed_events(ctx: Context, path: Path) -> list[dict]:
    """The guard's allowed_by_operator_prompt events whose call named this file: the operator's message let
    the write through, and said which."""
    if not ctx.project_dir:
        return []
    out = []
    for ev in ledger.read_events(ctx):
        if ev.get("event") != "allowed_by_operator_prompt":
            continue
        subject = str(ev.get("subject") or "")
        if path.name in subject or str(path) in subject or MANIFEST_DIR in subject:
            out.append({"ts": ev.get("ts"), "tool": ev.get("tool"), "rule": ev.get("rule"),
                        "prompt_id": ev.get("prompt_id"), "prompt_excerpt": ev.get("prompt_excerpt")})
    return out


def check(ctx: Context) -> dict:
    files = []
    unexplained = explained = 0
    for p in tracked_files(ctx):
        r = check_file(p)
        if r["findings"]:
            cover = allowed_events(ctx, p)
            r["allowed_by_operator_prompt"] = cover
            r["explanation"] = (
                "the guard let a call naming this file through on the operator's message(s): "
                + ", ".join(sorted({f"{c['prompt_id']} '{c['prompt_excerpt']}'" for c in cover}))
                if cover else "outside any recorded operator prompt: nothing logged a call that could have written it")
            if cover:
                explained += len(r["findings"])
            else:
                unexplained += len(r["findings"])
        files.append(r)
    n = unexplained + explained
    return {"ok": n == 0, "findings": n, "unexplained": unexplained, "during_operator_prompt": explained,
            "files": files, "no_baseline": [f["name"] for f in files if not f["baseline"]]}


def summary(ctx: Context) -> dict:
    """A small answer for `aem status` and the context text."""
    try:
        r = check(ctx)
    except (OSError, AemError):
        return {"ok": True, "findings": 0, "files": []}
    return {"ok": r["ok"], "findings": r["findings"], "unexplained": r["unexplained"],
            "files": [f["name"] for f in r["files"] if f["findings"]]}


def accept(ctx: Context, names: list[str] | None, reason: str | None) -> dict:
    """The operator accepts what is in the ledgers now. Records an edit_accepted event for each file that
    differed, then re-baselines it."""
    from . import operator
    operator.assert_checked("accept-edit")
    report = check(ctx)
    todo = [f for f in report["files"] if f["findings"] and (not names or f["name"] in names)]
    unknown = [n for n in (names or []) if n not in {f["name"] for f in report["files"]}]
    if unknown:
        raise AemError(f"not a tracked ledger: {', '.join(unknown)}",
                       hint="Tracked: " + ", ".join(f["name"] for f in report["files"]))
    if not todo:
        return {"ok": True, "accepted": [], "message": "nothing to accept: every ledger matches what AEM wrote"}
    accepted = []
    for f in todo:
        path = Path(f["file"])
        detail = {"inserted_or_edited_lines": [x["line"] for fi in f["findings"] for x in fi["now"]],
                  "removed_lines": sum(fi["removed_count"] for fi in f["findings"] if fi["kind"] in ("removed", "edited")),
                  "kinds": sorted({fi["kind"] for fi in f["findings"]})}
        ledger.record(ctx, "edit_accepted", note=(reason or "").strip() or None, fill_stage=True,
                      file=path.name, explained_by=(f.get("allowed_by_operator_prompt") or None),
                      examples=[x["text"] for fi in f["findings"] for x in fi["now"]][:5],
                      source="aem accept-edit", **detail)
        snapshot(path, by="aem accept-edit", accepted=detail)
        accepted.append({"file": path.name, **detail})
    return {"ok": True, "accepted": accepted}
