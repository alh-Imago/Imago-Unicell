# k7_freeze_v2 -- freeze the Tang tree on the Kintex card and read the cells' VISIBLE AND HIDDEN state over JTAG (ledger #1247)

Clone of the freeze kit k7_freeze (#1243-#1246, proven on the card: 341 frames equal to the simulation). Same driver, same freeze, same commands; the
differences are the cells and the size of the scan.

**New: the hidden state.** The cells are debug clones (`adder_cell_v4f`, `ram_cell_v4d` and their shells; made by `tools/cell_debug_clone_v1.py`,
behaviour identical, one extra output port each). For each of the 13 cells the scan now carries, besides the visible output word and flags:
* **adder:** the waiting first operand `a_reg`, `out_buffer`, downstream / upstream / second-downstream masks, `pending_ack`, subtract / join / second-output flags, carry state, phase, `armed`.
* **RAM:** the stored word `data_reg`, `init_data`, the 20-bit `addon_config`, the masks, `pending_ack`, `data_valid`, `fixed_mode`, `armed`.
Still not read: the shell's own wiring (combinational) and anything outside the 13 cells (the driver's counters are in the header words).

## Do this (same as the earlier kit; this is a different folder and a different bitstream)
1. Copy this folder into `demo-projects` (next to `k7_freeze`, so `../openXC7.mk` is found). In the openXC7 Nix shell: `make`, then `make program JTAG_LINK="-c ft232"`.
2. From a **plain terminal**, in this folder, one command per line:
   * `nix shell nixpkgs#openocd --command sh freeze_read.sh`           (pure read; expects magic 46525A32 "FRZ2")
   * `nix shell nixpkgs#openocd --command sh freeze_at.sh 346`
   * `nix shell nixpkgs#openocd --command sh freeze_release.sh`
   * `nix shell nixpkgs#openocd --command sh freeze_sweep.sh 0 1700 5`   (writes sweep.csv with the hidden columns)
   * `nix shell nixpkgs#openocd --command sh freeze_busy.sh`              (every count over the busy stretches)
3. Send back the logs / csv files.

## Checked in simulation (not on the card)
`make sim` (iverilog): the frozen snapshot, visible and hidden, equals an unfrozen copy at count T+1 at 24 counts; the hidden words agree with the configuration the
Tang schedule loads (adder masks 2 / 9 / 4, join mode, the exit cell's fixed mode and upstream mask 8, the exit word); release finishes the run with the Tang's signature.
