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
became a notary (§12 says what changed and why).

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

Python 3 standard library only, plus `ffprobe`/`ffmpeg`. About 5,100 lines (CLI) and 1,100 (plugin).
Installed by `cli/install.sh` as a link at `~/.local/bin/aem`. Every command takes `--json`.

| Module | Holds |
|---|---|
| `registry.py` | Reads the registry; resolves the project for every call (`AEM_PROJECT`, the plugin's session pin, the working folder); refuses temporary or out-of-registry folders; the last-used hint |
| `operator.py` | The check at the entry of the commands that write the record: the operator's terminal (no agent markers) or the plugin's one-time nonce |
| `observe.py` | `observe`: one tool call recorded with the files it names; stage inference; whether it delivers media with no current approval, and the question to ask |
| `recall.py` | `recall`: a client's preferences, last five rulings, open questions and labelled-case count, on one screen |
| `integrity.py` | `integrity`, `accept-edit`: the manifest of every ledger line AEM wrote, what differs from it, and the agent's observed calls that wrote it |
| `fps.py` | Frame rates as exact rationals (24000/1001, never 23.976); discovery from `aem.project.json`, FCPXML, `data/words.json`, `frame.md`; refuses conflicts; timecode incl. drop-frame |
| `ledger.py` | `events.jsonl`: stages (and inferred ones), waits, pauses, automatic events, the time report |
| `approvals.py` | `approvals.jsonl`: approve, reject, stale marks, the approval check; item kinds (render, still, plan row) |
| `render.py` | `check-render`: probe against spec, frame count against the composition's duration, and the one/two-frame flash scan |
| `sentinel.py` | `rendered`: is a finished command a render, which files did it write, check each |
| `context.py` | `context`: the text the agent is given each session |
| `review.py` | `import-review`: Frame.io CSV → frames, shots, word IDs, drafts |
| `inbox.py` | `inbox`: what waits on the operator; labelled cases from rulings |
| `clients.py` | `client-said`, `new-client` |
| `drift.py` | text exports vs HTML pages, installed skill vs master, rule IDs vs `rules.md` |
| `doctor.py` | `doctor`: Python, ffmpeg, registry and drives, the resolved project, plugin version, nonce folder, integrity, drift |
| `codex.py` | `codex-hook` and `codex-config` |
| `cli.py` | argument parsing, text and JSON output |

The commands, grouped by who runs them:

| Who | Commands |
|---|---|
| **Operator only**: the commands that write the record, refused to anyone else whatever the spelling | `approve`, `reject`, `client-said`, `stage` (including the plugin's automatic `stage auto`), `accept-edit`, `new-client`, `inbox accept`, `inbox dismiss` |
| **The plugin and Codex run them** (open: they only record and check) | `observe`, `rendered`, `codex-hook` |
| **Anyone** | `use`, `status`, `recall`, `context`, `report`, `check-render`, `check-approval`, `import-review` (writes drafts only), `inbox` (list), `drift`, `integrity`, `doctor`, `codex-config` |

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

Joel's entry still carries `protected_files`, `blocked_commands`, `shared_paths` and `audio_libraries`
from the guard; nothing reads them since 1.0.0 (left in place so the registry did not change; delete
them when convenient). `client-template/` is what `aem new-client` copies into an empty design-system
folder: decisions file (with an "Open questions" section for `recall`), rules file,
`critic/labelled-cases.jsonl` with its header, `text/`, a README and a registry entry template.

### 3.3 The Claude Code plugin (`plugin/aavkar-educational-motion-studio/`, 1.0.0)

One plugin of function hooks. The engine allows one hook per event per module and follows `$`
only within one file, so `hooks/register.tsx` owns every `on(...)`, builds an `io` object of
closures over `$`, and passes it to six feature files that never see `$`:

| Feature | File | What it does |
|---|---|---|
| Context | `context.ts` | On session start and every 30 s: `aem status` + `aem context` → the status line and a prompt section (the principle, the project, three rules for the agent, the client's recall). At session start a toast (`AEM 1.0.0 · joel/P2 · resolved from folder`, or `… no project (folder not registered)`), the recall in the transcript for the operator, and drift toasts. `/aem use` (checks with the CLI, then pins the project to this session), `/aem use --clear`, `/aem status`, `/aem recall`, `/aem new-client`. |
| Ledger | `ledger.ts` | Automatic events: session start/end, your prompts (with origin), turn start/end, tool calls ≥ 30 s, idle start/end (no prompt and no turn for `idle_minutes`, measured from the last activity). `/stage`, `/pause`, `/resume`, `/wait`, `/report`. |
| Observe | `observe.ts` | Before every `Bash`, `Read`, `Write`, `Edit`, `MultiEdit`, `NotebookEdit` call (subagents' too): `aem observe`, which records it. Never refuses, with one exception: a delivery of media with no current approval opens the engine's dialog, "fd_S01 was re-rendered after you approved it. Deliver anyway?", Deliver (records the approval through the confirmation, then runs) or Stop (refuses the call). Where no dialog can be shown, the call is refused once with the `/approve` command to type, and the identical call repeated goes through. Toasts a stage AEM inferred. |
| Record | `record.ts` | `/approve`, `/reject`, `/client-said`, `/accept-edit`: the slash commands that write the record, each with a one-time nonce. |
| Render sentinel | `sentinel.ts` | After every `Bash` call: `aem rendered`. For a render, a pass/fail toast with the first reason, the full result added after the command's output for the agent, and the status line redrawn (stale count). |
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
| `reviews/<client>/<date>-*` | project | `import-review` | CSV copy, review JSON, draft rulings, draft labelled cases |
| decisions file | design system | `client-said` only | dated, verbatim, scoped entry, "typed by <operator> with /client-said in Claude Code" or "in a terminal" |
| `critic/labelled-cases.jsonl` | design system | `approve`/`reject` with `--label`, `inbox accept`/`dismiss` | the file's own fields + `item_kind`, `gate`, `reason`, `decision`, `inbox_ref`…; `source` = operator id; operator rulings are `development case` |
| `codex/pending/` | `~/.aem/` | `codex-hook` | start time of a running Codex Bash call |

Ledgers are append-only. A correction is a new line (a rejection, a stale mark, a correcting case),
never an edit.

---

## 5. How it should be used: a video, gate by gate

The operator is Yuvraj (or whoever runs the studio). "Agent" is Claude Code with the plugin.

**Start.** Start Claude Code in the project's folder (`P2 - Claude Code`). Check the start toast
(`AEM 1.0.0 · joel/P2 · resolved from folder`; no toast means the plugin is not loaded), the recall in
the transcript, the status line and any drift toast. Started somewhere else? `/aem use joel/P2` pins it
to that session. `aem doctor` says what is wrong with an install.

**G1 Inputs.** `/stage G1`. The agent builds the word map, footage inventory and inputs list, per
the skill. If you are waiting for Joel's footage: `/wait joel`; `/stage G1` or `/resume` when it
arrives.

**G2 Plan.** `/stage G2`. The agent writes `style-guide.md`, `shotlist.md` (and `visual-plan.md`).
Review rows in `/inbox` or just read and approve the plan in conversation.

**G3 Stills.** `/stage G3`. Stills under `stills/` appear in the inbox; approve or reject each.

**G4 Rough render.** `/stage G4 fd_S01_next-token` per scene. The agent renders (`bin/r.sh …`);
the sentinel checks every output and tells both of you. A flash or wrong frame count is the agent's
to fix before you look. When you are happy: `/approve fd_S01_next-token` (its last checked render,
at the open gate). `/reject fd_S01_next-token <reason>` otherwise.

**G5 Critique and repair.** The agent critiques and repairs. Any re-render makes earlier approvals
stale at once (status line: `· 1 stale`). Approve again after you have looked.

**G6 Deliver.** `/stage G6 …`. The agent checks approvals first (`aem check-approval`). If it writes a
placement FCPXML or copies a render into `Animations Done` while that render has no current approval,
you get the one question AEM asks: Deliver (recorded as approved through the confirmation) or Stop.

**G7 Joel's review.** Export Frame.io comments as CSV; the agent (or you) runs `aem import-review`.
In `/inbox`, rule on each comment (Keep, Change, Remove, or Reject a mis-mapped one). Record what
Joel said with `/client-said video --source "Frame.io, <date>" <his words>`. Shots with no comment
stay pending: silence is not a ruling.

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

| What | Result at 1.0.0 |
|---|---|
| CLI unit tests (`tests/run.sh`, which wraps `python3 -m unittest discover -s tests -t tests`) | see §11 for the run's numbers. Kept: ledger, sentinel, integrity, operator-only refusal, isolation, resolution from the folder. New: `test_observe.py` (every call AEM denied in the P2 session of 6 October now runs with no interruption and is recorded; the delivery confirmation; stage inference), `test_integrity.py`, `test_recall.py`, `doctor`. Deleted: the guard's and the chat authority's tests (`test_guard.py`, `test_authority.py`). |
| Plugin tests (`claude plugin test`, Claude Code 2.1.288) | see §11. New: `observe.test.ts` (the P2 calls run with no dialog; an unapproved delivery asks, an approved one does not; Deliver, Stop, dismiss, the no-dialog fallback), `record.test.ts`. Deleted: `guard.test.ts`, `authority.test.ts`. The `claude` on PATH (2.1.283) cannot load the plugin; `tests/run.sh` uses the desktop app's newest bundled build |
| Isolation | the run fails if `~/.aem` or `registry/clients.json` changed |
| `claude plugin validate` (plugin and marketplace) | pass |
| `tsc` strict | **not run**: no TypeScript compiler is installed here |
| Flash scan on 59 real P1 masters and the client-fix renders | Joel's flash caught, fix passes (run at `275e0bc`, not repeated) |
| `aem drift` on Joel's real design system | no drift after the skill change (§3.6) |
| `aem recall joel` and `aem doctor` on the real design system and P2 | read-only; recall lists J-01…J-08, four rulings, four open questions, 3 development cases |
| Codex 0.146 live (`tests/live/codex-hooks-check.sh`) | at 0.8.0: SessionStart context ran; the agent's `aem approve` was refused by the CLI itself. Not re-run for 1.0.0 |

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
| Render sentinel | background renders; unlisted render scripts; renders written outside `renders/` and not named | other media changing under `renders/` during the command is checked too |
| Recall | rulings not written as `## ` entries; quotes not in `>` lines or quotation marks; long quotes are cut with an ellipsis (the agent reads the file for the rest) | — |
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

## 11. Where things stand (6 October 2026, 1.0.0)

Done and committed: the notary redesign below (§12), on top of Phases 1–7.

Results of the 1.0.0 run: CLI unit tests 187 pass; plugin tests 52 pass in 7 files; `claude plugin
validate` passes for the plugin and the marketplace; the isolation check found `~/.aem` and
`registry/clients.json` unchanged. The plugin 1.0.0 is installed for the user from the local
marketplace; it takes effect in new sessions.

Not done yet:

- **Not pushed anywhere**: the repository has no remote, so the marketplace works from a local path.
- **Not switched on for you**: the review inbox setting is off; Codex hooks are not in your
  `~/.codex/config.toml` (run `aem codex-config` and add them when you want them).
- **The end-to-end acceptance run** (`tests/acceptance/operator.sh`) was started before 0.8.0 and has
  not been re-run.
- **Live checks not re-run for 1.0.0**: the Codex hooks check, and a live session's dialog (the
  confirmation is covered by plugin tests with the engine's own AskUserQuestion path).
- P2 is registered (`joel/P2`, `P2 - Claude Code`, 25/1 from `RoughCut.mp4`, 3840 × 2160); it has no
  HyperFrames project yet.

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
