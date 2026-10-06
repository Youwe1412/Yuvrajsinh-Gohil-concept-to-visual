# Operating Aavkar Educational Motion Studio

AEM observes and records. It never blocks work in a session you are sitting in; it times the work,
checks every render, records every tool call, and keeps the record (the client's rulings in their words,
approvals tied to the exact render, the critic's labelled cases, time per stage). It interrupts at one
point only: before delivering a render that has no current approval, and then it asks.

**Start Claude Code in the project's folder** (P2: `…/Joel Belton - MergeToMaster/P2 - Claude Code`). You
get one toast, `AEM 1.0.0 · joel/P2 · resolved from folder`, and the client's recall in the transcript:
Joel's J- preferences, his last five rulings in his words, the open questions for him and the
labelled-case count (the agent is given the same). No toast means the plugin is not loaded. Started
somewhere else: `/aem use joel/P2` pins the project to that session.

## The five commands

Only you can run these; the agent asks you in one sentence when one is needed, and carries on once you
have.

| Type | It records |
|---|---|
| `/stage G4 fd_S01_next-token` | a stage starts (the one open for that scene finishes); `/stage G2` for the whole video; `/stage end` to finish |
| `/approve fd_S01_next-token` | an approval of that scene's last checked render, its exact bytes, at the open gate (`/approve <item> <path> <gate>` to name them) |
| `/reject fd_S01_next-token the cursor lands two frames late` | a rejection, with your reason word for word |
| `/client-said video --source "Frame.io, 6 Oct" <Joel's exact words>` | a dated entry in `joel-decisions.md`: his words exactly as you typed them (or the text you selected), marked as typed by you |
| `/report` | `reports/time.md`: per gate and scene, wall time, agent busy, idle, waiting on Joel, paused, unobserved |

Forgot `/stage`? If no stage is open when the agent changes a plan file, a still, a scene source or a
render, AEM opens that gate itself (G2, G3, G4), marked **inferred**, until you start a stage or the
session ends. Time is never lost to a missing `/stage`; start the right one when you notice.

## The delivery confirmation

When the agent is about to write an FCPXML that names a render, or copy a render into a delivery folder
(Joel's `Animations Done`), and that render has no current approval, you get a dialog:

```text
fd_S01 was re-rendered after you approved it. Deliver anyway?      Deliver   Stop
```

**Deliver** records an approval of the render as it is now, marked as made through this confirmation,
and the delivery runs. **Stop** (or closing the dialog) stops that call; the agent is told you stopped
it. A delivery of approved renders asks nothing. In a headless run, where no dialog can be shown, the
call is held once with the exact `/approve` command to type; the same call repeated goes through and is
recorded as delivered without approval.

## The status line

```text
AEM · MergeToMaster · P2 · G4 fd_S01_next-token · 0:42 · 1 stale · 1 ledger edit to review
```

Client · project · open gate and scene (`(inferred)` when AEM opened it) · time in that stage (`paused`
or `waiting on joel` when it is) · approvals made stale by a later render · ledger lines AEM did not
write. It re-reads every 30 seconds. `/aem status` prints the full state.

## When integrity flags something

`· N ledger edits to review` means a line in `events.jsonl`, `approvals.jsonl`, `joel-decisions.md` or
`critic/labelled-cases.jsonl` was written, changed or removed outside `aem`: by you in an editor, or by
the agent. AEM never stops such an edit; it shows it until you have looked.

1. Run `aem integrity` in a terminal. It lists each line, and whether AEM saw the agent write that file
   (which call, when) or the edit came from outside the agent.
2. If it is right (you made it, or you are happy with it): `/accept-edit <reason>` (`--file NAME` for one
   ledger). That is recorded, and the count clears.
3. If it is wrong: say so to the agent, correct the record with the commands above (a rejection, a new
   approval, a new `/client-said` entry), then `/accept-edit` with the reason.

Everything else (every command, file format and limit, Codex, the review inbox) is in [CLI.md](CLI.md).
