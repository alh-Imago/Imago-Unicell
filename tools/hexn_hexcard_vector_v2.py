#!/usr/bin/env python3
"""Make the board self-test vector for a Kintex array card (frame v4, byte port; clone of hexn_hexcard_vector_v1, 4 Nov 2026).
Runs the array core in iverilog through its BYTE PORT (hexn_bytecard_sim_v1; sources from `hexn_kxarr_v1.py sim`), checks the words against the hex VM, and writes a JSON
that tools/hexn_hexcard_host_v1.py replays on a real board over a serial port (no repo imports needed on the PC side).
usage: hexn_hexcard_vector_v2.py REF.json SIMDIR OUT.json     (SIMDIR = the folder `hexn_kxarr_v1.py sim REF SIMDIR` wrote; its src/ is simulated)"""
import json, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_wrgrid_hex_v3 as H, hexn_icm_export_v4 as X, hexn_vm_v7 as V, hexn_assemble_hex_v2 as A, hexn_bytecard_sim_v1 as B
N = H.Node9


def cases():
    return {"prio4": ([N("p", "prio", ["x", "y", "z", "w"], cfg=dict(mask=15, ranks=(0, 1, 2, 3), mode=0))], ["x", "y", "z", "w"], ["p"]),
            "addsub": ([N("a", "add", ["x", "y"]), N("r", "sub", ["a", "z"])], ["x", "y", "z"], ["r"])}


def make(ref_path, adir, out):
    ref = json.load(open(ref_path)); n = ref["rows"]; off = ref["offset"]
    ct = {(w["r"], w["c"]): w["type"] for w in ref["work_cells"]}
    res = {"format": "hexn-card-selftest-v1", "pattern": ref["name"], "pattern_id_hex": ref["pattern_id_hex"], "rows": n, "link": "byte-port", "tests": []}
    for kind, (nodes, ins, outs) in cases().items():
        H.OFFSET = off
        try: P = H.plan10(nodes, ins, outs, n, n, ct, tries=40)
        except Exception as e: print(kind, "not plannable on this pattern:", str(e)[:80]); continue
        prog = X.from_icm(X.to_icm(X.program_of(P, ct, ref["name"]))); H.OFFSET = 0
        rnd = random.Random(5); iv = {k: rnd.randrange(1 << 32) for k in ins}; rows = prog["pads_in"]
        chain = A.chain_image(ref, prog)
        cmds = [("I",), ("W",), ("B", chain)] + [("D", rows[k][0], iv[k]) for k in ins] + [("G", sum(1 << rows[k][0] for k in ins)), ("wait", 700), ("L",)]
        r = B.ByteSim(os.path.join(adir, "src")).run(cmds); got = r[-1]; cap = V.HexVM(prog).run(iv)[outs[0]]
        assert r[0] == dict(pattern_id=ref["pattern_id"], rows=n), r[0]
        assert got and [w for _, w, _ in got] == [w for _, w in cap], (got, cap)
        res["tests"].append({"name": kind, "chain_hex": chain.hex(), "inputs": [[rows[k][0], iv[k]] for k in ins],
                             "mask": sum(1 << rows[k][0] for k in ins), "expected": [list(e) for e in got]})
        print(kind, "chain bytes", len(chain), "words", [hex(w) for _, w, _ in got], "ticks", [t for _, _, t in got])
    json.dump(res, open(out, "w"), indent=1); print("wrote", out)


if __name__ == "__main__":
    make(*sys.argv[1:4])
