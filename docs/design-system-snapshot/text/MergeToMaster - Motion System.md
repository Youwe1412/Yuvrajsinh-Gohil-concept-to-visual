Generated from MergeToMaster - Motion System.html (SHA-256 d41ca9a92547ebd4) on 2026-10-06. Do not edit; edit the HTML and re-run.

*Motion system · v3.2 · 05 October 2026*

# MergeToMaster Motion System.

Motion exists to show a change the viewer needs to understand. Land it with the word, give it time to be read, then let it rest. Every number below is a default the scene's teaching job can change; only safety, determinism and honest verification are fixed.

- **Basis** Frontend Design production + October 2026 research
- **Design space** 1920 × 1080 · frame rate from each edit
- **Renderer** HyperFrames, pinned per video
- **Companion** Brand System v3.2

> **Note · Scope & precedence**
>
> Use v3.2 for every MergeToMaster animation project. It replaces v3.1 (kept in [System Archive / 2026-10-05-v3.1-before-v3.2](../System%20Archive/2026-10-05-v3.1-before-v3.2/)) and every motion and sound-design rule in the Edit System; Edit System v1.1 now covers only the edit itself. Frame rate is a delivery setting taken from each edit (P1 was 24000/1001, P2 is expected at 25); frame counts below are given for 23.976 unless stated. Evidence: [Claude Opus educational motion graphics](../reports/Claude%20Opus%20educational%20motion%20graphics.md). Tags: [J] Joel's own words, rulings or published videos, [E] peer-reviewed evidence, [P] documented practice, [I] inference to test on Joel's videos. Rule IDs, sources and status: [rules.md](../rules.md). Joel's dated rulings: [joel-decisions.md](../joel-decisions.md). Tool versions, model capabilities and prices are as of 5 October 2026; re-check them before relying on them.

## 00 · Motion earns its place by explaining a change

Animation on its own buys little: across meta-analyses it beats a static picture by only g 0.23–0.37. It pays when it shows the very change being taught (d 0.40), when it demonstrates a procedure (d 1.06), and when a diagram is drawn in step with the voice rather than shown pre-drawn (d 0.54). Decorative animation measures at zero (g −0.05), and long animated stretches lose to static pictures because each frame overwrites the last [E]. The onset of motion captures attention; continuous motion does not [E]. So every movement should answer one question: **what is changing, and why does the viewer need to see it change?**

- **01 · Establish**: Give the viewer a readable object or question.
- **02 · Demonstrate**: Change the thing being explained, on the word.
- **03 · Resolve**: Make the consequence visible.
- **04 · Hold**: Let the viewer read, then let the edit cut.

#### Tier 1 · never bends · Invariants

- **Viewer safety:** no more than three flashes in any second over a quarter of the frame; every final render checked [P]
- **Determinism:** the same frame from playback, a backward seek or a direct seek
- **Legibility:** text the viewer must read is never on a moving layer while it is being read
- **Exact delivery:** rational fps, frame-exact durations, verified alpha
- **Honest verification:** every claimed pass has a saved artifact

#### Tier 2 · bends for a stated purpose · Defaults

- Durations, eases, staggers and holds
- No overshoot on teaching objects; no ambient loops
- Exits left to the edit; final pose held
- One active cue at a time
- Pacing envelope set by the teaching job

#### Tier 3 · switch on when the job needs it · Options

- Motion blur on one to three snap beats
- A restrained settle on brand and punchline moments
- Camera moves, zooms and match cuts
- Stepped "on twos" evidence-board look
- 3D, Lottie, GPU effects, speed ramps
- Generated plates under code-rendered graphics
- Expressive kinetic type for tone

> **Note · Overrides are cheap and visible**
>
> Break any tier-2 default when the shot's purpose needs it. Log one line in the scene brief: **teaching job · default overridden · reason · how it was verified**. Purpose wins every tier-2 argument and none in tier 1.

> **Note · Current implementation**
>
> Frontend Design's scenes are built by `lib/scenes.js` with `lib/refinement.css`. The retained `lib/motion.js` and older motion notes are history; their five-curve presets are not the current behaviour.

## 01 · Teaching jobs set each scene's envelope

Every scene brief names one job. The job sets the default pace, ease and hold. The envelopes are starting points to check against Joel's retention graphs [I].

| Teaching job | What motion must do | Default envelope | Grounding |
|---|---|---|---|
| Hook / re-hook | Make the promise concrete; state the misconception that will be overturned. | A change of state every 2–5s; face and graphic alternate; a brand settle allowed; re-hook at chapter starts. | Misconception-first beats clear exposition (refutation g 0.41; in video 0.79–0.83) [E]; YouTube's intro window is the first 30s [P] |
| Refute a misconception | State the wrong idea concretely, let it stand a beat, then overturn it with evidence. | The misconception is shown, not mocked; the disproved claim recedes to dim; the correct model is built in the same frame. | Refutation g 0.41 (44 comparisons); misconception-first video 0.79–0.83 [E] |
| Cast of characters | Name a system's parts before they move. | Static, labelled layout; 2–3-word labels; hold until each part is named. | Pre-training (single-lab evidence) [E] |
| Mechanism / process | Animate the change itself inside one persistent canvas. | Build the system part by part; 10–30s scenes with an internal change every 2–4s; tracked transitions 0.5–1.25s, ease-in-out, staged; at most 3–4 tracked objects; no overshoot; end on a held summary. | Representational animation; transience; slow-in/slow-out tracking [E] |
| Connect / vary together | Move one object into another; change linked quantities in lockstep. | The same node travels from state to state; no invented in-between states. | 3Blue1Brown's teaching roles; object constancy [P] |
| Evidence | Source, then enlarged passage, then mark as spoken, then hold. | Native capture; highlight paced to the phrase; unnarrated text 0.375s/word + 1s. | Signalling + contiguity [E]; BBC timing [P] |
| Comparison / statistic | Same input, stable positions, real values on the spoken figure. | Builds that accumulate; shared denominators; no count-up unless counting is the point; natural frequencies and icon arrays, never "1 in X"; end on a static frame that states the claim. | Natural frequencies and icon arrays [E] |
| Code walkthrough | Keep the whole relevant snippet visible; move the highlight with the narration. | 5–15 lines; enlarge or highlight the discussed line; hold unnarrated code long enough to scan. | Code is read non-linearly; live, step-by-step code is at least as good as static [E] |
| Procedure / UI demo | Faithful UI, first-person view, purposeful pointing. | Real or faithfully rebuilt UI; pointer stops on the target while it is named; the camera widens after the build. | Procedural d 1.06, realism d 0.76; intermittent pointing [E] |
| Verdict, reaction, joke | Land abruptly; allow dead air. | One-frame cut, then hold; jokes related to the idea, kept out of dense mechanism stretches. | Related humour helped (d 0.49); fast pace with arousing content overloads [E] |
| Chapter / brand moment | Re-entry, orientation, personality. | One grammar for every chapter card; one restrained settle; chapters of 10s or more. | Viewers scrub to visual transitions (61% of interaction peaks) [E] |

## 02 · A vocabulary, not a compulsory preset

The previews play the helper defaults at small scale; they are teaching demonstrations, not composition code. Real shots set duration by the job and the distance travelled.

### Reveal

Lift and fade into the argument.
`power3.out · typically .20–.45s`

### Unmask

A spoken phrase rises from a stable edge.
`power4.out · typically .30–.60s`

### Cut

A verdict or reaction lands at once.
`1 frame · 41.7ms at 23.976`

### Mark

A highlight grows across its evidence.
`power3.inOut · .22–.55s`

### Transition

An element the eye must track moves state.
`ease-in-out · .5–1.25s, staged`

### Quiet appearance

Context arrives without taking over.
`power2.out · .12–.30s`

| Action | Starting point | Purpose and evidence |
|---|---|---|
| Arrival (reveal) | Opacity + 8–38px lift; .20–.45s; power3.out. Frontend Design's median across 215 calls was .28s, a habit of that film, not a target. | Entrances decelerate; duration grows with distance and area [P]. |
| Spoken phrase mask | yPercent 112→0; .30–.60s; power4.out. | Reveal from a readable edge; whole phrases, never word-by-word RSVP [E]. |
| Tracked transition | .5–1.25s, ease-in-out; stage complex changes (axis first, then values). | Slow-in/slow-out beat constant speed for tracking; staging helps; animated transitions beat instant cuts for following what moved [E]. |
| Stagger | .09–.16s between list items that only need to arrive. | Don't stagger elements whose identity the viewer must track; it doesn't help and may hurt [E]. |
| Simultaneous motion | At most 3–4 moving objects; 1–2 when identity matters. | Multiple-object tracking capacity [E]. |
| Highlight / structural wipe | scaleX from the left; .22–.55s; power3.inOut. Paper marks often .34s. | Colour on the object is the strongest cue [E]. |
| Path trace | Dash offset to zero; about .6s; power2.inOut. | Draw the real path in step with the voice [E]. |
| Zoom / camera | Zoom in to concentrate the eye on a small target; zoom out to reset context. | Zoom-ins concentrate gaze; zoom-outs behave like a static shot [E]. |
| Verdict | One frame at the edit's rate; ease none; then hold. | Abruptness is the statement. |
| Uniform progress | Linear when speed means something (a marker on a path, measured flow). | Representational loops only. |
| Slow push | sine.inOut; 1.2–1.45s; scale +2.5–4.5%; once. | A held phrase leaning into its word. |
| Pointer press | Arrive .38s power2.out; press to .97 for .10s; release .16s. | Arrival and response read as one causal event. |

### Character within restraint

- **Overshoot:** never on values, bars, counters, progress or causal arrows, because the overshoot frame briefly shows a false value. Brand cards, punchline words and chapter stamps may take one settle of about 3–8% with a stated reason.
- **Loops:** ambient motion with no meaning stays off teaching frames (persistent irrelevant detail costs most, g 0.43) [E]. Representational loops, such as a flow's direction or a cycle that really repeats, are welcome.
- **Motion blur:** HyperFrames has offered it since v0.8.45: a `data-hf-motion-blur` component (After Effects look) and an engine shutter (180° default). Use one, never both, on one to three snap beats per scene; text lands sharp [P].
- **On twos:** a stepped look at half the edit's rate (12fps in a 23.976 edit, 12.5 in a 25) can give evidence boards a handmade, editorial feel; watch high-contrast edges for strobing [P].
- **Kinetic type:** no evidence it improves learning; spend it on titles, jokes and tone, and let must-read text land whole and stay still [E].

### Motion rules by class of object

Write one rule per class of object, so similar things always move alike. The test after every move: does the viewer know where to look? [P]

| Class | Default | Never |
|---|---|---|
| Headline, title, question | Fast, decisive entrance; long stable hold. | Drifting while it is being read. |
| Data, values, bars, causal arrows | Ease-in-out to the exact value; staged. | Overshoot, which briefly shows a false value. |
| Panels, cards, containers | Controlled settle (spring damping 0.8–0.95). | Bounce. |
| Micro UI: buttons, toggles, chips | Quick snap. Overshoot only when the real interface does it, and then it is specimen behaviour. | An invented spring on a quoted product. |
| Camera | Slow, near-invisible, keeps orientation; zoom in to focus, out to reset. | Whips, spins, movement under must-read text. |
| Evidence: papers, posts, screenshots | Still; only the marks move. | Wobble, tilt or float. |
| Pointer | Travel, stop on the target while it is named, rest or hide. | Wandering. |
| Brand, chapter stamp, mascot, punchline | Playful and clearly intentional; one settle or spring. | Leaking into teaching objects. |

### Springs, the seekable way

Springs express weight better than a generic curve, but a running physics simulation cannot be seeked: frame 240 must render without replaying frames 0–239. Write the spring in closed form as a pure function of progress, which GSAP accepts as an ease. If everything springs, nothing feels precise, so use it only where the class table allows it.

### Closed-form spring ease

```
// Damped spring as a GSAP ease: a pure function of progress, so seek-safe.
// zeta 0.8–0.95 = controlled settle (panels); 0.5–0.7 = visible spring (brand moments).
function springEase(zeta = 0.85, omega = 12) {   // 0 < zeta < 1
  const wd = omega * Math.sqrt(1 - zeta * zeta);
  const x = p => 1 - Math.exp(-zeta * omega * p) *
    (Math.cos(wd * p) + (zeta * omega / wd) * Math.sin(wd * p));
  const end = x(1);
  return p => x(p) / end;                        // lands exactly on 1
}
tl.fromTo(stamp, { scale: .92 }, { scale: 1, duration: .6, ease: springEase(.6, 14) }, 'w431');
// Retargeting mid-move: add the response to each target change; still a function of time.
```

### How things leave inside a shot

| Why it goes | Treatment | Example |
|---|---|---|
| Superseded by the next beat | Opacity to 0, optional ~10px lift; .12–.22s. | "Feels AI-generated." clears for "What makes it feel that way?" |
| Still context | Recede to .28–.45 opacity and stay. | Parallel chips stay faint so the viewer sees what 70% was made of. |
| Refused by a person | Red strike in .22s, then the word dims. | The generic prompt; each exclusion. |
| Disproved by evidence | Recede; never strike. | Trust's wrong answers. |
| Changing hierarchy | Move or re-role the same element; .38–.66s power3.inOut. | FIRST IMPRESSION becomes the label over 50ms. |
| End of the master | Hold the completed pose. | The editor owns the cut. |

## 03 · Time to the voice; pace by the content

**The visual landing with the spoken word is the strongest lever in the evidence (temporal contiguity, g 0.78)** [E]. The idea should become readable when Joel says it. Start early enough for the readable pose to coincide with the stressed word; there is no fixed lead in frames.

### Cue map from forced alignment

| Step | Tool | Why |
|---|---|---|
| Draft transcript | `hyperframes transcribe` (Parakeet) or WhisperX | Fast; stable `w0, w1…` word IDs. |
| Final cue times | Montreal Forced Aligner against the approved script | 89.4% of word boundaries within 50ms on read speech vs 82.4% for WhisperX; about one frame at 23.976 or 25 [E]. |
| Labels | GSAP labels named by word ID | A re-recorded line regenerates labels, not tween times. |
| Check | Label time minus word onset, in frames | The model can't hear the narration, so sync is measured, not judged. |

> **Note · Motion must not argue with the narration**
>
> The cartoon rings once drew one at a time, a forensic three-point inspection, under "You don't need to zoom in to check how many fingers the character has." All three marks now land together on "but you know, it's AI" and withdraw during the line about not needing to look. Read the line, its paragraph and the next point before choreographing.

### Reading, holds and segments

- **Narrated text follows the voice.** Unnarrated text gets about 0.375s per word plus 1s, more for long numbers and busy frames; keep on-screen text near 15 characters per second while Joel talks [P]. Viewers at 1.25–1.5× lose little; 2× costs (g ≈ −0.36) [E].
- **Segments are the editor's job.** Designer-made segments raised retention (d 0.42); viewer control alone did almost nothing (g 0.05) [E]. End complex builds on a held summary frame of about 1–3s; skip it when the content is simple.
- **Cut at event boundaries.** Cuts placed at the end of an action preserve memory; cuts mid-action degrade it [E].
- **Show the real statistic.** Stable values; counting through invented intermediates is a fictional in-between state.
- **Chapter openings** show a state a returning viewer can read at once; viewers scrub to visual transitions.
- **Account for overlaps.** A transition that overlaps two scenes shortens running time; put it in the beat sheet.

### Pacing has no quota

No study links cut rate or visual-change rate to learning on YouTube. Channels that hold audiences range from 2.16 to 14.7 visual changes per minute [P]. Design pays off more on complex material (g 0.70 vs 0.20) [E], and fast pacing combined with emotionally charged content overloads viewers [E]. So: dense, quick hooks; calm, held mechanism scenes; re-hooks at chapter breaks; and slow down wherever the content is both complex and arousing.

### First and last frames

A meaningful first frame when the cut needs immediate information; never an accidental all-hidden frame. Hold a useful completed pose until the editor's cut. Exits belong to the edit; handles only when the handoff calls for them. The last 20 seconds of the video stay calm for end screens.

## 04 · Cues, pointer and presenter

| Cue | Use for | Evidence |
|---|---|---|
| Colour or highlight on the object | The default way to say "this part". | Signalling g 0.43 (retention 0.53, transfer 0.33); colour spreading through the relevant part beat arrows [E] |
| Label on the object | Naming as it is spoken. | Spatial contiguity g 0.63; label size drew glances [E] |
| Arrow | Causal or directional relations. | Weaker than on-object colour for "where to look" [E] |
| Dimming the rest | Focus without a second highlight. | Spotlight effects are mixed; keep the context readable [E] |
| Zoom | Genuinely small targets. | Concentrates gaze [E] |
| Motion onset | Pulling the eye at the right moment. | Onsets capture attention; continuous motion does not [E] |

**One active cue at a time, locked to the spoken referent, used sparingly.** Cues help when they are timed with the event and the narration.

### The pointer

A visible cursor on its own does nothing for learning; intermittent pointing beat continuous pointing, which beat none [E]. Travel, stop on the target while it is named, then rest or hide. No wandering. The pointer's tip touches the target and its press causes the response.

### Joel or the graphic

The presenter raises motivation and sense of connection, but a larger presenter image predicts lower transfer because the eye goes to the face [E]. When a graphic carries information that must be read, give it the full frame or a small picture-in-picture that does not compete. Keep Joel on screen for opinion, judgement, jokes and transitions; his pointing gestures help (g ≈ 0.3) [E].

## 05 · Patterns that earned their place

| Pattern | Choreography | Check |
|---|---|---|
| Persistent demonstrator | Establish one object → change density → change type → show states → name the resulting character. | Copy and other variables fixed so each decision is visible. |
| Evidence and detail | Authentic source → enlarge the actual passage → mark the words as spoken → hold. | Page and detail share source-coordinate highlights; no invented quote. |
| Mechanism canvas | Name the parts → animate the change → staged transitions → held summary. | No more than 3–4 things moving at once. |
| Causal loop | Build the chain → close the feedback edge → repeat only what really repeats. | Marker and path share exact geometry. |
| Compare, select, combine | Alternatives settle → chosen parts identified → each part moves from its real origin → hold. | Source identity, shape and opacity preserved. |
| Recurring board | Same layout → active step moves → its decision lands and stays. | Spatial model never rebuilt between appearances. |
| Pointer-driven UI | One pointer → place or change the component on its cue → keep completed parts. | Pointer and effect agree; the camera widens after the build. |
| Live code build | Whole snippet visible → build or highlight the active lines in step with the explanation. | The discussed line enlarged or highlighted; time to scan. |
| Data transition | Stage the change (axis, then values), ease-in-out → end on a static trace or small multiples. | Continuous trend animation is enjoyable but error-prone; the end state must be readable still [E]. |
| Countable proportion | Countable units → light the share on the spoken figure → hold. | Icon-array logic; natural frequencies on screen when reasoning matters. |
| Same structure, new content | Swap the page → outlines land on shared structure → swap again with outlines fixed. | Geometry never moves between versions. |
| Quoted accumulation | Speech-sized clauses of a quote, each kept. | A joke never shows the solution. |
| Exclusion list | Strike each spoken item, dim it, keep the earlier count. | Restarting at 01 discards the inventory. |
| Metaphor plate + overlay | Generated or filmed plate → code-rendered type and diagram on top on the cue. | Plate never carries text or data; logged; disclosed if photoreal. |
| 3D object | GLB via the Three.js adapter → one purposeful camera move → hold. | Deterministic seeking; no idle spin on teaching frames. |
| Footage annotation | Real footage → mark its actual feature → remove the mark after its job. | Tested over the exact plate; alpha verified. |
| Reaction or joke | Respect the setup → land the word → allow dead air → return on the spoken reversal. | Never cover the face on a punchline. |

*Figure: Final-render reference · 50ms, 3.3s. A persistent phrase changes hierarchy; the measured value appears directly.* (image: A stable gold 50ms value with First Impression above it and a citation below.)

### Two refinements to reuse as ideas

**First impression:** the phrase is readable at frame zero, grows once, then moves into a secondary role as the stable number arrives. A hierarchy change, not a loop. The one-frame website flash was removed in the final client fixes.

**Fingerprint:** a large centred metaphor establishes the subject, then title and fingerprint reframe together to make room for authentic examples. The pointer has a target and leaves after its job.

> **Note · Check the registry first**
>
> HyperFrames ships registry blocks for transitions, 3D motion, Lottie and text match cuts, plus seven runtimes (GSAP, Lottie, Three.js, Anime.js, CSS keyframes, WAAPI, TypeGPU). Start from a block when it fits and restyle it; own the patterns that are specifically this channel's.

## 06 · Building with Claude Opus 5.5

Opus 5.5 (released 22 September 2026) does not make video. It makes the loop this channel already runs (write HTML/GSAP, render, read the frames, revise) cheap and reliable enough to run across a whole 40–60-scene package [P].

### The studio has five layers

Most one-prompt AI videos look alike because the model fills every missing decision with the safest default it knows: the statistical middle that Frontend Design was about. The remedy is the film's own: make the decisions before rendering. Keep five layers separate and inspectable, and never let one prompt collapse them into a single unreviewed step [P].

| Layer | Question | Artifact | Who decides |
|---|---|---|---|
| Director | What should the viewer understand, and what would make this unacceptable? | `brief.md`: one sentence to remember, teaching jobs, facts vs choices, unacceptable outcomes | Yuvraj, from Joel's script, his notes when he gives them, and `joel-decisions.md` |
| Reference | What should it feel and look like? | `style-guide.md`: reference analysis, this video's colour map, DO NOT COPY list | Agent proposes; human approves |
| Timeline | What changes at each beat, and why? | `shotlist.md` + cue map: word ID, entry state, exit state, what the viewer knows before and after, what must stay true, reason; sound cues | Agent, against the narration |
| Renderer | How is every frame produced? | Seekable scenes: `frame = render(t, shotlist, assets, tokens, seed)` | Agent, in HyperFrames |
| Critic | What failed, exactly where, and why? | `reviews/`: contact sheets, rubric scores, top-three defect notes | Code, model and human graders |

### Six gates, not open-ended freedom

| Gate | Approve before moving on |
|---|---|
| G1 | References, approved assets, transcript and word map. Any missing asset is listed as a blocker. |
| G2 | Visual plan (when Joel leaves placement open), style guide and shot list. |
| G3 | One representative still per readable pose. |
| G4 | Rough render, contact sheets and narrated proxy. |
| G5 | The three worst defects per scene repaired; only affected frames re-rendered. |
| G6 | Cue sheets, format variants, photosensitivity log and deliverables. |

The agent can work for hours between gates and resumes from the last completed one. It never makes an irreversible brand or editorial decision on Joel's behalf. A missing screenshot, paper or logo is a blocker, not an invitation to draw a convincing fake. An unclear reference gets a question or one test frame, not 900 polished wrong frames. "Done" means the gate's artifacts exist, not that the last command exited cleanly.

> **Note · When Joel leaves placement open**
>
> For P2, Joel asked for visuals wherever they help instead of timestamped notes [J]. Then the Director's first artifact is `visual-plan.md`: one row per candidate moment with its word ID, teaching job, treatment (animation, Joel's footage, a screen recording, a shot to ask Joel to film, or nothing) and the reason. "Nothing" is a real answer, decided by the cover-it-with-your-hand test. Check the total against what Joel asked for (on P2, fewer visuals than P1). Every visual is then an addition, so every shot must name what the viewer will understand better.

### The shot list is a contract

| Word ID | Job | Entry state | Exit state | Knows before | Knows after | Must stay true | Why it exists |
|---|---|---|---|---|---|---|---|
| w1180 | Evidence | Full paper page | Abstract enlarged, phrase marked | Joel's claim, not yet shown | 92 people rated the designs blind | Ratings by people, blind; no figure the paper does not report | Shows the claim is measured, not opinion |

A list of effects ("zoom, then morph, then particles") describes activity, not meaning. Each beat names what the viewer knows before and after it. If the agent cannot say why a shot exists, it does not belong in the render.

"Must stay true" names what the picture asserts: what depends on what, what runs in sequence or in parallel, what is measured and what is schematic, and where a metaphor stops being accurate. Position, arrows, grouping and timing all make claims. A frame that looks right but asserts a wrong relationship fails, whatever else it scores.

### The critic

- **Observe.** A contact sheet with one frame per readable pose, a strip of consecutive frames around the fastest transition, a phone-size preview, and the cut joins.
- **Judge blind to intent.** A fresh critic subagent gets only the frames, the shot list's "knows after" and "must stay true" columns and the rubric, never the builder's account of what it meant. A model grading its own work tends to favour it.
- **Score pass or fail per criterion:** meaning (does the frame assert only what "must stay true" allows?), first readable pose, phone readability, continuity, motion purpose (does the viewer know where to look?), sync offset in frames, evidence fidelity, safety. Each finding names the rule ID it rests on.
- **Report three defects,** the largest, each with a timestamp, evidence (a crop) and a local fix. Patch only those and re-render only the affected frames.
- **Stop rule:** no new evidence, no new attempt.

| Grader | Checks |
|---|---|
| Code | Deterministic: check JSON, contrast, type floors, safe zones, label-to-word offsets, frame counts, alpha, photosensitivity. |
| Model | The Opus critic with the rubric, for judgement code can't express: hierarchy, clarity, whether the change reads. |
| Human | Yuvraj, then Joel on Frame.io. The gold standard. |

> **Note · Calibrate the critic before trusting it**
>
> The cohort's evals sessions teach combining code, model and human graders, starting from about 30 real examples that humans label, and refining the judge until it agrees with them. They also teach asking the expert for judgement, not procedure (course material in the cohort archive: Module 3, *The Last Interface* part 1 (video-1226218911, 02:15–02:19) and Module 2, *Evaluation of LLMs* (video-1216669350, 01:45–01:55)). Applied here, the human labels are still thin. Joel's 66 Frame.io comments on P1 say where visuals go, not what was wrong. The v05→v08 history is mostly Yuvraj's own refinements, so label those cases as his. Joel's own defect rulings number three: the one-frame flash and two demonstration captions (`joel-decisions.md`). Use these as development cases. Grow the set from Joel's keep, change or remove on each delivered shot and Yuvraj's logged rejections. Until about 30 labelled cases agree with the critic, it advises and does not gate. Where it misses, sharpen the rubric rather than loosening the threshold.

| Documented capability | How the pipeline uses it | Guardrail |
|---|---|---|
| Multi-hour runs with parallel subagents; 1M-token context; cached input at $0.20/M | A lead agent owns the beat map, tokens and scene ledger; one subagent per scene builds, renders, checks and reports. | Ledger as checklist; a continuation rule (it sometimes stops with a progress report); elapsed-time lines. |
| Better reading of position: which node an arrow reaches, what changed between two versions | Paired stills (v07 vs v08 at the same frame); "does the arrow land on the named node?" | A saved diff or crop for every such claim. |
| Images up to 2576px; a 1080p still costs 2,691 tokens | Review 1080p PNG stills; full-resolution crops for small text. | Ranked 40th of 61 on OCR: verify code and small text against the DOM source, not the pixels. |
| Browser toolset with JavaScript | Seek the paused timeline on a localhost preview and capture exact frames. | Prefer CLI snapshots; never drag a scrubber by pixel. |
| Effort per message | `medium`/`high` for scenes, `xhigh` for orchestration. | Avoid `max`; one SVG test used the full 128K output. |

> **Note · What it cannot do**
>
> It sees still images only: no video and no audio. It gives approximate coordinates and counts, falls back on generic styles unless specific patterns are named, lags on humour and creative mastery, and is documented to overstate what it has verified. Taste lives in these systems; pass and fail come from tools.

### The build-measure loop

| Stage | Tool | What counts as a pass |
|---|---|---|
| Brief | Scene brief with teaching job and override log | Job, envelope, each override with its reason. |
| Beat map | Parakeet draft → MFA final → GSAP labels by word ID | Table of word onsets. |
| Storyboard | Static, fully styled end states | One approved still per readable pose. |
| Build | One subagent per scene | A ledger row: scene, version, open issues. |
| Static gate | `check --json --at-transitions` | Zero lint errors (a lint error silently switches the layout and contrast audits off). |
| Frame review | `snapshot --at` readable poses; `--zoom`; paired versions | Critique in coordinates on a coarse anchor grid; a diff image for "only X changed". |
| Measurement | PIL / OpenCV / ImageMagick scripts the agent cannot edit | Contrast, type floors, safe zones, label-to-word offsets in frames. |
| Moves | `keyframes --shot` | One onion-skin still per move. |
| Render | Local render at the edit's exact rate; verify script | Dimensions, rational fps, frame count, alpha over magenta. |
| Safety | EA IRIS (free) or Harding FPA | A photosensitivity log per render version. |
| Human review | Narrated review at phone size | Sign-off and an updated pitfalls file. |

### Package the studio, not the chat

If the only record of a film is a conversation, there is no production system, only a lucky session. Keep every decision in files the next run can read; the next video swaps the brief and assets and keeps the render contract, review checklist and delivery structure.

```
<video>/                       Frontend Design equivalent
  brief.md          director    SPEC.md, scene briefs
  style-guide.md    reference   frame.md + this video's colour map
  shotlist.md       timeline    data/edit.json + beat comments
  data/             word map, cue map, variables
  assets/           approved media + SOURCES.md
  src/              scene builders (lib/scenes.js)
  reviews/          contact sheets, critic scores, defect notes
  out/              masters per format, poster frames, cue sheets
                    (renders/vNN, Animations Done)
```

### Named bans for the agent

Anthropic documents that naming specific patterns works where "avoid generic design" does not. These are the defaults the agent may only break through a logged override.

- Gold on output nobody chose, when the film separates choice from default
- Count-ups through invented values
- Overshoot on values, bars or causal arrows
- Ambient loops on teaching frames
- Monospace outside literal code, prompts and data
- Decorative gradients, glow or shadows
- An idle or wandering pointer
- Pulsing red
- Word-by-word reveals of must-read text
- Generated text, charts or UI presented as evidence
- An AI avatar or voice clone in place of Joel
- `snapshot --describe` on client frames (sends them to Gemini)
- Generated imagery or video on screen, unless it serves the purpose better than footage or code and would not read as AI (Joel's preference)
- Max effort
- Big centred text over a gradient as the default frame
- Everything entering with the same fade
- Rendering before the style guide and shot list are approved

### Copy-ready production contract

```
You are directing and engineering the animation package for a MergeToMaster video.
Goal: inserts that make [video] understood.
The viewer should remember: [one sentence].

Inputs
- Transcript and word map; approved assets only (papers, screenshots, footage, logos).
- Brand System v3.2 and Motion System v3.2; references in [folder].
- Joel's notes for this video, or "placement left open"; joel-decisions.md.

Before building
- If Joel left placement open, write visual-plan.md first: candidate moments,
  treatment or none, reason, shots to ask Joel to film.
- Write style-guide.md from the references (palette, type, composition, pacing,
  motion per object class, texture, DO NOT COPY) and this video's colour map.
- Write shotlist.md: word ID, teaching job, entry state, exit state,
  what the viewer knows before and after, what must stay true, why the shot exists.
- List missing assets as blockers. Never draw a convincing substitute.

Build
- HyperFrames, pinned for this video; every frame seekable and deterministic.
- GSAP labels keyed to word IDs; sound cues on the same labels.

Gates: stop and show me at each
1 assets + references   2 visual plan + style guide + shot list   3 one still per readable pose
4 rough render + contact sheets + narrated proxy
5 the three worst defects per scene fixed; re-render only those frames
6 cue sheets, Shorts variants, photosensitivity log, deliverables

Critique
- Judge only the rendered frames, blind to intent; pass/fail per rubric criterion.
- Three defects, each with timestamp, evidence and a local fix.

Deliver
4K masters (MP4, or ProRes 4444 with alpha), poster frames, contact sheets,
cue sheets, source, asset list with provenance, and a note on what still
needs human review.
```

### Copy-ready scene brief

```
Scene / ID: [fill in]
Teaching job: [hook | cast | mechanism | connect | evidence |
               comparison/statistic | procedure/UI | verdict/joke | chapter]
After this shot the viewer understands: [one sentence]
Viewer already knows: [what the previous shots and Joel have established]
Must stay true: [the claim and relationships the picture asserts]
Where the picture stops being accurate: [limits of the metaphor or simplification]
Asked by Joel or added: [asked | added, with its reason]
Visual evidence / demonstrator: [source and provenance]
Timeline in / out / exact fps: [from current edit]
Local duration: [seconds and frame count]
Opening pose: [what is visible at the cut]

Word ID | spoken phrase | visual action | readable pose / hold
[w123]  | [words]       | [action]      | [reading task]

Persistent objects: [what stays]
One variable being changed: [the decision]
Overrides: [default · reason · how verified]
Final pose / handles: [editorial agreement]
Output: [full-frame MP4 or true-alpha MOV]
Pass artifacts: [check JSON, stills, offsets in frames, IRIS log]
```

## 07 · Deterministic scenes, reviewable output

GSAP authors the animation; HyperFrames owns the playhead and media timing. A scene must produce the same frame from normal playback, a backward seek or a direct seek.

- **Build the DOM synchronously;** each builder returns a paused GSAP timeline registered under the composition ID.
- **Explicit states:** `fromTo()` with complete start and end; no callbacks that swap copy during playback.
- **GSAP owns animated transforms.** A tween replaces CSS centring; use wrappers, box positioning or matching percentage transforms.
- **Fading a parent fades its children.** Empty the parent's background instead; rotate shapes, never rows that carry labels.
- **Sub-frame bounds go inside the frame window.** At 23.976, frame 2 is 0.0834166…s; a set at 0.083417 fires late. Verify events under three frames in extracted frames.
- **No wall-clock time, unseeded randomness or runtime network.**
- **Alpha scenes keep a transparent root:** since v0.8.112 alpha exports keep the root's background. Composite over magenta to prove it.
- **Restore what QA scripts swap;** Studio previews `index.html`.
- **Load fonts and images locally;** renders wait for web fonts since v0.8.122.

### Minimal scene contract

```
// Labels come from the forced-alignment cue map, keyed by word ID.
const tl = gsap.timeline({ paused: true });
Object.entries(cues).forEach(([wordId, t]) => tl.addLabel(wordId, t));

// Build DOM and stable layout first; animate a separate motion wrapper.
// Land the readable pose on the stressed word, not the tween start.
tl.fromTo(label,
  { y: 18, opacity: 0 },
  { y: 0, opacity: 1, duration: .36, ease: 'power3.out' },
  'w214-=0.18'
);

window.__timelines = window.__timelines || {};
window.__timelines[compositionId] = tl;
// Declare the full duration on the composition and hold the final pose.
```

### Renderer policy

- **Pin HyperFrames per video; upgrade between videos, never mid-project.** Frontend Design ran on 0.8.38; the latest release on 5 October 2026 was 0.8.127, and the machine's global CLI was a third version. Run `hyperframes upgrade --project`, align the global CLI, update the skills, then re-verify one reference scene and one alpha overlay before trusting the new pin.
- **Render at the edit's exact rate, locally for 23.976.** Remote Lambda and Cloud Run help lists only 24, 30 and 60fps, so confirm 25 works before relying on remote rendering for it.
- **Long renders:** Claude Code stops background commands at 30 minutes by default (two hours maximum); run long 4K renders from the project scripts.
- **PNG intermediates** for the charcoal field, grid and alpha.

| Output | Authoring / render | Handoff |
|---|---|---|
| Full-frame insert | 1920×1080 design space; `--resolution 4k --format mp4 --fps <edit fps> --quality high --video-frame-format png` (24000/1001 for P1, 25 for P2; confirm from the edit) | Silent master, exact duration, versioned filename. |
| Transparent overlay | 3840×2160 root, transparent; the 1920-space scene scaled 2×; `--format mov` (ProRes 4444), no `--resolution` | Alpha verified over the actual footage. |
| Batch of variants | `--batch data/scenes.json` (one render per array row); `--variables-file` takes one object | One versioned file per row. |
| Review proxy | Lightweight video with narration and surrounding context | Labelled as review. |

### Variants from the source, not a crop

A Shorts cut is a different composition. Keep the same assets, states and cue map, and define layout behaviour per format; never crop the centre out of the 16:9 master. An export is correct when the composition survived the format change, not when the encoder finished, so render a contact sheet for every variant.

| Format | Layout behaviour |
|---|---|
| 16:9 master | Spatial context; the full system. |
| 9:16 Shorts | Fewer simultaneous elements, larger type, stronger vertical hierarchy, a different camera path, a tighter story. |
| 1:1 | Tighter typography, shorter holds. |

### Photosensitivity

- No more than three flashes in any second over more than 25% of the screen; a flash is a luminance change of 20 cd/m² or more while the darker state is below 160 cd/m²; any transition to or from saturated red counts [P].
- Keep at least 0.375s between flash leading edges (9 frames at 23.976, 10 at 25), and watch cuts from dark frames to white paper or bright UI.
- Regular stripes of more than five light–dark pairs are limited in area; patterns flowing smoothly in one direction are exempt.
- Run EA IRIS or Harding FPA on every final render. Avoid full-frame whips and spins on teaching frames.

### Sound on the same timeline

Masters stay silent and the mix happens in the edit, but sound cues run on the same clock as the picture. Many AI-made films look finished on mute; then the click lands after the button and the cut misses the beat. Every meaningful hit, click, whoosh or riser is a GSAP label, and each master ships with a cue sheet so the sound designer places effects on the exact frame, not by ear. Where music drives a sequence, measure its beats into the cue map before choreographing.

```
master,frame,timecode,cue,element,note
fd_S04_button-states_v09,0091,00:00:03:19,click,cta-button,pointer press
fd_S04_button-states_v09,0104,00:00:04:08,tick,hover-state,state change
fd_S05_stat-70_v09,0071,00:00:02:23,hit,stat-number,lands on "seventy"
```

Deliver it as CSV and, where convenient, as Final Cut markers. In the edit, run the eyes-closed test: listen without picture, and if the graphics' sound has no shape it isn't finished. Score meaningful actions, never every movement.

- **What gets a cue:** every meaningful visible action (a press, a state change, a value landing, a verdict); quiet arrivals and holds stay silent. This replaces Edit System v1's "every graphic gets a sound": a cue marks an event, and a cue on every entrance stops marking anything.
- **Sources:** Joel's Epidemic Sound and Envato libraries first [J]; Joel asked for mouse clicks, keyboards and anything else appropriate, and for music that is never distracting [J].
- **Hero moments:** choose the sound first, then time the graphic to reach about 80% of its final state on the transient frame.
- **Delivery:** each cue is a separate, editable audio clip placed on its frame; mix targets and music policy are in Edit System v1.1, section 05.

## 08 · Review the encoded result

- Every scene names its teaching job; every override is logged with its reason and check.
- Mute test: each placement does evidence, comparison, mechanism or emphasis.
- Label-to-word offsets are measured in frames; the frame under each stressed word shows what it names.
- In a teaching shot the demonstrator outweighs its caption.
- No more than 3–4 elements move at once; tracked transitions are staged.
- Unnarrated text gets its reading budget; on-screen text stays near 15 characters per second.
- Complex builds end on a held summary; nothing resets at the clip end.
- `check --json --at-transitions` passes with zero lint errors.
- Normal playback and direct or backward seeks give the same frame.
- Short events and cut boundaries are checked in encoded frames, and a scan of every frame finds nothing visible for only one or two frames unless the shot list says it should be.
- Every shot's "must stay true" holds in the encoded frames.
- Any generated imagery or video has a logged reason and would not be noticed as AI by a viewer.
- Width, height, rational fps, frame count, duration and audio policy match the handoff.
- Alpha composites correctly over the actual plate.
- IRIS or Harding log saved for the final render.
- Must-read text survives phone-size viewing and sits above y972.
- The review and the delivered master match the current source revision.
- Each master's final settled frame works as a still on its own (poster test).
- Cue-sheet frames match the picture; cuts and sound cues land together.
- Every format variant has its own contact sheet.
- The model critic was calibrated against this channel's golden set before it gated anything.

### What changed from v2, in v3.1 and in v3.2

| Before | Now |
|---|---|
| v3.1: 24000/1001 written in as the channel rate | v3.2: frame rate taken from each edit; safety limits stated in seconds. |
| v3.1: shot list records what the viewer knows after | v3.2: knows before, knows after and what must stay true; the critic scores meaning first and cites rule IDs. |
| v3.1: golden set said to be Joel's 66 comments | v3.2: Joel's defect rulings counted honestly (three); the critic advises until about 30 labelled cases agree with it. |
| v3.1: Director works from Joel's notes | v3.2: a visual plan first when Joel leaves placement open. |
| v3.1: sound rules split with Edit System v1 | v3.2: cues on meaningful actions only, Joel's libraries first, editable clips; the mix stays in Edit System v1.1. |
| v3.1: one-frame events checked when suspected | v3.2: every frame of the encode scanned for one- or two-frame appearances. |
| v3: a build-measure loop | v3.1: five studio layers, six gates, a shot-list contract and an intent-blind critic calibrated on Joel's comments. |
| v3: motion described by verb | v3.1: motion rules per class of object; closed-form springs. |
| v3: silent masters | v3.1: silent masters plus a cue sheet from the same labels. |
| v3: vertical re-layouts as an option | v3.1: variants built from the source with per-format layout rules. |
| Vocabulary values and a .28s median | Envelopes by teaching job; duration scales with travel; tracked transitions .5–1.25s ease-in-out, staged. |
| No overshoot, ever | Never on teaching objects; one restrained settle allowed on brand and punchline moments. |
| Blur only when a shot proves it | Motion blur is now built into HyperFrames; one to three snap beats, text sharp. |
| Automatic transcripts as estimates | MFA against the approved script; labels by word ID; offsets measured in frames. |
| New copy 0.3s/word + 0.5s | Unnarrated text 0.375s/word + 1s; narrated text follows the voice. |
| Recipes verified on 0.8.38 | Pin per video, upgrade between videos, re-verify alpha. |
| Flash safety unaddressed | Flash and pattern limits plus an IRIS log per render. |
| Cues, pointer rhythm and presenter unaddressed | Cue hierarchy, intermittent pointing, full frame for must-read graphics. |
| Agent workflow implicit | An Opus 5.5 build-measure loop with tool-made verdicts and named bans. |

The research comes from short lab lessons, not 12-minute YouTube essays. Change one variable per video, note the timestamps, and read them against the key-moments section of Joel's retention report, so the channel produces the evidence the literature lacks.

### Sources

- [joel-decisions.md](../joel-decisions.md) and [Edit System v1.1](../MergeToMaster%20-%20Edit%20System%20v1.md) — Joel's brief, preferences and rulings, the [J] sources.
- [reports / Claude Opus educational motion graphics.md](../reports/Claude%20Opus%20educational%20motion%20graphics.md) — October 2026 synthesis with links to every study, standard and release note.
- [research_notes / Claude Opus educational motion graphics](../research_notes/Claude%20Opus%20educational%20motion%20graphics/) — six sets of notes behind it.
- [Motion Engineering: Build a Video Studio Around Opus 5.5](https://x.com/0xwhrrari/article/2105643919119696297) (@0xwhrrari, 1 Oct 2026) — practitioner article behind the five layers, gates, critic protocol, cue sheets and variants in v3.1. Practice, not evidence. A copy is saved in 100x Engineers / Final Capstone Context.
- Course material in the cohort archive: Module 3, *The Last Interface* part 1 (video-1226218911, 02:15–02:19) and Module 2, *Evaluation of LLMs* (video-1216669350, 01:45–01:55) — the three-grader and judge-calibration method.
- [lib/scenes.js](../../P1%20-%20Frontend%20Design/Animations%20using%20Hyperframes/MergeToMaster/lib/scenes.js), [lib/refinement.css](../../P1%20-%20Frontend%20Design/Animations%20using%20Hyperframes/MergeToMaster/lib/refinement.css), [MOTION.md](../../P1%20-%20Frontend%20Design/Animations%20using%20Hyperframes/MergeToMaster/MOTION.md) — the Frontend Design implementation.
- [renders/v08/README.md](../../P1%20-%20Frontend%20Design/Animations%20using%20Hyperframes/MergeToMaster/renders/v08/README.md), [client-fixes/2026-09-14/DELIVERY.md](../../P1%20-%20Frontend%20Design/Animations%20using%20Hyperframes/MergeToMaster/client-fixes/2026-09-14/DELIVERY.md), [bin/verify-v08.py](../../P1%20-%20Frontend%20Design/Animations%20using%20Hyperframes/MergeToMaster/bin/verify-v08.py) — revisions, final fixes and the delivery verification script.

Previous versions: v3.1 in [System Archive / 2026-10-05-v3.1-before-v3.2](../System%20Archive/2026-10-05-v3.1-before-v3.2/); v3 in [System Archive / 2026-10-05-v3-before-studio-update](../System%20Archive/2026-10-05-v3-before-studio-update/); v2 in [System Archive / 2026-10-05-v2-before-purpose-rewrite](../System%20Archive/2026-10-05-v2-before-purpose-rewrite/); v1 in [_archive v1](../_archive%20v1/).

MergeToMaster · Motion System v3.2
Revised 05 October 2026 · Purpose first · Based on Frontend Design production and October 2026 research.
