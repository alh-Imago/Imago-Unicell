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

## Model library and server (added this session)

### unicell_model_library.py — two entry points
System models (SYSTEM_MODELS list, immutable):
  10 MathTrix models with full metadata, tags, tile_config, descriptions

User models (models/ directory, live CRUD):
  create_user_model / update_user_model / delete_user_model
  Live reload — no restart needed
  New domains emerge automatically from user model 'domain' field
  models/example_user_model.json created as template

### unicell_server.py — library endpoints added
  GET  /api/library                 All models, filterable
  GET  /api/library?domain=MathTrix Filter by domain
  GET  /api/library?tag=physics     Filter by tag
  GET  /api/library?search=wave     Search name/description
  GET  /api/library?system=true     System only
  GET  /api/library?user=true       User only
  GET  /api/library/domains         All domains
  GET  /api/library/tags            All tags
  GET  /api/library/setup           Setup instructions
  GET  /api/library/<id>            Single model
  POST /api/library                 Create user model
  PUT  /api/library/<id>            Update user model
  DELETE /api/library/<id>          Delete (system models protected)

### Hardware backends
  hardware_config.json — serial port config for iCEBreaker and Arria 10
  GET /api/hardware — status + setup instructions
  POST /api/hardware — set port without editing JSON
  run_model_hardware() — FPGABridge compile + configure + inject + read

### Arria 10 — still blocked
  FTDI chip on card is intermittent — almost certainly why it was shelved
  Waveshare USB Blaster V2 (£32) + JST SH 1.0mm 10-pin kit (£14) = £46
  Both on Amazon wishlist

## Things to break next session
1.  Wire fast_marching runner into unicell_server.py run_model_vm dispatch
2.  Add MUX tests to fp_tiles suite (currently only in compiler suite)
3.  MathTrix frontend — proper domain language, not just demo scripts
4.  Composer updates
5.  Documentation pass — README, getting-started, API reference
6.  Frontend for unicell_server — model browser shows system/user tabs
7.  unicell_deployed.py — test grid_2d output format end-to-end
8.  Backend activation for iCEBreaker — flash uart_bridge, test /api/hardware POST
9.  shift_in_en validation (Arria 10, when hardware arrives)
10. Paper — deployment model section (browser client, PTT interface, commons silicon)
