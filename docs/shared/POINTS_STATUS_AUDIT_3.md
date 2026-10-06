# points.md Status Audit, Part 3 — 2026-10-06 (#593-#997)

Part 3 continues `POINTS_STATUS_AUDIT.md` (#1-#330) and
`POINTS_STATUS_AUDIT_2.md` (#331-#592). Like part 2, it is organised
**status first** (done / pending / thought direction) and **era
second**. It is a map on top of the ledger and does not edit it. The
ledger wins wherever they disagree.

**Method:** I read all 401 entry titles in this range. Titles in this
project are full summary sentences. The full text was read for
#875-#997, and wherever a title left the status unclear. Each "open"
item below was then checked for a later entry closing it. Two kinds of
open item are kept apart:

- **Open now:** named as open in the most recent entries (#946-#988).
- **Last recorded open:** listed in a "real queue" up to about #886
  and not mentioned since. The Tang Nano line took over the queue at
  that point, so these are neither closed nor actively scheduled.
  Check the cited entry before relying on one.

**#990** is claimed by `main`'s "WIP #990" commit (the fp adder from cells), which had no ledger entry when this audit was written. Its open items are the fp-on-cells items below.

Where the ledger itself says a number is used twice or skipped (#824
twice; #893 and #902 never used), see `points/INDEX.md`.

---

## Quick reference: what is open right now

**fp on cells (the active thread, #982-#989).** The open fp assembler
(#989, `tools/fp_assembler_v1.py` + `tools/flex_layout_v1.py`) now builds
the normalise, align-with-sticky and round blocks for any format (fp32,
fp16 and bfloat16 given). The composition align → round is proven, and
`balance()` replaces the hand timing fixes. The blocks still missing are:
unpack, swap-larger-first, the effective add/sub choice, the significand
add/sub using the second port's carry, the rounding-overflow exponent
bump, pack, and zero/sub-normal/inf/nan. Then assemble one whole fp add
and compare it with `fp32_add_v1`. Also open: a placer that decides
positions itself (block layouts are fixed templates today), a VM
tick-latency model for the layout engine, and a 64-bit build (with a
6-bit shift field) for fp64.

**Width (#948, #957-#963, #985, #970).** The `--icm` generators build 32
bits only. Still to do: native-width builds, the loader's narrowing, the
save's padding, and the `min_bit_width` fit check (#959). The Tang's
spare-bit sign encoding is undefined. A 6-bit shift amount is needed at
W = 36. The v4/v4c/`CACell` nano width is open, including the question
of whether the 128-bit command word grows (#963). The flex sequencer
does not build below 8 bits.

**Second outputs (#976-#981).** The DAG dispatcher cannot pick a second
word's consumer. There is no automatic trigger from the program graph
(LLVM `uadd.with.overflow`, a wide `mul`). Also open: MAN cost rows for
port-on cells, and a pairing rule for a pair-cell consumer of both words.

**VM (#927, #960-#961, #947, #986).** Start-up flags (`vm flex -w36`), a
target profile, and a count estimator. The std VM's raw-unsigned
negative comparator threshold. Automatic coarse + fine shift splitting
for std targets.

**Cells and generators (#957, #988).** A genuine `priority` arbiter on
flex. `command` in sub/flex. Place-and-route of whole generated designs.
A per-merge mode carried in the ICM. (Operand-arrival ties are now
balanced automatically by `flex_layout_v1.balance()`, #989.)

**Hardware.** No sub/flex design has run on the board yet. The ESP32
pins and SPI link (#888). The `BTN_RST_N` root cause (#896). Whether the
Kintex 480T can be revived (#928). Whether Arria 10 hard-DSP offload is
still a goal (#943). The VIX Carrier has never been built in Quartus
(licence expired, #649).

**Decisions waiting on Alan** (recorded, not taken): whether the
sub sequencer should support host-tick pairing on purpose (#937); and
whether single-shot preloaded constants should be reproduced on purpose
(#939).

## Last recorded open (in the queue up to ~#886, not revisited since)

- **Reconfiguration / fold thread:** the triggered sequencer and a
  controlled command mode with a direction-carrying Start
  (#873/#874/#882). Also: per-direction ack in the VM, a feedback path
  so a fold is genuinely iterative (#882), computed command words
  (#883), the RTL path for `hold_in`/`a_reemit_in` (#879/#880), N passes
  beyond two, and an overflow indicator for grid-native paths (#877).
  Measured context: at small scale the fold loses to a static pipeline
  on time and cells (#885).
- **LLVM frontend:** the memory mapping (`load`/`store`/arrays onto the
  existing mechanisms, #830); the LLVM gap list.
- **VIX Carrier:** a VM model of `v1d`'s live add-on reprogramming
  (#841); the VIX backlog (#824); VIXb mutable core count (#735).
- **Ideas not started:** paired command-bus cells (#835/#836); an N-way
  sort network (#837); MIN/MAX via `branch`. The collapsed-assembler
  idea (#838) is largely realised for the sub/flex families by the
  Flex-Sub assembler (#921-#957), which bakes each cell's function in at
  build time.
- **fp:** the width-expansion scope (fp16/fp8/fp64, #852), filed as
  future work. #848's reminder to check the fp functions against real
  silicon still stands. The cell-built stages (#982-#988) are now the
  path to that.
- **Docs:** #829 and #856 asked for a full documentation update. The
  first was done at #991-#997. #856 asks for another full pass **once
  the fp32 work is complete**, which it is not yet.

## Thought directions on record (no build)

A virtual, card-decoupled and 3D substrate (#604). Photonic and
die-to-die interconnect paired with the VIX Carrier (#831-#834). Pond
boundaries and typed bridge cells from the old system (#671/#672). The
TRIX family's unifying vision (#698). The LaTeX-equation path (#691,
#744). External output confirmation via `io_name` (#715). Free-format
projects and workspaces (#754/#755; the checkbox was built at #766). The
pattern-library escalation ladder (#752). The Composer full editor and
the AI training buckets (#677; buckets' first slices were built at
#681/#682).

## Closed in this range that part 2 had listed as open

Part 2's queued Quartus items (the moat tile, #581's free-input
experiment, the v8 config-redundancy build, LogicLock headroom) were
overtaken. #595 measured the moat (it costs more), and **#596 closed
the Arria 10 hardware exploration track by Alan's decision**. The
config-off-shell rollout to the remaining cores was completed at #699.
The LLVM IR compiler path (#547) was built from #610 onward. The
"clockless" direction is restated at #995: a timing pulse schedules
transfers, the cell internals are unclocked, the ack controls flow, and
freeze decouples cells.

---

## Era 14: Hardware closure, the simulated Walker, workbench/Composer (#593-#609)

**Done.** Part 2 of this audit and the session close-out checklist
(#593/#594). The moat result and the deliberate closure of Arria 10
hardware work (#595/#596). VM mirror mode and the simulated Walker,
wired into the front end (#598-#602). The workbench as a checked
reflection of an assembler config. Composer's first build. ICM save/load
in the workbench (#605-#607). `branch` and `sequencer` Tier-0 tiles,
with sequencer VM dispatch (#608/#609).

## Era 15: The LLVM IR frontend (#610-#638, #650-#654, #661, #668, #674, #686-#718)

**Done.** Scope (#610). First frontend (#611). The archive's old
frontend read for what transfers (#612). `icmp` (#613), `select`
(#629/#630/#633/#674), `eq`/`ne` (#634/#668). Counting loops on a 4-cell
ring, ascending and descending (#635-#638, #652/#653, #661). Composed
Tier-1 tiles and freeze/preload persisted in ICM v3 (#686-#688).
`shl`/`lshr`/`ashr` (#690, #702-#705, #708/#709). General DAG data flow
through hold+trigger relays, with any number of consumers (#700/#701,
#706, #710-#717). Bitwise `and`/`or`/`xor` (#718). Scope notes: the
completion roadmap (#689) and LaTeX (#691).

## Era 16: Unified carrier cores, cardinal shells, the command core and the VIX Carrier (#617-#627, #639-#649, #655-#660, #665/#666, #683-#685, #699, #719-#735)

**Done, simulation only.** The unified-carrier `_v4` cores, all 8
(#617-#626), with a capability table (#627). Cardinal control shells
(#639/#640, #645/#646). The command core, designed (#628, #641-#643)
and built (#644). The VIX Carrier RTL (#647), its `--shell vix`
assembler path (#648), and VM (#655-#657, #660). Carrier-to-carrier
programming and core-select via live programming in RTL (#665/#666).
The fine shift for all shells (#683/#684). The add-on chain moved into
the carrier correctly (#719-#723). `mul` and `priority` as the 10th and
11th cores (#724/#726, #727/#730/#731). `fpga/verilog/` reorganised
(#728) and the tooling caught up (#734). VIXb scoped (#735).
**Pending:** Quartus/silicon for this family has never been run.

## Era 17: Archaeology, audits and training buckets (#632, #659, #662, #670-#673, #676-#682, #697/#698)

**Done.** The archive inventory (#632). TRIX first look (#659). The
"176 cells" claim corrected (#662). The orphaned-work audit (#676) and
scope notes (#677). The docs/static-pages audit and refresh
(#678/#679). The training-bucket structure and exporter (#680-#682).
MIF prior art (#697). **Thought directions:** Pond and bridges
(#671/#672) and the TRIX vision (#698).

## Era 18: Hierarchical ICM (ICM-VIX), CORDIC, roadmap (#736-#749)

**Done.** The carrier build frontend's two modes (#736). The ICM-VIX
design: patterns, addressing, prototype and examples (#737-#741). A
CORDIC design with five bugs found and fixed (#742). Compiler-facing
lessons (#743). The roadmap (#744/#745). LLVM side scoped (#746).
ICM-VIX formalised and wired into the workbench (#747). The VIX tile
library (#748). Gotchas as a static check (#749).

## Era 19: DAG compilation, convergence and the dispatcher (#750-#803)

**Done.** The smallest DAG solved by hand (#750). `priority` as the
convergence tool, and its operand-order limit with two fixes: path
equalisation (#771) and a VM-only sequenced mode (#772) (#751, #769-#775).
The rat's-nest router, tightening and the symbolic timing model
(#760-#765). Convergence points are defined by the compiler (#767). The
convergence shape catalogue and orientation cost (#776-#778). The DAG
dispatcher, rebuilt on Alan's correction (#779/#780). Core-by-core role
tests (#781-#790). Library entries (#792/#793). `compile_dag()`'s first
frontend (#795) and the opcode ports (#797/#798). Unnamed SSA values
(#799). Virtual-space placement (#800). Loop unrolling (#801). i1 logic
(#802). If/else via `phi` (#803).

## Era 20: Card fit, routing, BRAM/DSP structures and host lifecycle (#804-#826)

**Done.** Card fit with fixed DSP/BRAM sites, units corrected (#804,
#806). The PathFinder router (#805). The BRAM/DSP dispatch and gather
trees, placed, with separate read/write ports (#807-#809). Counter
feedback, the planarity limit, and ack-driven address supply
(#810-#813). The priority cell on a shared bus, DSP chains as monitored
black boxes, and Arria 10 DSP chain placement (#814-#819). Credit-return
decoding (#820). The host stall/refill lifecycle (#821). DSP latency
lowering (#822). The VM mirror in the LLVM path, plus a new CLI and a
serialization gap closed for `mul`/`priority` (#824/#825).
Store-and-shift (#826).

## Era 21: Floating point (Python models), mul's second output, ideas (#827-#857)

**Done.** TRIX/MIF prior art (#827). fp32 pack/unpack (#839), compare
(#840), add (#844/#845), round-to-nearest-even bit-exact over 1,000,000
pairs (#847), multiply (#849), divide (#851) and min/max (#857). The G/R/S
split construction (#846). `mul_cell_v5` with its high word, and the
VM (#853/#854). The carrier `v1d` with live add-on reprogramming (#841).
The cheat sheet (#842). The change-impact map (#855). **Thought
directions / ideas:** interconnect (#831-#834), paired command-bus cells
(#835/#836), the collapsed assembler (#838), and the fold thread (#843).
The postcode sort was re-measured (#837).

## Era 22: The reconfiguration loop and the fold (#858-#885)

**Done, VM only.** The drain signal (#858), the command-word builder
and release gate (#859/#860), and the command cell's existing protocol
used instead (#861-#863). The loop assembled, closed, and made
value-independent (#866-#872). Grid-native change detection and drain
events (#875-#878). The loop with no harness glue (#879). The actual fold
(#880). **Measured verdicts:** the fold's cost (#882), fp4096 (#883,
corrected by #884), and the stage pipeline against the fold (#885): at
small scale static wins on time and cells. **Pending:** see "Last
recorded open" above.

## Era 23: The Tang Nano 20K arrives (#886-#897)

**Done.** Cells sized for the GW2A (#886). The generated MAN (#887). The
ESP32-D host identified (#888). Real place-and-route (#889/#890). The
board's role decided: testbed and proof of concept (#891). The first
flashable bitstream (#892); the reset-button failure isolated
(#894/#895); **a UniCell core confirmed running on the physical board
(#896/#897)**.

## Era 24: The sub and flex families and the Flex-Sub assembler (#898-#945)

**Done.** The v4s cells, build-time config, DSP multipliers and the
time-multiplexed multiplier (#898-#902). The 18-bit alignment and the
target-agnostic seam (#903-#905). Ack + freeze added back for less area
(#906). Native flip-flops in the MAN (#907). Timing at scale and the
WIDTH parameter (#908-#910). The flex family built cell by cell
(#911-#918). The cross-target obligation ruled not live (#919/#920).
The assembler: step 1 (#921/#922), the netlist (#923), rulings (#924),
and `sub` generation completed through corpus, nano, merges, branch,
sequencer, level sources, wiring add-ons and loops (#925-#940). The
multiplier ladder and the MAN's DSP facts (#941-#943). Flex stages 1-2
(#944/#945).

## Era 25: Flex generation completed, -nowidelut, width and FlexGrid (#946-#973)

**Done.** Ledger sealed through #945 (#946). Flex stages 3-8: nano,
comparator, level sources, branch, merge (then a merge core), and the
sequencer (#947, #951, #953-#956). Merge trees and per-merge modes
(#957). `-nowidelut` measured and made the default (#948-#950, #952).
The `min_bit_width` flag and the strict-ICM ruling (#958/#959). VM before
fit, and the VM's data width (#960/#961). The nano variants compared
(#962/#963). FlexGrid steps 1-9, and four RTL limits found and resolved
(#964-#973).

## Era 26: Second ports, the capability table and fp on cells (#974-#989)

**Done.** Second output ports, the build parameter and the merge shape
(#974, #976). The accumulator cascade and the cost-vs-width sweep (#975).
Rulings (#977, #978). The compiler's request and one generic
`second_output` flag (#979/#980). The second word's own faces and the
per-target capability table (#981). The fp32 stage map (#982) and its
loop-free plan (#983). Left-normalise, sticky and RNE (#984). Any-amount
flex shift and per-target shift checks (#985/#986). Align, and align with
sticky (#987/#988). The open fp assembler: a layout engine with timing
balance and parametric fp blocks proven for fp32 and fp16. In the flex VM,
same-tick operands are no longer ORed (one is taken; a subtract raises
an error) (#989). **Pending:** see the quick reference.

## Era 27: Documentation and the public site (#991-#997)

**Done.** The reference docs (#991); the manual's source docs, including
two DSL examples that no longer compiled (#992); the static pages, with
an explainer bug fixed (#993); ledger numbering reconciled with `main`
(#994); the public site published with the explainer, and timing
described as pulse / ack / freeze (#995); remaining quick fixes, plus a
regression from #993 fixed (#996); this audit (#997).

---

## Summary

Of the roughly 400 entries in this range, nearly all record finished
work. In this project an entry is usually written when something is
built, measured or ruled on. The genuinely open work is concentrated in
three places:

1. **The active fp32-on-cells and width threads.** These have clear
   next steps.
2. **The reconfiguration/fold thread.** It was paused when the Tang Nano
   arrived. Its own measurements (#885) narrowed its purpose to rare,
   run-time retuning.
3. **Hardware runs.** No sub/flex design on the board yet, and no VIX
   Carrier in Quartus.

The next audit should start at #998.
