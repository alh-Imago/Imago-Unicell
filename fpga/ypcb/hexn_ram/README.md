# hexn_ram: RAM latency probe for the Kintex card's DDR3 (work in progress, nothing run on the card yet)

`memlat.v` measures how long the UberDDR3 Wishbone port takes to answer reads: one random read at a time (min, max, sum of
latency in controller clock cycles), then reads issued back to back (random and sequential) to see whether they overlap.
Reads only; nothing in the RAM is changed.

How it plugs in (nothing of Alan's ypcb repo or of UberDDR3 is copied or changed here):
- `memtest.v` here has the SAME module name and ports as ypcb `designs/uberddr3/memtest.v` but runs `memlat`; results come back in the
  old memory test's register words (23 lat_min, 24 lat_max, 25 lat_sum, 26 stall_sum, 27 read-data fold, 28 total cycles, 29 reads counted).
- `prebuild.py` just runs ypcb's own `designs/uberddr3/prebuild.py` with the same arguments, so the generated top level and the JTAG
  USER1 layout are the uberddr3 ones. UberDDR3 (GPL) must be at `~/fpga/src/UberDDR3`, commit 79d8fd3.
- `memlat.py` is the host script (uses ypcb's `tools/jtagdr.py`).
- Simulation: `python3 tools/hexn_memlat_sim_v1.py` (stand-in memory; PASS says only that the probe counts correctly).

Build facts (read from ypcb tools/xc7-build.sh): it runs this folder's prebuild.py with the build dir, reads `gen_*.v` from the build dir then every `*.v` in THIS folder (not subfolders, so the testbench lives in `sim/`), uses `gen_*.xdc` from the build dir, and the top module is the 2nd argument (default: folder name). The top module name of the uberddr3 generated top level still has to be confirmed. This folder is meant to be symlinked as `~/ypcb-00338-1p1/designs/hexn_ram`, like `designs/hexn`. Not built yet.

## Running on a machine without xsdb (Alan's OptiPlex)
ypcb's `tools/jtagdr.py` reads the card through `xsdb`, which is not installed here. `jtagdr_openocd.py` offers the same calls
(`read_dr`, `xfer_dr`, `words`, `gray_to_bin`) over OpenOCD, and `run_with_openocd.py` puts it in place of `jtagdr` and then runs an
unchanged script. From `~/ypcb-00338-1p1`, in the nix shell:

    nix shell nixpkgs#openocd --command env OPENOCD=openocd python3 ~/hexn-wt/fpga/ypcb/hexn_ram/run_with_openocd.py designs/uberddr3/check.py
    nix shell nixpkgs#openocd --command env OPENOCD=openocd python3 ~/hexn-wt/fpga/ypcb/hexn_ram/run_with_openocd.py ~/hexn-wt/fpga/ypcb/hexn_ram/memlat.py --len 10

Tested only against a fake scan (packing and splitting of the register); NOT yet against the card.
