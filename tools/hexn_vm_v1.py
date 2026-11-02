"""hexn_vm_v1.py - the SERIAL VM (2 Nov 2026; Alan 17:17: 'add in a new serial version of the vm, and you have a place to check they work').

Loads an icm-hexn-v1 file (tools/hexn_icm_export_v1.py) and runs it on the word-level serial grid model - the same model whose cores and links were
checked tick for tick against the RTL (tests/vm/test_hexn_twins_v1.py, z-words at least 32 ticks apart on a link).  It needs ONLY the file: no planner
objects and no Base.  Use: vm = SerialVM.load(path_or_dict); out = vm.run({'x': 5, 'off': 7}) -> {'y': [(tick, word), ...]}.
`inputs` values are an int (one word at tick 0) or a list of (tick, word).  Scope: this is a model of the Hex-N grid, not of the 4-face parallel UniCell
SuperGrid; it does not run Verilog; six faces are refused (the exporter does so)."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_bases_v2 as B
import hexn_icm_export_v1 as X

G = B.G
from hexn_wrgrid_v6 import Grid


class SerialVM:
    def __init__(self, program, name=""):
        self.program, self.name = program, name
        # grid size from the file alone: one more than the largest row or column used by a cell, a route or a pad
        pts = [tuple(map(int, k.split(","))) for k in list(program["cells"]) + list(program["routing"])] + [tuple(v) for v in list(program["pads_in"].values()) + list(program["pads_out"].values())]
        self.n = max(max(p) for p in pts) + 1
        self.inputs, self.outputs = sorted(program["pads_in"]), sorted(program["pads_out"])

    @classmethod
    def load(cls, src):
        if isinstance(src, str):
            with open(src) as f: src = json.load(f)
        return cls(X.from_icm(src), src.get("name", ""))

    def grid(self):
        p = json.loads(json.dumps(self.program)); g = Grid(self.n, self.n)
        for key, sel in p["routing"].items(): r, c = map(int, key.split(",")); g.route[(r, c)] = dict(sel)
        for key, v in p["cells"].items():
            r, c = map(int, key.split(",")); assert v["kind"] in G.CELLTYPES[v["type"]][0], "cell %s: %s is not a kind of %s" % (key, v["kind"], v["type"])
            g.work[(r, c)] = dict(op=v["kind"], k=v["k"], mode=v["mode"], aligned=(v["mode"] == "aligned"), cfg=dict(v["cfg"]), ins=v["ins"], outs=v["outs"])
        g.pads_in = {k: tuple(v) for k, v in p["pads_in"].items()}; g.pads_out = {k: tuple(v) for k, v in p["pads_out"].items()}
        return g

    def run(self, inputs, ticks=900):
        missing = [n for n in self.inputs if n not in inputs]
        if missing: raise ValueError("no value for input(s): %s" % ", ".join(missing))
        return G.simulate9(None, inputs, self.outputs, ticks=ticks, g=self.grid())
