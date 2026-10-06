# P1 fixture: Frontend Design, as delivered

Copied from Joel Belton's P1 project and design system on 7 October 2026 (read only), so the moment,
review and calibration tests run on real moments and real rulings without the drive.

| File | From | Notes |
|---|---|---|
| `edit.json` | `P1 - Frontend Design/Animations using Hyperframes/MergeToMaster/data/edit.json` | 66 placements on the edit timeline: 58 of ours (`kind`), 8 of Joel's footage (`type`) |
| `PLACEMENTS.csv` | `…/renders/v08/PLACEMENTS.csv` | the asset of each placement, as listed before the last retimes (63 rows; it predates HF-026) |
| `renders-v08.txt` | the file names in `…/renders/v08/` | 59 masters: one per placement, plus `fd_title-average-question_alpha_v08.mov`, which no placement uses; tests make a stand-in file of each name |
| `words.json` | `…/data/narration-words.json` | whisper.cpp small.en token times, rewritten in the skill's `words.json` shape (`w0001`…); they drift by up to 0.19 s around 08:05 (P1 `OUTSTANDING.md`) |
| `frameio-notes.csv` | `…/FRAMEIO-COMMENTS-MAP.md` | Joel's 66 timestamped Frame.io notes on the rough cut (numbered 1–70; 28, 58, 59, 66 never existed), his words verbatim. #52, #63 and #70 had no text in the Frame.io export, so their text is empty here. `Timecode Out` is set only for #20, whose note runs "through 00:02:19:12". At 24000/1001. |
| `labelled-cases.jsonl` | design system `critic/labelled-cases.jsonl` | the three change rulings after delivery (14 September 2026) |
| `rules.md`, `joel-decisions.md` | design system | as of 7 October 2026 |

The renders themselves are not copied: tests that need real frames (evidence) read them from the drive
and are skipped when it is not mounted.
