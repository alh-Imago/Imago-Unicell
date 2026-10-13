# Group run on the real card, 13 Oct 2026 (ledger #1167)
Card: Sipeed Tang Nano 20K, GW2AR-LV18QN88C8/I7 (Alan's, run on his PC with `sudo ./run_groups_v2.sh /dev/ttyUSB1`). Bitstreams built from commit 13f12fd with `tools/board_groups_v2.py` (yosys 0.69, nextpnr-himbaechel-gowin, gowin_pack).
Result: 10 of 10 tests pass; `board_results_1167.txt/.csv` come from `fpga/board_tests/board_collect_v2.py` run on the captured serial bytes (`group_A.bin.gz`, `group_B.bin.gz`).
The run script printed "0 of 0" because the v1 collector looked for the bitstreams next to itself and the groups are in `groups/`: a fault of the collector (fixed in v2), not of the card.
Built sizes: group A 5461 LUT4 / 2684 FF, Fmax est. 121.1 MHz; group B 3686 LUT4 / 2116 FF, 136.5 MHz (the committed `fpga/board_tests/groups/*.json` of #1025 say 6982 and 4610 LUT4 from the older yosys; those files are kept unedited).
