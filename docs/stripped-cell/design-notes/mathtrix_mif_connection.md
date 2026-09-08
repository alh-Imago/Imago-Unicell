# The MathTrix/MIF connection — real prior art for the FP split, and a validated field-extraction technique

*Captured 2026-09-07, per Alan's own direct request to deep-dive the
MathTrix archive for prior work relevant to splitting a packed
float's exponent and mantissa, following directly from the lane
combine/fan-out work (`#692`-`#696`). Real findings below, cross-
checked against the current project's own real capabilities, not
just historical color.*

## The real prior art, found and confirmed

`archeology/shared/docs/software/PAPER_DRAFT.md` and `FORMAT_
DEFINITION_GUIDE.md` describe **MIF (MathTrix Internal Float)** — a
complete, tested floating-point system built on the old, pre-nano
full-cell architecture, not a sketch:

- **17 real tiles** (`UNPACK`, `PACK`, `ADD`, `SUB`, `MUL`, `DIV`
  (Newton-Raphson), `SQRT`, `MADD`, `ABS`, `NEG`, `MIN`, `MAX`, five
  comparisons), later grown to 20 with `MIF_MUX`/`MIF_RECIP`/`MIF_
  RSQRT`.
- **Real, measured numbers**, not estimates: `MIF_MUL` = 3,066 cells /
  89-tick depth; `MIF_DIV` = 4,789 cells / 1,177-tick depth (the
  Newton-Raphson iteration shows up directly in that depth number).
- **242/242 tile tests passing**, and real applications built on it:
  FlowTrix's lattice-Boltzmann solver validated against the actual
  Strouhal-number correlation for flow past a cylinder; NeuroTrix's
  spiking-neuron model matched a reference implementation over
  300-tick runs.
- MIF was the reference case that got generalized into a whole
  `FormatDefinition` system, later reused for DNA, chemistry, physics
  constants, and finance domains.

## The real design decision, confirmed precisely

MIF never packs a float into one word for internal computation at
all — exponent+sign live in one cell ("control"), mantissa lives in a
separate cell, from the moment data enters the fabric. The packed
IEEE-754 word only exists at the real boundary (`MIF_UNPACK`/`MIF_
PACK`), paid once per value, amortized across however many arithmetic
operations follow on that value afterward. This is the same real
"avoid the split problem, don't solve it repeatedly" framing
`docs/stripped-cell/design-notes/llvm_ir_frontend_completion_scope.md`
already named as the natural fit for this project's own style.

## A real, second connection, found while reading, not gone looking for

The same archive names a **"preloaded-A" pattern** — a cell whose
value is loaded once at configure time and fires with zero runtime
cost, used there for physical constants (CODATA values, lattice
weights). This is the same real idea as this session's own freeze/
preload/unfreeze mechanism (`#686`/`#687`) — independently arrived at
twice, on two completely different hardware generations, for the same
real reason. Worth keeping on record as real, cross-generational
validation of that design choice, not a coincidence to shrug past.

## The real technique, validated directly against actual IEEE-754 bit
patterns, per Alan's own precise fix

**The problem, confirmed precisely:** `nibble_mask` only cleanly keeps
whole nibbles. A float32's own real field boundaries (bit 31 sign,
bits 30-23 exponent, bits 22-0 mantissa) don't land on nibble
boundaries. Extracting sign+exponent (the top 9 bits) is actually
easy: a plain right-shift by 23 (`shift_amt=20` + `shift_fine=3`,
exactly representable by the real coarse+fine decomposition, `#690`)
zero-fills everything above the real field for free — no mask needed
at all. **Extracting the mantissa alone is the real, remaining
problem:** a single mask can only cleanly reach 20 or 24 bits (5 or 6
nibbles), and keeping 24 leaks bit 23 — the exponent's own real LSB —
into what should be pure mantissa, for any value whose exponent
happens to be odd. Confirmed directly, not asserted: for `100000.0`
(real exponent 143, odd), a naive single mask returns `0xc35000`
against a real mantissa of `0x435000` — off by exactly the one stray
bit.

**Alan's own real fix, verified bit-for-bit against real IEEE-754
values:** mask to 24 bits (6 nibbles), shift LEFT by 1 (moving the
stray exponent bit from position 23 to position 24 — now outside the
6-nibble window), mask to 24 bits AGAIN (this time correctly dropping
the now-out-of-range stray bit), then shift RIGHT by 1 to restore the
real mantissa's own original bit positions. Two real addon-chain
passes (each one a real mask-then-shift stage, matching the chain's
own real order) — no new hardware, no new mechanism, just the existing
`nibble_mask`/`shift_fine`/`shift_lane_v2` chain applied twice.

**Verified directly** (`tests/vm/test_unicell_super_automaton_v1.py`,
3 new tests): the plain top-of-word shift for sign+exponent, the real
naive-mask leak demonstrated concretely (not just described), and the
full mask-shift-mask-shift technique confirmed to exactly reproduce
Python's own `struct`-computed mantissa for seven real test values
spanning ordinary numbers, negative numbers, very small and very
large magnitudes, and negative zero.

## Real, honest scope

This confirms the FULL boundary extraction (sign+exponent AND
mantissa) is genuinely achievable with the CURRENT project's own real
primitives — no new RTL, no new addon capability. What remains real,
separate, unbuilt work: the PACK direction (reassembling sign+
exponent+mantissa back into a standard IEEE-754 word, the mirror of
this extraction — a real, symmetric problem to the fan-out/combine
work already proven in `#692`-`#696`); the actual arithmetic tiles
(`ADD`/`MUL`/etc. operating on the split representation, matching
MIF's own real 17-tile family, scaled to whatever this project's own
real per-cell primitives can support); and the larger, still-open
question of whether this project follows MIF's own "never repack, split
from the boundary in" strategy for real, or takes a different path.
None of that is attempted here — this note closes out the specific
"can the split be done cleanly" question Alan asked, not the whole FP
story.

## Status

Design-note-only, plus 3 real, passing VM tests confirming the
extraction technique against actual IEEE-754 values. No RTL, no
composed tile, no arithmetic built. Real, ready-to-pick-up next steps
named above, not attempted here.
