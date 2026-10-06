"""aem recall: what a new session needs to know about a client, on one screen.

How the client reviews (the registry's review profile), how much they directed the last video and this one, what
they changed last time (by treatment and job, in their words), their channel-level rulings, their standing
preferences (the rows of the rules file with the client's preference prefix: Joel's J- rules), the last five
rulings in the decisions file, quoted in the client's own words, the open questions for the client, and the
critic's labelled-case count. The Claude Code plugin shows it at session start in place of a longer context; the
agent reads the full files when it needs them.

Read-only. Quotes are verbatim, cut with an ellipsis where long; nothing is paraphrased into the client's voice.
"""
from __future__ import annotations

import re
from pathlib import Path

from .registry import Client
from .util import AemError, expand, read_json, read_jsonl

RULINGS = 5
QUESTIONS = 8
RULE_CHARS = 150
QUOTE_CHARS = 200
CHANNEL = 4
OPEN_QUESTIONS = re.compile(r"\bopen questions?\b", re.I)


def _cut(text: str, n: int) -> str:
    text = " ".join(text.split())
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def preferences(client: Client) -> list[dict]:
    """The client's stated preferences: rows of the rules file whose ID has the client's prefix."""
    prefix = client.raw.get("preference_prefix")
    if not prefix or not client.rules_path.exists():
        return []
    rows = []
    for line in client.rules_path.read_text(encoding="utf-8", errors="replace").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and re.fullmatch(re.escape(prefix) + r"-\d{2,}", cells[0]):
            row = {"id": cells[0], "rule": cells[1]}
            if len(cells) >= 5:
                row.update(kind=cells[2], status=cells[4])
            rows.append(row)
    return rows


def sections(path: Path) -> list[dict]:
    """The decisions file's `## ` sections, in file order, each ended by the next heading or a `---` line."""
    out: list[dict] = []
    cur = None
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    for line in lines:
        if line.startswith("## "):
            cur = {"heading": line[3:].strip(), "body": []}
            out.append(cur)
        elif line.strip() == "---":
            cur = None
        elif cur is not None:
            cur["body"].append(line)
    return out


def quotes(body: list[str]) -> list[str]:
    """Each block of `>` lines, joined into one quote, as written."""
    out, block = [], []
    for line in body + [""]:
        if line.lstrip().startswith(">"):
            block.append(line.lstrip()[1:].strip())
        elif block:
            out.append(" ".join(b for b in block if b))
            block = []
    return [q for q in out if q]


def _first_text(body: list[str]) -> str:
    """The entry's first paragraph of plain text (ours, not the client's), its wrapped lines joined."""
    para: list[str] = []
    for line in body:
        t = line.strip()
        if t and not t.startswith(("|", ">", "#")):
            para.append(t)
        elif para:
            break
    return " ".join(para)


def _quoted_in_table(body: list[str]) -> list[str]:
    """Words in quotation marks inside the entry's table rows: the client's, quoted where the entry has no `>`."""
    out = []
    for line in body:
        if line.strip().startswith("|"):
            out += [f'"{q}"' for q in re.findall(r'"([^"]{3,})"', line)]
    return out


def rulings(client: Client) -> list[dict]:
    """Every entry of the decisions file but its open questions, newest first."""
    entries = [s for s in sections(client.decisions_path) if not OPEN_QUESTIONS.search(s["heading"])]
    if client.decisions_order != "newest_first":
        entries.reverse()
    out = []
    for s in entries:
        q = quotes(s["body"]) or _quoted_in_table(s["body"])
        out.append({"heading": s["heading"], "quotes": q, "text": _first_text(s["body"])})
    return out


def open_questions(client: Client) -> list[str]:
    out: list[str] = []
    for s in sections(client.decisions_path):
        if not OPEN_QUESTIONS.search(s["heading"]):
            continue
        for line in s["body"]:
            m = re.match(r"^\s*(?:[-*]|\d+[.)])\s+(.*)$", line)
            if m:
                out.append(m.group(1).strip())
            elif out and line.startswith((" ", "\t")) and line.strip():
                out[-1] += " " + line.strip()
    return out


def labelled_counts(client: Client) -> dict:
    try:
        cases = read_jsonl(client.labelled_cases_path)
    except AemError:
        cases = []
    by: dict[str, int] = {}
    for c in cases:
        st = str(c.get("status") or "unknown")
        by[st] = by.get(st, 0) + 1
    return {"total": len(cases), "labelled": by.get("labelled", 0), "by_status": by}


def _profile_line(client: Client) -> str | None:
    p = client.raw.get("review_profile") or {}
    if not p:
        return None
    bits = []
    if p.get("unit"):
        bits.append(f"reviews the {p['unit']}")
    if p.get("approval_channel"):
        bits.append(f"approval on {p['approval_channel']}")
    if p.get("notes_channel"):
        bits.append(f"timestamped notes on {p['notes_channel']}")
    if p.get("other_channels"):
        bits.append("other feedback on " + ", ".join(p["other_channels"]))
    if p.get("sees_process") is False:
        bits.append("never sees the production process")
    return "; ".join(bits)


def _index_of(client: Client, name: str) -> dict | None:
    """A registered project's moments index (moments/index.json), if it has been built."""
    entry = client.project_entries().get(name) or {}
    if not entry.get("dir"):
        return None
    return read_json(expand(client.projects_root) / entry["dir"] / "moments" / "index.json")


def _direction(client: Client) -> list[tuple[str, str]]:
    """(project, direction) for each registered project: stated in the profile, else from its moments index."""
    stated = (client.raw.get("review_profile") or {}).get("direction") or {}
    out = []
    for name in client.project_entries():
        if name in stated:
            out.append((name, f"{stated[name]} (stated in the profile)"))
            continue
        idx = _index_of(client, name)
        if idx:
            out.append((name, f"{idx.get('direction')} ({idx.get('notes', 0)} notes)"))
        else:
            out.append((name, "not yet known (no moments index: aem moments)"))
    return out


def _client_cases(client: Client) -> list[dict]:
    try:
        return read_jsonl(client.labelled_cases_path)
    except AemError:
        return []


def _words(c: dict):
    w = c.get(next((k for k in c if k.endswith("_words")), ""))
    if not w or (isinstance(w, str) and (not w.strip() or w.upper().startswith("TODO"))):
        return None
    return w


def _our_note(c: dict) -> str | None:
    """The first sentence of the case's notes (ours, never the client's), for when the client's words are missing."""
    n = re.sub(r"^\s*Ours:\s*", "", str(c.get("notes") or ""))
    first_sentence = re.split(r"(?<=[.!?])\s", n, maxsplit=1)[0].rstrip(".")
    return _cut(first_sentence, 120) if first_sentence else None


def changed_last_time(client: Client, current: str | None) -> tuple[str | None, list[dict]]:
    """The client's explicit changes on the most recent earlier video that has any, each with the moment's
    treatment and teaching job (from that video's moments index) and the client's words."""
    from . import moments as momentsmod
    names = list(client.project_entries())
    order = names[:names.index(current)] if current in names else names
    cases = _client_cases(client)
    for name in reversed(order):
        mine = [c for c in cases if (str(c.get("video") or "") == name or str(c.get("video") or "").startswith(name + " ")
                                     or str(c.get("case_id") or "").startswith(name + "-"))
                and momentsmod.case_level(c, client.operator_id) == "explicit" and c.get("ruling") in ("change", "remove")]
        if not mine:
            continue
        ms = (_index_of(client, name) or {}).get("moments") or []
        out = []
        for c in mine:
            item = momentsmod.item_of(Path(str(c.get("moment") or c.get("shot") or "")))
            m = next((m for m in ms if m["id"] == c.get("moment") or momentsmod._matches(item, m)), {})
            out.append({"case_id": c.get("case_id"), "moment": m.get("id") or item, "ruling": c.get("ruling"),
                        "treatment": m.get("treatment") or "treatment not recorded",
                        "job": m.get("job") or "job not recorded", "asked": m.get("asked"),
                        "rule_ids": c.get("rule_ids") or m.get("rule_ids") or [], "words": _words(c),
                        "note": _our_note(c)})
        return name, out
    return None, []


def recall(client: Client, project: str | None = None) -> dict:
    prefs = preferences(client)
    rul = rulings(client)
    qs = open_questions(client)
    cases = labelled_counts(client)
    contact = client.contact
    first = (contact.split() or [client.id])[0]
    ds = client.design_system
    rel = lambda p: p.relative_to(ds).as_posix() if ds in p.parents else str(p)  # noqa: E731
    lines = [f"AEM recall · {client.name} ({client.id}) · {contact}"]
    how = _profile_line(client)
    summary = (client.raw.get("review_profile") or {}).get("summary")
    if how:
        lines.append(f"How {first} reviews: {how}.")
    direction = _direction(client)
    if direction:
        names = [n for n, _ in direction]
        here = project if project in names else None
        last = names[names.index(here) - 1] if here and names.index(here) > 0 else None
        shown = [(n, d) for n, d in direction if n in (last, here)] if here else direction
        lines.append("Direction: " + "; ".join(f"{n}{' (this video)' if n == here else ' (last video)' if n == last else ''} "
                                               f"{d}" for n, d in shown))
    channel = [c for c in reversed(_client_cases(client)) if c.get("level") == "channel"]
    if channel:
        lines.append(f"{first} on how to work for this channel (channel-level rulings, newest first; his words):")
        for c in channel[:CHANNEL]:
            lines.append(f"  {c.get('ruling_date')} · {c.get('source')}: \"{_cut(str(_words(c) or ''), QUOTE_CHARS)}\"")
    video, changed = changed_last_time(client, project)
    if changed:
        lines.append(f"What {first} changed last time ({video}: {len(changed)} explicit change"
                     f"{'s' if len(changed) != 1 else ''}, by treatment and job; {first}'s words):")
        for c in sorted(changed, key=lambda c: (c["treatment"], c["job"], c["moment"])):
            w = c["words"]
            said = ('"' + _cut(" / ".join(w) if isinstance(w, list) else str(w), QUOTE_CHARS) + '"') if w \
                else f"{first}'s words not recorded" + (f" (our note: {c['note']})" if c["note"] else "")
            rules = ", ".join(c["rule_ids"]) or "no rule cited"
            asked = {True: "asked; ", False: "added; "}.get(c["asked"], "")  # unknown until its moments index is built
            lines.append(f"  {c['treatment']} · {c['job']} · {c['moment']} ({asked}{c['ruling']}; {rules}): {said}")
    elif video is None and len(direction) > 1:
        lines.append(f"What {first} changed last time: no explicit change recorded on an earlier video")
    prefix = client.raw.get("preference_prefix")
    if prefs:
        lines.append(f"Standing preferences ({rel(client.rules_path)}, the {prefix}- rows; cite the ID):")
        lines += [f"  {r['id']} {_cut(r['rule'], RULE_CHARS)}" for r in prefs]
    else:
        lines.append(f"Standing preferences: none in {rel(client.rules_path)}" + (f" with prefix {prefix}-" if prefix else ""))
    shown = rul[:RULINGS]
    if shown:
        lines.append(("Last ruling" if len(shown) == 1 else f"Last {len(shown)} rulings")
                     + f" ({rel(client.decisions_path)}, newest first; quotes are {first}'s words, cut where long):")
        for r in shown:
            if r["quotes"]:
                more = len(r["quotes"]) - 1
                lines.append(f"  {r['heading']}: {_cut(r['quotes'][0], QUOTE_CHARS)}"
                             + (f" (+{more} more quote{'s' if more > 1 else ''})" if more else ""))
            else:
                lines.append(f"  {r['heading']}: no quote; our note: {_cut(r['text'], QUOTE_CHARS)}".rstrip())
    else:
        lines.append(f"Rulings: none yet in {rel(client.decisions_path)}")
    if qs:
        lines.append(f"Open questions for {first} ({len(qs)}):")
        lines += [f"  - {_cut(q, QUOTE_CHARS)}" for q in qs[:QUESTIONS]]
        if len(qs) > QUESTIONS:
            lines.append(f"  … and {len(qs) - QUESTIONS} more in {rel(client.decisions_path)}")
    else:
        lines.append(f"Open questions for {first}: none listed")
    others = ", ".join(f"{n} {s}{'s' if n > 1 and not s.endswith('s') else ''}"
                       for s, n in sorted(cases["by_status"].items()) if s != "labelled")
    lines.append(f"Labelled cases: {cases['total']} in {rel(client.labelled_cases_path)}, {cases['labelled']} labelled"
                 + (f" ({others})" if others else ""))
    lines.append(f"Read the full files in {ds} when you need them.")
    return {"ok": True, "client": client.id, "preferences": prefs, "rulings": shown, "rulings_total": len(rul),
            "open_questions": qs, "labelled_cases": cases, "review_profile": client.raw.get("review_profile"),
            "how_reviews": how, "review_summary": summary, "direction": dict(direction),
            "changed_last_time": {"video": video, "changes": changed},
            "channel_rulings": [c.get("case_id") for c in channel], "text": "\n".join(lines)}
