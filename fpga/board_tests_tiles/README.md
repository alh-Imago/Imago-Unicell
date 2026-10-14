# Tang Nano 20K: the native cross and corner cells on the card (ledger #1169)

One self-checking bitstream, `tiles_flex`: three tiles in one generated flex design, a CROSS (W->E and N->S) and a CORNER with turn 0 (W->S, E->N) and a CORNER with turn 1 (W->N, E->S).
Six independent streams of 8 words each (48 words) go through them, handed in round-robin and taken out in the same order, with random exit stalls. The output must equal the input.
A tile that mixed, swapped or dropped a stream changes the order or the words: with every tile built as an ordinary relay the same wrapper reports FAIL in simulation (96 words instead of 48).

3032 LUT4, Fmax estimate 117.1 MHz (27 MHz needed). Pass = `res=P n=0030 bad=0000`, sig=8B9E23CD.

Run (Linux, needs openFPGALoader and root; power-cycle the board first, one load per power-up):
    sudo env ONLY="tiles_flex" ./run_all_v2.sh /dev/ttyUSB1
Send back board_results.txt and the raw folder.

Honest limits: passed in simulation and closed timing at 27 MHz; not yet on the board. Flex family only (the sub-family native tiles are not in this bitstream). Small design at 27 MHz: it shows the tile logic and handshake on silicon, not speed or capacity.
