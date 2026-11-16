#!/usr/bin/env python3
"""mkpreplaced.py - turn a finished build's placement into a file for  nextpnr  -o preplaced=FILE  (pins those cells to the same places in a later build).

Why: the placer's layout decides whether the DDR3 lanes meet timing.  When one build tests clean on the card, this keeps its layout (all of it, or only the DDR3 part).
Format read by nextpnr (himbaechel xilinx, xilinx.cc apply_preplaced): one line per cell, "<cell name><TAB><bel name>", bel name as <tile>/<bel>.
Input: the JSON that nextpnr writes with  --write placed.json  after place and route (each placed cell carries the attribute NEXTPNR_BEL).
Usage:  python3 mkpreplaced.py placed.json preplaced.txt                  (all cells)
        python3 mkpreplaced.py placed.json preplaced.txt --only REGEX     (only cells whose name matches, e.g. the DDR3 part)
        python3 mkpreplaced.py placed.json --list                         (show the first name parts, to choose REGEX)
Then rebuild with  PNR_ARGS="--freq 50 --seed N -o preplaced=$PWD/preplaced.txt".   GPL-3.0 folder because it serves that build; the script itself is original (MIT text of the repo applies to it)."""
import json, re, sys, collections


def cells_of(path):
    d = json.load(open(path))
    mods = d.get('modules', {})
    top = next((m for m in mods.values() if m.get('attributes', {}).get('top') not in (None, 0, '0', '')), None) or next(iter(mods.values()))
    return top.get('cells', {})


def bel_of(c):
    v = c.get('attributes', {}).get('NEXTPNR_BEL')
    return v.strip() if isinstance(v, str) and v.strip() else None


def main(a):
    if len(a) < 2: print(__doc__); return 2
    cells = cells_of(a[0])
    placed = {n: bel_of(c) for n, c in cells.items() if bel_of(c)}
    print('%d cells in the file, %d of them carry a placed bel' % (len(cells), len(placed)))
    if a[1] == '--list':
        h = collections.Counter(re.split(r'[./$]', n.lstrip('\\'))[0] or n for n in placed)
        for k, v in h.most_common(30): print('%6d  %s' % (v, k))
        return 0
    only = re.compile(a[a.index('--only') + 1]) if '--only' in a else None
    out = [(n, b) for n, b in sorted(placed.items()) if only is None or only.search(n)]
    with open(a[1], 'w') as f:
        for n, b in out: f.write('%s\t%s\n' % (n, b))
    print('wrote %d lines to %s' % (len(out), a[1]))
    for n, b in out[:5]: print('   ', n, '->', b)
    return 0 if out else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
