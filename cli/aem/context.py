"""The session context the Claude Code plugin adds to the system prompt: the principle, the project, three
rules for the agent, and `aem recall` for the client.

The plugin only inserts this text; what it says is decided here, so a plain `aem context` shows exactly what
the agent is told.
"""
from __future__ import annotations

from . import integrity, ledger, recall
from .registry import Context

# The first principle, as ABOUT.md states it, with the client's name from the registry.
PRINCIPLE = ("AEM observes and records. It never blocks work in a session the operator is sitting in. The record is "
             "the product: rulings in {contact}'s own words, approvals tied to the exact render, the critic's labelled "
             "cases, time per stage. The only interruption is a confirmation before delivering a render that has no "
             "current approval.")

# The commands that write the record: the agent asks the operator to run them.
ASK_FOR = "`/approve <item>`, `/reject <item> <reason>`, `/client-said <scope> <their exact words>`, `/stage <gate> [scene]`"
OPEN = ("`aem status`, `aem recall`, `aem check-render`, `aem check-approval`, `aem evidence`, `aem rounds`, "
        "`aem chose`, `aem report`, `aem integrity`, `aem drift`, `aem inbox` and `aem import-review`")


def record_files(ctx: Context) -> list[str]:
    return [str(p) for p in integrity.tracked_files(ctx)]


def _record_line(ctx: Context) -> str:
    c = ctx.client
    ds = [p.relative_to(c.design_system).as_posix() for p in (c.decisions_path, c.labelled_cases_path)]
    return (f"- The record: `events.jsonl` and `approvals.jsonl` in the project folder; `{ds[0]}` and `{ds[1]}` in the "
            f"design system, `{c.design_system}`. Only `aem` writes it: read these files whenever you need to, and "
            "never write them yourself, with any tool.")


def build(ctx: Context) -> dict:
    c = ctx.client
    first = (c.contact.split() or [c.id])[0]
    op = c.operator
    st = ledger.stage_time(ctx) if ctx.project_dir else None
    if st:
        gate = f"{st['gate']} ({c.gates.get(st['gate'], '')})" + (f" · scene {st['scene']}" if st["scene"] else "")
        if st.get("inferred"):
            gate += f", inferred by AEM ({st.get('inferred_from')} changed while no stage was open)"
    else:
        gate = "none open (AEM infers one from the first plan file, still, scene source or render you change)"
    fps = f"{ctx.fps.numerator}/{ctx.fps.denominator} (from {ctx.fps_source})" if ctx.fps else "unknown"
    lines = [
        "# Aavkar Educational Motion Studio (AEM)",
        "",
        PRINCIPLE.format(contact=first),
        "",
        f"- Project: {ctx.project} ({c.id}) at `{ctx.project_dir}`, resolved from {ctx.resolution.source}. "
        f"Gate: {gate}. Frame rate: {fps}; use this exact rational for every frame conversion, never an assumed rate."
        + (f" Skill: `{c.skill}`." if c.skill else ""),
        _record_line(ctx),
        f"- When an approval, a rejection, {first}'s words or a stage change is needed, ask {op} in one sentence, "
        f"naming the command ({ASK_FOR}), and carry on once {op} has run it. Those commands refuse an agent with one "
        "line; there is no other way to run them.",
        f"- Everything else is yours: {OPEN}. Every tool call is recorded with the files it names, and every render is "
        "checked when its command finishes (the result follows the command's output). Check approvals before a "
        f"delivery (`aem check-approval <render>`): delivering media with no current approval asks {op} first, and "
        "a delivery they stop stays stopped until they say otherwise.",
    ]
    lines.append(f"- When you fill a gap the brief, the plan and {first}'s rulings left open (a default, a treatment, a "
                 "timing), record it: `aem chose \"<what>\" --why \"<what the viewer understands better>\" [--moment M] "
                 "[--rule ID]`. At review, AEM tells the changes that rest on our choices from the ones that do not. "
                 "After a re-render, `aem rounds` shows which earlier findings each version fixed, kept or brought back.")
    integ = integrity.summary(ctx) if ctx.project_dir else {"findings": 0}
    if integ["findings"]:
        lines.append(f"- AEM integrity: {integ['findings']} ledger difference(s) in {', '.join(integ['files'])} were not "
                     f"written by AEM (`aem integrity` lists them). Tell {op}; only {op} accepts them (`/accept-edit`).")
    rec = recall.recall(c, ctx.project)
    lines += ["", rec["text"]]
    return {"active": True, "text": "\n".join(lines), "preferences": rec["preferences"], "recall": rec,
            "record_files": record_files(ctx), "skill": c.skill, "decisions_file": str(c.decisions_path),
            "gate": st["gate"] if st else None}


INACTIVE_TEXT = (
    "# Aavkar Educational Motion Studio (AEM)\n\n"
    "AEM is loaded but no project is resolved here: the working folder is not a registered project and no "
    "project is pinned to this session, so AEM records nothing. If the work is for an AEM client, ask the operator "
    "to start the session in the project's folder or to pin it with /aem use <client>/<project> (`aem use` in a "
    "shell does not pin a session)."
)
