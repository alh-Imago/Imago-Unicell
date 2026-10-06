# fp adder from cells (#990) and the crossing tile (#999)

## Why a crossing tile
Cells sit on a plane and data lanes are routes. Joining two operand sides forms closed "rooms" that no lane can leave except through a data cell: a planarity wall. Packing sign+exponent into one word helped, the crossing tile removed it. A route may now pass straight through another route's straight relay at right angles; that relay becomes a `cross` tile.

## The tile
No control: west<->east and north<->south pass straight through, the word keeps its direction. ONE TICK PER TILE per direction of travel, as with every other core (Alan): each used direction is its own one-word register slice, so the two axes never share state. Core `cross` (select 10; confirmed by Alan, #999 addendum): downstream_mask bits 0-3, upstream_mask 4-7. RTL today = the netlist gives each used direction a ram relay slice; FlexGrid steps through it; layout engine plans it. FPGA: one flop slice per direction, no logic; because every tile registers, long chains do not lengthen the critical path.

## The adder
unpack -> exponent difference/swap (packed T word, far-east join unit) -> two align-with-sticky -> S = A + sgn*B -> |S| -> normalise (window S+4) -> RNE -> round-overflow bump -> zero -> sign -> pack. Parametric in `FpFormat`. Scope: normals and zero. Missing: subnormal, overflow/underflow, inf, nan, formats wider than 32 bits (6-bit shift field).

## Review: what else is missing
1. Special values (subnormal, inf, nan, overflow) for the adder; then multiply and compare built the same way.
2. A placer: layouts are hand templates; only routing and balance are automatic.
3. Native crossing cores (nano/sub/flex); cost rows in router/MAN.
4. Wide formats (fp64): 64-bit build, 6-bit shift field.
5. VM tick-latency model for the layout engine (hop model is the generator's).
6. Std-target coarse/fine shift split; sequencer under 8 bits; DAG second-word consumer; automatic flag trigger.
7. Environment check in current/START.md.

## Special values (#1001)
`fp_add(..., specials=True)` adds inf/nan/overflow-to-inf on the output side: per operand c = inf-or-nan, n = nan; nan out = [n_a+n_b+inf_a*inf_b*(sa xor sb) >= 1]; spec = [c_a+c_b >= 1]; infinity sign = [sa*c_a+sb*c_b >= 1]; overflow = [rounded exponent*nonzero >= 2^E-1]; F = F_fin + spec*(Z-F_fin) with F_fin = R + ovf*(INF word - R). Layout: chains as rows, one column per cell, nets as lanes through gutter tracks, crossing tiles wherever lanes meet (`route_line`, multi-crossing). Still open: subnormal inputs/results and underflow (plan: input effective exponent e+[e==0]; denormalise right by 1-er with sticky before rounding). Test: `tests/vm/test_fp_special_v1.py`.

## Subnormals (#1006)
Inputs use the effective exponent max(e,1) (hidden bit = [e>=1] as before). The normalise is CLAMPED: total shift = min(leading zeros, EXPIN-1), five stages each testing its exponent budget first, so a result below the smallest normal stays unnormalised; such a sum is exact (no sticky, no denormalise block, no underflow for addition). Pack = ((EXPOUT-1)*nonzero << m) + rounded significand with its hidden bit, so a rounding carry lands in the exponent field by itself. Overflow = packed magnitude >= the infinity pattern. The adder is now complete for IEEE binary add in round-to-nearest-even. Tests: `test_fp_special_v1.py`, `test_fp_normalise_clamp_v1.py`.
