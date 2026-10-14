# Tang Nano 20K: the DIVISION core on the standard line and on the carrier, on the card (ledger #1171)

Two self-checking bitstreams (SRAM only). Each word goes flex (adds 1000) -> adapter -> divider -> adapter -> flex (adds 5), so the exit is 1000000 // (x + 1000) + 5 (32 bit). 9 words, random exit stalls, and one word divides by zero (the divider then gives all ones, the rule the LaTeX front end uses).

| test | middle block | LUT4 | FF | Fmax est. (27 MHz needed) |
|---|---|---|---|---|
| `mixed_std_div_pipe` | standard line, join-mode divider (div_cell_v4e), 1 quotient bit per clock | 1918 | 1077 | 126.6 MHz |
| `mixed_carrier_div_pipe` | trimmed VIXeN carrier keeping only ram + div | 1890 | 1077 | 118.2 MHz |

Run (Linux, needs openFPGALoader and root), power-cycling the board between the two:
    sudo env ONLY="mixed_std_div_pipe" ./run_all_v2.sh /dev/ttyUSB1
    (switch the board off and on, wait 20 s)
    sudo env ONLY="mixed_carrier_div_pipe" ./run_all_v2.sh /dev/ttyUSB1
Pass = `res=P n=0009 bad=0000` and sig=0002F664 for each. Send back board_results.txt and the raw folder of each run.

Honest limits: passed in simulation and closed timing at 27 MHz; not yet on the board. The dividend is a fixed 1000000 and the divisor a streamed word; unsigned division only; 1 quotient bit per clock (the cell takes about 32 clocks per word). This is the divider cell through the flex adapters, NOT a LaTeX formula built for the standard line: the LaTeX front end still builds division for flex and sub only.
