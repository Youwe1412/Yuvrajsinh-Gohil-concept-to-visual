"""The session context the Claude Code plugin adds to the system prompt, built from the registry.

The plugin only inserts this text; what it says is decided here, so a plain `aem context`
shows exactly what the agent is told.
"""
from __future__ import annotations

import re

from . import ledger
from .registry import Context

AGENT_DENIED = ("approve", "reject", "client-said", "allow", "use", "new-client")


def preferences(ctx: Context) -> list[dict]:
    """The client's stated preferences: rows of the rules file whose ID has the client's prefix."""
    prefix = ctx.client.raw.get("preference_prefix")
    if not prefix or not ctx.client.rules_path.exists():
        return []
    rows = []
    for line in ctx.client.rules_path.read_text(encoding="utf-8", errors="replace").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and re.fullmatch(re.escape(prefix) + r"-\d{2,}", cells[0]):
            row = {"id": cells[0], "rule": cells[1]}
            if len(cells) >= 5:
                row.update(kind=cells[2], status=cells[4])
            rows.append(row)
    return rows


def protected_paths(ctx: Context) -> list[str]:
    p = ctx.client.protected
    out = [str(ctx.client.design_system / f) for f in p["design_system"]]
    if ctx.project_dir:
        out += [str(ctx.project_dir / f) for f in p["project"]]
    return out


def build(ctx: Context) -> dict:
    c = ctx.client
    st = ledger.stage_time(ctx) if ctx.project_dir else None
    gate = (f"{st['gate']} ({c.gates.get(st['gate'], '')})" + (f" · scene {st['scene']}" if st["scene"] else "")
            if st else "none open (the operator starts one with /stage <gate> [scene])")
    fps = f"{ctx.fps.numerator}/{ctx.fps.denominator} (from {ctx.fps_source})" if ctx.fps else "unknown"
    prefs = preferences(ctx)
    lines = [
        "# Aavkar Educational Motion Studio (AEM)",
        "",
        "AEM is loaded in this session. The operator chose the active project with /aem use; "
        "do not change it yourself.",
        "",
        f"- Client: {c.name} (id `{c.id}`, contact {c.contact})",
        f"- Project: {ctx.project} at `{ctx.project_dir}`",
        f"- Gate: {gate}",
        f"- Frame rate: {fps}. Use this exact rational for every frame conversion; never assume a rate.",
        f"- Design system: `{c.design_system}`",
        f"- Read first: `{c.decisions_path}` (the client's own words and rulings), then `{c.rules_path}`.",
    ]
    if c.skill:
        lines.append(f"- Skill: use `{c.skill}` for this client's work.")
    lines.append("- Protected files (only the operator's commands write them):")
    lines += [f"  - `{p}`" for p in protected_paths(ctx)]
    if prefs:
        lines.append(f"- {c.contact}'s stated preferences (the {c.raw.get('preference_prefix')}- rows of "
                     f"{c.raw['rules_file']}; cite the ID):")
        for r in prefs:
            lines.append(f"  - {r['id']}: {r['rule']}" + (f" ({r['kind']}; {r['status']})" if r.get("kind") else ""))
    lines += [
        "",
        "While this plugin is loaded:",
        "- Never write, edit or append to events.jsonl, approvals.jsonl, the client's decisions file, "
        "the rules file or critic/labelled-cases.jsonl yourself, by any tool. When one needs a line, "
        "ask the operator to run the command: /stage, /pause, /resume, /wait, /approve, /reject, "
        "/client-said or /allow.",
        "- Never run `aem " + "`, `aem ".join(AGENT_DENIED) + "` yourself. You may run `aem status`, "
        "`aem check-render`, `aem check-approval`, `aem drift`, `aem report` and `aem import-review`.",
        "- Before placing or delivering a render, `aem check-approval <path>` must pass.",
        "- A tool call AEM denies says why and how the operator can approve or override it. Do not try "
        "another route to the same effect; tell the operator what was denied.",
        "- These are recorded checks, not security boundaries.",
    ]
    return {"active": True, "text": "\n".join(lines), "preferences": prefs, "protected": protected_paths(ctx),
            "skill": c.skill, "decisions_file": str(c.decisions_path), "gate": st["gate"] if st else None}


INACTIVE_TEXT = (
    "# Aavkar Educational Motion Studio (AEM)\n\n"
    "AEM is loaded but no project is active. If the work is for an AEM client, ask the operator to run "
    "/aem use <client>/<project>. Never run `aem use` yourself."
)
