"""Shared helpers: paths, clock, hashing and append-only JSON Lines files."""
from __future__ import annotations

import datetime as _dt
import fcntl
import hashlib
import json
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


class AemError(Exception):
    """A usage or input error. Exit code 2."""

    exit_code = 2

    def __init__(self, message: str, *, hint: str | None = None, data: dict | None = None):
        super().__init__(message)
        self.message = message
        self.hint = hint
        self.data = data or {}


class CheckFailed(AemError):
    """A check ran and failed (missing approval, failed render check). Exit code 1."""

    exit_code = 1


def aem_home() -> Path:
    """Where AEM keeps per-user state (active project). AEM_HOME overrides ~/.aem."""
    return Path(os.environ.get("AEM_HOME") or (Path.home() / ".aem")).expanduser()


def expand(p: str | os.PathLike) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(str(p))))


def now() -> _dt.datetime:
    """Local time with its offset. AEM_FIXED_NOW pins the clock (tests only)."""
    fixed = os.environ.get("AEM_FIXED_NOW")
    if fixed:
        return parse_ts(fixed)
    return _dt.datetime.now().astimezone()


def ts(dt: _dt.datetime | None = None) -> str:
    return (dt or now()).isoformat(timespec="seconds")


def parse_ts(s: str) -> _dt.datetime:
    d = _dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    if d.tzinfo is None:
        d = d.astimezone()
    return d


def today() -> str:
    return now().date().isoformat()


def sha256_file(path: str | os.PathLike) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def append_jsonl(path: Path, record: dict, *, track: bool = False, by: str | None = None) -> None:
    """Append one JSON object as one line, under an exclusive lock. Never rewrites.

    track=True is for a ledger AEM stands behind: the line's hash goes into the file's integrity manifest in
    the same locked write (see integrity.py), so a line written any other way shows up in `aem integrity`."""
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False)
    with open(path, "a", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            if track:
                from . import integrity
                integrity.ensure_baseline(path)
            # If the file does not end in a newline (hand edit), start on a fresh line.
            if f.tell() > 0:
                with open(path, "rb") as r:
                    r.seek(-1, os.SEEK_END)
                    if r.read(1) != b"\n":
                        f.write("\n")
            f.write(line + "\n")
            f.flush()
            if track:
                integrity.note_append(path, line, by=by)
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def read_jsonl(path: Path, *, keep_comments: bool = False) -> list[dict]:
    """Read a JSON Lines ledger. Lines with a `_comment` key are headers and skipped."""
    if not path.exists():
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        for n, raw in enumerate(f, 1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise AemError(f"{path}:{n} is not valid JSON ({exc.msg})",
                               hint="Ledgers are append-only; add a correcting line rather than editing.") from exc
            if not isinstance(obj, dict):
                raise AemError(f"{path}:{n} is not a JSON object")
            if "_comment" in obj and not keep_comments:
                continue
            obj["_line"] = n
            out.append(obj)
    return out


def strip_private(record: dict) -> dict:
    return {k: v for k, v in record.items() if not k.startswith("_")}


def write_json_atomic(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def read_json(path: Path, default=None):
    if not path.exists():
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def rel_to(path: Path, base: Path) -> str:
    """Path relative to base when inside it, else absolute. Always forward slashes."""
    path = Path(os.path.abspath(path))
    try:
        return path.relative_to(Path(os.path.abspath(base))).as_posix()
    except ValueError:
        return path.as_posix()


def fmt_duration(seconds: float) -> str:
    seconds = int(round(seconds))
    sign = "-" if seconds < 0 else ""
    seconds = abs(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{sign}{h}:{m:02d}:{s:02d}"
