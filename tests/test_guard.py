"""aem guard: every rule's denial, overrides by /allow, and the approval gate."""
import json

from helpers import WorldCase


class Guard(WorldCase):
    def setUp(self):
        super().setUp()
        self.w.use()

    def guard(self, tool, cwd=None, **args):
        code, d = self.w.run("guard", stdin=json.dumps({"tool": tool, "input": args, "cwd": cwd or str(self.w.project)}))
        return code, d

    def assertDenied(self, rule, tool, **args):
        code, d = self.guard(tool, **args)
        self.assertEqual((code, d.get("decision"), d.get("rule")), (1, "deny", rule), d)
        self.assertTrue(d["reason"] and d["how"])
        return d

    def assertAllowed(self, tool, **args):
        code, d = self.guard(tool, **args)
        self.assertEqual((code, d.get("decision")), (0, "allow"), d)
        return d

    # AEM-G01
    def test_protected_writes_denied(self):
        for f in (self.w.ds / "acme-decisions.md", self.w.ds / "rules.md", self.w.ds / "critic" / "labelled-cases.jsonl",
                  self.w.project / "events.jsonl", self.w.project / "approvals.jsonl", self.w.registry):
            d = self.assertDenied("AEM-G01", "Edit", file_path=str(f), old_string="a", new_string="b")
            self.assertIn("/allow AEM-G01", d["how"])
        self.assertDenied("AEM-G01", "Write", file_path=str(self.w.project / "events.jsonl"), content="{}")
        self.assertDenied("AEM-G01", "Bash", command="echo '{}' >> events.jsonl")
        self.assertDenied("AEM-G01", "Bash", command=f"sed -i '' s/a/b/ '{self.w.ds}/acme-decisions.md'")
        self.assertDenied("AEM-G01", "Bash", command="python3 -c 'open(\"critic/labelled-cases.jsonl\",\"a\")'")

    def test_symlink_to_protected_denied(self):
        link = self.w.project / "notes.md"
        link.symlink_to(self.w.ds / "acme-decisions.md")
        self.assertDenied("AEM-G01", "Write", file_path=str(link), content="x")

    def test_reading_protected_with_read_tool_allowed(self):
        self.assertAllowed("Read", file_path=str(self.w.ds / "acme-decisions.md"))
        self.assertAllowed("Bash", command="aem status")
        self.assertAllowed("Edit", file_path=str(self.w.project / "brief.md"), old_string="a", new_string="b")

    # AEM-G02
    def test_outside_scope(self):
        self.assertDenied("AEM-G02", "Read", file_path="/Volumes/Other Client/secret.md")
        self.assertDenied("AEM-G02", "Write", file_path="/Volumes/Other Client/x.md", content="x")
        self.assertDenied("AEM-G02", "Bash", command="cat '/Volumes/Other Client/brief.md'")
        self.assertAllowed("Bash", command="ls /usr/bin")
        self.assertAllowed("Read", file_path=str(self.w.ds / "rules.md"))

    # AEM-G03
    def test_blocked_command(self):
        d = self.assertDenied("AEM-G03", "Bash", command="npx hyperframes snapshot --describe .")
        self.assertIn('/allow "snapshot --describe"', d["how"])

    # AEM-G04
    def test_operator_only_aem_commands(self):
        for c in ("aem approve shot renders/a.mp4 --gate G4", "aem reject shot --reason x",
                  "echo hi | aem client-said --scope video --source x", "aem allow AEM-G01 --reason x",
                  "aem use acme/P1", "aem stage start G1", "~/.local/bin/aem stage auto prompt",
                  "cd cli && python3 -m aem approve shot x --gate G4", "aem new-client b --name B",
                  "aem guard < req.json"):
            self.assertDenied("AEM-G04", "Bash", command=c)
        self.assertAllowed("Bash", command="aem check-render renders/a.mp4")
        self.assertDenied("AEM-G04", "Bash", command="aem inbox accept comment:x#1 --ruling keep")
        self.assertDenied("AEM-G04", "Bash", command="aem inbox dismiss denial:3 --reason no")
        self.assertAllowed("Bash", command="aem inbox")

    def test_g04_holds_with_no_project_resolved(self):
        code, d = self.guard("Bash", cwd=str(self.w.tmp), command="aem approve x y --gate G4")
        self.assertEqual((code, d["rule"]), (1, "AEM-G04"))
        code, d = self.guard("Read", cwd=str(self.w.tmp), file_path="/Volumes/Other Client/secret.md")
        self.assertEqual((code, d["decision"]), (0, "allow"))

    # AEM-G05
    def test_placement_needs_standing_approval(self):
        r = self.w.project / "renders" / "shot_v01.mp4"
        r.write_bytes(b"one")
        cmd = f"python3 place.py --fcpxml out/placement.fcpxml '{r}'"
        d = self.assertDenied("AEM-G05", "Bash", command=cmd)
        self.assertIn("/approve shot", d["how"])
        self.w.run("approve", "shot", str(r), "--gate", "G4", check=True)
        self.assertAllowed("Bash", command=cmd)
        r.write_bytes(b"two")
        d = self.assertDenied("AEM-G05", "Bash", command=cmd)
        self.assertTrue(d["stale"])
        self.assertDenied("AEM-G05", "Bash", command=f"cp '{r}' '/tmp/Animations Done/x.mp4' # deliver")
        self.assertDenied("AEM-G05", "Bash", command="python3 place.py --out out/placement.fcpxml")  # names no render
        self.assertAllowed("Bash", command="grep -r placement docs/")

    def test_fcpxml_write_checks_media(self):
        r = self.w.project / "renders" / "shot_v01.mp4"
        r.write_bytes(b"one")
        content = f'<asset src="file://{r}"/>'
        self.assertDenied("AEM-G05", "Write", file_path=str(self.w.project / "out" / "p.fcpxml"), content=content)
        self.w.run("approve", "shot", str(r), "--gate", "G4", check=True)
        self.assertAllowed("Write", file_path=str(self.w.project / "out" / "p.fcpxml"), content=content)

    # overrides
    def test_one_time_allow_is_consumed_and_logged(self):
        self.w.run("allow", "snapshot --describe", "--reason", "need one look", "--once", check=True)
        d = self.assertAllowed("Bash", command="npx hyperframes snapshot --describe .")
        self.assertEqual(d["overridden"]["rule"], "AEM-G03")
        self.assertTrue(d["once"])
        self.assertDenied("AEM-G03", "Bash", command="npx hyperframes snapshot --describe .")
        events = [e["event"] for e in self.w.events()]
        self.assertIn("allow_used", events)
        self.assertEqual(events.count("denial"), 1)

    def test_rule_allow_and_standing_allow(self):
        self.w.run("allow", "AEM-G02", "--reason", "shared font", check=True)
        self.assertAllowed("Read", file_path="/Volumes/Fonts/x.otf")
        self.assertAllowed("Read", file_path="/Volumes/Fonts/y.otf")
        used = [e for e in self.w.events() if e["event"] == "allow_used"]
        self.assertEqual(len(used), 2)

    def test_denials_are_recorded(self):
        self.assertDenied("AEM-G01", "Write", file_path=str(self.w.project / "approvals.jsonl"), content="x")
        ev = self.w.events()[-1]
        self.assertEqual((ev["event"], ev["rule"], ev["tool"]), ("denial", "AEM-G01", "Write"))


class ApproveDefaults(WorldCase):
    def test_path_from_last_check_and_gate_from_stage(self):
        self.w.use()
        r = self.w.project / "renders" / "shot_v01.mp4"
        r.write_bytes(b"one")
        code, d = self.w.run("approve", "shot")
        self.assertEqual(code, 2)
        self.assertIn("none checked", d["error"])
        # A render_check event for the item, as aem check-render writes it.
        self.w.run("stage", "start", "G4", "shot", check=True)
        from aem import ledger, registry
        import argparse
        with self.w.environ():
            ledger.record(registry.context(argparse.Namespace(), cwd=self.w.project), "render_check", scene="shot",
                          render="renders/shot_v01.mp4", result="pass")
        _, d = self.w.run("approve", "shot", check=True)
        self.assertEqual((d["approval"]["gate"], d["approval"]["render"]), ("G4", "renders/shot_v01.mp4"))
