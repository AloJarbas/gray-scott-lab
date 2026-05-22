# Gray-Scott grid-size comparison sidecar

The horizon comparison settled one honest question: some cells were still changing because the run was too short. This follow-up asks the next one: **after the longer run, which cells still depend on the lattice size itself?**

This sidecar holds the feed/kill grid, seed, and 1400-step horizon fixed. It then compares the same scan on a `40×40` lattice and a `72×72` lattice while scaling the seeded patch from radius `5` to `9` so the initial disturbance stays roughly proportional to the box.

## What changed the most

- biggest larger-lattice growth: `F = 0.030`, `k = 0.054` with `Δactive = +1.000` and `Δedge = -0.0012`
- biggest larger-lattice fade: `F = 0.018`, `k = 0.054` with `Δactive = -0.134` and `Δedge = -0.0027`
- sharpest larger-lattice front growth: `F = 0.018`, `k = 0.051` with `Δedge = +0.0134`
- strongest larger-lattice smoothing: `F = 0.022`, `k = 0.060` with `Δedge = -0.0128`

## The practical read

- median absolute active-fraction shift across the whole grid: `0.042`
- median absolute edge-density shift across the whole grid: `0.0037`
- several cells barely move, which is good news: the first chemistry story survives a larger arena
- some cells do move a lot, especially where the smaller lattice either trapped the fronts too tightly or let the initial patch dominate too much of the field
- that means the coarse map is maturing into a real packet: horizon drift and finite-size drift are now separate failure modes instead of one vague caution

## Caveat

This still uses one deterministic seed and one scaled patch rule. It is a bounded finite-size check, not a universal claim that the whole Gray-Scott regime atlas is now settled.

Open `art/gray-scott-grid-size-comparison.png`, `art/gray-scott-grid-size-comparison.csv`, and `notebooks/gray_scott_grid_size_comparison.ipynb` together next.
