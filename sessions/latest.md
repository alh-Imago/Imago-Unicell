# Session Log — 2026-06-08

## Status at session end
Last commit: 74f4996
Suites: 101/101 compiler_int32, 233/233 fp_tiles

## Done this session

### Compiler bugs fixed

**Passthrough / multi-param bug (PLAN item 6):**
`return a` (passthrough) produced zero records → security gate rejected.
Fixed: emit GS_PASS_B|GS_LATCH_IN self-relays for each output bit when
record list is empty. All passthrough and multi-param cases now pass.

**MUX selector bug (PLAN item 5) — completed from previous session:**
Three root causes all fixed. 22/22 MUX cases passing.
See previous session notes for full detail.

### Server architecture — three-tier system

**unicell_server.py** (full development/research server):
- Compiler + TileLibrary + all 9 MathTrix models
- REST API: /api/status, /api/backends, /api/models, /api/run, /api/job
- Browser frontend: model browser, parameter forms, canvas rendering
- Backend selector: vm / icebreaker / arria10
- Any device on network: tablet, phone, laptop — just a browser URL
- University lab portal: iframe or link into existing portal
- Usage: python unicell_server.py --host 0.0.0.0

**unicell_deployed.py** (lightweight PTT-only server):
- ~300 lines — no compiler, no tile library, no workbench
- Reads PTT last_tick_value per entry, serves via REST
- Output formats: flat / grid_2d / vector
- attach_hardware_ptt(ptt, meta) — called from bring-up code
- Deployment: SCADA, ECU, security module, rack node
- Client is still just a browser — no installation anywhere
- Usage: python unicell_deployed.py --model models/x.json

**Three-tier separation:**
  Workbench        — developer tool, full cell visibility, local
  unicell_server   — research/education, full models, network
  unicell_deployed — production, PTT only, minimal footprint

### Arria 10 bring-up — status
- Card alive on PCIe (VEN_1172/DEV_2494) ✓
- Onboard FTDI USB programmer faulty (enumerated once, never again)
- Shopping list (next month, ~£46 total):
  - Waveshare USB Blaster V2: £32 (Amazon Prime)
  - JST SH 1.0mm 10-pin connector kit: £14 (Amazon Prime)
  - JTAG header: 10-pin lower connector, ~1.5mm pitch
