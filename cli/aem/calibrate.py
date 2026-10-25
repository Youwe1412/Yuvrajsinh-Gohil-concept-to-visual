"""aem calibrate <client>: what the client's rulings say, reported honestly.

  acceptance per video   moments delivered, explicitly changed, explicitly kept, implicitly accepted, split by asked
                         vs added, by treatment and by teaching job
  critic agreement       for moments the client changed, did the critic flag them (hits, misses); for moments the
                         client accepted, did it flag them (false alarms). Explicit rulings weigh more than implicit
                         acceptances (1 and 0.25), and the report says so
  rules                  per rule ID: how many rulings involve it, how many the client's own words confirm, how many
                         overrule the critic's finding on it, or untested. An inferred or unconfirmed rule the rulings
                         now support or contradict appears as a candidate status change with the decisions-file entry
                         it rests on; rules.md is never edited, the proposed line is printed

With fewer than 30 explicit cases every figure carries its count and "development data, not evidence" (M-19: the
critic only advises until about 30 labelled cases agree with it). With no rulings at all it says so and stops.
Read-only.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from . import moments as momentsmod, recall, registry
from .registry import Client
from .util import AemError

EVIDENCE_AT = 30
WEIGHT = {"explicit": 1.0, "implicit": 0.25}


def _contexts(client: Client, reg_path: str | None) -> tuple[list, list[str]]:
    out, skipped = [], []
    for name in client.project_entries():
        try:
            ctx = registry.context(argparse.Namespace(client=client.id, project=name, registry=reg_path))
        except AemError as exc:
            skipped.append(f"{name}: {exc.message}")
            continue
        out.append(ctx)
    return out, skipped


def _rule_rows(client: Client) -> dict[str, list[str]]:
    rows = {}
    if client.rules_path.exists():
        for line in client.rules_path.read_text(encoding="utf-8", errors="replace").splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 5 and re.fullmatch(client.raw.get("rule_id_pattern") or r"[A-Z]{1,2}(?:-T\d)?-\d{2}", cells[0]):
                rows[cells[0]] = cells
    return rows


def _words(c: dict) -> str | list | None:
    wf = next((k for k in c if k.endswith("_words")), None)
    w = c.get(wf) if wf else None
    if isinstance(w, str) and (not w.strip() or w.upper().startswith("TODO")):
        return None
    return w or None


def _entry_for(client: Client, cases: list[dict], rule_id: str) -> str | None:
    """The decisions-file entry a rule's rulings rest on: named in a case's source, or mentioning the rule."""
    heads = [s["heading"] for s in recall.sections(client.decisions_path)]
    for c in cases:
        m = re.search(r"entry (\d{4}-\d{2}-\d{2})", str(c.get("source") or ""))
        if m:
            hit = next((h for h in heads if h.startswith(m.group(1))), None)
            if hit:
                return hit
    for s in recall.sections(client.decisions_path):
        if rule_id in "\n".join(s["body"]):
            return s["heading"]
    return None


def calibrate(client: Client, reg_path: str | None = None) -> dict:
    ctxs, skipped = _contexts(client, reg_path)
    op = client.operator_id
    videos, all_cases = [], []
    for ctx in ctxs:
        index = momentsmod.read_index(ctx) or momentsmod.build(ctx)
        cases = momentsmod.video_cases(ctx)
        ms = [m for m in index.get("moments") or [] if m.get("treatment") != "nothing"]
        chosen = momentsmod.choice_events(ctx)  # read fresh: a cached index may predate the latest choices
        rows = []
        for m in ms:
            mine = [c for c in cases if c.get("moment") == m["id"]
                    or momentsmod._matches(momentsmod.item_of(Path(str(c.get("moment") or c.get("shot") or ""))), m)]
            r = momentsmod.ruling_of(mine, op)
            crit = next((x for x in reversed(m.get("critic") or [])), None)
            rows.append({"moment": m, "ruling": r, "cases": mine, "critic": crit,
                         "choices": momentsmod.choices_of(chosen, m)})
        for c in cases:
            all_cases.append((ctx.project, c))
        videos.append({"project": ctx.project, "direction": index.get("direction"), "notes": index.get("notes"),
                       "rows": rows, "cases": cases,
                       "video_level": [c for c in cases if momentsmod.case_level(c, op) == "video"],
                       "channel_level": [c for c in cases if momentsmod.case_level(c, op) == "channel"]})
    levels = {}
    for _p, c in all_cases:
        lvl = momentsmod.case_level(c, op)
        if lvl == "explicit" and c.get("ruling") not in ("keep", "change", "remove"):
            lvl = "remark"  # the client's words on a moment, with no keep, change or remove
        if lvl:
            levels[lvl] = levels.get(lvl, 0) + 1
    explicit_n = levels.get("explicit", 0)
    ruled = explicit_n + levels.get("implicit", 0) + levels.get("video", 0) + levels.get("channel", 0)
    tag = "" if explicit_n >= EVIDENCE_AT else f" [{explicit_n} explicit case{'s' if explicit_n != 1 else ''}: development data, not evidence]"
    out = {"ok": True, "client": client.id, "levels": levels, "explicit": explicit_n, "evidence": explicit_n >= EVIDENCE_AT,
           "skipped_projects": skipped, "videos": [], "critic": None, "rules": [], "candidates": []}
    lines = [f"AEM calibrate · {client.name} ({client.id})"]
    if not ruled:
        lines.append(f"No rulings recorded for {client.contact} yet: nothing to calibrate.")
        out["stopped"] = "no rulings"
        out["text"] = "\n".join(lines)
        return out
    lines.append(", ".join(f"{levels.get(k, 0)} {k}" for k in ("explicit", "implicit", "video", "channel"))
                 + " ruling(s) from the client"
                 + (f"; {levels['remark']} remark(s) on a moment with no keep, change or remove" if levels.get("remark") else "")
                 + (f"; {levels['operator']} of ours (operator), left out" if levels.get("operator") else "") + ".")
    if explicit_n < EVIDENCE_AT:
        lines.append(f"Fewer than {EVIDENCE_AT} explicit cases: every figure below is development data, not evidence.")
    lines.append("Explicit rulings weigh more than implicit acceptances: an explicit ruling is the client's word on one moment; "
                 "an implicit acceptance only says the whole video was not rejected.")

    # Acceptance per video.
    lines += ["", "Acceptance per video"]
    for v in videos:
        rows = v["rows"]
        delivered = len(rows)
        changed = [r for r in rows if r["ruling"] and r["ruling"]["level"] == "explicit" and r["ruling"]["ruling"] in ("change", "remove")]
        kept = [r for r in rows if r["ruling"] and r["ruling"]["level"] == "explicit" and r["ruling"]["ruling"] == "keep"]
        implicit = [r for r in rows if r["ruling"] and r["ruling"]["level"] == "implicit"]
        unruled = [r for r in rows if not r["ruling"]]

        def split(key):
            groups = {}
            for r in rows:
                k = key(r["moment"])
                g = groups.setdefault(k, [0, 0])
                g[1] += 1
                if r in changed:
                    g[0] += 1
            return groups
        asked = split(lambda m: "asked" if m.get("asked") else "added")
        treat = split(lambda m: m.get("treatment") or "treatment not recorded")
        job = split(lambda m: m.get("job") or "job not recorded")
        vdoc = {"project": v["project"], "direction": v["direction"], "notes": v["notes"], "delivered": delivered,
                "changed": len(changed), "kept": len(kept), "implicit": len(implicit), "unruled": len(unruled),
                "asked": {k: {"changed": a, "of": b} for k, (a, b) in asked.items()},
                "treatment": {k: {"changed": a, "of": b} for k, (a, b) in treat.items()},
                "job": {k: {"changed": a, "of": b} for k, (a, b) in job.items()},
                "changed_moments": [r["moment"]["id"] for r in changed],
                "video_level": len(v["video_level"]), "channel_level": len(v["channel_level"])}
        out["videos"].append(vdoc)
        lines.append(f"  {v['project']} · direction: {v['direction']} ({v['notes']} notes) · {delivered} moments delivered")
        if not any(r["ruling"] for r in rows) and not v["video_level"]:
            lines.append("    no rulings on this video yet")
            continue
        lines.append(f"    explicitly changed {len(changed)} of {delivered}{tag}")
        lines.append(f"    explicitly kept {len(kept)} · implicitly accepted {len(implicit)} · not ruled {len(unruled)}"
                     + (f" · video-level remarks {len(v['video_level'])}" if v["video_level"] else ""))
        a, d = asked.get("asked", [0, 0]), asked.get("added", [0, 0])
        lines.append(f"    {d[0]} of {d[1]} additions changed, {a[0]} of {a[1]} asked{tag}")
        on_choice = [r for r in changed if r["choices"]]
        logged = sum(1 for r in rows if r["choices"])
        vdoc["changed_on_our_choice"] = len(on_choice)
        vdoc["moments_with_choices"] = logged
        if logged:
            lines.append(f"    {len(on_choice)} of {len(changed)} changed moment(s) rest on a choice of ours (aem chose); "
                         f"{logged} of {delivered} moments carry one{tag}")
        lines.append("    by treatment: " + " · ".join(f"{k} {x[0]} of {x[1]}" for k, x in sorted(treat.items())))
        lines.append("    by job: " + " · ".join(f"{k} {x[0]} of {x[1]}" for k, x in sorted(job.items())))

    # Critic agreement.
    hits = misses = alarms = passes = 0
    score = weight = 0.0
    unscored = 0
    for v in videos:
        for r in v["rows"]:
            if not r["ruling"]:
                continue
            if not r["critic"] or not r["critic"].get("verdict"):
                unscored += 1
                continue
            flagged = r["critic"]["verdict"] == "flag"
            changed = r["ruling"]["ruling"] in ("change", "remove")
            w = WEIGHT.get(r["ruling"]["level"], 0.0)
            weight += w
            if changed and flagged:
                hits += 1
                score += w
            elif changed:
                misses += 1
            elif flagged:
                alarms += 1
            else:
                passes += 1
                score += w
    scored = hits + misses + alarms + passes
    out["critic"] = {"hits": hits, "misses": misses, "false_alarms": alarms, "correct_passes": passes,
                     "unscored": unscored, "weighted_agreement": round(score / weight, 3) if weight else None,
                     "weights": WEIGHT}
    lines += ["", "Critic agreement"]
    if not scored:
        lines.append(f"  untested: no critic findings (critic.json) recorded for any ruled version ({unscored} ruled moments unscored)")
    else:
        lines.append(f"  changed and flagged (hits) {hits} · changed, not flagged (misses) {misses} · accepted but flagged "
                     f"(false alarms) {alarms} · accepted, not flagged {passes}{tag}")
        lines.append(f"  weighted agreement {score / weight:.2f} (explicit 1, implicit 0.25); {unscored} ruled moment(s) unscored")

    # Rules.
    rows = _rule_rows(client)
    by_rule: dict[str, dict] = {}
    for v in videos:
        for r in v["rows"]:
            ids = set((r["ruling"] or {}).get("rule_ids") or []) | set(r["moment"].get("rule_ids") or [])
            flagged_rules = {f.get("rule") for f in (r["critic"] or {}).get("findings") or []} - {None}
            for rid in ids | flagged_rules:
                d = by_rule.setdefault(rid, {"rulings": 0, "changes": 0, "keeps": 0, "accepted": 0, "words": 0,
                                             "overruled": 0, "videos": set(), "cases": []})
                if not r["ruling"]:
                    continue
                d["rulings"] += 1
                d["videos"].add(v["project"])
                d["cases"] += r["cases"]
                kind = r["ruling"]["ruling"]
                if kind in ("change", "remove"):
                    d["changes"] += 1
                elif kind == "keep":
                    d["keeps"] += 1
                else:
                    d["accepted"] += 1
                if r["ruling"]["level"] == "explicit" and r["ruling"].get("words"):
                    d["words"] += 1
                if rid in flagged_rules and kind in ("keep", "accepted"):
                    d["overruled"] += 1
    lines += ["", "Rules"]
    first = (client.contact.split() or [client.id])[0]
    for rid, d in sorted(by_rule.items()):
        if not d["rulings"]:
            continue
        cells = rows.get(rid)
        tags = (cells[3] if cells else "").replace(" ", "")
        status = cells[4] if cells else "not in rules.md"
        inferred = "I" in tags.split(",") or status.lower().startswith("unconfirmed")
        if d["words"]:
            verdict = f"confirmed by {first}'s words in {d['words']} ruling(s)"
        elif d["changes"]:
            verdict = "suggested by rulings, unconfirmed"
        elif d["overruled"]:
            verdict = "contradicted: the client accepted what the critic flagged under it"
        else:
            verdict = "involved, neither supported nor contradicted"
        doc = {"rule": rid, "rulings": d["rulings"], "changes": d["changes"], "keeps": d["keeps"],
               "accepted": d["accepted"], "confirmed_by_words": d["words"], "overruled": d["overruled"],
               "videos": sorted(d["videos"]), "status": status, "verdict": verdict}
        out["rules"].append(doc)
        lines.append(f"  {rid}: {d['rulings']} ruling(s) ({d['changes']} change, {d['keeps']} keep, {d['accepted']} accepted), "
                     f"confirmed by words {d['words']}, overruled {d['overruled']} — {verdict}{tag}")
        if inferred and cells and (d["changes"] or d["overruled"] or d["words"]):
            if d["words"]:
                new_status = f"{first} stated"
            elif d["changes"]:
                new_status = (f"Unconfirmed (suggested by rulings: {d['changes']} change ruling{'s' if d['changes'] != 1 else ''} "
                              f"on {', '.join(sorted(d['videos']))}; no words from {first} yet)")
            else:
                new_status = f"Unconfirmed (contradicted by {d['overruled']} acceptance(s))"
            proposed = "| " + " | ".join(cells[:4] + [new_status] + cells[5:]) + " |"
            entry = _entry_for(client, d["cases"], rid)
            out["candidates"].append({"rule": rid, "from": status, "to": new_status, "line": proposed, "entry": entry})
    untested = len([r for r in rows if r not in by_rule or not by_rule[r]["rulings"]])
    lines.append(f"  untested: {untested} other rule(s) in {client.raw.get('rules_file', 'rules.md')} have no ruling yet")
    out["untested"] = untested
    if out["candidates"]:
        lines += ["", f"Candidate status changes (proposed lines; {client.raw.get('rules_file', 'rules.md')} is never edited by AEM; "
                      "a status changes only after an entry in the decisions file):"]
        for c in out["candidates"]:
            lines.append(f"  {c['line']}")
            lines.append(f"    rests on: {client.raw.get('decisions_file')} entry \"{c['entry']}\"" if c["entry"]
                         else "    rests on: no decisions-file entry found; write one before changing the status")
    if skipped:
        lines += ["", "Not read: " + "; ".join(skipped)]
    out["text"] = "\n".join(lines)
    return out
