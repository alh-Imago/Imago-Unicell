# Tools

Standalone utilities and offshoots built alongside the Imago UniCell project.

## `project_assemble_v1.py` — real N-cell Quartus project generator

Given a MAN file (a card's own real capabilities, see `docs/man/`)
and a cell count, generates one complete, self-contained folder ready
to import directly into Quartus: every real Verilog source file
needed, a newly-generated top-level RTL file instantiating N
`unicell_super_v3` cells in a real, cardinally-wired row-major grid,
and matching `.qsf`/`.sdc` files (built on this project's own proven
flat-file-path template — see `points.md` #538).

```bash
python3 tools/project_assemble_v1.py --man docs/man/mustang-f100-a10.man.json --cells 500
```

**Two real extensions, `points.md` #567:**
- `-S`/`--single-core <name>` — generate an array of ONE real core
  type instead of the full 8-core shell (a card of pure RAM cells, or
  pure nano cells, no shell overhead at all). Real options: `ram_cell`,
  `adder_cell`, `accumulator_cell`, `compare_cell`, `latch_cell`,
  `sequencer_cell`, `branch_cell`, `unicell_stripped`.
- `-x`/`--core-path <dir>` — real, configurable source directory for
  core files (default: `fpga/verilog`). Files are matched by base
  name only, ignoring version suffixes (`_v1`/`_v2`/etc.) — the
  highest real version found at that path wins automatically.
- `-P`/`--probe [NAME]` — include a real ISSP debug probe, optionally
  naming the instance (default `DEBUG_PROBE` if `-P` given with no
  value). **Omitted by default** — the LED-based anti-pruning check
  works completely independently of the probe (confirmed: a no-probe
  build compiles with genuinely zero errors, no `issp` reference
  anywhere), so for a pure resource/timing measurement the probe is a
  real, optional extra, not a requirement. When included, prints a
  real reminder to generate the `issp` IP in Quartus before compiling
  (same real `probe_width=2`/`source_width=1`/no-clock configuration
  used throughout this project) -- without that step, Analysis &
  Synthesis fails with `undefined entity "issp"`.

This is deliberately NOT the Composer (a separate, visual placement-
*review* tool for an already-compiled model — RTL generation is
explicitly out of scope for it, see `docs/stripped-cell/design-notes/
composer_scope.md`) and NOT the Walker (a live, hardware-discovery
tool for mapping a *programmed* chip's own real topology cell by
cell — see `points.md` #501). This tool's own job stops at "produce a
real, buildable Quartus project" — it does no placement/routing
optimization (Quartus's own fitter does that regardless) and wires no
live host connectivity.

A real, already-confirmed risk (Quartus pruning logic it can prove
unreachable, `points.md` #528/#550) is guarded against directly: one
real, unconstrained top-level input feeds the array's own entry cell,
and every cell's own outputs are XOR-reduced into one real, observable
output — so nothing in the array can be silently optimized away. See
`points.md` #552 for the full real build/verification history.

## `shape_extract_v1.py` — real cell-to-cell adjacency extraction

Given a top-level Verilog file, extracts the real cell-to-cell
adjacency graph — which instances exist, their role (programmable
substrate / host-interface / fixed connection point, per the SHELL/
CORE/ADDON/HOST-INTERFACE taxonomy), and every direct, real
point-to-point wire connection between them. Pure RTL-source analysis
— no Quartus, no `.sof`, no hardware needed at all.

```bash
python3 tools/shape_extract_v1.py <verilog_file> --card-id <id> -o <output.shape.json>
```

**Real, honest limitation, not a minor edge case:** this does NOT
trace through registered or conditional logic — only bare wire-to-wire
connections. A relationship mediated through an `always` block (a
common pattern in this project's own RTL) is invisible to it. See
`docs/shapes/README.md` for the full real schema and the specific,
real example this limitation was found against.

**Real, important distinction from the Walker:** this is a static,
source-level tool — it tells you what the RTL's own wiring *says*
should be connected, not what a real, programmed chip's fitter
actually placed or whether `CELL_ID` values stayed consistent across
builds. See `points.md` #551 for the real correction made once this
distinction became load-bearing.

## `placement_extract_v1.py` — real physical bounding boxes from Quartus

Given a SHAPE file (above) and Quartus's own real Control Signals
report, produces real per-instance physical bounding boxes — where
each cell's own logic actually landed on the die. See
`docs/shapes/placement/README.md` for the generation instructions,
schema, and the real history of why Quartus's "Back-Annotate
Assignments" feature was tried first and found insufficient
(`points.md` #456/#457).

## `chaos_topology_v1.py` — genuine random-topology exploration

Random core assignment, random valid wiring, real data fed in, watched
through the real VM — not a generated narrative about what a random
topology might do. Every cell's own required config fields are always
populated with SOME valid random value (guaranteeing it loads into a
real `SuperGrid`), but nothing about whether its wiring "makes sense"
is guaranteed — that's the point. Some cells offer into empty space,
some never fire, some form real chains by pure chance, all genuinely
observed, not designed.

## onion/ (git submodule → github.com/alh-Imago/Onion)

**Onion 🧅 — Adaptive Layered Compression Engine**

A self-contained file compression engine with a layered pipeline architecture:
RLE → LZ77 → Huffman → AES-256-GCM. The Strategist analyses input entropy before
compressing; the Gain Monitor prunes layers that don't help. Archives are
fully self-describing with a signed metadata block.

This directory is a git submodule pointing at its own repository
(`github.com/alh-Imago/Onion`), not a plain copy — the tool is developed
there independently and updates pull straight through here. After cloning
this repo fresh, run `git submodule update --init --recursive` to populate
it (it will appear empty otherwise). See `onion/README.md` for full
documentation once populated.

Each tool that isn't a single script lives in its own subdirectory with
its own README, setup, and dependencies. None require the UniCell VM or
hardware to run, except where noted above (Quartus, for `placement_extract_v1.py`
specifically).
