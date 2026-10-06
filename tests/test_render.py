"""check-render: probe against the spec, the one- and two-frame flash scan, hashing, stale approvals."""
import json
import unittest

from helpers import HAVE_FFMPEG, WorldCase, make_video

BOX = "drawbox=x=100:y=60:w=80:h=60:color=white:t=fill:enable='{expr}'"


@unittest.skipUnless(HAVE_FFMPEG, "ffmpeg and ffprobe are needed")
class FlashScan(WorldCase):
    fps = "25/1"
    fps_in = "settings"

    def setUp(self):
        super().setUp()
        self.w.use()

    def check(self, name, **kw):
        path = make_video(self.w.project / "renders" / f"{name}.mp4", **kw)
        code, d = self.w.run("check-render", str(path), "--no-record")
        return code, d

    def test_clean_clip_passes(self):
        code, d = self.check("clean", frames=40)
        self.assertEqual(code, 0, d)
        self.assertEqual(d["flashes"], [])
        self.assertEqual(d["probe"]["frames"], 40)
        self.assertEqual(d["flash_scan"]["frames_scanned"], 40)

    def test_one_frame_flash(self):
        code, d = self.check("one", frames=40, box=BOX.format(expr="eq(n,10)"))
        self.assertEqual(code, 1)
        self.assertEqual([(f["frame"], f["length"]) for f in d["flashes"]], [(10, 1)])
        self.assertEqual(d["flashes"][0]["timecode"], "00:00:00:10")
        self.assertEqual(d["flashes"][0]["severity"], "fail")

    def test_two_frame_flash(self):
        code, d = self.check("two", frames=40, box=BOX.format(expr="between(n,20,21)"))
        self.assertEqual(code, 1)
        self.assertEqual([(f["frame"], f["length"]) for f in d["flashes"]], [(20, 2)])

    def test_three_frames_is_not_a_flash(self):
        code, d = self.check("three", frames=40, box=BOX.format(expr="between(n,20,22)"))
        self.assertEqual(code, 0, d)

    def test_fast_motion_is_not_a_flash(self):
        # A 50 px box crossing the frame at 30 px per frame (9% of the width per frame; 360 px at 4K).
        graph = ("color=c=0x202020:s=320x180:r=25[bg];color=c=white:s=50x50:r=25[fg];"
                 "[bg][fg]overlay=x='t*750':y=60:shortest=1")
        code, d = self.check("motion", frames=9, graph=graph)
        self.assertEqual(code, 0, d["flashes"])
        self.assertEqual(d["flash_scan"]["frames_scanned"], 9)

    def test_teleporting_object_is_reported(self):
        # Stated limit: an object that jumps further than about 12% of the frame width in one frame
        # is reported at the place it left, because nothing near it carries on.
        graph = ("color=c=0x202020:s=320x180:r=25[bg];color=c=white:s=50x50:r=25[fg];"
                 "[bg][fg]overlay=x='t*1750-260*floor(t*1750/260)':y=60:shortest=1")
        code, d = self.check("teleport", frames=12, graph=graph)
        self.assertEqual(code, 1)

    def test_hard_cut_is_not_a_flash(self):
        code, d = self.check("cut", frames=40, box="drawbox=x=0:y=0:w=320:h=180:color=white:t=fill:enable='gte(n,15)'")
        self.assertEqual(code, 0, d["flashes"])

    def test_full_frame_one_frame_cut(self):
        # Joel's P1 case: a different picture for exactly one frame.
        code, d = self.check("fullflash", frames=40, box="drawbox=x=0:y=0:w=320:h=180:color=0xF0E0C0:t=fill:enable='eq(n,2)'")
        self.assertEqual(code, 1)
        self.assertEqual(d["flashes"][0]["frame"], 2)
        self.assertEqual(d["flashes"][0]["area_pct"], 100.0)

    def test_small_flash_is_minor(self):
        (self.w.project / "aem.project.json").write_text(json.dumps({"fps": "25/1", "flash": {"min_area_pct": 5}}))
        code, d = self.check("small", frames=40, box="drawbox=x=10:y=10:w=12:h=12:color=white:t=fill:enable='eq(n,10)'")
        self.assertEqual(code, 0, d)
        self.assertEqual(d["flashes"][0]["severity"], "minor")


@unittest.skipUnless(HAVE_FFMPEG, "ffmpeg and ffprobe are needed")
class Spec(WorldCase):
    fps = "24000/1001"

    def setUp(self):
        super().setUp()
        (self.w.project / "aem.project.json").write_text(json.dumps({"render": {"width": 320, "height": 180, "alpha": False}}))
        self.w.use()

    def test_frame_count_from_composition_duration(self):
        # 2.002 s at 24000/1001 is 48 frames exactly.
        (self.w.project / "compositions" / "next-token.html").write_text('<div data-duration="2.002"></div>')
        make_video(self.w.project / "renders" / "fd_S01_next-token_v01.mp4", frames=48, fps="24000/1001")
        code, d = self.w.run("check-render", "renders/fd_S01_next-token_v01.mp4", "--no-record")
        self.assertEqual(code, 0, d)
        checks = {c["check"]: c for c in d["checks"]}
        self.assertTrue(checks["frame count"]["ok"])
        self.assertIn("data-duration", checks["frame count"]["detail"])
        self.assertTrue(checks["fps"]["ok"])
        self.assertEqual(d["scene"], "fd_S01_next-token")

    def test_wrong_fps_size_and_count(self):
        (self.w.project / "compositions" / "shot.html").write_text('<div data-duration="2.002"></div>')
        make_video(self.w.project / "renders" / "shot_v01.mp4", frames=50, fps="25", size="640x360")
        code, d = self.w.run("check-render", "renders/shot_v01.mp4", "--no-record")
        self.assertEqual(code, 1)
        failed = {c["check"] for c in d["checks"] if c["ok"] is False}
        self.assertEqual(failed, {"width", "height", "fps", "frame count"})

    def test_alpha_expected(self):
        (self.w.project / "aem.project.json").write_text(json.dumps({"render": {"width": 320, "height": 180, "alpha_extensions": [".mov"]}}))
        make_video(self.w.project / "renders" / "ov_v01.mov", frames=24, fps="24000/1001", codec="prores_ks", pix_fmt="yuv422p10le")
        code, d = self.w.run("check-render", "renders/ov_v01.mov", "--no-record")
        self.assertEqual(code, 1)
        alpha = [c for c in d["checks"] if c["check"] == "alpha"][0]
        self.assertEqual((alpha["expected"], alpha["actual"]), (True, False))


@unittest.skipUnless(HAVE_FFMPEG, "ffmpeg and ffprobe are needed")
class StaleApprovals(WorldCase):
    fps = "25/1"
    fps_in = "settings"

    def setUp(self):
        super().setUp()
        self.w.use()
        self.path = self.w.project / "renders" / "scene_v01.mp4"

    def test_rerender_marks_old_approval_stale(self):
        self.w.run("stage", "start", "G4", "scene", check=True)
        make_video(self.path, frames=30)
        code, first = self.w.run("check-render", "renders/scene_v01.mp4")
        self.assertEqual(code, 0, first)
        ev = self.w.events()[-1]
        self.assertEqual((ev["event"], ev["result"], ev["render_sha256"], ev["gate"], ev["scene"]),
                         ("render_check", "pass", first["render_sha256"], "G4", "scene"))
        self.w.run("approve", "scene", "renders/scene_v01.mp4", "--gate", "G4", check=True)
        self.assertEqual(self.w.approvals()[-1]["render_check"], "pass")
        self.assertEqual(self.w.run("check-approval", "renders/scene_v01.mp4")[0], 0)

        make_video(self.path, frames=30, color="0x303030")  # source changed, same path
        code, second = self.w.run("check-render", "renders/scene_v01.mp4")
        self.assertEqual(code, 0)
        self.assertNotEqual(first["render_sha256"], second["render_sha256"])
        self.assertEqual(len(second["stale_marked"]), 1)
        stale = self.w.approvals()[-1]
        self.assertEqual((stale["type"], stale["render_sha256"], stale["superseded_by_sha256"]),
                         ("stale", first["render_sha256"], second["render_sha256"]))
        _, st = self.w.run("status", check=True)
        self.assertEqual(st["approvals"]["stale"], 1)
        self.assertIn("1 stale", st["statusline"])
        code, d = self.w.run("check-approval", "renders/scene_v01.mp4")
        self.assertEqual(code, 1)
        self.assertTrue(d["stale"])

        # Re-checking the same render does not add a second stale line.
        self.w.run("check-render", "renders/scene_v01.mp4", check=True)
        self.assertEqual(sum(1 for a in self.w.approvals() if a.get("type") == "stale"), 1)

        self.w.run("approve", "scene", "renders/scene_v01.mp4", "--gate", "G4", check=True)
        self.assertEqual(self.w.run("check-approval", "renders/scene_v01.mp4")[0], 0)
        _, st = self.w.run("status", check=True)
        self.assertEqual(st["approvals"]["stale"], 0)

    def test_old_render_back_is_not_silently_approved_after_stale(self):
        make_video(self.path, frames=30)
        self.w.run("approve", "scene", "renders/scene_v01.mp4", "--gate", "G4", check=True)
        old = self.path.read_bytes()
        make_video(self.path, frames=30, color="0x303030")
        self.w.run("check-render", "renders/scene_v01.mp4", check=True)
        self.path.write_bytes(old)  # restore the approved bytes
        code, d = self.w.run("check-approval", "renders/scene_v01.mp4")
        self.assertEqual(code, 1)
        self.assertIn("no longer standing", d["reason"])


if __name__ == "__main__":
    unittest.main()
