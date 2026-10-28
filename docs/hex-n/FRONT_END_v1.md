# Hex-N front end (boot shell), proposal v1, 28 Oct 2026

**Status: proposal; nothing built.** Alan's idea (28 Oct 2026, 16:41): on boot a front end is loaded; it can copy a bitstream from the SD card into the flash space and load it with its data; move files between the SD card and the host in both directions; create new bitstream folders (volumes, see CARD_FORMAT_v1.md) on the card; and when a task is finished a simple reboot returns to the front end.

## What the Tang board allows (checked)

| Fact | Source |
|---|---|
| The board flash is 64 Mbit = 8 MB (XT25F64F, partly legible in a photo, so the exact part is not certain) and holds the configuration bitstream | `docs/man/tang-nano-20k.man.json` |
| One of our bitstreams is about 907,000 bytes (counted from a built `.fs`), so the flash holds roughly 8 images | measured on `hexn_tang_tiertest_v1.fs` |
| The flash pins are the configuration pins MCLK/MCS_N/MO/MI = package pins 59/60/61/62; the open flow can release them as ordinary I/O (`gowin_pack --mspi_as_gpio`), and at least one third-party design uses the on-board flash from user logic | `tang-nano-20k.cst`, `gowin_pack --help`, MAN sources |
| RECONFIG_N is package pin 9 (chip database). Whether pin 9 is reachable on the board (edge connector, button, BL616) is NOT in our board files | Apicula chip database read 28 Oct |
| The GW2AR-18 QN88 chip has only JTAG and flash boot; no slave configuration; no multi-boot or fallback is described. A reload (RECONFIG_N low) re-reads the flash from its start | Gowin UG206 as fetched 28 Oct |

## The central consequence

The chip always boots the image at the START of the flash. So if the front end copies a task bitstream into that place, the front end is gone and a reboot loads the task again, not the front end. Three ways to give Alan "a simple reboot brings it back to the front end":

1. **Front end inside every task (recommended).** Every build links in a small standard front-end block (SD controller, flash writer, host serial protocol; the SD controller is about 1/3 of the size of the pieces already built and proven, `sd_spi_v1`). A task design starts in front-end mode after any reset; a reboot (power cycle, or the reload trigger) therefore returns to the front end with no flash rewriting. Cost: some logic in every build (estimate, not measured: 1,000 to 2,000 LUT cells of 20,736). Fits the project rule "compose from existing cells".
2. **Task writes the front end back.** A small "return" block in the task copies a saved front-end image (kept in the upper flash or on the card) over the start of the flash and reloads: about 1 MB erased and programmed, an estimated 15 to 25 seconds each time, and a power cut in that window leaves the board unbootable until the host re-flashes it over USB (always possible; the board cannot be permanently bricked this way).
3. **Task loaded volatile by the host** (as now): power cycle returns to the flash. This keeps the flash holding the front end, but needs the host to load the task, which is what Alan wants to avoid.

## Risks that must be tested before anything touches the start of the flash

* Writing the flash from user logic: not yet shown on this board. First test is read-only (JEDEC ID, first bytes), then erase/program/verify only in the upper half of the flash (at or above 4 MB), with the controller refusing writes below 4 MB unless an unlock input is set. A bug can then never damage the boot image.
* Unplanned loss of power or a bad image while the start of the flash is rewritten: recoverable over USB-JTAG from the host, not automatically. Mitigation: stage the new image in the upper flash first, check its CRC, and only then copy it to the start.
* Flash endurance: each load is one erase cycle per 4 KB sector; the vendor figure (typically tens of thousands of cycles) is not verified for this part.
* Reload trigger (RECONFIG_N): unverified. If pin 9 is not reachable, a reload still happens at every power-up, but "reboot from inside the design" is not available; option 1 then needs a soft reset into front-end mode instead, which needs no pin.

## Host side

File moves between the host and the card use the BL616 USB serial port. At 115200 baud that is about 11 KB/s (a 900 KB bitstream takes about 80 s); faster rates are possible but not tested on this board. Commands (proposal): list volumes, create volume, put file, get file, delete file, copy bitstream to flash, verify, run. The existing `hexn_tang_host_*.py` host scripts are the pattern for the PC end.

## Proposed build order (each step simulated, then run on the board, as before)

1. Flash read-only probe and the guarded upper-flash erase/program/verify test (`hexn_flash_v1`): proves the board lets user logic use the flash.
2. SD file area: write, read and list named files in a volume's file region (extends the card format).
3. SD to upper flash copy with CRC check.
4. Front-end command protocol over the serial port (host put/get).
5. Swap-in of a staged image to the start of the flash and reload (the only step that touches the boot image; do last, with the host recovery path at hand).
