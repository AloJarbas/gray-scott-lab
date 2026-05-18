from __future__ import annotations

from html import escape
from pathlib import Path
import shutil
import subprocess
import tempfile

from .analysis import ParameterScanRow, PresetStudy, TimeEvolutionStudy


def svg_text(x: float, y: float, text: str, klass: str, anchor: str = 'start') -> str:
    return f'<text x="{x:.1f}" y="{y:.1f}" class="{klass}" text-anchor="{anchor}">{escape(text)}</text>'


def svg_paragraph(x: float, y: float, lines: list[str], klass: str, *, line_height: float = 20.0) -> str:
    spans = [f'<tspan x="{x:.1f}" dy="0">{escape(lines[0])}</tspan>']
    spans.extend(f'<tspan x="{x:.1f}" dy="{line_height:.1f}">{escape(line)}</tspan>' for line in lines[1:])
    return f'<text x="{x:.1f}" y="{y:.1f}" class="{klass}">{"".join(spans)}</text>'


def interpolate_color(stops: list[tuple[float, tuple[int, int, int]]], value: float) -> str:
    value = max(0.0, min(1.0, value))
    for (left_value, left_color), (right_value, right_color) in zip(stops, stops[1:]):
        if value <= right_value:
            span = right_value - left_value
            mix = 0.0 if span == 0 else (value - left_value) / span
            rgb = tuple(round(left + (right - left) * mix) for left, right in zip(left_color, right_color))
            return '#%02x%02x%02x' % rgb
    return '#%02x%02x%02x' % stops[-1][1]


PATTERN_STOPS = [
    (0.0, (8, 15, 32)),
    (0.25, (33, 82, 118)),
    (0.55, (45, 171, 145)),
    (0.8, (245, 208, 66)),
    (1.0, (251, 113, 133)),
]

HEATMAP_STOPS = [
    (0.0, (15, 23, 42)),
    (0.4, (37, 99, 235)),
    (0.7, (16, 185, 129)),
    (1.0, (250, 204, 21)),
]


def pattern_color(value: float, *, vmax: float = 0.45) -> str:
    return interpolate_color(PATTERN_STOPS, min(1.0, value / vmax))


def metric_color(value: float, vmin: float, vmax: float) -> str:
    if vmax <= vmin:
        return interpolate_color(HEATMAP_STOPS, 0.0)
    return interpolate_color(HEATMAP_STOPS, (value - vmin) / (vmax - vmin))


def metric_label_color(value: float, vmin: float, vmax: float) -> str:
    if vmax <= vmin:
        return '#e2e8f0'
    normalized = (value - vmin) / (vmax - vmin)
    return '#0f172a' if normalized > 0.72 else '#e2e8f0'


def base_svg(width: int, height: int, title: str, subtitle: str) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        f'<title>{escape(title)}</title>',
        f'<desc>{escape(subtitle)}</desc>',
        '<style>',
        'svg { background: #07111f; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }',
        '.title { fill: #e2e8f0; font-size: 30px; font-weight: 700; }',
        '.subtitle { fill: #94a3b8; font-size: 16px; }',
        '.label { fill: #cbd5e1; font-size: 18px; font-weight: 600; }',
        '.small { fill: #94a3b8; font-size: 14px; }',
        '.metric { fill: #f8fafc; font-size: 14px; }',
        '.axis { stroke: #475569; stroke-width: 1.5; }',
        '.panel { fill: #0f172a; stroke: #334155; stroke-width: 2; rx: 18; }',
        '.cell-label { fill: #e2e8f0; font-size: 13px; font-weight: 600; }',
        '</style>',
        svg_text(56, 54, title, 'title'),
        svg_text(56, 82, subtitle, 'subtitle'),
    ]


def render_pattern_atlas(studies: list[PresetStudy]) -> str:
    width, height = 1260, 1320
    parts = base_svg(
        width,
        height,
        'Gray-Scott pattern atlas',
        'A pure-Python reaction-diffusion atlas for seeing how feed and kill steer sparse spots, worm bands, and denser labyrinths.',
    )

    panel_w = 544
    panel_h = 554
    pixel = 4.0
    positions = [(56, 128), (660, 128), (56, 718), (660, 718)]

    for study, (left, top) in zip(studies, positions):
        parts.append(f'<rect x="{left}" y="{top}" width="{panel_w}" height="{panel_h}" class="panel"/>')
        parts.append(svg_text(left + 22, top + 30, study.preset.name, 'label'))
        parts.append(svg_text(left + 22, top + 54, f'feed={study.preset.feed:.3f}, kill={study.preset.kill:.3f}, steps={study.preset.steps}', 'small'))
        grid_left = left + 22
        grid_top = top + 78
        for row_index, row in enumerate(study.state.v):
            for col_index, value in enumerate(row):
                parts.append(
                    f'<rect x="{grid_left + col_index * pixel:.1f}" y="{grid_top + row_index * pixel:.1f}" width="{pixel + 0.2:.1f}" height="{pixel + 0.2:.1f}" fill="{pattern_color(value)}"/>'
                )
        metrics_y = top + 402
        parts.append(svg_paragraph(left + 22, metrics_y, [
            f'mean V: {study.metrics.mean_v:.3f}',
            f'V std: {study.metrics.std_v:.3f}',
            f'active > 0.15: {study.metrics.active_fraction:.1%}',
            f'edge density: {study.metrics.edge_density:.4f}',
        ], 'metric', line_height=24.0))
        parts.append(svg_paragraph(left + 264, metrics_y, [
            'Read:',
            'low active fraction = sparse islands',
            'high edge density = sharper fronts',
            'higher fill = denser labyrinths',
        ], 'small', line_height=22.0))

    parts.append(svg_paragraph(56, 1064, [
        'The atlas uses the V concentration field after a fixed number of Euler steps.',
        'It is not a full phase diagram; it is a reproducible visual packet that makes regime differences visible on day one.',
    ], 'small', line_height=20.0))
    parts.append('</svg>')
    return '\n'.join(parts) + '\n'


def render_metric_map(rows: list[ParameterScanRow], feeds: tuple[float, ...], kills: tuple[float, ...]) -> str:
    width, height = 1040, 1280
    parts = base_svg(
        width,
        height,
        'Gray-Scott parameter scan',
        'A coarse feed-vs-kill sweep turns the chemistry knobs into a measurable map.',
    )

    active_values = [row.metrics.active_fraction for row in rows]
    edge_values = [row.metrics.edge_density for row in rows]
    cell = 82
    maps = [
        ('active fraction', active_values, lambda r: r.metrics.active_fraction, 168),
        ('edge density', edge_values, lambda r: r.metrics.edge_density, 694),
    ]

    def lookup(feed: float, kill: float) -> ParameterScanRow:
        for row in rows:
            if row.feed == feed and row.kill == kill:
                return row
        raise KeyError((feed, kill))

    left = 72
    for title, values, getter, top in maps:
        vmin = min(values)
        vmax = max(values)
        parts.append(f'<rect x="{left}" y="{top}" width="{cell * len(feeds) + 130}" height="{cell * len(kills) + 120}" class="panel"/>')
        parts.append(svg_text(left + 24, top + 34, title, 'label'))
        parts.append(svg_text(left + 24, top + 58, f'min={vmin:.4f}, max={vmax:.4f}', 'small'))
        grid_left = left + 24
        grid_top = top + 90

        for column, feed in enumerate(feeds):
            x = grid_left + column * cell
            parts.append(svg_text(x + cell / 2, grid_top - 18, f'{feed:.3f}', 'small', 'middle'))
        parts.append(svg_text(grid_left + cell * len(feeds) / 2, grid_top - 44, 'feed rate F', 'small', 'middle'))

        for row_index, kill in enumerate(kills):
            y = grid_top + row_index * cell
            parts.append(svg_text(grid_left - 18, y + cell / 2 + 6, f'{kill:.3f}', 'small', 'end'))
            for column, feed in enumerate(feeds):
                x = grid_left + column * cell
                entry = lookup(feed, kill)
                value = getter(entry)
                parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{cell - 6}" height="{cell - 6}" fill="{metric_color(value, vmin, vmax)}" rx="10"/>')
                parts.append(f'<text x="{x + (cell - 6) / 2:.1f}" y="{y + cell / 2 - 2:.1f}" class="cell-label" text-anchor="middle" fill="{metric_label_color(value, vmin, vmax)}">{value:.3f}</text>')

    parts.append(svg_paragraph(72, 1188, [
        'Read the pair of maps together:',
        'active fraction tracks how much of the field stays chemically busy, while edge density tracks how sharp the interfaces remain.',
        'The middle band is where the patterns stop being isolated islands but have not yet blurred into a mostly filled field.',
    ], 'small', line_height=22.0))
    parts.append('</svg>')
    return '\n'.join(parts) + '\n'


def render_time_evolution(study: TimeEvolutionStudy) -> str:
    width, height = 1340, 1240
    parts = base_svg(
        width,
        height,
        'Gray-Scott time evolution',
        f'{study.preset.name} grows from one seeded patch into a full regime. The snapshots show shape; the curves show what the chemistry is doing over time.',
    )

    snapshot_positions = [
        (50, 132), (470, 132), (890, 132),
        (50, 466), (470, 466), (890, 466),
    ]
    panel_w = 400
    panel_h = 300
    pixel = 3.2

    for (step_count, state), (left, top) in zip(study.snapshots, snapshot_positions):
        parts.append(f'<rect x="{left}" y="{top}" width="{panel_w}" height="{panel_h}" class="panel"/>')
        parts.append(svg_text(left + 18, top + 28, f'step {step_count}', 'label'))
        metrics = next((point.metrics for point in study.timeline if point.step == step_count), None)
        if metrics is None:
            from .analysis import measure_pattern
            metrics = measure_pattern(state)
        parts.append(svg_text(left + 18, top + 50, f'active={metrics.active_fraction:.1%}, edge={metrics.edge_density:.4f}', 'small'))
        grid_left = left + 18
        grid_top = top + 68
        for row_index, row in enumerate(state.v):
            for col_index, value in enumerate(row):
                parts.append(
                    f'<rect x="{grid_left + col_index * pixel:.1f}" y="{grid_top + row_index * pixel:.1f}" width="{pixel + 0.15:.1f}" height="{pixel + 0.15:.1f}" fill="{pattern_color(value)}"/>'
                )

    def plot_metric_panel(left: float, top: float, title: str, subtitle: str, values: list[float], color: str, y_label: str) -> None:
        panel_w = 590
        panel_h = 250
        plot_left = left + 54
        plot_top = top + 74
        plot_right = left + panel_w - 34
        plot_bottom = top + panel_h - 42
        y_min = 0.0
        y_max = max(values) * 1.12 if max(values) > 0 else 1.0
        max_step = max(point.step for point in study.timeline)

        parts.append(f'<rect x="{left}" y="{top}" width="{panel_w}" height="{panel_h}" class="panel"/>')
        parts.append(svg_text(left + 18, top + 28, title, 'label'))
        parts.append(svg_text(left + 18, top + 50, subtitle, 'small'))

        for fraction in (0.0, 0.25, 0.5, 0.75, 1.0):
            x = plot_left + (plot_right - plot_left) * fraction
            parts.append(f'<line x1="{x:.1f}" y1="{plot_top:.1f}" x2="{x:.1f}" y2="{plot_bottom:.1f}" class="axis" opacity="0.35"/>')
            parts.append(svg_text(x, plot_bottom + 22, f'{round(max_step * fraction):d}', 'small', 'middle'))
        for fraction in (0.0, 0.33, 0.66, 1.0):
            y_value = y_min + (y_max - y_min) * fraction
            y = plot_bottom - (plot_bottom - plot_top) * fraction
            parts.append(f'<line x1="{plot_left:.1f}" y1="{y:.1f}" x2="{plot_right:.1f}" y2="{y:.1f}" class="axis" opacity="0.35"/>')
            parts.append(svg_text(plot_left - 12, y + 5, f'{y_value:.3f}', 'small', 'end'))

        parts.append(f'<line x1="{plot_left:.1f}" y1="{plot_bottom:.1f}" x2="{plot_right:.1f}" y2="{plot_bottom:.1f}" class="axis"/>')
        parts.append(f'<line x1="{plot_left:.1f}" y1="{plot_top:.1f}" x2="{plot_left:.1f}" y2="{plot_bottom:.1f}" class="axis"/>')
        parts.append(svg_text((plot_left + plot_right) / 2, plot_bottom + 44, 'simulation step', 'small', 'middle'))
        parts.append(svg_text(plot_left, plot_top - 10, y_label, 'small'))

        polyline_points = []
        for point, value in zip(study.timeline, values):
            x = plot_left + (plot_right - plot_left) * point.step / max_step
            y = plot_bottom if y_max == y_min else plot_bottom - (plot_bottom - plot_top) * (value - y_min) / (y_max - y_min)
            polyline_points.append(f'{x:.2f},{y:.2f}')
            parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3.1" fill="{color}"/>')
        parts.append(f'<polyline points="{" ".join(polyline_points)}" fill="none" stroke="{color}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>')

    active_values = [point.metrics.active_fraction for point in study.timeline]
    edge_values = [point.metrics.edge_density for point in study.timeline]
    plot_metric_panel(70, 830, 'active fraction over time', 'How much of the field stays chemically busy as the pattern grows.', active_values, '#38bdf8', 'active')
    plot_metric_panel(680, 830, 'edge density over time', 'How sharp the interfaces stay while the regime fills in.', edge_values, '#f97316', 'edge')

    peak_active = max(study.timeline, key=lambda point: point.metrics.active_fraction)
    peak_edge = max(study.timeline, key=lambda point: point.metrics.edge_density)
    parts.append(svg_paragraph(70, 1122, [
        f'Peak activity lands around step {peak_active.step} at {peak_active.metrics.active_fraction:.1%}.',
        f'Peak edge density lands around step {peak_edge.step} at {peak_edge.metrics.edge_density:.4f}.',
        'That is the useful split: filling in and sharpening are related, but they are not the same process.',
    ], 'small', line_height=22.0))
    parts.append('</svg>')
    return '\n'.join(parts) + '\n'


def export_png_from_svg(svg_path: str | Path, png_path: str | Path, *, size: int = 1800, dpi: int = 300) -> bool:
    svg_file = Path(svg_path).resolve()
    png_file = Path(png_path).resolve()
    qlmanage = shutil.which('qlmanage')
    if qlmanage is None:
        return False

    with tempfile.TemporaryDirectory() as tmpdir:
        subprocess.run(
            [qlmanage, '-t', '-s', str(size), '-o', tmpdir, str(svg_file)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        generated = Path(tmpdir) / f'{svg_file.name}.png'
        if not generated.exists():
            raise FileNotFoundError(f'Quick Look did not generate {generated}')
        png_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(generated, png_file)

    sips = shutil.which('sips')
    if sips is not None:
        subprocess.run(
            [sips, '--setProperty', 'dpiWidth', str(dpi), '--setProperty', 'dpiHeight', str(dpi), str(png_file)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    return True
