"""
test_ptt_sentry.py — Tests that sentry cells correctly update the PTT.

Verifies:
1. _ptt_ref is wired to cells after load_map(ptt=...)
2. Sentry placeholder address (PTT_BUS_BASE) is patched to real PTT address
3. bus_tick() fires correctly and PTT status transitions work
4. Two tiles in same pond get separate PTT entries and separate sentry addresses
"""

import os
os.environ['IMAGO_VERBOSE'] = '0'

from controller import ImagoController, CellMapRecord
from pond_ptt import (
    PondPTT, ptt_bus_address, PTT_BUS_BASE, is_ptt_bus_address,
    TYPE_PRIMITIVE, TYPE_SENTRY,
    STATUS_RESERVED, STATUS_LOADING, STATUS_IDLE, STATUS_WAITING,
    STATUS_ACTIVE, STATUS_COMPLETING,
    PTT_TICK_WAITING, PTT_TICK_ACTIVE, PTT_TICK_IDLE, PTT_TICK_LOADING,
)
from gate_states import GS_PASS, GS_SENTRY

results = []

def check(label, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    results.append((status, label))
    suffix = f" — {detail}" if detail and not condition else ""
    print(f"  [{status}] {label}{suffix}")


# ── Setup: PTT with two registered entries ────────────────────────────────────

ptt = PondPTT("test_pond", PondPTT.STATIC)

idx_a = ptt.register(address=0x1000, entry_type=TYPE_PRIMITIVE, label="tile_a")
ptt.register_sentry(idx_a, staleness_threshold=5.0)

idx_b = ptt.register(address=0x2000, entry_type=TYPE_PRIMITIVE, label="tile_b")
ptt.register_sentry(idx_b, staleness_threshold=5.0)

sentry_addr_a = ptt_bus_address(idx_a)
sentry_addr_b = ptt_bus_address(idx_b)

check("PTT sentry addresses are in PTT bus range",
      is_ptt_bus_address(sentry_addr_a) and is_ptt_bus_address(sentry_addr_b))
check("Two entries get different sentry addresses",
      sentry_addr_a != sentry_addr_b,
      f"a=0x{sentry_addr_a:08X} b=0x{sentry_addr_b:08X}")


# ── Build cell map: two sentry cells + one data cell ─────────────────────────

sentry_rec_a = CellMapRecord(
    gate_state=GS_SENTRY,
    input_address=0x1000,
    output_address=PTT_BUS_BASE,   # placeholder — patched by load_map
)
sentry_rec_b = CellMapRecord(
    gate_state=GS_SENTRY,
    input_address=0x2000,
    output_address=PTT_BUS_BASE,   # placeholder — patched by load_map
)
data_rec = CellMapRecord(
    gate_state=GS_PASS,
    input_address=0x3000,
    output_address=0x3001,
)

records = [sentry_rec_a, sentry_rec_b, data_rec]
ctrl = ImagoController(cell_count=50)
rid = ctrl.load_map(records, "sentry_test", ptt=ptt)

check("load_map with ptt= returns a region id", rid is not None)

region = ctrl._regions[rid]


# ── Test 1: _ptt_ref wired on all cells ──────────────────────────────────────

ptt_ref_set = all(
    getattr(ctrl.array.cells.get(addr), '_ptt_ref', None) is ptt
    for addr in region.cell_addresses
    if ctrl.array.cells.get(addr) is not None
)
check("_ptt_ref wired on all loaded cells", ptt_ref_set)


# ── Test 2: Sentry placeholder addresses patched ──────────────────────────────
# gate_state & 0x3FF = 0 for SENTRY (bits 10-11 are stripped at config).
# Identify sentry cells by output_address being in the PTT bus range.

loaded_cells = [ctrl.array.cells.get(addr) for addr in region.cell_addresses
                if ctrl.array.cells.get(addr) is not None]

sentry_cells = [c for c in loaded_cells if is_ptt_bus_address(c.output_address)]
data_cells   = [c for c in loaded_cells if not is_ptt_bus_address(c.output_address)]

check("Two sentry cells identified by PTT bus range output address",
      len(sentry_cells) == 2,
      f"found {len(sentry_cells)}")
check("One data cell with non-PTT output address",
      len(data_cells) == 1)

if len(sentry_cells) == 2:
    addrs = {c.output_address for c in sentry_cells}
    # Note: ptt_bus_address(0) == PTT_BUS_BASE, so entry 0's sentry
    # legitimately lives at PTT_BUS_BASE. The real test is that the two sentry
    # cells have DISTINCT addresses — both at PTT_BUS_BASE would mean no patching.
    check("Sentry addresses are not both PTT_BUS_BASE (patching occurred)",
          not (addrs == {PTT_BUS_BASE}),
          f"addresses: {[hex(a) for a in addrs]}")
    check("Both sentry addresses distinct",
          len(addrs) == 2)
    check("Sentry addr A matches registered PTT sentry address",
          sentry_addr_a in addrs,
          f"expected 0x{sentry_addr_a:08X}, got {[hex(a) for a in addrs]}")
    check("Sentry addr B matches registered PTT sentry address",
          sentry_addr_b in addrs)


# ── Test 3: PTT status transitions via bus_tick ───────────────────────────────
# Entries start RESERVED. Walk them through the state machine manually.

entry_a = ptt.get(idx_a)
entry_b = ptt.get(idx_b)

check("Entry A starts RESERVED", entry_a.status == STATUS_RESERVED)

# Walk A to IDLE via LOADING
ptt.bus_tick(sentry_addr_a, PTT_TICK_LOADING)
check("Entry A → LOADING after PTT_TICK_LOADING", entry_a.status == STATUS_LOADING)

ptt.bus_tick(sentry_addr_a, PTT_TICK_IDLE)
check("Entry A → IDLE after PTT_TICK_IDLE", entry_a.status == STATUS_IDLE)

# First invocation
result = ptt.bus_tick(sentry_addr_a, PTT_TICK_WAITING)
check("bus_tick returns True for known sentry address", result is True)
check("Entry A → WAITING after PTT_TICK_WAITING", entry_a.status == STATUS_WAITING,
      f"status={entry_a.status}")

# Keep-alive ticks
ptt.bus_tick(sentry_addr_a, PTT_TICK_ACTIVE)
check("Entry A stays in WAITING/ACTIVE after keep-alive",
      entry_a.status in (STATUS_WAITING, STATUS_ACTIVE))

# Entry B should be unaffected
check("Entry B status unaffected by entry A ticks",
      entry_b.status == STATUS_RESERVED)

# Bus tick on unrelated address returns False
check("bus_tick returns False for non-PTT address",
      ptt.bus_tick(0x3001, 1) is False)

# Bus tick on B's sentry address works independently
ptt.transition(idx_b, STATUS_LOADING)
ptt.transition(idx_b, STATUS_IDLE)
ptt.bus_tick(sentry_addr_b, PTT_TICK_WAITING)
check("Entry B transitions independently via its own sentry address",
      entry_b.status == STATUS_WAITING,
      f"status={entry_b.status}")


# ── Test 4: tick_count increments on keep-alive ticks ─────────────────────────

before = entry_a.tick_count
ptt.bus_tick(sentry_addr_a, PTT_TICK_ACTIVE)
check("tick_count increments on PTT_TICK_ACTIVE",
      entry_a.tick_count == before + 1)


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
