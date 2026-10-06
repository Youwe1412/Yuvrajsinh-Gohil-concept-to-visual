"""aem evidence: what a render looks like, written so that Claude, or a critic subagent given one file, can see it.

For one render (the sentinel runs it after every render), under reviews/<moment>/<version>/:

  poses/fNNNN.png   one per readable pose: the frame where the picture settles after each cue word, plus the first
                    and last frame; 1920 px wide
  phone/fNNNN.png   each pose 390 px wide, the width of a phone held upright: what a phone viewer can read
  strip.jpg         eight frames around the fastest transition, side by side
  sync.json         per cue word: the word's onset frame, the frame the picture starts to change, the frame the
                    readable pose settles, and the offset in frames (settle - onset)
  facts.json        the render check: spec, frame count, flashes, SHA-256 (what the sentinel reported)
  evidence.md       all of the above with relative image paths, the moment's contract and the rule IDs that apply

Cue words come from --cue-at (seconds into the scene, for hand-measured onsets), --cue (word IDs), the shot list's
cue column, or, when none is written, from motion: each movement is paired with the moment's word nearest its start.
Readable poses are found in the frames themselves: a run of at least a quarter second in which nothing changes.

For a cut (--video): reviews/video/<cut>/, one contact sheet per moment from the assembled cut at the moment's word
span, and video.md, so moments can be reviewed in context before delivery, the way the client will see them.

Advisory only: nothing here blocks anything. Cheap by design: one 160x90 grey decode for motion, one ffmpeg pass for
the poses and their phone copies, one for the strip.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import time
from fractions import Fraction
from pathlib import Path

from . import approvals, fps as fpsmod, ledger, moments as momentsmod, render
from .registry import Context
from .util import AemError, CheckFailed, rel_to, sha256_file, strip_private, write_json_atomic

AW, AH = 160, 90          # analysis grid
QUIET = 0.08              # mean grey-level change per pixel under which a frame is still
HOLD_S = 0.25             # still this long: a readable pose
CUE_WINDOW_S = 0.6        # a movement this close to a cue word answers it
POSE_W, PHONE_W, STRIP_W = 1920, 390, 480
MAX_POSES = 16
SHEET_FRAMES = 6

DEFAULT_RULES = {}  # which rule IDs evidence speaks to is the client's; see the registry's evidence.rules


def settings(ctx: Context) -> dict:
    cfg = {"max_per_command": 6, "rules": dict(DEFAULT_RULES), "quiet": QUIET, "hold_s": HOLD_S}
    cfg.update(ctx.client.raw.get("evidence") or {})
    cfg.update(ctx.project_settings().get("evidence") or {})
    return cfg


def _ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if not path:
        raise AemError("ffmpeg not found on PATH", hint="Install FFmpeg (brew install ffmpeg).")
    return path


def motion(path: Path) -> list[float]:
    """Mean absolute grey change per pixel from the previous frame (0 for the first), at 160x90."""
    p = subprocess.run([_ffmpeg(), "-v", "error", "-i", str(path), "-vf", f"scale={AW}:{AH}:flags=area,format=gray",
                        "-f", "rawvideo", "-"], capture_output=True)
    if p.returncode != 0:
        raise CheckFailed(f"ffmpeg could not decode {path.name}: {p.stderr.decode(errors='replace')[:300]}")
    data, size = p.stdout, AW * AH
    n = len(data) // size
    out = [0.0]
    prev = data[0:size]
    for i in range(1, n):
        cur = data[i * size:(i + 1) * size]
        out.append(sum(abs(a - b) for a, b in zip(cur, prev)) / size)
        prev = cur
    return out


def segments(d: list[float], quiet: float, hold: int) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    """(still runs of at least `hold` frames, movements between them), each as (first, last) frame."""
    still, moves, i, n = [], [], 0, len(d)
    while i < n:
        j = i
        if d[i] < quiet:
            while j + 1 < n and d[j + 1] < quiet:
                j += 1
            if j - i + 1 >= hold or i == 0 or j == n - 1:
                still.append((i, j))
        else:
            while j + 1 < n and d[j + 1] >= quiet:
                j += 1
            moves.append((i, j))
        i = j + 1
    return still, moves


def _settle_after(still: list[tuple[int, int]], frame: int, hold: int) -> int | None:
    for a, b in still:
        if a >= frame and b - a + 1 >= hold:
            return a
    return None


def cues_for(ctx: Context, m: dict | None, words: list[dict], fps: Fraction, moves: list[tuple[int, int]],
             *, cue_at: list[float], cue_ids: list[str]) -> tuple[list[dict], str]:
    """[{id, word, onset_frame}] and where they came from."""
    start = (m or {}).get("start")
    if cue_at:
        return [{"id": None, "word": f"at {t:g} s", "onset_frame": round(t * float(fps))} for t in cue_at], "--cue-at"
    by_id = {w["id"]: w for w in words}
    ids = cue_ids or (m or {}).get("cue_ids") or []
    if ids:
        if start is None:
            return [], "cue words given, but the moment has no placement, so their times in the scene are unknown"
        out = [{"id": i, "word": by_id[i]["word"], "onset_frame": round((by_id[i]["start"] - start) * float(fps))}
               for i in ids if i in by_id]
        return out, "--cue" if cue_ids else "the shot list's cue column"
    if start is None or not (m or {}).get("word_ids"):
        return [], "no cue words: the moment has no placement or no words, so sync is not measured"
    mine = [by_id[i] for i in m["word_ids"] if i in by_id]
    out, used = [], set()
    for a, _b in moves:
        if a == 0:
            continue
        best = min(mine, key=lambda w: abs((w["start"] - start) * float(fps) - a), default=None)
        if best and abs((best["start"] - start) * float(fps) - a) <= CUE_WINDOW_S * float(fps) and best["id"] not in used:
            used.add(best["id"])
            out.append({"id": best["id"], "word": best["word"], "onset_frame": round((best["start"] - start) * float(fps))})
    return out, "inferred: each movement paired with the moment's nearest word (no cue column in the shot list)"


def sync(cues: list[dict], d: list[float], quiet: float, hold: int, fps: Fraction) -> list[dict]:
    still, moves = segments(d, quiet, hold)
    win = round(CUE_WINDOW_S * float(fps))
    out = []
    for c in cues:
        on = c["onset_frame"]
        near = [mv for mv in moves if abs(mv[0] - on) <= win]
        mv = min(near, key=lambda x: abs(x[0] - on)) if near else None
        settle = _settle_after(still, mv[1] + 1, hold) if mv else None
        out.append({**c, "change_frame": mv[0] if mv else None, "settle_frame": settle,
                    "offset_frames": (settle - on) if settle is not None else None,
                    "lead_frames": (mv[0] - on) if mv else None,
                    "note": None if mv else "nothing moves within 0.6 s of this cue"})
    return out


def _extract(path: Path, frames: list[int], outdir: Path) -> dict[int, tuple[str, str]]:
    """PNG of each frame at 1920 and at phone width; {frame: (pose path, phone path)}."""
    frames = sorted(set(frames))
    (outdir / "poses").mkdir(parents=True, exist_ok=True)
    (outdir / "phone").mkdir(parents=True, exist_ok=True)
    sel = "+".join(f"eq(n\\,{f})" for f in frames)
    tmp_big, tmp_small = outdir / "poses" / ".x%04d.png", outdir / "phone" / ".x%04d.png"
    graph = f"select='{sel}',split=2[a][b];[a]scale={POSE_W}:-2:flags=lanczos[big];[b]scale={PHONE_W}:-2:flags=lanczos[small]"
    p = subprocess.run([_ffmpeg(), "-v", "error", "-y", "-i", str(path), "-filter_complex", graph,
                        "-map", "[big]", "-fps_mode", "passthrough", str(tmp_big),
                        "-map", "[small]", "-fps_mode", "passthrough", str(tmp_small)], capture_output=True)
    if p.returncode != 0:
        raise CheckFailed(f"ffmpeg could not extract frames: {p.stderr.decode(errors='replace')[:300]}")
    out = {}
    for k, f in enumerate(frames, 1):
        names = []
        for sub in ("poses", "phone"):
            src = outdir / sub / f".x{k:04d}.png"
            dst = outdir / sub / f"f{f:04d}.png"
            if src.exists():
                src.replace(dst)
                names.append(f"{sub}/{dst.name}")
        if len(names) == 2:
            out[f] = (names[0], names[1])
    return out


def _strip(path: Path, first: int, outdir: Path, n: int) -> str | None:
    frames = list(range(first, first + n))
    sel = "+".join(f"eq(n\\,{f})" for f in frames)
    dst = outdir / "strip.jpg"
    p = subprocess.run([_ffmpeg(), "-v", "error", "-y", "-i", str(path), "-vf",
                        f"select='{sel}',scale={STRIP_W}:-2,tile={n}x1", "-frames:v", "1", "-q:v", "3", str(dst)],
                       capture_output=True)
    return "strip.jpg" if p.returncode == 0 and dst.exists() else None


def _facts(ctx: Context, path: Path, given: dict | None) -> dict:
    if given and given.get("checks"):
        return given
    try:
        return render.check_render(ctx, str(path), record=False)
    except CheckFailed as exc:
        return exc.data if exc.data.get("checks") else {"result": "error", "failures": [exc.message]}


def _rules(ctx: Context, m: dict | None) -> list[tuple[str, str]]:
    """(rule ID, what it is checked against here): the client's evidence rules, then the moment's own."""
    cfg = settings(ctx)["rules"]
    out = []
    names = {"sync": "sync.json and the poses", "phone": "phone/*.png", "flash": "strip.jpg and facts.json flashes",
             "motion": "strip.jpg", "contract": "the contract above and the poses", "critic": "how findings are reported"}
    for key, ids in cfg.items():
        for rid in ids if isinstance(ids, list) else [ids]:
            out.append((rid, names.get(key, key)))
    for rid in (m or {}).get("rule_ids") or []:
        if rid not in [r for r, _ in out]:
            out.append((rid, "the moment's own rule (shot list)"))
    return out


def build(ctx: Context, render_path: str, *, facts: dict | None = None, moment: str | None = None,
          cue_at: list[float] | None = None, cue_ids: list[str] | None = None, record: bool = True) -> dict:
    t0 = time.monotonic()
    path = approvals.resolve_path(ctx, render_path)
    if not path.is_file():
        raise AemError(f"render not found: {path}")
    cfg = settings(ctx)
    fct = _facts(ctx, path, facts)
    rate = None
    try:
        rate = fpsmod.parse_rate(((fct.get("probe") or {}).get("r_frame_rate")) or "")
    except AemError:
        rate = ctx.fps
    rate = rate or ctx.fps or Fraction(25)
    index = momentsmod.read_index(ctx) or momentsmod.build(ctx)
    item = approvals.item_from_path(path)
    m = momentsmod.find(index, moment or item)
    mid = (m or {}).get("id") or moment or item
    version = momentsmod.version_of(path)
    sha = fct.get("render_sha256") or sha256_file(path)
    if version == "unversioned":
        version = f"sha-{sha[:12]}"
    outdir = ctx.project_dir / "reviews" / mid.replace("#", "-") / version
    outdir.mkdir(parents=True, exist_ok=True)

    d = motion(path)
    n = len(d)
    quiet, hold = float(cfg.get("quiet", QUIET)), max(2, round(float(cfg.get("hold_s", HOLD_S)) * float(rate)))
    still, moves = segments(d, quiet, hold)
    words, _src = momentsmod.load_words(ctx)
    cues, cue_src = cues_for(ctx, m, words, rate, moves, cue_at=cue_at or [], cue_ids=cue_ids or [])
    s = sync(cues, d, quiet, hold, rate)
    poses = [0] + [c["settle_frame"] if c["settle_frame"] is not None else min(max(c["onset_frame"], 0), n - 1) for c in s]
    if not s:
        poses += [a for a, b in still if b - a + 1 >= hold and a > 0]
    poses = sorted(set(p for p in poses + [n - 1] if 0 <= p < n))[:MAX_POSES]
    if n - 1 not in poses:
        poses.append(n - 1)
    images = _extract(path, poses, outdir)
    peak = max(range(n), key=lambda i: d[i]) if n > 1 else 0
    width = min(8, n)
    first = min(max(peak - 3, 0), max(n - width, 0))
    strip = _strip(path, first, outdir, width) if n else None

    offsets = [abs(c["offset_frames"]) for c in s if c["offset_frames"] is not None]
    measured = bool(s) and not cue_src.startswith("inferred")  # real cue words, not movements paired with words
    flashes = [f for f in fct.get("flashes") or [] if f.get("severity") == "fail"]
    sync_doc = {"render": rel_to(path, ctx.project_dir), "moment": mid, "version": version, "fps": fpsmod.rate_str(rate),
                "frames": n, "cue_source": cue_src, "quiet_threshold": quiet, "hold_frames": hold,
                "moment_start_s": (m or {}).get("start"), "cues": s, "measured": measured,
                "max_abs_offset_frames": max(offsets) if offsets else None}
    write_json_atomic(outdir / "sync.json", sync_doc)
    write_json_atomic(outdir / "facts.json", strip_private(fct))
    md = markdown(ctx, path, mid, m, version, sha, rate, n, fct, s, cue_src, poses, images, strip, first, width, peak, d)
    (outdir / "evidence.md").write_text(md, encoding="utf-8")
    seconds = round(time.monotonic() - t0, 2)
    toast = (f"evidence ready: {mid} {version}, "
             + (f"sync max offset {max(offsets)}f" if measured and offsets else "no cue words, sync not measured")
             + (", no flash" if not flashes else f", FLASH at frame {flashes[0]['frame']}"))
    result = {"ok": True, "moment": mid, "version": version, "dir": rel_to(outdir, ctx.project_dir),
              "evidence_md": rel_to(outdir / "evidence.md", ctx.project_dir), "poses": len(images), "strip": bool(strip),
              "max_abs_offset_frames": sync_doc["max_abs_offset_frames"] if measured else None,
              "sync_measured": measured, "flashes": len(flashes), "seconds": seconds,
              "frames": n, "toast": toast, "render_sha256": sha}
    if record:
        ledger.record(ctx, "evidence", scene=mid, note=toast, render=rel_to(path, ctx.project_dir), render_sha256=sha,
                      evidence=result["evidence_md"], seconds=seconds, source="aem evidence")
    return result


def _clip(text: str | None) -> str:
    return (text or "").strip() or "not written in the plan"


def markdown(ctx, path, mid, m, version, sha, rate, n, fct, s, cue_src, poses, images, strip, first, width, peak, d) -> str:
    c = (m or {}).get("contract") or {}
    asked = (m or {}).get("asked")
    notes = (m or {}).get("notes") or []
    L = [f"# Evidence · {mid} · {version}", "",
         f"Render `{rel_to(path, ctx.project_dir)}`, SHA-256 `{sha[:16]}…`, {n} frames at {fpsmod.rate_str(rate)}"
         f" ({n / float(rate):.2f} s). Built {ledger.ts()} by `aem evidence`.", "",
         "You are reviewing what is on screen. Read this file and open the images it names. Do not read the scene "
         "source or the builder's notes: judge the frames. Every finding names the image and a rule ID.", "",
         "## The moment", ""]
    if m:
        span = m.get("word_span")
        L += [f"- {m.get('name')} (moment {m.get('index')} of the index)"
              + (f", on the words \"{(m.get('words') or '')[:240]}\"" if m.get("words") else ""),
              f"- Teaching job: {m.get('job') or 'not written in the plan'}; treatment: {m.get('treatment') or '-'}",
              "- " + ("Asked by the client: " + "; ".join(f"note #{x['number']} \"{x['text'][:160]}\"" for x in notes)
                      if asked else "Added by us: no note of the client's covers it"),
              f"- Knows before: {_clip(c.get('knows_before'))}",
              f"- Knows after: {_clip(c.get('knows_after'))}",
              f"- Must stay true: {_clip(c.get('must_stay_true'))}",
              f"- Where the picture stops being accurate: {_clip(c.get('accuracy_limit'))}"]
        if span:
            L.append(f"- On the timeline from {span[0]:.2f} s to {span[1]:.2f} s")
    else:
        L.append(f"- No moment in moments/index.json matches `{mid}`; no contract to judge against.")
    rules = _rules(ctx, m)
    L += ["", "## Rules that apply", ""]
    L += [f"- {rid}: {what}" for rid, what in rules] if rules else ["- none listed for this client (registry evidence.rules)"]
    L += ["", "## Readable poses", "",
          "A pose is where the picture settles (nothing changes for a quarter second). `poses/` at 1920 px; `phone/` "
          "the same frame 390 px wide, as a phone held upright shows it.", "",
          "| Frame | Time | Why | Pose | Phone |", "|---:|---:|---|---|---|"]
    why = {0: "first frame", n - 1: "last frame"}
    for c_ in s:
        if c_["settle_frame"] is not None:
            why.setdefault(c_["settle_frame"], f"settles after \"{c_['word']}\"")
    for f in poses:
        if f in images:
            big, small = images[f]
            L.append(f"| {f} | {f / float(rate):.3f} s | {why.get(f, 'still')} | [{big}]({big}) | [{small}]({small}) |")
    L += ["", "## Fastest transition", ""]
    if strip:
        L.append(f"[strip.jpg](strip.jpg): frames {first}–{first + width - 1}, left to right; the largest change is "
                 f"into frame {peak} ({d[peak]:.2f} grey levels per pixel at 160x90).")
    else:
        L.append("No strip: the render is too short or could not be read.")
    L += ["", "## Sync ([sync.json](sync.json))", "", f"Cue words from {cue_src}. Offset = the frame the pose settles "
          "minus the word's onset frame; a readable pose lands on its word."
          + (" These pairings are guesses: weigh them only where the shot list would agree." if cue_src.startswith("inferred") else ""), ""]
    if s:
        L += ["| Cue | Onset | Moves | Settles | Offset |", "|---|---:|---:|---:|---:|"]
        for c_ in s:
            L.append(f"| {c_['word']}{' (' + c_['id'] + ')' if c_['id'] else ''} | {c_['onset_frame']} | "
                     f"{c_['change_frame'] if c_['change_frame'] is not None else '-'} | "
                     f"{c_['settle_frame'] if c_['settle_frame'] is not None else '-'} | "
                     f"{c_['offset_frames'] if c_['offset_frames'] is not None else (c_['note'] or '-')} |")
    else:
        L.append("Not measured.")
    flashes = fct.get("flashes") or []
    L += ["", "## Facts ([facts.json](facts.json))", "",
          f"Render check: **{str(fct.get('result', '?')).upper()}**" + (": " + "; ".join(fct.get("failures") or []) if fct.get("failures") else "")]
    for f in flashes:
        L.append(f"- {'FLASH' if f.get('severity') == 'fail' else 'minor'}: frame {f['frame']} ({f.get('timecode', '?')}), "
                 f"{f['length']} frame(s), {f['area_pct']}% of the frame, {f['plane']}")
    if not flashes:
        L.append("- no one- or two-frame flash found (the first and last frame cannot be scanned)")
    L += ["", "## How to report", "",
          "Write `critic.json` beside this file: `{\"verdict\": \"flag\" or \"pass\", \"findings\": [{\"rule\": \"<rule ID>\", "
          "\"image\": \"<path above>\", \"note\": \"<what is wrong, what the viewer would get instead>\"}]}`. At most the "
          "three worst findings. A finding with no image or no rule ID is not a finding.", ""]
    return "\n".join(L)


# --- the assembled cut ---------------------------------------------------------------------------------

def video(ctx: Context, cut_path: str, *, offset_s: float = 0.0) -> dict:
    """Per moment, a contact sheet of the assembled cut at its word span, and video.md listing them in order."""
    t0 = time.monotonic()
    cut = approvals.resolve_path(ctx, cut_path)
    if not cut.is_file():
        raise AemError(f"cut not found: {cut}")
    index = momentsmod.read_index(ctx) or momentsmod.build(ctx)
    outdir = ctx.project_dir / "reviews" / "video" / cut.stem
    outdir.mkdir(parents=True, exist_ok=True)
    L = [f"# The cut, moment by moment · {cut.name}", "",
         f"Built {ledger.ts()} by `aem evidence --video`. Each sheet is {SHEET_FRAMES} frames from the assembled cut across "
         "the moment's word span, as the client will see it. Review moments in context; findings name the sheet and a "
         "rule ID.", ""]
    made, skipped = [], []
    for m in index.get("moments") or []:
        span = m.get("word_span") or ([m["start"], m["end"]] if m.get("start") is not None else None)
        if not span:
            skipped.append(m["id"])
            continue
        a, b = span[0] + offset_s, span[1] + offset_s
        dur = max(b - a, 0.2)
        name = f"{m['index']:03d}-{m['id'].replace('#', '-')}.jpg"
        p = subprocess.run([_ffmpeg(), "-v", "error", "-y", "-ss", f"{max(a, 0):.3f}", "-t", f"{dur:.3f}", "-i", str(cut),
                            "-vf", f"fps={SHEET_FRAMES / dur:.6f},scale={STRIP_W}:-2,tile={SHEET_FRAMES}x1",
                            "-frames:v", "1", "-q:v", "4", str(outdir / name)], capture_output=True)
        if p.returncode != 0 or not (outdir / name).exists():
            skipped.append(m["id"])
            continue
        made.append(m["id"])
        c = m.get("contract") or {}
        r = m.get("ruling")
        L += [f"## {m['index']}. {m['id']} · {span[0]:.2f}–{span[1]:.2f} s", "",
              f"[{name}]({name})", "",
              f"- {('asked: ' + ', '.join('#' + str(x['number']) for x in m.get('notes') or [])) if m.get('asked') else 'added'}"
              f" · {m.get('treatment') or '-'} · job: {m.get('job') or '-'}"
              + (f" · ruling: {r['level']} {r['ruling'] or ''}" if r else ""),
              f"- Words: \"{(m.get('words') or '')[:200]}\"" if m.get("words") else "- Words: -",
              f"- Must stay true: {_clip(c.get('must_stay_true'))}", ""]
    (outdir / "video.md").write_text("\n".join(L), encoding="utf-8")
    seconds = round(time.monotonic() - t0, 2)
    ledger.record(ctx, "evidence_video", note=f"{len(made)} moment sheets from {cut.name}", fill_stage=True,
                  cut=rel_to(cut, ctx.project_dir), seconds=seconds, source="aem evidence --video")
    return {"ok": True, "cut": rel_to(cut, ctx.project_dir), "dir": rel_to(outdir, ctx.project_dir),
            "video_md": rel_to(outdir / "video.md", ctx.project_dir), "sheets": len(made), "skipped": skipped,
            "seconds": seconds}
