# Tang batch scorer v1 (1 Nov 2026)

Status: simulated and built, NOT run on a board. Everything below marked "checked" was checked in simulation or by the open-flow build; nothing is measured on hardware yet.

## What it is
`fpga/verilog/hexn_scorer_v1.v` is one small block that sits where the CORDIC sits in the existing SD+SPI small unit. The SPI bridge, playout RAM and capture RAM are the proven ones, unchanged. It holds a two-class weight table (whole numbers, 8-bit) and, for each word of layer-1 bins, returns the two class scores and the decision.

Word formats (32-bit; the top nibble is both sensor 7's bin and the word type, because layer 1 has only 12 bins):
- top nibble 0..11, SCORE: sensor i's bin in bits 4i+3:4i, eight sensors. One result per word.
- top nibble 12, LOAD: bit 24 class, bits 22:16 address {sensor(3), bin(4)}, bits 7:0 signed weight. No result.
- top nibble 13, BIAS: bits 15:0 signed, added to class 1 before the decision. No result.
- result: bit 31 decision, bits 27:16 class-1 score, bits 11:0 class-0 score (signed 12-bit).
Reference and encoders: `tools/hexn_scorer_ref_v1.py`.

## Checked
- Bit-exact against the Python reference on three random tables, 400 scored words each, with random gaps on both sides of the handshake (`tests/hexn_scorer/`, run with iverilog).
- Through the full unit with a simulated ESP32 on SPI: table, bias, 100 words in, results out (`tests/vm/test_hexn_scorer_unit_v1.py`).
- The exact words the ESP32 test sketch puts on the wire (table, bias, 1,280 samples) give the results the sketch expects.
- Open-flow build (yosys, nextpnr, gowin_pack): `fpga/build/hexn_scorer_unit_v1/unit_top.fs`, 2,080 of 20,736 LUT4 (10%), 4 of 46 block RAMs, 32 small RAMs for the table, 154 MHz capable at the 27 MHz used.
- Accuracy cost of whole-number weights, River Exe (`tools/hexn_scorer_quant_v1.py`): float table AUC 0.9730; whole numbers at 0.5-nat steps 0.9727, at 0.25 / 0.125 / 0.083-nat steps 0.9730. At 0.0625-nat steps 10% of entries clip at -127 (the table's floor entries) with no change to AUC; 0.083-nat steps (scale 12) need no clipping.

## To run on the boards
1. Load: `openFPGALoader -b tangnano20k fpga/build/hexn_scorer_unit_v1/unit_top.fs` (same pins and wiring as `LINK_TEST_v1.md`).
2. Upload `tools/esp32/hexn_scorer_test/hexn_scorer_test.ino`. Commands: `id`, `table`, `bench`, `all`; `hz 1500000` changes the SPI clock.
3. `bench` sends 20 batches of 64 words, checks every result against the ESP32 judging the same word, and prints the time per batch for the Tang route and for the ESP32 alone.

## Expectation (arithmetic from the earlier measured link rates, not a measurement)
The scorer itself needs about 12 clock cycles a word (about 0.45 us at 27 MHz). The link needs a word in and a word out: at the measured 44,100 words/s (1.5 MHz) that is about 45 us per scored word, so the link, not the scorer, sets the speed (about 22,000 scored words/s at most). A simple judge like this one will be faster on the ESP32 itself (the earlier search figure was about 7 us a node). The scorer pays when the work per word is much bigger than this (more classes, sensors, tables), when the ESP32 is busy, or when sensors feed it directly (the unit's direct mode, no SPI in the path).
