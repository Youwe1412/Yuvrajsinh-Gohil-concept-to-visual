"""Phase 1 (1.1.0): the moment is the unit of work.

On P1's real files (tests/fixtures/p1): 58 placements of ours become moments; Joel's 66 timestamped notes
decide which were asked (a note within a second of the moment's word span) and which we added.

What the real data says, measured here rather than assumed: by note coverage P1 has 50 asked moments and 8
added, not 45 and 13. The three scenes Joel changed after delivery were asked (notes #42, #48 and #49 sit on
them: "50ms shown on screen in big text", "different button states", "Boxes layering up ontop of eachother ...
with the word character below it"); what he removed were elements we added inside them (the one-frame website
flash, two demonstration captions). joel-decisions.md's "All three shots were additions he had not asked for"
reads them at the level of those elements, not the shots.
"""
import json
import unittest

from helpers import JoelWorld, P1World, WorldCase

ADDED_P1 = ["fd_title-t08_okay", "fd_S02_tells-b", "fd_S05_board-a", "fd_S05_audience-questions", "fd_teach-gaps",
            "fd_S05_parallel-1", "fd_S05_board-e", "fd_S05_parallel-3"]
FIXED_P1 = {"fd_S04_50ms": "42", "fd_S04_button-states": "48", "fd_S04_character": "49"}


class P1Moments(unittest.TestCase):
    def setUp(self):
        self.w = P1World()

    def tearDown(self):
        self.w.cleanup()

    def moments(self):
        code, d = self.w.run("moments", operator=False)
        self.assertEqual(code, 0, d)
        return d, {m["id"]: m for m in d["moments"]}

    def test_58_placements_become_moments_and_footage_does_not(self):
        d, by = self.moments()
        self.assertEqual(d["moments_count"], 58)
        self.assertEqual(len(by), 58)  # every moment has its own ID, the five board-bf states included
        self.assertTrue({"fd_S05_board-b", "fd_S05_board-c", "fd_S05_board-d", "fd_S05_board-e", "fd_S05_board-f"} <= set(by))
        self.assertNotIn("ai-cartoon.webp", {m["name"] for m in by.values()})  # Joel's footage is not ours
        self.assertEqual(sorted({m["treatment"] for m in by.values()}), ["animation"])
        self.assertTrue((self.w.project / "moments" / "index.json").exists())

    def test_with_no_notes_every_moment_is_added_and_the_index_says_so(self):
        d, by = self.moments()
        self.assertEqual((d["notes"], d["asked"], d["added"], d["direction"]), (0, 0, 58, "none"))
        self.assertIn("every moment is added", d["note"])
        text = self.w.run_raw("moments", operator=False).stdout
        self.assertIn("No timestamped notes for this video: every moment is added", text.splitlines()[1])

    def test_joels_66_notes_decide_asked_or_added_by_coverage(self):
        _, r = self.w.import_notes()
        self.assertEqual((r["notes"], r["unreadable"]), (66, 0))
        d, by = self.moments()
        self.assertEqual((d["notes"], d["asked"], d["added"], d["direction"]), (66, 50, 8, "full notes"))
        self.assertEqual([m["id"] for m in d["moments"] if not m["asked"]], ADDED_P1)
        # Notes that sit on no moment of ours are about the video or the edit (footage, Final Cut captions).
        self.assertEqual([n["number"] for n in d["video_notes"]], ["4", "8", "23", "29", "32", "33", "62", "69", "70"])

    def test_the_three_client_fixed_scenes_carry_explicit_rulings_and_were_asked(self):
        self.w.import_notes()
        d, by = self.moments()
        ruled = {k: m for k, m in by.items() if m["ruling"]}
        self.assertEqual(sorted(ruled), sorted(FIXED_P1))
        for mid, note in FIXED_P1.items():
            m = by[mid]
            self.assertEqual((m["ruling"]["level"], m["ruling"]["ruling"]), ("explicit", "change"), mid)
            self.assertTrue(m["asked"], mid)
            self.assertIn(note, [n["number"] for n in m["notes"]], mid)
        self.assertEqual(by["fd_S04_50ms"]["ruling"]["rule_ids"], ["M-26"])
        self.assertEqual(by["fd_S04_50ms"]["name"], "stat-50ms")

    def test_p1_scene_20_resolves_to_comment_20s_word_span(self):
        self.w.import_notes()
        d, by = self.moments()
        words = json.loads((self.w.project / "data" / "words.json").read_text())["words"]
        note = json.loads(next((self.w.project / "reviews" / "joel").glob("*-notes.json")).read_text())
        n20 = next(c for c in note["comments"] if c["number"] == "20")
        self.assertEqual((n20["timecode"], n20["timecode_out"]), ("00:02:06:02", "00:02:19:12"))
        span = {w["id"] for w in words if w["start"] < n20["end_seconds"] and w["end"] > n20["seconds"]}
        # Scene #20 (next-token) lies inside the note's span; statistical-middle, the second half Joel's note asked
        # for ("through 00:02:19:12"), starts inside it and runs past its end.
        nt, sm = by["fd_S01_next-token"], by["fd_S01_statistical-middle"]
        self.assertEqual([n["number"] for n in nt["notes"]], ["20"])
        self.assertTrue(nt["word_ids"] and set(nt["word_ids"]) <= span)
        self.assertEqual(nt["word_span"], [127.45, 133.05])
        self.assertEqual([n["number"] for n in sm["notes"]], ["20"])
        self.assertTrue(set(sm["word_ids"]) & span and not set(sm["word_ids"]) <= span)

    def test_what_could_not_be_linked_is_reported(self):
        d, _ = self.moments()
        self.assertEqual(d["unlinked"], ["render renders/v08/fd_title-average-question_alpha_v08.mov belongs to no moment"])
        self.assertIn("Could not link (1):", self.w.run_raw("moments", operator=False).stdout)

    def test_status_line_counts_moments_approved_and_ruled(self):
        self.moments()
        _, st = self.w.run("status", operator=False)
        self.assertTrue(st["statusline"].endswith("· 58 moments · 0 approved · 3 ruled"), st["statusline"])
        self.w.run("approve", "fd_S01_next-token", "renders/v08/fd_S01_next-token_v08.mp4", "--gate", "G4", check=True)
        _, st = self.w.run("status", operator=False)
        self.assertEqual(st["statusline_parts"]["moments"], {"moments": 58, "approved": 1, "ruled": 3})


class MomentTime(unittest.TestCase):
    """Time attaches to a moment only where a stage names it; whole-video stages stay unattributed."""

    def setUp(self):
        self.w = P1World()
        self.w.run("moments", check=True)

    def tearDown(self):
        self.w.cleanup()

    def at(self, *args, t):
        return self.w.run("stage", *args, "--at", f"2026-10-06T{t}:00+05:30", check=True)

    def test_per_moment_and_per_stage_sections(self):
        self.at("auto", "session_start", "--session", "s1", t="10:00")
        self.at("start", "G2", t="10:00")                       # whole video: unattributed
        self.at("start", "G4", "fd_S01_next-token", t="10:30")  # names a moment
        self.at("end", "G4", "fd_S01_next-token", t="11:00")
        self.at("start", "G6", "fd_S04_50ms", t="11:00")
        self.at("end", "G6", "fd_S04_50ms", t="11:10")
        self.at("end", "G2", t="11:30")
        self.at("auto", "session_end", t="11:30")
        _, r = self.w.run("report", env={"AEM_FIXED_NOW": "2026-10-06T12:00:00+05:30"}, check=True)
        self.assertEqual(r["per_moment"]["fd_S01_next-token"]["wall_s"], 1800)
        self.assertEqual(r["per_moment"]["fd_S04_50ms"]["wall_s"], 600)
        self.assertEqual(r["unattributed"]["wall_s"], 5400)  # never spread over the 58 moments
        self.assertEqual(r["moments_without_stages"], 56)
        groups = r["per_stage_group"]
        self.assertEqual(list(groups), ["design (G1, G2, G3)", "build (G4)", "placement (G6)"])
        self.assertEqual((groups["design (G1, G2, G3)"]["wall_s"], groups["build (G4)"]["wall_s"],
                          groups["placement (G6)"]["wall_s"]), (5400, 1800, 600))
        md = (self.w.project / "reports" / "time.md").read_text()
        self.assertIn("## Per stage (design, build, review, placement)", md)
        self.assertIn("## Per moment", md)
        self.assertIn("| fd_S01_next-token | 0:30:00 |", md)
        self.assertIn("never spread across moments", md)
        _, d = self.w.run("moments", operator=False)
        m = next(x for x in d["moments"] if x["id"] == "fd_S04_50ms")
        self.assertEqual(m["time"], {"wall_s": 600.0, "by_gate": {"G6": 600.0}})


SHOTLIST = """# Shot list

| Shot | Word IDs | Teaching job | Knows before | Knows after | Must stay true | Where the picture stops being accurate | Rule IDs |
|---|---|---|---|---|---|---|---|
| fd_S01_park-map | w0002–w0004 | show | parks exist | which park | real park names | the map is not to scale | M-03, B-T1-03 |
| fd_S01_grade | w0006 | notice | - | grade kept | his grade | - | J-08 |
"""

PLAN = """# Visual plan

| Moment | Treatment | Why | Asked or added |
|---|---|---|---|
| fd_S01_park-map | animation | the viewer needs the route | added |
| fd_S01_grade | nothing | Joel asked to keep his grade | asked |
| fd_S01_dog | his footage | a real dog beats a drawing | added |
"""


class PlanMoments(unittest.TestCase):
    """P2's way: moments from visual-plan.md and shotlist.md; Joel's P2 has no notes, by his decision."""

    def setUp(self):
        self.w = JoelWorld()
        words = {"fps_num": 25, "fps_den": 1, "words": [
            {"id": f"w{i:04d}", "word": t, "start": i * 0.5, "end": i * 0.5 + 0.4}
            for i, t in enumerate(["so", "here", "are", "parks", "and", "the", "grade"], 1)]}
        (self.w.project / "data").mkdir(exist_ok=True)
        (self.w.project / "data" / "words.json").write_text(json.dumps(words))
        (self.w.project / "shotlist.md").write_text(SHOTLIST)
        (self.w.project / "visual-plan.md").write_text(PLAN)
        (self.w.project / "renders" / "fd_S01_park-map_v02.mp4").write_bytes(b"x")

    def tearDown(self):
        self.w.cleanup()

    def test_rows_become_moments_with_their_contract(self):
        code, d = self.w.run("moments", operator=False)
        self.assertEqual(code, 0, d)
        by = {m["id"]: m for m in d["moments"]}
        self.assertEqual(sorted(by), ["fd_S01_dog", "fd_S01_grade", "fd_S01_park-map"])
        m = by["fd_S01_park-map"]
        self.assertEqual(m["word_ids"], ["w0002", "w0003", "w0004"])  # a range, expanded through the word map
        self.assertEqual(m["words"], "here are parks")
        self.assertEqual(m["contract"], {"knows_before": "parks exist", "knows_after": "which park",
                                         "must_stay_true": "real park names", "accuracy_limit": "the map is not to scale"})
        self.assertEqual((m["job"], m["rule_ids"], m["treatment"]), ("show", ["M-03", "B-T1-03"], "animation"))
        self.assertEqual(m["renders"], [{"version": "v02", "path": "renders/fd_S01_park-map_v02.mp4"}])
        self.assertEqual((by["fd_S01_grade"]["treatment"], by["fd_S01_dog"]["treatment"]), ("nothing", "footage"))
        # The plan's own column wins over coverage; P2's direction is Joel's decision, recorded in the profile.
        self.assertEqual((by["fd_S01_grade"]["asked"], by["fd_S01_grade"]["asked_from"]), (True, "the plan"))
        self.assertEqual((d["direction"], d["direction_from"]), ("none", "the review profile in the registry"))

    def test_other_tables_and_struck_rows_are_not_moments(self):
        """P2's visual-plan.md (23 Oct 2026): a totals table, the shots to ask Joel for and a pacing audit sit beside
        the moment tables, and a retired moment is struck through. Only rows of tables whose header names a moment
        field (words, cues, job, treatment, the contract) are moments, and never a struck one."""
        (self.w.project / "visual-plan.md").write_text(
            "# Visual plan\n\n| Treatment | Moments |\n|---|---|\n| Animation | 23 |\n| Nothing | 6 |\n\n"
            + PLAN.split("\n", 2)[2].replace("| fd_S01_dog |", "| ~~`fd_S01_dog`~~ |")
            + "\n## Shots to ask Joel to film\n\n| Was | Found in his footage | Now | Still needed |\n|---|---|---|---|\n"
              "| S1 real project | no | built | his B-roll |\n\n"
              "## Pacing audit\n\n| Stretch | Length |\n|---|---|\n| 2:26.96–2:45.68 (19 s) | 19 s |\n")
        _, d = self.w.run("moments", operator=False)
        self.assertEqual(sorted(m["id"] for m in d["moments"]), ["fd_S01_grade", "fd_S01_park-map"])

    def test_without_the_asked_column_and_no_notes_every_moment_is_added(self):
        (self.w.project / "visual-plan.md").write_text(PLAN.replace(" Asked or added |", "").replace("|---|---|---|---|", "|---|---|---|")
                                                      .replace(" | added |", " |").replace(" | asked |", " |"))
        _, d = self.w.run("moments", operator=False)
        self.assertEqual((d["asked"], d["added"]), (0, 3))
        self.assertTrue(all(m["asked_from"] == "no notes" for m in d["moments"]))


class NoMoments(WorldCase):
    def test_a_project_with_no_plan_or_placements_has_none_and_the_status_line_says_nothing(self):
        self.w.use()
        code, d = self.w.run("moments", operator=False)
        self.assertEqual((code, d["moments_count"]), (0, 0))
        _, st = self.w.run("status", operator=False)
        self.assertNotIn("moments", st["statusline"])


if __name__ == "__main__":
    unittest.main()
