from __future__ import annotations

import unittest

from gray_scott_lab.analysis import TIME_EVOLUTION_PRESET, measure_pattern, scan_parameter_grid, study_time_evolution
from gray_scott_lab.core import GrayScottParameters, seed_state, simulate, simulate_samples


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

    def test_simulate_samples_returns_requested_steps(self) -> None:
        params = GrayScottParameters(feed=0.022, kill=0.051)
        samples = simulate_samples(params, (0, 5, 12), size=20, patch_radius=3, seed=1)
        self.assertEqual([step for step, _ in samples], [0, 5, 12])

    def test_time_evolution_metrics_move_between_seed_and_mature_pattern(self) -> None:
        study = study_time_evolution(TIME_EVOLUTION_PRESET, snapshot_steps=(0, 200, TIME_EVOLUTION_PRESET.steps), timeline_every=200)
        first = study.timeline[0].metrics
        last = study.timeline[-1].metrics
        self.assertGreater(last.active_fraction, first.active_fraction)
        self.assertNotAlmostEqual(last.edge_density, first.edge_density, places=4)


if __name__ == '__main__':
    unittest.main()
