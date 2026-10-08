# Hex-N walkthrough, v0.2 (9 Oct 2026)

Status: review of the v0.1 notes against what the UniCell side has since built (the small unit: SD card + SPI bridge + ESP32 web control, running on the real Tang Nano 20K), plus a first behavioural RTL (`rtl/hexn_cell_v0.v`) and an independent Python model (`tests/test_hexn_cell_v0.py`, passes on 300 random configurations). **Nothing here is a decision**: it lists what the notes contradict or leave open, and what changes because the unit exists.

## The cell in one paragraph
A cell has 6 faces; each face has 4 channels (6x8 version) or 8 (6x16); a channel is one `in` line plus one `out` line to a matching channel on the neighbouring cell. Once per window (one shared tick for the whole mesh) the cell samples its inputs, counts how many active channels on each face are high, and the face fires if that count reaches the face's threshold. Each channel's output is then one of AND / OR / XOR / NOT of (the face's fire decision, that channel's own input), registered so it appears only at the next window. Everything is trained offline (discrete: active bits, gates, thresholds), frozen, and loaded as a pattern.

## What the notes disagree about or leave open
1. **Spatial count or temporal accumulation?** README: each face "accumulates its active input lines over a timer-gated window". Internals v0.1: the count is a one-shot sample at the window start, range 0-4, so thresholds are 3 bits. These are different machines. The 16-bit shared bias only makes sense against a wide, accumulated count; against 0-4 it is meaningless (a 16-bit value subtracted from at most 4). **Decision needed first.** The prototype implements the spatial sample and ignores the bias.
2. **What does NOT negate?** NOT(fire) is an inhibitory output (high unless the face fires); NOT(in) is an inverted echo. Both are cheap; they behave very differently. The prototype takes NOT(fire) by default (parameter `NOT_OF_IN`).
3. **Config bits.** v0.1 says per-line config falls from 4 to 3 bits (gate 2 + active 1). But gate and active belong to a *channel* (an in/out pair), not to a line. Per channel: 24 channels x 3 = 72 bits plus 6 x 3 thresholds = 90 bits (+16 bias) for 6x8; 6x16: 48 x 3 + 6 x 4 = 168 (+16). The old 4x96-bit total (384) no longer applies.
4. **Hop latency.** "Computed from the sample, presented at the next boundary" read strictly with flip-flops is two windows per hop; one register stage is one. The prototype uses one. Decide, because training depends on it.
5. **Echo behaviour.** Because a channel's output includes its own input, a signal can bounce between neighbours. In a rough two-cell toy run, AND/OR pulses simply died out, while an all-NOT(fire) pair never settled (period-2 oscillation). The toy wiring was crude; the proper check is a 7-cell hexagonal "flower" in the real mesh wiring, with a defined quiet state and a global activity limit (the bias knob).
6. **No task yet.** Evolutionary search needs a fitness function. Suggest the first one is tiny and checkable: parity or "all four inputs equal", then a delay line, then a pattern detector.

## What the unit changes
- **The pin budget stops being the limit.** v0.1 chose 6x8 because 96 lines cannot all go to pins (66 chip I/O, and the Tang's headers expose only about 34 usable signals). With the unit, the cell's input lines can come from an SPI-loaded register and its outputs go to the capture RAM, so no line needs a pin. A full 6x16 cell, or an array, is possible; pins are needed only for the SPI link (5), SD card (4), clock and status.
- **The BL616 hop is not needed.** The draft ESP32-to-BL616 protocol maps onto the existing ESP32-to-FPGA SPI bridge: `PATTERN_PUSH` = words written into a config RAM over SPI (WR_WORDS); `RESULT_DATA` = RD_WORDS from capture; `STATUS_*` = the STATUS register; the attention line = the READY pin (already wired, IO34); `REF_DATA` = the SD load/save registers. `BITSTREAM_SELECT` is the only message that stays hard: it is the JTAG-loader research (spare Tang first). The BL616's own SPI port is wired to FPGA pins 75/76/13/86 on the board, so a BL616 route remains possible, but nothing needs it now.
- **Test rig and tools exist:** playout/capture RAMs, SD card, web page, file card on the ESP32 (for pattern libraries), S1 reset.

## Measured cost (yosys synth_gowin, config held outside; before place-and-route)
| Cell | LUT4 | ALU (carry) | Flip-flops (state) | Config flip-flops if on-cell |
|---|---|---|---|---|
| 6 faces x 4 channels (6x8) | 66 | 48 | 30 | about 106 |
| 6 faces x 8 channels (6x16) | 240 | 48 | 54 | about 184 |
Rough capacity on a Nano 20K after the unit (2,150 LUT4 / 1,870 FF): flip-flops limit it to roughly 100 cells of 6x8 or 55 of 6x16, before routing; the W2 engine showed routing can take most of the chip, so treat these as upper bounds. **Not placed-and-routed.**


## Alan's recollection of the original intent (9 Oct 2026, from memory, "it's been a while")
A simple neural cell: it has an **accumulated weight**; connections are made in **pairs whose direction can be set either way**; each can have **one of four logic gates** applied; and the original concept was **single wires, where the more of them are active the greater the chance of flowing down that path**.
What this does to the open points (my reading, to be confirmed):
- **Accumulation is temporal** (point 1 goes the README's way): a weight that builds up, not a one-shot 0-4 count. That also gives the 16-bit shared value a job (it is wide enough to be compared against a running total) and makes the thresholds wider than 3 bits.
- **Direction is a configurable property of each pair**, not implicit. v0.1's removal of the direction bit (config 4 -> 3 bits) contradicts this; it should stay: gate 2 + active 1 + direction 1 = 4 bits per pair.
- **"Greater chance of flowing"** is new and is not in any note. Two readings: (a) *graded, deterministic*: more active wires fill the accumulator sooner, so that path reaches its threshold earlier and carries more; (b) *literally probabilistic*: the accumulated value is compared with a random number, so the chance of a path firing rises with its weight. (b) needs a pseudo-random source in each cell (a small shift register, which is fine here: this is not the security use). It makes runs non-repeatable unless the random source is seeded and the VM copies it bit for bit, which matters for training.

## Decided by Alan, 9 Oct 2026
1. **Temporal accumulation** (a weight that builds over the window), not a one-off 0-4 count.
2. **Graded and deterministic**: more active wires fill the accumulator sooner and carry more; no random source.
3. **Direction is configurable per pair**, and a wire can carry flow **both ways, never at the same time**: that reverse flow is the **feedback** that makes the cell behave like a simple neural net (forward pass, then feedback pass) rather than a feed-forward logic mesh.

## What those decisions imply (my reading, to confirm)
- **Time-shared direction.** Each pair is logically ONE wire whose direction is set by a phase: forward in one window, feedback in the next (or fixed forward / fixed back by config; three modes: forward only, back only, alternating). On the die this is two unidirectional wires and a mux (the fabric has no internal tri-state); only at the package pins would a real bidirectional pin be needed.
- **That is the loop fix, done properly.** v0.1 separated in and out per channel and clocked the whole cell to avoid a combinational loop. With one direction live at a time there is no loop at all, and the same window tick also provides the phase.
- **The gate formula must change.** v0.1 had `out = GATE(fire, own in)`, which needs the channel's own input while it is the output. Under time-sharing that input is not live in the same phase. Suggest `out = GATE(face fire, the face's other-phase value)` or simply `GATE(fire, 1)`: needs a decision (below).
- **Accumulator.** Proposal: each clock, add the number of active input pairs currently flowing into the face; at the window end compare with the face threshold (wide enough for window length x pairs); the 16-bit shared value is the bias/damping applied to the total before the compare; clear at the window end. "Greater chance of flowing" then means: more active wires -> the total clears the threshold by a bigger margin / sooner, and the margin can scale the output (graded) if wanted.
- **Prototype status.** `rtl/hexn_cell_v0.v` still implements the v0.1 spatial reading; it is superseded by the above and kept only as the first measurement.

## What the four "gates" mean in the neural reading (Alan, 9 Oct 2026; my table, to confirm)
"NOT" is the wrong word here. Alan's description: NOT is really a **negative value**; the positive case is its opposite; and the others are about **choosing paths**: a **choice made between equal paths**, and an **XOR that depends on the flow in** ("if it is this we go that way, if it is that we go the other way").
| Code | Better name | Meaning (proposed) |
|---|---|---|
| 3 | **NEGATIVE** (inhibit) | the pair's active flow is subtracted from the face's accumulated weight |
| (positive) | **POSITIVE** (excite) | the pair's active flow is added; this is the plain case. Which of AND/OR is this is not stated |
| OR | **CHOOSE** | when paths carry equal weight, one is picked (arbitrate, like the flex family's merge core) |
| XOR | **STEER** | the incoming flow decides which way it goes (a branch/switch, like the flex branch core): this value one way, that value the other |
| AND | (unclear) | probably "both must be present" (coincidence/join); not described yet |
So the four codes are really {positive, negative, choose, steer}, with AND/OR/XOR/NOT only their logic-gate shadows. UniCell's flex family already has the matching pieces (merge arbitrate/join, branch select), which the Hex-N RTL could reuse.

## Still open
1. ~~What does NOT negate~~ answered: it is a negative weight (above). Still to confirm: which of the four codes is plain positive, and what AND does.
2. How is the output formed from fire plus the carried value now that in and out share a wire?
3. Is the output on/off, or graded (the margin above threshold)?
4. Alternating phase: one global phase for the mesh, or per-pair?
5. First bring-up shape: one 6x8 cell through the unit, or the 7-cell flower?

## Proposed next steps once decided
Pattern RAM + SPI loader for the cell; wrap one cell as a unit "design" (inputs register in, outputs to capture); Python/VM model kept bit-identical to the RTL; the 7-cell flower; first fitness task and a simple evolutionary search on the PC; patterns saved to the ESP32 file card.
