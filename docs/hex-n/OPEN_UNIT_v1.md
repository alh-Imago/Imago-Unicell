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
