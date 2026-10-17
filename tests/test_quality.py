"""Judging quality, not only compliance: holds that freeze, the sound-off read, reference frames for the director's
review, loudness, the agent's own choices, and repair rounds that show what each re-render fixed or brought back."""
import json
import subprocess
import unittest

from helpers import HAVE_FFMPEG, WorldCase, make_video

APPEAR = "drawbox=x=40:y=40:w=120:h=60:color=white:t=fill:enable='gte(n,30)'"


def make_tone_video(path, *, seconds=2, volume=None):
    af = ["-af", f"volume={volume}"] if volume else []
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=0x202020:s=320x180:r=25",
                    "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000", "-t", str(seconds), *af,
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(path)], check=True)
    return path


@unittest.skipUnless(HAVE_FFMPEG, "ffmpeg and ffprobe are needed")
class Quality(WorldCase):
    fps = "25/1"
    fps_in = "settings"

    def setUp(self):
        super().setUp()
        self.w.use()
        self.r = self.w.project / "renders"

    def run_ok(self, *args, operator=False):
        code, d = self.w.run(*args, operator=operator)
        self.assertEqual(code, 0, d)
        return d

    def settings(self, **kw):
        path = self.w.project / "aem.project.json"
        cur = json.loads(path.read_text())
        cur.update(kw)
        path.write_text(json.dumps(cur))

    # --- holds ----------------------------------------------------------------------------------------

    def test_frozen_holds_are_listed_with_where_they_sit(self):
        make_video(self.r / "shot_v01.mp4", frames=60, box=APPEAR)  # 1.2 s frozen, a box appears, 1.2 s frozen
        d = self.run_ok("evidence", "renders/shot_v01.mp4")
        out = self.w.project / d["dir"]
        h = json.loads((out / "holds.json").read_text())
        self.assertEqual([(r["first"], r["last"], r["where"]) for r in h["runs"]], [(0, 29, "start"), (30, 59, "end")])
        self.assertEqual(len(h["over"]), 2)
        self.assertTrue(h["per_30s_over"])
        self.assertEqual(d["frozen_over"], 2)
        md = (out / "evidence.md").read_text()
        self.assertIn("## Holds and freezes", md)
        self.assertIn("Frozen 1.2 s, frames 0–29 (start)", md)
        self.assertEqual(d["toast"], "evidence ready: shot v01, no cue words, sync not measured, no flash")  # advice, not alarm

    def test_continuous_motion_never_freezes(self):
        make_video(self.r / "move_v01.mp4", frames=50, graph="testsrc2=s=320x180:r=25")
        d = self.run_ok("evidence", "renders/move_v01.mp4")
        h = json.loads((self.w.project / d["dir"] / "holds.json").read_text())
        self.assertEqual(h["over"], [])
        self.assertEqual(h["frozen_s"], 0)

    def test_the_hold_threshold_is_the_projects(self):
        self.settings(evidence={"max_still_s": 2.0})
        make_video(self.r / "shot_v02.mp4", frames=60, box=APPEAR)
        d = self.run_ok("evidence", "renders/shot_v02.mp4")
        self.assertEqual(d["frozen_over"], 0)

    # --- sound-off read and references ------------------------------------------------------------------

    def test_the_sound_off_reader_gets_the_sheet_and_nothing_else(self):
        make_video(self.r / "shot_v03.mp4", frames=60, box=APPEAR)
        d = self.run_ok("evidence", "renders/shot_v03.mp4")
        out = self.w.project / d["dir"]
        self.assertTrue((out / "sheet.jpg").is_file())
        retell = (out / "retell.md").read_text()
        self.assertIn("[sheet.jpg](sheet.jpg)", retell)
        self.assertIn("5 frames, one every 0.48 s", retell)  # 2.4 s at 2 a second, evenly
        for leak in ("Knows after", "Must stay true", "Teaching job", "evidence.md", "rule"):
            self.assertNotIn(leak, retell)
        md = (out / "evidence.md").read_text()
        self.assertIn("## Sound-off read", md)
        self.assertIn("give a fresh subagent [retell.md](retell.md)", md)
        self.assertIn('"retell_match"', md)

    def test_reference_frames_are_linked_when_the_project_has_them(self):
        make_video(self.r / "shot_v04.mp4", frames=30, box=APPEAR)
        d = self.run_ok("evidence", "renders/shot_v04.mp4")
        md = (self.w.project / d["dir"] / "evidence.md").read_text()
        self.assertIn("No reference frames found (references/*.png, references/*.jpg", md)
        ref = self.w.project / "references"
        ref.mkdir()
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=red:s=64x36", "-frames:v", "1",
                        str(ref / "kurzgesagt-hold.png")], check=True)
        d = self.run_ok("evidence", "renders/shot_v04.mp4")
        out = self.w.project / d["dir"]
        md = (out / "evidence.md").read_text()
        self.assertIn("[../../../references/kurzgesagt-hold.png](../../../references/kurzgesagt-hold.png)", md)
        self.assertTrue((out / "../../../references/kurzgesagt-hold.png").resolve().is_file())
        self.assertEqual(d["references"], 1)

    # --- loudness ---------------------------------------------------------------------------------------

    def test_a_silent_render_says_loudness_was_not_checked(self):
        make_video(self.r / "quiet_v01.mp4", frames=25)
        d = self.run_ok("check-render", "renders/quiet_v01.mp4")
        c = next(c for c in d["checks"] if c["check"] == "loudness")
        self.assertIsNone(c["ok"])
        self.assertIn("no audio stream", c["detail"])

    def test_loudness_is_measured_and_checked_against_the_target_when_one_is_set(self):
        make_tone_video(self.r / "tone_v01.mp4")
        d = self.run_ok("check-render", "renders/tone_v01.mp4")
        checks = {c["check"]: c for c in d["checks"]}
        self.assertIsNone(checks["loudness"]["ok"])  # measured, no target
        self.assertLess(d["loudness"]["integrated_lufs"], -14)
        self.assertTrue(checks["true peak"]["ok"])
        self.settings(loudness={"target_lufs": -14})
        code, d = self.w.run("check-render", "renders/tone_v01.mp4", operator=False)
        self.assertNotEqual(code, 0)
        self.assertIn("loudness", " ".join(d["failures"]))

    def test_a_hot_mix_fails_the_true_peak_ceiling(self):
        make_tone_video(self.r / "hot_v01.mp4", volume="8")
        code, d = self.w.run("check-render", "renders/hot_v01.mp4", operator=False)
        self.assertNotEqual(code, 0)
        self.assertFalse(next(c for c in d["checks"] if c["check"] == "true peak")["ok"])

    # --- choices ----------------------------------------------------------------------------------------

    def test_the_agent_records_its_own_choice_with_a_reason(self):
        d = self.run_ok("chose", "hold the chart 0.8 s before the count-up", "--why", "the axis reads before it moves",
                        "--moment", "shot", "--rule", "M-03", "--alt", "count up at once")
        c = d["choice"]
        self.assertEqual((c["event"], c["scene"], c["note"], c["why"], c["rule_ids"], c["source"]),
                         ("choice", "shot", "hold the chart 0.8 s before the count-up", "the axis reads before it moves",
                          ["M-03"], "aem chose"))
        self.assertEqual(self.w.events()[-1]["event"], "choice")
        self.assertEqual(self.run_ok("integrity")["findings"], 0)  # written by AEM, so tracked
        code, d = self.w.run("chose", "something", "--why", " ", operator=False)
        self.assertNotEqual(code, 0)
        self.assertIn("--why", d["error"])

    def test_the_session_context_tells_the_agent_about_choices_and_rounds(self):
        d = self.run_ok("context")
        self.assertIn("aem chose", d["text"])
        self.assertIn("aem rounds", d["text"])

    # --- repair rounds ----------------------------------------------------------------------------------

    def critic(self, version, rules, retell_match=None):
        out = self.w.project / "reviews" / "shot" / version
        (out / "critic.json").write_text(json.dumps({
            "verdict": "flag" if rules else "pass", "retell_match": retell_match,
            "findings": [{"rule": r, "image": "poses/f0000.png", "note": "x"} for r in rules]}))

    def test_rounds_show_what_each_version_fixed_kept_and_brought_back(self):
        for v, rules in (("v01", ["M-01", "M-02"]), ("v02", ["M-02"]), ("v03", ["M-01"])):
            make_video(self.r / f"shot_{v}.mp4", frames=30, box=APPEAR)
            self.run_ok("evidence", f"renders/shot_{v}.mp4")
            self.critic(v, rules, retell_match="partly" if v == "v03" else None)
        (self.w.project / "reviews" / "shot" / "v03" / "retell.json").write_text(json.dumps({"retell": "A box appears."}))
        self.run_ok("chose", "white box", "--why", "contrast on dark", "--moment", "shot")
        d = self.run_ok("rounds")
        rows = {r["version"]: r for r in d["moments"]["shot"]}
        self.assertEqual(rows["v01"]["new"], ["M-01", "M-02"])
        self.assertEqual((rows["v02"]["fixed"], rows["v02"]["kept"]), (["M-01"], ["M-02"]))
        self.assertEqual((rows["v03"]["fixed"], rows["v03"]["came_back"]), (["M-02"], ["M-01"]))
        self.assertEqual(rows["v03"]["retell_match"], "partly")
        md = (self.w.project / "reports" / "rounds.md").read_text()
        self.assertIn('Latest sound-off retell (v03): "A box appears."', md)
        self.assertIn("white box · why: contrast on dark", md)
        (self.w.project / "visual-plan.md").write_text(
            "# Visual plan\n\n| Moment | Treatment | Why |\n|---|---|---|\n| shot | animation | the box |\n")
        idx = self.run_ok("moments")
        shot = next(m for m in idx["moments"] if m["id"] == "shot")
        self.assertEqual(shot["choices"][0]["choice"], "white box")


if __name__ == "__main__":
    unittest.main()
