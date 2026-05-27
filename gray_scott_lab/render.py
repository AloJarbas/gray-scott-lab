from __future__ import annotations

from collections import Counter
from html import escape
from pathlib import Path
import shutil
import subprocess
import tempfile

from .analysis import GridSizeComparisonStudy, HorizonComparisonStudy, HorizonTagStudy, HORIZON_TAG_FADING, HORIZON_TAG_GROWING, HORIZON_TAG_REVERSING, HORIZON_TAG_SETTLED, InitializationSensitivityStudy, ParameterScanRow, PresetStudy, ProfileHorizonTagStudy, PROFILE_HORIZON_SINGLE_FLIP, PROFILE_HORIZON_STABLE, PROFILE_HORIZON_THREE_WAY_SPLIT, TimeEvolutionStudy
from .core import GrayScottState, seed_profile_label


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

DELTA_STOPS = [
    (0.0, (30, 64, 175)),
    (0.5, (15, 23, 42)),
    (1.0, (245, 158, 11)),
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


def delta_color(value: float, scale: float) -> str:
    if scale <= 0.0:
        return interpolate_color(DELTA_STOPS, 0.5)
    normalized = 0.5 + 0.5 * (value / scale)
    return interpolate_color(DELTA_STOPS, normalized)


def delta_label_color(value: float, scale: float) -> str:
    if scale <= 0.0:
        return '#e2e8f0'
    return '#0f172a' if abs(value) / scale < 0.24 else '#f8fafc'


def horizon_tag_color(tag: str) -> str:
    mapping = {
        HORIZON_TAG_SETTLED: '#16a34a',
        HORIZON_TAG_GROWING: '#0ea5e9',
        HORIZON_TAG_FADING: '#f97316',
        HORIZON_TAG_REVERSING: '#a855f7',
    }
    return mapping[tag]


def horizon_tag_short_label(tag: str) -> str:
    mapping = {
        HORIZON_TAG_SETTLED: 'SET',
        HORIZON_TAG_GROWING: 'UP',
        HORIZON_TAG_FADING: 'DOWN',
        HORIZON_TAG_REVERSING: 'FLIP',
    }
    return mapping[tag]


def horizon_tag_long_label(tag: str) -> str:
    mapping = {
        HORIZON_TAG_SETTLED: 'settled',
        HORIZON_TAG_GROWING: 'late-growing',
        HORIZON_TAG_FADING: 'late-fading',
        HORIZON_TAG_REVERSING: 'reversing',
    }
    return mapping[tag]


def profile_horizon_stability_color(label: str) -> str:
    mapping = {
        PROFILE_HORIZON_STABLE: '#16a34a',
        PROFILE_HORIZON_SINGLE_FLIP: '#f59e0b',
        PROFILE_HORIZON_THREE_WAY_SPLIT: '#ec4899',
    }
    return mapping[label]


def profile_horizon_stability_short_label(label: str) -> str:
    mapping = {
        PROFILE_HORIZON_STABLE: '3x',
        PROFILE_HORIZON_SINGLE_FLIP: '2+1',
        PROFILE_HORIZON_THREE_WAY_SPLIT: '3-way',
    }
    return mapping[label]


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


def render_horizon_comparison(study: HorizonComparisonStudy, feeds: tuple[float, ...], kills: tuple[float, ...]) -> str:
    width, height = 1220, 1540
    parts = base_svg(
        width,
        height,
        'Gray-Scott horizon comparison',
        f'The same feed-vs-kill grid at {study.short_steps} and {study.long_steps} steps. This is the cutoff check: which cells were already real, and which ones were still moving?',
    )

    cell = 82
    panel_w = cell * len(feeds) + 136
    panel_h = cell * len(kills) + 150
    positions = [
        (72, 156),
        (648, 156),
        (72, 748),
        (648, 748),
    ]

    lookup = {(row.feed, row.kill): row for row in study.rows}
    short_active = [row.short_metrics.active_fraction for row in study.rows]
    long_active = [row.long_metrics.active_fraction for row in study.rows]
    active_delta = [row.active_fraction_delta for row in study.rows]
    edge_delta = [row.edge_density_delta for row in study.rows]
    active_vmin = min(short_active + long_active)
    active_vmax = max(short_active + long_active)
    active_delta_scale = max(abs(value) for value in active_delta) if active_delta else 1.0
    edge_delta_scale = max(abs(value) for value in edge_delta) if edge_delta else 1.0

    peak_growth = max(study.rows, key=lambda row: row.active_fraction_delta)
    biggest_fade = min(study.rows, key=lambda row: row.active_fraction_delta)
    sharpest_gain = max(study.rows, key=lambda row: row.edge_density_delta)
    strongest_smoothing = min(study.rows, key=lambda row: row.edge_density_delta)

    def draw_panel(
        left: float,
        top: float,
        title: str,
        subtitle: str,
        *,
        getter,
        formatter,
        color_fn,
        label_color_fn,
    ) -> None:
        parts.append(f'<rect x="{left}" y="{top}" width="{panel_w}" height="{panel_h}" class="panel"/>')
        parts.append(svg_text(left + 24, top + 34, title, 'label'))
        parts.append(svg_paragraph(left + 24, top + 58, [subtitle], 'small', line_height=18.0))
        grid_left = left + 24
        grid_top = top + 116

        for column, feed in enumerate(feeds):
            x = grid_left + column * cell
            parts.append(svg_text(x + cell / 2, grid_top - 18, f'{feed:.3f}', 'small', 'middle'))
        parts.append(svg_text(grid_left + cell * len(feeds) / 2, grid_top - 44, 'feed rate F', 'small', 'middle'))

        for row_index, kill in enumerate(kills):
            y = grid_top + row_index * cell
            parts.append(svg_text(grid_left - 18, y + cell / 2 + 6, f'{kill:.3f}', 'small', 'end'))
            for column, feed in enumerate(feeds):
                x = grid_left + column * cell
                entry = lookup[(feed, kill)]
                value = getter(entry)
                fill = color_fn(value)
                label_fill = label_color_fn(value)
                parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{cell - 6}" height="{cell - 6}" fill="{fill}" rx="10"/>')
                parts.append(f'<text x="{x + (cell - 6) / 2:.1f}" y="{y + cell / 2 - 2:.1f}" class="cell-label" text-anchor="middle" fill="{label_fill}">{formatter(value)}</text>')

    draw_panel(
        *positions[0],
        f'active fraction at {study.short_steps} steps',
        'The early map: what still looks chemically busy before the longer run settles.',
        getter=lambda row: row.short_metrics.active_fraction,
        formatter=lambda value: f'{value:.3f}',
        color_fn=lambda value: metric_color(value, active_vmin, active_vmax),
        label_color_fn=lambda value: metric_label_color(value, active_vmin, active_vmax),
    )
    draw_panel(
        *positions[1],
        f'active fraction change ({study.long_steps} - {study.short_steps})',
        'Positive = more occupied later. Negative = early overread.',
        getter=lambda row: row.active_fraction_delta,
        formatter=lambda value: f'{value:+.3f}',
        color_fn=lambda value: delta_color(value, active_delta_scale),
        label_color_fn=lambda value: delta_label_color(value, active_delta_scale),
    )
    draw_panel(
        *positions[2],
        f'active fraction at {study.long_steps} steps',
        'The later map: the same grid after the longer chemical horizon.',
        getter=lambda row: row.long_metrics.active_fraction,
        formatter=lambda value: f'{value:.3f}',
        color_fn=lambda value: metric_color(value, active_vmin, active_vmax),
        label_color_fn=lambda value: metric_label_color(value, active_vmin, active_vmax),
    )
    draw_panel(
        *positions[3],
        f'edge-density change ({study.long_steps} - {study.short_steps})',
        'Positive = sharper later fronts. Negative = smoothing or collapse.',
        getter=lambda row: row.edge_density_delta,
        formatter=lambda value: f'{value:+.3f}',
        color_fn=lambda value: delta_color(value, edge_delta_scale),
        label_color_fn=lambda value: delta_label_color(value, edge_delta_scale),
    )

    parts.append(svg_paragraph(72, 1350, [
        f'Biggest active growth: F={peak_growth.feed:.3f}, k={peak_growth.kill:.3f}, Δactive={peak_growth.active_fraction_delta:+.3f}.',
        f'Biggest fade: F={biggest_fade.feed:.3f}, k={biggest_fade.kill:.3f}, Δactive={biggest_fade.active_fraction_delta:+.3f}.',
        f'Sharpest late front growth: F={sharpest_gain.feed:.3f}, k={sharpest_gain.kill:.3f}, Δedge={sharpest_gain.edge_density_delta:+.4f}.',
        f'Strongest smoothing: F={strongest_smoothing.feed:.3f}, k={strongest_smoothing.kill:.3f}, Δedge={strongest_smoothing.edge_density_delta:+.4f}.',
    ], 'small', line_height=22.0))
    parts.append(svg_paragraph(72, 1452, [
        'This is the practical read: the coarse map was useful, but not every bright cell had finished becoming itself.',
        'Some settings keep growing into clearer bands, while others looked active early and then cooled almost all the way out.',
    ], 'small', line_height=22.0))
    parts.append('</svg>')
    return '\n'.join(parts) + '\n'


def render_grid_size_comparison(study: GridSizeComparisonStudy, feeds: tuple[float, ...], kills: tuple[float, ...]) -> str:
    width, height = 1220, 1540
    parts = base_svg(
        width,
        height,
        'Gray-Scott grid-size comparison',
        f'Same feed-vs-kill scan after {study.steps} steps on {study.small_size}x{study.small_size} and {study.large_size}x{study.large_size} lattices. A finite-size check for which cells stay robust in a bigger arena.',
    )

    cell = 82
    panel_w = cell * len(feeds) + 136
    panel_h = cell * len(kills) + 150
    positions = [
        (72, 156),
        (648, 156),
        (72, 748),
        (648, 748),
    ]

    lookup = {(row.feed, row.kill): row for row in study.rows}
    small_active = [row.small_metrics.active_fraction for row in study.rows]
    large_active = [row.large_metrics.active_fraction for row in study.rows]
    active_delta = [row.active_fraction_delta for row in study.rows]
    edge_delta = [row.edge_density_delta for row in study.rows]
    active_vmin = min(small_active + large_active)
    active_vmax = max(small_active + large_active)
    active_delta_scale = max(abs(value) for value in active_delta) if active_delta else 1.0
    edge_delta_scale = max(abs(value) for value in edge_delta) if edge_delta else 1.0

    biggest_growth = max(study.rows, key=lambda row: row.active_fraction_delta)
    biggest_fade = min(study.rows, key=lambda row: row.active_fraction_delta)
    sharpest_gain = max(study.rows, key=lambda row: row.edge_density_delta)
    strongest_smoothing = min(study.rows, key=lambda row: row.edge_density_delta)

    def draw_panel(
        left: float,
        top: float,
        title: str,
        subtitle: str,
        *,
        getter,
        formatter,
        color_fn,
        label_color_fn,
    ) -> None:
        parts.append(f'<rect x="{left}" y="{top}" width="{panel_w}" height="{panel_h}" class="panel"/>')
        parts.append(svg_text(left + 24, top + 34, title, 'label'))
        parts.append(svg_paragraph(left + 24, top + 58, [subtitle], 'small', line_height=18.0))
        grid_left = left + 24
        grid_top = top + 116

        for column, feed in enumerate(feeds):
            x = grid_left + column * cell
            parts.append(svg_text(x + cell / 2, grid_top - 18, f'{feed:.3f}', 'small', 'middle'))
        parts.append(svg_text(grid_left + cell * len(feeds) / 2, grid_top - 44, 'feed rate F', 'small', 'middle'))

        for row_index, kill in enumerate(kills):
            y = grid_top + row_index * cell
            parts.append(svg_text(grid_left - 18, y + cell / 2 + 6, f'{kill:.3f}', 'small', 'end'))
            for column, feed in enumerate(feeds):
                x = grid_left + column * cell
                entry = lookup[(feed, kill)]
                value = getter(entry)
                fill = color_fn(value)
                label_fill = label_color_fn(value)
                parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{cell - 6}" height="{cell - 6}" fill="{fill}" rx="10"/>')
                parts.append(f'<text x="{x + (cell - 6) / 2:.1f}" y="{y + cell / 2 - 2:.1f}" class="cell-label" text-anchor="middle" fill="{label_fill}">{formatter(value)}</text>')

    draw_panel(
        *positions[0],
        f'active fraction at {study.small_size}×{study.small_size}',
        f'The smaller lattice with patch radius {study.small_patch_radius}.',
        getter=lambda row: row.small_metrics.active_fraction,
        formatter=lambda value: f'{value:.3f}',
        color_fn=lambda value: metric_color(value, active_vmin, active_vmax),
        label_color_fn=lambda value: metric_label_color(value, active_vmin, active_vmax),
    )
    draw_panel(
        *positions[1],
        f'active-fraction delta ({study.large_size} vs {study.small_size})',
        'Positive = busier on the larger lattice. Negative = the small box overread occupancy.',
        getter=lambda row: row.active_fraction_delta,
        formatter=lambda value: f'{value:+.3f}',
        color_fn=lambda value: delta_color(value, active_delta_scale),
        label_color_fn=lambda value: delta_label_color(value, active_delta_scale),
    )
    draw_panel(
        *positions[2],
        f'active fraction at {study.large_size}×{study.large_size}',
        f'The larger lattice with scaled patch radius {study.large_patch_radius}.',
        getter=lambda row: row.large_metrics.active_fraction,
        formatter=lambda value: f'{value:.3f}',
        color_fn=lambda value: metric_color(value, active_vmin, active_vmax),
        label_color_fn=lambda value: metric_label_color(value, active_vmin, active_vmax),
    )
    draw_panel(
        *positions[3],
        f'edge-density delta ({study.large_size} vs {study.small_size})',
        'Positive = sharper fronts on the larger lattice. Negative = smoothing or box bias.',
        getter=lambda row: row.edge_density_delta,
        formatter=lambda value: f'{value:+.3f}',
        color_fn=lambda value: delta_color(value, edge_delta_scale),
        label_color_fn=lambda value: delta_label_color(value, edge_delta_scale),
    )

    parts.append(svg_paragraph(72, 1350, [
        f'Biggest larger-lattice growth: F={biggest_growth.feed:.3f}, k={biggest_growth.kill:.3f}, Δactive={biggest_growth.active_fraction_delta:+.3f}.',
        f'Biggest larger-lattice fade: F={biggest_fade.feed:.3f}, k={biggest_fade.kill:.3f}, Δactive={biggest_fade.active_fraction_delta:+.3f}.',
        f'Sharpest larger-lattice front growth: F={sharpest_gain.feed:.3f}, k={sharpest_gain.kill:.3f}, Δedge={sharpest_gain.edge_density_delta:+.4f}.',
        f'Strongest larger-lattice smoothing: F={strongest_smoothing.feed:.3f}, k={strongest_smoothing.kill:.3f}, Δedge={strongest_smoothing.edge_density_delta:+.4f}.',
    ], 'small', line_height=22.0))
    parts.append(svg_paragraph(72, 1452, [
        'This is the practical read: some cells are genuinely robust, but others only look settled because the box is small.',
        'The larger lattice mostly confirms the coarse story, then points to the cells where finite-size drift still matters before the repo starts talking like it owns a phase diagram.',
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


def _draw_state_thumbnail(parts: list[str], *, state: GrayScottState, left: float, top: float, pixel: float = 4.2) -> None:
    for row_index, row in enumerate(state.v):
        for col_index, value in enumerate(row):
            parts.append(
                f'<rect x="{left + col_index * pixel:.1f}" y="{top + row_index * pixel:.1f}" width="{pixel + 0.15:.1f}" height="{pixel + 0.15:.1f}" fill="{pattern_color(value)}"/>'
            )


def render_horizon_tags(study: HorizonTagStudy, feeds: tuple[float, ...], kills: tuple[float, ...]) -> str:
    width, height = 1440, 1995
    parts = base_svg(
        width,
        height,
        'Gray-Scott horizon drift tags',
        f'The same feed-vs-kill grid at {study.early_steps}, {study.middle_steps}, and {study.late_steps} steps. A bounded tag pass for which cells settled, grew, faded, or reversed.',
    )

    cell = 82
    panel_w = cell * len(feeds) + 140
    panel_h = cell * len(kills) + 150
    left_panel = (72, 156)
    right_panel = (748, 156)
    lookup = {(row.feed, row.kill): row for row in study.rows}
    late_active = [row.late_active_delta for row in study.rows]
    late_scale = max(abs(value) for value in late_active) if late_active else 1.0
    counts = Counter(row.tag for row in study.rows)

    def draw_tag_map(left: float, top: float) -> None:
        parts.append(f'<rect x="{left}" y="{top}" width="{panel_w}" height="{panel_h}" class="panel"/>')
        parts.append(svg_text(left + 24, top + 34, 'bounded horizon tag map', 'label'))
        parts.append(svg_paragraph(left + 24, top + 58, [
            'Each cell reads the three-horizon active-fraction path only.',
            'Descriptive tags: settled, late-growing, late-fading, or reversing.',
        ], 'small', line_height=18.0))
        grid_left = left + 24
        grid_top = top + 116

        for column, feed in enumerate(feeds):
            x = grid_left + column * cell
            parts.append(svg_text(x + cell / 2, grid_top - 18, f'{feed:.3f}', 'small', 'middle'))
        parts.append(svg_text(grid_left + cell * len(feeds) / 2, grid_top - 44, 'feed rate F', 'small', 'middle'))

        for row_index, kill in enumerate(kills):
            y = grid_top + row_index * cell
            parts.append(svg_text(grid_left - 18, y + cell / 2 + 6, f'{kill:.3f}', 'small', 'end'))
            for column, feed in enumerate(feeds):
                x = grid_left + column * cell
                entry = lookup[(feed, kill)]
                tag = entry.tag
                parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{cell - 6}" height="{cell - 6}" fill="{horizon_tag_color(tag)}" rx="10"/>')
                parts.append(f'<text x="{x + (cell - 6) / 2:.1f}" y="{y + cell / 2 - 4:.1f}" class="cell-label" text-anchor="middle" fill="#f8fafc">{horizon_tag_short_label(tag)}</text>')
                parts.append(svg_text(x + (cell - 6) / 2, y + cell / 2 + 16, f'{entry.total_active_delta:+.2f}', 'small', 'middle'))

        legend_left = left + 24
        legend_top = top + panel_h - 30
        legend_items = [
            (HORIZON_TAG_SETTLED, f'{counts.get(HORIZON_TAG_SETTLED, 0)} settled'),
            (HORIZON_TAG_GROWING, f'{counts.get(HORIZON_TAG_GROWING, 0)} late-growing'),
            (HORIZON_TAG_FADING, f'{counts.get(HORIZON_TAG_FADING, 0)} late-fading'),
            (HORIZON_TAG_REVERSING, f'{counts.get(HORIZON_TAG_REVERSING, 0)} reversing'),
        ]
        for index, (tag, text) in enumerate(legend_items):
            x = legend_left + index * 150
            parts.append(f'<rect x="{x:.1f}" y="{legend_top - 14:.1f}" width="18" height="18" fill="{horizon_tag_color(tag)}" rx="5"/>')
            parts.append(svg_text(x + 26, legend_top, text, 'small'))

    def draw_late_delta(left: float, top: float) -> None:
        parts.append(f'<rect x="{left}" y="{top}" width="{panel_w}" height="{panel_h}" class="panel"/>')
        parts.append(svg_text(left + 24, top + 34, f'late active change ({study.late_steps} - {study.middle_steps})', 'label'))
        parts.append(svg_paragraph(left + 24, top + 58, [
            'This isolates the second leg only.',
            'Positive means late fill-in. Negative means the middle horizon overread the cell.',
        ], 'small', line_height=18.0))
        grid_left = left + 24
        grid_top = top + 116

        for column, feed in enumerate(feeds):
            x = grid_left + column * cell
            parts.append(svg_text(x + cell / 2, grid_top - 18, f'{feed:.3f}', 'small', 'middle'))
        parts.append(svg_text(grid_left + cell * len(feeds) / 2, grid_top - 44, 'feed rate F', 'small', 'middle'))

        for row_index, kill in enumerate(kills):
            y = grid_top + row_index * cell
            parts.append(svg_text(grid_left - 18, y + cell / 2 + 6, f'{kill:.3f}', 'small', 'end'))
            for column, feed in enumerate(feeds):
                x = grid_left + column * cell
                entry = lookup[(feed, kill)]
                value = entry.late_active_delta
                parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{cell - 6}" height="{cell - 6}" fill="{delta_color(value, late_scale)}" rx="10"/>')
                parts.append(f'<text x="{x + (cell - 6) / 2:.1f}" y="{y + cell / 2 - 2:.1f}" class="cell-label" text-anchor="middle" fill="{delta_label_color(value, late_scale)}">{value:+.3f}</text>')

        biggest_late_growth = max(study.rows, key=lambda row: row.late_active_delta)
        biggest_late_fade = min(study.rows, key=lambda row: row.late_active_delta)
        parts.append(svg_paragraph(left + 24, top + panel_h - 30, [
            f'Biggest late growth: F={biggest_late_growth.feed:.3f}, k={biggest_late_growth.kill:.3f}, Δactive={biggest_late_growth.late_active_delta:+.3f}.',
            f'Biggest late fade: F={biggest_late_fade.feed:.3f}, k={biggest_late_fade.kill:.3f}, Δactive={biggest_late_fade.late_active_delta:+.3f}.',
        ], 'small', line_height=18.0))

    draw_tag_map(*left_panel)
    draw_late_delta(*right_panel)

    parts.append(svg_paragraph(72, 780, [
        'Read the left panel as the bounded classifier and the right panel as the raw second-leg drift.',
        'Together they show that the unsettled cells do not all fail the same way: some keep growing, some fade out, and a smaller set overshoot and then reverse.',
    ], 'small', line_height=22.0))

    spotlight_top = 874
    panel_height = 238
    panel_gap = 18
    thumb_pixel = 2.7
    thumb_size = study.size * thumb_pixel
    subpanel_width = 392

    for index, spotlight in enumerate(study.spotlights):
        top = spotlight_top + index * (panel_height + panel_gap)
        parts.append(f'<rect x="72" y="{top}" width="1296" height="{panel_height}" class="panel"/>')
        parts.append(svg_text(96, top + 32, spotlight.title, 'label'))
        parts.append(svg_paragraph(96, top + 56, [spotlight.reason], 'small', line_height=18.0))
        for frame_index, frame in enumerate(spotlight.frames):
            left = 96 + frame_index * subpanel_width
            box_top = top + 86
            parts.append(f'<rect x="{left}" y="{box_top}" width="364" height="128" fill="#111c30" stroke="#334155" stroke-width="1.5" rx="14"/>')
            parts.append(svg_text(left + 16, box_top + 24, f'{frame.step} steps', 'label'))
            parts.append(svg_text(left + 16, box_top + 46, f'active={frame.metrics.active_fraction:.3f}, edge={frame.metrics.edge_density:.4f}, peak={frame.metrics.peak_v:.3f}', 'small'))
            _draw_state_thumbnail(parts, state=frame.state, left=left + 16, top=box_top + 58, pixel=thumb_pixel)
            text_left = left + 16 + thumb_size + 18
            parts.append(svg_paragraph(text_left, box_top + 76, [
                f'mean V: {frame.metrics.mean_v:.3f}',
                f'V std: {frame.metrics.std_v:.3f}',
                f'tag lane: {horizon_tag_long_label(spotlight.tag)}',
            ], 'small', line_height=18.0))

    parts.append(svg_paragraph(72, 1946, [
        'This is still a bounded read built from one lattice, one seed, and one active-fraction rule.',
        'That is enough to sharpen the repo’s caveat story without pretending the whole Gray-Scott plane has been universally classified.',
    ], 'small', line_height=22.0))
    parts.append('</svg>')
    return '\n'.join(parts) + '\n'


def render_initialization_sensitivity(study: InitializationSensitivityStudy, feeds: tuple[float, ...], kills: tuple[float, ...]) -> str:
    width, height = 1440, 1860
    parts = base_svg(
        width,
        height,
        'Gray-Scott initialization sensitivity',
        f'The same feed-vs-kill grid after {study.steps} steps under three bounded seed profiles: centered square, split twin patches, and annulus shell.',
    )

    cell = 78
    panel_w = cell * len(feeds) + 140
    panel_h = cell * len(kills) + 150
    positions = [(72, 156), (748, 156)]

    lookup = {(row.feed, row.kill): row for row in study.rows}
    active_spans = [row.active_span for row in study.rows]
    edge_spans = [row.edge_span for row in study.rows]
    active_vmin = min(active_spans) if active_spans else 0.0
    active_vmax = max(active_spans) if active_spans else 1.0
    edge_vmin = min(edge_spans) if edge_spans else 0.0
    edge_vmax = max(edge_spans) if edge_spans else 1.0

    biggest_active = max(study.rows, key=lambda row: row.active_span)
    biggest_edge = max(study.rows, key=lambda row: row.edge_span)
    robust_candidates = [row for row in study.rows if row.min_active_fraction > 0.05]
    most_robust = min(robust_candidates, key=lambda row: (row.active_span + 30.0 * row.edge_span, -row.max_active_fraction)) if robust_candidates else min(study.rows, key=lambda row: (row.active_span + 30.0 * row.edge_span, -row.max_active_fraction))

    def draw_heatmap(left: float, top: float, title: str, subtitle: str, *, getter, vmin: float, vmax: float) -> None:
        parts.append(f'<rect x="{left}" y="{top}" width="{panel_w}" height="{panel_h}" class="panel"/>')
        parts.append(svg_text(left + 24, top + 34, title, 'label'))
        parts.append(svg_paragraph(left + 24, top + 58, [subtitle], 'small', line_height=18.0))
        grid_left = left + 24
        grid_top = top + 116

        for column, feed in enumerate(feeds):
            x = grid_left + column * cell
            parts.append(svg_text(x + cell / 2, grid_top - 18, f'{feed:.3f}', 'small', 'middle'))
        parts.append(svg_text(grid_left + cell * len(feeds) / 2, grid_top - 44, 'feed rate F', 'small', 'middle'))

        for row_index, kill in enumerate(kills):
            y = grid_top + row_index * cell
            parts.append(svg_text(grid_left - 18, y + cell / 2 + 6, f'{kill:.3f}', 'small', 'end'))
            for column, feed in enumerate(feeds):
                x = grid_left + column * cell
                row = lookup[(feed, kill)]
                value = getter(row)
                parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{cell - 6}" height="{cell - 6}" fill="{metric_color(value, vmin, vmax)}" rx="10"/>')
                parts.append(f'<text x="{x + (cell - 6) / 2:.1f}" y="{y + cell / 2 - 2:.1f}" class="cell-label" text-anchor="middle" fill="{metric_label_color(value, vmin, vmax)}">{value:.3f}</text>')

    draw_heatmap(
        *positions[0],
        'active-fraction span across seed profiles',
        'Each cell shows max(active fraction) - min(active fraction) after swapping only the seed profile.',
        getter=lambda row: row.active_span,
        vmin=active_vmin,
        vmax=active_vmax,
    )
    draw_heatmap(
        *positions[1],
        'edge-density span across seed profiles',
        'The same bounded seed swap, now measured through interface sharpness instead of fill fraction.',
        getter=lambda row: row.edge_span,
        vmin=edge_vmin,
        vmax=edge_vmax,
    )

    parts.append(svg_paragraph(72, 734, [
        f'Largest active-profile swing: F={biggest_active.feed:.3f}, k={biggest_active.kill:.3f}, span={biggest_active.active_span:.3f} ({seed_profile_label(biggest_active.active_loser_profile)} → {seed_profile_label(biggest_active.active_winner_profile)}).',
        f'Largest edge-profile swing: F={biggest_edge.feed:.3f}, k={biggest_edge.kill:.3f}, span={biggest_edge.edge_span:.4f}.',
        f'Robust active counterexample: F={most_robust.feed:.3f}, k={most_robust.kill:.3f} stays active under every profile with only {most_robust.active_span:.3f} active span.',
    ], 'small', line_height=22.0))
    parts.append(svg_paragraph(72, 818, [
        'This is the bounded caveat the repo needed: some chemistry cells survive profile swaps almost unchanged, while others flip from near-extinction to broad occupancy once the seeded patch is split or hollowed.',
        'The three profiles were kept comparable but not identical on purpose.',
        'This is a seed-geometry audit, not a claim that one universal initialization already exists.',
    ], 'small', line_height=22.0))

    panel_top = 924
    panel_gap = 362
    spotlight_panel_h = 322
    thumb_pixel = 3.2
    thumb_size = study.size * thumb_pixel
    profile_panel_w = 414

    for spotlight_index, spotlight in enumerate(study.spotlights):
        top = panel_top + spotlight_index * panel_gap
        parts.append(f'<rect x="72" y="{top}" width="1276" height="{spotlight_panel_h}" class="panel"/>')
        parts.append(svg_text(96, top + 34, spotlight.title, 'label'))
        parts.append(svg_paragraph(96, top + 60, [spotlight.reason], 'small', line_height=18.0))
        for profile_index, profile_study in enumerate(spotlight.profiles):
            left = 96 + profile_index * profile_panel_w
            parts.append(f'<rect x="{left}" y="{top + 88}" width="376" height="212" fill="#111c30" stroke="#334155" stroke-width="1.5" rx="14"/>')
            parts.append(svg_text(left + 18, top + 112, seed_profile_label(profile_study.profile), 'label'))
            parts.append(svg_text(left + 18, top + 134, f'active={profile_study.metrics.active_fraction:.3f}, edge={profile_study.metrics.edge_density:.4f}', 'small'))
            _draw_state_thumbnail(parts, state=profile_study.state, left=left + 18, top=top + 152, pixel=thumb_pixel)
            text_left = left + 18 + thumb_size + 20
            parts.append(svg_paragraph(text_left, top + 166, [
                f'peak V: {profile_study.metrics.peak_v:.3f}',
                f'mean V: {profile_study.metrics.mean_v:.3f}',
                f'V std: {profile_study.metrics.std_v:.3f}',
            ], 'small', line_height=22.0))

    parts.append(svg_paragraph(72, 1780, [
        'Read the heatmaps first, then the spotlight rows.',
        'The top cells tell you where profile swaps matter most; the thumbnails show what those swings actually look like in the final V field instead of leaving the note at one scalar drift score.',
    ], 'small', line_height=22.0))
    parts.append('</svg>')
    return '\n'.join(parts) + '\n'


def render_profile_horizon_tags(study: ProfileHorizonTagStudy, feeds: tuple[float, ...], kills: tuple[float, ...]) -> str:
    width, height = 1560, 2340
    parts = base_svg(
        width,
        height,
        'Gray-Scott seed-profile horizon tags',
        f'The three-horizon tag rule repeated under {", ".join(seed_profile_label(profile) for profile in study.profiles)} instead of one fixed seeded patch.',
    )

    cell = 60
    panel_w = cell * len(feeds) + 126
    panel_h = cell * len(kills) + 156
    map_positions = [(60, 150), (566, 150), (1072, 150)]
    lookup = {(row.feed, row.kill): row for row in study.rows}
    late_spans = [row.late_active_fraction_span for row in study.rows]
    span_vmin = min(late_spans) if late_spans else 0.0
    span_vmax = max(late_spans) if late_spans else 1.0
    stability_counts = Counter(row.stability_class for row in study.rows)
    profile_counts = {
        profile: Counter(lookup[(feed, kill)].row_for(profile).tag for kill in kills for feed in feeds)
        for profile in study.profiles
    }

    def draw_profile_map(profile: str, left: float, top: float) -> None:
        counts = profile_counts[profile]
        parts.append(f'<rect x="{left}" y="{top}" width="{panel_w}" height="{panel_h}" class="panel"/>')
        parts.append(svg_text(left + 22, top + 32, seed_profile_label(profile), 'label'))
        parts.append(svg_paragraph(left + 22, top + 56, [
            'Same chemistry grid, same three horizons.',
            'Only the seed geometry changes here.',
        ], 'small', line_height=18.0))
        grid_left = left + 22
        grid_top = top + 108
        for column, feed in enumerate(feeds):
            x = grid_left + column * cell
            parts.append(svg_text(x + cell / 2, grid_top - 18, f'{feed:.3f}', 'small', 'middle'))
        parts.append(svg_text(grid_left + cell * len(feeds) / 2, grid_top - 42, 'feed rate F', 'small', 'middle'))
        for row_index, kill in enumerate(kills):
            y = grid_top + row_index * cell
            parts.append(svg_text(grid_left - 16, y + cell / 2 + 5, f'{kill:.3f}', 'small', 'end'))
            for column, feed in enumerate(feeds):
                x = grid_left + column * cell
                entry = lookup[(feed, kill)].row_for(profile)
                parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{cell - 6}" height="{cell - 6}" fill="{horizon_tag_color(entry.tag)}" rx="10"/>')
                parts.append(f'<text x="{x + (cell - 6) / 2:.1f}" y="{y + cell / 2 - 5:.1f}" class="cell-label" text-anchor="middle" fill="#f8fafc">{horizon_tag_short_label(entry.tag)}</text>')
                parts.append(svg_text(x + (cell - 6) / 2, y + cell / 2 + 15, f'{entry.total_active_delta:+.2f}', 'small', 'middle'))
        legend_y = top + panel_h - 34
        legend_items = [
            (HORIZON_TAG_SETTLED, f'{counts.get(HORIZON_TAG_SETTLED, 0)} set'),
            (HORIZON_TAG_GROWING, f'{counts.get(HORIZON_TAG_GROWING, 0)} up'),
            (HORIZON_TAG_FADING, f'{counts.get(HORIZON_TAG_FADING, 0)} down'),
            (HORIZON_TAG_REVERSING, f'{counts.get(HORIZON_TAG_REVERSING, 0)} flip'),
        ]
        for index, (tag, text) in enumerate(legend_items):
            x = left + 20 + index * 92
            parts.append(f'<rect x="{x:.1f}" y="{legend_y - 13:.1f}" width="16" height="16" fill="{horizon_tag_color(tag)}" rx="4"/>')
            parts.append(svg_text(x + 22, legend_y, text, 'small'))

    for profile, (left, top) in zip(study.profiles, map_positions):
        draw_profile_map(profile, left, top)

    center_reversing = sum(1 for row in study.rows if row.row_for('center').tag == HORIZON_TAG_REVERSING) if 'center' in study.profiles else 0
    survived_reversing = sum(1 for row in study.rows if len(row.reversing_profiles) >= 2)
    parts.append(svg_paragraph(60, 652, [
        f'{stability_counts.get(PROFILE_HORIZON_STABLE, 0)} cells keep one shared tag, {stability_counts.get(PROFILE_HORIZON_SINGLE_FLIP, 0)} have a two-against-one flip, and {stability_counts.get(PROFILE_HORIZON_THREE_WAY_SPLIT, 0)} split three ways.',
        f'The earlier center-profile reversing lane does not stay chemistry-only: {center_reversing} center reversing cells exist here, but only {survived_reversing} cells keep a reversing tag in two or more profiles.',
    ], 'small', line_height=22.0))
    parts.append(svg_paragraph(60, 718, [
        'Read the three maps left to right first. Then use the agreement and late-span cards below to see whether the tag change is a minor relabel or a real late-horizon fate shift.',
    ], 'small', line_height=22.0))

    summary_top = 800
    summary_panel_w = 670
    summary_panel_h = 392
    summary_cell = 50

    parts.append(f'<rect x="60" y="{summary_top}" width="{summary_panel_w}" height="{summary_panel_h}" class="panel"/>')
    parts.append(svg_text(84, summary_top + 32, 'profile agreement map', 'label'))
    parts.append(svg_paragraph(84, summary_top + 56, [
        '3x means all profiles agree. 2+1 means one profile flips. 3-way means every profile lands on a different tag.',
    ], 'small', line_height=18.0))
    grid_left = 84
    grid_top = summary_top + 108
    for column, feed in enumerate(feeds):
        x = grid_left + column * summary_cell
        parts.append(svg_text(x + summary_cell / 2, grid_top - 18, f'{feed:.3f}', 'small', 'middle'))
    parts.append(svg_text(grid_left + summary_cell * len(feeds) / 2, grid_top - 42, 'feed rate F', 'small', 'middle'))
    for row_index, kill in enumerate(kills):
        y = grid_top + row_index * summary_cell
        parts.append(svg_text(grid_left - 16, y + summary_cell / 2 + 5, f'{kill:.3f}', 'small', 'end'))
        for column, feed in enumerate(feeds):
            x = grid_left + column * summary_cell
            entry = lookup[(feed, kill)]
            label = entry.stability_class
            parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{summary_cell - 6}" height="{summary_cell - 6}" fill="{profile_horizon_stability_color(label)}" rx="10"/>')
            parts.append(f'<text x="{x + (summary_cell - 6) / 2:.1f}" y="{y + summary_cell / 2 + 3:.1f}" class="cell-label" text-anchor="middle" fill="#f8fafc">{profile_horizon_stability_short_label(label)}</text>')
    legend_y = summary_top + summary_panel_h - 28
    legend_items = [
        (PROFILE_HORIZON_STABLE, 'all agree'),
        (PROFILE_HORIZON_SINGLE_FLIP, 'one flips'),
        (PROFILE_HORIZON_THREE_WAY_SPLIT, 'three-way'),
    ]
    for index, (label, text) in enumerate(legend_items):
        x = 84 + index * 150
        parts.append(f'<rect x="{x:.1f}" y="{legend_y - 13:.1f}" width="18" height="18" fill="{profile_horizon_stability_color(label)}" rx="4"/>')
        parts.append(svg_text(x + 24, legend_y, text, 'small'))

    right_left = 830
    parts.append(f'<rect x="{right_left}" y="{summary_top}" width="{summary_panel_w}" height="{summary_panel_h}" class="panel"/>')
    parts.append(svg_text(right_left + 24, summary_top + 32, f'late active span at {study.late_steps} steps', 'label'))
    parts.append(svg_paragraph(right_left + 24, summary_top + 56, [
        'This is max(final active fraction) - min(final active fraction) across the seed profiles.',
    ], 'small', line_height=18.0))
    grid_left = right_left + 24
    grid_top = summary_top + 108
    for column, feed in enumerate(feeds):
        x = grid_left + column * summary_cell
        parts.append(svg_text(x + summary_cell / 2, grid_top - 18, f'{feed:.3f}', 'small', 'middle'))
    parts.append(svg_text(grid_left + summary_cell * len(feeds) / 2, grid_top - 42, 'feed rate F', 'small', 'middle'))
    for row_index, kill in enumerate(kills):
        y = grid_top + row_index * summary_cell
        parts.append(svg_text(grid_left - 16, y + summary_cell / 2 + 5, f'{kill:.3f}', 'small', 'end'))
        for column, feed in enumerate(feeds):
            x = grid_left + column * summary_cell
            entry = lookup[(feed, kill)]
            value = entry.late_active_fraction_span
            parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{summary_cell - 6}" height="{summary_cell - 6}" fill="{metric_color(value, span_vmin, span_vmax)}" rx="10"/>')
            parts.append(f'<text x="{x + (summary_cell - 6) / 2:.1f}" y="{y + summary_cell / 2 + 3:.1f}" class="cell-label" text-anchor="middle" fill="{metric_label_color(value, span_vmin, span_vmax)}">{value:.2f}</text>')
    largest_span = max(study.rows, key=lambda row: row.late_active_fraction_span)
    parts.append(svg_paragraph(right_left + 24, summary_top + summary_panel_h - 34, [
        f'Largest final span: F={largest_span.feed:.3f}, k={largest_span.kill:.3f}, span={largest_span.late_active_fraction_span:.3f}.',
    ], 'small', line_height=18.0))

    spotlight_top = 1220
    spotlight_panel_h = 300
    spotlight_gap = 28
    thumb_pixel = 2.9
    thumb_size = study.size * thumb_pixel
    profile_panel_w = 432
    for index, spotlight in enumerate(study.spotlights):
        top = spotlight_top + index * (spotlight_panel_h + spotlight_gap)
        parts.append(f'<rect x="60" y="{top}" width="1440" height="{spotlight_panel_h}" class="panel"/>')
        parts.append(svg_text(84, top + 32, spotlight.title, 'label'))
        parts.append(svg_paragraph(84, top + 56, [spotlight.reason], 'small', line_height=18.0))
        for profile_index, profile_entry in enumerate(spotlight.profiles):
            left = 84 + profile_index * profile_panel_w
            parts.append(f'<rect x="{left}" y="{top + 90}" width="400" height="182" fill="#111c30" stroke="#334155" stroke-width="1.5" rx="14"/>')
            parts.append(svg_text(left + 16, top + 116, seed_profile_label(profile_entry.profile), 'label'))
            parts.append(svg_text(left + 16, top + 140, f'{horizon_tag_long_label(profile_entry.row.tag)} | Δtotal={profile_entry.row.total_active_delta:+.3f}', 'small'))
            _draw_state_thumbnail(parts, state=profile_entry.state, left=left + 16, top=top + 158, pixel=thumb_pixel)
            text_left = left + 16 + thumb_size + 20
            parts.append(svg_paragraph(text_left, top + 176, [
                f'late active: {profile_entry.row.late_metrics.active_fraction:.3f}',
                f'leg 1: {profile_entry.row.early_active_delta:+.3f}',
                f'leg 2: {profile_entry.row.late_active_delta:+.3f}',
                f'edge late: {profile_entry.row.late_metrics.edge_density:.4f}',
            ], 'small', line_height=18.0))

    parts.append(svg_paragraph(60, 2288, [
        'This is still one lattice, one seed value, and one bounded three-horizon tag rule.',
        'That is enough to show that some late-horizon cautions belong to the seed geometry as much as to the chemistry cell itself.',
    ], 'small', line_height=20.0))
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
