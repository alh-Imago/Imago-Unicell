# Core parity audit: flex (v4sa) against carrier (v4c) — ledger #1104, 12 Oct 2026

Method: the header comments and the RTL of every flex cell (`sub/verilog/*_cell_v4sa.v`) read against its carrier cell (`fpga/verilog/*_v4c.v`, `nano_gate_v4c.v`) and the carrier (`unicell_vix_carrier_v1d.v`), plus `nano/root_definition.json` (the ICM field list) and the VM's config keys. READ, NOT SIMULATED, except where a row says MEASURED (#1102). Alan's ruling (12 Oct): all families on equal footing; the command core on the sub side is the only exception.

**The structural difference behind most rows.** A flex cell has ONE point-to-point handshake input per operand, so a two-operand cell (adder, mul, div) is a JOIN: it waits for both. A carrier cell has four faces and masks and takes ANY two successive arrivals as its two operands. A fixed constant that offers itself again and again therefore pairs with itself in the carrier (MEASURED: K+K, #1102), never in flex.

| ICM core | Flex cell | Carrier cell | Same job? | Gap (carrier unless stated) |
|---|---|---|---|---|
| ram | ram_cell_v4sa | ram_cell_v4c | yes (fixed, flowing, one-shot preload, HOLD #1021/#1035) | none for function. A fixed ram is "always valid" in flex, re-offers by pending/ack in the carrier — harmless unless it feeds a pairing cell |
| adder | adder_cell_v4sa | adder_cell_v4c | NO for constants | **no join: pairs any two successive arrivals** (MEASURED). Add/subtract, second_output both present |
| mul | mul_cell_v4sa(_dsp) | mul_cell_v4c/v5c | NO for constants | same pairing rule as the adder (read) |
| div | div_cell_v4sa | div_cell_v4c | NO for constants | same pairing rule (dividend = first arrival, divisor = second). Both RTLs call the register `rem_primary`, the ICM/VM key is `remainder_primary` (internal RTL name, harmless) |
| compare | compare_cell_v4sa | compare_cell_v4c | yes | flex takes the threshold on its own WIDTH-bit port, carrier in the 32-bit config (width only) |
| accumulator | accumulator_cell_v4sa | accumulator_cell_v4c | yes | flex has inc/dec pulse ports, carrier inc_dir/dec_dir faces; step 8 bit, threshold 16 bit in both |
| latch | latch_cell_v4sa | latch_cell_v4c | yes | set/clear/toggle pulses vs faces |
| sequencer | sequencer_cell_v4sa | sequencer_cell_v4c | yes | 4 x 8-bit values both |
| merge | merge_cell_v4sa | merge_cell_v4c | yes, one stated difference | join-OR acknowledges each half as it arrives (carrier) vs both together (flex) — written in the carrier header |
| priority | priority_cell_v4sa | priority_cell_v4c | NO | **sequenced-channel mode (scheduling_mode 2, #772/#1018) is in the ICM field list, the standard VM and the flex RTL but NOT in the carrier RTL** (config has strict / weighted only) |
| nano | nano_cell_v4sa | nano_gate_v4c | NO | **hold, feedback, re-emit and update wires are tied to 0 in the carrier** (`unicell_vix_carrier_v1d.v` ~l.545), so the held-operand and stored-constant paths are unreachable there; flex has `hold_in_data` + `load_hold` ports (#917) |
| branch | branch_cell_v4sa | branch_cell_v4c | different shapes | carrier: one upstream, reference-vs-next compare, rolling mode, per-outcome fixed value of 7 bits, fan-out to 4 faces. Flex (#918): two inputs each fixed or flowing, one shared emit source incl. in1−in2, wide fixed value, two outputs. The ICM branch record is the carrier shape and the flex generator lowers it; flex-only features (two live streams, difference) have no ICM field. Capabilities differ both ways, not read line by line |
| mask / router / shift | mask_cell, router_cell, shift_stage | the carrier's shared add-on chain (nibble mask, lane shift, fine shift, invert); router = ram with two downstream faces | by composition | the add-on is configured once per carrier (VIX_LATCH [159:133]); nothing missing found, not tested |
| corner / cross | made by the generator from ram cells | corner_cell_v4c / cross_cell_v4c | yes | native cell exists only in the carrier (#999 open) |
| command | none (sub-side exception) | command_cell_v4c | n/a | the agreed exception |

**What the ICM relies on (naming and type consistency).** The ICM core strings are `ram adder accumulator comparator latch sequencer branch mul priority merge div nano`; the VM keys on these, the flex generator keys on these, and the carrier's `core_select` names are `compare` / `seq` / `accum` for three of them (a mapping table is needed wherever an ICM goes to a carrier word; `tools/carrier_grid_v1.py` has one for ram/adder/branch only). `nano/root_definition.json` gives bit positions for the OLD lineage's layout (4-bit masks, e.g. div second_output at bit 12); the carrier cores use 6-bit masks and other positions (their own header maps, mirrored in `nano/vix_tile_library_v1.py`). Nothing checks the carrier words against the field list, so a field the ICM names but the carrier RTL lacks (priority sequence fields) passes silently. The ICM field names themselves agree across VM, flex generator and carrier headers except `remainder_primary` / `rem_primary` (RTL-internal).

**Gaps, in order of what they block:** (1) two-operand cells (adder, mul, div) cannot be fed a constant in the carrier; (2) priority sequenced mode; (3) nano hold wiring; (4) branch: no agreed single shape; (5) a check that ties the ICM field list to the carrier words.

**Not done:** no carrier change made; nothing here was simulated beyond #1102; mul/div pairing and the nano wiring are from the RTL text only; branch comparison is by headers.
