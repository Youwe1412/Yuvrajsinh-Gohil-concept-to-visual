# Aavkar Educational Motion Studio

Aavkar Educational Motion Studio (AEM) is a client-agnostic production layer for educational
animation work. It keeps the ledgers a studio skill asks for (time per gate, approvals tied to the
exact render, the client's own words, the critic's labelled cases) and runs the checks that should
happen before a render is placed or delivered.

AEM has two parts:

- **`aem`**, a command-line tool that holds all the logic. Python 3 standard library only, plus
  `ffprobe` and `ffmpeg` for render checks. Every command takes `--json`.
- **A Claude Code plugin**, `aavkar-educational-motion-studio`, that only does what needs a mod:
  the session context, automatic time events and a status line, tool-call guards, a render
  sentinel, and an optional review inbox. It calls `aem` for every decision; no business logic
  lives only in the plugin.

OpenAI Codex (0.146 and later) gets the same guards, context, render sentinel and time events
through its command hooks, which call `aem codex-hook`. It has no slash commands, status line or
inbox: in Codex the operator runs `aem` commands in a terminal.

Nothing about a client is in the code. Names, paths, protected files, blocked commands, gates,
render scripts and idle time come from `registry/clients.json`. The first client is Joel Belton's
MergeToMaster.

## What AEM is not

These are **recorded checks inside Claude Code (and Codex, once its hooks are set up), not
security boundaries.** A shell command is read as text, so a script or a path built at run time can
get around a check; anyone with the drive can edit a ledger; nothing outside those two agents is
checked; and if `aem` cannot run, the checks fail open and say so. AEM keeps an honest record and
stops the common mistakes; it does not stop a determined person. Each guard's exact limits are in
[docs/CLI.md](docs/CLI.md#guards-aem-guard).

## Start here

- [docs/ABOUT.md](docs/ABOUT.md): the whole picture: why, every part, how it should be used,
  limits, and where things stand.
- [docs/INSTALL.md](docs/INSTALL.md): install the command, the plugin (as a marketplace) and the
  Codex hooks.
- [docs/OPERATOR.md](docs/OPERATOR.md): day-to-day use, for whoever runs the studio.
- [docs/CLI.md](docs/CLI.md): every command, every file format and the limits of each check.

## Layout

| Path | Holds |
|---|---|
| `cli/` | The `aem` package (`cli/aem/`), its launcher (`cli/bin/aem`) and `install.sh` |
| `plugin/aavkar-educational-motion-studio/` | The Claude Code plugin: `hooks/` (one module, `register.tsx`, dispatching to `context`, `ledger`, `guard`, `sentinel`, `inbox`), `types/`, `tests/` |
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
  events (pause, resume, session and turn events, idle, render checks, approvals, denials,
  overrides, inbox rulings).
- `<project>/approvals.jsonl`: the skill's approval line, field for field, plus `type`
  (`approval`, `rejection`, `stale`), `ts` and `item_kind` (render, still, plan row). Lines are
  only ever appended.
- `<project>/reports/time.md`: the time report.
- `<project>/reviews/<client>/`: imported review comments and drafts.
- The client's decisions file: only through `aem client-said`, verbatim, marked as entered by the
  operator.
- The client's `critic/labelled-cases.jsonl`: only through `--label` on an approval or rejection
  (the review inbox), in the file's own field names, `"source"` the operator's id.
