# What a freeze would have to capture (flex family, v4sa)

Written 10 Oct 2026 (ledger addendum 63). Source: a read of the cell files in `sub/verilog/*_v4sa.v`. Nothing here was run; it is a reading of the RTL. The register lists came from a text search for `reg` declarations, so a register declared in an unusual way could be missing. A check by synthesis (list every flip-flop in a generated design) is still to do.

## What `freeze_in` does today

`freeze_in` is a clock-enable. Every flex cell wraps its normal update in `else if (!freeze_in)`, so when it is high the cell keeps every register exactly as it is, and `ack_out` is forced low so nothing claims to be ready. `valid_out` is just the `pending` register, so it holds too. That is a true pause: it holds the state but **does not read it out**. The generators tie `freeze_in` to 1'b0, so no generated design can be frozen at present.

## Where the words in flight live

In the flex family every cell output is registered (`out_buffer` plus `pending`, or `data_reg` plus `have` in the RAM cell), and `valid_out` and `ack_out` are plain functions of those registers and `freeze_in`. There is no state sitting on the wires between cells. So, **if the reading is right, freezing at a clock edge and capturing every dynamic register captures the whole computation, including the words in flight.** (The VM keeps those words in a separate `_pending` list, which is why checkpoint v1 lost them; in the RTL they are already inside the cells.)

## Registers to capture, per cell type

Dynamic = changes while the design runs. Configuration = set by `cfg_valid`, constant in generated designs (it is baked in), so it needs no capture if the same bitstream is reloaded.

| Cell | Dynamic registers | Configuration registers |
|---|---|---|
| adder | `pending`, `pending_c`, `out_buffer`, `carry_buffer` | `armed`, `subtract_mode`, `carry_enable` |
| accumulator | `pending`, `accumulator`, `out_buffer` | `armed`, `step_amount`, `pulse_mode`, `threshold` |
| branch | `pending_1`, `pending_2`, `held1_reg`, `held2_reg`, `has_loaded_1`, `has_loaded_2`, `out_buffer` | `armed`, fixed-mode flags, `emit_source`, `route_low/equal/high` |
| compare | `pending`, `out_buffer` | `armed`, `threshold` |
| latch | `pending`, `latched`, `out_buffer` | `armed` |
| mask | `pending`, `out_buffer` | `armed`, `mask_en`, `nibble_mask` |
| merge | `pending`, `rr`, `out_buffer` | `armed`, `mode` |
| mul (LUT and DSP) | `pending`, `pending_hi`, `out_buffer`, `hi_buffer` | `armed`, `hi_enable` |
| nano | `pending`, `held_value`, `out_buffer` | `armed`, `topology` |
| priority | `pending`, `seq_idx`, `credit_n/s/e/w`, `out_buffer` | `armed`, masks, ranks, mode, sequence settings |
| ram | `have`, `data_reg` | `armed`, `pending`, `fixed_mode` (`pending` also changes at run time in non-fixed mode: treat as dynamic) |
| router | `pending_a`, `pending_b`, `out_buffer` | `armed`, `enable_a/b` |
| sequencer | `pending`, `seq_index`, `out_buffer` | `armed`, `value_0..3`, `sequence_len_m1` |
| shift stage | `pending`, `out_buffer` | `armed` |

Not examined: the `adder_v1` arithmetic block and any pipeline registers inside the DSP primitive used by `mul_cell_v4sa_dsp` (the DSP block may hold internal registers that a text search of the cell file cannot see).

## Two findings that matter for the plan

1. **Capture is plausible, restore is not possible yet.** A configuration load (`cfg_valid`) works while frozen, but it also clears `pending` and `out_buffer` on that cell ("discard any in-flight result on reconfigure"). There is no path that writes `out_buffer`, `pending` or the other dynamic registers with chosen values. Reloading a saved state needs a new load path into every cell. That is new hardware, not a software change.
2. **The cell list is not the whole state.** The design also contains whatever holds its inputs and outputs (the feed from the ESP32, the output port, the unit shield). Those would need the same treatment.

## Not yet done (the tests this suggests)

- Synthesis check: list every flip-flop of the generated CORDIC and sum the dynamic bits against this table.
- RTL test: freeze the flex CORDIC at each cycle, read every dynamic register, then start a second copy of the design with those values forced in (in simulation, via `$deposit` or a test-only load) and show the same result at the same time. This repeats the VM test (addendum 60) in the RTL.
- Decide the hardware design for the load path and the readout (a scan chain through the cells is the classic way; the cost in LUTs is unknown).
