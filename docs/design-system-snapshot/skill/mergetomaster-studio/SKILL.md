---
name: mergetomaster-studio
description: >
  The production studio for Joel Belton's MergeToMaster (Merge to Master) YouTube channel: how
  every animation, motion graphic, title, overlay, B-roll choice, sound cue and delivery for his
  videos is planned, built, critiqued, placed in his timeline and reviewed, using the channel's
  design system in "00 - MergeToMaster Design System". Use for any Joel / MergeToMaster video work:
  a new video's visual plan or brief, a scene, a revision or review from his Frame.io comments, a
  critique, a render, an FCPXML placement, a delivery. Also use when a request mentions rules.md
  rule IDs, joel-decisions.md, the Brand, Motion or Edit System, the studio gates, or a P1/P2/P3
  project. It decides what is right; the HyperFrames skills do the building. Not for other clients
  or generic motion-graphics questions.
---

# MergeToMaster Studio

Joel's videos are narrated essays (AI and dev topics, talking-head A-roll). Every graphic exists to
make the viewer **understand, notice, compare or feel** something the narration needs. Purpose comes
first; everything except the invariants bends for a stated reason.

## The design system is the source of truth

Home: `/Volumes/T7 Red/Yuvraj Folder/Freelance Work/Joel Belton - MergeToMaster/00 - MergeToMaster Design System/`

If that folder is readable (Claude Code on Yuvraj's Mac), it is the master: always read from it.
If it is not (Claude chat, another machine), use the snapshot bundled with this skill in
`system/` (see `system/SNAPSHOT.md` for its date and hashes), say that you are working from a
snapshot, and note anything that may need checking against the master. Its files sit flat in
`system/` (so `text/MergeToMaster - Motion System.md` is `system/MergeToMaster - Motion System.md`).
The snapshot now holds the text versions of Brand and Motion, so chat has the reasoning, templates
and render recipes, but not `critic/labelled-cases.jsonl`. Chat
still can't run tools, read the drive or reach Cut Assist, so word timing, renders, checks and
FCPXML belong in Claude Code.

| Read | When | What it gives you |
|---|---|---|
| `joel-decisions.md` | **First, every time** | Joel's own words and rulings, dated and scoped. The **J** source. His rulings beat our defaults. |
| `rules.md` | Before planning, and to cite in every brief, critique and override | Every rule with an ID and kind: **Invariant**, **Joel default**, **Default**, **Option** |
| `text/MergeToMaster - Motion System.md` | Planning, choreography, the studio workflow, production, QC | Teaching jobs, motion vocabulary, voice sync, cues, patterns, the gates, the critic rubric, scene brief, production contract, render recipes |
| `text/MergeToMaster - Brand System.md` | Colour, type, frame, evidence, generated media, formats | Purpose tiers, colour map, type floors, safe areas, specimen rules, reference analysis, project brief, CSS starter |
| `MergeToMaster - Edit System v1.md` | The edit: timeline, cut, pacing, sound mix, music, captions | Editorial context. Brand and Motion win where they differ. |
| `Handbook/Educational YouTube Animation Framework.md` | Craft judgement, diagnosing a failed shot | Lessons from Frontend Design (P1) |
| `critic/labelled-cases.jsonl` | Calibrating or reporting on the critic (G5, G7) | Joel's rulings on delivered shots, the critic's golden set |
| `README.md` | Starting a project, changing the system | Folder map, project start steps, how rules change |

**Never read the Brand or Motion HTML pages directly.** Each is over 1 MB of embedded fonts and
images. The `.md` files in `text/` are generated from them by `tools/export-text.py`; the HTML pages
are the human-readable versions. If a text version's header hash or date looks older than its page,
re-run the script (Claude Code) or say so (chat).

`rules.md` carries every rule ID; the text versions carry the reasoning, templates and render recipes.
The pages themselves contain no rule IDs; `rules.md` gives each rule's page and section. Read
`rules.md` and `joel-decisions.md` in full, and the text versions' sections as you need them. Never
copy rule text into project files or this skill; cite the ID.

Precedence: **invariants** (B-T1-01…05, M-T1-01…05) > the user's latest specific instruction >
`joel-decisions.md` > `rules.md` defaults > craft habits. A user instruction cannot override an
invariant; say so and offer the nearest safe alternative.

## The studio: five layers, never collapsed into one prompt

Generic output comes from missing decisions that the model fills with its safest default. Make the
decisions before rendering.

| Layer | Artifact in the project folder |
|---|---|
| Director | `brief.md`: the one sentence the viewer should remember, teaching job per scene (M-01), facts (from real assets) vs choices (open to us), what would be unacceptable |
| Reference | `style-guide.md`: reference analysis on top of the Brand System, this video's colour map (B-02), DO NOT COPY |
| Timeline | `shotlist.md` + cue map: per M-17 (knows before, knows after, must stay true, why it exists); sound cues (M-25) |
| Renderer | Seekable HyperFrames scenes |
| Critic | `reviews/`: contact sheets, rubric results, top-three defect notes |

If Joel left placement open, write `visual-plan.md` first (M-16).

## Workflow: seven gates

Stop at each gate, show the artifacts, and wait for approval. Work autonomously between gates and
resume from the last gate passed. A gate is passed when its artifacts exist, not when a command
exits cleanly (M-20). G1–G6 are Motion's six gates; G7 is this skill's addition, to be written into
Motion and `rules.md` at the next system change.

At every gate's start and finish, and whenever work waits on someone, append a line to the
project's `events.jsonl` (`references/project-ledgers.md`).

1. **G1 · Inputs.** Expect from Yuvraj: the video (the current cut, or Joel's recording), Joel's
   script, and his footage and assets (Frame.io downloads, screen recordings, B-roll). Read Joel's
   message or brief and `joel-decisions.md`. Then produce three artifacts before any planning:
   - **Word map** (`data/words.json`): every spoken word with a stable ID and timeline time accurate
     to a frame, by `references/word-timing.md` (M-03). Start from Cut Assist's alignment when the
     cut went through it. What Joel *said* beats the script; his scripts often cover only part of a
     video.
   - **Footage inventory** (`footage-inventory.md` + contact sheets): every file Joel has provided,
     what it shows, its specs and problems, and which lines it could serve, by
     `references/footage-inventory.md`. Check this before deciding anything needs building.
   - **Inputs list**: the edit's exact frame rate as a rational (`fps_num/fps_den`, read from the
     timeline), references, and every missing asset as a **blocker** (B-T1-02).
2. **G2 · Plan.** `style-guide.md` and `shotlist.md` (plus `visual-plan.md` if placement is ours).
   Every shot names its teaching job and why it exists; a shot that can't say why is cut. For each
   moment, choose the source in J-01's order, starting from the footage inventory.
3. **G3 · Stills.** Yuvraj approves fully styled stills for one representative scene per teaching
   job. The other scenes' stills go into the G4 contact sheets. Settle the frame before animating it.
4. **G4 · Rough render.** Build in HyperFrames (pinned per video, M-22), render, produce contact
   sheets and a narrated proxy. Sync is measured in frames (M-03). Every render gets its evidence
   (`reviews/<moment>/<version>/evidence.md`: readable poses, phone-size crops, a strip around the
   fastest transition, sync per cue word, the render check), built by AEM after the render or with
   `aem evidence <render>`; the critic reads that, never the source. After Yuvraj approves, append each
   approved render to `approvals.jsonl`.
5. **G5 · Critique and repair.** Give the critic (below) each render's `evidence.md` and the images it
   names, never the scene source; its findings cite the image and the rule ID. Repair per M-19;
   re-render only the affected frames. Before delivery, review moments in context with
   `aem evidence --video <cut>` (a contact sheet of the assembled cut per moment).
6. **G6 · Deliver.** Masters per format, cue sheets, poster frames, photosensitivity log (M-23),
   verification record, delivery copies updated, and a note of what still needs human review. Plus:
   - **Placement FCPXML** that puts each master at its word ID on the current timeline, with each
     sound cue as its own editable audio clip on the Effects role, by
     `references/fcpxml-delivery.md`. It counts as working only after Yuvraj imports it into Final
     Cut and confirms; until then it is "written and validated, not yet imported".
   - **Approvals:** place or deliver only renders whose SHA-256 matches their approval; after
     Yuvraj approves the delivery, append it to `approvals.jsonl`.
   - **Time:** write `reports/time.md` from `events.jsonl`.
7. **G7 · Joel's review.** The system learns from every delivery, by `references/joel-review.md`.
   Joel reviews the finished video, never the process. After delivery, wait for Frame.io; import his
   comments (CSV) with `aem import-review`, which maps each to a moment and its word IDs at the
   delivered edit's frame rate (outside every moment: a video-level remark). Attach any WhatsApp
   feedback with `client-said --about <moment|video|channel>`. When he accepts the video, Yuvraj runs
   `accept-video <version>`: silence on a moment is an implicit acceptance only once the whole video is
   accepted, and never an explicit ruling. Never ask Joel to rule on individual animations unless he
   offers. Add a dated entry to `joel-decisions.md` in his exact words; report the critic's agreement
   with `aem calibrate` (M-19); update `reports/time.md`.

For a revision of an existing scene (Joel's notes, a bug): read his note, the exact narration line and
the next point (M-15), the current source **and the actual encoded render**; name the failure and its
viewer consequence; propose one approach; change only that scene; then run gates 4–7 for it.

## Approvals are tied to the exact render

An approval at G4 or G6 covers one file: gate, scene, render path, render SHA-256, source revision,
approver and date, appended to the project's `approvals.jsonl`. Placement and delivery refuse any
render whose SHA-256 doesn't match its approval; a changed render needs a fresh approval. This is a
recorded check, not a security boundary. Details: `references/project-ledgers.md`.

## When Aavkar Educational Motion Studio (AEM) is loaded

- AEM records the work (every stage, tool call, render check, approval and quote of Joel's) and never blocks it.
- Never write the record files yourself, with any tool: `events.jsonl`, `approvals.jsonl`, `joel-decisions.md`, `critic/labelled-cases.jsonl`.
- When an approval, a rejection, a quote of Joel's or a stage change is needed, ask Yuvraj in one sentence, naming the command (`/approve fd_S01`), and continue once Yuvraj has run it.

## The critic

- **Inputs:** the render's `evidence.md` and the images it names (poses, phone crops, strip, `sync.json`,
  `facts.json`), which carry the shot list's "knows after" and "must stay true", and
  the rubric, per M-18 and M-19. Never the scene source or the builder's explanation. Use a fresh
  subagent where possible, given `evidence.md` alone.
  The rubric and the frames to observe are in Motion section 06 (`text/MergeToMaster - Motion System.md`).
- **Score meaning first:** does the frame assert only what "must stay true" allows (M-18)? Then the
  rest of the rubric. Every finding cites the image it is seen in and its rule ID, and the critic writes
  them to `critic.json` beside `evidence.md` (`verdict`, `findings`: rule, image, note) so G7 can score it.
- **Graders:** code, model and human (Motion 06); code and human outrank the model.
- **Status:** the critic advises and does not gate until about 30 labelled cases in
  `critic/labelled-cases.jsonl` agree with it (M-19). Record its verdict per shot so G7 can score it.

## Overrides

Any non-invariant rule may bend when the video's purpose needs it. Log it in the scene brief and in
QC in B-28's format. Overrides of a **Joel default** are flagged to Yuvraj in the final message.

## Build stack

This skill decides what is right; these skills and sources do the building.

| Need | Use |
|---|---|
| Composition contract, timing attributes, deterministic render | `hyperframes-core` |
| Motion patterns, GSAP, text effects | `hyperframes-animation` |
| Camera moves, punch-ins, keyframes | `hyperframes-keyframes` |
| check, snapshot, preview, render | `hyperframes-cli` |
| Registry blocks | `hyperframes-registry` |
| Logos, footage, audio, treatments | `media-use` |
| Word timings from a cleaned cut | Aavkar Cut Assist MCP, read only (`references/word-timing.md`) |
| Sound | Cues per M-25 and J-05, on the same GSAP labels as the picture. Joel's Epidemic Sound and Envato libraries first. No generated SFX until Joel answers that open question in `joel-decisions.md`. |
| Placement in Joel's timeline | FCPXML by `references/fcpxml-delivery.md`, reusing Cut Assist's frame-exact helpers |

## Files this skill and its projects use

| Where | File | Holds |
|---|---|---|
| Design system | `rules.md`, `joel-decisions.md`, `text/*.md`, `critic/labelled-cases.jsonl` | Rules, Joel's rulings, the readable pages, the critic's golden set |
| Design system | `tools/export-text.py` | Regenerates `text/` from the HTML pages |
| Skill | `references/word-timing.md`, `footage-inventory.md`, `fcpxml-delivery.md`, `joel-review.md`, `project-ledgers.md`, `p1-frontend-design.md` | Procedures for G1, G6, G7, the ledgers, and the P1 case study |
| Project | `brief.md`, `style-guide.md`, `shotlist.md`, `visual-plan.md`, `footage-inventory.md` | The plan |
| Project | `data/words.json`, `data/transcript-final.txt` | The word map |
| Project | `approvals.jsonl`, `events.jsonl`, `reports/time.md` | Approvals and time |
| Project | `reviews/`, `reviews/joel/`, `out/` | Critic output, Joel's comments and rulings, masters, cue sheets, FCPXML |

## Communication

Short progress updates while working. The final message says what changed, where it is, what was
verified (with artifacts), any override and any real limitation. Never call a source edit "rendered",
an unopened file "checked", an unverified export "done", or an FCPXML "working" before Yuvraj has
imported it.

## Keeping the system current

When Joel rules on something, add it to `joel-decisions.md` first, in his words, with its scope; then
update `rules.md` and the system page, following `README.md` ("Changing the system"), and re-run
`tools/export-text.py`. A one-video exception is an override, not a rule change. Lessons from
Frontend Design specifically are in `references/p1-frontend-design.md`; they are examples, not
channel law.

## What changed in v2 (6 October 2026)

Skill versions are separate from the design system's. Skill v2 works with Brand System v3.2, Motion
System v3.2 and Edit System v1.1. If the pages' version (in the `text/` headers) is newer than these,
check this skill against the pages' "What changed" tables before relying on it.

- Reads the generated text versions of Brand and Motion, never the 1 MB HTML pages.
- Rule text replaced by rule IDs; the shot list and critic now follow v3.2 (M-17, M-18, M-19).
- Frame rate recorded per edit as a rational; word timing can start from Cut Assist's alignment.
- G3 approves stills for one representative scene per teaching job.
- G6 adds a placement FCPXML with editable sound cues; approvals tied to each render's SHA-256.
- New G7: Joel's review feeds `joel-decisions.md` and the critic's labelled cases.
- 7 October 2026: G4–G5 read AEM's `evidence.md`; G7 follows how Joel reviews (the finished video on
  Frame.io, each ruling at its level, `accept-video` once he accepts the whole video).
- Time per gate and scene logged in `events.jsonl` and reported in `reports/time.md`.
- The chat snapshot now includes the text versions of Brand and Motion.

v1 is archived in `System Archive/2026-10-06-skill-v1-before-v2/`.
