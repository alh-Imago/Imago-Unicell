"""hexn_icm_export_v1.py - the Hex-N program as ICM-style records (2 Nov 2026; Alan 16:37 to 16:47).

Format name 'icm-hexn-v1'.  It is an EXTENSION of the ICM record idea, not yet an existing ICM format: same cell fields (cell_id, row, col, core,
core_config, io names) plus (a) a header `faces` (4 now; absent or 4 means four, 6 reserved for later) and (b) a routing cell with core 'route' whose
core_config.route is a PER-OUTPUT select table {out face: in face}, because an ICM relay cell merges every masked input into every masked output and a
Hex-N routing cell may carry several independent paths (tools/hexn_icm_survey_v1.py: 106 of 450 cells).
Work cells keep the Hex-N kind/mode/k/cfg in core_config and carry `icm_core`, the nearest existing ICM core name where there is one (None where there is none),
so a UniCell-side reader can see at once what it can map.  Nothing here runs on a VM or a card; `from_icm` rebuilds the program so the round trip and the
replay on the Python twin (hexn_bases_v2.run_program) can be tested."""
import hashlib, json

FORMAT = "icm-hexn-v1"
# nearest existing ICM core for each Hex-N kind (nano/icm_v3.py core names, flexsub_icm_netlist_v1.CORE_TO_SHAPE); None = no ICM equivalent known
ICM_CORE = {"add": "adder", "sub": "adder", "lt": "comparator", "min": "comparator", "max": "comparator", "ge": "comparator",
            "accum": "accumulator", "branch": "branch", "seq": "sequencer", "latch": "latch", "merge": None, "prio": None, "join": None}


def _canon(x):
    return json.dumps(x, sort_keys=True, separators=(",", ":"))


def to_icm(program, name, faces=4):
    assert faces in (4, 6)
    if faces == 6:
        raise NotImplementedError("six faces: reserved in the format, no planner or export for a hex layout yet")
    records = []
    for key in sorted(program["cells"], key=lambda k: tuple(map(int, k.split(",")))):
        r, c = map(int, key.split(",")); v = program["cells"][key]
        records.append(dict(cell_id="r%dc%d" % (r, c), row=r, col=c, core=v["type"], icm_core=ICM_CORE.get(v["kind"]),
                            core_config=dict(kind=v["kind"], mode=v["mode"], k=v["k"], cfg=v["cfg"], ins=v["ins"], outs=v["outs"])))
    for key in sorted(program["routing"], key=lambda k: tuple(map(int, k.split(",")))):
        r, c = map(int, key.split(","))
        records.append(dict(cell_id="r%dc%d" % (r, c), row=r, col=c, core="route", icm_core=None, core_config=dict(route=dict(program["routing"][key]))))
    d = dict(format_version=FORMAT, name=name, faces=faces, bitstream=program["bitstream"], records=records,
             io=dict(inputs={k: list(v) for k, v in program["pads_in"].items()}, outputs={k: list(v) for k, v in program["pads_out"].items()}),
             config_bits_estimate=program.get("config_bits_estimate"))
    d["record_hash"] = hashlib.sha256(_canon([d["records"], d["io"], d["faces"]]).encode()).hexdigest()
    return json.loads(_canon(d))


def from_icm(d):
    if d.get("format_version") != FORMAT:
        raise ValueError("not an icm-hexn-v1 file")
    if d.get("record_hash") != hashlib.sha256(_canon([d["records"], d["io"], d["faces"]]).encode()).hexdigest():
        raise ValueError("record_hash mismatch: file damaged or edited")
    if d.get("faces", 4) != 4:
        raise NotImplementedError("only four faces are supported")
    cells, routing = {}, {}
    for rec in d["records"]:
        key = "%d,%d" % (rec["row"], rec["col"]); cc = rec["core_config"]
        if rec["core"] == "route":
            routing[key] = dict(cc["route"])
        else:
            cells[key] = dict(type=rec["core"], kind=cc["kind"], mode=cc["mode"], k=cc["k"], cfg=cc["cfg"], ins=cc["ins"], outs=cc["outs"])
    return dict(bitstream=d["bitstream"], cells=cells, routing=routing, pads_in=d["io"]["inputs"], pads_out=d["io"]["outputs"],
                config_bits_estimate=d.get("config_bits_estimate"))


def report(d):
    """what a UniCell-side reader would find: counts of cells with a known ICM core, without one, and routing cells with 2+ paths"""
    work = [r for r in d["records"] if r["core"] != "route"]; rt = [r for r in d["records"] if r["core"] == "route"]
    return dict(work_cells=len(work), work_with_icm_core=sum(1 for r in work if r["icm_core"]), work_without=sorted({r["core_config"]["kind"] for r in work if not r["icm_core"]}),
                routing_cells=len(rt), routing_multi_path=sum(1 for r in rt if len(r["core_config"]["route"]) > 1))
