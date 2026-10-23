# P2 status · Claude Code video · MergeToMaster

Status as of 9 Oct 2026, 23:30 IST. Generated from `aem moments` (`moments/index.json`), `aem report` (`reports/time.md`) and `events.jsonl` in the P2 project folder by `docs/tools/p2status.py`. The tables below are that 9 Oct snapshot, unchanged.

## Delivery and review (23 Oct 2026, reconstructed)

- **Delivered:** `P2 - Claude Code Done.mov`, exported 15 Oct 2026, 02:00 IST; on Frame.io at [f.io/dBF09OXt](https://f.io/dBF09OXt). SHA-256 `7029f2311417bf611be9c6e88e6f768b104be7dd195b654e49f515ba761058da`, 3840×2160, 25 fps, 666.36 s.
- **Joel's review:** accepted with no changes on WhatsApp, 19 Oct 2026: "Hi, no I think its all ready to go :) happy for you to send me the invoice". 0 Frame.io comments on the share page, 23 Oct. Screenshots, transcript and hashes: [p2-review](p2-review/README.md).
- **Not in AEM yet:** Joel's words wait for the operator's `client-said`; the master went out with 0 standing approvals and no delivery event in `events.jsonl` (measured).

## Counts (measured by AEM unless marked)

- Named moments in the plan: **47** (`aem moments` lists 68 rows; the other 21 are table headings and scene labels it read from `visual-plan.md` and `shotlist.md`, a parsing defect noted in CASE-STUDY §g).
- Treatments: animation 20, footage 8, screen recording 8, nothing 6, joel's terminal, re-typeset 5.
- Direction: none (0 notes from Joel); asked 7, added 61 (every moment is ours to decide).
- Moments with at least one render checked: **39**; render versions checked: **79**; check failures: **5**.
- Evidence runs (`aem evidence`): **83** renders.
- Render versions where `check-render` flagged one- or two-frame luma flashes (area 0.02–0.04 % of frame): **14**; the evidence notes record no flash for any render.
- Standing approvals: **0**; stale: **1** (cc_S00_agenda_v02.mp4 superseded by cc_S00_agenda_v03.mp4).
- Failed checks: `cc_S08_skills-list_v03.mp4` (fail: short flashes (1-2 frames): expected 0, got 3); `cc_S00_promise_v01.mov` (fail: alpha: expected False, got True); `cc_S00_promise_v02.mov` (fail: alpha: expected False, got True); `cc_S01_model-fit_v01.mov` (fail: alpha: expected False, got True); `cc_S01_exceptions_v01.mov` (fail: alpha: expected False, got True).
- Rulings from Joel on P2: **0** at 9 Oct (review pending then). On 19 Oct he accepted the video with no changes; see Delivery and review above.

## Time per gate (measured by AEM, `aem report`)

| Gate | Wall | Agent busy | Idle | Waiting on client | Waiting on others | Paused | Attended, between turns | Unobserved |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| G2 | 11:43:58 | 2:39:12 | 8:49:05 | 0:00:00 | 0:00:00 | 0:00:00 | 0:32:03 | 0:00:01 |
| G4 | 5:33:57 | 5:11:14 | 0:17:58 | 0:00:00 | 0:00:00 | 0:00:00 | 0:04:45 | 0:00:00 |

Per-moment time: none attributable. Every stage so far was whole-video (`G2 · (whole video)`, `G4 · (whole video)`), so `aem report` leaves 7:07:00 unattributed and spreads nothing across moments. Observed session time outside any stage: 16:00:10 of 23:07:09 observed. Three stages were inferred by AEM from file changes (one G2, two G4).

## Moments

Latest render per moment; sync is the maximum word-to-cue offset in frames at 25 fps from the evidence run on that render.

| Moment | Words | Teaching job | Treatment | Latest render | Versions | Check | Flash flagged | Max sync | Approved |
|---|---|---|---|---|---:|---|---|---|---|
| cc_S00_cold-open | w0–w10 | Hook | nothing | - | - | - | - | - | - |
| cc_S00_real-projects | w11–w21 | Hook | footage | - | - | - | - | - | - |
| cc_S00_waste | w22–w29 | Hook | footage | - | - | - | - | - | - |
| cc_S00_promise | w30–w56 | Hook | footage | cc_S00_promise_v02.mov | 2 | fail | no | 3f | - |
| cc_S00_agenda | w57–w89 | Hook | animation | cc_S00_agenda_v03.mp4 | 3 | pass | no | 17f | - |
| cc_S00_anthropic-doc | w90–w101 | Evidence | screen recording | cc_S00_anthropic-doc_v01.mp4 | 1 | pass | no | 18f | - |
| cc_S01_docs-scroll | w115–w150 | Evidence | footage | cc_S01_docs-scroll_v04.mp4 | 2 | pass | yes | not measured | - |
| cc_S01_madness | w151–w157 | Verdict / joke | nothing | - | - | - | - | - | - |
| cc_S01_lofi-radio | w158–w173 | Evidence | footage | cc_S01_lofi-radio_v03.mp4 | 3 | pass | no | 11f | - |
| cc_S01_three-dials | w213–w232 | Cast of characters | animation | cc_S01_three-dials_v03.mp4 | 3 | pass | no | 9f | - |
| cc_S01_modes | w241–w261 | Procedure / UI demo | joel's terminal, re-typeset | cc_S01_modes_v04.mp4 | 4 | pass | no | 2f | - |
| cc_S01_plan-vs-accept | w282–w388 | Comparison | animation | cc_S01_plan-vs-accept_v03.mp4 | 2 | pass | yes | 31f | - |
| cc_S01_model | w397–w430 | Cast of characters | animation | cc_S01_model_v01.mp4 | 1 | pass | no | 11f | - |
| cc_S01_model-fit | w431–w470 | Verdict | footage | cc_S01_model-fit_v01.mov | 1 | fail | no | not measured | - |
| cc_S01_effort-levels | w471–w512 | Comparison / statistic | animation | cc_S01_effort-levels_v04.mp4 | 4 | pass | yes | 1f | - |
| cc_S01_benchmarks | w529–w590 | Comparison / statistic | screen recording | cc_S01_benchmarks_v01.mp4 | 1 | pass | no | 11f | - |
| cc_S01_exceptions | w598–w659 | Comparison | footage | cc_S01_exceptions_v01.mov | 1 | fail | no | not measured | - |
| cc_S02_goal | w660–w705 | Procedure / UI demo | joel's terminal, re-typeset | cc_S02_goal_v03.mp4 | 3 | pass | no | 27f | - |
| cc_S02_branch | w761–w785 | Procedure / UI demo | joel's terminal, re-typeset | cc_S02_branch_v03.mp4 | 3 | pass | no | 23f | - |
| cc_S02_branch-fork | w786–w857 | Mechanism | animation | cc_S02_branch-fork_v01.mp4 | 1 | pass | no | not measured | - |
| cc_S02_advisor | w858–w887 | Procedure / UI demo | joel's terminal, re-typeset | cc_S02_advisor_v04.mp4 | 2 | pass | no | 4f | - |
| cc_S02_advisor-diagram | w905–w949 | Mechanism | nothing | - | - | - | - | - | - |
| cc_S03_docs-quote | w970–w1003 | Evidence | screen recording | cc_S03_docs-quote_v01.mp4 | 1 | pass | no | 1f | - |
| cc_S03_window | w1023–w1071 | Cast of characters → mechanism | animation | cc_S03_window_v01.mp4 | 1 | pass | no | 49f | - |
| cc_S03_controls | w1072–w1106 | Evidence | footage | cc_S03_controls_v02.mp4 | 2 | pass | no | 2f | - |
| cc_S03_40-60 | w1107–w1133 | Comparison / statistic | animation | cc_S03_40-60_v01.mp4 | 1 | pass | no | 7f | - |
| cc_S03_clean-context | w1134–w1269 | Verdict / opinion | nothing | - | - | - | - | - | - |
| cc_S04_offload | w1311–w1393 | Comparison (mechanism) | animation | cc_S04_offload_v01.mp4 | 1 | pass | no | 25f | - |
| cc_S04_agent-file | w1407–w1450 | Code walkthrough | animation | cc_S04_agent-file_v02.mp4 | 2 | pass | no | 14f | - |
| cc_S04_fan-out | w1458–w1513 | Connect / vary together | animation | cc_S04_fan-out_v01.mp4 | 1 | pass | no | 16f | - |
| cc_S04_token-bill | w1514–w1551 | Verdict / opinion | nothing | - | - | - | - | - | - |
| cc_S05_not-that-memory | w1570–w1579 | Verdict / joke | animation | cc_S05_not-that-memory_v02.mp4 | 2 | pass | no | not measured | - |
| cc_S05_loaded-every-run | w1580–w1609 | Connect / vary together | animation | cc_S05_loaded-every-run_v01.mp4 | 1 | pass | no | 34f | - |
| cc_S05_init | w1610–w1628 | Procedure / UI demo | joel's terminal, re-typeset | cc_S05_init_v03.mp4 | 3 | pass | no | 12f | - |
| cc_S05_docs-guidance | w1644–w1731 | Evidence | animation | cc_S05_docs-guidance_v01.mp4 | 1 | pass | no | 11f | - |
| cc_S05_less-is-more | w1732–w1796 | Comparison / statistic | animation | cc_S05_less-is-more_v05.mp4 | 4 | pass | no | 34f | - |
| cc_S06_anthropic-doc | w1836–w1859 | Evidence | screen recording | cc_S06_anthropic-doc_v01.mp4 | 1 | pass | no | not measured | - |
| cc_S06_critical | w1860–w1980 | Comparison | animation | cc_S06_critical_v04.mp4 | 3 | pass | no | 12f | - |
| cc_S06_prototyping | w1981–w2066 | Comparison | animation | cc_S06_prototyping_v05.mp4 | 3 | pass | no | 26f | - |
| cc_S07_be-specific | w2087–w2148 | Evidence | screen recording | cc_S07_be-specific_v01.mp4 | 1 | pass | no | 2f | - |
| cc_S07_course-correct | w2149–w2175 | Procedure / UI demo | animation | cc_S07_course-correct_v03.mp4 | 3 | pass | yes | 28f | - |
| cc_S07_clean-session | w2176–w2191 | Evidence | screen recording | cc_S07_clean-session_v01.mp4 | 1 | pass | no | 8f | - |
| cc_S07_ask-questions | w2192–w2237 | Procedure / UI demo | animation | cc_S07_ask-questions_v01.mp4 | 1 | pass | no | 12f | - |
| cc_S08_skills-list | w2257–w2339 | Evidence | screen recording | cc_S08_skills-list_v03.mp4 | 3 | fail | yes | 70f | - |
| cc_S09_mcp | w2436–w2483 | Mechanism | animation | cc_S09_mcp_v04.mp4 | 4 | pass | no | 36f | - |
| cc_S09_mcp-servers | w2484–w2558 | Evidence | screen recording | cc_S09_mcp-servers_v03.mp4 | 2 | pass | no | 2f | - |
| cc_S10_outro | w2574–w2600 | Chapter / brand moment | nothing | - | - | - | - | - | - |

## Evidence summary

| Render | Check | Flash flagged | Max sync | Evidence seconds |
|---|---|---|---|---:|
| cc_S00_agenda_v01.mp4 | pass | no | 5f | 3.64 |
| cc_S00_agenda_v02.mp4 | pass | no | 2f | 3.38 |
| cc_S00_agenda_v03.mp4 | pass | no | 17f | 2.4 |
| cc_S00_anthropic-doc_v01.mp4 | pass | no | 18f | 1.12 |
| cc_S00_promise_v01.mov | fail | no | 3f | 5.07 |
| cc_S00_promise_v02.mov | fail | no | 3f | 5.07 |
| cc_S01_benchmarks_v01.mp4 | pass | no | 11f | 2.86 |
| cc_S01_docs-scroll_v01.mp4 | pass | yes | 5f | 20.92 |
| cc_S01_docs-scroll_v04.mp4 | pass | yes | not measured | 11.52 |
| cc_S01_effort-levels_v01.mp4 | pass | yes | 35f | 3.91 |
| cc_S01_effort-levels_v02.mp4 | pass | no | 6f | 3.69 |
| cc_S01_effort-levels_v03.mp4 | pass | no | 6f | 3.6 |
| cc_S01_effort-levels_v04.mp4 | pass | yes | 1f | 2.38 |
| cc_S01_exceptions_v01.mov | fail | no | not measured | 12.53 |
| cc_S01_lofi-radio_v01.mp4 | pass | no | 1f | 3.4 |
| cc_S01_lofi-radio_v02.mp4 | pass | no | 1f | 3.68 |
| cc_S01_lofi-radio_v03.mp4 | pass | no | 11f | 2.23 |
| cc_S01_model-fit_v01.mov | fail | no | not measured | 3.56 |
| cc_S01_model_v01.mp4 | pass | no | 11f | 1.74 |
| cc_S01_modes_v01.mp4 | pass | yes | 1f | 2.61 |
| cc_S01_modes_v02.mp4 | pass | yes | 1f | 2.68 |
| cc_S01_modes_v03.mp4 | pass | yes | 1f | 2.73 |
| cc_S01_modes_v04.mp4 | pass | no | 2f | 1.6 |
| cc_S01_plan-vs-accept_v01.mp4 | pass | yes | 31f | 4.52 |
| cc_S01_plan-vs-accept_v03.mp4 | pass | yes | 31f | 4.19 |
| cc_S01_three-dials_v01.mp4 | pass | no | 8f | 2.64 |
| cc_S01_three-dials_v02.mp4 | pass | no | 8f | 2.58 |
| cc_S01_three-dials_v03.mp4 | pass | no | 9f | 1.8 |
| cc_S02_advisor_v01.mp4 | pass | no | 31f | 4.42 |
| cc_S02_advisor_v04.mp4 | pass | no | 4f | 1.8 |
| cc_S02_branch-fork_v01.mp4 | pass | no | not measured | 1.14 |
| cc_S02_branch_v01.mp4 | pass | no | 23f | 3.11 |
| cc_S02_branch_v02.mp4 | pass | no | 23f | 3.83 |
| cc_S02_branch_v03.mp4 | pass | no | 23f | 1.73 |
| cc_S02_goal_v01.mp4 | pass | no | 9f | 2.5 |
| cc_S02_goal_v02.mp4 | pass | no | 9f | 2.86 |
| cc_S02_goal_v03.mp4 | pass | no | 27f | 1.67 |
| cc_S03_40-60_v01.mp4 | pass | no | 7f | 1.53 |
| cc_S03_controls_v01.mp4 | pass | no | 2f | 3.94 |
| cc_S03_controls_v02.mp4 | pass | no | 2f | 2.25 |
| cc_S03_docs-quote_v01.mp4 | pass | no | 1f | 2.76 |
| cc_S03_window_v01.mp4 | pass | no | 49f | 2.58 |
| cc_S04_agent-file_v01.mp4 | pass | no | 14f | 4.58 |
| cc_S04_agent-file_v02.mp4 | pass | no | 14f | 2.86 |
| cc_S04_fan-out_v01.mp4 | pass | no | 16f | 2.39 |
| cc_S04_offload_v01.mp4 | pass | no | 25f | 4.13 |
| cc_S05_docs-guidance_v01.mp4 | pass | no | 11f | 4.4 |
| cc_S05_init_v01.mp4 | pass | no | 1f | 2.28 |
| cc_S05_init_v02.mp4 | pass | no | 1f | 2.47 |
| cc_S05_init_v03.mp4 | pass | no | 12f | 1.3 |
| cc_S05_less-is-more_v01.mp4 | pass | no | 23f | 6.83 |
| cc_S05_less-is-more_v02.mp4 | pass | no | 31f | 6.13 |
| cc_S05_less-is-more_v03.mp4 | pass | no | not measured | 2.63 |
| cc_S05_less-is-more_v05.mp4 | pass | no | 34f | 3.78 |
| cc_S05_loaded-every-run_v01.mp4 | pass | no | 34f | 1.98 |
| cc_S05_not-that-memory_v01.mp4 | pass | no | not measured | 0.87 |
| cc_S05_not-that-memory_v02.mp4 | pass | no | not measured | 0.62 |
| cc_S06_anthropic-doc_v01.mp4 | pass | no | not measured | 1.78 |
| cc_S06_critical_v01.mp4 | pass | no | 4f | 11.95 |
| cc_S06_critical_v02.mp4 | pass | no | 4f | 9.78 |
| cc_S06_critical_v04.mp4 | pass | no | 12f | 5.21 |
| cc_S06_prototyping_v01.mp4 | pass | no | 8f | 6.96 |
| cc_S06_prototyping_v02.mp4 | pass | no | 4f | 5.91 |
| cc_S06_prototyping_v05.mp4 | pass | no | 26f | 4.2 |
| cc_S07_ask-questions_v01.mp4 | pass | no | 12f | 1.91 |
| cc_S07_be-specific_v01.mp4 | pass | no | 2f | 3.33 |
| cc_S07_clean-session_v01.mp4 | pass | no | 8f | 1.22 |
| cc_S07_course-correct_v01.mp4 | pass | no | 5f | 3.23 |
| cc_S07_course-correct_v02.mp4 | pass | no | 5f | 3.74 |
| cc_S07_course-correct_v03.mp4 | pass | yes | 28f | 1.59 |
| cc_S08_skills-list_v01.mp4 | pass | no | 0f | 11.46 |
| cc_S08_skills-list_v02.mp4 | pass | no | 0f | 10.71 |
| cc_S08_skills-list_v03.mp4 | fail | yes | 70f | 7.01 |
| cc_S09_mcp-servers_v01.mp4 | pass | no | 1f | 6.91 |
| cc_S09_mcp-servers_v03.mp4 | pass | no | 2f | 4.35 |
| cc_S09_mcp_v01.mp4 | pass | yes | 22f | 4.27 |
| cc_S09_mcp_v02.mp4 | pass | yes | not measured | 1.54 |
| cc_S09_mcp_v03.mp4 | pass | yes | 31f | 4.37 |
| cc_S09_mcp_v04.mp4 | pass | no | 36f | 2.79 |

Note: 44 render files are in the P2 `renders/` folder at snapshot time (8 of them ProRes 4444 alpha overlays, `.mov`, for the moments drawn over Joel's face: promise, exceptions, model-fit). The record of every check and evidence run (render SHA-256, result, flashes, sync note, seconds) is in `events.jsonl`.
