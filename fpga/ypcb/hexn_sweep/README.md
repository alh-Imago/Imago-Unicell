# hexn_sweep: four builds, one change each, to see what keeps the clock up as the cell count grows (prepared 25 Oct 2026)

Nothing here has been built yet. Simulation status is in `docs/hex-n/HEXN_DESIGN.md` (the row for this sweep).

| Variant | What changes | Files (all new clones; the proven files are untouched) |
|---|---|---|
| base | nothing: identical to `hexn_u2` | core v2, lattice v16, bank v17 |
| A | the signals going to all cells (cph, cph_start, cwin_end, lk_in, the replayed tokens) are registered once before the fan-out | bank v18, lattice v17 (generator `tools/hexn_lattice_gen_v17.py`) |
| B | the RUNCELLN reply is read from a result register that is loaded once and shifted, instead of a 2*NC-way multiplexer | core v3 |
| AB | both | core v3, lattice v17, bank v18 |

Why these two: `docs/hex-n/TILE_SHARED_SIGNALS_v1.md` (read from the RTL, a hypothesis). Not in this sweep: moving the per-cell settings into the cell (a bigger change).

## Run (one at a time; ~4 builds)
In the openXC7 nix shell from `~/ypcb-00338-1p1`, CHIPDB exported, no sudo, /mnt/hdd mounted, swap on:

    git -C ~/hexn-wt pull origin Hex-N
    ln -sfn ~/hexn-wt/fpga/ypcb/hexn_sweep designs/hexn_sweep
    bash ~/hexn-wt/fpga/ypcb/hexn_sweep/run_sweep.sh 64            # base A B AB at 64 cells
    bash ~/hexn-wt/fpga/ypcb/hexn_sweep/run_sweep.sh 64 base B     # only some variants

It writes `/mnt/hdd/hexn_builds/sweep_<variant>_64.log` and prints a summary at the end. Paste the summary back.

## Reading the result
- Compare the variants' clocks AGAINST THE `base` ROW OF THE SAME RUN, not against the older 64-cell figure (75.6 / 76.3 MHz): placement varies from run to run, and the older build used another top level.
- One build per variant is one sample. A difference of a few MHz is inside the run-to-run spread (not measured yet). A difference of 10+ MHz is worth following up.
- The clock is what nextpnr reports, not a measurement on silicon.
- If a variant goes onto the card later, run `tools/hexn_card_run_v2.py` with `tools/hexn_tang_cells_v1.py ... --ncell 64` (the all-cells check) before trusting it.
