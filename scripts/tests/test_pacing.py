"""Unit tests for pacing math."""
import sys
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPT_DIR))

from pacing import compute_pacing, parse_signalstats, motion_scores_per_shot  # noqa: E402


class TestPacing(unittest.TestCase):

    def test_basic_metrics(self):
        scene_times = [0.0, 5.0, 13.0, 25.0, 35.0, 50.0]
        result = compute_pacing(
            scene_times=scene_times,
            video_duration=60.0,
            motion_scores=None,
        )
        self.assertEqual(result["shot_count"], 6)
        self.assertAlmostEqual(result["cuts_per_minute"], 6.0, places=1)
        self.assertAlmostEqual(result["mean_shot_length"], 10.0, places=1)
        self.assertEqual(len(result["shots"]), 6)
        self.assertAlmostEqual(result["shots"][0]["start_seconds"], 0.0)
        self.assertAlmostEqual(result["shots"][0]["duration_seconds"], 5.0)
        self.assertAlmostEqual(result["shots"][-1]["start_seconds"], 50.0)
        self.assertAlmostEqual(result["shots"][-1]["duration_seconds"], 10.0)

    def test_handles_single_shot(self):
        result = compute_pacing(
            scene_times=[0.0],
            video_duration=120.0,
            motion_scores=None,
        )
        self.assertEqual(result["shot_count"], 1)
        self.assertAlmostEqual(result["cuts_per_minute"], 0.5, places=1)
        self.assertAlmostEqual(result["mean_shot_length"], 120.0)

    def test_handles_empty_input(self):
        result = compute_pacing(scene_times=[], video_duration=60.0, motion_scores=None)
        self.assertEqual(result["shot_count"], 0)
        self.assertEqual(result["cuts_per_minute"], 0.0)
        self.assertEqual(result["mean_shot_length"], 0.0)
        self.assertEqual(result["shots"], [])

    def test_motion_scores_attached(self):
        result = compute_pacing(
            scene_times=[0.0, 10.0, 20.0],
            video_duration=30.0,
            motion_scores=[0.1, 0.5, 0.9],
        )
        scores = [s["motion_score"] for s in result["shots"]]
        self.assertEqual(scores, [0.1, 0.5, 0.9])


class TestParseSignalstats(unittest.TestCase):

    def test_parses_pts_time_and_ydif_pairs(self):
        text = (
            "frame:0    pts:0       pts_time:0\n"
            "lavfi.signalstats.YMIN=16\n"
            "lavfi.signalstats.YDIF=0.000000\n"
            "frame:1    pts:512     pts_time:0.040000\n"
            "lavfi.signalstats.YMIN=16\n"
            "lavfi.signalstats.YDIF=3.500000\n"
        )
        self.assertEqual(parse_signalstats(text), [(0.0, 0.0), (0.04, 3.5)])

    def test_ignores_other_signalstats_keys(self):
        text = (
            "frame:0    pts:0       pts_time:0\n"
            "lavfi.signalstats.YMAX=235\n"
            "lavfi.signalstats.UDIF=1.2\n"
            "lavfi.signalstats.YDIF=2.0\n"
        )
        self.assertEqual(parse_signalstats(text), [(0.0, 2.0)])

    def test_skips_ydif_before_any_frame(self):
        text = "lavfi.signalstats.YDIF=9.9\nframe:0 pts:0 pts_time:0\nlavfi.signalstats.YDIF=1.0\n"
        self.assertEqual(parse_signalstats(text), [(0.0, 1.0)])

    def test_empty_input_returns_empty(self):
        self.assertEqual(parse_signalstats(""), [])


class TestMotionScoresPerShot(unittest.TestCase):

    def test_normalizes_to_highest_motion_shot(self):
        # shot 0 = [0,10): avg ydif 1.0; shot 1 = [10,20): avg ydif 4.0
        diffs = [(1.0, 1.0), (5.0, 1.0), (11.0, 4.0), (15.0, 4.0)]
        scores = motion_scores_per_shot(diffs, scene_times=[0.0, 10.0], video_duration=20.0)
        self.assertEqual(scores, [0.25, 1.0])

    def test_length_matches_shot_count_with_implicit_zero(self):
        # scene_times[0] > 0 -> compute_pacing prepends shot 0; motion must match
        scores = motion_scores_per_shot([], scene_times=[5.0], video_duration=10.0)
        self.assertEqual(len(scores), 2)

    def test_all_zero_diffs_no_division_error(self):
        scores = motion_scores_per_shot(
            [(1.0, 0.0), (11.0, 0.0)], scene_times=[0.0, 10.0], video_duration=20.0
        )
        self.assertEqual(scores, [0.0, 0.0])

    def test_empty_scene_times_returns_empty(self):
        self.assertEqual(motion_scores_per_shot([(1.0, 5.0)], scene_times=[], video_duration=20.0), [])

    def test_aligns_with_compute_pacing_shot_count(self):
        scene_times = [0.0, 5.0, 13.0, 25.0]
        diffs = [(t, 1.0) for t in (1.0, 6.0, 14.0, 26.0)]
        scores = motion_scores_per_shot(diffs, scene_times, video_duration=40.0)
        pacing = compute_pacing(scene_times=scene_times, video_duration=40.0, motion_scores=scores)
        self.assertEqual(len(scores), pacing["shot_count"])
        self.assertTrue(all(s["motion_score"] is not None for s in pacing["shots"]))


if __name__ == "__main__":
    unittest.main()
