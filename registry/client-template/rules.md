# {{CLIENT_NAME}} rules index

The agent-readable version of {{CLIENT_NAME}}'s Brand, Motion and Edit Systems. The pages carry
the reasoning and examples; this file gives every rule an ID so plans, briefs, critic findings
and override logs can cite it. When a page and this file disagree, the page wins and this file
is corrected.

As of {{DATE}}.

## How to use it

| Kind | What a finding against it means |
|---|---|
| **Invariant** | Must be fixed. No override. |
| **Client default** (tag C) | Fix it, or override it with a logged reason that names what the viewer understands better. Every override of a C rule is flagged to {{OPERATOR}}. |
| **Default** | Fix it, or override it with a logged reason. |
| **Option** | Switched on per shot when the job needs it. No finding. |

Override line, in the scene brief and QC: `rule ID · teaching job · reason · how it was verified`.

**Tags:** C the client's own words, rulings or published videos · E peer-reviewed evidence ·
P documented practice, standards or platform policy · I our inference, to be tested on the
client's videos.

**Status:** *Client stated* (their words, in `{{CLIENT_ID}}-decisions.md`) · *Measured* (sampled
from the client's own material) · *Unconfirmed*. Change a status only by adding an entry to
`{{CLIENT_ID}}-decisions.md` first.

---

## {{CONTACT}}'s stated preferences

| ID | Rule | Kind | Tags | Status | Source |
|---|---|---|---|---|---|
| C-01 | (the client's first stated preference, in plain words) | Client default | C | Client stated | Brief |

## Brand

| ID | Rule | Kind | Tags | Status | Source |
|---|---|---|---|---|---|
| B-T1-01 | (invariant) | Invariant | P | Unconfirmed | Brand 01 |

## Motion

| ID | Rule | Kind | Tags | Status | Source |
|---|---|---|---|---|---|
| M-T1-01 | (invariant) | Invariant | P | Unconfirmed | Motion 01 |

## Aavkar baseline

Aavkar's house craft defaults, explained in [craft-baseline.md](craft-baseline.md). Every client starts
with them as **Default**. Invariants, {{CONTACT}}'s rulings and this client's own Brand and Motion rules
outrank them. When a page above says otherwise, the page wins: mark the A rule *Superseded* and name the
rule that replaced it. "Measured" in the Rule column names the AEM file that measures it.

| ID | Rule | Kind | Tags | Status | Source |
|---|---|---|---|---|---|
| A-01 | Every moment states the one thing the viewer knows after it; a frame that cannot say why it exists is cut | Default | I | Unconfirmed | craft-baseline.md §1 |
| A-02 | A standalone piece's first frame works as a still on a busy feed; the hook lands in the first second | Default | P | Unconfirmed | craft-baseline.md §1 |
| A-03 | One object, shape or word carries each handoff and lands on the same pixels on both sides | Default | P | Unconfirmed | craft-baseline.md §2 |
| A-04 | Transitions are made of content (it moves to camera, wipes or unfolds into the next); hard cuts only when size, direction and subject match, on a cue word or beat | Default | P | Unconfirmed | craft-baseline.md §2 |
| A-05 | One lead movement with overlapping secondary ones; nothing starts or stops all at once | Default | P | Unconfirmed | craft-baseline.md §3 |
| A-06 | Speed always changes: no linear easing on movement; anticipation, follow-through, springs and arcs | Default | P | Unconfirmed | craft-baseline.md §3 |
| A-07 | Every action has a visible result | Default | P | Unconfirmed | craft-baseline.md §3 |
| A-08 | Type enters, masks and reveals with the words; on screen at least 0.3 s per word (0.7 s minimum), on a plate over busy graphics (over footage: A-29); if the picture says it, cut the word | Default | P | Unconfirmed | craft-baseline.md §4 |
| A-09 | Holds breathe with micro-motion: no frozen run over 0.5 s inside a moment, at most 1 s frozen per 30 s. Measured: holds.json | Default | I | Unconfirmed | craft-baseline.md §3 |
| A-10 | Vary scale and layout (macro, wide, overhead, full-frame type); never the same layout twice in a row | Default | P | Unconfirmed | craft-baseline.md §5 |
| A-11 | Camera moves are motivated, land on the word and hold still while text is read; one plane with the content, subject inside safe padding (10 % / ~11 %); fast ones carry natural motion blur (~90° shutter, 16 samples, never frame blending) | Default | P | Unconfirmed | craft-baseline.md §5 |
| A-12 | 3D only where it explains something spatial: product-shot lighting, camera at 35–55°, real materials, labels as HTML tracked from the scene | Default | P | Unconfirmed | craft-baseline.md §5 |
| A-13 | Every effect earns its place: no decorative particles, generic gradients or stock glitches | Default | P | Unconfirmed | craft-baseline.md §6 |
| A-14 | Never redraw a logo: take it as SVG from the source, and sample the real colours and fonts | Default | P | Unconfirmed | craft-baseline.md §7 |
| A-15 | Never show a raw screenshot as a static slab: rebuild its panels, icons and text so each part can move | Default | P | Unconfirmed | craft-baseline.md §7 |
| A-16 | Generated images are references (style frames, key poses) rebuilt in code; on screen only when the brief allows, labelled as concept | Default | P | Unconfirmed | craft-baseline.md §7 |
| A-17 | Every on-screen claim traces to a source sentence and where it came from; nothing invented (testimonials, ratings, prices, results, real people) | Default | P | Unconfirmed | craft-baseline.md §7 |
| A-18 | Sound effects only for real on-screen events: one soft whoosh per scene change, clicks and impacts on real actions, each in its own frequency range just above the music | Default | P | Unconfirmed | craft-baseline.md §8 |
| A-19 | Music sits under the voice and is edited at bar lines, never bent to the picture; a music prompt never names a brand or artist | Default | P | Unconfirmed | craft-baseline.md §8 |
| A-20 | A finished mix meets the client's loudness target (web default −14 LUFS) with true peak at or below −1 dBTP, measured on the encoded file that is delivered. Measured: check-render | Default | P | Unconfirmed | craft-baseline.md §8 |
| A-21 | Every cue lands within one frame of its word or beat. Measured: sync.json | Default | P | Unconfirmed | craft-baseline.md §8 |
| A-22 | Text contrast at least 4.5:1, inside the platform's safe margins; no collisions; type size measured on screen (font × camera scale) | Default | P | Unconfirmed | craft-baseline.md §4 |
| A-23 | Build contract-first: shared tokens, eases and handoff positions are written before any scene, so scenes can be built in parallel | Default | I | Unconfirmed | craft-baseline.md §9 |
| A-24 | Before real work, render a 3–5 s piece through the whole pipeline, placement import included; long renders through a memory-gated queue, versions never reused | Default | I | Unconfirmed | craft-baseline.md §9 |
| A-25 | Recompose each format rather than crop; keep 9:16 content out of the platform's UI zones | Default | P | Unconfirmed | craft-baseline.md §5 |
| A-26 | The critic is a fresh reader who saw none of the building: the sound-off retell first, then the evidence, then the references; it advises and does not gate until its labelled cases agree with the client | Default | I | Unconfirmed | craft-baseline.md §10 |
| A-27 | Refine before rendering: a live preview per scene and all scenes with the client's voice, judged in context, never from stills; render only approved looks | Default | I | Unconfirmed (MergeToMaster P2, Oct 2026) | craft-baseline.md §9 |
| A-28 | Back-to-back inserts meet frame to frame (a gap under 0.5 s flashes the A-roll); no graphic flashed between two live shots | Default | I | Unconfirmed (MergeToMaster P2, Oct 2026) | craft-baseline.md §2 |
| A-29 | Words over the client's footage: no darkening field of any kind; contrast measured on the footage; a letter-hugging shadow; move the text rather than add a field | Default | I | Unconfirmed (MergeToMaster P2, Oct 2026) | craft-baseline.md §4 |
| A-30 | Explain a tool with its real interface redrawn from captured references (strings, glyphs, colours; prose as text bars; no "redrawn" caption); soft enlarged recordings re-typeset | Default | I | Unconfirmed (MergeToMaster P2, Oct 2026) | craft-baseline.md §7 |
| A-31 | A video frame used as a picture is written untagged, so the browser draws it as bright as the frame it continues | Default | P | Unconfirmed (MergeToMaster P2, Oct 2026) | craft-baseline.md §7 |
| A-32 | A hook or agenda promises its payoff and never shows it: title readable, content blurred past reading | Default | I | Unconfirmed (MergeToMaster P2, Oct 2026) | craft-baseline.md §1 |
| A-33 | In a teaching video, music plays only where it does a job (no teaching under it, a punchline set-up, a chapter mark, the one reveal); teaching is dry | Default | E | Unconfirmed (MergeToMaster P2, Oct 2026) | craft-baseline.md §8 |
| A-34 | Sound comes from the picture: made from each animation's own timeline or recorded, keyed to events measured in the footage; no generic stock SFX folder | Default | I | Unconfirmed (MergeToMaster P2, Oct 2026) | craft-baseline.md §8 |
