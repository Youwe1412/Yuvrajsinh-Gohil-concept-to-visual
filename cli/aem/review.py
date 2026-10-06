"""import-review: map a client's Frame.io comment export to shots and word IDs.

Writes, under <project>/reviews/<client id>/:

  <date>-frameio.csv                 the CSV, byte for byte
  <date>-review.json                 every comment with its frame, time, shot and nearby word IDs
  <date>-rulings.md                  a draft rulings table, one row per delivered shot
  <date>-labelled-cases.draft.jsonl  draft labelled cases for the operator to complete

It never edits the client's decisions file or the critic's labelled cases: the client's words
reach those only through `aem client-said` and the operator's own approve or reject.
"""
from __future__ import annotations

import csv
import io
import json
import shutil
from fractions import Fraction
from pathlib import Path

from . import fps as fpsmod
from . import ledger
from .registry import Context
from .util import AemError, append_jsonl, read_jsonl, rel_to, sha256_file, today, ts, write_json_atomic

COLUMN_NAMES = {
    "timecode": ("timecode", "time code", "frame", "timestamp", "time"),
    "commenter": ("commenter", "author", "name", "user", "commented by"),
    "comment": ("comment", "comment text", "text", "message", "body"),
    "replies": ("replies", "reply", "thread"),
    "completed": ("completed", "resolved", "status", "done"),
    "number": ("#", "comment #", "id", "comment id", "number"),
}


def map_columns(header: list[str]) -> dict:
    low = [h.strip().lower() for h in header]
    found = {}
    for key, names in COLUMN_NAMES.items():
        for name in names:
            if name in low:
                found[key] = header[low.index(name)]
                break
        else:
            for i, h in enumerate(low):
                if any(n in h for n in names if len(n) > 3):
                    found[key] = header[i]
                    break
    return found


def parse_time(value: str, fps: Fraction) -> int:
    """A Frame.io time (HH:MM:SS:FF, ;FF drop-frame, or HH:MM:SS.mmm) to a frame number."""
    v = value.strip()
    if v.count(":") == 2 and "." in v:
        hh, mm, rest = v.split(":")
        secs = int(hh) * 3600 + int(mm) * 60 + Fraction(rest)
        return fpsmod.seconds_to_frame(secs, fps)
    return fpsmod.timecode_to_frame(v, fps)


def load_placements(ctx: Context, explicit: str | None, fps: Fraction) -> tuple[list[dict], str | None]:
    """Shots on the delivered timeline: [{shot, start_frame, end_frame}] in frames."""
    candidates = []
    if explicit:
        candidates.append(Path(explicit))
    settings = ctx.project_settings()
    if settings.get("placements"):
        candidates.append(ctx.project_dir / settings["placements"])
    candidates += [ctx.project_dir / "data" / "placements.json", ctx.project_dir / "data" / "edit.json"]
    for c in candidates:
        if not c.exists():
            continue
        data = json.loads(c.read_text(encoding="utf-8"))
        rows = data.get("placements", data.get("shots")) if isinstance(data, dict) else data
        out = []
        for r in rows or []:
            shot = r.get("shot") or r.get("name") or r.get("master")
            if r.get("start_frame") is not None:
                a = int(r["start_frame"])
                b = a + int(r.get("frames", r.get("duration_frames", 0)))
            elif r.get("start") is not None:
                a = fpsmod.seconds_to_frame(r["start"], fps)
                b = fpsmod.seconds_to_frame(Fraction(str(r["start"])) + Fraction(str(r.get("duration", 0))), fps)
            else:
                continue
            out.append({"shot": shot, "start_frame": a, "end_frame": b})
        return out, rel_to(c, ctx.project_dir)
    return [], None


def load_words(ctx: Context) -> tuple[list[dict], str | None]:
    """Word IDs with start times in seconds, from data/words.json or a whisper.cpp JSON."""
    for rel in ("data/words.json", "data/narration-words.json"):
        p = ctx.project_dir / rel
        if not p.exists():
            continue
        data = json.loads(p.read_text(encoding="utf-8"))
        words = []
        if isinstance(data, dict) and isinstance(data.get("words"), list):
            wf = Fraction(int(data["fps_num"]), int(data["fps_den"])) if data.get("fps_num") else ctx.fps
            for i, w in enumerate(data["words"]):
                if w.get("start") is not None:
                    start = float(w["start"])
                elif w.get("start_frame") is not None:
                    start = float(fpsmod.frame_to_seconds(int(w["start_frame"]), wf))
                else:
                    continue
                words.append({"id": w.get("id") or f"w{i}", "word": w.get("word") or w.get("text"), "start": start})
        elif isinstance(data, dict) and isinstance(data.get("transcription"), list):
            for i, seg in enumerate(data["transcription"]):
                off = seg.get("offsets") or {}
                if off.get("from") is None:
                    continue
                words.append({"id": f"w{i}", "word": (seg.get("text") or "").strip(), "start": off["from"] / 1000})
        if words:
            return words, rel
    return [], None


def import_review(ctx: Context, csv_path: str, *, fps_override: str | None = None, start_tc: str | None = None,
                  placements: str | None = None, window_s: float = 1.0) -> dict:
    src = Path(csv_path).expanduser().resolve()
    if not src.is_file():
        raise AemError(f"CSV not found: {src}")
    fps = fpsmod.parse_rate(fps_override) if fps_override else ctx.fps
    if not fps:
        raise AemError("the delivered edit's frame rate is unknown", hint="Pass --fps N/D (the delivered edit's rate).")
    raw = src.read_bytes()
    text = raw.decode("utf-8-sig", errors="replace")
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        raise AemError(f"{src.name} is empty")
    header, body = rows[0], rows[1:]
    cols = map_columns(header)
    if "timecode" not in cols or "comment" not in cols:
        raise AemError(f"could not find timecode and comment columns in {header}",
                       hint="Check the export; AEM reads the header row and never assumes column names.")
    offset = fpsmod.timecode_to_frame(start_tc, fps) if start_tc else 0

    shots, placements_src = load_placements(ctx, placements, fps)
    words, words_src = load_words(ctx)

    comments = []
    for n, row in enumerate(body, 2):
        rec = dict(zip(header, row))
        tc = (rec.get(cols["timecode"]) or "").strip()
        comment = rec.get(cols["comment"]) or ""
        if not tc and not comment.strip():
            continue
        entry = {"row": n, "timecode": tc, "comment": comment,
                 "commenter": rec.get(cols.get("commenter", ""), None),
                 "replies": rec.get(cols.get("replies", ""), None),
                 "completed": rec.get(cols.get("completed", ""), None),
                 "number": rec.get(cols.get("number", ""), None)}
        try:
            frame = parse_time(tc, fps) - offset
        except AemError as exc:
            entry.update(frame=None, error=exc.message)
            comments.append(entry)
            continue
        secs = float(fpsmod.frame_to_seconds(frame, fps))
        hit = [s["shot"] for s in shots if s["start_frame"] <= frame < s["end_frame"]]
        near = [w["id"] for w in words if abs(w["start"] - secs) <= window_s]
        entry.update(frame=frame, seconds=round(secs, 4), shot=hit[0] if hit else None,
                     also_overlapping=hit[1:] or None, word_ids=near,
                     about="shot" if hit else "edit (outside every placed shot)")
        comments.append(entry)

    outdir = ctx.project_dir / "reviews" / ctx.client.id
    outdir.mkdir(parents=True, exist_ok=True)
    date = today()
    stem = f"{date}-frameio"
    dest = outdir / f"{stem}.csv"
    k = 2
    while dest.exists() and sha256_file(dest) != sha256_file(src):
        dest = outdir / f"{stem}-{k}.csv"
        k += 1
    if not dest.exists():
        shutil.copyfile(src, dest)
    base = dest.stem.replace("-frameio", "")

    review = {
        "client": ctx.client.id, "project": ctx.project, "imported": ts(), "csv": rel_to(dest, ctx.project_dir),
        "csv_sha256": sha256_file(dest), "fps": fpsmod.rate_str(fps), "fps_source": "--fps" if fps_override else ctx.fps_source,
        "timeline_start": start_tc or "00:00:00:00", "columns": cols, "placements": placements_src, "words": words_src,
        "comments": comments,
        "check": "Confirm one comment by opening its frame and checking it shows what the comment describes.",
    }
    review_path = outdir / f"{base}-review.json"
    write_json_atomic(review_path, review)

    # Draft rulings: every delivered shot gets a row; silence is not a ruling.
    by_shot: dict = {}
    for c in comments:
        if c.get("shot"):
            by_shot.setdefault(c["shot"], []).append(c)
    rulings = [f"# Draft rulings · {ctx.client.name} · {ctx.project} · {date}", "",
               f"From `{rel_to(dest, ctx.project_dir)}` at {fpsmod.rate_str(fps)}. Draft written by `aem import-review`; "
               "the operator fills in the ruling. Silence is not a ruling: a shot with no comment stays `pending` "
               "until the client gives an explicit keep, change or remove.", "",
               "| Shot | Word IDs | Ruling (keep / change / remove) | Client's words | Source |", "|---|---|---|---|---|"]
    shot_names = [s["shot"] for s in shots] or list(by_shot)
    for shot in shot_names:
        cs = by_shot.get(shot, [])
        if cs:
            words_ = sorted({w for c in cs for w in c["word_ids"]})
            quote = " / ".join(c["comment"].replace("|", "\\|").replace("\n", " ") for c in cs)
            srcs = ", ".join(f"row {c['row']}" for c in cs)
            rulings.append(f"| {shot} | {' '.join(words_) or '-'} | TODO | {quote} | {srcs} |")
        else:
            rulings.append(f"| {shot} | - | pending (no comment) | - | - |")
    edit_notes = [c for c in comments if c.get("frame") is not None and not c.get("shot")]
    if edit_notes:
        rulings += ["", "## About the edit, not a shot", ""]
        rulings += [f"- row {c['row']} at {c['timecode']}: {c['comment']}" for c in edit_notes]
    unparsed = [c for c in comments if c.get("frame") is None]
    if unparsed:
        rulings += ["", "## Rows that could not be read", ""]
        rulings += [f"- row {c['row']}: {c.get('error')}" for c in unparsed]
    rulings_path = outdir / f"{base}-rulings.md"
    rulings_path.write_text("\n".join(rulings) + "\n", encoding="utf-8")

    # Draft labelled cases, using the client's own field names from its file header.
    header_line = next((h for h in read_jsonl(ctx.client.labelled_cases_path, keep_comments=True) if "_comment" in h), {})
    fields = list((header_line.get("fields") or {}).keys())
    words_field = next((f for f in fields if f.endswith("_words")), "client_words")
    drafts_path = outdir / f"{base}-labelled-cases.draft.jsonl"
    drafts = []
    for shot, cs in by_shot.items():
        case = {
            "case_id": f"{ctx.project}-{shot}-{date}", "status": "development case", "video": ctx.project,
            "shot": shot, "word_ids": sorted({w for c in cs for w in c["word_ids"]}), "render_sha256": None,
            "frames_or_crops": [], "ruling": None, words_field: [c["comment"] for c in cs], "ruling_date": None,
            "source": f"{rel_to(dest, ctx.project_dir)} rows " + ", ".join(str(c["row"]) for c in cs),
            "rule_ids": [], "critic_verdict_g5": None, "critic_agreed": None,
            "notes": "Draft from aem import-review. The words are the commenter's, verbatim from the CSV. "
                     "Ruling, render SHA-256 and rule IDs are for the operator to fill in.",
            "draft": True,
        }
        drafts.append(case)
    if drafts_path.exists():
        drafts_path.unlink()
    for d in drafts:
        append_jsonl(drafts_path, d)

    ledger.record(ctx, "review_import", note=f"{len(comments)} comments from {src.name}", fill_stage=True,
                  csv=rel_to(dest, ctx.project_dir), source="aem import-review")
    return {
        "ok": True, "comments": len(comments), "mapped_to_shots": sum(1 for c in comments if c.get("shot")),
        "about_edit": len(edit_notes), "unreadable": len(unparsed),
        "shots_pending": [s for s in shot_names if s not in by_shot],
        "files": {"csv": str(dest), "review": str(review_path), "rulings": str(rulings_path), "drafts": str(drafts_path)},
        "columns": cols, "fps": fpsmod.rate_str(fps), "placements": placements_src, "words": words_src,
    }
