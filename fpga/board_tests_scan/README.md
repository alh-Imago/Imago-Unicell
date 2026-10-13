# In-flight capture and restore on the Tang Nano 20K (ledger #1145-#1147)

What this proves: a computation (the looped CORDIC) is stopped **part-way through**, with a word still travelling inside the compute cells; its whole state is read out over the serial cable, the card is reset (or powered off), the state is
written back, and the card carries on to the **same answer** as the run that was never interrupted. The serial side is checked at every step, because a corrupted state is worse than a lost one.

Two bitstreams, same serial protocol, same host script:
- `scan.fs`      -- the UniCell version: the flex cells with a scan chain through every cell (1905 bits), stop wrapper v3.
- `scan_pure.fs` -- the usual-FPGA version: plain Verilog CORDIC (no cells) with a clock-enable freeze and a 132-bit scan chain.

## Run
    sudo ./run_scan.sh                       # UniCell version, three cuts, prints PASS/FAIL per cut
    sudo ./run_scan.sh /dev/ttyUSB1 scan_pure.fs
    sudo ./run_scan.sh /dev/ttyUSB1 scan.fs --damage     # the host damages its own traffic on purpose (flipped bit in a written chunk, a lost byte, a flipped bit in a received line) and must still end PASS
    python3 scan_card_host.py PORT --capture-only --out img.json        # run to the cut and save the state to a file (power the card off after this if you want)
    python3 scan_card_host.py PORT --load scan.fs --restore-only --in img.json   # fresh load, state back in, run on, compare with the loop's own model
Each demonstration cut = `steps:lag:delay`; the default `3:0:0,4:7:1,5:20:0`. A PASS line means: answer of the interrupted-and-restored run = answer of the uninterrupted run = the Python model, **and** the complete card state at the end is identical.
Results are written to `results/scan_<time>.json`; send that file back.

## How the serial side is protected
Every chunk (32 bytes) carries design name, session number, sequence number and a CRC-32; the host accepts a chunk only if all four are right, otherwise it asks again (up to 4 retries, then it stops with an error and never returns a wrong image).
A capture is taken twice and the two must be identical. A restore is read back from the card and compared with what was sent. The card keeps a written chunk only if its own CRC check passes. The port is opened before the load and kept open.

## What has and has not been shown (read before trusting a PASS)
Shown in simulation (real Verilog in iverilog, wire damage injected): ledger #1145 (scan chain), #1146 (protocol), #1147 (this kit and the usual-FPGA version). Not shown until you run it: anything on the real card, the real 115200 baud timing, the card's own 77 ms byte timeout.
Cost (nextpnr, Tang Nano 20K part, 27 MHz target, whole card design including the serial controller): scan.fs 3905 LUT4 / 2828 flip-flops / Fmax estimate 98.6 MHz; scan_pure.fs 1778 LUT4 / 1035 flip-flops / 143.6 MHz. Fmax values are estimates, not measured on the card.
If the card stops answering after a few loads in a row (every fifth load, ledger #1024) unplug and replug the USB cable. If the run reports a ScanError, send the whole output back: it tells which step failed.
