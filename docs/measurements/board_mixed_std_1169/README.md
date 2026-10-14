# Flex <-> standard / carrier mixed pipelines on the real card, 14 Oct 2026 (ledger #1169)
Card: Sipeed Tang Nano 20K (GW2AR-LV18QN88C8/I7), Alan's PC, `sudo env ONLY=<name> ./run_all_v2.sh /dev/ttyUSB1`, one load per power-up. Bitstreams from `tools/board_mixed_std_v1.py` (#1168).
- mixed_carrier_pipe: PASS. 270 complete board lines, every one equal to the simulated line (n=0008, sig=0000CC60). Result files and raw bytes (gz) here.
- mixed_std_pipe: PASS as printed by the run script (42,232 bytes captured; "SUMMARY: 1 of 1 passed"). Alan pasted the terminal output; his result file for this run was not sent, so the line itself is not archived here.
