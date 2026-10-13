# Serial probe for the Tang Nano 20K (ledger #1130)

Two bitstreams with no cells in them; they only send framed, CRC-32-protected lines so we can measure the serial line to the PC on its own.

1. Power the card up cold.  2. `sudo ./run_probe.sh /dev/ttyUSB1`  3. Send `probe_results.txt` (and the `raw/` folder if anything is not CLEAN).

Verdicts: CLEAN = more than 20 frames, none corrupt, none missed. DEGRADED = some corrupt or missed (the counts say how many and how many bytes differ). SILENT = 0 bytes.
LED0 blinking and LED3 on mean the bitstream is running. Each variant is loaded once (no reload on silence). `serial_probe_fast` sends frames back to back (the hardest case for the PC side); `serial_probe_gap` leaves about 10 ms between frames.

| variant | LUT4 | FF | Fmax est. MHz |
|---|---|---|---|
| serial_probe_fast | 788 | 121 | 139.6 |
| serial_probe_gap | 809 | 153 | 139.5 |
