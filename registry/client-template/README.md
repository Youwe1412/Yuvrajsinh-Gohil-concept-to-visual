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

Agents read the Markdown text versions of the Brand and Motion pages in `text/`, never the HTML.

## Folder map

| Folder or file | Holds |
|---|---|
| `rules.md`, `{{CLIENT_ID}}-decisions.md` | The rules index and the client's rulings |
| `text/` | Generated Markdown versions of the Brand and Motion pages. Each starts with `Generated from <page> (SHA-256 <hex>) on <date>.` so `aem drift` can tell when a page changed after its export. |
| `critic/labelled-cases.jsonl` | The critic's golden set: the client's keep, change or remove on delivered shots. Its first line describes the fields. |
| `Skill/{{SKILL}}/` | Master copy of the client's studio skill |

## With AEM

- `aem use {{CLIENT_ID}}/<project>` makes a project active; the Claude Code plugin then loads this
  folder's paths, the decisions file and the skill into the session.
- Protected files (`{{CLIENT_ID}}-decisions.md`, `rules.md`, `critic/labelled-cases.jsonl`, and each
  project's `approvals.jsonl` and `events.jsonl`) are written by the operator's commands, not by an
  agent. These are recorded checks inside Claude Code, not security boundaries.

## Starting a new project

1. Create the project folder under the projects root (for example `P1 - <title>`).
2. Read the client's brief and `{{CLIENT_ID}}-decisions.md`. Record the edit's exact frame rate as
   a rational in the project's `aem.project.json` (`"fps": "24000/1001"`), or export the edit's
   FCPXML into the project.
3. `aem use {{CLIENT_ID}}/<project>`, then work through the gates G1 to G7.

## Changing the system

A rule changes when the channel changes or when the client rules on it, not when one video needs an
exception. Record the client's ruling in `{{CLIENT_ID}}-decisions.md` first, then update the pages and
`rules.md` together, regenerate `text/`, and run `aem drift`.
