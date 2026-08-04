# Imago UniCell — Documentation Index

Complete reference. Use Ctrl+F to find any topic.

**Ground truth for all numbers:** Verilog (`unicell_v3.v`), silicon tests (`tests/fpga/test_sanity.py`), tile library (`fp_tiles.py`).

---

## Getting Started

→ **[VM_GETTING_STARTED.md](VM_GETTING_STARTED.md)** — install, run first example, compile first function (< 5 min)

→ **[EXAMPLES.md](EXAMPLES.md)** — all runnable examples with copy-paste commands

→ **[RUNNING.md](RUNNING.md)** — full workflow: VM → Workbench → FPGA

→ **[HARDWARE_SETUP.md](HARDWARE_SETUP.md)** — iCEBreaker and Arria 10 backend setup for unicell_server

---

## Architecture

| Topic | Where |
|-------|-------|
| NOR universality, wired-OR bus | [ARCHITECTURE.md § Foundations](ARCHITECTURE.md) |
| Cell model — gate_state, 12 functions, one cycle | [ARCHITECTURE.md § The Cell](ARCHITECTURE.md) |
| Two-arrival firing model (A posedge, B negedge) | [ARCHITECTURE.md § Edge model](ARCHITECTURE.md) |
| Wired-OR bus — no arbitration, NOR for free | [ARCHITECTURE.md § The Bus](ARCHITECTURE.md) |
| Compile pipeline (source → IR → cells) | [ARCHITECTURE.md § Compiler](ARCHITECTURE.md) |
| Portability — same `.icm` on VM, FPGA, ASIC | [ARCHITECTURE.md § Portability](ARCHITECTURE.md) |
| Preloaded-A pattern — constants at configure time | [PRELOAD_MODEL.md](PRELOAD_MODEL.md) |
| tile_config — strategy selection per tile type | [COMPILER_TILE_CONFIG.md](COMPILER_TILE_CONFIG.md) |

---

## OS Layer

| Topic | Where |
|-------|-------|
| Pond — isolated compute environment | [ARCHITECTURE.md § Pond](ARCHITECTURE.md) |
| Pond security levels (OPEN / PRIVATE / HIDDEN) | [ARCHITECTURE.md § Pond](ARCHITECTURE.md) |
| PTT — Pond Translation Table | [ARCHITECTURE.md § PTT](ARCHITECTURE.md) |
| Bridge — INBOUND / OUTBOUND / MONITOR / LOG | [ARCHITECTURE.md § Bridge](ARCHITECTURE.md) |
| Ward — health monitor, stall/spike/anomaly | [ARCHITECTURE.md § Ward](ARCHITECTURE.md) |
| Shore — name → address registry | [ARCHITECTURE.md § Shore](ARCHITECTURE.md) |
| COMPANION — permanent OS anchor | [ARCHITECTURE.md § COMPANION](ARCHITECTURE.md) |
| WORKSPACE pond — user's desk | [ARCHITECTURE.md § WORKSPACE](ARCHITECTURE.md) |

---

## Server and Network Access

| Topic | Where |
|-------|-------|
| unicell_server.py — full REST server (compiler + models + VM) | [RUNNING.md § Server](RUNNING.md) |
| unicell_deployed.py — lightweight PTT-only server | [RUNNING.md § Deployed](RUNNING.md) |
| Browser frontend (frontend/index.html) | frontend/index.html |
| Hardware backend setup (iCEBreaker, Arria 10) | [HARDWARE_SETUP.md](HARDWARE_SETUP.md) |
| hardware_config.json — serial port configuration | hardware_config.json |
| REST API: /api/library, /api/run, /api/hardware | unicell_server.py |
| PTT output API: /api/ptt, /api/output | unicell_deployed.py |

---

## MathTrix

| Topic | Where |
|-------|-------|
| MathTrix overview — parallel compute domains | [TRIX_ECOSYSTEM.md](TRIX_ECOSYSTEM.md) |
| mathtrix.py — domain language (Grid1D, Grid2D, MathTrix) | mathtrix.py |
| mathtrix_animate.py — video/animation output (MP4, GIF, PNG, live window) | mathtrix_animate.py |
| Built-in models (9 system models) | unicell_model_library.py |
| User models (models/ directory, live CRUD) | unicell_model_library.py |
| MIF tile family — MathTrix Internal Float | [MIF_FORMAT.md](MIF_FORMAT.md) |
| Adding new domains (BioTrix, ChemTrix, etc.) | unicell_model_library.py |

---

## Programs and the `.icm` Format

| Topic | Where |
|-------|-------|
| `.icm` file structure | [ICM_FORMAT.md](ICM_FORMAT.md) |
| `inputs` / `outputs` — named port declarations | [ICM_FORMAT.md § Ports](ICM_FORMAT.md) |
| `records` — cell configurations | [ICM_FORMAT.md § Records](ICM_FORMAT.md) |
| `vm_only` — FPGA budget flag | [ICM_FORMAT.md § Target](ICM_FORMAT.md) |
| `security_context` — reserved auth token binding | [ICM_FORMAT.md § Integrity](ICM_FORMAT.md) |

---

## Tile Library

All figures from `fp_tiles.py` — ground truth.
iCEBreaker limit: **4 cells** (16-bit data bus packing, hardware constraint).

### Integer Arithmetic

| Tile | Cells | Depth | Notes |
|------|-------|-------|-------|
| INT32_ADD | 482 | 10 | Kogge-Stone 32-bit adder |
| INT32_ADD_CLA | 3,969 | 52 | Carry-lookahead, fully combinational |
| INT32_SUB | 517 | 12 | NOT(b) + KS adder + carry-in=1 |
| INT32_MUX | 128 | 3 | 32-bit 2:1 mux — sel=0→a, sel=1→b |
| INT32_NOT/AND/OR/XOR | 32 | 1 | Bitwise, one cell per bit |
| INT32_EQ | 95 | 7 | XNOR + AND tree |
| INT32_LT_U | 518 | 14 | Unsigned a<b |
| INT32_LT_S | 523 | 16 | Signed a<b |
| INT32_MIN / INT32_MAX | 317 | 66 | Signed min/max via LT_S + MUX |
| INT32_MIN_U / INT32_MAX_U | 615 | 17 | Unsigned min/max |
| INT32_CAS | 711 | 17 | Compare-and-swap sort primitive |
| INT32_SAR_N | 32 | 1 | Arithmetic right shift (N=1,2,3,4,8,16) |
| INT32_SHL_N | 33–48 | 2 | Left shift (N=1,2,3,4,8,16) |
| INT32_SHR_N | 33–48 | 2 | Logical right shift (N=1,2,3,4,8,16) |

### Float (IEEE-754)

| Tile | Cells | Depth | Notes |
|------|-------|-------|-------|
| FP32_ADD | 1,253 | 85 | Simplified (no denormals) |
| FP32_MUL | 3,066 | 89 | Simplified (no denormals) |
| FP32_CMP_EQ | 95 | 7 | Bit-exact equality |

### MIF — MathTrix Internal Float

Compact floating-point for parallel stencil computation.
Boundary: `MIF_UNPACK` (IEEE→MIF) and `MIF_PACK` (MIF→IEEE).

| Tile | Cells | Depth | Notes |
|------|-------|-------|-------|
| MIF_UNPACK | 74 | 25 | IEEE-754 → MIF pair. Boundary tile. |
| MIF_PACK | 126 | 4 | MIF pair → IEEE-754. Boundary tile. |
| MIF_ADD | 814 | 79 | MIF addition |
| MIF_SUB | 810 | 79 | MIF subtraction |
| MIF_MUL | 3,066 | 89 | MIF multiply |
| MIF_DIV | 4,789 | 1,177 | MIF divide — use low_latency tile_config |
| MIF_SQRT | 5,317 | 1,177 | MIF square root — use low_latency tile_config |
| MIF_MADD | 3,875 | 107 | Fused multiply-add (a×b+c) |
| MIF_ABS | 0 | 0 | Absolute value — zero cells (sign bit clear) |
| MIF_NEG | 1 | 1 | Negation — sign bit flip |
| MIF_MIN / MIF_MAX | 468 | 59 | MIF min/max |
| MIF_CMP_EQ | 98 | 26 | MIF equality (1-bit result) |
| MIF_CMP_LT / MIF_CMP_GT | 212 | 56 | MIF less/greater-than |
| MIF_CMP_LE / MIF_CMP_GE | 213 | 57 | MIF less/greater-or-equal |
| MIF_MUX | 193 | 3 | MIF 2:1 mux on full 64-bit pair (ctrl+mant). Use for conditional select on MIF data; INT32_MUX only covers 32 bits. |
| MIF_RECIP | 15,288 | 349 | 1/B via LUT-seeded Newton-Raphson. 3.4× shallower than MIF_DIV. Use when only reciprocal is needed (e.g. LBM 1/ρ, shared 1/r in n-body). |
| MIF_RSQRT | 22,916 | 445 | 1/√B via LUT-seeded Newton-Raphson. 3.4× shallower than MIF_SQRT+MIF_RECIP combined (depth 1526→445). Use for normalise/inverse-distance in geometric models. |

Full tile reference: `fp_tiles.py` → `TileLibrary.available()`

---

## Compiler

| Topic | Where |
|-------|-------|
| Single-bit compiler (`compiler.py`) | [ARCHITECTURE.md § Compiler](ARCHITECTURE.md) |
| INT32 compiler (`compiler_int32.py`) | compiler_int32.py |
| MUX selector — if/else branch compilation | compiler_int32.py |
| tile_config — strategy dictionaries | [COMPILER_TILE_CONFIG.md](COMPILER_TILE_CONFIG.md) |
| Preloaded-A pattern | [PRELOAD_MODEL.md](PRELOAD_MODEL.md) |
| LLVM IR mapper | [LLVM.md](LLVM.md) |

---

## Composer (Visual Design Tool)

| Topic | Where |
|-------|-------|
| Open Composer (no install, no server) | composer/unicell_composer.html |
| Composer README | [composer/README.md](../composer/README.md) |
| Current version | v2.1 (2026-06-08) |
| Place cells, wire, drop tile macros | composer/unicell_composer.html |
| Export `.icm` | composer/unicell_composer.html |
| 86 tile/model entries in library panel | composer/unicell_composer.html |

---

## FPGA and Hardware

→ **[FPGA_HARDWARE.md](FPGA_HARDWARE.md)** — hardware reference (protocol, PCIe, build, silicon results)

→ **[HARDWARE_SETUP.md](HARDWARE_SETUP.md)** — server backend setup (iCEBreaker, Arria 10)

| Topic | Where |
|-------|-------|
| iCEBreaker iCE40UP5K — 4-cell limit (data bus) | [FPGA_HARDWARE.md](FPGA_HARDWARE.md) |
| Arria 10 GX660 Mustang-F100 — pending bring-up | [HARDWARE_SETUP.md](HARDWARE_SETUP.md) |
| UART bridge protocol | [FPGA_HARDWARE.md § UART](FPGA_HARDWARE.md) |
| Command bus protocol (v2.1, 8-bit opcodes) | [FPGA_HARDWARE.md § Protocol](FPGA_HARDWARE.md) |
| Verilog specification | [VERILOG_SPEC.md](VERILOG_SPEC.md) |

---

## Test Suites

All tests pass against the VM. Silicon tests pass against iCEBreaker hardware.

| Suite | Count | Coverage |
|-------|-------|----------|
| `tests/vm/test_compiler_int32.py` | **157/157** | MUX selector, passthrough, arithmetic, all comparison operators, nested ifs, multi-param |
| `tests/vm/test_fp_tiles.py` | **242/242** | All tile types, MIF family, MIF_MUX/MIF_RECIP/MIF_RSQRT, edge cases |
| `tests/vm/test_flowtrix.py` | **27/27** | FlowTrix D2Q9 FormatDefinition and collide |
| `tests/vm/test_flowtrix_collide.py` | **13/13** | LBM_COLLIDE tile composition vs ground truth |
| `tests/vm/test_flowtrix_cylinder.py` | **18/18** | Flow past cylinder, Strouhal vs Williamson |
| `tests/vm/test_neurotrix_lif.py` | **28/28** | LIF neuron FormatDefinition and runner |
| `tests/vm/test_neurotrix_lif_mif.py` | **14/14** | LIF tick as composed MIF tiles |
| `tests/vm/test_miditrix.py` | **19/19** | MidiTrix tonotopic MIDI→LIF runner |
| `tests/vm/test_mif_mux.py` | **14/14** | MIF_MUX correctness |
| `tests/vm/test_mif_recip.py` | **16/16** | MIF_RECIP vs float reference |
| `tests/vm/test_mif_rsqrt.py` | **15/15** | MIF_RSQRT vs float reference |
| `tests/vm/test_walker.py` | **29/29** | walk_tiles.py, --module flag, record_hash canonR |
| `tests/vm/test_community_raw.py` | **14/14** | Non-Trix raw-model contribution kind |
| `tests/vm/test_community_models.py` | **175/175** | BioTrix/ChemTrix/PhysTrix worked example models |
| `tests/fpga/test_sanity.py` | **31/31** | iCEBreaker silicon — two-arrival model, NOT/AND/OR/XOR/PASS/NOR, latch_in, one_shot, invert_out, preload_sel, shift_out_en, CMD_ARRAY_RESET |

**iCEBreaker hardware limit: 4 cells** (16-bit UART data bus packing).
`shift_in_en` validation deferred to Arria 10 (hardware pending).

Run the VM suites:
```bash
PYTHONPATH=. python tests/vm/test_compiler_int32.py
PYTHONPATH=. python tests/vm/test_fp_tiles.py
```

Run silicon tests (hardware required):
```bash
python tests/fpga/test_sanity.py /dev/ttyUSB0
```

---

## Repository Map

```
README.md               — overview + quick start
PLAN.md                 — open work items and architecture decisions

# Core VM — LEGACY (pre-v3.1 protocol). Still the ACTIVE implementation
# behind the compiler/controller/workbench/pond stack below and 30+
# existing tests -- NOT yet migrated to the v3.1 cell/array model (see
# "Core VM (v3.1, current)" further down). Do not treat unicell.py's own
# "UniCell v3" naming as meaning it matches the current RTL -- it predates
# the 64-bit methodology bus, the routing latch, targeted opcodes, and
# command-emit entirely (points.md #67/#68). Migration to the files below
# is real, scoped future work, not yet started.
unicell.py              — cell model (pre-v3.1 protocol; LEGACY, see note above)
unicell_array.py        — array tick loop, wired-OR bus (pre-v3.1; LEGACY)
command_interface.py    — v2.3 command-word builder (pre-v3.1; LEGACY, no
                          direct v3.1 replacement file -- the equivalent
                          opcode-level logic now lives directly in
                          unicell_v3.py's methods and loader_fsm_v3.py's
                          transport model)
gate_states.py          — all gate_state bit definitions (authoritative for the LEGACY model)
ir.py                   — IR graph → CellMapRecord lowering
compiler.py             — single-bit function compiler
compiler_int32.py       — 32-bit integer compiler (MUX, all comparisons)
fp_tiles.py             — tile library (INT32, FP32, MIF, MIF_MUX/RECIP/RSQRT, counters)
controller.py           — region lifecycle, load/run/halt/freeze
pond_ptt.py             — Pond Translation Table
workbench.py            — browser workbench UI (full cell visibility)

# Core VM (v3.1, current) — matches fpga/verilog/unicell64_v3.v /
# unicell_array64_v3.v / loader_fsm_v3.v exactly, verified line-by-line
# against the actual RTL logic (points.md #67/#68). Not yet wired into
# the compiler/controller/workbench stack above -- a standalone, fully
# tested model (240 VM tests, all passing) usable today for fabric-design
# prototyping and RTL cross-checking, ahead of that migration.
unicell_v3.py           — the CURRENT cell model: topology/methodology/routing
                          latches, comparator, targeted opcodes, command-emit
unicell_array_v3.py     — the CURRENT array model: wired-OR combine, command-
                          emit arbiter, targeted-emission delivery
loader_fsm_v3.py        — VM model of the real loader_fsm_v3.v (boot-time
                          icmP loader + the SET_TARGET/cpu_addr_w transport)
tests/vm/test_unicell_v3.py, test_unicell_array_v3.py, test_loader_fsm_v3.py
                        — the 240 tests proving the above against the RTL

# Server and Network
unicell_server.py       — REST server (compiler + tile library + 10 models)
unicell_deployed.py     — PTT-only server (production/embedded use)
unicell_model_library.py — unified model library (system + user models)
mathtrix.py             — MathTrix domain language (Grid1D, Grid2D, MathTrix)
mathtrix_animate.py     — video/animation output (MP4, GIF, PNG, live window)
hardware_config.json    — serial port assignments for hardware backends
frontend/index.html     — browser frontend (model browser, run, visualise)

# Domain frontends (Trix family)
cell_format.py          — FormatDefinition base + all format classes + FormatRegistry
flowtrix_lbm_mif.py     — FlowTrix: LBM_COLLIDE tile composition (1,714 ticks/update)
flowtrix_cylinder.py    — FlowTrix: flow past cylinder, Strouhal validation
flowtrix_cost.py        — FlowTrix: cost comparison vs 777 PowerFLOW
neurotrix_lif.py        — NeuroTrix: LIF neuron FormatDefinition and runner
neurotrix_lif_mif.py    — NeuroTrix: LIF tick as composed MIF tiles (353 ticks/update)
miditrix_lif.py         — MidiTrix: MIDI event stream → tonotopic LIF bank

# Composer
composer/
  unicell_composer.html — standalone visual design tool (v2.1)
  README.md             — composer guide

# Community contribution space
community/
  community_tools.py    — validate / hash / register / search / scaffold
  REGISTRY.md           — contribution index (trix-domain and raw-model kinds)
  mathtrix/             — 10 reference models (boids, conway, gray_scott, …)
  biotrix/              — BioTrix format + 5 worked example models
  chemtrix/             — ChemTrix format + 3 worked example models
  phystrix/             — PhysTrix format + 3 worked example models
  fintrix/              — FinTrix format definition
  general/              — BCD + FixedPoint format definitions
  politicstrix/         — PoliticsTrix format definition

# Walker — tile .icm export tool
examples/
  walker/
    walk_tiles.py       — emit .icm for any tile or whole builder library
                          (--builder module:fn or --module FILE)
    example_user_models.py — pattern for a user builder library file
  tiles/samples/        — curated 152KB sample palette (committed; bulk git-ignored)

# Tests
tests/vm/               — 14 active suites (see Test Suites table above)
tests/fpga/
  test_sanity.py        — 31 tests (iCEBreaker silicon validation)

# FPGA
fpga/verilog/           — Verilog-2001 (unicell_v3.v, uart_bridge.v)
fpga_bridge.py          — UART host bridge

# Papers
papers/
  PAPERS.md             — publication tracking (7 papers, status + dependencies)
  paper_main/           — working notes/figures for main paper
  paper_timing/         — deterministic timing paper
  paper_bridges/        — typed cross-domain computation + bridge inference
  paper_hawking/        — Hawking bridge standalone result
  paper_robotics/       — sensor-to-actuator robotics pipeline
  paper_flowtrix/       — FlowTrix fluid simulation paper
  paper_substrate/      — universal symbolic substrate (vision paper)
docs/PAPER_DRAFT.md     — Paper 1 working draft (in docs/ for manual access)

# Docs
docs/
  INDEX.md              — this file
  ARCHITECTURE.md       — cell, bus, OS, PTT, security
  RUNNING.md            — full workflow guide
  VM_GETTING_STARTED.md — new user guide (< 5 min)
  HARDWARE_SETUP.md     — iCEBreaker and Arria 10 backend setup
  FPGA_HARDWARE.md      — hardware reference (protocol, silicon results)
  VERILOG_SPEC.md       — Verilog bring-up, timing, parity table
  ICM_FORMAT.md         — .icm format specification
  MIF_FORMAT.md         — MIF tile format and usage
  TRIX_ECOSYSTEM.md     — Trix family current state (MathTrix, FlowTrix, SensorTrix, NetTrix, community)
  COMPILER_TILE_CONFIG.md — tile_config strategy selection
  PRELOAD_MODEL.md      — preloaded-A pattern
  LLVM.md               — LLVM IR mapper
  VISION.md             — project vision
  EXAMPLES.md           — runnable examples
  LIBRARY.md            — user library (.icm sharing) and community contribution
  addressing_note.md    — 32-bit address space
  archive/              — historical docs (v1.1, superseded)
  diagrams/             — Mermaid architecture diagrams (7 files)
```

---

## Silicon Validation (iCEBreaker, May 2026)

Tested on iCEBreaker v1.0e (iCE40UP5K sg48) via UART bridge.
**Hardware cell limit: 4 cells** (16-bit data bus packing in uart_bridge.v).

| # | Test | Result |
|---|------|--------|
| 1 | Two-arrival model — fires on second arrival only | ✓ |
| 2 | NOT gate | ✓ |
| 3 | AND gate | ✓ |
| 4 | OR gate | ✓ |
| 5 | XOR gate | ✓ |
| 6 | PASS | ✓ |
| 7 | NOR gate | ✓ |
| 8 | latch_in — stores A, fires on B | ✓ |
| 9 | one_shot — fires once then disarms | ✓ |
| 10 | invert_out — output inverted before emission | ✓ |
| 11 | preload_sel — preload a_data in one transaction | ✓ |
| 12 | shift_out_en — output shifted right by N nibbles | ✓ |
| 13 | CMD_ARRAY_RESET — authenticated system-wide reset | ✓ |
| 14–31 | Edge cases, boundary values, combined modes | ✓ |

31/31 passing. Synthesis: 3,780 ICESTORM_LC (71%), 24 MHz.
`shift_in_en` deferred — requires Arria 10 hardware (Waveshare USB Blaster pending).

---

## Glossary

| Term | Meaning |
|------|---------|
| Cell | Universal compute unit. One gate_state, one input address, one output address. |
| gate_state | 32-bit config word. Bits 0-8: NOR topology. Bits 11-26: mode flags. |
| Two-arrival | Cell fires on second arrival. First stores in a_data, second triggers gate tree. |
| Wired-OR bus | Shared address space. Two cells writing same address → OR of values. No arbitration. |
| Pond | Isolated compute environment with address space, bridges, Ward health monitor. |
| PTT | Pond Translation Table. Named ports with bus addresses. |
| Bridge | Cell cluster connecting Ponds. INBOUND / OUTBOUND / MONITOR / LOG. |
| Ward | Per-Pond health monitor. Detects stall, spike, anomaly. |
| Shore | Name → address registry. |
| COMPANION | Permanent OS anchor. HIDDEN, cannot be destroyed. |
| `.icm` | Portable program file. JSON. Runs on VM, FPGA, ASIC unchanged. |
| Tile | Pre-built verified cell network (INT32_ADD, MIF_MUL, etc.). |
| MIF | MathTrix Internal Float — compact floating-point for stencil computation. |
| Depth | Pipeline depth: exact ticks from input to output. Structural, not statistical. |
| Preloaded-A | a_data set at configure time — eliminates runtime preload sequences. |
| tile_config | Strategy dict passed to compiler — selects low_latency, const_divisor, etc. |
| iCEBreaker limit | 4 cells max on iCEBreaker (16-bit UART data bus packing, hardware constraint). |
