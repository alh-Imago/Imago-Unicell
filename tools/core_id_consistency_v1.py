#!/usr/bin/env python3
"""tools/core_id_consistency_v1.py -- ledger #1337: check that every place that names a core by NUMBER agrees with the RTL it belongs to, and that the ICM files agree with both.

The project has TWO lineages of core_select numbers (both fixed, neither is changed here):
  * the original SUPER shell (fpga/verilog/unicell_super/unicell_super_v9.v, Arria 10 line): nano 0, ram 1, adder 2, accumulator 3, comparator 4, latch 5, sequencer 6, branch 7, ...
    ICM v3 (nano/icm_v3.py CORE_IDS) and the composer's core_select bar (tools/flex_layout_view_v1.py) follow it.
  * the VIX carrier (fpga/verilog/unicell_vixen_v1.v, unicell_vix_carrier_v1d.v): nano 0, adder 1, ram 2, compare 3, branch 4, accum 5, latch 6, seq 7, command 8, mul 9, ...
    the carrier grid generator (tools/carrier_grid_v3.py SEL, by core NAME) and the VM's carrier model (nano/vix_carrier_automaton_v1.py) follow it.
ICM files name the core (`core`: "adder"); an ICM v3 file also carries `super_latch_hex`, whose low 5 bits are the SUPER-shell number. Nothing reads that hex back (ledger #1337).
Checks (each must hold within a lineage; the difference BETWEEN lineages is expected and printed):
  1 ICM v3 CORE_IDS == the super shell RTL's localparams (for the cores the RTL has)   2 composer core_select == ICM v3
  3 carrier grid SEL == VIXeN RTL   4 VM carrier model order == VIXeN RTL   5 v1d RTL == VIXeN RTL for the cores both have
  6 every ICM file's core names are known; every ICM v3 `super_latch_hex` low 5 bits == CORE_IDS[core]
Usage: python3 tools/core_id_consistency_v1.py [--quiet]     exit 1 on any failure."""
import glob, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (os.path.join(ROOT, "tools"), os.path.join(ROOT, "nano"), os.path.join(ROOT, "nano", "examples")):
    if p not in sys.path:
        sys.path.insert(0, p)

CANON = {"NANO": "nano", "RAM": "ram", "ADDER": "adder", "ACC": "accumulator", "ACCUM": "accumulator", "CMP": "comparator", "COMPARE": "comparator", "LATCH": "latch", "SEQ": "sequencer",
         "BRANCH": "branch", "COMMAND": "command", "MUL": "mul", "PRIORITY": "priority", "CROSS": "cross", "CORNER": "corner", "MERGE": "merge", "DIV": "div"}


def rtl_ids(path):
    """{canonical core name: number} from the `SEL_X = 5'dN` localparams of an RTL file (SEL_ADDON_CONFIG is not a core and is skipped)"""
    t = open(os.path.join(ROOT, path)).read()
    t = re.sub(r"//[^\n]*", "", t)
    out = {}
    for m in re.finditer(r"\bSEL_([A-Z_]+)\s*=\s*5'd(\d+)", t):
        if m.group(1) in CANON:
            out[CANON[m.group(1)]] = int(m.group(2))
    return out


def icm_files():
    out = []
    for f in sorted(glob.glob(os.path.join(ROOT, "**", "*"), recursive=True)):
        rel = os.path.relpath(f, ROOT)
        if rel.startswith(("dist/", "archeology/", "tools/onion", ".git/")) or not os.path.isfile(f):
            continue
        if f.endswith((".icm", ".icm.json", ".icm-hier.json")):
            out.append(f)
    return out


def main():
    quiet = "--quiet" in sys.argv
    import icm_v3, carrier_grid_v3 as G, vix_carrier_automaton_v1 as VM, flex_layout_view_v1 as flv
    fails = []

    def eq(label, a, b, keys=None):
        for k in sorted(set(a) & set(b) if keys is None else keys):
            if a.get(k) != b.get(k):
                fails.append("%s: %s is %s on one side and %s on the other" % (label, k, a.get(k), b.get(k)))
    super_rtl = rtl_ids("fpga/verilog/unicell_super/unicell_super_v9.v")
    vixen = rtl_ids("fpga/verilog/unicell_vixen_v1.v")
    v1d = rtl_ids("fpga/verilog/unicell_vix_carrier_v1d.v")
    v3ids = dict(icm_v3.CORE_IDS)
    eq("1 ICM v3 vs super shell RTL", v3ids, super_rtl)
    eq("2 composer bar vs ICM v3", {c: m["sel"] for c, m in flv.core_meta()["cores"].items()}, v3ids)
    gen = {("accumulator" if k == "accum" else k): v for k, v in G._v2.SEL.items()}
    eq("3 carrier grid generator vs VIXeN RTL", gen, vixen, keys=sorted(gen))
    eq("4 VM carrier model vs VIXeN RTL", {n: i for i, n in VM._SEL_FROM_INDEX.items()}, vixen, keys=sorted(VM._INDEX_FROM_SEL))
    eq("5 v1d carrier RTL vs VIXeN RTL", v1d, vixen)
    n_files = n_cells = n_hex = 0
    for f in icm_files():
        rel = os.path.relpath(f, ROOT)
        try:
            d = json.load(open(f))
        except (ValueError, OSError):
            continue
        cores = []
        if isinstance(d, dict) and d.get("format_version") == "icm-v3":
            for r in d.get("records", []):
                cores.append(r.get("core"))
                h = r.get("super_latch_hex")
                if h is not None and r.get("core") in v3ids:
                    n_hex += 1
                    if (int(h, 16) & 31) != v3ids[r["core"]]:
                        fails.append("6 %s: cell %s core %s but super_latch_hex %s has select %d (expected %d)" % (rel, r.get("cell_id"), r.get("core"), h, int(h, 16) & 31, v3ids[r["core"]]))
        elif isinstance(d, dict) and d.get("format_version") == "icm-vix-v1":
            import icm_vix_v1 as vix
            try:
                cores = [r.core for r in vix.IcmVixFile.load(f).flatten()[0]]
            except Exception as e:                  # a file the loader itself refuses is reported, not guessed at
                fails.append("6 %s: cannot be read by the ICM-VIX loader (%s)" % (rel, str(e)[:80]))
        else:
            continue
        n_files += 1
        n_cells += len(cores)
        for c in sorted({c for c in cores if c not in v3ids and c not in vixen and c != "ram"}):
            fails.append("6 %s: unknown core name %r" % (rel, c))
    if not quiet:
        names = sorted(set(v3ids) | set(vixen), key=lambda c: (v3ids.get(c, 99), c))
        print("core            ICM v3 / super shell    VIX carrier (VIXeN)")
        for c in names:
            a, b = v3ids.get(c), vixen.get(c)
            print("%-15s %-23s %-6s %s" % (c, "-" if a is None else a, "-" if b is None else b, "" if a == b else "(differ: expected, two lineages)"))
        print("\n%d ICM files read, %d cells; %d ICM v3 super_latch_hex words checked" % (n_files, n_cells, n_hex))
    for x in fails:
        print("FAIL", x)
    print("RESULT:", "all consistent within each lineage" if not fails else "%d FAILURE(S)" % len(fails))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
