# Hex-N guarded record v1 (draft, 1 Nov 2026, Alan 17:50: "start with the extended space save and load")

Status: DRAFT. Reference code and test exist (tools/hexn_record_v1.py, tests/vm/test_hexn_record_v1.py, host side only). Nothing of this is in the ESP32 sketch or on the board yet. Space 7 below is a PROPOSAL; no hardware for it exists.

## Why
Table files /tab<N>.bin on the ESP32 are raw words: nothing says what they are, how many, or whether a bit flipped. Only the batch judges (260-word record) have a guard, in hardware. The neural judge (space 6) carries no guard in the card by design. One common record, checked by the ESP32 BEFORE anything is written to the card, covers every space, and the Hex-N UCC patterns later.

## Record (32-bit words, same checksum style as the judge record)
| Word | Content |
|---|---|
| 0 | {16'h4852 'HR', 8'd version = 1, 8'd kind} |
| 1 | geometry {16'd count (entries), 8'd entry width in bits, 8'd 0} |
| 2 | structure id (32 bits): which block set / wiring the payload belongs to; 0 = not tied to a structure (all fixed tables) |
| 3 .. 3+count-1 | payload, one entry per word, upper bits beyond the entry width must be 0 |
| last | sum of all earlier words, mod 2^32 |

Kinds: 1 reaction table (256 x 32), 2 Morse table (256 x 32), 3 decode table (256 x 6), 4 glyph table (64 x 8), 5 presets (64 x 32), 6 neural judge values (8 x 16), 7 PATTERN BANK (proposal: 64 x 32).

## Refusal codes (checked in this order; the first fault found wins)
1 bad magic, version or unknown kind. 2 geometry wrong for the kind (count above the capacity or a different entry width). 3 bad checksum. 4 truncated, too long, or a payload word with bits set above the entry width. 5 structure id differs from the one the card reports (the pattern was made for another design).
A refused record is never written to the card.

## Pattern bank (space 7, proposal)
The Hex-N UCC part processes data, it does not store it, so what must be saved is its configuration: the 32-bit config word of each block (mode, topology, step; a carrier region would need 160 bits = 5 words). The cells have no config read-back port, so the card keeps a COPY: a small pattern RAM written by the load path, and applying a slot sends its word through the config gate (config_gate_v3). Save is then a plain RAM read, in the same path as the other spaces. Open points: slot layout for 160-bit carrier words; where the structure id comes from (a constant per bitstream); how a slot is applied (command word); nothing here is built.
