"""aem inbox: what is waiting on the operator, and the labelled case each ruling leaves.

Items, each with an id and the exact aem commands its buttons run:

  plan:<file>#<row>   a row of a plan table (shotlist.md by default) with no ruling on its text  G2
  still:<path>        an image under stills/ with no ruling on its SHA-256                       G3
  render:<scene>      the scene's last checked render, unchanged since, with no ruling           G4
  denial:<line>       a guard denial in events.jsonl the operator has not answered
  comment:<file>#<n>  a client comment imported by aem import-review, not yet ruled on

Approving or rejecting with --label appends one line to the client's critic/labelled-cases.jsonl
in the file's own fields (its header line), with "source" set to the operator's id. Those lines are
"development case": the operator's ruling is not the client's, so the critic's count of labelled
cases (M-19) is unchanged. An accepted client comment keeps the client's words verbatim and is
"labelled" only when it has a ruling, the words and the reviewed render's SHA-256.
"""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from . import approvals, ledger, operator
from .registry import Context
from .util import AemError, append_jsonl, now, parse_ts, read_jsonl, rel_to, sha256_file, today, ts

DEFAULTS = {
    "plan_files": ["shotlist.md"],
    "stills_dirs": ["stills"],
    "gates": {"plan_row": "G2", "still": "G3", "render": "G4"},
    "denial_days": 2,
    "reviews_dir": "reviews",
}
RULINGS = ("keep", "change", "remove")


def settings(ctx: Context) -> dict:
    cfg = {**DEFAULTS, **(ctx.client.raw.get("review_inbox") or {}), **(ctx.project_settings().get("review_inbox") or {})}
    cfg["gates"] = {**DEFAULTS["gates"], **(cfg.get("gates") or {})}
    return cfg


# --- labelled cases --------------------------------------------------------------------

def _header(ctx: Context) -> dict:
    return next((h for h in read_jsonl(ctx.client.labelled_cases_path, keep_comments=True) if "_comment" in h), {})


def words_field(ctx: Context) -> str:
    fields = list((_header(ctx).get("fields") or {}).keys())
    return next((f for f in fields if f.endswith("_words")), "client_words")


def append_case(ctx: Context, *, item_kind: str, item: str, ruling: str | None, reason: str | None,
                gate: str | None = None, sha: str | None = None, files: list[Path] | None = None,
                decision: str | None = None, inbox_ref: str | None = None, extra: dict | None = None) -> dict:
    """One operator ruling as a labelled case, in the client's field names. Never a client ruling."""
    if not ctx.client.labelled_cases_path.parent.is_dir():
        raise AemError(f"no critic folder at {ctx.client.labelled_cases_path.parent}")
    stamp = now().strftime("%H%M%S")
    case = {
        "case_id": f"{ctx.project}-{item}-{today()}-{ctx.client.operator_id}-{stamp}",
        "status": "development case",
        "video": ctx.project,
        "shot": item,
        "word_ids": None,
        "render_sha256": sha,
        "frames_or_crops": [rel_to(f.resolve(), ctx.client.projects_root.resolve()) for f in (files or [])],
        "ruling": ruling,
        words_field(ctx): None,
        "ruling_date": today(),
        "source": ctx.client.operator_id,
        "rule_ids": [],
        "critic_verdict_g5": None,
        "critic_agreed": None,
        "notes": (f"Ours: the operator's ruling in the AEM review inbox, not {ctx.client.contact}'s. "
                  + (f"Reason: {reason.strip()}" if reason and reason.strip() else "No reason given.")),
        # AEM's additions: what was reviewed and at which gate.
        "item_kind": item_kind,
        "gate": gate,
        "reason": reason.strip() if reason else None,
    }
    if decision:
        case["decision"] = decision
    if inbox_ref:
        case["inbox_ref"] = inbox_ref
    case.update(extra or {})
    prov = operator.provenance()
    if prov:
        case.update(via=prov["via"], prompt_id=prov["prompt_id"])
    append_jsonl(ctx.client.labelled_cases_path, case, track=True, by="aem inbox")
    ledger.record(ctx, "labelled_case", scene=item, gate=gate, note=case["case_id"], fill_stage=False,
                  case_id=case["case_id"], item_kind=item_kind, ruling=ruling, inbox_ref=inbox_ref, source="aem inbox")
    return case


def label_approval(ctx: Context, rec: dict, reason: str | None = None) -> dict:
    return _label(ctx, rec, "keep", reason)


def label_rejection(ctx: Context, rec: dict) -> dict:
    return _label(ctx, rec, "change", rec.get("reason"))


def _label(ctx: Context, rec: dict, ruling: str, reason: str | None) -> dict:
    ik = approvals.item_kind(rec)
    files = [ctx.project_dir / rec["render"]] if rec.get("render") else []
    # A plan row is not a render: its text's hash goes in plan_row_sha256, render_sha256 stays empty.
    extra = ({"plan_file": rec.get("plan_file"), "plan_row": rec.get("plan_row"),
              "plan_row_sha256": rec.get("plan_row_sha256")} if ik == "plan_row" else {})
    return append_case(ctx, item_kind=ik, item=rec["scene"], ruling=ruling, reason=reason, gate=rec.get("gate"),
                       sha=rec.get("render_sha256"), files=files, extra=extra)


# --- what is waiting --------------------------------------------------------------------

def _decided(lines: list[dict], of_kind: str) -> set:
    out = set()
    for l in lines:
        if approvals.item_kind(l) != of_kind or approvals.kind(l) == "stale":
            continue
        out.add(l.get("plan_row_sha256") if of_kind == "plan_row" else l.get("render_sha256"))
    return out


def _resolved_refs(events: list[dict]) -> set:
    return {e["inbox_ref"] for e in events if e.get("inbox_ref") and e.get("event") in ("inbox_resolved", "allow")}


def items(ctx: Context) -> list[dict]:
    cfg = settings(ctx)
    lines = approvals.read(ctx)
    events = ledger.read_events(ctx)
    gates = cfg["gates"]
    out: list[dict] = []

    # Plan rows.
    decided = _decided(lines, "plan_row")
    for f in cfg["plan_files"]:
        path = ctx.project_dir / f
        for r in approvals.plan_rows(path):
            if r["sha256"] in decided:
                continue
            prev = approvals.latest_approval(lines, r["row"], of_kind="plan_row")
            rel = rel_to(path, ctx.project_dir)
            out.append(_item(f"plan:{rel}#{r['row']}", "plan_row", r["row"], gates["plan_row"],
                             title=f"{r['row']} ({rel} line {r['line']})", detail=r["text"],
                             note="changed since it was approved" if prev else None,
                             approve=["approve", r["row"], str(path), "--row", r["row"], "--gate", gates["plan_row"], "--label"],
                             reject=["reject", r["row"], "--path", str(path), "--row", r["row"], "--gate", gates["plan_row"], "--label"]))

    # Stills.
    decided = _decided(lines, "still")
    for d in cfg["stills_dirs"]:
        folder = ctx.project_dir / d
        if not folder.is_dir():
            continue
        for p in sorted(folder.rglob("*")):
            if not p.is_file() or p.suffix.lower() not in approvals.STILL_EXTENSIONS or p.name.startswith("."):
                continue
            sha = sha256_file(p)
            if sha in decided:
                continue
            item = approvals.item_from_path(p)
            rel = rel_to(p, ctx.project_dir)
            out.append(_item(f"still:{rel}", "still", item, gates["still"], title=rel, detail=None, path=str(p),
                             approve=["approve", item, str(p), "--gate", gates["still"], "--label"],
                             reject=["reject", item, "--path", str(p), "--gate", gates["still"], "--label"]))

    # Renders: each scene's last check, if the file is unchanged since and nobody ruled on it.
    decided = _decided(lines, "render")
    last: dict[str, dict] = {}
    for e in events:
        if e.get("event") == "render_check" and e.get("scene") and e.get("render"):
            last[e["scene"]] = e
    for scene, e in last.items():
        p = ctx.project_dir / e["render"]
        if e.get("render_sha256") in decided or not p.is_file() or sha256_file(p) != e.get("render_sha256"):
            continue
        detail = "check passed" if e.get("result") == "pass" else "check FAILED: " + "; ".join(e.get("failures") or [e.get("note") or ""])
        out.append(_item(f"render:{scene}", "render", scene, gates["render"], title=e["render"], detail=detail,
                         path=str(p), check=e.get("result"),
                         approve=["approve", scene, str(p), "--gate", gates["render"], "--label"],
                         reject=["reject", scene, "--path", str(p), "--gate", gates["render"], "--label"]))

    # Guard denials not yet answered.
    resolved = _resolved_refs(events)
    since = now() - timedelta(days=float(cfg["denial_days"]))
    for e in events:
        if e.get("event") != "denial" or f"denial:{e['_line']}" in resolved:
            continue
        try:
            if parse_ts(e["ts"]) < since:
                continue
        except (KeyError, ValueError):
            continue
        ref = f"denial:{e['_line']}"
        target = e.get("rule") or ""
        out.append(_item(ref, "override", e.get("rule") or "denial", None,
                         title=f"{e.get('rule')} denied {e.get('tool')}: {(e.get('subject') or '')[:160]}",
                         detail=e.get("note"),
                         approve=["allow", target, "--once", "--reason", f"approved in the AEM inbox ({ref})",
                                  "--inbox-ref", ref, "--label"],
                         reject=["inbox", "dismiss", ref, "--label"],
                         approve_label="Allow once"))

    # Imported client comments.
    rdir = ctx.project_dir / cfg["reviews_dir"] / ctx.client.id
    if rdir.is_dir():
        wf = words_field(ctx)
        for f in sorted(rdir.glob("*-labelled-cases.draft.jsonl")):
            for n, d in enumerate(read_jsonl(f), start=1):
                ref = f"comment:{f.name}#{n}"
                if ref in resolved:
                    continue
                words = d.get(wf) or []
                said = " / ".join(words) if isinstance(words, list) else str(words)
                acts = [{"label": r.capitalize(), "argv": ["inbox", "accept", ref, "--ruling", r, "--label"], "needs_reason": False}
                        for r in RULINGS]
                out.append(_item(ref, "client_comment", d.get("shot") or "?", None, title=f"{d.get('shot')}: {ctx.client.contact} said",
                                 detail=said, approve=None, reject=["inbox", "dismiss", ref, "--label"], actions=acts,
                                 words_from=d.get("source")))
    return out


def _item(ref, kind, item, gate, *, title, detail, approve, reject, approve_label="Approve", actions=None, **extra) -> dict:
    acts = list(actions or [])
    if approve:
        acts.append({"label": approve_label, "argv": approve, "needs_reason": False})
    acts.append({"label": "Reject", "argv": reject, "needs_reason": True})
    return {"id": ref, "kind": kind, "item": item, "gate": gate, "title": title, "detail": detail,
            "actions": acts, **{k: v for k, v in extra.items() if v is not None}}


# --- resolving the items that are not approvals ---------------------------------------------

def _find(ctx: Context, ref: str) -> dict:
    for it in items(ctx):
        if it["id"] == ref:
            return it
    raise AemError(f"nothing waiting with id {ref!r}", hint="aem inbox lists what is waiting.")


def accept(ctx: Context, ref: str, ruling: str, *, label: bool, reason: str | None = None) -> dict:
    operator.assert_checked("inbox accept")
    """Accept an imported client comment as the client's ruling on the shot."""
    if ruling not in RULINGS:
        raise AemError(f"ruling must be one of {', '.join(RULINGS)}")
    it = _find(ctx, ref)
    if it["kind"] != "client_comment":
        raise AemError(f"{ref} is not a client comment; approve it with the command its item lists")
    fname, n = ref.split(":", 1)[1].rsplit("#", 1)
    draft = read_jsonl(ctx.project_dir / settings(ctx)["reviews_dir"] / ctx.client.id / fname)[int(n) - 1]
    wf = words_field(ctx)
    item = approvals.item_from_path(Path(draft.get("shot") or "?"))
    a = approvals.latest_approval(approvals.read(ctx), item)
    sha = draft.get("render_sha256") or (a or {}).get("render_sha256")
    words = draft.get(wf)
    case = None
    if label:
        status = "labelled" if (words and sha) else "development case"
        notes = (f"Ours: {ctx.client.contact}'s words are verbatim from the review CSV ({draft.get('source')}); "
                 f"the operator read them as '{ruling}' in the AEM review inbox."
                 + (f" Reason: {reason.strip()}" if reason and reason.strip() else "")
                 + ("" if sha else " No approved render found for the shot, so no SHA-256: a development case."))
        extra = {wf: words, "word_ids": draft.get("word_ids"), "words_source": draft.get("source"),
                 "status": status, "notes": notes}
        case = append_case(ctx, item_kind="client_comment", item=draft.get("shot") or item, ruling=ruling,
                           reason=reason, sha=sha, decision="accepted", inbox_ref=ref, extra=extra)
    ev = ledger.record(ctx, "inbox_resolved", scene=it["item"], note=f"accepted as {ruling}", fill_stage=False,
                       inbox_ref=ref, decision="accepted", ruling=ruling, case_id=(case or {}).get("case_id"),
                       source="aem inbox accept")
    return {"ok": True, "id": ref, "ruling": ruling, "event": ev, "case": case}


def dismiss(ctx: Context, ref: str, reason: str, *, label: bool) -> dict:
    operator.assert_checked("inbox dismiss")
    """Close a denial or a client comment without approving it, with a reason."""
    if not reason or not reason.strip():
        raise AemError("dismissing needs a reason")
    it = _find(ctx, ref)
    if it["kind"] not in ("override", "client_comment"):
        raise AemError(f"{ref} is a {it['kind']}; reject it with the command its item lists")
    case = None
    if label:
        extra = {"shot": None, "rule": it["item"]} if it["kind"] == "override" else {}
        case = append_case(ctx, item_kind=it["kind"], item=it["item"], ruling=None, reason=reason,
                           decision="dismissed", inbox_ref=ref, extra=extra)
    ev = ledger.record(ctx, "inbox_resolved", scene=None if it["kind"] == "override" else it["item"],
                       note=reason.strip(), fill_stage=False, inbox_ref=ref, decision="dismissed",
                       case_id=(case or {}).get("case_id"), source="aem inbox dismiss")
    return {"ok": True, "id": ref, "decision": "dismissed", "event": ev, "case": case}


def label_allow(ctx: Context, allow: dict, ref: str | None) -> dict:
    return append_case(ctx, item_kind="override", item=allow["target"], ruling=None, reason=allow["reason"],
                       decision="allowed once" if allow["once"] else "allowed", inbox_ref=ref,
                       extra={"shot": None, "rule": allow["target"]})


def summary_line(its: list[dict]) -> str:
    if not its:
        return "Nothing is waiting on you."
    counts: dict[str, int] = {}
    for i in its:
        counts[i["kind"]] = counts.get(i["kind"], 0) + 1
    names = {"plan_row": "plan row", "still": "still", "render": "render", "override": "denial",
             "client_comment": "client comment"}
    return f"{len(its)} waiting: " + ", ".join(f"{n} {names[k]}{'s' if n > 1 else ''}" for k, n in counts.items())
