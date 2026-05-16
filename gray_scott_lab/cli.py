from __future__ import annotations

import argparse
import json
from pathlib import Path

from .analysis import CURATED_PRESETS, SCAN_FEEDS, SCAN_KILLS, measure_pattern, scan_parameter_grid, study_presets
from .core import GrayScottParameters, simulate
from .render import export_png_from_svg, render_metric_map, render_pattern_atlas


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
