# About Aavkar Educational Motion Studio

The whole picture in one document: why Aavkar Educational Motion Studio (AEM) exists, what each
part does, how the parts fit, how the studio should use it day to day, what it deliberately does
not do, and where it stands today. The other docs go deeper: [INSTALL.md](INSTALL.md) (setup),
[OPERATOR.md](OPERATOR.md) (daily use), [CLI.md](CLI.md) (every command, format and limit).

Written 6 October 2026 at commit `275e0bc` (plugin 0.7.0), and updated the same day for the 0.8.0
redesign (§12): there is no global active project, and the CLI refuses operator-only commands itself;
and again for 0.9.0 (§13): **AEM allows whatever the operator asks for in chat**, and ledger integrity.
Sections 3, 4, 5, 9 and 11 describe 0.9.0; §12 and §13 say what changed and why.

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
| `registry.py` | Reads the registry; resolves the project for every call (`AEM_PROJECT`, the plugin's session pin, the working folder); refuses temporary or out-of-registry folders; the last-used hint |
| `operator.py` | The check at the entry of every operator-only command: a real terminal with no agent markers, the plugin's one-time nonce, or the operator's message (a turn authority) |
| `authority.py` | `authority open/close/uses`: the turn authority an operator's prompt opens, and its `operator_prompt` record |
| `integrity.py` | `integrity`, `accept-edit`: the manifest of every ledger line AEM wrote, and what differs from it |
| `fps.py` | Frame rates as exact rationals (24000/1001, never 23.976); discovery from `aem.project.json`, FCPXML, `data/words.json`, `frame.md`; refuses conflicts; timecode incl. drop-frame |
| `ledger.py` | `events.jsonl`: stages, waits, pauses, automatic events, the time report |
| `approvals.py` | `approvals.jsonl`: approve, reject, stale marks, the approval check; item kinds (render, still, plan row) |
| `render.py` | `check-render`: probe against spec, frame count against the composition's duration, and the one/two-frame flash scan |
| `sentinel.py` | `rendered`: is a finished command a render, which files did it write, check each |
| `guard.py` | `guard`: rules AEM-G01, G02, G03 and G05 for one tool call (there is no G04) |
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
| **Operator only** (the CLI refuses them unless you are running them or asked for them in chat, §12, §13) | `use` (and `use --clear`), `stage` (including the plugin's automatic `stage auto`), `approve`, `reject`, `client-said`, `allow`, `new-client`, `accept-edit`, `inbox accept`, `inbox dismiss`; the plugin's own `authority open`/`close` |
| **Plugin / Codex run them** | `guard`, `rendered`, `codex-hook` (open: they only judge or check) |
| **Anyone, read-mostly** | `status`, `context`, `report`, `check-render`, `check-approval`, `import-review` (writes drafts only), `inbox` (list), `drift`, `integrity`, `authority uses`, `codex-config` |

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

### 3.3 The Claude Code plugin (`plugin/aavkar-educational-motion-studio/`, v0.8.0)

One plugin of function hooks. The engine allows one hook per event per module and follows `$`
only within one file, so `hooks/register.tsx` owns every `on(...)`, builds an `io` object of
closures over `$`, and passes it to five feature files that never see `$`:

| Feature | File | What it does |
|---|---|---|
| Context | `context.ts` | On session start and every 30 s: `aem status` + `aem context` → the status line (`AEM · client · project · gate scene · h:mm · N stale`) and a prompt section telling the agent the project, gate, frame rate, files to read first, Joel's J- preferences, the protected files and which `aem` commands it may not run. Toasts drift. A toast at every session start (`AEM 0.8.0 · joel/P2 · resolved from folder`, or `… no project (folder not registered)`). `/aem use` (checks with the CLI, then pins the project to this session), `/aem use --clear` (drops the pin), `/aem status`, `/aem new-client`. |
| Ledger | `ledger.ts` | Automatic events: session start/end, your prompts (with origin), turn start/end, tool calls ≥ 30 s, idle start/end (no prompt and no turn for `idle_minutes`, measured from the last activity). `/stage`, `/pause`, `/resume`, `/wait`, `/report`. |
| Guard | `guard.ts` | Before every `Bash`, `Read`, `Write`, `Edit`, `MultiEdit`, `NotebookEdit`, `Glob`, `Grep`, `LS` call (subagents' too): `aem guard`. A denial never runs; the agent is told the rule, why, and what the operator can do; you get a toast. `/approve`, `/reject`, `/client-said`, `/allow`. |
| Render sentinel | `sentinel.ts` | After every `Bash` call: `aem rendered`. For a render, a pass/fail toast with the first reason, the full result added after the command's output for the agent, and the status line redrawn (stale count). |
| Review inbox | `inbox.tsx` | Only with the `reviewInbox` setting on: `/inbox` opens a pane listing what waits on you; buttons run the commands each item names; Reject asks for a reason. |

Settings: `aemPath` (default `aem`, falls back to `~/.local/bin/aem`) and `reviewInbox` (off).
Slash commands that change records answer only to the operator: prompts from the composer, the
bridge or the SDK; a plugin, a peer agent or the agent itself is refused. For each operator command
the plugin makes a random one-time nonce, writes only its SHA-256 to `~/.aem/nonces/` with a
60-second expiry, and hands the nonce to that one `aem` call, which is how the CLI knows the
operator typed it (`hooks/aem.ts`, `hooks/sha256.ts`).

State it keeps (`types/index.d.ts`): `view` (what `aem status`/`context` said), `ledger` (session
recorded for, last activity, idle start, running turn, idle minutes), `inbox` (items, the item
asking for a reason, last message), and `pin` (the session's `<client>/<project>`, passed to every
`aem` call as `AEM_PROJECT`; nothing global stores a project).

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
| `active.json` | `~/.aem/` | `aem use` | **A last-used hint only**, `{_comment, client, project, project_dir, set_at}`: `aem status` shows it when nothing resolved; nothing else reads it. A hint pointing outside the registry's roots is renamed `active.json.stale`. |
| `nonces/<sha256>` | `~/.aem/` | the plugin | `{expires_at}`: the hash of a one-time operator nonce; deleted when used or expired. The guard denies the agent's Write and Edit there. |
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

**Start.** Start Claude Code in the project's folder (`P2 - Claude Code`). Check the start toast
(`AEM 0.8.0 · joel/P2 · resolved from folder`; no toast means the plugin is not loaded), the status
line and any drift toast. Started somewhere else? `/aem use joel/P2` pins it to that session. If the
frame rate is not found or disagrees, fix the source: state it in `aem.project.json`.

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

**Close.** `/stage end`, `/report`. Nothing needs clearing: a project is not stored anywhere global.

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

| What | Result at 0.9.0 (earlier results say when they were run) |
|---|---|
| CLI unit tests (`tests/run.sh`, which wraps `python3 -m unittest discover -s tests -t tests`) | 194 pass (157 at 0.8.0, plus 37 in `tests/test_authority.py`: authority from chat, the guard on it, `client-said` from chat, the P2 friction, integrity, isolation) |
| Plugin tests (`claude plugin test`, Claude Code 2.1.288) | 55 pass in 7 files (44 at 0.8.0, plus 11 in `tests/authority.test.ts`). The `claude` on PATH (2.1.283) cannot load the plugin (`prompt.compose` is not an event there); `tests/run.sh` uses the desktop app's newest bundled build |
| P2 friction regression | the four friction tests fail against the 0.8.0 guard and pass against 0.9.0 |
| Live chat authority (`tests/live/chat-authority-check.sh`, headless, installed plugin, sandbox) | **not run**: headless `claude -p` could not authenticate ("OAuth session expired"). That `$.env.set` reaches the Bash tool rests on the engine's documentation and the plugin tests' mocked engine, not on a live session yet |
| Isolation | the run fails if `~/.aem` or `registry/clients.json` changed; it did not |
| `claude plugin validate` (plugin and marketplace) | pass |
| `tsc` strict | **not re-run**: no TypeScript compiler is installed here (it was 0 errors at `275e0bc`) |
| Flash scan on 59 real P1 masters and the client-fix renders | Joel's flash caught, fix passes (run at `275e0bc`, not repeated) |
| `aem drift` on Joel's real design system | no drift (after the 0.9.0 skill change) |
| Marketplace install | 0.9.0 installed for the user from the local marketplace (`claude plugin update`), enabled; takes effect in new sessions |
| Codex 0.146 live (`tests/live/codex-hooks-check.sh`) | SessionStart context ran; the agent's `aem approve` was refused by the CLI itself (no hook needed) |
| Real P2 | `aem status` from the P2 folder resolves `joel/P2`, fps 25/1 from `aem.project.json`; from the AEM repo it resolves no project |
| Live guard in the build session | denied the agent's own commands several times (G01, G02, G04) before 0.8.0, including the false positives that motivated §12 |

Real client files were only read, except the skill change in §3.6, which the brief asked for.
Everything else was tested on copies in temporary folders.

---

## 9. Limits, exactly

| Check | Misses | Over-matches |
|---|---|---|
| AEM-G01 protected file | a path built at run time, a script that writes the ledger, an MCP tool | any command whose text names a protected file (`cmp joel-decisions.md`): use the Read tool |
| AEM-G02 outside the client's folders | files reached through variables, globs expanded later, `cd` then a relative path, a program's own config | a tool outside `shared_paths` (the Claude Code app folder was, until added) |
| AEM-G03 blocked command | another spelling, a wrapper script | — |
| Operator-only commands (the CLI, §12) | an agent that strips the agent markers from its environment and allocates a terminal, or writes a nonce file with a shell command; a script that sets the library's private flag | — (a commit message or heredoc that mentions one is just text) |
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

## 11. Where things stand (6 October 2026, after Phases 1 and 2 of 0.8.0)

Done and committed: Phases 1–6 and most of Phase 7 (marketplace, Codex parity, docs, the skill
change, the guard fix).

Not done yet:

- **The end-to-end acceptance test is in progress**, and has to be re-planned for 0.8.0 (it runs in a
  sandbox with `AEM_PROJECT`; `tests/acceptance/operator.sh init`). Step 1 was done on a temporary
  copy of P1 scene #20 (next-token) before the redesign. Steps 2–8 (protected-file edit denied, render and
  check, `/approve`, change source and re-render → stale, placement denied, re-approve → placement
  allowed, `/report` with idle separated) remain. Its operator steps are typed into headless Claude
  Code sessions by `tests/acceptance/operator.sh`; the agent steps run live in a session with the
  plugin. Its results will go in `docs/ACCEPTANCE.md`.
- **Not pushed anywhere**: the repository has no remote yet, so the marketplace works from a local
  path until it is on GitHub.
- **Not switched on for you**: the review inbox setting is off; Codex hooks are not in your
  `~/.codex/config.toml` (run `aem codex-config` and add them when you want them).
- Installing the plugin from the marketplace into your own Claude Code (rather than the development
  folder this session used) is yours to do, per INSTALL.md. **The installed plugin is still 0.7.0 until
  you update it, and the CLI you are running is already 0.8.0**: until you update the plugin, its slash
  commands and automatic ledger events are refused by the CLI (INSTALL.md, "Updating").
- The guard's G01/G02 text matching is as limited as §9 says (0.9.0 fixed the `~/…;` tokenizer bug and
  G05 on reads, nothing more). The ledger integrity check is built (§13).
- P2 is registered (`joel/P2`, `P2 - Claude Code`, 25/1 from `RoughCut.mp4`, 3840 × 2160); it has no
  HyperFrames project yet.

---

## 12. What 0.8.0 changed, and why (6 October 2026)

The first acceptance run left the one global file `~/.aem/active.json` pointing at a temporary copy of
P1, with that copy's registry path in it. Every session then trusted it: the guard scoped work to a
`/tmp` project, the ledger wrote there, and the operator's own `/aem use --clear` went to a session
without the plugin and did nothing, silently. Five faults, five fixes:

| Fault | Fix |
|---|---|
| A global file held the active project and its registry path, and a test overwrote it | **No global state.** The project is resolved per call: `AEM_PROJECT`, the plugin's session pin, the working folder, else none. The registry is never stored. `active.json` is a labelled last-used hint that only `aem status` shows; a stale one is renamed and reported. Tests run in a sandbox and a test fails if `~/.aem` or `registry/clients.json` changed. |
| A project under `/tmp` was accepted | Refused unless `AEM_SANDBOX=1` (only the test sandbox sets it), and so is a folder outside the client's roots. |
| `/aem use --clear` failed silently in a session without the plugin | The pin lives in the plugin and dies with the session. Every session shows a start toast; no toast means no plugin. |
| The guard read shell text: `"path";` became a path, a commit message or heredoc naming `aem approve` was denied | **Operator-only commands are checked by the CLI, not by text.** The CLI refuses them unless a real terminal (no agent markers) or the plugin's one-time nonce shows the operator is running them, however they are spelled. AEM-G04 is gone. (The remaining text rules, G01, G02 and G03, and the tokenizer false positives in them, are Phase 3.) |
| A cached view let an edit through for minutes | Fixed in 0.7.0, test kept: every guarded call goes to the CLI. |

Experiments behind the operator check (CLI.md has the table): neither Claude Code's Bash tool nor
Codex's shell can open `/dev/tty`; but a pseudo-terminal the agent's own shell allocates (`script`,
Python's `pty`) passes a bare terminal test, so the check also requires that none of the markers an
agent host sets (`CLAUDECODE`, `CODEX_CI`, ...) is in the environment. That is cooperative: an agent
that strips them, or writes a nonce hash file with a shell command, passes. The ledgers' append-only
hashes, and the integrity check (§13), are what show it afterwards.

Two bugs found on the way, both fixed with tests: the longest-match folder lookup compared the wrong
tuple field, and the plugin's idle tick could record `idle_start` twice when `aem` was slow.

Compatibility: the skill's `events.jsonl`, `approvals.jsonl` and labelled-cases formats are unchanged
(no field was added or removed). Removed: `aem use --path` and `--fps`, the `AEM-G04` rule, and the
stored `registry`/`fps` fields in `active.json`.

---

## 13. What 0.9.0 changed, and why (6 October 2026)

**A new first principle, replacing guard modes: AEM allows whatever the operator asks for in chat.** The
guard and the operator-only commands exist only to stop the agent acting on its own authority. When the
operator has asked, the decision is theirs; AEM records it and never blocks it. The P2 session that day
showed the cost of the old rule: Yuvraj asked for things in plain words and had to retype them as slash
commands, and the guard denied reads of an FCPXML and the shared `~/Tools/fcp-edit-workflow`.

| Part | What it does |
|---|---|
| Turn authority (`authority.py`, plugin `authority.ts`) | On a prompt from an operator origin (composer, bridge, SDK; never a plugin, peer, schedule, notification or the agent) the plugin runs `aem authority open`: a random nonce whose SHA-256 goes to `~/.aem/nonces/` with the prompt's exact text, session and turn, expiring at the turn's end or after 60 minutes, whichever is first; and an `operator_prompt` event with the exact text, its SHA-256, session, turn and time. The nonce is set as `AEM_OPERATOR_TURN` in the plugin's process environment (`$.env.set`), which every `Bash` call inherits. `turn.complete` closes it. |
| Guard | On a valid authority it never denies: what it would have denied is allowed and logged as `allowed_by_operator_prompt` (rule, tool, call, prompt id), with a toast. Without one, unchanged. |
| Operator commands | Accepted on the authority (path (c) in `operator.py`), each record carrying `via: "chat"`, `prompt_id`, `prompt_excerpt`; each one toasted (`approve x via chat: '<excerpt>'`). `authority open`/`close` are never accepted on it. |
| `client-said` from chat | The quote must appear verbatim in the authorising prompt, or: "paste Joel's exact words in your message". Joel's words stay his. |
| Ledger integrity (`integrity.py`) | A manifest of every line AEM writes to `events.jsonl`, `approvals.jsonl`, the decisions file and the labelled cases; `aem integrity` reports inserted, edited and removed lines and whether an operator's prompt let the write through; `aem accept-edit` (operator only) accepts them, recorded. |
| Friction from P2 | AEM-G05 never fires on reads (`cat`, `grep`, `unzip`, `xmllint`, `ffprobe`, inline parsing code) and no longer denies a command that names an `.fcpxml` but no render. Shell words are split as a shell splits them, so `~/Tools/fcp-edit-workflow;` is the folder and a `;`. An XPath (`//asset`) is not a path. These work with and without an authority, because a turn may be autonomous. |
| Skill | `mergetomaster-studio`: run operator commands only when Yuvraj's latest message asks for that action; say what was recorded after each; never treat earlier messages as standing permission. Zip rebuilt, skill reinstalled, no drift. |

Limits, plainly: the authority is the turn's, not the command's (AEM cannot tell whether the message
really asked for a given action; the record lets the operator check); the CLI does not verify that the
process holding the nonce belongs to that session; during an operator turn the agent could write a nonce
file or a ledger by hand, which is logged and flagged but not stopped; an agent that writes a nonce file in
an autonomous turn forges an authority, as it could forge a one-time nonce before; the integrity manifest
sits beside the ledger; Codex has no turn authority. CLI.md, "Operator authority from chat" and "Ledger
integrity", has the detail.
