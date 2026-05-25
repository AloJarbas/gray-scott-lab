from __future__ import annotations

import unittest

from gray_scott_lab.analysis import HORIZON_TAG_FADING, HORIZON_TAG_GROWING, HORIZON_TAG_REVERSING, HORIZON_TAG_SETTLED, TIME_EVOLUTION_PRESET, measure_pattern, scan_parameter_grid, scaled_patch_radius, study_grid_size_comparison, study_horizon_comparison, study_horizon_tags, study_initialization_sensitivity, study_time_evolution
from gray_scott_lab.core import GrayScottParameters, seed_state, simulate, simulate_samples


class GrayScottTests(unittest.TestCase):
    def test_seed_state_starts_in_bounds(self) -> None:
        state = seed_state(size=24, patch_radius=4, seed=3)
        values = [value for row in state.u for value in row] + [value for row in state.v for value in row]
        self.assertTrue(all(0.0 <= value <= 1.0 for value in values))

    def test_all_seed_profiles_start_in_bounds(self) -> None:
        for profile in ('center', 'double', 'ring'):
            state = seed_state(size=24, patch_radius=4, seed=3, profile=profile)
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

    def test_horizon_comparison_detects_growth_and_fade_cells(self) -> None:
        study = study_horizon_comparison((0.018, 0.022, 0.030), (0.051, 0.054, 0.057), short_steps=700, long_steps=1400, size=40, patch_radius=5, seed=0)
        growth = max(study.rows, key=lambda row: row.active_fraction_delta)
        fade = min(study.rows, key=lambda row: row.active_fraction_delta)
        self.assertGreater(growth.active_fraction_delta, 0.05)
        self.assertLess(fade.active_fraction_delta, -0.05)

    def test_horizon_comparison_requires_longer_second_horizon(self) -> None:
        with self.assertRaises(ValueError):
            study_horizon_comparison(short_steps=700, long_steps=700)

    def test_scaled_patch_radius_preserves_reference_case(self) -> None:
        self.assertEqual(scaled_patch_radius(40), 5)
        self.assertEqual(scaled_patch_radius(72), 9)

    def test_grid_size_comparison_detects_lattice_sensitive_cells(self) -> None:
        study = study_grid_size_comparison(
            (0.014, 0.022, 0.030),
            (0.051, 0.057, 0.063),
            steps=900,
            small_size=24,
            large_size=48,
            small_patch_radius=3,
            seed=0,
        )
        growth = max(study.rows, key=lambda row: row.active_fraction_delta)
        fade = min(study.rows, key=lambda row: row.active_fraction_delta)
        self.assertGreater(growth.active_fraction_delta, 0.2)
        self.assertLess(fade.active_fraction_delta, -0.04)

    def test_grid_size_comparison_requires_larger_second_grid(self) -> None:
        with self.assertRaises(ValueError):
            study_grid_size_comparison(steps=900, small_size=40, large_size=40)

    def test_initialization_sensitivity_detects_strong_and_robust_cells(self) -> None:
        study = study_initialization_sensitivity(
            (0.022, 0.026, 0.030),
            (0.054, 0.057, 0.063),
            steps=900,
            size=24,
            patch_radius=3,
        )
        strongest = max(study.rows, key=lambda row: row.active_span)
        robust_active = min((row for row in study.rows if row.min_active_fraction > 0.05), key=lambda row: row.active_span + 30.0 * row.edge_span)
        self.assertGreater(strongest.active_span, 0.45)
        self.assertLess(robust_active.active_span, 0.06)

    def test_initialization_sensitivity_requires_multiple_profiles(self) -> None:
        with self.assertRaises(ValueError):
            study_initialization_sensitivity(profiles=('center',))

    def test_horizon_tags_split_settled_growing_fading_and_reversing_cells(self) -> None:
        study = study_horizon_tags(
            (0.022, 0.026, 0.030),
            (0.051, 0.054, 0.057, 0.060, 0.063),
            early_steps=700,
            middle_steps=1400,
            late_steps=2800,
            size=40,
            patch_radius=5,
            seed=0,
        )
        by_cell = {(row.feed, row.kill): row.tag for row in study.rows}
        self.assertEqual(by_cell[(0.030, 0.063)], HORIZON_TAG_GROWING)
        self.assertEqual(by_cell[(0.026, 0.051)], HORIZON_TAG_FADING)
        self.assertEqual(by_cell[(0.022, 0.051)], HORIZON_TAG_REVERSING)
        self.assertEqual(by_cell[(0.030, 0.060)], HORIZON_TAG_SETTLED)

    def test_horizon_tags_require_strictly_increasing_steps(self) -> None:
        with self.assertRaises(ValueError):
            study_horizon_tags(early_steps=700, middle_steps=700, late_steps=1400)


if __name__ == '__main__':
    unittest.main()
