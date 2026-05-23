# Gray-Scott initialization sensitivity sidecar

The horizon and grid-size passes settled two honest caveats, but one important one remained: **how much of the coarse chemistry story still depends on the seeded patch itself?**

This sidecar keeps the feed/kill grid, step count, and lattice size fixed. It only swaps between three bounded seed profiles with roughly comparable seeded mass:

- centered square patch
- split twin patches
- annulus shell

## What changed the most

- biggest active-fraction swing: `F = 0.030`, `k = 0.054` with `span = 1.000` (centered square -> split twin patches)
- biggest edge-density swing: `F = 0.026`, `k = 0.054` with `span = 0.0254`
- robust active counterexample: `F = 0.030`, `k = 0.051` stays active under every profile with only `span = 0.000`

## The practical read

- median active-fraction span across the whole grid: `0.067`
- median edge-density span across the whole grid: `0.0035`
- several cells are robust, which is good: the repo is not collapsing into “everything depends on the seed”
- some middle-band cells are not robust at all, which is equally useful: the same chemistry can flip from near-extinction to broad occupancy once the seeded patch is split or hollowed
- that means the coarse scan is now better framed as a scouting surface plus three bounded caveat passes: horizon, lattice size, and initialization geometry

## Caveat

These profiles are intentionally comparable, not identical. This pass measures seed-geometry sensitivity in a bounded way; it does not claim to have found one universal initialization family for the Gray-Scott model.

Open `art/gray-scott-initialization-sensitivity.png`, `art/gray-scott-initialization-sensitivity.csv`, and `notebooks/gray_scott_initialization_sensitivity.ipynb` together next.
