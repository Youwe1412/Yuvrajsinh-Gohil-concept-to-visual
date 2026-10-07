# MergeToMaster rules index

The agent-readable version of Brand System v3.2, Motion System v3.2 and Edit System v1.1.
The HTML pages carry the reasoning and examples; this file gives every rule an ID so
plans, briefs, critic findings and override logs can cite it. When a page and this file
disagree, the page wins and this file is corrected.

As of 5 October 2026.

## How to use it

| Kind | What a finding against it means |
|---|---|
| **Invariant** | Must be fixed. No override. |
| **Joel default** (tag J) | Fix it, or override it with a logged reason that names what the viewer understands better. Every override of a J rule is flagged to Yuvraj. |
| **Default** | Fix it, or override it with a logged reason. |
| **Option** | Switched on per shot when the job needs it. No finding. |

Override line, in the scene brief and QC: `rule ID · teaching job · reason · how it was verified`.

**Tags:** J Joel's own words, rulings or published videos · E peer-reviewed evidence ·
P documented practice, standards or platform policy · I our inference, to be tested on
Joel's videos.

**Status:** *Joel stated* (his words, in `joel-decisions.md`) · *Measured* (sampled from
Joel's own material) · *Unconfirmed* (not yet confirmed by Joel). Change a status only by
adding an entry to `joel-decisions.md` first.

---

## Joel's stated preferences

| ID | Rule | Kind | Tags | Status | Source |
|---|---|---|---|---|---|
| J-01 | Prefer no AI imagery or AI video ("It's too obvious"). Reach for his footage, a shot he films, a code-rendered graphic, then light licensed footage; generated media only when it serves the purpose better and a viewer would not notice it as AI | Joel default | J | Joel stated | Brief; Brand 04 |
| J-02 | Light stock B-roll only; nothing that reads as stock | Joel default | J | Joel stated | Brief; Edit 08 |
| J-03 | Music where appropriate, never distracting | Joel default | J | Joel stated | Brief; Edit 05 |
| J-04 | The rough cut goes to him bare: no B-roll, music or animation until he has reviewed it | Joel default | J | Joel stated | Brief; Edit 06 |
| J-05 | Sound: mouse clicks, keyboards and anything else appropriate | Joel default | J | Joel stated | Brief; Edit 05 |
| J-06 | Add your own creativity and flair; suggestions welcome | Joel default | J | Joel stated | Brief; Edit 06 |
| J-07 | Cut frequently in the first 30 seconds with B-roll; change every 10–20 s after the opening at most | Joel default | J | Joel stated | Brief; Edit 04 |
| J-08 | P2 only: visuals where they help instead of his notes; fewer than P1; keep his grade; he films specific shots on request | Joel default (P2) | J | Joel stated | 2026-10-05 |

## Brand

| ID | Rule | Kind | Tags | Status | Page |
|---|---|---|---|---|---|
| B-T1-01 | No more than three flashes in any second; pattern limits respected | Invariant | P | Unconfirmed | Brand 00 |
| B-T1-02 | Evidence fidelity: real sources at native resolution, quoted values exact, nothing generated presented as real data, UI or paper; a missing asset is a blocker, never a convincing fake | Invariant | P | Unconfirmed | Brand 00, 04 |
| B-T1-03 | Text the viewer must read unaided is readable at phone size on the encode; otherwise it is narrated, enlarged or reference-only | Invariant | P | Unconfirmed | Brand 00 |
| B-T1-04 | Meaning never rests on hue alone: every colour-coded state also has a shape, mark, label or position | Invariant | P | Unconfirmed | Brand 00 |
| B-T1-05 | Seek-safe scenes, rational frame rate from the edit, verified alpha | Invariant | P | Unconfirmed | Brand 00 |
| B-01 | Palette: ground #121212, deep #0C0C0C, panel #242A36, panel alt #1E2430, white #F8F8F8, dim #C9C6CA, gold #D9A43B, gold fill #786C36, red #E8515A, crimson fill #C01218, olive #727854; sky blue #56B4E9 as an option | Default | J | Measured | Brand 01 |
| B-02 | Write this video's colour map into frame.md before the first scene | Default | I | Unconfirmed | Brand 01 |
| B-03 | Gold marks one active focus, locked to the spoken referent; dim the rest instead of a second highlight | Default | E | Unconfirmed | Brand 01 |
| B-04 | Colour on the object before arrows; arrows for causal or directional relations | Default | E | Unconfirmed | Brand 01 |
| B-05 | Red #E8515A for words and marks, #C01218 for large fills only; red always paired with a mark; small red text on the ground, not on panels | Default | P | Unconfirmed | Brand 01 |
| B-06 | Never gold vs red, or red vs olive, as the only difference between two states; sky blue is the safe third meaning | Default | I | Unconfirmed | Brand 01 |
| B-07 | Refused items are struck; things the evidence disproved recede to dim | Default | I | Unconfirmed | Brand 01 |
| B-08 | House frame flat, square and unornamented; depth, glow or gradient only when it carries meaning | Default | E | Unconfirmed | Brand 01 |
| B-09 | Specimens keep their own colours, type, radius and shadows; quoted values stay literal and never become channel tokens | Default | P | Unconfirmed | Brand 01, 04 |
| B-10 | Not the generic demo by default: centred text over a gradient, uniform fades, logo at the end | Default | P | Unconfirmed | Brand 01 |
| B-11 | Type sizes at 1080p: must-read floor 52px; reference 24–28; labels 56–72; mono 36–40+; headline 76–140; hero 180–340 | Default | I | Unconfirmed | Brand 02 |
| B-12 | Labels of 2–3 words, matching the spoken term, attached to the object | Default | E | Unconfirmed | Brand 02 |
| B-13 | Unnarrated text gets about 0.375 s per word plus 1 s; on-screen text near 15 characters per second while Joel talks | Default | P | Unconfirmed | Brand 02 |
| B-14 | Whole phrases land on their cue and stay still; no word-by-word reveals of must-read text | Default | E | Unconfirmed | Brand 02 |
| B-15 | Code: the whole relevant snippet (5–15 lines), the discussed line highlighted or enlarged; mono only for code, prompts and data | Default | E | Unconfirmed | Brand 02 |
| B-16 | Numbers: real values, natural frequencies, icon arrays, shared denominators; end any chart change on a static frame that states the claim | Default | E | Unconfirmed | Brand 02 |
| B-17 | Burned-in captions: Poppins Bold 54px, 1–3 words, top centre | Default | J | Measured | Brand 02; Edit 02 |
| B-18 | 1920 × 1080 design space; 112px spine both sides | Default | P | Unconfirmed | Brand 03 |
| B-19 | Nothing must-read below y972; the last 20 seconds stay calm for end screens | Default | P | Unconfirmed | Brand 03 |
| B-20 | Grid (60px, 2%) chosen by teaching job; encode-tested | Default | I | Unconfirmed | Brand 03 |
| B-21 | Panels only to group or separate; glass overlay 8% fill, 30% stroke | Default | J | Measured | Brand 03; Edit 02 |
| B-22 | A must-read graphic gets the full frame or a small picture-in-picture; Joel's face for opinion, judgement, jokes and transitions | Default | E | Unconfirmed | Brand 03 |
| B-23 | Positions stay stable across connected shots; before left of after by default | Default | I | Unconfirmed | Brand 03 |
| B-24 | Evidence: papers in native ratio then the actual passage enlarged; screenshots re-captured at 2–3× instead of AI upscaling; reconstruct only when parts must move | Default | P | Unconfirmed | Brand 04 |
| B-25 | House pointer: macOS-style, black with 2.5px white outline, 44–54px tall; tip on a credible target | Default | I | Unconfirmed | Brand 04 |
| B-26 | Generated media never as evidence; no likeness of a real person; no avatar or voice clone for Joel; every asset in the provenance log | Default | P | Unconfirmed | Brand 04 |
| B-27 | Each format (16:9, 9:16, 1:1) is its own composition with its own contact sheet | Default | P | Unconfirmed | Brand 05 |
| B-28 | Every override logged: rule ID · teaching job · reason · how verified | Default | I | Unconfirmed | Brand 00 |
| B-29 | No production words on screen, and no caption describing a demonstration the viewer can already see | Default | I | Unconfirmed (suggested by P1 fixes) | Brand 04, 06 |
| B-O1 | Options: sky-blue third meaning; meaningful depth; full-bleed UI or footage; generated plates, SVG or 3D (see J-01); on-twos look; motion blur; camera moves; vertical re-layouts | Option | P, I | Unconfirmed | Brand 00 |

## Motion

| ID | Rule | Kind | Tags | Status | Page |
|---|---|---|---|---|---|
| M-T1-01 | At least 0.375 s between flash leading edges; under three flashes per second over 25% of the frame; saturated red counts | Invariant | P | Unconfirmed | Motion 07 |
| M-T1-02 | The same frame from playback, a backward seek or a direct seek | Invariant | P | Unconfirmed | Motion 00, 07 |
| M-T1-03 | Must-read text never sits on a moving layer while it is being read | Invariant | E | Unconfirmed | Motion 00 |
| M-T1-04 | Rational fps from the edit, frame-exact durations, verified alpha | Invariant | P | Unconfirmed | Motion 00, 07 |
| M-T1-05 | Every claimed pass has a saved artifact | Invariant | I | Unconfirmed | Motion 00 |
| M-01 | Every scene names one teaching job; the job sets pace, ease and hold | Default | I | Unconfirmed | Motion 01 |
| M-02 | Motion shows the change being taught; no decorative animation | Default | E | Unconfirmed | Motion 00 |
| M-03 | The readable pose lands on the stressed word; labels by word ID from forced alignment; offsets measured in frames | Default | E | Unconfirmed | Motion 03 |
| M-04 | Tracked transitions 0.5–1.25 s ease-in-out, staged; at most 3–4 moving objects, 1–2 when identity matters | Default | E | Unconfirmed | Motion 02 |
| M-05 | No overshoot on values, bars, counters or causal arrows; one settle of 3–8% on brand and punchline moments | Default | I | Unconfirmed | Motion 02 |
| M-06 | No ambient loops on teaching frames; representational loops are fine | Default | E | Unconfirmed | Motion 02 |
| M-07 | One motion rule per class of object (headline, data, panel, micro UI, camera, evidence, pointer, brand) | Default | P | Unconfirmed | Motion 02 |
| M-08 | Springs only in closed form, as a pure function of progress | Default | P | Unconfirmed | Motion 02 |
| M-09 | Exits: superseded fades .12–.22 s; context recedes to .28–.45; the editor owns the cut; hold the final pose | Default | I | Unconfirmed | Motion 02 |
| M-10 | Complex builds end on a 1–3 s held summary | Default | E | Unconfirmed | Motion 03 |
| M-11 | Cut at event boundaries, not mid-action | Default | E | Unconfirmed | Motion 03 |
| M-12 | No count-ups through invented values | Default | I | Unconfirmed | Motion 03 |
| M-13 | Pacing by content, no quota: dense hooks, calm mechanism scenes | Default | E, P | Unconfirmed | Motion 03 |
| M-14 | Pointer travels, stops on the target while it is named, then rests or hides | Default | E | Unconfirmed | Motion 04 |
| M-15 | Motion never argues with the narration: read the line, its paragraph and the next point first | Default | I | Unconfirmed | Motion 03 |
| M-16 | When Joel leaves placement open, write visual-plan.md first: every candidate moment, its treatment or none, the reason, shots to ask him to film; total checked against his request | Default | J | Joel stated (P2) | Motion 06 |
| M-17 | Shot list per beat: word ID, job, entry and exit state, knows before, knows after, must stay true, why it exists | Default | I | Unconfirmed | Motion 06 |
| M-18 | What the frame asserts (dependency, sequence, parallelism, measured or schematic) matches "must stay true" | Default | I | Unconfirmed | Motion 06 |
| M-19 | Critic: blind to intent; three worst defects with timestamp, evidence and local fix; findings cite rule IDs; no new evidence, no new attempt; advises until about 30 labelled cases agree | Default | P | Unconfirmed | Motion 06 |
| M-20 | Six gates; a gate is passed when its artifacts exist | Default | P | Unconfirmed | Motion 06 |
| M-21 | Named bans for the agent (Motion 06 list) | Default | P | Unconfirmed | Motion 06 |
| M-22 | HyperFrames pinned per video; upgrade only between videos and re-verify | Default | P | Unconfirmed | Motion 07 |
| M-23 | Photosensitivity log (EA IRIS or Harding) for every final render | Default | P | Unconfirmed | Motion 07 |
| M-24 | Variants built from source, never cropped | Default | P | Unconfirmed | Motion 07 |
| M-25 | Sound cues on the picture's labels; cues on meaningful visible actions only; Joel's libraries first; each cue a separate editable clip with a cue sheet | Default | J, P | Unconfirmed | Motion 07 |
| M-26 | Scan every encoded frame; nothing visible for only one or two frames unless the shot list says so | Default | J, I | Unconfirmed (suggested by P1 fixes) | Motion 08 |
| M-27 | Change one variable per video and read it against the retention key moments | Default | I | Unconfirmed | Motion 08 |

## Edit

| ID | Rule | Kind | Tags | Status | Page |
|---|---|---|---|---|---|
| E-01 | A graphic must close a comprehension gap: the cover-it-with-your-hand test, then the subtraction pass before export | Default | I | Unconfirmed | Edit rules, 07 |
| E-02 | Cut on the argument's open and close beats; the cadence is an output | Default | I | Unconfirmed | Edit rules, 04 |
| E-03 | An energy contour, with a deliberate dip before the payoff | Default | P | Unconfirmed | Edit 04 |
| E-04 | On-screen text is the spoken words, a 1–3 word label, or a document the narration hands over | Default | E | Unconfirmed | Edit rules |
| E-05 | Pacing contract (hook 2.5–4 s, setup 3.5–5 s, body 6–9 s, ceiling 15 s) as an audit, met with footage and punch-ins when Joel asks for fewer visuals | Default | J | Measured | Edit 04 |
| E-06 | Pauses over 250 ms cut; punch ladder 100 / 106 / 112%, ceiling 115% | Default | I | Unconfirmed | Edit 04 |
| E-07 | Hook: open bare about 2 s, first change inside 3 s, every hook claim gets proof, one comedy beat with a sound | Default | J, I | Unconfirmed | Edit 04 |
| E-08 | Mix: dialogue −16 to −14 LUFS short-term, music 18–22 dB under, master −14 LUFS integrated, −1 dBTP | Default | P | Unconfirmed | Edit 05 |
| E-09 | Music: Epidemic Sound, no vocals under speech, one bed per segment, silence before the biggest reveal | Default | J, P | Unconfirmed | Edit 05 |
| E-10 | Timeline 3840 × 2160, Rec.709, fps from the footage, ProRes 422, 48 kHz, H.264 about 60 Mbps | Default | J | Measured | Edit 01 |
| E-11 | Basic grade on A-roll only; leave Joel's grade untouched when he asks (P2) | Default | J | Joel stated (P2) | Edit 06 |
| E-12 | No graphic over a punchline or reaction | Default | I | Unconfirmed | Edit 04, 07 |
| E-13 | Three watch-throughs before sending: at 2×, on a phone, and for subtraction | Default | I | Unconfirmed | Edit 07 |
