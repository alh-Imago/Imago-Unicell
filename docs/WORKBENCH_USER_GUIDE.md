# The Workbench: a plain guide (current page: `nano/workbench_v7.py`)

Written 20 Oct 2026 (ledger #1302) from what was built and tried on 19 Oct (#1294-#1300). Everything here was seen working in a real browser; items marked *not tried* were not.

A 34-second clip of the grid running (CORDIC under a simulated-card SHAPE) is at `docs/media/workbench_v7_demo.mp4` (and `.webm`); it is also embedded in the Workbench tab of `docs/teaching_manual.html`.

## Start it

```bash
python3 nano/workbench_v7.py        # opens http://localhost:7420
```

The Workbench runs the UniCell virtual machine (the VM) in your browser. It is a separate web page from the front panel (the Bench) that drives the card; the two do not share a server.

## The four tabs on the left

| Tab | What it is for |
|---|---|
| **Target** | Optional. Make the grid a checked reflection of a real card: either from a MAN file plus a cell count, or from the card's own SHAPE (`card.shape.json`, written by the Walker). Leave it unset for free mode. |
| **Load / save** | Load a design: the **File** drop-down lists what the server finds (the repository's `nano/examples`, the folder you started in, uploads). **Browse...** opens your computer's file picker; a picked design loads at once (`.icm` through Load .icm, any other `.json` through Load hierarchical design). |
| **Program** | Type or load a small program (DSL or Python) and compile it onto the grid. |
| **Run** | Step, Step 10, Refresh, **Reset** (back to tick 0 with the design as loaded), Auto-play at a ticks/sec rate, Pause, and Deliver (put one value into one cell). |

## Using it with the real card (the sequence that worked)

1. **Walk the card first, in the Bench** (the front panel): Check OpenOCD **once** before anything else on the card side, then Load the folder's bitstream into the card (Build, then Load), then **Walk the card**. Seen on 19 Oct: the Walk button ran only after Check OpenOCD had been used (cause not confirmed). A card with nothing or another design loaded shows magic 00000000 or "IS NOT this folder's design", and no SHAPE is written. Folders made before the v6 Bench have no Walk button; make a new folder.
2. The Walk writes `card.shape.json` in that card build folder (for example `~/openFPGALoader/build/demo-projects/<folder>/card.shape.json`).
3. **Workbench, Target tab:** pick that `card.shape.json` under "From the card's own SHAPE" and press **Use as target**. The status line should say "Card SHAPE target" with the cell and connection counts. The tiles turn copper (Flex).
4. **Workbench, Load / save tab:** pick the design the folder was built from (for CORDIC, `cordic_z_convergence_v2.icm-hier.json` in the drop-down) and press **Load hierarchical design**. The Workbench checks the design against the card: every cell and connection must exist on the card, and it reports any connection the card has not yet shown a word crossing.

Other files in a card build folder (`ASSEMBLY.json`, `design.json`, `design_map.json`, `expected.json`, `kit.json`, the large `k7_icm_..._flex.json`) are build records. They are not loaded in the Workbench.

With CORDIC the simulated card gives 40 design cells and 36 + 4 on the card: 4 design cells are **absorbed** (the generator folded the entry merges into their branches) and 4 **card-only** merge cores exist only in the hardware. *Your own card's counts: not yet seen in the Workbench.*

## Reading the grid

- **Background colour** = cell family: Std (green), Carrier (purple), Flex (copper), Sub (teal), Sub.bridge (grey). With a card SHAPE as target everything is Flex; a design that names a family colours by it.
- **Inner colour and letters** = core type (ADD adder, BR branch, RAM, and so on; the legend has them all).
- **Arrows** on a tile's edges: copper = out, blue = in. Click a tile for its details (the details are kept to the side and only shown for the clicked tile).
- **Gold glow** (flash) = a data value changed on the last tick. **Magenta glow** = logic or configuration changed (a field whose name says mask, mode, direction, route, select, sequence, scheduling, subtract, add-on, latency or width). Running data through a design normally changes no logic, so magenta is rare.
- **Steady soft glow** = the cell holds a value (a valid flag is set).
- **Gold dots** run along the arrows from a cell whose data changed to the neighbour that accepts it. They show per-tick change, not a traced value.
- **Click a tile:** the cells its output reaches are outlined with a dashed trail and dashed arrows; click it again to clear. The trail follows the arrows as drawn, it is not a measured data path.
- **Dashed outline** = absorbed in the card build (the VM runs it, the card has no separate cell). **"+1" badge** = the card also has a cell at this site that the design does not. **Dashed placeholder tile** = a card-only cell at a site the design does not use (built, but no design has exercised it yet).

## Limits to know

- The VM runs every cell in its standard mode; the family colour is shown, not simulated (a fixed-latency sub block cannot be expressed faithfully).
- The mirror runs in the VM's own cell model. A flat DSL or flat ICM program is refused under a card SHAPE target; only the card's own hierarchical design (or one that fits it) loads.
- Sub.bridge tiles rarely appear: the VM has no bridge cells (the assembler inserts them when it builds).
