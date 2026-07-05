# Packed shift-adder on the cluster mesh — verified 45-cell design

Status: ALGORITHM + PLACEMENT + ROUTING fully verified in Python (cell-by-
cell simulation, 10000/10000 random cases against real addition). RTL not
yet built — this is the exact spec to build it from. Read this before
writing any Verilog for it.

## Two real bugs found getting here (both matter beyond this one adder)

1. **`packed_shift_adder.py`'s `build_packed_adder_chain()` had a genuine
   algorithm bug**, independent of anything about clustering: it held
   `P_word` constant across all 5 Kogge-Stone stages, but the file's own
   reference function `packed_ks_add()` (proven correct, tested 1000/1000)
   updates P every stage too (`P = P & (P<<span)`). The cell-plan function
   was never actually run end-to-end against real addition — only the
   separate reference function was tested — so it silently drifted wrong
   (passed only ~33/2000 random cases). **Fixed in the source file**, this
   session: P now gets its own SHL+AND update chain mirroring G's.

2. **A cell has exactly one `output_address` per firing — the algorithm
   assumes free software-style fan-out that doesn't hold in hardware.**
   Every value read by more than one consumer needs an explicit relay cell
   (`PASS_B` + `latch_in`, primed via `CMD_SWAP_AB` — the same mechanism
   verified in `tb_v3_shl_cell.v`) per *extra* destination. This is
   structural to prefix-computation trees generally (not fixable by
   reordering this specific algorithm) — any future tile with a value used
   more than once needs to budget relay cells the same way.

Real, fully verified cell count: **45**, not 19/22/28 (numbers used earlier
in this same conversation before the above were found). Still a
**10.7x–12.2x compaction** vs. the wide KS tree (482–548 cells) — close to
Alan's own "8 to 10x" estimate despite the correction.

## The verified 45-cell chain

Built by an automatic relay-insertion pass (not hand-placed — hand-placing
this exact kind of fan-out was tried twice in this session and got it wrong
both times; the algorithmic version is trustworthy because it was verified
against 10000 random cases, cell-by-cell, not just algebraically):

- `G0`, `P0`: initial AND/XOR of `A_raw`,`B_raw`.
- `P0_fanout_r1/r2/r3`: relay chain preserving the ORIGINAL P0 across all 5
  stages, for the final sum (which needs `P0_original`, not the
  stage-evolved P).
- Per stage k (span 1,2,4,8,16): `SHL_Gk`, `SHL_Pk`, `AND_PGk`, `AND_Pk`,
  `OR_Gk`, plus whatever relay cells that stage's fan-out needs (a producer
  feeding 2 consumers gets 1 relay; 3 consumers gets 2, chained).
- `CARRY_SHL`, `SUM_XOR`: final carry and sum extraction.

Full cell list with exact inputs, cell IDs, and cluster assignment is
reproducible from `/tmp/final_chain.pkl`'s generation script (see the build
log for the exact commands run) — regenerate rather than hand-transcribe
when building the RTL, for the same reason the placement was computed
rather than hand-placed.

## Cluster placement (9 clusters, 5 cells each, cells 0-44 sequential)

Greedy fill in dependency order. Cross-cluster edges: 31 total, 15 distinct
(src,dst) directed bridge pairs. Every cluster has **at most 4 distinct
neighboring clusters** (clusters 1, 2, 3, 5 are the busiest) — fits exactly
within the existing 4-directional (N/S/E/W) bridge port model, no
`NUM_BRIDGES`-widening or new bridge mechanism needed.

## What the loader needs that `loader_fsm_v3.v` doesn't have yet

1. **`SET_OUTPUT_ADDR` as an explicit per-cell load step.** Every cell here
   needs a specific, non-default output target (its single consumer's
   CELL_ID) — the existing loader only does target+topology+methodology+
   done, relying on default output addresses. This build needs a 5th step.
2. **A priming pass** for every relay/shift-role cell (`CMD_SWAP_AB`,
   pre-arming `a_arrived` — see `tb_v3_shl_cell.v`'s finding that a cold
   one-shot relay cell's first-ever value can't self-trigger). Roughly
   26 of the 45 cells need this (every `RELAY` and `RELAY_SHIFT` op).

## Next step (explicit)

Build the actual RTL: extend the loader (or write a purpose-built one for
this specific 45-cell design, since it's a one-off proof, not a reusable
general component) with the SET_OUTPUT_ADDR + priming steps; instantiate 9
small `unicell_zone64_v3` clusters (`NUM_CELLS=5`) wired per the bridge plan
above; build a testbench injecting real A/B operands and checking SUM
against real addition. Not done this session — the design above is the
spec to build it from, verified in Python first so the RTL has something
solid to be tested against.

## Update 2026-07-05 (later same day): RTL actually built, real progress, one real conflict found

The RTL described above as "not yet built" is now built: adder_loader_v3.v
(the 7-step-per-cell loader with SET_TARGET/SET_INPUT_ADDR/SET_OUTPUT_ADDR/
LOAD_AT/methodology/LOAD_DONE, plus a post-load priming phase),
top_packed_adder45_v3.v, and adder45_config.vh/adder45_clusters.vh
(machine-generated from the placement scripts, not hand-transcribed). Grew
from 45 to 50 cells along the way (delay cells added to the G-path, one per
stage, to help resolve a bus-contention finding -- see below).

Loading and priming work correctly end to end (all 50 cells + 32 priming
steps confirmed via emit_count). The computation itself does not yet
produce the correct SUM. Three more real things were found and are worth
recording precisely, in the order they surfaced:

### 1. Same-cluster collision (G0/P0)

Simple sequential-fill-by-5 clustering put G0 and P0 -- the one genuinely
simultaneous pair in the whole design -- in the same cluster, causing a real
local-arbiter collision (confirmed via trace: both fire the same cycle, only
one value survives). Fixed with a cluster-LABEL swap (not a chain reorder,
which would have broken topological validity for the simulator) separating
them. This part is resolved and stayed resolved through everything below.

### 2. CMD_SWAP_AB had no address gating at all (real bug, fixed, affects the whole project)

Found while debugging the priming phase: CMD_SWAP_AB was gated only by
`auth_ok`, no `config_match` check -- meaning it broadcasts to EVERY cell
in the array, not just whichever cell SET_TARGET holds. This silently
pre-armed every cell (not just the intended relay targets) during priming.
Fixed in `unicell64_v3.v`: CMD_SWAP_AB is now config_match+auth gated, same
as every other per-cell config opcode. This is a real, standing fix --
confirmed via full regression that everything built earlier this session
still passes, with two testbenches (`tb_card_2zone_v3.v`) needing an
explicit SET_TARGET added before their own CMD_SWAP_AB calls, since they'd
been unknowingly relying on the broadcast bug to work.

### 3. Zone bridge address-decode (built) vs shared-broadcast fan-out (not yet reconciled)

The deeper bus-contention finding from the same debugging thread: any local
fire (even one targeting a REMOTE cluster) was clobbering the local cluster's
own bus_addr, confirmed via trace to be genuine structural contention in the
bridge mechanism (`bridge_X_out_valid <= za_out_valid`, broadcasting every
fire to every neighbor unconditionally -- fine with one bridge partner,
which is all that existed before this session, not fine with 2-4 active
neighbors).

Fixed: `unicell_zone64_v3.v` now takes per-direction `{DIR}_ZONE`/
`{DIR}_ACTIVE` parameters and only asserts a bridge output when the fired
address's own zone (`addr[15:5]`) matches that direction's configured
neighbor. Confirmed via trace that a real cross-cluster delivery now routes
cleanly with zero contamination from unrelated traffic.

But this exposed a real conflict with something built earlier the same day:
the automatic relay-insertion pass's fan-out solution has a relay cell
listen at its "natural" sibling's OWN address (a borrowed/shared address) to
catch the same broadcast. That only works if the broadcast reaches
everywhere -- which is exactly what the new address-decode fix correctly
stops doing. Confirmed via trace: relay cells whose sibling lives in a
different cluster stay primed forever, never receiving their real value,
because the now-smart router correctly keeps the shared address local to
whichever cluster owns it by CELL_BASE.

Real fix (not yet applied, next concrete step): add a placement constraint
so any two cells sharing a broadcast address always land in the SAME
cluster. Both the router and the relay mechanism are individually correct;
the clustering step just wasn't enforcing a constraint it needed to once
routing became address-aware instead of broadcast.

### Also requested this session, not yet started

A host-triggerable "start programming" control register (today `start_load`
is a raw testbench pin) -- needed so a real PCIe interface can initiate
loading by addressing a register the same way it addresses BRAM, rather
than an out-of-band signal that has no equivalent once there's a real
external host.
