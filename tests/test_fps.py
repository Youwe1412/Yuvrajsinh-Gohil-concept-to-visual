"""Frame-rate maths at 24000/1001 and 25, drop-frame timecode, and where a project's rate comes from."""
import json
import unittest
from fractions import Fraction

from helpers import World, WorldCase  # noqa: F401  (puts cli/ on sys.path)

from aem import fps as F
from aem.util import AemError

NTSC24 = Fraction(24000, 1001)
PAL = Fraction(25)


class Rates(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(F.parse_rate("24000/1001"), NTSC24)
        self.assertEqual(F.parse_rate("25"), PAL)
        self.assertEqual(F.parse_rate("25/1"), PAL)
        self.assertEqual(F.parse_rate({"num": 30000, "den": 1001}), Fraction(30000, 1001))

    def test_decimal_refused(self):
        for bad in ("23.976", "29.97", "abc", "0", "-25"):
            with self.assertRaises(AemError):
                F.parse_rate(bad)

    def test_frame_duration(self):
        self.assertEqual(F.parse_frame_duration("1001/24000s"), NTSC24)
        self.assertEqual(F.parse_frame_duration("1/25s"), PAL)
        self.assertEqual(F.parse_frame_duration("100/2500s"), PAL)

    def test_nominal(self):
        self.assertEqual(F.nominal(NTSC24), 24)
        self.assertEqual(F.nominal(PAL), 25)
        self.assertEqual(F.nominal(Fraction(30000, 1001)), 30)


class FrameMaths(unittest.TestCase):
    def test_seconds_to_frame_ntsc(self):
        # P1 next-token: data-duration 5.457792 s at 24000/1001 rendered 131 frames.
        self.assertEqual(F.seconds_to_frame(5.457792, NTSC24), 131)
        self.assertEqual(F.seconds_to_frame(127.542208, NTSC24), 3058)
        self.assertEqual(F.seconds_to_frame(Fraction(1001, 24000), NTSC24), 1)
        self.assertEqual(F.seconds_to_frame(60, NTSC24), 1439)  # 1438.56 -> 1439

    def test_seconds_to_frame_pal(self):
        self.assertEqual(F.seconds_to_frame(5.457792, PAL), 136)
        self.assertEqual(F.seconds_to_frame(60, PAL), 1500)
        self.assertEqual(F.seconds_to_frame(0.04, PAL), 1)

    def test_frame_to_seconds_exact(self):
        self.assertEqual(F.frame_to_seconds(24, NTSC24), Fraction(1001, 1000))
        self.assertEqual(F.frame_to_seconds(131, NTSC24), Fraction(131 * 1001, 24000))
        self.assertEqual(F.frame_to_seconds(25, PAL), 1)

    def test_round_trip(self):
        for fps in (NTSC24, PAL):
            for frame in (0, 1, 23, 24, 25, 1439, 86399, 123456):
                self.assertEqual(F.seconds_to_frame(F.frame_to_seconds(frame, fps), fps), frame)


class Timecode(unittest.TestCase):
    def test_ndf_counts_nominal(self):
        # Frame.io timecode counts at the nominal rate: 24 for 24000/1001, 25 for 25/1.
        self.assertEqual(F.timecode_to_frame("00:02:07:13", NTSC24), 127 * 24 + 13)
        self.assertEqual(F.timecode_to_frame("00:02:07:13", PAL), 127 * 25 + 13)
        self.assertEqual(F.timecode_to_frame("01:00:00:00", NTSC24), 86400)

    def test_ff_out_of_range(self):
        with self.assertRaises(AemError):
            F.timecode_to_frame("00:00:01:24", NTSC24)
        F.timecode_to_frame("00:00:01:24", PAL)  # fine at 25

    def test_drop_frame(self):
        df = Fraction(30000, 1001)
        self.assertEqual(F.timecode_to_frame("00:01:00;02", df), 1800)
        self.assertEqual(F.timecode_to_frame("00:10:00;00", df), 17982)
        for frame in (0, 1799, 1800, 17981, 17982, 107892):
            self.assertEqual(F.timecode_to_frame(F.frame_to_timecode(frame, df, drop=True), df), frame)
        with self.assertRaises(AemError):
            F.timecode_to_frame("00:01:00;02", PAL)

    def test_to_timecode(self):
        self.assertEqual(F.frame_to_timecode(3061, NTSC24), "00:02:07:13")
        self.assertEqual(F.frame_to_timecode(3188, PAL), "00:02:07:13")


class Discovery(WorldCase):
    def test_frame_md(self):
        r = F.resolve(self.w.project)
        self.assertEqual(r["fps"], NTSC24)
        self.assertEqual(r["source"], "frame.md")

    def test_fcpxml_edit(self):
        (self.w.project / "frame.md").unlink()
        (self.w.project / "edit.fcpxml").write_text(
            '<?xml version="1.0"?><fcpxml version="1.11"><resources>'
            '<format id="r1" frameDuration="1/25s" width="1920" height="1080"/></resources>'
            '<library><event><project name="x"><sequence format="r1" duration="100/25s"/></project></event></library></fcpxml>')
        r = F.resolve(self.w.project)
        self.assertEqual(r["fps"], PAL)
        self.assertIn("frameDuration", r["source"])

    def test_words_json(self):
        (self.w.project / "frame.md").unlink()
        (self.w.project / "data" / "words.json").write_text(json.dumps({"fps_num": 25, "fps_den": 1, "words": []}))
        self.assertEqual(F.resolve(self.w.project)["fps"], PAL)

    def test_conflict_refused(self):
        (self.w.project / "aem.project.json").write_text(json.dumps({"fps": "25/1"}))
        with self.assertRaises(AemError) as cm:
            F.resolve(self.w.project)
        self.assertIn("disagree", cm.exception.message)
        self.assertEqual(F.resolve(self.w.project, "25/1")["fps"], PAL)

    def test_none_never_assumed(self):
        (self.w.project / "frame.md").unlink()
        with self.assertRaises(AemError) as cm:
            F.resolve(self.w.project)
        self.assertIn("never assumes", cm.exception.hint)


if __name__ == "__main__":
    unittest.main()
