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

## DEEPER PRINCIPLE: logical-address uniqueness is an INVARIANT (fusing is reset-only to undo)

Following the fused-cell problem to its conclusion: two cells fused on a shared LOGICAL address
cannot be separated in RUN mode (RUN addressing IS the shared logical address — any command hits
both). The ONLY addressing that distinguishes them is the PHYSICAL address (CELL_ID), reachable
ONLY in BOOT/physical mode, reached ONLY by a GLOBAL RESET. A global reset is system-wide and
untargeted => to un-fuse two cells you must reboot the whole fabric and LOSE EVERYTHING (every
model, every config, all loaded state).

So a fused pair is effectively PERMANENT for the life of that boot; the only recovery is TOTAL
state loss. That is categorically worse than "spend an extra cell" — it's a state only
recoverable by wiping everything. Fully vindicates: keep duplicators (a duplicator is a normal
cell, individually addressable, reclaimable in RUN mode, no reset).

GENERAL INVARIANT (carry beyond the adder): LOGICAL ADDRESS UNIQUENESS is load-bearing for ALL
RUN-mode operability. Collapsing/aliasing two cells' logical addresses is IRREVERSIBLE without a
global reset. Any future temptation to share/alias logical addresses (compression, clever
routing, resource sharing) hits this same trap — guard against it.

Note the coherence: physical mode being reset-ONLY is a SAFETY property (no local "force a cell
to physical" escape hatch -> can't re-address a cell past its auth; auth re-established cleanly
only on a full reset). The safety property and the un-fixability of fusion are the SAME property.
We wouldn't want a local physical-mode escape (it'd undermine auth) — so the cost of fusing is
necessarily total. Correct design; just don't fuse.

## FINDING (stage 1 attempt): host INJECT can't deliver 32-bit data to a non-zero address

The INJECT opcode packs target address in cpu_data[31:16] and data in the same word, so a
host inject to a NON-ZERO address forces the address bits into the high half of the data — you
cannot host-inject a full 32-bit value to an interior cell. The entry stage worked only because
cell 0's address is 0x0000 (high bits zero, 16-bit operands fit clean).

CONSEQUENCE for testing: interior stage cells must be fed CELL-TO-CELL over the bus (where
address and data are SEPARATE lanes), NOT host-injected. This is faithful to the real fabric —
interior operands always come from other cells, never from host injects — so it's not a fabric
limitation, it's a test-construction requirement: drive stage 1 by letting the ENTRY cells emit
to the join cells through the bus, not by injecting interior values.

ARRIVAL-ORDER (the join physics): resolved in principle via latch_in (cmd_latch[26], "hold
a_arrived after firing — single arrival fires next") + preload_sel (bits 18:17). The join's A
operand is ESTABLISHED first (preloaded/latched); the second operand is then the SOLE arrival
that triggers the fire. So joins don't race two arrivals — A is in place, B triggers. This is
also faithful to the loader (A-operands established at load, B-operands flow as live dataflow).

## Stage 1 (teed up, bus-connected build)
Entry (proven) feeds the prefix cells over the bus: Gp1=P&(G<<1) and P1=P&(P<<1) (self-join via
P-duplicator), G1=G|Gp1. A-operands established first (latch_in/preload), B-operands flow from
the entry. Duplicators (Gdup, Pdup) give each consumer a distinct arrival (a cell emits to ONE
addr). The honest, more-involved next build — not a host-inject shortcut.

## RESOLVED: models have declared ENTRY/EXIT POINTS — host feeds entry points, never interior

The inject-collision was the WRONG FRAME. The workbench (even on the old cell version) already
showed the right model: it exposes ENTRY POINTS where the user inputs data. That is structural,
not UI convenience:
- A model declares ENTRY POINTS (input seams) and EXIT POINTS (output seams). Data is delivered
  TO entry points and FLOWS through the topology. No entry point = no input = inert; the flow is
  what animates the model.
- The host NEVER injects to interior cells. Interior cells receive from UPSTREAM cells (the
  flow). The host only delivers to declared entry points — so it's never an arbitrary-address
  inject; it's "deliver a to entry-A, b to entry-B", where the model defines those points and
  the loader places them to be cleanly deliverable.
- => the "can't inject 32 bits to a non-zero interior address" problem DISSOLVES: you don't
  input to the interior at all. It was an artifact of trying to do the wrong thing.

Same concept at different scopes: pond BRIDGES are the pond's entry/exit to the wider fabric;
ENTRY POINTS are the model's entry/exit. Declared seams where data crosses in/out. The workbench
exposing entry points for user input is the user-facing face of this structural fact — the old
workbench was already showing the deployment architecture.

Unifies with freeze/release: load model (cells+config) frozen; entry points are the declared
input cells; host PRELOADS a,b into the entry points; RELEASE triggers the flow. "Preload entry
operands + release" and "workbench exposes entry points" are the SAME thing — entry points are
both the input UI and the cells the host preloads.

NB distinction: this is the FUNCTION-execution model (inputs present at start, release, read
result) — perfect for the adder (pure function, a+b). STREAMING models (continuous data) need a
separate live-input path (bridge/host-feed); that's a different case, don't over-generalise.

## How this clarifies the SHIFT-ADDER design
- The adder's ENTRY POINTS are the two stage-0 cells (G=a&b, P=a^b) — already proven. a,b are
  delivered THERE; everything else is flow. No interior injects.
- Test method for ALL stages: feed a,b at the entry points, let the prefix stages receive
  CELL-TO-CELL over the bus (separate addr/data lanes — already correct in the fabric). Stage N
  is driven by the flow from stage N-1, not by host injects.
- Operand loading = preload entry A-operands under freeze, release = the single trigger; the
  wave propagates through the whole graph. Faithful to deployment (a loaded function runs by
  release).
- EXIT POINT = the SUM cell; the host/workbench reads the result there.
- Confirms the staged build: each stage's test feeds the entry points and reads the stage
  outputs over the bus — no host-inject-to-interior anywhere. The bus-connected stage 1 is the
  honest build and the inject limitation never applies.

## STAGE 1 ATTEMPT (bus-connected): the current addressing model fights multi-cell flow

Tried stage 1 as bus-connected flow (entry G,P -> converge on join cell5) on the CURRENT cell.
Hit a chain of addressing frictions, each solvable but all from one root:
- SET_INPUT_ADDR (logical listen) KILLS firing — the proven entry worked only in PHYSICAL listen.
  So flow must use physical-listen + custom-OUT routing (emit to the consumer's physical CELL_ID).
- With physical-listen + custom-out: G(cell0) and P(cell1) both routed emit->addr5 (Gp1's
  CELL_ID). Result: only P emitted (0xb9f9); G never fired. Two identically-configured entry
  cells, same feed, only one fires — an entry/arrival-order interaction in the fan-out injection.
- Underlying: a JOIN needs two arrivals A-then-B on one addr; two COMPUTED sources (G,P) firing at
  the same depth race, and establishing A-first for a computed operand isn't clean on this cell.

ROOT CAUSE (the honest finding): the current cell conflates LISTEN with IDENTITY (addr_match on
input_address gates both data and config; physical-vs-logical mode is load-bearing for firing).
Multi-cell FLOW wiring fights this at every step. This is EXACTLY what the cell v3 addressing
change fixes (identity = OUT/CELL_ID fixed; IN = mutable listen; addr_match split config-vs-data).

CONCLUSION: the adder's individual MECHANISMS are all proven in sim (math 18-cell=a+b; chain+shift;
two-source join; entry G=a&b,P=a^b load-cold/release). But assembling them into a flowing
multi-cell GRAPH is impeded by the current addressing model. Rather than keep fighting the current
cell's addressing in the test harness, the natural path is: do the cell v3 addressing change
(identity=out, mutable-in, split match) FIRST, then the graph wiring becomes clean (cells emit at
identity, consumers point mutable INs, no physical/logical mode fight), and the full adder
assembles on the cleaner substrate. The adder is the MOTIVATING test case for v3 — it surfaced
precisely why v3 is needed. (Entry stage remains proven/committed; broken stage-1 attempt removed.)
