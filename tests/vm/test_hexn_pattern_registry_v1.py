"""tests/vm/test_hexn_pattern_registry_v1.py -- the pattern registry (docs/hex-n/data/patterns/registry.json), 3 Nov 2026. Every reference file that is NOT listed as superseded has a unique pattern id, matches the registry's type / version / hash for its name,
and has a verification record for the same id and hash. (J0U2_7_17000001 is the superseded first issue of J0U2_7: it collided with J0U9_7 on 17000001, see the ledger row 3 Nov 14:15.)"""
import glob, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_pattern_ref_v7 as R, hexn_pattern_verify_v10 as V

D = os.path.join(ROOT, "docs/hex-n/data")
SUPERSEDED = {"J0U2_7_17000001"}


def _files():
    return {os.path.basename(f)[:-5]: json.load(open(f)) for f in glob.glob(D + "/patterns/*_*.json") if os.path.basename(f) != "registry.json"}


def test_ids_are_unique_among_current_files():
    cur = {n: f for n, f in _files().items() if n not in SUPERSEDED}
    ids = [f["pattern_id"] for f in cur.values()]
    assert len(ids) == len(set(ids)) and len(ids) >= 5, ids


def test_registry_matches_the_files_and_every_file_is_verified():
    reg = json.load(open(D + "/patterns/registry.json"))
    for n, f in _files().items():
        if n in SUPERSEDED: continue
        e = reg[f["name"]]
        assert (e["type"], e["version"], e["hash"]) == (f["pattern_id"] >> 16, f["pattern_id"] & 0xFFFF, f["content_hash"]), n
        assert not R.check_reference(f), n
        rec = json.load(open(D + "/pnr/%s.pnr.json" % n))
        assert V.verified(f, rec), n


def test_the_superseded_file_has_the_same_content_as_its_replacement():
    old = _files()["J0U2_7_17000001"]; new = _files()["J0U2_7_17010001"]
    assert old["content_hash"] == new["content_hash"] and old["pattern_id"] != new["pattern_id"]
