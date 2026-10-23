# Concept to Visual: a Creator OS capstone (100x Engineers C7)

**Status as of 23 Oct 2026 (first written 7 Oct 2026, 23:50 IST). P2 delivered 15 Oct; Joel accepted it with no changes on 19 Oct. Final video: [f.io/dBF09OXt](https://f.io/dBF09OXt). Proof: [p2-review](p2-review/README.md).**

**Changelog since submission.** 23 Oct: Joel's review landed (WhatsApp, 17 and 19 Oct; no Frame.io comments); §a, §c, §g, §h and §i updated; final video link and proof in [p2-review](p2-review/README.md). Sections d to f are the 9 Oct state. 8 Oct: renders restored; placement FCPXML generated. 9 Oct: 44 renders (3 alpha overlays); 5 moments added; showcase rebuilt; approvals 0 standing at 23:50 ([P2-STATUS.md](P2-STATUS.md)). 9 Oct 2026, 23:55: section j added, the same workflow on two other creators, anonymized, outside the measured run; the hackathon gap table added to §g.

Every number links to its file. **Measured by AEM**: written by the tool from timestamps or file reads. **Reconstructed**: counted by hand. Client-folder figures are mirrored in [P2-STATUS.md](P2-STATUS.md) and the [snapshot](design-system-snapshot/SNAPSHOT.md).

## a. The trust signal

On P1 Joel gave 66 timestamped Frame.io notes ([ABOUT.md §13.1](ABOUT.md), [joel-review.md](design-system-snapshot/skill/mergetomaster-studio/references/joel-review.md)). After seeing the delivered video he wrote on WhatsApp on 5 Oct 2026 ([joel-decisions.md](design-system-snapshot/joel-decisions.md), entry 2026-10-05):

> "I really liked what you did with the other video so id like to try you mostly just adding in visuals that you feel like are appropriate at the time rather than me commenting what should go where."

On P2 he gave zero placement notes ([P2-STATUS.md](P2-STATUS.md)). That is the creator moving from directing every placement to accepting the editor's recorded standard: the Creator OS hypothesis in his words. P2 is the first test without his direction.

After P2 was delivered he wrote on WhatsApp ([p2-review](p2-review/README.md), screenshot and transcript), on 17 Oct 2026:

> "Hi, the intro is absolutely awesome 👌" · "I love it" · "You've done an amazing job here"

and on 19 Oct 2026, answering "No Changes in Claude Code Video?":

> "Hi, no I think its all ready to go :) happy for you to send me the invoice"

No change requests, and no comments on the Frame.io share page ([f.io/dBF09OXt](https://f.io/dBF09OXt)). P1 took 66 notes; P2 took none.

## b. The creator and the friction

Joel Belton runs MergeToMaster, narrated essays on AI and developer topics ([SKILL.md](design-system-snapshot/skill/mergetomaster-studio/SKILL.md)); 92 published pieces (operator-stated). He reviews the finished video on Frame.io, never individual animations, and never sees the process ([ABOUT.md §13.1](ABOUT.md)). P1, "Frontend Design", published 23 Sept 2026 ([p1-frontend-design.md](design-system-snapshot/skill/mergetomaster-studio/references/p1-frontend-design.md)). The friction: 66 notes for 58 visuals is the creator doing the editor's job.

## c. Hypothesis

From [P2-HYPOTHESIS.md](P2-HYPOTHESIS.md), written 7 Oct 2026 at G1 before any moment was designed:

> On a video with no placement notes, Joel's recorded standard (rules.md, his rulings, the no-unrequested-detail lesson, a critic reading rendered evidence) holds without his direction. Measured by: moments he changes on Frame.io, time per moment and per stage, and his words. Baseline: three moments made the ordinary way first. Negative result if he changes more of our moments than P1's rate or asks for fewer visuals again.

**Result, 23 Oct 2026 (reconstructed from his messages, [p2-review](p2-review/README.md#against-the-hypothesis)).** He changed 0 of P2's 47 named moments, against P1's 3 of 58 (5.2 %), and did not ask for fewer visuals. Neither kill condition fired. His words: accepted with no changes. The time half of the measure did not hold: AEM attributes no time to any single moment, and the three hand-made baseline moments were never made (§g).

## d. What was built

- **Design system v3.2**: [rules.md](design-system-snapshot/rules.md), 87 rule IDs with J/E/P/I tags, indexing the Brand, Motion and Edit Systems ([text exports](design-system-snapshot/text/)); [joel-decisions.md](design-system-snapshot/joel-decisions.md), Joel's rulings verbatim.
- **The `mergetomaster-studio` skill**, seven gates G1 Inputs to G7 Joel's review ([SKILL.md](design-system-snapshot/skill/mergetomaster-studio/SKILL.md)).
- **AEM 1.1.0 as a notary**: observes and records, never blocks ([ABOUT.md](ABOUT.md)); check and evidence per render ([CLI.md](CLI.md)); moments as the unit of work; `aem calibrate` reads the client's rulings ([registry/clients.json](../registry/clients.json)).
- **Tests**: 218 CLI and 54 plugin tests pass at 1.1.0 ([ABOUT.md §8](ABOUT.md), [tests/](../tests), [plugin](../plugin/aavkar-educational-motion-studio/tests)).

## e. P1 baseline, reconstructed

From P1's real placement files ([ABOUT.md §13.2](ABOUT.md), [tests/fixtures/p1](../tests/fixtures/p1)): 58 moments, 50 asked, 8 added. Joel's 3 changes ([joel-decisions.md](design-system-snapshot/joel-decisions.md), entry 2026-09-14) all removed unrequested detail inside asked scenes: a one-frame website flash, two captions describing a visible demo. No addition was removed. Lesson: nothing the viewer didn't need. Retrospective counts.

## f. P2 so far

All from [P2-STATUS.md](P2-STATUS.md), generated by [p2status.py](tools/p2status.py) from `aem moments`, `aem report` and `events.jsonl`. The animations: [showcase](showcase/README.md).

| Figure | Value | Source |
|---|---|---|
| Named moments planned | 47 (40 visual, 6 "nothing") | `aem moments`, measured |
| Treatments | animation 20, footage 8 (3 alpha overlays), screen recording 8, nothing 6, re-typeset terminal 5 | `aem moments`, measured |
| Moments with a checked render | 39 of 40 visual; 44 render files | `events.jsonl`, measured |
| Render versions checked / failed | 79 / 5 (3 short flashes; 4 overlays the spec did not expect alpha on) | `events.jsonl`, measured |
| Approved renders | 0 standing at 23:50; 1 stale (`cc_S00_agenda_v02`, superseded by v03) | `approvals.jsonl`, measured |
| G2 (plan) wall / agent busy | 11:43:58 / 2:39:12 (8:49 idle) | `aem report`, measured |
| G4 (build) wall / agent busy | 5:33:57 / 5:11:14 | `aem report`, measured |
| Minutes per built moment | about 9 wall (5:33:57 ÷ 39); 33 of 50 observed hours ran outside any stage | reconstructed |
| Baseline-by-hand minutes | none: the hand-made baseline was dropped on 7 Oct (P2 `inputs.md`) | measured absence |
| Flash scans | 14 of 79 render versions flagged 1–2 frame luma flashes at 0.02–0.04 % of frame | `check-render`, measured |
| Max sync offset, latest renders | 0f to 36f at 25 fps | `aem evidence`, measured |

## g. Negative results and what they changed

- **The guard blocked a day's work and was removed.** 0.7.0 built it; 1.0.0 made AEM a notary ([ABOUT.md §12](ABOUT.md), commit `705c5b3`). 5 denials from 6 Oct remain in `events.jsonl`.
- **The "3 of 13 additions" claim was wrong.** The brief expected 45 asked and 13 added; the real placements give 50 and 8, and the 3 changes sat inside asked scenes ([ABOUT.md §13.2](ABOUT.md)). `aem calibrate` still prints "3 of 58" for P1: development data.
- **P1 numbers are retrospective.** AEM postdates P1.
- **The hand-made baseline does not exist.** Built by the pipeline instead (P2 `inputs.md`); the control is gone.
- **What the September hackathon left open, and where each item stands** (from the 5 Oct build plan): no numeric hypothesis with a kill condition, closed by [P2-HYPOTHESIS.md](P2-HYPOTHESIS.md); creator rewrite minutes never measured, open until Joel's review; hours saved was a modelled estimate, half closed (AEM measures stage time, no hand-made baseline); one paid delivery's creator had 15 published pieces against the project's own 20-piece rule, still 15; claim and archive checks partial, closed per render by `aem evidence`. The hackathon counted two paid deliveries with the creators' words and 3 and 0 corrections; those records predate the capstone and are reconstructed.
- **`aem moments` over-counts.** 68 rows for 47 moments; 21 are table headings from the plan ([P2-STATUS.md](P2-STATUS.md)).
- **Renders were off disk at the 7 Oct snapshot.** Back on 9 Oct; every check's record stands in `events.jsonl`.
- **The master went out with 0 standing approvals.** P2 was delivered on 15 Oct with no approval tied to any render in it, and `events.jsonl` has no delivery event: the master was exported from Final Cut, which AEM does not observe. The notary recorded the build, not the hand-off (measured, [p2-review](p2-review/README.md#what-aem-recorded-and-what-it-did-not)).
- **`aem accept-video` does not fit a mixed delivery.** It takes one version string; P2's delivered moments sit at v01 to v06, and `moments/index.json` predates the delivery. Joel's acceptance cannot be recorded per moment until AEM can accept each moment's delivered render.

## h. Not done

- Joel's words in the ledger: his 17 and 19 Oct messages wait for the operator's `aem client-said` (the CLI refuses an agent). The [joel-decisions.md](design-system-snapshot/joel-decisions.md) snapshot stays at 9 Oct until then.
- Per-moment acceptance (`aem accept-video`): blocked, see §g.
- Critic calibration: 3 development cases, 0 rulings in Joel's words; `calibrate` needs 30 ([ABOUT.md §13](ABOUT.md)). Joel's P2 review is video-level and adds no per-moment cases.
- The full acceptance test ([tests/acceptance](../tests/acceptance)).

## i. Next

- Done: P2 delivered on Frame.io 15 Oct ([f.io/dBF09OXt](https://f.io/dBF09OXt)); Joel's review 17 and 19 Oct, accepted with no changes ([p2-review](p2-review/README.md)).
- Operator: `aem client-said` for the 17 and 19 Oct messages, then `aem calibrate` and `aem report`.
- AEM: let `accept-video` take each moment's delivered render; observe the delivery itself.
- Not done from the 10 Oct plan: the external-operator run and the hand-timed baseline moment.

## j. Beyond Joel: the same workflow on two other creators (outside the measured run)

Facts from the project folders, read 9 Oct 2026. No names, channels, footage or links. Nothing here enters the P2 numbers above.

**Creator B, an engineering/build YouTuber.** On 6 Oct he asked for a 30 to 60 s test edit from 5 min of raw footage, and for project files, not just renders. On 7 and 8 Oct a design system was built for him before the edit: five documents (Brand, Motion, 3D, Edit, Sound), a generated `rules.md` with 127 rule IDs (Brand 33, Motion 27, 3D 19, Edit 37, Sound 11), and a decisions file holding his own words as 10 dated quotes and 6 logged open questions, each with the working assumption it rests on. The trial then ran ten versions in two days, each with a README and a review export:

- v001, 7 Oct: first cut, 43.5 s, kept for reference.
- v002, 8 Oct: accuracy pass, every label and sound rebuilt from a measured timing spec, 38.3 s.
- v003, 8 Oct: full-screen 3D stepper explainer added, library music. Its coil lighting was wrong (all four poles lit equally; a two-phase stepper alternates polarity).
- v004, 8 Oct: one assembling music theme. Rejected for vibe.
- v005, 8 Oct: music matched to his current videos.
- v006, 8 Oct: three audio fixes from the operator's notes.
- v007, 8 Oct: Part 2 starts on the action, 15 frames trimmed, 37.8 s.
- v008, 8 Oct: ending lands on the freeze; ducking fixed.
- v009, 8 Oct: every music transition audited.
- v010, 9 Oct: the v003 polarity error caught by a full accuracy check and fixed; the bright pole pair now turns 45° per step while the rotor clicks 1.8°, and the Blender script aborts the render if rotor and coils disagree.

Tools: HyperFrames overlays as ProRes 4444 with alpha, scripted Blender for the 3D, scripted FCPXML, plus a Resolve project. He replied on 9 Oct, after watching: "the edit is good, the animation is excellent"; the sections of his current video with b-roll or mediocre graphics "could benefit from your animations"; then an offer of paid work. What it shows: a second creator, in a different genre, named the problem in his own words and acted on the result, and the rule index plus decisions ledger were built for him in two days. What it does not show: AEM did not run, it is one trial of about 38 s, and none of it is in the P2 figures.

**Creator C, a fitness YouTuber.** Video 12, delivered 26 Sept 2026 as V6, before AEM existed. Its animations were built with Claude Code and Codex from an `AGENTS.md` contract of 286 lines (6,968 words) that fixes the delivered audio as the source of truth over the written script, the specs, the naming, and 22 shots mapped to audio windows. The folder holds 206 render files across 24 shots, and 35 finished animations across 26 shots in the done folder. Client ruling not recorded here. What it shows: the before. Same editor, same tools, a written contract, and no record of what the client ruled, which render was approved, or how long each shot took.

