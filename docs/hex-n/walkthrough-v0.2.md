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

## Decisions I need from you
1. Spatial count (0..4, v0.1) or temporal accumulation over the window (README, gives the bias a job)?
2. NOT of the face's fire decision, or of the channel's own input?
3. One window or two per hop?
4. First bring-up shape: one 6x8 cell through the unit, or the 7-cell flower?

## Proposed next steps once decided
Pattern RAM + SPI loader for the cell; wrap one cell as a unit "design" (inputs register in, outputs to capture); Python/VM model kept bit-identical to the RTL; the 7-cell flower; first fitness task and a simple evolutionary search on the PC; patterns saved to the ESP32 file card.
