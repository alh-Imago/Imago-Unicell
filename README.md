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
install` today. If the PCIe host-integration side of this project
succeeds, the realistic best-case outcome is an FPGA accelerator card
for specific spatial-dataflow workloads — not a CPU replacement. If it
doesn't, what remains is still real, working architecture research. This
README aims to represent exactly that, no more.

---

## The current architecture: the super carrier shell (Unicell-S)

The active line of development is the **super carrier shell**
(`fpga/verilog/unicell_super_v1.v`): a single physical FPGA cell that
holds *six* real, different cores simultaneously — a NOR-gate logic
cell, RAM, an adder, an accumulator, a comparator, and a latch — with
the active one chosen by a runtime configuration write (`core_select`),
not a synthesis-time choice. Every core is always physically present in
every bitstream; only the selected one ever does real work. Cells wire
directly to their North/South/East/West physical neighbors — there is
no addressed bus anywhere in this design.

**Real, Quartus-confirmed silicon numbers** (target: IEI Mustang-F100-A10,
Arria 10 GX, 10AX066H2F34E2SG):

| | |
|---|---|
| Total shell cost | 213 ALM, 257 registers — all 6 cores present |
| Isolation/selection overhead | 25.9 ALM — smaller than any one of the 3 largest individual cores |
| Timing | `clk_div` 200.76 MHz — 8.03× margin over the 25 MHz requirement |

For full detail, see [`docs/stripped-cell/SUPER_CELL_INTERNALS.md`](docs/stripped-cell/SUPER_CELL_INTERNALS.md).

## What's built on top of it, and how it's verified

Everything below lives in [`nano/`](nano/) and is genuinely tested —
but tested in software/simulation, not yet independently confirmed on
real hardware as these specific multi-cell layouts. That distinction is
kept honest throughout the project's own documentation, not blurred.

- **ICM v3** — the program format: real `SUPER_LATCH[79:0]` encode/decode,
  verified two independent ways (bit-for-bit against real, iverilog-compiled
  RTL test vectors, and mechanically re-derived straight from the RTL's
  own comments).
- **A real VM** (`SuperGrid`/`SuperCell`) — event-driven, all 6 cores,
  a real registry so a new core type can be added without touching the
  VM's own dispatch code.
- **A tile library** — primitive cores plus composed multi-cell patterns
  (`sentinel`, `dual_threshold_monitor`, `twin_sentinel`), with real
  nested composition.
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
  — the shell/RTL reference.
- [`docs/stripped-cell/CELL_INTERNALS.md`](docs/stripped-cell/CELL_INTERNALS.md)
  — the standalone nano cell's own reference (a related but genuinely
  different, smaller cell design, still real and independently
  buildable).
- `points.md` — the project's own append-only, numbered decision log.
  Every real design decision, bug found, and measurement taken is in
  here with its actual reasoning, not just a changelog line.

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
