# Current State (as of 2026-08-10, RAM-interface/distribution-system thread — see `archeology/sessions/archive-2026-08-09.md` for the earlier same-day narrative)

## NOTE ON HOW THIS SECTION GOT HERE: two sessions worked in parallel

This thread was worked on from two different interfaces at the same
time on 2026-08-10 — one session built `#266` (mux core + single
memory interface) then reported itself paused; while paused, a
**different** session pushed `#267`-`#270` (RAM-cell economics,
`combiner_cell_v1.v`, the full read+write pipeline proven end to end,
and a DSP integration design note). The first session then resumed and
built a 2-level mux tree, unaware `#267`-`#270` had landed — creating a
real numbering collision, resolved by renumbering that entry to `#271`
rather than overwriting anything (see `#271`'s own correction note in
`points.md` for the full detail). **All of the work below is real and
verified** — nothing here was fabricated; this note exists so a future
session understands why the numbering jumps the way it does.

## MAJOR MILESTONE: full distribution system proven end to end (points.md #269)

**The entire system, from BRAM out to BRAM in, now works as one real
pipeline — Alan's own "full test build" ask, answered directly:**
`BRAM(out) → mem_read_splitter_v1 → mux_cell_v1 → two real 2-cell
ram_cell_v1 relay chains → adder_cell_v1 (real work) → combiner_cell_v1
→ BRAM(in) → read-back`. Result: `0x1000 + 0x234 = 0x1234`, real
arithmetic through `adder_v1.v`'s carry chain, two operands seeded at
scattered BRAM addresses each routed to a DIFFERENT chain by the mux's
own per-transaction decision. **Passed on the first real logic run**
after two trivial Verilog-mechanics fixes (a `reg`/`wire` type error) —
every individual core's own prior verification held up completely once
assembled. Full regression: all 16 testbenches pass, zero regressions.

`combiner_cell_v1.v` built (`#268`) — the write-side core, fixed
round-robin chain-select counter (Alan's own explicit choice: no
waiting, "if it waits then others get backed up"), proven with real
SIMULTANEOUS-offer contention (2 stub chains firing the same cycle,
correctly serialized in whichever valid order the scanner's phase
produces, dense address packing with zero gaps despite many
skipped-empty-slot cycles). One testbench-only bug caught (an unstated
assumption about capture order for the simultaneous case — the DUT was
correct, the test's expectation was too rigid, fixed).

RAM-cell economics reality check locked in (`#267`) — a genuine
question worth having answered on record: if a whole card were built
as uniform `ram_cell_v1.v` per `#263`'s own "all-RAM is a valid
ICM-compatible configuration" policy, is it viable as raw storage?
**No — the die's own embedded M20K beats an all-RAM card by roughly
50x capacity-per-ALM**, checked against real numbers already in hand,
not estimated. `ram_cell_v1.v` was never designed as capacity, though —
it's a cheap, fast, per-stage-backpressured streaming pipeline buffer
(its original `#231`-`#234` framing), genuinely good at that, genuinely
bad at bulk storage. Not a contradiction, a scope clarification.

DSP integration design note locked in (`#270`) — Alan's own insight: a
DSP chain is a fixed, static pipeline (data flows through a set
sequence of MAC stages), so unlike BRAM there's no arbitrary position
to address dynamically. IN/OUT are both just `ram_cell_v1.v` — no new
core type needed. Addressing collapses to two FIXED config-time values
(chain start/end), not a live counter. Real chain-length numbers
flagged (depth >1600 overall, max 27 per individual chain — not yet
independently sourced, flagged as needing a real citation). **One real
open question, not resolved:** DSP blocks are physically fixed in
columns on the die, unlike the uniform cardinal mesh every other core
lives on — reaching a DSP column needs some real interconnect resource
outside the ordinary mesh, and if that's shared, genuine contention
exists independent of chain load. Connects to the pre-existing "Loader
DSP placement strategy" already on record. Real next step, Alan's own:
get the actual DSP block locations for `10AX066H2F34E2SG`.

## SECOND, PARALLEL TRACK: a real 2-level mux TREE proven (points.md #271, renumbered from a colliding `#267`)

Independently of `#267`-`#270` above, this session built and proved a
genuine 2-level `mux_cell_v1.v` TREE (not the single-node mux `#266`/
`#269` used) — `tb_mux_tree2_v1.v`: ROOT (2 direct 1-hop leaves + 1
face to CHILD) → CHILD (3 more leaves via a real 2-hop path).
**6/6 correct**, all 5 leaves reached, zero false deliveries, a repeat
delivery confirmed correct across multiple transactions. First
construction reaching PAST the 4-chain minimum via a genuine tree, not
a single node — `#258`'s hierarchical count/slot addressing scheme
confirmed across a real node-to-node hop for the first time.

## THAT GAP IS NOW CLOSED: a real 2-level combiner TREE too (points.md #272)

`combiner_relay_v1.v` (child, offers upward through cardinal
data+routing, mirroring `mux_cell_v1.v`'s own shape) +
`combiner_cell_v2.v` (tree-aware root, clones `#268`'s `combiner_cell_
v1.v`, extended with per-slot child-input support). Builds `#258`'s own
ENCODE description for real: root reads a child's `routing_in`,
computes `effective_count = child_count+1`, writes its own slot into
the matching field, preserves the child's lower stamps unchanged.
Regression-equivalence to `#268`'s proven `combiner_cell_v1.v`
confirmed directly (identical output, is_child off). Real 2-level tree
(2 raw chains + 2 via a real relay child): **4/4 correct**, one result
hand-decoded bit-by-bit to confirm against the design, not just trusted
from the testbench's own check. All 18 testbenches (both sessions'
work combined) pass together.

**Still open:** no Quartus data for either tree side. A genuinely full
system combining BOTH trees with real chains and real computation at
matching multi-level scale (mirroring `#269`'s "full test build" but at
real tree depth on both sides, not the single-node slice `#269` used)
has not yet been assembled — that's the real next integration step.

## What's real and settled, independent of either track above

Real Quartus silicon data exists for compute/RAM/adder cell types
(`#209`/`#224`, `#250`, `#261`) and for `bram_controller_v1.v` (`#265`,
confirmed real M20K inference, exact match — 128 blocks, 158.78 MHz).
No Quartus data yet for `mem_read_splitter_v1.v`, `mux_cell_v1.v`, or
`combiner_cell_v1.v`. The SHELL/CORE/ADDON architectural model
(`#253`) and its real ICM/VM-portability consequence + resolving
policy (`#263`) are both settled and logged.

**Nothing is mid-edit or broken** — clean working tree, everything
pushed to `origin/main`.



## RAM-interface thread opened (points.md #248-#250)

Alan's three-part directive for this thread: (1) real Quartus size/
timing for `ram_cell_v1.v` — **DONE**, see below. (2) an adder wrapper
onto a normal cell, own size/timing check — design proposed by Claude
(reuse the compute cell's existing two-arrival A/B capture, route it
through `adder_v1.v`'s carry chain instead of the NOR gate tree,
cloned not edited in place), **awaiting Alan's confirmation before any
RTL is written.** (3) BRAM access mechanism — Alan's own framing: an
opcode plus address, with read data distributed to ≥4 parallel chains
— **open design question, not yet resolved:** does one BRAM read
broadcast to all chains, or does each chain get its own address stream
with the controller arbitrating real BRAM read ports among them?

**Task (1) CLOSED, real Quartus data (`#250`):** `top_ram_chain50_v1.v`
(50-cell `ram_cell_v1.v` chain, `#249`) built clean —
**193 ALM / 251,680 (3.86 ALM/cell), clk_div Fmax 277.32 MHz, +36.394ns
slack, SDC confirmed applied** (same `Reading SDC File` +
two-distinct-clocks check `#241`/`#242`/`#247` established). **3.86
ALM/cell is ~26-27x smaller than the compute cell's own confirmed
~100-106 ALM/cell** (`#209`/`#224`) — a real, now-measured number, not
an assumption from the simpler RTL. 0 BRAM/0 DSP used — this is the
chain-mechanism-alone cost; real BRAM wiring will add to it later.
Worst paths are all reset fanout into config registers, unremarkable.

**Task (2) CLOSED, real Quartus data (`#251`/`#252`/`#261`):** Alan's
correction — an arithmetic cell REMOVES the compute cell's gate tree,
doesn't run beside it — confirmed against `unicell_stripped_v1.v`'s
own single-`case(topology)` structure. `adder_cell_v1.v` reuses the
compute cell's two-arrival A/B capture shape + `ram_cell_v1.v`'s
handshake conventions, with `adder_v1.v`'s real carry chain replacing
the gate tree entirely. iverilog-confirmed against real arithmetic (5
operand pairs incl. two 32-bit wraparounds, bit-exact). Two real bugs
found+fixed along the way: a genuine DUT-side priority bug
(`capture_now`/`offer_draining` wrongly `else if`-chained, could
permanently strand `data_valid=1`), and a testbench-only stimulus-
timing race (unrelated to the DUT). **Real Quartus build (`#261`): 262
ALM / 251,680 (5.24 ALM/cell), clk_div Fmax 233.97 MHz, same
two-distinct-clocks SDC-confirmation signature as every other build.**

**All three cell types now have real, measured ALM/cell numbers:**
compute ~100-106 (`#209`/`#224`), RAM 3.86 (`#250`), adder 5.24
(`#261`) — adder modestly larger than RAM (real arithmetic vs. plain
latch) but both dramatically smaller than the compute cell's gate
tree, confirming the SHELL/CORE claim (`#253`) in real silicon.

**Task (3), BRAM ≥4-chain distribution — active development
(`#257`-`#260`), not yet complete.** Full architecture locked in
(40-bit BRAM packing, mux/combiner cores, hierarchical tree
addressing, host stall/refill lifecycle); `bram_controller_v1.v`
widened to 40 bits and `mem_read_splitter_v1.v` built+verified; mux
and combiner cores themselves still unbuilt.

## Named architectural confirmation: SHELL/CORE/ADDON (points.md #253)

Alan's own framing, locked in: the cell's exterior (cardinal ports,
ready/ack handshake, offer/drain) is the **SHELL** — identical across
nano/RAM/adder. The interior compute is the **CORE** — one swappable
component per cell type (nano's gate tree, RAM's latch, adder's carry
chain). **ADDONS** wrap around the outside, a separate mutable layer
(the pre-existing Unicell-Shell compile-time-gated addon concept).
`#249`-`#252` are the proof the shell tolerates a swapped core with no
shell redesign — a real architectural claim, not just two new cell
types. **CORRECTED by `#254`:** the "latency-bearing core" fork
flagged here didn't come from Alan and isn't right — DSP is a
card-level hardened resource, interfaced the same way RAM is (a
bridge at the chain edge), not a component swapped into the shell's
core slot. That's the same open problem as task (3)'s BRAM interface,
not a new core-design question. No known latency-bearing CORE
requirement currently exists.

## NAMED CONSEQUENCE + POLICY: heterogeneous cores break ICM/VM portability (points.md #263)

Real, permanent cost of the SHELL/CORE architecture, named directly:
CORE is now a HARDWARE property (fixed at synthesis), not a config-time
property like topology was — so a model mixing RAM/adder/mux cores
isn't portable "logic, not wiring" anymore, it demands a specific
physical hardware arrangement. VM fidelity breaks the same way (would
need per-card physical-layout knowledge to simulate correctly).
**Scoped:** only affects models that actually mix core types — a
model built entirely on ONE core type keeps full ICM portability,
unchanged. **Resolving policy (Alan's own):** the BRAM/DSP interface
(mux/combiner/splitter/bram_controller) was never going to be
ICM-portable anyway (fixed physical die resources) — confine
heterogeneity to that one bounded addon; the REST of any card's fabric
must stay homogeneous (one core type) to remain ICM-compatible. This
makes "all-RAM" or "all-adder" cards EQUALLY VALID complete
configurations, not just nano-with-exceptions — real new design space.
Freely mixing cores beyond the fixed interface remains buildable but
is an explicit step outside the ICM format, same discipline as
`#231`-`#234`'s own logged divergence.

## BRAM READ/WRITE command interface built (points.md #255)

`bram_controller_v1.v` — the "code plus address" command mechanism
Alan asked for once the counter and RAM cells were both in hand:
`cmd_valid`+`cmd_op`(1 bit, READ/WRITE)+`cmd_addr`+`cmd_wdata`, the
standard Quartus BRAM-inference idiom (single clocked process, one
`mem` array — should map to M20K, not yet Quartus-confirmed).
Single-stage synchronous read confirmed via iverilog: result registered
at the SAME edge the command is sampled (earliest possible response,
standard M20K single-port timing) — this is the fixed latency figure
`#243`'s read-latency-absorption item will build against. 5/5
write-then-read round trips bit-exact, deliberately out of write order.
**Not yet done:** no Quartus M20K confirmation, no wiring to
`addr_counter_v1.v` or a real `ram_cell_v1.v` chain head, and the
≥4-chain distribution/arbitration question (task 3's other half) is
completely untouched — this is the command mechanism those pieces will
issue through, not the distribution design itself.

## mux_cell_v1 built + COMPLETE SINGLE MEMORY INTERFACE proven end-to-end (points.md #266)

`mux_cell_v1.v` — the mux core from `#257`/`#258`'s design: same shell,
one direction reserved as fixed upstream input, 3 usable output faces.
Routing byte layout pinned down concretely: `[7:6]=count [5:4]=slot1
[3:2]=slot2 [1:0]=slot3`. Face mapping is config-time, not hardcoded —
same module works anywhere in a future tree. One real DUT bug caught
before compiling (a double-driver conflict on `downstream_mask`,
fixed). `tb_mux_cell_v1.v`: 5/5 transactions routed to the CORRECT
face every time, both `count=1` and `count=2` decode paths verified,
zero false deliveries.

**Then wired to `mem_read_splitter_v1.v` for the complete single
memory interface** (`tb_single_memory_interface_v1.v`): one address →
real BRAM read → DATA/ROUTING split → mux decode → correct
destination, proven **5/5 correct end to end**. One bug caught in the
integration test's own seed literals (wrong bit position for the
intended pattern), not the DUT — the DUT behaved exactly as designed.

Full regression: all 14 testbenches pass, zero regressions.

**Not yet done:** no Quartus data for either module. This is ONE mux
node (up to 3 destinations) — reaching 4+ chains needs a real
multi-level tree, per `#258`. The combiner core (write side) remains
completely unbuilt.

## bram_controller_v1 REAL M20K INFERENCE CONFIRMED (points.md #264/#265)

Real Quartus build hit `#256`'s zero-init loop trying to unroll 65536
iterations — Quartus caps constant-loop unrolling at 5000. Fixed by
removing the zero-init entirely (it was never correct hardware
behavior anyway — real M20K content is undefined at power-up without
a `.mif`) rather than chasing an unconfirmed Quartus setting. Every
consumer now writes before reading; only 1 of 12 testbenches actually
depended on the removed init, fixed. **Real Quartus result: 145 ALM,
2,621,440 block memory bits — an EXACT match to the predicted 64K×40
capacity, exactly 128 M20K blocks, definitively confirming real M20K
inference.** clk_div Fmax 158.78 MHz — comfortably closed but the
lowest Fmax of any build this session (RAM 277 MHz, adder 234 MHz),
plausibly real M20K routing/fanout cost at 128-block scale, not
investigated further.

## New CORE type: memory interface, counter-sync claim PROVEN (points.md #256)

Alan's own design: a new core — takes a counting cell's data as the
address, combines with a fixed READ/WRITE command, data pops out or is
taken; each cell's own ack is the control, so a counter driven by this
mechanism naturally syncs. `mem_interface_cell_v1.v` built on the
SHELL/CORE model (`#253`) — same shell as RAM/adder cells, core is
`bram_controller_v1.v`. **The sync claim is proven directly, not just
asserted:** `tb_mem_counter_sync_v1.v` wires `addr_counter_v1.v`'s
`advance_en` straight to the mem cell's own ack (one line, zero
separate arbitration logic) and confirms 34 real captures across a
0-4 wraparound, address sequence correct every time, capture count
never outrunning the consumer by more than 1. One real latent bug
caught and fixed before it could corrupt data (a missing "doubly full"
guard — the header already claimed no-pipelining but the logic didn't
enforce it). **Still open:** no Quartus data yet; no real
cross-instance shared-memory write-then-read (current test seeds via
simulation backdoor); the ≥4-chain distribution question (task 3's
other half) is completely untouched — this proves ONE chain's sync,
not how multiple chains share one BRAM.



Everything through 2026-08-09 (points.md #230-#247) has been moved to
`archeology/sessions/archive-2026-08-09.md`, most-recent-first within its
own sections, preserved as written. This file starts fresh as the fast
catch-up document, per its own stated purpose.

## Timing is now on a genuinely confirmed-good foundation (points.md #237-#247)

**The whole `#176`-`#227` timing arc's Fmax/slack figures were invalid.**
Confirmed directly (Quartus's own "file not found" message, `#241`): the
SDC constraint file was never actually applied to any of those builds —
a project-folder workflow gap, not an RTL/repo problem — so every one of
those numbers was measured against a phantom auto-derived ~1GHz clock,
not the real target. ALM counts were NOT affected (confirmed twice, at
two scales — see below).

**The fix is confirmed working, at both scales that matter:**
- 240-cell build (`#242`): 28,930 ALM (vs `#223`'s invalidated 28,900 —
  noise-level), clk_div Fmax 214.87 MHz, **+0.346ns slack, PASSING.**
- 750-cell build (`#247`, the real target scale): **89,778 ALM (vs
  `#198`'s invalidated 89,818 — noise-level), clk_div Fmax 210.79 MHz,
  +0.256ns slack, PASSING.**

**The design genuinely meets a real 200MHz target with margin to spare.**
Worst-path list at 750-cell scale is still dominated by `cmd_latch[13]`/
`ready_bit` self-loops — the same structural signature `#198`/`#227`
already (invalidly) flagged; that qualitative finding held up the whole
time, only its numbers needed correcting. `#209`/`#224`'s ALM-per-cell
figures and `#229`'s ~1500-1700 cell capacity estimate all stand.

## RAM cell — real RTL, still DRAFT (points.md #231-#236, #243-#246)

`fpga/verilog/ram_cell_v1.v` — minimal latch-only cousin of the compute
cell, no NOR-tree. Chain direction fixed at config time
(`downstream_mask`/`upstream_mask`, routing_mask-style). The pull
mechanism is genuinely just `ready_out = !data_valid` — no dedicated
request signal anywhere, reuses the existing ack fabric entirely. Three
passing iverilog testbenches: fixed-mode re-offer, 3-cell cascading
chain, and freeze/backpressure cascade (both directions, confirmed).

**Still explicitly DRAFT — Alan has not yet confirmed the read/write
mechanism himself.** cfg_data field layout is a first proposal, not
frozen. Read `#231` through `#236` in order before touching this.

**BRAM controller thread (`#243`-`#246`), address-generation piece
built and tested, controller NOT complete:** `adder_v1.v` (standalone
arithmetic adder — checked directly, NEITHER cell type's gate table has
ever had a real arithmetic primitive, confirmed against both the
stripped cell and the FULL cell's own `loop_back` history) and
`addr_counter_v1.v` (wrapping counter built on it, `advance_en`
deliberately ack-gated, not free-running). Both iverilog-verified.
NOT yet wired to `ram_cell_v1.v` or real BRAM — still open: the actual
chain-head-ack -> `advance_en` connection, and BRAM's own 1-2 cycle
read latency absorption. Design (not yet RTL): dual in/out bus matching
real M20K dual-port capability, USB as the initial connection point,
circular/wrapping addressing. The "write keeps pace with read" concern
was raised and then correctly relaxed — starvation/resume is the
natural, already-proven behavior of the pull mechanism, not a fragile
throughput requirement.

## Other items from this session

- Tang Nano 20K (`#230`) adopted as a new proving/embedded-candidate
  card, alongside the main Arria 10 line — no RTL ported yet, gated on
  Alan having the board in hand.

## Full distribution system design LOCKED IN, no RTL yet (points.md #257)

Closes `#248` task (3)'s ≥4-chain distribution question with a
complete architecture, worked out across extended discussion:

- **40-bit BRAM packing** (real M20K native width, confirmed via
  Intel's own spec — `bram_controller_v1.v`'s 32-bit default was
  Claude's own arbitrary choice, needs widening): `{8-bit ID, 32-bit
  data}` per word, both fields split at the source.
- **Mux core** (read side, new CORE type): DATA→staging `ram_cell_v1`
  (normal shell path), ROUTING→mux's selector register directly (no
  draining needed). Mux outputs are genuinely cardinal, point-to-point
  to each header cell — no shared bus/select signal, no special header
  cells. `downstream_mask` computed fresh per-transaction from the
  captured routing byte instead of fixed at config time. 2-cycle
  latency, 1-cycle throughput. **CORRECTED by `#258`: only 3 faces are
  usable per node (one is consumed by the RAM-facing connection), not
  4 — reaching 4+ chains needs a real TREE of mux nodes, not one flat
  node.**
- **Addressing (`#258`, replacing `#257`'s flat 8-bit ID):**
  hierarchical, level-based encoding — 2 bits (level count, 0-3) +
  three 2-bit slots (one per level). Each node reads the CURRENT count
  as a slot index, picks one of its 3 faces, decrements by 1, forwards
  the full field unchanged (no shifting). Write side mirrors exactly:
  innermost node starts count=1, each parent increments + stamps its
  own face into the new slot. A considered "free bonus level" via
  count=0/4 was tried and dropped — bit-width collision (2 bits can't
  hold a distinct 4, and an ordinary 3-level decrement already produces
  0 for an unrelated reason). Alan's choice: count 0-3 directly and
  only means "use this many dynamic levels," no reserved values.
- **Combiner core** (write side, mirror of mux): cardinal INPUTS per
  chain, arrival direction alone = origin, no ID needs to travel with
  write data. Same 3-usable-faces/tree correction as the mux applies
  here too. **Contention resolved via a chain-select counter**
  (reuses `#256`'s proven counter mechanism) doing FIXED round-robin —
  one slot per chain regardless of occupancy (Alan's explicit choice
  over variable-time waiting, to avoid backing up other chains).
  Counter position doubles as both "which chain to check" and "the ID
  to stamp." Real consequence: empty slots get skipped (dense packing,
  no waste), so stored order carries zero positional information — the
  ID is the ONLY way to interpret a word, both directions now.
- **Host-driven stall/refill lifecycle:** two independent counters (out
  feeding chains, in collecting results); stall = out-empty or
  in-full; USB host watches externally, drains in-side, refills
  out-side, resets both counters, restarts.

**Two questions left explicitly OPEN:** (1) "farthest point" for
drain/refill — current-position-relative vs. oldest-unconsumed
circular-wrap (`#244`'s framing) — genuinely different addressing
logic, not chosen. (2) No empty/full status signal exists anywhere in
the RTL yet — the whole lifecycle depends on one existing, not
designed.

**Scope note:** this has moved from fabric/RTL into system-workbench
territory (Ward/Shore/PTT layer already on record in `PLAN.md`) — the
stall/refill lifecycle belongs there, not purely in this session's
fabric-RTL thread.

## NEXT (agreed order, 2026-08-10 — this is what a fresh session picks up first)

1. **Assemble a FULL system at real multi-level tree scale on both
   sides** — `#271`'s mux tree (5 destinations) and `#272`'s combiner
   tree (4 real capture points) are both proven independently. Nobody
   has yet combined both trees with real chains and real computation
   in one assembled system (`#269`'s own full-pipeline proof used a
   single-node mux + single-node combiner, "the smallest meaningful
   slice," not tree depth on either side). This is the genuine
   completion of the minimum-4-chain target.
2. **Real cross-instance shared-memory write-then-read** — `#256`'s
   PARTS 1+2 test and `#269`'s full-pipeline test both still use
   SEPARATE `bram_controller_v1.v` instances for OUT vs. IN (matching
   `#257`'s own "two independent regions" design, not a shortcut) — a
   real round trip through ONE shared memory via the cell interface
   itself remains open, separate from that design choice.
3. **Resolve `#257`'s two open questions**: the "farthest point"
   drain/refill addressing semantics, and the empty/full status-signal
   mechanism the host-driven stall/refill lifecycle depends on.
4. **DSP bus-contention question from `#270`** — get the real DSP
   block locations for `10AX066H2F34E2SG` before reasoning further
   about whether reaching a DSP column shares a contended resource.
5. **Remaining Quartus builds** — `bram_controller_v1.v`'s real M20K
   inference at 40 bits, and eventually `mem_interface_cell_v1.v`'s and
   `mem_read_splitter_v1.v`'s own real size/timing figures. (The
   compute/RAM/adder three-way comparison is DONE, per `#261`.)
6. **Addon headroom work, now against a real baseline** — `#229`'s
   original plan (every future addon tested against a FULL-CARD build,
   real size+timing manifest) is now meaningful for the first time,
   since the 200MHz floor is a confirmed real number, not a phantom one.
7. **Two long-queued, never-run experiments** — `#206`'s
   OPTIMIZATION_MODE "Aggressive Performance" and `#200`'s duplication-
   flags diagnostic — now genuinely worth running against a trustworthy
   baseline.

**Also still open:** the `#210` programming-delivery architecture
decision (single-hop/addressed vs. accepted broadcast) — `#247`'s
worst-path list showed the programming channel as timing-relevant with
real numbers for the first time, worth revisiting with that in mind.
The VM core rebuild (`#216`/`#217`, gap analysis at `current/
VM_CORE_GAP_ANALYSIS.md`) — still deliberately not started while RTL
settles. The BRAM+DSP hybrid integration (`#220`) — the RAM-cell chain
is its planned front door, per `#232`.
