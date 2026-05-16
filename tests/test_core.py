from __future__ import annotations

import unittest

from gray_scott_lab.analysis import measure_pattern, scan_parameter_grid
from gray_scott_lab.core import GrayScottParameters, seed_state, simulate


class GrayScottTests(unittest.TestCase):
    def test_seed_state_starts_in_bounds(self) -> None:
        state = seed_state(size=24, patch_radius=4, seed=3)
        values = [value for row in state.u for value in row] + [value for row in state.v for value in row]
        self.assertTrue(all(0.0 <= value <= 1.0 for value in values))

    def test_simulation_is_deterministic_for_same_seed(self) -> None:
        params = GrayScottParameters(feed=0.022, kill=0.051)
        first = simulate(params, size=24, steps=60, patch_radius=4, seed=2)
        second = simulate(params, size=24, steps=60, patch_radius=4, seed=2)
        self.assertEqual(first.v, second.v)
        self.assertEqual(first.u, second.u)

    def test_worm_band_regime_keeps_more_activity_than_sparse_spots(self) -> None:
        sparse = simulate(GrayScottParameters(feed=0.014, kill=0.054), size=40, steps=500, patch_radius=5, seed=0)
        worms = simulate(GrayScottParameters(feed=0.022, kill=0.051), size=40, steps=500, patch_radius=5, seed=0)
        self.assertLess(measure_pattern(sparse).active_fraction, measure_pattern(worms).active_fraction)

    def test_parameter_scan_returns_one_row_per_feed_kill_pair(self) -> None:
        rows = scan_parameter_grid((0.014, 0.022), (0.051, 0.057), size=24, steps=80, patch_radius=4, seed=0)
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(0.0 <= row.metrics.active_fraction <= 1.0 for row in rows))


if __name__ == '__main__':
    unittest.main()
