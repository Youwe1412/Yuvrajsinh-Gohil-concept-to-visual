# {{CLIENT_NAME}} Design System

The home base for every {{CLIENT_NAME}} ({{CONTACT}}) animation project. Start every new video
here. Scaffolded by Aavkar Educational Motion Studio (AEM) on {{DATE}}; fill in each file before
the first project.

## Current: use these

| Document | Version | What it owns |
|---|---|---|
| Brand System (HTML page) | v1 | Colour, type, frame, evidence, formats |
| Motion System (HTML page) | v1 | Teaching jobs, motion vocabulary, voice sync, the studio gates, the critic |
| [rules.md](rules.md) | {{DATE}} | Every rule with an ID, kind, source tags, status and page |
| [{{CLIENT_ID}}-decisions.md]({{CLIENT_ID}}-decisions.md) | {{DATE}} | The client's own words, requests and rulings, dated and scoped |
| [craft-baseline.md](craft-baseline.md) | {{DATE}} | Aavkar's house craft defaults (rules A-01…A-26): the floor before the client rules, the critic's order, what AEM measures |

Agents read the Markdown text versions of the Brand and Motion pages in `text/`, never the HTML.

## Folder map

| Folder or file | Holds |
|---|---|
| `rules.md`, `{{CLIENT_ID}}-decisions.md` | The rules index and the client's rulings |
| `craft-baseline.md` | Aavkar's house defaults; the lowest tier, below every rule of the client's |
| `text/` | Generated Markdown versions of the Brand and Motion pages. Each starts with `Generated from <page> (SHA-256 <hex>) on <date>.` so `aem drift` can tell when a page changed after its export. |
| `critic/labelled-cases.jsonl` | The critic's golden set: the client's keep, change or remove on delivered shots. Its first line describes the fields. |
| `Skill/{{SKILL}}/` | Master copy of the client's studio skill |

## With AEM

- A session started in a project's folder (registered under `projects` in AEM's registry) records
  into that project; `/aem use {{CLIENT_ID}}/<project>` pins one to a session started elsewhere. At
  the start of each session the agent is given `aem recall`: the client's stated preferences, the last
  five rulings in their words, the open questions and the labelled-case count.
- The record (`{{CLIENT_ID}}-decisions.md`, `critic/labelled-cases.jsonl`, and each project's
  `approvals.jsonl` and `events.jsonl`) is written only by the operator's `aem` commands. AEM never
  blocks an edit; `aem integrity` flags any line it did not write until the operator accepts it.
- Every render gets evidence: poses, phone crops, sync, frozen holds (`holds.json`), and a silent
  2 fps sheet with `retell.md` for the sound-off read. The agent records its own decisions with
  `aem chose`; `aem rounds` shows what each re-render fixed, kept or brought back; `aem calibrate`
  separates the client's changes that rest on our choices from the rest.

## Starting a new project

1. Create the project folder under the projects root (for example `P1 - <title>`).
2. Read the client's brief and `{{CLIENT_ID}}-decisions.md`. Record the edit's exact frame rate as
   a rational in the project's `aem.project.json` (`"fps": "24000/1001"`), or export the edit's
   FCPXML into the project.
3. Put a few frames of the work this video should hold up beside in the project's `references/`
   folder (stills, from the client's best videos and the references in the brief). Evidence links them
   for the critic's director's review.
4. Register the project in AEM's registry, start Claude Code in its folder, then work through the
   gates G1 to G7. At G1, push a 3–5 s test through the whole pipeline, placement import included
   (A-24). Before the first scene, write the shared tokens, eases and handoff positions (A-23).

## Changing the system

A rule changes when the channel changes or when the client rules on it, not when one video needs an
exception. Record the client's ruling in `{{CLIENT_ID}}-decisions.md` first, then update the pages and
`rules.md` together, regenerate `text/`, and run `aem drift`. When a client ruling or page covers an
A rule, mark the A row *Superseded* and name the rule that replaced it.
