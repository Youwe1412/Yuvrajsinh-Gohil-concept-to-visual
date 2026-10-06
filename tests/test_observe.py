"""1.0.0: AEM observes and records, and never stands in the way. `aem observe` records every tool call with the
files it names; the one thing it ever asks about is a delivery of media with no current approval.

The P2 tests replay, with Joel's real registry entry, every call AEM denied in the P2 session of 6 October 2026:
each now runs with no interruption and is in the record as an observed event.
"""
import json
import unittest
from pathlib import Path

from helpers import JoelWorld, WorldCase

ZIP_CACHE = ("/var/folders/yh/753jqf190vv2h597rcd4025h0000gp/T/com.anthropic.claudefordesktop/zip_cache/"
             "5CFFB904-7324-464A-AB52-385F04447962-1155-000000295F95A5D4")
TOOL_RESULT = ("/Users/yuvrajdarbar/.claude/projects/-Volumes-T7-Red-Yuvraj-Folder-Freelance-Work-Joel-Belton---MergeToMaster"
               "-P2---Claude-Code/4eb68817-016b-4580-82c2-569461248219/tool-results/mcp-aavkar-cut-assist-studio_context"
               "-1791295257947.txt")


class Observe(WorldCase):
    """A world and an `observe` call as the plugin makes one: the agent's call, before it runs, from no terminal."""

    def setUp(self):
        super().setUp()
        self.w.use()

    def observe(self, tool, cwd=None, session="s1", **inp):
        req = {"tool": tool, "input": inp, "cwd": str(cwd or self.w.project), "session": session}
        code, d = self.w.run("observe", stdin=json.dumps(req), operator=False)
        self.assertEqual(code, 0, d)
        return d

    def observed(self):
        return [e for e in self.w.events() if e["event"] == "observed"]


class P2Session(Observe):
    """Every call AEM denied in the P2 session now runs with no interruption and is recorded."""

    def setUp(self):
        self.w = JoelWorld()
        fcpxml = self.w.project / "XML" / "P2 - Claude Code - New Rough Cut - Oct 5.fcpxml"
        fcpxml.write_text('<fcpxml><asset src="file:///Volumes/T7/RoughCut.mp4"/></fcpxml>')
        self.fcpxml = fcpxml
        ds = self.w.ds
        joel = "/Volumes/T7 Red/Yuvraj Folder/Freelance Work/Joel Belton - MergeToMaster"
        self.calls = [
            # reading the FCPXML
            ("Bash", {"command": f"cat '{fcpxml}'"}),
            ("Bash", {"command": "xmllint --xpath '//asset/@src' 'XML/P2 - Claude Code - New Rough Cut - Oct 5.fcpxml'"}),
            ("Bash", {"command": "python3 -c \"import xml.etree.ElementTree as ET; "
                                 "print(len(ET.parse('XML/P2 - Claude Code - New Rough Cut - Oct 5.fcpxml').getroot()))\""}),
            ("Read", {"file_path": str(fcpxml)}),
            # unzip -p of the rough cut's FCPXML bundle (AEM-G05, "names no render")
            ("Bash", {"command": f'unzip -p "{ZIP_CACHE}" "P2 - Claude Code - New Rough Cut - Oct 5.fcpxmld/Info.fcpxml"'}),
            # ~/Tools/fcp-edit-workflow with a trailing semicolon (AEM-G02)
            ("Bash", {"command": "which hyperframes whisper-cli mfa ffmpeg sox 2>&1; hyperframes --version 2>&1 | head -2; "
                                 "hyperframes models list 2>&1 | head -20; ls ~/Tools/fcp-edit-workflow 2>&1 | head; "
                                 "ls ~/Tools 2>&1; conda env list 2>&1 | head"}),
            # cd into a path ending in ";" (AEM-G02: `~/Tools/fcp-edit-workflow;` read as the path)
            ("Bash", {"command": 'cd ~/Tools/fcp-edit-workflow; head -5 fcp-workflow; ls -a | head -40; '
                                 'grep -iE "venv|python" README.md | head -15'}),
            # grep of joel-decisions.md and the rules (AEM-G01, a protected file named in a command)
            ("Bash", {"command": f'grep -n "grade" "{ds / "joel-decisions.md"}"'}),
            ("Bash", {"command": f"grep -c '^| J-' '{ds / 'rules.md'}' && head -20 '{ds / 'joel-decisions.md'}'"}),
            # the registry, and a tool result outside the client's folders (AEM-G01, AEM-G02)
            ("Bash", {"command": "which hyperframes whisper-cli mfa ffmpeg 2>&1; hyperframes --version 2>&1 | head -2; "
                                 "hyperframes models list 2>&1 | head -20; "
                                 'cat "/Users/yuvrajdarbar/Documents/Aavkar Educational Motion Studio/registry/clients.json"'}),
            ("Bash", {"command": f'F="{TOOL_RESULT}"; head -c 600 "$F"; echo; python3 - "$F" <<\'EOF\'\n'
                                 "import json,sys\nt=open(sys.argv[1]).read()\nprint(len(t))\nEOF"}),
            # the first call of the day, before the guard was fixed (AEM-G02, the P2 folder read as "P2 - Claude Code;")
            ("Bash", {"command": f'aem status 2>&1 | head -50; echo ---; ls -la "{joel}/P2 - Claude Code"; echo ---; '
                                 f'ls -la "{joel}"'}),
        ]

    def tearDown(self):
        self.w.cleanup()

    def test_each_runs_with_no_question_and_is_recorded_with_what_it_names(self):
        for tool, inp in self.calls:
            d = self.observe(tool, **inp)
            self.assertTrue(d["observed"], (tool, inp))
            self.assertIsNone(d["delivery"], (tool, inp))  # nothing to confirm: the plugin lets it run
        obs = self.observed()
        self.assertEqual(len(obs), len(self.calls))
        for (tool, inp), ev in zip(self.calls, obs):
            self.assertEqual(ev["tool"], tool)
            if tool == "Bash":
                self.assertEqual(ev["command"], inp["command"][:500])
        self.assertEqual(obs[3]["reads"], ["XML/P2 - Claude Code - New Rough Cut - Oct 5.fcpxml"])
        self.assertIn("~/Tools/fcp-edit-workflow", obs[5]["paths"])
        self.assertIn("~/Tools/fcp-edit-workflow", obs[6]["paths"])  # the folder, not the folder and a ";"
        self.assertIn(str(self.w.ds / "joel-decisions.md"), " ".join(obs[7]["paths"]))
        # Nothing of the old guard is left in the record.
        kinds = {e["event"] for e in self.w.events()}
        self.assertFalse(kinds & {"denial", "allowed_by_operator_prompt", "allow", "allow_used"}, kinds)

    def test_none_of_them_infers_a_stage_or_writes_a_record_file(self):
        for tool, inp in self.calls:
            self.observe(tool, **inp)
        self.assertEqual([e for e in self.w.events() if e["event"] != "observed"], [])
        self.assertFalse((self.w.project / "approvals.jsonl").exists())


class Recording(Observe):
    def test_read_write_and_edit_name_their_file(self):
        self.observe("Read", file_path=str(self.w.project / "brief.md"))
        self.observe("Write", file_path=str(self.w.project / "notes" / "a.md"), content="x")
        self.observe("Edit", file_path=str(self.w.project / "notes" / "a.md"), old_string="x", new_string="y")
        a, b, c = self.observed()
        self.assertEqual((a["tool"], a["reads"], b["writes"], c["writes"]),
                         ("Read", ["brief.md"], ["notes/a.md"], ["notes/a.md"]))
        self.assertEqual(a["session"], "s1")

    def test_a_shell_command_is_split_as_a_shell_splits_it(self):
        self.observe("Bash", command="cp renders/a.mp4 out/b.mp4 && ls ~/x;echo done > log.txt 2>&1 # a note")
        ev = self.observed()[-1]
        self.assertEqual(ev["writes"], ["out/b.mp4", "log.txt"])
        self.assertIn("renders/a.mp4", ev["paths"])
        self.assertIn("~/x", ev["paths"])
        self.assertNotIn("note", " ".join(ev["paths"]))

    def test_a_long_command_is_cut_and_says_how_long_it_was(self):
        self.observe("Bash", command="echo " + "x" * 900)
        ev = self.observed()[-1]
        self.assertEqual((len(ev["command"]), ev["command_chars"]), (500, 905))

    def test_no_project_resolved_records_nothing(self):
        d = self.observe("Bash", cwd=self.w.tmp, command="ls")
        self.assertEqual((d["observed"], d["delivery"]), (False, None))
        self.assertEqual(self.w.events(), [])

    def test_observe_is_open_to_the_agent(self):
        code, d = self.w.run("observe", stdin=json.dumps({"tool": "Bash", "input": {"command": "ls"},
                                                          "cwd": str(self.w.project)}), operator=False)
        self.assertEqual(code, 0)
        self.assertNotIn("operator_only", d)


class Delivery(Observe):
    """The one interruption: delivering media that has no current approval. AEM says so; the plugin asks."""

    def setUp(self):
        super().setUp()
        self.r = self.w.project / "renders" / "fd_S01_v01.mp4"
        self.r.write_bytes(b"render one")
        (self.w.project / "delivery").mkdir()

    def deliver(self, command="cp renders/fd_S01_v01.mp4 delivery/"):
        return self.observe("Bash", command=command)["delivery"]

    def test_an_unapproved_render_raises_the_question(self):
        d = self.deliver()
        self.assertEqual(d["kinds"], ["copy"])
        self.assertEqual(d["question"], "fd_S01 has no approval. Deliver anyway?")
        self.assertEqual(d["unapproved"][0]["state"], "none")
        self.assertEqual(d["slash"], ["/approve fd_S01 renders/fd_S01_v01.mp4 G6"])
        self.assertEqual(d["approve"], [["approve", "fd_S01", str(self.r), "--gate", "G6", "--delivery-confirmation"]])
        self.assertEqual(self.observed()[-1]["delivery"]["media"][0]["state"], "none")  # in the record too

    def test_an_approved_render_raises_nothing(self):
        self.w.run("approve", "fd_S01", "renders/fd_S01_v01.mp4", "--gate", "G4", check=True)
        d = self.deliver()
        self.assertEqual((d["unapproved"], d.get("question")), ([], None))
        self.assertEqual(d["media"][0]["state"], "approved")

    def test_a_render_changed_after_its_approval(self):
        self.w.run("approve", "fd_S01", "renders/fd_S01_v01.mp4", "--gate", "G4", check=True)
        self.r.write_bytes(b"render two")
        d = self.deliver()
        self.assertEqual(d["question"], "fd_S01 was re-rendered after you approved it. Deliver anyway?")
        self.assertEqual(d["unapproved"][0]["state"], "stale")

    def test_a_rejected_render(self):
        self.w.run("reject", "fd_S01", "--path", "renders/fd_S01_v01.mp4", "--reason", "late", check=True)
        self.assertEqual(self.deliver()["question"], "fd_S01 was rejected. Deliver anyway?")

    def test_several_renders_are_named_in_one_question(self):
        (self.w.project / "renders" / "fd_S02_v01.mp4").write_bytes(b"two")
        d = self.deliver("cp renders/fd_S01_v01.mp4 renders/fd_S02_v01.mp4 delivery/")
        self.assertEqual(d["question"], "fd_S01 has no approval; fd_S02 has no approval. Deliver anyway?")
        self.assertEqual(len(d["approve"]), 2)

    def test_an_fcpxml_that_names_the_media_is_a_delivery(self):
        for command in ("python3 place.py --fcpxml out/p.fcpxml renders/fd_S01_v01.mp4",
                        f"python3 - <<'EOF'\nopen('out/p.fcpxml','w').write('<asset src=\"file://{self.r}\"/>')\nEOF"):
            d = self.deliver(command)
            self.assertEqual((d["kinds"], d["unapproved"][0]["item"]), (["fcpxml"], "fd_S01"), command)
        d = self.observe("Write", file_path=str(self.w.project / "out" / "p.fcpxml"),
                         content=f'<fcpxml><asset src="file://{self.r}"/></fcpxml>')["delivery"]
        self.assertEqual(d["question"], "fd_S01 has no approval. Deliver anyway?")

    def test_reads_renders_and_copies_elsewhere_are_not_deliveries(self):
        for command in ("cat out/p.fcpxml", "ffprobe -v error renders/fd_S01_v01.mp4",
                        "aem check-approval renders/fd_S01_v01.mp4", "cp renders/fd_S01_v01.mp4 /tmp/look.mp4",
                        "hyperframes render . -o renders/fd_S01_v02.mp4", "python3 place.py --fcpxml out/p.fcpxml"):
            self.assertIsNone(self.deliver(command), command)

    def test_deliver_records_the_approval_as_made_through_the_confirmation(self):
        d = self.deliver()
        code, out = self.w.run(*d["approve"][0])  # what the plugin runs when Deliver is pressed, with its nonce
        self.assertEqual(code, 0, out)
        a = self.w.approvals()[-1]
        self.assertEqual((a["scene"], a["gate"], a["via"]), ("fd_S01", "G6", "delivery confirmation"))
        self.assertIn("Deliver pressed", a["note"])
        self.assertEqual(self.deliver()["unapproved"], [])  # the same delivery asks nothing now
        code, out = self.w.run(*d["approve"][0], operator=False)  # the agent cannot press Deliver itself
        self.assertEqual((code, out.get("operator_only")), (2, True))

    def test_what_became_of_a_delivery_is_recorded(self):
        for outcome, event in (("stopped", "delivery_stopped"), ("held", "delivery_held"),
                               ("unconfirmed", "delivery_unconfirmed")):
            req = {"tool": "Bash", "input": {"command": "cp renders/fd_S01_v01.mp4 delivery/"},
                   "cwd": str(self.w.project), "outcome": outcome, "note": "why"}
            code, d = self.w.run("observe", stdin=json.dumps(req), operator=False)
            self.assertEqual(code, 0, d)
            ev = self.w.events()[-1]
            self.assertEqual((ev["event"], ev["note"], ev["media"][0]["item"]), (event, "why", "fd_S01"))

    def test_joels_animations_done_folder_is_a_delivery_folder(self):
        w = JoelWorld()
        try:
            r = w.project / "renders" / "fd_S01_v01.mp4"
            r.write_bytes(b"x")
            req = {"tool": "Bash", "input": {"command": "cp renders/fd_S01_v01.mp4 '/Volumes/X/Animations Done/'"},
                   "cwd": str(w.project)}
            code, d = w.run("observe", stdin=json.dumps(req), operator=False)
            self.assertEqual(d["delivery"]["question"], "fd_S01 has no approval. Deliver anyway?")
            self.assertEqual(d["delivery"]["gate"], "G6")
        finally:
            w.cleanup()


class Inference(Observe):
    """No stage open when a plan file, a still, a scene source or a render changes: AEM opens the gate itself."""

    def inferred(self):
        return [e for e in self.w.events() if e["event"] == "stage_inferred"]

    def test_each_kind_of_file_infers_its_gate(self):
        cases = [("shotlist.md", "G2"), ("style-guide.md", "G2"), ("stills/s01.png", "G3"), ("src/scene.html", "G4"),
                 ("compositions/next-token.html", "G4"), ("renders/x_v01.mp4", "G4")]
        for rel, gate in cases:
            w = self.w
            self.observe("Write", file_path=str(w.project / rel), content="x")
            ev = self.inferred()[-1]
            self.assertEqual((ev["gate"], ev["inferred"], ev["inferred_from"]), (gate, True, rel), rel)
            self.assertEqual(self.observed()[-1]["gate"], gate)
            w.run("stage", "end", check=True)  # close it, so the next file infers again

    def test_other_files_and_reads_infer_nothing(self):
        self.observe("Write", file_path=str(self.w.project / "notes.md"), content="x")
        self.observe("Read", file_path=str(self.w.project / "shotlist.md"))
        self.observe("Bash", command="cat shotlist.md")
        self.assertEqual(self.inferred(), [])

    def test_a_shell_write_infers_too(self):
        self.observe("Bash", command="sed -i '' 's/a/b/' shotlist.md")
        self.assertEqual(self.inferred()[-1]["gate"], "G2")

    def test_nothing_is_inferred_while_a_stage_is_open(self):
        self.w.run("stage", "start", "G5", check=True)
        self.observe("Write", file_path=str(self.w.project / "shotlist.md"), content="x")
        self.assertEqual(self.inferred(), [])
        self.assertEqual(self.observed()[-1]["gate"], "G5")

    def test_the_status_line_says_inferred(self):
        self.observe("Write", file_path=str(self.w.project / "shotlist.md"), content="x")
        _, st = self.w.run("status", operator=False)
        self.assertIn("· G2 (inferred) ·", st["statusline"])
        self.assertTrue(st["statusline_parts"]["inferred"])
        _, ctx = self.w.run("context", operator=False)
        self.assertIn("inferred by AEM (shotlist.md changed while no stage was open)", ctx["text"])

    def test_the_operators_stage_ends_it(self):
        self.observe("Write", file_path=str(self.w.project / "shotlist.md"), content="x")
        self.w.run("stage", "start", "G4", "fd_S01", check=True)
        fin = [e for e in self.w.events() if e["event"] == "finish"]
        self.assertEqual((fin[-1]["gate"], fin[-1]["inferred"]), ("G2", True))
        self.assertIn("superseded by stage start G4 fd_S01", fin[-1]["note"])
        _, st = self.w.run("status", operator=False)
        self.assertEqual((st["stage"]["gate"], st["stage"]["inferred"]), ("G4", False))

    def test_the_operator_may_open_the_same_gate_the_aem_inferred(self):
        self.observe("Write", file_path=str(self.w.project / "shotlist.md"), content="x")
        code, d = self.w.run("stage", "start", "G2")
        self.assertEqual(code, 0, d)

    def test_the_session_end_ends_it_and_the_report_counts_and_lists_it(self):
        at = lambda t: {"AEM_FIXED_NOW": f"2026-10-06T{t}:00+05:30"}  # noqa: E731
        self.w.run("stage", "auto", "session_start", "--session", "s1", env=at("10:00"), check=True)
        req = {"tool": "Write", "input": {"file_path": str(self.w.project / "shotlist.md"), "content": "x"},
               "cwd": str(self.w.project), "session": "s1"}
        self.w.run("observe", stdin=json.dumps(req), operator=False, env=at("10:10"), check=True)
        self.w.run("stage", "auto", "session_end", "--session", "s1", env=at("11:10"), check=True)
        fin = [e for e in self.w.events() if e["event"] == "finish"][-1]
        self.assertEqual((fin["gate"], fin["inferred"], fin["ts"][11:16]), ("G2", True, "11:10"))
        _, r = self.w.run("report", env=at("12:00"), check=True)
        self.assertEqual(r["per_gate"]["G2"]["wall_s"], 3600)
        self.assertEqual(r["open_stages"], [])
        self.assertEqual(r["inferred_stages"][0]["gate"], "G2")
        md = (self.w.project / "reports" / "time.md").read_text()
        self.assertIn("## Inferred stages", md)
        self.assertIn("G2, a plan file changed: shotlist.md", md)


if __name__ == "__main__":
    unittest.main()
