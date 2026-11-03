# hexn_vm_v6 = hexn_vm_v5 (untouched) on hexn_wrgrid_v21 (face choice; 3 Nov 2026).
# hexn_vm_v5 = hexn_vm_v4 (untouched) on hexn_wrgrid_v21: the latch is simulated (3 Nov 2026).
"""hexn_vm_v4 = the serial VM that REPLAYS THE RAM HOLDS from the program (3 Nov 2026): reads icm-hexn-v3 (holds as core_config.hold) and puts them on the grid, so a plan that needs a hold runs right from the file alone. vm_v3 untouched (it dropped holds).
hexn_vm_v3 = the serial VM on the v16 planner's core model (lt / min / max on RTL timing, 3 Nov 2026); vm_v2 untouched.
hexn_vm_v1.py - the SERIAL VM (v2: reads icm-hexn-v2 and v1 files; 2 Nov 2026; Alan 17:17: 'add in a new serial version of the vm, and you have a place to check they work').

Loads an icm-hexn-v2 file (tools/hexn_icm_export_v2.py) and runs it on the word-level serial grid model - the same model whose cores and links were
checked tick for tick against the RTL (tests/vm/test_hexn_twins_v1.py, z-words at least 32 ticks apart on a link).  It needs ONLY the file: no planner
objects and no Base.  Use: vm = SerialVM.load(path_or_dict); out = vm.run({'x': 5, 'off': 7}) -> {'y': [(tick, word), ...]}.
`inputs` values are an int (one word at tick 0) or a list of (tick, word).  Scope: this is a model of the Hex-N grid, not of the 4-face parallel UniCell
SuperGrid; it does not run Verilog; six faces are refused (the exporter does so)."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_wrgrid_v21 as G
import hexn_icm_export_v3 as X

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
        g.holds = {}
        for key, h in (p.get("holds") or {}).items():
            r, c = map(int, key.split(",")); g.holds[((r, c), h["out"])] = h["dly"]
        g.pads_in = {k: tuple(v) for k, v in p["pads_in"].items()}; g.pads_out = {k: tuple(v) for k, v in p["pads_out"].items()}
        return g

    def run(self, inputs, ticks=900):
        missing = [n for n in self.inputs if n not in inputs]
        if missing: raise ValueError("no value for input(s): %s" % ", ".join(missing))
        return G.simulate9(None, inputs, self.outputs, ticks=ticks, g=self.grid())
