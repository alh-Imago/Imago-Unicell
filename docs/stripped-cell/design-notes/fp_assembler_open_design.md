# The open fp assembler (ledger #989)

Alan: "make the fp assembler quite open, the same design, in principle at least, could be used for larger or smaller fp units."

## Shape
* `tools/flex_layout_v1.py` -- the LAYOUT ENGINE: cells on grid squares, links between neighbours, `route()` (relay chains over free squares, shortest or deliberately longer),
  `hops()` (the generator's hop model), `balance()` (removes the timing ties the generator refuses by lengthening a routed operand path by two relays), `records()` -> ICM.
* `tools/fp_assembler_v1.py` -- `FpFormat(name, sig_bits, exp_bits, word)` and PARAMETRIC BLOCKS. Everything format-dependent is computed from the format:
  | block | what | parameters it derives |
  |---|---|---|
  | `normalise_chain` | left-normalise + exponent adjust | K = bit_length(S-1) stages, shifts 2^(K-1)..1, thresholds 2^(S-s), exponent constant 2^32 - (2^K - 1) |
  | `align_sticky` | right shift by exponent difference d, sticky | Ka = bit_length(S+2) d-bits + a clamp stage, extra shift Ka+1, aligned lsb at bit word-S-(Ka+1) |
  | `round_rne` | round to nearest even | `low` extra bits below the lsb: lsb/guard/sticky shift counts, optional external sticky |
* Blocks are connected with `route()` between an exit and an entry: align -> round passes the guard bits and the sticky flag (test: OUT = round-half-even(sig / 2^d)).
* Proven in `tests/vm/test_fp_blocks_v1.py` for fp32 (S=24) AND fp16 (S=11): generated RTL (plain + random stalls) == FlexGrid == Python.

## What is general, what is not yet
* General: S, exponent width (only enters through the exponent constants), shift counts, stage counts, thresholds. A custom format (bfloat16 `FP.BF16`, S=8) is one line.
* Not yet: a WORD wider than 32 (the generator builds 32-bit cells; fp64 needs a 64-bit build and the 5-bit shift field widening to 6 bits); fp16/bf16 fit.
* Not yet built for the whole adder: unpack (sign/exponent/mantissa split), the swap so the larger operand is first (comparator + selects), effective add/sub choice, add/sub of the two significands (with the
  second port's carry), rounding-overflow exponent bump, pack, zero/subnormal/inf/nan paths. All of them reuse the same pieces (comparators, relays with shift add-ons, adders, multipliers, second ports).

## Findings of this step
1. The FlexGrid VM ORed two operands that arrive in the SAME tick (std behaviour); the real handshake cell waits for both. Flex VM now takes one (lower face) and acknowledges only that one; for a subtract it
   refuses (no operand order). Std VM untouched. This showed up only once two long lanes met (align -> round).
2. The generator's hop model says two operands differ while the VM can still tick them together (adders/comparators/multipliers do not all cost one tick); the VM guard above makes this safe for add and multiply.
3. On a grid every path between two squares has the same parity, so the only way to separate two operand arrivals is a deliberate detour (+2 relays): `balance()` does it.
