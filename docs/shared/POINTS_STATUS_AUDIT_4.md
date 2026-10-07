# points.md Status Audit, Part 4 -- 2026-10-07 (#1000-#1020)

Part 4 continues `POINTS_STATUS_AUDIT_3.md` (#593-#999), which ended by saying the next audit should start at #1001. Same method as before: **status first**
(done / open / closed by decision), era second. It is a map on top of the ledger and does not edit it; the ledger wins wherever they disagree.

**Method:** the entry titles for #1000-#1019 were read, and the full text of #1017-#1019 (written in the session that produced this audit). Each item that part 3
listed as open was checked against a later entry. Part 3's list is the baseline, so only what changed is recorded here.

---

## Quick reference: what is open right now

**Hardware.** Unchanged and still the biggest gap: no sub or flex design has run on the Tang Nano 20K. The ESP32 pins and SPI link (#888), the `BTN_RST_N` root cause
(#896), whether the Kintex 480T can be revived (#928), whether Arria 10 hard-DSP offload is still a goal (#943), and the VIX Carrier never having been built in Quartus (#649).

**fp on cells.** The adder, multiplier and comparator exist (see "Closed since part 3"). Open:
- the **adder with the tight placement treatment** (the multiplier fell from 5,805 to 1,103 cells and the comparator from 641 to 74; the adder has not been done);
- the multiplier's real **synthesis cost**: the yosys run on the tight multiplier was abandoned after more than 25 minutes, so only cell counts are known, not LUTs or flip-flops;
- the remaining long lanes in the multiplier (EXPIN 84, STK 51, EXR 34 relays), which are physical distance, not padding (#1015): a delay-line cell, or a tighter AL / NR / RND (about 490 cells);
- **fp64** (a 128-bit word); the `--icm` generators still build 32 bits only; a placer that chooses positions itself for whole designs (the tight blocks use an annealer; whole designs are hand-laid);
- fp32 at the 64-bit word is proven for multiply and compare; the adder's fp32 and the full pipeline are not yet re-measured under the tight layouts.

**Priority core.** Built (see below). Open: a **FlexGrid model** (the RTL is the reference), a **width sweep row** (`docs/measurements/flex_width_sweep_975/costs.json` and the Tang MAN's `cell_costs`
do not include `priority_cell_v4sa`), orders longer than four turns (refused), and a flex-cell explainer (the explainer covers only the SUPER_LATCH encoder).

**Carried over from part 3, not touched in this range:** width (#948, #957-#963, #985, #970); second outputs (#976-#981); VM start-up flags, target profile and count estimator
(#927, #960-#961); a per-merge mode in the ICM (#957); the reconfiguration / fold thread (paused, #885 narrowed its purpose); the LLVM memory mapping (#830); the VIX backlog.

**Docs.** #856 asks for one more full documentation pass once the fp32 work is complete. fp32 multiply and compare now exist at word 64, but the adder and the full pipeline do not,
so this is still premature.

**Waiting on Alan:** whether single-shot preloaded constants should be reproduced on purpose (#939).

## Closed by decision (new in this part)

Both were open in part 3. Alan ruled on them on 2026-10-07 (#1020).

- **`command` in sub / flex: not ported, by design.** `command` lets one cell rewrite other cells' configuration while the system runs, which only means something where a cell can be a different core
  (the nano system). A sub or flex cell is one function fixed at build time, so there is nothing for it to switch to; the settings that can differ (a merge's mode, a priority's ranks and order) are
  set when the design is built, from the ICM file, which already works. The reconfiguration work also lost to a static pipeline at small scale (#885).
- **The sub sequencer's host-tick pairing (#937): the sub refusal stands.** In the VM a sequencer feeding a two-operand cell pairs its own values with each other, which depends on timing and has no
  reliable oracle. Sub advances on an outside pulse, so the generator refuses the combination. Flex does the useful version (one value per stream item, paced by the ack), and that is deterministic and tested.

## Closed since part 3 (what part 3 listed as open and later entries finished)

| Part 3 said open | Closed by |
|---|---|
| Adder: inf, nan, overflow | #1001 (special values, `fp_add(..., specials=True)`) |
| Adder: sub-normals | #1006 (gradual underflow, clamped normalise) |
| Adder rounding | #1007 (rne, rna, rtz, rup, rdn; sign of exact zero and overflow value per mode) |
| "Then multiply and compare built the same way" | #1008 (fp16 multiplier, all five modes, specials), #1009 (comparator, fp16 and bf16, full IEEE incl. NaN) |
| A larger floating-point word | #1010 (survey and groundwork), #1011 (fp32 multiply and compare run in generated RTL at a 64-bit cell word; the ram's constant port scales with width) |
| Hand templates / a person building designs by hand | #1002-#1005 (the Composer: view, drag, author, set fields, join ports, reuse saved designs as blocks that survive a save) |
| A genuine `priority` arbiter on flex | #1017 (`priority_cell_v4sa`: strict and weighted, up to four faces), #1018 (the sequenced channel, with the turn order now saved in the ICM) |

## Era 28: the fp pipeline from cells, completed for add, multiply, compare (#1001-#1011)

**Done.** The adder gained special values, subnormals and five rounding modes. The multiplier and comparator were built the same way, bit-exact against references in generated RTL (plain and with random stalls).
Making fp32 fit meant widening the flex cell word to 64 bits; the ram's constant port was made to scale with the width so every existing 32-bit instance is unchanged (#1011).

## Era 29: tight placement (#1012-#1016)

**Done.** The multiplier and comparator were shrunk without changing the arithmetic, by hand-placing short paths and, for the multiplier, keeping the flags separate until the end.
Cell counts: comparator 641 to 74 (flip-flops 14,259 to 913 at fp16); multiplier 5,805 to 2,125 (#1013) to 1,229 (#1014) to 1,103 with a U-shaped layout that also cut the footprint from 18x165 to 43x91 (#1016);
fp32 at word 64 went 5,899 to 1,175. #1015 recorded a finding worth keeping: the flex RTL already joins operands on valid and the nano's held operand is ported, so the long lanes were distance, not padding.
**Pending:** see the quick reference.

## Era 30: the priority core and the sequenced channel (#1017-#1020)

**Done.** `priority_cell_v4sa` has all three of the VM's modes. Mode 2 (Alan's #772) existed only as a VM prototype because the ICM file had nowhere to record its turn order; it now does
(`sequence_len`, `sequence_0..3`), the compiler's placers write it, the VM reads it, and a two-turn sequenced priority in front of a two-operand cell becomes operand wiring with the turn deciding A and B.
Proof: a 129-check bench, 22 planted defects caught, generated designs under stalls and skewed arrivals, and a compiled `x - y` whose generated RTL equals the VM. #1018 also corrected #1017: its assembler-suite
failures (flex cell count; the priority shape's liveness stim) had been pushed unseen and were fixed. Docs, explainer and manual were brought into line (#1019). Costs: the cell alone 291 LUT / 155 ALU / 94 FF at W=32;
in a generated design, strict 46 / 0 / 133, weighted 108 / 51 / 149, sequenced 51 / 6 / 136 (LUT / ALU / FF, including three rams).
**Known test state:** two tests fail on the baseline, both over the `cross` core's entry (`test_generic_field_codec_v1`, `test_icm_v3::test_unassigned_core_select_is_inert_not_error_on_decode`); they pre-date this range.
The whole VM suite was not run end to end in this session (it ran for over an hour); the flexsub suites and the tests related to the changed files pass.

---

## Summary

Part 3 ended with three clusters of open work: the fp-on-cells and width threads, the paused reconfiguration thread, and hardware runs. In this range the first cluster moved a long way (the adder is complete for
IEEE special values, subnormals and rounding; multiply and compare exist; sizes fell by factors of 5 to 9), the second was closed on the sub/flex side by decision, and the third has not moved: **nothing has run on the board.**
The flex core suite is now complete: every function the VM has, except `command` (not applicable) and the nano system's own multi-core reconfiguration, exists as a flex cell.

The next audit should start at #1021.
