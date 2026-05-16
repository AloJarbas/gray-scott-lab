# Gray-Scott Lab

A compact reaction-diffusion lab for the Gray-Scott model.

The point is simple: turn the feed and kill knobs into something you can see and measure instead of treating pattern names like folklore.

## Model

The simulator evolves the standard two-species Gray-Scott system on a periodic square grid:

```text
u[t+1] = u[t] + D_u ∇²u - u v² + F (1 - u)
v[t+1] = v[t] + D_v ∇²v + u v² - (F + k) v
```

This repo starts with a fixed seeded perturbation and then asks two day-one questions:

- what visibly different regimes show up for a few curated `(F, k)` pairs?
- what changes on a coarse feed-vs-kill scan if you measure active fraction and edge density instead of only eyeballing the field?

## What is here

- `gray_scott_lab/core.py`: deterministic seeding, explicit Euler updates, and simulation helpers
- `gray_scott_lab/analysis.py`: curated presets plus pattern metrics for activity and interface sharpness
- `gray_scott_lab/render.py`: SVG atlas and parameter-map renderers plus PNG export
- `gray_scott_lab/cli.py`: one-shot summaries and figure rendering commands
- `scripts/generate_gallery.py`: rebuild the public artifacts, CSV, and report in one pass
- `reports/pattern-atlas-and-parameter-scan.md`: the first technical sidecar for reading the regimes
- `notebooks/gray_scott_regimes.ipynb`: a slower companion notebook with equations, code, and interpretation
- `tests/test_core.py`: small checks for determinism, bounds, and regime separation

## Generated artifacts

### Pattern atlas

<img src="art/gray-scott-pattern-atlas.png" width="980" alt="Gray-Scott pattern atlas showing sparse spots, worm bands, labyrinth mix, and split spots" />

### Coarse parameter scan

<img src="art/gray-scott-parameter-map.png" width="920" alt="Gray-Scott parameter scan heatmaps for active fraction and edge density" />

## Run it

```bash
python3 scripts/generate_gallery.py
python3 -m unittest discover -s tests
```

Get a quick metric summary for one pair:

```bash
python3 -m gray_scott_lab.cli summarize --feed 0.022 --kill 0.051
```

Render the atlas alone:

```bash
python3 -m gray_scott_lab.cli render-atlas --output art/gray-scott-pattern-atlas.svg --png-output art/gray-scott-pattern-atlas.png
```

Render the coarse parameter scan alone:

```bash
python3 -m gray_scott_lab.cli render-metric-map --output art/gray-scott-parameter-map.svg --png-output art/gray-scott-parameter-map.png
```

## Why this repo is interesting

Most introductions stop at pretty pictures. This one starts building a reusable measurement lane:

- the atlas gives four reproducible regimes with fixed initialization and step counts
- the parameter scan turns the chemistry knobs into an experiment instead of a list of screenshot captions
- the CSV, report, notebook, and tests make it easier to deepen into a real regime study later

## Good next moves

- add a time-series sidecar so one preset can be read as a growth process instead of only a final frame
- compare the same parameter scan at two grid sizes or integration horizons to separate real structure from cutoff effects
- add one bounded note on how much the seeded patch controls the outcome before claiming a broad phase diagram
