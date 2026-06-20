"""Tests for report.md emission."""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPT_DIR))

from report import write_report  # noqa: E402


class TestReport(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="watch-report-test-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_writes_all_required_sections(self):
        out = write_report(
            out_path=self.tmp / "report.md",
            source="https://youtu.be/test",
            title="Test Video",
            duration_seconds=125.0,
            intent="studying hook patterns",
            transcript_segments=[
                {"start": 0.0, "end": 2.0, "text": "Hello world."},
                {"start": 2.0, "end": 5.0, "text": "Second segment."},
            ],
            transcript_source="captions",
            all_frames=[
                {"index": 0, "timestamp_seconds": 0.0, "path": "/tmp/f1.jpg"},
                {"index": 1, "timestamp_seconds": 5.0, "path": "/tmp/f2.jpg"},
                {"index": 2, "timestamp_seconds": 60.0, "path": "/tmp/f3.jpg"},
            ],
            hero_frames=[
                {"index": 0, "timestamp_seconds": 0.0, "path": "/tmp/f1.jpg"},
                {"index": 1, "timestamp_seconds": 5.0, "path": "/tmp/f2.jpg"},
            ],
            pacing={
                "shot_count": 6,
                "cuts_per_minute": 2.88,
                "mean_shot_length": 20.83,
                "median_shot_length": 18.5,
                "shots": [],
            },
            hook={"frames": [], "words": [], "ran": False, "skipped_reason": "video <30s"},
        )

        text = out.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"))
        self.assertIn("source: https://youtu.be/test", text)
        self.assertIn("intent: studying hook patterns", text)
        self.assertIn("hero_frames:", text)
        for header in (
            "# Test Video",
            "## TL;DR",
            "## Key moments",
            "## Hook microscope",
            "## Editorial profile",
            "## Quotable moments",
            "## Entities mentioned",
            "## Concepts surfaced",
            "## Transcript",
        ):
            self.assertIn(header, text, f"missing: {header}")
        self.assertIn("<!-- pending Claude fill", text)
        self.assertIn("Cuts/min: 2.88", text)
        self.assertIn("Mean shot length: 20.83", text)
        self.assertIn("Hello world.", text)


    def test_editorial_profile_includes_motion_when_scored(self):
        out = write_report(
            out_path=self.tmp / "report.md",
            source="x", title="T", duration_seconds=30.0, intent="",
            transcript_segments=[], transcript_source=None,
            all_frames=[{"index": 0, "timestamp_seconds": 0.0, "path": "/tmp/a.jpg"}],
            hero_frames=[],
            pacing={
                "shot_count": 3,
                "cuts_per_minute": 6.0,
                "mean_shot_length": 10.0,
                "median_shot_length": 10.0,
                "shots": [
                    {"start_seconds": 0.0, "duration_seconds": 10.0, "motion_score": 0.2},
                    {"start_seconds": 10.0, "duration_seconds": 10.0, "motion_score": 1.0},
                    {"start_seconds": 20.0, "duration_seconds": 10.0, "motion_score": 0.5},
                ],
            },
            hook={"frames": [], "words": [], "ran": False, "skipped_reason": "n/a"},
        )
        text = out.read_text(encoding="utf-8")
        self.assertIn("Motion", text)
        self.assertIn("peak 1.0", text)
        self.assertIn("@ 00:10", text)  # busiest shot starts at 10s

    def test_editorial_profile_omits_motion_when_unscored(self):
        out = write_report(
            out_path=self.tmp / "report.md",
            source="x", title="T", duration_seconds=30.0, intent="",
            transcript_segments=[], transcript_source=None,
            all_frames=[{"index": 0, "timestamp_seconds": 0.0, "path": "/tmp/a.jpg"}],
            hero_frames=[],
            pacing={
                "shot_count": 2,
                "cuts_per_minute": 4.0,
                "mean_shot_length": 15.0,
                "median_shot_length": 15.0,
                "shots": [
                    {"start_seconds": 0.0, "duration_seconds": 15.0, "motion_score": None},
                    {"start_seconds": 15.0, "duration_seconds": 15.0, "motion_score": None},
                ],
            },
            hook={"frames": [], "words": [], "ran": False, "skipped_reason": "n/a"},
        )
        text = out.read_text(encoding="utf-8")
        self.assertNotIn("- Motion", text)


if __name__ == "__main__":
    unittest.main()
