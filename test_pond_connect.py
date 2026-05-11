"""
test_pond_connect.py — Tests spawn_workspace() and connect() on PondManager.

Verifies:
1. spawn_workspace creates a PRIVATE WORKSPACE pond with Ward + PTT
2. connect() wires bus addresses correctly (zero-overhead, one-tick latency)
3. connect() grants whitelist access both ways
4. Workspace PTT receives connected program's output as a tracked entry
5. Multiple program ponds can connect to one workspace simultaneously
6. Security: a non-whitelisted identity is rejected at the bridge
"""

import os, json
os.environ['IMAGO_VERBOSE'] = '0'

from pond import PondManager, PondBridge
from unicell_array import UniCellArray
from pond_ptt import (
    TYPE_PRIMITIVE, TYPE_WORKSPACE, TYPE_BRIDGE_INBOUND, TYPE_BRIDGE_OUTBOUND,
    STATUS_IDLE, STATUS_ACTIVE, STATUS_NAMES, is_ptt_bus_address,
)
from pond_types import PRIVATE, WORKSPACE

results = []

def check(label, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    results.append((status, label))
    suffix = f" — {detail}" if detail and not condition else ""
    print(f"  [{status}] {label}{suffix}")

def make_mgr(cells=4096):
    return PondManager(UniCellArray(cell_count=cells))

def load_icm(name):
    with open(f'composer/examples/{name}.icm') as f:
        return json.load(f)

def bridge(pond, role):
    return next(b for b in pond.bridges if b.role == role)


# ── Test 1: spawn_workspace ───────────────────────────────────────────────────

print("\n── spawn_workspace ──")

mgr = make_mgr()
ws = mgr.spawn_workspace(owner_id='user_alice')

check("Workspace pond_type is WORKSPACE", ws.pond_type == WORKSPACE)
check("Workspace security_level is PRIVATE", ws.security_level == PRIVATE)
check("Workspace has Ward", ws.ward is not None)
check("Workspace has PTT (INCREMENTAL)", ws._ptt is not None)
check("Workspace has INBOUND bridge",
      any(b.role == PondBridge.INBOUND for b in ws.bridges))
check("Workspace has OUTBOUND bridge",
      any(b.role == PondBridge.OUTBOUND for b in ws.bridges))
check("Workspace starts with empty whitelist", len(ws._whitelist) == 0)
check("Workspace owner is user_alice", ws.owner_id == 'user_alice')


# ── Test 2: connect() bus wiring ─────────────────────────────────────────────

print("\n── connect() bus wiring ──")

prog = mgr.spawn_pond_from_icm(load_icm('not_gate'), owner_id='user_alice')

ws_out = bridge(ws,   PondBridge.OUTBOUND)
ws_in  = bridge(ws,   PondBridge.INBOUND)
pg_in  = bridge(prog, PondBridge.INBOUND)
pg_out = bridge(prog, PondBridge.OUTBOUND)

# Record original addresses before connect
orig_pg_in_addr  = pg_in.external_address
orig_ws_in_addr  = ws_in.external_address

conn = mgr.connect(ws, prog)

check("connect() returns dict", isinstance(conn, dict))
check("ws OUTBOUND now points to pg INBOUND address",
      ws_out.external_address == orig_pg_in_addr,
      f"ws_out=0x{ws_out.external_address:08X} pg_in=0x{orig_pg_in_addr:08X}")
check("pg OUTBOUND now points to ws INBOUND address",
      pg_out.external_address == orig_ws_in_addr,
      f"pg_out=0x{pg_out.external_address:08X} ws_in=0x{orig_ws_in_addr:08X}")
check("connection dict has correct program_name",
      conn['program_name'] == 'not_gate')
check("connection dict ws_outbound == pg_inbound",
      conn['ws_outbound_addr'] == conn['pg_inbound_addr'])
check("connection dict pg_outbound == ws_inbound",
      conn['pg_outbound_addr'] == conn['ws_inbound_addr'])


# ── Test 3: whitelist grants ──────────────────────────────────────────────────

print("\n── whitelist grants ──")

check("Workspace whitelist contains program's owner",
      'user_alice' in ws._whitelist)
check("Program whitelist contains workspace's owner",
      'user_alice' in prog._whitelist)

# Workspace owner is always admitted regardless of whitelist
ok, reason = ws._check_identity('user_alice')
check("Workspace owner admitted (OWNER path)", ok and reason == 'OWNER')

# A stranger without a grant is rejected on a PRIVATE pond
ok_stranger, reason_stranger = prog._check_identity('user_bob')
check("Unknown identity rejected on PRIVATE program pond",
      not ok_stranger,
      f"reason={reason_stranger}")


# ── Test 4: workspace PTT tracks connected program ────────────────────────────

print("\n── workspace PTT tracks connected program ──")

ws_entries = ws._ptt._entries
ws_primitives = [e for e in ws_entries.values() if e.entry_type == TYPE_PRIMITIVE]

check("Workspace PTT has entry for program output after connect",
      len(ws_primitives) >= 1,
      f"found {len(ws_primitives)}")
if ws_primitives:
    entry = ws_primitives[0]
    check("Entry label contains program name", 'not_gate' in entry.label)
    check("Entry is IDLE (program connected, not yet run)",
          entry.status == STATUS_IDLE,
          f"status={STATUS_NAMES.get(entry.status)}")
    check("Entry metadata has program_pond_id",
          'program_pond' in entry.metadata)
    check("Entry sentry address in PTT bus range",
          is_ptt_bus_address(entry.sentry_address))


# ── Test 5: multiple program ponds on one workspace ───────────────────────────

print("\n── multiple programs on one workspace ──")

mgr2 = make_mgr(8192)
ws2  = mgr2.spawn_workspace(owner_id='user_bob', name='bob_workspace')

prog_not = mgr2.spawn_pond_from_icm(load_icm('not_gate'), owner_id='user_bob', cell_count=512)
prog_mux = mgr2.spawn_pond_from_icm(load_icm('mux'),      owner_id='user_bob', cell_count=512)

conn_not = mgr2.connect(ws2, prog_not)
conn_mux = mgr2.connect(ws2, prog_mux)

check("Two programs connected to one workspace",
      conn_not['workspace_pond'] == ws2.pond_id and
      conn_mux['workspace_pond'] == ws2.pond_id)
check("Two programs have distinct pond IDs",
      prog_not.pond_id != prog_mux.pond_id)

# Workspace PTT should have entries for both programs
ws2_prims = [e for e in ws2._ptt._entries.values()
             if e.entry_type == TYPE_PRIMITIVE]
check("Workspace PTT has entries for both programs",
      len(ws2_prims) >= 2,
      f"found {len(ws2_prims)}")

# Each program's OUTBOUND points back to same workspace INBOUND
ws2_in = bridge(ws2, PondBridge.INBOUND)
out_not = bridge(prog_not, PondBridge.OUTBOUND)
out_mux = bridge(prog_mux, PondBridge.OUTBOUND)
check("Both programs route output to workspace INBOUND",
      out_not.external_address == ws2_in.external_address and
      out_mux.external_address == ws2_in.external_address)

# Each program's INBOUND is its own (programs don't share input lanes)
in_not = bridge(prog_not, PondBridge.INBOUND)
in_mux = bridge(prog_mux, PondBridge.INBOUND)
check("Each program has distinct INBOUND address",
      in_not.external_address != in_mux.external_address)


# ── Test 6: two workspaces are isolated ──────────────────────────────────────

print("\n── workspace isolation ──")

check("Two workspaces have distinct pond IDs", ws.pond_id != ws2.pond_id)
check("Two workspaces have distinct PTTs",     ws._ptt is not ws2._ptt)
check("Two workspaces have distinct whitelist dicts",
      ws._whitelist is not ws2._whitelist)


# ── Results ───────────────────────────────────────────────────────────────────

print()
passed = sum(1 for s, _ in results if s == "PASS")
failed = sum(1 for s, _ in results if s == "FAIL")
print(f"Results: {passed} passed, {failed} failed out of {len(results)} tests")
if failed == 0:
    print("ALL TESTS PASSED")
else:
    print("\nFailed tests:")
    for status, name in results:
        if status == "FAIL":
            print(f"  [FAIL] {name}")
