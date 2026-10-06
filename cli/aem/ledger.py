"""events.jsonl: stage events, automatic session events, observed tool calls, and the time report.

Format is the mergetomaster-studio skill's (references/project-ledgers.md), extended:

    {"ts": "...+05:30", "gate": "G2", "scene": null, "event": "start", "note": "..."}

The skill's events are start, finish, waiting_on_<who>, blocked. AEM adds pause, resume, the automatic
events below, stage_inferred (a gate AEM opened itself because no stage was open when the work changed a
plan file, a still, a scene source or a render), observed (one per tool call), render_check, approval,
rejection, client_said, the delivery outcomes and the rest. Extra fields (source, session, tool, duration_s,
inferred, backfilled) are added after the skill's five. Every line is appended, never rewritten.
"""
from __future__ import annotations

from collections import OrderedDict, defaultdict
from . import operator
from .registry import Context
from .util import AemError, append_jsonl, fmt_duration, now, parse_ts, read_jsonl, strip_private, ts

STAGE_EVENTS = {"start", "stage_inferred", "finish", "pause", "resume", "blocked"}
AUTO_EVENTS = {
    "session_start", "session_end", "prompt", "turn_start", "turn_end",
    "tool_call", "idle_start", "idle_end",
}
# Events the plugin records while a session runs: each shows the session was being recorded at that time.
ACTIVITY_EVENTS = AUTO_EVENTS | {"observed", "render_check"}
STARTS = ("start", "stage_inferred")


def record(ctx: Context, event: str, *, gate=None, scene=None, note=None, at: str | None = None,
           fill_stage: bool = True, **extra) -> dict:
    """Append one event. With no gate given, gate (and scene, if missing) come from the current open stage."""
    if fill_stage and gate is None:
        cur = current_stage(read_events(ctx))
        if cur:
            gate = cur[0]
            if scene is None:
                scene = cur[1]
    rec = {"ts": at or ts(), "gate": gate, "scene": scene, "event": event, "note": note}
    if at:
        rec["backfilled"] = True
    for k, v in extra.items():
        if v is not None:
            rec[k] = v
    append_jsonl(ctx.events_path, rec, track=True, by=extra.get("source"))
    return rec


def read_events(ctx: Context) -> list[dict]:
    return read_jsonl(ctx.events_path)


def _key(ev) -> tuple:
    return (ev.get("gate"), ev.get("scene"))


def open_stages(events: list[dict]) -> "OrderedDict[tuple, dict]":
    """(gate, scene) pairs started and not finished, oldest first, with their pause/wait state and whether
    AEM inferred them."""
    opened: OrderedDict = OrderedDict()
    for ev in events:
        e, k = ev.get("event"), _key(ev)
        if e in STARTS and k[0]:
            if e == "stage_inferred" and k in opened:
                continue
            opened[k] = {"since": ev["ts"], "paused": False, "waiting": None, "inferred": e == "stage_inferred",
                         "inferred_from": ev.get("inferred_from")}
        elif e == "finish" and k in opened:
            opened.pop(k)
        elif k in opened:
            if e == "pause":
                opened[k]["paused"] = True
            elif e == "resume":
                opened[k]["paused"] = False
                opened[k]["waiting"] = None
            elif e and (e.startswith("waiting_on_") or e == "blocked"):
                opened[k]["waiting"] = e
    return opened


def current_stage(events: list[dict]) -> tuple | None:
    opened = open_stages(events)
    if not opened:
        return None
    return next(reversed(opened))


def close_inferred(ctx: Context, why: str, *, at=None, events: list[dict] | None = None) -> list[dict]:
    """Finish every stage AEM inferred that is still open: the operator opened a stage, or the session ended."""
    out = []
    for (g, sc), st in open_stages(events if events is not None else read_events(ctx)).items():
        if st["inferred"]:
            out.append(record(ctx, "finish", gate=g, scene=sc, note=why, at=at, inferred=True, source="aem stage"))
    return out


def stage(ctx: Context, action: str, args: list[str], *, note=None, at=None, extra=None, switch=False) -> dict:
    operator.assert_checked("stage")
    events = read_events(ctx)
    opened = open_stages(events)
    extra = extra or {}
    if action == "start":
        if not args:
            raise AemError("stage start needs a gate", hint=f"Gates: {', '.join(ctx.client.gates)}")
        gate = args[0].upper()
        if gate not in ctx.client.gates:
            raise AemError(f"unknown gate {gate!r}", hint=f"Gates for {ctx.client.id}: {', '.join(ctx.client.gates)}")
        scene = args[1] if len(args) > 1 else None
        if (gate, scene) in opened and not opened[(gate, scene)]["inferred"]:
            raise AemError(f"{gate}{' · ' + scene if scene else ''} is already open since {opened[(gate, scene)]['since']}")
        # The operator's stage replaces any AEM inferred: those end now.
        superseded = close_inferred(ctx, f"superseded by stage start {gate}{' ' + scene if scene else ''}", at=at,
                                    events=events)
        if superseded:
            events = read_events(ctx)
            opened = open_stages(events)
        closed = None
        if switch:
            # Moving on: the stage open for the same scene (or the whole video) finishes first.
            same = [k for k in opened if k[1] == scene]
            if same:
                k = same[-1]
                closed = record(ctx, "finish", gate=k[0], scene=k[1], note=f"switched to {gate}", at=at,
                                source="aem stage", **extra)
        rec = record(ctx, "start", gate=gate, scene=scene, note=note, at=at, source="aem stage", **extra)
        if closed:
            rec = {**rec, "_closed": closed}
        return rec
    if action == "end":
        if args:
            k = (args[0].upper(), args[1] if len(args) > 1 else None)
        else:
            if not opened:
                raise AemError("no stage is open")
            k = next(reversed(opened))
        if k not in opened:
            raise AemError(f"{k[0]}{' · ' + k[1] if k[1] else ''} is not open")
        return record(ctx, "finish", gate=k[0], scene=k[1], note=note, at=at, source="aem stage", **extra)
    if action in ("pause", "resume", "wait"):
        if not opened:
            raise AemError(f"no stage is open to {action}", hint="Start one with: aem stage start <gate> [scene]")
        k = next(reversed(opened))
        st = opened[k]
        if action == "pause":
            if st["paused"]:
                raise AemError(f"{k[0]} is already paused")
            return record(ctx, "pause", gate=k[0], scene=k[1], note=note, at=at, source="aem stage", **extra)
        if action == "resume":
            if not st["paused"] and not st["waiting"]:
                raise AemError(f"{k[0]} is not paused or waiting")
            return record(ctx, "resume", gate=k[0], scene=k[1], note=note, at=at, source="aem stage", **extra)
        if not args:
            raise AemError("stage wait needs who", hint=f"For example: aem stage wait {ctx.client.id}")
        who = args[0].lower().strip()
        event = "blocked" if who == "blocked" else f"waiting_on_{who}"
        return record(ctx, event, gate=k[0], scene=k[1], note=note, at=at, source="aem stage", **extra)
    if action == "auto":
        if not args or args[0] not in AUTO_EVENTS:
            raise AemError(f"stage auto needs one of: {', '.join(sorted(AUTO_EVENTS))}")
        rec = record(ctx, args[0], note=note, at=at, source="aem auto", **extra)
        if args[0] == "session_end":  # an inferred stage lasts as long as the session that inferred it
            close_inferred(ctx, "inferred stage ended with the session", at=at)
        return rec
    raise AemError(f"unknown stage action {action!r}", hint="start | end | pause | resume | wait <who> | auto <event>")


# --- the report ----------------------------------------------------------------------

def _union(iv):
    iv = sorted((a, b) for a, b in iv if b > a)
    out = []
    for a, b in iv:
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return [(a, b) for a, b in out]


def _intersect(a, b):
    a, b = _union(a), _union(b)
    i = j = 0
    out = []
    while i < len(a) and j < len(b):
        lo, hi = max(a[i][0], b[j][0]), min(a[i][1], b[j][1])
        if hi > lo:
            out.append((lo, hi))
        if a[i][1] < b[j][1]:
            i += 1
        else:
            j += 1
    return out


def _length(iv):
    return sum(b - a for a, b in _union(iv))


def build_timeline(events: list[dict], report_time: float, client_ids: set) -> dict:
    stages = defaultdict(list)       # (gate, scene) -> [(a, b)]
    open_flags = []
    pauses = defaultdict(list)       # (gate, scene) -> [(a, b)]
    waits = defaultdict(list)        # (gate, scene) -> [(a, b, who)]
    busy, idle, sessions = [], [], []
    notes = []
    o_stage, o_pause, o_wait = {}, {}, {}
    o_turn = o_idle = o_session = None
    last_auto = None
    backfilled = 0

    def close_wait(k, t):
        if k in o_wait:
            a, who = o_wait.pop(k)
            waits[k].append((a, t, who))

    def close_pause(k, t):
        if k in o_pause:
            pauses[k].append((o_pause.pop(k), t))

    inferred = []
    timed = []
    for i, ev in enumerate(events):
        try:
            timed.append((parse_ts(ev["ts"]).timestamp(), i, ev))
        except (KeyError, ValueError):
            notes.append(f"line {ev.get('_line')}: no usable ts, skipped")
    timed.sort()
    for t, _, ev in timed:
        e, k = ev.get("event"), _key(ev)
        if ev.get("backfilled"):
            backfilled += 1
        if e in ACTIVITY_EVENTS:
            last_auto = t
        if e in STARTS:
            for wk in [w for w in o_wait if w[0] == k[0]]:
                close_wait(wk, t)
            if e == "stage_inferred":
                inferred.append({"ts": ev["ts"], "gate": k[0], "scene": k[1], "from": ev.get("inferred_from"),
                                 "why": ev.get("note")})
            if k in o_stage:
                notes.append(f"{ev['ts']}: {k[0]} {k[1] or ''} started twice; kept the first start")
            else:
                o_stage[k] = t
        elif e == "finish":
            for wk in [w for w in o_wait if w[0] == k[0]]:
                close_wait(wk, t)
            close_pause(k, t)
            if k in o_stage:
                stages[k].append((o_stage.pop(k), t))
            else:
                notes.append(f"{ev['ts']}: finish of {k[0]} {k[1] or ''} with no start; ignored")
        elif e == "pause":
            o_pause.setdefault(k, t)
        elif e == "resume":
            close_pause(k, t)
            close_wait(k, t)
        elif e and (e.startswith("waiting_on_") or e == "blocked"):
            close_wait(k, t)
            o_wait[k] = (t, "blocked" if e == "blocked" else e[len("waiting_on_"):])
        elif e == "session_start":
            if o_session is not None:
                sessions.append((o_session, t))
                notes.append(f"{ev['ts']}: session started before the previous one recorded its end")
            o_session = t
        elif e == "session_end":
            if o_session is not None:
                sessions.append((o_session, t))
                o_session = None
            if o_turn is not None:
                busy.append((o_turn, t))
                o_turn = None
                notes.append(f"{ev['ts']}: a turn had no turn_end; closed at session end")
            if o_idle is not None:
                idle.append((o_idle, t))
                o_idle = None
        elif e == "turn_start":
            if o_turn is not None:
                busy.append((o_turn, t))
                notes.append(f"{ev['ts']}: turn_start with a turn still open; closed the earlier one here")
            o_turn = t
            if o_idle is not None:
                idle.append((o_idle, t))
                o_idle = None
        elif e == "turn_end":
            if o_turn is not None:
                busy.append((o_turn, t))
                o_turn = None
        elif e == "idle_start":
            if o_idle is None:
                # The ledger mod notices idleness idle_minutes after the last activity and records
                # that activity's time as inactive_since: idle is measured from there.
                since = ev.get("inactive_since")
                try:
                    o_idle = min(t, parse_ts(since).timestamp()) if since else t
                except ValueError:
                    o_idle = t
        elif e in ("idle_end", "prompt"):
            if o_idle is not None:
                idle.append((o_idle, t))
                o_idle = None

    end_of_record = last_auto if last_auto is not None else report_time
    for k, a in o_stage.items():
        stages[k].append((a, report_time))
        open_flags.append(k)
    for k in list(o_pause):
        close_pause(k, report_time)
    for k in list(o_wait):
        close_wait(k, report_time)
    if o_session is not None:
        sessions.append((o_session, end_of_record))
        notes.append("the last session has no session_end; its observed time is counted to its last recorded event")
    if o_turn is not None:
        busy.append((o_turn, end_of_record))
        notes.append("a turn has no turn_end; counted to the last recorded event")
    if o_idle is not None:
        idle.append((o_idle, end_of_record))
    return {
        "stages": stages, "open": open_flags, "pauses": pauses, "waits": waits,
        "busy": busy, "idle": idle, "sessions": sessions, "notes": notes,
        "backfilled": backfilled, "client_ids": client_ids, "inferred": inferred,
    }


def _measure(span, tl, keys) -> dict:
    """Split one span (list of intervals) into the report's categories."""
    client_ids = tl["client_ids"]
    wait_client, wait_other, paused = [], [], []
    for k in keys:
        for a, b, who in tl["waits"].get(k, []):
            (wait_client if who in client_ids else wait_other).append((a, b))
        paused.extend(tl["pauses"].get(k, []))
    observed = _intersect(span, tl["sessions"])
    busy = _intersect(span, tl["busy"])
    idle = _intersect(span, tl["idle"])
    wc = _intersect(span, wait_client)
    wo = _intersect(span, wait_other)
    pz = _intersect(span, paused)
    accounted = _intersect(observed, busy + idle + wc + wo + pz)
    return {
        "wall_s": _length(span),
        "agent_busy_s": _length(busy),
        "idle_s": _length(idle),
        "waiting_on_client_s": _length(wc),
        "waiting_on_others_s": _length(wo),
        "paused_s": _length(pz),
        "attended_between_turns_s": max(0.0, _length(observed) - _length(accounted)),
        "unobserved_s": max(0.0, _length(span) - _length(observed)),
    }


# Which gates are design, build, review and placement work, when the registry does not say (by the gate's name).
STAGE_GROUP_WORDS = [("design", ("input", "plan", "still", "brief", "design")), ("build", ("render", "build")),
                     ("review", ("critique", "critic", "review")), ("placement", ("deliver", "placement", "place"))]


def stage_groups(ctx: Context) -> "OrderedDict[str, list]":
    given = ctx.client.raw.get("stage_groups")
    if given:
        return OrderedDict((k, list(v)) for k, v in given.items())
    out: OrderedDict = OrderedDict((g, []) for g, _ in STAGE_GROUP_WORDS)
    for gate, name in ctx.client.gates.items():
        low = str(name).lower()
        for g, words in STAGE_GROUP_WORDS:
            if any(w in low for w in words):
                out[g].append(gate)
                break
    return out


COLUMNS = [
    ("wall_s", "Wall"), ("agent_busy_s", "Agent busy"), ("idle_s", "Idle"),
    ("waiting_on_client_s", "Waiting on client"), ("waiting_on_others_s", "Waiting on others"),
    ("paused_s", "Paused"), ("attended_between_turns_s", "Attended, between turns"),
    ("unobserved_s", "Unobserved"),
]


def report(ctx: Context, *, write: bool = True) -> dict:
    events = read_events(ctx)
    rt = now()
    tl = build_timeline(events, rt.timestamp(), ctx.client.waiting_ids)
    stages = tl["stages"]
    gates = OrderedDict((g, []) for g in ctx.client.gates)
    scenes = OrderedDict()
    for (g, s), iv in stages.items():
        gates.setdefault(g, []).append((g, s))
        if s:
            scenes.setdefault(s, []).append((g, s))
    per_gate = OrderedDict()
    for g, keys in gates.items():
        if not keys:
            continue
        span = [x for k in keys for x in stages[k]]
        per_gate[g] = _measure(span, tl, keys)
    per_scene = OrderedDict()
    for s, keys in scenes.items():
        span = [x for k in keys for x in stages[k]]
        per_scene[s] = _measure(span, tl, keys)
    per_pair = OrderedDict()
    for k, iv in stages.items():
        per_pair[f"{k[0]} · {k[1] or '(whole video)'}"] = _measure(iv, tl, [k])
    per_group = OrderedDict()
    for group, gates_ in stage_groups(ctx).items():
        keys = [k for k in stages if k[0] in gates_]
        span = [x for k in keys for x in stages[k]]
        if span:
            per_group[f"{group} ({', '.join(gates_)})"] = _measure(span, tl, keys)
    per_moment, unattributed, idle_moments = _moment_time(ctx, stages, tl)
    all_stage = [x for iv in stages.values() for x in iv]
    in_session = _union(tl["sessions"])
    outside = _length(in_session) - _length(_intersect(in_session, all_stage))
    result = {
        "client": ctx.client.id, "project": ctx.project, "generated": ts(rt),
        "events": len(events), "per_gate": per_gate, "per_scene": per_scene, "per_stage": per_pair,
        "per_stage_group": per_group, "per_moment": per_moment, "unattributed": unattributed,
        "moments_without_stages": idle_moments,
        "open_stages": [f"{g} · {s or '(whole video)'}" for g, s in tl["open"]],
        "session_time_outside_stages_s": outside,
        "observed_session_s": _length(in_session),
        "inferred_stages": tl["inferred"],
        "backfilled_events": tl["backfilled"], "notes": tl["notes"],
    }
    md = render_markdown(ctx, result)
    if write:
        out = ctx.project_dir / "reports" / "time.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(md, encoding="utf-8")
        result["written"] = str(out)
    result["markdown"] = md
    return result


def _moment_time(ctx: Context, stages: dict, tl: dict) -> tuple["OrderedDict[str, dict]", dict | None, int]:
    """Stage time per moment: only stages whose scene names the moment. The rest stays unattributed."""
    from . import moments as momentsmod
    try:
        index = momentsmod.read_index(ctx) or momentsmod.build(ctx)
    except (OSError, ValueError, AemError):
        return OrderedDict(), None, 0
    ms = index.get("moments") or []
    out: OrderedDict = OrderedDict()
    claimed = set()
    for m in ms:
        keys = [k for k in stages if k[1] and momentsmod._matches(k[1], m)]
        if keys:
            claimed.update(keys)
            out[m["id"]] = _measure([x for k in keys for x in stages[k]], tl, keys)
    rest = [k for k in stages if k not in claimed]
    loose = _measure([x for k in rest for x in stages[k]], tl, rest) if rest else None
    return out, loose, len(ms) - len(out)


def _table(rows: "OrderedDict[str, dict]", first: str) -> list[str]:
    head = f"| {first} | " + " | ".join(c[1] for c in COLUMNS) + " |"
    sep = "|---|" + "---:|" * len(COLUMNS)
    lines = [head, sep]
    for name, m in rows.items():
        lines.append(f"| {name} | " + " | ".join(fmt_duration(m[c[0]]) for c in COLUMNS) + " |")
    return lines


def render_markdown(ctx: Context, r: dict) -> str:
    L = [
        f"# Time report · {ctx.client.name} · {ctx.project}",
        "",
        f"Generated {r['generated']} by `aem report` from `events.jsonl` ({r['events']} events). "
        "Durations are h:mm:ss.",
        "",
        "## How these numbers were computed",
        "",
        "Every figure is the difference between clock timestamps recorded in `events.jsonl`; "
        "nothing here is estimated.",
        "",
        "- **Wall**: from a stage's `start` to its `finish`. Where one gate or scene has overlapping "
        "stages, the overlap is counted once.",
        "- **Agent busy**: inside the stage, between `turn_start` and `turn_end` events.",
        "- **Idle**: inside the stage, from the last activity before an `idle_start` (recorded once there was no "
        f"input or agent activity for the client's idle_minutes, {ctx.client.idle_minutes:g} min) to the next activity.",
        "- **Waiting on client**: from a `waiting_on_<client>` event to the next start, finish or resume "
        "of that gate. **Waiting on others** is any other `waiting_on_…` or `blocked`.",
        "- **Paused**: from `pause` to `resume` (or the stage's finish).",
        "- **Attended, between turns**: observed session time in the stage that is none of the above "
        "(you reading, typing or deciding; under the idle threshold).",
        "- **Unobserved**: stage time when no Claude Code session with the AEM ledger was recording, so "
        "agent-busy and idle could not be measured. It is not counted as work or idle.",
        "",
        "Categories can overlap (the agent can run while you wait on the client), so columns other than "
        "Wall need not add up to Wall. These numbers are for planning the next video, not for billing.",
        "",
    ]
    if r["per_gate"]:
        L += ["## Per gate", ""] + _table(r["per_gate"], "Gate") + [""]
    else:
        L += ["## Per gate", "", "No stages recorded yet.", ""]
    if r["per_scene"]:
        L += ["## Per scene", ""] + _table(r["per_scene"], "Scene") + [""]
    if r["per_stage"]:
        L += ["## Per gate and scene", ""] + _table(r["per_stage"], "Stage") + [""]
    if r["per_stage_group"]:
        L += ["## Per stage (design, build, review, placement)", ""] + _table(r["per_stage_group"], "Stage") + [""]
    if r["per_moment"] or r["unattributed"]:
        rows = OrderedDict(r["per_moment"])
        if r["unattributed"]:
            rows["(unattributed: whole-video stages, or scenes that name no moment)"] = r["unattributed"]
        L += ["## Per moment", "",
              "Only stages whose scene names a moment are attributed to it; whole-video stages stay unattributed and "
              "are never spread across moments." + (f" {r['moments_without_stages']} moment(s) have no stage of their own."
                                                     if r["moments_without_stages"] else ""), ""]
        L += _table(rows, "Moment") + [""]
    L += [
        "## Outside any stage",
        "",
        f"Observed session time with no stage open: {fmt_duration(r['session_time_outside_stages_s'])} "
        f"(of {fmt_duration(r['observed_session_s'])} observed in total).",
        "",
    ]
    if r["open_stages"]:
        L += ["## Open stages", "", "Started and not finished; counted to the report time above:", ""]
        L += [f"- {s}" for s in r["open_stages"]] + [""]
    if r["inferred_stages"]:
        L += ["## Inferred stages", "",
              "No stage was open when the work changed these files, so AEM opened the gate each belongs to itself. "
              "Each ran until the next /stage or the end of its session. They are counted above like any stage.", ""]
        L += [f"- {x['ts']}: {x['gate']}, {x['why'] or ('from ' + str(x['from']))}" for x in r["inferred_stages"]] + [""]
    if r["backfilled_events"]:
        L += [f"**{r['backfilled_events']} events were backfilled** (entered with an explicit time, "
              "not recorded live).", ""]
    if r["notes"]:
        L += ["## Ledger notes", ""] + [f"- {n}" for n in r["notes"]] + [""]
    return "\n".join(L)


def last_events(ctx: Context, n: int = 10) -> list[dict]:
    return [strip_private(e) for e in read_events(ctx)[-n:]]


def stage_time(ctx: Context) -> dict | None:
    """The current stage and its wall time so far (for the status line)."""
    events = read_events(ctx)
    opened = open_stages(events)
    if not opened:
        return None
    k = next(reversed(opened))
    st = opened[k]
    secs = now().timestamp() - parse_ts(st["since"]).timestamp()
    return {"gate": k[0], "scene": k[1], "since": st["since"], "elapsed_s": secs,
            "paused": st["paused"], "waiting": st["waiting"], "inferred": st["inferred"],
            "inferred_from": st["inferred_from"]}
