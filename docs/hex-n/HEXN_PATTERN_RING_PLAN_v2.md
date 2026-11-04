# Hex pattern ring: results and what is left (4 Nov 2026, v2)

v1 (`HEXN_PATTERN_RING_PLAN_v1.md`) is the plan as written at 17:00 and is kept unchanged. This file records what was then done on Alan's Tang Nano 20K, from the ledger rows of 4 Nov 20:03-21:30 in `HEXN_DESIGN.md`. Every statement below is something Alan pasted from his board; "not shown" lists what was not.

## 1. What was shown
| Step | Result (observed) |
|---|---|
| P1/P2 hex card in SRAM | 7x7 (ID 90894555): `id` right; `selftest`: prio4 and addsub PASS, words equal the VM. Port is `/dev/ttyUSB1`. |
| P3 second and third pattern | 6x6 (ID 8F532C4A) and 5x5 (ID 3A7FD506), each in SRAM: `id` right, addsub PASS (prio4 is not plannable on 6x6 or 5x5, so not tested). |
| P4 ring in flash | Two-pattern ring then three-pattern ring (`hexn_flashimg_v1.py`, flag 0xcc, 1 MiB slots) written at offset 0 and compared with `cmp`: RING OK both times. |
| P5 hops | Pin 9 to GND tap: 7x7 -> 6x6 -> 7x7 seen by `id` and the LEDs; selftest PASS on both after the hop. **`openFPGALoader -b tangnano20k -r` also hops the ring** (follows the jump, both directions). `hexn_ring_cycle_v2.py`: ring of two 3 runs x 7 rounds, ring of three 7 rounds, all PASS. |
| Hop time | PC-driven: loader command 0.02-0.03 s, first UART answer 0.20-0.21 s after it ended (about 0.23 s in all), same for two and three slots. Probe step 0.05 s. The earlier camera figure for the hand tap (at most about 0.3 s) is coarse. |
| LEDs | `hexn_frame_v3` shows PATTERN_ID[2:0] on LEDs 5..3 (active low), so a person sees which pattern runs: 7x7 = LEDs 3+5, 6x6 = LED 4, 5x5 = LEDs 4+5 (7x7 and 6x6 confirmed by Alan; 5x5 from simulation only). |
| Restore | Full 8 MiB backup written back; dump SHA-256 equals the backup's `2416b7b4…a655`. |

## 2. Not shown
- Any run longer than 7 rounds, any temperature or long-duration test; rings of four or more; slot sizes other than 1 MiB.
- The 6x6 and 5x5 `prio4`; the prio4 failure at 7x7 offsets 0 and 1 is still undiagnosed.
- Which bit of header byte 0x25 (0xcc vs 0xae) enables the jump; side effects of 0xcc.
- The 20:20-20:24 attempt with the first (v2, no LED) ring showed no hop; its headers were correct; the cause is unknown and that ring was overwritten.
- A hop requested from inside the design (route b of v1 section 8) and the ESP32 route: not built, not needed for a PC-driven hop.
- The judge/open unit and the array are still not linked on chip; weights and state do not survive a hop (the program is reloaded over the UART each time).

## 3. Tools (all in the repo)
`tools/hexn_hexcard_host_v1.py` (id, watch, selftest), `tools/hexn_hexcard_vector_v1.py` (test vectors from the VM), `tools/hexn_ring_cycle_v2.py` (hop, wait, id, selftest, repeat; v1 kept), `tools/hexn_flashimg_v1.py` (ring image), `tools/hexn_fs2bin_v2.py`, `tools/hexn_assemble_hex_v2.py` (frame v3 choice; v1 kept), `sub/verilog/hexn_frame_v3.v`. Tests: `test_hexn_hexcard_host_v1.py`, `test_hexn_ring_cycle_v1.py`, `test_hexn_ring_cycle_v2.py`, `test_hexn_frame_v3_led_v1.py`.

## 4. How to repeat it (short)
1. Back up the flash and check its SHA-256 (kit steps 1-2). 2. Build each pattern: `hexn_assemble_hex_v2.py build REF.json --out DIR --frame v3` then `sh DIR/build.sh`. 3. Make a vector: `hexn_hexcard_vector_v1.py REF.json DIR VECTOR.json`. 4. Check each in SRAM: `openFPGALoader -b tangnano20k DIR/hexn.fs`, then `hexn_hexcard_host_v1.py id` and `selftest`. 5. `hexn_flashimg_v1.py ring.bin a.fs b.fs c.fs`, write at offset 0, dump, `cmp`. 6. `hexn_ring_cycle_v2.py VECTOR_A VECTOR_B VECTOR_C --rounds 6 --settle 0`. 7. Restore from the backup and compare the dump's SHA-256.
