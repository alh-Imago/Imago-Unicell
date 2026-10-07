# Tang Nano 20K on-board tests (ledger #1023)

Each `<name>.fs` is a complete, self-checking bitstream: a UniCell flex design, a fixed input stream, and the expected answers built in. When it has run it sends one line over the board's USB serial port (115200 baud, repeated about every 0.3 s) and lights the LEDs: **LED1 on = PASS, LED2 on = FAIL, LED3 on = finished, LED0 = heartbeat** (all active low, LED numbers as on the board silkscreen's `LED0..LED3` = pins 15-18).

## To run them all

1. Plug the board in by USB-C. 2. Install `openFPGALoader` and `pip install pyserial` (see `docs/shared/TOOLCHAIN_SETUP.md`). 3. Double-click `run_all.bat` (or `run_all.bat COM7` to name the serial port). 4. Read `board_results.txt` (and `board_results.csv`).

The bitstreams are loaded to SRAM only (gone at power-off); the flash is not touched.

## The line

`UCT <name> res=P|F n=<words received> e=<words expected> bad=<wrong or extra words> to=<1 if it timed out> last=<cycle of the last word> sig=<checksum> w=<first 8 words>` (all hex). `board_results.txt` puts the line the **simulation** produced beside the one the **board** produced; for a pass they match except `last=` (cycle counts can differ by a few at the start-up).

## The tests

| test | what it proves | LUT4 | FF | Fmax (MHz, 27 needed) |
|---|---|---|---|---|
| `relay_chain` | four ram cells in a row pass 16 distinct words through unchanged (the basic handshake) | 1792 | 652 | 128.5 |
| `relay_chain_stalled` | the same chain with random gaps on the input and random stalls on the output (nothing lost, repeated or reordered) | 1073 | 489 | 139.8 |
| `adder_stream` | an adder joins two streams, 12 sums (32-bit wraparound included) | 1792 | 704 | 127.0 |
| `adder_stalled` | the adder with random gaps on both inputs and random output stalls | 1226 | 520 | 144.1 |
| `adder_constant` | a fixed-mode ram feeds the constant 5 to an adder (offered on every tick, never used up) | 878 | 384 | 149.2 |
| `ram_hold` | the ram's HOLD behaviour: 7 is written once and added to six items; it is offered again each time (never used up) (#1021) | 814 | 398 | 160.4 |
| `ram_oneshot` | the ram's ONE-SHOT preload: the configured 100 is offered once; only the first item sees it, the rest wait (#1021) | 714 | 352 | 174.2 |
| `priority_strict` | priority core, strict ranks west > north > south, three sources of six items | 1079 | 468 | 146.8 |
| `priority_weighted` | priority core, weighted round robin (weights north 1, west 3, south 2) | 1103 | 492 | 130.7 |
| `priority_sequenced` | priority core, sequenced channel with the fixed turn order south, west, west, north | 1106 | 471 | 139.5 |

## What a failure would mean

- **NOLOAD**: the loader could not program the board (cable, driver, `openFPGALoader` not on the PATH).
- **NOREPORT**: it loaded but nothing came back on the serial port: wrong COM port (the board shows two; the FPGA UART is the second), or the UART pin (69) does not reach the PC the way the MAN file says (it has never been used by this project). The LEDs still show the verdict.
- **FAIL** with a line: the design ran on silicon and gave a different answer from the simulation: compare `board` and `simulated` (`bad=` counts wrong words, `n=` the words that arrived).

## Honest limits

- Every bitstream passed in simulation (with the UART text decoded) and closed timing at 27 MHz in place-and-route, but nothing here has been on the board yet. The UART pin is unverified (the earlier smoke test used LEDs only).
- 27 MHz only: there is no PLL, so this is not a speed test. The designs are small (a few cells), so they test the cell RTL and the handshake on real silicon, not capacity.
- The expected words come from FlexGrid (the VM's flex mirror), which is proven equal to the generated RTL; the simulation then proves the wrapper's own checker agrees.

## Rebuilding the bitstreams

The `.fs` files are not kept in git (about 4.5 MB each). Rebuild them with `python3 tools/board_tests_v1.py` (needs yosys, `pip install yowasp-nextpnr-himbaechel-gowin apycula`, iverilog; about 6 minutes), or use the zip that was sent with the ledger #1023 session.
