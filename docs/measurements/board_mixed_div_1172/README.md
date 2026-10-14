# Division core on the standard line and the trimmed carrier, on the real card, 14 Oct 2026 (ledger #1172)
Card: Sipeed Tang Nano 20K (GW2AR-LV18QN88C8/I7), Alan's PC, `sudo env ONLY=<name> ./run_all_v2.sh /dev/ttyUSB1`, one load per power-up, bitstreams from `tools/board_mixed_div_v1.py` (#1171).
Both PASS: the board line equals the simulated line in every field (n=0009, last=00000146, sig=0002F664), incl. the word that divides by zero. mixed_std_div_pipe: 45,578 bytes, 270 lines; mixed_carrier_div_pipe: 46,960 bytes, 267 lines. Result files and raw bytes (gz) here.
