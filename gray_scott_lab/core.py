from __future__ import annotations

from dataclasses import dataclass
import random

Grid = list[list[float]]


@dataclass(frozen=True)
class GrayScottParameters:
    feed: float
    kill: float
    diffusion_u: float = 0.16
    diffusion_v: float = 0.08


@dataclass(frozen=True)
class GrayScottPreset:
    name: str
    feed: float
    kill: float
    steps: int = 1200
    size: int = 72
    patch_radius: int = 7
    seed: int = 0


@dataclass
class GrayScottState:
    u: Grid
    v: Grid

    @property
    def size(self) -> int:
        return len(self.u)


def make_grid(size: int, value: float) -> Grid:
    return [[value for _ in range(size)] for _ in range(size)]


def seed_state(size: int = 72, *, patch_radius: int = 7, seed: int = 0) -> GrayScottState:
    u = make_grid(size, 1.0)
    v = make_grid(size, 0.0)
    center = size // 2
    rng = random.Random(seed)

    for i in range(center - patch_radius, center + patch_radius):
        for j in range(center - patch_radius, center + patch_radius):
            u[i][j] = 0.5
            v[i][j] = 0.25

    noise_radius = patch_radius + 5
    for i in range(center - noise_radius, center + noise_radius):
        for j in range(center - noise_radius, center + noise_radius):
            u[i][j] = min(1.0, max(0.0, u[i][j] - 0.02 * (rng.random() - 0.5)))
            v[i][j] = min(1.0, max(0.0, v[i][j] + 0.02 * (rng.random() - 0.5)))

    return GrayScottState(u=u, v=v)


def step(state: GrayScottState, params: GrayScottParameters) -> GrayScottState:
    size = state.size
    u = state.u
    v = state.v
    next_u = [row[:] for row in u]
    next_v = [row[:] for row in v]

    feed = params.feed
    kill = params.kill
    diffusion_u = params.diffusion_u
    diffusion_v = params.diffusion_v

    for i in range(size):
        i_minus = (i - 1) % size
        i_plus = (i + 1) % size
        u_row = u[i]
        u_row_minus = u[i_minus]
        u_row_plus = u[i_plus]
        v_row = v[i]
        v_row_minus = v[i_minus]
        v_row_plus = v[i_plus]
        next_u_row = next_u[i]
        next_v_row = next_v[i]

        for j in range(size):
            j_minus = (j - 1) % size
            j_plus = (j + 1) % size
            u_value = u_row[j]
            v_value = v_row[j]
            lap_u = u_row_minus[j] + u_row_plus[j] + u_row[j_minus] + u_row[j_plus] - 4.0 * u_value
            lap_v = v_row_minus[j] + v_row_plus[j] + v_row[j_minus] + v_row[j_plus] - 4.0 * v_value
            reaction = u_value * v_value * v_value
            updated_u = u_value + diffusion_u * lap_u - reaction + feed * (1.0 - u_value)
            updated_v = v_value + diffusion_v * lap_v + reaction - (feed + kill) * v_value
            next_u_row[j] = min(1.0, max(0.0, updated_u))
            next_v_row[j] = min(1.0, max(0.0, updated_v))

    return GrayScottState(u=next_u, v=next_v)


def simulate(
    params: GrayScottParameters,
    *,
    size: int = 72,
    steps: int = 1200,
    patch_radius: int = 7,
    seed: int = 0,
) -> GrayScottState:
    state = seed_state(size=size, patch_radius=patch_radius, seed=seed)
    for _ in range(steps):
        state = step(state, params)
    return state


def simulate_preset(preset: GrayScottPreset) -> GrayScottState:
    return simulate(
        GrayScottParameters(feed=preset.feed, kill=preset.kill),
        size=preset.size,
        steps=preset.steps,
        patch_radius=preset.patch_radius,
        seed=preset.seed,
    )


def flatten(grid: Grid) -> list[float]:
    return [value for row in grid for value in row]
