# The `aem` command

Reference for Aavkar Educational Motion Studio (AEM)'s command-line tool. Every command accepts
`--json` and then prints exactly one JSON object with an `ok` field. Exit codes: `0` success, `1` a
check ran and failed (approval missing or stale, render check failed, drift found), `2` a usage or
input error.

Commands act on the active project (`aem use`) unless `--client` and `--project` are given.
`--registry` picks another registry file; `aem use --registry` stores it in the active project so
later commands use the same one.

## Commands

| Command | What it does |
|---|---|
| `use <client>/<project> [--path DIR] [--fps N/D]` | Makes a project active: writes `~/.aem/active.json` (`AEM_HOME` overrides `~/.aem`). The project is found by registry entry, exact folder name, or a unique `NAME - ` prefix (`joel/P2` finds `P2 - Claude Code`); `--path` takes a folder anywhere (a test copy). |
| `status` | Client, project, fps, the open stage and its time, approvals (standing and stale), active overrides, the last render check, and the status-line text. |
| `stage start <gate> [scene] [--switch]` | Opens a stage. Gates come from the client's registry entry. `--switch` first finishes the stage open for the same scene (or the whole video); `/stage` always uses it. |
| `stage end [gate [scene]]` | Closes the named stage, or the most recently opened one. |
| `stage pause`, `stage resume` | Pause and resume the current stage. `resume` also ends a wait. |
| `stage wait <who>` | Work waits on someone: `waiting_on_<who>`. Waiting ends at the next start, finish or resume of that gate. `wait blocked` writes the skill's `blocked`. |
| `stage auto <event>` | Automatic events from the plugin: `session_start`, `session_end`, `prompt`, `turn_start`, `turn_end`, `tool_call` (with `--tool`, `--duration-s`), `idle_start` (with `--since`, the last activity's time), `idle_end`. `--session`, `--turn` and `--origin` record the Claude Code session, turn and prompt origin. |
| `report [--no-write]` | Writes `<project>/reports/time.md`. |
| `approve <item> <path> --gate G` | Appends an approval for that exact file's SHA-256. Operator only (the plugin refuses it from the agent). |
| `reject <item> --reason TEXT` | Appends a rejection; the item's earlier approval stops standing. Operator only. |
| `client-said --scope channel\|video\|instance --source TEXT [--item SHOT]` | Reads the client's words from standard input and adds a dated, verbatim entry to the client's decisions file, marked "entered by <operator>". Operator only. |
| `allow <rule-or-command> --reason TEXT [--once]` | An override the guards honour. `--once` is consumed by the next matching call. `--list`, `--revoke ID`. Operator only. |
| `check-approval <path> [--item] [--gate]` | Passes only if this file's SHA-256 has a standing approval. |
| `check-render <path> [--item] [--no-record]` | ffprobe against the project spec, a scan of every frame for one- and two-frame flashes, SHA-256, a `render_check` event, and stale marks on earlier approvals of the item. |
| `import-review <csv> [--fps N/D] [--start-tc TC] [--placements FILE]` | Maps a Frame.io comment export to frames, shots and word IDs. Writes review files and draft labelled cases; never edits the decisions file or the critic's file. |
| `drift [--client ID] [--skills-dir DIR]` | Text exports vs their HTML pages, installed skill vs master, and rule IDs in the skill vs the rules file. |
| `new-client <id> --name --design-system DIR --projects-root DIR [--contact] [--skill]` | Scaffolds a design system from `registry/client-template/` into a new or empty folder and adds a registry entry. |

## Frame rate

Never assumed. `aem use` reads every source the project has and refuses if they disagree or if
there is none:

1. `aem.project.json` `"fps": "24000/1001"`
2. FCPXML in the project (`*.fcpxml`, `out/`, `data/`, `*.fcpxmld/Info.fcpxml`): the sequence's
   format `frameDuration` (`1001/24000s` is 24000/1001)
3. `data/words.json` `fps_num`/`fps_den`
4. a HyperFrames `frame.md` `fps : "N/D"` line

`--fps N/D` overrides. The rate is stored as integers `num`/`den`. Decimal spellings (`23.976`) are
refused. Frame maths: `frame = round(seconds × num / den)`; timecode counts at the nominal rate
(24 for 24000/1001, 30 for 30000/1001, 25 for 25/1), with `;` drop-frame for 30000/1001 and
60000/1001.

## Project settings: `aem.project.json`

Optional, in the project folder.

```json
{
  "fps": "24000/1001",
  "render": {"width": 3840, "height": 2160, "alpha_extensions": [".mov"]},
  "scenes": {"fd_S01_next-token": {"composition": "compositions/next-token.html"}},
  "flash": {"min_area_pct": 0.1},
  "placements": "data/edit.json"
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
`allow_revoked`, `review_import`. Extra fields after the five: `source`, `session`, `tool`,
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
