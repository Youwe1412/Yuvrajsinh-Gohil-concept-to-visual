# Installing Aavkar Educational Motion Studio

Aavkar Educational Motion Studio (AEM) is two pieces: the `aem` command, which makes every
decision, and a Claude Code plugin that calls it. Codex can call it too, through hooks. Install the
command first; the plugin and the hooks do nothing without it.

## What you need

| Need | Version used to build and test AEM |
|---|---|
| macOS (Linux should work; not tested) | macOS 26 (Darwin 25.5) |
| Python 3 (standard library only) | 3.11.1; older versions not tested |
| `ffmpeg` and `ffprobe` on PATH | 9.0.1 |
| Claude Code with function-hook plugins | 2.1.288 (an older 2.1.283 rejected the plugin's `prompt.compose` hook) |
| Optional: OpenAI Codex with the `hooks` feature | codex-cli 0.146.0 |
| Optional: HyperFrames, for renders | 0.8.127 |

## 1. Get the repository

Clone it wherever you keep tools. These docs use `~/Documents/Aavkar Educational Motion Studio`,
which is also listed in the registry's `shared_paths`; if you put it elsewhere, update that entry.

## 2. Install the command

```bash
cli/install.sh
```

This links `cli/bin/aem` into `~/.local/bin` (pass another folder as the first argument) and warns
if that folder is not on PATH or if Python, `ffmpeg` or `ffprobe` is missing. It refuses to replace
an `aem` that is not this one. Check it:

```bash
aem --version
```

```bash
aem status
```

`aem status` should say no project is active.

## 3. Register your clients

`registry/clients.json` holds every client: its design-system folder, projects folder, protected
files, gates, blocked commands, render scripts, review settings and idle time. Read Joel's entry as
the worked example. To add a client from the template (`registry/client-template/`):

```bash
aem new-client acme --name "Acme Learning" --design-system "/path/to/00 - Acme Design System" --projects-root "/path/to/Acme"
```

It scaffolds the decisions file, rules file, critic file and text folder into an empty design-system
folder and adds the registry entry. Use another registry file with `--registry FILE` or the
`AEM_REGISTRY` environment variable. AEM keeps its own state (the active project, Codex's pending
calls) in `~/.aem`; set `AEM_HOME` to move it.

Add every folder your tools need outside the client's own folders to `shared_paths`, or the guard
will deny reaching them (AEM-G02). The default list covers this repository, `~/.aem`, Claude Code's
skills, plugins and app folders, Codex's packages, HyperFrames and Cut Assist.

## 4. Install the Claude Code plugin

The repository is a plugin marketplace named `aavkar-productions`
(`.claude-plugin/marketplace.json`). In Claude Code, add the marketplace, then install the plugin:

```text
/plugin marketplace add <owner>/<repo>
/plugin install aavkar-educational-motion-studio@aavkar-productions
```

`<owner>/<repo>` is the GitHub repository once this is pushed; a local path to the repository works
too. Claude Code has no single `install … --marketplace` command: adding the marketplace and
installing from it are two steps. From a terminal the same is:

```bash
claude plugin marketplace add "/path/to/Aavkar Educational Motion Studio"
```

```bash
claude plugin install aavkar-educational-motion-studio@aavkar-productions
```

Tested on 6 October 2026 with Claude Code 2.1.288 in an isolated config folder: the marketplace
added, the plugin installed (version 0.7.0) and enabled, and `/aem status` answered from the
installed copy.

### Plugin settings

| Setting | Default | What it does |
|---|---|---|
| `aemPath` | `aem` | The command to run. Left as `aem`, the plugin also tries `~/.local/bin/aem`. |
| `reviewInbox` | off | Adds `/inbox`, the review pane (see OPERATOR.md). |

Set them in the plugin's config menu (`/plugin configure aavkar-educational-motion-studio@aavkar-productions`)
or under `pluginConfigs["aavkar-educational-motion-studio"].options` in Claude Code's settings.

### Developing the plugin

Point Claude Code at the folder instead of installing it: `claude --plugin-dir
plugin/aavkar-educational-motion-studio`. Check it with `claude plugin validate`, `claude plugin test`
and `tsc -p` on that folder (the engine writes the types into `.claude-plugin/types/` once the
plugin has loaded).

## 5. The studio skill

AEM works alongside a client's studio skill (Joel's is `mergetomaster-studio`). The skill's master
lives in the client's design system (`Skill/`); install it as that design system's README says.
The skill has a section, "When Aavkar Educational Motion Studio (AEM) is loaded", that tells the
agent to leave the ledgers and records to the operator's commands. `aem drift` checks that the
installed skill matches its master.

## 6. Optional: Codex

Codex 0.146 runs command hooks (feature `hooks`, on by default). Print AEM's hook configuration, with
the absolute path of your `aem`:

```bash
aem codex-config
```

Add its `[hooks]` table to `~/.codex/config.toml` (if that file already has a `[hooks]` table, merge
the entries). `aem codex-config --format json` prints the same for `~/.codex/hooks.json`. Then
start Codex and review the hooks with `/hooks`: Codex runs a non-managed hook only after you trust
it, and asks again whenever it changes.

What was verified: with Codex 0.146.0, this exact TOML (passed with `-c` overrides) ran the
SessionStart hook (AEM's context reached the model) and the PreToolUse hook blocked an agent's
`aem approve` (AEM-G04). A project-level `<repo>/.codex/hooks.json` was not picked up by
`codex exec` in that test, so install the hooks at user level. Re-check after a Codex upgrade:

```bash
tests/live/codex-hooks-check.sh
```

It runs one real `codex exec` in a temporary folder (your Codex login, a few thousand tokens) and
never touches `~/.codex`.

## 7. Check the install

```bash
python3 -m unittest discover -s tests -t tests
```

```bash
aem drift --client joel
```

In Claude Code, `/aem status` should answer, and after `/aem use <client>/<project>` the status line
shows `AEM · <client> · <project> · …`.

## Updating and removing

Pull the repository; the command updates at once (it is a link). For the plugin, `/plugin
marketplace update aavkar-productions` and reinstall. Remove the plugin with `/plugin uninstall
aavkar-educational-motion-studio@aavkar-productions`, the command by deleting the
`~/.local/bin/aem` link, and the Codex hooks by deleting AEM's `[hooks]` entries. AEM's ledgers live
in the projects and stay.
