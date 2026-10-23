# hexn_ram: RAM latency probe for the Kintex card's DDR3 (work in progress)

`memlat.v` measures how long the UberDDR3 Wishbone port takes to answer reads: one random read at a time (min, max, sum of
latency in controller clock cycles), then reads issued back to back (random and sequential) to see whether they overlap.
Reads only; nothing in the RAM is changed. `tb_memlat.v` is a stand-in memory; check with `python3 tools/hexn_memlat_sim_v1.py`
(simulation only: PASS means the probe counts correctly, it says nothing about the real card).

NOT YET BUILT FOR THE CARD. Still to do: a build folder like `designs/uberddr3` (prebuild that copies UberDDR3 from
`~/fpga/src/UberDDR3` at commit 79d8fd3, GPL so never stored here, hooks `memlat` onto the Wishbone port in place of `memtest`,
and exposes its registers and a start/mode/count control over the JTAG USER1 register), and a host script to run it.
