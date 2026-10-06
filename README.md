# Imago UniCell

A spatial compute architecture built on one principle: **topology is
computation**. There's no CPU, no instruction set, no shared bus.
Programs are described as physical topology — which of a fixed set of
hardware cores sits where, wired to its physical neighbors — and
computation happens as values arrive and propagate outward across that
topology, one hop at a time.

**Timing, in Alan's words (2026-10-06):** there is a timing pulse, but
it only schedules when data is passed from one cell to the next; the
cell internals are unclocked. Most designs use the two-arrival model (a
cell waits for both of its operands), so skew between paths can almost
be ignored. It is the **ack** that really controls flow. That is why
the **freeze** line works so well. It disconnects a cell's inputs and
outputs from the flow, so a frozen cell can be reprogrammed without
moving any data. Each cell's state can be captured and its latch values
stored as a series of data, to be reloaded at any time. Freeze also
stops a partly loaded design from pre-firing in a half-built state.

**What this is:** a research project building working pieces of a new
FPGA architecture, on real hardware, with measured numbers. It is not
a general-purpose computer, not commercially packaged, and not
something you can `pip install` today.

---

## Where things stand (October 2026)

The project has two hardware lines. The second one is where current
work happens.

1. **The Arria 10 line (2026-08/09)** — the super carrier shell
   (`unicell_super_v3.v`, 8 cores per cell) on an IEI Mustang-F100-A10.
   Every core was confirmed on that silicon over JTAG. A measured
   ceiling of roughly 200-250 cells on that card closed hardware work
   there (see [The Arria 10 line](#the-arria-10-line-the-super-carrier-shell-unicell-s)
   below). It is still the reference for the VM's standard ("std") mode.
2. **The Tang Nano 20K line (from 2026-09-28, ledger #886 onward)** — a
   Sipeed Tang Nano 20K (Gowin GW2AR-LV18, 20,736 LUT4, 48 18x18
   multipliers) arrived and hardware work resumed on it, with a fully
   open toolchain (yosys → nextpnr-himbaechel-gowin → gowin_pack). A
   UniCell core has **run on the physical board** (#896). Measuring the
   original cells on this chip showed they are far too large for it
   (one VIX carrier position is ~80% of the chip, #887), so two new,
   stripped cell families were built for it: **sub** and **flex**
   (below). The board's role is a testbed and proof of concept, not an
   accelerator (#891).

The ledger in [`points/`](points/INDEX.md) is the full record. Every
design decision, measurement and correction is there with its reasoning.
[`current/latest.md`](current/latest.md) has a one-paragraph summary per
recent entry.

## The active line: the sub and flex cell families (`sub/`)

Alan's direction for the Tang (#898): strip each cell down to its bare
compute function. That means no add-on chain, no 4-way cardinal
routing and no runtime routing decisions: "computing through physics,
not control." Every cell lives in [`sub/verilog/`](sub/verilog/) with
its own self-checking testbench. The full design record is
[`sub/README.md`](sub/README.md).

| Family | Files | What it is |
|---|---|---|
| **sub** (v4s) | `*_cell_v4s.v` | Fixed 32-bit, no handshake. Every cell has exactly one cycle of latency, so a design is timed statically: the generator pads early operands with relay cells. Add-ons (mask, shift, invert) become plain wiring. One result per cycle. |
| **flex** (v4sa) | `*_cell_v4sa.v` | `WIDTH`-parameterised (the Tang's native width is **18**, #903/#913), with a point-to-point valid/ack handshake and a global freeze (#906). No alignment or padding is needed; one item per two cycles per cell. |

Cells in both families: adder (add/subtract), multiplier (LUT, and a
DSP version using `MULT36X36`), comparator, accumulator, latch,
sequencer, ram, router, mask, shift stage, nano (the universal 2-input
gate), and branch. Flex also has a **merge** core (`merge_cell_v4sa`:
A only / B only / arbitrate / join-OR, #955).

Main results, all measured with yosys `synth_gowin` and, where stated,
real place-and-route:

- **Stripping pays.** For example, the adder went from 2,348 LUT4
  (full cell) to 66 LUT4 (v4s, #898). Fixing a config value at build
  time instead of loading it at runtime cuts further: a shift stage costs
  26 LUT4 against 3,261 (#899).
- **The handshake is cheaper than expected.** The flex adder with
  ack+freeze is 37 LUT4, against 66 for the no-ack v4s (#906); the
  nano shows the same (#917).
- **18 bits fits the chip.** ALU use scales exactly with width (32 → 18
  = 0.5625 on every arithmetic cell). A 100-cell 18-bit chain
  place-and-routes at 287 MHz against the board's 27 MHz clock (#910).
- **`-nowidelut` is the default Gowin flow** (#950/#952). It is about
  3x smaller across all families, and the LUT multiplier is ~3x smaller
  *and* ~3x faster. The card's MAN file sets the default; `--wide-lut`
  opts out.
- **Cost against width** for every flex cell at W = 4…32 is in
  [`docs/measurements/flex_width_sweep_975/`](docs/measurements/flex_width_sweep_975/)
  and in the Tang MAN's `cell_costs` (#975/#976). For example,
  adder = W + 5 LUT4 and nano = 7W + 33.
- **Second output ports** (#974-#981): the adder can deliver its carry
  and the multiplier its high word as a second word on its own port.
  That makes multi-word arithmetic work: a 64-bit add from two 32-bit
  limbs is proven in RTL. The port is a build parameter (`SECOND_PORT`)
  and costs nothing unless a design asks for it.

### From an ICM file to Verilog: the Flex-Sub assembler

The existing assembler (`tools/project_assemble_v1.py`) takes a family
flag and can read an ICM-VIX file as a map of the design:

```bash
# an N-cell chain of one flex cell type at the card's native width
python3 tools/project_assemble_v1.py -s flex -S adder --cells 100 --man docs/man/tang-nano-20k.man.json --output build/chain

# a whole design from an ICM-VIX file, as handshake (flex) or fixed-latency (sub) hardware
python3 tools/project_assemble_v1.py -s flex --icm nano/examples/cordic_z_convergence.icm-hier.json --man docs/man/tang-nano-20k.man.json --output build/cordic
python3 tools/project_assemble_v1.py -s sub  --icm nano/examples/parallel_reduction_tree.icm-hier.json --man docs/man/tang-nano-20k.man.json --output build/tree
```

The width comes from `-w`, else the MAN's `native_width`, else 32
(#914). The multiplier uses DSP blocks while the MAN says the card has
them, falls back to the LUT multiplier, and refuses if even that does
not fit (`--mul auto|lut|dsp`, #941/#942). Each merge's mode can be
chosen (`--merge-mode`, #957). Every compiled program in the test
corpus (41 programs, compiled from LLVM IR via
`tools/flexsub_compile_v1.py`) and the hand-built 36-cell CORDIC run as
generated Verilog. Each one's output equals the VM's and plain
arithmetic, under random stalls on flex. **Limits:** the `--icm`
generators still build 32-bit designs; genuine cycles (rings with a
data-dependent exit) are refused; on sub, a sequencer feeding a
two-operand cell is refused.

## The ICM stays target-agnostic

The program format never names a target or a family. It states what a
design *needs*, and each target either provides it or refuses:

- **`min_bit_width`** (#958/#959) is an optional header flag in ICM v3,
  v4 and VIX files: "this design needs at least N bits". If it is
  absent, the width is 32. Values stay sign-extended in the 32-bit
  fields. A target narrower than the flag refuses; it never truncates.
- **`second_output`** (bit 12 on adder and mul; `carry_mode` and
  `wide_mode` are accepted aliases) and **`second_downstream_mask`**
  (bits 13-16) ask for the carry or high word, optionally on its own
  faces (#980/#981). The compiler sets the flag only when a program
  needs both results; the default is off.
- **Shift amount** (#985/#986) is one number. flex makes any amount
  from 0 to 31 (it is wiring); std makes coarse taps plus fine; sub
  makes coarse taps only.
- **Per-target capability table** (`nano/target_capabilities_v1.py`):
  when a target is named, the compiler refuses at compile time what that
  target cannot do. With no target named, the ICM is produced unchanged.

Field tables: [`docs/stripped-cell/ICM_V3_FORMAT.md`](docs/stripped-cell/ICM_V3_FORMAT.md),
[`docs/stripped-cell/ICM_VIX_FORMAT.md`](docs/stripped-cell/ICM_VIX_FORMAT.md).

## The VM: std mode and mirror mode (`FlexGrid`)

Alan's ruling (#960): the VM comes *before* the fit, because a fit can
only be proved by a VM that can mirror the target.

- **std mode** (`SuperGrid(records, width=W)`) is the original VM,
  unchanged in behaviour. Since #961 it takes a data width (default 32).
- **mirror mode for flex** (`nano/flex_grid_v1.py`, `FlexGrid(records,
  width=W, merge_mode=...)`) is a subclass with its own per-core
  handlers. An empty `FlexGrid` is proved identical to `SuperGrid`
  (#965). Each flex core was then added and checked against the
  **generated RTL as the oracle** at W = 4, 8, 18, 32 and 36 (#966-#973).
  Where the RTL has a limit, FlexGrid refuses with the reason rather
  than guessing.

That work also found and fixed real RTL defects in the flex cells: the
nano and sequencer captured while unarmed (#956/#971), the comparator
threshold above 32 bits (it now has its own port, #972), the
accumulator below 16 bits (#973), and the mask above 32 bits (the mask
word now scales with the width, #968).

### fp32 on cells

[`docs/stripped-cell/design-notes/fp32_stage_map_second_ports.md`](docs/stripped-cell/design-notes/fp32_stage_map_second_ports.md)
maps an fp32 add and multiply onto cells in 16 stages (#982). These
stages are built from real flex cells, with no loops, and tested
RTL == FlexGrid == the Python model: unpack, carry → exponent bump,
multiplier high word → normalise bit, a 5-stage left-normalise with
exponent adjust, sticky, round-to-nearest-even (#982-#984), and
alignment: a variable right shift that also collects the sticky bits,
built from one multiplier per stage using both of its output words
(#987/#988). An open fp assembler (`tools/fp_assembler_v1.py`, #989)
generates those blocks for any format (fp32, fp16, bfloat16), with
operand timing balanced automatically. **The whole fp adder is now
built from flex cells** (`tools/fp_add_v1.py`, #990). In generated RTL
it matches a reference anchored to `fp32_add_v1` on 3,000 pairs, for
normal numbers and zero. To route it, a new **crossing tile** (`cross`,
ICM core 10, #999) lets one lane pass straight over another: pure
wiring, with no state or latency. Still open: sub-normals, overflow, inf
and nan; formats wider than 32 bits; and a placer (layouts are hand
templates today).

## On the physical board

[`docs/man/tang-nano-20k-getting-started.md`](docs/man/tang-nano-20k-getting-started.md)
covers the first flashable deliverable, a `sequencer` core counting on
the LEDs. It is built from source to a committed bitstream
(`fpga/build/unicell_tang_nano_20k_smoke_v2.fs`). It is **confirmed
working on the physical board** (#896); use v2, because v1's reset
button held the design in reset. The board's MAN file
(`docs/man/tang-nano-20k.man.json`) is generated from the chip database
rather than written by hand. The planned ESP32 host link (an
ESP32-WROOM-32E) is not wired yet (#888).

---

## The Arria 10 line: the super carrier shell (Unicell-S)

*This was the active line until 2026-09; it is now the earlier line (see
"Where things stand" above). It remains the reference for the VM's std
mode and for ICM v3/v4.*

The **super carrier shell** is — a
single physical FPGA cell that holds multiple real, different cores
simultaneously, with the active one chosen by a runtime configuration
write (`core_select`), not a synthesis-time choice. Every core is
always physically present in every bitstream; only the selected one
ever does real work. Cells wire directly to their North/South/East/
West physical neighbors — there is no addressed bus anywhere in this
design.

**`unicell_super_v3.v` is the recommended baseline for this line** — the
real, cheapest, fastest, and most placement-tolerant of every shell
version built and measured, confirmed across four independent real
axes (ALM, Fmax, register-scaling behavior at array scale, and
tolerance of physical placement constraints). It holds 8 cores (nano,
RAM, adder, accumulator, comparator, latch, sequencer, branch), each
with its own separate, dedicated internal storage:

| Shell | Real change from v3 | Real N=1 ALM / Fmax | Real N=10 array avg (ALM/cell) |
|---|---|---|---|
| `unicell_super_v1.v` | 6 cores (original) | 233 ALM / 129.48 MHz | not measured at array scale |
| `unicell_super_v2.v` | +sequencer (7 total) | 305 ALM / 99.57 MHz | not measured at array scale |
| **`unicell_super_v3.v`** | **+branch cell (8 total) — current baseline** | **479 ALM / 107.05 MHz** | **1030.5 ALM/cell / 68.5-75.1 MHz** |
| `unicell_super_v4.v` | shared external storage (1 register for all 8 cores) | 708 ALM / 96.9 MHz | 1307.4 ALM/cell / 58.6 MHz — **costs more, not adopted** |
| `unicell_super_v5.v` | v4's storage, written per-bit instead of one wide mux | 721 ALM / 95.0 MHz | not measured — **ties v4, not adopted** |
| `unicell_super_v6.v`/`v7.v`/`v8.v` | 3 cores' own config fields read live off the shell instead of re-latched locally | 483-487 ALM / 96-107 MHz | not measured — **one core (compare) shows a real, solid win; the other two are inconclusive against normal build variance** |

**Real, honest summary of that exploration:** v4/v5's shared-storage
idea was tried, measured, and found to cost more than it saves — a
real, negative, useful result, not a dead end hidden from view. v6-v8
found one small, real, confirmed win (the comparator core) and two
inconclusive results, closed for now rather than chased further.
Full detail, including every real Quartus number behind the table
above, is in the ledger (`points/points_07_572-652.md` onward; see
`points/INDEX.md`).

(target: IEI Mustang-F100-A10, Arria 10 GX, 10AX066H2F34E2SG, 25 MHz
fabric clock)

**Every one of this project's own core capabilities has real,
independent, JTAG-based functional confirmation on actual silicon** —
not just simulation, not just "Quartus compiled it" — via a real
In-System Sources and Probes debug channel built specifically to give
an unambiguous pass/fail regardless of whether a given board's own
LEDs are reliably wired (a real uncertainty found and worked around
early in this project). Branch cell in particular went from zero real
hardware history to fully confirmed — standalone, and through the
real v3 shell's own `core_select` routing — in one session.

For full detail, see [`docs/stripped-cell/SUPER_CELL_INTERNALS.md`](docs/stripped-cell/SUPER_CELL_INTERNALS.md).

## The Arria 10's scale ceiling, and why hardware work on it closed

**This card's own real, measured ceiling is roughly 200-250 cells,**
at a real Fmax of 65-75 MHz at that scale (251,680 ALM / ~1030 ALM per
real cell, `unicell_super_v3.v`'s own array-scale measurement — every
alternative design tried costs more, not less, per cell). That Fmax
is a genuine ~2.5-3x margin over the card's actual 25 MHz fabric-clock
requirement — functionally comfortable — but 200-250 cells is not a
large substrate by any real measure, and a systematic investigation
(shared storage, config-sharing, physical placement constraints, a
"moat" of small buffer cells around each super-cell) found no lever
that moved this ceiling by more than a small amount, let alone an
order of magnitude.

Multi-card scaling remains real and possible in principle (a switched
PCIe backplane, not the direct card-to-card link this device's own
transceivers can't provide), but reaching a genuinely serious workload
that way would need tens to hundreds of cards and the enterprise-class
backplane infrastructure that implies — a real, honest cost that
undercuts the point of a small, novel compute substrate rather than
fulfilling it.

**Conclusion at the time: this project's near-term identity is a
small, correctness-proven hardware platform, not a compute
accelerator in any competitive sense.** Hardware exploration on the
Arria 10 was closed as a deliberate result. (Hardware work has since
resumed on a different, smaller board, the Tang Nano 20K, as a
testbed: see "Where things stand" above.) The genuinely promising path to real scale is a future custom
ASIC (matching this project's own clockless/asynchronous architecture
ideas, closest in spirit to Wave Computing's own DPU design) —
confirmed as real and worth pursuing eventually, and confirmed as not
a near-term undertaking. Ongoing work continues on the VM and
tooling side, where scale and design exploration remain genuinely
free of any real hardware ceiling.

## The software stack (shared by both lines), and how it's verified

Everything below lives in [`nano/`](nano/) unless noted, and every
piece states plainly whether it's simulation-only or independently
confirmed on real hardware — that distinction is kept honest
throughout the project's own documentation, never blurred.

- **ICM v3/v4** — the program format: real `SUPER_LATCH[79:0]` encode/
  decode, verified two independent ways (bit-for-bit against real,
  iverilog-compiled RTL test vectors, and mechanically re-derived
  straight from the RTL's own comments). ICM v4 extends this with a
  second real record kind for DSP wrapper cells (below), mixed freely
  with ordinary super-cell records in the same file.
- **A real VM** (`SuperGrid`/`SuperCell`) — event-driven, every core in
  every shell version, a real registry so a new core type can be added
  without touching the VM's own dispatch code. It takes a data width
  (`width=W`, default 32), and `FlexGrid` mirrors the flex family (see
  above).
- **A tile library** — primitive cores plus composed multi-cell patterns
  (`sentinel`, `dual_threshold_monitor`, `twin_sentinel`, DSP-wrapper
  compositions), with real nested composition.
- **A compiler and a real, purpose-built DSL** — `place`/`define`/`expose`
  syntax, real diagnostics (what/problem/why/suggestion, not bare
  exceptions), a naming-hygiene lint, and a circular-reference guard.
  See [`docs/stripped-cell/UNICELL_S_DSL_MANUAL.md`](docs/stripped-cell/UNICELL_S_DSL_MANUAL.md)
  — every example in it was independently compiled and confirmed
  working before being written down, not just described.
- **A second, genuinely independent frontend** — a real Python-AST
  parser (a declarative subset of actual Python syntax), proven to
  produce byte-identical output to the DSL for the same program.
- **A real LLVM IR frontend** — compiles real, working loops (both
  ascending and descending counting patterns) straight from LLVM IR's
  own `phi`/`br`/`icmp` control flow onto a real, proven 4-cell bounded
  loop-ring construction, plus `select` (ternary) and `icmp eq`/`ne`,
  each lowered to a small composition of existing primitives — no
  bespoke hardware needed for any of it. Deliberately narrow, stated
  plainly: single induction variable, no nested loops yet.
- **A real AI-interaction port** (`VMSession`) — compile → load → run →
  inspect, in one clean object, with real JSON introspection of any
  cell or the whole grid.
- **A step-by-step, tabbed browser front end** — the recommended
  starting point: MAN file generation, Quartus project generation,
  and the simulated Walker, each its own tab, walking through this
  project's own real build process in order. Every action-performing
  page also shows the exact equivalent CLI command. Run it with:
  ```bash
  python3 nano/frontend_v1.py
  # → http://localhost:7421
  ```
- **A working browser workbench** — compile a program, watch it run,
  drive individual cells, load multiple independent programs onto one
  shared grid as named regions, or let it auto-play at a chosen rate
  until you pause it or the design naturally settles. Linked from the
  front end above ("Other tools"), or run directly:
  ```bash
  python3 nano/workbench_v1.py
  # → http://localhost:7420
  ```
- **Real hard-IP wrapper cells** — a DSP arithmetic/comparison wrapper
  and a shared-BRAM interface, both **independently confirmed on real
  silicon**: correct fire/ACK/re-arming for the DSP wrapper, and real
  BRAM read/write plus real ICM (`SUPER_LATCH`) loading over an actual
  JTAG host bridge — the first genuinely host-driven hardware success
  in this project's own history. Honest note: the current DSP wrapper
  uses a real, hardware-confirmed soft-logic floating-point IP, not
  the chip's own hard DSP blocks — that path is real and deferred, not
  yet built.
- **Real MAN/SHAPE/placement tooling** (`tools/`, `docs/man/`,
  `docs/shapes/`) — a MAN file captures one card's own real, fixed
  capabilities (device resources, confirmed pin assignments); a SHAPE
  file captures one *compiled design's* own real cell-to-cell wiring,
  extracted straight from its RTL; a placement file adds real physical
  bounding boxes pulled from Quartus's own Control Signals report. See
  `tools/README.md` for each tool's own real scope and honest
  limitations.
- **A real Quartus project generator** (`tools/project_assemble_v1.py`)
  — given a MAN file and a cell count, produces a complete, ready-to-
  import Quartus project for a real N-cell array, guarding directly
  against a real, already-confirmed Quartus behavior (pruning logic it
  can prove unreachable) rather than assuming it away. Now also
  supports targeting any real shell version (not just the built-in
  ones), a real per-cell LogicLock placement mode, and a custom,
  explicit dependency-file list (with a real, advisory compatibility
  check) for mixing and matching core versions without hand-writing a
  Quartus project file list each time.

## The VIX Carrier — a 9-core generation (sim-only, no Quartus data)

Alongside `unicell_super_v1.v`-`v8.v` above, a genuinely separate,
parallel core family was built: a real 9th core (`command`), each of
the 9 cores wrapped in its own new cardinal control shell (so
`active`/`freeze_in`/nano's own feedback ports become real 4-way
cardinal ports instead of flat wires), all combined into one
mutually-exclusive, runtime-selected cell: `unicell_vix_carrier_v1.v`
("V" for version, "IX" for the real 9th-core count). The command core
watches for a real toggle pattern to trigger a burst, or drives a
freeze-and-relay programming sequence onto a neighboring cell — real,
new mechanisms this project didn't have before.

**Real, honest status:** RTL and VM both real and sim-verified —
including a genuine bounded loop-ring wired through the new cardinal
shells, and a command core actually programming a fresh, never-
configured target end to end. **No Quartus/silicon data exists for
this family yet** — the Quartus license expired before a real build
could be run — and it has no portable, on-disk ICM file format of its
own; ICM v3/v4 above are scoped to the older lineage only. (On the
Tang Nano 20K one carrier position measures ~80% of the chip, #887,
which is what led to the sub/flex families.) Full detail:
[`docs/stripped-cell/CORES_AND_WRAPPERS_REFERENCE.md`](docs/stripped-cell/CORES_AND_WRAPPERS_REFERENCE.md).

## Quick start

No installable package exists yet — everything runs as scripts directly
from a clone of this repo. The flex/sub suites need `iverilog` and
`yosys` on the path, and `pytest` and `llvmlite` installed. **Without
`iverilog` they skip and exit 0, which looks like a pass** (#965), so
check before trusting a run:

```bash
git clone https://github.com/alh-Imago/Imago-Unicell.git
cd Imago-Unicell
which iverilog yosys && python3 -c "import pytest, llvmlite"

# Run the VM test suite, then the flex/sub suites (each is a plain script)
python3 -m pytest tests/vm -q
for t in tests/test_*.py; do python3 "$t" || echo "FAILED: $t"; done

# Compile a DSL program to a real ICM v3 file
python3 nano/dsl_cli_v1.py your_program.uc -o out.icm

# Generate Verilog for the Tang Nano 20K from an ICM-VIX file (flex family)
python3 tools/project_assemble_v1.py -s flex --icm nano/examples/small_relay_chain.icm-hier.json \
    --man docs/man/tang-nano-20k.man.json --output build/relay

# Or drive the whole compile → run → inspect loop from Python directly
python3 -c "
import sys; sys.path.insert(0, 'nano')
from vm_ai_port_v1 import VMSession

session = VMSession.from_dsl('''
program my_sentinel {
    place s1 as sentinel at (0, 0) {
        inc: n
        dec: s
        clear: s
        out: e
        cmp.threshold: 8
    }
}
''')
session.tick(5)
print(session.describe())
"

# Or open the tabbed front end (MAN file -> Quartus project -> Walker)
python3 nano/frontend_v1.py

# Or just open the browser workbench directly
python3 nano/workbench_v1.py
```

## Documentation

- [`docs/README.md`](docs/README.md) — the documentation index.
- [`sub/README.md`](sub/README.md) — the sub and flex cell families:
  every cell, its measurements, and the design rules behind it.
- [`docs/man/README.md`](docs/man/README.md) — MAN files: one card's
  fixed capabilities (Arria 10 and Tang Nano 20K), including the DSP,
  synthesis and cost tables the assembler reads.
- [`docs/man/tang-nano-20k-getting-started.md`](docs/man/tang-nano-20k-getting-started.md)
  — flashing the first deliverable onto the board.
- [`docs/stripped-cell/ICM_V3_FORMAT.md`](docs/stripped-cell/ICM_V3_FORMAT.md)
  and [`docs/stripped-cell/ICM_VIX_FORMAT.md`](docs/stripped-cell/ICM_VIX_FORMAT.md)
  — the program formats, including the target-agnostic flags.
- [`tools/README.md`](tools/README.md) — the assembler (both lines),
  the Flex-Sub generators, the measurement tools, and their limits.
- [`docs/stripped-cell/UNICELL_S_DSL_MANUAL.md`](docs/stripped-cell/UNICELL_S_DSL_MANUAL.md)
  — the DSL language reference.
- [`docs/stripped-cell/SUPER_CELL_INTERNALS.md`](docs/stripped-cell/SUPER_CELL_INTERNALS.md)
  — the Arria 10 line's shell/RTL reference.
- `points/` — the project's append-only, numbered decision log (split
  across files since it outgrew GitHub's render limit; start at
  [`points/INDEX.md`](points/INDEX.md)). Every design decision, bug
  found and measurement taken is in here with its reasoning.
- [`current/latest.md`](current/latest.md) — a short summary per recent
  ledger entry, newest first.
- [`docs/shared/DOCS_AND_STATIC_PAGES_AUDIT.md`](docs/shared/DOCS_AND_STATIC_PAGES_AUDIT.md)
  — which docs are current and which have fallen behind. Read it before
  relying on an older reference doc.

## What's genuinely archived, and why

A large amount of earlier work — an older, addressed-bus cell
architecture (`gate_state`-configured cells sharing a wired-OR bus), its
own compiler/VM/tile-library stack, an OS-layer (Companion/Shore/Ward),
a domain-model ecosystem (the Trix family), and assorted tooling — is
real prior work, but built for a fundamentally different, incompatible
architecture than the one described above. None of it is deleted:
every file is preserved byte-for-byte, independently checksum-verified,
in `archeology/onion/` (real, searchable metadata per archive — see
`points.md` #364-#367 for the full record of what moved and why). If
you're looking for something referenced in older material and it's not
where you expect, it's very likely in there.

The Trix family specifically is a real, deliberate conclusion, not
just an artifact of the archival sweep: designing a proper interface
for even one small, well-bounded piece of real hardware (see the DSP
design notes under `docs/stripped-cell/design-notes/`) takes genuine,
careful, bit-level work — checking exactly which operations touch which
part of a value, finding real constraints that only show up once you
go and check. Trix wasn't one domain needing that treatment; it was a
whole family of them (fluid dynamics, neuron models, MIDI, sensor data,
and more), each with a genuinely different natural structure, each
needing that same depth of design work done again from scratch — on a
substrate that's still flat 32-bit integers today, with no signed
number representation and no fixed-point convention at all. Real,
useful domain logic, not lost — just not something this substrate is
ready to carry yet, and not a small gap to close.

## Licence

Imago UniCell is dual-licensed, with software and hardware under
separate permissive licences appropriate to each:

- **Software** (the Python VM, compiler, tooling) — [MIT License](LICENSE)
- **Hardware** (Verilog RTL, cell architecture, FPGA gateware) —
  [CERN Open Hardware Licence v2 - Permissive](LICENSE-HARDWARE)

Both are permissive and attribution-only. You are free to use, study,
modify, make, and distribute every part of this project, including
commercially, provided you retain the relevant notices. See
[NOTICE](NOTICE) for the full explanation of which licence covers which
files and why.
