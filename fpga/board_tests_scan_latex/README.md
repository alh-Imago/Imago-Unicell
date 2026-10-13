# In-flight capture and restore for a design written as ONE LINE OF LATEX (ledger #1151)

The design is the LaTeX line `y = (z^2 + 12345) \bmod 65521`, iterated (z -> y). Nobody wrote a cell or any Verilog: the LaTeX front end compiled it, the flex assembler placed it, the scan chain (678 bits, including the multiplier and the divider that are mid-calculation when you cut) was generated, and the same serial controller and host as the CORDIC kit carry the state.

## Run
    sudo ./run_scan.sh /dev/ttyUSB1                 # four cuts, PASS/FAIL each
    sudo ./run_scan.sh /dev/ttyUSB1 scan_latex.fs --damage
    python3 scan_card_host.py PORT --capture-only --out img.json
    python3 scan_card_host.py PORT --load scan_latex.fs --restore-only --in img.json   # power the card off in between if you like
Default cuts `3:3:0,4:12:0,5:30:0,3:0:0` (steps:lag:delay). PASS = interrupted-and-restored answer = uninterrupted answer = the plain Python model, and the complete end state is identical. Results go to `results/`; send them back.

## Swapping (from the repo, `tools/scan_swap_v1.py`)
    python3 tools/scan_swap_v1.py from-sim sim.json     # capture in the simulated card, then --restore-only --in sim.json on the real card
    python3 tools/scan_swap_v1.py to-sim card.json      # restore an image made on the real card into the simulated card
Images carry the design name and a fingerprint of the register layout; a different design is refused by the host and the swap tool (not yet by the card itself).

## Scope
Shown in simulation (real Verilog in iverilog, damage injected): cuts inside the multiply and the divide, round trips, swap sim to sim, foreign layout refused. Place and route: 2575 LUT4, 1601 flip-flops, Fmax estimate 110.8 MHz (not measured). NOT yet shown: any run on the real card, real-card to simulator swap, the VM (software) side.
