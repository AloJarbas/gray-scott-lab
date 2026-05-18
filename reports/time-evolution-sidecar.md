# Gray-Scott time evolution sidecar

The atlas and parameter map say what different regimes look like after a fixed run. This sidecar asks the next useful question: how does one regime get there?

This pass stays narrow on purpose. It follows the curated `worm bands` preset and keeps the same seed, grid, and chemistry parameters all the way through.

## Setup

- `feed = 0.022`
- `kill = 0.051`
- `size = 72`
- `steps = 1600`
- `seed = 0`

## Main read

- active fraction peaks around step `1160` at `70.9%`
- edge density peaks around step `560` at `0.0235`
- the regime does not simply fill in at one constant pace: it first grows chemical occupancy, then keeps reorganizing the interfaces as the banded structure settles
- that is why the repo tracks both active fraction and edge density instead of pretending one scalar is the whole story

## What the snapshots add

- early frames show the seeded patch stretching into directional fronts
- middle frames show the field becoming much more occupied without yet looking final
- later frames show that the pattern can keep sharpening and reorganizing after the chemistry is already broadly active

## Caveat

This is one preset with one deterministic seed. It is a growth-process sidecar, not a claim about the whole model family.

Open `art/gray-scott-time-evolution.png`, `art/gray-scott-time-evolution.csv`, and `notebooks/gray_scott_time_evolution.ipynb` together next.
