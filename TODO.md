# Imago UniCell — TODO

Last updated: 2026-06-03

---

## IMMEDIATE — Compiler quick wins

### Comparison against constants — massive overcount

Current: `x > 0` places INT32_LT_S (518 cells) + ternary mux = ~650 cells.
Correct:  `x > 0` is an OR-reduction of 32 bits = ~5 cells (log2 tree).

- [ ] **`x > 0` / `x != 0` intercept** — detect comparison against literal 0
      in `_compile_compare_typed`. Emit OR-reduction tree (5 cells) not LT_S tile.

- [ ] **`x == CONST` intercept** — detect equality against compile-time constant.
      XOR each bit against the constant bit (preloaded), then NOR-reduce. ~37 cells not 864.

- [ ] **`x > CONST` / `x < CONST` general case** — still needs LT_S tile but
      constant broadcast can be preloaded at compile time. No runtime forward sim needed.

### Branch between constants — MUX overkill

- [ ] **Constant-branch optimisation** — in `_compile_if`, detect when both
      branches return `_broadcast_constant` values. Emit direct preloaded
      selection, not MUX tile.

### INT32_MUL — optimise using packed shift-chain and nibble shift bits

Current MUL: shift-and-add, 2915 cells, depth 120. Correct but large.

- [ ] **Rewrite MUL inner accumulator** using packed shift-chain adder
      (~19 cells per add vs 32 ripple cells). Target: ~650 cells total.
      Depends on `make_int32_add_packed()` tile existing first.

- [ ] **Exploit shift_in_en / shift_out_en (bits C/D)** once Verilog lands.
      Partial product placement becomes zero extra cells — shift_out_en
      positions each partial product at the correct bit offset automatically.
      Enables Wallace tree: depth drops from ~120 to ~20, cells to ~500.
      See `packed_shift_adder.py` for methodology and chain plans.

- [ ] **Make `make_int32_add_packed()` tile** — wrap packed_shift_adder.py
      reference model as a proper fp_tiles Tile. Verify against INT32_ADD
      test cases first, then use as MUL accumulator.

- [ ] **Reminder: nibble shift bits useful beyond MUL** — shift_in_en /
      shift_out_en apply to any operation needing aligned data on the bus:
      byte/nibble extraction, fixed-point scaling, packed word ops.
      Check these before adding shift cells to any new tile — may be free.

### Packed shift-chain adder — integrate into compiler

- [ ] **Add packed adder as selectable path** in `compile_int32_function`.
      Flag: `cell_budget='tight'` → packed (19 cells, 15 ticks).
            `cell_budget='fast'`  → wide KS (482 cells, 5 ticks).
      Default: wide KS (existing behaviour).

---

## IMMEDIATE — Verilog / Silicon

### New gate_state bits (iCEBreaker bring-up)

- [ ] **a_preload_en (bit A)** — cell self-loads a_data from a_preload_val at CMD_RECONFIGURE.
- [ ] **a_preload_val (bit B)** — 0 = load 0x00000000, 1 = load 0xFFFFFFFF.
- [ ] **shift_in_en (bit C)** — incoming bus data shifted by nibble_set before gate tree.
- [ ] **shift_out_en (bit D)** — output shifted by nibble_set before emission.
- [ ] **Verilog update** — add above four bits to unicell.v cmd_latch decode.
- [ ] **`one_shot` and `loop` bits** (bits 30–31) — add to `unicell_v3.v` with testbench.
- [ ] **Pre-register `bus_hit`** — fan-out prep for Kintex-7 large arrays.
- [ ] **SYNC_WAIT test on iCEBreaker** — 4-cell topology, confirm two-arrival model.

---

## KINTEX-7

- [ ] **Top-level skeleton** — Kintex-7 wrapper around cell array.
- [ ] **Scale test** — confirm cell count budget for 150k cell target.

---

## COMPILER — Known bugs

- [ ] **MUL preloaded_a normalisation** — 0/1 values reach XOR cells as single bits
      not 0/0xFFFFFFFF. Moot after a_preload_en lands.
- [ ] **Output padding uses bare GS_PASS** — should be GS_PASS | GS_LATCH_IN.
- [ ] **Duplicate `compile_int32_function`** — dead definition at line ~136. Clean up.
- [ ] **`if x:` (int32 as bool)** — use explicit `x > 0` until OR-reduction intercept lands.
- [ ] **Multi-param MUX passthrough** — first int32 param excluded from re-injection.
      Workaround: put non-passthrough param first.

---

## SENTINEL / WARD / SHORE — Architecture rethink

- [ ] **3-cell Sentinel** — in-counter, out-counter, compare (holds depth in a_data).
- [ ] **Ward** — reads PTT table only, Python loop, no cells.
- [ ] **Shore** — tables + address space only.
- [ ] **Companion scan loop** — Tier 3, lives in Shore pond reserved region.
- [ ] **Clean up sentinel_core.py / ward_core.py / shore_core.py** — superseded.

---

## BOOTLOADER

- [ ] **`.isi` round-trip test** — compile → write → load → verify cells match.
- [ ] **`.isi` loader in Verilog** — SPI/UART receiver, streams to CMD_RECONFIGURE.
- [ ] **Bootloader test on iCEBreaker** — 3-cell sentinel .isi, verify PTT.
- [ ] **Update bootloader tests** — `test_icms.py` tests old arch, update to 3-cell sentinel.

---

## TESTS

- [ ] **SYNC_WAIT hardware test** — `tests/fpga/` needs `pyserial`.
- [ ] **Add comparison random fuzz to test suite** — 300/300 passing but not in suite.
- [ ] **Add load/run API test** — all 8 ops, currently manual only.

---

## RESOLVED THIS SESSION ✓

- ✅ **BranchPoint.build() API mismatch** — verified working, 56/56 tests. Was already fixed.
- ✅ **Comparison + ternary operator** — 5 root-cause bugs fixed, 300/300 random.
- ✅ **Signed comparisons** — INT32_LT_S wired in, 300/300 signed+unsigned.
- ✅ **load(A)/run(B) API** — 3 bugs fixed, all 8 ops 100/100 random.
- ✅ **Packed shift-chain adder** — 19 cells vs 482, methodology + tests committed.
- ✅ **Debian dev box** — SSH, Samba, repo, Python stack all working.
