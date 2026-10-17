# Operating Aavkar Educational Motion Studio

AEM observes and records. It never blocks work in a session you are sitting in; it times the work,
checks every render, records every tool call, and keeps the record (the client's rulings in their words,
approvals tied to the exact render, the critic's labelled cases, time per stage). It interrupts at one
point only: before delivering a render that has no current approval, and then it asks.

**Start Claude Code in the project's folder** (P2: `…/Joel Belton - MergeToMaster/P2 - Claude Code`). You
get one toast, `AEM 1.1.0 · joel/P2 · resolved from folder`, and the client's recall in the transcript:
how Joel reviews, how much he directed the last video and this one, what he changed last time (in his
words), his channel-level rulings, his J- preferences, his last five rulings, the open questions for him
and the labelled-case count (the agent is given the same). No toast means the plugin is not loaded.
Started somewhere else: `/aem use joel/P2` pins the project to that session.

## The commands that write the record

Only you can run these; the agent asks you in one sentence when one is needed, and carries on once you
have.

| Type | It records |
|---|---|
| `/stage G4 fd_S01_next-token` | a stage starts (the one open for that scene finishes); `/stage G2` for the whole video; `/stage end` to finish |
| `/approve fd_S01_next-token` | an approval of that scene's last checked render, its exact bytes, at the open gate (`/approve <item> <path> <gate>` to name them) |
| `/reject fd_S01_next-token the cursor lands two frames late` | a rejection, with your reason word for word |
| `/client-said video --source "Frame.io, 6 Oct" <Joel's exact words>` | a dated entry in `joel-decisions.md`: his words exactly as you typed them (or the text you selected), marked as typed by you |
| `/client-said --about fd_S04_50ms --ruling change --source "WhatsApp, 14 Sep" <his words>` | the same entry, and his ruling on that moment in the labelled cases (`--about video` or `--about channel` for a remark about the video or about you) |
| `/accept-video v08 Frame.io, 14 Sep 2026` | he accepted the delivered video: an implicit acceptance for every moment he did not comment on |
| `/report` | `reports/time.md`: per gate and scene, per stage group and per moment: wall time, agent busy, idle, waiting on Joel, paused, unobserved |

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
AEM · MergeToMaster · P2 · G4 fd_S01_next-token · 0:42 · 1 stale · 1 ledger edit to review · 12 moments · 3 approved · 0 ruled
```

Client · project · open gate and scene (`(inferred)` when AEM opened it) · time in that stage (`paused`
or `waiting on joel` when it is) · approvals made stale by a later render · ledger lines AEM did not
write · the moments index: moments, how many have a standing approval, how many the client has ruled
on. It re-reads every 30 seconds. `/aem status` prints the full state.

## Moments, evidence and the client's review

**Moments.** A moment is one thing placed in the cut: its words, its teaching job, whether the client
asked for it or we added it, its contract from the shot list (what the viewer knows before and after,
what must stay true, where the picture stops being accurate), its treatment, renders, approval, critic
findings, the client's ruling and its time. `aem moments` (or `/aem moments`) builds
`moments/index.json` from the plan, the placements, the words, the client's notes, the renders and the
rulings, prints the table, and lists anything it could not link. A moment is "asked" when one of the
client's timestamped notes lies within a second of its words; a video with no notes has every moment
"added", and the table says so at the top. `/report` adds time per moment and per stage group (design,
build, review, placement); time no moment claims is shown as unattributed, never spread.

**Evidence.** After every render the sentinel runs `aem evidence` on what it wrote and you get a toast:
`evidence ready: fd_S01_next-token v09, sync max offset 2f, no flash`. In `reviews/<moment>/<version>/`
are the readable poses (each cue word's frame, the first and the last) as 1920-wide PNGs with
390-wide phone crops, an 8-frame strip around the fastest transition, `sync.json`, `facts.json` and
`evidence.md`, which names every image and is all a critic subagent needs. It only informs: nothing
waits on it and nothing is refused because of it. On P1's 59 masters it took 1.4 s per render (median),
about 2.4 s per 10 s of 4K scene, before the sound-off sheet added about a quarter more. `aem evidence --video <cut>` makes one contact sheet per moment from
the assembled cut (P1's 11-minute film: 58 sheets in 8 s).

**Judging, not only checking.** Evidence also lists frozen holds (`holds.json`) and makes a silent 2 fps
sheet with `retell.md`: give a fresh subagent that file alone and it retells the moment with the sound
off; the critic then says whether that matches what the viewer should know after (`retell_match`). Put a
few reference stills in the project's `references/` and evidence links them for a director's review
("what looks assembled, slow or generic beside these?"). After each repair, `aem rounds` shows what each
version fixed, kept or brought back. The agent logs its own decisions with `aem chose`; at the client's
review, `aem calibrate` says how many of the changed moments rested on one of ours.

**The client's review.** Joel reviews the finished video on Frame.io and never sees the process, so
wait for his review. Export his comments as CSV and run `aem import-review <csv>`: each comment is
mapped to the moment it is on (a candidate for his explicit ruling) or, on no moment of ours, kept as a
remark about the video; in the review inbox you read each as keep, change or remove, or record the
remark. His notes on a rough cut are direction, not rulings: import them with `--notes`, which marks the
moments he asked for. Feedback on WhatsApp goes in with `/client-said --about`; a remark about you or how
to work ("do whatever you think is appropriate") is `--about channel`.

**Acceptance.** When Joel accepts the whole video, `/accept-video <version> <where it came from>` writes
an implicit acceptance for every moment he did not comment on, with the delivered render's SHA-256.
Silence counts only then, and never as an explicit ruling. Don't ask him to rule on individual
animations unless he offers. Running it again for the same version writes nothing new.

**Calibration.** `aem calibrate joel` (or `/aem calibrate`) reports what his rulings say, read-only:
per video, how many moments he changed, kept or accepted, split asked against added, by treatment and
by job; how often the critic agreed with him (an explicit ruling weighs 1, an implicit acceptance 0.25);
per rule ID, how many rulings involve it, confirm it in his words or overrule the critic. A rule the
rulings support or contradict is printed as a proposed `rules.md` line with the `joel-decisions.md`
entry it rests on; AEM never edits `rules.md`. Under 30 explicit cases every figure says "development
data, not evidence"; with no rulings it says so and stops.

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
