from __future__ import annotations

from dataclasses import dataclass
from statistics import mean, pstdev

from .core import GrayScottParameters, GrayScottPreset, GrayScottState, flatten, simulate, simulate_preset, simulate_preset_samples


@dataclass(frozen=True)
class PatternMetrics:
    mean_v: float
    std_v: float
    active_fraction: float
    edge_density: float
    peak_v: float


@dataclass(frozen=True)
class PresetStudy:
    preset: GrayScottPreset
    metrics: PatternMetrics
    state: GrayScottState


@dataclass(frozen=True)
class ParameterScanRow:
    feed: float
    kill: float
    metrics: PatternMetrics


@dataclass(frozen=True)
class TimeSeriesPoint:
    step: int
    metrics: PatternMetrics


@dataclass(frozen=True)
class TimeEvolutionStudy:
    preset: GrayScottPreset
    snapshots: tuple[tuple[int, GrayScottState], ...]
    timeline: tuple[TimeSeriesPoint, ...]


CURATED_PRESETS: tuple[GrayScottPreset, ...] = (
    GrayScottPreset(name='sparse spots', feed=0.014, kill=0.054, steps=1800, size=72, patch_radius=7, seed=0),
    GrayScottPreset(name='worm bands', feed=0.022, kill=0.051, steps=1600, size=72, patch_radius=7, seed=0),
    GrayScottPreset(name='labyrinth mix', feed=0.026, kill=0.055, steps=1400, size=72, patch_radius=7, seed=0),
    GrayScottPreset(name='split spots', feed=0.030, kill=0.062, steps=1400, size=72, patch_radius=7, seed=0),
)

SCAN_FEEDS: tuple[float, ...] = (0.014, 0.018, 0.022, 0.026, 0.030)
SCAN_KILLS: tuple[float, ...] = (0.051, 0.054, 0.057, 0.060, 0.063)
TIME_EVOLUTION_PRESET = CURATED_PRESETS[1]
DEFAULT_SNAPSHOT_STEPS: tuple[int, ...] = (0, 60, 180, 360, 800, 1600)
DEFAULT_TIMELINE_STEP = 40


def measure_pattern(state: GrayScottState, *, active_threshold: float = 0.15) -> PatternMetrics:
    values = flatten(state.v)
    mean_v = mean(values)
    std_v = pstdev(values)
    active_fraction = sum(1 for value in values if value > active_threshold) / len(values)
    peak_v = max(values)

    edges = 0.0
    comparisons = 0
    size = state.size
    for i in range(size):
        for j in range(size):
            edges += abs(state.v[i][j] - state.v[i][(j + 1) % size])
            edges += abs(state.v[i][j] - state.v[(i + 1) % size][j])
            comparisons += 2
    edge_density = edges / comparisons

    return PatternMetrics(
        mean_v=mean_v,
        std_v=std_v,
        active_fraction=active_fraction,
        edge_density=edge_density,
        peak_v=peak_v,
    )


def study_presets(presets: tuple[GrayScottPreset, ...] = CURATED_PRESETS) -> list[PresetStudy]:
    studies: list[PresetStudy] = []
    for preset in presets:
        state = simulate_preset(preset)
        studies.append(PresetStudy(preset=preset, metrics=measure_pattern(state), state=state))
    return studies


def scan_parameter_grid(
    feeds: tuple[float, ...] = SCAN_FEEDS,
    kills: tuple[float, ...] = SCAN_KILLS,
    *,
    size: int = 40,
    steps: int = 700,
    patch_radius: int = 5,
    seed: int = 0,
) -> list[ParameterScanRow]:
    rows: list[ParameterScanRow] = []
    for kill in kills:
        for feed in feeds:
            state = simulate(
                GrayScottParameters(feed=feed, kill=kill),
                size=size,
                steps=steps,
                patch_radius=patch_radius,
                seed=seed,
            )
            rows.append(ParameterScanRow(feed=feed, kill=kill, metrics=measure_pattern(state)))
    return rows


def preset_by_name(name: str) -> GrayScottPreset:
    for preset in CURATED_PRESETS:
        if preset.name == name:
            return preset
    raise KeyError(name)


def study_time_evolution(
    preset: GrayScottPreset = TIME_EVOLUTION_PRESET,
    *,
    snapshot_steps: tuple[int, ...] = DEFAULT_SNAPSHOT_STEPS,
    timeline_every: int = DEFAULT_TIMELINE_STEP,
) -> TimeEvolutionStudy:
    if timeline_every <= 0:
        raise ValueError('timeline_every must be positive')

    usable_snapshot_steps = tuple(step for step in snapshot_steps if 0 <= step <= preset.steps)
    timeline_steps = tuple(range(0, preset.steps + 1, timeline_every))
    if timeline_steps[-1] != preset.steps:
        timeline_steps = timeline_steps + (preset.steps,)

    requested_steps = tuple(sorted(set(usable_snapshot_steps + timeline_steps)))
    sampled = simulate_preset_samples(preset, requested_steps)
    state_lookup = {step: state for step, state in sampled}

    snapshots = tuple((step, state_lookup[step]) for step in usable_snapshot_steps)
    timeline = tuple(TimeSeriesPoint(step=step, metrics=measure_pattern(state_lookup[step])) for step in timeline_steps)
    return TimeEvolutionStudy(preset=preset, snapshots=snapshots, timeline=timeline)
