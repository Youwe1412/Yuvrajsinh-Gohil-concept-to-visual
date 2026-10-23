# The `aem` command

Reference for Aavkar Educational Motion Studio (AEM)'s command-line tool. Every command accepts
`--json` and then prints exactly one JSON object with an `ok` field. Exit codes: `0` success, `1` a
check ran and failed (approval missing or stale, render check failed, drift found, ledger edits found),
`2` a usage or input error.

AEM observes and records; it never blocks work. Commands act on the project they run for, which comes
from where they run (see [Which project](#which-project)); `--client` and `--project` override it.
`--registry` picks another registry file. The commands that write the record are the operator's alone
and refuse to run for anyone else (see [Operator-only commands](#operator-only-commands)); every other
command is open, to the agent too.

## Which project

There is no global "active project". Every `aem` call resolves its project, in this order:

1. `AEM_PROJECT=<client>/<project>` in the environment of that process.
2. The Claude Code plugin's **session pin**: set by `/aem use` for that one session, and passed to
   every `aem` call the plugin makes as `AEM_PROJECT` (with `AEM_PROJECT_SOURCE=session-pin`, so
   `aem status` can say it is a pin).
3. The **working directory**: the registered project (the registry's `projects`) whose folder
   contains it, the longest match winning; else the client whose design system contains it (a
   client, no project).
4. **Nothing.** Commands that need a project say so and how to give one; observation, the ledger,
   the render sentinel and the context then do nothing.

`--client`/`--project` on a command override the project and `aem status` says so. `aem observe` and
the Codex hook use the working directory of the call they record. `aem status` always shows the
project, its folder, the design system, the frame rate and the registry, and how each was found.

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
| `use <client>/<project>` | Checks that the project resolves (registry entry, exact folder name, or a unique `NAME - ` prefix: `joel/P2` finds `P2 - Claude Code`), has a stated frame rate and may be used, and writes the last-used hint (`AEM_HOME` overrides `~/.aem`). It changes nothing a command trusts. In Claude Code, `/aem use` runs it and then pins the project to that session. `use --clear` forgets the hint (`/aem use --clear` drops the session pin). There is no `--path` and no `--fps`: a project is its registered folder, and its frame rate is what the folder states. |
| `status` | The project, its folder, design system, fps and registry, and **how each was resolved**; the open stage (and whether AEM inferred it) and its time, approvals (standing and stale), ledger edits to review, the last render check, and the status-line text. With no project resolved, it says so and shows the last-used hint, labelled. |
| `recall [client]` | One screen on a client for a new session: how the client reviews (the registry's `review_profile`), how much they directed the last video and this one, what they changed last time (explicit changes on the latest earlier video that has any, by treatment and teaching job, in their words; our note, labelled as ours, where their words were never recorded), their channel-level rulings (newest first), their standing preferences (the rules file's rows with the client's `preference_prefix`, Joel's `J-`), the last five rulings in the decisions file, quoted in the client's own words and cut with an ellipsis where long, the open questions for the client (the decisions file's "Open questions" section), and the critic's labelled-case count. Read-only. The plugin shows it at session start. |
| `context` | The text the Claude Code plugin adds to the system prompt: the principle, the project, three rules for the agent, and `recall`. |
| `stage start <gate> [scene] [--switch]` | Opens a stage. Every `stage` action is operator only, including the plugin's `stage auto`, which the plugin runs with a nonce. Gates come from the client's registry entry. `--switch` first finishes the stage open for the same scene (or the whole video); `/stage` always uses it. Any stage AEM inferred finishes first ("superseded"). |
| `stage end [gate [scene]]` | Closes the named stage, or the most recently opened one. |
| `stage pause`, `stage resume` | Pause and resume the current stage. `resume` also ends a wait. |
| `stage wait <who>` | Work waits on someone: `waiting_on_<who>`. Waiting ends at the next start, finish or resume of that gate. `wait blocked` writes the skill's `blocked`. |
| `stage auto <event>` | Automatic events from the plugin: `session_start`, `session_end` (which also finishes any stage AEM inferred), `prompt`, `turn_start`, `turn_end`, `tool_call` (with `--tool`, `--duration-s`), `idle_start` (with `--since`, the last activity's time), `idle_end`. `--session`, `--turn` and `--origin` record the Claude Code session, turn and prompt origin. |
| `report [--no-write]` | Writes `<project>/reports/time.md`: per gate, scene, stage group and moment. |
| `approve <item> [path] [--gate G] [--row NAME] [--label] [--delivery-confirmation]` | Appends an approval for that exact file's SHA-256. Without a path, the item's most recently checked render; without a gate, the open stage's. An image is approved as a still; `--row` approves one row of a plan table in `path`. `--label` also appends the ruling to the client's labelled cases. `--delivery-confirmation` is what the plugin runs when the operator presses Deliver (see [Delivery confirmation](#delivery-confirmation)). Operator only. |
| `reject <item> --reason TEXT [--path FILE [--row NAME]] [--gate G] [--label]` | Appends a rejection: of that file (or plan row) when given, else of the item's latest approved render, whose approval stops standing. Operator only. |
| `client-said --scope channel\|video\|instance --source TEXT [--item SHOT]` | Reads the client's words from standard input and adds a dated entry to the client's decisions file: the quote exactly as typed, and who typed it and how ("typed by Yuvraj with /client-said in Claude Code" or "in a terminal"). Operator only. |
| `client-said --about MOMENT\|video\|channel [--ruling keep\|change\|remove] --source TEXT` | The same entry (the scope follows from `--about`), and the quote as the client's ruling at that level in the labelled cases: on a moment, an explicit ruling (with `--ruling`; without one, a remark, not a ruling) carrying the moment's latest render SHA-256; on the video or the channel, a remark at that level. What `--about` names is checked before anything is written. Words the decisions file already quotes (whitespace aside; 20 characters or more) are not written again: the ruling names the entry that has them (`decisions_entry`). See [Rulings](#rulings-and-calibration). Operator only. |
| `accept-video <version> --source TEXT` | The client accepted the delivered video: an implicit acceptance (`ruling: accepted`, `level: implicit`, the render's SHA-256 at that version) for every moment with no explicit keep, change or remove. Once per version. Operator only. |
| `accept-video latest --source TEXT [--before FILE\|DATETIME]` | The same, for a video whose moments went out at different versions (P2: v01 to v06): each moment's newest render (highest version), its version recorded per case. `--before` counts only renders no newer than the delivered master (its modification time, 2 s slack, resolved from the working folder or the project) or an ISO date-time. Run again later, it writes only the moments whose newest render changed. Operator only. |
| `inbox [list]`, `inbox accept <id> --ruling keep\|change\|remove\|note [--label]`, `inbox dismiss <id> --reason TEXT [--label]` | What waits on the operator, each item with the exact commands its buttons run; see Review inbox below. `accept` and `dismiss` are operator only. |
| `check-approval <path> [--item] [--gate]` | Passes only if this file's SHA-256 has a standing approval; `state` says `approved`, `stale`, `rejected`, `none` or `missing`. |
| `check-render <path> [--item] [--no-record]` | ffprobe against the project spec, a scan of every frame for one- and two-frame flashes, loudness and true peak when the render carries sound, SHA-256, a `render_check` event, and stale marks on earlier approvals of the item. |
| `import-review <csv> [--fps N/D] [--start-tc TC]` | Maps a Frame.io comment export to frames, moments and word IDs: a comment on a moment is a candidate for the client's explicit ruling; one on no moment is a remark about the video. Writes review files and draft labelled cases for the inbox; never edits the decisions file or the critic's file. |
| `import-review <csv> --notes [--fps N/D] [--start-tc TC]` | The client's timestamped notes on a rough cut: direction, not rulings. Kept as `reviews/<client>/<date>-notes.csv` and `.json`; the moments they cover become "asked". |
| `moments [--no-write]` | Builds `moments/index.json` (see [Moments](#moments-aem-moments)) and prints the table. |
| `evidence <render> [--moment ID] [--cue WORD_ID]… [--cue-at SECONDS]…` | Images, sync and facts a critic can read, for one render (see [Evidence](#evidence-aem-evidence)). The sentinel runs it after every render. Open. |
| `evidence <cut> --video [--offset SECONDS]` | One contact sheet per moment from the assembled cut, and `video.md`. |
| `chose "<what>" --why "<reason>" [--moment ID] [--rule ID]… [--alt TEXT]…` | Records a decision of ours where the brief, the plan and the client's rulings left a gap: a `choice` event in `events.jsonl`. `moments` attaches choices to their moment; `calibrate` counts the client's changes that rest on one. Open. |
| `rounds [--moment ID] [--no-write]` | Each moment's versions side by side from `reviews/`: render check, flashes, sync, frozen holds, the critic's verdict, which findings each version fixed, kept or brought back, and the sound-off read. Writes `reports/rounds.md`. Open. |
| `calibrate [client]` | What the client's rulings say: acceptance per video, critic agreement, rules (see [Calibration](#rulings-and-calibration)). Read-only. |
| `observe` | Records one tool call, read as JSON on stdin (`{tool, input, cwd, session, agent}`), and says whether it delivers media with no current approval. Never refuses. The plugin runs it before every `Bash`, `Read`, `Write`, `Edit`, `MultiEdit` and `NotebookEdit` call; see [Observation](#observation). |
| `rendered` | Checks the renders a finished shell command wrote, read as JSON on stdin (`{command, cwd, started_at, exit_code, probe_only}`). Runs `check-render` on each and returns a toast line and a note for the agent. The plugin runs it after every `Bash` call; see Render sentinel below. |
| `integrity` | Compares each ledger with what AEM wrote and lists every line AEM did not write, with the agent's observed calls that wrote that file. Exit 1 when there is any. See [Ledger integrity](#ledger-integrity). |
| `accept-edit [--file NAME] [--reason TEXT]` | Accepts what `integrity` found (all ledgers, or one), recording an `edit_accepted` event, and re-baselines. Operator only. |
| `drift [--client ID] [--skills-dir DIR]` | Text exports vs their HTML pages, installed skill vs master, and rule IDs in the skill vs the rules file. |
| `doctor` | Is AEM installed and able to record here? Read-only checks, each ok, warn or fail: this command and its Python; `ffmpeg`/`ffprobe` on PATH; the registry loads and each client's folders can be read (a drive mounted); the project resolved here and its frame rate; the plugin installed for this user (`~/.claude/plugins/installed_plugins.json`, or `AEM_CLAUDE_DIR`) has this command's version; the nonce folder can be written; integrity and drift for the resolved client. Exit 1 when a check fails. |
| `new-client <id> --name --design-system DIR --projects-root DIR [--contact] [--skill]` | Scaffolds a design system from `registry/client-template/` into a new or empty folder and adds a registry entry. Operator only. |
| `codex-hook` | Answers one OpenAI Codex hook event (JSON on stdin, one JSON object out); see Codex below. |
| `codex-config [--format toml\|json]` | Prints the hook configuration that makes Codex call `codex-hook`, with the absolute path of the installed `aem`. |

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
  "render_sentinel": {"command_patterns": ["\\bbin/render\\.sh\\b"], "output_dirs": ["renders"]},
  "stage_inference": {"scene_dirs": ["src", "compositions"]},
  "moments": {"plan_files": ["visual-plan.md"], "shotlist_files": ["shotlist.md"]},
  "evidence": {"max_per_command": 6, "max_still_s": 0.5, "max_frozen_per_30s": 1.0,
               "references": ["references/*.png", "references/*.jpg"]},
  "loudness": {"target_lufs": -14, "tolerance_lu": 1.0, "max_true_peak_db": -1.0}
}
```

`moments`, `evidence` and `loudness` override the client's registry settings of the same name (below).
With no `loudness.target_lufs` anywhere, integrated loudness is measured and shown but not checked; the
true-peak ceiling (default −1 dBTP) is checked whenever the render has an audio stream.

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
events above, `stage_inferred` (a gate AEM opened itself: `inferred: true`, `inferred_from` the file),
`observed` (one per tool call: `tool`, `command`, `reads`, `writes`, `paths`, `delivery`, `session`,
`agent`), `render_check`, `approval`, `rejection`, `client_said` (with `about` and `ruling` when given),
`review_import`, `notes_import`, `evidence` (`evidence`: the path of `evidence.md`), `evidence_video`,
`labelled_case` (`case_id`, `level`, `ruling`), `video_accepted` (`version`, `implicit`, `explicit`),
`inbox_resolved`, `edit_accepted`, and the delivery outcomes `delivery_stopped`, `delivery_held` and
`delivery_unconfirmed`. Extra fields after the five: `source`, `session`, `tool`, `duration_s`,
`render`, `render_sha256`, `result`, `via`, `inferred`, `backfilled`. Events entered with `--at` carry
`"backfilled": true` and the report counts them.

### approvals.jsonl

```json
{"gate": "G4", "scene": "fd_S01_next-token", "render": "renders/v09/fd_S01_next-token_v09.mp4", "render_sha256": "<64 hex>", "source_revision": "<git commit, or sha256: of the scene source>", "approver": "Yuvraj", "date": "2026-10-06", "type": "approval", "ts": "...", "render_check": "pass", "via": "slash command"}
```

`type` is `approval` (the default for lines without it), `rejection` (with `reason`) or `stale`
(with `superseded_by_sha256` and `superseded_by_render`). An approval stands until a later
rejection of its item or a later stale line for its SHA-256. A stale approval stays stale even if
the old bytes come back: re-approve. `via` says how the operator made it: `terminal`, `slash command`
or `delivery confirmation` (then `note` says Deliver was pressed).

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
once. Open stages are listed and counted to the report time. Stages AEM inferred are counted like
any other and listed under "Inferred stages" with the file that started each.

**Per stage group and per moment** (1.1.0). The client's `stage_groups` (Joel: design G1–G3, build G4,
review G5 and G7, placement G6) sum the gates' time. A stage's time belongs to a moment only when the
stage names it (`/stage G4 fd_S01_next-token`); whole-video stages, and scenes that name no moment, are
reported as unattributed, never spread across moments.

### Inferred stages

If no stage is open when the agent changes a plan file (`review_inbox.plan_files` and
`style-guide.md`: G2), a still (under `stills/`: G3), a scene source (any file under `src/` or
`compositions/`: G4) or a render (media under `renders/`, or what a render command wrote: G4), AEM
records `stage_inferred` for that gate (scene: the whole video), flagged as inferred, so a forgotten
`/stage` loses no time. The gates are the client's `review_inbox.gates` (plan row, still, render); the
folders can be set per client or project under `stage_inference` (`plan_files`, `stills_dirs`,
`scene_dirs`, `render_dirs`, `gates`). An inferred stage ends when the operator starts any stage
(`finish`, "superseded by stage start …") or when the session ends (Codex: its SessionEnd). Nothing is
inferred while any stage is open. The status line shows it: `G4 (inferred)`.

## Observation

`aem observe` records every tool call the plugin sends it (before the call runs) as an `observed`
event in the project's `events.jsonl`, and never refuses one:

| Tool | Recorded |
|---|---|
| `Bash` | `command` (the first 500 characters; `command_chars` when longer), `paths` (words that name files: absolute, `~`, `./`, `../`, relative words with a `/`, names with an extension; an XPath `//asset` or a URL is not one), `writes` (redirect targets, `-o`/`--output` values, `cp`/`mv`/`rsync`/`ditto`/`install`/`ln` destinations, `tee`, `touch`, `rm`, `sed -i` files), and `delivery` when it is one |
| `Read` | `reads` |
| `Write`, `Edit`, `MultiEdit`, `NotebookEdit` | `writes`, and `delivery` for an `.fcpxml` that names media |

Paths are shown relative to the project inside it, `~/…` under the home folder, else absolute, as
the call named them (symbolic links are not resolved for the record). A shell command is split the way
a shell splits it, so `ls ~/Tools/fcp-edit-workflow;` names the folder, not the folder and a `;`, and
a comment after `#` is not a word. With no project resolved nothing is recorded. `aem observe` is open:
it only records.

**Limits.** Parsing is text: a path built at run time (`$F`, a glob) is recorded as written; a script
that writes files it does not name, or a program's own configuration, is not seen; MCP tools are not
observed. The record keeps the command itself, so a person can read what was run.

## Delivery confirmation

The only interruption AEM makes. A call is a **delivery** when it is not a read (a command made only
of programs that read, such as `cat`, `grep`, `unzip`, `xmllint`, `ffprobe`, `aem check-approval`, or
inline Python with no write in it, never is), names media that exists, and:

- writes an FCPXML (an `.fcpxml` word, a `Write`/`Edit` of an `.fcpxml`, inline code that writes one), or
- copies or moves media into a delivery folder (a destination matching the client's
  `approval_gates.delivery_patterns`, by default its `command_patterns`; Joel's include `Animations Done`
  and `deliver(y)`), or
- matches one of the client's `approval_gates.command_patterns` (placement, delivery).

The media checked is what the command names, less what it writes (a copy's destination, an `-o`
output). When any of it has no current approval (none, re-rendered after its approval, or rejected),
`observe` answers with the question and the approvals that would answer it:

```json
{"delivery": {"kinds": ["copy"], "question": "fd_S01 was re-rendered after you approved it. Deliver anyway?",
  "unapproved": [{"item": "fd_S01", "path": "renders/fd_S01_v02.mp4", "state": "stale"}], "gate": "G6",
  "approve": [["approve", "fd_S01", "/…/renders/fd_S01_v02.mp4", "--gate", "G6", "--delivery-confirmation"]],
  "slash": ["/approve fd_S01 renders/fd_S01_v02.mp4 G6"]}}
```

The plugin shows the question in the engine's dialog with **Deliver** and **Stop**:

| Answer | What happens |
|---|---|
| Deliver | The plugin runs each `approve … --delivery-confirmation` with a one-time nonce (the operator's answer), recorded with `via: "delivery confirmation"`, then the call runs. If an approval cannot be recorded, the call still runs and `delivery_unconfirmed` says why. |
| Stop (or the dialog is dismissed) | The call is refused; the agent is told the operator stopped it and not to deliver another way. `delivery_stopped` is recorded. |
| No dialog can be shown (a `-p` run: no surface) | The call is refused once with the exact `/approve` command to type (`delivery_held`). The identical call repeated goes through and is recorded as `delivery_unconfirmed`. |

The approval gate is the client's deliver gate (the gate whose name contains "deliver", Joel's G6),
else the open stage's. A delivery of approved media asks nothing; the `observed` event still records
its media and their state. Codex shows no dialog: its hook records the delivery and asks nothing.

**Limits.** A placement tool that reads its renders from a manifest the command does not name, or a
delivery folder no pattern matches, is not seen as a delivery; a read is recognised by program name and
flags, so a script *file* is not known to only read.

## Render check limits

- Loudness is EBU R128 through ffmpeg's `ebur128` filter (`peak=true`) on the first audio stream:
  integrated loudness in LUFS, loudness range in LU, true peak in dBTP. A render with no audio stream says
  "not checked: no audio stream", which is right for inserts that ship silent with their cues as
  separate clips. Loudness of a short clip is measured over the clip, not the finished programme.

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
  (Joel: `bin/r.sh`, `bin/ra.sh`, `bin/renderall.sh`) and the project's in `aem.project.json`. A pattern
  counts only in a simple command that runs something: one whose program only reads or prints
  (`head bin/r.sh`, `grep … bin/r.sh`, `git diff bin/r.sh`, a `for f in … bin/r.sh` list) is not a render,
  and here-document bodies (`python3 - <<'EOF' … EOF`) are data, not commands (since 23 October 2026).
- **What did it write?** Media files (the client's `approval_gates.media_extensions`) found three ways:
  the value after `-o`, `--output` or `--out`; other media paths on the command line; and any media
  file under the output folders (`render_sentinel.output_dirs`, default `renders/`, searched
  recursively) whose modification time is at or after the command's start, less 2 seconds. An output
  value with `$` or `{` in it (a shell variable, a batch `{slug}`) adds its folder to the search.
  At most `max_outputs` (default 100) files are checked, the newest ones.
- **What happens** If no stage is open, AEM first infers the render gate (G4). Each file goes through
  `check-render` (recorded as a `render_check` event, and earlier approvals of a changed render marked
  stale). The operator gets a toast: `PASS`/`FAIL` with the first reason for one file, counts for
  several, the number of stale approvals, and `· G4 inferred` when it opened the stage. The agent reads
  the full result after the command's own output. The status line is redrawn, so its stale count is
  current. Nothing is ever blocked: a failed check is information for the agent and the operator.
- **Evidence.** Then `aem evidence` runs on each checked render (at most `evidence.max_per_command`, 6
  for Joel): the operator gets `evidence ready: <moment> v<n>, …` and the agent reads the path of each
  `evidence.md` after the check.

Limits:

- A render run with `run_in_background` finishes after the call returns, so it is not checked; the
  toast and the agent's note say so, and the agent is told to run `aem check-render` itself.
- A render command the patterns do not match (an unlisted script, an alias, a render started
  inside another program) is not seen.
- Outputs are found by modification time, so a render written outside the output folders and
  not named on the command line is missed, and any other media file that changes under `renders/`
  while the command runs is checked too.
- The check makes the agent wait until it finishes (up to 10 minutes): about a second per 4K scene on
  this machine; a full `renderall.sh` of 59 scenes adds about a minute.
- Every `Bash` call starts one `aem rendered` process (about 0.07 s) even when it is not a render,
  because the decision lives in the CLI, not the plugin.

## Moments (`aem moments`)

A moment is one thing placed in the cut, the unit the client reviews and the work is planned, built and
timed by. `aem moments` writes `moments/index.json`:

| Field | From |
|---|---|
| `id`, `index`, `start`, `end` | the plan's rows (`visual-plan.md`, `shotlist.md`: first cell the moment), else the placements (`data/edit.json`, `data/placements.json`, `renders/*/PLACEMENTS.csv`; the client's `moments.placement_files`, the project's `placements` first). The client's own footage is not a moment of ours unless `include_footage_placements` |
| `word_ids`, `word_span` | the plan's word-ID column, else the words of `data/words.json` inside the placement |
| `job`, `why`, `treatment` (animation, footage, screen recording, nothing), `cues`, `rule_ids`, `scene` | the plan's columns, by header name |
| `contract` | `knows_before`, `knows_after`, `must_stay_true`, `accuracy_limit` (where the picture stops being accurate): the shot list's columns |
| `asked`, `asked_from`, `notes` | the plan's "asked or added" column; else **note coverage**: asked when one of the client's notes (`import-review --notes`) lies within `review_profile.note_window_s` (1 s) of the moment's words, or a note's range overlaps them; else added. With no notes, every moment is added and the index says so in `note` |
| `renders` (version, path), `approval` (gate, standing) | `renders/` by item name and version; `approvals.jsonl` |
| `ruling` | the client's ruling at its level from the labelled cases: explicit (keep, change, remove) over implicit (accepted). A remark with no keep, change or remove is not a ruling; the operator's rulings never count |
| `critic` | `reviews/<moment>/<version>/critic.json` (`verdict`, `findings`), written by the critic |
| `time` | stages that name the moment (wall, agent busy, idle…) |

The index also carries `direction` (`full notes` when the notes cover at least half the moments,
`partial`, `none`; or as stated in `review_profile.direction`), `asked`, `added`, the notes that cover no
moment (`video_notes`), `unattributed_time`, and `unlinked`: everything it could not link (a render that
belongs to no moment, a moment with no render for its asset, a moment with no words and no placement, a
labelled case or approval that names no moment), which the command prints. On P1: 58 moments (8
placements are Joel's footage), 66 notes covering 50 of them, 8 added; unlinked: one render no
placement uses (`fd_title-average-question_alpha_v08.mov`).

Limits: a plan is read only as Markdown tables with a header row; a column is found by its header
words; a moment's words come from the placement's times when the plan names none, so they are as good
as `data/words.json`; "asked" is a matter of time, so a moment we added over footage the client asked
for at that time counts as asked (P1's `teach-*` inserts are) unless the plan's "asked or added" column
says otherwise.

## Evidence (`aem evidence`)

What a render looks like, written for Claude to read. For one render, in `reviews/<moment>/<version>/`:

| File | Holds |
|---|---|
| `poses/fNNNN.png`, `phone/fNNNN.png` | one per readable pose (the frame the picture settles on after each cue word, plus the first and last frame), 1920 px wide, and the same at 390 px, a phone held upright. At most 16 |
| `strip.jpg` | eight frames around the fastest transition, side by side (480 px each) |
| `sync.json` | per cue word: its onset frame, the frame the picture starts to change, the frame it settles, and the offset in frames (settle − onset) |
| `facts.json` | the render check: spec, frame count, flashes (frame, area, severity), SHA-256 |
| `holds.json` | every run of frozen frames (each repeats the one before it, under 0.03 grey levels per pixel at 160 × 90), its first and last frame, length and where it sits (start, middle, end); frozen seconds per 30 s; the runs longer than `evidence.max_still_s` (0.5 s) and whether frozen time is over `evidence.max_frozen_per_30s` (1 s) |
| `sheet.jpg`, `retell.md` | the render at 2 frames a second (at most 24, evenly spaced), tiled, 320 px each, no sound; and the only file a sound-off reader is given: open the sheet, nothing else, and write `retell.json` (`retell`, `unclear`) |
| `evidence.md` | all of it with relative paths, the moment's contract, the rule IDs it speaks to (the client's `evidence.rules`), holds, the sound-off read, reference frames for the director's review (the project's files matching `evidence.references`, at most 6) and how to report; a critic subagent given this file alone has everything, and is told not to read the scene source |

Cue words come from `--cue-at` (seconds into the scene, for hand-measured onsets), `--cue` (word IDs),
the plan's cue column, or, when none is written, are inferred from motion (each movement paired with the
moment's nearest word), and `evidence.md` says which. The toast quotes a sync offset only for real cue
words: `evidence ready: fd_S04_50ms v09, sync max offset 2f, no flash`, or `no cue words, sync not
measured`. A readable pose is a run of at least a quarter second in which the mean grey change per
pixel (160 × 90) stays under 0.08.

`--video` reads the assembled cut and writes `reviews/video/<cut>/NNN-<moment>.jpg`, six frames across
each moment's word span, and `video.md`.

**Cost, measured** on the 59 P1 v08 masters (423.6 s of 3840 × 2160 at 24000/1001): 120 s in all;
1.37 s per render (median, 9.9 s the most); 2.4 s per 10 s of scene for MP4 (median; 5.1 s the most, a
1.3 s title where start-up dominates); 11.9–15.4 s per 10 s for the four ProRes 4444 alpha MOVs, whose
decode is slower. The P1 film (11:24 at 1080p) gave 58 contact sheets in 8.2 s. Those figures predate `sheet.jpg`
(17 October 2026), which adds one more decode: about a quarter more (3.4 → 4.3 s on the 4K test scene). It runs after the
render has finished and is advisory: it blocks nothing and is never a gate.

`critic.json` keeps `verdict` and `findings` as before and adds `retell_match` (`yes`, `partly`, `no`,
`no target`) and `director` (the reference comparisons, or null). Neither changes the verdict.

Holds, the sound-off read and the director's review are advice: nothing fails because of them and the
toast does not mention them. The frozen threshold is uncalibrated: it was set on synthetic clips, not on
P1's renders; a very slow drift of a small element can read as frozen, and encoder noise can make a
true hold read as moving. Text contrast is not measured (AEM has no text geometry); the critic judges it
on the phone crops.

Limits: the poses are found by stillness, so a scene that never holds still for a quarter second has
only its first and last frame; inferred cue words are guesses and are labelled so; sync is measured
against the picture settling, not against a particular element; the strip is around the largest change,
which may be a cut rather than the transition that matters.

## Rulings and calibration

The client's rulings, at the level they were given (the registry's `review_profile` says how the client
reviews; Joel reviews the finished video, never individual animations):

| Level | What | Written by |
|---|---|---|
| `explicit` | a comment on one moment: `keep`, `change` or `remove`, in the client's words | `inbox accept` of an imported comment; `client-said --about <moment> --ruling …` |
| `implicit` | the video accepted with no comment on the moment: `accepted` | `accept-video`, once the whole video is accepted; silence is never written as explicit |
| `video` | a remark about the video as a whole | `inbox accept --ruling note` of a comment on no moment; `client-said --about video` |
| `channel` | a remark about the editor or how to work for the channel | `client-said --about channel` |

Each is a line in the client's `critic/labelled-cases.jsonl`, in that file's field names (`case_id`,
`status`, `video`, `shot`, `word_ids`, `render_sha256`, `ruling`, `joel_words`, `ruling_date`, `source`,
`rule_ids`, `critic_verdict_g5`, `critic_agreed`, `notes`), plus AEM's: `moment`, `level`, `asked`
(`asked` or `added`), `direction`, `version`, `critic_findings`. `status` is `labelled` only for an
explicit keep, change or remove with the client's words and the render's SHA-256.

`aem calibrate [client]` reads every registered project's moments and the labelled cases, and prints:

- **Acceptance per video:** moments delivered, explicitly changed, explicitly kept, implicitly
  accepted, not ruled; then `N of M additions changed, K of L asked`, and the same by treatment and by
  teaching job.
- **Critic agreement:** for ruled moments with a `critic.json` on the version the client saw: changed
  and flagged (hits), changed but not flagged (misses), accepted but flagged (false alarms), and a
  weighted agreement in which an explicit ruling weighs 1 and an implicit acceptance 0.25. With no
  critic findings it says "untested".
- **Rules:** per rule ID, the rulings that involve it (the moment's rule IDs, the case's, the critic's
  findings), how many the client's words confirm and how many overrule the critic, or untested. An
  inferred or unconfirmed rule that rulings now support or contradict is printed as a proposed line of
  the rules file with the decisions-file entry it rests on. AEM never edits the rules file.

Under 30 explicit cases (M-19) every figure carries its count and "development data, not evidence";
with no rulings it says so and stops. Operator rulings are counted apart and left out; a remark with no
keep, change or remove is counted as a remark. On P1 after `accept-video v08`: 3 explicit, 55 implicit;
`0 of 8 additions changed, 3 of 50 asked`; M-26 and B-29 "suggested by rulings, unconfirmed".

Limits: "asked" is note coverage (see Moments); the critic can be scored only where it wrote
`critic.json`; a rule is linked to a ruling only through rule IDs someone wrote down (the case, the
plan, the critic); one video's rulings say little about the next.

## Review inbox (`aem inbox`)

Off unless the plugin's **Review inbox** setting is on (`reviewInbox`, default off). Then `/inbox`
opens a pane listing what waits on the operator. `aem inbox` decides the list; the pane only draws
it and runs the commands each item names.

| Item | Waiting when | Approve runs | Reject runs (asks for a reason) |
|---|---|---|---|
| Plan row (G2) | A row of a table in the plan files (`review_inbox.plan_files`, default `shotlist.md`; Joel also `visual-plan.md`) whose text has no approval or rejection. The row is named by its first cell. Changing an approved row's text puts it back, marked "changed since it was approved". | `aem approve <row> <file> --row <row> --gate G2 --label` | `aem reject <row> --path <file> --row <row> --gate G2 --label --reason …` |
| Still (G3) | An image under `stills/` (`review_inbox.stills_dirs`) whose SHA-256 has no ruling. | `aem approve <item> <file> --gate G3 --label` | `aem reject <item> --path <file> --gate G3 --label --reason …` |
| Render (G4) | A scene's last `render_check`, if the file is unchanged since and its SHA-256 has no ruling. Failed checks are listed with the failure. | `aem approve <scene> <file> --gate G4 --label` | `aem reject <scene> --path <file> --gate G4 --label --reason …` |
| Client comment | A draft from `aem import-review` (`reviews/<client>/*-labelled-cases.draft.jsonl`) not yet ruled on: one per moment with its comments (Keep, Change, Remove), one per comment on no moment (Record, a remark about the video). | `aem inbox accept <id> --ruling keep\|change\|remove\|note --label` | `aem inbox dismiss <id> --label --reason …` |

Gates come from `review_inbox.gates`. A button whose command is not `approve`, `reject` or `inbox` is
refused by the plugin.

**Labelled cases.** Every ruling made with `--label` appends one line to the client's
`critic/labelled-cases.jsonl`, in that file's own field names (read from its header line). A ruling
on a plan row, still or render is the operator's: `"source"` is the operator's id (`"yuvraj"`), `"level"`
is `"operator"`, and AEM adds `item_kind`, `gate`, `reason`, and where they apply `decision`,
`inbox_ref`, `plan_file`, `plan_row`, `plan_row_sha256`. These lines are `"status": "development
case"`: they are ours, not the client's, so they never count toward the critic's labelled set (M-19) or
in `calibrate`, and the client's words field stays null. An accepted client comment is the client's
ruling at its level (see [Rulings](#rulings-and-calibration)): the words verbatim from the CSV,
`"source"` the CSV rows they came from, `"ruled_by"` the operator who read them, the moment's approved
render's SHA-256 (or, with no approval, its latest render's), and `"labelled"` only when it has an
explicit keep, change or remove, the words and that SHA-256. `"ruling"` is `keep` (approved) or `change` (rejected) for plan
rows, stills and renders, and the button's ruling for a client comment.

Limits: the list is read when `/inbox` runs and after each button, not live; a plan table is
recognised only as a Markdown table with a header row; a still or render is matched by SHA-256, so
an identical file under another name counts as already ruled; the mobile app draws no text field,
so Reject there says to use `/reject` instead. Pressing a button is the operator's act inside the
pane; `aem inbox accept`/`dismiss` from the agent's shell is refused by the CLI (next section).

## Operator-only commands

`approve`, `reject`, `client-said`, `stage` (every action), `accept-edit`, `accept-video`, `new-client`,
`inbox accept` and `inbox dismiss` write the record: approvals, rulings, the client's words, stages, accepted ledger
edits, the registry. They are the only commands the agent cannot run, and the only ones that matter,
because they are what makes the record the operator's. **The CLI itself refuses them** unless the
operator is shown to be running them, checked at the entry of the command (and again inside the
functions that write the records), so how the command is spelled (a path, a wrapper, a script,
`python3 -m aem`) does not matter. One of these must hold:

- **(a) Terminal.** `stdin` and `stdout` are a terminal, `/dev/tty` can be opened, and none of the agent
  markers is in the environment: `CLAUDECODE`, `AI_AGENT`, `CLAUDE_CODE_ENTRYPOINT`,
  `CLAUDE_CODE_SESSION_ID`, `CODEX_CI`, `CODEX_THREAD_ID`, `CODEX_SANDBOX`. For `client-said`, whose quote
  arrives on stdin, stdin need not be a terminal: type or paste the quote and press Control-D, or use
  `/client-said`. Output piped to another program (`aem approve … | tee`) is not a terminal.
- **(b) Slash command.** The plugin's slash-command handler (and the delivery confirmation's Deliver)
  makes a random one-time nonce, writes only its SHA-256 to `~/.aem/nonces/<hash>` with a 60-second
  expiry, and passes the nonce in `AEM_OPERATOR_NONCE` to that one `aem` call. `aem` checks the hash,
  deletes the file (so it works once), and removes the variable from its own environment so nothing it
  starts inherits it. The nonce is never written, logged or shown. The plugin also gives one to its own
  automatic ledger events (`stage auto`).

A refusal is one line, exit 2: "`aem approve` is the operator's command, run from their terminal or its
slash command, and this process is neither (…): ask the operator to run it." The agent then asks the
operator in one sentence and carries on once they have run it. Approvals, rejections, the client's words
and accepted edits say how they were made: `via` is `terminal`, `slash command` or `delivery confirmation`.

**Verified on 6 October 2026** (the probe is `tests/live/tty-probe.py`):

| Where | stdin/stdout | `/dev/tty` |
|---|---|---|
| Claude Code's Bash tool, in the Claude desktop app | not terminals | cannot be opened (ENXIO) |
| Codex 0.146's shell (workspace-write sandbox) | not terminals | cannot be opened (not permitted) |
| The desktop app's Terminal panel, or a Terminal window | terminals | opens |
| A pseudo-terminal the agent's own shell allocates (`script`, Python's `pty`) | terminals | **opens** |

Neither agent's shell can open `/dev/tty`, so neither can pass (a) by itself; a pseudo-terminal the
agent allocates passes the terminal test, which is why (a) also requires that none of the agent markers
is set (a child process inherits them through `script` or `pty`; the operator's own terminal has none).

**This is not a lock.** An agent that strips the markers and allocates a pseudo-terminal, or writes a
nonce hash file with a shell command, passes. AEM does not stop an agent that wants to misbehave; it
makes it visible: the observed tool calls show the command it ran, and `aem integrity` shows any ledger
line written outside `aem`.

## Ledger integrity

`events.jsonl`, `approvals.jsonl`, the client's decisions file and `critic/labelled-cases.jsonl` are
AEM's ledgers. Every line AEM writes to one also goes, in the same locked write, into a manifest beside it
(`.aem-integrity/<file>.jsonl`): a 16-hex-digit SHA-256 of the line (or, for an entry `client-said`
inserts in the decisions file, the inserted lines and where). `aem integrity` compares each file with its
manifest and reports:

| Finding | Means |
|---|---|
| `inserted` | lines AEM did not write (hand-written, pasted, written by a script) |
| `edited` | lines AEM wrote that now read differently |
| `removed` | lines AEM wrote that are gone |

Each finding says whether AEM observed the agent writing that file (`observed_writes`: an observed
`Write`/`Edit` of it, or a shell command naming it that is not a read, with the time, tool and session)
or not ("an edit outside the agent": an editor, a terminal, another tool). Findings stay until
`aem accept-edit` (operator only), which appends an `edit_accepted` event (file, lines, examples,
reason, the observed writes) and re-baselines that file. `aem status` and the status line count the
findings (`· 2 ledger edits to review`), and the agent's context tells it about them. This is the
whole safeguard: detection, not prevention.

The first time AEM writes a file that has no manifest, the lines already in it become the baseline,
trusted as they stand: AEM cannot tell an older hand-written line from its own. Until then `integrity`
says "no baseline yet". Limits: the manifest is beside the ledger, so whoever rewrites one consistently
with the other is not caught; a line identical to one AEM wrote cannot be told apart from it; the rules
file is not a ledger and is not tracked.

## Codex (`aem codex-hook`)

OpenAI Codex 0.146 runs command hooks (feature `hooks`). `aem codex-config` prints a `[hooks]` table
for `~/.codex/config.toml` (or `--format json` for `~/.codex/hooks.json`) that sends six events to
`aem codex-hook`, which answers each with the same code the plugin calls. It keeps context, ledger
events and the render sentinel; it never denies a call.

| Codex event | AEM does | Codex reads back |
|---|---|---|
| `SessionStart` | records `session_start` (`agent: codex`) | the AEM context text (principle, project, recall) as `additionalContext`, with a note that Codex has no slash commands or delivery dialog |
| `UserPromptSubmit` | records `prompt` and `turn_start` | nothing |
| `PreToolUse` (`Bash`, `apply_patch`) | `observe`: an `observed` event (a patch's files as `writes`; its added lines checked for FCPXML media), and an inferred stage when none is open. A delivery is recorded with its media's approval state, not asked about | nothing |
| `PostToolUse` (`Bash`) | the render sentinel (`aem rendered`), timed from the PreToolUse of the same `tool_use_id`; a `tool_call` event when 30 s or more | the render result as `additionalContext` |
| `Stop` | records `turn_end` | nothing |
| `SessionEnd` | records `session_end` and finishes any stage AEM inferred | nothing |

Verified live with codex-cli 0.146.0 (`tests/live/codex-hooks-check.sh`, at 0.8.0): the SessionStart
hook ran and the agent's `aem approve` was refused by the CLI itself. The other events are covered by
unit tests built from the shapes in Codex's hooks reference.

Limits: Codex has no slash commands, toasts, status line, inbox or dialog, so the operator runs `aem`
commands in a terminal and a delivery is never asked about; there is no timer, so idle time is not
detected live (gaps appear in the report as unobserved); a hook needs the operator's trust in Codex's
`/hooks` review before it runs, and again after it changes; a project-level `.codex/hooks.json` was not
loaded by `codex exec` in testing, so install the hooks at user level; MCP tools are not observed; and
Codex treats a hook that fails or cannot start as allowing the call, as the plugin does.
