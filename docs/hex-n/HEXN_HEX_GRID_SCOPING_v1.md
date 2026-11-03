# Hex-N on the hex grid (six faces) - scoping v1 (3 Nov 2026)

Decision (Alan, 15:04): go with the hex grid; it reframes the layout and the routing options change with it. Nothing below the "done" line is built yet.

## Prior art read first
- `sub/verilog/hexn_grid_v1.v` (2 Nov 07:10): R x C hex cells, odd-r layout (odd rows shifted half a cell right), six faces E W NE NW SE SW.
- Ledger 2 Nov 08:20: the work/routing split on the hex lattice by a 3-colouring: one cell in three is a work core, every work core has six routing neighbours, every routing cell touches three work cells and three routing cells. Marked "not tested" at the time.
- `docs/hex-n/HEXN_ASSEMBLER_SCOPING_v1.md`: routing cell measured (yosys, synthesis only): 4 faces data+flag 24 slots, 6 faces data+flag 59 slots.
- The tile RTL already has a FACES parameter ("6 reserved"); the exporter and VM refuse six faces today; the planner is square (`hexn_wrgrid_v6.DIRS` = N E S W).

## Done today
- `tools/hexn_hexgeom_v1.py`: odd-r neighbours, face numbering 0 E, 1 SE, 2 SW, 3 W, 4 NW, 5 NE (opposite = face + 3), 3-colouring, work cells.
- `tests/vm/test_hexn_hexgeom_v1.py` (3 pass): neighbours symmetric and distinct; work cells never adjacent and have six routing neighbours; routing cells touch 3 work + 3 routing; work density about one third. This turns the 2 Nov geometry statement into a tested one.
- Work cells in a square n x n layout vs the hex layout: 7 -> 9 vs 18; 9 -> 16 vs 27; 11 -> 25 vs 44; 13 -> 36 vs 59.
- All eight tiles (UN, AL, JN, BR, MG, PR, SQ, LT v2) elaborate and synthesise in yosys at FACES = 6. Flip-flop counts rise by 8 to 10 per tile at six faces (extra output registers and config bits). LUT counts were NOT extracted in this pass. Behaviour at six faces is NOT tested.

## What changes, layer by layer
1. **Tiles (RTL).** FACES = 6 already elaborates. The face roles are fixed to four faces in the packers (`FACE = N E S W`) and in the planner (priority reads W N S, latch set W / clear N / toggle S, sequencer advance W, joins W and N). The tiles' own select fields are generic (3 bits, index 6 and 7 free), so the work is: re-run each tile's testbench at six faces, and let the planner choose which face plays which role. A priority tile can then take four or more inputs.
2. **Planner.** New hex Grid class (six directions that depend on row parity); routing graph where each routing cell has 3 work and 3 routing neighbours; work-cell positions from the 3-colouring. The word-level twins and tick model are unchanged (one clock per hop); only path lengths change. Placed-cost calibration must be repeated (routing cell about 59 slots at six faces against 24 at four).
3. **Pattern generator and assembler.** Top-level wiring by parity-dependent neighbours; chain order row-major; pad rows on the edge need a rule (see questions).
4. **Exporter and VM.** Lift the six-face refusal: a new program format version (icm-hexn-v4) carrying faces = 6; VM on the hex grid.
5. **Frame / host.** No protocol change expected (row numbers 1..16); to be confirmed with the pad rule.
6. **Regression.** The existing programs (join, branch, merge, priority, sequencer, latch, holds) re-planned on the hex grid should give the same WORDS; ticks differ by path length. That is the board test: hex card vs hex VM, same method as before.

## Build order (each step tested before the next)
H1 geometry (done) - H2 tiles at six faces with testbenches - H3 hex planner + VM (simulation only) - H4 generator, exporter, assembler - H5 one hex 7 x 7 card in simulation - H6 real board.

## Open questions for Alan
1. Face numbering: clockwise from E (proposed above) - fine?
2. Pads: inputs on the west edge and outputs on the east edge as now (on a hex edge a west-edge cell has up to three outward faces: W, NW, SW)? Which face does a pad use?
3. First hex size: 7 x 7 (49 cells, 18 work cells) is the natural comparison with today's cards.
4. Fit: arithmetic only, not a build: 18 work cells and about 31 routing cells at 59 slots is roughly 1,800 slots of routing before the work cells and the frame; it should fit the Tang Nano 20K, but a mix of branch and priority tiles needs a real placement.
