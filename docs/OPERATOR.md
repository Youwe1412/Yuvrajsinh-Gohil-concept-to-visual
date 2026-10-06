# Operating Aavkar Educational Motion Studio

This is for whoever runs the studio: the person who briefs the agent, reviews its work and answers
to the client. Aavkar Educational Motion Studio (AEM) works in the background while you work with
the agent. These are the moments where you act.

## The idea in five lines

- One **active project** at a time. Everything AEM records goes into that project's
  `events.jsonl` and `approvals.jsonl`.
- Work moves through the client's **gates** (Joel's: G1 Inputs … G7 Joel's review). You open and
  close stages; AEM times them.
- An **approval** covers one exact render: its SHA-256. Change one byte and the approval is
  **stale**: placement and delivery refuse it until you approve again.
- Only **you** write the client's records: their words, approvals, rejections, overrides and the
  critic's labelled cases. The agent can read them but not write them, and is told so.
- Every check is a **recorded check, not a security boundary** (the limits are at the end).

## Starting a session

```text
/aem use joel/P2
```

The status line then reads, for example:

```text
AEM · MergeToMaster · P2 - Prompt Engineering · G4 fd_S01_next-token · 0:42 · 1 stale
```

That is: client · project · open gate and scene · time in that stage (`paused` or `waiting on joel`
when it is) · approvals made stale by a later render. With no project active the agent is told AEM
is loaded but idle, and only the operator-only-command guard applies. `/aem status` prints the
full state; `/aem use` also warns if the design system's text exports or the installed skill have
drifted from their masters.

The project's frame rate is read, never assumed (`aem.project.json`, the edit's FCPXML,
`data/words.json` or the HyperFrames `frame.md`); if they disagree, `/aem use` refuses and says
where. Give it with `--fps 24000/1001` when the project states none.

## Time per gate

| You type | It records |
|---|---|
| `/stage G2` | G2 starts for the whole video |
| `/stage G4 fd_S01_next-token` | G4 starts for that scene (finishing that scene's open stage) |
| `/stage end` | the open stage finishes |
| `/wait joel` | the work waits on Joel (counted as waiting on the client) |
| `/pause`, `/resume` | a break that is nobody's work |
| `/report` | writes `reports/time.md` |

The plugin adds the rest by itself: session start and end, each of your prompts, each agent turn,
tool calls of 30 seconds or more, and **idle** (no prompt and no agent activity for the client's
`idle_minutes`, Joel's 10), measured from the last activity. The report shows, per gate and scene,
wall time, agent busy, idle, waiting on the client, waiting on others, paused, attended between
turns, and time nothing observed; it explains how each number was computed. It is for planning the
next video, not for billing.

## Renders

When the agent renders (`hyperframes render`, or a script the registry lists, for Joel `bin/r.sh`,
`bin/ra.sh` and `bin/renderall.sh`), AEM finds the files it wrote and checks each one: size, frame
rate, constant frame rate, frame count against the composition's duration, alpha, and a scan of
every frame for one- and two-frame flashes. You get a toast (`AEM render check FAIL: x.mp4: flash at
frame 2 …`), the agent gets the full result, and the result and SHA-256 go into `events.jsonl`. A
render that replaces an approved one marks that approval stale at once, and the status line counts
it.

Check any file yourself with `aem check-render <path>`. A render run in the background is not
checked automatically; the agent is told to check it when it finishes.

## Approving and rejecting

| You type | It does |
|---|---|
| `/approve fd_S01_next-token` | approves the item's last checked render at the open gate |
| `/approve fd_S01_next-token renders/v09/fd_S01_next-token_v09.mp4 G6` | a specific file and gate |
| `/reject fd_S01_next-token the cursor lands two frames late` | rejects it, with your reason, word for word |

Before placing a render in the client's timeline or delivering it, the agent must pass
`aem check-approval <path>`, and AEM blocks any placement, FCPXML or delivery command that names a
render without a standing approval (AEM-G05). Approve again after any re-render.

## The client's words

```text
/client-said video --source "Frame.io, 6 Oct" Can we lose the caption under the button? It says what we can already see
```

AEM adds a dated entry to the client's decisions file (Joel's `joel-decisions.md`), newest first,
quoting exactly what you typed after the options (or the text you selected in the transcript, if
you type nothing), marked as entered by you. Scope is `channel`, `video` or `instance` (with
`--item SHOT`). Paste the client's own words; never paraphrase into their voice.

For a Frame.io review, export the comments as CSV and run `aem import-review <csv>`: it maps each
comment to its frame, shot and word IDs at the reviewed file's frame rate and writes review files
and **draft** labelled cases under `reviews/<client>/`. It never edits the decisions file or the
critic's file; you rule on each draft (below).

## The review inbox (optional)

Turn on the plugin setting **Review inbox** (`reviewInbox`). Then `/inbox` opens a pane of
everything waiting on you: plan rows (G2, from `shotlist.md`), stills (G3, under `stills/`),
checked renders (G4), guard denials you have not answered, and imported client comments. Each has
buttons: Approve (or Allow once, or Keep / Change / Remove for a client comment) and Reject, which
asks for a reason. Every ruling also goes into the client's `critic/labelled-cases.jsonl` with
`"source": "yuvraj"` (the operator's id) as a **development case**: your rulings help calibrate the
critic, but only the client's own rulings, in their words, count toward its labelled set.

## When AEM blocks the agent

The agent sees which rule, why, and what you can do; you get a toast. The rules:

| Rule | Blocks | You can |
|---|---|---|
| AEM-G01 protected file | writing the ledgers, the decisions file, the rules file, the critic's file, AEM's own state or the registry | run the matching command yourself, or `/allow AEM-G01 <reason>` |
| AEM-G02 outside the client's folders | reading or writing outside the client's design system and projects, the AEM repository and the registry's shared tools | `/allow AEM-G02 <reason>`, or add the folder to `shared_paths` |
| AEM-G03 blocked command | a command the registry blocks for the client (Joel: `snapshot --describe`) | `/allow "snapshot --describe" <reason>` |
| AEM-G04 operator-only command | the agent running `aem approve`, `reject`, `client-said`, `allow`, `use`, `new-client`, `stage`, `inbox accept`/`dismiss` or the hook commands | run it yourself |
| AEM-G05 render not approved | placement, FCPXML or delivery naming a render without a standing approval | review, then `/approve` |

`/allow` is one-time by default (used up by the next matching call); add `--standing` to keep it
until `aem allow --revoke ID`. Every denial, allow and use is recorded in `events.jsonl`.

The guards read shell commands as text. They miss a path built at run time or a script that does
the work, and they over-match: a command that only mentions a protected file or an operator
command (a heredoc, a commit message) is blocked too. The agent is told to use the Read tool to
read protected files and the Edit tool for documents; if a harmless command is blocked, `/allow`
it once. If `aem` cannot run at all, the plugin lets calls through and shows a toast every time:
fix the install rather than ignore it.

## Codex

With the hooks installed (INSTALL.md), Codex gets the same context, guards, render checks and time
events. There are no slash commands, toasts, status line or inbox in Codex: run the commands in
your terminal (`aem use joel/P2`, `aem stage start G4 fd_S01_next-token`, `aem approve …`,
`aem client-said --scope video --source … < words.txt`, `aem allow …`, `aem inbox`, `aem report`).
Idle time is not detected live in Codex (it has no timer); gaps show in the report as unobserved.

## New client

```bash
aem new-client acme --name "Acme Learning" --design-system "/path/to/00 - Acme Design System" --projects-root "/path/to/Acme"
```

Then fill in the registry entry (gates, protected files, blocked commands, render scripts, idle
time) and the client's rules and decisions files. Nothing else needs to change.

## Troubleshooting

| You see | Do |
|---|---|
| Toast "AEM guard could not run" | `aem` is missing or broken: `aem --version`, then `cli/install.sh` |
| The status line lags a change made elsewhere | it re-reads `aem status` every 30 seconds; guards and render checks always ask the CLI directly, so they never lag |
| A drift toast after `/aem use` | `aem drift` lists it: re-run the design system's text export, or reinstall the skill from its master |
| Codex does not block anything | check `/hooks` in Codex (hooks need your trust), then `tests/live/codex-hooks-check.sh` |
| Done for the day | `/stage end`, then `/aem use --clear` if you want no project active |

Every command, file format and limit is in [CLI.md](CLI.md).
