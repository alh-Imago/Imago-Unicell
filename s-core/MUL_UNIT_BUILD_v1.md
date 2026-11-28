# The multiply unit: what was built, and how to build and test it (ledger #1584)

Follows MUL_UNIT_DESIGN_v2.md. Nothing here has been built with Vivado or run on a card yet; it is tested in simulation and on the host interpreter only.

## What it is
- **RTL:** `sc_sys_v23.v` (v22 stays), parameter `MULU` (0 = no unit, the device window traps exactly as before; 1 = one multiply unit per block). With 1 a *device window* sits at byte address 0x20000: store operand A at +0, store operand B at +4, load the product (A x B, low 32 bits) from +8. Anything else in the window traps (cause code 2).
- **The refinement from design note v2 is in:** the two operand stores go straight into the slice's own registers (no wait for the slice's turn); only the product load waits for the slot. A load is held back 3 clocks after the last operand store so the operands are always settled.
- **One multiplier per block**, written as a plain 32 x 32 multiply keeping the low 32 bits; the free tools turn it into **3 DSP48E1 blocks** (checked with yosys: a 2-block build with the unit has 7 DSP48E1, the 1 that is there anyway plus 3 per block). Pipeline: operand select, multiply, result, arranged so the product is there when the slice's turn comes. 8 blocks = 24 DSP blocks.
- **Build files:** `fpga/sc_block_v7.v`, `fpga/sc_top_k7_v19.v`, `k7/make_mb_v14.py` (6th argument 1 = with unit; name prefix `hm`), `k7/stage_mb_v13.sh`, `make_manifest_v3.py` (field `mul_units`), `score_store_v2.py` (the shell reads `mul_units`). With the 6th argument 0, `make_mb_v14.py` writes the same files as `make_mb_v13.py` (checked: only the comment line differs).
- **Host side:** `jobio_ext_v1.py` (+ `jobio/lib_mul.s` software, `jobio/lib_mul_unit.s` unit): `lib_mul32` (a0 = a0 x a1, touches only a0, a1, t0, t1) is linked as the software shift-and-add version when the build has 0 units and as the unit version when it has 1 or more; header word 7 carries the unit count. The shell (v11) sets the count from the build when you `use` it. `jobiss_v2.py` models the unit so both paths are checked on the host.
  **One change from the earlier plan:** the choice is made when the program is linked (from the build's `mul_units`), not by a test at run time; that saves one shared-RAM access per multiply. The software version therefore runs on every build; the unit version on an `hm` build traps (cause 2) anywhere else, so the shell only links it when the build says it has the unit.

## Tests (all pass)
- `python3 test_sys23.py S ULW FZ NU` (iverilog): 16 products at every fusion width, alone and together, several slices multiplying at once, mixed with ordinary jobs, the real `lib_mul_unit.s` called with a jump, and the bad accesses trapping; with MULU=0 the same programs trap and ordinary ones run. Run at S=4 (1 unit), S=8 (2 units) and S=16 (ULW 3).
- `python3 test_jobio_ext_v1.py`: software and unit paths on the host interpreter (599 instructions against 9,519 for 40 words at multiplier 0xFFFFFFFF); header word 7.
- Shell v11 and window v22 tests.

## Building (on your machine, overnight)
Inside `s-core/k7` after `git pull`:
1. `python3 make_mb_v14.py 4 16 4 1 1024 1` (small first: `hm4s16u16n1i1024`), `python3 make_mb_v14.py 8 32 5 1 1024 1` (the big one: `hm8s32u32n1i1024`)
2. `S_CORE=$HOME/Imago-Unicell-score/s-core sh stage_mb_v13.sh`
3. `sh run_builds_v1.sh hm4s16u16n1i1024 hm8s32u32n1i1024` (Vivado; it never loads anything onto the card).
Look at the summary file: timing must pass before loading (never load a failed-timing bitstream). Copy the `.bit` and the manifest into your build store as you do for `hk` builds.

## Testing on the card (after a build with passing timing)
`use hm8s32u32n1i1024`, then `batch batches/mul_unit_cost.score`, then for lw 0 and lw 5 `python3 mul_unit_cost_calc_v1.py A B C LW`. Expect (an estimate, not a measurement) about 470 clocks per multiply at lw 0 and 50 at lw 5. Also run an old software batch (`batches/mul32_cost.score` on `hk8s32u32n1i1024`) to confirm the fall back is unchanged.

## Not done / open
- Fused tasks use the unit through the same signals and pass the pool tests, but a fused task multiplying in all its lanes is not a use anyone has asked for; unproven beyond the simulation.
- The unit gives the low 32 bits only (no high half, no divide). Which other cards get it (Tang Nano 20K has 48 multipliers, at most 16 units) is open.
- Timing of the new design on the Kintex is unknown until Vivado reports it. The design adds a 32-to-1 select of two 32-bit operands per block plus 3 DSP stages, none on the core's critical path as far as I can tell; the report decides.
