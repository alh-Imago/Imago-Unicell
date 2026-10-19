# k7_freeze_v1 -- freeze the Tang tree on the Kintex card and read its cells over JTAG (ledger #1243)

**Idea (Alan, 19 Oct 2026):** if JTAG works, initiate a freeze and save to get the actual states of the latches. This is the first small version.

**What it does.** The Tang Nano 20K's own `std_tree4` grid (13 cells; four-lane add tree) runs on the Kintex. A small driver replays the Tang
top's own load schedule. On a command from the PC the run restarts and **the card stops itself at a clock count T you choose** (every
cell's `freeze_in` is tied to one line). The PC then reads, in one JTAG scan, every cell's output word, its four "fire" (pending
acknowledge) bits and its data-valid and operand-arrived flags. A freeze at count T shows the state the running grid has at count T+1. Scan T = 0, 1, 2, ... to get a frame-by-frame record of the grid.

**What it does NOT show (yet).** Only the cells' visible state. The waiting operand (`a_reg`), configuration, masks and the RAM cells'
stored words are inside the cells and are not brought out; that needs a debug port on a cloned cell (v4f). The grid is the Tang's, unchanged
except the freeze line and the snapshot outputs.

## Do this (same flow as the earlier kits)
1. Copy this folder into `demo-projects` next to `blinky-ypcb003381p1` (so `../openXC7.mk` is found). In the openXC7 Nix shell: `make`, then `make program JTAG_LINK="-c ft232"` (SRAM only).
   LEDs: yellow = heartbeat, green = the automatic first run delivered its 6 results, red = frozen (off after loading).
2. From a **plain terminal** (not inside the openXC7 shell), in this folder:
   * `nix shell nixpkgs#openocd --command sh freeze_read.sh` -- pure read, nothing changed (expects magic 46525A31, 6 results).
   * `nix shell nixpkgs#openocd --command sh freeze_at.sh 346` -- restart the run, freeze at count 346, read the cells. (Try 30, 100, 250, 500, 1000.)
   * `nix shell nixpkgs#openocd --command sh freeze_release.sh` -- unfreeze; the run carries on and finishes.
   * `nix shell nixpkgs#openocd --command sh freeze_sweep.sh 0 1700 20` -- every 20th count from 0 to 1700; writes `sweep.csv` (one row per cell per count).
3. Send back `freeze_*.log` and `sweep.csv`.

## Checked in simulation (not on the card)
`make sim` (iverilog): the run is frozen at ten counts; each frozen snapshot equals the state of an unfrozen copy at count T+1 (the freeze takes one clock to act); reading twice
gives the same snapshot; releasing the freeze gives the same six results and signature as an unfrozen run; a plain rerun gives the same signature.
Real BSCANE2/JTAG timing, the Update-DR handling on the chip and the reset/restart on the card are **not** checked until you run it.
