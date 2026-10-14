# Native cross and corner cells on the real card, 14 Oct 2026 (ledger #1170)
Card: Sipeed Tang Nano 20K (GW2AR-LV18QN88C8/I7), Alan's PC, `sudo env ONLY="tiles_flex" ./run_all_v2.sh /dev/ttyUSB1`. Bitstream from `tools/board_tiles_v1.py` (#1169): cross, corner turn 0, corner turn 1, 6 streams x 8 words, random exit stalls.
Result: PASS. The board line equals the simulated line in every field (n=0030, last=0000006A, sig=8B9E23CD); 276 complete lines in the capture. Result files and raw bytes (gz) here.
