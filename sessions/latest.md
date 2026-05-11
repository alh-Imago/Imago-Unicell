# Latest Session — 2026-05-11 (session 7 — final)

## Tests
All pre-existing passing. Pre-existing failures unchanged (6).
test_workspace_pond.py: 19/19 (new)
test_pond_bootstrap.py: 36/36
test_pond_connect.py: 31/31
test_ptt_sentry.py: 20/20
test_compiler_int32.py: 82/82

## Latest commit
74c75ea — items 1,2,4,5,7,8 complete

## What was done

### Item 1 — Composer model library
INT32_MIN/MAX descriptions corrected to 'signed'. INT32_CAS flagged vmOnly.

### Item 2 — Stale figures
INT32_LT_U depth corrected 12→14 in MIGRATION_TODO and docs.
model_library items checked off.

### Item 4 — WorkspacePond refactor
WorkspacePond now accepts pond_manager= at construction.
When supplied: spawns real WORKSPACE Pond (PRIVATE, Ward+PTT+bridges).
  launch_program(icm)     → creates program pond, connects, returns handle
  run_program(handle_id)  → routes via wired bus, captures output
  disconnect_program(id)  → revokes grants, destroys pond, cleans PTT
  status()                → reports active_programs with per-port PTT status
Legacy bare-controller path fully preserved.

### Item 5 — Bridge access in tick loop
UniCellArray._bridge_registry: {inbound_addr: PondBridge}
Phase 0 drain: PRIVATE/HIDDEN bridge writes from wrong pond dropped + counted.
PondManager.connect() registers addresses + tags all cells with _pond_id.
Full per-cell identity tokens are future work.

### Items 7/8 — Index Pond design + workspace quota
Full Index Pond design documented: metadata fields, mask filter syntax,
consistency model, persistence, rebuild. All 5 items checked off.
Workspace quota: connect() raises ValueError at max_concurrent (default 8).

## Remaining open items (hardware-dependent or deferred)
- ECC Hamming SECDED in silicon
- Ward as silicon program
- PTT cell word comparison in silicon
- Shore table in silicon
- VM vs silicon diff tool (needs hardware)
- FPGA/silicon workbench mode (Kintex-7, July 2026)
- 64-bit address extension (future silicon)
- Access token in PTT hidden field (identity per bus write)
- Workbench WorkspacePond backed by real Pond (deferred)
- VM performance mode / numpy vectorisation (item 3, large item)
- inB/SYNC_WAIT in Verilog (JTAG arrives ~21 May)

## Hardware status
- JTAG programmer: in transit, ~21 May 2026
- Kintex-7 XC7K480T: in transit, ETA Jul 2026
