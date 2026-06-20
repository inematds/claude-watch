#!/usr/bin/env python3
"""Editorial pacing metrics: cuts/min, shot length distribution, motion.

Consumes scene-change timestamps (from frames.extract_scene_change) and an
optional list of per-shot motion scores. Produces a JSON blob the reporter
embeds in the editorial profile section.

Talking-head detection is intentionally out-of-scope here — it requires
opencv-python which is not in the skill's preflight. Leaving the field
nullable in the report; can be filled in later if/when opencv is added.
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path


def _shot_intervals(scene_times: list[float], video_duration: float) -> list[tuple[float, float]]:
    """Shot (start, end) windows. Mirrors the implicit-shot-0 rule so motion
    scoring and pacing agree on shot boundaries and counts."""
    times = sorted(scene_times)
    if times[0] > 0.01:
        times = [0.0] + times
    return [
        (times[i], times[i + 1] if i + 1 < len(times) else video_duration)
        for i in range(len(times))
    ]


def compute_pacing(
    scene_times: list[float],
    video_duration: float,
    motion_scores: list[float] | None = None,
) -> dict:
    """Build shot-by-shot pacing report.

    Args:
        scene_times: sorted list of shot-start timestamps (seconds). If the
            first entry is not ~0, treat 0 as the implicit shot 0 start.
        video_duration: total duration of the analysed range (seconds).
        motion_scores: per-shot motion score in [0,1]; len must match shot count.

    Returns:
        {
          "shot_count": int,
          "cuts_per_minute": float,
          "mean_shot_length": float,
          "median_shot_length": float,
          "shots": [
            {"start_seconds": float, "duration_seconds": float,
             "motion_score": float|null},
            ...
          ],
        }
    """
    if not scene_times or video_duration <= 0:
        return {
            "shot_count": 0,
            "cuts_per_minute": 0.0,
            "mean_shot_length": 0.0,
            "median_shot_length": 0.0,
            "shots": [],
        }

    shots: list[dict] = []
    for i, (start, end) in enumerate(_shot_intervals(scene_times, video_duration)):
        duration = max(0.0, end - start)
        shot = {
            "start_seconds": round(start, 2),
            "duration_seconds": round(duration, 2),
            "motion_score": None,
        }
        if motion_scores is not None and i < len(motion_scores):
            shot["motion_score"] = round(float(motion_scores[i]), 3)
        shots.append(shot)

    durations = [s["duration_seconds"] for s in shots]
    return {
        "shot_count": len(shots),
        "cuts_per_minute": round(len(shots) / (video_duration / 60.0), 2),
        "mean_shot_length": round(statistics.mean(durations), 2),
        "median_shot_length": round(statistics.median(durations), 2),
        "shots": shots,
    }


def parse_signalstats(text: str) -> list[tuple[float, float]]:
    """Parse ffmpeg `signalstats,metadata=print` output into (pts_time, YDIF) pairs.

    YDIF is the mean absolute luma difference from the previous frame — a cheap,
    opencv-free per-frame motion proxy (high on cuts and fast motion, ~0 on a
    static shot). The reporter never sees this raw stream; it's aggregated per
    shot by motion_scores_per_shot.
    """
    out: list[tuple[float, float]] = []
    cur_t: float | None = None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("frame:"):
            cur_t = None
            for tok in line.split():
                if tok.startswith("pts_time:"):
                    try:
                        cur_t = float(tok.split(":", 1)[1])
                    except ValueError:
                        cur_t = None
        elif line.startswith("lavfi.signalstats.YDIF=") and cur_t is not None:
            try:
                out.append((cur_t, float(line.split("=", 1)[1])))
            except ValueError:
                pass
    return out


def motion_scores_per_shot(
    diffs: list[tuple[float, float]],
    scene_times: list[float],
    video_duration: float,
) -> list[float]:
    """Aggregate per-frame (pts_time, YDIF) diffs into one motion score per shot.

    Scores are normalised relative to the busiest shot (max -> 1.0) so they line
    up with select_hero_frames' "highest-motion shot" pick. Shot boundaries come
    from _shot_intervals, so len() always equals compute_pacing's shot_count.
    Returns all-zeros (never raises) when there is no motion or no diff data.
    """
    if not scene_times or video_duration <= 0:
        return []
    intervals = _shot_intervals(scene_times, video_duration)
    sums = [0.0] * len(intervals)
    counts = [0] * len(intervals)
    for t, ydif in diffs:
        for i, (start, end) in enumerate(intervals):
            last = i == len(intervals) - 1
            if start <= t < end or (last and t == end):
                sums[i] += ydif
                counts[i] += 1
                break
    avgs = [sums[i] / counts[i] if counts[i] else 0.0 for i in range(len(intervals))]
    peak = max(avgs) if avgs else 0.0
    if peak <= 0:
        return [0.0] * len(intervals)
    return [round(a / peak, 3) for a in avgs]


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: pacing.py <duration-seconds> <scene-time-1> [<scene-time-2> ...]",
              file=sys.stderr)
        raise SystemExit(2)
    duration = float(sys.argv[1])
    times = [float(x) for x in sys.argv[2:]]
    print(json.dumps(compute_pacing(times, duration), indent=2))
