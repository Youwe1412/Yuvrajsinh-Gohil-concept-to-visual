"""aem inbox: what waits on the operator, the commands its buttons run, and the labelled cases left."""
import json
import shutil
import unittest

from helpers import HAVE_FFMPEG, REPO, WorldCase, make_video
from test_review import WORDS

FIX = REPO / "tests" / "fixtures"

SHOTLIST = """# Shot list

| Shot | Teaching job | Source |
|---|---|---|
| `next-token` | show prediction one token at a time | build |
| **fd_S02_teach-opening** | name the idea before the demo | A-roll |
"""


class Inbox(WorldCase):
    def setUp(self):
        super().setUp()
        self.w.use()
        self.cases_path = self.w.ds / "critic" / "labelled-cases.jsonl"

    def items(self):
        code, d = self.w.run("inbox")
        self.assertEqual(code, 0, d)
        return {i["id"]: i for i in d["items"]}

    def press(self, item, label, reason=None):
        """What the plugin does on a button: run the item's argv, adding --reason when asked for one."""
        act = next(a for a in item["actions"] if a["label"] == label)
        argv = list(act["argv"]) + (["--reason", reason] if act["needs_reason"] else [])
        code, d = self.w.run(*argv)
        self.assertEqual(code, 0, d)
        return d

    def cases(self):
        return [json.loads(l) for l in self.cases_path.read_text().splitlines()[1:] if l.strip()]

    def test_nothing_waiting(self):
        code, d = self.w.run("inbox")
        self.assertEqual((code, d["items"], d["summary"]), (0, [], "Nothing is waiting on you."))

    def test_plan_rows(self):
        (self.w.project / "shotlist.md").write_text(SHOTLIST)
        its = self.items()
        self.assertEqual(sorted(its), ["plan:shotlist.md#fd_S02_teach-opening", "plan:shotlist.md#next-token"])
        row = its["plan:shotlist.md#next-token"]
        self.assertEqual((row["kind"], row["gate"]), ("plan_row", "G2"))
        self.assertIn("show prediction one token at a time", row["detail"])

        self.press(row, "Approve")
        a = [json.loads(l) for l in (self.w.project / "approvals.jsonl").read_text().splitlines()][-1]
        self.assertEqual((a["item_kind"], a["gate"], a["scene"], a["plan_file"]), ("plan_row", "G2", "next-token", "shotlist.md"))
        self.assertNotIn("plan:shotlist.md#next-token", self.items())
        case = self.cases()[-1]
        self.assertEqual((case["source"], case["ruling"], case["status"], case["item_kind"], case["acme_words"]),
                         ("yuvraj", "keep", "development case", "plan_row", None))
        self.assertEqual((case["render_sha256"], len(case["plan_row_sha256"])), (None, 64))

        self.press(self.items()["plan:shotlist.md#fd_S02_teach-opening"], "Reject", reason="no A-roll for this line")
        case = self.cases()[-1]
        self.assertEqual((case["ruling"], case["reason"]), ("change", "no A-roll for this line"))
        self.assertEqual(self.items(), {})

        # The approved row's text changes: it waits again, marked as changed.
        (self.w.project / "shotlist.md").write_text(SHOTLIST.replace("one token at a time", "token by token"))
        again = self.items()["plan:shotlist.md#next-token"]
        self.assertEqual(again["note"], "changed since it was approved")

    def test_still_and_kinds_do_not_cross(self):
        (self.w.project / "stills").mkdir()
        (self.w.project / "stills" / "shot_v01.png").write_bytes(b"png one")
        r = self.w.project / "renders" / "shot_v01.mp4"
        r.write_bytes(b"render")
        self.w.run("approve", "shot", str(r), "--gate", "G4", check=True)
        it = self.items()["still:stills/shot_v01.png"]
        self.assertEqual((it["kind"], it["item"], it["gate"]), ("still", "shot", "G3"))
        self.press(it, "Reject", reason="type too small")
        # Rejecting the still leaves the render's approval standing.
        code, _ = self.w.run("check-approval", str(r))
        self.assertEqual(code, 0)
        self.assertEqual(self.cases()[-1]["item_kind"], "still")
        self.assertEqual(self.w.run("status")[1]["approvals"]["standing"], 1)

    @unittest.skipUnless(HAVE_FFMPEG, "ffmpeg and ffprobe are needed")
    def test_checked_render(self):
        p = make_video(self.w.project / "renders" / "scene_v01.mp4", frames=20)
        self.w.run("check-render", str(p))  # no expected duration: passes or fails, either way recorded
        it = self.items()["render:scene"]
        self.assertEqual((it["kind"], it["gate"], it["title"]), ("render", "G4", "renders/scene_v01.mp4"))
        self.press(it, "Approve")
        self.assertNotIn("render:scene", self.items())
        case = self.cases()[-1]
        self.assertEqual((case["item_kind"], case["ruling"], len(case["render_sha256"])), ("render", "keep", 64))
        self.assertEqual(case["frames_or_crops"], ["P1 - Test/renders/scene_v01.mp4"])
        # A new render, once checked, waits again.
        make_video(p, frames=21)
        self.w.run("check-render", str(p))
        self.assertIn("render:scene", self.items())

    def test_denials(self):
        self.w.run("guard", stdin=json.dumps({"tool": "Bash", "input": {"command": "npx hyperframes snapshot --describe ."},
                                              "cwd": str(self.w.project)}))
        self.w.run("guard", stdin=json.dumps({"tool": "Read", "input": {"file_path": "/Volumes/Other/x.md"},
                                              "cwd": str(self.w.project)}))
        its = [i for i in self.items().values() if i["kind"] == "override"]
        self.assertEqual([i["item"] for i in its], ["AEM-G03", "AEM-G02"])
        self.assertEqual([a["label"] for a in its[0]["actions"]], ["Allow once", "Reject"])
        d = self.press(its[0], "Allow once")
        self.assertTrue(d["once"])
        self.press(its[1], "Reject", reason="not needed for this client")
        self.assertEqual([i for i in self.items().values() if i["kind"] == "override"], [])
        cases = self.cases()
        self.assertEqual([(c["item_kind"], c["decision"], c["ruling"]) for c in cases],
                         [("override", "allowed once", None), ("override", "dismissed", None)])
        self.assertEqual([(c["shot"], c["rule"]) for c in cases], [(None, "AEM-G03"), (None, "AEM-G02")])
        # The one-time allow now lets the blocked command through once.
        code, g = self.w.run("guard", stdin=json.dumps({"tool": "Bash", "input": {"command": "npx hyperframes snapshot --describe ."},
                                                         "cwd": str(self.w.project)}))
        self.assertEqual((code, g["decision"]), (0, "allow"))

    def test_client_comments(self):
        shutil.copy(FIX / "edit.json", self.w.project / "data" / "edit.json")
        (self.w.project / "data" / "words.json").write_text(json.dumps(WORDS))
        self.w.run("import-review", str(FIX / "frameio-sample.csv"), check=True)
        before = self.cases_path.read_bytes()
        comments = {i["item"]: i for i in self.items().values() if i["kind"] == "client_comment"}
        self.assertEqual(sorted(comments), ["next-token", "teach-opening"])
        self.assertEqual(self.cases_path.read_bytes(), before)  # listing writes nothing
        c = comments["teach-opening"]
        self.assertEqual([a["label"] for a in c["actions"]], ["Keep", "Change", "Remove", "Reject"])
        self.assertIn("Can we lose the caption under the button?", c["detail"])

        # An approved render of the shot gives the case its SHA-256, so it is labelled.
        r = self.w.project / "renders" / "teach-opening_v01.mp4"
        r.write_bytes(b"delivered")
        self.w.run("approve", "teach-opening", str(r), "--gate", "G6", check=True)
        self.press(c, "Change")
        case = self.cases()[-1]
        self.assertEqual((case["status"], case["ruling"], case["source"], case["decision"]),
                         ("labelled", "change", "yuvraj", "accepted"))
        self.assertEqual(case["acme_words"], ["Can we lose the caption under the button? It says what we can already see"])
        self.assertTrue(case["words_source"].startswith("reviews/acme/"))
        self.assertEqual(len(case["render_sha256"]), 64)

        self.press(comments["next-token"], "Reject", reason="mapped to the wrong shot")
        self.assertEqual([i for i in self.items().values() if i["kind"] == "client_comment"], [])
        self.assertEqual(self.cases()[-1]["decision"], "dismissed")

    def test_dismiss_needs_reason_and_ids_must_exist(self):
        code, d = self.w.run("inbox", "dismiss", "denial:99", "--reason", "x")
        self.assertEqual(code, 2)
        self.assertIn("nothing waiting", d["error"])
        code, d = self.w.run("inbox", "dismiss", "denial:99")
        self.assertEqual(code, 2)
        self.assertIn("needs a reason", d["error"])

    def test_without_label_no_case_is_written(self):
        (self.w.project / "shotlist.md").write_text(SHOTLIST)
        self.w.run("approve", "next-token", str(self.w.project / "shotlist.md"), "--row", "next-token", "--gate", "G2",
                   check=True)
        self.assertEqual(self.cases(), [])
