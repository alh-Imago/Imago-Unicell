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

This is deliberately NOT the Composer (a separate, visual tool that
arranges an already-compiled design; RTL generation is explicitly out of
scope for it; built for flex layouts at #1002 as the front panel's
`/composer` over `tools/flex_layout_view_v1.py`, see `docs/stripped-cell/
design-notes/composer_layout_viewer_scope.md`) and NOT the Walker (a live, hardware-discovery
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

**Two more modes (2026-10):** `--target yosys` writes a `.ys` script
instead of `.qsf`/`.sdc` (`points.md` #663), and `-s/--family
flex|sub|nano` builds from the stripped Tang Nano families instead of
the shell lineage. That path is handled by the Flex-Sub tools below.
The help text (`-h`) lists every flag with its ledger reference.

## The Flex-Sub assembler (Tang Nano 20K; ledger #921-#986)

These tools are reached through `project_assemble_v1.py`'s `-s` flag.
With `-s` absent (or `-s nano`), every existing mode is byte-identical
to before (#921). The cells are in `sub/verilog/`; see `sub/README.md`.

| file | job |
|---|---|
| `flexsub_assemble_v1.py` | **Step 1.** An N-cell chain of one cell type (`-s flex -S adder --cells 100`), with the generated top, `.ys`, `build.sh` and `ASSEMBLY.json`. Every instantiation is checked against the cell's real parsed port list. It also owns the `-nowidelut` resolver (`resolve_nowidelut`) and the multiplier ladder. |
| `flexsub_icm_netlist_v1.py` | Read-only (`splice_crosses` gives each used direction of a `cross` tile a one-tick ram relay slice, #999). It derives the real netlist from an ICM-VIX or v3 file (cell masks plus grid position; the `connections` list is advisory) and says what each family can and cannot express (#923). |
| `flexsub_icm_generate_v1.py` | **Step 2, `sub`.** `-s sub --icm FILE` generates the design as fixed-latency hardware: one cycle per cell, early operands padded with relay cells, add-ons as wiring, merges as gated ORs, branches lowered onto `branch_cell_v4s`, a tick-driven sequencer, and the level-source rule (#925-#940). Its `plan()` is also the single source of truth `FlexGrid` reads. |
| `flexsub_icm_flex_v1.py` | **Step 2, `flex`.** `-s flex --icm FILE` generates handshake hardware: eager forks for fan-out, joins for two-operand cells, constants as fixed-mode rams, merge cores per merge, second ports where flagged (#944-#981). No padding is needed. |
| `flex_layout_v1.py` | A layout engine for hand-designed flex structures: cells and links on a grid, `route()`, the generator's hop model, and `balance()`, which removes the operand-arrival ties the generator refuses and enforces "minuend first" (#989); `route_nets(..., use_cross=True)` lets a route cross another at right angles through a `cross` tile (#999) |
| `flex_layout_view_v1.py` | The Composer's layout side (#1002): imports an ICM file (v3, v4 or VIX) or starts a blank board (`Layout.new`); `add_cell`, `set_config` (checked by encoding the SUPER_LATCH), `join(a, b, out, role)` with output ports (out, second, low/equal/high) and input roles (in, set/clear/toggle, inc/dec) from which every direction field is derived, `unjoin`, `delete_cell`, `set_minuend`, `balance`; `move` re-routes and re-balances or refuses with nothing changed; `place_block` puts a saved design in as one unit whose io-named cells are its ports (`move_block`, `unpack_block`, `delete_block`); `undo`; `save` writes ICM v3. Nano/priority/command cells are pinned. `--builder fp_add/fp16` loads a layout built by Python. The front panel's `/composer` page is its UI |
| `fp_add_v1.py` | The whole fp adder from flex cells: `fp_add(g, fmt)`, parametric in `FpFormat` (#990). Scope: normals and zero |
| `fp_assembler_v1.py` | The open fp assembler: `FpFormat` (FP32, FP16, BF16, or custom) and parametric normalise / align-with-sticky / round blocks whose counts and constants are computed from the format (#989; design note `docs/stripped-cell/design-notes/fp_assembler_open_design.md`) |
| `flexsub_compile_v1.py` | Compiles LLVM IR for sub/flex. It uses the stock compiler and rewrites VM-only mode-2 priorities to strict mode 0 with ranks, and marks the result cell. `--min-bit-width N` (#929/#930/#940/#958). |

```bash
python3 tools/project_assemble_v1.py -s flex -S adder --cells 100 --man docs/man/tang-nano-20k.man.json --output build/chain
python3 tools/project_assemble_v1.py -s flex --icm nano/examples/cordic_z_convergence.icm-hier.json --man docs/man/tang-nano-20k.man.json --output build/cordic
python3 tools/project_assemble_v1.py -s sub  --icm nano/examples/parallel_reduction_tree.icm-hier.json --man docs/man/tang-nano-20k.man.json --output build/tree
```

Flags that matter here:

- `-w N` sets the width (flex only). Without it the MAN's `native_width`
  is used (18 on the Tang). A MAN without that field gives 32. With no
  MAN and no `-w`, `-s flex` is an error (#914/#934).
- `--nowidelut` / `--wide-lut`: `-nowidelut` is the default whenever the
  MAN says the toolchain supports it. It is refused on the Arria 10
  path (#952).
- `--mul auto|lut|dsp` (`--icm`): auto uses the DSP cell while the MAN
  lists a usable primitive with blocks left, then the LUT multiplier,
  then refuses (#941/#942).
- `--merge-mode SPEC` (`-s flex --icm`): `arbitrate` (default) or
  `join-or`, set per merge consumer (#955/#957).
- `--no-align` (`-s sub --icm`): a negative control that skips operand
  padding.

**Limits:** the `--icm` generators build 32-bit designs (the step-1
chains honour `-w`). Cycles with a data-dependent exit are refused.
Some cell combinations are refused with a reason rather than guessed:
for example, a constant into an accumulator's inc/dec, a sequencer
into a two-operand cell on sub, or a second-port cell as a design exit.
Every result above is simulation plus synthesis or place-and-route,
not silicon.

## Measurement tools (Gowin, open toolchain)

All of these need `yosys`. The place-and-route ones also need
`yowasp-nextpnr-himbaechel-gowin` (pip; the apt `nextpnr-gowin` only
covers GW1N, #889). They write only to temporary folders unless noted.

| file | measures |
|---|---|
| `flex_width_sweep_v1.py` | every flex cell at W = 4…32: single cell (`-nowidelut` and wide-LUT), 3x3 array, and second port built. Writes `docs/measurements/flex_width_sweep_975/costs.json`, which feeds the Tang MAN's `cell_costs` (#975/#976) |
| `measure_cell_width_v1.py` | one flex cell at 32 vs 18 bits, in both synthesis flows, counting MUX2_LUT cells too (#948/#949) |
| `measure_synth_flow_v1.py` | real place-and-route of a cell, default flow vs `-nowidelut`, LFSR-wrapped so Fmax is credible (#949) |
| `measure_flag_across_families_v1.py` | the `-nowidelut` effect on sub, flex and the original nano family (#950) |
| `measure_flag_pnr_v1.py` | real place-and-route of every sub and flex cell, both flows (#950); raw logs in `docs/measurements/nowidelut_sweeps_950/` |
| `gowin_sizing/size_cells.sh`, `size_carrier.sh` | the ORIGINAL cells and VIX carrier on the GW2A, full and lean (#886/#887; synthesis only) |
| `gowin_sizing/gen_mesh_top.py`, `run_mesh_sweep.py` | pin-bound wrappers and the N=1 / 3x3 place-and-route sweep of the original standalone cells (#889) |
| `gowin_sizing/build_adder_v4sa_scaling.sh` | the 1-cell and 100-cell flex adder chain place-and-route (#908/#910) |
| `gowin_sizing/build_smoke_bitstream.sh` | the flashable Tang smoke-test bitstream, end to end, with a pinned seed (#892/#896) |

**Measurement pitfalls the ledger records:** observe every output bit
(XOR-reduce them), or the synthesiser legally deletes the logic you
are measuring (#889/#902/#908). A flattened shared-stimulus chain
understates live-config cells, so use the bare-cell convention for
per-cell cost (#922). Do not project costs from the wide-LUT flow
(#975).

## `man_gen/gen_tang_nano_20k_man.py` — the generated Tang MAN

This regenerates `docs/man/tang-nano-20k.man.json` and `.cst` from the
Apicula chip database, yosys's own cell declarations and the sweep
data. `--check` exits 1 if either committed file is stale. It needs
`pip install apycula msgpack`; pin apycula to 0.32 to reproduce the
committed file (#975). See `docs/man/README.md`.

## The local browser tools share one look (`nano/ui_theme_v1.py`, ledger #998)

The front panel (`python3 nano/frontend_v1.py`, port 7421: Start, MAN file, Create cells, Walker, Other tools, Manual) and the
workbench (`python3 nano/workbench_v1.py`, port 7420) use one stylesheet and one header/nav from `nano/ui_theme_v1.py`.
That module is presentation only. A new page should call `ui.page(title, body, active=...)` rather than carry its own CSS.

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
