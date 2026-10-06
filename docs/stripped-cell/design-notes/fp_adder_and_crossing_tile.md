# fp adder from cells (#990) and the crossing tile (#999)

## Why a crossing tile
Cells sit on a plane and data lanes are routes. Joining two operand sides forms closed "rooms" that no lane can leave except through a data cell: a planarity wall. Packing sign+exponent into one word helped, the crossing tile removed it. A route may now pass straight through another route's straight relay at right angles; that relay becomes a `cross` tile.

## The tile
Pure wiring: west<->east and north<->south pass straight through, the word keeps its direction, zero latency, no state, no ack. Core `cross` (select 10; confirmed by Alan, #999 addendum): downstream_mask bits 0-3, upstream_mask 4-7. RTL today = netlist splice (direct wire); FlexGrid steps through it; layout engine plans it. FPGA: no LUT/flop, routing only; long chains of crossings are a timing matter (hence the registered variant on the open list).

## The adder
unpack -> exponent difference/swap (packed T word, far-east join unit) -> two align-with-sticky -> S = A + sgn*B -> |S| -> normalise (window S+4) -> RNE -> round-overflow bump -> zero -> sign -> pack. Parametric in `FpFormat`. Scope: normals and zero. Missing: subnormal, overflow/underflow, inf, nan, formats wider than 32 bits (6-bit shift field).

## Review: what else is missing
1. Special values (subnormal, inf, nan, overflow) for the adder; then multiply and compare built the same way.
2. A placer: layouts are hand templates; only routing and balance are automatic.
3. Native crossing cores (nano/sub/flex) and the registered variant; cost rows in router/MAN.
4. Wide formats (fp64): 64-bit build, 6-bit shift field.
5. VM tick-latency model for the layout engine (hop model is the generator's).
6. Std-target coarse/fine shift split; sequencer under 8 bits; DAG second-word consumer; automatic flag trigger.
7. Environment check in current/START.md.
