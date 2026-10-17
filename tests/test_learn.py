"""Phase 3 (1.1.0): a loop that learns from how the client actually reviews.

P1 (tests/fixtures/p1) is the real case. Joel left 66 timestamped Frame.io notes on the rough cut, asked for three
changes after delivery (14 September 2026) and said nothing about the other 55 moments before the film went live.
For P2 he gave no notes, by choice, on WhatsApp (5 October 2026): a channel-level ruling in his words.

What the client's notes land on is checked two ways: against the moment each note is on by the coverage rule (within
a second of the moment's words), and against what P1's own FRAMEIO-COMMENTS-MAP.md says answered it.
"""
import hashlib
import json
import unittest

from helpers import P1_FIXTURE, P1World

QUOTE = ("I really liked what you did with the other video so id like to try you mostly just adding in visuals that "
         "you feel like are appropriate at the time rather than me commenting what should go where")

# The moment each of Joel's 66 notes is on (the one it overlaps most, or is closest to, within a second of its words;
# #20 runs to 00:02:19:12). None: on no moment of ours (his own footage and stills, captions and edits in Final Cut),
# so it is a remark about the video.
ON = {
    "1": "fd_teach-opening", "2": "fd_teach-opening", "3": "fd_teach-opening", "4": None,
    "5": "fd_S00_cartoon-rings", "6": "fd_reference-wag", "7": "fd_title-t01_mission", "8": None,
    "9": "fd_title-t02_forever", "10": "fd_title-t02_forever", "11": "fd_S00_comedy-title", "12": "fd_teach-promise",
    "13": "fd_title-t03_name", "14": "fd_title-t03_name", "15": "fd_title-t04_bad", "16": "fd_reference-nova",
    "17": "fd_S01_scorecard-92", "18": "fd_S01_scorecard-92", "19": "fd_teach-recognition", "20": "fd_S01_next-token",
    "21": "fd_S01_100-runs", "22": "fd_title-t05_average", "23": None, "24": "fd_S01_fingerprint",
    "25": "fd_title-t07_damn", "26": "fd_title-t09_oh", "27": "fd_S02_tells-a", "29": None,
    "30": "fd_S02_wathan-post", "31": "fd_S02_training-loop", "32": None, "33": None,
    "34": "fd_S03_convergence", "35": "fd_S03_convergence", "36": "fd_S03_convergence", "37": "fd_teach-decisions",
    "38": "fd_teach-accepted", "39": "fd_S03_pro-vs-nonpro", "40": "fd_title-t10_fix", "41": "fd_S04_claude-bin",
    "42": "fd_S04_50ms", "43": "fd_S04_trust", "44": "fd_S04_trust", "45": "fd_S04_stripe-space",
    "46": "fd_S04_stripe-space", "47": "fd_teach-type", "48": "fd_S04_button-states", "49": "fd_S04_character",
    "50": "fd_title-t11_bigq", "51": "fd_S05_board-b", "52": "fd_S05_specific-generic", "53": "fd_S05_board-c",
    "54": "fd_teach-template", "55": "fd_teach-v0", "56": "fd_S05_board-d", "57": "fd_S05_exclusions",
    "60": "fd_S05_parallel-2", "61": "fd_S05_board-f", "62": None, "63": "fd_teach-refine", "64": "fd_S05_stat-70",
    "65": "fd_S05_board-g", "67": "fd_S05_before-after", "68": "fd_S05_before-after", "69": None, "70": None,
}

# What answered each note with a HyperFrames build, from P1's FRAMEIO-COMMENTS-MAP.md (master table, "Animation").
# Notes answered by footage, a Final Cut caption or edit, or deliberately left blank are not listed.
ANSWERED_BY = {
    "4": ["fd_S00_cartoon-rings"], "5": ["fd_S00_cartoon-rings"], "7": ["fd_title-t01_mission"],
    "9": ["fd_title-t02_forever"], "11": ["fd_S00_comedy-title"], "13": ["fd_title-t03_name"],
    "15": ["fd_title-t04_bad"], "17": ["fd_S01_scorecard-92"], "18": ["fd_S01_scorecard-92"],
    "20": ["fd_S01_next-token", "fd_S01_statistical-middle"], "21": ["fd_S01_100-runs"],
    "22": ["fd_title-t05_average"], "24": ["fd_S01_fingerprint"], "25": ["fd_title-t07_damn"],
    "26": ["fd_title-t08_okay", "fd_title-t09_oh"], "27": ["fd_S02_tells-a", "fd_S02_tells-b"],
    "30": ["fd_S02_wathan-post"], "31": ["fd_S02_training-loop"], "34": ["fd_S03_convergence"],
    "35": ["fd_S03_convergence"], "39": ["fd_S03_pro-vs-nonpro"], "40": ["fd_title-t10_fix"],
    "41": ["fd_S04_claude-bin"], "42": ["fd_S04_50ms"], "43": ["fd_S04_trust"], "44": ["fd_S04_trust"],
    "46": ["fd_S04_stripe-space"], "48": ["fd_S04_button-states"], "49": ["fd_S04_character"],
    "50": ["fd_title-t11_bigq"], "51": ["fd_S05_board-a", "fd_S05_board-b"], "52": ["fd_S05_specific-generic"],
    "53": ["fd_S05_board-c"], "56": ["fd_S05_board-d"], "57": ["fd_S05_exclusions"],
    "60": ["fd_S05_board-e", "fd_S05_parallel-1", "fd_S05_parallel-2", "fd_S05_parallel-3"],
    "61": ["fd_S05_board-f"], "64": ["fd_S05_stat-70"], "65": ["fd_S05_board-g"], "68": ["fd_S05_before-after"],
}

CHANGED = ["fd_S04_50ms", "fd_S04_button-states", "fd_S04_character"]  # Joel's three changes, 14 September 2026
ADDED = ["fd_title-t08_okay", "fd_S02_tells-b", "fd_S05_board-a", "fd_S05_audience-questions", "fd_teach-gaps",
         "fd_S05_parallel-1", "fd_S05_board-e", "fd_S05_parallel-3"]  # on no note of his, by note coverage


def sha(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Learn(unittest.TestCase):
    def setUp(self):
        self.w = P1World()

    def tearDown(self):
        self.w.cleanup()

    def cases(self):
        return [json.loads(l) for l in (self.w.ds / "critic" / "labelled-cases.jsonl").read_text().splitlines()[1:]]

    def index(self):
        code, d = self.w.run("moments", check=True)
        return json.loads((self.w.project / "moments" / "index.json").read_text())

    def calibrate(self):
        code, d = self.w.run("calibrate", "joel", operator=False)
        self.assertEqual(code, 0, d)
        return d

    def p2(self):
        reg = json.loads(self.w.registry.read_text())
        joel = next(c for c in reg["clients"] if c["id"] == "joel")
        d = self.w.root / joel["projects"]["P2"]["dir"]
        (d / "data").mkdir(parents=True, exist_ok=True)
        return d

    # --- import-review: comments to moments ------------------------------------------------------------

    def test_the_66_comments_map_to_the_right_moments(self):
        self.w.import_notes()
        code, d = self.w.run("import-review", str(self.w.notes_csv), check=True)
        self.assertEqual((d["comments"], d["mapped_to_moments"], d["about_edit"], d["unreadable"]), (66, 57, 9, 0))
        review = json.loads(next((self.w.project / "reviews" / "joel").glob("*-review.json")).read_text())
        by = {c["number"]: c for c in review["comments"]}
        self.assertEqual({n: c["moment"] for n, c in by.items()}, ON)
        for n, c in by.items():
            self.assertEqual(c["level"], "explicit" if c["moment"] else "video", n)
        # Against P1's own map: every note a HyperFrames build answered is on that build, but #4. Its build
        # (cartoon-rings) starts 3.1 s after the note; at the note's frame Joel's still is on screen alone.
        idx = {m["id"]: m for m in self.index()["moments"]}
        for n, built in ANSWERED_BY.items():
            if n == "4":
                self.assertEqual(by[n]["moments"], [])
                self.assertGreater(idx[built[0]]["word_span"][0] - by[n]["seconds"], 3.0)
                continue
            self.assertTrue(set(built) & set(by[n]["moments"]), (n, built, by[n]["moments"]))
        # #20 runs "through 00:02:19:12": it is on both builds that answer it.
        self.assertEqual(by["20"]["timecode_out"], "00:02:19:12")
        self.assertLessEqual({"fd_S01_next-token", "fd_S01_statistical-middle"}, set(by["20"]["moments"]))
        # The same rule as note coverage: the moments the comments are on are exactly the asked moments.
        on = {m for c in by.values() for m in c["moments"]}
        self.assertEqual(on, {m for m, x in idx.items() if x["asked"]})
        self.assertEqual(sorted(set(idx) - on), sorted(ADDED))
        # Drafts for the inbox: one per moment with its comments, one per remark about the video.
        drafts = [json.loads(l) for l in next((self.w.project / "reviews" / "joel").glob("*.draft.jsonl")).read_text().splitlines()]
        self.assertEqual(len([x for x in drafts if x["level"] == "explicit"]), 50)
        self.assertEqual(len([x for x in drafts if x["level"] == "video"]), 9)

    # --- rulings at their level ------------------------------------------------------------------------

    def test_three_explicit_change_rulings(self):
        self.w.import_notes()
        ruled = {m["id"]: m["ruling"] for m in self.index()["moments"] if m.get("ruling")}
        self.assertEqual(sorted(ruled), CHANGED)
        for mid, r in ruled.items():
            self.assertEqual((r["level"], r["ruling"]), ("explicit", "change"), mid)
            self.assertIsNone(r["words"], mid)  # his words were never copied in (the case says TODO); not invented

    def test_accept_video_writes_55_implicit_acceptances(self):
        self.w.import_notes()
        before = len(self.cases())
        code, d = self.w.run("accept-video", "v08", "--source", "Frame.io, 14 Sep 2026", check=True)
        self.assertEqual((d["implicit_written"], sorted(d["explicit"]), d["no_render_at_version"]), (55, CHANGED, []))
        new = self.cases()[before:]
        self.assertEqual(len(new), 55)
        renders = self.w.project / "renders" / "v08"
        for c in new:
            self.assertEqual((c["level"], c["ruling"], c["status"], c["version"], c["source"]),
                             ("implicit", "accepted", "development case", "v08", "Frame.io, 14 Sep 2026"))
            self.assertIsNone(c["joel_words"])  # silence is never written as his words
            self.assertNotIn(c["moment"], CHANGED)
            self.assertEqual(c["render_sha256"], sha(next(renders.glob(c["moment"] + "_v08.*"))))
            self.assertEqual(c["direction"], "full notes")
        self.assertEqual(sorted(c["moment"] for c in new if c["asked"] == "added"), sorted(ADDED))
        self.assertEqual(self.w.events()[-1]["event"], "video_accepted")
        # Once is enough: a second acceptance of the same version writes nothing.
        code, d = self.w.run("accept-video", "v08", "--source", "Frame.io, 14 Sep 2026", check=True)
        self.assertEqual((d["implicit_written"], len(d["already_accepted"])), (0, 55))
        # The status line counts every moment as ruled now; the three changes stay explicit.
        idx = self.index()
        self.assertEqual(sum(1 for m in idx["moments"] if m.get("ruling")), 58)
        self.assertEqual(sorted(m["id"] for m in idx["moments"] if m["ruling"]["level"] == "explicit"), CHANGED)

    def test_accept_video_is_the_operators(self):
        code, d = self.w.run("accept-video", "v08", "--source", "Frame.io", operator=False)
        self.assertEqual(code, 2)
        self.assertTrue(d["operator_only"])

    # --- calibrate -------------------------------------------------------------------------------------

    def test_calibrate_on_p1(self):
        self.w.import_notes()
        self.w.run("accept-video", "v08", "--source", "Frame.io, 14 Sep 2026", check=True)
        rules_before = sha(self.w.ds / "rules.md")
        d = self.calibrate()
        text = d["text"]
        self.assertIn("3 explicit, 55 implicit, 0 video, 0 channel ruling(s) from the client.", text)
        self.assertIn("Fewer than 30 explicit cases: every figure below is development data, not evidence.", text)
        self.assertIn("0 of 8 additions changed, 3 of 50 asked [3 explicit cases: development data, not evidence]", text)
        v = d["videos"][0]
        self.assertEqual((v["project"], v["delivered"], v["changed"], v["implicit"], v["unruled"]), ("P1", 58, 3, 55, 0))
        self.assertEqual(v["asked"], {"asked": {"changed": 3, "of": 50}, "added": {"changed": 0, "of": 8}})
        self.assertEqual(sorted(v["changed_moments"]), CHANGED)
        verdicts = {r["rule"]: r["verdict"] for r in d["rules"]}
        self.assertEqual(verdicts["M-26"], "suggested by rulings, unconfirmed")
        self.assertEqual(verdicts["B-29"], "suggested by rulings, unconfirmed")
        self.assertEqual(sorted(c["rule"] for c in d["candidates"]), ["B-29", "M-26"])
        for c in d["candidates"]:
            self.assertEqual(c["entry"], "2026-09-14 · P1 · three change requests after delivery")
            self.assertIn("suggested by rulings", c["line"])
            self.assertIn(c["line"], text)  # printed, never applied
        self.assertEqual(sha(self.w.ds / "rules.md"), rules_before)
        self.assertIn("untested: no critic findings (critic.json) recorded for any ruled version", text)
        self.assertFalse(d["evidence"])

    def test_calibrate_tells_changes_that_rest_on_our_choices(self):
        self.w.import_notes()
        self.w.run("accept-video", "v08", "--source", "Frame.io, 14 Sep 2026", check=True)
        self.w.run("chose", "a 50 ms full-frame cut", "--why", "the speed is the point", "--moment", "fd_S04_50ms",
                   operator=False, check=True)
        self.w.run("chose", "the park map in his colours", "--why", "one colour per route",
                   "--moment", "fd_S05_board-a", operator=False, check=True)
        d = self.calibrate()
        v = d["videos"][0]
        self.assertEqual((v["changed_on_our_choice"], v["moments_with_choices"]), (1, 2))
        self.assertIn("1 of 3 changed moment(s) rest on a choice of ours (aem chose); 2 of 58 moments carry one", d["text"])

    def test_calibrate_with_no_rulings_says_so_and_stops(self):
        cases = self.w.ds / "critic" / "labelled-cases.jsonl"
        cases.write_text(cases.read_text().splitlines()[0] + "\n")  # the header line alone
        d = self.calibrate()
        self.assertEqual(d["stopped"], "no rulings")
        self.assertIn("No rulings recorded for Joel Belton yet: nothing to calibrate.", d["text"])
        self.assertNotIn("Acceptance per video", d["text"])

    def test_our_rulings_are_never_counted_as_the_clients(self):
        cases = self.w.ds / "critic" / "labelled-cases.jsonl"
        ours = {"case_id": "P1-fd_S04_trust-2026-09-01", "video": "P1", "shot": "fd_S04_trust", "ruling": "keep",
                "source": "yuvraj", "item_kind": "plan_row", "level": "operator", "notes": "Ours: approved in the inbox."}
        with cases.open("a") as f:
            f.write(json.dumps(ours) + "\n")
        d = self.calibrate()
        self.assertEqual((d["levels"]["operator"], d["explicit"]), (1, 3))
        self.assertIn("1 of ours (operator), left out", d["text"])

    # --- what the client said, at its level, and recall --------------------------------------------------

    def test_the_channel_statement_is_stored_and_recalled_first(self):
        self.w.import_notes()  # P1's moments index, as `aem moments` leaves it on the drive
        p2 = self.p2()
        decisions = self.w.ds / "joel-decisions.md"
        before = sha(decisions)
        code, d = self.w.run("client-said", "--about", "channel", "--source", "WhatsApp, 5 Oct 2026", stdin=QUOTE, cwd=p2)
        self.assertEqual(code, 0, d)
        case = self.cases()[-1]
        self.assertEqual((case["level"], case["video"], case["ruling"], case["moment"], case["source"]),
                         ("channel", "P2", None, None, "WhatsApp, 5 Oct 2026"))
        self.assertEqual(case["joel_words"], QUOTE)  # verbatim
        # His words are already in joel-decisions.md (the 5 October entry, across wrapped lines): not written again;
        # the ruling names that entry.
        self.assertEqual(d["existing_entry"], "2026-10-05 · P2 (Claude Code video) · WhatsApp")
        self.assertEqual(case["decisions_entry"], "2026-10-05 · P2 (Claude Code video) · WhatsApp")
        self.assertEqual(sha(decisions), before)
        r = self.w.run_raw("recall", cwd=p2, operator=False)
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = r.stdout.splitlines()
        self.assertIn("How Joel reviews: reviews the whole video; approval on Frame.io; timestamped notes on Frame.io; "
                      "other feedback on WhatsApp; never sees the production process.", lines)
        at = next(i for i, l in enumerate(lines) if l.startswith("Joel on how to work for this channel"))
        self.assertEqual(lines[at + 1], f'  {case["ruling_date"]} · WhatsApp, 5 Oct 2026: "{QUOTE}"')
        changed = next(i for i, l in enumerate(lines) if l.startswith("What Joel changed last time (P1: 3 explicit changes"))
        prefs = next(i for i, l in enumerate(lines) if l.startswith("Standing preferences"))
        self.assertLess(at, changed)
        self.assertLess(changed, prefs)
        self.assertIn("  animation · job not recorded · fd_S04_50ms (asked; change; M-26): Joel's words not recorded "
                      "(our note: he asked to remove the one-frame Prim & Paw website flash (frame 2))", lines)
        code, d = self.w.run("recall", cwd=p2, operator=False)
        self.assertEqual(d["channel_rulings"][0], case["case_id"])
        self.assertEqual(sorted(c["moment"] for c in d["changed_last_time"]["changes"]), CHANGED)
        self.assertEqual(self.calibrate()["levels"]["channel"], 1)

    def test_direction_of_the_last_video_and_this_one(self):
        self.w.import_notes()  # P1's notes make its direction "full notes"
        p2 = self.p2()
        code, d = self.w.run("recall", cwd=p2, operator=False)
        self.assertEqual(d["direction"], {"P1": "full notes (66 notes)", "P2": "none (stated in the profile)"})
        self.assertIn("Direction: P1 (last video) full notes (66 notes); P2 (this video) none (stated in the profile)",
                      d["text"].splitlines())

    def test_client_said_about_a_moment_is_an_explicit_ruling(self):
        self.w.import_notes()
        code, d = self.w.run("client-said", "--about", "fd_S04_50ms", "--ruling", "change", "--source",
                             "WhatsApp, 14 Sep 2026", stdin="take that flash out")
        self.assertEqual(code, 0, d)
        case = self.cases()[-1]
        self.assertEqual((case["level"], case["ruling"], case["moment"], case["asked"], case["status"], case["version"]),
                         ("explicit", "change", "fd_S04_50ms", "asked", "labelled", "v08"))
        self.assertEqual(case["render_sha256"], sha(self.w.project / "renders" / "v08" / "fd_S04_50ms_v08.mp4"))
        self.assertEqual(case["joel_words"], "take that flash out")
        self.assertTrue(case["decisions_entry"].endswith("· P1 · WhatsApp, 14 Sep 2026"))  # a new entry, written
        # A remark with no keep, change or remove is his words on the moment, not a ruling.
        code, d = self.w.run("client-said", "--about", "fd_S04_trust", "--source", "WhatsApp", stdin="love this one")
        self.assertEqual(code, 0, d)
        trust = next(m for m in self.index()["moments"] if m["id"] == "fd_S04_trust")
        self.assertIsNone(trust.get("ruling"))
        self.assertIn("1 remark(s) on a moment with no keep, change or remove", self.calibrate()["text"])

    def test_client_said_about_refuses_what_it_cannot_mean(self):
        code, d = self.w.run("client-said", "--about", "channel", "--ruling", "change", "--source", "WhatsApp", stdin="x")
        self.assertEqual(code, 2)
        self.assertIn("a channel-level remark has no keep, change or remove", d["error"])
        code, d = self.w.run("client-said", "--about", "fd_nothing", "--source", "WhatsApp", stdin="x")
        self.assertEqual(code, 2)
        self.assertIn("no moment 'fd_nothing'", d["error"])


if __name__ == "__main__":
    unittest.main()
