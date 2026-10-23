"""The client's rulings, at the level they were given.

How a client like Joel reviews decides what a ruling is (the registry's review profile): he reviews the finished
video, never individual animations, so a ruling has three levels.

  explicit   a comment on one moment (Frame.io at its timecode, or a quote attached with client-said --about
             <moment>): the strongest signal; keep, change or remove, in his words
  implicit   the video accepted with no comment on that moment (aem accept-video): weaker, but it counts, because
             the whole video was his to reject. Written only once the whole video is accepted; silence on a moment
             is never written as explicit
  video      a remark about the video as a whole; channel: a remark about the editor or the channel, in his words
             (client-said --about video|channel)

Each ruling is a line in the client's critic/labelled-cases.jsonl, in that file's own field names, with AEM's
additions: moment, level, asked (asked or added), direction (full notes, partial, none), the moment's rule IDs,
the critic's findings on the version the client saw. An operator's ruling in the review inbox is level
"operator": it is ours, never the client's.
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from . import inbox, ledger, moments as momentsmod, operator
from .registry import Context
from .util import AemError, append_jsonl, now, read_json, sha256_file, today

LEVELS = ("explicit", "implicit", "video", "channel")
RULINGS = ("keep", "change", "remove", "accepted")


def critic_on(ctx: Context, moment_id: str, version: str | None) -> dict | None:
    """The critic's findings on that version of the moment (reviews/<moment>/<version>/critic.json)."""
    if not version:
        return None
    data = read_json(ctx.project_dir / "reviews" / moment_id.replace("#", "-") / version / "critic.json")
    if not data:
        return None
    return {"version": version, "verdict": data.get("verdict"), "findings": data.get("findings") or []}


def agreed(critic: dict | None, ruling: str | None) -> bool | None:
    if not critic or not critic.get("verdict") or ruling not in RULINGS:
        return None
    flagged = critic["verdict"] == "flag"
    return flagged == (ruling in ("change", "remove"))


def make_case(ctx: Context, *, level: str, ruling: str | None, words, source: str, moment: dict | None,
              index: dict | None, render_sha256: str | None = None, version: str | None = None,
              notes: str, extra: dict | None = None) -> dict:
    """A ruling in the client's own field names, plus AEM's additions."""
    if level not in LEVELS:
        raise AemError(f"level must be one of {', '.join(LEVELS)}")
    wf = inbox.words_field(ctx)
    m = moment or {}
    critic = critic_on(ctx, m["id"], version) if m else None
    has_words = bool(words) and not (isinstance(words, str) and not words.strip())
    status = ("labelled" if level == "explicit" and ruling in ("keep", "change", "remove") and has_words and render_sha256
              else "development case")
    stamp = now().strftime("%H%M%S")
    case = {
        "case_id": f"{ctx.project}-{m.get('id') or level}-{today()}-{level}-{stamp}",
        "status": status,
        "video": ctx.project,
        "shot": m.get("id"),
        "word_ids": m.get("word_ids") or [],
        "render_sha256": render_sha256,
        "frames_or_crops": [],
        "ruling": ruling,
        wf: words if has_words else None,
        "ruling_date": today(),
        "source": source,
        "rule_ids": m.get("rule_ids") or ((m.get("ruling") or {}).get("rule_ids") or []),
        "critic_verdict_g5": (critic or {}).get("verdict"),
        "critic_agreed": agreed(critic, ruling),
        "notes": notes,
        # AEM's additions (1.1.0)
        "moment": m.get("id"),
        "level": level,
        "asked": (("asked" if m.get("asked") else "added") if m else None),
        "direction": (index or {}).get("direction"),
        "critic_findings": (critic or {}).get("findings"),
        "version": version,
    }
    case.update(extra or {})
    return case


def append(ctx: Context, case: dict, *, by: str) -> dict:
    if not ctx.client.labelled_cases_path.parent.is_dir():
        raise AemError(f"no critic folder at {ctx.client.labelled_cases_path.parent}")
    append_jsonl(ctx.client.labelled_cases_path, case, track=True, by=by)
    ledger.record(ctx, "labelled_case", scene=case.get("moment"), note=case["case_id"], fill_stage=False,
                  case_id=case["case_id"], level=case.get("level"), ruling=case.get("ruling"), source=by)
    return case


def _index(ctx: Context) -> dict:
    index = momentsmod.build(ctx)
    momentsmod.write(ctx, index)
    return index


def render_at(ctx: Context, m: dict, version: str) -> Path | None:
    """The moment's render file at a delivered version."""
    for r in m.get("renders") or []:
        if r["version"] == version.lower():
            p = ctx.project_dir / r["path"]
            if p.is_file():
                return p
    return None


# File times on some disks (exFAT keeps 2 s) are not exact; a render written just before the master still counts.
MTIME_SLACK_S = 2.0


def _version_number(version: str) -> int:
    m = re.search(r"\d+", version)
    return int(m.group()) if m else -1


def latest_render(ctx: Context, m: dict, before: float | None) -> tuple[str, Path] | None:
    """The moment's newest render (highest version) whose file is no newer than `before` (epoch seconds), if given.
    For a video whose moments were delivered at different versions (P2: v01 to v06)."""
    found = []
    for r in m.get("renders") or []:
        p = ctx.project_dir / r["path"]
        if not p.is_file():
            continue
        if before is not None and p.stat().st_mtime > before + MTIME_SLACK_S:
            continue
        found.append((_version_number(r["version"]), r["version"], p))
    if not found:
        return None
    _, version, p = max(found, key=lambda x: (x[0], x[1]))
    return version, p


def parse_before(ctx: Context, value: str) -> float:
    """--before: an existing file (its modification time: the delivered master), relative to the working folder or
    the project, or an ISO date-time (local time when it has no offset). Epoch seconds."""
    for p in (Path(value).expanduser(), ctx.project_dir / value if ctx.project_dir else None):
        if p is not None and p.exists():
            return p.stat().st_mtime
    try:
        t = datetime.fromisoformat(value.strip())
    except ValueError:
        raise AemError(f"--before {value!r} is neither a file nor an ISO date-time",
                       hint="name the delivered master (its modification time is used) or give e.g. 2026-10-15T02:00")
    return (t if t.tzinfo else t.astimezone()).timestamp()


def check_about(ctx: Context, target: str, ruling: str | None) -> dict | None:
    """What --about names, checked before anything is written: the moment (None for video or channel)."""
    if ruling and ruling not in ("keep", "change", "remove"):
        raise AemError("--ruling must be keep, change or remove")
    if target in ("video", "channel"):
        if ruling and target == "channel":
            raise AemError("a channel-level remark has no keep, change or remove; leave --ruling out")
        return None
    index = momentsmod.build(ctx) if ctx.project_dir else {"moments": []}
    m = momentsmod.find(index, target)
    if not m:
        raise AemError(f"no moment {target!r} in this project", hint="aem moments lists them; or use --about video|channel.")
    return m


def about(ctx: Context, target: str, quote: str, *, ruling: str | None, source: str, entry: str | None = None) -> dict:
    """A client quote attached to a moment, the video or the channel (aem client-said --about). `entry` is the
    decisions-file entry that quotes it."""
    check_about(ctx, target, ruling)
    index = _index(ctx) if ctx.project_dir else {"moments": []}
    extra = {"decisions_entry": entry} if entry else None
    if target in ("video", "channel"):
        case = make_case(ctx, level=target, ruling=ruling, words=quote, source=source, moment=None, index=index,
                         notes=f"Ours: {ctx.client.contact}'s words about the {target}, recorded with client-said --about {target}.",
                         extra=extra)
        return append(ctx, case, by="aem client-said")
    m = momentsmod.find(index, target)
    if not m:
        raise AemError(f"no moment {target!r} in this project", hint="aem moments lists them; or use --about video|channel.")
    latest = (m.get("renders") or [None])[-1]
    rp = ctx.project_dir / latest["path"] if latest else None
    sha = sha256_file(rp) if rp and rp.is_file() else None
    case = make_case(ctx, level="explicit", ruling=ruling, words=quote, source=source, moment=m, index=index,
                     render_sha256=sha, version=latest["version"] if latest else None,
                     notes=(f"Ours: {ctx.client.contact}'s words about this moment, recorded with client-said --about."
                            + ("" if ruling else " No keep, change or remove was given: a remark, not a ruling.")),
                     extra=extra)
    return append(ctx, case, by="aem client-said")


def accept_video(ctx: Context, version: str, source: str, before: str | None = None) -> dict:
    """The client accepted the delivered cut: one implicit acceptance per moment with no explicit comment.

    `version` is the delivered version (v08), or "latest": each moment's newest render, for a video whose moments
    went out at different versions; `before` (latest only) counts only renders no newer than the delivered master."""
    operator.assert_checked("accept-video")
    if not source or not source.strip():
        raise AemError("accept-video needs --source (where the acceptance came from, e.g. \"Frame.io, 12 Oct\")")
    version = version.lower()
    latest = version == "latest"
    if before and not latest:
        raise AemError("--before goes with latest only", hint="aem accept-video latest --before <delivered master> --source ...")
    cutoff = parse_before(ctx, before) if before else None
    index = _index(ctx)
    cases = momentsmod.video_cases(ctx)
    op = ctx.client.operator_id
    written, explicit, already, no_render = [], [], [], []
    versions: dict[str, str | None] = {}
    for m in index["moments"]:
        if m.get("treatment") == "nothing":
            continue
        mine = [c for c in cases if c.get("moment") == m["id"]
                or momentsmod._matches(momentsmod.item_of(Path(str(c.get("moment") or c.get("shot") or ""))), m)]
        if any(momentsmod.case_level(c, op) == "explicit" and c.get("ruling") in ("keep", "change", "remove") for c in mine):
            explicit.append(m["id"])
            continue
        if latest:
            hit = latest_render(ctx, m, cutoff)
            v, rp = hit if hit else (None, None)
        else:
            v, rp = version, render_at(ctx, m, version)
        versions[m["id"]] = v
        if any(c.get("level") == "implicit" and c.get("version") == v for c in mine):
            already.append(m["id"])
            continue
        if not rp:
            no_render.append(m["id"])
        missing = (f" No render file at {version} was found." if not latest
                   else " No render of this moment was found" + (" made before the delivered master." if cutoff else "."))
        case = make_case(ctx, level="implicit", ruling="accepted", words=None, source=source.strip(), moment=m,
                         index=index, render_sha256=sha256_file(rp) if rp else None, version=v,
                         notes=(f"Ours: {ctx.client.contact} accepted the delivered video ({source.strip()}) and said "
                                "nothing about this moment. Implicit acceptance: weaker than an explicit ruling, and "
                                "never written as one." + ("" if rp else missing)))
        append(ctx, case, by="aem accept-video")
        written.append(m["id"])
    label = version if not latest else "latest" + (f" before {before}" if before else "")
    ledger.record(ctx, "video_accepted", note=f"{label}: {source.strip()}", fill_stage=True, version=version,
                  implicit=len(written), explicit=len(explicit), already=len(already) or None,
                  source="aem accept-video")
    out = {"ok": True, "version": version, "source": source.strip(), "implicit_written": len(written),
           "explicit": explicit, "already_accepted": already, "no_render_at_version": no_render,
           "moments": len(index["moments"])}
    if latest:
        out["versions"] = versions
        out["before"] = before
    return out
