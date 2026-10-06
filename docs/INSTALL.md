# Installing Aavkar Educational Motion Studio

Aavkar Educational Motion Studio (AEM) is two pieces: the `aem` command, which makes every
decision, and a Claude Code plugin that calls it. Codex can call it too, through hooks. Install the
command first; the plugin and the hooks do nothing without it. AEM observes and records: once
installed it never blocks work, and asks only before a delivery of a render with no current approval.

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

Clone it wherever you keep tools. These docs use `~/Documents/Aavkar Educational Motion Studio`.

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

Run from anywhere that is not a registered project's folder, `aem status` should say no project is resolved.

## 3. Register your clients

`registry/clients.json` holds every client: its design-system folder, projects folder, gates,
approval and delivery patterns, render scripts, review settings and idle time. Read Joel's entry as
the worked example. (Since 1.0.0 nothing reads `protected_files`, `blocked_commands`, `shared_paths`
or `audio_libraries`; they belonged to the guard and can be deleted.) To add a client from the
template (`registry/client-template/`):

```bash
aem new-client acme --name "Acme Learning" --design-system "/path/to/00 - Acme Design System" --projects-root "/path/to/Acme"
```

It scaffolds the decisions file, rules file, critic file and text folder into an empty design-system
folder and adds the registry entry. Use another registry file with `--registry FILE` or the
`AEM_REGISTRY` environment variable. AEM keeps little state in `~/.aem`: a last-used hint (nothing
trusts it), the one-time nonces the plugin's slash commands write (`nonces/`, each good for one use within
60 seconds), and Codex's pending calls; set `AEM_HOME` to move it. The project a command acts on is
never stored there: it comes from the folder you work in (register each project under `projects` in the
registry), `AEM_PROJECT`, or the plugin's session pin. Give each client's decisions file an "Open
questions for <contact>" section: `aem recall` lists it at the start of every session.

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

Tested on 6 October 2026 with Claude Code 2.1.288: the marketplace added and the plugin installed and
enabled (0.7.0 in an isolated config folder, then 0.9.0 and 1.0.0 for the operator with
`claude plugin update`).

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
The skill has a three-line section, "When Aavkar Educational Motion Studio (AEM) is loaded": AEM
records; the agent never writes the record files; when an approval, rejection, client quote or stage
change is needed, the agent asks the operator in one sentence and continues after they run it.
`aem drift` checks that the installed skill matches its master.

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

What was verified (at 0.8.0): with Codex 0.146.0, this exact TOML (passed with `-c` overrides) ran the
SessionStart hook (AEM's context reached the model) and an agent's `aem approve` was refused by the
`aem` command itself (Codex's shell has no terminal and no operator nonce), with no hook involved. The
hooks never deny a call: they record it. A project-level `<repo>/.codex/hooks.json` was not picked up by
`codex exec` in that test, so install the hooks at user level. Re-check after a Codex upgrade:

```bash
tests/live/codex-hooks-check.sh
```

It runs one real `codex exec` in a temporary folder (your Codex login, a few thousand tokens) and
never touches `~/.codex`.

## 7. Check the install

```bash
tests/run.sh
```

It runs the CLI and plugin tests against a sandbox and fails if `~/.aem` or `registry/clients.json`
changed during the run.

```bash
aem drift --client joel
```

Start Claude Code in a registered project's folder: you should get one toast, `AEM 1.0.0 ·
<client>/<project> · resolved from folder`, the client's recall in the transcript (`AEM recall · …`),
and the status line `AEM · <client> · <project> · …`. No toast means the plugin is not loaded in that
session. `/aem status` answers either way once it is.

## Updating and removing

Pull the repository; the command updates at once (it is a link). **The plugin does not**, and the two
must match: a 0.9 plugin against the 1.0 command asks for `aem guard` and `aem authority`, which no
longer exist, so it toasts on every call (it blocks nothing, but records nothing either), and a plugin
older than 0.8 has its slash commands refused ("no operator nonce"). Update it, then start new sessions:

```bash
claude plugin marketplace update aavkar-productions
```

```bash
claude plugin update aavkar-educational-motion-studio@aavkar-productions
```

`claude plugin list` should then say version 1.0.0. Remove the plugin with `/plugin uninstall
aavkar-educational-motion-studio@aavkar-productions`, the command by deleting the
`~/.local/bin/aem` link, and the Codex hooks by deleting AEM's `[hooks]` entries. AEM's ledgers live
in the projects and stay.
