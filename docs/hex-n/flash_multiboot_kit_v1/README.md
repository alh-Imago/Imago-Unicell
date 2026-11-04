# Flash multiboot kit v1 (Tang Nano 20K, GW2AR-18)

**What this is.** Every step, command and tool we used (4 Nov 2026) to put several complete FPGA images into the
board's SPI flash and switch between them with a pulse on the RECONFIG_N pad. Written from measurements on one
board; each claim says whether it was measured. Full evidence trail: `docs/hex-n/HEXN_DESIGN.md` (rows 3-4 Nov) and
`docs/hex-n/HEXN_FLASH_LOAD_SCOPING_v1.md`.

## What was measured and what was not

| | Status |
|---|---|
| Read the whole flash over USB (`--dump-flash`), identical twice (SHA-256 matched) | measured |
| Write a file at an offset (`-f -o 0x200000`) without touching anything else | measured (64 KiB) |
| Write images at offset 0 and 0x200000 (577 KB and 907 KB), verified by dump | measured |
| Chip boots offset 0 from flash; power-up always boots offset 0 | measured |
| **A tap of RECONFIG_N loads the image at the header's jump address, if header byte 0x25 = 0xcc** | measured (flag 0xae did not jump) |
| First-row CRC repair is correct (chip loaded a patched image) | measured |
| Restore from backup, byte for byte | measured |
| Hop time: about 100-300 ms from lights-out to new pattern (median ~190 ms), includes the hand-held low time | measured, coarse (120 fps video) |
| Which bit of byte 0x25 enables the jump (0xae vs 0xcc differ in three bits) | **not known** |
| Rings of three or more images; hops started by the ESP32 or by logic inside a design | **not tested** |
| Other boards (their flash chip may differ: ours reads 0b 40 17, one other board log showed ef 40 17) | **not tested** |

## What you need
- Tang Nano 20K, a USB **data** cable (a charge-only cable shows no device: `lsusb` must list `0403:6010`).
- openFPGALoader v0.12.0, Python 3, `pip install apycula` (the CRC code is imported from it).
- A way to touch the RECONFIG_N pad (pin 9, IOR31B) to the neighbouring GND pad for an instant: pogo pin or a probe.
- Your own `.fs` bitstreams (text 0/1 files from gowin_pack).

## Steps (in this order)
1. **Check the programmer.** `lsusb` shows `0403:6010`; `openFPGALoader -b tangnano20k --detect` prints IDCODE `0x81b`.
2. **Back up the flash FIRST** and keep a second copy outside `/tmp`:
   ```
   openFPGALoader -b tangnano20k --dump-flash --file-size 8388608 /tmp/flash_backup.bin
   openFPGALoader -b tangnano20k --dump-flash --file-size 8388608 /tmp/flash_backup2.bin
   sha256sum /tmp/flash_backup.bin /tmp/flash_backup2.bin      # must match
   cp /tmp/flash_backup.bin ~/flash_backup_$(date +%d%b).bin
   ```
   The loader prints the flash's JEDEC ID (ours `0b 40 17` = 64 Mbit). It runs "Erase SRAM", so the board goes idle until a power-cycle.
3. **See what is on the flash:** `python3 scripts/flash_map.py /tmp/flash_backup.bin` (ours: LiteX bitstream 0x0-0xE0000 and one 64 KiB block at 0x700000, the rest blank).
4. **Practice write** into blank flash (a pattern file, not a bitstream), then verify:
   ```
   openFPGALoader -b tangnano20k -f -o 0x200000 /tmp/practice64k.bin
   openFPGALoader -b tangnano20k --dump-flash --file-size 8388608 /tmp/after.bin
   python3 scripts/verify_regions.py /tmp/flash_backup.bin /tmp/after.bin /tmp/practice64k.bin 0x200000
   ```
   All three lines must say `True`.
5. **Build the ring image** from your `.fs` files (each 1 MiB slot, last jumps back to first):
   ```
   python3 tools/hexn_flashimg_v1.py ring.bin first.fs second.fs [third.fs ...]
   ```
   It sets header byte 0x25 = 0xcc, writes each slot's jump address, repairs the first-row CRC, and prints what it did.
   (`tools/hexn_fs2bin_v2.py` converts a single image, e.g. with `--jump 0x200000 --set-byte 0x25=0xcc`.)
6. **Write it** (this replaces offset 0, so the backup in step 2 must exist):
   `openFPGALoader -b tangnano20k -f ring.bin`, then dump and compare with `scripts/find_headers.py` / `verify_regions.py`.
7. **Run it.** Power-cycle: slot 0 runs. Tap RECONFIG_N to GND: slot 1 runs. Tap again: the next, wrapping to slot 0.
8. **Restore the original** whenever you want it back: `openFPGALoader -b tangnano20k -f ~/flash_backup_<date>.bin`, then dump and `sha256sum`: it must equal the backup's checksum.
9. **Time a hop (optional):** film the LEDs in slow motion, shrink with `ffmpeg -i in.mov -an -vf scale=640:-2 -c:v libx264 -crf 30 -fps_mode passthrough small.mp4`, run `python3 scripts/led_video_trace.py small.mp4`; set `FPS` to the camera's real capture rate (it scales every figure).

## How it works (what we found in the header)
Each bitstream starts with a header; the line `d2 00 ff ff` is followed by a 4-byte big-endian flash address (bytes 0x38-0x3b of the file),
the "SPI address" in apycula's source. Writing the next slot's address there, and 0xcc in header byte 0x25 (the flags line `10 00 00 00 00 xx 00 00`), makes a
RECONFIG_N reload go to that address instead of 0. apycula's CRC skips the `d2` line, so the jump needs no checksum change, but
byte 0x25 is inside the CRC and the repair is needed. See `data/measured_headers.txt`.

## Pitfalls we hit
- A charge-only USB cable: no device in `lsusb`. A wrong file path: "fail to open" from the loader.
- apycula always writes byte 0x25 = 0xae (a constant in its chip database); with 0xae the tap reloads offset 0 and ignores the jump.
- **Do not use `gowin_pack --reconfign_as_gpio`:** it frees the RECONFIG_N pin you need. (None of the other `--*_as_gpio` flags changed byte 0x25 in our test; `--ready_as_gpio` alone was not completed.)
- The `.fs` size is not the image size: a short image just has fewer frames (header line `3b 80 xx xx` at 0x40-0x43), it is not compressed.
- We first called a short image "compressed" and later withdrew it; the ledger keeps both rows.
- Flash chips differ between boards; the loader prints "flash chip unknown" for ours and works anyway.

## Credit and licences
The multiboot idea and the header fields were cross-checked against hoglet67's TangNano20KMultiboot (build script, `multiboot.vhd`) and
its Atom core (the design drives pad 9 low itself). **We read it and measured its release image; no code was copied.** The AtomFpga repo carries an Apache 2.0 licence;
we did not find a licence file at the top of TangNano20KMultiboot (a quick look). This kit's own tools are part of this repository.

## Files
`tools/hexn_fs2bin_v2.py`, `tools/hexn_flashimg_v1.py` (copies of the files in `tools/`, tested by `tests/vm/test_hexn_fs2bin_v2.py` and `test_hexn_flashimg_v1.py`),
`scripts/flash_map.py`, `scripts/find_headers.py`, `scripts/verify_regions.py`, `scripts/led_video_trace.py`, `data/measured_headers.txt`.
