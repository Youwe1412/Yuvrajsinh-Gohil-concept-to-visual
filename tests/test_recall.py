"""aem recall, and the session context built around it: one screen on a client for a new session."""
import unittest

from helpers import JoelWorld, WorldCase


class Recall(unittest.TestCase):
    def setUp(self):
        self.w = JoelWorld()

    def tearDown(self):
        self.w.cleanup()

    def test_preferences_rulings_questions_and_cases_on_one_screen(self):
        code, d = self.w.run("recall", "joel", operator=False)
        self.assertEqual(code, 0, d)
        self.assertEqual([p["id"] for p in d["preferences"]], ["J-01", "J-03"])
        self.assertEqual([r["heading"] for r in d["rulings"]],
                         ["2026-10-05 · P2 (Claude Code video) · WhatsApp", "2026-09-23 · P1 (Frontend Design) published",
                          "Before P1 · Joel's video brief (Notion)"])
        self.assertEqual(d["open_questions"], ["Why did you ask for the three P1 changes?",
                                               'Is "leave the grade as is" for every video, or for P2?'])
        self.assertEqual((d["labelled_cases"]["total"], d["labelled_cases"]["labelled"]), (1, 0))
        t = d["text"]
        self.assertLessEqual(len(t.splitlines()), 40)
        # Joel's words verbatim, never paraphrased; our notes say they are ours.
        self.assertIn('WhatsApp: "Could you leave the color grading as is on this one I think its a bit more natural" (+1 more quote)', t)
        self.assertIn("published: no quote; our note: The film went live with the 14 September fixes below. Approved for publication.", t)
        self.assertIn('(Notion): "It\'s too obvious." (+1 more quote)', t)
        self.assertIn("J-01 Prefer no AI imagery or AI video", t)
        self.assertIn("Open questions for Joel (2):", t)
        self.assertIn("Labelled cases: 1 in critic/labelled-cases.jsonl, 0 labelled (1 development case)", t)

    def test_only_the_last_five_rulings(self):
        path = self.w.ds / "joel-decisions.md"
        head, rest = path.read_text().split("---\n", 1)
        extra = "".join(f"## 2026-10-1{i} · P2 · email\n\n> \"words {i}\"\n\n---\n\n" for i in range(5))
        path.write_text(head + "---\n\n" + extra + rest)
        _, d = self.w.run("recall", "joel", operator=False)
        self.assertEqual(len(d["rulings"]), 5)
        self.assertEqual(d["rulings_total"], 8)
        self.assertTrue(d["rulings"][0]["heading"].startswith("2026-10-10"))

    def test_the_client_resolves_from_the_folder_and_writes_nothing(self):
        code, d = self.w.run("recall", operator=False)
        self.assertEqual((code, d["client"]), (0, "joel"))
        self.assertEqual(self.w.events(), [])


class Context(WorldCase):
    def test_the_principle_the_project_three_rules_and_the_recall(self):
        self.w.use()
        self.w.run("stage", "start", "G2", check=True)
        _, d = self.w.run("context", operator=False, check=True)
        t = d["text"]
        self.assertTrue(t.startswith("# Aavkar Educational Motion Studio (AEM)\n\nAEM observes and records. It never "
                                     "blocks work in a session the operator is sitting in."))
        self.assertIn("The only interruption is a confirmation before delivering a render that has no current approval.", t)
        self.assertIn("rulings in Ada's own words", t)
        self.assertIn("Gate: G2 (Plan)", t)
        self.assertIn("Frame rate: 24000/1001 (from frame.md)", t)
        self.assertIn("never write them yourself", t)
        self.assertIn("ask Yuvraj in one sentence", t)
        self.assertIn("`/approve <item>`", t)
        self.assertIn("AEM recall · Acme Learning (acme) · Ada", t)
        self.assertEqual([p["id"] for p in d["preferences"]], ["A-01", "A-02"])
        for gone in ("AEM_OPERATOR_TURN", "/allow", "guard", "turn authority", "latest message"):
            self.assertNotIn(gone, t)

    def test_no_project_says_so(self):
        code, d = self.w.run("context", cwd=self.w.tmp, operator=False)
        self.assertEqual((code, d["active"]), (0, False))
        self.assertIn("/aem use", d["text"])
        self.assertIn("records nothing", d["text"])


if __name__ == "__main__":
    unittest.main()
