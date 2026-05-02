"""
test_shore_v2.py — ShoreV2 System Registry Tests

Validates the complete ShoreV2 implementation:

  ShoreTile      — internal table with capacity, growth, snapshot/restore
  ShoreEntry     — registry entry with address resolution
  ShoreV2        — four-table system registry

  Operations:    register, deregister, update, lookup, lookup_address,
                 lookup_pond, find_by_type, find_by_ward_state
  Extended:      register_extended, resolve_extended, is_proxy
  Connections:   connect, disconnect, connections_for
  Packets:       receive_packet (ANNOUNCE, READY, MOVING, ROUTE_UPDATE)
  Migration:     snapshot, restore, relocate
  Growth:        table growth, shrink_to_fit, needs_growth signals

Run with: python3 test_shore_v2.py
"""

from shore_v2 import (ShoreV2, ShoreEntry, ShoreTile, Connection,
                       ExtAddr, PROXY_BASE, PROXY_TOP)
from packet_spec import (Packet, CapabilityDescriptor,
                          POND_TYPE_PROCESS, POND_TYPE_LIBRARY,
                          POND_TYPE_FILE, POND_TYPE_COMPANION,
                          WARD_STATE_HEALTHY, WARD_STATE_DEGRADED,
                          WARD_STATE_IDLE, WARD_STATE_STALLED,
                          SECURITY_OPEN, SECURITY_PRIVATE, SECURITY_HIDDEN,
                          FLAG_ANNOUNCE, FLAG_CAPABILITY, FLAG_READY,
                          FLAG_MOVING, FLAG_ROUTE_UPDATE, FLAG_ACK)

results = []

def check(name, condition):
    status = "PASS" if condition else "FAIL"
    results.append((status, name))
    print(f"  [{status}] {name}")

def check_eq(name, got, expected):
    ok = got == expected
    if not ok:
        print(f"    got {got!r}, expected {expected!r}")
    check(name, ok)

def make_shore(shore_id="test", base=0x00500000, capacity=16):
    return ShoreV2(shore_id=shore_id, base_address=base,
                   initial_capacity=capacity)

def make_entry(name, addr=0x1000, rtype="POND", pond_id=0,
               base=None, offset=0, ward="IDLE"):
    return ShoreEntry(name=name, resource_type=rtype,
                      local_address=addr, base_address=base,
                      offset=offset, pond_id=pond_id, ward_state=ward)

def make_cap(pond_type=POND_TYPE_PROCESS, bridge_count=2,
             in_lanes=2, out_lanes=2, ward=WARD_STATE_HEALTHY,
             security=SECURITY_OPEN, pond_id=0):
    return CapabilityDescriptor(
        pond_type=pond_type, bridge_count=bridge_count,
        inbound_lanes=in_lanes, outbound_lanes=out_lanes,
        ward_state=ward, security_level=security, pond_id=pond_id)


# =============================================================================
print("\n=== ShoreTile — basic operations ===\n")

tile = ShoreTile("test_tile", capacity=4)
check_eq("Empty tile entry_count=0",  tile.entry_count, 0)
check_eq("Empty tile utilisation=0",  tile.utilisation, 0.0)
check("Empty tile not full",          not tile.is_full)
check("Empty tile doesn't need growth", not tile.needs_growth)

ok = tile.put("a", 1)
tile.put("b", 2); tile.put("c", 3)
check("put() returns True",           ok)
check_eq("entry_count=3",             tile.entry_count, 3)
check_eq("get() returns value",       tile.get("a"), 1)
check("get() missing returns None",   tile.get("z") is None)

tile.put("d", 4)
check("at capacity: is_full",         tile.is_full)

ok_full = tile.put("e", 5)
check("put() on full tile returns False", not ok_full)
check_eq("entry_count still 4",       tile.entry_count, 4)

removed = tile.remove("a")
check("remove() returns True",        removed)
check_eq("entry_count after remove=3", tile.entry_count, 3)
check("remove() missing returns False", not tile.remove("z"))

# Growth
tile.grow(4)
check_eq("After grow: capacity=8",    tile.capacity, 8)
ok_after = tile.put("e", 5)
check("put() succeeds after grow",    ok_after)

# Shrink to fit
freed = tile.shrink_to_fit()
check("shrink_to_fit returns freed count", freed >= 0)
check("capacity >= entry_count after shrink",
      tile.capacity >= tile.entry_count)


# =============================================================================
print("\n=== ShoreTile — snapshot and restore ===\n")

tile2 = ShoreTile("snap_tile", capacity=8)
tile2.put("x", 42); tile2.put("y", 99)
state = tile2.snapshot()

tile3 = ShoreTile("snap_tile", capacity=4)
tile3.restore(state)
check_eq("Restored entry_count=2",    tile3.entry_count, 2)
check_eq("Restored get('x')=42",      tile3.get("x"), 42)
check_eq("Restored capacity=8",       tile3.capacity, 8)


# =============================================================================
print("\n=== ShoreTile — needs_growth signal ===\n")

tile4 = ShoreTile("growth_tile", capacity=4)
for i in range(3):
    tile4.put(f"k{i}", i)
# 3/4 = 75% < 85% threshold
check("75% full: needs_growth=False", not tile4.needs_growth)
tile4.put("k3", 3)
# 4/4 = 100% >= 85%
check("100% full: needs_growth=True", tile4.needs_growth)


# =============================================================================
print("\n=== ShoreEntry — address resolution ===\n")

# Absolute address
e1 = make_entry("abs", addr=0x5000)
check_eq("Absolute resolve", e1.resolve_address(), 0x5000)

# Relative address (base + offset)
e2 = ShoreEntry(name="rel", resource_type="BRIDGE",
                local_address=0x4002,
                base_address=0x4000, offset=2)
check_eq("Relative resolve = base+offset", e2.resolve_address(), 0x4002)

# No address
e3 = ShoreEntry(name="none", resource_type="EXTERNAL")
check("No address resolves to None", e3.resolve_address() is None)


# =============================================================================
print("\n=== ShoreV2 — initialisation ===\n")

shore = make_shore()
check("Shore initialises",            shore is not None)
check_eq("shore_id set",              shore.shore_id, "test")
check("__shore__ entry exists",       shore.lookup("__shore__") is not None)
check("Initial entry count >= 1",  shore._registry.entry_count >= 1)


# =============================================================================
print("\n=== ShoreV2 — register and lookup ===\n")

shore = make_shore()
e = make_entry("pond_1_in", addr=0x10000, rtype="BRIDGE", pond_id=1,
               ward="HEALTHY")
ok = shore.register(e)
check("register() returns True",      ok)

found = shore.lookup("pond_1_in")
check("lookup() finds entry",         found is not None)
check_eq("lookup name",               found.name, "pond_1_in")
check_eq("lookup address",            found.local_address, 0x10000)
check_eq("lookup ward_state",         found.ward_state, "HEALTHY")

# Reverse lookup
found2 = shore.lookup_address(0x10000)
check("lookup_address() works",       found2 is not None)
check_eq("lookup_address name",       found2.name, "pond_1_in")

# lookup_pond by pond_id
e2 = make_entry("pond_2_in", addr=0x20000, pond_id=2)
shore.register(e2)
found3 = shore.lookup_pond(2)
check("lookup_pond() works",          found3 is not None)
check_eq("lookup_pond name",          found3.name, "pond_2_in")

# Miss
check("lookup() miss returns None",   shore.lookup("missing") is None)
check("lookup_address() miss=None",   shore.lookup_address(0xDEAD) is None)
check("lookup_pond() miss=None",      shore.lookup_pond(999) is None)


# =============================================================================
print("\n=== ShoreV2 — update ===\n")

shore = make_shore()
shore.register(make_entry("p1", addr=0x1000, ward="IDLE"))
ok = shore.update("p1", ward_state="HEALTHY", local_address=0x2000)
check("update() returns True",        ok)
check_eq("update ward_state",         shore.lookup("p1").ward_state, "HEALTHY")
check_eq("update local_address",      shore.lookup("p1").local_address, 0x2000)

# Address map updated
check("Old address removed from map", shore.lookup_address(0x1000) is None)
check("New address in map",           shore.lookup_address(0x2000) is not None)

# Miss
check("update() miss=False",         not shore.update("missing", ward_state="X"))


# =============================================================================
print("\n=== ShoreV2 — deregister ===\n")

shore = make_shore()
shore.register(make_entry("p1", addr=0x1000))
ok = shore.deregister("p1")
check("deregister() returns True",    ok)
check("Entry removed",                shore.lookup("p1") is None)
check("Address map cleared",          shore.lookup_address(0x1000) is None)
check("deregister() miss=False",      not shore.deregister("missing"))


# =============================================================================
print("\n=== ShoreV2 — find_by_type and find_by_ward_state ===\n")

shore = make_shore()
shore.register(make_entry("b1", addr=0x1000, rtype="BRIDGE", ward="HEALTHY"))
shore.register(make_entry("b2", addr=0x2000, rtype="BRIDGE", ward="DEGRADED"))
shore.register(make_entry("p1", addr=0x3000, rtype="POND",   ward="HEALTHY"))

bridges = shore.find_by_type("BRIDGE")
check_eq("find_by_type BRIDGE count=2", len(bridges), 2)

ponds = shore.find_by_type("POND")
check("find_by_type POND includes entry", any(p.name == "p1" for p in ponds))

healthy = shore.find_by_ward_state("HEALTHY")
check("find_by_ward_state HEALTHY finds entries",
      any(e.name == "b1" for e in healthy))
check("find_by_ward_state HEALTHY excludes DEGRADED",
      not any(e.name == "b2" for e in healthy))


# =============================================================================
print("\n=== ShoreV2 — extended address translation ===\n")

shore = make_shore()
proxy = shore.register_extended(0x200000000, "remote_storage")
check("register_extended returns proxy", proxy >= PROXY_BASE)
check("proxy in reserved range",        shore.is_proxy(proxy))
check("non-proxy not in range",         not shore.is_proxy(0x00400000))

ext = shore.resolve_extended(proxy)
check("resolve_extended returns ExtAddr", ext is not None)
check_eq("real_addr correct",           ext.real_addr, 0x200000000)
check_eq("description correct",         ext.description, "remote_storage")

# Multiple extended addresses get sequential proxies
proxy2 = shore.register_extended(0x300000000, "remote_b")
check("Second proxy is next sequential", proxy2 == proxy + 1)

# Unknown proxy
check("resolve unknown proxy=None",     shore.resolve_extended(0xF9999999) is None)

# Extended resource also in registry
found = shore.lookup("remote_storage")
check("Extended resource in registry",  found is not None)
check_eq("External resource_type",      found.resource_type, "EXTERNAL")


# =============================================================================
print("\n=== ShoreV2 — connections ===\n")

shore = make_shore()
shore.register(make_entry("src", addr=0x1000))
shore.register(make_entry("dst", addr=0x2000))

conn_id = shore.connect("src", "dst")
check("connect() returns conn_id",     conn_id is not None)

conns = shore.connections_for("src")
check_eq("connections_for source count=1", len(conns), 1)
check_eq("connection source_name",    conns[0].source_name, "src")
check_eq("connection dest_name",      conns[0].dest_name, "dst")
check("connection is active",         conns[0].active)

# Disconnect
ok = shore.disconnect(conn_id)
check("disconnect() returns True",    ok)
active = shore.connections_for("src")
check("After disconnect: no active",  len([c for c in active if c.active]) == 0)

# Connect with unknown resource
bad = shore.connect("src", "unknown")
check("connect() unknown returns None", bad is None)

# Status includes connection count
shore2 = make_shore()
shore2.register(make_entry("a", addr=0x1000))
shore2.register(make_entry("b", addr=0x2000))
shore2.connect("a", "b")
st = shore2.status()
check_eq("status active_connections=1", st["active_connections"], 1)


# =============================================================================
print("\n=== ShoreV2 — receive_packet: ANNOUNCE ===\n")

shore = make_shore()
cap = make_cap(pond_type=POND_TYPE_PROCESS, bridge_count=3,
               in_lanes=4, out_lanes=2, ward=WARD_STATE_HEALTHY,
               security=SECURITY_OPEN, pond_id=5)
pkt = Packet.announce(shore_address=0x00500000, capability=cap)
resp = shore.receive_packet(pkt)

check("ANNOUNCE returns ACK",         resp is not None and resp.is_ack)
found = shore.lookup("pond_5")
check("ANNOUNCE registers pond",      found is not None)
check_eq("ANNOUNCE ward_state",       found.ward_state, "HEALTHY")
check_eq("ANNOUNCE resource_type",    found.resource_type, "POND")
check("ANNOUNCE capabilities stored", found.capabilities is not None)
check_eq("ANNOUNCE cap pond_type",    found.capabilities.pond_type, POND_TYPE_PROCESS)

# Second ANNOUNCE (update) — same pond_id, new address
pkt2 = Packet.announce(shore_address=0x00600000, capability=cap)
shore.receive_packet(pkt2)
found2 = shore.lookup("pond_5")
check_eq("Second ANNOUNCE updates address", found2.local_address, 0x00600000)


# =============================================================================
print("\n=== ShoreV2 — receive_packet: READY ===\n")

shore = make_shore()
# First register as IDLE via announce
cap_idle = make_cap(pond_id=6, ward=WARD_STATE_IDLE)
shore.receive_packet(Packet.announce(0x00500000, cap_idle))
check_eq("Pre-READY ward=IDLE",       shore.lookup("pond_6").ward_state, "IDLE")

# Now send READY
cap_ready = make_cap(pond_id=6, ward=WARD_STATE_HEALTHY)
pkt_ready = Packet.ready(shore_address=0x00400000, capability=cap_ready)
resp = shore.receive_packet(pkt_ready)
check("READY returns ACK",            resp is not None and resp.is_ack)
check_eq("READY updates ward=HEALTHY", shore.lookup("pond_6").ward_state, "HEALTHY")


# =============================================================================
print("\n=== ShoreV2 — receive_packet: MOVING ===\n")

shore = make_shore()
shore.register(make_entry("pond_7", addr=0x00700000, ward="HEALTHY"))
pkt_moving = Packet(address=0x00700000, flags=0b0001000)  # FLAG_MOVING
shore.receive_packet(pkt_moving)
found = shore.lookup("pond_7")
check_eq("MOVING updates ward=MOVING", found.ward_state, "MOVING")


# =============================================================================
print("\n=== ShoreV2 — receive_packet: ROUTE_UPDATE ===\n")

shore = make_shore()
shore.register(make_entry("pond_8", addr=0x00800000, ward="HEALTHY"))
shore.register(make_entry("pond_9", addr=0x00900000))
shore.connect("pond_8", "pond_9")

# Pond_8 moves to new address
pkt_route = Packet.route_update(dest_address=0x00800000,
                                 new_external_address=0x00A00000)
shore.receive_packet(pkt_route)
found = shore.lookup("pond_8")
check_eq("ROUTE_UPDATE updates address", found.local_address, 0x00A00000)

# Connection updated
conns = shore.connections_for("pond_8")
updated = [c for c in conns if c.active]
check("Connection source_address updated",
      any(c.source_address == 0x00A00000 for c in updated))


# =============================================================================
print("\n=== ShoreV2 — CONFIG packet (cell configuration) ===\n")

shore = make_shore()
pkt_cfg = Packet.config(address=0x1000, gate_state=0b000000001,
                         input_offset=0x010, output_offset=0x020)
resp = shore.receive_packet(pkt_cfg)
# CONFIG packets are not registry operations — Shore ignores them
check("CONFIG packet: Shore returns None", resp is None)


# =============================================================================
print("\n=== ShoreV2 — snapshot and restore ===\n")

shore = make_shore("snap_shore", base=0x00500000)
shore.register(make_entry("r1", addr=0x1000, pond_id=1))
shore.register(make_entry("r2", addr=0x2000, pond_id=2))
shore.register_extended(0x100000000, "ext_device")
shore.connect("r1", "r2")

state = shore.snapshot()
check("snapshot returns dict",         isinstance(state, dict))
check("snapshot has registry",         "registry" in state)
check("snapshot has translation",      "translation" in state)
check("snapshot has connections",      "connections" in state)

# Restore into a fresh Shore
shore2 = make_shore("restored")
shore2.restore(state)
check_eq("Restored shore_id",          shore2.shore_id, "snap_shore")
check_eq("Restored entry count",       shore2._registry.entry_count,
          shore._registry.entry_count)
check("Restored r1 exists",            shore2.lookup("r1") is not None)
check("Restored r2 exists",            shore2.lookup("r2") is not None)
check("Restored translation exists",
      shore2._translation.entry_count > 0)


# =============================================================================
print("\n=== ShoreV2 — relocate ===\n")

shore = make_shore("reloc", base=0x00500000)
shore.register(ShoreEntry(
    name="internal_cell", resource_type="CELL",
    local_address=0x00500010,
    base_address=0x00500000, offset=0x10))

shore.relocate(0x00700000)
check_eq("Relocated base_address",    shore.base_address, 0x00700000)

moved = shore.lookup("internal_cell")
check("Relocated entry updated",      moved is not None)
check_eq("Relocated local_address",   moved.local_address, 0x00700010)
check_eq("Relocated base_address",    moved.base_address, 0x00700000)


# =============================================================================
print("\n=== ShoreV2 — automatic table growth ===\n")

shore = make_shore(capacity=4)
# Fill registry to capacity (it already has __shore__)
# With capacity=4 and __shore__ pre-populated, we can add 3 more before growth
for i in range(5):
    shore.register(make_entry(f"auto_{i}", addr=0x1000+i))

# Shore should have auto-grown to accommodate all entries
check("Auto-growth: all entries registered",
      all(shore.lookup(f"auto_{i}") is not None for i in range(5)))
check("Auto-growth: capacity increased",
      shore._registry.capacity > 4)


# =============================================================================
print("\n=== ShoreV2 — dump ===\n")

shore = make_shore()
shore.register(make_entry("test_pond", addr=0x9000))
dump = shore.dump()
check("dump() returns string",        isinstance(dump, str))
check("dump() contains shore_id",     shore.shore_id in dump)
check("dump() contains entry name",   "test_pond" in dump)


# =============================================================================
print("\n=== ShoreV2 — status ===\n")

shore = make_shore()
shore.register(make_entry("p1", addr=0x1000))
shore.register(make_entry("p2", addr=0x2000))
shore.connect("p1", "p2")
shore.register_extended(0x100000000, "ext")

st = shore.status()
check("status has shore_id",          "shore_id" in st)
check("status has tables",            "tables" in st)
check("status has total_entries",     "total_entries" in st)
check("status total_entries >= 2",    st["total_entries"] >= 2)
check("status active_connections=1",  st["active_connections"] == 1)
check("status proxy_used >= 1",       st["proxy_addresses_used"] >= 1)
check("status tables has registry",   "registry" in st["tables"])


# =============================================================================
print("\n=== Results ===\n")

passed = sum(1 for s, _ in results if s == "PASS")
failed = sum(1 for s, _ in results if s == "FAIL")
total  = len(results)
print(f"Results: {passed} passed, {failed} failed out of {total} tests")
if failed == 0:
    print("ALL TESTS PASSED")
else:
    print("\nFailed tests:")
    for status, name in results:
        if status == "FAIL":
            print(f"  [FAIL] {name}")
