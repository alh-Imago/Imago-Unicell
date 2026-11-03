"""hexn_icm_export_v4.py - the SIX-FACE (hex) program file, format 'icm-hexn-v4' (3 Nov 2026, H3/H4 of the hex line; Alan 18:46 'proceed through').
Not a clone of v3 (v1-v3 are four-face and untouched): the hex grid has no ICM cross/corner cores, so every routing cell is the private 'route' core with a per-output select table
{out face: in face} using the hex face names E SE SW W NW NE. A file carries everything needed to rebuild the grid from the file alone:
  header  faces=6, rows, cols, offset (which colour of the 3-colouring is a work cell), bitstream name
  records work cells (type, kind, mode, k, cfg - cfg holds fi/fo, the chosen faces), routing cells (route table, optional hold {out, dly})
  io      pads_in / pads_out (name -> [row, col])
Scope: a data format plus loader checks; it is NOT yet the ICM format of the UniCell side, and the hex cell RTL is not generated from it yet (that is the next stage)."""
import hashlib, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_hexgeom_v1 as HX

FORMAT = "icm-hexn-v4"
HOLD_MIN, HOLD_MAX = 2, 96
_canon = lambda x: json.dumps(x, sort_keys=True, separators=(",", ":"))


def program_of(P, types, name="hex"):
    """program dict from a hex plan (hexn_wrgrid_hex_v3): types = {work cell: type letters}"""
    import hexn_wrgrid_hex_v3 as H
    g = H.configure9(P)
    cells = {}
    for w, i in g.work.items():
        cells["%d,%d" % w] = dict(type=types[w], kind=i["op"], mode=i["mode"], k=i["k"], cfg={k: (list(v) if isinstance(v, (list, tuple)) else v) for k, v in i["cfg"].items()}, ins=i["ins"], outs=i["outs"])
    holds = {"%d,%d" % c: dict(out=f, dly=h) for (c, f), h in getattr(g, "holds", {}).items()}
    return dict(bitstream=name, rows=g.R, cols=g.C, offset=H.OFFSET, cells=cells, routing={"%d,%d" % c: dict(s) for c, s in g.route.items()},
                holds=holds, pads_in={k: list(v) for k, v in g.pads_in.items()}, pads_out={k: list(v) for k, v in g.pads_out.items()})


def _check(program):
    R, C, off = program["rows"], program["cols"], program["offset"]
    col = lambda r, c: HX.colour(r, c)
    for key in program["cells"]:
        r, c = map(int, key.split(","))
        if not (0 <= r < R and 0 <= c < C) or col(r, c) != off: raise ValueError("work cell %s is not a work position of a %dx%d grid at offset %d" % (key, R, C, off))
    for key, sel in program["routing"].items():
        r, c = map(int, key.split(","))
        if not (0 <= r < R and 0 <= c < C) or col(r, c) == off: raise ValueError("routing cell %s is outside the grid or is a work position" % key)
        for o, i in sel.items():
            if o not in HX.NAMES or i not in HX.NAMES: raise ValueError("routing cell %s: %s<-%s is not a hex face" % (key, o, i))
    for key, h in program["holds"].items():
        if key not in program["routing"] or h["out"] not in HX.NAMES or not (HOLD_MIN <= h["dly"] <= HOLD_MAX): raise ValueError("hold at %s invalid: %r" % (key, h))


def to_icm(program, name=None):
    _check(program)
    recs = []
    for key in sorted(program["cells"], key=lambda k: tuple(map(int, k.split(",")))):
        r, c = map(int, key.split(",")); v = program["cells"][key]
        recs.append(dict(cell_id="r%dc%d" % (r, c), row=r, col=c, core=v["type"], core_config=dict(kind=v["kind"], mode=v["mode"], k=v["k"], cfg=v["cfg"], ins=v["ins"], outs=v["outs"])))
    for key in sorted(program["routing"], key=lambda k: tuple(map(int, k.split(",")))):
        r, c = map(int, key.split(",")); cc = dict(route=dict(program["routing"][key]))
        if key in program["holds"]: cc["hold"] = dict(program["holds"][key])
        recs.append(dict(cell_id="r%dc%d" % (r, c), row=r, col=c, core="route", core_config=cc))
    d = dict(format_version=FORMAT, name=name or program["bitstream"], faces=6, rows=program["rows"], cols=program["cols"], offset=program["offset"], bitstream=program["bitstream"],
             records=recs, io=dict(inputs={k: list(v) for k, v in program["pads_in"].items()}, outputs={k: list(v) for k, v in program["pads_out"].items()}))
    d["record_hash"] = hashlib.sha256(_canon([d["records"], d["io"], d["faces"], d["rows"], d["cols"], d["offset"]]).encode()).hexdigest()
    return json.loads(_canon(d))


def from_icm(d):
    if d.get("format_version") != FORMAT or d.get("faces") != 6: raise ValueError("not an icm-hexn-v4 (six-face) file")
    if d.get("record_hash") != hashlib.sha256(_canon([d["records"], d["io"], d["faces"], d["rows"], d["cols"], d["offset"]]).encode()).hexdigest():
        raise ValueError("record_hash mismatch: file damaged or edited")
    cells, routing, holds = {}, {}, {}
    for rec in d["records"]:
        key = "%d,%d" % (rec["row"], rec["col"]); cc = rec["core_config"]
        if rec["core"] == "route":
            routing[key] = dict(cc["route"])
            if "hold" in cc: holds[key] = dict(cc["hold"])
        else: cells[key] = dict(type=rec["core"], kind=cc["kind"], mode=cc["mode"], k=cc["k"], cfg=cc["cfg"], ins=cc["ins"], outs=cc["outs"])
    prog = dict(bitstream=d["bitstream"], rows=d["rows"], cols=d["cols"], offset=d["offset"], cells=cells, routing=routing, holds=holds, pads_in=d["io"]["inputs"], pads_out=d["io"]["outputs"])
    _check(prog)
    return prog
