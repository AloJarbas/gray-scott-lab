# Gray-Scott horizon tags sidecar

The horizon, grid-size, and seed-profile passes all made the coarse scan more honest, but they still left one practical question open: **when a cell is not settled yet, what kind of late-horizon failure is it actually showing?**

This sidecar keeps the same feed/kill grid, seed, and `40×40` lattice, then measures the same cells at `700`, `1400`, and `2800` steps.

The tag rule is intentionally bounded. It only reads the active-fraction path across those three horizons, then keeps edge density nearby as context. The tags are descriptive, not universal:

- `settled`: both horizon legs stay small enough that the cell is basically stable already
- `growing`: the late horizon still ends materially busier than the early one
- `fading`: the late horizon collapses materially below the early one
- `reversing`: the cell changes direction between the two horizon legs instead of just drifting one way

## What the tag map says

- settled cells: `14`
- late-growing cells: `4`
- late-fading cells: `5`
- reversing cells: `2`
- biggest late growth: `F = 0.022`, `k = 0.054` with `Δactive_{late} = +0.139`
- biggest late fade: `F = 0.026`, `k = 0.051` with `Δactive_{late} = -1.000`

## The useful read

- settled active counterexample: `F = 0.030`, `k = 0.060` stays visibly active without large horizon drift
- strongest late-growing example: `F = 0.030`, `k = 0.063`
- strongest late-fading example: `F = 0.026`, `k = 0.051`
- reversing example: `F = 0.022`, `k = 0.051` changes direction between horizon legs
- that means the unsettled part of the map is not one generic caution blob after all. Some cells keep filling in, some were overread and later die back, and a smaller group overshoots before turning around.

## Caveat

This is still one lattice, one deterministic seed, and one active-fraction-driven tag rule. It sharpens the repo’s caveat story; it does not claim to classify the whole Gray-Scott plane once and for all.

Open `art/gray-scott-horizon-tags.png`, `art/gray-scott-horizon-tags.csv`, and `notebooks/gray_scott_horizon_tags.ipynb` together next.
