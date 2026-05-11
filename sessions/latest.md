# Latest Session — 2026-05-11 (session 6)

## Tests
All pre-existing passing. Pre-existing failures unchanged (6).
test_pond_bootstrap.py: 36/36
test_pond_connect.py: 31/31 (new)

## Latest commit
TBD — spawn_workspace + connect foundation

## What was done
- PondManager.spawn_workspace(owner_id, name):
    PRIVATE WORKSPACE pond, Ward + PTT (INCREMENTAL), INBOUND + OUTBOUND bridges
- PondManager.connect(workspace, program):
    Bus wiring: ws OUTBOUND → pg INBOUND, pg OUTBOUND → ws INBOUND (zero overhead)
    Whitelist grants both ways
    Workspace PTT receives TYPE_PRIMITIVE entry per connected program output
- spawn_pond_from_icm: changed default from OPEN → PRIVATE
    Program ponds are now correctly PRIVATE at spawn
- MIGRATION_TODO: full workspace implementation plan documented

## Architecture in place
User session → WORKSPACE pond (PRIVATE, INCREMENTAL PTT)
  ↕ connect() wires bus addresses directly (one tick, zero overhead)
Program pond (PRIVATE, STATIC PTT, input TILE_IN + output PRIMITIVE entries)
  Whitelist: only the connecting workspace identity admitted

Multi-program: N program ponds can connect to one workspace simultaneously.
Isolation: each workspace has its own PTT, whitelist, bridges.

## What remains (see MIGRATION_TODO § WORKSPACE POND)
- WorkspacePond backed by real Pond object (currently bare controller wrapper)
- WorkspacePond.launch_program(icm) → ProgramHandle
- Bridge.check_access() wired into UniCellArray tick loop (currently VM only)
- Access token in PTT hidden field for real identity enforcement
- Workbench integration

## Hardware status
- JTAG programmer: in transit, ~21 May 2026
- Kintex-7 XC7K480T: in transit, ETA Jul 2026
