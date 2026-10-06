# Operating Aavkar Educational Motion Studio

This is for whoever runs the studio: the person who briefs the agent, reviews its work and answers
to the client. Aavkar Educational Motion Studio (AEM) works in the background while you work with
the agent. These are the moments where you act.

## The idea in five lines

- A session works on **one project, the one it runs in**. Everything AEM records goes into that
  project's `events.jsonl` and `approvals.jsonl`. There is no global "active project" to forget to
  clear: the project comes from the folder you start in, or is pinned to one session with `/aem use`.
- Work moves through the client's **gates** (Joel's: G1 Inputs … G7 Joel's review). You open and
  close stages; AEM times them.
- An **approval** covers one exact render: its SHA-256. Change one byte and the approval is
  **stale**: placement and delivery refuse it until you approve again.
- **You decide, and AEM allows whatever you ask for in chat.** The client's records (their words,
  approvals, rejections, overrides, the critic's labelled cases) are written only by AEM's commands. You
  run them, or the agent runs them **because your latest message asked** ("approve fd_S01", "record what
  Joel said: …", "start G2"); each is recorded as done on your message. On its own initiative, or in a turn
  you did not start, the agent cannot (see below).
- Every check is a **recorded check, not a security boundary** (the limits are at the end).

## Starting a session

**Start Claude Code in the project's folder** (for P2: `…/Joel Belton - MergeToMaster/P2 - Claude Code`).
AEM finds the project from where the session runs, so there is nothing to type. At the start of every
session you get one toast:

```text
AEM 0.9.0 · joel/P2 · resolved from folder
AEM 0.9.0 · no project (folder not registered)
```

**No toast means the plugin is not loaded in that session** (not installed, disabled, or an older
version): nothing is guarded, timed or recorded, and `/aem`, `/stage` and `/approve` will not exist.
Fix that first. If you started somewhere else, pin the project to this one session:

```text
/aem use joel/P2
```

`/aem use --clear` drops the pin (the session goes back to its folder); other sessions and the
terminal are untouched. In a terminal, `AEM_PROJECT=joel/P2 aem status` does the same for one command.
`aem status` always says which project, which folder, which design system and frame rate, and *how* it
was resolved (environment, session pin, folder, flag or none).

The status line then reads, for example:

```text
AEM · MergeToMaster · P2 - Prompt Engineering · G4 fd_S01_next-token · 0:42 · 1 stale
```

That is: client · project · open gate and scene · time in that stage (`paused` or `waiting on joel`
when it is) · approvals made stale by a later render. With no project resolved the agent is told AEM
is loaded but idle, and nothing is guarded. `/aem status` prints the full state; `/aem use` also warns
if the design system's text exports or the installed skill have drifted from their masters.

A project in a temporary folder (`/tmp`, `/private/tmp`) or outside the client's folders is refused
with the reason: those are test copies, and only the test sandbox may use them.

The project's frame rate is read, never assumed (`aem.project.json`, the edit's FCPXML,
`data/words.json` or the HyperFrames `frame.md`); if they disagree, `/aem use` refuses and says
where. When the project states none, write it into the project's `aem.project.json`
(`"fps": "25/1"`), read from the edit itself. There is no `--fps` override.

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
| AEM-G01 protected file | writing the ledgers, the decisions file, the rules file, the critic's file, the registry or the operator-nonce folder | run the matching command yourself, or `/allow AEM-G01 <reason>` |
| AEM-G02 outside the client's folders | reading or writing outside the client's design system and projects, the AEM repository and the registry's shared tools | `/allow AEM-G02 <reason>`, or add the folder to `shared_paths` |
| AEM-G03 blocked command | a command the registry blocks for the client (Joel: `snapshot --describe`) | `/allow "snapshot --describe" <reason>` |
| AEM-G05 render not approved | placement, FCPXML or delivery naming a render without a standing approval | review, then `/approve` |

`/allow` is one-time by default (used up by the next matching call); add `--standing` to keep it
until `aem allow --revoke ID`. Every denial, allow and use is recorded in `events.jsonl`.

The guards read shell commands as text for the files and folders they protect. They miss a path
built at run time or a script that does the work, and they over-match: a command that only mentions
a protected file (a heredoc, a commit message) is blocked too. The agent is told to use the Read tool
to read protected files and the Edit tool for documents; if a harmless command is blocked, `/allow`
it once. (There is no longer a rule that reads text for *operator commands*: see the next section.) If `aem` cannot run at all, the plugin lets calls through and shows a toast every time:
fix the install rather than ignore it.

## Asking in chat (0.9.0)

AEM's first principle: **it allows whatever you ask for in chat.** Its guard and its operator-only commands
exist only to stop the agent acting on its own authority. When you have asked, the decision is yours; AEM
records it and never blocks it.

So you can just say it:

```text
approve fd_S01_next-token, the v09 render
start G4 for fd_S02_tokens
record what Joel said, his words: "Can we lose the caption under the button? It says what we can already see"
yes, add that note to events.jsonl by hand
```

What happens:

- When your message starts a turn, the plugin opens a **turn authority** for it and records your message,
  word for word, as an `operator_prompt` event in the project's `events.jsonl` (with its SHA-256, the
  session, the turn and the time). The plugin writes this, never the agent.
- During that turn the agent may run `aem approve`, `reject`, `client-said`, `stage`, `allow`, `use`,
  `accept-edit`, `inbox accept`/`dismiss`, `new-client`. Each record carries `via: "chat"`, your prompt's id
  and an excerpt, and you get a toast: `approve fd_S01_next-token via chat: 'approve fd_S01_next-token, the
  v09 render'`. The agent is told to run one only when your **latest** message asks for that action, to say
  what was recorded, and never to treat an earlier message as standing permission.
- **The client's words stay theirs.** `client-said` from chat is refused unless the quote appears verbatim in
  your message: "paste Joel's exact words in your message". Paste them; the agent cannot paraphrase into
  Joel's voice.
- **The guard never denies during your turn.** A call that would have been denied (a hand edit of a ledger,
  a folder outside the client's, a blocked command, a placement before approval) goes through, is logged as
  `allowed_by_operator_prompt` with the rule it would have hit and your prompt, and you get a toast
  (`AEM allowed Write on your message (AEM-G01 protected file would have denied it): '…'`).
- The authority ends when the turn ends, or after 60 minutes, whichever comes first.

**Not on your message** (an autonomous turn: a `/loop`, a schedule, a background task's notification, a
peer session's message, anything that did not start with you typing): no authority; the guard and the
commands' own checks apply exactly as before, and the agent has to ask you.

**Ledger integrity.** A hand-written or edited ledger line, even one you asked for, is flagged by
`aem integrity` (the status line shows `· 1 ledger edit to review`) until you accept it: say "accept that
edit" or type `/accept-edit <reason>`. It says whether each one came through on your message (and which) or
outside any recorded prompt; the latter is the case to look at.

## Why the agent cannot approve its own work

`approve`, `reject`, `client-said`, `allow`, `stage`, `use`, `new-client`, `accept-edit` and
`inbox accept`/`dismiss` are **refused by the `aem` command itself** unless you are the one running them:
from your own Terminal (a real terminal, not under an AI agent), through the plugin's slash command, which
hands that one call a one-time nonce that lasts 60 seconds, or on your message in chat (above). It does not matter how the agent spells the command
or what script it wraps it in. The old guard rule that matched the text of a command is gone, so a
commit message or a heredoc that mentions `aem approve` is just text.

This is cooperative, not a lock. A determined agent could strip the markers that tell `aem` it is an
agent and fake a terminal, or write a nonce file with a shell command. The ledgers are append-only with
hashes, so what it did shows. The details and the experiments behind this are in
[CLI.md](CLI.md#operator-only-commands).

## Codex

With the hooks installed (INSTALL.md), Codex gets the same context, guards, render checks and time
events. There are no slash commands, toasts, status line or inbox in Codex: run the commands in
your terminal (`aem use joel/P2`, `aem stage start G4 fd_S01_next-token`, `aem approve …`,
`aem client-said --scope video --source …` and then type or paste the words and press Control-D,
`aem allow …`, `aem inbox`, `aem report`). Start Codex in the project's folder so it resolves the project.
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
| No "AEM 0.9.0 · …" toast at session start | the plugin is not loaded in that session; check `claude plugin list` |
| A drift toast after `/aem use` | `aem drift` lists it: re-run the design system's text export, or reinstall the skill from its master |
| Codex does not block anything | check `/hooks` in Codex (hooks need your trust), then `tests/live/codex-hooks-check.sh` |
| The agent says "operator's command … the turn authority is unknown" after you asked it | the plugin is older than 0.9.0 (it opens no authority): update it (INSTALL.md, "Updating") and start a new session; meanwhile use the slash command |
| `aem integrity` flags a line | look at it: `aem integrity` says which prompt let it through, if any; accept it with `/accept-edit <reason>` or by asking |
| Slash commands refused: "operator's command … no operator nonce" | the plugin is older than the CLI (0.7.x cannot make nonces): update it (INSTALL.md, "Updating") and start a new session |
| Done for the day | `/stage end`. Nothing needs clearing: the next session resolves from its own folder |

Every command, file format and limit is in [CLI.md](CLI.md).
