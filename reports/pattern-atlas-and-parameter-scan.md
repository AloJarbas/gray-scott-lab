# Gray-Scott pattern atlas and parameter scan

This repo starts with a simple question: what do the Gray-Scott chemistry knobs actually do to the field if you hold the initialization fixed and only change feed and kill?

The answer here is deliberately practical. Instead of claiming a complete phase diagram, this first pass gives two things you can rerun:

- a curated four-panel atlas with visibly different regimes
- a coarse feed-vs-kill scan that measures active fraction and edge density

## Curated atlas

### sparse spots

- `feed = 0.014`, `kill = 0.054`, `steps = 1800`
- `mean V = 0.040`
- `std V = 0.088`
- `active fraction = 11.5%`
- `edge density = 0.0101`

### worm bands

- `feed = 0.022`, `kill = 0.051`, `steps = 1600`
- `mean V = 0.154`
- `std V = 0.088`
- `active fraction = 54.8%`
- `edge density = 0.0206`

### labyrinth mix

- `feed = 0.026`, `kill = 0.055`, `steps = 1400`
- `mean V = 0.161`
- `std V = 0.089`
- `active fraction = 54.8%`
- `edge density = 0.0246`

### split spots

- `feed = 0.030`, `kill = 0.062`, `steps = 1400`
- `mean V = 0.058`
- `std V = 0.100`
- `active fraction = 16.7%`
- `edge density = 0.0151`

## Coarse parameter scan

- highest edge density on this coarse grid: `F = 0.030`, `k = 0.057` with `edge density = 0.0266`
- most chemically active field on this coarse grid: `F = 0.026`, `k = 0.051` with `active fraction = 100.0%`
- sparsest surviving field on this coarse grid: `F = 0.014`, `k = 0.051` with `active fraction = 0.0%`

## Reading the first pass

- low active fraction means the chemistry only survives in small islands
- high edge density marks sharper reaction fronts and busier boundaries
- the middle of the scanned band is where the field stops looking like isolated dots but has not yet blurred into a broad fill pattern

Open `art/gray-scott-pattern-atlas.png`, `art/gray-scott-parameter-map.png`, and `notebooks/gray_scott_regimes.ipynb` together for the full packet.
