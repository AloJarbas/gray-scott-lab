# Gray-Scott seed-profile horizon tags sidecar

The earlier horizon-tag card made one honest point: the unsettled cells were not one generic caution blob. But it still left one question open: **does that late-horizon fate belong to the chemistry cell itself, or can the seeded geometry still change the tag?**

This sidecar keeps the same `40×40` grid, the same `700` → `1400` → `2800` horizon rule, and the same feed/kill scan. It only swaps between `centered square`, `split twin patches`, and `annulus shell`.

## Tag agreement across profiles

- stable cells (`3x`): `8`
- two-against-one flips (`2+1`): `16`
- three-way splits: `1`
- largest late active-fraction span: `F = 0.026`, `k = 0.051`, `span = 1.000`

## Per-profile tag counts

- centered square: settled `14`, growing `4`, fading `5`, reversing `2`
- split twin patches: settled `15`, growing `5`, fading `4`, reversing `1`
- annulus shell: settled `13`, growing `4`, fading `5`, reversing `3`

## The useful read

- three-way split example: `F = 0.022`, `k = 0.051`
- profile rescue example: `F = 0.026`, `k = 0.051`
- stable active counterexample: `F = 0.030`, `k = 0.051`
- the core point is that the late-horizon tag is not always a chemistry-only identity. Some cells keep one shared tag across seed profiles, but others move between fading, growing, and reversing even though feed, kill, lattice, and horizon rule never changed.
- that makes the old reversing lane narrower and more conditional than the center-profile card alone suggested. The seed geometry can erase it, move it, or create a different late-horizon caution altogether.

## Caveat

This is still a bounded three-profile audit, not a universal initialization theorem. It makes the caveat packet sharper because it shows where the late-horizon read survives the profile swap and where it does not.

Open `art/gray-scott-profile-horizon-tags.png`, `art/gray-scott-profile-horizon-tags.csv`, and `notebooks/gray_scott_profile_horizon_tags.ipynb` together next.
