"""Ledger integrity: anything written to a record outside AEM is detected, never prevented.

A hand edit of a ledger, by the operator or the agent, is flagged by `aem integrity` and on the status line
until the operator runs /accept-edit. When AEM observed the agent's tool call that wrote the file, the finding
says so.
"""
import json
import os
import unittest
from pathlib import Path

import isolation
from helpers import WorldCase


class Integrity(WorldCase):
    def setUp(self):
        super().setUp()
        self.w.use()

    def hand_write(self, name="events.jsonl", line='{"ts": "2026-10-06T12:00:00+05:30", "event": "approval", "scene": "x"}'):
        with open(self.w.project / name, "a") as f:
            f.write(line + "\n")

    def integrity(self):
        return self.w.run("integrity", operator=False)

    def render(self, name="x_v01.mp4", data=b"one"):
        p = self.w.project / "renders" / name
        p.write_bytes(data)
        return p

    def test_clean_after_aem_wrote_everything(self):
        self.w.run("stage", "start", "G1", check=True)
        self.render()
        self.w.run("approve", "x", "renders/x_v01.mp4", "--gate", "G4", check=True)
        self.w.run("observe", stdin=json.dumps({"tool": "Bash", "input": {"command": "ls"}, "cwd": str(self.w.project)}),
                   operator=False, check=True)
        code, d = self.integrity()
        self.assertEqual((code, d["ok"], d["findings"]), (0, True, 0), d)

    def test_a_hand_written_line_is_flagged_until_the_operator_accepts_it(self):
        self.w.run("stage", "start", "G1", check=True)
        self.hand_write(line='{"ts": "2026-10-06T12:00:00+05:30", "gate": "G1", "event": "note", "note": "Ada called"}')
        # 1. flagged, with what is in the line, and that no observed call wrote it
        code, r = self.integrity()
        self.assertEqual((code, r["ok"], r["findings"], r["outside_agent"]), (1, False, 1, 1), r)
        f = next(x for x in r["files"] if x["name"] == "events.jsonl")
        self.assertEqual(f["findings"][0]["kind"], "inserted")
        self.assertIn("Ada called", f["findings"][0]["now"][0]["text"])
        self.assertIn("no observed tool call wrote it", f["explanation"])
        # 2. the status line counts it, and the agent's context tells it
        _, st = self.w.run("status", operator=False)
        self.assertIn("· 1 ledger edit to review", st["statusline"])
        self.assertEqual(st["statusline_parts"]["integrity"], 1)
        _, ctx = self.w.run("context", operator=False)
        self.assertIn("AEM integrity: 1 ledger difference(s) in events.jsonl", ctx["text"])
        # 3. the agent cannot accept it; the operator can, and it is recorded
        code, d = self.w.run("accept-edit", operator=False)
        self.assertEqual((code, d.get("operator_only")), (2, True), d)
        self.assertEqual(self.integrity()[0], 1)
        code, d = self.w.run("accept-edit", "--reason", "I added that line")
        self.assertEqual(code, 0, d)
        self.assertEqual(d["accepted"][0]["file"], "events.jsonl")
        acc = [e for e in self.w.events() if e["event"] == "edit_accepted"]
        self.assertEqual((len(acc), acc[0]["file"], acc[0]["note"], acc[0]["via"]),
                         (1, "events.jsonl", "I added that line", "slash command"))
        code, r = self.integrity()
        self.assertEqual((code, r["ok"]), (0, True), r)
        # 4. a later hand edit is flagged again
        self.hand_write(line='{"event": "another"}')
        self.assertEqual(self.integrity()[0], 1)

    def test_an_edit_by_the_agent_says_so(self):
        self.w.run("stage", "start", "G1", check=True)
        target = self.w.project / "events.jsonl"
        req = {"tool": "Edit", "input": {"file_path": str(target), "old_string": "a", "new_string": "b"},
               "cwd": str(self.w.project), "session": "s9"}
        self.w.run("observe", stdin=json.dumps(req), operator=False, check=True)  # the plugin, before the Edit runs
        self.hand_write(line='{"event": "forged"}')  # what the Edit did
        code, r = self.integrity()
        self.assertEqual((code, r["by_agent"]), (1, 1), r)
        f = next(x for x in r["files"] if x["name"] == "events.jsonl")
        self.assertEqual((f["observed_writes"][0]["tool"], f["observed_writes"][0]["session"]), ("Edit", "s9"))
        self.assertIn("the agent wrote it", f["explanation"])
        self.w.run("accept-edit", "--reason", "fine", check=True)
        acc = [e for e in self.w.events() if e["event"] == "edit_accepted"][-1]
        self.assertEqual(acc["observed_writes"][0]["tool"], "Edit")

    def test_a_shell_read_of_a_ledger_is_not_taken_for_a_write(self):
        self.w.run("stage", "start", "G1", check=True)
        req = {"tool": "Bash", "input": {"command": "grep -c observed events.jsonl"}, "cwd": str(self.w.project)}
        self.w.run("observe", stdin=json.dumps(req), operator=False, check=True)
        self.hand_write(line='{"event": "by hand"}')
        code, r = self.integrity()
        self.assertEqual((code, r["by_agent"], r["outside_agent"]), (1, 0, 1), r)

    def test_edits_and_removals_of_aem_lines_are_found(self):
        self.w.run("stage", "start", "G1", check=True)
        self.render()
        self.w.run("approve", "x", "renders/x_v01.mp4", "--gate", "G4", check=True)
        path = self.w.project / "approvals.jsonl"
        text = path.read_text()
        path.write_text(text.replace('"gate": "G4"', '"gate": "G5"'))  # the approval now says another gate
        code, r = self.integrity()
        self.assertEqual(code, 1, r)
        self.assertEqual(next(x for x in r["files"] if x["name"] == "approvals.jsonl")["findings"][0]["kind"], "edited")
        path.write_text("")  # and now it is gone
        code, r = self.integrity()
        f = next(x for x in r["files"] if x["name"] == "approvals.jsonl")
        self.assertEqual((code, f["findings"][0]["kind"], f["findings"][0]["removed_count"]), (1, "removed", 1), r)

    def test_the_decisions_file_is_a_ledger_too_and_client_said_does_not_accept_a_hand_edit(self):
        self.w.run("client-said", "--scope", "video", "--source", "email", stdin="First words", check=True)
        path = self.w.ds / "acme-decisions.md"
        self.assertEqual(self.integrity()[0], 0)
        path.write_text(path.read_text().replace("> First words", "> First words, edited by hand"))
        code, r = self.integrity()
        self.assertEqual(code, 1, r)
        self.w.run("client-said", "--scope", "video", "--source", "email", stdin="Second words", check=True)
        code, r = self.integrity()
        f = next(x for x in r["files"] if x["name"] == "acme-decisions.md")
        self.assertEqual(code, 1, r)
        self.assertEqual(len(f["findings"]), 1, f)  # only the hand edit; the second entry is AEM's
        self.assertIn("edited by hand", f["findings"][0]["now"][0]["text"])

    def test_no_baseline_is_reported_not_guessed_and_the_first_write_makes_one(self):
        code, r = self.integrity()
        self.assertEqual((code, r["ok"]), (0, True))
        self.assertIn("events.jsonl", r["no_baseline"])
        self.hand_write(name="events.jsonl")  # an older line, from before AEM tracked the file
        self.w.run("stage", "start", "G1", check=True)  # AEM's first write: the old line is the baseline
        code, r = self.integrity()
        self.assertEqual((code, r["ok"]), (0, True), r)
        manifest = [json.loads(l) for l in (self.w.project / ".aem-integrity" / "events.jsonl.jsonl").read_text().splitlines()]
        self.assertEqual(manifest[0]["t"], "baseline")
        self.assertEqual(len(manifest[0]["hashes"]), 1)

    def test_accept_edit_with_nothing_to_accept_says_so_and_names_unknown_files(self):
        self.w.run("stage", "start", "G1", check=True)
        code, d = self.w.run("accept-edit")
        self.assertEqual((code, d["accepted"]), (0, []))
        code, d = self.w.run("accept-edit", "--file", "rules.md")
        self.assertEqual(code, 2, d)

    def test_a_whole_flow_leaves_the_real_aem_home_and_registry_untouched(self):
        before = isolation.snapshot()
        self.w.run("stage", "start", "G1", check=True)
        self.hand_write()
        self.integrity()
        self.w.run("accept-edit", "--reason", "test", check=True)
        self.assertEqual(isolation.changed(before, isolation.snapshot()), [])
        self.assertNotEqual(Path(os.environ["AEM_HOME"]).resolve(), isolation.REAL_AEM_HOME.resolve())


if __name__ == "__main__":
    unittest.main()
