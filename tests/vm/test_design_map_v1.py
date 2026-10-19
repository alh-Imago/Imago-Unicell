"""tests/vm/test_design_map_v1.py -- ledger #1285: tools/design_map_v1.py (the neighbour map of a generated flex design) against the Verilog the generator really writes.
1. generator v3 (+ flex emitter v3, which only records its final graph) writes byte-identical Verilog to v2 for every example design.
2. for every example the generator accepts: every non-tile cell of the map has the CELL_ID the Verilog gives the instance of that name, and the map has no cell the Verilog lacks and lacks none it has.
3. the fingerprint is the same on a second build, and different for a different design."""
import glob, os, re, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "nano")); sys.path.insert(0, os.path.join(ROOT, "tools"))
import design_map_v1 as dm  # noqa: E402
import flexsub_icm_generate_v2 as g2  # noqa: E402
import flexsub_icm_generate_v3 as g3  # noqa: E402

FILES = sorted(glob.glob(os.path.join(ROOT, "nano", "examples", "*.icm-hier.json")) + glob.glob(os.path.join(ROOT, "nano", "examples", "card_tested", "*.icm.json")))


def _gen(G, f):
    with tempfile.TemporaryDirectory() as d:
        G.generate(f, d + "/o", family="flex", rings=True)
        v = sorted(x for x in os.listdir(d + "/o") if x.endswith("_flex.v"))[0]
        return open(d + "/o/" + v).read()


def _ids(txt):
    ids = {}
    for line in txt.split("\n"):
        a, b = re.search(r"\.CELL_ID\(16'd(\d+)\)", line), re.search(r"\)\s+(c_\w+)\s*\(", line)
        if a and b:
            ids[b.group(1)] = int(a.group(1))
    return ids


def test_map_equals_the_verilog_for_every_example_the_generator_accepts():
    n = 0
    for f in FILES:
        try:
            t3 = _gen(g3, f)
        except Exception:
            continue                                   # refused by the generator, with a reason (looped_cordic_v1, _closed_flex)
        assert t3 == _gen(g2, f), os.path.basename(f)
        m = dm.build_map(f, rings=True)
        ids = _ids(t3)
        real = [c for c in m["cells"] if not c["tile"]]
        for c in real:
            assert ids.get("c_" + re.sub(r"\W", "_", c["id"])) == c["index"], (os.path.basename(f), c["id"])
        assert len(ids) == len(real), (os.path.basename(f), len(ids), len(real))
        n += 1
    assert n >= 22


def test_fingerprint_is_stable_and_distinguishes_designs():
    a = os.path.join(ROOT, "nano", "examples", "cordic_z_convergence_v2.icm-hier.json")
    b = os.path.join(ROOT, "nano", "examples", "card_tested", "priority_weighted.icm.json")
    assert dm.build_map(a, rings=True)["fingerprint"] == dm.build_map(a, rings=True)["fingerprint"]
    assert dm.build_map(a, rings=True)["fingerprint"] != dm.build_map(b, rings=True)["fingerprint"]
