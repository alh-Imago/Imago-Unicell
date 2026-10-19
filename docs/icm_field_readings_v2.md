# ICM readings across the families -- audit part 2 (ledger #1281)

Part 1 (`icm_field_readings_v1.md`, #1274) covered ram and branch; the ruling of #1275 settled the one conflict found there
(a preloaded, unfed, non-fixed ram is a one-shot; a constant says `fixed_mode` 1). This part covers the other cores.
Two kinds of evidence are kept apart: MEASURED (a run was made) and FROM THE SOURCE (read in the generator's own code or
comments, not re-run for this table).

## 1. Measured: generated flex hardware (iverilog, through the Kintex wrapper) against the VM, every example design

Method: `flexsub_icm_generate_v2` (flex family) then `kintex_icm_runner_v2.wrap`, whose simulation feeds three words per entry
(two vector sets) and compares every exit with the original VM grid. Default vectors, simulation only.

| result | designs |
|---|---|
| PASS (agree) | adder_constant, adder_stalled, adder_stream, priority_sequenced, priority_strict, ram_oneshot, relay_chain, relay_chain_stalled, tiles_flex, cordic_z_convergence, cordic_z_convergence_v2, looped_cordic_v1_open, mixed_flex_carrier_flex_v1, mixed_flex_std_flex_v1, mixed_flex_sub_flex_carrier_flex_v1, mixed_flex_sub_flex_v1, parallel_reduction_tree |
| DISAGREE: ram_hold | explained, a vector artefact: the default vectors write the HOLD ram 3 times while the other stream is flowing, so the result depends on timing. With the HOLD ram written once (the design's own description) the same check PASSES. Not a definition conflict. |
| DISAGREE: priority_weighted | NOT explained. RTL delivers 9 words (all 9 inputs), the VM side of this check 8 (`20 30 1 10 1 2 1 2`). A dedicated test (`tests/vm/test_flex_grid_priority_hold_v1.py`) compares the same mode on a 12-item stream and passes, so a reading artefact in the runner's VM side is possible, but that is a guess and was not tested. |
| refused by the generator, with reasons | looped_cordic_v1 (no output cell), looped_cordic_v1_closed_flex (a ring with no stop) |
| could not be compared | three `mixed_flex_*_div_*` designs (the VM refuses: both operands of a div arrive in the same tick, no operand order); reduction_tree4_exit_v1 and small_relay_chain (the check's exit-name lookup fails; a harness problem) |

## 2. From the source (the generator's own comments and code, `tools/flexsub_icm_generate_v2.py`)

| core | reading, where families differ |
|---|---|
| comparator | signed `>=` threshold -> 0/1 in the standard RTL (`compare_cell_v4.v` line 129), the VM (line 1098) and the generator: agree |
| adder | a two-operand cell pairs by ARRIVAL order; the CORDIC deliberately avoids the adder's arrival-order-dependent subtract |
| mul | low 32 bits of the product |
| div | unsigned; dividend = operand A by arrival order; both operands in the same tick has no order and the VM refuses it. Flex holds valid until ack, sub pulses (#1070): not cycle-identical, own benches |
| nano | first arrival = HELD operand A, second = FLOWING operand B; on sub/flex A must arrive exactly one cycle before B (unlike adder/mul) |
| sequencer | VM advances when a consumer drains its offer (backward ack); the sub cell takes an external advance pulse, so the generator exposes `adv_<name>` and rotates the stored values. Feeding a sequencer into a two-operand cell pairs values with each other in the VM but with the stream on sub: refused |
| accumulator, latch | VM: continuous-mode accumulator and latch are always-valid LEVEL sources; the v4s cells pulse valid only on update, so the generator holds valid high. Pulse-mode accumulator is a discrete event and matches |
| priority | exists on the flex family only (`priority_cell_v4sa`); on sub a priority that is not eliminated is refused |
| merge core modes | flex only (`merge_cell_v4sa`); sub has no merge cell |

## 3. What this shows, and does not

- No new conflict of MEANING like the preload one was found among the cores in the examples that could be compared; the cores
  differ in capability (flex-only cores, refusals) and in timing conventions the generator already states.
- Not covered: the cores' fields individually against each family's RTL (this table relies on the generator's statements);
  designs beyond the 26 examples; widths other than 32; the standard-family RTL (not run here).
- Open: priority_weighted (above) should be resolved before it is called agreement or disagreement.
