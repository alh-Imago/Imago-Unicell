"""hexn_icm_export_v3.py - clone of hexn_icm_export_v2.py (kept as it was) that CARRIES THE RAM HOLDS (3 Nov 2026, Alan 09:50 'apply the ram side').
Why: the planner's holds (hexn_wrgrid_v18: g.holds {(cell, out face): h}, h = 2..96 clocks) were not in the program dict, so the ICM file, the unit file and the serial VM silently lost them: a plan that depended on a hold ran wrong anywhere but in the planner.
Change: to_icm takes program["holds"] = {"r,c": {"out": face letter, "dly": h}} (ONE hold per cell - the RAM routing cell RTL has one delay line; a second hold in a cell is refused by name) and writes it as core_config["hold"] of that cell's routing record;
from_icm returns it again as program["holds"]. Format name 'icm-hexn-v3'; v1 and v2 files are still read (no holds). The record hash covers the holds.
Original v2 text follows.
"""
import hashlib, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_icm_export_v2 as V2
import hexn_icm_export_v1 as V1

FORMAT = "icm-hexn-v3"
_canon = V1._canon
HOLD_MIN, HOLD_MAX = 2, 96


def to_icm(program, name, faces=4, bridges=None):
    holds = program.get("holds") or {}
    d = V2.to_icm(program, name, faces, bridges)
    recs = {"%d,%d" % (r["row"], r["col"]): r for r in d["records"]}
    for key, h in holds.items():
        if not isinstance(h, dict) or set(h) != {"out", "dly"}: raise ValueError("hold at %s must be {out, dly}, got %r (more than one hold in a cell is not supported: one delay line per RAM cell)" % (key, h))
        if key not in recs: raise ValueError("hold at %s: no routing cell there" % key)
        if recs[key]["core"] not in ("route", "cross", "corner", "ram"): raise ValueError("hold at %s: that is a work cell, not a routing cell" % key)
        if not (HOLD_MIN <= h["dly"] <= HOLD_MAX) or h["out"] not in "NESW": raise ValueError("hold at %s out of range: %r" % (key, h))
        recs[key]["core_config"] = dict(recs[key]["core_config"], hold=dict(h))
    d["format_version"] = FORMAT
    d["record_hash"] = hashlib.sha256(_canon([d["records"], d["io"], d["faces"]]).encode()).hexdigest()
    return json.loads(_canon(d))


def from_icm(d):
    if d.get("format_version") != FORMAT: return V2.from_icm(d)
    if d.get("record_hash") != hashlib.sha256(_canon([d["records"], d["io"], d["faces"]]).encode()).hexdigest():
        raise ValueError("record_hash mismatch: file damaged or edited")
    plain = json.loads(json.dumps(d)); holds = {}
    for rec in plain["records"]:
        cc = rec["core_config"]
        if "hold" in cc: holds["%d,%d" % (rec["row"], rec["col"])] = cc.pop("hold")
    plain["format_version"] = V2.FORMAT
    plain["record_hash"] = hashlib.sha256(_canon([plain["records"], plain["io"], plain["faces"]]).encode()).hexdigest()
    prog = V2.from_icm(plain)
    prog["holds"] = holds
    return prog
