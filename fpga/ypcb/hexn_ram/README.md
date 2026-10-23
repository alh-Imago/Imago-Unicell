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

STILL UNKNOWN (needs ypcb's `fpga` script): how `fpga build` finds the top module and picks up the .v files of a design folder. This
folder is meant to be symlinked as `~/ypcb-00338-1p1/designs/hexn_ram`, like `designs/hexn`. Not built yet.
