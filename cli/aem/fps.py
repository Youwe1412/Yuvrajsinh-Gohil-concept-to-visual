"""Frame rates as exact rationals, frame and timecode maths, and where a project's rate comes from.

A rate is never assumed. It is read from the project's settings or its edit and kept as
fps_num/fps_den (24000/1001, 25/1). Decimal spellings such as 23.976 are refused because
they are not exact.
"""
from __future__ import annotations

import json
import math
import re
import xml.etree.ElementTree as ET
from fractions import Fraction
from pathlib import Path

from .util import AemError

PROJECT_SETTINGS = "aem.project.json"

_RATIONAL = re.compile(r"^\s*(\d+)\s*(?:/\s*(\d+))?\s*$")
_FRAME_DURATION = re.compile(r"^\s*(\d+)(?:/(\d+))?s\s*$")


def parse_rate(value) -> Fraction:
    """Parse a frame rate given as N/D, an integer, a {num, den} dict or a (num, den) pair."""
    if isinstance(value, Fraction):
        fps = value
    elif isinstance(value, dict):
        fps = Fraction(int(value["num"]), int(value["den"]))
    elif isinstance(value, (tuple, list)) and len(value) == 2:
        fps = Fraction(int(value[0]), int(value[1]))
    elif isinstance(value, int):
        fps = Fraction(value)
    else:
        s = str(value).strip()
        m = _RATIONAL.match(s)
        if not m:
            raise AemError(
                f"frame rate {s!r} is not an exact rational",
                hint="Give it as N/D from the edit (24000/1001, 30000/1001, 25/1), never a decimal like 23.976.",
            )
        fps = Fraction(int(m.group(1)), int(m.group(2) or 1))
    if fps <= 0:
        raise AemError(f"frame rate {value!r} must be positive")
    return fps


def parse_frame_duration(value: str) -> Fraction:
    """FCPXML frameDuration ('1001/24000s', '1/25s', '100/2500s') to a frame rate."""
    m = _FRAME_DURATION.match(value or "")
    if not m:
        raise AemError(f"frameDuration {value!r} is not an FCPXML time")
    dur = Fraction(int(m.group(1)), int(m.group(2) or 1))
    if dur <= 0:
        raise AemError(f"frameDuration {value!r} must be positive")
    return 1 / dur


def rate_str(fps: Fraction) -> str:
    return f"{fps.numerator}/{fps.denominator}"


def rate_dict(fps: Fraction, source: str | None = None) -> dict:
    d = {"num": fps.numerator, "den": fps.denominator}
    if source is not None:
        d["source"] = source
    return d


def nominal(fps: Fraction) -> int:
    """Counting base for timecode: 24 for 24000/1001, 30 for 30000/1001, 25 for 25/1."""
    return math.ceil(fps)


def is_drop_frame_rate(fps: Fraction) -> bool:
    return fps.denominator == 1001 and nominal(fps) in (30, 60)


def seconds_to_frame(seconds, fps: Fraction) -> int:
    """frame = round(seconds × fps_num / fps_den). Halves round to even, as Python does."""
    sec = seconds if isinstance(seconds, Fraction) else Fraction(str(seconds))
    return round(sec * fps)


def frame_to_seconds(frame: int, fps: Fraction) -> Fraction:
    return Fraction(frame) / fps


_TC = re.compile(r"^\s*(\d{1,2}):(\d{2}):(\d{2})([:;.])(\d{2,3})\s*$")


def timecode_to_frame(tc: str, fps: Fraction) -> int:
    """HH:MM:SS:FF (or ;FF drop-frame) to a frame count at this rate's nominal base."""
    m = _TC.match(tc or "")
    if not m:
        raise AemError(f"timecode {tc!r} is not HH:MM:SS:FF")
    hh, mm, ss, sep, ff = int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(4), int(m.group(5))
    base = nominal(fps)
    if ff >= base or mm >= 60 or ss >= 60:
        raise AemError(f"timecode {tc!r} is out of range at {rate_str(fps)} (nominal {base})")
    frame = ((hh * 3600 + mm * 60 + ss) * base) + ff
    if sep == ";":
        if not is_drop_frame_rate(fps):
            raise AemError(f"timecode {tc!r} is drop-frame but {rate_str(fps)} is not a drop-frame rate")
        drop = 2 if base == 30 else 4
        total_minutes = hh * 60 + mm
        frame -= drop * (total_minutes - total_minutes // 10)
    return frame


def frame_to_timecode(frame: int, fps: Fraction, drop: bool = False) -> str:
    base = nominal(fps)
    sep = ":"
    if drop:
        if not is_drop_frame_rate(fps):
            raise AemError(f"{rate_str(fps)} is not a drop-frame rate")
        sep = ";"
        d = 2 if base == 30 else 4
        per_10min = base * 600 - d * 9
        per_min = base * 60 - d
        tens, rem = divmod(frame, per_10min)
        if rem > d:
            frame += d * 9 * tens + d * ((rem - d) // per_min)
        else:
            frame += d * 9 * tens
    ff = frame % base
    total_s = frame // base
    return f"{total_s // 3600:02d}:{(total_s // 60) % 60:02d}:{total_s % 60:02d}{sep}{ff:02d}"


# --- where a project's rate comes from -------------------------------------------------

def _fcpxml_rates(path: Path) -> list[Fraction]:
    """Rates of the sequences in an FCPXML file (the edit), via their format's frameDuration."""
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError):
        return []
    formats = {f.get("id"): f.get("frameDuration") for f in root.iter("format")}
    rates = []
    for seq in root.iter("sequence"):
        fd = formats.get(seq.get("format"))
        if fd:
            try:
                rates.append(parse_frame_duration(fd))
            except AemError:
                pass
    return rates


def discover(project_dir: Path) -> list[dict]:
    """Every frame rate the project states, with where it came from.

    Sources, in this order: the AEM project settings (aem.project.json), FCPXML edits in the
    project (sequence frameDuration), the word map (data/words.json fps_num/fps_den) and a
    HyperFrames frame.md `fps :` line.
    """
    found: list[dict] = []
    settings = project_dir / PROJECT_SETTINGS
    if settings.exists():
        try:
            data = json.loads(settings.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise AemError(f"{settings} is not valid JSON ({exc.msg})") from exc
        if data.get("fps") is not None:
            found.append({"fps": parse_rate(data["fps"]), "source": PROJECT_SETTINGS})

    candidates: list[Path] = []
    for pattern in ("*.fcpxml", "out/*.fcpxml", "data/*.fcpxml", "*.fcpxmld/Info.fcpxml", "out/*.fcpxmld/Info.fcpxml"):
        candidates.extend(sorted(project_dir.glob(pattern)))
    for p in candidates:
        for r in sorted(set(_fcpxml_rates(p))):
            found.append({"fps": r, "source": f"{p.relative_to(project_dir).as_posix()} (sequence frameDuration)"})

    words = project_dir / "data" / "words.json"
    if words.exists():
        try:
            w = json.loads(words.read_text(encoding="utf-8"))
            if isinstance(w, dict) and w.get("fps_num") and w.get("fps_den"):
                found.append({"fps": Fraction(int(w["fps_num"]), int(w["fps_den"])), "source": "data/words.json"})
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

    frame_md = project_dir / "frame.md"
    if frame_md.exists():
        m = re.search(r"^\s*fps\s*:\s*\"?(\d+(?:/\d+)?)\"?", frame_md.read_text(encoding="utf-8", errors="replace"), re.M)
        if m:
            found.append({"fps": parse_rate(m.group(1)), "source": "frame.md"})
    return found


def resolve(project_dir: Path, override: str | None = None) -> dict:
    """The project's rate. An explicit override wins; otherwise every source must agree."""
    if override:
        return {"fps": parse_rate(override), "source": "operator (--fps)", "candidates": []}
    found = discover(project_dir)
    distinct = sorted({f["fps"] for f in found})
    if not found:
        raise AemError(
            f"no frame rate found in {project_dir}",
            hint=f"Set \"fps\": \"N/D\" in {PROJECT_SETTINGS} (read it from the edit: ffprobe r_frame_rate), or export the "
                 "edit's FCPXML into the project. AEM never assumes a rate.",
        )
    if len(distinct) > 1:
        listing = "; ".join(f"{rate_str(f['fps'])} from {f['source']}" for f in found)
        raise AemError(
            f"the project's sources disagree on frame rate: {listing}",
            hint=f"Check the edit's frameDuration, then make the sources agree ({PROJECT_SETTINGS} states the rate).",
        )
    return {"fps": distinct[0], "source": found[0]["source"],
            "candidates": [{"fps": rate_str(f["fps"]), "source": f["source"]} for f in found]}
