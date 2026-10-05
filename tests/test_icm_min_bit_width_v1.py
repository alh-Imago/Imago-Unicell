#!/usr/bin/env python3
"""tests/test_icm_min_bit_width_v1.py -- the ICM `min_bit_width` header flag in the three formats' load and save functions (ledger #958).

Run: python3 tests/test_icm_min_bit_width_v1.py
Alan: the width minimum goes in the HEADER (it must be part of the transferable artifact); when it is absent the width stays 32; the load and save functions are the points to
target, so the ICM stays open and cross-targetable. Checked: the field is validated; it round-trips through icm-v3, icm-v4 and icm-vix; an ABSENT flag changes NOTHING (the
hashes below were captured from the ORIGINAL code, so they pin "no existing file ever changes"); the VIX header's other fields stay DERIVED; the flag is covered by the
integrity hash; and the generators accept a declared minimum up to 32, refuse above it, and record what was declared.
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for sub in ("nano", "tools", ""):
    sys.path.insert(0, os.path.join(ROOT, sub) if sub else ROOT)
import icm_v3  # noqa: E402
import icm_v4  # noqa: E402
import icm_vix_v1 as vix  # noqa: E402
import icm_width_v1 as w  # noqa: E402

CLI = [sys.executable, os.path.join(ROOT, "tools", "project_assemble_v1.py")]
COMPILE = [sys.executable, os.path.join(ROOT, "tools", "flexsub_compile_v1.py")]
EX = os.path.join(ROOT, "nano", "examples")
passed = failed = 0

# captured from the ORIGINAL (pre-#958) code: a file WITHOUT the flag must hash, and describe itself, exactly as it always did
GOLD_VIX = {"cordic_z_convergence": ("d1937eb3da1f0b6209830a2a3c8bec04667d4646980c6f364787641444a03d40", {"cell_count": 40, "cores_used": ["adder", "branch", "ram"]}),
            "parallel_reduction_tree": ("8ed3b440893c95b67f38d0fb09f9704a859912b0f2e3818280e884e91ce8f8a2", {"cell_count": 12, "cores_used": ["adder", "ram"]}),
            "small_relay_chain": ("b1160c706dec8a0bccbde806473c5bcf84f54b09d0d679902d4d247f6f2ca53e", {"cell_count": 8, "cores_used": ["ram"]})}
GOLD_V3_3 = "337ee05451fc5de28f4c37867e78efafcb520d41eeb4ecef8e3b446eaab49201"
GOLD_V4_3 = "1ab339452325beb5a0e704ab577649299d7400c7a51e048d81431de70f8ce921"


def check(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}  {detail}")


def rec(i, core="ram"):
    return icm_v3.IcmV3Record(cell_id=f"c{i}", row=1, col=i, core=core, core_config={"upstream_mask": ["w"] if i else [], "downstream_mask": ["e"]})


def raises(fn, exc=Exception):
    try:
        fn()
    except exc as e:
        return str(e)
    return None


tmp = tempfile.mkdtemp(prefix="minbw_")
print("the flag itself: validated, and absent means 32")
good = [1, 8, 18, 32, 36, 64]
check(f"valid widths {good} are accepted", all(w.validate_min_bit_width(x) == x for x in good))
bad = [0, -1, 65, 100, True, False, 18.5, "18", [], {}]
check(f"invalid values are refused with an IcmWidthError: {bad}", all(raises(lambda x=x: w.validate_min_bit_width(x), w.IcmWidthError) for x in bad))
check("None (absent) is valid, and means 32", w.validate_min_bit_width(None) is None and w.effective_min_bit_width(None) == 32 and w.effective_min_bit_width(18) == 18)
check("the hash suffix is EMPTY when absent (so no existing hash can change) and fixed when set", w.hash_suffix(None) == "" and w.hash_suffix(18) == "|min_bit_width=18")
check("each file class validates the flag on construction (v3, v4, vix all refuse a bad width)",
      raises(lambda: icm_v3.IcmV3File(name="x", records=[], min_bit_width=0), w.IcmWidthError) is not None
      and raises(lambda: icm_v4.IcmV4File(name="x", min_bit_width=99), w.IcmWidthError) is not None
      and raises(lambda: vix.IcmVixFile(min_bit_width="eighteen"), w.IcmWidthError) is not None)

print("an ABSENT flag changes NOTHING: golden hashes and headers captured from the original code")
for nm, (gold_hash, gold_header) in GOLD_VIX.items():
    x = vix.IcmVixFile.load(os.path.join(EX, nm + ".icm-hier.json"))
    check(f"icm-vix {nm}: record_hash and derived header identical to the original code's; no min_bit_width key anywhere",
          x.record_hash() == gold_hash and x.header() == gold_header and "min_bit_width" not in json.dumps(x.to_dict()), f"{x.record_hash()} {x.header()}")
f3 = icm_v3.IcmV3File(name="t3", records=[rec(i) for i in range(3)], description="d")
f4 = icm_v4.IcmV4File(name="t3", super_records=[rec(i) for i in range(3)])
check("icm-v3 (3 cells): hash identical to the original code's; no flag key in the dict", f3.record_hash() == GOLD_V3_3 and "min_bit_width" not in f3.to_dict())
check("icm-v4 (3 cells): hash identical to the original code's; no flag key in the dict", f4.record_hash() == GOLD_V4_3 and "min_bit_width" not in f4.to_dict())

print("round trip: the flag travels with the artifact through every format's save and load")
for label, make, load in (("icm-v3", lambda: icm_v3.IcmV3File(name="t", records=[rec(i) for i in range(3)], min_bit_width=18), icm_v3.IcmV3File.load),
                          ("icm-v4", lambda: icm_v4.IcmV4File(name="t", super_records=[rec(i) for i in range(3)], min_bit_width=18), icm_v4.IcmV4File.load),
                          ("icm-vix", lambda: (lambda x: (setattr(x, "min_bit_width", 18), x)[1])(vix.IcmVixFile.load(os.path.join(EX, "small_relay_chain.icm-hier.json"))), vix.IcmVixFile.load)):
    f = make()
    path = os.path.join(tmp, label + ".json")
    f.save(path)
    g = load(path)
    d = json.load(open(path))
    where = d["header"].get("min_bit_width") if label == "icm-vix" else d.get("min_bit_width")
    check(f"{label}: saved in the {'header' if label == 'icm-vix' else 'top-level metadata'} as 18, reloaded as 18, same hash", where == 18 and g.min_bit_width == 18 and g.record_hash() == f.record_hash(), str(where))
    unflagged = load(path)
    unflagged.min_bit_width = None
    check(f"{label}: the flag is COVERED by the integrity hash (the same content without the flag hashes DIFFERENTLY)", unflagged.record_hash() != f.record_hash() and f.record_hash() == g.record_hash())
    d2 = json.loads(json.dumps(d))
    if label == "icm-vix":
        d2["header"]["min_bit_width"] = 36
    else:
        d2["min_bit_width"] = 36
    json.dump(d2, open(path + ".edited", "w"))
    check(f"{label}: hand-editing the declared width (18 -> 36) is CAUGHT on load", raises(lambda: load(path + ".edited"), ValueError) is not None and "hash mismatch" in (raises(lambda: load(path + ".edited"), ValueError) or ""))
    d3 = json.loads(json.dumps(d))
    if label == "icm-vix":
        d3["header"].pop("min_bit_width")
    else:
        d3.pop("min_bit_width")
    json.dump(d3, open(path + ".stripped", "w"))
    check(f"{label}: DELETING the flag from a flagged file is also caught", "hash mismatch" in (raises(lambda: load(path + ".stripped"), ValueError) or ""))
    d4 = json.loads(json.dumps(d))
    if label == "icm-vix":
        d4["header"]["min_bit_width"] = 0
    else:
        d4["min_bit_width"] = 0
    json.dump(d4, open(path + ".bad", "w"))
    check(f"{label}: an invalid width in the file (0) is refused on load", raises(lambda: load(path + ".bad"), w.IcmWidthError) is not None)

print("the VIX header: other fields stay DERIVED; the flag is the one STORED field")
x = vix.IcmVixFile.load(os.path.join(EX, "cordic_z_convergence.icm-hier.json"))
x.min_bit_width = 36
h = x.header()
check("header() recomputes cores_used and cell_count from the data and adds min_bit_width", h == {"cell_count": 40, "cores_used": ["adder", "branch", "ram"], "min_bit_width": 36}, str(h))
path = os.path.join(tmp, "stale.json")
x.save(path)
d = json.load(open(path))
d["header"]["cores_used"] = ["bogus"]
d["header"]["cell_count"] = 999
json.dump(d, open(path, "w"))
y = vix.IcmVixFile.load(path)
check("a stale or hand-edited derived header (cores_used, cell_count) is IGNORED and recomputed; the declared width survives", y.header() == h and y.min_bit_width == 36, str(y.header()))
recs_flag, _ = y.flatten()
recs_plain, _ = vix.IcmVixFile.load(os.path.join(EX, "cordic_z_convergence.icm-hier.json")).flatten()
check("flatten() is unaffected by the flag (the same 40 records)", [(r.cell_id, r.row, r.col, r.core) for r in recs_flag] == [(r.cell_id, r.row, r.col, r.core) for r in recs_plain])

print("the generators: a declared minimum up to 32 is MET (building wider satisfies it), above 32 is REFUSED, and what was declared is recorded")
src = os.path.join(tmp, "p.ll")
open(src, "w").write("define i32 @f(i32 %x, i32 %y) {\nentry:\n  %r = add i32 %x, %y\n  ret i32 %r\n}\n")
for width, expect_ok in ((None, True), (18, True), (32, True), (36, False)):
    icm = os.path.join(tmp, f"w{width}.icm")
    r = subprocess.run(COMPILE + [src, "-o", icm] + (["--min-bit-width", str(width)] if width else []), capture_output=True, text=True)
    check(f"compile tool: {'--min-bit-width ' + str(width) if width else 'no flag'} -> the saved file {'carries ' + str(width) if width else 'has no flag key'}",
          r.returncode == 0 and json.load(open(icm)).get("min_bit_width") == width, r.stderr.strip()[:160])
    for fam in ("sub", "flex"):
        out = os.path.join(tmp, f"g_{fam}_{width}")
        r = subprocess.run(CLI + ["-s", fam, "--icm", icm, "--output", out], capture_output=True, text=True)
        if expect_ok:
            rec_ = json.load(open(os.path.join(out, "ASSEMBLY.json"))) if r.returncode == 0 else {}
            check(f"  {fam}: declared {width} -> generates; record says min_bit_width={width}, built_width=32", r.returncode == 0 and rec_.get("min_bit_width") == width and rec_.get("built_width") == 32, r.stderr.strip()[:200])
        else:
            check(f"  {fam}: declared {width} -> REFUSED, naming the declared width and why", r.returncode != 0 and "min_bit_width = 36" in r.stderr and "32-bit" in r.stderr, r.stderr.strip()[:200])
r = subprocess.run(COMPILE + [src, "-o", os.path.join(tmp, "bad.icm"), "--min-bit-width", "99"], capture_output=True, text=True)
check("the compile tool refuses an invalid width cleanly (a message, rc 2, no traceback)", r.returncode == 2 and "between 1 and 64" in r.stderr and "Traceback" not in r.stderr, r.stderr.strip()[:200])
vx = vix.IcmVixFile.load(os.path.join(EX, "small_relay_chain.icm-hier.json"))
for width, expect_ok in ((18, True), (36, False)):
    vx.min_bit_width = width
    p_ = os.path.join(tmp, f"vix{width}.json")
    vx.save(p_)
    r = subprocess.run(CLI + ["-s", "flex", "--icm", p_, "--output", os.path.join(tmp, f"gv{width}")], capture_output=True, text=True)
    check(f"an ICM-VIX file with header min_bit_width={width}: {'generates' if expect_ok else 'REFUSED'} on flex", (r.returncode == 0) == expect_ok and (expect_ok or "min_bit_width = 36" in r.stderr), r.stderr.strip()[:200])

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
