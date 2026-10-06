"""aem recall: what a new session needs to know about a client, on one screen.

The client's standing preferences (the rows of the rules file with the client's preference prefix: Joel's J-
rules), the last five rulings in the decisions file, quoted in the client's own words, the open questions for
the client, and the critic's labelled-case count. The Claude Code plugin shows it at session start in place of a
longer context; the agent reads the full files when it needs them.

Read-only. Quotes are verbatim, cut with an ellipsis where long; nothing is paraphrased into the client's voice.
"""
from __future__ import annotations

import re
from pathlib import Path

from .registry import Client
from .util import AemError, read_jsonl

RULINGS = 5
QUESTIONS = 8
RULE_CHARS = 150
QUOTE_CHARS = 200
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


def recall(client: Client) -> dict:
    prefs = preferences(client)
    rul = rulings(client)
    qs = open_questions(client)
    cases = labelled_counts(client)
    contact = client.contact
    first = (contact.split() or [client.id])[0]
    ds = client.design_system
    rel = lambda p: p.relative_to(ds).as_posix() if ds in p.parents else str(p)  # noqa: E731
    lines = [f"AEM recall · {client.name} ({client.id}) · {contact}"]
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
            "open_questions": qs, "labelled_cases": cases, "text": "\n".join(lines)}
