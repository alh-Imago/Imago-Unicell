# Hex-N loadable item: byte layout v1 (31 Oct 2026)

New file. Implements section 3 of `PROFILE_v1.md`. Reference code and tests: `tools/hexn_item_v1.py`, `tests/test_hexn_item_v1.py` (3 pass). **Status: MODEL (Python); no RTL, no firmware, nothing on a card.**

## Header (40 bytes, little-endian)

| Offset | Size | Field | Notes |
|---|---|---|---|
| 0 | 4 | magic | `HXI1` |
| 4 | 1 | type | 1 goals, 2 weights, 3 settings, 4 detector, 5 history, 6 memory, 7 target |
| 5 | 1 | usage | 0 any, 1 game, 2 sensor |
| 6 | 2 | item version | clone and increment: a changed item is a new version |
| 8 | 4 | payload length | bytes |
| 12 | 1 | needs: inputs | the item needs at least this many neural inputs (0 = no requirement) |
| 13 | 1 | needs: WB | fractional bits of the weights (weights items must equal the build) |
| 14 | 1 | needs: look-back max | build maximum the item assumes |
| 15 | 1 | flags | reserved, 0 |
| 16 | 4 | parent id | crc32 of the parent item's whole bytes; 0 = none |
| 20 | 4 | created | unix seconds; 0 = unknown |
| 24 | 8 | trained on | ASCII tag, space padded, e.g. `hand`, `weakopp`, `shadowA` |
| 32 | 4 | payload crc32 | |
| 36 | 4 | header crc32 | over bytes 0 to 35 |

## Payloads fixed now

- **goals:** K u8, bins u8, bin width u16 (tenths of a unit), then K x [name 8 bytes ASCII, mean u16 tenths, spread u16 tenths].
- **weights:** outputs u8, inputs u8, WB u8, pad u8, then per output: inputs x i16, then one i32 bias.
- **settings:** count u8, then count x [key u8, value i32].
- **target:** one byte: 0 esp, 1 host, 2 onboard.
- **detector, history, memory:** opaque for now; the layout is not fixed.

## Checks before anything is written (`validate`)

Refused with the reason: bad magic; header or payload checksum; payload length not equal to the header's; item needs more inputs or look-back than the build has; weights with a different WB than the build; item for another usage than the user chose. A flipped bit in the header or payload is caught (tested at four positions).

## Goals to weights, in whole numbers

`goals_to_weights(payload, WB)`: per animal and bin, score = max(-z^2/2, -8) - ln(max(spread, 3)), with z^2 computed as an integer ratio in Q8 and ln from the bit length with a straight line between powers of two; weights stored Q8 (WB 8). Largest weight 3,264, so it fits 16 bits. **Checked on the shadow test's prior (2,000 passings per world): integer and float give the same accuracy: A .922, B .579, C .724.** The integer table carries a common offset of about ln(10) because it works in tenths; it does not change which animal scores highest. Not done: the learning step for several outputs in whole numbers; the hardware that would run this at load time (it is a few hundred additions and one division per table, so it fits the strategist's side, ESP or host, and need not be in the fabric).
