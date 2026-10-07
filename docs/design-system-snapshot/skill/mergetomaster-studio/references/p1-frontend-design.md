# Case study: P1 · Frontend Design (delivered September 2026)

How the first video applied the system. These are worked examples and project facts, **not channel
rules**. Reuse an idea when a new video has the same teaching job; never import P1's argument
(gold = human choice, indigo = machine default) unless the new script makes the same argument.

Project: `P1 - Frontend Design/Animations using Hyperframes/MergeToMaster/`. Read its `CONTEXT.md`
before touching any P1 scene. Joel published the video on 23 September 2026; his final change requests
(14 September) are in `joel-decisions.md`.

## Laws that were specific to P1

- **The side decides the specimen.** Better wore Joel's finished Prim & Paw design; worse wore the
  generic version of the same brief (indigo `#6366F1`, blue→purple gradient, Inter, three rounded
  cards, centred hero, soft shadows). Same business, same copy. If both sides looked good, the shot
  failed.
- **The reveal was protected.** The finished design appeared in full exactly once, at its scripted
  moment; before that only parts.
- **P1's colour law** (gold = a human chose this, red = a human refused something, indigo = the
  machine's default) stopped at the edge of a quoted page.
- **Durations were fixed by the transcript slot**, and word timings came from
  `data/narration-words.json`.

## Patterns that earned their place

- **Repeated attempts under an unresolved question** (`title-t03-name`): the supplied page under the
  question; a macOS cursor clicks "Generate again"; attempts stack as 01, 02, 03 with small variations.
  Never claim illustrative variations are Joel's real generation history.
- **Different content, same structure** (`teach-recognition`): pages change; gold outlines on shared
  structure stay fixed through the change.
- **Metaphor, then concrete evidence** (`fingerprint`): a sourced thumbprint gets its own beat, then
  recedes as real UI details enlarge from their original locations.
- **Parallel exploration, coherent result** (`board-e`, `parallel-2`, `parallel-3`): empty A/B/C frames,
  three directions differing in structure and expression, then selection into one result referenced to
  the actual final design.
- **Agent-built intro:** the generic interface builds component by component under labelled agent
  pointers; the UI owns the frame; authentic, sourced agent logos, diagonally below-right of the
  pointer; an explanatory animation, never presented as a recording.

## What Joel changed after delivery (14 Sep 2026)

He removed the one-frame website flash from the 50 ms shot, and the bottom demonstration captions from
`button-states` and `character`. Lesson kept in the system: a literal demonstration the viewer cannot
perceive is decoration, and a caption that repeats a visible demonstration is clutter.

## P1 source and delivery map

| Path | Holds |
|---|---|
| `lib/scenes.js` | scene logic (frozen build folders may hold a different approved revision) |
| `lib/tokens.css`, `lib/refinement.css`, `lib/fonts/` | tokens and type, the starting point for new projects |
| `lib/primpaw.js`, `lib/specimens.js` | Joel's finished design elements / generic specimens |
| `data/edit.json`, `data/narration-words.json` | placement and word timings |
| `renders/v08/` | masters, `REVIEW.html`, manifests, verification files |
| `../Animations Done/` | the editor-facing delivery copies |

P1 safeguards worth repeating: never edit media inside a Final Cut library bundle; bump the video source
revision as well as the URL query to beat the browser cache; use a byte-range server for long-video
seeking; update master, delivery copy, narrated proxy and full-film review together.

The skill that held these as rules (educational-animation-framework) is archived in
`00 - MergeToMaster Design System/System Archive/2026-10-05-skill-educational-animation-framework/`.
