"""import-review: map a client's Frame.io comment export to moments, shots and word IDs.

Two kinds of export:

  --notes   the client's timestamped notes on the rough cut, before we build: direction, not rulings. Written to
            <date>-notes.json; `aem moments` reads every notes file to decide which moments were asked (a note
            covers the moment's word span) and which we added.
  (review)  comments on the delivered cut: each comment that falls on a moment is an explicit ruling candidate
            for that moment, the rest video-level feedback. Written as below.

For a review, writes under <project>/reviews/<client id>/:

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
    "timecode_out": ("timecode out", "out", "out point", "end timecode", "timecode end", "end"),
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


def import_notes(ctx: Context, csv_path: str, *, fps_override: str | None = None, start_tc: str | None = None) -> dict:
    """The client's timestamped notes on the rough cut: which moments they asked for. Not rulings."""
    from . import moments as momentsmod
    src = Path(csv_path).expanduser().resolve()
    if not src.is_file():
        raise AemError(f"CSV not found: {src}")
    fps = fpsmod.parse_rate(fps_override) if fps_override else ctx.fps
    if not fps:
        raise AemError("the edit's frame rate is unknown", hint="Pass --fps N/D (the rate of the cut the notes are on).")
    text = src.read_bytes().decode("utf-8-sig", errors="replace")
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        raise AemError(f"{src.name} is empty")
    header, body = rows[0], rows[1:]
    cols = map_columns(header)
    if "timecode" not in cols:
        raise AemError(f"could not find a timecode column in {header}")
    offset = fpsmod.timecode_to_frame(start_tc, fps) if start_tc else 0
    notes, unreadable = [], []
    for n, row in enumerate(body, 2):
        rec = dict(zip(header, row))
        tc = (rec.get(cols["timecode"]) or "").strip()
        if not tc:
            continue
        note = {"row": n, "number": (rec.get(cols.get("number", "")) or "").strip() or None, "timecode": tc,
                "comment": rec.get(cols["comment"]) if "comment" in cols else "",
                "commenter": rec.get(cols.get("commenter", ""), None)}
        try:
            frame = parse_time(tc, fps) - offset
        except AemError as exc:
            unreadable.append({**note, "error": exc.message})
            continue
        note.update(frame=frame, seconds=round(float(fpsmod.frame_to_seconds(frame, fps)), 4))
        out_tc = (rec.get(cols.get("timecode_out", ""), "") or "").strip() if "timecode_out" in cols else ""
        if out_tc:
            try:
                end = parse_time(out_tc, fps) - offset
                note.update(timecode_out=out_tc, end_frame=end,
                            end_seconds=round(float(fpsmod.frame_to_seconds(end, fps)), 4))
            except AemError:
                pass
        notes.append(note)
    outdir = ctx.project_dir / "reviews" / ctx.client.id
    outdir.mkdir(parents=True, exist_ok=True)
    dest = outdir / f"{today()}-notes.csv"
    k = 2
    while dest.exists() and sha256_file(dest) != sha256_file(src):
        dest = outdir / f"{today()}-notes-{k}.csv"
        k += 1
    if not dest.exists():
        shutil.copyfile(src, dest)
    notes_path = dest.with_suffix(".json")
    write_json_atomic(notes_path, {
        "kind": "notes", "client": ctx.client.id, "project": ctx.project, "imported": ts(),
        "csv": rel_to(dest, ctx.project_dir), "csv_sha256": sha256_file(dest), "fps": fpsmod.rate_str(fps),
        "timeline_start": start_tc or "00:00:00:00", "columns": cols, "comments": notes, "unreadable": unreadable,
        "meaning": "The client's timestamped notes on the rough cut: direction (which moments were asked), not rulings."})
    index = momentsmod.build(ctx)
    momentsmod.write(ctx, index)
    by_note: dict = {}
    for m in index["moments"]:
        for n in m["notes"]:
            by_note.setdefault((n["number"], n["timecode"]), []).append(m["id"])
    mapped = [{"number": n["number"], "timecode": n["timecode"], "moments": by_note.get((n["number"], n["timecode"]), [])}
              for n in notes]
    ledger.record(ctx, "notes_import", note=f"{len(notes)} timestamped notes from {src.name}", fill_stage=True,
                  csv=rel_to(dest, ctx.project_dir), source="aem import-review --notes")
    return {"ok": True, "notes": len(notes), "unreadable": len(unreadable), "fps": fpsmod.rate_str(fps),
            "mapped": mapped, "covering_no_moment": [m for m in mapped if not m["moments"]],
            "moments": index["moments_count"], "asked": index["asked"], "added": index["added"],
            "direction": index["direction"], "files": {"csv": str(dest), "notes": str(notes_path)}, "columns": cols}


def import_review(ctx: Context, csv_path: str, *, fps_override: str | None = None, start_tc: str | None = None,
                  window_s: float = 1.0) -> dict:
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

    from . import moments as momentsmod
    index = momentsmod.build(ctx)
    momentsmod.write(ctx, index)
    window = float(momentsmod.profile(ctx).get("note_window_s", window_s))
    words, words_src = load_words(ctx)

    def moments_at(secs: float, end: float | None = None) -> list[dict]:
        """The moments a comment is on: those whose word span lies within the profile's window of its time (or of
        its range, for a comment with an out point), the one it overlaps most (or is closest to) first. The same
        rule as note coverage, so a comment maps to the moments it would be said to have asked for."""
        end = secs if end is None or end < secs else end
        hits = []
        for m in index["moments"]:
            span = m.get("word_span")
            if not span:
                continue
            a, b = span
            overlap = min(end, b) - max(secs, a)  # negative: the gap between them
            if overlap >= -window:
                hits.append((overlap, m))
        hits.sort(key=lambda h: -h[0])
        return [m for _, m in hits]

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
        end_secs = None
        out_tc = (rec.get(cols.get("timecode_out", ""), "") or "").strip() if "timecode_out" in cols else ""
        if out_tc:
            try:
                end_frame = parse_time(out_tc, fps) - offset
                end_secs = float(fpsmod.frame_to_seconds(end_frame, fps))
                entry.update(timecode_out=out_tc, end_frame=end_frame, end_seconds=round(end_secs, 4))
            except AemError:
                pass
        ms = moments_at(secs, end_secs)
        m = ms[0] if ms else None
        near = [w["id"] for w in words if secs - window <= w["start"] <= (end_secs or secs) + window]
        entry.update(frame=frame, seconds=round(secs, 4), shot=m["id"] if m else None, moment=m["id"] if m else None,
                     moments=[x["id"] for x in ms], word_ids=near, level="explicit" if m else "video",
                     about="moment: an explicit ruling candidate" if m else "the video or the edit (on no moment)")
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
        "timeline_start": start_tc or "00:00:00:00", "columns": cols, "moments": "moments/index.json", "words": words_src,
        "comments": comments,
        "check": "Confirm one comment by opening its frame and checking it shows what the comment describes.",
    }
    review_path = outdir / f"{base}-review.json"
    write_json_atomic(review_path, review)

    # Draft rulings: every delivered shot gets a row; silence is not a ruling.
    by_shot: dict = {}
    for c in comments:
        for mid in c.get("moments") or []:  # a comment over a range is a candidate on each moment it is on
            by_shot.setdefault(mid, []).append(c)
    rulings = [f"# Draft rulings · {ctx.client.name} · {ctx.project} · {date}", "",
               f"From `{rel_to(dest, ctx.project_dir)}` at {fpsmod.rate_str(fps)}. Draft written by `aem import-review`; "
               "the operator reads each comment as keep, change or remove. A moment with no comment is not a ruling: it "
               "becomes an implicit acceptance only when the whole video is accepted (`aem accept-video`).", "",
               "| Moment | Word IDs | Ruling (keep / change / remove) | Client's words | Source |", "|---|---|---|---|---|"]
    shot_names = [m["id"] for m in index["moments"]] or list(by_shot)
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
        rulings += ["", "## About the video or the edit (on no moment)", ""]
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
                     "The operator reads them as keep, change or remove in the review inbox.",
            "draft": True, "moment": shot, "level": "explicit",
        }
        drafts.append(case)
    for c in edit_notes:
        drafts.append({
            "case_id": f"{ctx.project}-video-{date}-row{c['row']}", "status": "development case", "video": ctx.project,
            "shot": None, "word_ids": c["word_ids"], "render_sha256": None, "frames_or_crops": [], "ruling": None,
            words_field: [c["comment"]], "ruling_date": None,
            "source": f"{rel_to(dest, ctx.project_dir)} row {c['row']}", "rule_ids": [], "critic_verdict_g5": None,
            "critic_agreed": None, "notes": "Draft from aem import-review: a comment on no moment, about the video or "
                                            "the edit.", "draft": True, "moment": None, "level": "video"})
    if drafts_path.exists():
        drafts_path.unlink()
    for d in drafts:
        append_jsonl(drafts_path, d)

    ledger.record(ctx, "review_import", note=f"{len(comments)} comments from {src.name}", fill_stage=True,
                  csv=rel_to(dest, ctx.project_dir), source="aem import-review")
    return {
        "ok": True, "comments": len(comments), "mapped_to_shots": sum(1 for c in comments if c.get("shot")),
        "mapped_to_moments": sum(1 for c in comments if c.get("moment")),
        "about_edit": len(edit_notes), "unreadable": len(unparsed),
        "shots_pending": [s for s in shot_names if s not in by_shot],
        "files": {"csv": str(dest), "review": str(review_path), "rulings": str(rulings_path), "drafts": str(drafts_path)},
        "columns": cols, "fps": fpsmod.rate_str(fps), "moments": index["moments_count"], "words": words_src,
    }
