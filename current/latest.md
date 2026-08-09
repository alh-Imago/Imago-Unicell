# Current State (as of 2026-08-09, RAM-interface thread — see `archeology/sessions/archive-2026-08-09.md` for the earlier same-day narrative)

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

**Task (2) design confirmed + RTL built + prepared for Quartus
(`#251`/`#252`):** Alan's correction — an arithmetic cell REMOVES the
compute cell's gate tree, doesn't run beside it — confirmed against
`unicell_stripped_v1.v`'s own single-`case(topology)` structure.
`adder_cell_v1.v` reuses the compute cell's two-arrival A/B capture
shape + `ram_cell_v1.v`'s handshake conventions, with `adder_v1.v`'s
real carry chain replacing the gate tree entirely. iverilog-confirmed
against real arithmetic (5 operand pairs incl. two 32-bit wraparounds,
bit-exact). Two real bugs found+fixed along the way: a genuine
DUT-side priority bug (`capture_now`/`offer_draining` wrongly
`else if`-chained, could permanently strand `data_valid=1`), and a
testbench-only stimulus-timing race (unrelated to the DUT). Same-scale
(50-cell) Quartus project prepared (`Unicell-Q-adder-chain50-v1.qsf`),
not yet built — **awaiting Alan's Quartus run for the real ALM/Fmax
number.**

**Task (3), BRAM ≥4-chain distribution, still fully open** — no
mechanism chosen yet.

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

## NEXT (agreed order, 2026-08-09 — this is what a fresh session picks up first)

1. **BRAM ≥4-chain distribution/arbitration** — `#248` task (3)'s other
   half, still completely open: does one BRAM read broadcast to all
   chains, or does each chain get its own address stream with the
   controller arbitrating real read ports among them?
   `mem_interface_cell_v1.v`/`#256` proves the sync mechanism works for
   ONE chain; this is the genuinely undecided multi-chain question.
2. **Real cross-instance shared-memory write-then-read** — `#256`'s
   PARTS 1+2 test used two SEPARATE `bram_controller_v1.v` instances
   (one per cell); a real round trip through ONE shared memory via the
   cell interface itself (not a simulation backdoor seed) is still open.
3. **Quartus builds for the three prepared-but-unbuilt projects** —
   `Unicell-Q-adder-chain50-v1.qsf` (task 2's real ALM/Fmax number,
   completing the three-way compute/RAM/adder comparison),
   `bram_controller_v1.v`'s real M20K inference, and eventually
   `mem_interface_cell_v1.v`'s own real size/timing figure.
4. **Addon headroom work, now against a real baseline** — `#229`'s
   original plan (every future addon tested against a FULL-CARD build,
   real size+timing manifest) is now meaningful for the first time,
   since the 200MHz floor is a confirmed real number, not a phantom one.
5. **Two long-queued, never-run experiments** — `#206`'s
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
