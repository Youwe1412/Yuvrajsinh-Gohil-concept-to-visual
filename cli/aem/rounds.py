"""Choices and repair rounds: what the agent decided on its own, and whether each re-render made a moment better.

`aem chose` records one decision the agent made where the brief, the plan and the client's rulings left a gap
(a default, a treatment, a timing): a `choice` event in events.jsonl with the reason and the rule IDs it leans on.
At the client's review, `aem calibrate` then tells the moments the client changed that rest on a choice of ours
from those that do not.

`aem rounds` reads what evidence and the critic left under reviews/<moment>/<version>/ (facts.json, sync.json,
holds.json, critic.json, retell.json) and lays the versions of each moment side by side: the render check, flashes,
sync, frozen time, the critic's verdict and findings, the sound-off retell, and which earlier findings each version
fixed, kept or brought back. It writes reports/rounds.md (derived, rebuilt each time; not a ledger) and changes
nothing else. Read-only on the record: anyone may run it.
"""
from __future__ import annotations

from pathlib import Path

from . import ledger
from .registry import Context
from .util import AemError, read_json, rel_to, ts

CHOICE = "choice"


def chose(ctx: Context, what: str, *, why: str, moment: str | None = None, rules: list[str] | None = None,
          alternatives: list[str] | None = None) -> dict:
    what, why = (what or "").strip(), (why or "").strip()
    if not what:
        raise AemError("chose needs the decision, in a few words")
    if not why:
        raise AemError("chose needs --why: one line on what the viewer understands better because of it")
    rec = ledger.record(ctx, CHOICE, scene=moment, note=what, why=why, rule_ids=rules or None,
                        alternatives=alternatives or None, source="aem chose")
    return {"ok": True, "choice": rec}


def choices(ctx: Context) -> list[dict]:
    return [e for e in ledger.read_events(ctx) if e.get("event") == CHOICE]


def _finding_keys(critic: dict | None) -> set[str]:
    out = set()
    for f in (critic or {}).get("findings") or []:
        out.add(str(f.get("rule") or f.get("note") or "?"))
    return out


def _version_row(d: Path) -> dict:
    facts = read_json(d / "facts.json") or {}
    sync = read_json(d / "sync.json") or {}
    holds = read_json(d / "holds.json") or {}
    critic = read_json(d / "critic.json")
    retell = read_json(d / "retell.json")
    flashes = [f for f in facts.get("flashes") or [] if f.get("severity") == "fail"]
    md = d / "evidence.md"
    return {
        "version": d.name, "built": md.stat().st_mtime if md.exists() else d.stat().st_mtime,
        "check": facts.get("result"), "failures": facts.get("failures") or [], "flashes": len(flashes),
        "sync_max_offset_frames": sync.get("max_abs_offset_frames") if sync.get("measured") else None,
        "frozen_over": len(holds.get("over") or []) if holds else None,
        "frozen_per_30s": holds.get("frozen_per_30s") if holds else None,
        "verdict": (critic or {}).get("verdict"), "findings": sorted(_finding_keys(critic)),
        "critic": critic is not None, "retell": (retell or {}).get("retell"),
        "retell_match": (critic or {}).get("retell_match"),
        "director": len((critic or {}).get("director") or []),
    }


def moment_rounds(root: Path) -> list[dict]:
    rows = sorted((_version_row(d) for d in root.iterdir() if d.is_dir() and (d / "evidence.md").exists()),
                  key=lambda r: (r["built"], r["version"]))
    ever: set[str] = set()
    prev: set[str] | None = None
    for r in rows:
        cur = set(r["findings"])
        if prev is None or not r["critic"]:
            r["fixed"], r["kept"], r["new"], r["came_back"] = [], [], sorted(cur), []
        else:
            r["fixed"] = sorted(prev - cur)
            r["kept"] = sorted(prev & cur)
            r["came_back"] = sorted((cur - prev) & ever)
            r["new"] = sorted(cur - prev - ever)
        if r["critic"]:
            ever |= cur
            prev = cur
    return rows


def rounds(ctx: Context, moment: str | None = None, *, write: bool = True) -> dict:
    base = ctx.project_dir / "reviews"
    if not base.is_dir():
        raise AemError("no reviews/ folder in this project yet", hint="Run `aem evidence <render>` first.")
    dirs = [d for d in sorted(base.iterdir()) if d.is_dir() and d.name != "video" and not d.name.startswith(".")]
    if moment:
        dirs = [d for d in dirs if d.name == moment.replace("#", "-")]
        if not dirs:
            raise AemError(f"no evidence for moment {moment} under reviews/")
    by_moment = {}
    for d in dirs:
        rows = moment_rounds(d)
        if rows:
            by_moment[d.name] = rows
    mine = choices(ctx)
    out = {"ok": True, "project": ctx.project, "built": ts(), "moments": by_moment,
           "choices": {k: [c for c in mine if str(c.get("scene") or "").replace("#", "-") == k] for k in by_moment}}
    md = markdown(out)
    if write:
        path = ctx.project_dir / "reports" / "rounds.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(md, encoding="utf-8")
        out["written"] = rel_to(path, ctx.project_dir)
    out["markdown"] = md
    return out


def _cell(v) -> str:
    if v is None or v == []:
        return "-"
    if isinstance(v, list):
        return ", ".join(str(x) for x in v)
    return str(v)


def markdown(r: dict) -> str:
    L = [f"# Repair rounds · {r['project']}", "",
         f"Built {r['built']} by `aem rounds` from reviews/<moment>/<version>/. Versions in the order their evidence "
         "was built. Findings are keyed by rule ID: **fixed** were in the version before and are gone, **kept** are still "
         "there, **back** were fixed once and returned (a regression).", ""]
    if not r["moments"]:
        L.append("No evidence yet.")
    for mid, rows in r["moments"].items():
        L += [f"## {mid}", "",
              "| Version | Check | Flash | Sync (f) | Frozen > max | Critic | Findings | Fixed | Kept | Back | Sound-off |",
              "|---|---|---:|---:|---:|---|---|---|---|---|---|"]
        for x in rows:
            L.append(f"| {x['version']} | {_cell(x['check'])} | {x['flashes']} | {_cell(x['sync_max_offset_frames'])} | "
                     f"{_cell(x['frozen_over'])} | {_cell(x['verdict']) if x['critic'] else 'not run'} | "
                     f"{_cell(x['findings'])} | {_cell(x['fixed'])} | {_cell(x['kept'])} | {_cell(x['came_back'])} | "
                     f"{_cell(x['retell_match']) if x['retell'] or x['retell_match'] else 'not read'} |")
        last = rows[-1]
        if last["retell"]:
            L += ["", f"Latest sound-off retell ({last['version']}): \"{last['retell']}\""]
        ch = r["choices"].get(mid) or []
        if ch:
            L += ["", "Choices of ours on this moment:"]
            L += [f"- {c.get('ts', '')[:10]} · {c.get('note')} · why: {c.get('why')}"
                  + (f" · {', '.join(c['rule_ids'])}" if c.get("rule_ids") else "") for c in ch]
        L.append("")
    return "\n".join(L)
