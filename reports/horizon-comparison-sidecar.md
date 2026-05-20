# Gray-Scott horizon comparison sidecar

The original parameter map was useful, but it left one honest question open: **how much of that coarse structure was already persistent, and how much was still transient because the run stopped early?**

This sidecar keeps the feed/kill grid, seed, and spatial size fixed and only changes the simulation horizon from 700 to 1400 Euler steps.

## What changed the most

- biggest late growth: `F = 0.022`, `k = 0.051` with `Δactive = +0.321` and `Δedge = +0.0170`
- strongest fade: `F = 0.030`, `k = 0.054` with `Δactive = -0.998` and `Δedge = -0.0011`
- sharpest late interface growth: `F = 0.022`, `k = 0.051` with `Δedge = +0.0170`
- strongest interface smoothing: `F = 0.018`, `k = 0.057` with `Δedge = -0.0186`

## The practical read

- median absolute active-fraction shift across the whole grid: `0.016`
- median absolute edge-density shift across the whole grid: `0.0006`
- some cells that looked mature at 700 steps were still transient and cooled sharply by 1400 steps
- some middle-band settings kept growing into busier, sharper patterns instead of simply freezing in place
- that makes the first parameter map a good scouting pass, not a finished phase diagram

## Caveat

This still holds grid size and seed fixed. It separates **time-horizon drift** from the original map, but it does not yet answer whether the same cells stay stable under a larger lattice or a different initialization patch.

Open `art/gray-scott-horizon-comparison.png`, `art/gray-scott-horizon-comparison.csv`, and `notebooks/gray_scott_horizon_comparison.ipynb` together next.
