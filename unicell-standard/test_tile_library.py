"""
test_tile_library.py — Tile Library Signing & Licensing Tests

Validates the tile signing and licensing system per
Imago Tile Library & Licensing Specification v0.1:

  - Tile signing: HMAC-SHA256 over canonical fields using machine key
  - machine_id: truncated SHA-256 of machine key (public identifier)
  - Signature verification: correct key passes, wrong key fails
  - Tamper detection: modified cell_map fails signature check
  - Checksum verification: metadata corruption detected
  - License tiers: BASE < INTEGER < FLOAT < FULL
  - License enforcement: insufficient tier rejected
  - Save/load round-trip: tile persists correctly to .icm file
  - Library persistence: save_library() saves all tiles
  - Controller.load_tile(): end-to-end from .icm file to running region
  - Controller licensed_tier: enforced on tile load

Run with: python3 test_tile_library.py
"""

import os, json, tempfile
from fp_tiles import (TileLibrary, TilePlacer,
                      TileSigningError, TileLicenseError,
                      TIER_BASE, TIER_INTEGER, TIER_FLOAT, TIER_FULL)
from controller import ImagoController, CellMapRecord
from unicell import VAR_TRUE, VAR_FALSE

results = []
MACHINE_KEY       = 0xDEADC0DEBEEF1234   # matches ImagoController._machine_key
WRONG_MACHINE_KEY = 0x1234567890ABCDEF

def check(name, condition):
    status = "PASS" if condition else "FAIL"
    results.append((status, name))
    print(f"  [{status}] {name}")

lib = TileLibrary()

# =============================================================================
print("\n=== Tile Signing ===\n")

tile_eq = lib.get("INT32_EQ")
signed  = lib.sign_tile(tile_eq, MACHINE_KEY, TIER_INTEGER)

check("sign_tile: returns dict",           isinstance(signed, dict))
check("sign_tile: tile_name present",      signed["tile_name"] == "INT32_EQ")
check("sign_tile: version present",        "version" in signed)
check("sign_tile: compiled_at is int",     isinstance(signed["compiled_at"], int))
check("sign_tile: signature is str",       isinstance(signed["signature"], str))
check("sign_tile: signature length 64",    len(signed["signature"]) == 64)
check("sign_tile: machine_id length 16",   len(signed["machine_id"]) == 16)
check("sign_tile: license_tier correct",   signed["license_tier"] == TIER_INTEGER)
check("sign_tile: checksum length 64",     len(signed["checksum"]) == 64)
check("sign_tile: cell_map is list",       isinstance(signed["cell_map"], list))
check("sign_tile: cell_map length matches tile",
      len(signed["cell_map"]) == len(tile_eq.records))
check("sign_tile: input_addresses present",
      "in_a" in signed["input_addresses"])
check("sign_tile: output_addresses present",
      isinstance(signed["output_addresses"], list))

# machine_id is deterministic for the same key
signed2 = lib.sign_tile(tile_eq, MACHINE_KEY, TIER_INTEGER)
check("sign_tile: machine_id deterministic for same key",
      signed["machine_id"] == signed2["machine_id"])

# Different machines have different machine_ids
signed_wrong = lib.sign_tile(tile_eq, WRONG_MACHINE_KEY, TIER_INTEGER)
check("sign_tile: different machine → different machine_id",
      signed["machine_id"] != signed_wrong["machine_id"])

# =============================================================================
print("\n=== Signature Verification ===\n")

valid, reason = lib.verify_tile(signed, MACHINE_KEY, TIER_FULL)
check("verify_tile: correct key → valid", valid)
check("verify_tile: correct key → reason 'valid'", reason == "valid")

# Wrong machine key
valid2, reason2 = lib.verify_tile(signed, WRONG_MACHINE_KEY, TIER_FULL)
check("verify_tile: wrong machine key → invalid", not valid2)
check("verify_tile: wrong machine key → machine_id mismatch",
      "machine_id" in reason2)

# Tampered cell_map (gate_state changed)
tampered = json.loads(json.dumps(signed))  # deep copy
tampered["cell_map"][0]["gate_state"] = 999
valid3, reason3 = lib.verify_tile(tampered, MACHINE_KEY, TIER_FULL)
check("verify_tile: tampered cell_map → signature invalid", not valid3)
check("verify_tile: tampered cell_map → signature reason",
      "signature" in reason3)

# Tampered metadata (pipeline_depth changed)
tampered2 = json.loads(json.dumps(signed))
tampered2["metadata"]["pipeline_depth"] = 9999
valid4, reason4 = lib.verify_tile(tampered2, MACHINE_KEY, TIER_FULL)
check("verify_tile: tampered metadata → checksum fails", not valid4)

# Tampered license_tier (trying to upgrade)
tampered3 = json.loads(json.dumps(signed))
tampered3["license_tier"] = TIER_FULL   # try to upgrade
valid5, reason5 = lib.verify_tile(tampered3, MACHINE_KEY, TIER_FULL)
check("verify_tile: tampered license_tier → signature invalid", not valid5)

# =============================================================================
print("\n=== License Tier Enforcement ===\n")

# Sign tiles at different tiers
signed_base = lib.sign_tile(lib.get("INT32_MUX"),   MACHINE_KEY, TIER_BASE)
signed_int  = lib.sign_tile(lib.get("INT32_ADD"),   MACHINE_KEY, TIER_INTEGER)
signed_fp   = lib.sign_tile(lib.get("FP32_CMP_EQ"), MACHINE_KEY, TIER_FLOAT)

# FULL license accepts all tiers
for sd, name in [(signed_base, "BASE"), (signed_int, "INTEGER"), (signed_fp, "FLOAT")]:
    v, r = lib.verify_tile(sd, MACHINE_KEY, TIER_FULL)
    check(f"License FULL accepts {name} tile", v)

# FLOAT accepts BASE, INTEGER, FLOAT but not FULL-only tiles
v, r = lib.verify_tile(signed_fp, MACHINE_KEY, TIER_FLOAT)
check("License FLOAT accepts FLOAT tile", v)
v, r = lib.verify_tile(signed_int, MACHINE_KEY, TIER_FLOAT)
check("License FLOAT accepts INTEGER tile", v)

# INTEGER does NOT accept FLOAT tile
v, r = lib.verify_tile(signed_fp, MACHINE_KEY, TIER_INTEGER)
check("License INTEGER rejects FLOAT tile", not v)
check("License INTEGER rejects FLOAT: license reason", "license" in r)

# BASE does NOT accept INTEGER tile
v, r = lib.verify_tile(signed_int, MACHINE_KEY, TIER_BASE)
check("License BASE rejects INTEGER tile", not v)

# BASE accepts BASE tile
v, r = lib.verify_tile(signed_base, MACHINE_KEY, TIER_BASE)
check("License BASE accepts BASE tile", v)

# =============================================================================
print("\n=== Save and Load Round-Trip ===\n")

with tempfile.TemporaryDirectory() as tmpdir:
    # Save INT32_EQ to .icm file
    path = os.path.join(tmpdir, "INT32_EQ.icm")
    saved_path = lib.save_tile(tile_eq, path, MACHINE_KEY, TIER_INTEGER)
    check("save_tile: file created", os.path.exists(saved_path))
    check("save_tile: .icm extension", saved_path.endswith(".icm"))

    # Verify file contents
    with open(saved_path) as f:
        raw = json.load(f)
    check("save_tile: tile_name in file", raw["tile_name"] == "INT32_EQ")
    check("save_tile: signature in file", "signature" in raw)
    check("save_tile: machine_id in file", "machine_id" in raw)
    check("save_tile: license_tier in file", raw["license_tier"] == TIER_INTEGER)
    check("save_tile: metadata in file", "pipeline_depth" in raw["metadata"])

    # Load back with correct key and sufficient tier
    loaded_tile = lib.load_tile(saved_path, MACHINE_KEY, TIER_FULL)
    check("load_tile: returns Tile object", loaded_tile is not None)
    check("load_tile: correct cell count",
          len(loaded_tile.records) == len(tile_eq.records))
    check("load_tile: correct operation",
          loaded_tile.metadata.operation == "INT32_EQ")
    check("load_tile: pipeline_depth preserved",
          loaded_tile.metadata.pipeline_depth == tile_eq.metadata.pipeline_depth)
    check("load_tile: in_a addresses preserved",
          loaded_tile.in_a == tile_eq.in_a)

    # Load with wrong machine key → TileSigningError
    error_raised = False
    try:
        lib.load_tile(saved_path, WRONG_MACHINE_KEY, TIER_FULL)
    except TileSigningError:
        error_raised = True
    check("load_tile: wrong machine key raises TileSigningError", error_raised)

    # Load with insufficient license → TileLicenseError
    license_error = False
    try:
        lib.load_tile(saved_path, MACHINE_KEY, TIER_BASE)  # needs INTEGER
    except TileLicenseError:
        license_error = True
    check("load_tile: insufficient tier raises TileLicenseError", license_error)

    # save_library: save multiple tiles
    library_dir = os.path.join(tmpdir, "library")
    paths = lib.save_library(library_dir, MACHINE_KEY,
                             tile_names=["INT32_EQ", "INT32_MUX"])
    check("save_library: returns path dict", isinstance(paths, dict))
    check("save_library: correct tile count", len(paths) == 2)
    check("save_library: INT32_EQ saved",
          os.path.exists(paths.get("INT32_EQ", "")))
    check("save_library: INT32_MUX saved",
          os.path.exists(paths.get("INT32_MUX", "")))

    # Reload and verify both
    for name, p in paths.items():
        t = lib.load_tile(p, MACHINE_KEY, TIER_FULL)
        check(f"save_library: {name} loads correctly",
              t.metadata.operation == name)

    # ==========================================================================
    print("\n=== Controller.load_tile — end-to-end ===\n")

    # Save INT32_MUX tile (BASE tier)
    mux_tile = lib.get("INT32_MUX")
    mux_path = os.path.join(tmpdir, "INT32_MUX.icm")
    lib.save_tile(mux_tile, mux_path, MACHINE_KEY, TIER_BASE)

    # Controller with FULL license loads BASE tile
    ctrl = ImagoController(cell_count=mux_tile.metadata.cell_count + 200,
                           licensed_tier=TIER_FULL)
    check("Controller: licensed_tier attribute", ctrl.licensed_tier == TIER_FULL)

    rid = ctrl.load_tile(mux_path, "mux_from_file")
    check("Controller.load_tile: region created", rid is not None)

    if rid:
        region = ctrl._regions[rid]
        check("Controller.load_tile: correct cell count",
              len(region.cell_addresses) == len(mux_tile.records))

        # Run the tile: MUX(sel=1, A=0xAAAAAAAA, B=0x55555555) → A
        def int_to_bits(v, w=32):
            return [(v >> i) & 1 for i in range(w)]
        def bits_to_int(bits):
            return sum(b << i for i, b in enumerate(bits))

        sel = 1
        a_val = 0xAAAAAAAA
        b_val = 0x55555555
        in_a_bits = [sel] + int_to_bits(a_val)
        in_b_bits  = int_to_bits(b_val)

        inputs = {}
        for addr, v in zip(mux_tile.in_a, in_a_bits): inputs[addr] = v
        for addr, v in zip(mux_tile.in_b, in_b_bits): inputs[addr] = v

        result = ctrl.run(rid, inputs=inputs, capture_addresses=mux_tile.out)
        if result:
            got = bits_to_int([result.get(a, 0) for a in mux_tile.out])
            check("Controller.load_tile: MUX(sel=1) selects A", got == a_val)

    # Controller with BASE license tries to load INTEGER tile
    int_path = os.path.join(tmpdir, "INT32_EQ.icm")
    lib.save_tile(tile_eq, int_path, MACHINE_KEY, TIER_INTEGER)

    ctrl_base = ImagoController(cell_count=1000, licensed_tier=TIER_BASE)
    rid_rejected = ctrl_base.load_tile(int_path, "eq_rejected")
    check("Controller: BASE license rejects INTEGER tile", rid_rejected is None)

    # Controller with INTEGER license accepts INTEGER tile
    ctrl_int = ImagoController(
        cell_count=tile_eq.metadata.cell_count + 200,
        licensed_tier=TIER_INTEGER)
    rid_accepted = ctrl_int.load_tile(int_path, "eq_accepted")
    check("Controller: INTEGER license accepts INTEGER tile", rid_accepted is not None)

# =============================================================================
print("\n=== Default License Tier Assignment ===\n")

# Tiles get the correct default tier when signed without explicit tier
from fp_tiles import _TILE_TIERS
for tile_name, expected_tier in _TILE_TIERS.items():
    t = lib.get(tile_name)
    signed_default = lib.sign_tile(t, MACHINE_KEY)
    check(f"Default tier: {tile_name} → {expected_tier}",
          signed_default["license_tier"] == expected_tier)

# =============================================================================

print(f"\n{'='*55}")
passed = sum(1 for s,_ in results if s == "PASS")
failed = sum(1 for s,_ in results if s == "FAIL")
print(f"Results: {passed} passed, {failed} failed out of {len(results)} tests")
if failed == 0:
    print("ALL TESTS PASSED")
    print("\nTile Library & Licensing validated:")
    print("  - HMAC-SHA256 signing over canonical tile fields")
    print("  - machine_id: SHA-256(machine_key)[:16]")
    print("  - Tamper detection: cell_map and metadata changes caught")
    print("  - License tiers: BASE < INTEGER < FLOAT < FULL enforced")
    print("  - Save/load round-trip preserves all tile data")
    print("  - Controller.load_tile(): signed .icm → running region")
    print("  - Wrong machine and insufficient license both rejected")
else:
    print("\nFailed tests:")
    for s, n in results:
        if s == "FAIL":
            print(f"  {n}")
