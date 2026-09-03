# Unified carrier — real configuration-space projection

*Captured 2026-09-03, per Alan's own direct request at session pause.
A real, grounded projection, not a hand-wave: every number below is
computed from actual field widths, either read directly from the four
real, sim-verified `v4` cores already built (`#618`-`#621`) or from
the three not-yet-built cores' own real `v1` RTL field maps, applying
the SAME real widening/addon conventions those four builds already
established and proved. `nano` is included for completeness, marked
clearly as the one core that will be STRIPPED to match this shape, not
added to (per this same session's own closing note) — its own real
`v1` field widths are used as the honest basis for what survives.*

## Two real numbers, not one, and why both matter

A single "total configurations" number is misleading on its own — a
32-bit data field like `ram`'s `init_data` or `comparator`'s
`threshold` contributes 2³² raw combinations, but those aren't 4
billion different *behaviors* the way `subtract_mode`'s 2 states are —
it's one behavior ("hold and offer whatever value you're given"),
multiplied by every possible value that behavior could hold. Counting
it the same way as a real structural choice buries the genuinely
interesting number under an arithmetic artifact.

So this note gives both, kept honestly separate:

- **Full state space** — every real field counted at its full width,
  including raw data payloads. The honest, complete number; also the
  reason exhaustive testing was never the goal (real, sim-verified
  functional coverage per core is what `#618`-`#621` actually did).
- **Structural-only** — the same calculation with pure data-payload
  fields (`init_data`, `threshold`, `value_0`-`value_3`,
  `fixed_value_low/equal/high`) excluded, counted as a single real
  "holds whatever value it's given" slot instead of their own raw
  width. This is the more meaningful number for understanding real
  *behavioral* diversity — how many genuinely different ways a cell
  can be told to act, not how many numbers it could be told to act on.

The line between the two is a judgment call in a few places (`nano`'s
own `pattern_low/equal/high` fields are small comparison values, kept
structural here since they're closer to a mode selector than an
arbitrary payload) — flagged here rather than silently decided.

## The real, shared multiplier every core now carries

Per `#617`-`#621`'s own real work: every core now carries the SAME
real, already-proven 3-addon chain (`nibble_mask` → `shift`/`lane` →
`invert`, `#303`-`#312`) and the same real 6-bit-headroom mask fields
(4 real physically-wired bits each). Computed as real, DISTINCT
behaviors (not raw bit patterns — e.g. `shift_amt` only has 9 real
meaningful values out of its 32 raw ones, per `shift_lane_addon_v1.v`'s
own real, deliberate sparse design):

| Addon | Real distinct behaviors |
|---|---|
| `nibble_mask` (off, or 1 of 255 real masks) | 256 |
| `shift`/`lane` (off; 9 real amounts × IN; 9 × 8 lane cuts × OUT) | 82 |
| `invert` (on/off) | 2 |
| **Shared addon total** | **41,984** |

Each real, physically-wired 4-bit direction field (`downstream_mask`,
`upstream_mask`, etc.) contributes 16 real distinct combinations (every
raw value is a real, meaningful behavior under the OR-combine
convention, `#153`).

## Full state space (includes raw data payloads at full width)

| Core | Own real fields | × masks | × addon | = Total |
|---|---:|---:|---:|---:|
| `adder` (built, `#618`) | 2 | 256 | 41,984 | 2.15 × 10⁷ |
| `ram` (built, `#619`) | 1.72 × 10¹⁰ | 256 | 41,984 | 1.85 × 10¹⁷ |
| `comparator` (built, `#620`) | 4.29 × 10⁹ | 256 | 41,984 | 4.62 × 10¹⁶ |
| `accumulator` (built, `#621`) | 8.59 × 10⁹ | 16 | 41,984 | 5.77 × 10¹⁵ |
| `latch` (projected) | 4,096 | 16 | 41,984 | 2.75 × 10⁹ |
| `sequencer` (projected) | 1.72 × 10¹⁰ | 16 | 41,984 | 1.15 × 10¹⁶ |
| `branch` (projected) | 4.40 × 10¹² | 1 | 41,984 | 1.85 × 10¹⁷ |
| `nano` (projected, strip not add) | 2.52 × 10⁷ | 1 | 41,984 | 1.06 × 10¹² |
| **Grand total (one physical cell, any core selected)** | | | | **≈ 4.33 × 10¹⁷** |

## Structural-only (data payloads excluded — the more meaningful number)

| Core | Own structural fields | × masks | × addon | = Total |
|---|---:|---:|---:|---:|
| `adder` (built) | 2 | 256 | 41,984 | 21,495,808 |
| `ram` (built) | 4 | 256 | 41,984 | 42,991,616 |
| `comparator` (built) | 1 | 256 | 41,984 | 10,747,904 |
| `accumulator` (built) | 131,072 | 16 | 41,984 | 88,046,829,568 |
| `latch` (projected) | 4,096 | 16 | 41,984 | 2,751,463,424 |
| `sequencer` (projected) | 4 | 16 | 41,984 | 2,686,976 |
| `branch` (projected) | 2,097,152 | 1 | 41,984 | 88,046,829,568 |
| `nano` (projected, strip not add) | 25,165,824 | 1 | 41,984 | 1,056,561,954,816 |
| **Grand total (structural-only)** | | | | **≈ 1.235 × 10¹²** |

## Real, honest caveats, stated plainly

- **Four rows are real and sim-verified** (`adder`/`ram`/`comparator`/
  `accumulator`, `#618`-`#621`) — their own real field widths were
  read directly from working, tested RTL. **Three rows are
  projections**, not builds — `latch`/`sequencer`/`branch` use their
  own real `v1` field widths with the SAME widening/addon convention
  already proven four times, but the actual `v4` files don't exist yet
  and could reveal real, unforeseen adaptations the way `ram`'s split-
  write and `accumulator`'s `active`-gates-internal-state real
  discoveries did.
- **`nano` is the one real exception to the whole pattern**: per this
  session's own closing note, it won't be built up to match the
  others — it already has the programming channel and more; it will
  need STRIPPING down to fit the same uniform shape. Its own row here
  uses its real, current `v1` field widths as the honest starting
  point for that future work, not a prediction of what survives.
- **This is a real measure of EXPRESSIVENESS, not of usefulness or
  test coverage.** Most of this space is neither meaningful to a real
  program nor something any real testing regime should try to
  enumerate — `#618`-`#621`'s own real discipline (functional
  categories, sim-verified, not exhaustive) remains the right approach
  regardless of how large this number is.
- **No real ALM/Fmax cost is implied by this table at all** — a large
  configuration space costs nothing extra in silicon by itself (it's
  bits already paid for); the real hardware cost question is the
  separate, standing one from `#617`-`#621`'s own scope (measure every
  real addon/core as a delta), still awaiting Alan's own Quartus run.
