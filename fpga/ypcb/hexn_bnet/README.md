# hexn_bnet: the merged bus network on the Kintex card (prepared 9 Nov 2026)

Nothing here has been built on the openXC7 flow yet. What it answers: **how many LUTs the merged bus network (direction doc sections 44 and 46) takes on the real chip, and what clock nextpnr estimates for it.** Not a function test: the card has no pins to drive the network, so an LFSR feeds a shift register that drives every input (event lines, table and threshold writes), and every output is folded into one LED. The proof that the logic is right is the iverilog cross-check against the Python model (`tests/vm/test_hexn_bnet_net_v2.py`), not this build.

The flow is the openXC7 one in `docs/` / `claude/kintex-card-flow.md` (yosys + nextpnr-xilinx, **no Vivado**), the same as `hexn_sweep`.

## Run
In the openXC7 nix shell from `~/ypcb-00338-1p1`, CHIPDB exported (the script sets the known path if you forgot), no sudo, /mnt/hdd mounted, swap on:

    git -C ~/hexn-wt pull origin Hex-N
    ln -sfn ~/hexn-wt/fpga/ypcb/hexn_bnet designs/hexn_bnet
    bash ~/hexn-wt/fpga/ypcb/hexn_bnet/run_bnet.sh                      # 2:8:16:2  4:16:48:3  8:8:48:3, one after another
    bash ~/hexn-wt/fpga/ypcb/hexn_bnet/run_bnet.sh 2:8:16:2             # just the small one first (the quick check that the flow accepts the RTL)

Shapes are G:PER:NIN:SQL (buses per layer : cells per bus : input lines : sub-queue depth 2^SQL). Allow tens of minutes per build; 4:16:48:3 is the biggest (about 19K LUT6 in the yosys count of section 44; the earlier 255-cell Hex-N build took about 69 minutes).

## What to send back
The SUMMARY the script prints at the end (or the `.log` files in `/mnt/hdd/hexn_builds/`). The numbers wanted: the nextpnr "Max frequency" lines, the LUT/FF/DSP use, and any error text.

## Things that could go wrong (guesses, not seen)
- The RTL uses SystemVerilog `always_comb` and `$clog2`. The Gowin and plain yosys runs here accept it; whether the flow's yosys call is in SystemVerilog mode is not known. If the first build stops at a syntax error on `always_comb`, send the first lines of the log.
- The design uses about 50 DSP48 blocks in yosys (cause not traced). If the flow rejects them, send the log.
- 50 MHz is the target. The Tang Nano 20K figure (about 75 MHz after pipelining, plus or minus 10) is a different chip and not a prediction for this one.
