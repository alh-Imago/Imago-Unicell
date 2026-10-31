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
