# Current State (as of 2026-08-10, RAM-interface/distribution-system thread — see `archeology/sessions/archive-2026-08-09.md` for the earlier same-day narrative)

## Quartus prep for the discrete decomposition -- 2 real bugs fixed, 1 open, NOT ready to build yet (points.md #298)

`top_sentinel_discrete_test_v1.v` — real synthesizable self-test for
`#294`/`#295`/`#297`'s cells. **Two real bugs found and fixed:** the
same missing-`ready_out` mistake already caught once in simulation
(silently blocked the comparator from ever firing), and a missing
per-pass reconfiguration (accumulator carried over between passes,
making the "expect cleared" check wrong from pass 2 onward — confirmed
by tracing the real accumulator value). **A third bug found but NOT
yet root-caused**, honestly left open rather than chased indefinitely
or quietly dropped: passes 0-2 now correctly reset and match exactly,
but pass 3 comes up one feed short — looks like a genuine intermittent
timing race, not yet confirmed. **Recommendation: do not build this
top-level in Quartus yet.** The underlying cells themselves remain
fully proven and completely unaffected — this is a test-harness
problem only.

## `latch_cell_v1.v` -- closes #295's own sticky-latch gap, full discrete chain proven (points.md #297)

New CORE, same continuously-live pattern as the accumulator, SET/CLEAR
instead of inc/dec, clear takes priority (matching #279/#284's rule).
Wired into the full chain (accumulator → comparator → latch): **4/4
checks pass, including the exact case #295 flagged as a real
divergence** — collecting below threshold with no unfreeze now
correctly stays latched, genuine recovery correctly clears it. Gap
closed.

Two real bugs found via direct tracing: (1) both new cells were
missing a `ready_out` port entirely — invisible in standalone tests,
silently broke the chain (a floating wire poisoned the comparator's
readiness with `x`); fixed by adding it to both. (2) A genuine logic
bug in the latch — `capture_set` never checked the actual arriving
*value*, only whether something arrived, so a correct `0` reading was
misread as a trigger; fixed to require the value genuinely be 1.

One flawed latency measurement ("0 cycles," a physical impossibility
given registered logic throughout) discarded rather than reported,
per the project's own discipline against overclaiming.

Full regression: all 29 testbenches pass, zero regressions.

**Not yet done:** no Quartus data for any of the three cells; the
diff<0 path (already proven free) not yet combined into this same
3-cell chain; proper isolated per-hop latency measurement still open;
freeze_out/freeze_in not yet wired into any real chain.

## `compare_cell_v1.v` + full decomposition proof against `sentinel_counter_v2.v` (points.md #295)

`compare_cell_v1.v` — deliberately simpler than the accumulator (plain
single-capture shell, `ram_cell_v1.v`'s own shape), since the
comparator only cares about the CURRENT value, unlike the accumulator's
never-drop-an-event requirement. 5/5 correct standalone, including the
inclusive boundary case. **The real proof:** wired directly into
`accumulator_cell_v1.v`, driven with the identical event sequence as a
real `sentinel_counter_v2.v` reference — **11/11 checks pass**, exact
step-by-step agreement including the precise boundary crossing.

**Honest gap found, not papered over:** the discrete comparator is
stateless; the reference's `err_overflow` is sticky. Collecting back
below the threshold with no unfreeze correctly diverges — comparator
clears, reference correctly stays latched. The sticky-latch bookkeeping
itself isn't built into this decomposition yet — open question (small
glue logic vs. a genuine new latch cell).

Two real testbench bugs found, both revealing genuine multi-cell
pipeline properties, not RTL flaws: an unacked initial offer silently
shifting every check by one step, and a real structural pipeline-
latency effect (fixed-duration drains aren't always enough — fixed by
draining repeatedly until genuinely settled, not guessing a bigger
delay). Worth stating plainly: a discrete decomposition is eventually,
correctly consistent, not cycle-exact with a monolithic module — that's
how real hardware pipelines behave, not a defect.

Full regression: all 27 testbenches pass, zero regressions.

## `accumulator_cell_v1.v` -- first real cell of the sentinel discrete-cell decomposition (points.md #294)

Genuine new CORE (per `#293`'s naming): direction-tagged hold-and-refire
(inc_dir always +1, dec_dir always -1), not `adder_cell_v1.v`'s matched-
pair model. Internal total updates unconditionally every capture — a
slow reader must never drop or corrupt a count. Offered snapshot only
refreshes when free, keeping the standard shell protocol. **Free sign-
bit tap confirmed real** — two's-complement arithmetic means `diff<0`
needs no separate comparator at all. One testbench-timing bug found
(same class as before — a `#10` margin landed on an ambiguous edge,
making working logic look broken), fixed with a generous `#20` margin.
All 7 checks pass, including the two core claims: zero events lost with
a stuck consumer, offered value stays stable then correctly catches up
to the latest total.

Full regression: all 25 testbenches pass, zero regressions.

**Not yet done:** the comparator cell (`diff>=2×chain_length`) is still
unbuilt — one piece of the decomposition, not the whole thing. No
Quartus data. Equivalence against `sentinel_counter_v1/v2.v`'s own
established behavior not yet proven for the full assembly.

## Fourth architectural category named: HOST-INTERFACE (points.md #293)

Checked directly against `#253`'s own SHELL/CORE/ADDON definitions: the
sentinel's "hold and re-fire" accumulator mechanism (from Alan's own
recollection of the old fat cell's `one_shot` flag) is a genuine new
CORE — shell untouched, same lineage as ram/adder cores, just a
different capture-and-compute pattern. The ISSP bridge does NOT fit
ADDON (no cardinal ports, never joins the fabric mesh, wraps a whole
subsystem not one cell). **Fourth category, formally named: HOST-
INTERFACE** — no cardinal ports, bridges the fabric to something
outside it (JTAG today). Second independent example (after the
pre-existing `unicell_issp_bridge.v`), confirming it's real and
recurring. **Real cost, Alan's own flag:** baked into the bitstream at
synthesis time — no runtime toggle, using one means a full recompile +
reprogram cycle, which is exactly why every real hardware exercise
touching one needed its own dedicated Quartus project. How HOST-
INTERFACE components should eventually coexist with production builds
is deliberately deferred — "once some of these core items are tested."

## FIRST REAL HARDWARE CONFIRMATION of the sentinel system (points.md #291)

`Unicell-Q-sentinel-issp-test-v1` built clean, programmed onto the real
Arria 10, exercised live over real JTAG via `sentinel_issp.tcl`.
**Confirms `#287`/`#288`/`#290` simultaneously, on real silicon:**
power-on already shows `need_data/results_ready/safe=1` with no
configuration; `chain_length=0` correctly produces `err=0` (no false
overflow); the build compiles and the individual error-cause ports
read correctly over JTAG; command injection genuinely works
(`chain_length=4` set and read back correctly). **Not yet exercised
live:** `feed_pulse`/`collect_pulse`/`out_wrap_pulse`/`host_unfreeze_
pulse` — only the config command was tried; `diff` tracking and actual
error-triggering remain sim-only confirmed so far.

Also worked out in the same exchange: could the sentinel be built from
real fabric cells instead of a standalone module? Two counters (one
down-counting, making `A-B` computable with the existing real adder
directly — no subtractor needed) + the nano cell's proven 3-way
comparator, for the threshold checks. Real open question: genuinely 5
cells needed (2 counters + adder + 2 comparators, since one comparator
only checks one reference), not 4, unless time-multiplexed. If it
holds, this would make the sentinel a model-resident mechanism subject
to `#263`'s own ICM/VM-portability policy, not a separate peripheral —
not yet committed to, flagged as a promising direction.

## Real Quartus synthesis failure fixed: hierarchical references aren't synthesizable (points.md #290)

Real build hit `Error (10207): can't resolve reference to object
"out_frozen"` — the bridge's hierarchical debug references (`SENTINEL.
out_frozen` etc.) work in simulation but are a universal EDA
limitation, not synthesizable. Fixed: `sentinel_counter_v2.v` (clone)
adds real output ports for the two individual error causes (`err_
negative_flag`/`err_overflow_flag`) — `out_frozen` itself needed no new
port, it's already an exact alias of `need_data_flag`. Regression-
equivalence confirmed directly against v1's own test vectors. Bridge
updated to use v2 + the new ports. Full regression: all 24 testbenches
pass, zero regressions. Qsf updated. Real next step: rebuild, should
clear this error.

## Standalone Quartus project ready: `top_sentinel_issp_test_v1.v` (points.md #289)

Minimal wrapper around `sentinel_issp_bridge_v1.v` — no on-chip self-test,
driven live from the host via `sentinel_issp.tcl` once programmed.
`Unicell-Q-sentinel-issp-test-v1.qsf` prepared, elaboration-confirmed
in iverilog. **Will NOT compile until the real `issp` IP is generated
locally first** (IP Catalog → In-System Sources and Probes, `issp`,
Source width 66 / Probe width 113, Source Clock enabled, sync
registers enabled — same one-time setup as the existing `unicell_
issp_bridge.v`). Real next step: generate the IP, build, run
`quartus_stp -t sentinel_issp.tcl` — first real hardware confirmation
of the whole sentinel system.

## `sentinel_issp_bridge_v1.v` -- real JTAG access to sentinel status, found a real bug (points.md #288)

Alan's own ask, answered directly: a bridge exposing the sentinel's
status/error state over real JTAG (USB-Blaster), matching this
project's existing `unicell_issp_bridge.v` pattern (same source/probe
protocol, separate purpose-built file — the old bridge stays untouched).
Opcodes inject `feed_pulse`/`collect_pulse`/`out_wrap_pulse`/`host_
unfreeze_pulse`, or set `chain_length`; probe exposes every status/
error flag individually (including `err_negative`/`err_overflow`
broken out separately, as asked).

**Building it found a real bug, not by design review:** `chain_length`
starting at its natural reset default of 0 (genuinely unconfigured,
before a host's first command) trivially satisfied the overflow check
(`diff >= 2×0` = `0>=0`), incorrectly flagging an error before any real
operation happened — never caught before because the original sentinel
testbench always pre-set a nonzero `chain_length` from time zero, never
exercising the real unconfigured state. Fixed: overflow check now
requires `chain_length` to be genuinely configured (nonzero) first.
New `PART -1` test added confirming this exact scenario directly.

Real Tcl harness (`sentinel_issp.tcl`) written matching the established
`issp_unicell.tcl` pattern. Full regression: all 23 testbenches pass,
zero regressions.

**Not yet done:** neither bridge built in real Quartus (the `issp` IP
needs local generation first). `sentinel_counter_v1.v` still not wired
into any real chain — this lets the mechanism be exercised standalone
over real JTAG, full integration is separate, not started.

## Real shared-memory RTL: one BRAM, not two (points.md #282)

`mem_read_splitter_v1_ext.v` (clone, exposes its read command
externally instead of owning its own BRAM, mirroring how the combiner
already works) + `shared_bram_arbiter_v1.v` (write-priority arbiter,
one real `bram_controller_v1.v` shared). **Real problem caught before
it could cause silent data loss:** the splitter's single-cycle
`ext_cmd_valid` pulse would be lost forever if the arbiter couldn't
service it immediately — solved with genuine queuing (one outstanding
blocked read, retried the first cycle no write contends), safe by
construction since the splitter's own doubly-full guard already
prevents more than one outstanding request. One testbench race found
(same class as `#252`), fixed the same way.

**Critical case confirmed directly:** read and write requested the
EXACT same cycle — write wins, read is genuinely queued (not dropped),
serviced correctly once the write clears.

Full regression: all 22 testbenches pass together, zero regressions.

**Not yet done:** no Quartus data; not yet wired into a real end-to-end
topology with actual chains/trees (`#273`'s topology, rebuilt with one
shared memory) — proven at the arbiter level so far. JTAG-based host
access to this memory is separate, not started.

## `sentinel_counter_v1.v` -- first real sentinel-system RTL (points.md #281)

Standalone, reusable module per `#279`'s exact spec: `diff` = feed
count − collect count, `need_data_flag`/`results_ready_flag`/
`safe_to_intervene`, two sticky error latches (`diff<0`,
`diff>=2×chain_length`). Two real bugs found and fixed: a testbench
race (same class as `#252`, fixed the same proven way), and a genuine
RTL priority bug — error latches checked the fault condition before
`host_unfreeze_pulse`, so the flag silently re-latched instead of
clearing. Confirmed via direct per-edge tracing after reasoning alone
missed it twice. **Real insight confirmed by testing:** even after the
fix, pulsing unfreeze ALONE (without resolving the underlying
condition) still correctly re-latches the error — deliberate, safe
behavior, not a bug; the test's own expectation was wrong, fixed by
simulating a genuine recovery (drain first, then unfreeze).

Full regression: all 21 testbenches pass together, zero regressions.

**Not yet done:** no Quartus data; `out_wrap_pulse` detection and
`feed_pulse`/`collect_pulse` wiring into any real chain not yet built —
this is the core state machine proven in isolation, integration is next.

## THIRD constant-propagation trap: fixed DATA values collapsed the memory to 10 bits, not 40 (points.md #286)

`#284`'s registered-address fix genuinely worked — real Fitter Report
confirmed 40 M20K blocks, 655,360 bits used. But that same report's own
RAM summary showed **Port A/B Width: 10, not 40** — a real, separate
problem. Root cause, confirmed by checking the actual values: only 4
distinct 40-bit patterns were ever written across the whole design
(`VAL_A`/`VAL_B`/`VAL_C` and every routing stamp were fixed literals).
`#283` fixed the ADDRESS half of this trap; this is a THIRD instance
hitting the DATA half. Fixed: `VAL_A/B/C` → `pass_val_a/b/c`, XORed
with the already-varying `addr_offset`, and `EXP_RESULT1/2` made
combinational so the check stays valid. **Also a materially stronger
test now** — 46 passes exercise genuinely different arithmetic, not
the same 2 fixed sums repeated. Routing stamps deliberately left fixed
(legitimately bounded by the real 5-leaf tree topology, not laziness).

**Separate finding:** Alan's own Chip Planner GUI cross-check (clicking
through blocks 3 times) got inconsistent ownership counts each time
(9/13/15) — almost certainly a GUI refresh reliability issue, not real
hardware ambiguity. Resolved by using the static Fitter Report's RAM
summary table instead, which is what this whole diagnosis is actually
based on. Real caveat on `#277`'s own method: fine for a one-off
lookup, not demonstrated reliable for repeated cross-checking.

Full regression: all 22 testbenches pass, zero regressions.

**Not yet done:** not yet re-built in Quartus. Also unconfirmed:
whether `BRAM_IN` (the second memory) got its own real M20K allocation
— only one `ALTSYNCRAM` row was seen so far.

## `bram_controller_v2.v` -- fixes a real Quartus RAM-inference failure at hierarchy depth (points.md #284)

Real Quartus build (`#283`'s follow-up) showed `Info (276007): RAM
logic ... is uninferred due to asynchronous read logic` — 655,712 plain
registers instead of real M20K. Confirmed via direct research: a
documented Intel/Altera limitation — the same unmodified RTL infers
correctly at 2 hierarchy levels (`#265`) but fails at 3 (this build).
**Fix: `bram_controller_v2.v` registers the read address** (Quartus's
own canonical RAM template), the standard robust pattern. **Real
consequence: reads are now genuinely 2-stage, not 1** — Alan's own
layered-latency insight confirmed correct by direct testing: every
consumer already waits on `rdata_valid` as a genuine event, never a
fixed cycle count, so **zero changes were needed anywhere else** in the
system — confirmed empirically (identical pass timestamps before/after
the swap, not just asserted from code inspection). Two testbench bugs
found and fixed along the way (a stimulus pulse-width bug, and swapping
both memory instances to v2 for consistency).

Full regression: all 22 testbenches pass, zero regressions.

**Not yet done:** not yet re-built in Quartus — qsf updated, watch for
nonzero "Total block memory bits" this time.

## CORRECTION: `#280`'s Quartus numbers are NOT trustworthy — constant-address optimization trap (points.md #283)

Real Quartus build reported `Total block memory bits 0/43,642,880 (0%)`
— confirming the self-test's literal constant addresses (`0x10/0x11/
0x12`, never runtime-variable) let Quartus's optimizer collapse the
whole 64K-deep memory into plain registers instead of real M20K, same
trap `#249`/`#262` already solved elsewhere but wasn't applied here.
**`#280`'s 239 ALM / 219.59 MHz numbers should NOT be used for any real
planning — superseded by this entry, not silently replaced.** Fixed:
a genuine runtime-varying `addr_offset`, self-test now loops
continuously rather than running once. 46 real passes confirmed
correct in sim, each targeting a genuinely different address. Full
regression: all 22 testbenches pass. **Not yet re-built in Quartus —
real next step, watch for nonzero block memory bits this time.**

## `top_full_tree_system_v1.v` -- REAL Quartus project ready for `#273`'s full system (points.md #280)

Real synthesizable version of `#273`'s full tree system, iverilog-
confirmed. `mem_read_splitter_v1_test.v` (new file, clone of the
proven READ-only splitter with a debug write port added) lets a real
FSM seed A/B/C instead of the sim-only hierarchical backdoor. Two real
FSM bugs found and fixed via simulation before ever reaching Quartus:
a genuine race (checking a registered `ready_out` one cycle too early
after a pulse — first run reached S_RUN with zero results, zero
errors, confirming the failure directly), and a straightforward
missing step (C's value was simply never written to memory). Both
caught by refusing to trust reasoning alone and tracing signals
directly instead. **PASS after both fixes.** Full regression: all 20
testbenches pass together. **Quartus project
(`Unicell-Q-full-tree-system-v1.qsf`) ready — first real silicon
attempt for the complete assembled distribution system.**

## THE FULL SENTINEL SYSTEM -- both #257 open questions resolved (points.md #279)

Complete design, no RTL yet. "Farthest point" resolved: `addr_counter_
v1.v` already wraps to 0 automatically (no reset input exists), and
since every word is self-describing (`#258`), lap-start position is
irrelevant — wrap-to-0 itself IS the sync checkpoint. Freeze/flag
mechanism (Alan's own): OUT wraps → freeze + "need data" flag → host
reloads → unfreeze. IN naturally idles via existing ack discipline →
"results ready" flag once genuinely drained. **Host only acts on the
AND of both flags** — OUT alone doesn't prove the pipeline is drained.
Detecting IN's "genuinely drained" state precisely (not by idle-
timeout guessing, explicitly rejected): a sentinel counter,
`diff = A's feed count − B's collect count`, starts at 0, rises toward
`chain_length` during steady state, `diff==0` after OUT freezes = exact
finish, `diff<0` = impossible/error (freeze OUT), `diff≥2×chain_length`
= error (freeze IN). Compiler needs `chain_length` per model — but
this was always required anyway (disparate chains joining need
matching timing regardless of this mechanism), not new scope.
System-workbench-layer territory, not fabric RTL — flagged for
whoever picks it up next.

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

## THE FULL TREE SYSTEM -- genuine completion, both trees exercised at once (points.md #273)

Alan's own design, built exactly as specified: a single join only ever
produces ONE result, so a meaningful test needs 3 starter chains (A,B,C)
with B genuinely SHARED across two real joins. Built
(`tb_full_tree_system_v1.v`): SPLITTER → MUX_ROOT (2 direct leaves + 1
to MUX_CHILD) → 4 real relay stages → 2 real `adder_cell_v1.v`
instances (A+B, B+C) → COMBINER_ROOT (1 raw slot + 1 child slot via
COMBINER_RELAY) → BRAM(in). B read TWICE from the SAME address, routed
differently each time — genuine sharing, not coincidence. Exercises
every level built across `#266`-`#272` in one real pipeline.

Two real wiring bugs found and fixed, both in the testbench: a
floating-wire mistake (connected an adder's `ready_in` to a port that
doesn't exist on `combiner_cell_v2.v` — that module's input side has
no `ready_out` gate by design) causing a hang, and a test-sequencing
bug (a poll loop starting to watch for writes *after* both real writes
had already happened and gone by). Once fixed: **PASS on the first
run.** `result1=A+B=0x1234`, `result2=B+C=0x0284`, both hand-decoded
bit-by-bit against the design to confirm, not just trusted from the
test's own check.

Full combined regression: all 19 testbenches (everything built across
both sessions) pass together, zero regressions.

**Not yet done:** no Quartus data for any tree/distribution piece.
`#257`'s two open questions (farthest-point addressing, empty/full
status signal) remain untouched — system-workbench-layer concerns, not
blocking.

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



## DSP block locations confirmed real (points.md #274)

`find_resources_of_type "MP DSP"` (real Chip Planner Tcl command,
Alan found it directly) confirmed: DSP blocks form distinct vertical
column bands on `10AX066H2F34E2SG`, clustered with real gaps, not a
uniform mesh like the cell fabric -- confirms `#270`'s own framing
directly. Exact numeric coordinate extraction via Tcl (`get_node_info`
+ `get_info_parameters`) was attempted but inconclusive after several
real, confirmed-working API calls returned either the wrong list or
empty results -- stopped deliberately rather than keep guessing blind.
The qualitative column layout is treated as sufficient for `#270`'s
design reasoning; exact coordinates remain a nice-to-have.

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

1. **Quartus builds for the distribution-system pieces** — no Quartus
   data exists yet for any of `mem_read_splitter_v1.v`, `mux_cell_v1.v`,
   `combiner_relay_v1.v`, `combiner_cell_v1.v`/`v2.v`, or `mem_
   interface_cell_v1.v` (`#273`'s full tree system is only iverilog-
   proven so far). Real ALM/Fmax numbers are the natural next milestone
   now that the design is functionally complete and proven end to end.
   (`bram_controller_v1.v`'s own M20K inference is DONE, per `#265`.)
2. **The sentinel system — integration, not the core anymore** —
   `#281` built and proved the standalone `sentinel_counter_v1.v` core
   (freeze/flag/error logic). Still needed: `out_wrap_pulse` detection
   (watching `addr_counter_v1.v` externally — never modify that proven
   module), wiring `feed_pulse`/`collect_pulse` to real cell ack/
   capture events, and wiring `freeze_out`/`freeze_in` into real
   chains' own `freeze_in` ports. System-workbench-layer territory,
   not pure fabric RTL.
3. **Real cross-instance shared-memory write-then-read** — `#256`'s
   PARTS 1+2 test and `#269`'s full-pipeline test both still use
   SEPARATE `bram_controller_v1.v` instances for OUT vs. IN (matching
   `#257`'s own "two independent regions" design, not a shortcut) — a
   real round trip through ONE shared memory via the cell interface
   itself remains open, separate from that design choice.
4. **DSP bus-contention question from `#270`** — real column data now
   exists (`#275`-`#277`: DSP and M20K columns confirmed disjoint), but
   nobody has actually reasoned through the contention question using
   that data yet.
5. **Addon headroom work, now against a real baseline** — `#229`'s
   original plan (every future addon tested against a FULL-CARD build,
   real size+timing manifest) is now meaningful for the first time,
   since the 200MHz floor is a confirmed real number, not a phantom one.
6. **Two long-queued, never-run experiments** — `#206`'s
   OPTIMIZATION_MODE "Aggressive Performance" and `#200`'s duplication-
   flags diagnostic — now genuinely worth running against a trustworthy
   baseline.
7. **A real 3-level tree** — both the mux tree (`#271`) and combiner
   tree (`#272`) have only been proven at 2 levels; the design supports
   up to 3 (2-bit count field). Untested territory if more than 5
   read-destinations or 4 write-sources are ever needed.
8. **No software/loader path exists for any of the new cell types** —
   every `cfg_valid`/`cfg_data` load across `ram_cell_v1.v`, `adder_
   cell_v1.v`, `mem_interface_cell_v1.v`, `mux_cell_v1.v`, `combiner_
   cell_v1.v`/`v2.v`, `mem_read_splitter_v1.v` has been driven by
   testbench-only stand-ins. No real `loader_fsm_v3.v` integration, and
   the compiler/VM software side still only understands the old
   full-cell format — the real gap between "proven in isolation" and
   "actually deployable."

**Also still open:** the `#210` programming-delivery architecture
decision (single-hop/addressed vs. accepted broadcast) — `#247`'s
worst-path list showed the programming channel as timing-relevant with
real numbers for the first time, worth revisiting with that in mind.
The VM core rebuild (`#216`/`#217`, gap analysis at `current/
VM_CORE_GAP_ANALYSIS.md`) — still deliberately not started while RTL
settles. The BRAM+DSP hybrid integration (`#220`) — the RAM-cell chain
is its planned front door, per `#232`.
