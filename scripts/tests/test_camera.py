"""Unit tests for camera-movement classification from vidstabdetect .trf."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPT_DIR))

from pacing import (  # noqa: E402
    parse_transforms, classify_shot_movement, camera_moves_per_shot,
)
from frames import extract_camera_transforms  # noqa: E402


def _has_vidstab() -> bool:
    if shutil.which("ffmpeg") is None:
        return False
    out = subprocess.run(["ffmpeg", "-hide_banner", "-filters"],
                         capture_output=True, text=True)
    return "vidstabdetect" in out.stdout

W, H = 320, 240
# symmetric field positions about the centre (160,120) so a pure pan/tilt
# leaves zero net radial (zoom) component
SYM = [(40, 120), (280, 120), (160, 40), (160, 200)]


def _vecs(vx, vy, pts=SYM):
    return [(vx, vy, x, y) for (x, y) in pts]


# Trimmed but real vidstabdetect output (a pan-right clip on this machine).
SAMPLE_TRF = """VID.STAB 1
#      accuracy = 15
#     shakiness = 10
Frame 1 (List 0 [])
Frame 2 (List 2 [(LM 7 -7 106 52 24 0.469799 4.838542),(LM 22 -1 52 52 24 0.341423 2.607639)])
Frame 3 (List 1 [(LM 6 0 106 133 24 0.283061 0.000000)])
"""


class TestParseTransforms(unittest.TestCase):

    def test_parses_local_motions_per_frame(self):
        frames = parse_transforms(SAMPLE_TRF)
        self.assertEqual(frames, [
            [],
            [(7, -7, 106, 52), (22, -1, 52, 52)],
            [(6, 0, 106, 133)],
        ])

    def test_ignores_header_and_comment_lines(self):
        # Only the three "Frame N" lines should produce entries.
        self.assertEqual(len(parse_transforms(SAMPLE_TRF)), 3)

    def test_empty_input_returns_empty(self):
        self.assertEqual(parse_transforms(""), [])

    def test_handles_negative_vectors(self):
        frames = parse_transforms("Frame 1 (List 1 [(LM -16 -17 52 79 24 0.30 0.48)])")
        self.assertEqual(frames, [[(-16, -17, 52, 79)]])


class TestClassifyShotMovement(unittest.TestCase):

    def test_static(self):
        m = [(0, 0, 100, 100), (1, 0, 160, 120), (0, 1, 220, 80), (0, 0, 60, 160)]
        self.assertEqual(classify_shot_movement(m, W, H)["label"], "static")

    def test_pan_right(self):
        self.assertEqual(classify_shot_movement(_vecs(8, 0), W, H)["label"], "pan-right")

    def test_pan_left(self):
        self.assertEqual(classify_shot_movement(_vecs(-8, 0), W, H)["label"], "pan-left")

    def test_tilt_is_vertical(self):
        self.assertTrue(classify_shot_movement(_vecs(0, 8), W, H)["label"].startswith("tilt"))

    def test_zoom_in_radial_outward(self):
        m = [(8, 0, 300, 120), (-8, 0, 20, 120), (0, -8, 160, 20), (0, 8, 160, 220),
             (6, -5, 280, 40), (-6, 5, 40, 200)]
        self.assertEqual(classify_shot_movement(m, W, H)["label"], "zoom-in")

    def test_handheld_when_directions_cancel(self):
        m = [(12, 0, 80, 60), (-12, 0, 80, 60), (0, 12, 240, 180), (0, -12, 240, 180),
             (11, 2, 160, 120), (-10, -3, 160, 120)]
        self.assertEqual(classify_shot_movement(m, W, H)["label"], "handheld")

    def test_empty_is_unknown(self):
        self.assertEqual(classify_shot_movement([], W, H)["label"], "unknown")


class TestCameraMovesPerShot(unittest.TestCase):

    def test_classifies_each_shot_independently(self):
        per_frame = [
            (1.0, _vecs(8, 0)), (5.0, _vecs(8, 0)),          # shot 0: pan-right
            (11.0, [(0, 0, 100, 100), (1, 0, 160, 120)]),    # shot 1: static
            (15.0, [(0, 0, 60, 160)]),
        ]
        labels = camera_moves_per_shot(per_frame, scene_times=[0.0, 10.0],
                                       video_duration=20.0, frame_w=W, frame_h=H)
        self.assertEqual(labels, ["pan-right", "static"])

    def test_shot_without_frames_is_unknown(self):
        per_frame = [(1.0, _vecs(8, 0))]  # only falls in shot 0
        labels = camera_moves_per_shot(per_frame, scene_times=[0.0, 10.0],
                                       video_duration=20.0, frame_w=W, frame_h=H)
        self.assertEqual(labels[0], "pan-right")
        self.assertEqual(labels[1], "unknown")

    def test_empty_scene_times_returns_empty(self):
        self.assertEqual(
            camera_moves_per_shot([(1.0, _vecs(8, 0))], scene_times=[],
                                  video_duration=20.0, frame_w=W, frame_h=H),
            [],
        )


class TestCameraRunner(unittest.TestCase):

    def setUp(self):
        if not _has_vidstab():
            self.skipTest("ffmpeg vidstabdetect not available")
        self.tmp = Path(tempfile.mkdtemp(prefix="watch-cam-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_detects_horizontal_pan_end_to_end(self):
        # Freeze one textured frame, then slide a window across it = a clean
        # horizontal pan with no in-scene animation to muddy the vectors.
        still = self.tmp / "still.png"
        subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", "testsrc2=s=1280x480", "-frames:v", "1", str(still),
        ], check=True, capture_output=True)
        pan = self.tmp / "pan.mp4"
        subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-loop", "1", "-i", str(still), "-t", "2", "-r", "30",
            "-vf", "crop=640:480:x='(in_w-640)*t/2':y=0", "-pix_fmt", "yuv420p", str(pan),
        ], check=True, capture_output=True)

        per_frame, w, h = extract_camera_transforms(str(pan))
        self.assertTrue(per_frame, "expected per-frame motion data")
        pooled = [v for _, motions in per_frame for v in motions]
        label = classify_shot_movement(pooled, w, h)["label"]
        self.assertTrue(label.startswith("pan"), f"expected a pan, got {label!r}")


if __name__ == "__main__":
    unittest.main()
