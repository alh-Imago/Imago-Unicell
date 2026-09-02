# Imago UniCell

A spatial compute architecture built on one principle: **topology is
computation**. There's no CPU, no instruction set, no shared bus.
Programs are described as physical topology — which of a fixed set of
hardware cores sits where, wired to its physical neighbors — and
computation happens as values arrive and propagate outward across that
topology, one wire-delay hop at a time. No global clock coordinates it;
wire delay does.

**What this actually is, stated plainly:** a research project building
real, working pieces of a genuinely novel FPGA architecture, on real
hardware, with real measured numbers. It is not a general-purpose
computer, not commercially packaged, and not something you can `pip
install` today. **A real, deliberate architectural investigation
(2026-09-01/02) established this card's own real ceiling — roughly
200-250 cells, ~65-75 MHz Fmax at that scale — and hardware
exploration is closed for now as a result** (see "Real scale ceiling"
below for the full, honest reasoning). What remains is real, working
architecture research and a genuinely novel design methodology, not a
path to a competitive compute accelerator on this card alone. This
README aims to represent exactly that, no more.

---

## The current architecture: the super carrier shell (Unicell-S)

The active line of development is the **super carrier shell** — a
single physical FPGA cell that holds multiple real, different cores
simultaneously, with the active one chosen by a runtime configuration
write (`core_select`), not a synthesis-time choice. Every core is
always physically present in every bitstream; only the selected one
ever does real work. Cells wire directly to their North/South/East/
West physical neighbors — there is no addressed bus anywhere in this
design.

**`unicell_super_v3.v` is the current, recommended baseline** — the
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
above, is in `points/points_active.md` and `points/INDEX.md`.

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

## Real scale ceiling, and why hardware work is closed for now

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

**Real, honest conclusion: this project's near-term identity is a
small, correctness-proven hardware platform, not a compute
accelerator in any competitive sense.** Hardware exploration is
closed for now as a deliberate result, not an open question left to
drift. The genuinely promising path to real scale is a future custom
ASIC (matching this project's own clockless/asynchronous architecture
ideas, closest in spirit to Wave Computing's own DPU design) —
confirmed as real and worth pursuing eventually, and confirmed as not
a near-term undertaking. Ongoing work continues on the VM and
tooling side, where scale and design exploration remain genuinely
free of any real hardware ceiling.

## What's built on top of it, and how it's verified

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
  without touching the VM's own dispatch code.
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
- **A real AI-interaction port** (`VMSession`) — compile → load → run →
  inspect, in one clean object, with real JSON introspection of any
  cell or the whole grid.
- **A working browser workbench** — compile a program, watch it run,
  drive individual cells, load multiple independent programs onto one
  shared grid as named regions. Run it with:
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

## Quick start

No installable package exists yet — everything runs as real scripts
directly from a clone of this repo.

```bash
git clone https://github.com/alh-Imago/Imago-Unicell.git
cd Imago-Unicell

# Compile a DSL program to a real ICM v3 file
python3 nano/dsl_cli_v1.py your_program.uc -o out.icm

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

# Or just open the browser workbench
python3 nano/workbench_v1.py
```

## Documentation

- [`docs/README.md`](docs/README.md) — the real documentation index,
  kept current as new pieces land.
- [`docs/stripped-cell/UNICELL_S_DSL_MANUAL.md`](docs/stripped-cell/UNICELL_S_DSL_MANUAL.md)
  — the DSL language reference.
- [`docs/stripped-cell/SUPER_CELL_INTERNALS.md`](docs/stripped-cell/SUPER_CELL_INTERNALS.md)
  — the shell/RTL reference, covering all three real shell versions.
- [`docs/stripped-cell/CELL_INTERNALS.md`](docs/stripped-cell/CELL_INTERNALS.md)
  — the standalone nano cell's own reference (a related but genuinely
  different, smaller cell design, still real and independently
  buildable).
- [`docs/man/README.md`](docs/man/README.md) — MAN files: one real
  card's own fixed capabilities, authored once.
- [`docs/shapes/README.md`](docs/shapes/README.md) — SHAPE files: one
  real compiled design's own cell-to-cell adjacency, extracted fresh
  per build.
- [`tools/README.md`](tools/README.md) — every standalone tool this
  project has built, its real scope, and its honest limitations.
- `points/` — the project's own append-only, numbered decision log
  (split across multiple files since it outgrew GitHub's own render
  limit; start at [`points/INDEX.md`](points/INDEX.md)). Every real
  design decision, bug found, and measurement taken is in here with
  its actual reasoning, not just a changelog line.
- [`docs/shared/POINTS_STATUS_AUDIT.md`](docs/shared/POINTS_STATUS_AUDIT.md)
  and [`docs/shared/POINTS_STATUS_AUDIT_2.md`](docs/shared/POINTS_STATUS_AUDIT_2.md)
  — a real, curated status map on top of the ledger above: what's
  done, what's genuinely still pending, and what's an open thought-
  direction with no build started.

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
