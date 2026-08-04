# Session Log — 2026-06-08 (full session)

## Final commit: e7db74c
## Suites: 140/140 compiler_int32, 236/236 fp_tiles

---

## Done this session

### Compiler bugs fixed

**MUX selector — three root causes (PLAN item 5):**
1. GS_PASS → GS_PASS_B in padding chains (outputs A=0 → outputs arriving B)
2. Zero-comparison fast path replaced with tile-based comparisons
3. Constants 0/1 → _compile_int32_literal (not IR single-bit path)
22/22 MUX cases passing.

**Passthrough/multi-param (PLAN item 6):**
Empty record list → security gate rejected. Fixed: emit GS_PASS_B self-relays.

**General comparisons (>=, <=, != with arbitrary b) — found by fuzz test:**
IR NOT nodes fire after tile records in forward sim → preload=0 always → FALSE.
Fixed: _tile_space_not() emits GS_NOT_B|GS_LATCH_IN tile record instead.
Zero-comparison path (a>=0, a!=0 etc.) unchanged — already tile-space.
300-case fuzz (50 pairs × 6 ops) all passing.

### Server architecture
unicell_server.py — full REST server, 10 models, VM + hardware backends
unicell_deployed.py — lightweight PTT-only, ~300 lines, production use
hardware_config.json — serial port config
GET /api/hardware — status + setup instructions per backend
Three-tier: Workbench (dev) / full server (research) / deployed (production)

### Model library
unicell_model_library.py — system + user, two entry points
CRUD API: POST/PUT/DELETE /api/library
New domains emerge automatically from user model 'domain' field
models/example_user_model.json template

### MathTrix frontend
mathtrix.py — MathTrix, Grid1D, Grid2D, Result1D, Result2D, ResultParticles
All 10 runners wired through mathtrix.py (server is thin wrappers)
base_model routing: user models inherit system runners

### mathtrix_animate.py — video/animation output
GPU renders. UniCell produces data. No pixel pushing in cells.
Output: MP4 (H.264/ffmpeg), GIF (Pillow), PNG snapshot, live window
Renderers: 2D heatmap, 1D line chart, particle trails, rank convergence
Colourmaps: auto by model (inferno/RdBu_r/viridis/coolwarm/cividis/plasma)
API: animate(), show(), snapshot()
Demo: python mathtrix_animate.py --demo gray_scott --fps 30

### Composer v2.1
MIF tile family (17 tiles) added — was completely absent
Shift tiles (18) — replaced zero-cell v2.3 stubs with real specs
MOUSE_HANDLER added, port CSS fixed, pond addressing note
86 total MODELS entries (was 51)

### Documentation pass
Corrected: INT32_ADD 19c → 482c depth 10 (4 files)
Corrected: iCEBreaker ~1,040 cells → 4 cells hardware limit (3 files)
Corrected: test counts 15/15, 19/19, 81/82 → 31/31, 133/133, 236/236
INDEX.md rewritten: new sections, correct tile table, silicon validation list
RUNNING.md: correct test paths and counts

### Package v0.2.0
flask as optional [server] dep, imago-server + imago-deploy entry points
MANIFEST.in: frontend/, models/, composer/, fpga/verilog/, docs/
imago.serve(), imago.mathtrix(), imago.models() API

### Paper draft
docs/PAPER_DRAFT.md — complete 11-section draft
Key claim: no known architecture combines NOR universality + wired-OR
arbitration + two-arrival firing. Documented with 31/31 silicon evidence.

### Tests
140/140 compiler_int32 (was 133 — added depth padding + comparison fuzz)
236/236 fp_tiles (was 233 — added MUX edge cases)
300-case fuzz: all comparison operators, 50 random int32 pairs

---

## Hardware status
Arria 10 GX660 (Mustang-F100): PCIe alive, onboard FTDI USB faulty
Shopping list (next month):
  Waveshare USB Blaster V2: £32 (Amazon wishlist)
  JST SH 1.0mm 10-pin connector kit: £14 (Amazon wishlist)
  Total: £46

---

## Remaining (non-hardware)
- command_interface.py naming (PRELOAD_NONE → PRELOAD_SEL_*) — cosmetic
- docs/RUNNING.md and ICM_FORMAT.md inB field cleanup — cosmetic
- DisplayPond hosted flag (GPU passthrough vs cell rendering) — deferred
- Sentinel/Ward/Shore rethink — architectural, deferred
- SymPy input for MathTrix — post-release

## Hardware-gated (next month)
- Arria 10 first bitstream (Quartus, uart_bridge.v)
- shift_in_en silicon validation
- Scale test — actual cell count on GX660
- Paper Section 4 update with Arria 10 results

## Video (next session)
mathtrix_animate.py is the mathematical output side (done).
Fabric fire visualiser (cell-by-cell firing animation) deferred —
needs Arria 10 scale to be visually meaningful.
