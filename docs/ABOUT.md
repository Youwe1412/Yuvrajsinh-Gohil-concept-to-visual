# About Aavkar Educational Motion Studio

> **AEM observes and records. It never blocks work in a session the operator is sitting in. The record
> is the product: Joel's rulings in his words, approvals tied to the exact render, the critic's
> labelled cases, time per stage. The only interruption is a confirmation before delivering a render
> that has no current approval.**

The whole picture in one document: why Aavkar Educational Motion Studio (AEM) exists, what each part
does, how the studio should use it, what it deliberately does not do, and where it stands. The other
docs go deeper: [INSTALL.md](INSTALL.md) (setup), [OPERATOR.md](OPERATOR.md) (daily use, one page),
[CLI.md](CLI.md) (every command, format and limit).

Written 6 October 2026 and rewritten the same day for 1.0.0, when AEM stopped being a gatekeeper and
became a notary (§12 says what changed and why). Extended 7 October 2026 for 1.1.0, which makes the
record work for the agent: the moment as the unit of work, evidence Claude can see, and a loop that
learns from how the client actually reviews (§13).

---

## 1. Why AEM exists

Aavkar Productions makes educational animation for clients; the first is Joel Belton's
MergeToMaster YouTube channel. The craft lives in the client's **design system** (Joel's: Brand,
Motion and Edit Systems, `rules.md`, `joel-decisions.md`) and in a **studio skill**
(`mergetomaster-studio`) that tells an AI agent how to plan, build, critique, place and deliver
animations through seven gates (G1 Inputs … G7 Joel's review).

The skill asks for records an agent cannot be trusted to keep about its own work, and that a person
forgets to keep while working: what the client ruled, in their words; which exact render was approved;
how the critic's verdicts compared with the client's; how long each stage took. AEM keeps them. It is a
**notary**: it stands beside the work, records what happened and who decided it, measures time, checks
every render, and never stands in the way. It has three jobs, in this order:

1. **Remember.** The record: `joel-decisions.md` (Joel's rulings, verbatim, each entry saying who typed
   it), `approvals.jsonl` (approvals and rejections tied to a render's SHA-256, each saying how it was
   made), `critic/labelled-cases.jsonl` (the critic's golden set) and `events.jsonl` (stages, sessions,
   every tool call, every render check). Only `aem` writes them, append-only; a hand edit is flagged
   (`aem integrity`) until the operator accepts it. Each new session starts with `aem recall`: Joel's
   standing preferences, his last five rulings, the open questions for him and the labelled-case count.
2. **Measure.** Time per gate and scene: stages, waits, pauses, idle, agent turns, long tool calls, and
   a stage AEM infers itself when none was opened, so a forgotten `/stage` loses no time
   (`reports/time.md`).
3. **Check.** Every render, as soon as its command finishes (size, frame rate, frame count, alpha, and a
   scan of every frame for one- and two-frame flashes), the ledgers' integrity, drift between the design
   system's masters and what the agent reads, and AEM's own install (`aem doctor`).

It interrupts at exactly one point, delivery, and even there it asks rather than refuses.

Since 1.1.0 the record also helps the agent do its best work for each client: every placement is a
**moment** that knows what it teaches, whether the client asked for it, and what happened to it; every
render comes with **evidence** the agent can look at (poses, phone crops, a strip, sync in frames); and
the client's **rulings**, at the level they were given, come back at the start of the next video
(§13). The principle does not change: AEM observes and records, never blocks; the evidence and the
calibration are advisory.

**AEM does not stop an agent that wants to misbehave; it makes the misbehaviour visible in the
record.** Every tool call the agent makes is in `events.jsonl` with the files it named; a ledger line
written outside `aem` stays flagged until the operator accepts it; the only commands an agent cannot run
are the ones that write the record, and the CLI refuses them however they are spelled. §9 lists exactly
what each part misses.

---

## 2. The shape of it

```
                          registry/clients.json  (everything client-specific)
                                     │
   ┌─────────────────────────────────┼──────────────────────────────────┐
   │                        aem  (Python CLI)                           │
   │  record · recall · ledger · approvals · render check · observe     │
   │  sentinel · integrity · drift · doctor · review import · inbox     │
   │  moments · evidence · rulings · accept-video · calibrate (1.1.0)   │
   └───────▲──────────────────────────▲─────────────────────▲──────────┘
           │ process calls            │ hook command        │ typed
           │                          │                     │
   Claude Code plugin           OpenAI Codex hooks       Operator's terminal
   (aavkar-educational-         (aem codex-hook)         (aem stage, approve, …)
    motion-studio)
           │
   status line · toasts · slash commands · recall at start · delivery dialog · /inbox pane
```

Three rules shaped every decision:

1. **All logic lives in the CLI.** The plugin and the Codex hooks only translate events into `aem`
   calls and show the answers. `aem observe`, `aem rendered`, `aem context` and the rest give the
   same answer whoever asks, and every decision can be reproduced in a terminal with `--json`.
2. **Nothing client-specific is in code.** Names, folders, gates, approval and delivery patterns,
   render scripts, review settings and idle time come from the registry. A second client is a registry
   entry, not a code change.
3. **Extend the skill's formats, never fork them.** The skill's `events.jsonl` and
   `approvals.jsonl` lines are kept field for field; AEM only adds fields. The labelled-cases
   header line decides AEM's field names (Joel's file says `joel_words`, so AEM writes
   `joel_words`).

---

## 3. The parts

### 3.1 The `aem` command (`cli/`)

Python 3 standard library only, plus `ffprobe`/`ffmpeg`. About 7,100 lines (CLI) and 1,150 (plugin).
Installed by `cli/install.sh` as a link at `~/.local/bin/aem`. Every command takes `--json`.

| Module | Holds |
|---|---|
| `registry.py` | Reads the registry; resolves the project for every call (`AEM_PROJECT`, the plugin's session pin, the working folder); refuses temporary or out-of-registry folders; the last-used hint |
| `operator.py` | The check at the entry of the commands that write the record: the operator's terminal (no agent markers) or the plugin's one-time nonce |
| `observe.py` | `observe`: one tool call recorded with the files it names; stage inference; whether it delivers media with no current approval, and the question to ask |
| `recall.py` | `recall`: how the client reviews, direction of the last video and this one, what they changed last time, their channel-level rulings, preferences, last five rulings, open questions and labelled-case count, on one screen |
| `moments.py` | `moments`: the moments index (`moments/index.json`): words, job, asked or added, contract, treatment, renders, approval, critic, ruling, time |
| `evidence.py` | `evidence`: poses, phone crops, a strip, sync and facts for one render, in `evidence.md`; `--video` contact sheets of the cut |
| `rulings.py` | the client's rulings at their level: `client-said --about`, `accept-video` |
| `calibrate.py` | `calibrate`: acceptance per video, critic agreement, rules and candidate status changes |
| `integrity.py` | `integrity`, `accept-edit`: the manifest of every ledger line AEM wrote, what differs from it, and the agent's observed calls that wrote it |
| `fps.py` | Frame rates as exact rationals (24000/1001, never 23.976); discovery from `aem.project.json`, FCPXML, `data/words.json`, `frame.md`; refuses conflicts; timecode incl. drop-frame |
| `ledger.py` | `events.jsonl`: stages (and inferred ones), waits, pauses, automatic events, the time report |
| `approvals.py` | `approvals.jsonl`: approve, reject, stale marks, the approval check; item kinds (render, still, plan row) |
| `render.py` | `check-render`: probe against spec, frame count against the composition's duration, and the one/two-frame flash scan |
| `sentinel.py` | `rendered`: is a finished command a render, which files did it write, check each |
| `context.py` | `context`: the text the agent is given each session |
| `review.py` | `import-review`: Frame.io CSV → frames, moments, word IDs, drafts (`--notes`: the client's rough-cut notes, which mark moments asked) |
| `inbox.py` | `inbox`: what waits on the operator; labelled cases from rulings |
| `clients.py` | `client-said`, `new-client` |
| `drift.py` | text exports vs HTML pages, installed skill vs master, rule IDs vs `rules.md` |
| `doctor.py` | `doctor`: Python, ffmpeg, registry and drives, the resolved project, plugin version, nonce folder, integrity, drift |
| `codex.py` | `codex-hook` and `codex-config` |
| `cli.py` | argument parsing, text and JSON output |

The commands, grouped by who runs them:

| Who | Commands |
|---|---|
| **Operator only**: the commands that write the record, refused to anyone else whatever the spelling | `approve`, `reject`, `client-said`, `stage` (including the plugin's automatic `stage auto`), `accept-edit`, `accept-video`, `new-client`, `inbox accept`, `inbox dismiss` |
| **The plugin and Codex run them** (open: they only record and check) | `observe`, `rendered`, `codex-hook` |
| **Anyone** | `use`, `status`, `recall`, `context`, `report`, `moments`, `evidence`, `calibrate`, `check-render`, `check-approval`, `import-review` (writes drafts only), `inbox` (list), `drift`, `integrity`, `doctor`, `codex-config` |

### 3.2 The registry (`registry/`)

`clients.json` has `operator` (`{id: "yuvraj", name: "Yuvraj"}`) and `clients`. Joel's entry, field by
field:

| Field | Joel's value | Used by |
|---|---|---|
| `design_system`, `projects_root`, `projects` | the `00 - MergeToMaster Design System` folder; the Joel folder; `P1` → its HyperFrames project, `P2` → `P2 - Claude Code` | everything |
| `decisions_file`, `decisions_order`, `decision_scopes` | `joel-decisions.md`, newest first, channel/video/instance | `client-said`, `recall` |
| `rules_file`, `preference_prefix`, `rule_id_pattern` | `rules.md`, `J`, rule-ID regex | `recall` (Joel's J- preferences), drift |
| `labelled_cases_file` | `critic/labelled-cases.jsonl` | `recall`, inbox, review drafts |
| `text_dirs`, `skill`, `skill_master` | `text`, `mergetomaster-studio`, `Skill/mergetomaster-studio` | drift |
| `gates` | G1 Inputs … G7 Joel's review | stages, approvals, status, the delivery gate (G6) |
| `waiting_on_client_ids` | `joel` | time report (waiting on client) |
| `approval_gates` | patterns `fcpxml`, `placement`, `place`, `deliver(y)`, `Animations Done`; `.fcpxml` writes; media `.mp4 .mov .m4v .mxf` | the delivery confirmation; the sentinel's media |
| `render_sentinel` | `bin/r.sh`, `bin/ra.sh`, `bin/renderall.sh`; output `renders/` | sentinel, stage inference |
| `review_inbox` | Frame.io CSV; plan files `shotlist.md`, `visual-plan.md`; stills `stills/`; gates G2/G3/G4 | import-review, inbox, stage inference |
| `idle_minutes` | 10 | idle detection |
| `review_profile` | reviews the whole video; approval and notes on Frame.io; other feedback on WhatsApp; never sees the process; a note covers a moment within 1 s of its words; direction P2 "none" (§13.1) | moments, import-review, recall, calibrate |
| `moments` | plan files `visual-plan.md`, shot list `shotlist.md`, placements `data/edit.json`, `renders/*/PLACEMENTS.csv` | moments |
| `stage_groups` | design G1–G3, build G4, review G5 and G7, placement G6 | the time report |
| `evidence` | the rule IDs evidence speaks to (sync M-03, phone B-T1-03, flash B-T1-01 M-T1-01 M-26, motion M-T1-03, contract M-18, critic M-19); 6 renders per command at most | evidence |
| `audio` | sound policy from Joel's rules: libraries Epidemic Sound and Envato Elements first (M-25, E-09), cue kinds (J-05), music (J-03, E-09), loudness −14 LUFS integrated, −1 dBTP, dialogue −16 to −14 LUFS short-term, music 18–22 dB under (E-08), `generated_sfx: allowed` (Yuvraj's decision, 19 Oct 2026; Joel's open question still unanswered), `llm_upload: false` | the client skill's Listening step with earshot; not read by `aem` |

Joel's entry still carries `protected_files`, `blocked_commands` and `shared_paths`
from the guard (`audio_libraries` moved into `audio.libraries`); nothing reads them since 1.0.0 (left in place so the registry did not change; delete
them when convenient). `client-template/` is what `aem new-client` copies into an empty design-system
folder: decisions file (with an "Open questions" section for `recall`), rules file,
`critic/labelled-cases.jsonl` with its header, `text/`, a README and a registry entry template.

### 3.3 The Claude Code plugin (`plugin/aavkar-educational-motion-studio/`, 1.1.0)

One plugin of function hooks. The engine allows one hook per event per module and follows `$`
only within one file, so `hooks/register.tsx` owns every `on(...)`, builds an `io` object of
closures over `$`, and passes it to six feature files that never see `$`:

| Feature | File | What it does |
|---|---|---|
| Context | `context.ts` | On session start and every 30 s: `aem status` + `aem context` → the status line and a prompt section (the principle, the project, three rules for the agent, the client's recall). At session start a toast (`AEM 1.1.0 · joel/P2 · resolved from folder`, or `… no project (folder not registered)`), the recall in the transcript for the operator, and drift toasts. The status line ends with the moments index's counts (`58 moments · 0 approved · 58 ruled`). `/aem use` (checks with the CLI, then pins the project to this session), `/aem use --clear`, `/aem status`, `/aem moments`, `/aem recall`, `/aem calibrate`, `/aem new-client`. |
| Ledger | `ledger.ts` | Automatic events: session start/end, your prompts (with origin), turn start/end, tool calls ≥ 30 s, idle start/end (no prompt and no turn for `idle_minutes`, measured from the last activity). `/stage`, `/pause`, `/resume`, `/wait`, `/report`. |
| Observe | `observe.ts` | Before every `Bash`, `Read`, `Write`, `Edit`, `MultiEdit`, `NotebookEdit` call (subagents' too): `aem observe`, which records it. Never refuses, with one exception: a delivery of media with no current approval opens the engine's dialog, "fd_S01 was re-rendered after you approved it. Deliver anyway?", Deliver (records the approval through the confirmation, then runs) or Stop (refuses the call). Where no dialog can be shown, the call is refused once with the `/approve` command to type, and the identical call repeated goes through. Toasts a stage AEM inferred. |
| Record | `record.ts` | `/approve`, `/reject`, `/client-said` (with `--about` and `--ruling`), `/accept-video`, `/accept-edit`: the slash commands that write the record, each with a one-time nonce. |
| Render sentinel | `sentinel.ts` | After every `Bash` call: `aem rendered`. For a render, a pass/fail toast with the first reason, the full result added after the command's output for the agent (with the path of each render's `evidence.md`), an `evidence ready: …` toast, and the status line redrawn (stale count). |
| Review inbox | `inbox.tsx` | Only with the `reviewInbox` setting on: `/inbox` opens a pane listing what waits on you; buttons run the commands each item names; Reject asks for a reason. |

Settings: `aemPath` (default `aem`, falls back to `~/.local/bin/aem`) and `reviewInbox` (off). Slash
commands answer only to the operator: prompts from the composer, the bridge or the SDK; a plugin, a peer
agent or the agent itself is refused. For each command that writes the record the plugin makes a random
one-time nonce, writes only its SHA-256 to `~/.aem/nonces/` with a 60-second expiry, and hands the nonce
to that one `aem` call, which is how the CLI knows the operator ran it (`hooks/aem.ts`,
`hooks/sha256.ts`). State it keeps (`types/index.d.ts`): `view`, `ledger`, `inbox`, `pin` (the session's
`<client>/<project>`, passed to every `aem` call as `AEM_PROJECT`) and `held` (the delivery calls held
once where no dialog could be shown). If `aem` cannot run, every call goes through, with a toast at most
once a minute.

### 3.4 Codex (`aem codex-hook`, `aem codex-config`)

Codex 0.146 has command hooks. `aem codex-config` prints a `[hooks]` table for
`~/.codex/config.toml` with the absolute path of your `aem`. The hook keeps context, ledger events and
the render sentinel, and never denies:

| Codex event | AEM |
|---|---|
| SessionStart | the context text (principle, project, recall) as `additionalContext`; `session_start` recorded (`agent: codex`) |
| UserPromptSubmit | `prompt`, `turn_start` |
| PreToolUse (`Bash`, `apply_patch`) | `observe`: the call recorded; a stage inferred when none is open; a delivery recorded with its media's approval state, not asked about |
| PostToolUse (`Bash`) | the render sentinel; long tool calls |
| Stop / SessionEnd | `turn_end` / `session_end` (and any inferred stage finished) |

No slash commands, status line, toasts, dialog or inbox in Codex: the operator types `aem …` in a
terminal. No idle detection (no timer).

### 3.5 The marketplace (`.claude-plugin/marketplace.json`)

The repository is a marketplace named `aavkar-productions` listing the one plugin. Install is two
steps: `/plugin marketplace add <owner>/<repo>` (or a local path), then
`/plugin install aavkar-educational-motion-studio@aavkar-productions`.

### 3.6 The skill

Joel's skill master (`00 - MergeToMaster Design System/Skill/mergetomaster-studio/SKILL.md`) has a
section, "When Aavkar Educational Motion Studio (AEM) is loaded", of three lines: AEM records; the agent
never writes the record files; when an approval, rejection, client quote or stage change is needed, the
agent asks Yuvraj in one sentence and continues once Yuvraj has run it. Without AEM the skill works as
before. For 1.0.0 the section's 44 lines (a records table and the 0.9.0 chat-authority rules) became
those three; the chat zip was rebuilt with `Skill/build-chat-zip.sh`, the skill installed to
`~/.claude/skills/mergetomaster-studio/`, and `aem drift` reports no drift. `SKILL.md` went from SHA-256
`ea3f7a73…` to `3fc1ff4e…`, the zip from `59987d64…` to `0af1b8de…`.

For 1.1.0 (7 October 2026): G4 and G5 now give the critic each render's `evidence.md` (never the
source) and have it write `critic.json` beside it so G7 can score it; G7 follows how Joel reviews (wait
for Frame.io; import the CSV; attach WhatsApp feedback with `client-said --about`; `accept-video` once he
accepts the whole video; never ask him to rule on individual animations unless he offers; silence is an
implicit acceptance only once the whole video is accepted), in `SKILL.md` and
`references/joel-review.md`, whose rulings table gains a Level column. `SKILL.md` is now `6adc6fe1…`, the
zip `9b87e573…`; the installed copy matches and `aem drift` reports no drift.

---

## 4. The files AEM reads and writes

| File | Where | Written by | Format |
|---|---|---|---|
| `active.json` | `~/.aem/` | `aem use` | **A last-used hint only**, `{_comment, client, project, project_dir, set_at}`: `aem status` shows it when nothing resolved; nothing else reads it. A hint pointing outside the registry's roots is renamed `active.json.stale`. |
| `nonces/<sha256>` | `~/.aem/` | the plugin | `{expires_at}`: the hash of a one-time operator nonce; deleted when used or expired. |
| `events.jsonl` | project | AEM only | skill's `{ts, gate, scene, event, note}` + `source`, `session`, `turn`, `tool`, `command`, `reads`, `writes`, `paths`, `delivery`, `duration_s`, `render`, `render_sha256`, `result`, `via`, `inferred`, `inferred_from`, `agent`, `backfilled`… |
| `approvals.jsonl` | project | `approve`, `reject`, `check-render` (stale marks) | skill's `{gate, scene, render, render_sha256, source_revision, approver, date}` + `type` (approval / rejection / stale), `ts`, `via` (terminal / slash command / delivery confirmation), `render_check`, `item_kind`, plan-row fields |
| `.aem-integrity/<ledger>.jsonl` | beside each ledger | AEM only | the hash of every line AEM wrote, for `aem integrity` |
| `reports/time.md` | project | `report` | per gate, per scene, per gate-and-scene, inferred stages, with how each number was computed |
| `aem.project.json` | project (optional) | you | `fps`, `render` (width, height, alpha), `scenes`, `flash.min_area_pct`, `placements`, `render_sentinel`, `review_inbox`, `stage_inference` |
| `reviews/<client>/<date>-*` | project | `import-review` | CSV copy, review JSON, draft rulings, draft labelled cases; with `--notes`, `<date>-notes.csv` and `.json` |
| `moments/index.json` | project | `moments` (and `import-review`, `client-said --about`, `accept-video`, which rebuild it) | the moments and what could not be linked (CLI.md, Moments) |
| `reviews/<moment>/<version>/` | project | `evidence` (the sentinel after a render) | `poses/`, `phone/`, `strip.jpg`, `sync.json`, `facts.json`, `evidence.md`; the critic adds `critic.json` |
| `reviews/video/<cut>/` | project | `evidence --video` | one contact sheet per moment, `video.md` |
| decisions file | design system | `client-said` only | dated, verbatim, scoped entry, "typed by <operator> with /client-said in Claude Code" or "in a terminal" |
| `critic/labelled-cases.jsonl` | design system | `approve`/`reject` with `--label`, `inbox accept`/`dismiss`, `client-said --about`, `accept-video` | the file's own fields + `moment`, `level` (explicit, implicit, video, channel; `operator` for ours), `asked`, `direction`, `version`, `critic_findings`, and for ours `item_kind`, `gate`, `reason`, `decision`, `inbox_ref`…; operator rulings are `development case` |
| `codex/pending/` | `~/.aem/` | `codex-hook` | start time of a running Codex Bash call |

Ledgers are append-only. A correction is a new line (a rejection, a stale mark, a correcting case),
never an edit.

---

## 5. How it should be used: a video, gate by gate

The operator is Yuvraj (or whoever runs the studio). "Agent" is Claude Code with the plugin.

**Start.** Start Claude Code in the project's folder (`P2 - Claude Code`). Check the start toast
(`AEM 1.1.0 · joel/P2 · resolved from folder`; no toast means the plugin is not loaded), the recall in
the transcript (how Joel reviews, P1's direction and P2's, what he changed on P1, his channel-level
rulings), the status line and any drift toast. `aem moments` once the plan or placements exist. Started somewhere else? `/aem use joel/P2` pins it
to that session. `aem doctor` says what is wrong with an install.

**G1 Inputs.** `/stage G1`. The agent builds the word map, footage inventory and inputs list, per
the skill. If you are waiting for Joel's footage: `/wait joel`; `/stage G1` or `/resume` when it
arrives.

**G2 Plan.** `/stage G2`. The agent writes `style-guide.md`, `shotlist.md` (and `visual-plan.md`).
Review rows in `/inbox` or just read and approve the plan in conversation.

**G3 Stills.** `/stage G3`. Stills under `stills/` appear in the inbox; approve or reject each.

**G4 Rough render.** `/stage G4 fd_S01_next-token` per scene. The agent renders (`bin/r.sh …`);
the sentinel checks every output, builds its evidence (`evidence ready: …`), and tells both of you. A flash or wrong frame count is the agent's
to fix before you look. When you are happy: `/approve fd_S01_next-token` (its last checked render,
at the open gate). `/reject fd_S01_next-token <reason>` otherwise.

**G5 Critique and repair.** The agent gives a critic subagent the render's `evidence.md` alone; the
critic writes `critic.json` beside it. The agent repairs. Any re-render makes earlier approvals stale at
once (status line: `· 1 stale`). Approve again after you have looked; `aem evidence --video <cut>` shows
each moment in the assembled cut first.

**G6 Deliver.** `/stage G6 …`. The agent checks approvals first (`aem check-approval`). If it writes a
placement FCPXML or copies a render into `Animations Done` while that render has no current approval,
you get the one question AEM asks: Deliver (recorded as approved through the confirmation) or Stop.

**G7 Joel's review.** Wait for his review on Frame.io. Export the comments as CSV; the agent (or you)
runs `aem import-review`. In `/inbox`, read each comment on a moment as Keep, Change or Remove, record
each comment on no moment as a remark about the video, or Reject a mis-mapped one. WhatsApp feedback:
`/client-said --about <moment|video|channel> --source "WhatsApp, <date>" <his words>`. When he accepts
the whole video: `/accept-video <version> Frame.io, <date>`. Moments he did not comment on stay
unruled until then. `aem calibrate joel` says what his rulings show.

**Close.** `/stage end`, `/report`. Nothing needs clearing: a project is not stored anywhere global.
Forgot a `/stage` somewhere? The report lists the stages AEM inferred and counts their time.

**When the agent needs a record written**, it asks in one sentence ("Please run `/approve fd_S01`"):
run it, or don't. **When integrity flags a ledger edit**, look at `aem integrity` and `/accept-edit` it
(OPERATOR.md).

---

## 6. Render checks in detail

`aem check-render` (and so the sentinel) checks, against `aem.project.json` and the composition:
width and height, frame rate (exact rational), constant frame rate, frame count (from the
composition's `data-duration` at the project rate, or `scenes` settings), duration (frames ÷ stream
rate, within half a frame), alpha, and decoded frame count.

The flash scan decodes every frame to a 96×54 grey grid (and the alpha plane when there is one) and
looks for a change of 20+ grey levels that returns within 6 levels after one or two frames, where
nothing within 12 cells carries on (so fast motion is not a flash). Findings under 0.1% of the
frame are listed as minor, not failed (`flash.min_area_pct`). On Joel's real P1 renders it caught
the frame-2 flash Joel reported in `fd_S04_50ms_v08` and passed the fixed render; it also reports a
2-frame dip at frames 46–47 of `fd_S04_character_v08`, left for a human to judge rather than tuned
away. It cannot see the first or last frame's flash, and an object teleporting more than about 12%
of the frame width in one frame is reported. A failed check never blocks anything: it is information
for the agent (fix it before asking for approval) and the operator.

---

## 7. Time report in detail

From `events.jsonl`, per gate, scene, and gate-and-scene: **wall** (start to finish), **agent busy**
(turn start to end), **idle** (no prompt and no activity for `idle_minutes`, from the last
activity), **waiting on client** (`waiting_on_<id>` for the client's ids), **waiting on others**,
**paused**, **attended between turns** (an operator present between turns), and **unobserved**
(gaps with no events, such as Codex sessions or a closed laptop). Idle is always separate, never
counted as work. Backfilled events (`--at`) are marked and counted. Stages AEM inferred (no stage was
open when a plan file, still, scene source or render changed) are counted like any other and listed
with the file that started each; each ran until the next `/stage` or the session's end. It is for
planning, not billing.

---

## 8. Testing and verification

| What | Result at 1.0.0 (1.1.0: §11) |
|---|---|
| CLI unit tests (`tests/run.sh`, which wraps `python3 -m unittest discover -s tests -t tests`) | see §11 for the run's numbers. Kept: ledger, sentinel, integrity, operator-only refusal, isolation, resolution from the folder. New: `test_observe.py` (every call AEM denied in the P2 session of 6 October now runs with no interruption and is recorded; the delivery confirmation; stage inference), `test_integrity.py`, `test_recall.py`, `doctor`. Deleted: the guard's and the chat authority's tests (`test_guard.py`, `test_authority.py`). |
| Plugin tests (`claude plugin test`, Claude Code 2.1.288) | see §11. New: `observe.test.ts` (the P2 calls run with no dialog; an unapproved delivery asks, an approved one does not; Deliver, Stop, dismiss, the no-dialog fallback), `record.test.ts`. Deleted: `guard.test.ts`, `authority.test.ts`. The `claude` on PATH (2.1.283) cannot load the plugin; `tests/run.sh` uses the desktop app's newest bundled build |
| Isolation | the run fails if `~/.aem` or `registry/clients.json` changed |
| `claude plugin validate` (plugin and marketplace) | pass |
| `tsc` strict | **not run**: no TypeScript compiler is installed here |
| Flash scan on 59 real P1 masters and the client-fix renders | Joel's flash caught, fix passes (run at `275e0bc`, not repeated) |
| `aem drift` on Joel's real design system | no drift after the skill change (§3.6) |
| `aem recall joel` and `aem doctor` on the real design system and P2 | read-only; recall lists J-01…J-08, four rulings, four open questions, 3 development cases |
| Codex 0.146 live (`tests/live/codex-hooks-check.sh`) | at 0.8.0: SessionStart context ran; the agent's `aem approve` was refused by the CLI itself. Not re-run for 1.0.0 or 1.1.0 |
| 1.1.0, moments (`test_moments.py`, P1 fixture in `tests/fixtures/p1`) | 58 moments from P1's real placements; 50 asked, 8 added by Joel's 66 notes; the three client-fixed scenes carry explicit rulings; note #20's range resolves to its word span; no notes means all added, said at the top; time only per stage |
| 1.1.0, evidence (`test_evidence.py`, P1's real renders from the drive) | the 50 ms flash in the strip and `facts.json` before the fix and not after; `audience-questions` reveals within a frame of P1's hand-measured onsets; `evidence.md` parses and every image it names exists; 4K cost |
| 1.1.0, learning loop (`test_learn.py`) | the 66 comments map to the right moments; 3 explicit changes; `accept-video` writes 55 implicit; calibrate's figures, both candidate rules and the 30-case message; no rulings stops; operator rulings left out; the channel quote stored (linked to its entry) and recalled first |

Real client files were only read, except the skill change in §3.6. Everything else was tested on
copies in temporary folders.

---

## 9. Limits, exactly

AEM does not stop an agent that wants to misbehave; it makes the misbehaviour visible in the record.
What each part misses:

| Part | Misses | Over-matches |
|---|---|---|
| Observation (`aem observe`) | MCP tools; a path built at run time (recorded as written, `$F`); files a script writes without naming them; calls made outside Claude Code and Codex (your shell, other editors) | a name with an extension is recorded as a path even when it is not one (`json.tool`) |
| Delivery confirmation | a placement tool that reads its renders from a manifest the command does not name; a delivery folder no pattern matches; Codex (records, never asks); a script file is not known to only read, so it is judged by what it names | a non-read command that names media and matches a placement pattern (`place`, `deliver`) asks even if it delivers nothing |
| Operator-only commands | an agent that strips the agent markers and allocates a terminal, or writes a nonce hash file with a shell command, passes: the record shows the command it ran (observed) and how each record was made (`via`) | — |
| Ledger integrity | a ledger and its manifest rewritten consistently; a line identical to one AEM wrote; lines already there before AEM's first write (the baseline) | — |
| Stage inference | work that changes no plan file, still, scene source or render; work while any stage is open (it stays in that stage) | a stray write to `shotlist.md` opens G2 when nothing else was open |
| Render sentinel | background renders (P2's `bin/r_queue.py --detach`: run `aem check-render` on each); unlisted render scripts; renders written outside `renders/` and not named | other media changing under `renders/` during the command is checked too; a script name inside a quoted string or a `-c` argument (read-only programs and here-document bodies are skipped since 23 Oct 2026) |
| Recall | rulings not written as `## ` entries; quotes not in `>` lines or quotation marks; long quotes are cut with an ellipsis (the agent reads the file for the rest); a video's direction until its moments index is built | — |
| Moments | plan tables that are not Markdown tables; a moment's words when `data/words.json` drifts | "asked" is by time: a moment we added over footage the client asked for at that time counts as asked |
| Evidence | a scene that never holds still for a quarter second (first and last frame only); which element moved (it measures the whole picture); cue words nobody wrote down (guessed from motion, and labelled so) | the strip sits on the largest change, which may be a cut |
| Calibrate | critic agreement where the critic wrote no `critic.json`; rules nobody linked to a ruling by ID | one video's rulings read as a pattern: under 30 explicit cases every figure says it is development data |
| Inbox | not live (refreshed on open and after each button); plan tables must be Markdown tables | an identical file under another name counts as already ruled |
| Everything | anything when `aem` cannot run: every call goes through and the plugin says so (a toast at most once a minute) | — |

What the Claude Code API could not do, and the nearest thing built instead:

- One module may hook each event once, and `$` cannot cross an import: one dispatcher module with an
  `io` object of closures.
- `$.state` keys must be string literals: atoms declared in `register.tsx` only.
- A tool's result can carry extra text for the model only when the tool succeeded: on a failed Bash
  call the sentinel can toast but not add a note.
- A dialog needs a surface to draw on: in a plain `-p` run there is none, so the delivery confirmation
  holds the call once and tells the agent the `/approve` command to ask for.
- The mobile app draws no text field, although its element table lists `Input`: the inbox checks
  the surface and sends Reject to `/reject` there.

---

## 10. Design decisions worth knowing

- **Detection, not prevention.** AEM never denies a tool call except the operator's own Stop at the
  delivery confirmation. A hand edit of a ledger is allowed and flagged; an agent running an operator
  command is refused by the CLI with one line, and asks.
- **The record says who and how.** Approvals and rejections carry `approver` and `via` (terminal, slash
  command, delivery confirmation); a client quote says who typed it and how; every observed call
  carries its session (and subagent).
- **Operator rulings are `development case`** in the labelled cases, with the client's words field
  empty: the skill counts only the client's explicit rulings in their own words toward the critic's 30
  (M-19). A client comment accepted in the inbox keeps Joel's words verbatim and is `labelled` only
  with a ruling, the words and the approved render's SHA-256.
- **Approvals carry `item_kind`**: rejecting a still never unseats the render's approval; the stale
  count is renders only.
- **Fail open.** If `aem` cannot run, calls go through with a toast (at most once a minute); a broken
  install should not stop a delivery day. `aem doctor` says what is wrong.
- **Inferred stages are bounded.** One lasts until the operator opens a stage or the session ends, so
  a guess never runs on for days.
- **Codex hooks at user level.** A project-level `.codex/hooks.json` did not load in `codex exec`
  testing.

---

## 11. Where things stand (7 October 2026, 1.1.0)

Done and committed: the three 1.1.0 additions (§13), one commit per phase, on top of the notary
redesign (§12).

Results of the 1.1.0 run: CLI unit tests 218 pass (187 at 1.0.0; new: `test_moments.py` 11,
`test_evidence.py` 9, `test_learn.py` 11, the P1 ones on the real fixture and, for evidence, the real
renders on the drive); plugin tests 54 pass in 7 files; `claude plugin validate` passes for the plugin
and the marketplace; the isolation check found `~/.aem` and `registry/clients.json` unchanged. Evidence
on P1's 59 real masters: 1.37 s per render (median), 2.4 s per 10 s of 4K MP4 scene, 120 s for all 59
(§13.3). The plugin 1.1.0 is installed for the user from the local marketplace; it takes effect in new
sessions.

Not done yet:

- **Joel's P2 trust statement is not yet a ruling in the labelled cases.** His words are in
  `joel-decisions.md` (the 5 October entry); `client-said --about channel` is the operator's to run, and
  it links the ruling to that entry rather than writing the words again.
- **Not pushed anywhere**: the repository has no remote, so the marketplace works from a local path.
- **Not switched on for you**: the review inbox setting is off; Codex hooks are not in your
  `~/.codex/config.toml` (run `aem codex-config` and add them when you want them).
- **The end-to-end acceptance run** (`tests/acceptance/operator.sh`) was started before 0.8.0 and has
  not been re-run.
- **Live checks not re-run for 1.1.0**: the Codex hooks check, and a live session's dialog (the
  confirmation is covered by plugin tests with the engine's own AskUserQuestion path).
- P2 is registered (`joel/P2`, `P2 - Claude Code`, 25/1 from `RoughCut.mp4`, 3840 × 2160); it has no
  plan or HyperFrames project yet, so it has no moments.

---

## 12. What 1.0.0 changed, and why (6 October 2026)

**AEM had been acting as a gatekeeper, and it cost a working day.** In the P2 session the guard denied,
among others, a read of the rough cut's FCPXML (`unzip -p … Info.fcpxml`, AEM-G05: "names no render"),
the shared `~/Tools/fcp-edit-workflow` (AEM-G02, read as `fcp-edit-workflow;` with the semicolon), a
`cat` of the registry (AEM-G01), and a tool result in Claude Code's own folder (AEM-G02); 0.9.0 then added
an "authority from chat" so the operator could get past the guard by asking, with nonces, turn records
and `/allow` overrides to manage. Each fix solved a problem the guard itself created. 1.0.0 removes the
guard and keeps what was always the point: the record.

| Removed | Replaced by |
|---|---|
| AEM-G01 protected file, G02 outside the client's folders, G03 blocked command (and G04, removed in 0.8.0) | nothing: the agent may read and write anywhere. Every call is observed and recorded (`observe`); a ledger edit is flagged (`integrity`) |
| AEM-G05 render not approved, as a denial | the delivery confirmation: a question with Deliver and Stop; no other rule may deny |
| `aem guard`, the text-matching guard code, guard modes | `aem observe` (records; never refuses) |
| Turn authority from chat (`aem authority`, `AEM_OPERATOR_TURN`, its nonces, `operator_prompt`/`operator_turn` events, `client-said`'s quote-in-prompt rule) | the operator runs the commands that write the record (slash command or terminal); the agent asks in one sentence |
| `/allow`, `aem allow`, the allow ledger events, the inbox's guard-denial items | nothing to override |
| `allowed_by_operator_prompt` events | `observed` events; integrity names the observed call that wrote a file |
| `use` as an operator-only command | `use` is open (it only writes a last-used hint) |
| the context dump (every preference, protected file and rule for the agent) | the principle, the project, three rules, and `aem recall` |

Added: `aem recall` (shown at session start), stage inference (`stage_inferred`, flagged), `via` on
records, `aem doctor`, `--delivery-confirmation` on `approve`, and the delivery outcome events.

History, briefly: 0.7.0 built the guard; 0.8.0 removed the global "active project" (the project comes
from the folder) and made the CLI refuse operator commands itself; 0.9.0 let the operator's chat message
stand for its turn and added ledger integrity; 1.0.0 made AEM a notary. The skill's `events.jsonl`,
`approvals.jsonl` and labelled-cases formats are unchanged throughout: fields were only added.

---

## 13. What 1.1.0 added (7 October 2026)

1.0.0 made AEM a notary. 1.1.0 makes what it records useful to the agent doing the work, in three
additions, each built on the one before: the moment as the unit of work, evidence Claude can see, and a
loop that learns from how the client actually reviews. The ground rules held: all logic in the CLI, the
plugin only translates and shows; everything client-specific in the registry; the skill's formats
extended, never forked; records append-only and integrity-checked; nothing slows the agent (evidence runs
after a render; findings are advisory).

### 13.1 How Joel reviews: the review profile

Joel reviews the finished video. He never reviews individual animations and never sees the process.
His approval, feedback and any timestamped instructions arrive on Frame.io; some feedback arrives on
WhatsApp. He doesn't always give instructions: P1 had 66 timestamped Frame.io notes; for P2 he gave
none, and said why ("I really liked what you did with the other video so id like to try you mostly
just adding in visuals that you feel like are appropriate at the time rather than me commenting what
should go where", WhatsApp, 5 October 2026). The absence of notes is his decision, a channel-level
ruling in his words, and his level of direction per video is data.

So a ruling has a level: a comment on one moment (**explicit**), the video accepted with no comment on
it (**implicit**), a remark about the video (**video**) or about the editor and how to work (**channel**).
The registry's `review_profile` holds this for each client (Joel: unit "whole video", approval and notes
on Frame.io, other feedback on WhatsApp, `sees_process: false`, a note covers a moment within 1 s of its
words, as G7 says, and P2's direction "none"); `aem recall` opens with it.

### 13.2 The moment is the unit of work (Phase 1)

A moment is one thing placed in the cut, with its word IDs, teaching job, whether the client asked for
it or we added it, its contract from the shot list (what the viewer knows before and after, what must
stay true, where the picture stops being accurate), treatment (animation, footage, screen recording,
nothing), scene and source, render versions, approvals, critic findings, the client's ruling at its
level, and the time spent on it. `aem moments` derives all of it from the files the skill already
writes (the plan and shot list, the placements, `data/words.json`, the renders, `approvals.jsonl`,
`events.jsonl`, the labelled cases) into `moments/index.json`, and lists what it could not link. Asked or
added is note coverage: a moment is asked when one of the client's notes lies within a second of its
words; with no notes, every moment is added and the index says so at the top. `aem report` adds time per
moment and per stage group (design, build, review, placement); the status line shows
`N moments · M approved · K ruled`.

On P1: 58 moments (the other 8 placements are Joel's footage), 66 notes covering **50 asked and 8
added** (`fd_title-t08_okay`, `fd_S02_tells-b`, `fd_S05_board-a`, `fd_S05_audience-questions`,
`fd_teach-gaps`, `fd_S05_parallel-1`, `fd_S05_board-e`, `fd_S05_parallel-3`); nine notes (#4, #8, #23,
#29, #32, #33, #62, #69, #70) cover no moment of ours. The brief expected 45 and 13: the gap is the
`teach-*` and `reference-*` inserts of the v07 opportunity pass, which we added but which sit where
Joel's notes asked for footage, so by time they count as asked. A plan's "asked or added" column
overrides coverage when a project has one.

**It does not:** decide what a moment should be, edit the plan or the placements, guess a moment's
words beyond `data/words.json`, or spread time that names no moment across moments (it is reported as
unattributed).

### 13.3 Evidence Claude can see (Phase 2)

After every render, `aem evidence` writes `reviews/<moment>/<version>/`: a PNG of each readable pose (the
frame the picture settles on after each cue word, plus the first and last frame) 1920 px wide, the same
at 390 px (a phone held upright), an 8-frame JPEG strip around the fastest transition, `sync.json` (each
cue word against the frame the picture settles, in frames), `facts.json` (the render check), and
`evidence.md`, which names every image by relative path with the moment's contract and the rule IDs and
is all a critic subagent needs. `--video` makes a contact sheet per moment from the assembled cut. The
plugin adds the `evidence.md` path to the render's tool result and toasts `evidence ready: fd_S04_50ms
v09, sync max offset 2f, no flash`.

On P1's real renders: the one-frame flash Joel had removed shows in the strip and in `facts.json` of
the render he ruled on (frame 2, the whole frame) and not in the fix; the reveals of
`audience-questions` land within a frame of the onsets measured by hand in P1's `OUTSTANDING.md`.
Measured cost on all 59 v08 masters (423.6 s of 4K): 120 s in all, 1.37 s per render (median, 9.9 s the
most), 2.4 s per 10 s of MP4 scene (median; at most 5.1 s), 11.9–15.4 s per 10 s for the four ProRes
alpha MOVs; under the 30 s budget throughout. The 11-minute P1 film: 58 contact sheets in 8.2 s.

**It does not:** judge anything (it shows; the critic and the operator judge), block or delay a delivery
(it runs after the render, and a failure to build it is a note, not an error), read the scene source, or
claim a sync offset it did not measure (without cue words the toast says "sync not measured", and cue
words inferred from motion are labelled as guesses).

### 13.4 A loop that learns from how the client reviews (Phase 3)

`aem import-review` maps each Frame.io comment to the moments it is on, by the same rule as note
coverage: an explicit ruling candidate, read as keep, change or remove in the inbox; a comment on no
moment is a video-level remark. On P1 all 66 map: 57 to moments (exactly the 50 asked ones), 9 to the
video; every comment a HyperFrames build answered (P1's `FRAMEIO-COMMENTS-MAP.md`) is on that build,
except #4, whose build starts 3.1 s after the note, over Joel's still. `client-said --about
<moment|video|channel>` records the client's words as a ruling at that level ("do whatever you think is
appropriate" is channel-level); words the decisions file already has are not written again. `aem
accept-video <version> --source "Frame.io, <date>"` (the operator's) writes an implicit acceptance,
with the delivered render's SHA-256, for each moment with no explicit comment: on P1, 55. Silence is
never written as explicit. Each labelled case carries the moment, level, ruling (keep, change, remove,
accepted), the client's words, render hash, critic findings, rule IDs, asked or added and the video's
direction, in the file's own field names.

`aem calibrate joel` reports acceptance per video (asked against added, by treatment and job), the
critic's agreement (hits, misses, false alarms; explicit rulings weigh 1, implicit 0.25), and per rule
ID whether it was involved, confirmed, overruled or untested; a rule the rulings support or contradict
appears as a proposed `rules.md` line with the `joel-decisions.md` entry it rests on. On P1:
`0 of 8 additions changed, 3 of 50 asked`, the opposite of the brief's expectation: Joel's three changes
(`fd_S04_50ms`, `fd_S04_button-states`, `fd_S04_character`) are on moments he asked for, and each
took out something inside them he had not asked for (a one-frame website flash, two demonstration
captions). M-26 and
B-29 come out "suggested by rulings, unconfirmed"; with 3 explicit cases, everything is "development
data, not evidence". `aem recall` now opens with how Joel reviews, the direction of the last video and
this one, what he changed last time by treatment and job, and his channel-level rulings, newest first.

**It does not:** edit `rules.md` or change a rule's status (it prints the proposed line), treat silence
as a ruling before the whole video is accepted, ask the client to rule on individual animations, count
the operator's own rulings as the client's, score the critic where it wrote no `critic.json` (P1 has
none, so critic agreement is "untested"), or call three cases a pattern.

### 13.5 What only becomes meaningful after Joel reviews P2

P2 has no notes by Joel's choice, so every moment will be "added" and P2's direction is "none".
Everything that compares rulings with what we did needs his review of the finished P2 on Frame.io:
whether "added" moments fare differently from P1's asked ones when he did not direct them; the first
critic agreement figures (the skill now has the critic write `critic.json`; P1 has none); whether M-26
and B-29 hold on a second video; the first rulings on treatments other than animation, if P2's plan
uses footage or screen recordings; and the first change or keep in his own words, since none of P1's
three changes has them. Until then calibrate reports development data.

### 13.6 What Joel's review of P2 showed (23 October 2026)

P2 was delivered on 15 October 2026 (`Done/P2 - Claude Code Done.mov`, SHA-256 `7029f231…058da`) with
45 moments, every one *added*. Joel left **no Frame.io comments at all**; his verdict came on WhatsApp:
"Hi, the intro is absolutely awesome 👌", "I love it", "You've done an amazing job here" (17 October) and
"Hi, no I think its all ready to go :) happy for you to send me the invoice" (19 October). No changes,
against P1's three. P2's hypothesis (`docs/P2-HYPOTHESIS.md`) held, as development data: one video.

What it changed in AEM and around it:

- **Acceptance across versions.** P2's moments went out at v01 to v06, so `accept-video <version>` could
  not record it; `accept-video latest [--before <delivered master>]` takes each moment's newest render.
- **The record was thin, and why.** The operator approved in conversation ("Render", "execute"), not with
  `/approve` (run once, through the delivery dialog) or `/stage` (never; AEM inferred G2 and G4), and the
  agent never ran `aem chose`; no render got a `critic.json`, so calibrate has no critic agreement for P2.
  The skill (v3) now hands the operator paste-ready `/approve` lines at the end of a batch instead of
  stopping, and has the agent run `aem chose` and write `critic.json` when asked whether the work is the
  best it can be.
- **Sentinel noise.** Reading a render script (`head bin/r.sh`) or a here-document that named it set the
  sentinel off; it now skips read-only programs and here-document bodies. Detached batch renders
  (`bin/r_queue.py --detach`) are still invisible to it.
- **House craft.** The operator's rulings on P2 that apply to any client are in the craft baseline as
  A-27…A-34 (live preview before render, joins frame to frame, words over footage with no field, real UI
  redrawn, untagged frame grabs, hooks that promise, music only where it does a job, sound from the
  picture), and A-11, A-20, A-22, A-24 gained P2's specifics. The Joel-specific ones are in the
  `mergetomaster-studio` skill v3 (`references/operator-direction.md`).
- **Still the operator's to run:** `/client-said` for his two messages, then `/accept-video latest`,
  `aem calibrate` and `aem report` (the commands are in P2's `reviews/joel/2026-10-19-whatsapp.md`).

