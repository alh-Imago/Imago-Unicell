# Placing the packed adder as a physics-driven graph — findings

Goal: the full 18-cell (→ ~23 with duplicators) packed Kogge-Stone adder running as a
PLACED, ADDRESSED cell graph where the FABRIC carries the computation (each cell fires on
arrivals), driven by physics, not stepped by the controller. Built up in stages
(entry → stage 1 → … → full), smallest-first, so any failure is wiring/placement not an
unproven mechanism.

## Mechanisms already proven in sim (the pieces)
- math: packed_adder_cells.py, 18-cell graph = a+b (5000+ cases).
- linear chain + mid-chain stored shift: tb_zone64_shiftchain.v.
- two-source JOIN (two-arrival + stored shift): tb_zone64_ksstage.v (AND(P,G<<1)=0x44).

## Findings from staging the placement (the model additions the fabric forces)

### 1. The model is RELOCATABLE — addresses are base + offset
A compiled model is NOT pinned to absolute addresses. The LOADER drops it into free space;
addressing becomes "start point + per-cell offset". The loader creates the entry/exit points
(where a,b enter, where SUM leaves) at load time. Internal wiring is RELATIVE (cell-to-cell
offsets); only the base is absolute, chosen at load. => position-independent: "my cell 3
listens to my cell 1" becomes "base+3 listens to base+1" wherever base lands.
- TEST consequence: absolute base is arbitrary; only INTERNAL CONSISTENCY matters. Starting
  at 0x100 vs 0x01 is fine as long as every cell's offset follows the model wiring.
- The walker + final cell-addressing scheme are NOT sorted yet — fine at this stage. The
  CURRENT model's convention is logical address = physical CELL_ID, so the test uses CELL_ID
  as the logical address directly (no boot-commit dance; physical and logical coincide). This
  is why the "physical mode" proven tests worked — the two addresses are the same numbers.

### 2. Self-joins need DUPLICATOR cells
Every prefix stage has P' = P & (P<<span): a cell needs the SAME source on BOTH inputs (A and
B). One emit delivers ONE arrival, so a self-join can't be fed from one source. Solution
(chosen): a PASS-type DUPLICATOR cell copies P to a second address, so P' gets two genuine
distinct arrivals from two paths. Clean physics — every arrival is a real emit, no "fire
twice" special case. Cost: ~1 duplicator per self-join → adder is ~23 cells, not the 18-cell
math minimum. The math model papered over this; the fabric forces the honest count.

### 3. Serial load UNDER FREEZE, release as ONE call (the controller→physics boundary)
The model loads SERIALLY. Cells must be LOCKED (disarmed, won't fire, won't process arrivals)
during load, then RELEASED in a single call so the whole graph goes live at once in a known-
complete state. If cells went live as loaded, a downstream cell could fire into a half-built
topology (garbage). So: load every cell COLD, then one release arms them together.
- Native mechanism: start_flag (cmd_latch[22]) = armed bit. Topology presets come in
  COLD (even opcode, disarmed) / ARMED (odd opcode) pairs. CMD_FREEZE (0x05) disarms,
  CMD_RELEASE (0x06) re-arms. Load cold → release = the freeze line.
- This is the SAME freeze that guarantees state drains for save (cell states yes, DSP no),
  applied at LOAD time. Not a new invention — the existing freeze used as the load boundary.
- TEST consequence: each stage test must LOAD COLD, then RELEASE, THEN present a,b. The
  release is the single moment the host hands control to the fabric. (The broken first entry
  test implicitly configured-and-fired incrementally — wrong; mirror load-cold-then-release.)

## Open question to answer empirically (next build)
Arrival ORDERING at joins: when two sources fire together, which lands as A (1st/stored) vs B
(2nd/trigger, the one the stored shift hits)? Handled in principle by relative path
lengths/propagation, but the sim will show the actual behaviour once addressing is consistent.
The duplicator + load-cold-then-release structure is the frame to test it in.

## Corrected first-stage plan (teed up)
Entry (G=a&b, P=a^b) then stage 1 (Gp1, G1, P1 with a P-duplicator), on the current model's
logical=physical convention, consistent offsets from a chosen base, LOAD COLD → RELEASE →
present a,b. Prove the stage computes from propagation alone, then replicate the stage pattern
up to the full ~23-cell adder.

## UPDATE (staging stage 1): fan-out needs duplicators too — adder is ~34 cells, multi-zone

Building stage 1 surfaced that the duplicator cost is BIGGER than just self-joins. Confirmed
against unicell64.v: a cell emits to ONE output_address; a value reaches a consumer by emitting
to the consumer's listen address. Multiple cells CAN share a listen address (fan-out to
same-address listeners is free), BUT a node feeding consumers at DIFFERENT addresses needs a
DUPLICATOR per extra destination (PASS cell copying the value to another address).

Fan-out count across the full graph:
- every G feeds {Gp_n, G_n} -> +1 dup each (5 stages)
- every P feeds {Gp_n, P_n, P_n(self-join)} -> +2 dup each (5 stages); P0 also feeds SUM (+1)
- total ~16 duplicators on top of the 18 compute cells = **~34 cells**.

CONSEQUENCE: ~34 cells EXCEEDS one 25-cell zone. The packed adder is a MULTI-ZONE structure
(spanning zones via bridges), OR needs a fan-out strategy that duplicates less (e.g. reusing a
single broadcast address where consumers can share it, or restructuring so fewer nodes fan to
distinct addresses). The math model's 18 was the LOGICAL minimum; two-arrival physics roughly
DOUBLES it. This is a real placement/loader input, not a detail — the loader's anchor-first
embedding must account for duplicator cells and cross-zone bridging for the adder.

Stage-by-stage testing is unaffected (each stage's subset fits a zone); this concerns the FULL
assembly. Worth revisiting whether the fan-out duplication can be reduced before committing the
full ~34-cell multi-zone graph — a cheaper fan-out primitive (if one exists) would shrink it.
Open question banked.

## RESOLVED (Alan's reclaim insight): keep DUPLICATORS — shared-address fan-out breaks clean reclaim

The "reduce duplicators via shared listen address" optimisation was tempting (two cells on one
input address => one emit feeds both, free fan-out). It WORKS for compute, but it BITES at
load/reclaim time, so it is rejected as the default.

THE PROBLEM: config is delivered by address (LOAD_AT rides addr_match). If two cells share a
listen address for fan-out, then ANYTHING addressing that point hits BOTH — they were made
indistinguishable on purpose, so you can no longer target them individually. Consequences:
- Can't reconfigure / repurpose one without the other — they're welded by the shared address.
- Breaks the allocation model's core assumption (cells are INDIVIDUALLY allocatable/reclaimable,
  allocate-on-load / reclaim-on-unload). Shared-address cells are a FUSED pair: they allocate
  and reclaim together, not as two free cells.
- Chicken-and-egg on un-fusing: to re-address one apart you must address it individually, but
  it shares an address, so you can't. The fusion is hard to undo in place.

THE TRADE: shared-address saves a cell but costs INDIVIDUAL ADDRESSABILITY + clean reclaim. A
DUPLICATOR costs a cell but keeps every cell individually addressable, reclaimable, repurposable
— consistent with the whole system (freeze-drains-state, allocate-on-load, relocatable offsets
all assume clean per-cell units).

DECISION: the DUPLICATOR is the default. Cell count is NOT the binding constraint (density
headroom exists; the ~34-cell adder spanning zones is just bridges, which we have).
Addressability and clean reclaim ARE precious — they're what make load/unload/repurpose work.
Spend a cell to preserve them. Shared-address fan-out is a RARE special-case, only where cells
are genuinely tight AND those cells will NEVER need independent reconfiguration (a fixed,
never-repurposed structure). This closes the earlier "can fan-out duplication be reduced?" open
question: technically yes, but it shouldn't be — keep the duplicators.

(General principle worth carrying: a duplicator is an honest addressable cell doing fan-out; a
shared address is a shortcut that fuses cells into one addressable unit. The system rewards
cleanliness over cell-thrift, so the honest version wins by default.)
