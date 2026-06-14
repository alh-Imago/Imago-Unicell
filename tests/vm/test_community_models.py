"""
test_community_models.py — BioTrix / ChemTrix / PhysTrix worked example models

Validates that all community model JSON files:
  - Are valid JSON
  - Have required fields (id, name, domain, format, description, pipeline, validation)
  - Pipeline references only valid_tiles for their format
  - Validation strings are non-empty and contain checkable numbers
  - MANIFESTs list exactly the models that exist on disk

Run: python3 tests/vm/test_community_models.py
"""

import sys, os, json, glob
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from cell_format import (
    FormatRegistry, DNA_4Base, RNA_4Base, Amino20,
    Chemistry_Element, SI_Physics
)

PASS, FAIL = 0, 0

def check(label, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {label}")
    else:
        FAIL += 1
        print(f"  [FAIL] {label}" + (f" — {detail}" if detail else ""))

REQUIRED_FIELDS = ["id", "name", "domain", "description", "pipeline", "validation", "version"]

DOMAIN_FORMATS = {
    "BioTrix":  [DNA_4Base(), RNA_4Base(), Amino20()],
    "ChemTrix": [Chemistry_Element()],
    "PhysTrix": [SI_Physics()],
}

def all_valid_tiles(domain):
    tiles = set()
    for fmt in DOMAIN_FORMATS.get(domain, []):
        tiles.update(fmt.valid_tiles)
    return tiles

COMMUNITY_ROOT = os.path.join(os.path.dirname(__file__), '..', '..', 'community')

DOMAINS = {
    "biotrix":  "BioTrix",
    "chemtrix": "ChemTrix",
    "phystrix": "PhysTrix",
}

def run():
    for folder, domain in DOMAINS.items():
        domain_path = os.path.join(COMMUNITY_ROOT, folder)
        models_path = os.path.join(domain_path, "models")
        manifest_path = os.path.join(domain_path, "MANIFEST.json")

        print(f"\n{'='*55}")
        print(f"Domain: {domain} ({folder}/)")
        print(f"{'='*55}")

        # --- MANIFEST ---
        print("\nMANIFEST checks:")
        check(f"{folder}/MANIFEST.json exists", os.path.exists(manifest_path))
        try:
            with open(manifest_path) as f:
                manifest = json.load(f)
            check("MANIFEST is valid JSON", True)
        except Exception as e:
            check("MANIFEST is valid JSON", False, str(e))
            manifest = {}

        manifest_models = manifest.get("models", [])
        check("MANIFEST lists at least one model", len(manifest_models) > 0,
              f"got {manifest_models}")

        # --- MODELS DIR ---
        print("\nModels directory checks:")
        check("models/ directory exists", os.path.isdir(models_path))

        disk_models = [
            os.path.splitext(os.path.basename(f))[0]
            for f in glob.glob(os.path.join(models_path, "*.json"))
        ]
        check("models/ contains files", len(disk_models) > 0,
              f"found: {disk_models}")
        check("MANIFEST model list matches disk files",
              sorted(manifest_models) == sorted(disk_models),
              f"manifest={sorted(manifest_models)} disk={sorted(disk_models)}")

        valid_tiles = all_valid_tiles(domain)

        # --- PER-MODEL ---
        for model_id in sorted(disk_models):
            model_file = os.path.join(models_path, f"{model_id}.json")
            print(f"\n  Model: {model_id}")

            try:
                with open(model_file) as f:
                    m = json.load(f)
                check(f"{model_id}: valid JSON", True)
            except Exception as e:
                check(f"{model_id}: valid JSON", False, str(e))
                continue

            # required fields
            for field in REQUIRED_FIELDS:
                check(f"{model_id}: has '{field}'",
                      field in m and bool(m[field]),
                      f"missing or empty")

            # id matches filename
            check(f"{model_id}: id matches filename", m.get("id") == model_id)

            # domain matches
            check(f"{model_id}: domain is {domain}", m.get("domain") == domain)

            # pipeline is a non-empty list
            pipeline = m.get("pipeline", [])
            check(f"{model_id}: pipeline is non-empty list",
                  isinstance(pipeline, list) and len(pipeline) > 0)

            # pipeline tile references are valid for this domain
            tile_refs = [
                step["tile"] for step in pipeline
                if isinstance(step, dict) and "tile" in step
            ]
            for tile in tile_refs:
                check(f"{model_id}: tile '{tile}' is valid for {domain}",
                      tile in valid_tiles,
                      f"valid tiles: {sorted(valid_tiles)[:5]}...")

            # validation string is meaningful (contains a number)
            val_str = m.get("validation", "")
            has_number = any(c.isdigit() for c in val_str)
            check(f"{model_id}: validation string contains numeric example",
                  has_number, f"got: {val_str[:60]!r}")

    print(f"\n{'='*55}")
    print(f"Results: {PASS} passed, {FAIL} failed out of {PASS+FAIL} tests")
    if FAIL == 0:
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS FAILED")
    return FAIL == 0

if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)
