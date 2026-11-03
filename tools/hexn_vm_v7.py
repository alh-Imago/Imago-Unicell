"""hexn_vm_v7.py - the HEX serial VM (3 Nov 2026, H3). Reads an icm-hexn-v4 file (six faces, tools/hexn_icm_export_v4.py) and runs it on the hex grid model of tools/hexn_wrgrid_hex_v3.py from the file ALONE (no planner objects).
vm_v6 (four faces) is untouched. Same use: vm = HexVM.load(path_or_dict); vm.run({'x': 5}) -> {'y': [(tick, word), ...]}.
Scope: the same word-level serial model as the planner's simulation (cores checked tick for tick against RTL at four faces, tests/vm/test_hexn_tiles6_v1.py at six); no Verilog is run."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_wrgrid_hex_v3 as H
import hexn_icm_export_v4 as X


class HexVM:
    def __init__(self, program, name=""):
        self.program, self.name = program, name
        self.inputs, self.outputs = sorted(program["pads_in"]), sorted(program["pads_out"])

    @classmethod
    def load(cls, src):
        if isinstance(src, str):
            with open(src) as f: src = json.load(f)
        return cls(X.from_icm(src), src.get("name", ""))

    def grid(self):
        p = json.loads(json.dumps(self.program)); g = H.Grid12(p["rows"], p["cols"])
        for key, sel in p["routing"].items(): r, c = map(int, key.split(",")); g.route[(r, c)] = dict(sel)
        for key, v in p["cells"].items():
            r, c = map(int, key.split(",")); assert v["kind"] in H.CELLTYPES[v["type"]][0], "cell %s: %s is not a kind of %s" % (key, v["kind"], v["type"])
            g.work[(r, c)] = dict(op=v["kind"], k=v["k"], mode=v["mode"], aligned=(v["mode"] == "aligned"), cfg=dict(v["cfg"]), ins=v["ins"], outs=v["outs"])
        g.holds = {}
        for key, h in p["holds"].items(): r, c = map(int, key.split(",")); g.holds[((r, c), h["out"])] = h["dly"]
        g.pads_in = {k: tuple(v) for k, v in p["pads_in"].items()}; g.pads_out = {k: tuple(v) for k, v in p["pads_out"].items()}
        return g

    def run(self, inputs, ticks=900):
        missing = [n for n in self.inputs if n not in inputs]
        if missing: raise ValueError("no value for input(s): %s" % ", ".join(missing))
        old = H.OFFSET; H.OFFSET = self.program["offset"]
        try: return H.simulate9(None, inputs, self.outputs, ticks=ticks, g=self.grid())
        finally: H.OFFSET = old
