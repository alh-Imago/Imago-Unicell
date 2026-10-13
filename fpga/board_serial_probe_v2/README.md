# Serial probe for the Tang Nano 20K (ledger #1131)

Two bitstreams with no cells in them; they only send framed, CRC-32-protected lines so we can measure the serial line to the PC on its own.

1. Power the card up cold.  2. `sudo ./run_probe_watch.sh /dev/ttyUSB1` (the port is opened BEFORE the load by `watch_serial.py`; one variant per run, `ONLY=serial_probe2_gap` for the other).  3. Send `probe_results.txt` and `raw/` (the `.watch.log` has the arrival time of every chunk).

`run_probe.sh` is the older script that reads with `stty` + `cat` after the load: on this card that reader stalls after the first ~54 frames (ledger #1137), so it is kept only for comparison. `LATE=7 ./run_probe_watch.sh` opens the port 7 s after the load; add `READER=cat` to reproduce the stall.

Verdicts: CLEAN = more than 20 frames, none corrupt, none missed. DEGRADED = some corrupt or missed (the counts say how many and how many bytes differ). SILENT = 0 bytes.
LED0 blinking and LED3 on mean the bitstream is running. Each variant is loaded once (no reload on silence). `serial_probe2_fast` sends frames back to back (the hardest case for the PC side); `serial_probe2_gap` leaves about 10 ms between frames.

| variant | LUT4 | FF | Fmax est. MHz |
|---|---|---|---|
| serial_probe2_fast |  |  |  |
| serial_probe2_gap |  |  |  |
