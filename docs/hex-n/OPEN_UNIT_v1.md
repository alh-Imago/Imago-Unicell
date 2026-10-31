# Open unit v1: one build, personality chosen by data (DESIGN NOTE, 1 Nov 2026, nothing built yet)

Alan, 19:23: "if it can become more open, so when we integrate with the front end (which could be housed on the esp), you just select the data type, raw, game etc, and the extra parts to be switched on or off, the extra table, maybe the pin assignments ... an open enough system design that can handle a lot of things thrown at it."

## What can be data, what stays a build (honest split)
| Part | Can be chosen by data at run time? | How |
|---|---|---|
| Judging tables (thresholds, weights, bias) | Yes (already: the ESP32 test loads one over SPI) | LOAD / BIAS words |
| A second or third table | Yes | table-select field per scorer job (or two scorer blocks) |
| Which input feeds which sensor slot, and how it is binned | Yes | per-slot config: source, mode (level, press length, space length, range or log2 bins), range low/high |
| Morse code table, display glyph table | Yes | small RAMs loaded over SPI instead of ROMs |
| Which optional blocks are active (reaction game, Morse decoder, display, buzzer) | Yes | enable bits in a mode register; the blocks are in the build all the time and idle when off (together about 10% of the chip) |
| Pin assignments | Mostly yes | a pin matrix: every free header pin goes through a small mux, registers say which logical signal (sensor 0..7, display latch/clock/data, buzzer, LED) is on which pin |
| A new kind of game or a new state machine | No, that needs a build | add it to the block library once, then it is selectable |
| Pull-up or pull-down on a pin, 3.3 V levels, which pins exist | No (fixed in the constraints file) | default: weak pull-up on all free pins (buttons work; a sensor needing a pull-down needs an external resistor) |

## Shape of it
- Host side (ESP32, or the PC): writes a "personality" = register values + tables, over SPI. Front-end choices (raw, game, Morse) become a preset of those values.
- Tang side: pin matrix -> input conditioning (sync, debounce) -> slot binner (config per slot) -> scorer (table loadable) -> outputs (display, buzzer, LEDs, SPI result words). Optional blocks (reaction game, Morse) sit beside and use the same slots.
- Raw data from the ESP32 (an ADC reading) arrives as SPI words and is binned in a slot, the same as a pin would be.

## Prerequisite found on the way
The proven SPI bridge counts bytes in 8 bits (63-word limit, measured on the boards). A new bridge version (`spi_bridge_v2`, new file, v1 untouched) with a 16-bit byte counter and room for config registers is the first step, so config and tables can be written in long transactions.

## Stages (each one tested before the next)
1. `spi_bridge_v2` with config registers; a mode register; the reaction game and the Morse key in ONE build, selected by the mode register (shows the principle with parts we already have).
2. Slot binner with per-slot config (source, mode, range); loadable Morse and glyph tables.
3. Pin matrix.
4. A second table / second scorer job, raw-word input from the ESP32, a preset list for the front end.
Stage 1 is small; stages 2 to 4 are each a day-sized piece. Nothing here is built or measured yet.

## STAGE 1 DONE IN SIMULATION AND BUILT (1 Nov 2026, not run on a board)
One bitstream, `fpga/build/hexn_open_unit_v1/unit_top.fs` (`hexn_open_top_v1.v`). Config register 16 (SPI address 16), bits 1:0 = MODE: 0 idle (display blank, nothing running), 1 reaction game, 2 Morse key. The personality not chosen is held in reset, and a mode change restarts the chosen one.
- `spi_bridge_v2.v` (new; v1 untouched): 16-bit byte counter (long transactions work), ID `0x57320002`, config registers 16..31 (written and read back), read-only status register 10 (bits 1:0 mode, bit 2 reaction core ready, bit 3 Morse core ready). Bridge v1's registers 0..9 are unchanged.
- The two personalities are now cores (`hexn_react_core_v1.v`, `hexn_morse_core_v1.v`) with no pins or shield driver of their own; the top gives them reset, buttons and the single shield driver (`hw262_shield_v2.v`).
- A 1,024-word scratch RAM behind WR_WORDS / RD_WORDS lets long transfers be checked on the board.
- Pins: SPI 73 to 77 as `LINK_TEST_v1.md`; shield A1 72, A2 71, A3 86, display 25/26/27, buzzer 28. READY (77) is high while a personality runs.
Checked in simulation (`tests/vm/test_hexn_open_v1.py`): ID, config write and read-back, a 64-word and a 200-word transfer written and read back exactly, mode 2 decoding O, mode 1 scoring a good hit, switching modes (the other one reset), switching back to Morse and decoding L, mode 0 idle and silent. Build: 3,245 of 20,736 LUT4 (16%), 2 block RAMs, 162 MHz capable at 27, 20 pins.
To try on the boards: `openFPGALoader -b tangnano20k fpga/build/hexn_open_unit_v1/unit_top.fs`, upload `tools/esp32/hexn_open_test/hexn_open_test.ino`, then `id`, `ram`, `mode 1`, `mode 2`, `mode 0`.

## Stage 2 (1 Nov 2026): loadable tables and per-channel binning

The same unit, but the data the personalities judge by is now LOADED over SPI instead of being fixed in the build. Nothing from stage 1 was edited: new files are `hexn_open_top_v2.v`, `hexn_react_core_v2.v`, `hexn_morse_core_v2.v`, `hexn_tabs_v1.v`; the stage 1 files stay as they were.
- Four table spaces, each filled with the factory contents at power-up: 1 reaction scorer table (up to 256 words), 2 Morse scorer table (up to 256 words), 3 Morse decode table (256 x 6 bits: index {length, dots-and-dashes bits} gives a character code), 4 glyph table (64 x 8 bits: character code gives the seven-segment byte).
- Loading: write the words into the scratch RAM (WR_WORDS at address 0), then set cfg17 = {space[31:28], scratch base[27:16], count[15:0]} and write ANY new value to cfg19. The copy runs in hardware; status bit 4 (busy) is high until it is done. Then re-select the mode (the cores are held in reset while a copy runs and reload their table when they start).
- Binning, one word per channel (cfg20 reaction time, cfg21 press length, cfg22 gap length): 0 = log2 of the milliseconds (stage 1 behaviour); bit 0 set = linear, bin = (ms - low) >> shift, capped at 11, with shift in bits 7:4 and the low end in ms in bits 27:16.
- cfg23: write any new value to restore all four factory tables.
- Status register 10 now: bits 1:0 mode, 2 reaction ready, 3 Morse ready, 4 copy busy, 5 defaults loaded.
Checked in simulation (`tests/vm/test_hexn_open2_v1.py`, passes): defaults still decode L; a custom decode table (a single dot becomes Q) and glyph table (S shown differently) take effect; a Morse scorer table for a fast key with linear 32 ms bins decodes S and O at a 60 ms unit; restore brings E back; the default reaction table calls 170 ms a good hit and a loaded strict table (good only under 128 ms) does not. Build (`tools/hexn_open_build_v2.sh`): 3,790 of 20,736 LUT4 (18%), 9 block RAMs, 139 MHz capable at 27. The first build failed to place (each table had two write statements, so the tools used logic RAM, 187% of it); fixed with one write port per table in `hexn_tabs_v1.v`, simulation re-run after the fix.
Not yet run on a board. To try: `openFPGALoader -b tangnano20k fpga/build/hexn_open_unit_v2/unit_top.fs`, upload `tools/esp32/hexn_open2_test/hexn_open2_test.ino`, then `id`, `all`, `fast` then `mode 2` (tap a quick key, about 60 ms dots), `strict` then `mode 1`, `bins press log`, `restore`.

## Stage 4a (1 Nov 2026): mode 3, the raw word stream

Alan, 20:01: if the ESP32 can send its sensor data too, that is just a data stream, the same as loading data. Built that way: in MODE 3 the unit takes scorer words from the ESP32 and sends result words back; table LOAD / BIAS words and sensor SCORE words are the same kind of thing and can be mixed in one stream.
- New files (earlier ones untouched): `hexn_raw_engine_v1.v`, `hexn_open_top_v3.v`. The engine has its own scorer. The ESP32 writes the words into the scratch RAM at address 0 (up to 255 per SPI transaction, several transactions for more), sets cfg24 = {out_base[27:16], count[15:0]} and changes cfg25 (any new value) to start. Each SCORE word's result is written at out_base, out_base+1, ... in order (LOAD and BIAS words give no result). Status: bit 6 raw busy, bits 15:8 results written (saturates at 255).
- The scorer's weights are NOT cleared by a reset or mode change (only the bias is). A table loaded once stays until overwritten or power-off. Send a BIAS word at the start of a stream if you rely on one.
- The scratch RAM has ONE write port, shared: do not write over SPI while raw busy is set (those writes are lost). Reads are fine at any time. The table-copy of stage 2 and the raw engine share the second read port, so run one at a time.
- READY (77) is now high in any mode but 0.
Checked in simulation (`tests/vm/test_hexn_open3_v1.py`, 2 tests pass): (1) a random table as LOAD words plus a BIAS plus 55 SCORE words with a LOAD in the middle, in ONE stream: all results equal the bit-exact reference; after a mode change the weights stay, the bias is cleared and a second batch is exact; Morse mode still starts. (2) REAL River Exe rows: the int8 table learned on 2022 (193 words) and 210 evenly spaced 2023 rows, results all equal the reference. The test was shown to fail when the engine's result address is deliberately wrong. Build (`tools/hexn_open_build_v3.sh`): 4,363 of 20,736 LUT4 (21%), 9 block RAMs, 134 MHz capable at 27. Earlier stage tests still pass.
Real-data replay: `tools/hexn_raw_replay_v1.py` writes `tools/esp32/hexn_open3_test/replay_data.h` (the table plus 1,000 evenly spaced 2023 rows; only 18 of them are high-flow crossings, so on this subset the AUC is 0.9647 float and 0.9639 int8, against 0.973 on the whole of 2023). The sketch `hexn_open3_test.ino` command `replay` streams them in batches of 250 and counts result words that differ from the expected ones.
Not yet run on a board. To try: `openFPGALoader -b tangnano20k fpga/build/hexn_open_unit_v3/unit_top.fs`, upload `tools/esp32/hexn_open3_test/hexn_open3_test.ino` (keep `replay_data.h` next to it), then `id`, `replay`.

## Stage 3 (1 Nov 2026): the pin matrix, chosen by the ESP32

Alan, 20:21: 'let the choice be on the esp'. A chip pin cannot change its physical position at run time, so the build fixes a POOL of 16 pre-assigned pins and the ESP32 chooses, by register, which pool pin each shield signal uses. New files (earlier ones untouched): `hexn_pins_v1.v`, `hexn_open_top_v4.v`, `tools/hexn_open_build_v4.sh`.
- Pool (pool index: Tang pin): 0:72, 1:71, 2:86, 3:25, 4:26, 5:27, 6:28, 7:29, 8:30, 9:31, 10:85, 11:80, 12:42, 13:41, 14:56, 15:54. Each pad has an internal pull-up and is an input unless an output is routed to it.
- Three logical inputs (button 1, 2, 3) and four logical outputs (display latch, display clock, display data, buzzer) each pick a pool pin with a 4-bit selector. cfg26 = {button 3 [11:8], button 2 [7:4], button 1 [3:0]}; cfg27 = {buzzer [15:12], data [11:8], clock [7:4], latch [3:0]}. Each selector is stored XOR the default index (buttons 0, 1, 2; latch, clock, data, buzzer 3, 4, 5, 6), so a register value of 0 is exactly the old wiring: pins 72, 71, 86, 25, 26, 27, 28.
- Two outputs picking the same pin: the lower one in the order latch, clock, data, buzzer drives it.
- Status register 10 bits 31:16 = the live level of all 16 pool pins (so the ESP32 can scan which pin a wire or button is on).
- The buzzer on the HW-262 is ACTIVE LOW: a beep is the pin going low.
- SAFETY: routing an output onto a pin that something else drives makes two drivers fight. Only route outputs to pins you have wired to the matching shield input. Not touched: SPI 73 to 77, KEY S1, the six on-board LEDs 15 to 20, the RGB LED 79 and the HDMI EDID pins 52/53.
Checked in simulation (`tests/vm/test_hexn_open4_v1.py`, passes, shown to fail when a default is wrong): default wiring scores a good hit; the three buttons moved to pool pins 9 to 11 still work and the old pins do nothing; the status bits show a held-low pin; the buzzer moved to pool pin 12 beeps there and not on pin 6; register 0 restores the default. Build (`tools/hexn_open_build_v4.sh`): 4,552 of 20,736 LUT4 (22%), 9 block RAMs, 16 bidirectional pads, 149 MHz capable at 27. NOT yet on a board; in particular, bidirectional pads (tristate) are exercised only in simulation and by the tools' IOBUF mapping.
To try: `openFPGALoader -b tangnano20k fpga/build/hexn_open_unit_v4/unit_top.fs`, upload `tools/esp32/hexn_open4_test/hexn_open4_test.ino`, then `id`, `mode 1` (shield as before), `pins` (press a button: its pin reads 0), `btn 1 31` and wire a switch from pin 31 to GND: button 1 is now on pin 31; `out buzz 54` with the buzzer lead on 54; `default`.

## Stage 4b (1 Nov 2026): presets and a second table (two judges)

Alan, 20:38: 'start on the presets and second table, we have space on the tang so lets use some'. New files (earlier ones untouched): `hexn_tabs_v2.v` (adds table space 5), `hexn_presets_v1.v`, `hexn_raw_engine_v2.v`, `hexn_open_top_v5.v`, `tools/hexn_open_build_v5.sh`.
**Second table = a second judge in the raw stream.** Two scorers, A and B, each with its own weight table and bias. With the TWO-JUDGES bit set, every SCORE word is scored by A and then by B and two result words are written, A first. Judge control jc[2:0]: bit 0 = two judges; bits 2:1 = where LOAD and BIAS words go (0 judge A, 1 judge B, 2 both). jc starts each run at cfg28 (or the active preset's word 6) and can be changed INSIDE the stream by a control word, top nibble 14, jc in bits 2:0 (no result). One stream can therefore load table A, switch, load table B, switch back, then stream data. Top nibble 15 stays reserved.
**Presets.** The Tang holds eight presets of eight words in table space 5 (64 x 32; loaded like any table: scratch RAM, cfg17 with space 5, count 64, change cfg19). Words: 0 mode, 1 reaction binning, 2 press binning, 3 gap binning, 4 input pins (cfg26 format), 5 output pins (cfg27 format), 6 raw judge control, 7 reserved. cfg29 = preset select: 0 = none, the registers act directly (as before); n = 1..8 applies preset n-1 (the personalities are held in reset for the few clock cycles it takes). While one is active its words REPLACE the mode, binning, pin and judge registers; the tables themselves are not part of a preset. Writing 0 returns to the direct registers. Status bit 7 = a preset is active. cfg23 (restore) refills the presets with the factory ones.
Factory presets: 1 reaction game, 2 Morse key, 3 raw stream with one judge, 4 raw stream with two judges (loads go to A), 5..8 idle.
Checked in simulation (`tests/vm/test_hexn_open5_v1.py`, passes, shown to fail when the judge-B routing is wrong): preset 1 and 2 start the games with no mode register written; preset 0 returns to direct control (mode 0, idle) and the mode register still works; a custom preset loaded into space 5 moves the buttons to pool pins 9 to 11 and the buzzer to pin 12 in one write; preset 4 plus a stream of two different random tables loaded by control words, two biases and 20 rows: every A and B result equals the bit-exact reference. Stages 1 to 4a tests still pass (6 tests together). Build (`tools/hexn_open_build_v5.sh`): 5,375 of 20,736 LUT4 (26%), 10 block RAMs, 116 MHz capable at 27.
Not yet run on a board. To try: `openFPGALoader -b tangnano20k fpga/build/hexn_open_unit_v5/unit_top.fs`, upload `tools/esp32/hexn_open5_test/hexn_open5_test.ino` (with its `replay_data.h`), then `id`, `preset 1` (the game runs with no mode set), `preset 2`, `preset 0`, `twojudge -40` (the river table into both judges, B with bias -40: A and B answers for 1,000 real rows from one pass), `setp 6 1 0 0 0 0 0 0` (edit preset 6: reaction game) then `preset 6`, `factory`.

## Stage 4c (1 Nov 2026): a CLEAR control word for the judges (SIMULATED and BUILT, not on a board)
Alan remembered a 'clear function' from the layer-1 days (the `hexn_tier2` CLEAR, 29 Oct). The open unit had none: the judges keep their weights between runs. Now a control word does it, inside the stream.
- **Control word** `0xE000000C` = clear BOTH judges, `0xE000000A` = clear B only, `0xE0000008` = clear A only. Layout: top nibble 14 (CONTROL), bit 3 = CLEAR, bits 2:1 = target (0 A, 1 B, 2 or 3 both), bit 0 = two judges as before. Clear sets all 256 weights and the bias of the target to zero; the rest of the stream waits until it is done (about 130 clocks, one address per clock). A word with bit 3 clear behaves exactly as before.
- **New files** (the proven ones are untouched): `hexn_scorer_v2.v` (v1 plus `clr` / `clr_busy`), `hexn_raw_engine_v3.v`, `hexn_open_top_v6.v`, `tools/hexn_open_build_v6.sh`. The Morse core still uses scorer v1. Build: 5,380 LUT4, 10 BSRAM, 132 MHz against a 27 MHz target (about 4 minutes).
- **Test**: `tests/vm/test_hexn_open6_v1.py` (iverilog): stage 4b repeated on the v6 top, then judge B cleared (A still equals the reference, B all zero), then both cleared (all zero). Passes; open2 to open5 tests still pass.
- **Host**: `clear_judges(which, hardware=True)` sends the one word; the default still sends 256 zero LOADs, so it works on every build. The ID word is the same on v5 and v6, so the host cannot detect the build: a v5 bitstream ignores the bit and clears nothing. Diagnostic: `python3 tools/hexn_front_diag_v1.py --port ... --hw-clear` adds stage 6 (v6 only).
- **Not yet done**: load `fpga/build/hexn_open_unit_v6/unit_top.fs` and run the diagnostic with `--hw-clear`.
