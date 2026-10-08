# P2 showcase · the animations, as AEM's evidence shows them

Status as of 9 Oct 2026. Each moment below is an animation this pipeline built for Joel Belton's Claude Code video (P2). The frames are **readable poses** that `aem evidence` extracted from the latest checked render (a pose is where the picture settles for a quarter second), downscaled to 960 px, plus the **strip** of frames around the fastest transition. Nothing here is Joel's footage or his terminal; those moments are left out on purpose. The renders themselves (3840x2160, 25 fps) stay in the project folder; where a 1080p proxy is linked, GitHub plays it on the file page. Max sync is the largest offset, in frames, between a cue word's onset and the pose settling on it.

18 animation moments. Measured state: [P2-STATUS.md](../P2-STATUS.md); method: [CASE-STUDY.md](../CASE-STUDY.md). Built by `docs/tools/showcase.py`.

| Moment | Teaching job | Latest render | Check | Max sync | Poses | Video |
|---|---|---|---|---|---:|---|
| [cc_S00_agenda](#ccs00agenda) | Hook | `cc_S00_agenda_v03.mp4` | pass | 17f | 8 | [1080p](video/cc_S00_agenda.mp4) |
| [cc_S01_three-dials](#ccs01threedials) | Cast of characters | `cc_S01_three-dials_v03.mp4` | pass | 9f | 6 | [1080p](video/cc_S01_three-dials.mp4) |
| [cc_S01_model](#ccs01model) | Cast of characters | `cc_S01_model_v01.mp4` | pass | 11f | 5 | [1080p](video/cc_S01_model.mp4) |
| [cc_S01_effort-levels](#ccs01effortlevels) | Comparison / statistic | `cc_S01_effort-levels_v04.mp4` | pass | 1f | 12 | [1080p](video/cc_S01_effort-levels.mp4) |
| [cc_S03_window](#ccs03window) | Cast of characters → mechanism | `cc_S03_window_v01.mp4` | pass | 49f | 10 | [1080p](video/cc_S03_window.mp4) |
| [cc_S03_40-60](#ccs034060) | Comparison / statistic | `cc_S03_40-60_v01.mp4` | pass | 7f | 4 | [1080p](video/cc_S03_40-60.mp4) |
| [cc_S04_offload](#ccs04offload) | Comparison (mechanism) | `cc_S04_offload_v01.mp4` | pass | 25f | 17 | [1080p](video/cc_S04_offload.mp4) |
| [cc_S04_agent-file](#ccs04agentfile) | Code walkthrough | `cc_S04_agent-file_v02.mp4` | pass | 14f | 8 | [1080p](video/cc_S04_agent-file.mp4) |
| [cc_S04_fan-out](#ccs04fanout) | Connect / vary together | `cc_S04_fan-out_v01.mp4` | pass | 16f | 13 | [1080p](video/cc_S04_fan-out.mp4) |
| [cc_S05_not-that-memory](#ccs05notthatmemory) | Verdict / joke | `cc_S05_not-that-memory_v02.mp4` | pass | not measured | 2 | [1080p](video/cc_S05_not-that-memory.mp4) |
| [cc_S05_loaded-every-run](#ccs05loadedeveryrun) | Connect / vary together | `cc_S05_loaded-every-run_v01.mp4` | pass | 34f | 5 | [1080p](video/cc_S05_loaded-every-run.mp4) |
| [cc_S05_docs-guidance](#ccs05docsguidance) | Evidence | `cc_S05_docs-guidance_v01.mp4` | pass | 11f | 16 | [1080p](video/cc_S05_docs-guidance.mp4) |
| [cc_S05_less-is-more](#ccs05lessismore) | Comparison / statistic | `cc_S05_less-is-more_v05.mp4` | pass | 34f | 13 | [1080p](video/cc_S05_less-is-more.mp4) |
| [cc_S06_critical](#ccs06critical) | Comparison | `cc_S06_critical_v04.mp4` | pass | 12f | 20 | [1080p](video/cc_S06_critical.mp4) |
| [cc_S06_prototyping](#ccs06prototyping) | Comparison | `cc_S06_prototyping_v05.mp4` | pass | 26f | 17 | [1080p](video/cc_S06_prototyping.mp4) |
| [cc_S07_course-correct](#ccs07coursecorrect) | Procedure / UI demo | `cc_S07_course-correct_v03.mp4` | pass | 28f | 4 | [1080p](video/cc_S07_course-correct.mp4) |
| [cc_S07_ask-questions](#ccs07askquestions) | Procedure / UI demo | `cc_S07_ask-questions_v01.mp4` | pass | 12f | 6 | [1080p](video/cc_S07_ask-questions.mp4) |
| [cc_S09_mcp](#ccs09mcp) | Mechanism | `cc_S09_mcp_v04.mp4` | pass | 36f | 9 | [1080p](video/cc_S09_mcp.mp4) |

## cc_S00_agenda

**Teaching job:** Hook. **On his words:** "We're going to talk CLI, skills, MCP, context management, memory, multi-agents, and a lot of common mistakes t…"

**Why (from the plan):** Seven topics in 9 s are hard to hold by ear; the promise made concrete is the hook's job (Motion 01). Joel asked for dark-ground title cards in P1 (#7).

Latest render `cc_S00_agenda_v03.mp4` · check pass · max sync 17f · evidence v03, 8 readable poses. **[Watch the 1080p proxy](video/cc_S00_agenda.mp4)** (GitHub plays it on the file page).

![cc_S00_agenda f0000.jpg](cc_S00_agenda/f0000.jpg) ![cc_S00_agenda f0049.jpg](cc_S00_agenda/f0049.jpg) ![cc_S00_agenda f0113.jpg](cc_S00_agenda/f0113.jpg) ![cc_S00_agenda f0221.jpg](cc_S00_agenda/f0221.jpg)

Fastest transition: ![strip](cc_S00_agenda/strip.jpg)

## cc_S01_three-dials

**Teaching job:** Cast of characters. **On his words:** "So obviously the three main dials that you have on Claude are your mode, your model, and your effort level."

**Why (from the plan):** Organises the next minute and a quarter (mode, model, effort) on one object, and shows where each dial lives in the real interface (B-23, Brand 03 statement + specimen).

Latest render `cc_S01_three-dials_v03.mp4` · check pass · max sync 9f · evidence v03, 6 readable poses. **[Watch the 1080p proxy](video/cc_S01_three-dials.mp4)** (GitHub plays it on the file page).

![cc_S01_three-dials f0000.jpg](cc_S01_three-dials/f0000.jpg) ![cc_S01_three-dials f0081.jpg](cc_S01_three-dials/f0081.jpg) ![cc_S01_three-dials f0098.jpg](cc_S01_three-dials/f0098.jpg) ![cc_S01_three-dials f0179.jpg](cc_S01_three-dials/f0179.jpg)

Fastest transition: ![strip](cc_S01_three-dials/strip.jpg)

## cc_S01_model

**Teaching job:** Cast of characters. **On his words:** "In terms of model, at the time of recording this video, Opus and Fable 5 are the most recent and capable model…"

**Why (from the plan):** Completes the three dials (mode and effort are shown; model was only named) and shows where it is chosen. The newest of each are marked, as asked: his 'at the time of recording' covers the step from his Opus 5 and Fable 

Latest render `cc_S01_model_v01.mp4` · check pass · max sync 11f · evidence v01, 5 readable poses. **[Watch the 1080p proxy](video/cc_S01_model.mp4)** (GitHub plays it on the file page).

![cc_S01_model f0000.jpg](cc_S01_model/f0000.jpg) ![cc_S01_model f0011.jpg](cc_S01_model/f0011.jpg) ![cc_S01_model f0119.jpg](cc_S01_model/f0119.jpg) ![cc_S01_model f0203.jpg](cc_S01_model/f0203.jpg)

Fastest transition: ![strip](cc_S01_model/strip.jpg)

## cc_S01_effort-levels

**Teaching job:** Comparison / statistic. **On his words:** "And last up is effort. So again, as it stands, there are five different effort levels. There's a low, medium, …"

**Why (from the plan):** Five ordered items are easier seen than heard, and his choice needs a place on the scale.

Latest render `cc_S01_effort-levels_v04.mp4` · check pass · max sync 1f · evidence v04, 12 readable poses. **[Watch the 1080p proxy](video/cc_S01_effort-levels.mp4)** (GitHub plays it on the file page).

![cc_S01_effort-levels f0000.jpg](cc_S01_effort-levels/f0000.jpg) ![cc_S01_effort-levels f0115.jpg](cc_S01_effort-levels/f0115.jpg) ![cc_S01_effort-levels f0163.jpg](cc_S01_effort-levels/f0163.jpg) ![cc_S01_effort-levels f0313.jpg](cc_S01_effort-levels/f0313.jpg)

Fastest transition: ![strip](cc_S01_effort-levels/strip.jpg)

## cc_S03_window

**Teaching job:** Cast of characters → mechanism. **On his words:** "Well, your model will hold about 200k to about a million tokens in its current memory window. This will typica…"

**Why (from the plan):** Named at G1: context is the video's thread; the window is the object later moments reuse.

Latest render `cc_S03_window_v01.mp4` · check pass · max sync 49f · evidence v01, 10 readable poses. **[Watch the 1080p proxy](video/cc_S03_window.mp4)** (GitHub plays it on the file page).

![cc_S03_window f0000.jpg](cc_S03_window/f0000.jpg) ![cc_S03_window f0165.jpg](cc_S03_window/f0165.jpg) ![cc_S03_window f0244.jpg](cc_S03_window/f0244.jpg) ![cc_S03_window f0341.jpg](cc_S03_window/f0341.jpg)

Fastest transition: ![strip](cc_S03_window/strip.jpg)

## cc_S03_40-60

**Teaching job:** Comparison / statistic. **On his words:** "And it seems current best practice points to using to about 40 to 60% of your available context window with an…"

**Why (from the plan):** A percentage range is a position on a bar; the real readout shows the same range in Claude Code, and /compact is the manual step.

Latest render `cc_S03_40-60_v01.mp4` · check pass · max sync 7f · evidence v01, 4 readable poses. **[Watch the 1080p proxy](video/cc_S03_40-60.mp4)** (GitHub plays it on the file page).

![cc_S03_40-60 f0000.jpg](cc_S03_40-60/f0000.jpg) ![cc_S03_40-60 f0071.jpg](cc_S03_40-60/f0071.jpg) ![cc_S03_40-60 f0198.jpg](cc_S03_40-60/f0198.jpg) ![cc_S03_40-60 f0206.jpg](cc_S03_40-60/f0206.jpg)

Fastest transition: ![strip](cc_S03_40-60/strip.jpg)

## cc_S04_offload

**Teaching job:** Comparison (mechanism). **On his words:** "It reads 10 files, grep through some logs, runs a few commands, and every bit of that lands in your main conte…"

**Why (from the plan):** Named at G1: the section's argument is a before and after of what lands in the main window.

Latest render `cc_S04_offload_v01.mp4` · check pass · max sync 25f · evidence v01, 17 readable poses. **[Watch the 1080p proxy](video/cc_S04_offload.mp4)** (GitHub plays it on the file page).

![cc_S04_offload f0000.jpg](cc_S04_offload/f0000.jpg) ![cc_S04_offload f0177.jpg](cc_S04_offload/f0177.jpg) ![cc_S04_offload f0372.jpg](cc_S04_offload/f0372.jpg) ![cc_S04_offload f0498.jpg](cc_S04_offload/f0498.jpg)

Fastest transition: ![strip](cc_S04_offload/strip.jpg)

## cc_S04_agent-file

**Teaching job:** Code walkthrough. **On his words:** "You spin one up by dropping a markdown file in .claude slash agents. Give it a name, a description, and when t…"

**Why (from the plan):** 'Drop a markdown file' is only actionable once the viewer has seen the file.

Latest render `cc_S04_agent-file_v02.mp4` · check pass · max sync 14f · evidence v02, 8 readable poses. **[Watch the 1080p proxy](video/cc_S04_agent-file.mp4)** (GitHub plays it on the file page).

![cc_S04_agent-file f0000.jpg](cc_S04_agent-file/f0000.jpg) ![cc_S04_agent-file f0053.jpg](cc_S04_agent-file/f0053.jpg) ![cc_S04_agent-file f0211.jpg](cc_S04_agent-file/f0211.jpg) ![cc_S04_agent-file f0314.jpg](cc_S04_agent-file/f0314.jpg)

Fastest transition: ![strip](cc_S04_agent-file/strip.jpg)

## cc_S04_fan-out

**Teaching job:** Connect / vary together. **On his words:** "You're not even limited to just one subagent. You can send several agents going off and doing different things…"

**Why (from the plan):** 'A whole little team' is about parallel, isolated work; the picture shows it. A rebuilt Claude Code parallel-agent screen would need a real reference we don't have (B-T1-02).

Latest render `cc_S04_fan-out_v01.mp4` · check pass · max sync 16f · evidence v01, 13 readable poses. **[Watch the 1080p proxy](video/cc_S04_fan-out.mp4)** (GitHub plays it on the file page).

![cc_S04_fan-out f0000.jpg](cc_S04_fan-out/f0000.jpg) ![cc_S04_fan-out f0095.jpg](cc_S04_fan-out/f0095.jpg) ![cc_S04_fan-out f0220.jpg](cc_S04_fan-out/f0220.jpg) ![cc_S04_fan-out f0350.jpg](cc_S04_fan-out/f0350.jpg)

Fastest transition: ![strip](cc_S04_fan-out/strip.jpg)

## cc_S05_not-that-memory

**Teaching job:** Verdict / joke. **On his words:** "provide it some memory. No, not that kind of memory."

**Why (from the plan):** Joel writes jokes in; they land when the edit acknowledges them (Edit 04). A drawing is honest where a photo would read as stock (J-02).

Latest render `cc_S05_not-that-memory_v02.mp4` · check pass · max sync not measured · evidence v02, 2 readable poses. **[Watch the 1080p proxy](video/cc_S05_not-that-memory.mp4)** (GitHub plays it on the file page).

![cc_S05_not-that-memory f0000.jpg](cc_S05_not-that-memory/f0000.jpg) ![cc_S05_not-that-memory f0011.jpg](cc_S05_not-that-memory/f0011.jpg)

Fastest transition: ![strip](cc_S05_not-that-memory/strip.jpg)

## cc_S05_loaded-every-run

**Teaching job:** Connect / vary together. **On his words:** "Files you can define and include and load into Claude every time it runs. For example, CLAUDE.md is a markdown…"

**Why (from the plan):** Ties memory back to context, the video's thread, in one picture: the file is part of the window, every session.

Latest render `cc_S05_loaded-every-run_v01.mp4` · check pass · max sync 34f · evidence v01, 5 readable poses. **[Watch the 1080p proxy](video/cc_S05_loaded-every-run.mp4)** (GitHub plays it on the file page).

![cc_S05_loaded-every-run f0000.jpg](cc_S05_loaded-every-run/f0000.jpg) ![cc_S05_loaded-every-run f0114.jpg](cc_S05_loaded-every-run/f0114.jpg) ![cc_S05_loaded-every-run f0211.jpg](cc_S05_loaded-every-run/f0211.jpg) ![cc_S05_loaded-every-run f0231.jpg](cc_S05_loaded-every-run/f0231.jpg)

Fastest transition: ![strip](cc_S05_loaded-every-run/strip.jpg)

## cc_S05_docs-guidance

**Teaching job:** Evidence. **On his words:** "Claude themselves actually gave some guidance on this. It recommends we do bash commands that Claude can't gue…"

**Why (from the plan):** Named at G1: Joel reads Anthropic's own guidance at list speed; the real source makes it readable and checkable.

Latest render `cc_S05_docs-guidance_v01.mp4` · check pass · max sync 11f · evidence v01, 16 readable poses. **[Watch the 1080p proxy](video/cc_S05_docs-guidance.mp4)** (GitHub plays it on the file page).

![cc_S05_docs-guidance f0000.jpg](cc_S05_docs-guidance/f0000.jpg) ![cc_S05_docs-guidance f0225.jpg](cc_S05_docs-guidance/f0225.jpg) ![cc_S05_docs-guidance f0526.jpg](cc_S05_docs-guidance/f0526.jpg) ![cc_S05_docs-guidance f0732.jpg](cc_S05_docs-guidance/f0732.jpg)

Fastest transition: ![strip](cc_S05_docs-guidance/strip.jpg)

## cc_S05_less-is-more

**Teaching job:** Comparison / statistic. **On his words:** "When it comes to this file, often less is considered more. And here's a nice way to remember it. Don't tell Cl…"

**Why (from the plan):** A rule meant to be remembered ('here's a nice way to remember it') and two numbers; Joel liked spoken key lines on screen in P1.

Latest render `cc_S05_less-is-more_v05.mp4` · check pass · max sync 34f · evidence v05, 13 readable poses. **[Watch the 1080p proxy](video/cc_S05_less-is-more.mp4)** (GitHub plays it on the file page).

![cc_S05_less-is-more f0000.jpg](cc_S05_less-is-more/f0000.jpg) ![cc_S05_less-is-more f0146.jpg](cc_S05_less-is-more/f0146.jpg) ![cc_S05_less-is-more f0281.jpg](cc_S05_less-is-more/f0281.jpg) ![cc_S05_less-is-more f0391.jpg](cc_S05_less-is-more/f0391.jpg)

Fastest transition: ![strip](cc_S05_less-is-more/strip.jpg)

## cc_S06_critical

**Teaching job:** Comparison. **On his words:** "They do different things when it comes to prototyping and simple features and when it comes to implementing bu…"

**Why (from the plan):** Claude Code itself, redrawn (Yuvraj, 8 Oct: the real UI, designed, not B-roll; references in `reviews/S06/ui-reference/`): 'Prototyping' left, 'Critical features' right, the same tool's first screen under each. The criti

Latest render `cc_S06_critical_v04.mp4` · check pass · max sync 12f · evidence v04, 20 readable poses. **[Watch the 1080p proxy](video/cc_S06_critical.mp4)** (GitHub plays it on the file page).

![cc_S06_critical f0000.jpg](cc_S06_critical/f0000.jpg) ![cc_S06_critical f0316.jpg](cc_S06_critical/f0316.jpg) ![cc_S06_critical f0531.jpg](cc_S06_critical/f0531.jpg) ![cc_S06_critical f0877.jpg](cc_S06_critical/f0877.jpg)

Fastest transition: ![strip](cc_S06_critical/strip.jpg)

## cc_S06_prototyping

**Teaching job:** Comparison. **On his words:** "But whereas for prototyping, they tend to make a very different approach. They use auto mode for pretty much e…"

**Why (from the plan):** Same canvas: the prototyping session switches to auto mode (Shift+Tab), takes one short prompt, and Claude writes, runs the tests (two fail), fixes, runs (one fails), fixes, runs (all pass): a loop that really runs, name

Latest render `cc_S06_prototyping_v05.mp4` · check pass · max sync 26f · evidence v05, 17 readable poses. **[Watch the 1080p proxy](video/cc_S06_prototyping.mp4)** (GitHub plays it on the file page).

![cc_S06_prototyping f0000.jpg](cc_S06_prototyping/f0000.jpg) ![cc_S06_prototyping f0209.jpg](cc_S06_prototyping/f0209.jpg) ![cc_S06_prototyping f0360.jpg](cc_S06_prototyping/f0360.jpg) ![cc_S06_prototyping f0569.jpg](cc_S06_prototyping/f0569.jpg)

Fastest transition: ![strip](cc_S06_prototyping/strip.jpg)

## cc_S07_course-correct

**Teaching job:** Procedure / UI demo. **On his words:** "You want to be course correcting early. So escape to cancel out existing runs, using rewind and clear to go ba…"

**Why (from the plan):** A key press is invisible in a recording, so a drawn key shows it; the rows reuse real evidence the viewer has already seen.

Latest render `cc_S07_course-correct_v03.mp4` · check pass · max sync 28f · evidence v03, 4 readable poses. **[Watch the 1080p proxy](video/cc_S07_course-correct.mp4)** (GitHub plays it on the file page).

![cc_S07_course-correct f0000.jpg](cc_S07_course-correct/f0000.jpg) ![cc_S07_course-correct f0064.jpg](cc_S07_course-correct/f0064.jpg) ![cc_S07_course-correct f0146.jpg](cc_S07_course-correct/f0146.jpg) ![cc_S07_course-correct f0187.jpg](cc_S07_course-correct/f0187.jpg)

Fastest transition: ![strip](cc_S07_course-correct/strip.jpg)

## cc_S07_ask-questions

**Teaching job:** Procedure / UI demo. **On his words:** "If you're not sure whether you've given it enough information, just tell it to ask you some questions. This wa…"

**Why (from the plan):** Clear spoken; his face carries the advice (B-22).

Latest render `cc_S07_ask-questions_v01.mp4` · check pass · max sync 12f · evidence v01, 6 readable poses. **[Watch the 1080p proxy](video/cc_S07_ask-questions.mp4)** (GitHub plays it on the file page).

![cc_S07_ask-questions f0000.jpg](cc_S07_ask-questions/f0000.jpg) ![cc_S07_ask-questions f0089.jpg](cc_S07_ask-questions/f0089.jpg) ![cc_S07_ask-questions f0201.jpg](cc_S07_ask-questions/f0201.jpg) ![cc_S07_ask-questions f0256.jpg](cc_S07_ask-questions/f0256.jpg)

Fastest transition: ![strip](cc_S07_ask-questions/strip.jpg)

## cc_S09_mcp

**Teaching job:** Mechanism. **On his words:** "MCP stands for Model Context Protocol. It's basically a standard way to plug external tools into your agent. S…"

**Why (from the plan):** 'A standard way to plug tools in' is abstract; one before and after makes it concrete.

Latest render `cc_S09_mcp_v04.mp4` · check pass · max sync 36f · evidence v04, 9 readable poses. **[Watch the 1080p proxy](video/cc_S09_mcp.mp4)** (GitHub plays it on the file page).

![cc_S09_mcp f0000.jpg](cc_S09_mcp/f0000.jpg) ![cc_S09_mcp f0122.jpg](cc_S09_mcp/f0122.jpg) ![cc_S09_mcp f0197.jpg](cc_S09_mcp/f0197.jpg) ![cc_S09_mcp f0328.jpg](cc_S09_mcp/f0328.jpg)

Fastest transition: ![strip](cc_S09_mcp/strip.jpg)

