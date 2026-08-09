# Current State (as of 2026-08-09 — see `archeology/sessions/archive-2026-08-09.md` for the full narrative)

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

1. **RAM cell confirmation** — Alan reviews `#231`-`#236`'s read/write
   mechanism and either confirms it or flags what needs to change,
   before any further scope is built on top of `ram_cell_v1.v`.
2. **BRAM controller** — wire `addr_counter_v1.v`'s `advance_en` to a
   real chain-head cell's ack; design the read-latency absorption;
   design the dual-bus USB/BRAM connection point concretely.
3. **Addon headroom work, now against a real baseline** — `#229`'s
   original plan (every future addon tested against a FULL-CARD build,
   real size+timing manifest) is now meaningful for the first time,
   since the 200MHz floor is a confirmed real number, not a phantom one.
4. **Two long-queued, never-run experiments** — `#206`'s
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
