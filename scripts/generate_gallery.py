from __future__ import annotations

import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gray_scott_lab.analysis import CURATED_PRESETS, SCAN_FEEDS, SCAN_KILLS, TIME_EVOLUTION_PRESET, scan_parameter_grid, study_presets, study_time_evolution
from gray_scott_lab.render import export_png_from_svg, render_metric_map, render_pattern_atlas, render_time_evolution
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


def main() -> None:
    atlas_path = write_atlas()
    map_path, csv_path = write_metric_map()
    report_path = write_report()
    timeline_path, timeline_csv_path, timeline_report_path, timeline_notebook_path = write_time_evolution()
    print(atlas_path)
    print(map_path)
    print(csv_path)
    print(report_path)
    print(timeline_path)
    print(timeline_csv_path)
    print(timeline_report_path)
    print(timeline_notebook_path)


if __name__ == '__main__':
    main()
