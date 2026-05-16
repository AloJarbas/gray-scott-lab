from __future__ import annotations

import csv
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gray_scott_lab.analysis import CURATED_PRESETS, SCAN_FEEDS, SCAN_KILLS, scan_parameter_grid, study_presets
from gray_scott_lab.render import export_png_from_svg, render_metric_map, render_pattern_atlas
ART = ROOT / 'art'
REPORTS = ROOT / 'reports'


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


def main() -> None:
    atlas_path = write_atlas()
    map_path, csv_path = write_metric_map()
    report_path = write_report()
    print(atlas_path)
    print(map_path)
    print(csv_path)
    print(report_path)


if __name__ == '__main__':
    main()
