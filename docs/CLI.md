# The `aem` command

Reference for Aavkar Educational Motion Studio (AEM)'s command-line tool. Every command accepts
`--json` and then prints exactly one JSON object with an `ok` field. Exit codes: `0` success, `1` a
check ran and failed (approval missing or stale, render check failed, drift found), `2` a usage or
input error.

Commands act on the project they run for, which comes from where they run (see [Which
project](#which-project)); `--client` and `--project` override it. `--registry` picks another
registry file. Some commands are the operator's alone and refuse to run for anyone else (see
[Operator-only commands](#operator-only-commands)).

## Which project

There is no global "active project". Every `aem` call resolves its project, in this order:

1. `AEM_PROJECT=<client>/<project>` in the environment of that process.
2. The Claude Code plugin's **session pin**: set by `/aem use` for that one session, and passed to
   every `aem` call the plugin makes as `AEM_PROJECT` (with `AEM_PROJECT_SOURCE=session-pin`, so
   `aem status` can say it is a pin).
3. The **working directory**: the registered project (the registry's `projects`) whose folder
   contains it, the longest match winning; else the client whose design system contains it (a
   client, no project).
4. **Nothing.** Commands that need a project say so and how to give one; the guard, the ledger, the
   render sentinel and the context then do nothing.

`--client`/`--project` on a command override the project and `aem status` says so. The guard and the
Codex hook use the working directory of the call they judge. `aem status` always shows the project,
its folder, the design system, the frame rate and the registry, and how each was found.

The registry is `--registry`, else `AEM_REGISTRY`, else the repository's `registry/clients.json`. It is
never a path read back from a state file.

**Where a project may be.** A project folder under `/tmp` or `/private/tmp`, or outside the client's
`projects_root` and design system, is refused, with the reason, unless `AEM_SANDBOX=1`. Only the test
sandbox (`tests/isolation.py`) sets it.

**`~/.aem/active.json`** is only a *last-used hint*: `aem use` writes it (`client`, `project`,
`project_dir`, `set_at`, and a comment saying so), and `aem status` shows it, labelled as a hint,
when nothing resolved, so a bare Terminal can say what you used last. Nothing else reads it. A hint
that points outside the registry's real roots is renamed to `active.json.stale` and `aem status`
says it did.

## Commands

| Command | What it does |
|---|---|
| `use <client>/<project>` | Checks that the project resolves (registry entry, exact folder name, or a unique `NAME - ` prefix: `joel/P2` finds `P2 - Claude Code`), has a stated frame rate and may be used, and writes the last-used hint (`AEM_HOME` overrides `~/.aem`). It changes nothing a command trusts. In Claude Code, `/aem use` runs it and then pins the project to that session. `use --clear` forgets the hint (`/aem use --clear` drops the session pin). There is no `--path` and no `--fps`: a project is its registered folder, and its frame rate is what the folder states. Operator only. |
| `codex-hook` | Answers one OpenAI Codex hook event (JSON on stdin, one JSON object out); see Codex below. Codex runs it; the agent may not. |
| `codex-config [--format toml\|json]` | Prints the hook configuration that makes Codex call `codex-hook`, with the absolute path of the installed `aem`. |
| `status` | The project, its folder, design system, fps and registry, and **how each was resolved**; the open stage and its time, approvals (standing and stale), active overrides, the last render check, and the status-line text. With no project resolved, it says so and shows the last-used hint, labelled. |
| `stage start <gate> [scene] [--switch]` | Opens a stage. Every `stage` action is operator only, including the plugin's `stage auto`, which the plugin runs with a nonce. Gates come from the client's registry entry. `--switch` first finishes the stage open for the same scene (or the whole video); `/stage` always uses it. |
| `stage end [gate [scene]]` | Closes the named stage, or the most recently opened one. |
| `stage pause`, `stage resume` | Pause and resume the current stage. `resume` also ends a wait. |
| `stage wait <who>` | Work waits on someone: `waiting_on_<who>`. Waiting ends at the next start, finish or resume of that gate. `wait blocked` writes the skill's `blocked`. |
| `stage auto <event>` | Automatic events from the plugin: `session_start`, `session_end`, `prompt`, `turn_start`, `turn_end`, `tool_call` (with `--tool`, `--duration-s`), `idle_start` (with `--since`, the last activity's time), `idle_end`. `--session`, `--turn` and `--origin` record the Claude Code session, turn and prompt origin. |
| `report [--no-write]` | Writes `<project>/reports/time.md`. |
| `approve <item> [path] [--gate G] [--row NAME] [--label]` | Appends an approval for that exact file's SHA-256. Without a path, the item's most recently checked render; without a gate, the open stage's. An image is approved as a still; `--row` approves one row of a plan table in `path`. `--label` also appends the ruling to the client's labelled cases. Operator only. |
| `reject <item> --reason TEXT [--path FILE [--row NAME]] [--gate G] [--label]` | Appends a rejection: of that file (or plan row) when given, else of the item's latest approved render, whose approval stops standing. Operator only. |
| `client-said --scope channel\|video\|instance --source TEXT [--item SHOT]` | Reads the client's words from standard input and adds a dated, verbatim entry to the client's decisions file, marked "entered by <operator>". Operator only. |
| `allow <rule-or-command> --reason TEXT [--once]` | An override the guards honour. `--once` is consumed by the next matching call. `--list`, `--revoke ID`. Operator only. |
| `inbox [list]`, `inbox accept <id> --ruling keep\|change\|remove [--label]`, `inbox dismiss <id> --reason TEXT [--label]` | What waits on the operator, each item with the exact commands its buttons run; see Review inbox below. `accept` and `dismiss` are operator only. |
| `check-approval <path> [--item] [--gate]` | Passes only if this file's SHA-256 has a standing approval. |
| `check-render <path> [--item] [--no-record]` | ffprobe against the project spec, a scan of every frame for one- and two-frame flashes, SHA-256, a `render_check` event, and stale marks on earlier approvals of the item. |
| `import-review <csv> [--fps N/D] [--start-tc TC] [--placements FILE]` | Maps a Frame.io comment export to frames, shots and word IDs. Writes review files and draft labelled cases; never edits the decisions file or the critic's file. |
| `rendered` | Checks the renders a finished shell command wrote, read as JSON on stdin (`{command, cwd, started_at, exit_code, probe_only}`). Runs `check-render` on each and returns a toast line and a note for the agent. The plugin runs it after every `Bash` call; see Render sentinel below. |
| `guard` | Decides one tool call, read as JSON on stdin (`{tool, input, cwd}`). Exit 0 allow, 1 deny. The plugin runs it before every file or shell tool call; see Guards below. |
| `drift [--client ID] [--skills-dir DIR]` | Text exports vs their HTML pages, installed skill vs master, and rule IDs in the skill vs the rules file. |
| `new-client <id> --name --design-system DIR --projects-root DIR [--contact] [--skill]` | Scaffolds a design system from `registry/client-template/` into a new or empty folder and adds a registry entry. |

## Frame rate

Never assumed. `aem use` (and every command that needs the rate) reads every source the project has,
and refuses if they disagree or if there is none:

1. `aem.project.json` `"fps": "24000/1001"`
2. FCPXML in the project (`*.fcpxml`, `out/`, `data/`, `*.fcpxmld/Info.fcpxml`): the sequence's
   format `frameDuration` (`1001/24000s` is 24000/1001)
3. `data/words.json` `fps_num`/`fps_den`
4. a HyperFrames `frame.md` `fps : "N/D"` line

There is no override: state the rate where the project can be read (`aem.project.json` is the place;
read it from the edit, for example `ffprobe`'s `r_frame_rate`). `import-review --fps` is a separate,
per-file option for a delivered file at another rate. The rate is stored as integers `num`/`den`. Decimal spellings (`23.976`) are
refused. Frame maths: `frame = round(seconds × num / den)`; timecode counts at the nominal rate
(24 for 24000/1001, 30 for 30000/1001, 25 for 25/1), with `;` drop-frame for 30000/1001 and
60000/1001.

## Project settings: `aem.project.json`

Optional, in the project folder. AEM reads the keys below and ignores any other (a `notes` field is a
good place to say where the rate came from).

```json
{
  "fps": "24000/1001",
  "render": {"width": 3840, "height": 2160, "alpha_extensions": [".mov"]},
  "scenes": {"fd_S01_next-token": {"composition": "compositions/next-token.html"}},
  "flash": {"min_area_pct": 0.1},
  "placements": "data/edit.json",
  "render_sentinel": {"command_patterns": ["\\bbin/render\\.sh\\b"], "output_dirs": ["renders"]}
}
```

Per scene you can also give `frames`, `duration_s`, `width`, `height`, `alpha`. Without a duration,
`check-render` reads the HyperFrames composition's `data-duration` (found by `scenes.<item>.composition`,
or a file in `compositions/` whose name ends the item name: `fd_S01_next-token` finds `next-token.html`).

## Item names

An item is the scene or master name an approval is about. When not given, it is the file name
without its version suffix: `renders/v09/fd_S01_next-token_v09.mp4` is `fd_S01_next-token`. An
approval matches a file by SHA-256, so a delivery copy at another path passes if its bytes match.

## Ledgers

### events.jsonl

The skill's line, with the skill's fields first:

```json
{"ts": "2026-10-06T14:05:00+05:30", "gate": "G2", "scene": null, "event": "start", "note": "shot list"}
```

AEM's events: `start`, `finish`, `pause`, `resume`, `waiting_on_<who>`, `blocked`, the automatic
events above, `render_check`, `approval`, `rejection`, `client_said`, `allow`, `allow_used`,
`allow_revoked`, `review_import`, `denial`, `labelled_case`, `inbox_resolved`. Extra fields after the five: `source`, `session`, `tool`,
`duration_s`, `render`, `render_sha256`, `result`, `backfilled`. Events entered with `--at` carry
`"backfilled": true` and the report counts them.

### approvals.jsonl

```json
{"gate": "G4", "scene": "fd_S01_next-token", "render": "renders/v09/fd_S01_next-token_v09.mp4", "render_sha256": "<64 hex>", "source_revision": "<git commit, or sha256: of the scene source>", "approver": "Yuvraj", "date": "2026-10-06", "type": "approval", "ts": "...", "render_check": "pass"}
```

`type` is `approval` (the default for lines without it), `rejection` (with `reason`) or `stale`
(with `superseded_by_sha256` and `superseded_by_render`). An approval stands until a later
rejection of its item or a later stale line for its SHA-256. A stale approval stays stale even if
the old bytes come back: re-approve.

`item_kind` says what was reviewed: `render` when absent (the skill's lines), `still` for an image
(G3), `plan_row` for one row of a plan table (G2), which carries `plan_file`, `plan_row` (the row's
text) and `plan_row_sha256` and leaves `render` and `render_sha256` null. Approvals, rejections and
stale marks act only within one kind, so rejecting a still does not unseat the render's approval,
and the status line's stale count is renders only.

## Time report

`reports/time.md` gives, per gate, per scene and per gate-and-scene: **wall** (start to finish),
**agent busy** (turn start to turn end), **idle** (no input or agent activity for the client's
`idle_minutes`, measured from the last activity), **waiting on client** (`waiting_on_<id>` where the id is the client's or listed in
`waiting_on_client_ids`), **waiting on others**, **paused**, **attended between turns** (observed
session time that is none of these) and **unobserved** (stage time when no ledger was recording).
Every number is a difference of recorded timestamps. Overlapping stages of one gate are counted
once. Open stages are listed and counted to the report time.

## Render check limits

- Dimensions, fps, frame count and alpha are checked only when the spec gives them; otherwise the
  check says "not checked" and why. Duration is checked against frames ÷ the stream's own rate.
- The flash scan decodes every frame, averages it down to a 96 × 54 grid of luma (and alpha when
  the file has alpha), and reports regions that change by at least 20 of 255 and return within 6 of
  255 one or two frames later, unless a lasting change lies within 12 cells (about 12% of the
  width), which reads as motion or a transition.
  - It found P1's one-frame website flash in `fd_S04_50ms_v08` (frame 2, the whole frame) and
    passed the fixed render. Across the 59 P1 v08 masters it also reported a two-frame dip of the
    "Schedule a visit" button in `fd_S04_character_v08` (frames 46–47), plus minor one-cell
    findings listed but not failed.
  - Findings under `flash.min_area_pct` (default 0.1% of the frame) are listed as minor and do not
    fail the check.
  - It can miss: low-contrast flashes (under 20/255 after averaging), flashes smaller than one grid
    cell that are averaged away, and a flash next to a lasting change.
  - It can over-report: an object that jumps more than about 12% of the frame width in one frame.
  - The first and last frame cannot be scanned (each lacks a neighbour on one side).
- The SHA-256 is of the file's bytes; any re-encode is a new render.

## Drift limits

- Text exports are compared by the hash prefix in each generated file's first line
  (`Generated from <page> (SHA-256 <hex>)`); files without that line are skipped.
- Skill comparison ignores macOS `._` files and `.DS_Store`.
- Rule IDs are found with the client's `rule_id_pattern`; a range written as `B-T1-01…05` is read
  as `B-T1-01` only.

## Render sentinel (`aem rendered`)

After every `Bash` call the agent makes while a project is active, the plugin sends the command to
`aem rendered`, which decides whether it was a render and checks what it wrote.

- **Is it a render?** It matches a render pattern: `hyperframes render`, `npx hyperframes render` and
  `remotion render` always, plus the client's `render_sentinel.command_patterns` in the registry
  (Joel: `bin/r.sh`, `bin/ra.sh`, `bin/renderall.sh`) and the project's in `aem.project.json`.
- **What did it write?** Media files (the client's `approval_gates.media_extensions`) found three ways:
  the value after `-o`, `--output` or `--out`; other media paths on the command line; and any media
  file under the output folders (`render_sentinel.output_dirs`, default `renders/`, searched
  recursively) whose modification time is at or after the command's start, less 2 seconds. An output
  value with `$` or `{` in it (a shell variable, a batch `{slug}`) adds its folder to the search.
  At most `max_outputs` (default 100) files are checked, the newest ones.
- **What happens** Each file goes through `check-render` (recorded as a `render_check` event, and
  earlier approvals of a changed render marked stale). The operator gets a toast: `PASS`/`FAIL` with
  the first reason for one file, counts for several, and the number of stale approvals. The agent
  reads the full result after the command's own output. The status line is redrawn, so its stale
  count is current.

Limits:

- A render run with `run_in_background` finishes after the call returns, so it is not checked; the
  toast and the agent's note say so, and the agent is told to run `aem check-render` itself.
- A render command the patterns do not match (an unlisted script, an alias, a render started
  inside another program) is not seen.
- Outputs are found by modification time, so a render written outside the output folders and
  not named on the command line is missed, and any other media file that changes under `renders/`
  while the command runs is checked too.
- The check blocks the agent until it finishes (up to 10 minutes): about a second per 4K scene on
  this machine; a full `renderall.sh` of 59 scenes adds about a minute.
- Every `Bash` call starts one `aem rendered` process (about 0.07 s) even when it is not a render,
  because the decision lives in the CLI, not the plugin.

## Review inbox (`aem inbox`)

Off unless the plugin's **Review inbox** setting is on (`reviewInbox`, default off). Then `/inbox`
opens a pane listing what waits on the operator. `aem inbox` decides the list; the pane only draws
it and runs the commands each item names.

| Item | Waiting when | Approve runs | Reject runs (asks for a reason) |
|---|---|---|---|
| Plan row (G2) | A row of a table in the plan files (`review_inbox.plan_files`, default `shotlist.md`; Joel also `visual-plan.md`) whose text has no approval or rejection. The row is named by its first cell. Changing an approved row's text puts it back, marked "changed since it was approved". | `aem approve <row> <file> --row <row> --gate G2 --label` | `aem reject <row> --path <file> --row <row> --gate G2 --label --reason …` |
| Still (G3) | An image under `stills/` (`review_inbox.stills_dirs`) whose SHA-256 has no ruling. | `aem approve <item> <file> --gate G3 --label` | `aem reject <item> --path <file> --gate G3 --label --reason …` |
| Render (G4) | A scene's last `render_check`, if the file is unchanged since and its SHA-256 has no ruling. Failed checks are listed with the failure. | `aem approve <scene> <file> --gate G4 --label` | `aem reject <scene> --path <file> --gate G4 --label --reason …` |
| Guard denial | A `denial` event from the last `denial_days` (default 2) not yet answered. | `aem allow <rule> --once --inbox-ref denial:<line> --label` ("Allow once") | `aem inbox dismiss denial:<line> --label --reason …` |
| Client comment | A draft from `aem import-review` (`reviews/<client>/*-labelled-cases.draft.jsonl`) not yet ruled on. Buttons Keep, Change, Remove. | `aem inbox accept <id> --ruling keep\|change\|remove --label` | `aem inbox dismiss <id> --label --reason …` |

Gates come from `review_inbox.gates`. A button whose command is not `approve`, `reject`, `allow` or
`inbox` is refused by the plugin.

**Labelled cases.** Every ruling made with `--label` appends one line to the client's
`critic/labelled-cases.jsonl`, in that file's own field names (read from its header line), with
`"source"` set to the operator's id (`"yuvraj"`). AEM adds `item_kind`, `gate`, `reason`, and where
they apply `decision`, `inbox_ref`, `rule`, `plan_file`, `plan_row`, `plan_row_sha256`,
`words_source`. These lines are `"status": "development case"`: they are the operator's rulings,
not the client's, so they never count toward the critic's labelled set (M-19), and the client's
words field stays null. An accepted client comment keeps the client's words verbatim from the CSV
(`words_source` says which rows), takes the shot's latest approved render's SHA-256, and is
`"labelled"` only when it has the ruling, the words and that SHA-256. `"ruling"` is `keep`
(approved) or `change` (rejected) for plan rows, stills and renders, the button's ruling for a
client comment, and null for a guard denial, whose `decision` is `allowed once` or `dismissed`.

Limits: the list is read when `/inbox` runs and after each button, not live; a plan table is
recognised only as a Markdown table with a header row; a still or render is matched by SHA-256, so
an identical file under another name counts as already ruled; the mobile app draws no text field,
so Reject there says to use `/reject` instead. Pressing a button is the operator's act inside the
pane; the agent cannot press it, and `aem inbox accept`/`dismiss` from the agent's shell is refused by
the CLI (see Operator-only commands).

## Guards (`aem guard`)

The plugin asks `aem guard` about every `Bash`, `Read`, `Write`, `Edit`, `MultiEdit`, `NotebookEdit`,
`Glob`, `Grep` and `LS` call, the agent's and its subagents', whether or not its own view shows a
project: the CLI resolves the project itself from the call's working folder (or `AEM_PROJECT`, or the
session pin), so there is no stored state for a session to trust or a test to overwrite (the plugin's
view, which draws the status line and the prompt section, is refreshed every 30 seconds). With no
project resolved the guard allows every call except a write into the operator-nonce folder. Every denial is appended to `events.jsonl` as a
`denial` event, and its message tells the agent why and how the operator can approve or override.
MCP tools are not checked.

| Rule | Denies | Limits |
|---|---|---|
| AEM-G01 protected file | `Write`/`Edit`/`NotebookEdit` to a protected file (the registry's `protected_files`, plus the registry itself), compared after resolving symbolic links; a `Write`/`Edit` into the operator-nonce folder `~/.aem/nonces/` even with no project resolved; a `Bash` command whose text names a protected file (by path or file name), except AEM's read-only commands. | A shell command is read as text: a path assembled at run time (`f=events; echo >> $f.jsonl`), a script file that writes the ledger, or an MCP tool that writes files is not seen. Reading with the `Read` tool is allowed; `cat` of a protected file is denied as a side effect. |
| AEM-G02 outside the client's folders | `Read`/`Write`/`Edit`/`Glob`/`Grep` of a path outside the active client's design system, its projects root, the active project, its audio libraries, the AEM repo, the registry's `shared_paths` and system folders (`/usr`, `/opt/homebrew`, `/tmp`, `/var/folders`, …); a `Bash` word that is such a path. | Only words that look like paths (`/…`, `~/…`, `./…`, `../…`) are checked. A command that reaches a file through a variable, a glob expanded later, `cd` then a relative path, or a program's own configuration is not seen. With no project resolved nothing is out of scope. |
| AEM-G03 blocked command | A `Bash` command containing one of the client's `blocked_commands` (`snapshot --describe` for Joel). | Plain text match: a different spelling or a script that runs it is not seen. |
| AEM-G05 render not approved | A `Bash` command matching the client's `approval_gates.command_patterns` (FCPXML, placement, delivery, Joel's "Animations Done") that names a render without a standing approval (missing, stale or rejected), or names an `.fcpxml` but no render; a `Write`/`Edit` of an `.fcpxml` whose content names such a render. | A placement step that reads its renders from a manifest the command does not name, or a pattern the registry does not list, is not checked. |

**There is no AEM-G04 any more** (the number is not reused). Until 0.8.0 the guard matched the text of a
shell command for the operator-only `aem` commands, which denied a commit message or a heredoc that
merely mentioned one and could not see a command spelled another way. The CLI now refuses those
commands itself, wherever they are run from (next section), so the guard no longer reads shell text for
them: a commit message, a heredoc, a grep or an echo that mentions `aem approve` is just text.

Overrides: `aem allow <target> --reason …` where the target is a rule ID (`AEM-G02`), a command
text or a path. `--once` (the default for `/allow`) is consumed by the next call it lets through and
logged as `allow_used`; a standing allow is logged on every use until `aem allow --revoke ID`.

If `aem` cannot start, the plugin lets the call through and toasts that it was not checked: the
guards fail open so a broken install does not stop work, and the toast says so every time.

These are recorded checks inside Claude Code and, once its hooks are set up, Codex; not security
boundaries. The operator's own shell, another editor, or Codex without the hooks is not checked.

## Operator-only commands

`use`, `stage` (every action), `approve`, `reject`, `client-said`, `allow`, `new-client`,
`inbox accept` and `inbox dismiss` change what the operator owns: approvals, rulings, overrides, the
ledger, the registry. **The CLI itself refuses them** unless the operator is shown to be running them,
checked at the entry of the command (and again inside the functions that write the records), so how the
command is spelled (a path, a wrapper, a script, `python3 -m aem`) does not matter. One of these must hold:

- **(a) Terminal.** `stdin` and `stdout` are a terminal, `/dev/tty` can be opened, and none of the agent
  markers is in the environment: `CLAUDECODE`, `AI_AGENT`, `CLAUDE_CODE_ENTRYPOINT`,
  `CLAUDE_CODE_SESSION_ID`, `CODEX_CI`, `CODEX_THREAD_ID`, `CODEX_SANDBOX`. For `client-said`, whose quote
  arrives on stdin, stdin need not be a terminal: type or paste the quote and press Control-D, or use
  `/client-said`. Output piped to another program (`aem approve … | tee`) is not a terminal.
- **(b) Plugin.** The plugin's slash-command handler makes a random one-time nonce, writes only its
  SHA-256 to `~/.aem/nonces/<hash>` with a 60-second expiry, and passes the nonce in
  `AEM_OPERATOR_NONCE` to that one `aem` call. `aem` checks the hash, deletes the file (so it works once),
  and removes the variable from its own environment so nothing it starts inherits it. The nonce is never
  written, logged or shown. The plugin also gives one to its own automatic ledger events (`stage auto`).

A refusal exits 2, says which command and why, and tells an agent to ask the operator. `status`,
`context`, `report`, `check-render`, `check-approval`, `import-review`, `inbox` (list), `drift`, `guard`,
`rendered`, `codex-config` and `codex-hook` are open.

**Verified on 6 October 2026** (the probe is `tests/live/tty-probe.py`):

| Where | stdin/stdout | `/dev/tty` |
|---|---|---|
| Claude Code's Bash tool, in the Claude desktop app | not terminals | cannot be opened (ENXIO) |
| Codex 0.146's shell (workspace-write sandbox) | not terminals | cannot be opened (not permitted) |
| The desktop app's Terminal panel, or a Terminal window | terminals | opens |
| A pseudo-terminal the agent's own shell allocates (`script`, Python's `pty`) | terminals | **opens** |

Neither agent's shell can open `/dev/tty`, so neither can pass (a) by itself. But the last row shows the
terminal test alone is not enough: an agent can allocate a pseudo-terminal and pass it. So (a) also
requires that none of the agent markers is set. They are set in the environment of the Claude Code Bash
tool (`CLAUDECODE`, `AI_AGENT`, `CLAUDE_CODE_*`) and of Codex's shell (`CODEX_CI`, `CODEX_THREAD_ID`,
`CODEX_SANDBOX`), a child process inherits them through `script` or `pty`, and the operator's own
terminal has none of them. Claude Code run as a CLI in a Terminal window was **not** observed: the
`claude` in that tab could not authenticate (its OAuth session had expired). Run `tests/live/tty-probe.py`
from inside such a session to see it.

**Limits. This is cooperative, not a security boundary.**

- An agent that removes the markers from its environment (`env -u`, `env -i`) and then allocates a
  pseudo-terminal passes (a). An agent whose shell can write a file can write a nonce hash file itself and
  pass (b): the guard denies its `Write` and `Edit` tools there, but not a shell redirect.
- A script that imports the `aem` package and sets its private flag passes the in-library backstop.
- What catches the result is the records themselves: ledgers are append-only, approvals carry the render's
  SHA-256, and Phase 4's integrity check compares them.
- The marker list is the markers observed today; another agent host that sets none would pass (a) from a
  pseudo-terminal.

## Codex (`aem codex-hook`)

OpenAI Codex 0.146 runs command hooks (feature `hooks`). `aem codex-config` prints a `[hooks]` table
for `~/.codex/config.toml` (or `--format json` for `~/.codex/hooks.json`) that sends six events to
`aem codex-hook`, which answers each with the same code the plugin calls:

| Codex event | AEM does | Codex reads back |
|---|---|---|
| `SessionStart` | records `session_start` (`agent: codex`) | the AEM context text as `additionalContext`, with a note that Codex has no slash commands |
| `UserPromptSubmit` | records `prompt` and `turn_start` | nothing |
| `PreToolUse` (`Bash`, `apply_patch`) | the guard: a Bash command as is; a patch as one `Write` per file it adds, updates, deletes or moves, with its added lines as content (so AEM-G05 sees FCPXML media) | `permissionDecision: "deny"` with the same message as the plugin's, or nothing |
| `PostToolUse` (`Bash`) | the render sentinel (`aem rendered`), timed from the PreToolUse of the same `tool_use_id`; a `tool_call` event when 30 s or more | the render result as `additionalContext` |
| `Stop` | records `turn_end` | nothing |
| `SessionEnd` | records `session_end` | nothing |

Verified live with codex-cli 0.146.0 (`tests/live/codex-hooks-check.sh`): the SessionStart hook
ran and the PreToolUse hook blocked an agent's `aem approve` with AEM-G04. The other events are
covered by unit tests built from the shapes in Codex's hooks reference.

Limits beyond the guards' own: Codex has no slash commands, toasts, status line or inbox, so the
operator runs `aem` commands in a terminal; there is no timer, so idle time is not detected live
(gaps appear in the report as unobserved); a hook needs the operator's trust in Codex's `/hooks`
review before it runs, and again after it changes; a project-level `.codex/hooks.json` was not
loaded by `codex exec` in testing, so install the hooks at user level; MCP tools are not checked;
and Codex treats a hook that fails or cannot start as allowing the call, as the plugin does.
