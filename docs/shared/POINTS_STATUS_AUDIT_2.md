# points.md Status Audit, Part 2 — 2026-09-02

**Real, direct continuation of `POINTS_STATUS_AUDIT.md` (2026-08-16,
covered #1-#330). This part covers #331-#592 — the ledger has more
than doubled since the first audit, and per Alan's own explicit
request, this pass is organized around STATUS first (done / pending /
thought-direction), era second, rather than era-only like the first
pass. Same real discipline as before: this document does not edit
`points.md` itself; it's a curated map on top of it, split across
`points/` for the same reason this audit itself needed writing —
GitHub stopped rendering the ledger past ~2MB, and a project whose
own status-tracking doc needs a status-tracking doc is a real signal
worth naming, not hiding.**

**Method:** every one of the 262 entry titles in this range read in
full (titles in this project are consistently full real summary
sentences, not labels), grouped into six eras by real subject matter,
cross-checked against `current/latest.md`'s own real recent-first
cascade for anything still open. Spot-checked several entries in full
text where the title alone left the real status ambiguous.

---

## Quick reference: what's actually pending or open RIGHT NOW

The single most useful thing this document can do is answer "what's
queued" without reading 262 entries. As of this writing:

**Real Quartus builds queued, awaiting a result (all in `points/
points_active.md`):**
- `top_moat_tile_v1.qsf` (#588/#589) — Alan's own moat idea, pattern A,
  currently building as this document is being written.
- `top_unicell_super_test_v8.qsf` (#592) — the cumulative compare +
  latch + accumulator config-redundancy result.
- `top_array_v3_10cells_llfix_v1.qsf` / v4 equivalent — the middle-
  headroom LogicLock question is still open (#583/#585 only tested
  AUTO_SIZE and 25% headroom; nothing in between).

**Real, named next steps, not yet built:**
- Roll the config-off-shell fix (#584/#587/#592) out to the remaining
  5 cores (ram, adder, sequencer, branch, nano) — explicitly deferred
  pending whether accumulator's own wider config budget clears the
  real build-to-build noise floor #591 found.
- Moat pattern B (shared moats between neighboring super-cells, Alan's
  own "may prove a new type of beast altogether") — explicitly gated
  on pattern A (#588) actually working first.
- `#581`'s free-input isolation experiment (real Quartus target built,
  never actually run — genuinely still open, easy to lose track of
  since #582-#592's own LogicLock/moat/config-redundancy threads all
  happened after it).

**Real, genuine thought-directions on record, no build started:**
- Clockless/asynchronous UniCell model (#560), matching Wave
  Computing's own DPU architecture — flagged as potentially a better
  fit for a future Tiny Tapeout ASIC path than the current FPGA target.
- LLVM IR → substrate compiler path (#547) — a real, long-standing
  intent, named explicitly, not started.
- AI training buckets (#510/#511) — a real roadmap item tied to
  `vm_ai_port_v1.py`'s own docstring, not started.
- Multi-card scaling / PCIe switched backplane requirement (long-range
  vision doc, #503) — real, hard requirement confirmed, no hardware
  acquired.

---

## Era 6: VM/Compiler/tile-library/workbench build-out + repo honesty pass (#331–#369)

**Status: DONE, and a real, deliberate dead end simultaneously — both
true at once, not a contradiction.** This era built a genuinely
complete Unicell-S DSL compiler (lex/parse/resolve/place/emit,
`#343`), a frontend-agnostic ProgramIR proven against two real
frontends (`#344`/`#348`), a working interactive workbench (`#362`/
`#363`), and a real tile library with nested composition (`#340`-
`#342`). **Then #365's own real project-scope recalibration by Alan
("accelerator card at best, novelty at worst") led directly to
archiving nearly all of it** — 20 files at `#364`, the full remaining
sweep at `#365`, then 151 more files across 9 folders at `#366`. This
is not wasted work being hidden; it's real, working software that
stopped being the right investment once the project's own real scope
sharpened. Safely historical — the current active line (RTL cores,
`project_assemble_v1.py`, real Quartus builds) descends from what
came AFTER this era, not from this era's own compiler stack.

**One real item worth a conscious look, not obviously dead:** `#368`/
`#369`'s own README and GitHub Pages honesty rewrite — worth
reconfirming still accurate given how much has been built since
(the `v3` shell, real silicon confirmations, the shared-storage
thread). Not urgent, but a stale public-facing doc is a real,
different kind of risk than a stale internal one.

---

## Era 7: Priority-list execution + DSP integration research (#370–#399)

**Status: mostly DONE.** Alan's own real, direct prioritization at
`#370` (parser error recovery, `define` forward references, a C
frontend, a loader/binder, manual rebuilds, DSP-column-aware
placement) was executed item by item, `#372`-`#377`, each confirmed
working. Two real architectural conclusions came out of this era and
are worth remembering as settled, not open: **TRIX is not viable on
this substrate at all** (`#370`, sharpened further at `#384`), and
**branching has a real, non-trivial cost** on this model (`#370`,
resolved into the actual branch cell design later in Era 10).

**Real DSP groundwork done here, still directly relevant:** the
Arria 10 DSP-chain-vs-BRAM-connectivity asymmetry (`#379`, verified
against real Intel docs), and the architectural conclusion that DSP
integration needs a dedicated specialist wrapper core type, not a
mode on an existing core (`#380`) — this is the real design that
`dsp_add_wrapper_v1.v` etc. (Era 9) actually built.

**Real, still-open thread from this era:** `#388`/`#389`'s chaos-
topology tool found that closed relay loops, not heartbeat cores,
keep random topologies alive — a real, structural VM finding. `#394`
(itself a real, minor ledger anomaly — the number is used twice for
two different, real entries, both about the same idea) flagged
extending the tool into a first-class capture capability for others
to analyze later. Never built. Genuinely low-stakes, worth a
conscious "still wanted or not" rather than silent drift.

---

## Era 8: RAM interface / collector / sentinel / shared-BRAM + first real JTAG bring-up (#400–#448)

**Status: DONE, and the real, first hardware-confirmed milestone of
this entire project.** This era is dense and foundational:

- The full 27-leaf (3×3×3) hierarchical collector tree proven at the
  VM level (`#402`), then a real, self-contained Quartus top-level
  built (`#403`) and measured (`#407`: 274 ALM, 235.96 MHz).
- A real, fundamental architecture correction mid-stream, not
  defended past its own evidence: real BRAM has only 2 ports, which
  is why the header/collector/combiner design needed a genuine
  shared-BRAM redesign (`#412`/`#413`), not a patch.
- **`#441`/`#442`: the FIRST real, host-driven (not self-test-FSM)
  hardware in this project's history — real BRAM read/write and real
  ICM loading, proven on actual silicon, first try, zero failures.**
  A real, honest failure at `#444` (erratic results) was correctly
  diagnosed as "most likely IP/hardware integration, not RTL" before
  being explained at `#445` as simply forgetting to reprogram the
  card after the last compile — a real, human, worth-remembering
  failure mode, not a design flaw.
- `#447`: DDR4 (when built) connects via BRAM as an intermediate
  buffer, not a direct fabric link — a real, settled architectural
  answer to a question `#382` had explicitly left open.
- `#448`: a real, measured, important finding — the JTAG bridge, while
  PCIe remains unavailable, is a bring-up/correctness tool ONLY, not
  remotely viable for GB-scale staging. Still true; still the reason
  PCIe stays on the long-range roadmap rather than being treated as
  optional polish.

**Nothing genuinely open from this era** — it closes cleanly into
Era 9's own MAN/SHAPE/placement tooling work, built specifically
because this era's own real hardware success made a real "what does
the card actually look like" question worth answering formally.

---

## Era 9: MAN/SHAPE/placement tooling + DSP wrapper hardware (#449–#480)

**Status: DONE, real hardware confirmed on the DSP side; the
placement/shape tooling is real and working but explicitly scoped as
partial (only what's needed so far).**

- The first real MAN file (`docs/man/mustang-f100-a10.man.json`,
  `#450`) and SHAPE extractor (`#451`/`#452`/`#455`) — this is the
  same real MAN file `project_assemble_v1.py` (Era 12) still uses
  today. Not superseded; foundational and current.
- `#456`/`#457`: a real, honest two-attempt process to close the
  physical-placement gap — Back-Annotate tried first and found
  genuinely insufficient on real hardware, Quartus's own Control
  Signals report used instead, `placement_extract_v1.py` built and
  proven. Worth remembering the FIRST recommendation didn't work,
  in case it resurfaces as a suggestion later.
- **Real DSP hardware confirmed working, `#472`**: fire/ACK/re-arming
  all correct on actual silicon, after two real, honest IP-name
  corrections found from real Quartus build failures (`#469`/`#471`)
  — the IP Alan actually had access to
  (`altera_nios_custom_instr_floating_point_2_multi`) was NOT what
  `#462` had originally researched and assumed available. A real,
  concrete lesson: confirm the ACTUAL available IP before writing
  RTL against a name found in documentation alone.
- `#479`: the real, final five-tool pipeline architecture (Composer →
  Walker → Compiler → VM → Tile Designer) — still the current, agreed
  shape of this project's own tooling, referenced correctly in
  system-level memory today.

**Real, genuinely still-open item, not lost but not actioned either:**
`#477`'s own real, future documentation task — full per-file
documentation for every individual `.v` file. Named explicitly by
Alan as future work, not started, no urgency signaled since.

---

## Era 10: Branch/comparator core design + VM tooling (Tile Designer, checkpointing, ICM v4) (#481–#519)

**Status: DONE and directly ancestral to the CURRENT active shell
design.** This is where `branch_cell_v1.v` — the core every real
shell version from v1 through v8 still uses today — was actually
designed and built.

- `#491`-`#497`: a real, iterative design process, not a single
  decision — three real corrections along the way (three-mode framing
  wrong, corrected to a per-outcome table at `#493`; the held-
  reference optimization needed to make the 42-bit `core_config`
  budget actually fit, `#497`). `#500`: the first real RTL draft,
  sim-first, one real bug found and fixed before it ever reached
  Quartus.
- `#487`-`#490`: the real Tile Designer, the fifth tool in the agreed
  pipeline, built and iteratively extended per Alan's own direct
  requests (drag-to-connect, params UI, reciprocal auto-wire).
- `#482`-`#484`: real checkpoint/freeze/save/wipe/reload for
  DspWrapperCell, then generalized to full mixed-grid checkpointing
  across all 6 cores, and a genuine new ICM v4 format built to carry
  mixed-kind records (super-cell + DSP wrapper).
- `#508`/`#509`: two real, standing principles worth remembering as
  settled, not just historical — captured explicitly by Alan as
  permanent working rules, not case-by-case judgment calls.

**Real, still-open item:** `#513`'s own real, confirmed capability
gap — trigonometric/exponential functions are completely unsupported
today (checked directly, zero hits for CORDIC/sin/cos/tan/exponent).
`#514` added two standing queue items in response (a Designer
mechanism for loop-vs-chain workload choice, plus the gap itself) —
neither built yet.

---

## Era 11: Per-core headroom review + T-tree + real silicon confirmations across the board (#520–#551)

**Status: DONE, and the era with the highest density of REAL SILICON
CONFIRMATIONS in the whole project.** Alan's own systematic per-core
review (`#505`, "revisit each core individually for underexploited
headroom") produced real, working extensions to accumulator
(`#515`/`#516`-`#518`: variable step, pulse mode, THREE composed
applications — cascade counter, multiplication via repeated addition,
division via repeated subtraction — all zero new RTL, pure
composition per `#509`'s own method), adder (`#521`: ADD/SUBTRACT
mode), and latch (`#522`: TOGGLE input, plus nano's 5 previously-
hidden ports finally exposed through the shell).

**Then, in sequence, real silicon confirmed EVERY one of them:**
`#530` (branch, first ever), `#537` (accumulator pulse mode), `#539`
(adder subtract), `#540` (nano's exposed ports), `#541` (latch
toggle), `#549` (comparator's own first standalone target), `#550`
(branch through the real v3 8-core shell's own `core_select`
routing). **This is the real, empirical foundation every later
ALM/Fmax comparison in this session (#573 onward) builds on** — the
individual cores were already known-correct on real hardware before
any of the shared-storage or config-redundancy work started.

A real, genuinely valuable diagnostic finding from this era worth
remembering: `#537` found the original fixed-2-second JTAG poll
script had a real aliasing problem, fixed with `debug_issp_poll.tcl`
— still the correct tool to use for any future ISSP polling, not the
older fixed-gap script.

`#544`-`#546`: Alan's own real lane-split/recombine architecture idea,
proven both the positive case (equal hop counts) and a genuine
negative case (mismatched counts) in the VM, then the real 1→3→9
T-tree built and proven with all 9 leaves at exactly equal depth. A
real geometric collision was found and fixed BEFORE running, not
after. **Genuinely proven at the VM level; never built in real RTL or
measured on real Quartus** — worth remembering this is a VM-level
proof, not a hardware-confirmed one, if it comes up again.

---

## Era 12: project_assemble_v1.py genesis + the single-core-type real dataset (#552–#572)

**Status: DONE.** The real origin of the tool this whole current
session's own work depends on. `#552` built it; `#554` found and
fixed a real, serious anti-pruning bug (a 500-cell build had come back
at a catastrophic, wrong 13 ALM); `#567`/`#569` added the version-
agnostic core path and single-core-type generation mode; `#568` found
and fixed a real bug (wrong instantiated module names, affecting all
8 core types identically). `#572`: the real, complete N=10 dataset for
all 8 single-core-type arrays — the real, direct, first answer to
"what does full runtime reconfigurability cost" (roughly 4.4-4.9x
versus 8 fixed, dedicated cells) that `#579`'s own later full-shell
finding echoed independently from a different angle.

**Nothing open here** — this era closes directly into the current
session's own work (Era 13 below), which is the SAME tool, extended
repeatedly (`--shell`, `--logiclock`, `--shell-file`/`--file-list`).

---

## Era 13: THIS SESSION — shared-storage exploration, LogicLock, moat, config-redundancy rollout (#573–#592)

**Status: the real, live, current work.** No audit needed for
"what happened" — `points/points_active.md` has the full, current
detail, and `current/latest.md`'s own cascade is accurate and
current. What THIS document adds is the STATUS lens the quick-
reference section above already gives. Worth one real, connecting
observation here that's easy to lose across 20 dense entries: the
whole shared-storage thread (`#561`-`#585`, spanning back into Era 12
at `#561`) reached a real, negative-but-valuable conclusion — v4/v5's
shared external storage costs more than it saves, on every real axis
measured (ALM, Fmax, register-scaling behavior, AND placement-
constraint tolerance, `#585`'s own real fourth finding). **The config-
redundancy thread (`#584` onward) and the moat thread (`#588` onward)
are both real, separate, still-open investigations that started only
AFTER that conclusion was reached** — worth keeping straight that
these are not attempts to revive shared runtime storage; they're
different real mechanisms (config-only sharing, physical placement
fencing) explored independently, per real, explicit reasoning for why
each one doesn't share v4/v5's own specific failure mode.

---

## Summary: what this audit actually changes

**Nothing in `points.md`/`points/` itself**, same discipline as the
first audit. The real value is the same too: connective and
status-clarifying, not corrective. The single most useful output is
the quick-reference section at the top — five real queued builds/next
steps and four real thought-directions, pulled out of 262 entries so
they don't need re-finding by scrolling.

**One real, structural observation worth Alan's own attention:** this
project's own documentation-about-documentation has now itself needed
splitting and auditing twice. That's not a criticism — it's a real,
direct signal of how much real, working progress has actually
happened (592 entries, real silicon confirmed dozens of times over,
a five-tool pipeline built and used) — but it's worth treating as a
genuine data point on `#477`'s own still-open "per-file documentation"
item and on how session catch-up itself scales from here.
