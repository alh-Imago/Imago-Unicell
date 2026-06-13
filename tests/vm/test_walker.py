"""
test_walker.py — tile walker produces valid composer-loadable .icm

Checks the walker's serialisation against the schema the composer's raw-load
path needs (program_id + records with gs/in/out/inB/init, inputs/outputs as
{name:addr} dicts), and that the records round-trip the tile's cell network.

Run with: python3 test_walker.py
"""

import os, sys, json, importlib.util
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)

# load the walker module by path (it lives under examples/walker/)
spec = importlib.util.spec_from_file_location(
    "walk_tiles", os.path.join(REPO, "examples", "walker", "walk_tiles.py"))
walk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(walk)

from fp_tiles import TileLibrary
lib = TileLibrary()

results = []
def check(label, condition):
    status = "PASS" if condition else "FAIL"
    results.append((status, label))
    print(f"  [{status}] {label}")


print("Serialisation schema")
tile = lib.get("MIF_MUX")
icm = walk.tile_to_icm("MIF_MUX", tile)
check("has program_id (composer raw-load trigger)", "program_id" in icm)
check("has records", "records" in icm and len(icm["records"]) == len(tile.records))
check("no composer_meta (loads as raw cell grid)", "composer_meta" not in icm)
check("format_version 2 (inB read, not 'retired')", icm.get("format_version") == 2)
check("security_context is null", icm["security_context"] is None)
check("inputs is {name:addr} dict", isinstance(icm["inputs"], dict)
      and all(isinstance(v, int) for v in icm["inputs"].values()))
check("outputs is {name:addr} dict", isinstance(icm["outputs"], dict))
r0 = icm["records"][0]
check("record has gs/in/out/inB/init keys",
      set(r0.keys()) == {"gs", "in", "out", "inB", "init"})
check("cell_count matches records", icm["cell_count"] == len(icm["records"]))
check("preload_map carried for mux-family tile", len(icm.get("preload_map", {})) > 0)

print("\nRecords round-trip the tile network")
check("record addresses match tile records",
      all(icm["records"][i]["out"] == tile.records[i].output_address
          for i in range(len(tile.records))))

print("\nJSON-serialisable + valid on disk")
s = json.dumps(icm)
check("icm is JSON-serialisable", isinstance(s, str) and len(s) > 0)
reloaded = json.loads(s)
check("survives JSON round-trip", reloaded["cell_count"] == icm["cell_count"])

print("\nTile selection rules")
names = list(walk.selectable_tiles(lib, include_handlers=False))
check("handlers skipped by default", not any(n.endswith("_HANDLER") for n in names))
check("deprecated INT32_ADD_CLA skipped", "INT32_ADD_CLA" not in names)
check("functional tiles present (MIF_MUX, INT32_ADD)",
      "MIF_MUX" in names and "INT32_ADD" in names)
with_handlers = list(walk.selectable_tiles(lib, include_handlers=True))
check("--all includes handlers", any(n.endswith("_HANDLER") for n in with_handlers))

print("\nCommitted sample palette exists")
sample_dir = os.path.join(REPO, "examples", "tiles", "samples")
for s in ("INT32_ADD", "INT32_MUX", "MIF_MUX", "MIF_CMP_LT"):
    p = os.path.join(sample_dir, f"{s}.icm")
    ok = os.path.exists(p)
    if ok:
        d = json.load(open(p))
        ok = "program_id" in d and "records" in d
    check(f"sample {s}.icm present and valid", ok)

print("\nrecord_hash matches composer canonR")
import hashlib
icm_h = walk.tile_to_icm("MIF_MUX", lib.get("MIF_MUX"))
check("icm carries a record_hash", bool(icm_h.get("record_hash")))
# independent recompute of the composer canonicalisation
canon = json.dumps([{"gs": r["gs"], "in": r["in"], "init": r["init"], "out": r["out"]}
                    for r in icm_h["records"]], separators=(",", ":"))
indep = hashlib.sha256(canon.encode("utf-8")).hexdigest()
check("record_hash == independent canonR(gs,in,init,out) sha256",
      icm_h["record_hash"] == indep)
check("canon string has no whitespace (matches JS JSON.stringify)",
      " " not in canon and ": " not in canon)
# committed samples must also carry a valid hash now
sp = json.load(open(os.path.join(sample_dir, "MIF_MUX.icm")))
sp_canon = json.dumps([{"gs": r["gs"], "in": r["in"], "init": r["init"], "out": r["out"]}
                       for r in sp["records"]], separators=(",", ":"))
check("committed sample MIF_MUX.icm has matching hash",
      sp.get("record_hash") == hashlib.sha256(sp_canon.encode()).hexdigest())

print("\n--module walks a whole user library file")
ex_mod = os.path.join(REPO, "examples", "walker", "example_user_models.py")
mod = walk._import_module(ex_mod)
builders = [getattr(mod, n) for n in dir(mod)
            if n.startswith("make_") and callable(getattr(mod, n))]
tiles = [fn() for fn in builders]
check("example library has >= 2 make_* builders", len(builders) >= 2)
check("all builders return Tiles", all(walk._is_tile(t) for t in tiles))
icm_um = walk.tile_to_icm("MY_XNOR", next(t for t in tiles
                          if getattr(t.metadata, "operation", "") == "MY_XNOR"))
check("user model serialises with a valid hash",
      icm_um.get("record_hash") ==
      hashlib.sha256(json.dumps(
          [{"gs": r["gs"], "in": r["in"], "init": r["init"], "out": r["out"]}
           for r in icm_um["records"]], separators=(",", ":")).encode()).hexdigest())
check("_import_module loads by .py path", walk._is_tile(mod.make_my_and3()))

# ---- Results ----------------------------------------------------------------
print(f"\n{'='*55}")
passed = sum(1 for s, _ in results if s == "PASS")
failed = sum(1 for s, _ in results if s == "FAIL")
print(f"Results: {passed} passed, {failed} failed out of {len(results)} tests")
if failed == 0:
    print("ALL TESTS PASSED")
else:
    print("\nFailed tests:")
    for st, n in results:
        if st == "FAIL":
            print(f"  {n}")
