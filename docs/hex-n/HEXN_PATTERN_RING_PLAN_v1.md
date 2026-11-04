# Hex pattern ring: plan (4 Nov 2026, v1)

**Goal.** Put two or more real hex-array builds (each a full bitstream with a different PATTERN_ID) in the Tang Nano 20K's flash as a ring and show, with the card's own ID read-back, that a RECONFIG_N tap switches the array that is running. Everything below the first section is a plan, not a result.

## 1. What is already proven (flash side, 4 Nov, ledger rows 09:35-16:40)
A two-image ring built by `tools/hexn_flashimg_v1.py` (byte 0x25 = 0xcc, jump to the next slot) alternates between the two designs on taps; a hop takes about 100-300 ms (coarse); backup and restore are byte-exact. All of this used the blink and cordic images, **not** hex builds. Kit: `docs/hex-n/flash_multiboot_kit_v1/`.

## 2. What is NOT proven for the hex builds
- A hex card build has never been run on a real board (H5/H6 not done). RTL simulation against the VM passes (tests `test_hexn_hexcard_v1.py`); the UART link to a PC over the BL616 has not been tried.
- Bitstream sizes of the hex builds, measured from the 3 Nov fit-run outputs (.fs converted to bytes, 4 Nov 17:12): the array-only build with the slim frame v2 (/tmp/hexfit/v2run1) is 577,178 B; the array-only build with frame v1 (/tmp/hexfit/fitA) is 907,418 B. Both fit a 1 MiB slot. These are the same two sizes as smoke_v2 and unit_top; the size follows the number of frames in the header, not the design. Other builds not measured.
- Whether the hex card builds survive `hexn_fs2bin_v2.py` (same GW2A-18 header layout expected; the header finder will say).

## 3. How we will see which pattern is running
The LEDs will not tell us: in `hexn_frame_v2` the six LED outputs show frame status (busy, log pending, clear), not the pattern. The card answers `'I'` over the UART with 4 bytes PATTERN_ID (little endian) and 1 byte ROWS. So **identity = the ID read after each tap**, and the two patterns must differ in PATTERN_ID (and preferably in ROWS: for instance the 7x7 17-work mix and a 6x6 12-work mix, both of which have placed in nextpnr).
The UART pins 69/70 go to the BL616 and reach the PC over the same USB cable. Default CLKDIV 234 on 27 MHz gives about 115,385 baud (0.16 % above 115,200); the board file warns the on-board UART misbehaves at 3 Mbaud with heavy output, so we stay at ~115 k.

## 4. Steps and pass criteria
| # | Step | Pass when |
|---|---|---|
| P0 | Find the PC serial port (`ls /dev/ttyACM* /dev/ttyUSB*` before/after plugging; the BL616 may show two interfaces: the JTAG one is not the UART). | One port echoes our `'I'` reply in P1. |
| P1 | **Single hex card on the board (this is H5).** Build the 7x7 array, frame v2 (46 % of the chip, placed at 107.9 MHz, already built in /tmp/hexfit/v2run1 on 3 Nov; rebuild from `hexn_assemble_hex_v1.py build REF --out DIR --frame v2`). Load over USB into SRAM (`openFPGALoader -b tangnano20k hexn.fs`, no flash). New host script reads `'I'`. | PATTERN_ID and ROWS equal the build's ASSEMBLY.json. |
| P2 | Same card: wipe, load the add/sub test program (`'B'` chain from the assembler's `image` command), present words (`'D'`), start (`'G'`), read `'L'`. | Output words and ticks equal HexVM (ticks = VM tick + 32 on the card frame). This is the first real-board proof of the hex VM. |
| P3 | Build a second, different pattern (e.g. 6x6 12-work) and check it in P1/P2 the same way. | Different PATTERN_ID/ROWS, correct words. |
| P4 | Ring: `python3 tools/hexn_flashimg_v1.py ring.bin pat7.fs pat6.fs`. Back up the flash first (kit step 2), write at offset 0, dump and compare. | Dump equals ring; header finder shows two starts, jumps 0x100000 and 0. |
| P5 | Power-cycle (slot 0), read `'I'`; tap RECONFIG_N, read `'I'`; tap, read again; repeat six times. | IDs alternate pat7, pat6, pat7, ... with no other value. |
| P6 | Optional: a ring of three (third pattern), then restore LiteX and verify the SHA-256 (kit step 8). | Wrap-around works with three slots. |

Each step is its own ledger row, with what was observed and what was not.

## 5. New pieces to build
- **Host script** `tools/hexn_hexcard_host_v1.py` (pyserial): `id`, `wipe`, `load PROGRAM`, `run INPUTS` against HexVM, `watch` (read `'I'` on demand, for P5). Not written yet.
- Per-pattern build helper: assembler `build` + `build.sh` already exist (yosys, nextpnr-himbaechel, gowin_pack); each full run takes minutes, not measured here.
- Nothing needs changing in the flash tools.

## 6. Limits to keep in view
- A hop reloads the whole chip: the config chain, any weights and any state are **lost**; after each tap the program has to be loaded again over the UART. (Weights save/load across a hop is the subject of `hexn-weights-save-load`; not built.)
- The judge/open unit and the array fit together only at 6x6 with 12 work cells (87.6 %, placed) and do not at 7x7; on the card they are not linked on-chip. A ring switching between a judge+array image and a pure-array image is possible in principle; nothing here tests it.
- The prio4 failure at 7x7 offsets 0 and 1 is still undiagnosed; the P1/P2 reference uses offset 2, which placed and simulated.
- The first-row CRC repair, the 0xcc byte and the jump field are proven on two images only; the enabling bit in 0xcc is unknown.

## 7. Questions for Alan
1. Which serial port appears when the Tang is plugged in (name from `ls /dev/ttyACM* /dev/ttyUSB*`)?
2. Happy to do P1/P2 over SRAM first, leaving the flash alone? (Recommended: it proves the hex card on a board before any flash work.)
3. Which two patterns should be in the first ring?
