# points.md — ACTIVE part (currently entries #946 onward)

**This is the real, currently-open tail of the single, canonical
points.md ledger — the file new entries get appended to.** Split
across multiple files purely because GitHub won't render a file over
~512KB in the browser (the single combined file had grown past 2MB);
no entry content was changed, reworded, or reordered. See `points/
INDEX.md` for the full real map of which part holds which entries,
and `points.md` (repo root) for the short, canonical pointer every
session should still start from.

**Naming convention, for future-me:** this file keeps the stable name
`points_active.md` (no entry range in the filename) for as long as
it's still being appended to, so appending never requires a rename.
Once it approaches ~350KB, seal it — rename to `points_NN_XXX-YYY.md`
with its real final range, start a fresh, empty `points_active.md` for
continued work, and add the sealed file's own row to `points/INDEX.md`.

---

## 946. THE LEDGER IS SEALED THROUGH #945: `points_active.md` (1,600,122 bytes, 373 entries, #572-#945) is now sealed as parts 7-11, and this file starts fresh at #946. Lossless, proven; three pre-existing numbering anomalies recorded, not "fixed".

Alan: "while there is space left, move this current record and archive it, so we can start a new one." This is the procedure in `current/START.md`'s close-out checklist (item 4) and `points/INDEX.md`: seal at entry boundaries only, never edit content, name each part `points_NN_XXX-YYY.md` with its real range, add rows to the INDEX, start a fresh `points_active.md`.

**Why five parts, not one:** the file was 1.6 MB against the ~350 KB sealing threshold (GitHub stops rendering past ~512 KB). The six earlier parts are each ~350 KB, so it was cut into five balanced parts at entry boundaries (317-323 KB each).

| Part | File | Entries | Range | Size | sha256 |
|---|---|---|---|---|---|
| 7 | `points_07_572-652.md` | 81 entries | #572-#652 | 323,451 bytes | `9929f9f0775db5798dd9f66afe7bce08fb15e09bbff2ec304306e1b27cc4c26e` |
| 8 | `points_08_653-735.md` | 83 entries | #653-#735 | 319,611 bytes | `5849f7f96ca469b4daffaf81fd3795b10f3659d93c887fcc93c42cd2f494fbed` |
| 9 | `points_09_736-810.md` | 75 entries | #736-#810 | 322,358 bytes | `95fafa910e1af4993e03785514e707bc9ea9dd8d1dcdc8efbd6caae7b3eb21e2` |
| 10 | `points_10_811-874.md` | 65 entries | #811-#874 | 317,213 bytes | `0f90f88551ebcb06b4577020cfe6f41bb2213aae2f29cb4c9f314ed3dc6b55d4` |
| 11 | `points_11_875-945.md` | 69 entries | #875-#945 | 319,314 bytes | `7a28f3da76a09f4310684d114c7f359232e1c25b37fcef7008f4300549a72e2c` |

**Lossless, proven before anything was replaced:** the entries of the five new parts, concatenated, are byte-identical to the original file's body (everything after its header): original sha256 `7a7e864680b077820f2bce606d8b14c52a8275f803d82450d361b8d27a5c2b5b`, 1,600,122 bytes. Only each part's own header line was added (`# points.md -- part N of 12 (entries ...)`, in the same words as the earlier parts). The unsplit file is also recoverable from git: `git show 0f9595a:points/points_active.md`.

**Three numbering anomalies already in this range -- recorded in the INDEX, left exactly as they are (the ledger is append-only):** #824 is used TWICE (two different entries, both in part 10); #893 and #902 were never used (skipped numbers, in part 11). The earlier anomalies (#191-#201 after #202-#203; #394 used twice) are unchanged.

**What else changed (documents only, no ledger entry touched):** `points/INDEX.md` (rows for parts 7-11, the active row now `#946 onward`, the anomalies, and a new catch-up paragraph, since the fresh active file is nearly empty and the real recent work is now in part 11); the root `points.md` pointer; `current/START.md`'s catch-up line; and the few docs that cited specific entries as living in `points_active.md` (`current/PLAN.md` for #827 and #596 and others, the DSL manual and `llvm_ir_compiler_scope.md` for "#612 onward") now name the part that holds them. The older sealed parts' headers still say "of 7" -- left unedited, as sealed parts never are; there are now 12 parts counting this one.

**Not done:** a session archive under `archeology/sessions/` (START.md close-out item 8, "if the session was substantial") -- a separate step Alan has not asked for; no `.onion` packing. The next entry is #947.


## 947. FLEX ICM GENERATION, STAGES 3-4: NANO AND COMPARATOR. ALL 41 corpus programs now run on flex, each verified under streams with stalls and forced operand orders. A VM finding on negative comparator thresholds.

Alan (a new week): "lets get into the nano on flex and move through the field of cores."

**Nano (stage 3) -- the first core whose two operands are NOT symmetric.** Read from `nano_cell_v4sa.v`: the HELD operand A is only a LOAD STROBE (`load_hold` overwrites the held register on any edge, with NO handshake and regardless of `pending`); the FLOWING operand B is the ordinary valid/ready; the gate reads the held register's CURRENT value at capture, so a hold loaded on the same edge is not yet visible (the "A one cycle before B" rule of #932). The emitter adds ONE flag per nano, `aload` = "A is loaded for the current pair": A's ready is `~aload & armed` and the load is `vA & ready` (allowed while the previous result is still pending, so the next pair's setup overlaps the drain); B's ready is `aload & ack_out`, and its capture clears `aload`; `armed` = `ack_out | valid_out` (derivable from the cell's own outputs). **Arrival ORDER no longer matters** -- a B that arrives first just waits -- which is why a handshake design needs none of sub's padding. A source feeding both operands works through the existing eager fork (A is taken first, B a cycle later).
**Comparator (stage 4):** `compare_cell_v4sa` is a single-input cell (signed(data) >= threshold -> 0/1, threshold in `cfg_data`), so its handshake is exactly a relay's; a handful of lines.

**Verified (`tests/test_flexsub_flex_v1.py`, 51/51; was 33):**
- **THE CORPUS: all 41 of 41 programs are accepted on flex** (was 20 after constants, 31 after nano), each 12 items x 3 modes (plain, random stalls, heavy stall) == plain arithmetic, 18 of them using constants. The four signed-compare programs (`icmp_slt/sgt/sle/sge`) apply the corpus's OWN rules (arithmetic is the oracle only where the stock compare lowering's subtraction does not overflow, #931; vectors filtered by `no_overflow`) and are ALSO checked against the real VM on the 8 overflow-boundary vectors, where arithmetic is not the oracle: all agree.
- **Nano, dedicated:** `and`, `or`, `xor`, `and_c255` (a constant operand), a 3-nano chain, a REAL FORK feeding a nano, `add_then_xor`: each 16 items x **6 modes** -- plain, two random-stall seeds, heavy stall, and **two order-forcing skew modes (first input slow, last input slow) that force B-before-A and A-before-B arrivals deliberately** rather than by luck. All correct, in order.
- **Mutation controls on the `aload` glue, all caught:** B captured without waiting for A (a stale hold is read); A re-loaded when already loaded (the hold overwritten before B); the capture never clears `aload`.
- **Comparator, dedicated:** a hand-built relay -> comparator -> exit at thresholds 0, 5 and -5 over 12 probe values incl. INT_MIN/INT_MAX around each, 3 modes each; thresholds 0 and 5 also == the real VM; a zeroed-threshold mutant is caught.
All 14 suites pass: flex 51; generator 37; loops 9; addon 21; level 16; sequencer 20; branch 19; merge 17; netlist 12; compile 13; corpus 47; family equivalence 36; assembler 76; mul 38.

**A FINDING about the VM (a core-part cascade item; NOT patched):** at threshold -5 (0xFFFFFFFB) the flex hardware matches a true SIGNED compare on all 12 probe values, but the VM returns 0 for EVERY value. The VM declares `cmp_threshold: int = 0  # signed` but loads it raw -- `cell.cmp_threshold = cfg.get("threshold", 0)` -- and the ICM v3 `threshold` field is an UNSIGNED 32-bit field (bits 8-39), so a two's-complement negative threshold is read back as 4,294,967,291 and `signed(data) >= 4294967291` is false for every possible value. The RTL cells declare `reg signed` (flex: `reg signed [WIDTH-1:0] threshold`; sub: `reg signed [31:0] threshold`, both read, the sub one not tested), so the RTL agrees with the VM's own COMMENT about what the field means. The stock compiler only emits non-negative thresholds, so nothing in the corpus exercises it; recorded as a test that asserts the VM's behaviour (it must be revisited if the VM changes). VM catch-up item (#927).

**Mistakes of my own, caught by running:** my first corpus sweep after enabling nano crashed because the reference lambdas call a helper (`s32`) defined in the corpus test file, which refused programs never reached; and my first comparator test assumed the VM would agree at a negative threshold -- it did not, which is what surfaced the finding above.

**Not done / limits:** merges, branch, accumulator, latch and the ack-driven sequencer on flex, and level sources; the streaming tests check VALUES and ORDER, not throughput (the nano's overlap of the next A-load with the drain is a design choice not measured here); nano is checked against arithmetic and (through the compare programs and the thresholds) the VM, but there is no nano-vs-VM single-item comparison on flex like the sub corpus has; width fixed at 32; no flex place-and-route; the hand-built `cordic` still needs the branch and merges; the VM catch-up (#927) and the deferred no-size fallback stand. Nothing has run on silicon.


## 948. ASIDE (Alan): "the nano logic shrinks to fit the current 18-bit target, not remaining at the original 32-bit?" MEASURED: the cells CAN shrink -- but the `--icm` path does not use it yet, the sub cells have no WIDTH parameter, and a much BIGGER saving turned up: the nano's topology is a runtime register, which costs ~28x more than a fixed one.

**Method:** `yosys synth_gowin` per cell, `chparam WIDTH` 32 vs 18; synthesis only, no place-and-route, no silicon. Reproducible: `python3 tools/measure_cell_width_v1.py`.

**1. Width: flex (v4sa) cells shrink; the ICM path does not use it.** Every flex cell carries a `WIDTH` parameter; almost every sub (v4s) cell does NOT (only the accumulator does), so the sub cells are hard-wired to 32 bits. And both ICM emitters (`flexsub_icm_generate_v1`, `flexsub_icm_flex_v1`) contain zero mentions of `WIDTH`: designs from `--icm` are 32-bit whatever the card's `native_width: 18` says. (Only the older step-1 chain assembler honours `-w` / the MAN width, #921.) Measured, 32 -> 18 bits [LUT1-4 / ALU / DFF]:
| flex cell | W=32 | W=18 |
|---|---|---|
| ram | 39 / 0 / 35 | 25 / 0 / 21 |
| **nano** | **1,088** / 0 / 76 | **626** / 0 / 48 |
| comparator | 28 / 32 / 35 | **86** / 18 / 21 |
| adder | 37 / 32 / 35 | 23 / 18 / 21 |
| mul (LUT) | 4,257 / 32 / 34 | **1,045** / 18 / 20 |
So the nano shrinks 42% in LUTs (37% in flops); the adder and relay roughly 40%; the LUT multiplier ~75% (it is quadratic in width). **An oddity, unexplained:** the comparator's LUT count goes UP at 18 bits (28 -> 86; LUTs + ALUs 60 -> 104) -- yosys maps the 18-bit signed compare differently; worth a look before relying on it.

**2. The bigger saving is not the width. The nano costs 1,088 LUTs -- about 34 per bit -- for what is one two-input gate per bit, because its topology is a REGISTER loaded at configuration, so synthesis cannot fold it and every bit carries a full 12-way selector.** A scratch copy with the topology pinned as a CONSTANT (what a fixed, generated design could use), for each of the 12 implemented topologies [LUT1-4 / DFF]: at W=32: pass A 6, pass B 5, NOT A/NOT B/NOR/AND/OR/NAND/XOR/XNOR **37-38**, const 0 4, const 1 5; at W=18: 4-24. So a fixed nano is **~38 LUTs at 32 bits (about 1 per bit) instead of 1,088, and ~24 instead of 626 at 18 bits** -- roughly 28x and 26x smaller, against 1.7x from the width alone; both together ~45x. (Gate names derived from the cell's own gate network: g0 = ~A, g1 = ~B, g2 = A&B, g3 = NAND, g4 = NOR, g5 = OR, g8 = XNOR, g9 = XOR. The register version is the true RECONFIGURABLE nano -- the architecture's point; the pinned version is only for a design that is fixed at generation time, i.e. what sub and the generated flex designs are, and the same logic as Alan's #939 ruling that mask/shift/invert become wiring once the variant is fixed.) The same question applies to the other configurable cells -- the comparator's threshold register, the adder's subtract-mode bit -- not measured here.

**What 18 bits would change, if the ICM path gained a width (not done):** the data nets, constants, thresholds and add-on maps all truncate to W bits; results wrap at 2^W; the sign bit is bit 17; the stock compare lowering's no-overflow domain (#931) shrinks accordingly; the add-on shift taps are defined on 32-bit lanes; and THE VM IS 32-BIT ONLY, so at 18 bits the oracle becomes arithmetic mod 2^18, not the VM (the VM width parameter is already on the #927 catch-up list). At 18 bits a `mul` could also use the MULT18X18 primitive exactly (the MAN now lists it, 0.25 block per instance = 48 instances on the Tang, versus 12 MULT36X36), so the multiplier ladder would change too.

**Not done:** nothing in the generators changed -- this entry is measurements and a tool. No width parameter on the `--icm` path; no pinned-topology nano; no comparator/adder-config measurements; the comparator anomaly is not investigated.


## 949. CORRECTION TO #948, and a real finding: the comparator "anomaly" is the synthesis MAPPER, not signing and not width -- and the default `synth_gowin` flow wastes resources that `-nowidelut` does not. Real place-and-route confirms it.

Alan, on the comparator getting bigger at 18 bits: "that may be something to look into ... you would have thought the reduction would have been universal, may be a signing issue, not sure." He was right that it should shrink; he was right to ask; the cause was not where either of us expected.

**The comparator investigation (`compare_cell_v4sa`, synth_gowin):**
- **Not signing.** A scratch copy with `$signed` removed shows the SAME pattern as the shipped cell at every width.
- **The 18-bit cell is not the odd one -- the 32-bit cell is.** LUT1-4 by width (default flow, signed): 8 -> 12, 12 -> 20, 16 -> 50, 17 -> 63, 18 -> 86, 20 -> 90, 24 -> 110, 28 -> 134, then **31 -> 30 and 32 -> 28**, 33 -> 76, 36 -> 41. About 4.5 LUTs per bit, collapsing at 31/32. So "32 -> 18" compared against the one width the mapper happens to handle well.
- **Not the RTL.** Before technology mapping the netlist is IDENTICAL at 18 and 32 bits (20 cells, one `$alu`). After mapping, the default flow builds a large tree of `LUT1` and `MUX2_LUT5/6/7/8` cells at most widths (73 MUX2 at W=18) but not at 31/32.
- **`-nowidelut` (no wide-LUT muxes) makes it smooth and monotonic:** 17, 19, 22, 28, 35 LUTs at W = 16, 18, 24, 32, 33. At 18 bits the comparator is **19 LUTs against 28 at 32 bits: a real 32% shrink**, with the ALUs 32 -> 18. The universal reduction Alan expected is there.

**A CORRECTION to my own #948, which this exposed. Three of its claims were wrong or misleading:**
1. **My LUT counts excluded the `MUX2_LUT` cells.** In the default flow the nano is 1,088 LUT4 **plus 814 MUX2** (not just 1,088), and the LUT multiplier is 4,257 LUT4 **plus 3,411 MUX2**. With `-nowidelut`: **256** and **1,332** LUT4, no MUX2. Those #948 figures were inflated by the mapper.
2. **"The nano's runtime topology register costs 28x" is overstated.** Against the fair `-nowidelut` baseline (256 / 158) the pinned nano (38 / 24, the same in every flow) is **6.7x / 6.6x** smaller, not 28x / 26x. **And it does not apply to generated designs at all:** a whole generated flex `and` design (one nano) is ~50 LUTs in total, because the generator feeds the cell a constant `cfg_data` and synthesis folds the always-zero topology bits itself. The register cost is real only for the standalone configurable cell.
3. **The comparator "unexplained anomaly" is explained** (above).
What HOLDS: the width shrink 32 -> 18 in BOTH flows -- nano -42% (default) / -38% (-nowidelut); LUT multiplier -75% / -70%; adder -38%; ram -36%; comparator -32% (-nowidelut). And the finding that the flex cells carry `WIDTH` while the sub cells (all but the accumulator) do not, and that both `--icm` emitters hard-code 32 bits.

**THE REAL FINDING: the synthesis flag.**
- **Whole generated designs, synthesis only (32-bit):** the 3-multiplier + 2-adder sub design is **12,982 LUT4 + 10,236 MUX2** in the default flow versus **4,195 LUT4** with `-nowidelut` (3.1x); a flex `abs` design 400 + 58 MUX2 versus 355; a flex `and` design 52 + 4 versus 49. ALUs and flops are identical.
- **Real place-and-route (nextpnr-himbaechel, GW2AR-LV18QN88C8/I7 -- the Tang part, 27 MHz target), cells wrapped with an LFSR and one LED pin:**
| cell | flow | LUT4 | MUX2 | Fmax |
|---|---|---|---|---|
| LUT multiplier | default | 4,343 | 3,412 | 75.05 MHz |
| LUT multiplier | `-nowidelut` | **1,418** | 0 | **231.75 MHz** |
| nano (register topology) | default | 1,399 | 1,104 | 300.12 MHz |
| nano (register topology) | `-nowidelut` | **277** | 0 | 232.07 MHz |
For the multiplier `-nowidelut` is **~3x smaller AND ~3x faster** (the wide-LUT mux trees are slow as well as big); for the nano ~5x smaller at the cost of clock speed (300 -> 232 MHz, both far above 27 MHz). **Caveats, stated plainly:** one run per config (no seed sweep); Fmax is nextpnr's own estimator against a modest target; a wrapper, not a full design; not silicon. Strong evidence, not proof.

**Tools (reproducible; the real-P&R tool reproduces my manual runs exactly, which shows it is faithful, not that the result is robust across seeds):** `tools/measure_cell_width_v1.py` (REWRITTEN: now counts MUX2 and runs both flows; #948's version was the misleading one) and `tools/measure_synth_flow_v1.py` (new: real P&R, default vs `-nowidelut`).
**Spreadsheet** `width_and_nano_cost_measurements.xlsx` was rebuilt (73 formulas, 7 sheets, the values re-verified): both flows with MUX2 counts, the pinned-vs-register factors against both baselines, the real P&R table, whole designs, the comparator sweep, width coverage, and an explicit "Corrections & open items" sheet. (My first attempt crashed on a bad line and the "success" it printed was a recalc of the OLD file; I caught it by the formula count, rewrote the script, and fixed a second error -- a colon in a sheet name -- before delivering.)

**DECISION for Alan (not made):** adopt `-nowidelut` in the generated `.ys` scripts? It would change the build flow of every generated design and the multiplier budget constant (`LUT_MUL_LUT4 = 4277` in `flexsub_icm_generate_v1.py` is the DEFAULT-flow measurement; ~1,332 under `-nowidelut`), and trade some clock speed on logic-heavy cells like the nano for large area savings. A seed sweep and a full-design P&R would firm up the evidence first. Nothing in the generators changed.

**Not done:** adopting the flag; a seed sweep; a full-design P&R; the width parameter on the `--icm` path; the other cells' configuration registers; nothing has run on silicon. **Next, as Alan directed ("continue with the other cells in order"): the flex level sources (accumulator, latch), then branch, merges, sequencer.**


## 950. THE `--nowidelut` SYNTHESIS FLAG: built, tested, and measured across ALL THREE families (sub, flex, and the original nano family). It cuts area in every family; it costs clock speed on some cells. Default left OFF pending Alan's decision.

Alan: "yes, for the flex, and maybe all of the designs this may be a flag that needs to be initiated, though you would have to test and see if it makes a difference on the nano and sub designs too."

**The flag.** `--nowidelut` writes `synth_gowin -nowidelut` into the generated build script for `-s flex` and `-s sub`, in all FOUR Gowin generator paths (the step-1 chain assembler for both families, and the sub and flex `--icm` emitters), and records `synth_flags` in each `ASSEMBLY.json`. **Off by default; the default build is byte-unchanged.** **Refused on the original nano/Quartus path** (`project_assemble_v1.generate_yosys_script` targets `synth_intel_alm`, which has no such option, so it would be silently ignored -- it is refused with that reason instead). Test `tests/test_flexsub_synthflag_v1.py` (9/9): the flag reaches the `.ys` and the record in every path and is absent by default; the Intel path refuses it; and it REALLY changes the netlist (sub nano cell 1,558 LUT4 + 1,303 MUX2_LUT -> 332 + 0; flex nano 881 + 742 -> 185 + 0). The test caught one omission of mine: the `--icm` sub generator was not recording the flag.

**Does it matter beyond flex? YES, in every family (synthesis only, one cell each; raw logs in `docs/measurements/nowidelut_sweeps_950/`).**
- **sub (v4s), 16 cells:** total LUT4 13,000 -> 4,376 (3.0x). Nano 1,558 -> 332 (4.7x); LUT multiplier 3,685 -> 1,118 (3.3x); shifter 3,303 -> 1,099 (3.0x); comparator 55 -> 22 (2.5x); router 1.5x.
- **flex (v4sa, WIDTH 32), 13 cells:** total 5,924 -> 1,894 (3.1x). Nano 1,530 -> 297 (5.2x); multiplier 3,657 -> 1,088 (3.4x); router 81 -> 26 (3.1x); comparator 2.3x.
- **original nano family (v4 cells, as built, shifter included), 9 cells:** EVERY cell smaller, 1.16x-2.86x (mul 7,015 -> 2,454; nano gate 3,898 -> 1,672; branch 3,036 -> 1,237; adder 2,348 -> 1,130); with the shifter stubbed out ("lean") 1.15x-3.66x. This family's numbers are the ones `nano/card_fit_v1.py` records (default flow): with the flag they would be roughly HALF -- a cascade item, not changed.
- Small cells (adder, mask, ram, shift_stage, mul_dsp2) are roughly neutral in synthesis: LUT4 can rise by ~18 while 16 MUX2 cells disappear.

**Real place-and-route (nextpnr, Tang part GW2AR-LV18QN88C8/I7, 27 MHz target; 22 cells, each wrapped with registered LFSR inputs and one LED pin):** total LUT4 14,793 -> 5,129 (2.9x) -- smaller in EVERY cell. **Fmax is MIXED:** faster or equal with the flag: LUT multiplier 3.05x (sub) / 1.80x (flex), accumulator +12% / +19%, latch +21%, router +15%, ram/mask/shift_stage ~1.0 (sub). SLOWER with the flag: nano 0.40x (sub) / 0.36x (flex), comparator 0.51x / 0.38x, sequencer 0.55x / 0.66x, flex branch 0.81x, flex mul_dsp 0.61x, flex ram 0.67x, flex shift_stage 0.65x. **Context:** even the slowest flagged result is ~225 MHz, about 8x the 27 MHz target; and many default-flow readings sit at EXACTLY 616.9 MHz, which looks like an estimator ceiling, so those "losses" compare against a capped number. **No Fmax at all for 7 cells** (sub adder, branch, shift; flex adder, latch, mask, router): nextpnr reports "no interior timing paths found" -- reported as unavailable, not guessed.

**Mistakes of my own, all caught:** (1) my FIRST place-and-route sweep built each bare cell with its ports as IO, so nextpnr timed only register-to-register paths and reported impossible clocks (up to 1,493 MHz); I recognised the artifact, discarded that Fmax column and rewrote the tool to wrap each cell automatically (inputs from a registered LFSR, outputs XOR-reduced to one pin) -- only its utilisation survived; (2) the first flex synthesis sweep generated nothing (I had not passed the width the assembler requires); (3) the `--icm` sub record omission above; (4) process slips (a wait loop longer than the tool's limit; a `pkill` that matched my own shell).

**What this does NOT show:** single runs, no seed sweep; wrapped single cells, not full designs (the earlier full-design result -- a 3-multiplier design 12,982 LUT4 + 10,236 MUX2 -> 4,195 -- is synthesis only); yosys 0.33; nothing on silicon.

**DECISION for Alan (open):** should `--nowidelut` become the DEFAULT for Gowin generation? For: smaller in every cell measured; every flagged cell still clocks ~8x above the target. Against: the nano, comparator and sequencer lose real clock speed, and the 7 no-Fmax cells are unmeasured. It is currently opt-in and nothing else was changed -- including the multiplier budget constant (`LUT_MUL_LUT4 = 4277` is a default-flow figure; ~1,332 with the flag) and `card_fit`'s default-flow tables.

**Tools (new):** `tools/measure_flag_across_families_v1.py`, `tools/measure_flag_pnr_v1.py`. **Next, as Alan directed: the flex level sources (accumulator, latch), then branch, merges, sequencer.**


## 951. FLEX ICM GENERATION, STAGE 5: THE LEVEL SOURCES (accumulator, latch). Their pulse inputs have no handshake and can silently lose a snapshot, so the emitter gates every pulse by the cell's ready. Verified against the real VM.

Alan: "Continue" (the flex cores in order: level sources, then branch, merges, sequencer).

**What the flex cells actually do (read from `accumulator_cell_v4sa.v` / `latch_cell_v4sa.v`):** the pulse inputs (`inc_pulse`/`dec_pulse`; `set_in`/`clear_in`/`toggle_in`) are bare strobes with NO handshake; the internal total / state ALWAYS updates on a pulse, but the output snapshot (`out_buffer`) is captured only when the cell is NOT `pending`. A pulse that lands while the cell is pending is therefore COUNTED but its snapshot is silently LOST, so `data_out` goes stale. **The emitter's rule:** every pulse is gated by the cell's ready -- a pulse is `source valid & ack_out`, and the source is acknowledged at that same moment -- so every event is both counted and snapshotted and `data_out` always equals the true total. Several sources on one role OR together (one event, all acknowledged); a latch `set` also needs bit 0 of the arriving value (the value is consumed either way, as in the VM). **Level mode** (a continuous accumulator, any latch -- `is_level`, #938): valid is held high once armed (`ack_out | valid_out`), the cell's own `ack_in` is tied high so it never stalls, and consumers never acknowledge it -- no fork, no ack, like a constant. A level cell may itself be an output (its out valid is held high; the host's ack is ignored). **A pulse-mode accumulator** is an ordinary event source (fork, acks) but still pulse-gated. **Refused, as on sub:** a constant or level source into an accumulator's inc/dec or a latch's toggle (rate-dependent). `ASSEMBLY.json` lists `level_sources`.

**Verified (`tests/test_flexsub_flex_level_v1.py`, 37/37, new).** A level never "completes an item", so the observation is different from the stream tests: the level is SAMPLED EVERY CYCLE and the SEQUENCE OF DISTINCT VALUES it passes through is compared -- which exposes any dropped or duplicated event whatever the timing -- against the REAL VM's per-item totals/states:
- counter (nine increments of 3): [0, 3, 6, ... 27] == the VM, back-to-back and under random input gaps;
- **up/down with TWO sources** whose arrivals interleave differently in every mode (plain, two stall seeds, first-input-slow, last-input-slow): the final level (8 inc - 3 dec of 5 = 25) is right and every level visited is a reachable partial sum;
- **pulse mode**, both directions: the discrete events [30, 30, 30] / [-30, -30, -30] == the VM's, through random exit stalls;
- **latch:** six toggles [0,1,0,1,0,1,0] == the VM; `set` over [0,2,1,3,0,5] (only odd values set; even ones are consumed with no effect) == the VM; an ALL-EVEN stream never sets, == the VM; **the priority clear > set > toggle with two events forced into the SAME cycle** (set+clear -> 0, set+toggle -> 1, toggle+clear -> 0), each == the VM;
- **a sentinel chain** accumulator -> comparator -> latch SET (a level driving a level): the latch reads 0 until the count reaches 5, then 1 == the VM, in three modes;
- **mutation controls, all caught:** a pulse NOT gated by ready (counted but snapshot lost); sources acknowledged when the cell is not ready (items consumed but lost); a `set` that ignores bit 0;
- the three rate-dependent refusals (a constant, a level, a comparator-of-a-level into inc/inc/toggle).
All 16 suites pass: flex_level 37 (new); flex 51; generator 37; flag 9; loops 9; addon 21; level 16; sequencer 20; branch 19; merge 17; netlist 12; compile 13; corpus 47; family equivalence 36; assembler 76; mul 38; plus the repo's MAN 14 and card-fit 28.

**A weakness in my own test, caught:** my first "latch set ignores bit 0" mutant check PASSED THE MUTANT -- the mutant simply sets at item 1 instead of item 3, and the compressed level sequence [0, 1] is identical, so the test could not tell when. Replaced with an all-even stream, on which a correct latch must never set and the mutant does.

**Not done / limits:** branch, merges and the sequencer on flex; a level source feeding a two-operand join with a live operand is generated but not tested (the pairing is timing-dependent, as in the VM's own self-pairing finding, #937, so there is no deterministic oracle); the pulse gating throttles the pulse sources to the cell's rate (one event per two cycles) -- a design choice, not measured as throughput; width fixed at 32; no flex place-and-route; the VM catch-up (#927); the open DECISION on `--nowidelut` as a default (#950). Nothing has run on silicon.
