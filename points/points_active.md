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
