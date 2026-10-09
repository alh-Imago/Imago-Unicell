# Small unit for design `icm_parallel_reduction_tree_flex` (4 entry lanes, 1 exits)
Sources: FILES.txt. Pins: unit_top.cst (top module `unit_top`). Lanes and registers: lanes.json.
Typical sequence over SPI (ESP32): read ID (reg 0) -> wait STATUS bit0 (card up) -> set START_BLOCK / NBLOCKS, CONTROL=1 (load) -> wait STATUS bit4 -> set PLAY_COUNT = items*4, CONTROL=4 (play) ->
(a design that holds ONE item at a time, e.g. the CORDIC, needs pacing: CONTROL=8 to clear the capture, MAX_OUT=1, RPI=1 first) poll CAP_COUNT (reg 6) until all results are in -> RD_WORDS from capture address 0 (and/or set START_BLOCK, NBLOCKS and CONTROL=2 to save them to the card; CONTROL=0x10 clears the done bits first).
Use blocks well away from block 0 (a FAT32 card keeps its partition table there): e.g. input at block 16.., results at block 17.. or later. Raw blocks overwrite whatever is there.
NOT run on a board. The SD slot's pull-ups are not listed in the board file: the .cst turns the FPGA's internal pull-ups on for the SD pins.
