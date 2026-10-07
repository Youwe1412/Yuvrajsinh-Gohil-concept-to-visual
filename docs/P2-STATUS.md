# P2 status · Claude Code video · MergeToMaster

Status as of 7 Oct 2026, 23:50 IST. Generated from `aem moments` (`moments/index.json`), `aem report` (`reports/time.md`) and `events.jsonl` in the P2 project folder by `docs/tools/p2status.py`. Joel's Frame.io review is pending; this page is updated after it.

## Counts (measured by AEM unless marked)

- Named moments in the plan: **42** (`aem moments` lists 64 rows; the other 22 are table headings and scene labels it read from `visual-plan.md` and `shotlist.md`, a parsing defect noted in CASE-STUDY §g).
- Treatments: animation 15, footage 12, nothing 11, screen recording 4.
- Direction: none (0 notes from Joel); asked 0, added 64 (every moment is ours to decide).
- Moments with at least one render checked: **20**; render versions checked: **38**; check failures: **0**.
- Evidence runs (`aem evidence`): **38** renders.
- Render versions where `check-render` flagged one- or two-frame luma flashes (area 0.02–0.04 % of frame): **8**; the evidence notes record no flash for any render.
- Standing approvals: **1** (cc_S00_agenda_v02.mp4 · delivery confirmation).
- Rulings from Joel on P2: **0** (review pending).

## Time per gate (measured by AEM, `aem report`)

| Gate | Wall | Agent busy | Idle | Waiting on client | Waiting on others | Paused | Attended, between turns | Unobserved |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| G2 | 1:48:17 | 1:12:47 | 0:25:27 | 0:00:00 | 0:00:00 | 0:00:00 | 0:10:02 | 0:00:01 |
| G4 | 5:18:43 | 4:57:40 | 0:17:58 | 0:00:00 | 0:00:00 | 0:00:00 | 0:03:05 | 0:00:00 |

Per-moment time: none attributable. Every stage so far was whole-video (`G2 · (whole video)`, `G4 · (whole video)`), so `aem report` leaves 7:07:00 unattributed and spreads nothing across moments. Observed session time outside any stage: 16:00:10 of 23:07:09 observed. Three stages were inferred by AEM from file changes (one G2, two G4).

## Moments

Latest render per moment; sync is the maximum word-to-cue offset in frames at 25 fps from the evidence run on that render.

| Moment | Words | Teaching job | Treatment | Latest render | Versions | Check | Flash flagged | Max sync | Approved |
|---|---|---|---|---|---:|---|---|---|---|
| cc_S00_cold-open | w0–w10 | Hook | nothing | - | - | - | - | - | - |
| cc_S00_real-projects | w11–w29 | Hook | footage | - | - | - | - | - | - |
| cc_S00_agenda | w57–w89 | Hook | animation | cc_S00_agenda_v02.mp4 | 2 | pass | no | 2f | yes |
| cc_S00_anthropic-doc | w90–w101 | Evidence | screen recording | - | - | - | - | - | - |
| cc_S01_docs-scroll | w115–w150 | Evidence | footage | cc_S01_docs-scroll_v01.mp4 | 1 | pass | yes | 5f | - |
| cc_S01_madness | w151–w157 | Verdict / joke | nothing | - | - | - | - | - | - |
| cc_S01_lofi-radio | w158–w173 | Evidence | footage | cc_S01_lofi-radio_v02.mp4 | 2 | pass | no | 1f | - |
| cc_S01_three-dials | w213–w232 | Cast of characters | animation | cc_S01_three-dials_v02.mp4 | 2 | pass | no | 8f | - |
| cc_S01_modes | w241–w261 | Procedure / UI demo | footage | cc_S01_modes_v03.mp4 | 3 | pass | yes | 1f | - |
| cc_S01_plan-vs-auto | w262–w396 | Comparison | nothing | - | - | - | - | - | - |
| cc_S01_model | w397–w470 | Verdict / opinion | nothing | - | - | - | - | - | - |
| cc_S01_effort-levels | w471–w512 | Comparison / statistic | animation | cc_S01_effort-levels_v03.mp4 | 3 | pass | no | 6f | - |
| cc_S01_benchmarks | w529–w659 | Comparison / statistic | nothing | - | - | - | - | - | - |
| cc_S02_goal | w660–w705 | Procedure / UI demo | footage | cc_S02_goal_v02.mp4 | 2 | pass | no | 9f | - |
| cc_S02_branch | w761–w785 | Procedure / UI demo | footage | cc_S02_branch_v02.mp4 | 2 | pass | no | 23f | - |
| cc_S02_advisor | w858–w887 | Procedure / UI demo | footage | cc_S02_advisor_v01.mp4 | 1 | pass | no | 31f | - |
| cc_S02_advisor-diagram | w905–w949 | Mechanism | nothing | - | - | - | - | - | - |
| cc_S03_docs-quote | w970–w1003 | Evidence | screen recording | - | - | - | - | - | - |
| cc_S03_window | w1023–w1071 | Cast of characters → mechanism | animation | - | - | - | - | - | - |
| cc_S03_controls | w1072–w1106 | Evidence | footage | cc_S03_controls_v01.mp4 | 1 | pass | no | 2f | - |
| cc_S03_40-60 | w1107–w1133 | Comparison / statistic | animation | - | - | - | - | - | - |
| cc_S03_clean-context | w1134–w1269 | Verdict / opinion | nothing | - | - | - | - | - | - |
| cc_S04_offload | w1311–w1393 | Comparison (mechanism) | animation | - | - | - | - | - | - |
| cc_S04_agent-file | w1407–w1450 | Code walkthrough | animation | cc_S04_agent-file_v01.mp4 | 1 | pass | no | 14f | - |
| cc_S04_fan-out | w1458–w1513 | Connect / vary together | animation | - | - | - | - | - | - |
| cc_S04_token-bill | w1514–w1551 | Verdict / opinion | nothing | - | - | - | - | - | - |
| cc_S05_not-that-memory | w1570–w1579 | Verdict / joke | animation | cc_S05_not-that-memory_v01.mp4 | 1 | pass | no | not measured | - |
| cc_S05_loaded-every-run | w1580–w1609 | Connect / vary together | animation | - | - | - | - | - | - |
| cc_S05_init | w1610–w1628 | Procedure / UI demo | footage | cc_S05_init_v02.mp4 | 2 | pass | no | 1f | - |
| cc_S05_docs-guidance | w1644–w1731 | Evidence | animation | - | - | - | - | - | - |
| cc_S05_less-is-more | w1732–w1796 | Comparison / statistic | animation | cc_S05_less-is-more_v03.mp4 | 3 | pass | no | not measured | - |
| cc_S06_anthropic-doc | w1836–w1859 | Evidence | screen recording | - | - | - | - | - | - |
| cc_S06_critical | w1860–w1980 | Comparison | animation | cc_S06_critical_v02.mp4 | 2 | pass | no | 4f | - |
| cc_S06_prototyping | w1981–w2066 | Comparison | animation | cc_S06_prototyping_v02.mp4 | 2 | pass | no | 4f | - |
| cc_S07_be-specific | w2067–w2148 | Verdict / opinion | nothing | - | - | - | - | - | - |
| cc_S07_course-correct | w2149–w2175 | Procedure / UI demo | footage | cc_S07_course-correct_v02.mp4 | 2 | pass | no | 5f | - |
| cc_S07_clean-session | w2176–w2191 | Evidence | screen recording | - | - | - | - | - | - |
| cc_S07_ask-questions | w2192–w2237 | Verdict / opinion | nothing | - | - | - | - | - | - |
| cc_S08_skills-list | w2257–w2320 | Evidence | footage | cc_S08_skills-list_v02.mp4 | 2 | pass | no | 0f | - |
| cc_S09_mcp | w2436–w2483 | Mechanism | animation | cc_S09_mcp_v03.mp4 | 3 | pass | yes | 31f | - |
| cc_S09_mcp-servers | w2484–w2558 | Evidence | footage | cc_S09_mcp-servers_v01.mp4 | 1 | pass | no | 1f | - |
| cc_S10_outro | w2574–w2600 | Chapter / brand moment | nothing | - | - | - | - | - | - |

## Evidence summary

| Render | Check | Flash flagged | Max sync | Evidence seconds |
|---|---|---|---|---:|
| cc_S00_agenda_v01.mp4 | pass | no | 5f | 3.64 |
| cc_S00_agenda_v02.mp4 | pass | no | 2f | 3.38 |
| cc_S01_docs-scroll_v01.mp4 | pass | yes | 5f | 20.92 |
| cc_S01_effort-levels_v01.mp4 | pass | yes | 35f | 3.91 |
| cc_S01_effort-levels_v02.mp4 | pass | no | 6f | 3.69 |
| cc_S01_effort-levels_v03.mp4 | pass | no | 6f | 3.6 |
| cc_S01_lofi-radio_v01.mp4 | pass | no | 1f | 3.4 |
| cc_S01_lofi-radio_v02.mp4 | pass | no | 1f | 3.68 |
| cc_S01_modes_v01.mp4 | pass | yes | 1f | 2.61 |
| cc_S01_modes_v02.mp4 | pass | yes | 1f | 2.68 |
| cc_S01_modes_v03.mp4 | pass | yes | 1f | 2.73 |
| cc_S01_three-dials_v01.mp4 | pass | no | 8f | 2.64 |
| cc_S01_three-dials_v02.mp4 | pass | no | 8f | 2.58 |
| cc_S02_advisor_v01.mp4 | pass | no | 31f | 4.42 |
| cc_S02_branch_v01.mp4 | pass | no | 23f | 3.11 |
| cc_S02_branch_v02.mp4 | pass | no | 23f | 3.83 |
| cc_S02_goal_v01.mp4 | pass | no | 9f | 2.5 |
| cc_S02_goal_v02.mp4 | pass | no | 9f | 2.86 |
| cc_S03_controls_v01.mp4 | pass | no | 2f | 3.94 |
| cc_S04_agent-file_v01.mp4 | pass | no | 14f | 4.58 |
| cc_S05_init_v01.mp4 | pass | no | 1f | 2.28 |
| cc_S05_init_v02.mp4 | pass | no | 1f | 2.47 |
| cc_S05_less-is-more_v01.mp4 | pass | no | 23f | 6.83 |
| cc_S05_less-is-more_v02.mp4 | pass | no | 31f | 6.13 |
| cc_S05_less-is-more_v03.mp4 | pass | no | not measured | 2.63 |
| cc_S05_not-that-memory_v01.mp4 | pass | no | not measured | 0.87 |
| cc_S06_critical_v01.mp4 | pass | no | 4f | 11.95 |
| cc_S06_critical_v02.mp4 | pass | no | 4f | 9.78 |
| cc_S06_prototyping_v01.mp4 | pass | no | 8f | 6.96 |
| cc_S06_prototyping_v02.mp4 | pass | no | 4f | 5.91 |
| cc_S07_course-correct_v01.mp4 | pass | no | 5f | 3.23 |
| cc_S07_course-correct_v02.mp4 | pass | no | 5f | 3.74 |
| cc_S08_skills-list_v01.mp4 | pass | no | 0f | 11.46 |
| cc_S08_skills-list_v02.mp4 | pass | no | 0f | 10.71 |
| cc_S09_mcp-servers_v01.mp4 | pass | no | 1f | 6.91 |
| cc_S09_mcp_v01.mp4 | pass | yes | 22f | 4.27 |
| cc_S09_mcp_v02.mp4 | pass | yes | not measured | 1.54 |
| cc_S09_mcp_v03.mp4 | pass | yes | 31f | 4.37 |

Note: at snapshot time the P2 `renders/` folder and the per-version `reviews/<moment>/vNN/` evidence folders are not on disk; the record of each check and evidence run (render SHA-256, result, flashes, sync note, seconds) is in `events.jsonl`, and the HyperFrames `check` results in `reviews/checks/<moment>.json` (30 files, 29 ok, `cc_S04_agent-file` not ok).
