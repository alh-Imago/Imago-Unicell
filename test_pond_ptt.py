"""
test_pond_ptt.py — Pond Translation Table tests

Covers: registration, transitions, resolution, late binding,
        freeze/restore (static + incremental), event log,
        workspace incremental updates, Ward query interface.
"""

import time
from pond_ptt import (
    PondPTT, PttEntry, PttEvent,
    TYPE_CELL, TYPE_TILE_IN, TYPE_TILE_OUT, TYPE_BRIDGE,
    TYPE_STORAGE, TYPE_WORKSPACE, TYPE_SENTRY,
    STATUS_RESERVED, STATUS_LOADING, STATUS_IDLE,
    STATUS_WAITING, STATUS_ACTIVE, STATUS_COMPLETING, STATUS_FAULTED,
    PTT_BUS_BASE, PTT_TICK_ACTIVE, PTT_TICK_WAITING,
    PTT_TICK_COMPLETING, PTT_TICK_LOADING, PTT_TICK_IDLE,
    ptt_bus_address, is_ptt_bus_address,
)

passed = failed = 0

def check(label, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
    else:
        failed += 1
        print(f"  [FAIL] {label}" + (f": {detail}" if detail else ""))

def section(name):
    print(f"\n=== {name} ===")


# ── Registration ──────────────────────────────────────────────────────────────
section("Registration")

ptt = PondPTT("p0001", PondPTT.STATIC)
idx0 = ptt.register(0x00400000, TYPE_TILE_IN, label="add.input")
idx1 = ptt.register(0x00400040, TYPE_TILE_OUT, label="add.output")
idx2 = ptt.register(0x00400080, TYPE_BRIDGE, label="inbound")

check("register returns index 0", idx0 == 0)
check("register returns index 1", idx1 == 1)
check("register returns index 2", idx2 == 2)
check("entry count", len(ptt) == 3)

e0 = ptt.get(idx0)
check("entry address",    e0.absolute_address == 0x00400000)
check("entry type",       e0.entry_type == TYPE_TILE_IN)
check("entry status",     e0.status == STATUS_RESERVED)
check("entry label",      e0.label == "add.input")
check("entry type_name",  e0.type_name == "TILE_IN")
check("entry status_name",e0.status_name == "RESERVED")


# ── Status transitions ────────────────────────────────────────────────────────
section("Status transitions")

ptt2 = PondPTT("p0002", PondPTT.STATIC)
idx = ptt2.register(0x00500000, TYPE_CELL, label="cell_0")

ok = ptt2.transition(idx, STATUS_LOADING)
check("RESERVED->LOADING", ok)
check("status is LOADING", ptt2.get(idx).status == STATUS_LOADING)

ok = ptt2.transition(idx, STATUS_IDLE)
check("LOADING->IDLE", ok)

ok = ptt2.transition(idx, STATUS_WAITING)
check("IDLE->WAITING", ok)

ok = ptt2.transition(idx, STATUS_ACTIVE)
check("WAITING->ACTIVE", ok)
check("is_active", ptt2.get(idx).is_active)

# Invalid transition
ok_bad = ptt2.transition(idx, STATUS_LOADING)
check("ACTIVE->LOADING rejected", not ok_bad)
check("status unchanged after bad transition",
      ptt2.get(idx).status == STATUS_ACTIVE)

# FAULTED path
ptt3 = PondPTT("p0003", PondPTT.STATIC)
idx_f = ptt3.register(0x00600000)
ptt3.transition(idx_f, STATUS_LOADING)
ptt3.transition(idx_f, STATUS_FAULTED)
check("LOADING->FAULTED", ptt3.get(idx_f).status == STATUS_FAULTED)
ptt3.transition(idx_f, STATUS_RESERVED)
check("FAULTED->RESERVED", ptt3.get(idx_f).status == STATUS_RESERVED)


# -- Resolution ----------------------------------------------------------------
section("Address resolution")

ptt4 = PondPTT("p0004", PondPTT.STATIC)
idx = ptt4.register(0x00700000, TYPE_TILE_OUT, label="out")

# Not available until IDLE or ACTIVE
check("resolve RESERVED -> None", ptt4.resolve(idx) is None)
ptt4.transition(idx, STATUS_LOADING)
check("resolve LOADING -> None",  ptt4.resolve(idx) is None)
ptt4.transition(idx, STATUS_IDLE)
check("resolve IDLE -> address",  ptt4.resolve(idx) == 0x00700000)
ptt4.transition(idx, STATUS_WAITING)
check("resolve WAITING -> address", ptt4.resolve(idx) == 0x00700000)
ptt4.transition(idx, STATUS_ACTIVE)
check("resolve ACTIVE -> address", ptt4.resolve(idx) == 0x00700000)

# Missing index
check("resolve missing -> None", ptt4.resolve(999) is None)


# -- Late binding / waiters ----------------------------------------------------
section("Late binding (resolve_or_wait)")

ptt5 = PondPTT("p0005", PondPTT.STATIC)
idx = ptt5.register(0x00800000, TYPE_TILE_IN, label="late")

fired = []
result = ptt5.resolve_or_wait(idx, lambda e: fired.append(e.absolute_address))
check("not yet active: returns None", result is None)
check("not yet active: no callback fired", len(fired) == 0)

ptt5.transition(idx, STATUS_LOADING)
ptt5.transition(idx, STATUS_IDLE)
ptt5.transition(idx, STATUS_WAITING)
ptt5.transition(idx, STATUS_ACTIVE)

check("callback fired on ACTIVE",     len(fired) == 1)
check("callback received address",    fired[0] == 0x00800000)

# resolve_or_wait on already-active entry fires immediately
fired2 = []
addr = ptt5.resolve_or_wait(idx, lambda e: fired2.append(e.absolute_address))
check("already active: returns address", addr == 0x00800000)
check("already active: fires immediately", len(fired2) == 1)


# ── Address update (migration) ────────────────────────────────────────────────
section("Address update (Pond migration)")

ptt6 = PondPTT("p0006", PondPTT.STATIC)
idx = ptt6.register(0x00400000, TYPE_BRIDGE, label="bridge")
ptt6.transition(idx, STATUS_LOADING)
ptt6.transition(idx, STATUS_IDLE)

ptt6.update_address(idx, 0x00800000)
check("address updated", ptt6.get(idx).absolute_address == 0x00800000)
check("resolve gives new address", ptt6.resolve(idx) == 0x00800000)

log = ptt6.log
resolved_events = [e for e in log if e.event_type == PttEvent.RESOLVED]
check("RESOLVED event emitted", len(resolved_events) == 1)
check("RESOLVED event has new address",
      resolved_events[0].address == 0x00800000)


# ── Release ───────────────────────────────────────────────────────────────────
section("Entry release (Workspace)")

ptt7 = PondPTT("p0007", PondPTT.INCREMENTAL)
idx = ptt7.register(0x00900000, TYPE_WORKSPACE, label="para_1")
ptt7.transition(idx, STATUS_LOADING)
ptt7.transition(idx, STATUS_IDLE)
ptt7.transition(idx, STATUS_WAITING)
ptt7.transition(idx, STATUS_ACTIVE)

ok = ptt7.release(idx)
check("release succeeds", ok)
check("entry removed", ptt7.get(idx) is None)
check("count decremented", len(ptt7) == 0)

released = [e for e in ptt7.log if e.event_type == PttEvent.RELEASED]
check("RELEASED event emitted", len(released) == 1)

# Released slot is reused
idx_new = ptt7.register(0x00A00000, TYPE_WORKSPACE, label="para_2")
check("slot reused", idx_new == idx)


# ── Freeze / restore — STATIC ────────────────────────────────────────────────
section("Freeze / restore — STATIC (Program Pond)")

ptt8 = PondPTT("prog_0001", PondPTT.STATIC)
i0 = ptt8.register(0x00400000, TYPE_TILE_IN,  label="add.in")
i1 = ptt8.register(0x00400040, TYPE_TILE_OUT, label="add.out")
i2 = ptt8.register(0x00400080, TYPE_BRIDGE,   label="inbound")

for i in [i0, i1, i2]:
    ptt8.transition(i, STATUS_LOADING)
    ptt8.transition(i, STATUS_IDLE)
    ptt8.transition(i, STATUS_WAITING)
    ptt8.transition(i, STATUS_ACTIVE)

snap = ptt8.freeze()
check("frozen after freeze()", ptt8.is_frozen)

# Mutation rejected after freeze
try:
    ptt8.register(0x00B00000)
    check("mutation after freeze rejected", False)
except RuntimeError:
    check("mutation after freeze rejected", True)

# Restore
ptt8r = PondPTT.restore(snap)
check("restored pond_id",    ptt8r.pond_id == "prog_0001")
check("restored mode",       ptt8r.mode == PondPTT.STATIC)
check("restored frozen",     ptt8r.is_frozen)
check("restored entry count",len(ptt8r) == 3)
check("restored address i0", ptt8r.get(i0).absolute_address == 0x00400000)
check("restored status i1",  ptt8r.get(i1).status == STATUS_ACTIVE)
check("restored label i2",   ptt8r.get(i2).label == "inbound")
check("restored type i2",    ptt8r.get(i2).entry_type == TYPE_BRIDGE)

# Resolve works after restore — no rebuild needed
check("resolve after restore", ptt8r.resolve(i0) == 0x00400000)
check("resolve after restore", ptt8r.resolve(i1) == 0x00400040)


# ── Freeze / restore — INCREMENTAL ───────────────────────────────────────────
section("Freeze / restore — INCREMENTAL (Workspace Pond)")

ptt9 = PondPTT("ws_0001", PondPTT.INCREMENTAL)
for k in range(5):
    idx = ptt9.register(0x00600000 + k*0x40, TYPE_WORKSPACE,
                        label=f"para_{k}")
    ptt9.transition(idx, STATUS_LOADING)
    ptt9.transition(idx, STATUS_IDLE)
    ptt9.transition(idx, STATUS_WAITING)
    ptt9.transition(idx, STATUS_ACTIVE)

snap9 = ptt9.freeze()
check("incremental not frozen after snapshot", not ptt9.is_frozen)

# Can still mutate after snapshot
new_idx = ptt9.register(0x00600500, TYPE_WORKSPACE, label="para_5")
check("still mutable after snapshot", new_idx is not None)

# Restore
ptt9r = PondPTT.restore(snap9)
check("incremental restore count", len(ptt9r) == 5)  # snapshot was before para_5
check("incremental not frozen",    not ptt9r.is_frozen)


# ── Event log ─────────────────────────────────────────────────────────────────
section("Event log (document history)")

events_received = []
ptt10 = PondPTT("ws_doc", PondPTT.INCREMENTAL,
                on_event=lambda e: events_received.append(e))

idx = ptt10.register(0x00700000, TYPE_WORKSPACE, label="heading_1")
ptt10.transition(idx, STATUS_LOADING)
ptt10.transition(idx, STATUS_IDLE)
ptt10.transition(idx, STATUS_WAITING)
ptt10.transition(idx, STATUS_ACTIVE)
ptt10.update_address(idx, 0x00700040)
ptt10.release(idx)

log = ptt10.log
check("REGISTERED event",  any(e.event_type == PttEvent.REGISTERED  for e in log))
check("TRANSITION events", sum(1 for e in log if e.event_type == PttEvent.TRANSITION) == 4)
check("RESOLVED event",    any(e.event_type == PttEvent.RESOLVED    for e in log))
check("RELEASED event",    any(e.event_type == PttEvent.RELEASED    for e in log))
check("callback fires for each event", len(events_received) == len(log))
check("events have pond_id", all(e.pond_id == "ws_doc" for e in log))
check("events are timestamped", all(e.timestamp > 0 for e in log))

# log_since
t_mid = log[2].timestamp
recent = ptt10.log_since(t_mid)
check("log_since returns subset", len(recent) < len(log))
check("log_since all after cutoff", all(e.timestamp > t_mid for e in recent))


# ── Query interface (Ward) ────────────────────────────────────────────────────
section("Ward query interface")

ptt11 = PondPTT("p_ward", PondPTT.STATIC)
for k in range(4):
    i = ptt11.register(0x00800000 + k*0x40, TYPE_CELL, label=f"cell_{k}")
    ptt11.transition(i, STATUS_LOADING)
    if k < 3:
        ptt11.transition(i, STATUS_IDLE)
    if k < 2:
        ptt11.transition(i, STATUS_WAITING)
        ptt11.transition(i, STATUS_ACTIVE)
    if k == 3:
        ptt11.transition(i, STATUS_FAULTED)

check("active_count",  ptt11.active_count() == 2)
check("faulted_count", ptt11.faulted_count() == 1)

active  = ptt11.entries_by_status(STATUS_ACTIVE)
idle    = ptt11.entries_by_status(STATUS_IDLE)
faulted = ptt11.entries_by_status(STATUS_FAULTED)
check("entries_by_status ACTIVE",  len(active)  == 2)
check("entries_by_status IDLE",    len(idle)    == 1)
check("entries_by_status FAULTED", len(faulted) == 1)

by_type = ptt11.entries_by_type(TYPE_CELL)
check("entries_by_type CELL", len(by_type) == 4)

st = ptt11.status()
check("status dict has pond_id",  st["pond_id"] == "p_ward")
check("status dict has entries",  st["entries"] == 4)
check("status dict has by_status",len(st["by_status"]) > 0)


# ── Capacity limit ────────────────────────────────────────────────────────────
section("Capacity")

ptt12 = PondPTT("p_cap", PondPTT.INCREMENTAL)
# Fill to capacity
for k in range(PondPTT.MAX_ENTRIES):
    ptt12.register(0x10000000 + k*0x40, TYPE_WORKSPACE)
check("fills to MAX_ENTRIES", len(ptt12) == PondPTT.MAX_ENTRIES)

try:
    ptt12.register(0x99999999)
    check("overflow rejected", False)
except OverflowError:
    check("overflow rejected", True)


# -- Sentry mechanism ----------------------------------------------------------
section("Sentry cell and PTT bus address")

ptt_s = PondPTT("p_sentry", PondPTT.STATIC)
idx_s = ptt_s.register(0x00A00000, TYPE_TILE_IN, label="add_tile")
ptt_s.transition(idx_s, STATUS_LOADING)
ptt_s.transition(idx_s, STATUS_IDLE)

# register_sentry assigns PTT bus address
sentry_addr = ptt_s.register_sentry(idx_s, staleness_threshold=0.5)
check("sentry_addr in PTT range",     is_ptt_bus_address(sentry_addr))
check("sentry_addr == ptt_bus_address", sentry_addr == ptt_bus_address(idx_s))
check("entry has sentry_address",     ptt_s.get(idx_s).sentry_address == sentry_addr)
check("staleness_threshold set",      ptt_s.get(idx_s).staleness_threshold == 0.5)

# bus_tick: PTT_TICK_WAITING -> IDLE->WAITING
ok = ptt_s.bus_tick(sentry_addr, PTT_TICK_WAITING)
check("bus_tick returns True for PTT addr", ok)
check("IDLE->WAITING on first tick",   ptt_s.get(idx_s).status == STATUS_WAITING)

# bus_tick: PTT_TICK_ACTIVE -> touch only
ptt_s.transition(idx_s, STATUS_ACTIVE)
t_before = ptt_s.get(idx_s).updated_at
import time as _time; _time.sleep(0.01)
ptt_s.bus_tick(sentry_addr, PTT_TICK_ACTIVE)
check("ACTIVE tick updates updated_at",
      ptt_s.get(idx_s).updated_at > t_before)
check("tick_count increments",         ptt_s.get(idx_s).tick_count > 0)
check("status stays ACTIVE",           ptt_s.get(idx_s).status == STATUS_ACTIVE)

# bus_tick: PTT_TICK_COMPLETING -> ACTIVE->COMPLETING
ptt_s.bus_tick(sentry_addr, PTT_TICK_COMPLETING)
check("COMPLETING on output tick",     ptt_s.get(idx_s).status == STATUS_COMPLETING)

# bus_tick on non-PTT address returns False
check("non-PTT addr returns False",    not ptt_s.bus_tick(0x00001234, PTT_TICK_ACTIVE))

# check_staleness: only flags ACTIVE entries past threshold
ptt_st = PondPTT("p_stale", PondPTT.STATIC)
idx_st = ptt_st.register(0x00B00000, TYPE_TILE_IN, label="stale_tile")
ptt_st.transition(idx_st, STATUS_LOADING)
ptt_st.transition(idx_st, STATUS_IDLE)
ptt_st.transition(idx_st, STATUS_WAITING)
ptt_st.transition(idx_st, STATUS_ACTIVE)
ptt_st.register_sentry(idx_st, staleness_threshold=0.05)

# Not yet stale
faulted = ptt_st.check_staleness()
check("not stale immediately",         len(faulted) == 0)

# Wait past threshold
_time.sleep(0.1)
faulted = ptt_st.check_staleness()
check("stale after threshold",         len(faulted) == 1)
check("entry transitions to FAULTED",
      ptt_st.get(idx_st).status == STATUS_FAULTED)

# IDLE entry never stale — silence is correct
ptt_idle = PondPTT("p_idle", PondPTT.STATIC)
idx_idle = ptt_idle.register(0x00C00000, TYPE_TILE_IN, label="idle_tile")
ptt_idle.transition(idx_idle, STATUS_LOADING)
ptt_idle.transition(idx_idle, STATUS_IDLE)
ptt_idle.register_sentry(idx_idle, staleness_threshold=0.0)
_time.sleep(0.01)
faulted_idle = ptt_idle.check_staleness()
check("IDLE entry never flagged stale", len(faulted_idle) == 0)

# WAITING entry never stale
ptt_wait = PondPTT("p_wait", PondPTT.STATIC)
idx_wait = ptt_wait.register(0x00D00000, TYPE_TILE_IN, label="wait_tile")
ptt_wait.transition(idx_wait, STATUS_LOADING)
ptt_wait.transition(idx_wait, STATUS_IDLE)
ptt_wait.transition(idx_wait, STATUS_WAITING)
ptt_wait.register_sentry(idx_wait, staleness_threshold=0.0)
_time.sleep(0.01)
faulted_wait = ptt_wait.check_staleness()
check("WAITING entry never flagged stale", len(faulted_wait) == 0)

# ptt_bus_address and is_ptt_bus_address
check("ptt_bus_address(0) == PTT_BUS_BASE", ptt_bus_address(0) == PTT_BUS_BASE)
check("is_ptt_bus_address(PTT_BUS_BASE)",    is_ptt_bus_address(PTT_BUS_BASE))
check("is_ptt_bus_address below range",      not is_ptt_bus_address(0x00001234))
check("is_ptt_bus_address above range",      not is_ptt_bus_address(0x100000000))


# -- Results -------------------------------------------------------------------
total = passed + failed
print(f"\nResults: {passed} passed, {failed} failed out of {total} tests")
