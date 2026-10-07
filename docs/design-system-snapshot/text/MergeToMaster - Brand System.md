Generated from MergeToMaster - Brand System.html (SHA-256 9eae9b126202de27) on 2026-10-06. Do not edit; edit the HTML and re-run.

*Brand system · v3.2 · 05 October 2026*

# MergeToMaster Brand System.

Purpose first. Everything in this document is a default that exists to help a viewer understand something. When a video's purpose is better served by breaking a default, break it, write down why, and check that it worked. Only five things never bend.

- **Basis** Frontend Design production + October 2026 research
- **Design space** 1920 × 1080
- **Authoring agent** Claude Opus 5.5
- **Companion** Motion System v3.2

> **Note · Scope & precedence**
>
> Use v3.2 for every MergeToMaster animation project. It replaces v3.1 (kept in [System Archive / 2026-10-05-v3.1-before-v3.2](../System%20Archive/2026-10-05-v3.1-before-v3.2/)) and every visual rule in the Edit System; Edit System v1.1 now covers only the edit itself. The evidence behind each change is in the research report [Claude Opus educational motion graphics](../reports/Claude%20Opus%20educational%20motion%20graphics.md). Tags show where a rule comes from: [J] Joel's own words, rulings or published videos, the strongest source for this channel's taste, [E] peer-reviewed evidence, [P] documented practice, standards and platform policy, [I] our inference, to be tested on Joel's videos. Every rule has an ID, its tags, source and status in [rules.md](../rules.md), the file agents read. Joel's dated rulings, in his words, are in [joel-decisions.md](../joel-decisions.md). Tool versions, model names, prices and platform statistics are as of 5 October 2026; re-check them before relying on them.

## 00 · Purpose sets the rules

One question decides every visual choice: **after this shot, what should the viewer understand, and what on screen makes that happen?** A rule that helps answer it is kept. A rule that gets in its way is overridden for that shot. The brand is the house voice Joel speaks in, not a fence around what a video may do.

#### Tier 1 · never bends · Five invariants

- **Viewer safety.** No more than three flashes in any second; pattern limits respected [P]
- **Evidence fidelity.** Real sources at native resolution, quoted values exact, nothing generated presented as real data, UI or paper; photoreal synthetic shots disclosed. A missing asset is a blocker, never a convincing fake [P]
- **Must-read legibility.** Text the viewer has to read unaided can be read at phone size on the encoded video; anything that can't is narrated, enlarged where it is discussed, or reference-only. The 52px floor is the default way to meet this (tier 2) [P]
- **Meaning never rests on hue alone.** Every colour-coded state also has a shape, mark, label or position [P]
- **Deterministic, exact delivery.** Seek-safe scenes, rational frame rate, verified alpha [P]

#### Tier 2 · bends for a stated purpose · Defaults

- Palette roles, and what gold and red mean in this film
- The grid, the 112px spine and optical centring
- The 52px must-read floor, type sizes, and Poppins / Barlow Condensed / JetBrains Mono roles
- Square corners and a flat house frame
- One active focus at a time
- Panels only when they group or separate
- Joel's stated preferences: no AI imagery or video, light stock, quiet music [J]

#### Tier 3 · switch on when the job needs it · Options

- A third semantic colour (sky blue `#56B4E9`)
- Depth, shadow, glow or gradient that carries meaning
- Full-bleed UI or footage with no house ground
- Generated plates, textures, SVG art, 3D objects, when they serve the purpose better than the alternatives (Joel prefers none; see 04)
- Stepped "on twos" evidence-board look, motion blur, camera moves
- Vertical re-layouts for Shorts

> **Note · How to override a default**
>
> One line in the scene brief: **teaching job · default overridden · reason · how it was verified**, and one row in QC. If the reason can't name what the viewer will understand better, the override is decoration. That is the whole rule: purpose wins every argument in tier 2, never one in tier 1, and every win is visible.

> **Note · Facts versus choices**
>
> Separate what must come from the real world from what is open to invention. The agent may invent camera moves, composition, metaphors and a stronger opening. It may not invent a screen, a metric, a paper, a quote or a logo. If one is missing, it stops and asks. That boundary matters more than any list of adjectives.

### Where the brand spends its budget

Independent meta-analyses put the gains from good multimedia design at roughly half what single labs report, and they concentrate in a few levers. They pay off most on complex material (g 0.70 vs 0.20 for simple) and in video the viewer can't pace (0.41 vs 0.27) [E].

| Lever, as it appears on screen | Pooled effect | What the brand does with it |
|---|---|---|
| Visual lands with the spoken word | g 0.78 | Motion System owns this; the brand keeps frames calm enough for the eye to arrive on time. |
| Label sits on the object | g 0.63 | 2–3-word labels attached to what they name, not in a legend. |
| Cue what matters, sparingly | g 0.43 (retention 0.53) | One active focus; colour on the object before arrows. |
| Irrelevant extras | small cost (newest meta-analysis g −0.16), worst when they stay on screen | Ornament is opt-in and must carry meaning. |
| Warmth built into relevant elements | d 0.39 retention | Personality goes on the teaching objects, not beside them. |
| Decorative animation | g −0.05 | Never the reason a frame exists. |

Sources: Noetel et al. 2022 (29 meta-analyses, 1,189 studies); Schneider et al. 2018; Cheng et al. 2026; Brom et al. 2018; Höffler & Leutner 2007. Nearly all studies are short lab lessons, so treat these as priorities, not predicted gains.

### Keep across projects

- One clear focal idea at a time.
- Persistent objects and stable positions across related shots.
- Large, readable evidence and purposeful contrast.
- Authentic sources, precise annotation, honest labels.
- Room around the active idea so it can be read.

### Choose for each video

- The teaching job of every scene.
- What gold, red and any third colour mean in this argument.
- The composition families and which details need enlarging.
- Which specimens keep another brand's identity.
- What must stay unrevealed until the payoff.

*Figure: Final-render reference · fingerprint, 1.8s. A large teaching object and a balanced title; the later reframe makes room for examples.* (image: Final fingerprint animation with a centered title and large fingerprint on the charcoal grid.)

> **Note · An episode rule is not a channel rule**
>
> In *Frontend Design*, gold meant a human choice or evidence for human judgement, and the machine's own output never wore it. That was right for that argument. Keep the principle of consistent meaning; choose the meaning for the next subject instead of importing this episode's AI-versus-human story.

## 01 · Colour carries meaning, chosen per film

The palette is inherited and stable: its values were measured from Joel's own graphics (his threads-and-processes Short and his `Table.mp4` and `filing.mp4` references) [J]. What each colour means is decided for each video and written into `frame.md` before the first scene.

- **Ground** `#121212`: Default full-frame field.
- **Panel** `#242A36`: Structured data or a needed container.
- **Panel alt** `#1E2430`: Recessed regions, plates and mocks.
- **White** `#F8F8F8`: Primary type; what is observed now.
- **Dim** `#C9C6CA`: Context, explanation, the superseded.
- **Signal gold** `#D9A43B`: The active focus or key evidence.
- **Gold fill** `#786C36`: Solid row highlight; white text on it.
- **Working red** `#E8515A`: Refusal, failure, negative result. Always with a mark.
- **Crimson shape** `#C01218`: Large solid fills only; never text.
- **Signal blue · option** `#56B4E9`: A third meaning that must survive colour-blindness.
- **Olive** `#727854`: Subdued surface; never pass/fail against red.
- **Ground deep** `#0C0C0C`: Clean dramatic field; falloff.

### Write the colour map first

```
Gold  means: [the one thing the viewer should look at now / a human decision / key evidence]
Red   means: [refused / failed / negative result]  — always paired with a strike, ✕, label or position
Dim   means: [context, the default, the superseded]
White means: [what is being observed right now]
Blue  means: [optional third state, e.g. "the other option", "the user", "time"]
Quoted colours: [specimen values that stay literal and never become channel tokens]
```

### Gold: one active focus

- **One active cue at a time, locked to the spoken referent.** Signalling helps when it is sparing and timed with the event [E]. Dim what is not in focus instead of adding a second highlight.
- **Colour spreading on the object beats an arrow pointing at it** for showing which part matters; keep arrows for causal or directional relations [E].
- **Completed choices may stay as quieter gold context.** A selected row, its marker and the detail it explains can share gold because they are one idea.
- **Selection without a person reads by brightness:** winner at full white, the rest at 45%. Use this whenever the film separates choosing from defaulting.

### Red: never by colour alone

- `#E8515A` is the working red for words, strike bars and negative-finding highlights; it measures 5.13:1 on the ground. `#C01218` measures 2.98:1 and is for large fills only.
- Small red text sits on the ground, not on panels (4.26:1 and 3.94:1 there).
- `#E8515A` counts as saturated red under WCAG, so a pulsing red alert is a red flash however bright it is. No red pulse more than three times per second, and none over large areas [P].
- Refused is not disproved: struck items were rejected by a person; things the evidence disproved recede to dim.

### Colour vision, computed

| Pair | Normal vision | Simulated colour-vision deficiency | Consequence |
|---|---|---|---|
| Gold vs red | ΔE 38.6; luminance only 1.62:1 | Deuteranopia ΔE 12.8 | Never let gold vs red be the only difference between two states. |
| Red vs olive | Distinct | Protanopia ΔE 3.2 | Never use them as fail vs pass. |
| Sky blue `#56B4E9` vs gold or red | ΔE 51–54 | ΔE 39 or more under protan, deutan and tritan | The safe third meaning when two opposing states need colour. |

Computed with the WCAG luminance formula, CIEDE2000 and Machado et al. (2009) simulation matrices. Inference, not a user study.

| Pair | Contrast | Use |
|---|---|---|
| White / ground | 17.64:1 | Primary type. |
| Dim / ground | 11.07:1 | Secondary copy. |
| Gold / ground | 8.32:1 | Primary emphasis. |
| Sky blue / ground | 8.12:1 | Optional third meaning; 6.74:1 on panel alt. |
| Working red / ground | 5.13:1 | Red words and marks. |
| White / gold fill | 4.95:1 | Active solid row. |
| White 45% / ground | 4.36:1 | Unchosen options; never the line being read. |
| Quoted indigo `#6366F1` / ground | 4.19:1 | Evidence strokes and fills; text only inside its specimen. |
| Working red / panel | 3.94–4.26:1 | Large emphasis only. |
| Crimson shape / ground | 2.98:1 | Shapes only. |
| Gold / gold fill | 2.33:1 | Never. |

### Ornament costs; depth can teach

Interesting but irrelevant additions carry a small, consistent cost to learning (g −0.16 in the newest meta-analysis), larger when they stay on screen [E]. Small, but never worth paying for nothing. So the house frame defaults to flat, square and unornamented. That default bends whenever ornament carries meaning:

- a shadow or depth that shows one layer sits on top of another, or a stack that really is a stack;
- a glow that marks the selected state in a UI being taught;
- a gradient that is itself the subject (a quoted tell), or light that explains a physical idea;
- a warm, characterful treatment on the teaching object itself, which helps (d 0.39) where decoration beside it does not [E];
- a chapter or brand card with personality.

Specimens always keep their own gradients, radius, shadows and type: they are evidence. Their colours never become channel tokens.

> **Note · The generic demo, named**
>
> Most one-prompt Opus 5.5 videos share one look: large text in the centre, a gradient behind it, everything fading in, the logo at the end. That is what an unbriefed model produces when nobody made the decisions, the visual equivalent of the statistical middle Frontend Design argued against. These are named bans for the agent, overridable only with a logged reason.

## 02 · Type that survives a phone and a TV

The same essay plays across a room and in a phone's inline player. TV became YouTube's main US viewing device in 2025 and takes 42% of minutes watched globally, while 69% of views happen on mobile [P]. In a portrait inline player, 24px in 1080p design space is about 5pt, and 42px about 9pt, below Apple's 11pt interface minimum [I]. So text is sized by what it has to do.

| Tier | 1080p design | ≈ pt, portrait inline | Use |
|---|---|---|---|
| Reference | 24–28px | 5–6 | Citations, source lines also given in the description. Never carries the lesson. |
| Must-read floor | 52px+ | ≈11 | Anything the viewer has to read to follow. Narrated text may sit lower because the voice carries it. |
| Labels | 56–72px | 11–15 | 2–3-word labels on objects. |
| Code and prompts | 36–40px+ mono | 7–8 | Literal code, prompts, data; the whole relevant snippet, about 5–15 visible lines. Below the floor, so the line being discussed is narrated and enlarged or highlighted. |
| Headline | 76–140px | 15–28 | Statements, questions, titles. |
| Hero number | 180–340px | 37–69 | A measured value that is the point. Rare. |
| Burned-in caption | 54px | ≈11 | Final Cut's job; one to three words. |

- Context / Barlow Condensed
- Show the decision.
- Keep the object large enough to teach the idea.
- input → choice → consequence

### Labels, not paragraphs

- **2–3 words that match the spoken term, attached to the object.** Short labels placed on the part being narrated raised retention (d 0.47 and 0.70) [E].
- **Key terms beat verbatim text.** Adding text to narration is mildly positive (g 0.29), and most of that comes from key terms [E]. Use verbatim text for quotes, titles and frames with little else on them.
- **Reading budget for text that is not narrated:** about 0.375s per word plus 1s, more for long numbers and busy frames (BBC subtitle timing) [P]. Many viewers watch at 1.25–1.5×, which costs little comprehension but shortens every hold [E].

### Animated and kinetic type

No experiment shows kinetic typography improving learning, and word-by-word presentation at a fixed point impairs comprehension [E]. Any benefit comes from revealing text in step with the reasoning. So: bring whole phrases in on their spoken cue, keep must-read text still once it lands, and spend expressive type on titles, jokes, quotes and emphasis, where tone is the job.

### Code on screen

Programmers read code non-linearly, jumping around the snippet [E]. Show the whole relevant snippet, give it time, and point at the active line rather than revealing one token at a time. Building code step by step in sync with the explanation is at least as good as static code [E]. Colour coding has mixed evidence; use it for meaning (the changed line), not decoration. Mono is reserved for literal code, prompts and data.

### Numbers people can reason with

- Show the real value; say the exact figure if the screen rounds it.
- Natural frequencies ("24 out of 1,000") roughly sextupled correct probability reasoning compared with percentages [E].
- Icon arrays are the best general-purpose picture of a proportion; "1 in X" phrasing inflates perceived risk [E].
- When numbers are compared, give them a shared denominator, and end any animated chart change on a static frame that states the claim.

- **Own the line break.** Keep spoken phrases together; no stranded last words.
- **Protect letterforms.** Masks keep .14em top and .20em bottom clearance.
- **Hang opening quotes** with `text-indent:-0.044em` (measured on Poppins).
- **Centre a lone statement as a block** with its lines on one left edge; left-aligned title cards once measured their ink centroid at x≈378 against a frame centre of 960.

> **Note · Captions are separate**
>
> Burned-in A-roll captions start from Poppins Bold 54px, one to three words, top centre. Full captions belong in YouTube's caption track, checked by a person for technical terms.

## 03 · Frame, spine and safe areas

Build in **1920 × 1080 design coordinates**. The 112px editorial spine on both sides already exceeds the EBU R95 graphics-safe margin of 5% (96px) [P]. Eyebrows start near y108 and source notes near y960. During playback, keep must-read text out of the bottom 10% (below about y972), where player controls sit. The last 20 seconds of a video are a calm frame with no new information, leaving room for end screens [P].

*Diagram: 1920 by 1080 design frame with 112-pixel side spine, eyebrow at y108, optically centered subject, source note at y960 and a bottom band kept free of must-read text.*

| Composition family | Use when | What stays consistent |
|---|---|---|
| Hook / re-hook | The opening or a chapter needs a concrete promise or a misconception to overturn. | The real subject on screen fast; Joel's face and graphics alternate. |
| Isolated statement | A verdict, question, joke or title is the point. | Optical balance; deliberate line breaks. |
| Statement + specimen | The viewer needs to recognise a visible feature. | A large specimen and a label on the exact feature. |
| Source + detail | A finding needs evidence. | Source, enlarged passage, claim and citation in separate zones. |
| Controlled comparison | Two treatments must be compared. | Same input, comparable scale, stable positions. |
| Evolving demonstrator | Several decisions accumulate. | One persistent object; only the explained variable changes. |
| Mechanism canvas | A process or system has to be understood. | One canvas for the whole explanation; parts named before they move. |
| Recurring board | A method returns through the film. | Fixed geometry; the active step and detail change. |
| Footage annotation | The footage already holds the proof. | Marks follow the real object; the face stays readable. |
| Chapter card | Re-entry and orientation. | One grammar for every chapter; readable at once by a returning viewer. |

### Grounds and containers

- **Grid by job.** The 60px, 2% grid is the default for mechanisms, boards and scenes with camera moves, where it gives objects something to sit on. Verdicts, quotes, jokes and full-bleed UI intros may drop it. Test whether it survives YouTube's 1080p and 720p encodes; if it must read, thicken the lines rather than raising opacity. If it ever moves, it drifts in one direction only.
- **Clean dramatic field.** #0C0C0C–#121212 without grid for promises, quotes and punchlines.
- **Panels** (#242A36 or #1E2430, square edges) only when they group or separate information.
- **Glass overlay option** over A-roll: white 8% fill, 30% stroke, 2px border, about 40px padding. Check contrast over the actual plate.
- **Transparent annotation** has no background and no grid; marks go where the evidence is.

### Face or full frame

Seeing Joel raises motivation and slightly raises retention (g 0.22), but not transfer, and a larger presenter image predicts lower transfer because it pulls the eye away from the visual [E]. Give a must-read graphic the full frame or a small picture-in-picture that does not compete. Keep Joel's face for opinion, judgement, jokes and transitions.

> **Note · Alignment carries no meaning**
>
> Compositions that use the width hang off the 112px spine. A lone statement is centred optically. Before is left of after unless a labelled arrangement serves the comparison better; whatever is chosen stays stable across connected shots.

## 04 · Evidence, specimens and generated media

The house graphic frames the evidence; it never repaints it. Preserve an authentic page's colour, font, layout, proportions and wording. A supplied screenshot and an editable reconstruction do different jobs and need clear provenance.

*Figure: Final-render reference · scorecard-92, 10.0s. Establish the source, enlarge the actual passage, and keep the finding separate from the quotation.* (image: Research paper and an enlarged actual abstract crop beside a 92-participant finding.)

| Material | Treatment | Verification |
|---|---|---|
| Research paper | The document in its native ratio, then the actual passage enlarged and marked as it is spoken. | Page and detail share source-pixel rectangles; marks stop at word boundaries. Check each paper's licence and attribute accordingly. |
| Post or screenshot | The real capture, reframed continuously or cropped faithfully. | Re-capture at device-pixel ratio 2–3 (PDFs at 300–600 DPI) instead of AI upscaling, which can reshape letters [P]. |
| Editable specimen | Reconstruct only when parts must move, spacing must change or UI states must work. | Sample the reference; same copy and input; mark the root `data-layout-ignore` so checks don't "fix" the evidence. |
| Logo or pointer | Sourced marks, used unmodified; a pointer suited to the example. | Record provenance; an editorial agent pointer is never claimed as a native product cursor. |
| Chart or statistic | Sourced numbers with context; schematic models labelled as such. | No invented score, comparator or implied causal measurement. |
| Excerpts of others' work | Short, annotated and commented on. | Credit alone does not make a use fair; keep excerpts to what the argument needs [P]. |

### The house pointer

Human interaction uses one macOS-style pointer: black fill, 2.5px white outline with round joins, `drop-shadow(0 2px 2px rgba(0,0,0,.35))`, 44–54px tall at 1080p. Its tip touches a credible target. When an agent acts, its identity is a separate sourced logo, 62×62 at +43,+43 diagonally below-right of the pointer.

### Quoted values stay literal

Frontend Design threaded one literal value, `#6366F1` (`bg-indigo-500`), through a post, a loop, a fingerprint and an exclusion list, and that continuity was the argument. Store quoted values in a specimen file, never correct them toward the brand, and lift a hue only for a small moving mark that must stay visible.

### Generated media: atmosphere and metaphor, never evidence

> **Note · Joel's preference [J]**
>
> Joel's video brief asks for no AI imagery or AI video, because "it's too obvious." Treat it as a strong default, not a ban: the purpose of the video decides. Reach for, in order: Joel's own footage or a shot he films on request, a code-rendered graphic, licensed footage used lightly, then generated media. Use generated media when it serves the teaching purpose better than all of these, and hold it to the reason behind his preference: if a viewer would notice it as AI, it has not earned its place. Log the override with its reason and keep the asset in the provenance log.

The toolset as of October 2026 [P]. Vendors withdraw models fast (OpenAI shut the Sora 2 API on 24 September 2026), so log the exact model and date for every asset.

| Need | Starting tools | How it enters the frame |
|---|---|---|
| Metaphor shot or background plate | Wan 3.0, Seedance 2.5, Kling 3.0, Veo 3.1; Luma Ray3 for 16-bit HDR EXR | Mostly 720p–1080p, 24fps, 4–30s clips. Under the code-rendered type and diagrams, graded to the house look. Start/end-frame interpolation lands a plate on the first frame of an HTML scene. |
| Illustration GSAP can draw or morph | Recraft V4 / V4.1 (native editable SVG) | Cleaned SVG paths animated in code. |
| Ideation and storyboards | Nano Banana Pro | Reference only; its in-image text is never final. |
| 3D object | Rodin Gen-2, Meshy-6 | GLB into HyperFrames' Three.js adapter. |
| Sound effect | Joel's Epidemic Sound and Envato libraries first; ElevenLabs SFX v2 (loopable, 48kHz) when no licensed sound fits | Mixed in the edit, never baked into masters. Check each tool's commercial terms. |

- **Never generated:** text, data, charts, UI or papers presented as real. No likeness of a real person, and no AI avatar or voice clone standing in for Joel.
- **No mainstream video model outputs alpha.** Key or remove the background and deliver ProRes 4444.
- **Disclosure:** YouTube requires it for realistic content a viewer could mistake for real; animation, AI-assisted scripts and upscaling are exempt [P].
- **Trust:** AI-made instructional video teaches about as well but is rated less engaging and less credible, and AI labels lower trust [E]. Keep the teaching and the evidence human-authored and real.
- **Originality:** YouTube demonetises mass-produced, templated AI content. Shared tokens are fine; each film's argument, evidence and choreography must be its own [P].
- **Provenance log:** model ID, prompt, seed, date, plan tier and licence for every generated asset. Prompts alone do not make an author under US Copyright Office guidance; the human arrangement does.

*Figure: Final-render reference · button-states, 5.0s. Identical action, visibly different decisions. Specimen colours and rounded buttons remain intact; channel labels stay neutral.* (image: Two button designs with the same Schedule a visit label shown side by side.)

Keep disclosures that prevent factual confusion ("illustrative probabilities", "schematic outputs"). Remove production explanations and captions that repeat a visible demonstration. Never turn one episode's critique (no indigo, no Inter, no rounded cards) into a ban on faithfully showing another brand.

## 05 · Start the next project

1. **Read Joel's brief for this video and `joel-decisions.md`.** If he gave timestamped notes, they are the starting placements. If he left placement open, write the visual plan first (Motion System, section 06).
2. **Write the visual argument.** What should the viewer understand, and which object can demonstrate it?
3. **Give every scene a teaching job** (Motion System v3.2, section 01). The job sets the defaults.
4. **Analyse the references into `style-guide.md`** (template below). Any missing asset is listed as a blocker.
5. **Write the colour map** and check any two-state contrast for colour-vision safety.
6. **Make the project truth file.** `frame.md`, one token stylesheet, local fonts, the named-bans list.
7. **Pin HyperFrames for this video** and confirm the delivery spec from the edit: aspect ratio, exact frame rate, alpha needs.
8. **Build one representative scene,** review it with narration at phone size, then multiply.

### Reference analysis → this video's style guide

If you don't supply a visual grammar, the model supplies its own; that is why unrelated one-prompt reels look related. Give the agent something to inspect (a frame, a film, Joel's earlier videos, the Inspiration folder) and make it write down what it learned before anything moves. The output is a style guide, not a collage of borrowed shots. This Brand System is the channel layer; `style-guide.md` is the per-video layer on top.

```
REFERENCE ANALYSIS
Palette:      [actual hex values, not "premium"]
Typography:   [family, width, weight, scale]
Composition:  [where the eye goes first]
Pacing:       [average time between meaningful changes]
Motion:       [snap, glide, settle, cut, hold, per class of object]
Texture:      [grain, paper, glass, none]
Keep:         [specific traits this video borrows]
DO NOT COPY:  [subjects, logos, copy, product-specific imagery]
```

### One story, three formats

A Shorts cut is a different composition, not a crop. Keep the assets, states and cue map; redefine the layout. Render a contact sheet for every variant: it is correct when the composition survived the format change, not when the encoder finished.

| Format | Layout behaviour |
|---|---|
| 16:9 master | Spatial context; this whole system. |
| 9:16 Shorts | Fewer simultaneous elements, larger type, stronger vertical hierarchy, a different camera path, a tighter story. Keep must-read text clear of the bottom fifth and the right-hand button column, and check on a phone [I]. |
| 1:1 | Tighter typography, shorter holds. |

### CSS starter · 1080p design space

```
:root {
  --ground: #121212; --ground-deep: #0C0C0C;
  --panel: #242A36; --panel-alt: #1E2430;
  --white: #F8F8F8; --dim: #C9C6CA; --white-45: rgba(248,248,248,.45);
  --gold: #D9A43B; --gold-fill: #786C36;
  --red: #E8515A; --crimson-fill: #C01218;
  --blue: #56B4E9;            /* optional third meaning */
  --olive: #727854;
  --panel-stroke: rgba(255,255,255,.30);
  --panel-fill: rgba(255,255,255,.08);
  --grid-line: rgba(255,255,255,.02); --grid-gap: 60px;
  --spine: 112px; --content-width: 1696px; --radius: 0;
  --t-reference: 24px;        /* citations only */
  --t-must-read: 52px;        /* floor for text the viewer must read */
  --t-label: 60px; --t-mono: 38px;
  --t-headline: 100px; --t-display: 140px; --t-hero: 300px;
}
/* Specimen colours live in specimens.js, never here. */
```

### Copy-ready project brief

```
Use MergeToMaster Brand System v3.2 and Motion System v3.2. Purpose first:
every default may bend for a stated teaching purpose; the five invariants never do.
Create frame.md for this project before authoring scenes.

Project / audience: [fill in]
The viewer should remember (one sentence): [fill in]
Joel's notes for this video: [timestamped placements, or "placement left open" -> visual plan first]
Joel's standing preferences that apply: [from joel-decisions.md]
Facts that must come from real assets: [screens, papers, numbers, logos]
Choices open to the agent: [camera, composition, metaphor, openings]
Unacceptable if: [e.g. an invented screen, a misattributed quote]
References allowed to influence: [paths] -> style-guide.md
Edit format / exact fps: [confirm from the timeline]
Teaching job per scene: [hook, cast of characters, mechanism, connect,
  evidence, comparison/statistic, procedure/UI, verdict/joke, chapter]
Gold means: [ ]   Red means: [ ] (always with a mark)   Blue (optional): [ ]
Sources and authentic assets: [paths + provenance]
Specimens needing reconstruction: [reason + reference]
Generated media: [none by default (Joel's preference); each use + reason + provenance log]
What stays unrevealed until the payoff: [ ]
Overrides planned: [job · default · reason · how verified]

Invariants: no more than 3 flashes/second; evidence real and literal;
must-read text readable at phone size on the encode (default floor 52px at 1080p);
meaning never by hue alone;
seek-safe scenes, exact fps, verified alpha.
Review the encoded output with narration at phone size.
```

## 06 · Review and maintain the system

- Every scene names its teaching job, and every override is logged with its reason and check.
- Must-read text reads at phone size on the encode (52px default, or a logged override); reference text never carries the lesson.
- Every colour-coded state also has a shape, mark, label or position.
- Every accent supports one coherent focal idea at a time.
- Evidence is authentic, correctly proportioned and precisely highlighted; generated assets are logged and never pose as evidence.
- Any generated imagery or video has a logged reason and would not be noticed as AI by a viewer.
- Nothing must-read sits below y972; the last 20 seconds stay calm.
- No hex typed outside the token sheet or the specimen file; every gold appearance has a reason in the colour map.
- On-screen strings are free of production words.
- The taught detail is readable at phone size, checked on the encode.
- Each master's final settled frame works as a still on its own (poster test).
- Every format variant has its own contact sheet.
- Nothing in the frame is the generic demo by default: centred text over a gradient, uniform fades.

### What changed from v2, in v3.1 and in v3.2

| Before | Now |
|---|---|
| v3.1: tags E, P, I only | v3.2: a J tag for Joel's own words, rulings and videos; rule IDs in `rules.md`; his rulings dated in `joel-decisions.md`. |
| v3.1: the 52px floor listed as never bending | v3.2: legibility at phone size is the invariant; 52px is the default that meets it, tested per video. |
| v3.1: generated media as an open option | v3.2: Joel's preference recorded as a strong default with an order of alternatives; used when it serves the purpose better, with a logged reason. |
| v3.1: Edit System brand rules partly in force | v3.2: Edit System v1.1 covers only the edit; its conflicting rules resolved in favour of this system. |
| v3.1: start assumes Joel's placement notes | v3.2: when Joel leaves placement open, a visual plan comes first. |
| v3: evidence fidelity | v3.1: facts versus choices made explicit; a missing asset blocks the build. |
| v3: channel style only | v3.1: a per-video reference analysis written to `style-guide.md`. |
| v3: Shorts as an option | v3.1: one story, three formats, each its own composition. |
| v3: decoration discouraged | v3.1: the generic Opus demo named and banned by default. |
| Rules and exceptions mixed in one list | Three tiers: five invariants, purpose-scoped defaults, options; overrides logged. |
| 24px floor for house type | Tiers by job: reference 24–28px, must-read 52px+, labels 56–72px, mono 36–40px+. |
| Red defined by colour | Red always paired with a mark; colour-vision checks; optional sky-blue third meaning. |
| No gradients, shadows or glow | Flat by default; depth, glow or gradient allowed when it carries meaning. |
| Grid on by default | Grid chosen by teaching job; encode test. |
| Generated media not covered | Tools, roles, provenance, disclosure and trust rules. |
| Safe areas implied | Bottom-10% band and a calm 20-second end-screen tail. |
| Kinetic type unaddressed | Phrases land whole; expressive type spent on tone, not on must-read text. |

Treat v3 as a set of hypotheses for Joel's channel: the research comes from short lab lessons, not 12-minute YouTube essays. Change one variable per video (the 52px floor, summary holds after complex builds), note the timestamps, and read them against the key-moments section of the audience-retention report. Update both systems together when a shared rule changes, and archive the previous version. A rule changes when the channel changes or when Joel rules on it; record his ruling in `joel-decisions.md` first.

### Sources

- [joel-decisions.md](../joel-decisions.md) and [Edit System v1.1](../MergeToMaster%20-%20Edit%20System%20v1.md) — Joel's brief, preferences and rulings, the [J] sources.
- [reports / Claude Opus educational motion graphics.md](../reports/Claude%20Opus%20educational%20motion%20graphics.md) — the October 2026 research synthesis behind v3, with links to every study and policy page.
- [research_notes / Claude Opus educational motion graphics](../research_notes/Claude%20Opus%20educational%20motion%20graphics/) — six sets of notes: Opus 5.5, HyperFrames and code video, learning science and its follow-up, explainer craft, generative media and accessibility.
- [Motion Engineering: Build a Video Studio Around Opus 5.5](https://x.com/0xwhrrari/article/2105643919119696297) (@0xwhrrari, 1 Oct 2026) — practitioner article behind facts versus choices, reference analysis, formats and the named generic demo. Practice, not evidence.
- [lib/refinement.css](../../P1%20-%20Frontend%20Design/Animations%20using%20Hyperframes/MergeToMaster/lib/refinement.css) and [lib/scenes.js](../../P1%20-%20Frontend%20Design/Animations%20using%20Hyperframes/MergeToMaster/lib/scenes.js) — the Frontend Design implementation this system grew from.
- [renders/v08/README.md](../../P1%20-%20Frontend%20Design/Animations%20using%20Hyperframes/MergeToMaster/renders/v08/README.md), [VIEWER-NOTE-AUDIT.md](../../P1%20-%20Frontend%20Design/Animations%20using%20Hyperframes/MergeToMaster/renders/v08/VIEWER-NOTE-AUDIT.md), [client-fixes/2026-09-14/DELIVERY.md](../../P1%20-%20Frontend%20Design/Animations%20using%20Hyperframes/MergeToMaster/client-fixes/2026-09-14/DELIVERY.md) — resolved revisions and Joel's final fixes.

Previous versions: v3.1 in [System Archive / 2026-10-05-v3.1-before-v3.2](../System%20Archive/2026-10-05-v3.1-before-v3.2/); v3 in [System Archive / 2026-10-05-v3-before-studio-update](../System%20Archive/2026-10-05-v3-before-studio-update/); v2 in [System Archive / 2026-10-05-v2-before-purpose-rewrite](../System%20Archive/2026-10-05-v2-before-purpose-rewrite/); v1 in [_archive v1](../_archive%20v1/).

MergeToMaster · Brand System v3.2
Revised 05 October 2026 · Purpose first · Based on Frontend Design production and October 2026 research.
