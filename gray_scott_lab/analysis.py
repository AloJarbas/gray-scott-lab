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


@dataclass(frozen=True)
class HorizonComparisonRow:
    feed: float
    kill: float
    short_metrics: PatternMetrics
    long_metrics: PatternMetrics

    @property
    def active_fraction_delta(self) -> float:
        return self.long_metrics.active_fraction - self.short_metrics.active_fraction

    @property
    def edge_density_delta(self) -> float:
        return self.long_metrics.edge_density - self.short_metrics.edge_density


@dataclass(frozen=True)
class HorizonComparisonStudy:
    short_steps: int
    long_steps: int
    size: int
    patch_radius: int
    seed: int
    rows: tuple[HorizonComparisonRow, ...]


HORIZON_TAG_SETTLED = 'settled'
HORIZON_TAG_GROWING = 'growing'
HORIZON_TAG_FADING = 'fading'
HORIZON_TAG_REVERSING = 'reversing'
HORIZON_TAGS: tuple[str, ...] = (
    HORIZON_TAG_SETTLED,
    HORIZON_TAG_GROWING,
    HORIZON_TAG_FADING,
    HORIZON_TAG_REVERSING,
)
HORIZON_SETTLED_ACTIVE_THRESHOLD = 0.05
HORIZON_SETTLED_EDGE_THRESHOLD = 0.007
HORIZON_TOTAL_GROW_THRESHOLD = 0.04
HORIZON_TOTAL_FADE_THRESHOLD = -0.06
HORIZON_LEG_SWING_THRESHOLD = 0.05


@dataclass(frozen=True)
class HorizonTagStepMetrics:
    step: int
    metrics: PatternMetrics


@dataclass(frozen=True)
class HorizonTagRow:
    feed: float
    kill: float
    horizon_metrics: tuple[HorizonTagStepMetrics, ...]

    def metrics_at(self, step: int) -> PatternMetrics:
        for entry in self.horizon_metrics:
            if entry.step == step:
                return entry.metrics
        raise KeyError(step)

    @property
    def early_step(self) -> int:
        return self.horizon_metrics[0].step

    @property
    def middle_step(self) -> int:
        return self.horizon_metrics[1].step

    @property
    def late_step(self) -> int:
        return self.horizon_metrics[2].step

    @property
    def early_metrics(self) -> PatternMetrics:
        return self.horizon_metrics[0].metrics

    @property
    def middle_metrics(self) -> PatternMetrics:
        return self.horizon_metrics[1].metrics

    @property
    def late_metrics(self) -> PatternMetrics:
        return self.horizon_metrics[2].metrics

    @property
    def early_active_delta(self) -> float:
        return self.middle_metrics.active_fraction - self.early_metrics.active_fraction

    @property
    def late_active_delta(self) -> float:
        return self.late_metrics.active_fraction - self.middle_metrics.active_fraction

    @property
    def total_active_delta(self) -> float:
        return self.late_metrics.active_fraction - self.early_metrics.active_fraction

    @property
    def early_edge_delta(self) -> float:
        return self.middle_metrics.edge_density - self.early_metrics.edge_density

    @property
    def late_edge_delta(self) -> float:
        return self.late_metrics.edge_density - self.middle_metrics.edge_density

    @property
    def total_edge_delta(self) -> float:
        return self.late_metrics.edge_density - self.early_metrics.edge_density

    @property
    def tag(self) -> str:
        return classify_horizon_tag(self)


@dataclass(frozen=True)
class HorizonTagSpotlightFrame:
    step: int
    metrics: PatternMetrics
    state: GrayScottState


@dataclass(frozen=True)
class HorizonTagSpotlight:
    tag: str
    title: str
    reason: str
    feed: float
    kill: float
    frames: tuple[HorizonTagSpotlightFrame, ...]


@dataclass(frozen=True)
class HorizonTagStudy:
    early_steps: int
    middle_steps: int
    late_steps: int
    size: int
    patch_radius: int
    seed: int
    profile: str
    rows: tuple[HorizonTagRow, ...]
    spotlights: tuple[HorizonTagSpotlight, ...]


@dataclass(frozen=True)
class GridSizeComparisonRow:
    feed: float
    kill: float
    small_metrics: PatternMetrics
    large_metrics: PatternMetrics

    @property
    def active_fraction_delta(self) -> float:
        return self.large_metrics.active_fraction - self.small_metrics.active_fraction

    @property
    def edge_density_delta(self) -> float:
        return self.large_metrics.edge_density - self.small_metrics.edge_density


@dataclass(frozen=True)
class GridSizeComparisonStudy:
    steps: int
    small_size: int
    large_size: int
    small_patch_radius: int
    large_patch_radius: int
    seed: int
    rows: tuple[GridSizeComparisonRow, ...]


@dataclass(frozen=True)
class SeedProfileMetrics:
    profile: str
    metrics: PatternMetrics


@dataclass(frozen=True)
class InitializationSensitivityRow:
    feed: float
    kill: float
    profile_metrics: tuple[SeedProfileMetrics, ...]

    def metrics_for(self, profile: str) -> PatternMetrics:
        for entry in self.profile_metrics:
            if entry.profile == profile:
                return entry.metrics
        raise KeyError(profile)

    @property
    def active_span(self) -> float:
        values = [entry.metrics.active_fraction for entry in self.profile_metrics]
        return max(values) - min(values)

    @property
    def edge_span(self) -> float:
        values = [entry.metrics.edge_density for entry in self.profile_metrics]
        return max(values) - min(values)

    @property
    def max_active_fraction(self) -> float:
        return max(entry.metrics.active_fraction for entry in self.profile_metrics)

    @property
    def min_active_fraction(self) -> float:
        return min(entry.metrics.active_fraction for entry in self.profile_metrics)

    @property
    def active_winner_profile(self) -> str:
        return max(self.profile_metrics, key=lambda entry: entry.metrics.active_fraction).profile

    @property
    def active_loser_profile(self) -> str:
        return min(self.profile_metrics, key=lambda entry: entry.metrics.active_fraction).profile


@dataclass(frozen=True)
class InitializationSensitivitySpotlightProfile:
    profile: str
    metrics: PatternMetrics
    state: GrayScottState


@dataclass(frozen=True)
class InitializationSensitivitySpotlight:
    title: str
    reason: str
    feed: float
    kill: float
    profiles: tuple[InitializationSensitivitySpotlightProfile, ...]


@dataclass(frozen=True)
class InitializationSensitivityStudy:
    steps: int
    size: int
    patch_radius: int
    seed: int
    profiles: tuple[str, ...]
    rows: tuple[InitializationSensitivityRow, ...]
    spotlights: tuple[InitializationSensitivitySpotlight, ...]


PROFILE_HORIZON_STABLE = 'stable'
PROFILE_HORIZON_SINGLE_FLIP = 'single-flip'
PROFILE_HORIZON_THREE_WAY_SPLIT = 'three-way-split'


@dataclass(frozen=True)
class ProfileHorizonTagProfileRow:
    profile: str
    row: HorizonTagRow


@dataclass(frozen=True)
class ProfileHorizonTagRow:
    feed: float
    kill: float
    profile_rows: tuple[ProfileHorizonTagProfileRow, ...]

    def row_for(self, profile: str) -> HorizonTagRow:
        for entry in self.profile_rows:
            if entry.profile == profile:
                return entry.row
        raise KeyError(profile)

    @property
    def tags(self) -> tuple[str, ...]:
        return tuple(entry.row.tag for entry in self.profile_rows)

    @property
    def unique_tag_count(self) -> int:
        return len(set(self.tags))

    @property
    def agreement_count(self) -> int:
        return max(self.tags.count(tag) for tag in set(self.tags))

    @property
    def stability_class(self) -> str:
        if self.unique_tag_count == 1:
            return PROFILE_HORIZON_STABLE
        if self.unique_tag_count == 2:
            return PROFILE_HORIZON_SINGLE_FLIP
        return PROFILE_HORIZON_THREE_WAY_SPLIT

    @property
    def majority_tag(self) -> str | None:
        if self.agreement_count < 2:
            return None
        for tag in self.tags:
            if self.tags.count(tag) == self.agreement_count:
                return tag
        return None

    @property
    def stable_tag(self) -> str | None:
        return self.tags[0] if self.unique_tag_count == 1 else None

    @property
    def late_active_fraction_span(self) -> float:
        values = [entry.row.late_metrics.active_fraction for entry in self.profile_rows]
        return max(values) - min(values)

    @property
    def total_active_delta_span(self) -> float:
        values = [entry.row.total_active_delta for entry in self.profile_rows]
        return max(values) - min(values)

    @property
    def max_late_active_fraction(self) -> float:
        return max(entry.row.late_metrics.active_fraction for entry in self.profile_rows)

    @property
    def min_late_active_fraction(self) -> float:
        return min(entry.row.late_metrics.active_fraction for entry in self.profile_rows)

    @property
    def reversing_profiles(self) -> tuple[str, ...]:
        return tuple(entry.profile for entry in self.profile_rows if entry.row.tag == HORIZON_TAG_REVERSING)


@dataclass(frozen=True)
class ProfileHorizonTagSpotlightProfile:
    profile: str
    row: HorizonTagRow
    state: GrayScottState


@dataclass(frozen=True)
class ProfileHorizonTagSpotlight:
    title: str
    reason: str
    feed: float
    kill: float
    profiles: tuple[ProfileHorizonTagSpotlightProfile, ...]


@dataclass(frozen=True)
class ProfileHorizonTagStudy:
    early_steps: int
    middle_steps: int
    late_steps: int
    size: int
    patch_radius: int
    seed: int
    profiles: tuple[str, ...]
    rows: tuple[ProfileHorizonTagRow, ...]
    spotlights: tuple[ProfileHorizonTagSpotlight, ...]


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
INITIALIZATION_PROFILES: tuple[str, ...] = ('center', 'double', 'ring')


def scaled_patch_radius(size: int, *, reference_size: int = 40, reference_patch_radius: int = 5) -> int:
    if size <= 0:
        raise ValueError('size must be positive')
    if reference_size <= 0:
        raise ValueError('reference_size must be positive')
    if reference_patch_radius <= 0:
        raise ValueError('reference_patch_radius must be positive')
    return max(1, round(reference_patch_radius * size / reference_size))


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
    profile: str = 'center',
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
                profile=profile,
            )
            rows.append(ParameterScanRow(feed=feed, kill=kill, metrics=measure_pattern(state)))
    return rows


def _build_horizon_rows(
    feeds: tuple[float, ...],
    kills: tuple[float, ...],
    *,
    early_steps: int,
    middle_steps: int,
    late_steps: int,
    size: int,
    patch_radius: int,
    seed: int,
    profile: str,
) -> tuple[HorizonTagRow, ...]:
    early_rows = {
        (row.feed, row.kill): row
        for row in scan_parameter_grid(
            feeds,
            kills,
            size=size,
            steps=early_steps,
            patch_radius=patch_radius,
            seed=seed,
            profile=profile,
        )
    }
    middle_rows = {
        (row.feed, row.kill): row
        for row in scan_parameter_grid(
            feeds,
            kills,
            size=size,
            steps=middle_steps,
            patch_radius=patch_radius,
            seed=seed,
            profile=profile,
        )
    }
    late_rows = {
        (row.feed, row.kill): row
        for row in scan_parameter_grid(
            feeds,
            kills,
            size=size,
            steps=late_steps,
            patch_radius=patch_radius,
            seed=seed,
            profile=profile,
        )
    }

    return tuple(
        HorizonTagRow(
            feed=feed,
            kill=kill,
            horizon_metrics=(
                HorizonTagStepMetrics(step=early_steps, metrics=early_rows[(feed, kill)].metrics),
                HorizonTagStepMetrics(step=middle_steps, metrics=middle_rows[(feed, kill)].metrics),
                HorizonTagStepMetrics(step=late_steps, metrics=late_rows[(feed, kill)].metrics),
            ),
        )
        for kill in kills
        for feed in feeds
    )


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


def study_horizon_comparison(
    feeds: tuple[float, ...] = SCAN_FEEDS,
    kills: tuple[float, ...] = SCAN_KILLS,
    *,
    short_steps: int = 700,
    long_steps: int = 1400,
    size: int = 40,
    patch_radius: int = 5,
    seed: int = 0,
) -> HorizonComparisonStudy:
    if short_steps < 0 or long_steps < 0:
        raise ValueError('step counts must be non-negative')
    if long_steps <= short_steps:
        raise ValueError('long_steps must be greater than short_steps')

    short_rows = {
        (row.feed, row.kill): row
        for row in scan_parameter_grid(
            feeds,
            kills,
            size=size,
            steps=short_steps,
            patch_radius=patch_radius,
            seed=seed,
        )
    }
    long_rows = {
        (row.feed, row.kill): row
        for row in scan_parameter_grid(
            feeds,
            kills,
            size=size,
            steps=long_steps,
            patch_radius=patch_radius,
            seed=seed,
        )
    }

    rows = tuple(
        HorizonComparisonRow(
            feed=feed,
            kill=kill,
            short_metrics=short_rows[(feed, kill)].metrics,
            long_metrics=long_rows[(feed, kill)].metrics,
        )
        for kill in kills
        for feed in feeds
    )
    return HorizonComparisonStudy(
        short_steps=short_steps,
        long_steps=long_steps,
        size=size,
        patch_radius=patch_radius,
        seed=seed,
        rows=rows,
    )


def classify_horizon_tag(row: HorizonTagRow) -> str:
    early_delta = row.early_active_delta
    late_delta = row.late_active_delta
    total_delta = row.total_active_delta
    edge_early = row.early_edge_delta
    edge_late = row.late_edge_delta

    if total_delta <= HORIZON_TOTAL_FADE_THRESHOLD and (late_delta <= -0.03 or row.late_metrics.active_fraction <= 0.05):
        return HORIZON_TAG_FADING
    if (
        max(abs(early_delta), abs(late_delta), abs(total_delta)) <= HORIZON_SETTLED_ACTIVE_THRESHOLD
        and max(abs(edge_early), abs(edge_late)) <= HORIZON_SETTLED_EDGE_THRESHOLD
    ):
        return HORIZON_TAG_SETTLED
    if total_delta >= HORIZON_TOTAL_GROW_THRESHOLD and late_delta >= -0.03:
        return HORIZON_TAG_GROWING
    if early_delta * late_delta < 0.0 and (abs(early_delta) >= HORIZON_LEG_SWING_THRESHOLD or abs(late_delta) >= HORIZON_LEG_SWING_THRESHOLD):
        return HORIZON_TAG_REVERSING
    return HORIZON_TAG_SETTLED


def _horizon_tag_reason(row: HorizonTagRow) -> str:
    if row.tag == HORIZON_TAG_SETTLED:
        return (
            f'F={row.feed:.3f}, k={row.kill:.3f} stays within ±{max(abs(row.early_active_delta), abs(row.late_active_delta)):.3f} active-fraction drift '
            f'while edge density only moves by {max(abs(row.early_edge_delta), abs(row.late_edge_delta)):.4f} per leg.'
        )
    if row.tag == HORIZON_TAG_GROWING:
        return (
            f'F={row.feed:.3f}, k={row.kill:.3f} finishes {row.total_active_delta:+.3f} higher in active fraction by the late horizon '
            f'with a last-leg edge change of {row.late_edge_delta:+.4f}.'
        )
    if row.tag == HORIZON_TAG_FADING:
        return (
            f'F={row.feed:.3f}, k={row.kill:.3f} loses {abs(row.total_active_delta):.3f} active fraction by the late horizon '
            f'and ends near {row.late_metrics.active_fraction:.3f} occupancy.'
        )
    return (
        f'F={row.feed:.3f}, k={row.kill:.3f} changes sign between legs: '
        f'{row.early_active_delta:+.3f} first, then {row.late_active_delta:+.3f}.'
    )


def study_horizon_tags(
    feeds: tuple[float, ...] = SCAN_FEEDS,
    kills: tuple[float, ...] = SCAN_KILLS,
    *,
    early_steps: int = 700,
    middle_steps: int = 1400,
    late_steps: int = 2800,
    size: int = 40,
    patch_radius: int = 5,
    seed: int = 0,
    profile: str = 'center',
) -> HorizonTagStudy:
    if early_steps < 0 or middle_steps < 0 or late_steps < 0:
        raise ValueError('step counts must be non-negative')
    if not (early_steps < middle_steps < late_steps):
        raise ValueError('need strictly increasing early, middle, and late step counts')

    rows = _build_horizon_rows(
        feeds,
        kills,
        early_steps=early_steps,
        middle_steps=middle_steps,
        late_steps=late_steps,
        size=size,
        patch_radius=patch_radius,
        seed=seed,
        profile=profile,
    )

    def make_spotlight(row: HorizonTagRow, *, title: str) -> HorizonTagSpotlight:
        frames = tuple(
            HorizonTagSpotlightFrame(
                step=step,
                metrics=row.metrics_at(step),
                state=simulate(
                    GrayScottParameters(feed=row.feed, kill=row.kill),
                    size=size,
                    steps=step,
                    patch_radius=patch_radius,
                    seed=seed,
                    profile=profile,
                ),
            )
            for step in (early_steps, middle_steps, late_steps)
        )
        return HorizonTagSpotlight(
            tag=row.tag,
            title=title,
            reason=_horizon_tag_reason(row),
            feed=row.feed,
            kill=row.kill,
            frames=frames,
        )

    settled_candidates = [
        row for row in rows
        if row.tag == HORIZON_TAG_SETTLED and 0.05 < row.late_metrics.active_fraction < 0.95
    ]
    if not settled_candidates:
        settled_candidates = [row for row in rows if row.tag == HORIZON_TAG_SETTLED]
    settled_row = min(
        settled_candidates,
        key=lambda row: (
            max(abs(row.early_active_delta), abs(row.late_active_delta)),
            max(abs(row.early_edge_delta), abs(row.late_edge_delta)),
            -row.late_metrics.active_fraction,
        ),
    )

    growing_candidates = [row for row in rows if row.tag == HORIZON_TAG_GROWING]
    fading_candidates = [row for row in rows if row.tag == HORIZON_TAG_FADING]
    reversing_candidates = [row for row in rows if row.tag == HORIZON_TAG_REVERSING]

    spotlights = [make_spotlight(settled_row, title='Settled active counterexample')]
    if growing_candidates:
        spotlights.append(make_spotlight(max(growing_candidates, key=lambda row: (row.total_active_delta, row.late_edge_delta)), title='Late-growing cell'))
    if fading_candidates:
        spotlights.append(make_spotlight(min(fading_candidates, key=lambda row: row.total_active_delta), title='Late-fading cell'))
    if reversing_candidates:
        spotlights.append(make_spotlight(max(reversing_candidates, key=lambda row: max(abs(row.early_active_delta), abs(row.late_active_delta))), title='Reversing cell'))

    return HorizonTagStudy(
        early_steps=early_steps,
        middle_steps=middle_steps,
        late_steps=late_steps,
        size=size,
        patch_radius=patch_radius,
        seed=seed,
        profile=profile,
        rows=rows,
        spotlights=tuple(spotlights),
    )


def study_grid_size_comparison(
    feeds: tuple[float, ...] = SCAN_FEEDS,
    kills: tuple[float, ...] = SCAN_KILLS,
    *,
    steps: int = 1400,
    small_size: int = 40,
    large_size: int = 72,
    small_patch_radius: int = 5,
    large_patch_radius: int | None = None,
    seed: int = 0,
) -> GridSizeComparisonStudy:
    if steps < 0:
        raise ValueError('steps must be non-negative')
    if small_size <= 0 or large_size <= 0:
        raise ValueError('sizes must be positive')
    if large_size <= small_size:
        raise ValueError('large_size must be greater than small_size')
    if small_patch_radius <= 0:
        raise ValueError('small_patch_radius must be positive')

    resolved_large_patch_radius = large_patch_radius
    if resolved_large_patch_radius is None:
        resolved_large_patch_radius = scaled_patch_radius(
            large_size,
            reference_size=small_size,
            reference_patch_radius=small_patch_radius,
        )
    if resolved_large_patch_radius <= 0:
        raise ValueError('large_patch_radius must be positive')

    small_rows = {
        (row.feed, row.kill): row
        for row in scan_parameter_grid(
            feeds,
            kills,
            size=small_size,
            steps=steps,
            patch_radius=small_patch_radius,
            seed=seed,
        )
    }
    large_rows = {
        (row.feed, row.kill): row
        for row in scan_parameter_grid(
            feeds,
            kills,
            size=large_size,
            steps=steps,
            patch_radius=resolved_large_patch_radius,
            seed=seed,
        )
    }

    rows = tuple(
        GridSizeComparisonRow(
            feed=feed,
            kill=kill,
            small_metrics=small_rows[(feed, kill)].metrics,
            large_metrics=large_rows[(feed, kill)].metrics,
        )
        for kill in kills
        for feed in feeds
    )
    return GridSizeComparisonStudy(
        steps=steps,
        small_size=small_size,
        large_size=large_size,
        small_patch_radius=small_patch_radius,
        large_patch_radius=resolved_large_patch_radius,
        seed=seed,
        rows=rows,
    )


def study_initialization_sensitivity(
    feeds: tuple[float, ...] = SCAN_FEEDS,
    kills: tuple[float, ...] = SCAN_KILLS,
    *,
    steps: int = 1400,
    size: int = 40,
    patch_radius: int = 5,
    seed: int = 0,
    profiles: tuple[str, ...] = INITIALIZATION_PROFILES,
) -> InitializationSensitivityStudy:
    if steps < 0:
        raise ValueError('steps must be non-negative')
    if size <= 0:
        raise ValueError('size must be positive')
    if patch_radius <= 0:
        raise ValueError('patch_radius must be positive')
    if len(profiles) < 2:
        raise ValueError('need at least two profiles')

    rows: list[InitializationSensitivityRow] = []
    for kill in kills:
        for feed in feeds:
            metrics = tuple(
                SeedProfileMetrics(
                    profile=profile,
                    metrics=measure_pattern(
                        simulate(
                            GrayScottParameters(feed=feed, kill=kill),
                            size=size,
                            steps=steps,
                            patch_radius=patch_radius,
                            seed=seed,
                            profile=profile,
                        )
                    ),
                )
                for profile in profiles
            )
            rows.append(InitializationSensitivityRow(feed=feed, kill=kill, profile_metrics=metrics))

    if not rows:
        return InitializationSensitivityStudy(
            steps=steps,
            size=size,
            patch_radius=patch_radius,
            seed=seed,
            profiles=profiles,
            rows=tuple(),
            spotlights=tuple(),
        )

    strongest_flip = max(rows, key=lambda row: (row.active_span, row.edge_span, row.max_active_fraction))
    robust_candidates = [row for row in rows if row.min_active_fraction > 0.05]
    if robust_candidates:
        most_robust = min(robust_candidates, key=lambda row: (row.active_span + 30.0 * row.edge_span, -row.max_active_fraction))
    else:
        most_robust = min(rows, key=lambda row: (row.active_span + 30.0 * row.edge_span, -row.max_active_fraction))

    def make_spotlight(row: InitializationSensitivityRow, *, title: str, reason: str) -> InitializationSensitivitySpotlight:
        profiles_with_state = tuple(
            InitializationSensitivitySpotlightProfile(
                profile=profile,
                metrics=row.metrics_for(profile),
                state=simulate(
                    GrayScottParameters(feed=row.feed, kill=row.kill),
                    size=size,
                    steps=steps,
                    patch_radius=patch_radius,
                    seed=seed,
                    profile=profile,
                ),
            )
            for profile in profiles
        )
        return InitializationSensitivitySpotlight(
            title=title,
            reason=reason,
            feed=row.feed,
            kill=row.kill,
            profiles=profiles_with_state,
        )

    spotlights = [
        make_spotlight(
            strongest_flip,
            title='Most profile-sensitive cell',
            reason=(
                f'F={strongest_flip.feed:.3f}, k={strongest_flip.kill:.3f} has the widest active-fraction span '
                f'({strongest_flip.active_span:.3f}) across the three bounded seed profiles.'
            ),
        )
    ]
    if most_robust != strongest_flip:
        spotlights.append(
            make_spotlight(
                most_robust,
                title='Robust active cell',
                reason=(
                    f'F={most_robust.feed:.3f}, k={most_robust.kill:.3f} stays chemically active under every profile '
                    f'while keeping one of the smallest combined active/edge drifts.'
                ),
            )
        )

    return InitializationSensitivityStudy(
        steps=steps,
        size=size,
        patch_radius=patch_radius,
        seed=seed,
        profiles=profiles,
        rows=tuple(rows),
        spotlights=tuple(spotlights),
    )


def study_profile_horizon_tags(
    feeds: tuple[float, ...] = SCAN_FEEDS,
    kills: tuple[float, ...] = SCAN_KILLS,
    *,
    early_steps: int = 700,
    middle_steps: int = 1400,
    late_steps: int = 2800,
    size: int = 40,
    patch_radius: int = 5,
    seed: int = 0,
    profiles: tuple[str, ...] = INITIALIZATION_PROFILES,
) -> ProfileHorizonTagStudy:
    if len(profiles) < 2:
        raise ValueError('need at least two profiles')

    profile_rows = {
        profile: _build_horizon_rows(
            feeds,
            kills,
            early_steps=early_steps,
            middle_steps=middle_steps,
            late_steps=late_steps,
            size=size,
            patch_radius=patch_radius,
            seed=seed,
            profile=profile,
        )
        for profile in profiles
    }
    row_lookup = {
        profile: {(row.feed, row.kill): row for row in rows}
        for profile, rows in profile_rows.items()
    }
    rows = tuple(
        ProfileHorizonTagRow(
            feed=feed,
            kill=kill,
            profile_rows=tuple(
                ProfileHorizonTagProfileRow(profile=profile, row=row_lookup[profile][(feed, kill)])
                for profile in profiles
            ),
        )
        for kill in kills
        for feed in feeds
    )

    if not rows:
        return ProfileHorizonTagStudy(
            early_steps=early_steps,
            middle_steps=middle_steps,
            late_steps=late_steps,
            size=size,
            patch_radius=patch_radius,
            seed=seed,
            profiles=profiles,
            rows=tuple(),
            spotlights=tuple(),
        )

    def make_spotlight(row: ProfileHorizonTagRow, *, title: str, reason: str) -> ProfileHorizonTagSpotlight:
        return ProfileHorizonTagSpotlight(
            title=title,
            reason=reason,
            feed=row.feed,
            kill=row.kill,
            profiles=tuple(
                ProfileHorizonTagSpotlightProfile(
                    profile=profile,
                    row=row.row_for(profile),
                    state=simulate(
                        GrayScottParameters(feed=row.feed, kill=row.kill),
                        size=size,
                        steps=late_steps,
                        patch_radius=patch_radius,
                        seed=seed,
                        profile=profile,
                    ),
                )
                for profile in profiles
            ),
        )

    three_way_candidates = [row for row in rows if row.stability_class == PROFILE_HORIZON_THREE_WAY_SPLIT]
    rescue_candidates = [
        row for row in rows
        if row.min_late_active_fraction <= 0.05 and row.max_late_active_fraction >= 0.30 and row.unique_tag_count >= 2
    ]
    stable_active_candidates = [
        row for row in rows
        if row.stability_class == PROFILE_HORIZON_STABLE and row.min_late_active_fraction > 0.05
    ]

    three_way = max(
        three_way_candidates if three_way_candidates else rows,
        key=lambda row: (row.unique_tag_count, row.late_active_fraction_span, row.total_active_delta_span),
    )
    rescue = max(
        rescue_candidates if rescue_candidates else rows,
        key=lambda row: (row.late_active_fraction_span, row.total_active_delta_span, row.unique_tag_count),
    )
    stable_active = min(
        stable_active_candidates if stable_active_candidates else rows,
        key=lambda row: (row.late_active_fraction_span, row.total_active_delta_span, -row.max_late_active_fraction),
    )

    spotlights = [
        make_spotlight(
            three_way,
            title='Three-way tag split',
            reason=(
                f'F={three_way.feed:.3f}, k={three_way.kill:.3f} changes late-horizon meaning across profiles '
                f'({", ".join(f"{profile}: {three_way.row_for(profile).tag}" for profile in profiles)}).'
            ),
        ),
        make_spotlight(
            rescue,
            title='Profile rescue cell',
            reason=(
                f'F={rescue.feed:.3f}, k={rescue.kill:.3f} swings from {rescue.min_late_active_fraction:.3f} to '
                f'{rescue.max_late_active_fraction:.3f} late occupancy depending only on the seeded geometry.'
            ),
        ),
    ]
    if stable_active != three_way and stable_active != rescue:
        spotlights.append(
            make_spotlight(
                stable_active,
                title='Stable active counterexample',
                reason=(
                    f'F={stable_active.feed:.3f}, k={stable_active.kill:.3f} keeps one shared late-horizon tag '
                    f'under every bounded seed profile while staying visibly active.'
                ),
            )
        )

    return ProfileHorizonTagStudy(
        early_steps=early_steps,
        middle_steps=middle_steps,
        late_steps=late_steps,
        size=size,
        patch_radius=patch_radius,
        seed=seed,
        profiles=profiles,
        rows=rows,
        spotlights=tuple(spotlights),
    )
