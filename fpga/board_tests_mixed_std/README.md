# Tang Nano 20K: flex <-> standard / carrier mixed pipelines on the card (ledger #1168)

Two self-checking bitstreams (SRAM only), 8 words each through flex -> adapter -> middle block -> adapter -> flex, every result x + 1239, random exit stalls:

| test | middle block | LUT4 | FF | Fmax est. (27 MHz needed) |
|---|---|---|---|---|
| `mixed_std_pipe` | STANDARD v4 cells | 1752 | 975 | 122.5 MHz |
| `mixed_carrier_pipe` | trimmed CARRIER cells | 1890 | 975 | 123.1 MHz |

Run (Linux, needs openFPGALoader and root), power-cycling the board between the two:
    sudo env ONLY="mixed_std_pipe" ./run_all_v2.sh /dev/ttyUSB1
    (switch the board off and on, wait 20 s)
    sudo env ONLY="mixed_carrier_pipe" ./run_all_v2.sh /dev/ttyUSB1
Results land in board_results.txt / .csv. Pass = `res=P` and sig=0000CC60 (the same checksum the flex-sub-flex `mixed_pipe` gave on the card, #1122); LED1 on = pass, LED3 on = finished, LED0 = heartbeat.

Honest limits: passed in simulation and closed timing at 27 MHz; nothing here has been on the board yet. 27 MHz, small design: it tests the flex <-> standard/carrier adapters (#1160, #1162) on silicon, not speed or capacity.
