"""Phase 2 (1.1.0): evidence Claude can read about what it made.

Synthetic clips check the mechanics; P1's real renders (read from the drive, skipped when it is not mounted) check
what matters: the one-frame flash Joel had removed shows in the strip and in facts.json before the fix and not after,
the reveal of each question in audience-questions lands within a frame of the times measured by hand in P1's
OUTSTANDING.md, and evidence for a long 4K scene costs seconds, not minutes.
"""
import json
import re
import shutil
import struct
import time
import unittest
from pathlib import Path

from helpers import HAVE_FFMPEG, P1_DRIVE, P1World, WorldCase, make_video

FLASH = "drawbox=x=100:y=60:w=80:h=60:color=white:t=fill:enable='eq(n,10)'"
APPEAR = "drawbox=x=40:y=40:w=120:h=60:color=white:t=fill:enable='gte(n,30)'"
FPS = 24000 / 1001


def png_width(path: Path) -> int:
    with open(path, "rb") as f:
        head = f.read(24)
    return struct.unpack(">I", head[16:20])[0]


def links(md: str) -> list[str]:
    return re.findall(r"\]\(([^)#]+)\)", md)


@unittest.skipUnless(HAVE_FFMPEG, "ffmpeg and ffprobe are needed")
class Evidence(WorldCase):
    fps = "25/1"
    fps_in = "settings"

    def setUp(self):
        super().setUp()
        self.w.use()
        self.r = self.w.project / "renders"

    def evidence(self, *args):
        code, d = self.w.run("evidence", *args, operator=False)
        self.assertEqual(code, 0, d)
        return d, self.w.project / d["dir"]

    def test_a_flash_shows_in_the_strip_and_facts(self):
        make_video(self.r / "shot_v01.mp4", frames=40, box=FLASH)
        d, out = self.evidence("renders/shot_v01.mp4")
        self.assertEqual((d["moment"], d["version"], d["dir"]), ("shot", "v01", "reviews/shot/v01"))
        facts = json.loads((out / "facts.json").read_text())
        self.assertEqual([f["frame"] for f in facts["flashes"] if f["severity"] == "fail"], [10])
        md = (out / "evidence.md").read_text()
        self.assertIn("[strip.jpg](strip.jpg): frames 7–14", md)  # the largest change is into frame 10
        self.assertIn("FLASH: frame 10", md)
        self.assertTrue(d["toast"].endswith(", FLASH at frame 10"), d["toast"])

    def test_poses_phone_crops_and_a_file_a_critic_can_be_given_alone(self):
        make_video(self.r / "shot_v02.mp4", frames=60, box=APPEAR)
        d, out = self.evidence("renders/shot_v02.mp4")
        md = (out / "evidence.md").read_text()
        for rel in links(md):  # every image and file evidence.md names exists, relative to it
            self.assertTrue((out / rel).is_file(), rel)
        poses = sorted((out / "poses").glob("*.png"))
        phone = sorted((out / "phone").glob("*.png"))
        self.assertEqual([p.name for p in poses], [p.name for p in phone])
        self.assertIn("f0000.png", [p.name for p in poses])  # first frame
        self.assertIn("f0059.png", [p.name for p in poses])  # last frame
        self.assertEqual((png_width(poses[0]), png_width(phone[0])), (1920, 390))
        for section in ("## The moment", "## Rules that apply", "## Readable poses", "## Fastest transition",
                        "## Sync", "## Facts", "## How to report"):
            self.assertIn(section, md)
        self.assertIn("Do not read the scene source", md)
        json.loads((out / "sync.json").read_text())
        ev = [e for e in self.w.events() if e["event"] == "evidence"][-1]
        self.assertEqual((ev["scene"], ev["evidence"]), ("shot", "reviews/shot/v02/evidence.md"))

    def test_a_cue_word_given_by_time_is_measured_in_frames(self):
        make_video(self.r / "shot_v03.mp4", frames=60, box=APPEAR)
        d, out = self.evidence("renders/shot_v03.mp4", "--cue-at", "1.16")  # 29 frames at 25/1
        cue = json.loads((out / "sync.json").read_text())["cues"][0]
        self.assertEqual((cue["onset_frame"], cue["change_frame"], cue["settle_frame"], cue["offset_frames"]), (29, 30, 31, 2))
        self.assertTrue(d["sync_measured"])
        self.assertIn("sync max offset 2f", d["toast"])

    def test_no_cue_words_says_so_rather_than_guessing_a_number(self):
        make_video(self.r / "shot_v04.mp4", frames=60, box=APPEAR)
        d, _ = self.evidence("renders/shot_v04.mp4")
        self.assertIn("no cue words, sync not measured", d["toast"])
        self.assertIsNone(d["max_abs_offset_frames"])

    def test_the_sentinel_builds_evidence_after_a_render(self):
        reg = json.loads(self.w.registry.read_text())
        reg["clients"][0]["render_sentinel"] = {"command_patterns": [r"(?:^|[\s;&|/])bin/r\.sh\b"]}
        self.w.registry.write_text(json.dumps(reg))
        start = time.time() - 1
        make_video(self.r / "a_v01.mp4", frames=30, box=FLASH)
        code, d = self.w.run("rendered", stdin=json.dumps({"command": "bin/r.sh a", "cwd": str(self.w.project),
                                                            "started_at": start}))
        self.assertEqual(code, 0, d)
        self.assertEqual(d["evidence"][0]["evidence_md"], "reviews/a/v01/evidence.md")
        self.assertIn("reviews/a/v01/evidence.md", d["text"])
        self.assertEqual(d["evidence_toasts"], ["evidence ready: a v01, no cue words, sync not measured, FLASH at frame 10"])

    def test_the_cut_moment_by_moment(self):
        make_video(self.r / "cut.mp4", frames=250, box=APPEAR)  # 10 s at 25/1
        (self.w.project / "data" / "edit.json").write_text(json.dumps([
            {"kind": "a", "name": "first", "start": 1.0, "duration": 2.0},
            {"kind": "b", "name": "second", "start": 5.0, "duration": 3.0},
            {"type": "video", "name": "theirs.mp4", "start": 8.5, "duration": 1.0}]))
        self.w.run("moments", check=True)
        d, out = self.evidence("renders/cut.mp4", "--video")
        self.assertEqual((d["sheets"], d["skipped"]), (2, []))
        self.assertEqual(sorted(p.name for p in out.glob("*.jpg")), ["001-first.jpg", "002-second.jpg"])
        md = (out / "video.md").read_text()
        self.assertIn("## 1. first · 1.00–3.00 s", md)
        for rel in links(md):
            self.assertTrue((out / rel).is_file(), rel)


@unittest.skipUnless(HAVE_FFMPEG and P1_DRIVE.is_dir(), "P1 on the T7 drive and ffmpeg are needed")
class P1Evidence(unittest.TestCase):
    def setUp(self):
        self.w = P1World()
        self.w.import_notes()  # Joel's notes: the moment knows it was asked, and by which note
        self.v8 = self.w.project / "renders" / "v08"

    def tearDown(self):
        self.w.cleanup()

    def copy(self, src: Path, dest: Path):
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)

    def evidence(self, rel, *extra):
        code, d = self.w.run("evidence", rel, *extra, operator=False)
        self.assertEqual(code, 0, d)
        return d, self.w.project / d["dir"]

    def test_the_50ms_flash_before_the_client_fix_and_not_after(self):
        fix = P1_DRIVE / "client-fixes" / "2026-09-14"
        self.copy(fix / "before" / "Animations Done" / "fd_S04_50ms_v08.mp4", self.v8 / "fd_S04_50ms_v08.mp4")
        self.copy(P1_DRIVE / "renders" / "v08" / "fd_S04_50ms_v08.mp4", self.w.project / "renders" / "v09" / "fd_S04_50ms_v09.mp4")
        self.w.run("moments", check=True)
        before, bdir = self.evidence("renders/v08/fd_S04_50ms_v08.mp4")
        facts = json.loads((bdir / "facts.json").read_text())
        self.assertEqual(facts["render_sha256"][:8], "c051544f")  # the render Joel ruled on
        self.assertEqual([(f["frame"], f["area_pct"]) for f in facts["flashes"] if f["severity"] == "fail"], [(2, 100.0)])
        md = (bdir / "evidence.md").read_text()
        self.assertIn("[strip.jpg](strip.jpg): frames 0–7, left to right; the largest change is into frame 2", md)
        self.assertIn('Asked by the client: note #42 "50ms shown on screen in big text"', md)
        self.assertTrue(before["toast"].endswith("FLASH at frame 2"), before["toast"])
        after, adir = self.evidence("renders/v09/fd_S04_50ms_v09.mp4")
        self.assertEqual([f for f in json.loads((adir / "facts.json").read_text())["flashes"] if f["severity"] == "fail"], [])
        self.assertNotIn("into frame 2 ", (adir / "evidence.md").read_text())
        self.assertTrue(after["toast"].endswith("no flash"), after["toast"])

    def test_audience_questions_sync_matches_the_hand_measured_onsets_within_a_frame(self):
        # P1 OUTSTANDING.md: the breath gaps were measured on the voice at 2.057, 3.984 and 6.564 s into the scene, and
        # each line's mask was started 0.15 s ahead of its onset (lib/scenes.js) so it reads on the word.
        self.copy(P1_DRIVE / "renders" / "v08" / "fd_S05_audience-questions_v08.mp4", self.v8 / "fd_S05_audience-questions_v08.mp4")
        hand = [2.057, 3.984, 6.564]
        d, out = self.evidence("renders/v08/fd_S05_audience-questions_v08.mp4", *sum((["--cue-at", str(t)] for t in hand), []))
        cues = json.loads((out / "sync.json").read_text())["cues"]
        for t, c in zip(hand, cues):
            self.assertEqual(c["onset_frame"], round(t * FPS))
            self.assertLessEqual(abs(c["change_frame"] - round((t - 0.15) * FPS)), 1, c)
            self.assertTrue(0 <= c["offset_frames"] <= 3, c)  # the readable pose lands on the word
        self.assertLessEqual(d["max_abs_offset_frames"], 3)
        self.assertIn("sync max offset", d["toast"])

    def test_cost_for_a_long_4k_scene_is_seconds(self):
        # fd_S01_100-runs: 404 frames of 3840x2160, 16.8 s. The budget is 30 s per 10 s of scene.
        self.copy(P1_DRIVE / "renders" / "v08" / "fd_S01_100-runs_v08.mp4", self.v8 / "fd_S01_100-runs_v08.mp4")
        t = time.time()
        d, _ = self.evidence("renders/v08/fd_S01_100-runs_v08.mp4")
        took = time.time() - t
        self.assertEqual(d["frames"], 404)
        self.assertLess(took, 30.0)
        print(f"\n    evidence for fd_S01_100-runs (404 frames, 4K): {d['seconds']} s in aem, {took:.2f} s with start-up")


if __name__ == "__main__":
    unittest.main()
