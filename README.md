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

- `gray_scott_lab/core.py`: deterministic seeding, explicit Euler updates, simulation helpers, and sampled trajectory capture for time-evolution studies
- `gray_scott_lab/analysis.py`: curated presets, pattern metrics for activity and interface sharpness, a time-evolution study for the worm-band lane, and a new short-vs-long horizon comparison for the coarse parameter grid
- `gray_scott_lab/render.py`: SVG atlas, parameter-map, time-evolution, and horizon-comparison renderers plus PNG export
- `gray_scott_lab/cli.py`: one-shot summaries plus atlas, metric-map, time-evolution, and horizon-comparison rendering commands
- `scripts/generate_gallery.py`: rebuild the public artifacts, CSV sidecars, reports, and notebooks in one pass
- `reports/pattern-atlas-and-parameter-scan.md`, `reports/time-evolution-sidecar.md`, and `reports/horizon-comparison-sidecar.md`: technical sidecars for reading the regimes as final states, growth processes, and horizon-sensitive scans
- `notebooks/gray_scott_regimes.ipynb`, `notebooks/gray_scott_time_evolution.ipynb`, and `notebooks/gray_scott_horizon_comparison.ipynb`: slower companions with equations, code, and interpretation
- `tests/test_core.py`: small checks for determinism, bounds, regime separation, time-evolution sampling, and the new horizon-comparison drift

## Generated artifacts

### Pattern atlas

<img src="art/gray-scott-pattern-atlas.png" width="980" alt="Gray-Scott pattern atlas showing sparse spots, worm bands, labyrinth mix, and split spots" />

### Coarse parameter scan

<img src="art/gray-scott-parameter-map.png" width="920" alt="Gray-Scott parameter scan heatmaps for active fraction and edge density" />

### Time evolution sidecar

<img src="art/gray-scott-time-evolution.png" width="980" alt="Gray-Scott time evolution card showing six snapshots and metric traces for the worm-band preset" />

### Horizon comparison sidecar

<img src="art/gray-scott-horizon-comparison.png" width="980" alt="Gray-Scott horizon comparison card showing the coarse scan at 700 and 1400 steps plus active-fraction and edge-density drift maps" />

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

Render the time-evolution sidecar for the curated worm-band preset:

```bash
python3 -m gray_scott_lab.cli render-timeline --output art/gray-scott-time-evolution.svg --png-output art/gray-scott-time-evolution.png
```

Render the short-vs-long horizon comparison for the coarse scan:

```bash
python3 -m gray_scott_lab.cli render-horizon-comparison --output art/gray-scott-horizon-comparison.svg --png-output art/gray-scott-horizon-comparison.png
```

## Why this repo is interesting

Most introductions stop at pretty pictures. This one starts building a reusable measurement lane:

- the atlas gives four reproducible regimes with fixed initialization and step counts
- the parameter scan turns the chemistry knobs into an experiment instead of a list of screenshot captions
- the new time-evolution sidecar shows one regime as a growth process instead of only a final frame
- the new horizon-comparison sidecar checks whether the coarse scan had already settled or was still moving under a longer run
- the CSV, reports, notebooks, and tests make it easier to deepen into a real regime study later

## Good next moves

- compare the same parameter scan at one larger grid size now that the horizon-comparison pass has already separated time drift from the first cutoff story
- add one bounded note on how much the seeded patch controls the outcome before claiming a broad phase diagram
- extend the chemistry lane with one second reaction-diffusion model only if it reveals a genuinely different pattern family instead of duplicating the same feed/kill story
