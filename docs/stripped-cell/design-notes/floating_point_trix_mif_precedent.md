# Floating point on the current substrate: what TRIX/MIF prior art actually offers

*Captured 2026-09-22, per Alan's direct request to look at the TRIX system and the MIF format for
reference before floating point work begins. `old_trix_domain_family.onion` and
`old_full_cell_tile_library.onion` extracted via the Onion tool (both submodule and archives were
un-initialized this session; `git submodule update --init`, `build_ext.py build_ext --inplace`,
`pip install -e . --break-system-packages`, then staged into distinguishing subdirectories per the
known same-basename extraction gotcha). Primary sources read directly -- `cell_format.py`'s real
`MIF_Format` class and `fp_tiles.py`'s real `make_fp32_add`/`make_mif_add`/`make_mif_mul` -- not
recalled from the existing `mathtrix_mif_connection.md` note (2026-09-07) alone, though that note's
own findings are confirmed accurate and extended here, not superseded.*

## Two genuinely different prior-art approaches existed, not one

**MIF (MathTrix Internal Float)** -- SPLIT representation. A float is never packed into one word for
internal computation at all: it enters the fabric via `MIF_UNPACK`, lives from then on as a
**control** cell (exponent, sign, and three EXPLICIT flags) plus a **mantissa** cell (the significand
with its implicit leading 1 already expanded), and is only repacked via `MIF_PACK` at the boundary
back out. The real internal layout, read directly from `cell_format.py`'s `MIF_Format` class:

```
control  [31:24] exponent (biased-127)   [23] sign        [22] is_nan
         [21] is_inf                     [20] is_zero     [19:16] guard bits
         [15:0]  unused
mantissa [23:0]  significand, implicit-1 already expanded  [31:24] unused
```

This is a genuinely useful design choice beyond "split the word in half": the three flag bits mean
`is_nan`/`is_inf`/`is_zero` never need re-deriving from the exponent pattern on every operation, and
the guard bits give Newton-Raphson iterations (`MIF_DIV`, `MIF_SQRT`) somewhere to keep rounding
precision without widening the whole mantissa field.

**FP32_ADD/FP32_MUL** -- PACKED representation, gate-level. A completely different, earlier design:
a real IEEE-754 adder built from primitive NOR/AND/OR/XOR gates via a `NORBuilder`, operating on the
standard packed 32-bit word throughout. Read directly from `fp_tiles.py`'s `make_fp32_add`: decompose
sign/exponent/mantissa, an 8-bit ripple-carry subtract to find which exponent is larger, a full
log-depth barrel shifter to align the smaller mantissa, a 24-bit mantissa add, then normalise and
pack. Both real, complete implementations existed side by side -- MIF was not a replacement for the
packed approach, it was a different point in the same design space, evaluated on its own terms.

## The concrete cost difference between the two, read directly from `make_mif_add`'s own comment

Compared to `FP32_ADD`, the split representation buys real savings, stated in the tile's own code:
- no decompose stage at all -- the fields are already separated the moment a value enters MIF form
- the exponent compare reads directly from isolated control-cell bits -- no subtract tree needed just
  to find which exponent is larger, since sign and magnitude are already sitting in clean nibbles
- only ONE barrel shifter is needed (for the smaller operand), and its input is a clean 24-bit
  mantissa, not a field extracted from a packed word
- the result stays in MIF form -- chained operations pay no repack cost between them, only the first
  unpack and the final pack for a whole expression

This is the same real principle the project's own README/design-notes already state for the TRIX
family generally: push domain-specific complexity to the boundary, pay it once, and let everything in
between use a plain, already-general substrate representation.

## Both historical systems were, deliberately and honestly, simplified

Neither one is a certifiably-correct IEEE-754 implementation, and neither pretended to be. `FP32_ADD`'s
own docstring: "simplified: no denormals, no NaN propagation, round-to-nearest-even approximated as
truncation." `MIF_Format`'s own `constraints`: `subnormal_handling: "flush_to_zero"` with an explicit
note to "upgrade to full later." Whenever floating point is picked up here, this is real, direct
precedent for NOT attempting full IEEE-754 compliance (denormals, correct rounding, NaN propagation)
on a first pass -- both prior systems that actually got built and used chose the same deliberate scope
cut, for the same reason: those cases are expensive and rare, and a first working system is worth more
than a fully compliant one that never ships.

## A real, honest limitation of the OLD systems this project's own current work already exceeds

Both `fp_tiles.py` systems (`FP32_ADD`, `MIF_ADD`, and the rest) are, by their own test suite's stated
scope, STRUCTURAL/COST models: they measure real cell count and pipeline depth from the built gate
network, but the actual numeric arithmetic is computed in Python `float` by the caller as a stand-in --
confirmed directly from `test_mif_recip.py`'s own docstring: "the numeric reference is computed in
float by the caller... these checks assert those structural properties, not a `run_tile` numeric
evaluation." Neither historical system ever simulated the bit-level arithmetic itself end to end.

This project's OWN mask-shift-mask-shift mantissa-extraction technique (`mathtrix_mif_connection.md`,
2026-09-07; `tests/vm/test_unicell_super_automaton_v1.py`) is, in this one specific respect, already
MORE rigorously verified than either historical system attempted: it reproduces Python's own
`struct`-computed mantissa bit-for-bit, for seven real IEEE-754 test values, using the CURRENT
substrate's own already-existing primitives (`nibble_mask`, `shift_fine`, `shift_lane_v2`) with zero
new hardware. That is the real, concrete, ALREADY-DONE starting point -- not a historical precedent to
port, a piece of the current work already ahead of the historical prior art in this specific way.

## What genuinely could transplant here, and what needs fresh design work

**Could transplant, as a design PRINCIPLE, confirmed twice independently (`#379`/`#380`):** wide
logical values as N cells of the fabric's own native width, not one wide cell -- MIF's control+mantissa
split and the DSP-wrapper's two-parallel-32-bit-lane conclusion are the same shape, arrived at for
unrelated reasons. Whatever floating-point width is picked (fp32 first, most likely, given the
substrate is "still flat 32-bit," `#383`/`#384`), the split-into-existing-width-cells shape is the
right starting shape, not a new wide-value fabric mechanism.

**Could transplant, as a CONCRETE layout, needing verification against the current core set rather
than copied blind:** MIF's own control-cell bit layout (exponent, sign, three explicit flags, guard
bits) is a genuinely well-thought design already proven useful across a dozen real domain
implementations (FlowTrix's LBM solver, NeuroTrix's LIF neurons) -- worth using as the starting
LAYOUT, re-checked bit by bit against whatever cell/core actually holds it here, not assumed
identical.

**Needs fresh design work, not transplantable as code:** the actual gate/cell NETWORKS
(`make_fp32_add`'s barrel shifter, `make_mif_add`'s alignment stage) are built on `NORBuilder`, an
abstraction over the OLD full-cell architecture's own primitive gate model -- genuinely useful as
ALGORITHMIC reference (what stages a real float add needs: exponent compare, align, add, normalise,
pack) but not directly portable code, since the current substrate's cell/core model, addon-chain
mechanism, and two-arrival firing convention are all different primitives than `NORBuilder` assumed.

**Still entirely unbuilt, on any substrate, per the existing note's own honest scope:** the PACK
direction (reassembling split control+mantissa back into a standard word -- the mirror of the already-
verified extraction, and a real, symmetric problem to the fan-out/combine work already proven
elsewhere in this project); any actual arithmetic tile (`ADD`/`MUL`/etc.) operating on a split
representation on the CURRENT substrate; and the larger, still-open question of whether this project
follows MIF's own "never repack, split from the boundary in" strategy for real, or takes a different
path.

## Honest scope of this note

This is grounding, not a build. Nothing new was written to the current codebase's own float-handling
capability in this pass -- this closes the "what does TRIX/MIF prior art actually offer" research
question Alan asked, ahead of picking up the fp4/8/16/32/64 expansion item for real. `#384`'s own
cost-basis argument stands unchanged: doing ANY one float width properly, end to end (pack direction,
arithmetic tiles, real VM verification), is realistically comparable in scope to the DSP-wrapper
interface design that took a full day here -- a real, bounded piece of work to schedule deliberately,
not a small follow-on to the extraction technique already proven.
