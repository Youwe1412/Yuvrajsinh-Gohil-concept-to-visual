"""Every aem command through the real CLI, with --json, against a throwaway client."""
import json
import unittest
from pathlib import Path

from helpers import REPO, WorldCase


class UseStatus(WorldCase):
    def test_status_without_a_project(self):
        code, d = self.w.run("status", cwd=self.w.tmp)
        self.assertEqual(code, 0)
        self.assertFalse(d["active"])
        self.assertEqual(d["message"], "no project resolved")
        self.assertEqual(d["resolution"]["source"], "none")

    def test_use_checks_and_writes_a_labelled_hint_not_state(self):
        _, d = self.w.use()
        self.assertEqual(d["project"], "P1")
        self.assertEqual((d["fps"]["num"], d["fps"]["den"]), (24000, 1001))
        hint = json.loads((self.w.home / "active.json").read_text())
        self.assertEqual((hint["client"], hint["project"]), ("acme", "P1"))
        self.assertIn("Last-used hint only", hint["_comment"])
        # Nothing that a command could trust: no registry path, no frame rate.
        self.assertEqual(set(hint) - {"_comment"}, {"client", "project", "project_dir", "set_at"})

    def test_use_has_no_path_or_fps_override(self):
        # A project is its registered folder; its frame rate is what the folder states.
        for extra in (["--fps", "25/1"], ["--path", str(self.w.tmp)]):
            p = self.w.run_raw("use", "acme/P1", *extra)
            self.assertEqual(p.returncode, 2)
            self.assertIn("unrecognized arguments", p.stderr)

    def test_use_unknown(self):
        code, d = self.w.run("use", "nobody/P1")
        self.assertEqual(code, 2)
        self.assertIn("unknown client", d["error"])
        code, d = self.w.run("use", "acme/P9")
        self.assertEqual(code, 2)

    def test_use_clear_as_the_plugin_sends_it(self):
        # Regression (6 Oct 2026): `/aem use --clear` reaches the CLI as `aem use "" --clear`.
        self.w.use()
        self.assertTrue((self.w.home / "active.json").exists())
        _, d = self.w.run("use", "", "--clear", check=True)
        self.assertEqual((d["cleared"], d["was"]["client"]), (True, "acme"))
        self.assertFalse((self.w.home / "active.json").exists())

    def test_use_without_fps_refuses(self):
        (self.w.project / "frame.md").unlink()
        code, d = self.w.run("use", "acme/P1")
        self.assertEqual(code, 2)
        self.assertIn("no frame rate", d["error"])

    def test_status_fields(self):
        self.w.run("stage", "start", "G1", check=True)
        _, d = self.w.run("status", check=True)
        self.assertTrue(d["active"])
        self.assertEqual(d["stage"]["gate"], "G1")
        self.assertTrue(d["statusline"].startswith("AEM · Acme Learning · P1 · G1 · 0:00:"))
        self.assertEqual(d["idle_minutes"], 10)


class Stage(WorldCase):
    def setUp(self):
        super().setUp()
        self.w.use()

    def test_lifecycle_and_format(self):
        self.w.run("stage", "start", "g2", "--note", "plan", check=True)
        self.w.run("stage", "wait", "Ada", check=True)
        self.w.run("stage", "resume", check=True)
        self.w.run("stage", "pause", check=True)
        self.w.run("stage", "resume", check=True)
        self.w.run("stage", "end", check=True)
        ev = self.w.events()
        self.assertEqual([e["event"] for e in ev], ["start", "waiting_on_ada", "resume", "pause", "resume", "finish"])
        for e in ev:
            self.assertEqual(list(e)[:5], ["ts", "gate", "scene", "event", "note"])  # the skill's fields first
            self.assertEqual(e["gate"], "G2")
            self.assertIsNone(e["scene"])
            self.assertRegex(e["ts"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d$")

    def test_scene_stage_and_auto(self):
        self.w.run("stage", "start", "G4", "fd_S01_next-token", check=True)
        self.w.run("stage", "auto", "tool_call", "--tool", "Bash", "--duration-s", "42.5", "--session", "s1", check=True)
        ev = self.w.events()[-1]
        self.assertEqual((ev["event"], ev["gate"], ev["scene"], ev["tool"], ev["duration_s"], ev["session"]),
                         ("tool_call", "G4", "fd_S01_next-token", "Bash", 42.5, "s1"))
        self.assertEqual(ev["source"], "aem auto")

    def test_errors(self):
        self.assertEqual(self.w.run("stage", "start", "G9")[0], 2)
        self.assertEqual(self.w.run("stage", "end")[0], 2)
        self.assertEqual(self.w.run("stage", "pause")[0], 2)
        self.w.run("stage", "start", "G1", check=True)
        self.assertEqual(self.w.run("stage", "start", "G1")[0], 2)
        self.assertEqual(self.w.run("stage", "auto", "bogus")[0], 2)
        self.assertEqual(self.w.run("stage", "resume")[0], 2)

    def test_backfill_is_marked(self):
        self.w.run("stage", "start", "G1", "--at", "2026-10-06T09:00:00+05:30", check=True)
        self.assertTrue(self.w.events()[-1]["backfilled"])


class Report(WorldCase):
    def setUp(self):
        super().setUp()
        self.w.use()

    def at(self, *args, t):
        return self.w.run("stage", *args, "--at", f"2026-10-06T{t}:00+05:30", check=True)

    def test_categories_are_measured(self):
        self.at("auto", "session_start", "--session", "s1", t="10:00")
        self.at("start", "G1", t="10:00")
        self.at("auto", "prompt", t="10:01")
        self.at("auto", "turn_start", t="10:01")
        self.at("auto", "turn_end", t="10:05")
        self.at("auto", "idle_start", t="10:20")
        self.at("auto", "idle_end", t="10:40")
        self.at("wait", "acme", t="10:45")
        self.at("end", t="11:00")
        self.at("start", "G2", "scene-a", t="11:00")
        self.at("wait", "yuvraj", t="11:10")
        self.at("resume", t="11:20")
        self.at("end", "G2", "scene-a", t="11:30")
        self.at("auto", "session_end", t="11:30")
        self.at("start", "G3", t="12:00")  # no session: unobserved
        self.at("end", t="12:30")
        _, r = self.w.run("report", env={"AEM_FIXED_NOW": "2026-10-06T13:00:00+05:30"}, check=True)
        g1 = r["per_gate"]["G1"]
        self.assertEqual(g1["wall_s"], 3600)
        self.assertEqual(g1["agent_busy_s"], 240)
        self.assertEqual(g1["idle_s"], 1200)
        self.assertEqual(g1["waiting_on_client_s"], 900)
        self.assertEqual(g1["attended_between_turns_s"], 3600 - 240 - 1200 - 900)
        self.assertEqual(g1["unobserved_s"], 0)
        g2 = r["per_gate"]["G2"]
        self.assertEqual((g2["wall_s"], g2["waiting_on_others_s"], g2["waiting_on_client_s"]), (1800, 600, 0))
        self.assertEqual(r["per_scene"]["scene-a"]["wall_s"], 1800)
        g3 = r["per_gate"]["G3"]
        self.assertEqual((g3["wall_s"], g3["unobserved_s"], g3["idle_s"]), (1800, 1800, 0))
        self.assertEqual(r["backfilled_events"], 16)
        md = (self.w.project / "reports" / "time.md").read_text()
        self.assertIn("| G1 | 1:00:00 | 0:04:00 | 0:20:00 | 0:15:00 |", md)
        self.assertIn("nothing here is estimated", md)
        self.assertIn("backfilled", md)

    def test_open_stage_listed(self):
        self.at("start", "G4", t="10:00")
        _, r = self.w.run("report", env={"AEM_FIXED_NOW": "2026-10-06T10:30:00+05:30"}, check=True)
        self.assertEqual(r["open_stages"], ["G4 · (whole video)"])
        self.assertEqual(r["per_gate"]["G4"]["wall_s"], 1800)

    def test_report_other_project_flag(self):
        self.at("start", "G1", t="10:00")
        _, r = self.w.run("report", "--client", "acme", "--project", "P1", "--registry", str(self.w.registry),
                          "--no-write", env={"AEM_FIXED_NOW": "2026-10-06T10:10:00+05:30"}, check=True)
        self.assertEqual(r["per_gate"]["G1"]["wall_s"], 600)
        self.assertFalse((self.w.project / "reports" / "time.md").exists())


class ApproveReject(WorldCase):
    def setUp(self):
        super().setUp()
        self.w.use()
        self.render = self.w.project / "renders" / "shot_v01.mp4"
        self.render.write_bytes(b"render one")

    def test_approve_format_and_check(self):
        self.w.run("stage", "start", "G4", "shot", check=True)
        code, d = self.w.run("approve", "shot", "renders/shot_v01.mp4", "--gate", "G4")
        self.assertEqual(code, 0)
        a = self.w.approvals()[-1]
        self.assertEqual(list(a)[:7], ["gate", "scene", "render", "render_sha256", "source_revision", "approver", "date"])
        self.assertEqual((a["gate"], a["scene"], a["render"], a["approver"]), ("G4", "shot", "renders/shot_v01.mp4", "Yuvraj"))
        self.assertEqual(len(a["render_sha256"]), 64)
        code, d = self.w.run("check-approval", str(self.render))
        self.assertEqual(code, 0, d)
        self.assertTrue(d["ok"])

    def test_missing_approval(self):
        code, d = self.w.run("check-approval", "renders/shot_v01.mp4")
        self.assertEqual(code, 1)
        self.assertFalse(d["ok"])
        self.assertIn("no approval", d["reason"])
        self.assertIn("/approve", d["how_to_fix"])

    def test_changed_file_is_stale_even_without_render_check(self):
        self.w.run("approve", "shot", "renders/shot_v01.mp4", "--gate", "G4", check=True)
        self.render.write_bytes(b"render two")
        code, d = self.w.run("check-approval", "renders/shot_v01.mp4")
        self.assertEqual(code, 1)
        self.assertTrue(d["stale"])
        self.assertIn("stale", d["reason"])

    def test_rejection_withdraws(self):
        self.w.run("approve", "shot", "renders/shot_v01.mp4", "--gate", "G4", check=True)
        code, d = self.w.run("reject", "shot", "--reason", "caption repeats the demo")
        self.assertEqual(code, 0)
        self.assertEqual(self.w.approvals()[-1]["type"], "rejection")
        code, d = self.w.run("check-approval", "renders/shot_v01.mp4")
        self.assertEqual(code, 1)
        self.assertIn("rejected", d["reason"])
        self.assertEqual(self.w.run("reject", "shot", "--reason", "  ")[0], 2)

    def test_reapprove_after_rejection(self):
        self.w.run("approve", "shot", "renders/shot_v01.mp4", "--gate", "G4", check=True)
        self.w.run("reject", "shot", "--reason", "no", check=True)
        self.w.run("approve", "shot", "renders/shot_v01.mp4", "--gate", "G4", check=True)
        self.assertEqual(self.w.run("check-approval", "renders/shot_v01.mp4")[0], 0)

    def test_source_revision_from_scene_source(self):
        (self.w.project / "compositions" / "shot.html").write_text("<div data-duration=\"2\"></div>")
        _, d = self.w.run("approve", "shot", "renders/shot_v01.mp4", "--gate", "G4", check=True)
        self.assertTrue(d["approval"]["source_revision"].startswith("sha256:"))


class ClientSaid(WorldCase):
    def setUp(self):
        super().setUp()
        self.w.use()

    def test_verbatim_newest_first(self):
        before = (self.w.ds / "acme-decisions.md").read_text()
        quote = 'Could you leave the colour grade as is?\nIt\'s "a bit more natural" — thanks |pipes| *stars*'
        code, d = self.w.run("client-said", "--scope", "video", "--source", "Frame.io", stdin=quote + "\n")
        self.assertEqual(code, 0, d)
        after = (self.w.ds / "acme-decisions.md").read_text()
        self.assertIn("> Could you leave the colour grade as is?\n> It's \"a bit more natural\" — thanks |pipes| *stars*", after)
        self.assertIn("entered by Yuvraj", after)
        self.assertLess(after.index("Frame.io"), after.index("## 2026-09-01"))
        # Every earlier line is still there, in order.
        new_block_start = after.index("\n## ") + 1
        new_block_end = after.index("## 2026-09-01")
        rebuilt = after[:new_block_start].rstrip("\n") + "\n\n" + after[new_block_end:]
        self.assertEqual(rebuilt, before)
        ev = self.w.events()[-1]
        self.assertEqual(ev["event"], "client_said")
        self.assertEqual(len(ev["quote_sha256"]), 64)

    def test_empty_and_scope(self):
        self.assertEqual(self.w.run("client-said", "--scope", "video", "--source", "x", stdin="  \n")[0], 2)
        self.assertEqual(self.w.run("client-said", "--scope", "instance", "--source", "x", stdin="hi")[0], 2)
        code, _ = self.w.run("client-said", "--scope", "instance", "--item", "shot", "--source", "x", stdin="hi")
        self.assertEqual(code, 0)


class Allow(WorldCase):
    def setUp(self):
        super().setUp()
        self.w.use()

    def test_once_standing_list_revoke(self):
        _, a = self.w.run("allow", "snapshot --describe", "--reason", "one look", "--once", check=True)
        _, b = self.w.run("allow", "AEM-G02", "--reason", "read a shared asset", check=True)
        _, l = self.w.run("allow", "--list", check=True)
        self.assertEqual({x["allow_id"] for x in l["allows"]}, {a["allow_id"], b["allow_id"]})
        from aem import clients, registry
        import argparse
        with self.w.environ():
            ctx = registry.context(argparse.Namespace(), cwd=self.w.project)
            clients.consume_allow(ctx, a["allow_id"], subject="hyperframes snapshot --describe")
        _, l = self.w.run("allow", "--list", check=True)
        self.assertEqual([x["allow_id"] for x in l["allows"]], [b["allow_id"]])
        self.w.run("allow", "--revoke", b["allow_id"], check=True)
        _, l = self.w.run("allow", "--list", check=True)
        self.assertEqual(l["allows"], [])
        self.assertEqual(self.w.run("allow", "x")[0], 2)  # no reason


class Drift(WorldCase):
    def setUp(self):
        super().setUp()
        self.w.use()

    def run_drift(self):
        return self.w.run("drift", "--skills-dir", str(self.w.skills))

    def test_clean(self):
        code, d = self.run_drift()
        self.assertEqual(code, 0, d)
        self.assertTrue(d["ok"])

    def test_text_export_stale(self):
        (self.w.ds / "Acme - Motion System.html").write_text("<html>changed</html>")
        code, d = self.run_drift()
        self.assertEqual(code, 1)
        self.assertEqual(d["findings"][0]["check"], "text-export")

    def test_skill_differs(self):
        (self.w.skills / "acme-studio" / "SKILL.md").write_text("# edited installed copy\n")
        code, d = self.run_drift()
        self.assertEqual(code, 1)
        self.assertTrue(any(f["check"] == "skill" for f in d["findings"]))

    def test_unknown_rule_id(self):
        p = self.w.ds / "Skill" / "acme-studio" / "SKILL.md"
        p.write_text(p.read_text() + "Also M-99.\n")
        (self.w.skills / "acme-studio" / "SKILL.md").write_text(p.read_text())
        code, d = self.run_drift()
        self.assertEqual(code, 1)
        self.assertEqual([f["rule_id"] for f in d["findings"] if f["check"] == "rule-ids"], ["M-99"])


class NewClient(WorldCase):
    def test_scaffold_and_register(self):
        ds = self.w.tmp / "Beta" / "00 - Beta Design System"
        code, d = self.w.run("new-client", "beta", "--name", "Beta Academy", "--design-system", str(ds),
                             "--projects-root", str(self.w.tmp / "Beta"), "--contact", "Bo", "--registry", str(self.w.registry))
        self.assertEqual(code, 0, d)
        for f in ("README.md", "rules.md", "beta-decisions.md", "text/README.md", "critic/labelled-cases.jsonl"):
            self.assertTrue((ds / f).exists(), f)
        self.assertNotIn("{{", (ds / "beta-decisions.md").read_text())
        hdr = json.loads((ds / "critic" / "labelled-cases.jsonl").read_text().splitlines()[0])
        self.assertIn("client_words", hdr["fields"])
        reg = json.loads(self.w.registry.read_text())
        entry = [c for c in reg["clients"] if c["id"] == "beta"][0]
        self.assertEqual(entry["decisions_file"], "beta-decisions.md")
        self.assertEqual(entry["protected_files"]["design_system"][0], "beta-decisions.md")
        self.assertEqual(self.w.run("new-client", "beta", "--name", "B", "--design-system", str(self.w.tmp / "x"),
                                    "--projects-root", str(self.w.tmp), "--registry", str(self.w.registry))[0], 2)
        self.assertEqual(self.w.run("new-client", "gamma", "--name", "G", "--design-system", str(ds),
                                    "--projects-root", str(self.w.tmp), "--registry", str(self.w.registry))[0], 2)
        self.assertEqual(self.w.run("new-client", "Bad Id", "--name", "G", "--design-system", str(self.w.tmp / "y"),
                                    "--projects-root", str(self.w.tmp), "--registry", str(self.w.registry))[0], 2)


class RealRegistry(unittest.TestCase):
    """The shipped registry parses and Joel's entry carries every field the CLI and mods read."""

    def test_joel_entry(self):
        from aem import registry
        reg = registry.load_registry(REPO / "registry" / "clients.json")
        joel = registry.find_client(reg, "joel")
        self.assertEqual(joel.name, "MergeToMaster")
        self.assertEqual(joel.raw["decisions_file"], "joel-decisions.md")
        self.assertEqual(joel.skill, "mergetomaster-studio")
        self.assertEqual(joel.idle_minutes, 10)
        self.assertIn("snapshot --describe", joel.blocked_commands)
        self.assertEqual(joel.raw["review_inbox"]["service"], "Frame.io")
        # P2 is registered in the same shape as P1: a folder under the projects root, and a note.
        for name, folder in (("P1", "P1 - Frontend Design/Animations using Hyperframes/MergeToMaster"), ("P2", "P2 - Claude Code")):
            self.assertEqual(set(joel.raw["projects"][name]), {"dir", "note"})
            self.assertEqual(joel.raw["projects"][name]["dir"], folder)
        self.assertTrue(joel.raw["audio_libraries"])
        self.assertEqual(str(joel.projects_root), str(joel.design_system.parent))
        template = json.loads((REPO / "registry" / "client-template" / "client.json").read_text())
        self.assertLessEqual(set(template) - {"projects"}, set(joel.raw) | {"projects"})


class JsonEverywhere(WorldCase):
    def test_every_command_prints_json(self):
        self.w.use()
        (self.w.project / "renders" / "a.mp4").write_bytes(b"x")
        cmds = [
            ("status",), ("stage", "start", "G1"), ("report", "--no-write"),
            ("approve", "a", "renders/a.mp4", "--gate", "G4"), ("reject", "a", "--reason", "r"),
            ("allow", "--list",), ("check-approval", "renders/a.mp4"), ("drift", "--skills-dir", str(self.w.skills)),
        ]
        for c in cmds:
            code, d = self.w.run(*c)
            self.assertIn("ok", d, c)


if __name__ == "__main__":
    unittest.main()


class ContextText(WorldCase):
    def test_inactive(self):
        code, d = self.w.run("context", cwd=self.w.tmp)
        self.assertEqual(code, 0)
        self.assertFalse(d["active"])
        self.assertIn("/aem use", d["text"])

    def test_active_section(self):
        self.w.use()
        self.w.run("stage", "start", "G2", check=True)
        _, d = self.w.run("context", check=True)
        t = d["text"]
        self.assertIn("Client: Acme Learning (id `acme`, contact Ada)", t)
        self.assertIn("Gate: G2 (Plan)", t)
        self.assertIn("Frame rate: 24000/1001 (from frame.md)", t)
        self.assertIn(str(self.w.ds / "acme-decisions.md"), t)
        self.assertIn("Skill: use `acme-studio`", t)
        self.assertIn(str(self.w.project / "approvals.jsonl"), t)
        self.assertEqual([p["id"] for p in d["preferences"]], ["A-01", "A-02"])
        self.assertIn("Do not write events.jsonl, approvals.jsonl", t)
        self.assertIn("`aem approve`", t)
        # 0.9.0: the operator decides; the agent runs an operator command only when the latest message asks for it.
        self.assertIn("only when the operator's latest message asks for that action", t)
        self.assertIn("An earlier message is never standing permission", t)
        self.assertIn("record what Ada said", t)

    def test_status_parts(self):
        self.w.use()
        self.w.run("stage", "start", "G4", "shot", check=True)
        _, d = self.w.run("status", check=True)
        p = d["statusline_parts"]
        self.assertEqual((p["client"], p["project"], p["gate"], p["scene"], p["stale"]), ("Acme Learning", "P1", "G4", "shot", 0))


class LedgerPhase3(WorldCase):
    def setUp(self):
        super().setUp()
        self.w.use()

    def at(self, *args, t):
        return self.w.run("stage", *args, "--at", f"2026-10-06T{t}:00+05:30", check=True)

    def test_switch_finishes_same_scene_stage(self):
        self.w.run("stage", "start", "G1", check=True)
        self.w.run("stage", "start", "G4", "shot-a", check=True)
        _, d = self.w.run("stage", "start", "G2", "--switch", check=True)
        self.assertEqual((d["closed"]["event"], d["closed"]["gate"], d["closed"]["scene"]), ("finish", "G1", None))
        _, st = self.w.run("status", check=True)
        self.assertEqual(st["stage"]["gate"], "G2")
        # The scene stage was not touched.
        self.assertEqual([e["event"] for e in self.w.events() if e["scene"] == "shot-a"], ["start"])
        _, d = self.w.run("stage", "start", "G5", "shot-a", "--switch", check=True)
        self.assertEqual((d["closed"]["gate"], d["closed"]["scene"]), ("G4", "shot-a"))
        _, d = self.w.run("stage", "start", "G6", "shot-b", "--switch", check=True)
        self.assertNotIn("closed", d)

    def test_idle_measured_from_last_activity(self):
        self.at("auto", "session_start", "--session", "s1", t="10:00")
        self.at("start", "G1", t="10:00")
        self.at("auto", "prompt", "--origin", "composer", t="10:02")
        self.at("auto", "turn_start", "--turn", "t1", t="10:02")
        self.at("auto", "turn_end", "--turn", "t1", t="10:05")
        # Noticed at 10:15 (idle_minutes after the last activity at 10:05), measured from 10:05.
        self.at("auto", "idle_start", "--since", "2026-10-06T10:05:00+05:30", t="10:15")
        self.at("auto", "idle_end", t="10:40")
        self.at("end", t="11:00")
        self.at("auto", "session_end", t="11:00")
        _, r = self.w.run("report", env={"AEM_FIXED_NOW": "2026-10-06T11:00:00+05:30"}, check=True)
        g1 = r["per_gate"]["G1"]
        self.assertEqual((g1["wall_s"], g1["agent_busy_s"], g1["idle_s"]), (3600, 180, 2100))
        self.assertEqual(g1["attended_between_turns_s"], 3600 - 180 - 2100)
        ev = [e for e in self.w.events() if e["event"] == "prompt"][0]
        self.assertEqual(ev["origin"], "composer")
