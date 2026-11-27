# Memory-mapped multiply unit: design note v2 (ledger #1581, 27 Nov 2026; v1 was ledger #1580 and stays) - a plan for Alan to approve, nothing of the hardware is built

## What Alan decided (27 Nov, 17:05)
- Start with **memory mapping**: the cheapest and easiest, flexible on any card, no massive rebuild.
- **One multiply unit per block** to start; later perhaps one per fusion core type; never fewer than one per block.
- Always keep a fall back (software), so a program runs on every card.
- The Onion archive was checked (see ledger #1580): it holds nothing on this idea; it does hold a per-card profile with a `dsp_blocks` field, the same idea as the per-card setting below.

## How a program would multiply (plain words)
The cores already read and write the block's shared RAM. The multiply unit would appear to a program as a few special addresses in that same data space (a "device window"), next to the shared window:
1. store the first number to the unit's address A;
2. store the second number to the unit's address B;
3. load the answer from the unit's address P (low 32 bits; a later extra address could give the high 32 bits).
Three ordinary instructions (`sw`, `sw`, `lw`), no new instruction, no change to how the cores decode instructions. The DSP block does the multiply in a few clocks; if the answer is not there yet, the core simply waits (cores already wait for the shared RAM).
Each of the 32 slices of a block needs its OWN copy of the two operands (slices take turns at the RAM, so another slice's store would otherwise overwrite them); that is two small registers per slice, tiny. The DSP itself is shared by the block and used in the slice's turn.

## The fall back, and how a program knows which to use
A card whose build has no unit must not crash a program that tries the special addresses (on today's builds an access outside the windows stops the job with a trap). So the program is told instead of asking: **the host writes the number of multiply units of the loaded build into the spare word 7 of every job's header** (it is 0 today) and one library routine `lib_mul32` (a0 = first number, a1 = second, result in a0, touches only a0, a1, t0, t1 like the other library routines) reads that word: 0 = do shift-and-add in software (the routine measured on the card, #1577), 1 or more = use the unit. Programs just call `lib_mul32`. The host gets the number from the build's manifest (a new field `mul_units`) and from the label on the card. No program has to be written twice, and an old build keeps working with zero units.

## What it costs: MEASURED on the hk card (ledger #1581, Alan's run of batches/mmio_cost.score, 17:11)
A loop with the three accesses to the shared window (two stores, one load) against the same loop with register moves, N = 100 and 300, two repeats each, all runs correct:

| | lw 0 (no fusion) | lw 5 (32 lanes fused) |
|---|---|---|
| clocks per pass, memory loop / control | 1,152 / 928 | 128.0 / 58.0 |
| one ordinary instruction (control loop) | 132.6 clocks | 8.3 clocks |
| one shared-RAM access | 207.2 clocks | 31.6 clocks |
| a multiply through memory, unit latency not included (3 accesses) | about 622 clocks | about 95 clocks |
| against the software 32-bit multiply (30,900 / 2,010) | 49.7 times cheaper | 21.2 times cheaper |
| against the software 8-bit multiply (7,940 / 540) | 12.8 times cheaper | 5.7 times cheaper |

So the prediction (20 to 40 times) held for the 32-bit multiply (50 and 21 times) and is lower for the 8-bit one (13 and 6 times). A shared-RAM access costs about one whole slot round at lw 5 (31.6 clocks, a slot comes once in 32) and about 1.6 instructions at lw 0. The unit's own latency (a few clocks) is small beside that. **The memory-mapped unit is clearly worth it for 32-bit multiplies; for 8-bit ones at lw 5 it gains only about 6 times (still fine, but the software path stays reasonable).**

## A refinement that should roughly double the gain (an estimate, not measured, for Alan to approve)
Only the LOAD of the product has to wait for the DSP. The two STORES of the operands could be answered inside the slice from its own operand registers, without waiting for its turn at the shared RAM: a store then costs one ordinary instruction (132.6 / 8.3 clocks). Estimate: two ordinary instructions plus one shared access = 2 x 132.6 + 207 = about 472 clocks at lw 0 (65 times cheaper than 30,900) and 2 x 8.3 + 31.6 = about 48 clocks at lw 5 (42 times cheaper than 2,010; 11 times for 8-bit). This costs a little more RTL (the device window decoded inside the slice, not in the RAM path). I suggest we build it this way, measure it with a simulation first, and keep the plain "all three through the RAM" version as the simpler fall back if the slice logic proves awkward.

## Units, cards and numbers (to check; not yet verified)
- One unit per block; every unit needs about three DSP blocks (a 32 x 32 product, low half, from three 16 x 16 pieces; four for the full 64-bit result). On the Kintex card with 8 blocks that is about 24 of the family's 1,920 (1.3 %); on the Tang Nano 20K (48 multipliers) at most 16 units. Both are my arithmetic, to be checked against the vendor documents and the first real build.
- Per card: the board profile (`targets_v1.json`, like Onion's card profile) gets a `dsp` entry (number of multiplier blocks and their width); the generator makes `min(blocks, dsp / 3)` units, never fewer than 1 per block, and 0 if the card has none (the software path).
- Later: more than one unit per block (one per fusion core type) is a change of a generator parameter, not a redesign; the per-slice operand registers and the address window stay the same.

## What would change, in order (every step keeps the fall back)
1. **Measure** the cost of the accesses (done, above). No change to any proven file.
2. **Host side, no hardware**: new `jobio_v2.py` / `lib_io_v2.s` with `lib_mul32` (software path), the header word, the build manifest field `mul_units` (0 everywhere today); the reference interpreter models the unit (so both paths are tested); a `vmul32` that calls the library routine and is checked against the measured card clocks.
3. **Hardware**: a new `sc_sys_v23.v` (v22 stays): device window, per-slice operand registers, one DSP-based unit per block with its pipeline; tests in simulation first (iverilog) against the reference; then a build for the Kintex (nextpnr-xilinx / Vivado as for the other builds), then on the card.
4. **Check on the card** that the software path still works on the old builds and the hardware path gives the same answers and the clocks of step 1.

## Open questions for Alan
- The extra-address idea: should the high 32 bits of the product (`mulh`) be in the first unit? It needs a fourth DSP block per unit; the low half alone covers most uses.
- Divide stays in software; the number of divides in real jobs is not known.
- Is it acceptable that the first hardware build is the Kintex only (Tang Nano 20K later, when an S-Core pool exists for it)?
