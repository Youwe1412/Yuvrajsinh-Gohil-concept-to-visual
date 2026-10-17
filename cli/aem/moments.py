"""Moments: the unit of work.

A moment is one beat of the video the studio decided something about: an animation, footage, a screen
recording, or deliberately nothing. AEM derives moments from what the skill already writes, and never asks
for a new file:

  plan rows       the client's plan and shot-list files (registry `moments.plan_files`, `shotlist_files`;
                  Joel: visual-plan.md, shotlist.md): one row per moment, its first cell the moment's name,
                  its columns the word IDs, teaching job, treatment and contract (knows before, knows after,
                  must stay true, where the picture stops being accurate), rule IDs, scene
  placements      the delivered timeline (`moments.placement_files`: data/edit.json, renders/*/PLACEMENTS.csv):
                  spans and the asset each placement uses. With no plan, each placement of ours (one with a
                  `kind`, not the client's footage) is a moment.
  words           data/words.json (or a whisper.cpp narration-words.json): the word IDs under each span
  notes           the client's timestamped notes for this video (`aem import-review --notes`): a moment whose
                  word span a note covers is asked; otherwise added. A video with no notes: every moment added.
  renders         files under the render folders named for the moment (`<id>_v08.mp4`)
  approvals       approvals.jsonl; rulings: the client's labelled cases for this video; critic findings:
                  reviews/<moment>/<version>/critic.json; time: stages in events.jsonl whose scene is the moment

`aem moments` writes <project>/moments/index.json (derived, rebuilt each time; not a ledger) and reports what
it could not link. Time is attached only where a stage names the moment; whole-video stages stay
unattributed, never spread.
"""
from __future__ import annotations

import csv
import fnmatch
import json
import re
from fractions import Fraction
from pathlib import Path

from . import approvals, ledger
from .registry import Context
from .util import read_json, read_jsonl, rel_to, ts, write_json_atomic

DEFAULTS = {
    "plan_files": ["visual-plan.md"],
    "shotlist_files": ["shotlist.md"],
    "placement_files": ["data/edit.json", "data/placements.json", "renders/*/PLACEMENTS.csv"],
    "render_dirs": ["renders"],
    "include_footage_placements": False,
}
MEDIA = (".mp4", ".mov", ".m4v", ".mxf")
INDEX = Path("moments") / "index.json"
VERSION = re.compile(r"[_-](v\d+)$", re.I)
WORD_ID = re.compile(r"\bw\d+\b")

# Plan-table columns, found by what their header says (lowercase, contains); the most specific first.
COLUMNS = [
    ("knows_before", ("knows before",)),
    ("knows_after", ("knows after",)),
    ("must_stay_true", ("must stay true",)),
    ("accuracy_limit", ("stops being accurate", "stop being accurate", "accuracy", "accurate until")),
    ("why", ("why it exists", "why", "reason")),
    ("treatment", ("treatment",)),
    ("job", ("teaching job", "job")),
    ("cues", ("cue",)),
    ("words", ("word id", "word ids", "words", "word")),
    ("rule_ids", ("rule id", "rules", "rule")),
    ("asked", ("asked or added", "asked")),
    ("scene", ("scene", "composition", "source")),
]
CONTRACT = ("knows_before", "knows_after", "must_stay_true", "accuracy_limit")
TREATMENTS = [
    ("nothing", ("none", "nothing", "no visual", "bare a-roll", "a-roll", "—", "-")),
    ("screen recording", ("screen rec", "screen recording", "recording", "capture")),
    ("footage", ("footage", "b-roll", "broll", "film", "clip", "photo", "image")),
    ("animation", ("animation", "build", "hyperframes", "graphic", "title", "motion", "card", "diagram")),
]


def settings(ctx: Context) -> dict:
    cfg = {**DEFAULTS, **(ctx.client.raw.get("moments") or {}), **(ctx.project_settings().get("moments") or {})}
    own = ctx.project_settings().get("placements")  # aem.project.json's placements file comes first
    if own:
        cfg["placement_files"] = [own] + [f for f in cfg["placement_files"] if f != own]
    return cfg


def profile(ctx: Context) -> dict:
    return dict(ctx.client.raw.get("review_profile") or {})


def treatment_of(text: str | None) -> str | None:
    t = (text or "").strip().lower()
    if not t:
        return None
    for name, words in TREATMENTS:
        if any(t == w or t.startswith(w) or f" {w}" in f" {t}" for w in words):
            return name
    return t


# --- words ----------------------------------------------------------------------------------------

def load_words(ctx: Context) -> tuple[list[dict], str | None]:
    """[{id, word, start, end}] by time, from data/words.json (the skill's word map) or a whisper.cpp JSON."""
    for rel in ("data/words.json", "data/narration-words.json"):
        p = ctx.project_dir / rel
        if not p.exists():
            continue
        data = read_json(p) or {}
        out = []
        if isinstance(data.get("words"), list):
            fps = Fraction(int(data["fps_num"]), int(data["fps_den"])) if data.get("fps_num") else ctx.fps
            for i, w in enumerate(data["words"]):
                start, end = w.get("start"), w.get("end")
                if start is None and w.get("start_frame") is not None and fps:
                    start = float(int(w["start_frame"]) / fps)
                    end = float(int(w.get("end_frame", w["start_frame"])) / fps)
                if start is None:
                    continue
                out.append({"id": w.get("id") or f"w{i}", "word": w.get("word") or w.get("text") or "",
                            "start": float(start), "end": float(end if end is not None else start)})
        elif isinstance(data.get("transcription"), list):
            for seg in data["transcription"]:
                t, off = (seg.get("text") or "").strip(), seg.get("offsets") or {}
                if t and not t.startswith("[_") and off.get("from") is not None:
                    out.append({"id": f"w{len(out) + 1:04d}", "word": t, "start": off["from"] / 1000,
                                "end": off.get("to", off["from"]) / 1000})
        if out:
            out.sort(key=lambda w: w["start"])
            return out, rel
    return [], None


def words_in(words: list[dict], a: float, b: float) -> list[dict]:
    return [w for w in words if w["start"] < b and w["end"] > a]


def expand_word_ids(text: str, words: list[dict]) -> list[str]:
    """Word IDs a cell names: a list (w0012, w0014) or a range (w0012–w0019, w0012…w0019)."""
    ids = WORD_ID.findall(text or "")
    if not ids:
        return []
    order = {w["id"]: i for i, w in enumerate(words)}
    out: list[str] = []
    for m in re.finditer(r"(\bw\d+\b)(?:\s*(?:–|—|-|\.\.\.?|…|to)\s*(\bw\d+\b))?", text):
        a, b = m.group(1), m.group(2)
        if b and a in order and b in order:
            out += [words[i]["id"] for i in range(order[a], order[b] + 1)]
        else:
            out += [a] + ([b] if b else [])
    return list(dict.fromkeys(out))


# --- plan rows ----------------------------------------------------------------------------------------

def _files(ctx: Context, patterns: list[str]) -> list[Path]:
    out: list[Path] = []
    for pat in patterns:
        out += sorted(p for p in ctx.project_dir.glob(pat) if p.is_file() and not p.name.startswith("._"))
    return list(dict.fromkeys(out))


def _assign(header: list[str]) -> dict:
    """Header cell -> field, each field and each column used once."""
    low = [h.strip().lower() for h in header]
    taken, out = set(), {}
    for field, names in COLUMNS:
        for i, h in enumerate(low):
            if i == 0 or i in taken:
                continue
            if any(n in h for n in names):
                out[header[i]] = field
                taken.add(i)
                break
    return out


def plan_rows(ctx: Context, cfg: dict, words: list[dict]) -> tuple[list[dict], list[str]]:
    rows: dict[str, dict] = {}
    files = []
    for path in _files(ctx, list(cfg["plan_files"]) + list(cfg["shotlist_files"])):
        files.append(rel_to(path, ctx.project_dir))
        for r in approvals.plan_rows(path):
            cells = r["cells"]
            header = list(cells)
            fields = _assign(header)
            m = rows.setdefault(r["row"], {"name": r["row"], "plan": []})
            m["plan"].append(f"{rel_to(path, ctx.project_dir)}:{r['line']}")
            for col, field in fields.items():
                val = (cells.get(col) or "").strip()
                if not val:
                    continue
                if field == "words":
                    m["word_ids"] = list(dict.fromkeys((m.get("word_ids") or []) + expand_word_ids(val, words)))
                elif field == "cues":
                    m["cue_ids"] = list(dict.fromkeys((m.get("cue_ids") or []) + expand_word_ids(val, words)))
                elif field == "rule_ids":
                    m["rule_ids"] = list(dict.fromkeys((m.get("rule_ids") or [])
                                                       + re.findall(ctx.client.raw.get("rule_id_pattern")
                                                                    or r"\b[A-Z]{1,2}(?:-T\d)?-\d{2}\b", val)))
                elif field == "treatment":
                    m["treatment"] = treatment_of(val)
                elif field == "asked":
                    m["asked_in_plan"] = val.lower().startswith(("asked", "yes", "y"))
                else:
                    m.setdefault(field, val)
    return list(rows.values()), files


# --- placements ----------------------------------------------------------------------------------------

def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def placement_rows(ctx: Context, cfg: dict) -> tuple[list[dict], list[str]]:
    """[{name, start, end, kind, footage, asset}] from the placement files: the first JSON timeline with
    placements (data/edit.json), else the newest placement CSV; every CSV adds the asset each placement used
    (the newest version wins)."""
    rows: list[dict] = []
    assets: dict[str, list[tuple[float, str]]] = {}
    used: list[str] = []
    csvs: list[tuple[str, list[dict]]] = []
    for path in _files(ctx, list(cfg["placement_files"])):
        rel = rel_to(path, ctx.project_dir)
        if path.suffix.lower() == ".json":
            if rows:
                continue
            data = read_json(path) or []
            items = data.get("placements", data.get("shots")) if isinstance(data, dict) else data
            for r in items or []:
                if not isinstance(r, dict):
                    continue
                start, dur = _num(r.get("start")), _num(r.get("duration"))
                if start is None or dur is None:
                    continue
                rows.append({"name": r.get("name") or r.get("shot") or r.get("master"), "start": start,
                             "end": start + dur, "kind": r.get("kind"), "footage": bool(r.get("type")) and not r.get("kind"),
                             "asset": r.get("asset") or r.get("render"), "from": rel})
            if rows:
                used.append(rel)
        elif path.suffix.lower() == ".csv":
            got = []
            with open(path, newline="", encoding="utf-8-sig") as f:
                for r in csv.DictReader(f):
                    low = {k.strip().lower(): (v or "").strip() for k, v in r.items() if k}
                    name = low.get("name") or low.get("shot")
                    start = _num(low.get("source_start_seconds", low.get("start")))
                    if not name or start is None:
                        continue
                    dur = _num(low.get("duration_seconds", low.get("duration"))) or 0.0
                    got.append({"name": name, "start": start, "end": start + dur, "kind": low.get("type"),
                                "footage": low.get("type") in ("image", "video"), "asset": low.get("asset") or None,
                                "from": rel})
            for g in got:
                if g["asset"]:
                    have = assets.setdefault(g["name"], [])
                    have[:] = [x for x in have if abs(x[0] - g["start"]) > 0.001] + [(g["start"], g["asset"])]
            if got:
                csvs.append((rel, got))
                used.append(rel)
    if not rows and csvs:
        rows = [dict(r) for r in csvs[-1][1]]
    for r in rows:
        if r.get("asset"):
            continue
        cands = assets.get(r["name"]) or []
        if len(cands) == 1 and sum(1 for x in rows if x["name"] == r["name"]) == 1:
            r["asset"] = cands[0][1]  # one placement of that name: its asset, even if a later retime moved it
        elif cands:
            near = min(cands, key=lambda x: abs(x[0] - r["start"]))
            r["asset"] = near[1] if abs(near[0] - r["start"]) <= 2.0 else None
    return rows, used


# --- notes --------------------------------------------------------------------------------------------

def load_notes(ctx: Context) -> tuple[list[dict], list[str]]:
    """The client's timestamped notes on this video, from every `aem import-review --notes`."""
    out, files, seen = [], [], set()
    rdir = ctx.project_dir / "reviews" / ctx.client.id
    for p in sorted(rdir.glob("*-notes.json")) if rdir.is_dir() else []:
        data = read_json(p) or {}
        files.append(rel_to(p, ctx.project_dir))
        for c in data.get("comments") or []:
            if c.get("seconds") is None:
                continue
            key = (c.get("number"), c.get("timecode"))
            if key in seen:
                continue
            seen.add(key)
            out.append(c)
    return out, files


def covering_notes(span: tuple[float, float] | None, notes: list[dict], window: float) -> list[dict]:
    if not span:
        return []
    a, b = span
    return [n for n in notes if n["seconds"] <= b + window and (n.get("end_seconds") or n["seconds"]) >= a - window]


def direction(ctx: Context, notes: list[dict], moments: list[dict]) -> tuple[str, str]:
    """How much the client directed this video: full notes, partial or none; stated in the profile, else from notes."""
    stated = (profile(ctx).get("direction") or {}).get(ctx.project)
    if stated:
        return stated, "the review profile in the registry"
    if not notes:
        return "none", "no timestamped notes imported for this video"
    asked = sum(1 for m in moments if m.get("asked"))
    share = asked / len(moments) if moments else 0
    return ("full notes" if share >= 0.5 else "partial"), f"{len(notes)} notes cover {asked} of {len(moments)} moments"


# --- renders, approvals, rulings, critic, time --------------------------------------------------------

def item_of(path: Path) -> str:
    return approvals.item_from_path(path)


def version_of(path: Path) -> str:
    m = VERSION.search(path.stem)
    if m:
        return m.group(1).lower()
    if re.fullmatch(r"v\d+", path.parent.name, re.I):
        return path.parent.name.lower()
    return "unversioned"


def render_files(ctx: Context, cfg: dict) -> list[Path]:
    out = []
    for d in cfg["render_dirs"]:
        root = ctx.project_dir / d
        if root.is_dir():
            out += [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in MEDIA and not p.name.startswith(".")]
    return sorted(out)


def _matches(item: str, m: dict) -> bool:
    """A render item, scene or shot name means this moment: the same name, or the name after the studio's
    prefix (fd_S01_next-token is next-token; fd_title-t02_forever is t02_forever)."""
    keys = {m.get("id") or "", m.get("name") or "", m.get("item") or ""} - {""}
    return item in keys or any(item.endswith(("_" + k, "-" + k)) or k.endswith(("_" + item, "-" + item)) for k in keys)


def video_cases(ctx: Context) -> list[dict]:
    """The client's labelled cases about this video."""
    names = {ctx.project, ctx.project_dir.name}
    out = []
    for c in read_jsonl(ctx.client.labelled_cases_path):
        v = str(c.get("video") or "")
        if v in names or v.startswith(f"{ctx.project} ") or str(c.get("case_id") or "").startswith(f"{ctx.project}-"):
            out.append(c)
    return out


def case_level(c: dict, operator_id: str | None = None) -> str | None:
    """explicit, implicit, video, channel; "operator" for the operator's own ruling in the review inbox (ours, never
    the client's); None for a line that is no ruling. Lines written before 1.1.0 carry no level: a keep, change or
    remove that is not the operator's is explicit."""
    if c.get("level"):
        return c["level"]
    if (operator_id and c.get("source") == operator_id) or c.get("item_kind") in ("plan_row", "still", "render", "override"):
        return "operator"
    if c.get("ruling") in ("keep", "change", "remove"):
        return "explicit"
    return None


def ruling_of(cases: list[dict], operator_id: str | None = None) -> dict | None:
    """The client's ruling on a moment at its level: an explicit one beats an implicit acceptance."""
    by = {"explicit": [], "implicit": []}
    for c in cases:
        lvl = case_level(c, operator_id)
        if lvl == "explicit" and c.get("ruling") not in ("keep", "change", "remove"):
            continue  # the client's words on the moment with no keep, change or remove: a remark, not a ruling
        if lvl in by:
            by[lvl].append(c)
    for lvl in ("explicit", "implicit"):
        if by[lvl]:
            c = by[lvl][-1]
            words_field = next((k for k in c if k.endswith("_words")), None)
            words = c.get(words_field) if words_field else None
            if isinstance(words, str) and words.upper().startswith("TODO"):
                words = None
            return {"level": lvl, "ruling": c.get("ruling"), "words": words or None, "case_id": c.get("case_id"),
                    "date": c.get("ruling_date"), "source": c.get("source"), "render_sha256": c.get("render_sha256"),
                    "rule_ids": c.get("rule_ids") or []}
    return None


def critic_findings(ctx: Context, moment_id: str) -> list[dict]:
    out = []
    root = ctx.project_dir / "reviews" / moment_id
    for p in sorted(root.glob("*/critic.json")) if root.is_dir() else []:
        data = read_json(p) or {}
        out.append({"version": p.parent.name, "verdict": data.get("verdict"),
                    "findings": data.get("findings") or [], "file": rel_to(p, ctx.project_dir)})
    return out


def choice_events(ctx: Context) -> list[dict]:
    """`aem chose` events: the decisions we made where the brief and the client's rulings left a gap."""
    return [e for e in read_jsonl(ctx.events_path) if e.get("event") == "choice"] if ctx.events_path.exists() else []


def choices_of(chosen: list[dict], m: dict) -> list[dict]:
    return [{"ts": e.get("ts"), "choice": e.get("note"), "why": e.get("why"), "rule_ids": e.get("rule_ids") or []}
            for e in chosen if e.get("scene") and (e["scene"] == m.get("id") or _matches(str(e["scene"]), m))]


def stage_time(ctx: Context, moments: list[dict]) -> tuple[dict, dict]:
    """Stage wall time per moment (stages whose scene names it) and what no moment claims."""
    events = ledger.read_events(ctx)
    if not events:
        return {}, {"wall_s": 0.0, "stages": []}
    tl = ledger.build_timeline(events, ledger.now().timestamp(), ctx.client.waiting_ids)
    per: dict[str, list] = {}
    loose = []
    for (gate, scene), iv in tl["stages"].items():
        owner = next((m["id"] for m in moments if scene and _matches(scene, m)), None)
        if owner:
            per.setdefault(owner, []).extend((a, b, gate) for a, b in iv)
        else:
            loose += [(a, b) for a, b in iv]
    out = {}
    for mid, iv in per.items():
        gates: dict[str, float] = {}
        for a, b, g in iv:
            gates[g] = gates.get(g, 0.0) + (b - a)
        out[mid] = {"wall_s": ledger._length([(a, b) for a, b, _ in iv]), "by_gate": gates}
    return out, {"wall_s": ledger._length(loose), "stages": len(loose)}


# --- the index ------------------------------------------------------------------------------------------

def build(ctx: Context) -> dict:
    cfg = settings(ctx)
    words, words_src = load_words(ctx)
    plan, plan_files = plan_rows(ctx, cfg, words)
    places, place_files = placement_rows(ctx, cfg)
    notes, note_files = load_notes(ctx)
    window = float(profile(ctx).get("note_window_s", 1.0))
    unlinked: list[str] = []

    moments: list[dict] = []
    if plan:
        for row in plan:
            p = next((x for x in places if x["name"] == row["name"]
                      or (x.get("asset") and _matches(item_of(Path(x["asset"])), {"id": row["name"], "name": row["name"]}))), None)
            m = {"name": row["name"], **{k: v for k, v in row.items() if k != "name"}}
            if p:
                m.update(start=p["start"], end=p["end"], asset=p.get("asset"))
            moments.append(m)
        names = {m["name"] for m in moments}
        unlinked += [f"placement {p['name']} at {p['start']:.3f}s matches no plan row" for p in places
                     if p["name"] not in names and not p["footage"]]
    else:
        for p in places:
            if p["footage"] and not cfg["include_footage_placements"]:
                continue
            moments.append({"name": p["name"], "start": p["start"], "end": p["end"], "asset": p.get("asset"),
                            "treatment": "footage" if p["footage"] else "animation", "kind": p.get("kind")})
    moments.sort(key=lambda m: (m.get("start") if m.get("start") is not None else float("inf")))

    files = render_files(ctx, cfg)
    items = sorted({item_of(f) for f in files})
    seen: dict[str, int] = {}
    for i, m in enumerate(moments, 1):
        if m.get("asset"):
            base = item_of(Path(m["asset"]))
        else:
            named = [it for it in items if _matches(it, {"name": m["name"]})]
            base = named[0] if len(named) == 1 else m["name"]
        seen[base] = seen.get(base, 0) + 1
        m["id"] = base if seen[base] == 1 else f"{base}#{seen[base]}"
        m["index"] = i
        m["item"] = base
        if m.get("start") is not None and words:
            ws = words_in(words, m["start"], m["end"])
            m.setdefault("word_ids", [w["id"] for w in ws])
        ids = set(m.get("word_ids") or [])
        ws = [w for w in words if w["id"] in ids]
        if ws:
            m["word_span"] = [min(w["start"] for w in ws), max(w["end"] for w in ws)]
            m["words"] = " ".join(w["word"] for w in ws)
        elif m.get("start") is not None:
            m["word_span"] = [m["start"], m["end"]]
        else:
            unlinked.append(f"moment {m['id']} has no words and no placement: its span is unknown")
        m.setdefault("treatment", "animation" if m.get("asset") or m.get("scene") else None)
        m["contract"] = {k: m.pop(k, None) for k in CONTRACT}

    # Asked or added, from the client's notes for this video.
    for m in moments:
        span = tuple(m["word_span"]) if m.get("word_span") else None
        hits = covering_notes(span, notes, window)
        m["notes"] = [{"number": n.get("number"), "timecode": n.get("timecode"), "text": n.get("comment") or ""}
                      for n in hits]
        if m.get("asked_in_plan") is not None:
            m["asked"] = m.pop("asked_in_plan")
            m["asked_from"] = "the plan"
        else:
            m["asked"] = bool(hits)
            m["asked_from"] = "note coverage" if notes else "no notes"
    covered = {id(n) for m in moments for n in covering_notes(tuple(m["word_span"]) if m.get("word_span") else None,
                                                                notes, window)}
    loose_notes = [n for n in notes if id(n) not in covered]
    level, level_why = direction(ctx, notes, moments)

    # Renders, approvals, rulings, critic findings, time.
    by_item: dict[str, list[Path]] = {}
    for f in files:
        by_item.setdefault(item_of(f), []).append(f)
    claimed = set()
    lines = approvals.read(ctx) if ctx.approvals_path.exists() else []
    cases = video_cases(ctx)
    case_moment: dict[str, list] = {}
    for c in cases:
        shot = item_of(Path(str(c.get("moment") or c.get("shot") or "")))
        owner = next((m for m in moments if c.get("moment") == m["id"] or _matches(shot, m)), None)
        if owner:
            case_moment.setdefault(owner["id"], []).append(c)
        elif case_level(c, ctx.client.operator_id) in ("explicit", "implicit"):
            unlinked.append(f"labelled case {c.get('case_id')} names {c.get('moment') or c.get('shot')}, which is no moment")
    times, loose_time = stage_time(ctx, moments)
    chosen = choice_events(ctx)
    for m in moments:
        mine = [f for item, fs in by_item.items() if _matches(item, m) for f in fs]
        claimed.update(mine)
        m["renders"] = sorted({version_of(f): rel_to(f, ctx.project_dir) for f in mine}.items())
        m["renders"] = [{"version": v, "path": p} for v, p in m["renders"]]
        a = approvals.latest_approval(lines, m["id"]) or approvals.latest_approval(lines, m["item"])
        m["approval"] = None
        if a:
            st = approvals.approval_state(lines, a)
            m["approval"] = {"gate": a.get("gate"), "render": a.get("render"), "date": a.get("date"),
                             "standing": st["standing"], "why": st["why"]}
        m["ruling"] = ruling_of(case_moment.get(m["id"], []), ctx.client.operator_id)
        m["critic"] = critic_findings(ctx, m["id"])
        m["choices"] = choices_of(chosen, m)
        m["time"] = times.get(m["id"])
        if not m["renders"] and m.get("treatment") in ("animation", None) and m.get("asset"):
            unlinked.append(f"moment {m['id']}: no render file for its asset {m['asset']}")
    for f in files:
        if f not in claimed:
            unlinked.append(f"render {rel_to(f, ctx.project_dir)} belongs to no moment")
    known = {m["id"] for m in moments} | {m["item"] for m in moments}
    for scene in sorted({l.get("scene") for l in lines if l.get("scene") and approvals.item_kind(l) == "render"}):
        if scene not in known and not any(_matches(scene, m) for m in moments):
            unlinked.append(f"approvals name {scene}, which is no moment")

    asked = sum(1 for m in moments if m["asked"])
    index = {
        "client": ctx.client.id, "project": ctx.project, "built": ts(), "moments_count": len(moments),
        "direction": level, "direction_from": level_why, "notes": len(notes), "note_window_s": window,
        "asked": asked, "added": len(moments) - asked,
        "note": ("No timestamped notes for this video: every moment is added (the client left placement to us)."
                 if not notes else f"Asked: a note's timecode falls within {window:g} s of the moment's word span."),
        "sources": {"plan": plan_files, "placements": place_files, "words": words_src, "notes": note_files},
        "unattributed_time": loose_time,
        "video_notes": [{"number": n.get("number"), "timecode": n.get("timecode"), "text": n.get("comment") or ""}
                        for n in loose_notes],
        "unlinked": unlinked,
        "moments": moments,
    }
    return index


def write(ctx: Context, index: dict) -> Path:
    path = ctx.project_dir / INDEX
    write_json_atomic(path, index)
    return path


def read_index(ctx: Context) -> dict | None:
    return read_json(ctx.project_dir / INDEX) if ctx.project_dir else None


def find(index: dict | None, name: str) -> dict | None:
    """The moment a render item, moment ID or name means."""
    for m in (index or {}).get("moments") or []:
        if _matches(name, m):
            return m
    return None


def counts(ctx: Context, index: dict | None = None) -> dict | None:
    """N moments, M with a standing approval, K with the client's ruling (explicit or implicit): the status line."""
    index = index or read_index(ctx)
    if not index or not index.get("moments"):
        return None
    lines = approvals.read(ctx) if ctx.approvals_path.exists() else []
    cases = video_cases(ctx)
    approved = ruled = 0
    for m in index["moments"]:
        a = approvals.latest_approval(lines, m["id"]) or approvals.latest_approval(lines, m.get("item") or m["id"])
        if a and approvals.approval_state(lines, a)["standing"]:
            approved += 1
        mine = [c for c in cases if c.get("moment") == m["id"]
                or _matches(item_of(Path(str(c.get("moment") or c.get("shot") or ""))), m)]
        if ruling_of(mine, ctx.client.operator_id):
            ruled += 1
    return {"moments": len(index["moments"]), "approved": approved, "ruled": ruled}


# --- text ------------------------------------------------------------------------------------------------

def _clock(s: float | None) -> str:
    if s is None:
        return "-"
    m, sec = divmod(s, 60)
    return f"{int(m)}:{sec:04.1f}"


def _span_ids(ids: list[str]) -> str:
    if not ids:
        return "-"
    return ids[0] if len(ids) == 1 else f"{ids[0]}–{ids[-1]}"


def table(index: dict) -> str:
    ms = index["moments"]
    head = (f"{index['project']} · {len(ms)} moments · direction: {index['direction']} ({index['direction_from']}) · "
            f"{index['asked']} asked · {index['added']} added")
    lines = [head]
    if not index["notes"]:
        lines.append(index["note"])
    lines.append(f"{'#':>3}  {'Moment':<28} {'Span':<15} {'Words':<12} {'Treatment':<10} {'Asked':<12} "
                 f"{'Renders':<9} {'Approval':<9} {'Ruling':<18} Time")
    for m in ms:
        span = f"{_clock(m.get('start'))}–{_clock(m.get('end'))}" if m.get("start") is not None else "-"
        asked = (" ".join(f"#{n['number']}" for n in m["notes"])[:12] or "asked") if m["asked"] else "added"
        rv = [r["version"] for r in m["renders"]]
        renders = "-" if not rv else rv[0] if len(rv) == 1 else f"{rv[0]}–{rv[-1]}"
        ap = "-" if not m["approval"] else (m["approval"]["gate"] or "") + ("" if m["approval"]["standing"] else " stale")
        r = m["ruling"]
        ruling = "-" if not r else f"{r['level']} {r['ruling'] or ''}".strip()
        t = m.get("time")
        lines.append(f"{m['index']:>3}  {m['id'][:28]:<28} {span:<15} {_span_ids(m.get('word_ids') or [])[:12]:<12} "
                     f"{(m.get('treatment') or '-')[:10]:<10} {asked:<12} {renders:<9} {ap:<9} {ruling[:18]:<18} "
                     + (ledger.fmt_duration(t["wall_s"]) if t else "-"))
    if index["video_notes"]:
        lines.append(f"{len(index['video_notes'])} note(s) cover no moment (about the video or the edit): "
                     + ", ".join(f"#{n['number']}" for n in index["video_notes"]))
    ut = index["unattributed_time"]
    if ut.get("wall_s"):
        lines.append(f"Unattributed stage time (whole-video stages, or scenes that name no moment): "
                     f"{ledger.fmt_duration(ut['wall_s'])}")
    if index["unlinked"]:
        lines.append(f"Could not link ({len(index['unlinked'])}):")
        lines += [f"  - {u}" for u in index["unlinked"][:25]]
        if len(index["unlinked"]) > 25:
            lines.append(f"  … {len(index['unlinked']) - 25} more in moments/index.json")
    return "\n".join(lines)
