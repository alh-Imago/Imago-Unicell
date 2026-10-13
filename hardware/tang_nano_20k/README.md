# Tang Nano 20K -- reading its serial line reliably on Linux

Written 13 Oct 2026 from a day of measurements (ledger #1129-#1138). For anyone testing designs on a Sipeed **Tang Nano 20K** (GW2AR-LV18QN88C8/I7, the on-board BL616 appears on the PC as an FTDI-style pair `ttyUSB0` = programming, `ttyUSB1` = the UART). The host tools are not specific to this card: they judge any framed serial stream (see "Other cards").

## The finding in one paragraph

Reading the card's UART with `stty ... ; cat /dev/ttyUSB1` **after** loading a bitstream stalled after the first ~54 frames in every run on a direct cable (3 runs: a 25 cm and a 10 cm cable), even though the card kept transmitting (an LED showed it). The same bitstream, same cable, same port, same delay, read with a small Python raw reader (`host_tools/watch_serial.py`), ran flat out for the whole 30 s: **2961 CRC-checked frames, none missing, none damaged (115200 baud fully used)**. So the stream is fine; the stall is in the `stty` + `cat` read path. Not known: *why* (the tty settings `stty` leaves, throttling, or opening the port twice are candidates; none tested). Also found: while no program has the port open the BL616 keeps only about the first 9 KB and drops the rest, so **open the port before you load, and keep it open**.

## What was measured (same card, 10 cm or 25 cm cable)

| run | port opened | reader | result |
|---|---|---|---|
| old script, twice | after the load | stty + cat | 54 valid frames (seq 1..54), then nothing, for the rest of 20 s |
| watcher | before the load | Python raw | 302,514 bytes in 30 s, 2961 valid frames, 0 missed, 0 bad bytes |
| watcher `LATE=7` | 7 s after the load | Python raw | live stream to the end, no stall; but 747 early frames missing (the bridge buffer held ~9 KB, the rest was dropped while nobody was reading) |
| watcher `LATE=7 READER=cat` | 7 s after the load | stty + cat | 54 valid frames (seq 1..54), then nothing -- the stall again |

Other things seen: a different cable length made no difference. The card's LiteX demo (in its flash) prints a banner and memtest text on the same UART at power-up; the checker counts those lines as "corrupt" but they are foreign text, not damaged frames. After a load the kernel log shows the FTDI device detach and re-attach; the Python reader opens the port once and keeps its stream. A late `ttyUSB0` disconnect/re-attach near the end of each run is unexplained and did not disturb the stream. Behind a switchable USB hub the same old reader got 0 bytes (not 54 frames); the hub was not re-tested with the Python reader, so whether it matters is not known. BL616 firmware version was not checked (Sipeed's 20K firmware is serial 2025030317; `lsusb -v -d 0403:6010 | grep -i iSerial`).

## Rules that follow

1. Open the serial port **before** the load and keep it open; read with the raw Python reader, not `stty`+`cat`.
2. Judge every capture by frame sequence numbers and checksums, not by "it printed something". A stalled or lossy capture then shows up as DEGRADED.
3. Power the card off between sessions (it overheats; every-fifth-load dropout, #1024). Load each bitstream into SRAM once.
4. Old results gathered with `stty`+`cat` (silent designs, NOREPORT) are suspect until re-run with the Python reader.

## Files

- `serial_probe/` -- two cell-free bitstreams (`serial_probe2_fast.fs`, `serial_probe2_gap.fs`) that send `UCP seq=XXXX d=W0..W7 crc=CCCCCCCC` frames, with LED1 toggling every 64 frames sent (about once a second = "the card is transmitting"), plus the Verilog and constraints. Run: `sudo ./run_probe_watch.sh /dev/ttyUSB1` (cold card, one variant per run: `ONLY=serial_probe2_gap`; `SECS=`; `LATE=7`; `READER=cat`). `run_probe.sh` is the old stty+cat script, kept only to reproduce the stall.
- `host_tools/watch_serial.py` -- opens the port raw 115200, 8N1, no flow control, re-opens it if the device vanishes, logs the arrival time and size of every chunk to `<out>.log`. `python3 watch_serial.py PORT out.bin SECONDS`.
- `host_tools/check_probe.py` -- judges a capture: valid frames, corrupt frames, missed frames between valid ones, differing bytes. `python3 check_probe.py capture.bin`.
- `host_tools/board_runner_v2.py` -- gives a board-test folder (this project's `fpga/board_tests*`) a `run_all_v2.sh` that uses the Python reader opened before the load. Tested against a simulated board (`tests/vm/test_board_runner_v2_v1.py`).
- Needs `openFPGALoader`, python3 (standard library only), root or the dialout group.

## Other cards

The frame is `UCP seq=XXXX d=<8 words as 8 hex digits, comma separated> crc=CCCCCCCC\r\n`; the CRC-32 (zlib) covers the text up to the last word digit (86 bytes), the frame is 101 bytes. word k of frame `seq` is `mix(seq,k)`: `x=(seq*0x9E3779B1+k*0x85EBCA6B+0x1234567)&0xFFFFFFFF; x^=x>>15; x=(x*0x2C1B3C6D)&0xFFFFFFFF; x^=x>>12`. Any card that can send that over a serial link can be judged by `check_probe.py`, and `watch_serial.py` works on any tty. The Verilog transmitter is `serial_probe/board_uart_tx.v` (clocks-per-bit parameter `CPB`, 234 = 115200 baud at 27 MHz; the `.cst` files are Tang Nano 20K pins).
