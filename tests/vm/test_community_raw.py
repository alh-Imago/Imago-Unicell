"""
test_community_raw.py — non-Trix (raw-model) community contribution support

Validates that community_tools.py can scaffold, hash, and validate model
contributions OUTSIDE the Trix system (raw .icm / tile libraries, no
format.py), while staying backward-compatible with existing trix-domain
contributions. The community validator verifies the SAME record_hash the
walker writes — closing the loop between generation and submission.

Run with: python3 test_community_raw.py
"""

import os, sys, json, shutil, importlib.util, hashlib
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)

ct_path = os.path.join(REPO, "community", "community_tools.py")
spec = importlib.util.spec_from_file_location("community_tools", ct_path)
ct = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ct)

# walker, for generating a real hashed .icm to submit
wspec = importlib.util.spec_from_file_location(
    "walk_tiles", os.path.join(REPO, "examples", "walker", "walk_tiles.py"))
walk = importlib.util.module_from_spec(wspec)
wspec.loader.exec_module(walk)
from fp_tiles import TileLibrary
from pathlib import Path

results = []
def check(label, condition):
    status = "PASS" if condition else "FAIL"
    results.append((status, label))
    print(f"  [{status}] {label}")


print("Kind constants and per-kind requirements")
check("two kinds defined", set(ct.VALID_KINDS) == {"trix-domain", "raw-model"})
check("raw-model does NOT require format.py",
      "format.py" not in ct.REQUIRED_FILES_BY_KIND[ct.KIND_RAW])
check("trix-domain DOES require format.py",
      "format.py" in ct.REQUIRED_FILES_BY_KIND[ct.KIND_TRIX])
check("raw-model manifest does NOT require domain/formats/bridges",
      "domain" not in ct.REQUIRED_MANIFEST_BY_KIND[ct.KIND_RAW]
      and "bridges" not in ct.REQUIRED_MANIFEST_BY_KIND[ct.KIND_RAW])
check("kind is optional in common fields (back-compat)",
      "kind" not in ct.REQUIRED_MANIFEST_COMMON)

print("\n.icm validator (reuses walker canonR hash)")
# Generate a real hashed .icm and validate it
tmp = Path(REPO) / "community" / "_test_raw_tmp"
if tmp.exists():
    shutil.rmtree(tmp)
(tmp / "models").mkdir(parents=True)
lib = TileLibrary()
icm = walk.tile_to_icm("MIF_MUX", lib.get("MIF_MUX"))
with open(tmp / "models" / "MIF_MUX.icm", "w") as f:
    json.dump(icm, f, indent=2)
ok, errs = ct.validate_icm(tmp / "models" / "MIF_MUX.icm")
check("walker .icm passes the community .icm validator", ok)
check("community canonR == walker canonR (same hash basis)",
      ct._canon_records(icm["records"]) ==
      json.dumps([{"gs": r["gs"], "in": r["in"], "init": r["init"], "out": r["out"]}
                  for r in icm["records"]], separators=(",", ":")))

# Tamper a record -> hash must fail
bad = json.loads(json.dumps(icm))
bad["records"][0]["gs"] ^= 0x1
with open(tmp / "models" / "BAD.icm", "w") as f:
    json.dump(bad, f)
ok_bad, errs_bad = ct.validate_icm(tmp / "models" / "BAD.icm")
check("tampered .icm fails hash verification", not ok_bad)

# Missing hash -> flagged
nohash = json.loads(json.dumps(icm)); nohash.pop("record_hash", None)
with open(tmp / "models" / "NOHASH.icm", "w") as f:
    json.dump(nohash, f)
ok_nh, errs_nh = ct.validate_icm(tmp / "models" / "NOHASH.icm")
check("missing record_hash is flagged (strict loader would refuse)", not ok_nh)
shutil.rmtree(tmp)

print("\nEnd-to-end: scaffold -> populate -> hash -> validate")
folder = Path(REPO) / "community" / "_test_raw_e2e"
if folder.exists():
    shutil.rmtree(folder)
ct.cmd_new("_test_raw_e2e", kind=ct.KIND_RAW)
check("raw scaffold creates folder + models/, NO format.py",
      folder.exists() and (folder / "models").exists()
      and not (folder / "format.py").exists())
man = json.load(open(folder / "MANIFEST.json"))
check("scaffolded manifest declares kind=raw-model", man.get("kind") == "raw-model")
# populate with a real hashed .icm
with open(folder / "models" / "MIF_MUX.icm", "w") as f:
    json.dump(walk.tile_to_icm("MIF_MUX", lib.get("MIF_MUX")), f, indent=2)
ct.cmd_hash(folder)
valid = ct.cmd_validate(folder)
check("populated raw contribution validates VALID", valid)
shutil.rmtree(folder)

print("\nBack-compat: trix scaffold still works and declares its kind")
tfolder = Path(REPO) / "community" / "_test_trix_tmp"
if tfolder.exists():
    shutil.rmtree(tfolder)
ct.cmd_new("_test_trix_tmp", kind=ct.KIND_TRIX)
tman = json.load(open(tfolder / "MANIFEST.json"))
check("trix scaffold writes format.py", (tfolder / "format.py").exists())
check("trix manifest declares kind=trix-domain", tman.get("kind") == "trix-domain")
shutil.rmtree(tfolder)

# ---- Results ----------------------------------------------------------------
print(f"\n{'='*55}")
passed = sum(1 for s, _ in results if s == "PASS")
failed = sum(1 for s, _ in results if s == "FAIL")
print(f"Results: {passed} passed, {failed} failed out of {len(results)} tests")
if failed == 0:
    print("ALL TESTS PASSED")
else:
    print("\nFailed tests:")
    for s, n in results:
        if s == "FAIL":
            print(f"  {n}")
