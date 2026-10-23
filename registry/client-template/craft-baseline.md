# Aavkar craft baseline

The house defaults every {{CLIENT_NAME}} project starts from, before {{CONTACT}} has ruled on anything.
The rows `A-01`…`A-34` in [rules.md](rules.md) cite the sections below. Taken from documented motion
practice and from a generic motion-director brief we studied in October 2026, then checked against our
earlier client work. A-27…A-34 and the additions to A-11, A-20, A-22 and A-24 (23 October 2026) come from
the operator's rulings on MergeToMaster P2, a video the client accepted with no changes; they are house
craft for any client, with that one video as their evidence.

**Where this sits.** Lowest tier. Invariants > the operator's latest specific instruction > the client's
rulings (`{{CLIENT_ID}}-decisions.md`) > this client's Brand and Motion rules > this baseline > craft habits.
A rule here changes or goes away when the client rules otherwise or when the client's own pages cover it,
never because one video needed an exception.

**The bar.** A render with no bugs is not finished. It is finished when a critic would put it beside the
references in the project's `references/` folder and it would not look weaker. These rules are the floor.

---

## 1. Purpose and the first frame

- Every moment has one thing the viewer knows after it, written in the shot list's *knows after*. If a
  frame cannot say why it exists, cut it (A-01).
- A standalone piece (a trailer, a launch film, a social cut) opens on a finished picture that works as a
  still on a busy feed, and the hook lands in the first second (A-02). An insert placed into the client's
  edit inherits the edit's opening instead.
- A hook or agenda promises its payoff and never shows it: the payoff's title stays readable, its content
  is blurred past reading (tight on the words, the meaning crisp), so the curiosity gap stays open (A-32).

## 2. Continuity and handoffs

- One object, shape or word carries each handoff and lands on the same pixels on both sides (A-03).
  Write the handoff positions down before building either scene (§9).
- Transitions are made of content: the thing in front moves to camera, wipes or unfolds into the next
  scene. A hard cut only when size, direction and subject match, and only on a cue word or beat (A-04).
- Back-to-back inserts meet frame to frame: one that is followed by another holds its last frame to the
  next one's first word, because a gap under half a second shows a flash of the A-roll. No graphic is
  flashed between two live shots; one entered by a continuous camera move is not a flash (A-28).

## 3. Movement

- One lead movement with overlapping secondary ones. Nothing starts or stops all at once (A-05).
- Speed always changes: arrive slowly enough to read, leave fast. No linear easing on movement. Use
  anticipation, follow-through, squash and stretch, springs and arcs (A-06).
- Every action has a visible result (A-07).
- Holds breathe with micro-motion; nothing freezes (A-09). AEM lists every frozen run over 0.5 s and the
  frozen seconds per 30 s in `holds.json`. A tail hold before a placement can be deliberate: say so in the
  scene brief.

## 4. Type

- Type is motion, not captions: it enters, masks and reveals with the words (A-08).
- On screen at least 0.3 s per word, 0.7 s minimum. Over busy graphics it sits on a plate; over the
  client's footage, see A-29. If the picture already says it, cut the word.
- Text contrast at least 4.5:1, inside the safe margins, with no collisions (A-22). Measure type size on
  screen (font size × every camera and scene scale), not in CSS: a camera that fits a tall, mostly empty
  panel quietly halves it. AEM does not measure this yet (it has no text geometry): the critic checks it on
  the phone crops.
- Words over the client's footage get no darkening of any kind behind them (no strip, box, blur or
  gradient: it reads as unnatural). Measure the footage behind the text (its brightest 5 % over the span);
  carry legibility with a shadow that hugs the letters; if a spot is too bright, move the text. Keep the
  words clear of the speaker's head, on both sides if needed (A-29).

## 5. Scale, layout, camera, formats

- Vary scale and layout: macro, wide, overhead, full-frame type. Never the same layout twice in a row (A-10).
- Camera moves are motivated and land their framing on the word; between moves the frame is still while
  text is read. The camera moves over one plane with the content (depth that carries no meaning splits a
  move and pulls the eye), and every framing keeps its subject inside safe padding (10 % of the width, about
  11 % of the height). Fast moves carry natural motion blur: about a 90° shutter, 16 samples a frame, never
  few-sample frame blending, which ghosts (A-11).
- 3D only where it explains something spatial, with product-shot lighting, a camera at 35–55°, real
  materials and labels as HTML tracked from the scene (A-12).
- Recompose each format rather than crop it, and keep 9:16 content out of the platform's UI zones (A-25).

## 6. Restraint

Every effect earns its place. No decorative particles, generic gradients or stock glitches (A-13). Build
the client's own never-list from their *remove* rulings in `critic/labelled-cases.jsonl`, in their words.

## 7. Assets and facts

- Capture the real product at 2×. Take the logo as SVG from the source and sample the real colours and
  fonts. Never redraw a logo (A-14).
- Never show a raw screenshot as a static slab. Rebuild its panels, icons and text as live HTML or SVG so
  each part can move (A-15). A screen recording enlarged past about 1:1 goes soft beside crisp animation:
  re-typeset it on its own character grid, every state transcribed from its frames.
- Explain a tool with its real interface, redrawn as UI from references captured in the real tool
  (strings, glyphs, colours, in the state the scene shows), not with abstract boxes; what people type is
  drawn as text bars, and no caption says it was redrawn. Never guess a UI string (A-30).
- A video frame used as a picture inside a composition is written untagged (decode raw pixels, write the
  PNG without colour chunks): browsers colour-manage tagged frames and draw them darker than the frame
  they continue (A-31).
- Generated images are references (style frames, character sheets, key poses) rebuilt in code. They go on
  screen only if the brief allows, labelled as concept (A-16).
- Every claim on screen or in voice traces to an exact source sentence and where it came from. Nothing is
  invented: no testimonials, ratings, prices, results or real people (A-17).
- References are for study: find their cuts and fast moments with a frame-difference pass and dense
  contact sheets, and extract the principles. Never copy footage, layouts or music.

## 8. Sound and sync

- Sound effects only for real on-screen events: one soft whoosh per scene change, clicks and impacts on
  real actions, each in its own frequency range just above the music (A-18).
- Sound comes from the picture: each animation's sounds are made from its own timeline (tag the tween that
  makes the sound; synthesise it for what that tween does) or are real recordings (keys, mouse), and in
  screen recordings every click, scroll and camera move is keyed to an event measured in the footage. A
  generic stock SFX folder dropped on cues sounds inaccurate (A-34).
- Music matches the energy and sits low, under the voice. Trim or offset the track at bar lines rather
  than bend the picture. A music prompt never names a brand or artist (A-19).
- In a teaching video, music plays only where it does a job: under picture with no teaching, to set up a
  punchline, to mark a chapter, or to carry the one reveal. Teaching is dry: music stops where
  explanation starts (the coherence principle) (A-33).
- A finished mix meets the client's loudness target (web default −14 LUFS) with true peak at or below
  −1 dBTP (A-20). Measure the encoded file that is delivered, not only the mix: an AAC encode can add most
  of a decibel of true peak. AEM measures every render that carries sound; set `loudness.target_lufs` for
  the client or project to have it checked. Inserts that ship silent, with cues as separate clips, say "not
  checked: no audio stream", which is correct.
- Every cue lands within one frame of its word or beat (A-21), measured in `sync.json`. For narrated work
  the clock is the narration's word IDs, not a music beat grid.

## 9. Build

- Contract first: shared tokens, eases and handoff positions are written before any scene. Then each
  scene is its own component and scenes can be built in parallel without drifting apart (A-23).
- Every value is a function of the frame number: no timers, no unseeded randomness. Fonts and assets are
  pinned locally.
- Before real work, render a 3–5 s piece through the whole pipeline: render, `aem check-render`,
  evidence, placement file and the import into the editor (A-24). A pipeline break found at G1 costs
  minutes; at delivery it costs the day. Long renders go through a queue that starts one only when memory
  allows (4K motion-blurred renders took about 4.8 GB each; four at once ran a 24 GB Mac out of memory and
  the batch died with the session); versions are never reused, and an old render is retired only after
  its replacement passes the check.
- Refine before rendering: each scene in a live preview that reloads as it is edited, and the scenes
  together with the client's voice, judged in context, never from stills. Render only once the look is
  approved; a fast draft first when a join or a timing is in doubt (A-27).

## 10. The critic

- The builder never judges its own work. The critic is a fresh reader who saw none of the building (A-26).
- **Sound-off read first.** A fresh subagent gets only `retell.md` (the render at 2 frames a second, no
  sound) and writes `retell.json`. The critic compares that retell with the shot list's *knows after*:
  `yes`, `partly` or `no`. A `no` is the most important finding a render can have.
- **Then the evidence.** `evidence.md` and the images it names, never the source. Findings name an image
  and a rule ID; at most the three worst.
- **Then the references.** One question: what looks assembled, slow or generic beside them? Advice to the
  director; it does not change the verdict.
- **Fix the biggest problem first, re-render, and recheck everything.** A fresh critic checks every earlier
  finding again. `aem rounds` shows what each version fixed, kept or brought back.
- **The critic advises.** It gates nothing until its verdicts agree with the client's labelled cases
  (about 30). Code and human graders outrank the model.
- **Plans get a reader too.** Before G3, a fresh subagent reads the shot list alone and retells the
  video. If the plan does not tell the story, the renders will not either.

## Choices

Where the brief, the plan and the client's rulings leave a gap, we decide and record it:
`aem chose "<what>" --why "<what the viewer understands better>" [--moment M] [--rule ID]`. At the
client's review, `aem calibrate` separates the changes that rest on our choices from the ones that do not.
That is how a choice becomes a rule, or stops being made.

## Measured by AEM

| Rule | Where | Threshold (default) | Fails the render check? |
|---|---|---|---|
| A-09 holds | `holds.json`, evidence.md | frozen run > 0.5 s; > 1 s frozen per 30 s (`evidence.max_still_s`, `evidence.max_frozen_per_30s`) | No: listed for the critic |
| A-20 loudness | `aem check-render` | `loudness.target_lufs` ± `tolerance_lu` (none by default); true peak ≤ −1 dBTP | Yes, when set and the render has sound |
| A-21 sync | `sync.json` | ±1 frame | No: listed for the critic |
| Flashes | `aem check-render` | 1–2 frame flashes over 0.1% of the frame | Yes |
| Spec | `aem check-render` | size, fps, frame count, alpha, duration | Yes |
| A-22 contrast | not measured | 4.5:1 | Critic, on the phone crops |
