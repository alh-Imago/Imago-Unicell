"""hexn_icm_export_v2.py - clone of hexn_icm_export_v1.py (kept as it was) that uses the ICM's NATIVE wiring cores (2 Nov 2026).

What changed and why: v1 wrote every routing cell as a private 'route' table.  The ICM already has 'cross' (W-E and N-S straight), 'corner' (turn 0: E-N and
W-S; turn 1: E-S and W-N) and the 'ram' relay (one input, fan-out through downstream_mask), with RTL (cross_cell_v4, corner_cell_v4) and VM models
(nano/corner_cell_automaton_v1.py).  tools/hexn_icm_survey_v2.py measured that 385 of 450 routing cells of the 19 example designs are one of those; the other 65
(a turn of each kind, or a turn with a straight) keep the private 'route' core (per-output select table), which stays an ADDITION to the ICM.
Record shapes: cross/corner/ram: core_config {upstream_mask: [faces], downstream_mask: [faces], turn: 0|1 (corner only)}; route: {route: {out: in}}.
A tile carries words both ways on each pair, so it does at least what the one-way paths need; from_icm rebuilds exactly the original paths from the masks.
Core table corrected from the real core names (nano/icm_v3.py CORE_NAMES): priority, merge, cross, corner exist.  join (JN) and shifts have no entry I can confirm.
Format name 'icm-hexn-v2'; from_icm still reads 'icm-hexn-v1' files.  Not run through the repo's own readers or the SuperGrid VM yet."""
import hashlib, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_icm_export_v1 as V1
import hexn_icm_survey_v2 as S

FORMAT = "icm-hexn-v2"
ICM_CORE = dict(V1.ICM_CORE, merge="merge", prio="priority")                  # both names exist in nano/icm_v3.py CORE_NAMES; kinds of a join/shift: not confirmed
PARTNER = {"cross": {"W": "E", "E": "W", "N": "S", "S": "N"},
           "corner0": {"E": "N", "N": "E", "W": "S", "S": "W"}, "corner1": {"E": "S", "S": "E", "W": "N", "N": "W"}}
_canon = V1._canon


def _tile(sel):
    """-> (core, core_config) for a routing cell's {out: in} table"""
    kind = S.classify(sel)
    if kind == "other": return "route", dict(route=dict(sel))
    ups, downs = sorted(set(sel.values())), sorted(set(sel))
    if kind == "relay": return "ram", dict(upstream_mask=ups, downstream_mask=downs, fixed_mode=0)
    if kind == "cross": return "cross", dict(upstream_mask=ups, downstream_mask=downs)
    return "corner", dict(upstream_mask=ups, downstream_mask=downs, turn=int(kind[-1]))


def _paths(core, cc):
    if core == "route": return dict(cc["route"])
    ups, downs = cc["upstream_mask"], cc["downstream_mask"]
    if core == "ram": return {o: ups[0] for o in downs}
    table = PARTNER["cross" if core == "cross" else "corner%d" % cc["turn"]]
    return {table[i]: i for i in ups if table[i] in downs}


def to_icm(program, name, faces=4, bridges=None):
    """bridges: optional list of {name, pad: [row, col] (an edge pad of this program), direction: 'to_unicell' | 'from_unicell', unicell_io: the io_name on the UniCell-side ICM file}.
    A bridge is where a serial stream meets the parallel UniCell side (flex_to_sub_v1 / sub_to_flex_v1 plus a serialiser, not built); the record only NAMES the join."""
    d = V1.to_icm(program, name, faces)                                         # also refuses six faces
    d["format_version"] = FORMAT
    pads = {tuple(v) for v in list(d["io"]["inputs"].values()) + list(d["io"]["outputs"].values())}
    for b in bridges or []:
        if b["direction"] not in ("to_unicell", "from_unicell") or tuple(b["pad"]) not in pads:
            raise ValueError("bridge %r: unknown direction or its pad is not a pad of this program" % b.get("name"))
    d["io"]["bridges"] = [dict(b) for b in (bridges or [])]
    for rec in d["records"]:
        if rec["core"] != "route":
            rec["icm_core"] = ICM_CORE.get(rec["core_config"]["kind"])              # the corrected table (v1's is not used)
        else:
            rec["core"], rec["core_config"] = _tile(rec["core_config"]["route"])
            rec["icm_core"] = None if rec["core"] == "route" else rec["core"] if rec["core"] != "ram" else "ram"
    d["record_hash"] = hashlib.sha256(_canon([d["records"], d["io"], d["faces"]]).encode()).hexdigest()
    return json.loads(_canon(d))


def from_icm(d):
    if d.get("format_version") == V1.FORMAT: return V1.from_icm(d)
    if d.get("format_version") != FORMAT: raise ValueError("not an icm-hexn file")
    if d.get("record_hash") != hashlib.sha256(_canon([d["records"], d["io"], d["faces"]]).encode()).hexdigest():
        raise ValueError("record_hash mismatch: file damaged or edited")
    if d.get("faces", 4) != 4: raise NotImplementedError("only four faces are supported")
    cells, routing = {}, {}
    for rec in d["records"]:
        key = "%d,%d" % (rec["row"], rec["col"]); cc = rec["core_config"]
        if rec["core"] in ("route", "cross", "corner", "ram"): routing[key] = _paths(rec["core"], cc)
        else: cells[key] = dict(type=rec["core"], kind=cc["kind"], mode=cc["mode"], k=cc["k"], cfg=cc["cfg"], ins=cc["ins"], outs=cc["outs"])
    return dict(bitstream=d["bitstream"], cells=cells, routing=routing, pads_in=d["io"]["inputs"], pads_out=d["io"]["outputs"], config_bits_estimate=d.get("config_bits_estimate"))


def report(d):
    work = [r for r in d["records"] if r["core"] not in ("route", "cross", "corner", "ram")]; rt = [r for r in d["records"] if r["core"] in ("route", "cross", "corner", "ram")]
    c = {}
    for r in rt: c[r["core"]] = c.get(r["core"], 0) + 1
    return dict(work_cells=len(work), work_with_icm_core=sum(1 for r in work if r["icm_core"]), work_without=sorted({r["core_config"]["kind"] for r in work if not r["icm_core"]}), routing_by_core=c)
