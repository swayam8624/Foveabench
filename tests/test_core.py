"""Numerical and reproducibility tests, not validation of GPU/perceptual claims."""
import math
import unittest

import numpy as np

from foveabench.__main__ import (
    Gaze, angular_map, assert_gaze, gaze_at_delay, gaze_trace,
    quality_metrics, reference_scene, render_reference_model,
)


class TraceTests(unittest.TestCase):
    def test_replay_determinism_and_validation(self):
        for kind in ("fixation", "pursuit", "saccade"):
            a = gaze_trace(kind, 25, 60)
            self.assertEqual(a, gaze_trace(kind, 25, 60))
            assert_gaze(a)
        with self.assertRaises(ValueError):
            assert_gaze([Gaze(0, .5, .5), Gaze(0, .5, .5)])
        with self.assertRaises(ValueError):
            assert_gaze([Gaze(0, 1.3, .5)])
        with self.assertRaises(ValueError):
            assert_gaze([Gaze(0, math.nan, .5)])

    def test_short_smoke_saccade_has_actual_jumps(self):
        trace = gaze_trace("saccade", 12, 60)
        self.assertGreater(len({(s.x, s.y) for s in trace}), 1)
        # The delayed policy must select a different frame around a jump.
        self.assertNotEqual(gaze_at_delay(trace, 4, 40).x, trace[4].x)

    def test_latency_is_past_zero_order_hold(self):
        t = [Gaze(0,.1,.1), Gaze(20_000_000,.2,.2),
             Gaze(40_000_000,.3,.3)]
        self.assertEqual(gaze_at_delay(t, 2, 20).x, .2)
        self.assertEqual(gaze_at_delay(t, 1, 80).x, .1)
        self.assertEqual(gaze_at_delay(t, 2, 0).x, .3)


class ProjectionAndRendererTests(unittest.TestCase):
    def test_center_is_small_angular_error(self):
        theta = angular_map(101, 101, .5, .5)
        self.assertLess(theta[50,50], 1e-5)
        self.assertGreater(theta[50,95], theta[50,60])

    def test_full_identical_and_proxy_fraction(self):
        ref = reference_scene("chirp", 80, 48, 0)
        full, n = render_reference_model(ref, (.8,.3), "full")
        self.assertEqual(n, 80*48)
        np.testing.assert_array_equal(full, ref)
        fov = quality_metrics(ref, full, Gaze(0,.8,.3))
        self.assertEqual(fov["mse"], 0)
        self.assertIsNone(fov["psnr_db"])
        coarse, samples = render_reference_model(ref, (.8,.3), "gaze_0ms")
        self.assertLess(samples, 80*48)
        self.assertGreaterEqual(quality_metrics(ref, coarse, Gaze(0,.8,.3))["mse"], 0)

    def test_edges_are_real_stimulus(self):
        e = reference_scene("edges", 128, 72, 5)
        self.assertEqual(e.shape, (72,128,3))
        self.assertGreater(int(np.max(e)), int(np.min(e)))


if __name__ == "__main__":
    unittest.main()
