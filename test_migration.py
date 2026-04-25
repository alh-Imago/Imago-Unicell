"""
test_migration.py — Migration and VM image restore end-to-end tests

Tests:
  - pond.migrate() FREEZE_BODY: addresses update, bridges stay registered
  - pond.migrate() FREEZE_FULL: full freeze and restore
  - VM image save + restore: controller regions, Shore entries preserved
  - Migrate + save: pond at new address survives round-trip
  - Shore entries updated after migration
  - Restore with pond_manager: pond state preserved
"""

import os, sys, tempfile
sys.path.insert(0, os.path.dirname(__file__))

from pond import Pond, PondManager, OPEN, PRIVATE
from pond_types import PROCESS, WORKSPACE
from unicell_array import UniCellArray
from controller import ImagoController
from shore_v2 import ShoreV2, ShoreEntry
from vm_image import VMImage, save_image, load_image
from compiler import ImagoCompiler
from fp_tiles import TileLibrary

results = []

def check(name, condition):
    status = "PASS" if condition else "FAIL"
    results.append((status, name))
    print(f"  [{status}] {name}")

def check_eq(name, got, expected):
    ok = got == expected
    results.append(("PASS" if ok else "FAIL", name))
    if not ok:
        print(f"  [FAIL] {name}  got={got!r}  expected={expected!r}")
    else:
        print(f"  [PASS] {name}")


def make_system():
    ctrl  = ImagoController(cell_count=2000)
    arr   = ctrl.array
    arr.enforce_emission_limits = False
    mgr   = PondManager(arr)
    shore = ShoreV2()
    return ctrl, arr, mgr, shore


# =============================================================================
print("\n=== pond.migrate(): FREEZE_BODY ===\n")
# =============================================================================

ctrl, arr, mgr, shore = make_system()

p = mgr.create_pond("migrating_pond", "owner",
                     security_level=OPEN, pond_type=PROCESS,
                     base_address=0x00100000, region_size=256)

# Register with Shore
shore.register(ShoreEntry(
    "migrating_pond", "POND",
    local_address=0x00100000, base_address=0x00100000,
    pond_id=1, ward_state="HEALTHY"))
for bridge in p.bridges:
    shore.register(ShoreEntry(
        f"migrating_pond_{bridge.role}", "BRIDGE",
        local_address=bridge.external_address,
        base_address=0x00100000,
        pond_id=1, ward_state="HEALTHY"))

old_base = p.base_address
old_bridge_addrs = {b.role: b.external_address for b in p.bridges}

check("migrate: initial base_address set",
      p.base_address == 0x00100000)

# Migrate to new address
new_base = 0x00200000
result = p.migrate(new_base, shore=shore, controller=ctrl, mode="FREEZE_BODY")

check("migrate: returns dict",              isinstance(result, dict))
check_eq("migrate: base_address updated",   p.base_address, new_base)
check("migrate: bridges updated",
      all(b.external_address != old_bridge_addrs[b.role]
          for b in p.bridges
          if b.role in old_bridge_addrs))

# Shore entry should reflect new address
entry = shore.lookup("migrating_pond")
check("migrate: Shore entry updated",       entry is not None)
check_eq("migrate: Shore local_address",    entry.local_address, new_base)


# =============================================================================
print("\n=== pond.migrate(): FREEZE_FULL ===\n")
# =============================================================================

ctrl2, arr2, mgr2, shore2 = make_system()
p2 = mgr2.create_pond("full_freeze_pond", "owner",
                       security_level=OPEN, pond_type=PROCESS,
                       base_address=0x00300000, region_size=256)

old_base2 = p2.base_address
result2 = p2.migrate(0x00400000, mode="FREEZE_FULL")

check("FREEZE_FULL: returns dict",         isinstance(result2, dict))
check_eq("FREEZE_FULL: base updated",      p2.base_address, 0x00400000)


# =============================================================================
print("\n=== VM image save + restore round-trip ===\n")
# =============================================================================

with tempfile.TemporaryDirectory() as d:
    img_path = os.path.join(d, "test_migrate.img")

    ctrl3, arr3, mgr3, shore3 = make_system()

    # Load a program
    c = ImagoCompiler(tile_library=TileLibrary())
    records, graph, imap, oa = c.compile_function(
        'def f(a, b):\n    return a & b', 'f', ['a', 'b'])
    rid = ctrl3.load_map(records, 'and_prog')
    check("setup: program loaded", rid is not None)

    shore3.register(ShoreEntry(
        "restore_test", "POND", 0x00500000, 0x00500000,
        pond_id=99, ward_state="HEALTHY"))

    image = save_image(img_path, ctrl3, shore3)
    check("save: image created",           os.path.exists(img_path))
    check("save: has array section",       "array" in image)
    check("save: has os_name",             image.get("os_name") == "Claudette")
    check("save: has os_version",          image.get("os_version") == "1.2")

    ctrl_r, shore_r, comp_r, _ = load_image(img_path)
    check("restore: controller returned",  ctrl_r is not None)
    check("restore: shore returned",       shore_r is not None)
    check("restore: regions present",
          len(ctrl_r._regions) >= 1)

    entry_r = shore_r.lookup("restore_test")
    check("restore: Shore entry present",  entry_r is not None)
    check_eq("restore: ward_state",        entry_r.ward_state, "HEALTHY")
    check_eq("restore: pond_id",           entry_r.pond_id, 99)


# =============================================================================
print("\n=== Migrate + save + restore ===\n")
# =============================================================================

with tempfile.TemporaryDirectory() as d:
    img_path = os.path.join(d, "post_migrate.img")

    ctrl4, arr4, mgr4, shore4 = make_system()

    p4 = mgr4.create_pond("migratable", "owner",
                           security_level=OPEN, pond_type=PROCESS,
                           base_address=0x00600000, region_size=256)
    shore4.register(ShoreEntry(
        "migratable", "POND", 0x00600000, 0x00600000,
        pond_id=42, ward_state="HEALTHY"))

    # Migrate first
    p4.migrate(0x00700000, shore=shore4, controller=ctrl4)
    check("pre-save: base address migrated",
          p4.base_address == 0x00700000)

    # Save after migration
    ptt_image = save_image(img_path, ctrl4, shore4, pond_manager=mgr4)
    check("post-migrate save: success",    os.path.exists(img_path))

    # Check pond state in image
    if "pond_manager" in ptt_image:
        ponds = ptt_image["pond_manager"]["ponds"]
        check("post-migrate: pond_manager saved", len(ponds) >= 1)
        pond_data = list(ponds.values())[0]
        check_eq("post-migrate: base_address in image",
                 pond_data.get("base_address"), 0x00700000)

    # Restore
    ctrl5, shore5, _, _ = load_image(img_path)
    check("post-migrate restore: success", ctrl5 is not None)

    # Shore should have the migrated address
    e5 = shore5.lookup("migratable")
    check("post-migrate restore: Shore entry present", e5 is not None)


# =============================================================================
print("\n=== VM image with pond_manager PTT ===\n")
# =============================================================================

with tempfile.TemporaryDirectory() as d:
    img_path = os.path.join(d, "ptt.img")

    ctrl6, arr6, mgr6, shore6 = make_system()

    p6a = mgr6.create_pond("alpha", "owner", security_level=OPEN, pond_type=PROCESS)
    p6b = mgr6.create_pond("beta",  "owner", security_level=OPEN, pond_type=WORKSPACE)

    # Set different access masks
    p6a._get_bridge("INBOUND").set_access_mask(0b00000011)
    p6b._get_bridge("INBOUND").set_access_mask(0b00000110)

    image6 = save_image(img_path, ctrl6, shore6, pond_manager=mgr6)

    check("PTT: pond_manager saved",
          "pond_manager" in image6)
    check_eq("PTT: pond count",
             image6["pond_manager"]["pond_count"], 2)

    ponds6 = image6["pond_manager"]["ponds"]
    names6 = {v["name"] for v in ponds6.values()}
    check("PTT: alpha in image",  "alpha" in names6)
    check("PTT: beta in image",   "beta"  in names6)

    # Access masks preserved
    for pond_data in ponds6.values():
        for bridge in pond_data["bridges"]:
            check(f"PTT: bridge {bridge['role']} has access_mask",
                  "access_mask" in bridge)


# =============================================================================
print("\n=== Results ===\n")
# =============================================================================

passed = sum(1 for s, _ in results if s == "PASS")
failed = sum(1 for s, _ in results if s == "FAIL")
print(f"Results: {passed} passed, {failed} failed out of {len(results)} tests")
if failed:
    print("\nFailed:")
    for s, n in results:
        if s == "FAIL":
            print(f"  {n}")
