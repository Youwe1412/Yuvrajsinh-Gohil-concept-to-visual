"""aem rendered: which commands are renders, which files they wrote, and the checks and toast."""
import json
import os
import time
import unittest

from helpers import HAVE_FFMPEG, WorldCase, make_video

FLASH = "drawbox=x=100:y=60:w=80:h=60:color=white:t=fill:enable='eq(n,10)'"


@unittest.skipUnless(HAVE_FFMPEG, "ffmpeg and ffprobe are needed")
class Rendered(WorldCase):
    fps = "25/1"
    fps_in = "settings"

    def setUp(self):
        super().setUp()
        reg = json.loads(self.w.registry.read_text())
        reg["clients"][0]["render_sentinel"] = {"command_patterns": [r"(?:^|[\s;&|/])bin/r\.sh\b"]}
        self.w.registry.write_text(json.dumps(reg))
        self.w.use()
        self.w.run("stage", "start", "G4", check=True)  # a stage is open, so nothing is inferred (see the last test)
        self.renders = self.w.project / "renders"

    def rendered(self, command, started_at=None, **extra):
        req = {"command": command, "cwd": str(self.w.project),
               "started_at": time.time() - 1 if started_at is None else started_at, **extra}
        code, d = self.w.run("rendered", stdin=json.dumps(req))
        self.assertEqual(code, 0, d)
        return d

    def checks(self):
        return [e for e in self.w.events() if e["event"] == "render_check"]

    def test_not_a_render(self):
        make_video(self.renders / "a_v01.mp4", frames=20)
        d = self.rendered("ls renders")
        self.assertEqual((d["render"], d["outputs"]), (False, []))
        self.assertEqual(self.checks(), [])

    def test_probe_only_checks_nothing(self):
        make_video(self.renders / "a_v01.mp4", frames=20)
        d = self.rendered("npx hyperframes render . -o renders/a_v01.mp4", probe_only=True)
        self.assertTrue(d["render"])
        self.assertEqual((d["outputs"], self.checks()), ([], []))

    def test_output_flag_found_checked_and_recorded(self):
        old = make_video(self.renders / "old_v01.mp4", frames=20)
        os.utime(old, (time.time() - 3600, time.time() - 3600))
        start = time.time() - 1
        make_video(self.renders / "a_v01.mp4", frames=20)
        d = self.rendered("hyperframes render . -c compositions/a.html -o renders/a_v01.mp4", start)
        self.assertEqual([(o["path"], o["result"], o["scene"]) for o in d["outputs"]],
                         [("renders/a_v01.mp4", "pass", "a")])
        self.assertEqual(d["outputs"][0]["found_by"], "-o on the command line")
        self.assertEqual(d["toast"], "AEM render check PASS: a_v01.mp4")
        self.assertEqual([(e["scene"], e["result"]) for e in self.checks()], [("a", "pass")])

    def test_script_render_found_by_folder_and_flash_reported(self):
        start = time.time() - 1
        make_video(self.renders / "b_v02.mp4", frames=40, box=FLASH)
        d = self.rendered('bash bin/r.sh b "b_v02.mp4"', start)
        self.assertEqual(d["pattern"], r"(?:^|[\s;&|/])bin/r\.sh\b")
        o = d["outputs"][0]
        self.assertEqual((o["result"], o["flashes"][0]["frame"]), ("fail", 10))
        self.assertIn("changed in renders/", o["found_by"])
        self.assertEqual(d["toast"], "AEM render check FAIL: b_v02.mp4: flash at frame 10 (00:00:00:10), 1 frame(s)")
        self.assertIn("Fix the failures", d["text"])

    def test_batch_pattern_and_variable_names(self):
        start = time.time() - 1
        make_video(self.renders / "t-one_v01.mp4", frames=20)
        make_video(self.renders / "t-two_v01.mp4", frames=20)
        d = self.rendered('hyperframes render . --batch data/t.json -o "renders/t-{slug}_v01.mp4"', start)
        self.assertEqual(sorted(o["scene"] for o in d["outputs"]), ["t-one", "t-two"])
        self.assertEqual(d["toast"], "AEM render check: 2 passed, 0 failed")

    def test_rerender_makes_approval_stale(self):
        p = make_video(self.renders / "c_v01.mp4", frames=20)
        self.w.run("check-render", str(p), check=True)
        self.w.run("approve", "c", str(p), "--gate", "G4", check=True)
        start = time.time() - 1
        make_video(self.renders / "c_v01.mp4", frames=21)
        d = self.rendered("hyperframes render . -o renders/c_v01.mp4", start)
        self.assertEqual(d["stale"], 1)
        self.assertEqual(d["outputs"][0]["stale_marked"], 1)
        self.assertTrue(d["toast"].endswith("; 1 approval(s) now stale"), d["toast"])
        code, _ = self.w.run("check-approval", str(p))
        self.assertEqual(code, 1)

    def test_render_that_wrote_nothing(self):
        d = self.rendered("hyperframes render . -o renders/none.mp4", exit_code=1)
        self.assertEqual(d["outputs"], [])
        self.assertEqual(d["toast"], "AEM render check: no new render found (the command exited 1)")

    def test_output_outside_renders_by_absolute_path(self):
        start = time.time() - 1
        out = self.w.project / "exports" / "d_v01.mp4"
        out.parent.mkdir()
        make_video(out, frames=20)
        d = self.rendered(f"hyperframes render . -o '{out}'", start)
        self.assertEqual([o["path"] for o in d["outputs"]], ["exports/d_v01.mp4"])

    def test_a_render_with_no_stage_open_infers_the_render_gate(self):
        self.w.run("stage", "end", check=True)
        start = time.time() - 1
        make_video(self.renders / "e_v01.mp4", frames=20)
        d = self.rendered("hyperframes render . -o renders/e_v01.mp4", start)
        self.assertEqual((d["inferred"]["gate"], d["inferred"]["inferred_from"]), ("G4", "renders/e_v01.mp4"))
        self.assertEqual(d["toast"], "AEM render check PASS: e_v01.mp4 · G4 inferred (no stage was open)")
        self.assertEqual(self.checks()[-1]["gate"], "G4")  # the check is recorded at the inferred gate
        d = self.rendered("hyperframes render . -o renders/e_v01.mp4", start)  # a stage is open now: nothing more
        self.assertIsNone(d["inferred"])
