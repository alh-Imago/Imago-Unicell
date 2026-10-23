"""Does an ODD number of look windows improve the WRITE RULES (hexn_mem_write_v3.py, Python model of the host policy on the memory block)? With an even number of looks a wire can split evenly, and the block turns a tie into 0, which biases the stored pattern. Runs the write-rule policies with 4, 5 and 7 acquisition looks (and, for the merge rule, WOLD = the number of watches of the old slot when blending, 1, 2 or 3, so that total looks = acq + WOLD is odd or even). Mean of SEEDS seeds. Usage: python3 tools/hexn_mem_write_odd_v1.py [SEEDS]"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_mem_write_v3 as W
seeds = range(1, (int(sys.argv[1]) if len(sys.argv) > 1 else 5) + 1)
rows = []
for acq in (4, 5, 7):
    for name, md, kill, wolds in (("v1 (no merge)", 0, False, (None,)), ("merge md2 retire", 2, True, (1, 2, 3)), ("merge md3 retire", 3, True, (1, 2, 3)), ("merge md5 retire", 5, True, (2,))):
        for wold in wolds:
            if wold is not None: W.WOLD = wold
            pol = (16, acq, "weak", 10, md, kill); acc = {k: 0 for k in W.KEYS}; bad = 0
            for sd in seeds:
                r = W.run(W.RefLink(), pol, sd)
                for k in W.KEYS: acc[k] += r[k] / len(seeds)
                bad += r["bad"]
            rows.append(("looks %d%s  %s" % (acq, "" if wold is None else " WOLD %d" % wold, name), acc))
W.show(rows)
