"""Unit tests for camera-movement classification from vidstabdetect .trf."""
import sys
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPT_DIR))

from pacing import parse_transforms, classify_shot_movement  # noqa: E402

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


if __name__ == "__main__":
    unittest.main()
