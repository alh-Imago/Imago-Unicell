# In-flight capture and restore for a design written as ONE LINE OF LATEX (ledger #1151)

The design is the LaTeX line `y = (z^2 + 12345) \bmod 65521`, iterated (z -> y). Nobody wrote a cell or any Verilog: the LaTeX front end compiled it, the flex assembler placed it, the scan chain (678 bits, including the multiplier and the divider that are mid-calculation when you cut) was generated, and the same serial controller and host as the CORDIC kit carry the state.

## Run
    sudo ./run_scan.sh /dev/ttyUSB1                 # four cuts, PASS/FAIL each
    sudo ./run_scan.sh /dev/ttyUSB1 scan_latex.fs --damage
    python3 scan_card_host.py PORT --capture-only --out state.json     # writes ONE self-describing file (every cell and register named, with its value); add --raw for the old bare-bits file
    python3 scan_card_host.py PORT --load scan_latex.fs --restore-only --in state.json     # accepts either kind   # power the card off in between if you like
Default cuts `3:3:0,4:12:0,5:30:0,3:0:0` (steps:lag:delay). PASS = interrupted-and-restored answer = uninterrupted answer = the plain Python model, and the complete end state is identical. Results go to `results/`; send them back.

## Swapping (from the repo, `tools/scan_swap_v1.py`)
    python3 tools/scan_swap_v1.py from-sim sim.json     # capture in the simulated card, then --restore-only --in sim.json on the real card
    python3 tools/scan_swap_v1.py to-sim card.json      # restore an image made on the real card into the simulated card
Images carry the design name and a fingerprint of the register layout; a different design is refused by the host and the swap tool (not yet by the card itself).

## The state file
`python3 scan_image.py show state.json` prints it in words. It carries the design name, formula, layout fingerprint, cut and every register by name; restoring rebuilds the bits by name and refuses, listing the differences, if the design does not match. One file is all that needs to travel (the card needs the matching bitstream, which names the same design).

## From the VM
`images/vm_after_3_results_10_ticks.state.json` is a state made by the VM (`tools/vm_state_bridge_v1.py from-vm`), not by a card: `python3 scan_card_host.py PORT --load scan_latex.fs --restore-only --in images/vm_after_3_results_10_ticks.state.json` should end at step 7, word 25408 = model.

## Scope
Shown in simulation (real Verilog in iverilog, damage injected): cuts inside the multiply and the divide, round trips, swap sim to sim, foreign layout refused. Place and route: 2575 LUT4, 1601 flip-flops, Fmax estimate 110.8 MHz (not measured). NOT yet shown: any run on the real card, real-card to simulator swap, the VM (software) side.
