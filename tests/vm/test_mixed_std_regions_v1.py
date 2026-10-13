"""tests/vm/test_mixed_std_regions_v1.py -- ledger #1162: STANDARD (standalone v4 shells) and CARRIER (trimmed VIXeN carrier) regions inside a mixed-family design. The Flex-Sub assembler cuts the design at the family
boundaries, builds each region with its own generator and puts the flex <-> std adapters (#1160) on every crossing. Chains (each block adds its own constant, 30 words, host at the first and last block):
flex-std-flex, flex-carrier-flex, flex-std-carrier-flex, flex-carrier-std-flex; random stalls on the sink; the unsupported combinations are refused with their reason. Needs iverilog (fails loudly without it)."""
import copy, json, os, shutil, subprocess, sys, tempfile
import pytest
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
for s_ in ("tools", "nano"):
    sys.path.insert(0, os.path.join(ROOT, s_))
import flexsub_mixed_v2 as mx  # noqa: E402

EX = os.path.join(ROOT, "nano", "examples", "mixed_flex_sub_flex_v1.icm-hier.json")
EX2 = os.path.join(ROOT, "nano", "examples", "mixed_flex_std_flex_v1.icm-hier.json")
TB = os.path.join(ROOT, "sub", "verilog", "tb_mixed_flex_sub_flex_v1.v")
ASM = [sys.executable, os.path.join(ROOT, "tools", "project_assemble_v1.py")]
K = [1000, 234, 5, 7]


def chain(fams):
    d = json.load(open(EX)); proto = d["design_map"]["placements"][0]
    d["design_map"]["placements"], d["design_map"]["connections"] = [], []
    for i, f in enumerate(fams):
        q = copy.deepcopy(proto); q["instance"] = "ABCD"[i]; q["at"] = [0, 3 * i]; q["family"] = f
        q["overrides"] = {"k": {"preload_value": K[i]}}
        if i == 0:
            q["overrides"]["in"] = {"io_name": "x_in"}
        if i == len(fams) - 1:
            q["overrides"]["out"] = {"io_name": "y_out"}
        d["design_map"]["placements"].append(q)
        if i:
            d["design_map"]["connections"].append({"from": ["ABCD"[i - 1], 0, 2, "E"], "to": ["ABCD"[i], 0, 0, "W"]})
    return d


def build(d):
    w = tempfile.mkdtemp(); p = os.path.join(w, "m.icm-hier.json"); json.dump(d, open(p, "w")); out = os.path.join(w, "out")
    r = subprocess.run(ASM + ["-s", "flex", "--icm", p, "--top", "mix", "--output", out], capture_output=True, text=True)
    return r, out


def sim(out, stall, n=30):
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is required (see current/START.md)"
    srcs = [os.path.join(out, f) for f in os.listdir(out) if f.endswith(".v")]
    exe = os.path.join(out, f"t{stall}.vvp")
    c = subprocess.run(["iverilog", "-g2012", "-DTOP=mix", f"-DN={n}", f"-DSTALL={stall}", "-o", exe, TB] + srcs, capture_output=True, text=True)
    assert c.returncode == 0, c.stderr[-600:]
    o = subprocess.run(["vvp", exe], capture_output=True, text=True, timeout=300).stdout
    return [int(l.split()[2]) for l in o.splitlines() if l.startswith("O ")], o


@pytest.mark.parametrize("fams", [("flex", "std", "flex"), ("flex", "carrier", "flex"), ("flex", "std", "carrier", "flex"), ("flex", "carrier", "std", "flex")])
def test_every_word_equals_x_plus_the_sum_in_order_through_the_assembler(fams):
    r, out = build(chain(fams))
    assert r.returncode == 0, r.stderr[-500:] + r.stdout[-300:]
    top = open(os.path.join(out, "mix.v")).read()
    assert top.count("flex_to_std_v1") + top.count("std_to_flex_v1") == 2 * sum(1 for f in fams if f in ("std", "carrier")) and "ext_ready" in open(os.path.join(out, "mix_" + [f for f in fams if f != "flex"][0] + "1.v")).read()
    add = sum(K[:len(fams)])
    for stall in (0, 1):
        vals, o = sim(out, stall)
        assert vals == [100 + 7 * k + add for k in range(30)] and "END" in o, (fams, stall, o[-200:])


def test_the_shipped_example_builds_and_the_unsupported_combinations_are_refused():
    r, out = build(json.load(open(EX2)))
    assert r.returncode == 0 and "std1(std)" in r.stdout
    for fams, why in ((("flex", "sub", "std", "flex"), "not built"), (("flex", "std", "sub", "flex"), "not built")):
        r, _ = build(chain(fams))
        assert r.returncode != 0 and why in r.stderr, (fams, r.stderr[-300:])
    d = chain(("flex", "std", "flex")); d["patterns"]["plus"]["cells"][3]["core"] = "mul"
    r, _ = build(d)
    assert r.returncode != 0 and "no cell for core" in r.stderr
    d = chain(("flex", "carrier", "flex", "carrier"))
    r, _ = build(d)
    assert r.returncode != 0 and "more than one carrier region" in r.stderr
    d = chain(("flex", "std", "flex")); d["design_map"]["placements"][1]["overrides"]["k"]["io_name"] = "host_k"
    r, _ = build(d)
    assert r.returncode != 0 and "host names" in r.stderr
