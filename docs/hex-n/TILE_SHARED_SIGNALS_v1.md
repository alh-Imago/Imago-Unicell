# Which signals reach every cell (read from the RTL, 25 Oct 2026)

Status: **read from `rtl/hexn_core_v2.v`, `rtl/hexn_bank_v17.v`, `rtl/hexn_glue_v1.v` by eye. Nothing was synthesised or measured.** Whether any of these actually clump the placer is a hypothesis, not a result.
Build in use: lattice v16 / bank v17 / cell v5, `NC` cells (the placed 255-cell build is the largest).

## Shape: a star, no cell-to-cell wires
There is no daisy chain. Each of the NC cells (`CELLS[gc].fcell`, `hexn_cell_v5`) takes shared inputs, its own settings, and returns two small results. This is good for tiling: a tile is one cell plus its settings.

## 1. Broadcast: ONE signal drives all NC cells
| Signal | Width | Source | Note |
|---|---|---|---|
| `gout` (becomes each cell's `rx`) | K (7 or 19) | glue buffer (`hexn_glue_v1`) | the same replayed tokens go to every cell |
| `cph` | 1 | bank run controller | combinational from `act`, `w` |
| `cph_start` | 1 | bank run controller | combinational from `t0`, `w` |
| `cwin_end` | 1 | bank run controller | combinational from `tl`, `w` |
| `lk_in` | 3 | bank (`w == W ? leak_sh : 7`) | combinational |
| `clk`, `rst` | 2 | core | rst is registered (`por`) |
About K+8 nets fan out to 255 cells. The four control nets are combinational from counters, so they have logic in front of the fan-out. **Candidate fix (not tried):** register each of them once, then a second register stage per row of tiles.

## 2. Per-cell settings written from the core
`lcfg` (NC x 40 bits) and `cthr` (NC x AW bits) are registers in `hexn_core_v2`, not in the cell. At NC = 255 that is 10,200 + 1,785 flip-flops in the core. They are written through `lcfg[a0*40 +: 40] <= {a6..a2}` (command 0x11): an NC-way decode of one index, with the same 6 data bytes broadcast to all. The placer must pull each cell towards its own 47 setting flops, and those towards one command block. **Candidate fix (not tried):** move the settings register into the tile so the only shared things are the index decode and the data bytes.

## 3. Collection: all cells back to ONE output mux
`cell_cnt` (5 bits) and `cell_fwd` (AW bits) from every cell go through the readout state `CELLNB` with `cell_cnt_all[5*(ci>>1)+:5]` / `cell_fwd_all[...]`, a 2*NC-way mux into `tx_d`. That is every cell wired to one byte register. **Candidate fix (not tried):** a shift chain or tree, one tile reading the next, which also gives the tiles a regular layout.

## Inside the cell
Not analysed here. `hexn_cell_v5` has its own internal nets; only its ports were read.

## What this means for placement
- The sharing is limited and countable: about K+8 broadcast nets, 47 setting flops per cell, and 13 result bits per cell.
- The two points most likely to hurt timing are the combinational control broadcasts (1) and the single big readout mux (3). That matches the clock drop measured on the card (75.6 MHz at 64 cells down to 60.3 MHz at 255), but that match is a coincidence I have not tested.
- Test before changing anything: build hex7 at 64 cells with only the readout mux replaced, and compare the clock with the existing 64-cell figure. A clone, not an edit of the proven files.
