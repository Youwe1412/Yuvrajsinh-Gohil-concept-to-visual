# Aavkar Educational Motion Studio

> **P2 delivered, accepted and paid, 23 Oct 2026; published on MergeToMaster, 24 Oct 2026.** The final Claude Code video:
> **[I Used Claude Code Every Day for a Year. Here’s What I Learnt](https://www.youtube.com/watch?v=-daz-uPJ53Q)** (YouTube, 11:06). Delivered on Frame.io as `P2 - Claude Code Done.mov`, 3840×2160, 25 fps: [f.io/dBF09OXt](https://f.io/dBF09OXt).
> Joel's review, 19 Oct 2026, on WhatsApp: "Hi, no I think its all ready to go :) happy for you to send me the invoice".
> No change requests and no comments on the Frame.io share page; on 17 Oct: "the intro is absolutely awesome".
> Paid on 23 Oct 2026: GBP 220.08 from Joel Belton (Infinity receipt). Proof, hashes and
> what AEM did not record: [docs/p2-review](docs/p2-review/README.md).

> **Capstone status, 9 Oct 2026** (snapshot first taken 7 Oct) (100x Engineers C7, "Concept to Visual"): the case study is
> [docs/CASE-STUDY.md](docs/CASE-STUDY.md); the whole picture of AEM is [docs/ABOUT.md](docs/ABOUT.md);
> P2's hypothesis is [docs/P2-HYPOTHESIS.md](docs/P2-HYPOTHESIS.md), copied from P2's `HYPOTHESIS.md`
> (SHA-256 `95c1003974d4885d961471dbbfce4470f6a11bfbd63d7821eb0215115ec484c2`, recorded in P2's `inputs.md`);
> P2's measured state is [docs/P2-STATUS.md](docs/P2-STATUS.md) (34 of 35 visual moments built, 72 render checks);
> the animations themselves, as AEM's evidence frames show them, are in [docs/showcase](docs/showcase/README.md).
> Demo: the P1 video delivered to Joel (the submitted link) and the P2 showcase with 1080p proxies ([docs/showcase](docs/showcase/README.md)).
> The same workflow on two other creators, anonymized: [CASE-STUDY §j](docs/CASE-STUDY.md#j-beyond-joel-the-same-workflow-on-two-other-creators-outside-the-measured-run). Updated after Joel's Frame.io review.
>
> **P2 outcome, 23 Oct 2026:** delivered 15 Oct with 45 moments; Joel accepted it with no changes on WhatsApp
> (17 and 19 Oct: "the intro is absolutely awesome"), and paid on 23 Oct. What it changed in AEM (`accept-video
> latest`, moments read only from moment tables, a quieter sentinel, craft baseline A-27…A-34):
> [ABOUT §13.6](docs/ABOUT.md#136-what-joels-review-of-p2-showed-23-october-2026).

> **AEM observes and records. It never blocks work in a session the operator is sitting in. The record
> is the product: Joel's rulings in his words, approvals tied to the exact render, the critic's
> labelled cases, time per stage. The only interruption is a confirmation before delivering a render
> that has no current approval.**

Aavkar Educational Motion Studio (AEM) is a client-agnostic notary for educational animation work. It
stands beside the work, records what happened and who decided it, measures time, checks every render,
and never stands in the way. Three jobs, in order: **remember** (the client's rulings in their words,
approvals tied to the exact render, the critic's labelled cases, every tool call; a new session starts
with `aem recall`), **measure** (time per stage, waits, idle, turns; a stage is inferred when none was
opened) and **check** (every render as it is made, the ledgers' integrity, drift, the install).

Since 1.1.0 the record also helps the agent do its best work for each client: each placement is a
**moment** (`aem moments`: its words, teaching job, whether the client asked for it, its contract,
renders, approval and ruling); each render comes with **evidence** the agent can look at (`aem
evidence`: readable poses, phone crops, a strip around the fastest transition, sync in frames); and the
client's rulings, at the level they gave them, are recorded (`import-review`, `client-said --about`,
`accept-video`) and reported (`aem calibrate`) without changing a rule.

AEM has two parts:

- **`aem`**, a command-line tool that holds all the logic. Python 3 standard library only, plus
  `ffprobe` and `ffmpeg` for render checks. Every command takes `--json`.
- **A Claude Code plugin**, `aavkar-educational-motion-studio`, that only does what needs a mod:
  the session context and recall, automatic time events and a status line, recording each tool call,
  the render sentinel, the delivery confirmation, and an optional review inbox. It calls `aem` for
  every decision; no business logic lives only in the plugin.

OpenAI Codex (0.146 and later) gets the same context, record and render sentinel through its command
hooks, which call `aem codex-hook`. It has no slash commands, status line, dialog or inbox: in Codex
the operator runs `aem` commands in a terminal.

Nothing about a client is in the code. Names, paths, gates, approval and delivery patterns, render
scripts and idle time come from `registry/clients.json`. The first client is Joel Belton's
MergeToMaster.

## What AEM is not

AEM does not stop an agent that wants to misbehave; it makes the misbehaviour visible in the record.
The only commands an agent cannot run are the ones that write the record (`approve`, `reject`,
`client-said`, `stage`, `accept-edit`, `accept-video`, `new-client`, `inbox accept`/`dismiss`), and the CLI refuses
those itself; a ledger line written any other way stays flagged by `aem integrity` until the operator
accepts it. Nothing outside Claude Code and Codex is observed, and if `aem` cannot run, everything goes
through and the plugin says so. The limits of each part are in [docs/ABOUT.md](docs/ABOUT.md#9-limits-exactly).

## Start here

- [docs/ABOUT.md](docs/ABOUT.md): the whole picture: why, every part, how it should be used,
  limits, and where things stand.
- [docs/INSTALL.md](docs/INSTALL.md): install the command, the plugin (as a marketplace) and the
  Codex hooks.
- [docs/OPERATOR.md](docs/OPERATOR.md): day-to-day use, on one page.
- [docs/CLI.md](docs/CLI.md): every command, every file format and the limits of each check.

## Layout

| Path | Holds |
|---|---|
| `cli/` | The `aem` package (`cli/aem/`), its launcher (`cli/bin/aem`) and `install.sh` |
| `plugin/aavkar-educational-motion-studio/` | The Claude Code plugin: `hooks/` (one module, `register.tsx`, dispatching to `context`, `ledger`, `observe`, `record`, `sentinel`, `inbox`), `types/`, `tests/` |
| `.claude-plugin/marketplace.json` | Makes this repository a Claude Code plugin marketplace (`aavkar-productions`) |
| `registry/` | `clients.json` and `client-template/`, the files a new client needs |
| `docs/` | `ABOUT.md` (the whole picture), `INSTALL.md`, `OPERATOR.md`, `CLI.md` |
| `tests/` | CLI unit tests; `acceptance/` (the end-to-end run's operator steps and placement stand-in); `live/codex-hooks-check.sh`, `live/tty-probe.py` |

## Tests

```bash
tests/run.sh
```

runs the CLI unit tests (`python3 -m unittest discover -s tests -t tests`) and the plugin's tests
(`claude plugin test plugin/aavkar-educational-motion-studio`) against a sandbox: a fresh temp
`AEM_HOME` and a temp copy of the registry with every client's folders moved inside it
(`tests/isolation.py`). It fails if `~/.aem` or `registry/clients.json` changed during the run;
`tests/test_zz_isolation.py` makes the same check at the end of a bare `unittest` run. The
acceptance script (`tests/acceptance/operator.sh init`, then `<step> <sandbox>`) and
`tests/live/codex-hooks-check.sh` run only against such a sandbox.

## Files AEM writes

AEM extends the `mergetomaster-studio` skill's formats rather than forking them:

- `<project>/events.jsonl`: the skill's `{ts, gate, scene, event, note}` lines, plus AEM's own
  events (pause, resume, session and turn events, idle, inferred stages, one `observed` event per tool
  call, render checks, approvals, delivery outcomes, inbox rulings, accepted edits, and `choice`: a
  decision the agent made where the brief and the client's rulings left a gap, with `why`, `rule_ids`
  and `alternatives`, written by `aem chose`).
- `<project>/approvals.jsonl`: the skill's approval line, field for field, plus `type`
  (`approval`, `rejection`, `stale`), `ts`, `via` (terminal, slash command or delivery confirmation)
  and `item_kind` (render, still, plan row). Lines are only ever appended.
- `<project>/reports/time.md`: the time report.
- `<project>/reports/rounds.md`: each moment's versions side by side (`aem rounds`), derived, rebuilt each time.
- `<project>/reviews/<moment>/<version>/`: evidence (`evidence.md`, poses, phone crops, `strip.jpg`,
  `sync.json`, `facts.json`, `holds.json`, `sheet.jpg`, `retell.md`); the critic and the sound-off
  reader write `critic.json` and `retell.json` beside it.
- `<project>/reviews/<client>/`: imported review comments and drafts.
- The client's decisions file: only through `aem client-said`, verbatim, marked with who typed it.
- The client's `critic/labelled-cases.jsonl`: only through `--label` on an approval or rejection
  (the review inbox), in the file's own field names, `"source"` the operator's id.
- `.aem-integrity/` beside each of those ledgers: the hash of every line AEM wrote, for `aem integrity`.
