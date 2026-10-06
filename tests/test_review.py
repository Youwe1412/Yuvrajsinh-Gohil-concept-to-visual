"""import-review: a Frame.io CSV fixture mapped to shots and word IDs at 24000/1001 and at 25."""
import json
import shutil
from pathlib import Path

from helpers import REPO, WorldCase

FIX = REPO / "tests" / "fixtures"
WORDS = {"fps_num": 24000, "fps_den": 1001, "words": [
    {"id": "w0", "word": "next", "start": 128.0, "end": 128.3},
    {"id": "w1", "word": "token", "start": 128.4, "end": 128.8},
    {"id": "w2", "word": "prediction", "start": 130.0, "end": 130.6},
    {"id": "w3", "word": "button", "start": 5.5, "end": 5.9},
    {"id": "w4", "word": "later", "start": 200.0, "end": 200.4},
]}


class ImportReview(WorldCase):
    def setUp(self):
        super().setUp()
        shutil.copy(FIX / "edit.json", self.w.project / "data" / "edit.json")
        (self.w.project / "data" / "words.json").write_text(json.dumps(WORDS))
        self.decisions_before = (self.w.ds / "acme-decisions.md").read_bytes()
        self.cases_before = (self.w.ds / "critic" / "labelled-cases.jsonl").read_bytes()

    def run_import(self, *extra):
        code, d = self.w.run("import-review", str(FIX / "frameio-sample.csv"), *extra)
        self.assertEqual(code, 0, d)
        review = json.loads(Path(d["files"]["review"]).read_text())
        return d, {c["row"]: c for c in review["comments"]}, review

    def assert_untouched(self):
        self.assertEqual((self.w.ds / "acme-decisions.md").read_bytes(), self.decisions_before)
        self.assertEqual((self.w.ds / "critic" / "labelled-cases.jsonl").read_bytes(), self.cases_before)

    def test_ntsc_24000_1001(self):
        self.w.use()
        d, by_row, review = self.run_import()
        self.assertEqual(review["fps"], "24000/1001")
        self.assertEqual(review["columns"]["timecode"], "Timecode")
        self.assertEqual(review["columns"]["comment"], "Comment")
        self.assertEqual(by_row[2]["frame"], 128 * 24)
        self.assertAlmostEqual(by_row[2]["seconds"], 128.128, places=3)
        self.assertEqual(by_row[2]["shot"], "next-token")
        self.assertEqual(by_row[2]["word_ids"], ["w0", "w1"])
        self.assertEqual(by_row[3]["shot"], "teach-opening")
        self.assertEqual(by_row[3]["word_ids"], ["w3"])
        self.assertIsNone(by_row[4]["shot"])
        self.assertTrue(by_row[4]["about"].startswith("edit"))
        self.assertEqual(by_row[5]["frame"], 129 * 24 + 23)
        self.assertEqual(by_row[5]["shot"], "next-token")
        self.assertEqual(by_row[5]["comment"], 'Two notes:\nfirst, slower; second, "brighter"')  # verbatim
        self.assertIsNone(by_row[6]["frame"])
        self.assertEqual(d["shots_pending"], ["statistical-middle"])
        self.assertEqual((d["mapped_to_shots"], d["about_edit"], d["unreadable"]), (3, 1, 1))
        # The CSV is kept byte for byte.
        self.assertEqual(Path(d["files"]["csv"]).read_bytes(), (FIX / "frameio-sample.csv").read_bytes())
        rulings = Path(d["files"]["rulings"]).read_text()
        self.assertIn("| statistical-middle | - | pending (no comment) |", rulings)
        drafts = [json.loads(l) for l in Path(d["files"]["drafts"]).read_text().splitlines()]
        self.assertEqual({c["shot"] for c in drafts}, {"next-token", "teach-opening"})
        nt = [c for c in drafts if c["shot"] == "next-token"][0]
        self.assertEqual(nt["acme_words"], ["Love this one, keep it", 'Two notes:\nfirst, slower; second, "brighter"'])
        self.assertIsNone(nt["ruling"])
        self.assertEqual(nt["status"], "development case")
        self.assertTrue(nt["draft"])
        self.assertEqual(self.w.events()[-1]["event"], "review_import")
        self.assert_untouched()

    def test_pal_25(self):
        self.w.use(["--fps", "25/1"])
        d, by_row, review = self.run_import()
        self.assertEqual(review["fps"], "25/1")
        self.assertEqual(by_row[2]["frame"], 128 * 25)
        self.assertEqual(by_row[2]["seconds"], 128.0)
        self.assertEqual(by_row[2]["shot"], "next-token")
        self.assertEqual(by_row[3]["frame"], 5 * 25 + 12)
        self.assertEqual(by_row[5]["frame"], 129 * 25 + 23)
        self.assertEqual(by_row[5]["word_ids"], ["w2"])
        self.assert_untouched()

    def test_delivered_rate_and_start_offset(self):
        self.w.use()
        d, by_row, review = self.run_import("--fps", "25/1", "--start-tc", "00:00:01:00")
        self.assertEqual(by_row[2]["frame"], 128 * 25 - 25)
        self.assertEqual(review["fps_source"], "--fps")
        self.assertEqual(review["timeline_start"], "00:00:01:00")

    def test_missing_columns_refused(self):
        self.w.use()
        bad = self.w.tmp / "bad.csv"
        bad.write_text("A,B\n1,2\n")
        code, d = self.w.run("import-review", str(bad))
        self.assertEqual(code, 2)
        self.assertIn("timecode and comment", d["error"])
