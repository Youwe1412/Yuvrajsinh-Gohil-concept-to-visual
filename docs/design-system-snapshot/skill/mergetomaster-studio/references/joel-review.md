# G7 · Joel's review: learning from every delivery

The critic is only as good as the cases it is checked against (M-19), and Joel's taste is only in the
system where it has been written down (`joel-decisions.md`). Every delivery is a chance to grow both.
P1 left three defect rulings and no reasons; this gate exists so the next video leaves more.

**How Joel reviews.** He reviews the finished video, never individual animations or the process. His
approval, feedback and timestamped instructions come on Frame.io; some feedback comes on WhatsApp.
How much he directs a video varies, and that is data: P1 had 66 timestamped notes; for P2 he gave
none, by choice ("I really liked what you did with the other video so id like to try you mostly just
adding in visuals that you feel like are appropriate at the time rather than me commenting what
should go where", WhatsApp, 5 October 2026). The absence of notes is his decision, recorded as a
channel-level ruling, not a gap to fill. Never ask him to rule on individual animations unless he
offers.

## 1. Wait for Frame.io, then import his comments

- After delivery, wait for his review on Frame.io. Don't chase notes he has chosen not to give.
- Ask Yuvraj for the Frame.io comments as a CSV export of the review link Joel commented on.
- Read the header row and map the real columns (timecode, commenter, comment, replies, completed);
  don't assume names. Keep the CSV unchanged in `reviews/joel/<date>-frameio.csv`.
  `aem import-review <csv>` does the conversion below and the mapping, and drafts each comment for
  Yuvraj's review inbox.
- **Timecode to frames.** Frame.io timecodes are `HH:MM:SS:FF` at the reviewed file's rate. Counted
  frames use the *nominal* rate (24 for P1's 24000/1001, 25 for P2's 25/1):
  `frame = ((HH×3600 + MM×60 + SS) × nominal) + FF`, then
  `seconds = frame × fps_den / fps_num`. Use the delivered edit's `fps_num`/`fps_den`, not the
  current project's if it has changed, and subtract the timeline start if the reviewed file doesn't
  start at 00:00:00:00. Confirm the conversion on one comment by checking that its frame shows
  what the comment describes.
- **Map each comment to a moment and word IDs:** the moment (shot) whose word span, from
  `data/words.json`, lies within a second of the comment's frame; that is an explicit ruling
  candidate on it. A comment outside every moment is a video-level remark: keep it as one, and log
  an edit note for the Edit System.
- **Other channels.** Feedback that arrives on WhatsApp or by email is attached by Yuvraj with
  `client-said --about <moment|video|channel> --source "WhatsApp, <date>"`, his words verbatim. A
  remark about the editor or how to work for the channel ("do whatever you think is appropriate")
  is channel-level.

## 2. A ruling for every delivered shot, at the level it was given

Make `reviews/joel/<date>-rulings.md`: one row per delivered shot.

| Shot | Word IDs | Render SHA-256 | Ruling (keep / change / remove / accepted) | Level | Joel's words | Source |
|---|---|---|---|---|---|---|

- **Explicit:** a comment on the shot. One that asks for a change is **change** or **remove**;
  praise of a shot is **keep**.
- **Implicit:** the video accepted with no comment on the shot. While the video is under review,
  silence is not a ruling: leave those shots `pending`. Once Joel accepts the whole video, Yuvraj
  runs `accept-video <version> --source "Frame.io, <date>"`, which writes **accepted**, level
  implicit, with the delivered render's SHA-256, for every shot without an explicit comment. An
  implicit acceptance is weaker than an explicit ruling and is never written as one.
- **Video or channel:** a remark about the video as a whole, or about the editor or the channel.
- Don't ask Joel to mark shots he didn't comment on. If he offers rulings, record them.

## 3. Record Joel in his own words

Add a dated entry to `joel-decisions.md` in the design-system folder, following that file's rules:
his exact words quoted, the scope (channel, video or instance), his reasons if he gave them, and our
reading labelled as ours. Never paraphrase into his voice. If he gave no reason, add the question to
"Open questions for Joel". A ruling that changes a channel rule then follows README "Changing the
system"; this gate does not change `rules.md` by itself.

## 4. Append the labelled cases

Append one line per ruled shot to `critic/labelled-cases.jsonl` in the design-system folder (channel
level, shared across videos). Fields are listed in the file's header line: video, shot, word IDs,
render SHA-256, frames or crops, Joel's ruling, his exact words, the rule IDs involved, the critic's
verdict at G5 and whether it agreed. AEM adds the moment, the level, whether the shot was asked for
or added, the video's direction (full notes, partial, none), the version and the critic's findings.
Status `labelled` needs his explicit ruling, verbatim words and the render's SHA-256; anything
missing, and every implicit acceptance, is a `development case`. Never edit a past line; append a
correcting one.

## 5. Report the critic's agreement

`aem calibrate joel` reports it, for this delivery and for the whole file: acceptance per video (asked
against added shots, by treatment and teaching job), how often the G5 critic agreed with Joel (hits,
misses, false alarms; explicit rulings weigh more than implicit acceptances), and per rule ID how many
rulings involve it, confirm it or overrule it. Under M-19 the critic advises and does not gate until
about 30 labelled cases agree with it; below 30 explicit cases every figure is development data, not
evidence. A rule status it proposes changes only through README "Changing the system", after an entry
in `joel-decisions.md`. Where the critic misses, sharpen the rubric, not the threshold.

Finish with the time report (`references/project-ledgers.md`).
