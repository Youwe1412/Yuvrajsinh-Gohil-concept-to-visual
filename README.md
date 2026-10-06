# Aavkar Educational Motion Studio

Aavkar Educational Motion Studio (AEM) is a client-agnostic production layer for educational
animation work. It keeps the ledgers a studio skill asks for (time per gate, approvals tied to the
exact render, the client's own words) and runs the checks that should happen before a render is
placed or delivered.

AEM has two parts:

- **`aem`**, a command-line tool that holds all the logic. Python 3 standard library only, plus
  `ffprobe` and `ffmpeg` for render checks. Every command takes `--json`.
- **A Claude Code plugin** (in `plugin/`, built in later phases) that only does what needs a mod:
  session context, automatic time events, tool-call guards, a render sentinel and a review inbox.
  The plugin calls `aem` for every decision; no business logic lives only in the plugin.

Nothing about a client is in the code. Names, paths, protected files, blocked commands, gates and
idle time come from `registry/clients.json`. The first client is Joel Belton's MergeToMaster.

## What AEM is not

These are **recorded checks inside Claude Code, not security boundaries.** A shell can get around a
path check, anyone with the drive can edit a ledger, and Codex does not load Claude Code mods. AEM
keeps an honest record and stops the common mistakes; it does not stop a determined person.

## Layout

| Folder | Holds |
|---|---|
| `cli/` | The `aem` package (`cli/aem/`), its launcher (`cli/bin/aem`) and `install.sh` |
| `registry/` | `clients.json` and `client-template/`, the files a new client needs |
| `plugin/` | The Claude Code plugin (later phases) |
| `docs/` | `CLI.md` (every command and file format); install and operator guides come with packaging |
| `tests/` | Unit tests (`python3 -m unittest discover -s tests -t tests`) |

## Install the command

```bash
cli/install.sh
```

This links `cli/bin/aem` into `~/.local/bin` (pass another folder as the first argument). It refuses
to replace an `aem` that is not this one.

## Quick start

```bash
aem use joel/P2                      # make a project active (~/.aem/active.json)
aem stage start G1                   # time per gate goes to the project's events.jsonl
aem check-render renders/x_v01.mp4   # probe, flash scan, SHA-256, stale approvals
aem approve x renders/x_v01.mp4 --gate G4
aem check-approval renders/x_v01.mp4
aem report                           # reports/time.md
```

See [docs/CLI.md](docs/CLI.md) for every command, the file formats and the limits of each check.

## Files AEM writes

AEM extends the `mergetomaster-studio` skill's formats rather than forking them:

- `<project>/events.jsonl`: the skill's `{ts, gate, scene, event, note}` lines, plus AEM's own
  events (pause, resume, session and turn events, idle, render checks, approvals, overrides).
- `<project>/approvals.jsonl`: the skill's approval line, field for field, plus `type`
  (`approval`, `rejection`, `stale`) and `ts`. Lines are only ever appended.
- `<project>/reports/time.md`: the time report.
- `<project>/reviews/<client>/`: imported review comments and drafts.
- The client's decisions file: only through `aem client-said`, verbatim, marked as entered by the
  operator.
