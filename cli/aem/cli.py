"""The `aem` command. Every subcommand takes --json and prints one JSON object with it.

AEM observes and records; it never blocks work. Only the commands that write the record (approve, reject,
client-said, stage, accept-edit, new-client, inbox accept/dismiss) are the operator's (operator.py)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import VERSION, approvals, calibrate, clients, codex, context, doctor, drift, evidence, inbox, integrity, ledger, moments, observe, operator, recall, registry, render, review, rounds, rulings, sentinel
from . import fps as fpsmod
from .util import AemError, expand, fmt_duration, strip_private


def _common(p: argparse.ArgumentParser, *, scope: bool = True) -> None:
    p.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help="print one JSON object")
    if scope:
        p.add_argument("--client", default=argparse.SUPPRESS, help="client id (default: resolved from AEM_PROJECT or the working folder)")
        p.add_argument("--project", default=argparse.SUPPRESS, help="project (default: resolved from AEM_PROJECT or the working folder)")
        p.add_argument("--registry", default=argparse.SUPPRESS, help="registry file (default: AEM_REGISTRY, else the repo's)")


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="aem", description="Aavkar Educational Motion Studio (AEM): it observes and records; "
                                 "it remembers, measures and checks, and never blocks work.")
    ap.add_argument("--json", action="store_true", default=False)
    ap.add_argument("--version", action="version", version=f"aem {VERSION}")
    sub = ap.add_subparsers(dest="cmd", metavar="command")

    p = sub.add_parser("use", help="check <client>/<project> and remember it as the last used (--clear: forget it)")
    p.add_argument("spec", metavar="client/project", nargs="?")
    p.add_argument("--clear", action="store_true", help="forget the last-used hint")
    _common(p, scope=False)
    p.add_argument("--registry", default=None)

    p = sub.add_parser("status", help="the resolved project and how, gate, stage time, approvals")
    _common(p)

    p = sub.add_parser("context", help="the text the Claude Code plugin adds to the system prompt")
    _common(p)

    p = sub.add_parser("calibrate", help="what the client's rulings say: acceptance per video, critic agreement, rules")
    p.add_argument("client_id", metavar="client", nargs="?", help="client id (default: the resolved client)")
    _common(p)

    p = sub.add_parser("recall", help="one screen on a client for a new session: how they review, direction, what they changed "
                                     "last time, channel-level rulings, preferences, last rulings, open questions, labelled cases")
    p.add_argument("client_id", metavar="client", nargs="?", help="client id (default: the resolved client)")
    _common(p)

    p = sub.add_parser("stage", help="start|end|pause|resume|wait <who>|auto <event> (operator only)")
    p.add_argument("action", choices=["start", "end", "pause", "resume", "wait", "auto"])
    p.add_argument("args", nargs="*")
    p.add_argument("--note")
    p.add_argument("--at", help="ISO time, for backfilling a missed event (marked backfilled)")
    p.add_argument("--session", help="(auto) Claude Code session id")
    p.add_argument("--tool", help="(auto tool_call) tool name")
    p.add_argument("--duration-s", type=float, help="(auto tool_call) duration in seconds")
    p.add_argument("--since", help="(auto idle_start) ISO time of the last activity")
    p.add_argument("--origin", help="(auto prompt) where the prompt came from")
    p.add_argument("--turn", help="(auto) Claude Code turn id")
    p.add_argument("--switch", action="store_true", help="(start) finish the stage open for the same scene first")
    _common(p)

    p = sub.add_parser("report", help="write reports/time.md from events.jsonl")
    p.add_argument("--no-write", action="store_true")
    _common(p)

    p = sub.add_parser("approve", help="approve one exact render (operator only)")
    p.add_argument("item")
    p.add_argument("path", nargs="?", help="default: the item's most recently checked render")
    p.add_argument("--gate", help="default: the open stage's gate")
    p.add_argument("--note")
    p.add_argument("--source-revision")
    p.add_argument("--row", help="approve one row of a plan table in <path>, named by its first cell")
    p.add_argument("--label", action="store_true", help="also append the ruling to the client's labelled cases")
    p.add_argument("--delivery-confirmation", action="store_true",
                   help="(the plugin's delivery confirmation) the operator pressed Deliver; recorded as such")
    _common(p)

    p = sub.add_parser("reject", help="reject an item, with a reason (operator only)")
    p.add_argument("item")
    p.add_argument("--reason", required=True)
    p.add_argument("--gate")
    p.add_argument("--path", help="the file rejected (default: the item's latest approved render)")
    p.add_argument("--row", help="with --path: one row of a plan table, named by its first cell")
    p.add_argument("--label", action="store_true", help="also append the ruling to the client's labelled cases")
    _common(p)

    p = sub.add_parser("client-said", help="record the client's exact words (read from stdin) in the decisions file (operator only)")
    p.add_argument("--scope", choices=list(clients.SCOPES), help="channel, video or instance (implied by --about)")
    p.add_argument("--source", required=True, help="where the words came from (Frame.io, WhatsApp, email)")
    p.add_argument("--item", help="the shot, for an instance-scope entry")
    p.add_argument("--about", metavar="MOMENT|video|channel",
                   help="also record the quote as the client's ruling at that level (labelled cases)")
    p.add_argument("--ruling", choices=["keep", "change", "remove"], help="with --about <moment>: what the words rule")
    _common(p)

    p = sub.add_parser("accept-video", help="the client accepted the delivered cut: implicit acceptance for every moment they did not comment on (operator only)")
    p.add_argument("version", help="the delivered version, e.g. v08, or latest: each moment's newest render "
                                   "(moments delivered at different versions)")
    p.add_argument("--source", required=True, help="where the acceptance came from, e.g. \"Frame.io, 12 Oct\"")
    p.add_argument("--before", metavar="FILE|DATETIME",
                   help="with latest: only renders no newer than this (the delivered master's modification time, "
                        "or an ISO date-time)")
    _common(p)

    p = sub.add_parser("inbox", help="what is waiting on the operator: list | accept <id> --ruling R | dismiss <id> --reason")
    p.add_argument("action", nargs="?", default="list", choices=["list", "accept", "dismiss"])
    p.add_argument("id", nargs="?")
    p.add_argument("--ruling", choices=list(inbox.RULINGS))
    p.add_argument("--reason")
    p.add_argument("--label", action="store_true")
    _common(p)

    p = sub.add_parser("integrity", help="compare each ledger with what AEM wrote; list lines AEM did not write")
    _common(p)

    p = sub.add_parser("accept-edit", help="accept the ledger edits integrity found, with a reason (operator only)")
    p.add_argument("--file", action="append", dest="files", metavar="NAME", help="a ledger by file name (default: all with findings)")
    p.add_argument("--reason")
    _common(p)

    p = sub.add_parser("check-approval", help="does this exact file have a standing approval?")
    p.add_argument("path")
    p.add_argument("--item")
    p.add_argument("--gate")
    _common(p)

    p = sub.add_parser("check-render", help="probe a render against the project spec and scan for 1-2 frame flashes")
    p.add_argument("path")
    p.add_argument("--item")
    p.add_argument("--no-record", action="store_true", help="check only; write nothing")
    _common(p)

    p = sub.add_parser("evidence", help="images, sync and facts a critic can read, for one render (or --video: the cut per moment)")
    p.add_argument("path", help="a render, or with --video the assembled cut")
    p.add_argument("--moment", help="the moment it renders (default: from the file name)")
    p.add_argument("--cue", action="append", default=[], metavar="WORD_ID", help="a cue word (repeatable)")
    p.add_argument("--cue-at", action="append", default=[], type=float, metavar="SECONDS",
                   help="a cue word's onset, seconds into the render (repeatable; for hand-measured onsets)")
    p.add_argument("--video", action="store_true", help="the path is the assembled cut: one contact sheet per moment")
    p.add_argument("--offset", type=float, default=0.0, help="(--video) seconds to add to timeline times")
    _common(p)

    p = sub.add_parser("chose", help="record a decision of ours where the brief and the client's rulings left a gap, and why")
    p.add_argument("what", help="the decision, in a few words")
    p.add_argument("--why", required=True, help="one line: what the viewer understands better because of it")
    p.add_argument("--moment", help="the moment it is about (default: the open stage's scene)")
    p.add_argument("--rule", action="append", default=[], metavar="RULE_ID", help="a rule it leans on (repeatable)")
    p.add_argument("--alt", action="append", default=[], metavar="TEXT", help="an option considered and not taken (repeatable)")
    _common(p)

    p = sub.add_parser("rounds", help="each moment's versions side by side: checks, critic findings fixed, kept or back, sound-off read")
    p.add_argument("--moment")
    p.add_argument("--no-write", action="store_true")
    _common(p)

    p = sub.add_parser("import-review", help="map a Frame.io comments CSV to shots and word IDs")
    p.add_argument("csv")
    p.add_argument("--fps", help="the reviewed file's rate as N/D, if it differs from the project's")
    p.add_argument("--start-tc", help="timecode of the reviewed file's first frame (default 00:00:00:00)")
    p.add_argument("--window-s", type=float, default=1.0)
    p.add_argument("--notes", action="store_true",
                   help="the client's timestamped notes on the rough cut (which moments were asked), not a review")
    _common(p)

    p = sub.add_parser("moments", help="build moments/index.json from the plan, placements, words, notes, renders and rulings")
    p.add_argument("--no-write", action="store_true")
    _common(p)

    p = sub.add_parser("observe", help="record one tool call, and say if it delivers unapproved media (the plugin runs this; JSON on stdin)")
    _common(p)

    p = sub.add_parser("rendered", help="check the renders a finished shell command wrote (the plugin runs this; JSON on stdin)")
    _common(p)

    p = sub.add_parser("codex-hook", help="answer one OpenAI Codex hook event (Codex runs this; JSON on stdin)")
    _common(p)

    p = sub.add_parser("codex-config", help="print the hook configuration that makes Codex call AEM")
    p.add_argument("--format", choices=["toml", "json"], default="toml",
                   help="toml for ~/.codex/config.toml (verified with Codex 0.146), json for ~/.codex/hooks.json")
    _common(p, scope=False)

    p = sub.add_parser("doctor", help="is AEM installed and able to record here? (read-only)")
    _common(p)

    p = sub.add_parser("drift", help="text exports vs pages, installed skill vs master, skill rule IDs vs rules")
    p.add_argument("--skills-dir", default="~/.claude/skills")
    _common(p)

    p = sub.add_parser("new-client", help="scaffold a client from registry/client-template and register it (operator only)")
    p.add_argument("id")
    p.add_argument("--name", required=True)
    p.add_argument("--design-system", required=True)
    p.add_argument("--projects-root", required=True)
    p.add_argument("--contact")
    p.add_argument("--skill")
    _common(p, scope=False)
    p.add_argument("--registry", default=None)
    return ap


# --- commands --------------------------------------------------------------------------

def cmd_use(a):
    if a.clear:
        was = registry.clear_hint()
        return {"ok": True, "cleared": True, "was": was}, (
            f"Forgot the last-used hint (was {was['client']}/{was['project']})." if was else "No last-used hint was stored.")
    if not a.spec:
        raise AemError("use takes <client>/<project>, or --clear")
    data = registry.use(a.spec, registry=a.registry)
    f = data["fps"]
    text = (f"{data['client']}/{data['project']} resolves.\n  folder {data['project_dir']}\n"
            f"  fps {f['num']}/{f['den']} (from {f['source']})\n"
            "  A command's project comes from where it runs: AEM_PROJECT=" + f"{data['client']}/{data['project']}"
            + ", the folder, or the Claude Code session pin set by /aem use.")
    return data, text


def _status(ctx) -> dict:
    st = ledger.stage_time(ctx)
    ap = approvals.summary(ctx)
    last_check = next((strip_private(e) for e in reversed(ledger.read_events(ctx)) if e.get("event") == "render_check"), None)
    parts = ["AEM", ctx.client.name, ctx.project or "-",
             (st["gate"] + (f" {st['scene']}" if st["scene"] else "") + (" (inferred)" if st["inferred"] else ""))
             if st else "no gate"]
    if st:
        parts.append(fmt_duration(st["elapsed_s"]) + (" paused" if st["paused"] else "")
                     + (f" {st['waiting'].replace('_', ' ')}" if st["waiting"] else ""))
    line = " · ".join(parts)
    if ap["stale"]:
        line += f" · {ap['stale']} stale"
    parts = {"client": ctx.client.name, "project": ctx.project, "gate": st["gate"] if st else None,
             "scene": st["scene"] if st else None, "since": st["since"] if st else None,
             "paused": bool(st and st["paused"]), "waiting": st["waiting"] if st else None, "stale": ap["stale"],
             "inferred": bool(st and st["inferred"])}
    integ = integrity.summary(ctx)
    if integ["findings"]:
        line += f" · {integ['findings']} ledger edit{'' if integ['findings'] == 1 else 's'} to review"
    parts["integrity"] = integ["findings"]
    try:
        mc = moments.counts(ctx)
    except (OSError, ValueError, AemError):
        mc = None
    if mc:
        line += f" · {mc['moments']} moments · {mc['approved']} approved · {mc['ruled']} ruled"
    parts["moments"] = mc
    return {**ctx.summary(), "stage": st, "approvals": ap, "integrity": integ,
            "last_render_check": last_check, "statusline": line, "statusline_parts": parts,
            "idle_minutes": ctx.client.idle_minutes, "gates": ctx.client.gates}


def _resolution_lines(res: dict) -> list[str]:
    return [f"  resolved from {res['source']}: {res['detail']}" if res.get("detail") else f"  resolved from {res['source']}",
            f"  registry {res['registry']}"]


def _no_project_status(a, exc: AemError):
    reg = registry.load_registry(registry.registry_path(getattr(a, "registry", None)))
    hint, note = registry.read_hint(reg)
    res = {"source": "none", "detail": "no AEM_PROJECT, no session pin, and the working folder is not in a registered project",
           "registry": registry.registry_source(getattr(a, "registry", None))}
    data = {"active": False, "resolved": False, "message": "no project resolved", "hint": exc.hint, "resolution": res,
            "last_used_hint": ({k: v for k, v in hint.items() if not k.startswith("_")} if hint else None),
            "hint_note": note}
    lines = ["No project resolved here (folder not registered).", *_resolution_lines(res)]
    if hint:
        lines.append(f"  last used (a hint only, nothing reads it): {hint['client']}/{hint['project']} at {hint['project_dir']}")
        lines.append(f"    work from that folder, or: AEM_PROJECT={hint['client']}/{hint['project']}")
    if note:
        lines.append(f"  {note}")
    lines.append(f"  {exc.hint}")
    return data, "\n".join(lines)


def cmd_status(a):
    try:
        ctx = registry.context(a, require_project=False)
    except registry.NoProject as exc:
        return _no_project_status(a, exc)
    _hint, note = registry.read_hint(ctx.registry)
    if ctx.project is None:
        data = {"active": False, "resolved": False, **ctx.summary(), "message": "no project resolved: client only",
                "hint_note": note}
        lines = [f"AEM · {ctx.client.name} · no project",
                 f"  client   {ctx.client.id} (the working folder is inside its design system)",
                 f"  design system  {ctx.client.design_system}", *_resolution_lines(data["resolution"])]
        if note:
            lines.append(f"  {note}")
        return data, "\n".join(lines)
    data = {"active": True, "resolved": True, **_status(ctx), "hint_note": note}
    st = data["stage"]
    res = data["resolution"]
    lines = [data["statusline"],
             f"  project  {res['project']}  (resolved from {res['source']}: {res['detail']})",
             f"  folder   {data['project_dir']}",
             f"  design system  {data['design_system']}  ({res['design_system']})",
             f"  fps      {data['fps']['num']}/{data['fps']['den']} (from {data['fps'].get('source')})" if data["fps"]
             else "  fps      unknown (no frame rate stated in the project folder)",
             f"  registry {res['registry']}: {data['registry']}"]
    if note:
        lines.append(f"  {note}")
    if st:
        lines.append(f"  stage    {st['gate']}{' · ' + st['scene'] if st['scene'] else ''} since {st['since']}"
                     + (f" (inferred by AEM from {st['inferred_from']}: no stage was open)" if st["inferred"] else ""))
    ap = data["approvals"]
    lines.append(f"  approvals standing {ap['standing']}, stale {ap['stale']}")
    for sc, v in ap["scenes"].items():
        if v["state"] != "approved":
            lines.append(f"    {sc}: {v['state']}{' — ' + v['why'] if v.get('why') else ''}")
    if data["integrity"]["findings"]:
        lines.append(f"  integrity {data['integrity']['findings']} ledger difference(s) AEM did not write "
                     f"({', '.join(data['integrity']['files'])}): aem integrity, then /accept-edit")
    return data, "\n".join(lines)


def cmd_context(a):
    try:
        ctx = registry.context(a)
    except registry.NoProject:
        return {"active": False, "text": context.INACTIVE_TEXT}, context.INACTIVE_TEXT
    data = context.build(ctx)
    return data, data["text"]


def cmd_calibrate(a):
    if a.client_id:
        reg = registry.load_registry(registry.registry_path(getattr(a, "registry", None)))
        client = registry.find_client(reg, a.client_id)
    else:
        client = registry.context(a, require_project=False).client
    r = calibrate.calibrate(client, getattr(a, "registry", None))
    return r, r["text"]


def cmd_recall(a):
    project = None
    if a.client_id:
        reg = registry.load_registry(registry.registry_path(getattr(a, "registry", None)))
        client = registry.find_client(reg, a.client_id)
    else:
        ctx = registry.context(a, require_project=False)
        client, project = ctx.client, ctx.project
    r = recall.recall(client, project)
    return r, r["text"]


def cmd_stage(a):
    ctx = registry.context(a)
    extra = {k: v for k, v in {"session": a.session, "tool": a.tool, "duration_s": a.duration_s,
                               "inactive_since": a.since, "origin": a.origin, "turn": a.turn}.items() if v is not None}
    rec = ledger.stage(ctx, a.action, a.args, note=a.note, at=a.at, extra=extra, switch=a.switch)
    closed = rec.pop("_closed", None)
    st = ledger.stage_time(ctx)
    data = {"ok": True, "event": strip_private(rec), "stage": st, "statusline": _status(ctx)["statusline"]}
    text = f"{rec['event']} {rec.get('gate') or ''} {rec.get('scene') or ''} at {rec['ts']}"
    if closed:
        data["closed"] = strip_private(closed)
        text = f"finish {closed['gate']} {closed.get('scene') or ''}\n" + text
    return data, " ".join(text.split(" ")).replace("  ", " ")


def cmd_report(a):
    ctx = registry.context(a)
    r = ledger.report(ctx, write=not a.no_write)
    text = r.pop("markdown")
    if r.get("written"):
        text += f"\nWritten to {r['written']}"
    return r, text


def cmd_approve(a):
    ctx = registry.context(a)
    rec = approvals.approve(ctx, a.item, a.path, a.gate, note=a.note, revision=a.source_revision, row=a.row,
                            delivery_confirmation=a.delivery_confirmation)
    rec = strip_private(rec)
    data = {"ok": True, "approval": rec}
    if a.label:
        data["case"] = inbox.label_approval(ctx, rec, a.note)
    if rec.get("item_kind") == "plan_row":
        return data, f"Approved plan row {a.item} at {rec['gate']} ({rec['plan_file']}, {rec['plan_row_sha256'][:12]}…)"
    check = rec.get("render_check")
    warn = "" if check in ("pass", "not a render") else f"\n  note: render check for this file: {check}"
    return data, f"Approved {a.item} at {rec['gate']}: {rec['render']} ({rec['render_sha256'][:12]}…){warn}"


def cmd_reject(a):
    ctx = registry.context(a)
    rec = strip_private(approvals.reject(ctx, a.item, a.reason, gate=a.gate, path=a.path, row=a.row))
    data = {"ok": True, "rejection": rec}
    if a.label:
        data["case"] = inbox.label_rejection(ctx, rec)
    return data, f"Rejected {a.item}: {rec['reason']}"


def cmd_client_said(a):
    ctx = registry.context(a)
    quote = sys.stdin.read()
    r = clients.client_said(ctx, quote, scope=a.scope, source=a.source, item=a.item, about=a.about, ruling=a.ruling)
    text = (f"Already in {r['file']}: {r['heading']} (not written again)" if r.get("existing_entry")
            else f"Recorded in {r['file']} ({r['placed']}): {r['heading']}")
    if r.get("case"):
        c = r["case"]
        text += f"\n  and as a {c['level']} ruling" + (f" ({c['ruling']})" if c.get("ruling") else "") + \
                (f" on {c['moment']}" if c.get("moment") else "") + f" in the labelled cases ({c['case_id']})"
    return r, text


def cmd_accept_video(a):
    ctx = registry.context(a)
    r = rulings.accept_video(ctx, a.version, a.source, before=a.before)
    latest = r["version"] == "latest"
    what = r["version"] if not latest else (
        "each moment's newest render" + (f" before {r['before']}" if r.get("before") else ""))
    text = (f"{what} accepted ({r['source']}): {r['implicit_written']} implicit acceptance(s) written; "
            f"{len(r['explicit'])} moment(s) keep their explicit ruling")
    if r["already_accepted"]:
        text += f"; {len(r['already_accepted'])} already accepted" + ("" if latest else f" at {r['version']}")
    if r.get("versions"):
        counts: dict[str, int] = {}
        for v in r["versions"].values():
            counts[v or "none"] = counts.get(v or "none", 0) + 1
        text += "\n  versions: " + ", ".join(f"{v} ×{n}" for v, n in sorted(counts.items()))
    if r["no_render_at_version"]:
        where = "found" if latest else f"at {r['version']}"
        text += f"\n  no render file {where} for: {', '.join(r['no_render_at_version'])}"
    return r, text


def cmd_integrity(a):
    ctx = registry.context(a, require_project=False)
    r = integrity.check(ctx)
    lines = []
    for f in r["files"]:
        if not f["baseline"]:
            lines.append(f"  {f['name']}: no baseline yet (AEM records one the first time it writes the file)")
        elif not f["findings"]:
            lines.append(f"  {f['name']}: matches what AEM wrote")
        else:
            lines.append(f"  {f['name']}: {len(f['findings'])} difference(s); {f['explanation']}")
            for fi in f["findings"]:
                where = (f"line(s) {', '.join(map(str, fi['lines'][:6]))}" if fi["lines"]
                         else f"after line {fi['after_line']}")
                lines.append(f"    {fi['kind']} {where}" + (f", {fi['removed_count']} AEM line(s) gone" if fi["removed_count"] else ""))
                for x in fi["now"][:3]:
                    lines.append(f"      {x['line']}: {x['text']}")
    head = ("Ledgers match what AEM wrote." if r["ok"] else
            f"{r['findings']} ledger difference(s) AEM did not write ({r['by_agent']} where AEM saw the agent write the "
            f"file, {r['outside_agent']} from outside the agent). The operator accepts them with /accept-edit.")
    text = head + "\n" + "\n".join(lines)
    if not r["ok"]:
        err = AemError(head, data=r)
        err.exit_code = 1
        err.text = text
        raise err
    return r, text


def cmd_accept_edit(a):
    ctx = registry.context(a, require_project=False)
    r = integrity.accept(ctx, a.files, a.reason)
    if not r["accepted"]:
        return r, r["message"]
    return r, "Accepted: " + "; ".join(f"{x['file']} ({', '.join(x['kinds'])})" for x in r["accepted"])


def cmd_check_approval(a):
    ctx = registry.context(a)
    r = approvals.check(ctx, a.path, item=a.item, gate=a.gate)
    return r, f"OK: {r['path']} {r['reason']}"


def cmd_check_render(a):
    ctx = registry.context(a)
    r = render.check_render(ctx, a.path, item=a.item, record=not a.no_record)
    return r, _render_text(r)


def _render_text(r: dict) -> str:
    lines = [f"{r['result'].upper()}: {r['path']} ({r['scene']}) sha256 {r['render_sha256'][:12]}…"]
    for c in r["checks"]:
        mark = {True: "ok  ", False: "FAIL", None: "--  "}[c["ok"]]
        lines.append(f"  {mark} {c['check']}: {c['actual']}" + (f" (expected {c['expected']})" if c["ok"] is False else "")
                     + (f"  [{c['detail']}]" if c.get("detail") and c["ok"] is not True else ""))
    for f in r.get("flashes", []):
        lines.append(f"  {'FLASH' if f.get('severity') == 'fail' else 'minor'}: frame {f['frame']} ({f.get('timecode', '?')}) {f['length']} frame(s), {f['plane']}, {f['area_pct']}% of frame")
    if r.get("stale_marked"):
        lines.append(f"  marked {len(r['stale_marked'])} earlier approval(s) stale")
    return "\n".join(lines)


def cmd_evidence(a):
    ctx = registry.context(a)
    if a.video:
        r = evidence.video(ctx, a.path, offset_s=a.offset)
        return r, (f"{r['sheets']} moment sheets in {r['dir']} ({r['seconds']} s); read {r['video_md']}"
                   + (f"\n  no sheet for: {', '.join(r['skipped'])}" if r["skipped"] else ""))
    r = evidence.build(ctx, a.path, moment=a.moment, cue_at=a.cue_at, cue_ids=a.cue)
    return r, f"{r['toast']} · {r['poses']} poses · {r['seconds']} s\n  {r['evidence_md']}"


def cmd_chose(a):
    ctx = registry.context(a)
    r = rounds.chose(ctx, a.what, why=a.why, moment=a.moment, rules=a.rule, alternatives=a.alt)
    c = r["choice"]
    return r, f"Recorded choice{' on ' + c['scene'] if c.get('scene') else ''}: {c['note']} (why: {c['why']})"


def cmd_rounds(a):
    ctx = registry.context(a)
    r = rounds.rounds(ctx, a.moment, write=not a.no_write)
    text = r.pop("markdown")
    if r.get("written"):
        text += f"\nWritten to {r['written']}"
    return r, text


def cmd_moments(a):
    ctx = registry.context(a)
    index = moments.build(ctx)
    if not a.no_write:
        index["written"] = str(moments.write(ctx, index))
    return index, moments.table(index) + (f"\nWritten to {index['written']}" if index.get("written") else "")


def cmd_import_review(a):
    ctx = registry.context(a)
    if a.notes:
        r = review.import_notes(ctx, a.csv, fps_override=a.fps, start_tc=a.start_tc)
        text = (f"{r['notes']} timestamped notes at {r['fps']}: {r['moments']} moments, {r['asked']} asked, "
                f"{r['added']} added; direction {r['direction']}.")
        if r["covering_no_moment"]:
            text += "\n  covering no moment: " + ", ".join(f"#{n['number'] or n['timecode']}" for n in r["covering_no_moment"])
        if r["unreadable"]:
            text += f"\n  {r['unreadable']} row(s) could not be read"
        return r, text
    r = review.import_review(ctx, a.csv, fps_override=a.fps, start_tc=a.start_tc, window_s=a.window_s)
    text = (f"{r['comments']} comments at {r['fps']}: {r['mapped_to_shots']} on shots, {r['about_edit']} about the edit, "
            f"{r['unreadable']} unreadable.\n" + "\n".join(f"  {k}: {v}" for k, v in r["files"].items()))
    if r["shots_pending"]:
        text += f"\n  {len(r['shots_pending'])} shots have no comment (pending, not a ruling)"
    return r, text


def cmd_observe(a):
    raw = sys.stdin.read()
    try:
        req = json.loads(raw or "{}")
    except json.JSONDecodeError as exc:
        raise AemError(f"observe reads one JSON object on stdin ({exc.msg})")
    r = observe.observe(req, reg_path=getattr(a, "registry", None))
    d = r.get("delivery") or {}
    if d.get("unapproved"):
        text = f"DELIVERY: {d['question']}\n  " + "\n  ".join(d["slash"])
    elif r.get("observed"):
        text = "observed" + (f"; {r['inferred']['gate']} inferred" if r.get("inferred") else "")
    else:
        text = f"not recorded: {r.get('note')}"
    return {"ok": True, **r}, text


def cmd_inbox(a):
    ctx = registry.context(a)
    if a.action == "list":
        its = inbox.items(ctx)
        text = inbox.summary_line(its)
        for i in its:
            text += f"\n  [{i['id']}] {i['title']}" + (f"\n      {i['detail']}" if i.get("detail") else "")
        return {"ok": True, "items": its, "summary": inbox.summary_line(its)}, text
    if not a.id:
        raise AemError(f"inbox {a.action} needs an item id", hint="aem inbox lists them.")
    if a.action == "accept":
        if not a.ruling:
            raise AemError("accept needs --ruling keep|change|remove")
        r = inbox.accept(ctx, a.id, a.ruling, label=a.label, reason=a.reason)
        return r, f"Accepted {a.id} as {a.ruling}" + (f"; labelled case {r['case']['case_id']}" if r.get("case") else "")
    r = inbox.dismiss(ctx, a.id, a.reason or "", label=a.label)
    return r, f"Dismissed {a.id}: {a.reason}"


def cmd_rendered(a):
    raw = sys.stdin.read()
    try:
        req = json.loads(raw or "{}")
    except json.JSONDecodeError as exc:
        raise AemError(f"rendered reads one JSON object on stdin ({exc.msg})")
    try:
        ctx = registry.context(a)
    except registry.NoProject:
        return {"ok": True, "render": False, "outputs": [], "passed": 0, "failed": 0, "text": "",
                "note": "no project resolved"}, "No project resolved here: nothing checked."
    started = req.get("started_at")
    r = sentinel.rendered(ctx, str(req.get("command") or ""), req.get("cwd"),
                          float(started) if started is not None else None, req.get("exit_code"),
                          probe_only=bool(req.get("probe_only")))
    return {"ok": True, **r}, r["text"] or ("A render command." if r["render"] else "Not a render command.")


def cmd_drift(a):
    if getattr(a, "client", None):
        reg = registry.load_registry(registry.registry_path(getattr(a, "registry", None)))
        client = registry.find_client(reg, a.client)
    else:
        client = registry.context(a, require_project=False).client
    r = drift.drift(client, expand(a.skills_dir))
    text = "No drift." if r["ok"] else "\n".join(f"- [{f['check']}] {f.get('file', '')} {f['problem']}" for f in r["findings"])
    if not r["ok"]:
        raise_data = r
        err = AemError(f"{len(r['findings'])} drift finding(s)", data=raise_data)
        err.exit_code = 1
        err.text = text
        raise err
    return r, text


def cmd_doctor(a):
    r = doctor.doctor(a)
    out = doctor.text(r)
    if not r["ok"]:
        err = AemError(f"{r['failed']} check(s) failed", data=r)
        err.exit_code = 1
        err.text = out
        raise err
    return r, out


def cmd_new_client(a):
    rpath = registry.registry_path(a.registry)
    r = clients.new_client(rpath, a.id, name=a.name, design_system=a.design_system, projects_root=a.projects_root,
                           contact=a.contact, skill=a.skill)
    return r, f"Created client {a.id} in {r['design_system']}:\n" + "\n".join(f"  {c}" for c in r["created"])


COMMANDS = {
    "use": cmd_use, "status": cmd_status, "context": cmd_context, "recall": cmd_recall, "calibrate": cmd_calibrate,
    "stage": cmd_stage,
    "report": cmd_report, "moments": cmd_moments, "evidence": cmd_evidence, "accept-video": cmd_accept_video,
    "approve": cmd_approve, "reject": cmd_reject, "client-said": cmd_client_said,
    "check-approval": cmd_check_approval, "check-render": cmd_check_render, "import-review": cmd_import_review,
    "integrity": cmd_integrity, "accept-edit": cmd_accept_edit, "doctor": cmd_doctor, "drift": cmd_drift, "observe": cmd_observe,
    "rendered": cmd_rendered, "inbox": cmd_inbox, "new-client": cmd_new_client, "chose": cmd_chose, "rounds": cmd_rounds,
}


def _jsonable(o):
    from fractions import Fraction
    if isinstance(o, Fraction):
        return fpsmod.rate_str(o)
    if isinstance(o, Path):
        return str(o)
    if isinstance(o, (set, tuple)):
        return list(o)
    return str(o)


def cmd_codex_config(a):
    import shlex
    import shutil
    installed = Path.home() / ".local" / "bin" / "aem"
    launcher = installed if installed.exists() else Path(shutil.which("aem") or Path(__file__).resolve().parents[1] / "bin" / "aem")
    command = f"{shlex.quote(str(launcher))} codex-hook"
    text = codex.config(command, a.format)
    return {"ok": True, "format": a.format, "command": command, "config": text}, text.rstrip("\n")


COMMANDS["codex-config"] = cmd_codex_config


def _codex_hook(a) -> int:
    """Codex reads exactly one JSON object back. Any failure allows the call (fail open) and says why
    on stderr, which Codex logs; the plugin does the same."""
    try:
        print(codex.main_json(sys.stdin.read(), getattr(a, "registry", None)))
    except Exception as exc:  # noqa: BLE001 - a broken check must not stop the agent
        print("{}")
        print(f"aem codex-hook: not checked: {exc}", file=sys.stderr)
    return 0


def main(argv=None) -> int:
    ap = build_parser()
    a = ap.parse_args(argv)
    if a.cmd == "codex-hook":
        return _codex_hook(a)
    as_json = bool(getattr(a, "json", False))
    if not a.cmd:
        ap.print_help()
        return 2
    try:
        operator.require(a.cmd, getattr(a, "action", None) if a.cmd == "inbox" else None)
        data, text = COMMANDS[a.cmd](a)
        if as_json:
            print(json.dumps({"ok": True, **data} if "ok" not in data else data, ensure_ascii=False, default=_jsonable))
        else:
            print(text)
        return 0
    except AemError as exc:
        if as_json:
            payload = {"ok": False, "error": exc.message}
            if exc.hint:
                payload["hint"] = exc.hint
            payload.update({k: v for k, v in exc.data.items() if k not in ("ok", "error")})
            print(json.dumps(payload, ensure_ascii=False, default=_jsonable))
        else:
            out = getattr(exc, "text", None)
            if exc.data and a.cmd == "check-render" and "checks" in exc.data:
                out = _render_text(exc.data)
            print(out or f"aem: {exc.message}", file=sys.stderr if exc.exit_code == 2 else sys.stdout)
            if exc.hint:
                print(f"  {exc.hint}", file=sys.stderr if exc.exit_code == 2 else sys.stdout)
            if exc.data.get("how_to_fix"):
                print(f"  {exc.data['how_to_fix']}")
        return exc.exit_code
