# Morse-key demo v1 (1 Nov 2026): press length and space length on the Tang alone

Status: simulated and built, NOT run on a board. Alan's idea (19:12): "go for press length and space length ... (- - - ,,, - - -)". Reading taken: a Morse key. His example, dashes then dots then dashes, is O S O when the groups are separated by letter gaps (not SOS, which is dots, dashes, dots); the test checks exactly that.

## How it works
- Button A1 is the key; the buzzer sounds while it is down (a sidetone). Button A2 clears the display.
- A 1 ms counter (an ordinary counter on the 27 MHz clock) measures how long the key is down (press length) and how long it is up (space length). Each becomes a layer-1 bin, floor(log2 ms), 0 to 11.
- One scorer table does three jobs, each in its own sensor slot (the other slots carry the neutral bin 15, weight 0):
  - slot 0, press: class 1 = dash (256 ms or more), class 0 = dot
  - slot 1, space: class 1 = letter gap or longer (256 ms or more)
  - slot 2, space: class 1 = word gap (1024 ms or more)
  The scorer is asked about the press when the key comes up, and about the space every millisecond the key stays up.
- The decoder collects up to 5 dots/dashes, turns them into a character when the scorer calls a letter gap, and adds a space at a word gap. Six symbols or an unknown pattern shows a dash (not a Morse character).
- Display: the last four characters, newest on the right. A decimal point on the right-hand digit means symbols of the next letter are pending. Digits show with their own point. Seven-segment letters are approximate (M, W, X, K, V look like other letters; use the point and the context).
- LEDs: 0 heartbeat, 1 key down, 2 last symbol was a dash, 3 letter gap seen, 4 word gap seen, 5 table loaded.

## Timing with the starting table (the bins are powers of two, so the limits are 256 and 1024 ms)
Dot under 256 ms, dash 256 ms or more; letter gap 256 ms or more, word gap 1024 ms or more. So a unit of about 150 to 200 ms works: dot 150-200, dash about 500, symbol gap 150-200, letter gap about 500, word gap about 1200 or more. A faster key would need a different table (the unit-time-adaptive version is the next step; the table is `tools/hexn_morse_gen_v1.py`, function table()).

## Wiring (Tang pin numbers from Alan's pinout picture)
| Shield | Tang pin | Header |
|---|---|---|
| A1 button (the key) | 72 | right, near the bottom |
| A2 button (clear) | 71 | right, near the bottom |
| display latch (shield pin 4) | 25 | left |
| display clock (shield pin 7) | 26 | left |
| display data (shield pin 8) | 27 | left |
| buzzer (shield pin 3) | 28 | left |
| shield 5V pin | Tang 3V3 | right header, 16th |
| shield GND | Tang GND | right header, 15th |
A3 is not used (the earlier reaction game used it on pin 86).

## Checked
- Simulation with a fast clock (`tests/hexn_morse/`, `tests/vm/test_hexn_morse_v1.py`), unit 160 ms: S, O, space after a 1.3 s gap, 1 (.----), C (-.-.), a 6-symbol pattern giving "not a character", E then a word gap, clear, dashes-dots-dashes giving O S O, and the buzzer low while the key is down.
- Build: `fpga/build/hexn_morse_demo_v1/unit_top.fs`, 1,113 of 20,736 LUT4 (5%), 175 MHz capable at 27, 14 pins.
- New file `hw262_shield_v2.v` (a clone of v1 that takes four raw segment bytes); v1 is unchanged.

## To run
`openFPGALoader -b tangnano20k fpga/build/hexn_morse_demo_v1/unit_top.fs`, wire as above, wait for LED 5, then key on A1.
