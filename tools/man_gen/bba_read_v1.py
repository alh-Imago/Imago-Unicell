#!/usr/bin/env python3
"""bba_read_v1.py - read the FACTS a MAN file needs out of an openXC7 / nextpnr-xilinx chip database in its text form (.bba), 2 Nov 2026 (Alan uploaded xc7k480tffg1156.bba).

What it reads (the layout was worked out from the file itself, not from documentation, and checked as noted):
  * the string table (every `str |...|` line, in order); dynamic string ids start at an offset B, found from the package record whose name is 'ffg1156' (id - table index);
  * tile types (98, 10 lines each: name id, bels, wires, pips, groups), tile instances (136,359, 4 lines each: type in the second line), bels of each tile type (10 lines each: name id, type id, ...);
  * packages (name id, pads, pad count); a pad is 7 numbers: pin name, tile name, site.pad name.
It counts SITES per type as (distinct 'PREFIX_XnYm' bel-name prefixes in a tile type) x (tile instances of that type).  Names of tile types and bel TYPES that are small ids are compiled
into nextpnr-xilinx and are not in the file, so the counts rely on bel NAMES, which are in the file.
Checks that held for XC7K480T FFG1156: slices 74,650 (x 8 LUT sites = 597,200 = the figure nextpnr reported in the card-flow note), see tests/vm/test_man_ypcb_00338_1p1_v1.py.
Usage: python3 tools/man_gen/bba_read_v1.py FILE.bba OUT.json   (reads ~280 MB of text; takes a minute or two)."""
import collections, json, re, sys

SITE = re.compile(r"^([A-Z0-9_]+?)_X(\d+)Y(\d+)\.")


def read(path):
    strs = []
    with open(path) as fh:
        for line in fh:
            if line.startswith("str |"): strs.append(line[5:].rsplit("|", 1)[0])
    idx = {x: i for i, x in enumerate(strs)}
    with open(path) as fh:
        for line in fh:
            if line.startswith("label packages"): break
        pk = []
        for _ in range(4):
            r = [next(fh).split() for _ in range(4)]; pk.append((int(r[0][1]), int(r[2][1])))
    B = pk[0][0] - idx["ffg1156"]                                  # package 0 is ffg1156
    nm = lambda i: strs[i - B] if 0 <= i - B < len(strs) else None
    pkgs = [(nm(n), c) for n, c in pk]
    with open(path) as fh:
        for line in fh:
            if line.startswith("label tile_types"): break
        rows = [next(fh).split() for _ in range(98 * 10)]
        types = [(int(rows[i][1]), int(rows[i + 2][1])) for i in range(0, len(rows), 10)]
        for line in fh:
            if line.startswith("label tile_insts"): break
        cnt = collections.Counter()
        for _ in range(136359):
            next(fh); b = next(fh).split(); next(fh); next(fh); cnt[int(b[1])] += 1
    sites = collections.Counter(); luts = ffs = 0
    with open(path) as fh:
        for line in fh:
            if line.startswith("label tt") and line.rstrip().endswith("_bels"):
                t = int(line.split()[1][2:-5]); nb = types[t][1]
                if not nb: continue
                prefixes = set(); lut = ff = 0
                for _ in range(nb):
                    r = [next(fh).split() for _ in range(10)]; name = nm(int(r[0][1])) or ""
                    m = SITE.match(name)
                    if m:
                        prefixes.add(name.split(".")[0])
                        suf = name.split(".", 1)[1]
                        if suf.endswith("LUT") and name.startswith("SLICE"): lut += 1
                        if suf.endswith("FF") and name.startswith("SLICE"): ff += 1
                for p in prefixes: sites[SITE.match(p + ".").group(1)] += cnt[t]
                luts += lut * cnt[t]; ffs += ff * cnt[t]
    # packages: the pads of package 0
    with open(path) as fh:
        for line in fh:
            if line.startswith("label pkg0_pads"): break
        pads = []
        for _ in range(pkgs[0][1]):
            r = [int(next(fh).split()[1]) for _ in range(7)]; pads.append((nm(r[0]), nm(r[1]), nm(r[2])))
    return dict(string_id_offset=B, packages=[dict(name=n, pads=c) for n, c in pkgs], tile_types=len(types), tile_instances=sum(cnt.values()),
                grid=None, sites=dict(sorted(sites.items())), slice_lut_sites=luts, slice_ff_sites=ffs,
                pads=[dict(pin=a, tile=b, site=c) for a, b, c in pads])


if __name__ == "__main__":
    out = read(sys.argv[1]); json.dump(out, open(sys.argv[2], "w"), indent=1)
    print({k: v for k, v in out.items() if k != "pads"})
