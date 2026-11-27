# Memory-mapped multiply unit: design note (ledger #1580, 27 Nov 2026) - a plan for Alan to approve, nothing of the hardware is built

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

## What it should cost (to be measured before any hardware is designed)
The software multiply costs 30,900 clocks (32-bit, lw 0) and 2,010 (lw 5) on the hk card. Through memory it costs three shared-RAM accesses plus the unit's own latency. A slice reaches the shared RAM only in its own slot (one clock in S, S = 32 on hk) so each access may wait up to 31 clocks: the real gain is therefore **not** the 224 times of an imaginary one-slot instruction, probably 20 to 40 times. The next test measures this with no hardware: `batches/mmio_cost.score` runs a loop with the same three accesses (`programs/vmmio.s`) against a control with register moves (`programs/vnomem.s`); `python3 mmio_cost_calc_v1.py M100 M300 C100 C300` turns the clocks into "a multiply through memory costs about N clocks" and "N times cheaper than software". If the gain is too small, the plan changes before anything is built.

## Units, cards and numbers (to check; not yet verified)
- One unit per block; every unit needs about three DSP blocks (a 32 x 32 product, low half, from three 16 x 16 pieces; four for the full 64-bit result). On the Kintex card with 8 blocks that is about 24 of the family's 1,920 (1.3 %); on the Tang Nano 20K (48 multipliers) at most 16 units. Both are my arithmetic, to be checked against the vendor documents and the first real build.
- Per card: the board profile (`targets_v1.json`, like Onion's card profile) gets a `dsp` entry (number of multiplier blocks and their width); the generator makes `min(blocks, dsp / 3)` units, never fewer than 1 per block, and 0 if the card has none (the software path).
- Later: more than one unit per block (one per fusion core type) is a change of a generator parameter, not a redesign; the per-slice operand registers and the address window stay the same.

## What would change, in order (every step keeps the fall back)
1. **Measure** the cost of the accesses (above). No change to any proven file.
2. **Host side, no hardware**: new `jobio_v2.py` / `lib_io_v2.s` with `lib_mul32` (software path), the header word, the build manifest field `mul_units` (0 everywhere today); the reference interpreter models the unit (so both paths are tested); a `vmul32` that calls the library routine and is checked against the measured card clocks.
3. **Hardware**: a new `sc_sys_v23.v` (v22 stays): device window, per-slice operand registers, one DSP-based unit per block with its pipeline; tests in simulation first (iverilog) against the reference; then a build for the Kintex (nextpnr-xilinx / Vivado as for the other builds), then on the card.
4. **Check on the card** that the software path still works on the old builds and the hardware path gives the same answers and the clocks of step 1.

## Open questions for Alan
- The extra-address idea: should the high 32 bits of the product (`mulh`) be in the first unit? It needs a fourth DSP block per unit; the low half alone covers most uses.
- Divide stays in software; the number of divides in real jobs is not known.
- Is it acceptable that the first hardware build is the Kintex only (Tang Nano 20K later, when an S-Core pool exists for it)?
