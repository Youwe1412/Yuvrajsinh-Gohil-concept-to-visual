# G6 · Placement FCPXML and sound cues

Masters are placed in Joel's timeline by hand today, by ear and eye. An FCPXML that puts each master on
its word ID and each sound cue on its frame makes placement exact and repeatable, and it moves with
the voice when the cut changes.

## Inputs

- The **current timeline** exported from Final Cut as FCPXML (File > Export XML), with its version.
- `data/words.json` aligned to that same cut (same audio SHA-256), with `fps_num`/`fps_den`.
- The approved masters: every one must pass the approval check in `references/project-ledgers.md`.
- The cue sheets (M-25) and the chosen sound files, from Joel's Epidemic Sound and Envato libraries.

## Build

1. Read the sequence format's `frameDuration` and check it equals `fps_den/fps_num` from
   `words.json`. If not, stop: the word map belongs to a different timeline.
2. For each master, its timeline start is the frame of its anchor word (from `shotlist.md`) minus any
   planned lead, in whole frames. Find the primary-storyline clip that spans that time and attach the
   master to it as a **connected clip** on a positive lane. A connected clip's `offset` is in the
   parent's local time: `parent.start + (timeline_time − parent.offset)`.
3. For each sound cue, add the sound file as its **own connected audio clip** on a negative lane at
   the cue's frame, with `audioRole="effects"`, so Yuvraj can move, swap or mix each one. Never bake
   sound into a master.
4. Write every time as an exact rational on the frame grid (no decimals). Add a marker per master named
   with its shot and word ID.
5. Write a **new** `.fcpxml` in `out/` with a new project name (`<video> · graphics placement · <date>`).
   Never edit the source FCPXML or anything inside a Final Cut library bundle.

## Reuse from Cut Assist

Aavkar Cut Assist's `App Code and Data/engine.py` already writes frame-exact FCPXML. Its cleanup
exporter (`export_plan`) rebuilds the primary storyline from cut segments and refuses timelines with
titles, connected or retimed content, so it does **not** fit placement. Reuse these helpers instead:

- `ft()`: a `Fraction` to FCPXML time (`n/ds`), so times stay rational.
- `frame_count()`: raises if a time is off the frame grid; run it on every placed time.
- `tree()`: the safe XML parser settings (no entities, no network, no DTD load).
- `add_marker()`: inserts markers where Apple's DTD expects them.
- `workflow.validate_xml()` from `~/Tools/fcp-edit-workflow` (which `engine.py` imports): DTD and
  static validation of the written file.

Import or copy them; don't modify Cut Assist's code.

## Verify, and what "done" means

- Re-parse the written file: every master's computed timeline frame equals its planned frame, every
  cue sits on its cue-sheet frame, every file path exists, and every master's SHA-256 matches its
  approval. `validate_xml` passes.
- **The FCPXML counts as working only after Yuvraj imports it into Final Cut and confirms** that the
  clips land on the right words and the cues are separate editable clips on the Effects role. Until
  then report it as "written and validated, not yet imported". Never report it as done before that.
