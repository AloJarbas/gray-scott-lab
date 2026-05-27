from __future__ import annotations

from collections import Counter
import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gray_scott_lab.analysis import CURATED_PRESETS, HORIZON_TAG_FADING, HORIZON_TAG_GROWING, HORIZON_TAG_REVERSING, HORIZON_TAG_SETTLED, INITIALIZATION_PROFILES, PROFILE_HORIZON_SINGLE_FLIP, PROFILE_HORIZON_STABLE, PROFILE_HORIZON_THREE_WAY_SPLIT, SCAN_FEEDS, SCAN_KILLS, TIME_EVOLUTION_PRESET, scan_parameter_grid, study_grid_size_comparison, study_horizon_comparison, study_horizon_tags, study_initialization_sensitivity, study_presets, study_profile_horizon_tags, study_time_evolution
from gray_scott_lab.core import seed_profile_label
from gray_scott_lab.render import export_png_from_svg, render_grid_size_comparison, render_horizon_comparison, render_horizon_tags, render_initialization_sensitivity, render_metric_map, render_pattern_atlas, render_profile_horizon_tags, render_time_evolution
ART = ROOT / 'art'
REPORTS = ROOT / 'reports'
NOTEBOOKS = ROOT / 'notebooks'


def write_atlas() -> Path:
    ART.mkdir(parents=True, exist_ok=True)
    studies = study_presets(CURATED_PRESETS)
    svg_path = ART / 'gray-scott-pattern-atlas.svg'
    svg_path.write_text(render_pattern_atlas(studies))
    export_png_from_svg(svg_path, ART / 'gray-scott-pattern-atlas.png', size=2200, dpi=300)
    return svg_path


def write_metric_map() -> tuple[Path, Path]:
    ART.mkdir(parents=True, exist_ok=True)
    rows = scan_parameter_grid(SCAN_FEEDS, SCAN_KILLS)
    svg_path = ART / 'gray-scott-parameter-map.svg'
    csv_path = ART / 'gray-scott-parameter-grid.csv'
    svg_path.write_text(render_metric_map(rows, SCAN_FEEDS, SCAN_KILLS))
    export_png_from_svg(svg_path, ART / 'gray-scott-parameter-map.png', size=1800, dpi=300)

    with csv_path.open('w', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(['feed', 'kill', 'mean_v', 'std_v', 'active_fraction', 'edge_density', 'peak_v'])
        for row in rows:
            writer.writerow([
                row.feed,
                row.kill,
                row.metrics.mean_v,
                row.metrics.std_v,
                row.metrics.active_fraction,
                row.metrics.edge_density,
                row.metrics.peak_v,
            ])
    return svg_path, csv_path


def write_report() -> Path:
    REPORTS.mkdir(parents=True, exist_ok=True)
    studies = study_presets(CURATED_PRESETS)
    rows = scan_parameter_grid(SCAN_FEEDS, SCAN_KILLS)

    highest_edge = max(rows, key=lambda row: row.metrics.edge_density)
    highest_active = max(rows, key=lambda row: row.metrics.active_fraction)
    sparsest = min(rows, key=lambda row: row.metrics.active_fraction)

    lines = [
        '# Gray-Scott pattern atlas and parameter scan',
        '',
        'This repo starts with a simple question: what do the Gray-Scott chemistry knobs actually do to the field if you hold the initialization fixed and only change feed and kill?',
        '',
        'The answer here is deliberately practical. Instead of claiming a complete phase diagram, this first pass gives two things you can rerun:',
        '',
        '- a curated four-panel atlas with visibly different regimes',
        '- a coarse feed-vs-kill scan that measures active fraction and edge density',
        '',
        '## Curated atlas',
        '',
    ]

    for study in studies:
        lines.extend([
            f"### {study.preset.name}",
            '',
            f"- `feed = {study.preset.feed:.3f}`, `kill = {study.preset.kill:.3f}`, `steps = {study.preset.steps}`",
            f"- `mean V = {study.metrics.mean_v:.3f}`",
            f"- `std V = {study.metrics.std_v:.3f}`",
            f"- `active fraction = {study.metrics.active_fraction:.1%}`",
            f"- `edge density = {study.metrics.edge_density:.4f}`",
            '',
        ])

    lines.extend([
        '## Coarse parameter scan',
        '',
        f"- highest edge density on this coarse grid: `F = {highest_edge.feed:.3f}`, `k = {highest_edge.kill:.3f}` with `edge density = {highest_edge.metrics.edge_density:.4f}`",
        f"- most chemically active field on this coarse grid: `F = {highest_active.feed:.3f}`, `k = {highest_active.kill:.3f}` with `active fraction = {highest_active.metrics.active_fraction:.1%}`",
        f"- sparsest surviving field on this coarse grid: `F = {sparsest.feed:.3f}`, `k = {sparsest.kill:.3f}` with `active fraction = {sparsest.metrics.active_fraction:.1%}`",
        '',
        '## Reading the first pass',
        '',
        '- low active fraction means the chemistry only survives in small islands',
        '- high edge density marks sharper reaction fronts and busier boundaries',
        '- the middle of the scanned band is where the field stops looking like isolated dots but has not yet blurred into a broad fill pattern',
        '',
        'Open `art/gray-scott-pattern-atlas.png`, `art/gray-scott-parameter-map.png`, and `notebooks/gray_scott_regimes.ipynb` together for the full packet.',
    ])

    report_path = REPORTS / 'pattern-atlas-and-parameter-scan.md'
    report_path.write_text('\n'.join(lines) + '\n')
    return report_path


def write_time_evolution() -> tuple[Path, Path, Path, Path]:
    ART.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    NOTEBOOKS.mkdir(parents=True, exist_ok=True)

    study = study_time_evolution(TIME_EVOLUTION_PRESET)
    svg_path = ART / 'gray-scott-time-evolution.svg'
    png_path = ART / 'gray-scott-time-evolution.png'
    csv_path = ART / 'gray-scott-time-evolution.csv'
    report_path = REPORTS / 'time-evolution-sidecar.md'
    notebook_path = NOTEBOOKS / 'gray_scott_time_evolution.ipynb'

    svg_path.write_text(render_time_evolution(study))
    export_png_from_svg(svg_path, png_path, size=2200, dpi=300)

    with csv_path.open('w', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(['step', 'mean_v', 'std_v', 'active_fraction', 'edge_density', 'peak_v'])
        for point in study.timeline:
            writer.writerow([
                point.step,
                point.metrics.mean_v,
                point.metrics.std_v,
                point.metrics.active_fraction,
                point.metrics.edge_density,
                point.metrics.peak_v,
            ])

    peak_active = max(study.timeline, key=lambda point: point.metrics.active_fraction)
    peak_edge = max(study.timeline, key=lambda point: point.metrics.edge_density)
    lines = [
        '# Gray-Scott time evolution sidecar',
        '',
        'The atlas and parameter map say what different regimes look like after a fixed run. This sidecar asks the next useful question: how does one regime get there?',
        '',
        f'This pass stays narrow on purpose. It follows the curated `{study.preset.name}` preset and keeps the same seed, grid, and chemistry parameters all the way through.',
        '',
        '## Setup',
        '',
        f'- `feed = {study.preset.feed:.3f}`',
        f'- `kill = {study.preset.kill:.3f}`',
        f'- `size = {study.preset.size}`',
        f'- `steps = {study.preset.steps}`',
        f'- `seed = {study.preset.seed}`',
        '',
        '## Main read',
        '',
        f'- active fraction peaks around step `{peak_active.step}` at `{peak_active.metrics.active_fraction:.1%}`',
        f'- edge density peaks around step `{peak_edge.step}` at `{peak_edge.metrics.edge_density:.4f}`',
        '- the regime does not simply fill in at one constant pace: it first grows chemical occupancy, then keeps reorganizing the interfaces as the banded structure settles',
        '- that is why the repo tracks both active fraction and edge density instead of pretending one scalar is the whole story',
        '',
        '## What the snapshots add',
        '',
        '- early frames show the seeded patch stretching into directional fronts',
        '- middle frames show the field becoming much more occupied without yet looking final',
        '- later frames show that the pattern can keep sharpening and reorganizing after the chemistry is already broadly active',
        '',
        '## Caveat',
        '',
        'This is one preset with one deterministic seed. It is a growth-process sidecar, not a claim about the whole model family.',
        '',
        'Open `art/gray-scott-time-evolution.png`, `art/gray-scott-time-evolution.csv`, and `notebooks/gray_scott_time_evolution.ipynb` together next.',
    ]
    report_path.write_text('\n'.join(lines) + '\n')

    notebook = {
        'cells': [
            {
                'cell_type': 'markdown',
                'metadata': {},
                'source': [
                    '# Gray-Scott time evolution\n',
                    '\n',
                    'This notebook is the slower companion to `reports/time-evolution-sidecar.md`.\n',
                    '\n',
                    'The narrow question is the useful one: **how does one Gray-Scott regime grow into itself instead of only appearing as a final frame?**\n',
                ],
            },
            {
                'cell_type': 'markdown',
                'metadata': {},
                'source': [
                    '## 1. Hold the chemistry fixed and watch the metrics move\n',
                    '\n',
                    f'This pass follows the curated `{study.preset.name}` preset with `F = {study.preset.feed:.3f}` and `k = {study.preset.kill:.3f}`.\n',
                    '\n',
                    'The point is not a broad phase diagram. The point is to separate **filling in** from **front sharpening** inside one reproducible run.\n',
                ],
            },
            {
                'cell_type': 'code',
                'execution_count': None,
                'metadata': {},
                'outputs': [],
                'source': [
                    'from gray_scott_lab.analysis import TIME_EVOLUTION_PRESET, study_time_evolution\n',
                    '\n',
                    'study = study_time_evolution(TIME_EVOLUTION_PRESET)\n',
                    '[(point.step, round(point.metrics.active_fraction, 4), round(point.metrics.edge_density, 4)) for point in study.timeline[:8]]\n',
                ],
            },
            {
                'cell_type': 'markdown',
                'metadata': {},
                'source': [
                    '## 2. Look for the split between occupancy and interface sharpness\n',
                    '\n',
                    'If both metrics were just different spellings of the same thing, their most important moments would land at the same time. They do not.\n',
                ],
            },
            {
                'cell_type': 'code',
                'execution_count': None,
                'metadata': {},
                'outputs': [],
                'source': [
                    'peak_active = max(study.timeline, key=lambda point: point.metrics.active_fraction)\n',
                    'peak_edge = max(study.timeline, key=lambda point: point.metrics.edge_density)\n',
                    '{\n',
                    "    'peak_active_step': peak_active.step,\n",
                    "    'peak_active': round(peak_active.metrics.active_fraction, 4),\n",
                    "    'peak_edge_step': peak_edge.step,\n",
                    "    'peak_edge': round(peak_edge.metrics.edge_density, 4),\n",
                    '}\n',
                ],
            },
            {
                'cell_type': 'markdown',
                'metadata': {},
                'source': [
                    'That difference is the notebook version of the figure caption:\n',
                    '\n',
                    '- active fraction tracks how much of the field stays chemically busy\n',
                    '- edge density tracks how sharp the interfaces stay while the fronts reorganize\n',
                    '- one preset can therefore carry both a growth story and a boundary story at the same time\n',
                ],
            },
        ],
        'metadata': {
            'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'},
            'language_info': {'name': 'python', 'version': '3.11'},
        },
        'nbformat': 4,
        'nbformat_minor': 5,
    }
    notebook_path.write_text(json.dumps(notebook, indent=2) + '\n')
    return svg_path, csv_path, report_path, notebook_path


def write_horizon_comparison() -> tuple[Path, Path, Path, Path]:
    ART.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    NOTEBOOKS.mkdir(parents=True, exist_ok=True)

    study = study_horizon_comparison(SCAN_FEEDS, SCAN_KILLS, short_steps=700, long_steps=1400, size=40, patch_radius=5, seed=0)
    svg_path = ART / 'gray-scott-horizon-comparison.svg'
    png_path = ART / 'gray-scott-horizon-comparison.png'
    csv_path = ART / 'gray-scott-horizon-comparison.csv'
    report_path = REPORTS / 'horizon-comparison-sidecar.md'
    notebook_path = NOTEBOOKS / 'gray_scott_horizon_comparison.ipynb'

    svg_path.write_text(render_horizon_comparison(study, SCAN_FEEDS, SCAN_KILLS))
    export_png_from_svg(svg_path, png_path, size=2200, dpi=300)

    with csv_path.open('w', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow([
            'feed',
            'kill',
            'short_steps',
            'long_steps',
            'short_active_fraction',
            'long_active_fraction',
            'active_fraction_delta',
            'short_edge_density',
            'long_edge_density',
            'edge_density_delta',
            'short_peak_v',
            'long_peak_v',
        ])
        for row in study.rows:
            writer.writerow([
                row.feed,
                row.kill,
                study.short_steps,
                study.long_steps,
                row.short_metrics.active_fraction,
                row.long_metrics.active_fraction,
                row.active_fraction_delta,
                row.short_metrics.edge_density,
                row.long_metrics.edge_density,
                row.edge_density_delta,
                row.short_metrics.peak_v,
                row.long_metrics.peak_v,
            ])

    peak_growth = max(study.rows, key=lambda row: row.active_fraction_delta)
    biggest_fade = min(study.rows, key=lambda row: row.active_fraction_delta)
    sharpest_gain = max(study.rows, key=lambda row: row.edge_density_delta)
    strongest_smoothing = min(study.rows, key=lambda row: row.edge_density_delta)
    median_abs_active = sorted(abs(row.active_fraction_delta) for row in study.rows)[len(study.rows) // 2]
    median_abs_edge = sorted(abs(row.edge_density_delta) for row in study.rows)[len(study.rows) // 2]
    lines = [
        '# Gray-Scott horizon comparison sidecar',
        '',
        'The original parameter map was useful, but it left one honest question open: **how much of that coarse structure was already persistent, and how much was still transient because the run stopped early?**',
        '',
        'This sidecar keeps the feed/kill grid, seed, and spatial size fixed and only changes the simulation horizon from 700 to 1400 Euler steps.',
        '',
        '## What changed the most',
        '',
        f'- biggest late growth: `F = {peak_growth.feed:.3f}`, `k = {peak_growth.kill:.3f}` with `Δactive = {peak_growth.active_fraction_delta:+.3f}` and `Δedge = {peak_growth.edge_density_delta:+.4f}`',
        f'- strongest fade: `F = {biggest_fade.feed:.3f}`, `k = {biggest_fade.kill:.3f}` with `Δactive = {biggest_fade.active_fraction_delta:+.3f}` and `Δedge = {biggest_fade.edge_density_delta:+.4f}`',
        f'- sharpest late interface growth: `F = {sharpest_gain.feed:.3f}`, `k = {sharpest_gain.kill:.3f}` with `Δedge = {sharpest_gain.edge_density_delta:+.4f}`',
        f'- strongest interface smoothing: `F = {strongest_smoothing.feed:.3f}`, `k = {strongest_smoothing.kill:.3f}` with `Δedge = {strongest_smoothing.edge_density_delta:+.4f}`',
        '',
        '## The practical read',
        '',
        f'- median absolute active-fraction shift across the whole grid: `{median_abs_active:.3f}`',
        f'- median absolute edge-density shift across the whole grid: `{median_abs_edge:.4f}`',
        '- some cells that looked mature at 700 steps were still transient and cooled sharply by 1400 steps',
        '- some middle-band settings kept growing into busier, sharper patterns instead of simply freezing in place',
        '- that makes the first parameter map a good scouting pass, not a finished phase diagram',
        '',
        '## Caveat',
        '',
        'This still holds grid size and seed fixed. It separates **time-horizon drift** from the original map, but it does not yet answer whether the same cells stay stable under a larger lattice or a different initialization patch.',
        '',
        'Open `art/gray-scott-horizon-comparison.png`, `art/gray-scott-horizon-comparison.csv`, and `notebooks/gray_scott_horizon_comparison.ipynb` together next.',
    ]
    report_path.write_text('\n'.join(lines) + '\n')

    notebook = {
        'cells': [
            {
                'cell_type': 'markdown',
                'metadata': {},
                'source': [
                    '# Gray-Scott horizon comparison\n',
                    '\n',
                    'This notebook is the slower companion to `reports/horizon-comparison-sidecar.md`.\n',
                    '\n',
                    'The question is narrow and worth asking before the repo starts talking like it owns a phase diagram: **which feed-kill cells were already persistent at 700 steps, and which ones were still drifting?**\n',
                ],
            },
            {
                'cell_type': 'markdown',
                'metadata': {},
                'source': [
                    '## 1. Hold the chemistry fixed and only change the horizon\n',
                    '\n',
                    'The Gray-Scott update used here is still the standard explicit Euler step\n',
                    '\n',
                    '$$u_{t+1} = u_t + D_u \\nabla^2 u_t - u_t v_t^2 + F(1-u_t),$$\n',
                    '$$v_{t+1} = v_t + D_v \\nabla^2 v_t + u_t v_t^2 - (F+k) v_t.$$\n',
                    '\n',
                    'This sidecar changes neither `F`, `k`, nor the lattice rules. It only asks what happens when the same coarse scan runs twice as long.\n',
                ],
            },
            {
                'cell_type': 'code',
                'execution_count': None,
                'metadata': {},
                'outputs': [],
                'source': [
                    'from gray_scott_lab.analysis import SCAN_FEEDS, SCAN_KILLS, study_horizon_comparison\n',
                    '\n',
                    'study = study_horizon_comparison(SCAN_FEEDS, SCAN_KILLS, short_steps=700, long_steps=1400)\n',
                    '[(row.feed, row.kill, round(row.active_fraction_delta, 3), round(row.edge_density_delta, 4)) for row in sorted(study.rows, key=lambda row: abs(row.active_fraction_delta), reverse=True)[:6]]\n',
                ],
            },
            {
                'cell_type': 'markdown',
                'metadata': {},
                'source': [
                    '## 2. The new figure\n',
                    '\n',
                    '![Gray-Scott horizon comparison](../art/gray-scott-horizon-comparison.png)\n',
                    '\n',
                    'Read it like this:\n',
                    '\n',
                    '1. the upper-left map is the old scouting pass at 700 steps\n',
                    '2. the upper-right map shows which cells kept spreading chemically and which ones were overconfident early reads\n',
                    '3. the lower-left map shows the same grid after the longer run\n',
                    '4. the lower-right map shows where the interfaces sharpened further and where they smoothed away\n',
                ],
            },
            {
                'cell_type': 'markdown',
                'metadata': {},
                'source': [
                    '## 3. What this does and does not settle\n',
                    '\n',
                    'The useful lesson is not just that some cells change. It is that they change **unevenly**. Some settings are already basically themselves at the shorter horizon, while others are still migrating toward either a denser banded field or a near-extinct one.\n',
                    '\n',
                    'That means the first map should be read as a scouting surface, not as a complete regime census.\n',
                ],
            },
            {
                'cell_type': 'markdown',
                'metadata': {},
                'source': [
                    '## Problems worth trying next\n',
                    '\n',
                    '1. Repeat the same comparison at one larger lattice size to separate horizon drift from finite-size drift.\n',
                    '2. Keep the horizon fixed and vary the seeded patch radius to see which cells are initialization-sensitive.\n',
                    '3. Add one compact classifier that tags cells as growing, fading, or largely settled without pretending those categories are universal.\n',
                ],
            },
        ],
        'metadata': {
            'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'},
            'language_info': {'name': 'python', 'version': '3.11'},
        },
        'nbformat': 4,
        'nbformat_minor': 5,
    }
    notebook_path.write_text(json.dumps(notebook, indent=2) + '\n')
    return svg_path, csv_path, report_path, notebook_path


def write_grid_size_comparison() -> tuple[Path, Path, Path, Path]:
    ART.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    NOTEBOOKS.mkdir(parents=True, exist_ok=True)

    study = study_grid_size_comparison(SCAN_FEEDS, SCAN_KILLS, steps=1400, small_size=40, large_size=72, small_patch_radius=5, seed=0)
    svg_path = ART / 'gray-scott-grid-size-comparison.svg'
    png_path = ART / 'gray-scott-grid-size-comparison.png'
    csv_path = ART / 'gray-scott-grid-size-comparison.csv'
    report_path = REPORTS / 'grid-size-comparison-sidecar.md'
    notebook_path = NOTEBOOKS / 'gray_scott_grid_size_comparison.ipynb'

    svg_path.write_text(render_grid_size_comparison(study, SCAN_FEEDS, SCAN_KILLS))
    export_png_from_svg(svg_path, png_path, size=2200, dpi=300)

    with csv_path.open('w', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow([
            'feed',
            'kill',
            'steps',
            'small_size',
            'large_size',
            'small_patch_radius',
            'large_patch_radius',
            'small_active_fraction',
            'large_active_fraction',
            'active_fraction_delta',
            'small_edge_density',
            'large_edge_density',
            'edge_density_delta',
            'small_peak_v',
            'large_peak_v',
        ])
        for row in study.rows:
            writer.writerow([
                row.feed,
                row.kill,
                study.steps,
                study.small_size,
                study.large_size,
                study.small_patch_radius,
                study.large_patch_radius,
                row.small_metrics.active_fraction,
                row.large_metrics.active_fraction,
                row.active_fraction_delta,
                row.small_metrics.edge_density,
                row.large_metrics.edge_density,
                row.edge_density_delta,
                row.small_metrics.peak_v,
                row.large_metrics.peak_v,
            ])

    biggest_growth = max(study.rows, key=lambda row: row.active_fraction_delta)
    biggest_fade = min(study.rows, key=lambda row: row.active_fraction_delta)
    sharpest_gain = max(study.rows, key=lambda row: row.edge_density_delta)
    strongest_smoothing = min(study.rows, key=lambda row: row.edge_density_delta)
    median_abs_active = sorted(abs(row.active_fraction_delta) for row in study.rows)[len(study.rows) // 2]
    median_abs_edge = sorted(abs(row.edge_density_delta) for row in study.rows)[len(study.rows) // 2]
    lines = [
        '# Gray-Scott grid-size comparison sidecar',
        '',
        'The horizon comparison settled one honest question: some cells were still changing because the run was too short. This follow-up asks the next one: **after the longer run, which cells still depend on the lattice size itself?**',
        '',
        f'This sidecar holds the feed/kill grid, seed, and {study.steps}-step horizon fixed. It then compares the same scan on a `{study.small_size}×{study.small_size}` lattice and a `{study.large_size}×{study.large_size}` lattice while scaling the seeded patch from radius `{study.small_patch_radius}` to `{study.large_patch_radius}` so the initial disturbance stays roughly proportional to the box.',
        '',
        '## What changed the most',
        '',
        f'- biggest larger-lattice growth: `F = {biggest_growth.feed:.3f}`, `k = {biggest_growth.kill:.3f}` with `Δactive = {biggest_growth.active_fraction_delta:+.3f}` and `Δedge = {biggest_growth.edge_density_delta:+.4f}`',
        f'- biggest larger-lattice fade: `F = {biggest_fade.feed:.3f}`, `k = {biggest_fade.kill:.3f}` with `Δactive = {biggest_fade.active_fraction_delta:+.3f}` and `Δedge = {biggest_fade.edge_density_delta:+.4f}`',
        f'- sharpest larger-lattice front growth: `F = {sharpest_gain.feed:.3f}`, `k = {sharpest_gain.kill:.3f}` with `Δedge = {sharpest_gain.edge_density_delta:+.4f}`',
        f'- strongest larger-lattice smoothing: `F = {strongest_smoothing.feed:.3f}`, `k = {strongest_smoothing.kill:.3f}` with `Δedge = {strongest_smoothing.edge_density_delta:+.4f}`',
        '',
        '## The practical read',
        '',
        f'- median absolute active-fraction shift across the whole grid: `{median_abs_active:.3f}`',
        f'- median absolute edge-density shift across the whole grid: `{median_abs_edge:.4f}`',
        '- several cells barely move, which is good news: the first chemistry story survives a larger arena',
        '- some cells do move a lot, especially where the smaller lattice either trapped the fronts too tightly or let the initial patch dominate too much of the field',
        '- that means the coarse map is maturing into a real packet: horizon drift and finite-size drift are now separate failure modes instead of one vague caution',
        '',
        '## Caveat',
        '',
        'This still uses one deterministic seed and one scaled patch rule. It is a bounded finite-size check, not a universal claim that the whole Gray-Scott regime atlas is now settled.',
        '',
        'Open `art/gray-scott-grid-size-comparison.png`, `art/gray-scott-grid-size-comparison.csv`, and `notebooks/gray_scott_grid_size_comparison.ipynb` together next.',
    ]
    report_path.write_text('\n'.join(lines) + '\n')

    notebook = {
        'cells': [
            {
                'cell_type': 'markdown',
                'metadata': {},
                'source': [
                    '# Gray-Scott grid-size comparison\n',
                    '\n',
                    'This notebook is the slower companion to `reports/grid-size-comparison-sidecar.md`.\n',
                    '\n',
                    'The question is the honest next one after the horizon pass: **once the run is long enough, which feed-kill cells still change because the box itself is larger?**\n',
                ],
            },
            {
                'cell_type': 'markdown',
                'metadata': {},
                'source': [
                    '## 1. Hold the chemistry and horizon fixed, then change the arena\n',
                    '\n',
                    'The Gray-Scott update stays the same:\n',
                    '\n',
                    '$$u_{t+1} = u_t + D_u \\nabla^2 u_t - u_t v_t^2 + F(1-u_t),$$\n',
                    '$$v_{t+1} = v_t + D_v \\nabla^2 v_t + u_t v_t^2 - (F+k) v_t.$$\n',
                    '\n',
                    f'This pass fixes the horizon at `{study.steps}` steps, keeps the same feed-kill grid and deterministic seed, and compares `{study.small_size}×{study.small_size}` against `{study.large_size}×{study.large_size}` while scaling the seeded patch from radius `{study.small_patch_radius}` to `{study.large_patch_radius}`.\n',
                ],
            },
            {
                'cell_type': 'code',
                'execution_count': None,
                'metadata': {},
                'outputs': [],
                'source': [
                    'from gray_scott_lab.analysis import SCAN_FEEDS, SCAN_KILLS, study_grid_size_comparison\n',
                    '\n',
                    'study = study_grid_size_comparison(SCAN_FEEDS, SCAN_KILLS, steps=1400, small_size=40, large_size=72, small_patch_radius=5)\n',
                    '[(row.feed, row.kill, round(row.active_fraction_delta, 3), round(row.edge_density_delta, 4)) for row in sorted(study.rows, key=lambda row: abs(row.active_fraction_delta), reverse=True)[:6]]\n',
                ],
            },
            {
                'cell_type': 'markdown',
                'metadata': {},
                'source': [
                    '## 2. The new figure\n',
                    '\n',
                    '![Gray-Scott grid-size comparison](../art/gray-scott-grid-size-comparison.png)\n',
                    '\n',
                    'Read it like this:\n',
                    '\n',
                    '1. the upper-left map is the smaller-lattice scan\n',
                    '2. the upper-right map shows which cells get busier or quieter on the larger lattice\n',
                    '3. the lower-left map is the same chemistry on the larger lattice\n',
                    '4. the lower-right map shows whether the front sharpness grows or smooths out when the arena gets bigger\n',
                ],
            },
            {
                'cell_type': 'markdown',
                'metadata': {},
                'source': [
                    '## 3. What this settles and what it does not\n',
                    '\n',
                    'The useful lesson is not that every cell changes. It is the opposite: **many cells barely move, while a smaller set still carry real finite-size drift.**\n',
                    '\n',
                    'That gives the repo a cleaner story. Horizon drift and finite-size drift are now separate checks, and both can be pointed to with concrete artifacts instead of hand-waving.\n',
                ],
            },
            {
                'cell_type': 'markdown',
                'metadata': {},
                'source': [
                    '## Problems worth trying next\n',
                    '\n',
                    '1. Keep the larger lattice and vary the seed patch radius to measure initialization sensitivity directly.\n',
                    '2. Add one compact settled/growing/fading tag only if it stays descriptive instead of pretending to be a universal classifier.\n',
                    '3. Try one second reaction-diffusion model only if it changes the pattern-family story instead of cloning the same workflow.\n',
                ],
            },
        ],
        'metadata': {
            'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'},
            'language_info': {'name': 'python', 'version': '3.11'},
        },
        'nbformat': 4,
        'nbformat_minor': 5,
    }
    notebook_path.write_text(json.dumps(notebook, indent=2) + '\n')
    return svg_path, csv_path, report_path, notebook_path


def write_horizon_tags() -> tuple[Path, Path, Path, Path]:
    ART.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    NOTEBOOKS.mkdir(parents=True, exist_ok=True)

    study = study_horizon_tags(
        SCAN_FEEDS,
        SCAN_KILLS,
        early_steps=700,
        middle_steps=1400,
        late_steps=2800,
        size=40,
        patch_radius=5,
        seed=0,
    )
    svg_path = ART / 'gray-scott-horizon-tags.svg'
    png_path = ART / 'gray-scott-horizon-tags.png'
    csv_path = ART / 'gray-scott-horizon-tags.csv'
    report_path = REPORTS / 'horizon-tags-sidecar.md'
    notebook_path = NOTEBOOKS / 'gray_scott_horizon_tags.ipynb'

    svg_path.write_text(render_horizon_tags(study, SCAN_FEEDS, SCAN_KILLS))
    export_png_from_svg(svg_path, png_path, size=2200, dpi=300)

    with csv_path.open('w', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow([
            'feed',
            'kill',
            'early_steps',
            'middle_steps',
            'late_steps',
            'tag',
            'early_active_fraction',
            'middle_active_fraction',
            'late_active_fraction',
            'early_active_delta',
            'late_active_delta',
            'total_active_delta',
            'early_edge_density',
            'middle_edge_density',
            'late_edge_density',
            'early_edge_delta',
            'late_edge_delta',
            'total_edge_delta',
        ])
        for row in study.rows:
            writer.writerow([
                row.feed,
                row.kill,
                study.early_steps,
                study.middle_steps,
                study.late_steps,
                row.tag,
                row.early_metrics.active_fraction,
                row.middle_metrics.active_fraction,
                row.late_metrics.active_fraction,
                row.early_active_delta,
                row.late_active_delta,
                row.total_active_delta,
                row.early_metrics.edge_density,
                row.middle_metrics.edge_density,
                row.late_metrics.edge_density,
                row.early_edge_delta,
                row.late_edge_delta,
                row.total_edge_delta,
            ])

    counts = Counter(row.tag for row in study.rows)
    settled_active = next(spotlight for spotlight in study.spotlights if spotlight.tag == HORIZON_TAG_SETTLED)
    late_growing = next((spotlight for spotlight in study.spotlights if spotlight.tag == HORIZON_TAG_GROWING), None)
    late_fading = next((spotlight for spotlight in study.spotlights if spotlight.tag == HORIZON_TAG_FADING), None)
    reversing = next((spotlight for spotlight in study.spotlights if spotlight.tag == HORIZON_TAG_REVERSING), None)
    strongest_late_growth = max(study.rows, key=lambda row: row.late_active_delta)
    strongest_late_fade = min(study.rows, key=lambda row: row.late_active_delta)

    lines = [
        '# Gray-Scott horizon tags sidecar',
        '',
        'The horizon, grid-size, and seed-profile passes all made the coarse scan more honest, but they still left one practical question open: **when a cell is not settled yet, what kind of late-horizon failure is it actually showing?**',
        '',
        f'This sidecar keeps the same feed/kill grid, seed, and `{study.size}×{study.size}` lattice, then measures the same cells at `{study.early_steps}`, `{study.middle_steps}`, and `{study.late_steps}` steps.',
        '',
        'The tag rule is intentionally bounded. It only reads the active-fraction path across those three horizons, then keeps edge density nearby as context. The tags are descriptive, not universal:',
        '',
        '- `settled`: both horizon legs stay small enough that the cell is basically stable already',
        '- `growing`: the late horizon still ends materially busier than the early one',
        '- `fading`: the late horizon collapses materially below the early one',
        '- `reversing`: the cell changes direction between the two horizon legs instead of just drifting one way',
        '',
        '## What the tag map says',
        '',
        f'- settled cells: `{counts.get(HORIZON_TAG_SETTLED, 0)}`',
        f'- late-growing cells: `{counts.get(HORIZON_TAG_GROWING, 0)}`',
        f'- late-fading cells: `{counts.get(HORIZON_TAG_FADING, 0)}`',
        f'- reversing cells: `{counts.get(HORIZON_TAG_REVERSING, 0)}`',
        f'- biggest late growth: `F = {strongest_late_growth.feed:.3f}`, `k = {strongest_late_growth.kill:.3f}` with `Δactive_{{late}} = {strongest_late_growth.late_active_delta:+.3f}`',
        f'- biggest late fade: `F = {strongest_late_fade.feed:.3f}`, `k = {strongest_late_fade.kill:.3f}` with `Δactive_{{late}} = {strongest_late_fade.late_active_delta:+.3f}`',
        '',
        '## The useful read',
        '',
        f'- settled active counterexample: `F = {settled_active.feed:.3f}`, `k = {settled_active.kill:.3f}` stays visibly active without large horizon drift',
        f'- strongest late-growing example: `F = {late_growing.feed:.3f}`, `k = {late_growing.kill:.3f}`' if late_growing is not None else '- no late-growing cell cleared the bounded threshold on this grid',
        f'- strongest late-fading example: `F = {late_fading.feed:.3f}`, `k = {late_fading.kill:.3f}`' if late_fading is not None else '- no late-fading cell cleared the bounded threshold on this grid',
        f'- reversing example: `F = {reversing.feed:.3f}`, `k = {reversing.kill:.3f}` changes direction between horizon legs' if reversing is not None else '- no reversing cell cleared the bounded threshold on this grid',
        '- that means the unsettled part of the map is not one generic caution blob after all. Some cells keep filling in, some were overread and later die back, and a smaller group overshoots before turning around.',
        '',
        '## Caveat',
        '',
        'This is still one lattice, one deterministic seed, and one active-fraction-driven tag rule. It sharpens the repo’s caveat story; it does not claim to classify the whole Gray-Scott plane once and for all.',
        '',
        'Open `art/gray-scott-horizon-tags.png`, `art/gray-scott-horizon-tags.csv`, and `notebooks/gray_scott_horizon_tags.ipynb` together next.',
    ]
    report_path.write_text('\n'.join(lines) + '\n')

    notebook = {
        'cells': [
            {
                'cell_type': 'markdown',
                'metadata': {},
                'source': [
                    '# Gray-Scott horizon tags\n',
                    '\n',
                    'This notebook is the slower companion to `reports/horizon-tags-sidecar.md`.\n',
                    '\n',
                    'The bounded question is the practical one: **after the earlier caveat passes, which cells are already settled, which are still growing, which fade out late, and which actually reverse?**\n',
                ],
            },
            {
                'cell_type': 'markdown',
                'metadata': {},
                'source': [
                    '## 1. Hold the chemistry fixed and read three horizons instead of two\n',
                    '\n',
                    'The Gray-Scott update stays the same. This sidecar only adds one later checkpoint and then reads the active-fraction path across the three horizons.\n',
                ],
            },
            {
                'cell_type': 'code',
                'execution_count': None,
                'metadata': {},
                'outputs': [],
                'source': [
                    'from gray_scott_lab.analysis import SCAN_FEEDS, SCAN_KILLS, study_horizon_tags\n',
                    '\n',
                    'study = study_horizon_tags(SCAN_FEEDS, SCAN_KILLS, early_steps=700, middle_steps=1400, late_steps=2800)\n',
                    '[(row.feed, row.kill, row.tag, round(row.early_active_delta, 3), round(row.late_active_delta, 3), round(row.total_active_delta, 3)) for row in study.rows]\n',
                ],
            },
            {
                'cell_type': 'markdown',
                'metadata': {},
                'source': [
                    '## 2. The new figure\n',
                    '\n',
                    '![Gray-Scott horizon tags](../art/gray-scott-horizon-tags.png)\n',
                    '\n',
                    'Read it in two passes:\n',
                    '\n',
                    '1. the left panel is the bounded tag map built from the active-fraction path\n',
                    '2. the right panel shows the raw late-horizon active drift so the tag map never floats free of the numbers\n',
                    '3. the spotlight rows show what one settled, growing, fading, and reversing cell actually look like in the `V` field\n',
                ],
            },
            {
                'cell_type': 'markdown',
                'metadata': {},
                'source': [
                    '## 3. What this settles and what it does not\n',
                    '\n',
                    'The useful lesson is that the unstable cells are **not all unstable in the same direction**. Some keep filling in, some die back after looking active in the middle horizon, and a smaller set overshoot and reverse.\n',
                    '\n',
                    'That makes the earlier Gray-Scott caveat packet more specific instead of just longer.\n',
                ],
            },
            {
                'cell_type': 'markdown',
                'metadata': {},
                'source': [
                    '## Problems worth trying next\n',
                    '\n',
                    '1. Repeat the same three-horizon tag rule on one larger lattice only if the tag counts actually change.\n',
                    '2. Stress the tag rule against the split and ring seed profiles only if the reversing lane survives that swap.\n',
                    '3. Extend the chemistry lane with one second reaction-diffusion model only if it reveals a genuinely different late-horizon failure pattern.\n',
                ],
            },
        ],
        'metadata': {
            'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'},
            'language_info': {'name': 'python', 'version': '3.11'},
        },
        'nbformat': 4,
        'nbformat_minor': 5,
    }
    notebook_path.write_text(json.dumps(notebook, indent=2) + '\n')
    return svg_path, csv_path, report_path, notebook_path


def write_initialization_sensitivity() -> tuple[Path, Path, Path, Path]:
    ART.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    NOTEBOOKS.mkdir(parents=True, exist_ok=True)

    study = study_initialization_sensitivity(
        SCAN_FEEDS,
        SCAN_KILLS,
        steps=1400,
        size=40,
        patch_radius=5,
        seed=0,
        profiles=INITIALIZATION_PROFILES,
    )
    svg_path = ART / 'gray-scott-initialization-sensitivity.svg'
    png_path = ART / 'gray-scott-initialization-sensitivity.png'
    csv_path = ART / 'gray-scott-initialization-sensitivity.csv'
    report_path = REPORTS / 'initialization-sensitivity-sidecar.md'
    notebook_path = NOTEBOOKS / 'gray_scott_initialization_sensitivity.ipynb'

    svg_path.write_text(render_initialization_sensitivity(study, SCAN_FEEDS, SCAN_KILLS))
    export_png_from_svg(svg_path, png_path, size=2200, dpi=300)

    with csv_path.open('w', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow([
            'feed',
            'kill',
            'steps',
            'size',
            'patch_radius',
            'profiles',
            'active_span',
            'edge_span',
            'active_winner_profile',
            'active_loser_profile',
            'center_active_fraction',
            'double_active_fraction',
            'ring_active_fraction',
            'center_edge_density',
            'double_edge_density',
            'ring_edge_density',
            'center_peak_v',
            'double_peak_v',
            'ring_peak_v',
        ])
        for row in study.rows:
            writer.writerow([
                row.feed,
                row.kill,
                study.steps,
                study.size,
                study.patch_radius,
                ','.join(study.profiles),
                row.active_span,
                row.edge_span,
                row.active_winner_profile,
                row.active_loser_profile,
                row.metrics_for('center').active_fraction,
                row.metrics_for('double').active_fraction,
                row.metrics_for('ring').active_fraction,
                row.metrics_for('center').edge_density,
                row.metrics_for('double').edge_density,
                row.metrics_for('ring').edge_density,
                row.metrics_for('center').peak_v,
                row.metrics_for('double').peak_v,
                row.metrics_for('ring').peak_v,
            ])

    biggest_active = max(study.rows, key=lambda row: row.active_span)
    biggest_edge = max(study.rows, key=lambda row: row.edge_span)
    robust_candidates = [row for row in study.rows if row.min_active_fraction > 0.05]
    most_robust = min(robust_candidates, key=lambda row: (row.active_span + 30.0 * row.edge_span, -row.max_active_fraction)) if robust_candidates else min(study.rows, key=lambda row: (row.active_span + 30.0 * row.edge_span, -row.max_active_fraction))
    median_active_span = sorted(row.active_span for row in study.rows)[len(study.rows) // 2]
    median_edge_span = sorted(row.edge_span for row in study.rows)[len(study.rows) // 2]
    lines = [
        '# Gray-Scott initialization sensitivity sidecar',
        '',
        'The horizon and grid-size passes settled two honest caveats, but one important one remained: **how much of the coarse chemistry story still depends on the seeded patch itself?**',
        '',
        'This sidecar keeps the feed/kill grid, step count, and lattice size fixed. It only swaps between three bounded seed profiles with roughly comparable seeded mass:',
        '',
        '- centered square patch',
        '- split twin patches',
        '- annulus shell',
        '',
        '## What changed the most',
        '',
        f'- biggest active-fraction swing: `F = {biggest_active.feed:.3f}`, `k = {biggest_active.kill:.3f}` with `span = {biggest_active.active_span:.3f}` ({seed_profile_label(biggest_active.active_loser_profile)} -> {seed_profile_label(biggest_active.active_winner_profile)})',
        f'- biggest edge-density swing: `F = {biggest_edge.feed:.3f}`, `k = {biggest_edge.kill:.3f}` with `span = {biggest_edge.edge_span:.4f}`',
        f'- robust active counterexample: `F = {most_robust.feed:.3f}`, `k = {most_robust.kill:.3f}` stays active under every profile with only `span = {most_robust.active_span:.3f}`',
        '',
        '## The practical read',
        '',
        f'- median active-fraction span across the whole grid: `{median_active_span:.3f}`',
        f'- median edge-density span across the whole grid: `{median_edge_span:.4f}`',
        '- several cells are robust, which is good: the repo is not collapsing into “everything depends on the seed”',
        '- some middle-band cells are not robust at all, which is equally useful: the same chemistry can flip from near-extinction to broad occupancy once the seeded patch is split or hollowed',
        '- that means the coarse scan is now better framed as a scouting surface plus three bounded caveat passes: horizon, lattice size, and initialization geometry',
        '',
        '## Caveat',
        '',
        'These profiles are intentionally comparable, not identical. This pass measures seed-geometry sensitivity in a bounded way; it does not claim to have found one universal initialization family for the Gray-Scott model.',
        '',
        'Open `art/gray-scott-initialization-sensitivity.png`, `art/gray-scott-initialization-sensitivity.csv`, and `notebooks/gray_scott_initialization_sensitivity.ipynb` together next.',
    ]
    report_path.write_text('\n'.join(lines) + '\n')

    notebook = {
        'cells': [
            {
                'cell_type': 'markdown',
                'metadata': {},
                'source': [
                    '# Gray-Scott initialization sensitivity\n',
                    '\n',
                    'This notebook is the slower companion to `reports/initialization-sensitivity-sidecar.md`.\n',
                    '\n',
                    'The bounded question is the useful one: **after horizon drift and finite-size drift are checked, how much of the remaining story still depends on the seeded patch geometry?**\n',
                ],
            },
            {
                'cell_type': 'markdown',
                'metadata': {},
                'source': [
                    '## 1. Keep the chemistry fixed and only swap the seed profile\n',
                    '\n',
                    'The reaction-diffusion update is unchanged. Only the initial disturbance changes between three bounded shapes: centered square, split twin patches, and annulus shell.\n',
                ],
            },
            {
                'cell_type': 'code',
                'execution_count': None,
                'metadata': {},
                'outputs': [],
                'source': [
                    'from gray_scott_lab.analysis import INITIALIZATION_PROFILES, SCAN_FEEDS, SCAN_KILLS, study_initialization_sensitivity\n',
                    '\n',
                    'study = study_initialization_sensitivity(SCAN_FEEDS, SCAN_KILLS, profiles=INITIALIZATION_PROFILES)\n',
                    '[(row.feed, row.kill, round(row.active_span, 3), round(row.edge_span, 4), row.active_loser_profile, row.active_winner_profile) for row in sorted(study.rows, key=lambda row: row.active_span, reverse=True)[:6]]\n',
                ],
            },
            {
                'cell_type': 'markdown',
                'metadata': {},
                'source': [
                    '## 2. The new figure\n',
                    '\n',
                    '![Gray-Scott initialization sensitivity](../art/gray-scott-initialization-sensitivity.png)\n',
                    '\n',
                    'Read it in two passes:\n',
                    '\n',
                    '1. the heatmaps show where active fraction and edge density move the most under profile swaps\n',
                    '2. the spotlight rows show what those swings actually look like in the final `V` field\n',
                ],
            },
            {
                'cell_type': 'markdown',
                'metadata': {},
                'source': [
                    '## 3. What this settles and what it does not\n',
                    '\n',
                    'The useful lesson is not that every cell is fragile. It is that fragility is **localized**. Some chemistry settings are already profile-robust, while others still change dramatically if the same initial mass is concentrated, split, or hollowed out.\n',
                    '\n',
                    'That makes the repo’s current atlas more honest. The coarse scan is still worth keeping, but now it comes with three explicit caveat layers instead of one vague warning.\n',
                ],
            },
            {
                'cell_type': 'markdown',
                'metadata': {},
                'source': [
                    '## Problems worth trying next\n',
                    '\n',
                    '1. Add one compact settled/growing/fading tag only if it sharpens the caveat story instead of pretending to classify the whole model.\n',
                    '2. Repeat the same profile swap on one larger lattice only if that changes the sensitivity map instead of redrawing it.\n',
                    '3. Extend the chemistry lane with one second reaction-diffusion model only if it reveals a genuinely different pattern family.\n',
                ],
            },
        ],
        'metadata': {
            'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'},
            'language_info': {'name': 'python', 'version': '3.11'},
        },
        'nbformat': 4,
        'nbformat_minor': 5,
    }
    notebook_path.write_text(json.dumps(notebook, indent=2) + '\n')
    return svg_path, csv_path, report_path, notebook_path


def write_profile_horizon_tags() -> tuple[Path, Path, Path, Path]:
    ART.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    NOTEBOOKS.mkdir(parents=True, exist_ok=True)

    study = study_profile_horizon_tags(
        SCAN_FEEDS,
        SCAN_KILLS,
        early_steps=700,
        middle_steps=1400,
        late_steps=2800,
        size=40,
        patch_radius=5,
        seed=0,
        profiles=INITIALIZATION_PROFILES,
    )
    svg_path = ART / 'gray-scott-profile-horizon-tags.svg'
    png_path = ART / 'gray-scott-profile-horizon-tags.png'
    csv_path = ART / 'gray-scott-profile-horizon-tags.csv'
    report_path = REPORTS / 'profile-horizon-tags-sidecar.md'
    notebook_path = NOTEBOOKS / 'gray_scott_profile_horizon_tags.ipynb'

    svg_path.write_text(render_profile_horizon_tags(study, SCAN_FEEDS, SCAN_KILLS))
    export_png_from_svg(svg_path, png_path, size=2200, dpi=300)

    with csv_path.open('w', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow([
            'feed',
            'kill',
            'stability_class',
            'agreement_count',
            'majority_tag',
            'late_active_fraction_span',
            'total_active_delta_span',
            'center_tag',
            'double_tag',
            'ring_tag',
            'center_late_active_fraction',
            'double_late_active_fraction',
            'ring_late_active_fraction',
            'center_total_active_delta',
            'double_total_active_delta',
            'ring_total_active_delta',
            'reversing_profiles',
        ])
        for row in study.rows:
            center = row.row_for('center')
            double = row.row_for('double')
            ring = row.row_for('ring')
            writer.writerow([
                row.feed,
                row.kill,
                row.stability_class,
                row.agreement_count,
                row.majority_tag or '',
                row.late_active_fraction_span,
                row.total_active_delta_span,
                center.tag,
                double.tag,
                ring.tag,
                center.late_metrics.active_fraction,
                double.late_metrics.active_fraction,
                ring.late_metrics.active_fraction,
                center.total_active_delta,
                double.total_active_delta,
                ring.total_active_delta,
                ','.join(row.reversing_profiles),
            ])

    stability_counts = Counter(row.stability_class for row in study.rows)
    profile_counts = {
        profile: Counter(row.row_for(profile).tag for row in study.rows)
        for profile in study.profiles
    }
    largest_span = max(study.rows, key=lambda row: row.late_active_fraction_span)
    three_way = next((spotlight for spotlight in study.spotlights if spotlight.title == 'Three-way tag split'), None)
    rescue = next((spotlight for spotlight in study.spotlights if spotlight.title == 'Profile rescue cell'), None)
    stable_active = next((spotlight for spotlight in study.spotlights if spotlight.title == 'Stable active counterexample'), None)

    lines = [
        '# Gray-Scott seed-profile horizon tags sidecar',
        '',
        'The earlier horizon-tag card made one honest point: the unsettled cells were not one generic caution blob. But it still left one question open: **does that late-horizon fate belong to the chemistry cell itself, or can the seeded geometry still change the tag?**',
        '',
        f'This sidecar keeps the same `{study.size}×{study.size}` grid, the same `{study.early_steps}` → `{study.middle_steps}` → `{study.late_steps}` horizon rule, and the same feed/kill scan. It only swaps between `{seed_profile_label("center")}`, `{seed_profile_label("double")}`, and `{seed_profile_label("ring")}`.',
        '',
        '## Tag agreement across profiles',
        '',
        f'- stable cells (`3x`): `{stability_counts.get(PROFILE_HORIZON_STABLE, 0)}`',
        f'- two-against-one flips (`2+1`): `{stability_counts.get(PROFILE_HORIZON_SINGLE_FLIP, 0)}`',
        f'- three-way splits: `{stability_counts.get(PROFILE_HORIZON_THREE_WAY_SPLIT, 0)}`',
        f'- largest late active-fraction span: `F = {largest_span.feed:.3f}`, `k = {largest_span.kill:.3f}`, `span = {largest_span.late_active_fraction_span:.3f}`',
        '',
        '## Per-profile tag counts',
        '',
        f'- centered square: settled `{profile_counts["center"].get(HORIZON_TAG_SETTLED, 0)}`, growing `{profile_counts["center"].get(HORIZON_TAG_GROWING, 0)}`, fading `{profile_counts["center"].get(HORIZON_TAG_FADING, 0)}`, reversing `{profile_counts["center"].get(HORIZON_TAG_REVERSING, 0)}`',
        f'- split twin patches: settled `{profile_counts["double"].get(HORIZON_TAG_SETTLED, 0)}`, growing `{profile_counts["double"].get(HORIZON_TAG_GROWING, 0)}`, fading `{profile_counts["double"].get(HORIZON_TAG_FADING, 0)}`, reversing `{profile_counts["double"].get(HORIZON_TAG_REVERSING, 0)}`',
        f'- annulus shell: settled `{profile_counts["ring"].get(HORIZON_TAG_SETTLED, 0)}`, growing `{profile_counts["ring"].get(HORIZON_TAG_GROWING, 0)}`, fading `{profile_counts["ring"].get(HORIZON_TAG_FADING, 0)}`, reversing `{profile_counts["ring"].get(HORIZON_TAG_REVERSING, 0)}`',
        '',
        '## The useful read',
        '',
        f'- three-way split example: `F = {three_way.feed:.3f}`, `k = {three_way.kill:.3f}`' if three_way is not None else '- no three-way split cleared the bounded grid on this run',
        f'- profile rescue example: `F = {rescue.feed:.3f}`, `k = {rescue.kill:.3f}`' if rescue is not None else '- no rescue cell crossed the bounded threshold on this run',
        f'- stable active counterexample: `F = {stable_active.feed:.3f}`, `k = {stable_active.kill:.3f}`' if stable_active is not None else '- no active stable counterexample was needed on this run',
        '- the core point is that the late-horizon tag is not always a chemistry-only identity. Some cells keep one shared tag across seed profiles, but others move between fading, growing, and reversing even though feed, kill, lattice, and horizon rule never changed.',
        '- that makes the old reversing lane narrower and more conditional than the center-profile card alone suggested. The seed geometry can erase it, move it, or create a different late-horizon caution altogether.',
        '',
        '## Caveat',
        '',
        'This is still a bounded three-profile audit, not a universal initialization theorem. It makes the caveat packet sharper because it shows where the late-horizon read survives the profile swap and where it does not.',
        '',
        'Open `art/gray-scott-profile-horizon-tags.png`, `art/gray-scott-profile-horizon-tags.csv`, and `notebooks/gray_scott_profile_horizon_tags.ipynb` together next.',
    ]
    report_path.write_text('\n'.join(lines) + '\n')

    notebook = {
        'cells': [
            {
                'cell_type': 'markdown',
                'metadata': {},
                'source': [
                    '# Gray-Scott seed-profile horizon tags\n',
                    '\n',
                    'This notebook is the slower companion to `reports/profile-horizon-tags-sidecar.md`.\n',
                    '\n',
                    'The bounded question here is simple: **if the chemistry stays fixed, how much of the late-horizon tag survives a swap from one seed geometry to another?**\n',
                ],
            },
            {
                'cell_type': 'code',
                'execution_count': None,
                'metadata': {},
                'outputs': [],
                'source': [
                    'from gray_scott_lab.analysis import SCAN_FEEDS, SCAN_KILLS, study_profile_horizon_tags\n',
                    '\n',
                    'study = study_profile_horizon_tags(SCAN_FEEDS, SCAN_KILLS, early_steps=700, middle_steps=1400, late_steps=2800)\n',
                    '[(row.feed, row.kill, row.stability_class, tuple(entry.row.tag for entry in row.profile_rows), round(row.late_active_fraction_span, 3)) for row in study.rows]\n',
                ],
            },
            {
                'cell_type': 'markdown',
                'metadata': {},
                'source': [
                    '## The new figure\n',
                    '\n',
                    '![Gray-Scott seed-profile horizon tags](../art/gray-scott-profile-horizon-tags.png)\n',
                    '\n',
                    'Read it in three passes:\n',
                    '\n',
                    '1. compare the three per-profile tag maps directly\n',
                    '2. use the agreement map to find cells where the tag is actually profile-stable\n',
                    '3. use the late-span map and spotlight rows to see whether the tag drift is just a relabel or a real fate change\n',
                ],
            },
            {
                'cell_type': 'markdown',
                'metadata': {},
                'source': [
                    '## Problems worth trying next\n',
                    '\n',
                    '1. Repeat this same profile-tag study on one larger lattice only if the agreement counts actually change.\n',
                    '2. Add one second reaction-diffusion model only if it reveals a genuinely different profile-versus-horizon failure split.\n',
                    '3. Test one extra bounded seed profile only if it changes the profile-stability map instead of just adding one more cosmetic variant.\n',
                ],
            },
        ],
        'metadata': {
            'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'},
            'language_info': {'name': 'python', 'version': '3.11'},
        },
        'nbformat': 4,
        'nbformat_minor': 5,
    }
    notebook_path.write_text(json.dumps(notebook, indent=2) + '\n')
    return svg_path, csv_path, report_path, notebook_path


def main() -> None:
    atlas_path = write_atlas()
    map_path, csv_path = write_metric_map()
    report_path = write_report()
    timeline_path, timeline_csv_path, timeline_report_path, timeline_notebook_path = write_time_evolution()
    horizon_path, horizon_csv_path, horizon_report_path, horizon_notebook_path = write_horizon_comparison()
    grid_size_path, grid_size_csv_path, grid_size_report_path, grid_size_notebook_path = write_grid_size_comparison()
    horizon_tags_path, horizon_tags_csv_path, horizon_tags_report_path, horizon_tags_notebook_path = write_horizon_tags()
    init_path, init_csv_path, init_report_path, init_notebook_path = write_initialization_sensitivity()
    profile_horizon_path, profile_horizon_csv_path, profile_horizon_report_path, profile_horizon_notebook_path = write_profile_horizon_tags()
    print(atlas_path)
    print(map_path)
    print(csv_path)
    print(report_path)
    print(timeline_path)
    print(timeline_csv_path)
    print(timeline_report_path)
    print(timeline_notebook_path)
    print(horizon_path)
    print(horizon_csv_path)
    print(horizon_report_path)
    print(horizon_notebook_path)
    print(grid_size_path)
    print(grid_size_csv_path)
    print(grid_size_report_path)
    print(grid_size_notebook_path)
    print(horizon_tags_path)
    print(horizon_tags_csv_path)
    print(horizon_tags_report_path)
    print(horizon_tags_notebook_path)
    print(init_path)
    print(init_csv_path)
    print(init_report_path)
    print(init_notebook_path)
    print(profile_horizon_path)
    print(profile_horizon_csv_path)
    print(profile_horizon_report_path)
    print(profile_horizon_notebook_path)


if __name__ == '__main__':
    main()
