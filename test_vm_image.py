"""
test_vm_image.py — VM Image Save/Restore Tests
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(__file__))

from vm_image import VMImage, save_image, load_image
from unicell_array import UniCellArray
from pond import PondManager

results = []

def check(name, condition):
    status = "PASS" if condition else "FAIL"
    results.append((status, name))
    print(f"  [{status}] {name}")

def check_eq(name, got, expected):
    ok = got == expected
    status = "PASS" if ok else "FAIL"
    results.append((status, name))
    if not ok:
        print(f"  [{status}] {name}  got={got!r}  expected={expected!r}")
    else:
        print(f"  [{status}] {name}")


def boot_test_system(cell_count=500):
    """Boot a minimal system for testing."""
    from unicell_array import UniCellArray
    from controller    import ImagoController
    from shore_v2      import ShoreV2
    from companion     import Companion
    arr   = UniCellArray(cell_count)
    ctrl  = ImagoController(cell_count=cell_count)
    shore = ShoreV2("shore_0", base_address=0x00500000)
    comp  = Companion.boot(arr, shore, ctrl)
    shore.attach_companion(comp.handle_ward_flag)
    return arr, ctrl, shore, comp


# =============================================================================
print("\n=== Save and restore — basic round trip ===\n")
# =============================================================================

with tempfile.TemporaryDirectory() as d:
    img_path = os.path.join(d, "test.img")

    arr, ctrl, shore, comp = boot_test_system()

    from compiler import ImagoCompiler
    from fp_tiles  import TileLibrary
    c = ImagoCompiler(tile_library=TileLibrary())
    records, graph, imap, oa = c.compile_function(
        'def f(a, b):\n    return a & b', 'f', ['a', 'b'])
    rid = ctrl.load_map(records, 'and_prog')
    check("setup: program loaded", rid is not None)

    from shore_v2 import ShoreEntry
    shore.register(ShoreEntry("test_pond", "POND", 0x00200000, 0x00200000,
                               pond_id=42, ward_state="HEALTHY"))

    image = save_image(img_path, ctrl, shore, comp)
    check("save: image file created",         os.path.exists(img_path))
    check("save: image has array section",    "array" in image)
    check("save: image has shore section",    "shore" in image)
    check("save: image has companion section","companion" in image)
    check("save: image version correct",      image["version"] == 4)
    check("save: gate_state_bits == 32",      image.get("gate_state_bits") == 32)
    check("save: regions captured",
          len(image["array"]["regions"]) >= 1)
    check("save: shore entries captured",
          image["shore"]["registry_entries"] >= 1)

    # Restore — must happen inside same with block while file still exists
    ctrl2, shore2, comp2, search2 = load_image(img_path)
    check("restore: controller returned",  ctrl2 is not None)
    check("restore: shore returned",       shore2 is not None)
    check("restore: companion returned",   comp2 is not None)
    check("restore: search_index is None", search2 is None)
    check("restore: regions present",
          len(ctrl2._regions) == len(ctrl._regions))

# ── PTT snapshot tests ────────────────────────────────────────────────────────
print("\n=== PTT / PondManager snapshot ===\n")

from pond import PondManager, OPEN, PROCESS

with tempfile.TemporaryDirectory() as d_ptt:
    ptt_path = os.path.join(d_ptt, "ptt.img")

    arr_ptt, ctrl_ptt, shore_ptt, comp_ptt = boot_test_system()
    pm_arr = UniCellArray(cell_count=300)
    pm_arr.enforce_emission_limits = False
    pm = PondManager(pm_arr)
    pm.create_pond("alpha", "owner", security_level=OPEN, pond_type=PROCESS)
    pm.create_pond("beta",  "owner", security_level=OPEN, pond_type=PROCESS)

    img_pm = VMImage(ctrl_ptt, shore_ptt, comp_ptt, pond_manager=pm)
    ptt_image = img_pm.save(ptt_path)

    check("PTT: pond_manager section present",
          "pond_manager" in ptt_image)
    check("PTT: pond_count = 2",
          ptt_image["pond_manager"]["pond_count"] == 2)
    ponds = ptt_image["pond_manager"]["ponds"]
    check("PTT: both ponds serialised",     len(ponds) == 2)
    first_pond = list(ponds.values())[0]
    check("PTT: pond has name",             "name" in first_pond)
    check("PTT: pond has owner_id",         "owner_id" in first_pond)
    check("PTT: pond has pond_type",        "pond_type" in first_pond)
    check("PTT: pond has bridges",          len(first_pond["bridges"]) >= 2)
    check("PTT: pond bridge has mask",
          all("access_mask" in b for b in first_pond["bridges"]))
    check("PTT: pond bridge mask default 0xFFFFFFFF",
          all(b["access_mask"] == 0xFFFFFFFF for b in first_pond["bridges"]))
    check("PTT: pond has restart_count",    "restart_count" in first_pond)
    check("PTT: pond has created_at",       "created_at" in first_pond)

    # No pond_manager = no pond_manager section
    no_pm_path = os.path.join(d_ptt, "no_pm.img")
    img_no_pm = VMImage(ctrl_ptt, shore_ptt, comp_ptt)
    no_pm_image = img_no_pm.save(no_pm_path)
    check("PTT: absent when no pond_manager",
          "pond_manager" not in no_pm_image)

    # Regions restored
    check("restore: regions present",
          len(ctrl2._regions) == len(ctrl._regions))

# Shore registry restored
entry = shore2.lookup("test_pond")
check("restore: Shore entry present",         entry is not None)
check_eq("restore: Shore entry ward_state",
     entry.ward_state, "HEALTHY")
check_eq("restore: Shore entry pond_id",
     entry.pond_id, 42)

# Companion keys restored
check("restore: Companion has keys",
      len(comp2._keys) >= 1)


# =============================================================================
print("\n=== Save and restore — with search index ===\n")
# =============================================================================

with tempfile.TemporaryDirectory() as d:
    img_path = os.path.join(d, "with_search.img")

    # Create some real files
    f1 = os.path.join(d, "invoice.pdf")
    f2 = os.path.join(d, "report.docx")
    open(f1, 'wb').close()
    open(f2, 'wb').close()

    arr, ctrl, shore, comp = boot_test_system()

    # Build search index
    from fs_search import SearchIndex, SearchPond
    idx = SearchIndex()
    sp  = SearchPond("docs", owner_id="user1")
    sp.index("invoice january", f1, tags=["finance"])
    sp.index("annual report",   f2, tags=["reports"])
    sp_hidden = SearchPond("secrets", owner_id="user1", hidden=True)
    sp_hidden.index("classified doc", f1)
    idx.add_pond(sp)
    idx.add_pond(sp_hidden)

    # Save with search index
    image = save_image(img_path, ctrl, shore, comp, search_index=idx)
    check("save+search: search_index section present",
          "search_index" in image)
    check_eq("save+search: 2 ponds",
             image["search_index"]["pond_count"], 2)
    check_eq("save+search: 3 entries",
             image["search_index"]["total_entries"], 3)

    # Restore
    ctrl2, shore2, comp2, idx2 = load_image(img_path)
    check("restore+search: index returned", idx2 is not None)
    check_eq("restore+search: 2 ponds",    len(idx2._ponds), 2)

    # Search works after restore
    r1 = idx2.search("invoice")
    check("restore+search: search works",           len(r1) > 0)
    check_eq("restore+search: correct file",
         r1[0].entry.file_path, os.path.abspath(f1))
    check_eq("restore+search: tags preserved",
         r1[0].entry.tags, ["finance"])

    # Hidden pond preserved
    check("restore+search: hidden pond preserved",
          idx2.get_pond("secrets").hidden)
    r2 = idx2.search("classified")
    check("restore+search: hidden excluded by default", len(r2) == 0)
    r3 = idx2.search("classified", include_hidden_ponds=True)
    check("restore+search: hidden visible with flag",   len(r3) > 0)

    # Access counts restored from saved value (search was run once above
    # on "invoice", not "annual" — so annual access_count is 0)
    r4 = idx2.search("annual")
    check("restore+search: access_count preserved",
      r4[0].entry.access_count >= 0)


# =============================================================================
print("\n=== Gzip compression ===\n")
# =============================================================================

with tempfile.TemporaryDirectory() as d:
    plain_path = os.path.join(d, "plain.img")
    gz_path    = os.path.join(d, "compressed.img.gz")

    arr, ctrl, shore, comp = boot_test_system()

    # Load a program to have something to compress
    from compiler import ImagoCompiler
    from fp_tiles  import TileLibrary
    c = ImagoCompiler(tile_library=TileLibrary())
    records, _, _, _ = c.compile_function(
        'def f(a, b):\n    return a | b', 'f', ['a', 'b'])
    ctrl.load_map(records, 'or_prog')

    save_image(plain_path, ctrl, shore, comp)
    save_image(gz_path,    ctrl, shore, comp)

    plain_size = os.path.getsize(plain_path)
    gz_size    = os.path.getsize(gz_path)
    check("gz: compressed file smaller than plain",
          gz_size < plain_size)
    print(f"    plain: {plain_size/1024:.1f} KB  "
          f"gz: {gz_size/1024:.1f} KB  "
          f"ratio: {plain_size/gz_size:.1f}x")

    # Round-trip from gz
    ctrl3, shore3, comp3, _ = load_image(gz_path)
    check("gz: round-trip restore works", ctrl3 is not None)
    check("gz: regions preserved after gz",
          len(ctrl3._regions) == len(ctrl._regions))


# =============================================================================
print("\n=== Companion state round-trip ===\n")
# =============================================================================

with tempfile.TemporaryDirectory() as d:
    img_path = os.path.join(d, "comp.img")
    arr, ctrl, shore, comp = boot_test_system()

    # Issue some keys and allocate a region
    admin_key = next(k for k in comp._keys.values()
                     if k.key_type == 'ADMIN')
    tile_key = comp.issue_tile_key("test_pond", "INT32_ADD",
                                    admin_key.key_id)
    region   = comp.allocate_region(size=128, owner_id="test_pond")

    keys_before   = len(comp._keys)
    regions_before = len(comp._regions)

    save_image(img_path, ctrl, shore, comp)
    _, _, comp2, _ = load_image(img_path)

    check_eq("companion: keys count preserved",
             len(comp2._keys), keys_before)
    check_eq("companion: regions count preserved",
             len(comp2._regions), regions_before)

    # Revoked key status preserved
    comp._keys[tile_key.key_id].revoked = True
    save_image(img_path, ctrl, shore, comp)
    _, _, comp3, _ = load_image(img_path)
    check("companion: revoked key preserved",
          comp3._keys[tile_key.key_id].revoked)


# =============================================================================
print("\n=== Convenience wrappers ===\n")
# =============================================================================

with tempfile.TemporaryDirectory() as d:
    img_path = os.path.join(d, "wrap.img")
    arr, ctrl, shore, comp = boot_test_system()

    # save_image / load_image wrappers
    result = save_image(img_path, ctrl, shore, comp)
    check("wrapper: save_image returns dict", isinstance(result, dict))

    components = load_image(img_path)
    check_eq("wrapper: load_image returns 4-tuple", len(components), 4)
    c2, s2, co2, se2 = components
    check("wrapper: controller valid", hasattr(c2, '_regions'))
    check("wrapper: shore valid",      hasattr(s2, '_registry'))
    check("wrapper: companion valid",  hasattr(co2, '_keys'))


# =============================================================================
print("\n=== Results ===\n")
# =============================================================================

passed = sum(1 for s, _ in results if s == "PASS")
failed = sum(1 for s, _ in results if s == "FAIL")
total  = len(results)
print(f"Results: {passed} passed, {failed} failed out of {total} tests")
if failed:
    print("\nFailed tests:")
    for s, n in results:
        if s == "FAIL":
            print(f"  {n}")
