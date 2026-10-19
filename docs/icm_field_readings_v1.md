# ICM field readings across the families (audit, ledger #1274)

Purpose: one ICM field should mean one thing in every design. This table records, from the actual files, how each
reader takes the fields. "Official" is blank wherever the readers differ: that is Alan's ruling to make.
Scope: reading of the source files only (listed per row). It is not a measurement of every design; where a row says
"not separately checked" nothing was run.

## RAM (ram core)

| ICM fields | Standard RTL `ram_cell_v4.v` | Generator -> flex (`flexsub_icm_generate_v1.py`) | Generator -> sub | VM SuperGrid / FlexGrid v1 | FlexGrid2 | Official |
|---|---|---|---|---|---|---|
| preload_value, fixed_mode 0, nothing feeding it | flowing; the value is DRAINED once the consumer acks (line 295: `!fixed_mode && offer_draining`) = one-shot | CONSTANT: built as a fixed-mode ram, always valid (`_const_set`, line 183; instance at line 888) | same generator code; not separately checked | one-shot (as standard) | constant ONLY when the consumers are all adder/mul and the ram is not fed; otherwise one-shot | **DIFFERS - needs ruling** |
| fixed_mode 1, nothing feeding | permanent value | constant | constant (cell has `cfg_fixed_mode`) | permanent value | same as v1 | agrees |
| fixed_mode 1 WITH a source (HOLD) | exists (`hold_mode`, line 138) | exists (`ram_cell_v4sa` HOLD, #1021) | generator REFUSES it | exists (ported #1035) | same as v1 | agrees where it exists; sub refuses |
| load_data_valid 1, fixed 0, no preload (one-shot) | `load_data_valid` bit marks data valid on load | exists (OFFER_PRELOAD) | generator REFUSES it | reads `load_data_valid` (line 731) | same as v1 | agrees where it exists; sub refuses |
| preload_value on a ram that is not a source | n/a | generator reports a problem (line 523) | same | VM accepts | same | VM looser than hardware |

## BRANCH

The VM branch is a held-reference comparator (first arrival becomes the reference). The generator lowers only the cases the
cell can do and REFUSES the rest with a reason: reference = first arrival of a plain stream with rolling off; value source or
fixed value differing among the emitting outcomes; more than two routed faces; a routed face with no cell; a branch fed only
by constants. The VM accepts all of these. So for branches the VM is looser than the hardware, and the refusal is explicit
(not silent), which is consistent as long as the refusal list is part of the definition.

## What this means

1. One real conflict found: a preloaded, unfed, non-fixed ram is a one-shot in the standard RTL and both VM grids, and a
   continuous constant in the flex hardware. FlexGrid2 narrows the gap (CORDIC constants) but does not close it: it does not
   cover consumers other than adder/mul.
2. The other rows are "exists on some families, refused on others". That is a capability difference, stated by the
   generator, not a disagreement of meaning.
3. Not yet done: running more generated designs against the VM to look for further conflicts; the other cores (merge,
   adder subtract/addon, multiplier, divider, comparator, accumulator, latch, sequencer) have not been tabulated.
