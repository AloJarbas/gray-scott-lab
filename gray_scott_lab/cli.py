from __future__ import annotations

import argparse
import json
from pathlib import Path

from .analysis import CURATED_PRESETS, INITIALIZATION_PROFILES, SCAN_FEEDS, SCAN_KILLS, measure_pattern, preset_by_name, scan_parameter_grid, study_grid_size_comparison, study_horizon_comparison, study_initialization_sensitivity, study_presets, study_time_evolution
from .core import GrayScottParameters, simulate
from .render import export_png_from_svg, render_grid_size_comparison, render_horizon_comparison, render_initialization_sensitivity, render_metric_map, render_pattern_atlas, render_time_evolution


def parse_series(value: str) -> tuple[float, ...]:
    return tuple(float(part.strip()) for part in value.split(',') if part.strip())


def main() -> None:
    parser = argparse.ArgumentParser(description='Gray-Scott reaction-diffusion mini lab')
    subparsers = parser.add_subparsers(dest='command', required=True)

    simulate_parser = subparsers.add_parser('summarize', help='simulate one feed/kill pair and print pattern metrics')
    simulate_parser.add_argument('--feed', type=float, required=True)
    simulate_parser.add_argument('--kill', type=float, required=True)
    simulate_parser.add_argument('--steps', type=int, default=1200)
    simulate_parser.add_argument('--size', type=int, default=72)
    simulate_parser.add_argument('--patch-radius', type=int, default=7)
    simulate_parser.add_argument('--seed', type=int, default=0)

    atlas_parser = subparsers.add_parser('render-atlas', help='render the curated pattern atlas')
    atlas_parser.add_argument('--output', type=Path, required=True)
    atlas_parser.add_argument('--png-output', type=Path, default=None)

    map_parser = subparsers.add_parser('render-metric-map', help='render a coarse feed/kill metric map')
    map_parser.add_argument('--feeds', type=parse_series, default=SCAN_FEEDS)
    map_parser.add_argument('--kills', type=parse_series, default=SCAN_KILLS)
    map_parser.add_argument('--steps', type=int, default=700)
    map_parser.add_argument('--size', type=int, default=40)
    map_parser.add_argument('--patch-radius', type=int, default=5)
    map_parser.add_argument('--seed', type=int, default=0)
    map_parser.add_argument('--output', type=Path, required=True)
    map_parser.add_argument('--png-output', type=Path, default=None)

    timeline_parser = subparsers.add_parser('render-timeline', help='render the time-evolution sidecar for one curated preset')
    timeline_parser.add_argument('--preset', choices=[preset.name for preset in CURATED_PRESETS], default='worm bands')
    timeline_parser.add_argument('--output', type=Path, required=True)
    timeline_parser.add_argument('--png-output', type=Path, default=None)

    horizon_parser = subparsers.add_parser('render-horizon-comparison', help='render a short-vs-long horizon comparison for the feed/kill scan')
    horizon_parser.add_argument('--feeds', type=parse_series, default=SCAN_FEEDS)
    horizon_parser.add_argument('--kills', type=parse_series, default=SCAN_KILLS)
    horizon_parser.add_argument('--short-steps', type=int, default=700)
    horizon_parser.add_argument('--long-steps', type=int, default=1400)
    horizon_parser.add_argument('--size', type=int, default=40)
    horizon_parser.add_argument('--patch-radius', type=int, default=5)
    horizon_parser.add_argument('--seed', type=int, default=0)
    horizon_parser.add_argument('--output', type=Path, required=True)
    horizon_parser.add_argument('--png-output', type=Path, default=None)

    grid_size_parser = subparsers.add_parser('render-grid-size-comparison', help='render a smaller-vs-larger lattice comparison for the feed/kill scan')
    grid_size_parser.add_argument('--feeds', type=parse_series, default=SCAN_FEEDS)
    grid_size_parser.add_argument('--kills', type=parse_series, default=SCAN_KILLS)
    grid_size_parser.add_argument('--steps', type=int, default=1400)
    grid_size_parser.add_argument('--small-size', type=int, default=40)
    grid_size_parser.add_argument('--large-size', type=int, default=72)
    grid_size_parser.add_argument('--small-patch-radius', type=int, default=5)
    grid_size_parser.add_argument('--large-patch-radius', type=int, default=None)
    grid_size_parser.add_argument('--seed', type=int, default=0)
    grid_size_parser.add_argument('--output', type=Path, required=True)
    grid_size_parser.add_argument('--png-output', type=Path, default=None)

    init_parser = subparsers.add_parser('render-initialization-sensitivity', help='render a seed-profile sensitivity comparison for the feed/kill scan')
    init_parser.add_argument('--feeds', type=parse_series, default=SCAN_FEEDS)
    init_parser.add_argument('--kills', type=parse_series, default=SCAN_KILLS)
    init_parser.add_argument('--steps', type=int, default=1400)
    init_parser.add_argument('--size', type=int, default=40)
    init_parser.add_argument('--patch-radius', type=int, default=5)
    init_parser.add_argument('--seed', type=int, default=0)
    init_parser.add_argument('--profiles', type=lambda value: tuple(part.strip() for part in value.split(',') if part.strip()), default=INITIALIZATION_PROFILES)
    init_parser.add_argument('--output', type=Path, required=True)
    init_parser.add_argument('--png-output', type=Path, default=None)

    args = parser.parse_args()

    if args.command == 'summarize':
        state = simulate(
            GrayScottParameters(feed=args.feed, kill=args.kill),
            steps=args.steps,
            size=args.size,
            patch_radius=args.patch_radius,
            seed=args.seed,
        )
        metrics = measure_pattern(state)
        print(json.dumps({
            'feed': args.feed,
            'kill': args.kill,
            'steps': args.steps,
            'size': args.size,
            'mean_v': metrics.mean_v,
            'std_v': metrics.std_v,
            'active_fraction': metrics.active_fraction,
            'edge_density': metrics.edge_density,
            'peak_v': metrics.peak_v,
        }, indent=2))
        return

    if args.command == 'render-atlas':
        content = render_pattern_atlas(study_presets(CURATED_PRESETS))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content)
        if args.png_output is not None:
            export_png_from_svg(args.output, args.png_output, size=2000, dpi=300)
        return

    if args.command == 'render-timeline':
        content = render_time_evolution(study_time_evolution(preset_by_name(args.preset)))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content)
        if args.png_output is not None:
            export_png_from_svg(args.output, args.png_output, size=2200, dpi=300)
        return

    if args.command == 'render-horizon-comparison':
        study = study_horizon_comparison(
            feeds=args.feeds,
            kills=args.kills,
            short_steps=args.short_steps,
            long_steps=args.long_steps,
            size=args.size,
            patch_radius=args.patch_radius,
            seed=args.seed,
        )
        content = render_horizon_comparison(study, args.feeds, args.kills)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content)
        if args.png_output is not None:
            export_png_from_svg(args.output, args.png_output, size=2200, dpi=300)
        return

    if args.command == 'render-grid-size-comparison':
        study = study_grid_size_comparison(
            feeds=args.feeds,
            kills=args.kills,
            steps=args.steps,
            small_size=args.small_size,
            large_size=args.large_size,
            small_patch_radius=args.small_patch_radius,
            large_patch_radius=args.large_patch_radius,
            seed=args.seed,
        )
        content = render_grid_size_comparison(study, args.feeds, args.kills)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content)
        if args.png_output is not None:
            export_png_from_svg(args.output, args.png_output, size=2200, dpi=300)
        return

    if args.command == 'render-initialization-sensitivity':
        study = study_initialization_sensitivity(
            feeds=args.feeds,
            kills=args.kills,
            steps=args.steps,
            size=args.size,
            patch_radius=args.patch_radius,
            seed=args.seed,
            profiles=args.profiles,
        )
        content = render_initialization_sensitivity(study, args.feeds, args.kills)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content)
        if args.png_output is not None:
            export_png_from_svg(args.output, args.png_output, size=2200, dpi=300)
        return

    rows = scan_parameter_grid(
        feeds=args.feeds,
        kills=args.kills,
        steps=args.steps,
        size=args.size,
        patch_radius=args.patch_radius,
        seed=args.seed,
    )
    content = render_metric_map(rows, args.feeds, args.kills)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content)
    if args.png_output is not None:
        export_png_from_svg(args.output, args.png_output, size=1800, dpi=300)


if __name__ == '__main__':
    main()
