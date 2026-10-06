# About Aavkar Educational Motion Studio

The whole picture in one document: why Aavkar Educational Motion Studio (AEM) exists, what each
part does, how the parts fit, how the studio should use it day to day, what it deliberately does
not do, and where it stands today. The other docs go deeper: [INSTALL.md](INSTALL.md) (setup),
[OPERATOR.md](OPERATOR.md) (daily use), [CLI.md](CLI.md) (every command, format and limit).

Written 6 October 2026, at commit `275e0bc` plus this document (plugin 0.7.0).

---

## 1. Why AEM exists

Aavkar Productions makes educational animation for clients; the first is Joel Belton's
MergeToMaster YouTube channel. The craft lives in the client's **design system** (Joel's:
Brand, Motion and Edit Systems, `rules.md`, `joel-decisions.md`) and in a **studio skill**
(`mergetomaster-studio`) that tells an AI agent how to plan, build, critique, place and deliver
animations through seven gates (G1 Inputs … G7 Joel's review).

The skill asks for records an agent cannot be trusted to keep about its own work:

- **time per gate** (`events.jsonl`), so the next video can be planned;
- **approvals tied to the exact render** (`approvals.jsonl`), so nothing reaches the client's
  timeline that Yuvraj did not see, byte for byte;
- **the client's own words** (`joel-decisions.md`), never paraphrased into his voice;
- **the critic's labelled cases** (`critic/labelled-cases.jsonl`), the golden set the automated
  critic is calibrated against.

Before AEM, the agent appended those lines itself, so the records were only as honest as the agent.
AEM moves the writing to the operator's commands, times the work automatically, checks every render
the agent makes, and stops the agent from placing or delivering what was not approved.

**AEM is a production layer, not a security system.** Its checks are recorded checks that stop
common mistakes and keep an honest ledger. Section 9 lists exactly what each one misses.

---

## 2. The shape of it

```
                          registry/clients.json  (everything client-specific)
                                     │
   ┌─────────────────────────────────┼──────────────────────────────────┐
   │                        aem  (Python CLI)                           │
   │  context · ledger · approvals · render check · guard · sentinel    │
   │  review import · inbox · drift · client records · codex hook       │
   └───────▲──────────────────────────▲─────────────────────▲──────────┘
           │ process calls            │ hook command        │ typed
           │                          │                     │
   Claude Code plugin           OpenAI Codex hooks       Operator's terminal
   (aavkar-educational-         (aem codex-hook)         (aem stage, approve, …)
    motion-studio)
           │
   status line · toasts · slash commands · /inbox pane · tool-call gate
```

Three rules shaped every decision:

1. **All logic lives in the CLI.** The plugin and the Codex hooks only translate events into `aem`
   calls and show the answers. `aem guard`, `aem rendered`, `aem context` and the rest give the
   same answer whoever asks, and every decision can be reproduced in a terminal with `--json`.
2. **Nothing client-specific is in code.** Names, folders, protected files, blocked commands,
   gates, render scripts, approval patterns, review settings and idle time come from the registry.
   A second client is a registry entry, not a code change.
3. **Extend the skill's formats, never fork them.** The skill's `events.jsonl` and
   `approvals.jsonl` lines are kept field for field; AEM only adds fields. The labelled-cases
   header line decides AEM's field names (Joel's file says `joel_words`, so AEM writes
   `joel_words`).

---

## 3. What was built, part by part

### 3.1 The `aem` command (`cli/`)

Python 3 standard library only, plus `ffprobe`/`ffmpeg`. About 4,700 lines across CLI and plugin.
Installed by `cli/install.sh` as a link at `~/.local/bin/aem`. Every command takes `--json`.

| Module | Holds |
|---|---|
| `registry.py` | Reads the registry; finds the client and project; the active project (`~/.aem/active.json`, `AEM_HOME` to move it) |
| `fps.py` | Frame rates as exact rationals (24000/1001, never 23.976); discovery from `aem.project.json`, FCPXML, `data/words.json`, `frame.md`; refuses conflicts; timecode incl. drop-frame |
| `ledger.py` | `events.jsonl`: stages, waits, pauses, automatic events, the time report |
| `approvals.py` | `approvals.jsonl`: approve, reject, stale marks, the approval check; item kinds (render, still, plan row) |
| `render.py` | `check-render`: probe against spec, frame count against the composition's duration, and the one/two-frame flash scan |
| `sentinel.py` | `rendered`: is a finished command a render, which files did it write, check each |
| `guard.py` | `guard`: rules AEM-G01 … G05 for one tool call |
| `context.py` | `context`: the text the agent is given each session |
| `review.py` | `import-review`: Frame.io CSV → frames, shots, word IDs, drafts |
| `inbox.py` | `inbox`: what waits on the operator; labelled cases from rulings |
| `clients.py` | `client-said`, `allow`, `new-client` |
| `drift.py` | text exports vs HTML pages, installed skill vs master, rule IDs vs `rules.md` |
| `codex.py` | `codex-hook` and `codex-config` |
| `cli.py` | argument parsing, text and JSON output |

The commands, grouped by who runs them:

| Who | Commands |
|---|---|
| **Operator only** (the guard denies them to the agent) | `use` (and `use --clear`), `stage`, `approve`, `reject`, `client-said`, `allow`, `new-client`, `inbox accept`, `inbox dismiss` |
| **Plugin / Codex only** | `guard`, `codex-hook` (denied to the agent); `rendered` (harmless) |
| **Anyone, read-mostly** | `status`, `context`, `report`, `check-render`, `check-approval`, `import-review` (writes drafts only), `inbox` (list), `drift`, `codex-config` |

### 3.2 The registry (`registry/`)

`clients.json` has `operator` (`{id: "yuvraj", name: "Yuvraj"}`), `shared_paths` (tools every
client may use: this repo, `~/.aem`, Claude Code's skills/plugins/dev-mods and app folder, Codex
packages, HyperFrames, Cut Assist, fcp-edit-workflow) and `clients`. Joel's entry, field by field:

| Field | Joel's value | Used by |
|---|---|---|
| `design_system`, `projects_root`, `projects` | the `00 - MergeToMaster Design System` folder; the Joel folder; `P1` → its HyperFrames project | everything |
| `decisions_file`, `decisions_order`, `decision_scopes` | `joel-decisions.md`, newest first, channel/video/instance | `client-said` |
| `rules_file`, `preference_prefix`, `rule_id_pattern` | `rules.md`, `J`, rule-ID regex | context (Joel's J- preferences), drift |
| `labelled_cases_file` | `critic/labelled-cases.jsonl` | inbox, review drafts |
| `text_dirs`, `skill`, `skill_master` | `text`, `mergetomaster-studio`, `Skill/mergetomaster-studio` | drift |
| `gates` | G1 Inputs … G7 Joel's review | stages, approvals, status |
| `waiting_on_client_ids` | `joel` | time report (waiting on client) |
| `protected_files` | design system: decisions, rules, labelled cases; project: approvals, events | AEM-G01 |
| `blocked_commands` | `snapshot --describe` | AEM-G03 |
| `approval_gates` | patterns `fcpxml`, `placement`, `place`, `deliver(y)`, `Animations Done`; `.fcpxml` writes; media `.mp4 .mov .m4v .mxf` | AEM-G05 |
| `render_sentinel` | `bin/r.sh`, `bin/ra.sh`, `bin/renderall.sh`; output `renders/` | sentinel |
| `review_inbox` | Frame.io CSV; plan files `shotlist.md`, `visual-plan.md`; stills `stills/`; gates G2/G3/G4 | import-review, inbox |
| `audio_libraries` | Epidemic Sound folder (Envato has no local path) | AEM-G02 scope |
| `idle_minutes` | 10 | idle detection |

`client-template/` is what `aem new-client` copies into an empty design-system folder:
decisions file, rules file, `critic/labelled-cases.jsonl` with its header, `text/`, a README and a
registry entry template.

### 3.3 The Claude Code plugin (`plugin/aavkar-educational-motion-studio/`, v0.7.0)

One plugin of function hooks. The engine allows one hook per event per module and follows `$`
only within one file, so `hooks/register.tsx` owns every `on(...)`, builds an `io` object of
closures over `$`, and passes it to five feature files that never see `$`:

| Feature | File | What it does |
|---|---|---|
| Context | `context.ts` | On session start and every 30 s: `aem status` + `aem context` → the status line (`AEM · client · project · gate scene · h:mm · N stale`) and a prompt section telling the agent the project, gate, frame rate, files to read first, Joel's J- preferences, the protected files and which `aem` commands it may not run. Toasts drift. `/aem use`, `/aem status`, `/aem new-client`. |
| Ledger | `ledger.ts` | Automatic events: session start/end, your prompts (with origin), turn start/end, tool calls ≥ 30 s, idle start/end (no prompt and no turn for `idle_minutes`, measured from the last activity). `/stage`, `/pause`, `/resume`, `/wait`, `/report`. |
| Guard | `guard.ts` | Before every `Bash`, `Read`, `Write`, `Edit`, `MultiEdit`, `NotebookEdit`, `Glob`, `Grep`, `LS` call (subagents' too): `aem guard`. A denial never runs; the agent is told the rule, why, and what the operator can do; you get a toast. `/approve`, `/reject`, `/client-said`, `/allow`. |
| Render sentinel | `sentinel.ts` | After every `Bash` call: `aem rendered`. For a render, a pass/fail toast with the first reason, the full result added after the command's output for the agent, and the status line redrawn (stale count). |
| Review inbox | `inbox.tsx` | Only with the `reviewInbox` setting on: `/inbox` opens a pane listing what waits on you; buttons run the commands each item names; Reject asks for a reason. |

Settings: `aemPath` (default `aem`, falls back to `~/.local/bin/aem`) and `reviewInbox` (off).
Slash commands that change records answer only to the operator: prompts from the composer, the
bridge or the SDK; a plugin, a peer agent or the agent itself is refused.

State it keeps (`types/index.d.ts`): `view` (what `aem status`/`context` said), `ledger` (session
recorded for, last activity, idle start, running turn, idle minutes), `inbox` (items, the item
asking for a reason, last message).

### 3.4 Codex (`aem codex-hook`, `aem codex-config`)

Codex 0.146 has command hooks. `aem codex-config` prints a `[hooks]` table for
`~/.codex/config.toml` with the absolute path of your `aem`. Then:

| Codex event | AEM |
|---|---|
| SessionStart | context text as `additionalContext`; `session_start` recorded (`agent: codex`) |
| UserPromptSubmit | `prompt`, `turn_start` |
| PreToolUse (`Bash`, `apply_patch`) | the guard; a patch is judged file by file; a denial is `permissionDecision: "deny"` |
| PostToolUse (`Bash`) | the render sentinel; long tool calls |
| Stop / SessionEnd | `turn_end` / `session_end` |

No slash commands, status line, toasts or inbox in Codex: the operator types `aem …` in a terminal.
No idle detection (no timer).

### 3.5 The marketplace (`.claude-plugin/marketplace.json`)

The repository is a marketplace named `aavkar-productions` listing the one plugin. Install is two
steps: `/plugin marketplace add <owner>/<repo>` (or a local path), then
`/plugin install aavkar-educational-motion-studio@aavkar-productions`.

### 3.6 The skill change

Joel's skill master (`00 - MergeToMaster Design System/Skill/mergetomaster-studio/SKILL.md`) has one
new section, "When Aavkar Educational Motion Studio (AEM) is loaded": when AEM's context is in the
session, the agent never writes `events.jsonl`, `approvals.jsonl`, `joel-decisions.md` or
`critic/labelled-cases.jsonl` by any tool, and asks Yuvraj to run the matching command (a table maps
each record to its slash command and `aem` command). Without AEM the skill works as before. The
chat zip was rebuilt with `Skill/build-chat-zip.sh` and the skill installed to
`~/.claude/skills/mergetomaster-studio/`; `aem drift` reports no drift. The previous `SKILL.md`
had SHA-256 `a75f6acf…` and the previous zip `7a423a7e…`.

---

## 4. The files AEM reads and writes

| File | Where | Written by | Format |
|---|---|---|---|
| `active.json` | `~/.aem/` | `aem use` | `{client, project, project_dir, registry, fps{num,den,source}, set_at}` |
| `events.jsonl` | project | AEM only | skill's `{ts, gate, scene, event, note}` + `source`, `session`, `turn`, `tool`, `duration_s`, `render`, `render_sha256`, `result`, `rule`, `allow_id`, `inbox_ref`, `agent`, `backfilled`… |
| `approvals.jsonl` | project | `approve`, `reject`, `check-render` (stale marks) | skill's `{gate, scene, render, render_sha256, source_revision, approver, date}` + `type` (approval / rejection / stale), `ts`, `render_check`, `item_kind`, plan-row fields |
| `reports/time.md` | project | `report` | per gate, per scene, per gate-and-scene, with how each number was computed |
| `aem.project.json` | project (optional) | you | `fps`, `render` (width, height, alpha), `scenes`, `flash.min_area_pct`, `placements`, `render_sentinel`, `review_inbox` |
| `reviews/<client>/<date>-*` | project | `import-review` | CSV copy, review JSON, draft rulings, draft labelled cases |
| decisions file | design system | `client-said` only | dated, verbatim, scoped entry, "entered by <operator>" |
| `critic/labelled-cases.jsonl` | design system | `approve`/`reject` with `--label`, `inbox accept`/`dismiss` | the file's own fields + `item_kind`, `gate`, `reason`, `decision`, `inbox_ref`…; `source` = operator id; operator rulings are `development case` |
| `codex/pending/` | `~/.aem/` | `codex-hook` | start time of a running Codex Bash call |

Ledgers are append-only. A correction is a new line (a rejection, a stale mark, a correcting case),
never an edit.

---

## 5. How it should be used: a video, gate by gate

The operator is Yuvraj (or whoever runs the studio). "Agent" is Claude Code with the plugin.

**Start.** `/aem use joel/P2`. Check the status line and any drift toast. If the frame rate is not
found or disagrees, fix the source or pass `--fps`.

**G1 Inputs.** `/stage G1`. The agent builds the word map, footage inventory and inputs list, per
the skill. If you are waiting for Joel's footage: `/wait joel`; `/stage G1` or `/resume` when it
arrives.

**G2 Plan.** `/stage G2`. The agent writes `style-guide.md`, `shotlist.md` (and `visual-plan.md`).
Review rows in `/inbox` (each row approved or rejected with a reason) or just read and approve the
plan in conversation.

**G3 Stills.** `/stage G3`. Stills under `stills/` appear in the inbox; approve or reject each.

**G4 Rough render.** `/stage G4 fd_S01_next-token` per scene. The agent renders (`bin/r.sh …`);
the sentinel checks every output and tells both of you. A flash or wrong frame count is the agent's
to fix before you look. When you are happy: `/approve fd_S01_next-token` (its last checked render,
at the open gate). `/reject fd_S01_next-token <reason>` otherwise.

**G5 Critique and repair.** The agent critiques and repairs. Any re-render makes earlier approvals
stale at once (status line: `· 1 stale`). Approve again after you have looked.

**G6 Deliver.** `/stage G6 …`. Placement FCPXML and delivery copies only go through for renders
whose exact bytes you approved (AEM-G05); the agent checks with `aem check-approval` first.

**G7 Joel's review.** Export Frame.io comments as CSV; the agent (or you) runs `aem import-review`.
In `/inbox`, rule on each comment (Keep, Change, Remove, or Reject a mis-mapped one). Record what
Joel said with `/client-said video --source "Frame.io, <date>" <his words>`. Shots with no comment
stay pending: silence is not a ruling.

**Close.** `/stage end`, `/report`. `/aem use --clear` if no project should be active.

**When the agent is blocked**, read the toast. Usually it is right (it tried to write a ledger, or to
place an unapproved render). If it is a harmless false match, `/allow <rule-or-text> <reason>` once.

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
of the frame width in one frame is reported.

---

## 7. Time report in detail

From `events.jsonl`, per gate, scene, and gate-and-scene: **wall** (start to finish), **agent busy**
(turn start to end), **idle** (no prompt and no activity for `idle_minutes`, from the last
activity), **waiting on client** (`waiting_on_<id>` for the client's ids), **waiting on others**,
**paused**, **attended between turns** (an operator present between turns), and **unobserved**
(gaps with no events, such as Codex sessions or a closed laptop). Idle is always separate, never
counted as work. Backfilled events (`--at`) are marked and counted. It is for planning, not billing.

---

## 8. Testing and verification

| What | Result at `275e0bc` |
|---|---|
| CLI unit tests (`python3 -m unittest discover -s tests -t tests`) | 109 pass |
| Plugin tests (`claude plugin test`) | 33 pass (context 7, guard 8, ledger 6, sentinel 6, inbox 6), terminal, desktop and mobile surfaces |
| `claude plugin validate` (plugin and marketplace) | pass |
| `tsc` strict | 0 errors |
| Flash scan on 59 real P1 masters and the client-fix renders | Joel's flash caught, fix passes |
| `aem drift` on Joel's real design system | no drift |
| Marketplace install (isolated config, Claude Code 2.1.288) | added, installed v0.7.0, enabled, `/aem status` answered |
| Codex 0.146 live (`tests/live/codex-hooks-check.sh`) | SessionStart context ran; PreToolUse blocked `aem approve` (AEM-G04) |
| Live guard in the build session | denied the agent's own commands several times (G01, G02, G04), including false positives listed in §9 |

Real client files were only read, except the skill change in §3.6, which the brief asked for.
Everything else was tested on copies in temporary folders.

---

## 9. Limits, exactly

| Check | Misses | Over-matches |
|---|---|---|
| AEM-G01 protected file | a path built at run time, a script that writes the ledger, an MCP tool | any command whose text names a protected file (`cmp joel-decisions.md`): use the Read tool |
| AEM-G02 outside the client's folders | files reached through variables, globs expanded later, `cd` then a relative path, a program's own config | a tool outside `shared_paths` (the Claude Code app folder was, until added) |
| AEM-G03 blocked command | another spelling, a wrapper script | — |
| AEM-G04 operator-only command | the Python package called from a script | a command that merely mentions one (a heredoc writing docs, a commit message) |
| AEM-G05 render not approved | renders read from a manifest the command does not name; unlisted patterns | — |
| Render sentinel | background renders; unlisted render scripts; renders written outside `renders/` and not named | other media changing under `renders/` during the command is checked too |
| Inbox | not live (refreshed on open and after each button); plan tables must be Markdown tables | an identical file under another name counts as already ruled |
| Everything | MCP tools; your own shell; other editors; Codex without hooks; anything when `aem` cannot run (fails open, with a toast every time) | — |

What the Claude Code API could not do, and the nearest thing built instead:

- One module may hook each event once, and `$` cannot cross an import: one dispatcher module with an
  `io` object of closures.
- `$.state` keys must be string literals: atoms declared in `register.tsx` only.
- A tool's result can carry extra text for the model only when the tool succeeded: on a failed Bash
  call the sentinel can toast but not add a note.
- The mobile app draws no text field, although its element table lists `Input`: the inbox checks
  the surface and sends Reject to `/reject` there.
- The prompt section cannot be verified headless without a model call; it is covered by tests and
  by `aem context`.

---

## 10. Design decisions worth knowing

- **Operator rulings are `development case`** in the labelled cases, with the client's words field
  empty: the skill counts only the client's explicit rulings in his words toward the critic's 30
  (M-19). A client comment accepted in the inbox keeps Joel's words verbatim and is `labelled` only
  with a ruling, the words and the approved render's SHA-256.
- **Overrides** (inbox Allow once / dismiss) also land in the labelled cases, as asked, with
  `ruling: null` and a `decision`, so they never look like shot rulings.
- **Approvals carry `item_kind`**: rejecting a still never unseats the render's approval; the stale
  count is renders only.
- **Fail open.** If `aem` cannot run, calls go through with a toast each time; a broken install
  should not stop a delivery day.
- **Guards ask the CLI on every call.** The first acceptance run found that a cached "no project"
  view let an edit through for up to 3 minutes after a project was activated elsewhere; since 0.7.0
  every guarded call and every Bash call goes to the CLI, and the view refreshes every 30 s.
- **Codex hooks at user level.** A project-level `.codex/hooks.json` did not load in `codex exec`
  testing.

---

## 11. Where things stand (6 October 2026)

Done and committed: Phases 1–6 and most of Phase 7 (marketplace, Codex parity, docs, the skill
change, the guard fix).

Not done yet:

- **The end-to-end acceptance test is in progress.** Step 1 (`/aem use`, `/stage G1`) is done on a
  temporary copy of P1 scene #20 (next-token). Steps 2–8 (protected-file edit denied, render and
  check, `/approve`, change source and re-render → stale, placement denied, re-approve → placement
  allowed, `/report` with idle separated) remain. Its operator steps are typed into headless Claude
  Code sessions by `tests/acceptance/operator.sh`; the agent steps run live in a session with the
  plugin. Its results will go in `docs/ACCEPTANCE.md`.
- **`~/.aem/active.json` currently points at that temporary copy**, so a Claude Code session with
  the plugin is guarded against Joel's temp folders until the test ends with `/aem use --clear`.
- **Not pushed anywhere**: the repository has no remote yet, so the marketplace works from a local
  path until it is on GitHub.
- **Not switched on for you**: the review inbox setting is off; Codex hooks are not in your
  `~/.codex/config.toml` (run `aem codex-config` and add them when you want them).
- Installing the plugin from the marketplace into your own Claude Code (rather than the development
  folder this session used) is yours to do, per INSTALL.md.
