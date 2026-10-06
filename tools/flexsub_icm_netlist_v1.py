#!/usr/bin/env python3
"""
flexsub_icm_netlist_v1.py -- STEP 2, FIRST SLICE of the Flex-Sub assembler plan: read an ICM-VIX file
as a map and extract the real netlist it describes, then say -- cell by cell and edge by edge -- what
the Flex-Sub families can and cannot express. READ-ONLY: it generates no Verilog.

Why this comes before the generator: the ICM-VIX `connections` list is ADVISORY (docs/stripped-cell/
ICM_VIX_FORMAT.md). The authoritative wiring is each flattened cell's own upstream/downstream masks
plus its grid position -- so the netlist here is derived from those, never from `connections`.
A Flex-Sub cell has dedicated ports instead of cardinal faces, and the old cells' semantics differ in
ways a translation must handle; this tool puts numbers on each difference for a real ICM file.

What the old (VM) semantics are, read from nano/unicell_super_automaton_v1.py, not assumed:
  * several masked directions arriving on the same tick are OR-combined (a "merge")
  * a two-operand cell (adder, mul) takes operand A = FIRST arrival, B = SECOND -- by ARRIVAL ORDER,
    not by direction. A fixed in_a/in_b port pair therefore needs the arrival order known statically.
  * a single stream can deliver BOTH operands on successive ticks (no direct two-port equivalent).

Usage:  python3 tools/flexsub_icm_netlist_v1.py FILE.icm-hier.json [--family flex|sub] [--json]
"""
import argparse
import collections
import json
import os
import sys

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(TOOLS_DIR)
sys.path.insert(0, os.path.join(REPO_ROOT, "nano"))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, TOOLS_DIR)

DELTA = {"N": (-1, 0), "S": (1, 0), "E": (0, 1), "W": (0, -1)}
OPP = {"N": "S", "S": "N", "E": "W", "W": "E"}

# Every core_config key that names INPUT directions, with the input "role" it feeds.
INPUT_FIELDS = {
    "upstream_mask": "in", "upstream_dir": "in",
    "set_dir": "set", "clear_dir": "clear", "toggle_dir": "toggle",
    "inc_dir": "inc", "dec_dir": "dec",
}
# ICM core -> Flex-Sub shape key (tools/flexsub_assemble_v1.SHAPES). None => no Flex-Sub equivalent.
CORE_TO_SHAPE = {
    "ram": "ram", "adder": "adder", "comparator": "compare", "accumulator": "accumulator",
    "sequencer": "sequencer", "latch": "latch", "mul": "mul", "nano": "nano", "branch": "branch",
    "priority": None, "command": None,
}
# Two-operand cores: operand roles are by ARRIVAL ORDER in the VM.
TWO_OPERAND = {"adder", "mul", "nano"}   # nano: first arrival = held operand A, second = flowing operand B (VM CACell)
# How each core's config words translate (read from the root_definition fields vs each v4sa cell's header).
CONFIG_NOTES = {
    "ram": "direct: fixed_mode -> cfg_fixed_mode port, init_data -> cfg_data (load_data_valid has no v4sa field)",
    "adder": "direct: subtract_mode -> cfg_data[0]; carry_mode (flex only, ledger #976) -> cfg_data[1] and the SECOND_PORT build parameter",
    "comparator": "direct: threshold -> cfg_data[WIDTH-1:0]",
    "accumulator": "direct: step_amount/pulse_mode/threshold -> cfg_data[7:0]/[8]/[24:9]",
    "sequencer": "direct: VALUE_0..3 -> cfg_data bytes, SEQUENCE_LEN -> cfg_seq_len_m1",
    "latch": "no config word (v4sa latch ignores cfg_data); set/clear/toggle come from the wiring",
    "mul": "wide_mode: v4s (sub) has no equivalent -- refused; on flex it is the mul's second output port (data_out_hi, cfg_data[0], ledger #976)",
    "nano": "topology[9:0] -> cfg_data[9:0] direct; routing_mask/cardinal_edge/out_buffer are carrier fields, no equivalent",
    "branch": "LOSSY: v4sa branch has two flowing inputs, ONE shared emit_source, and 2-bit out1/out2 routing; "
              "the ICM branch has per-outcome value_source/fixed_value/emit and 4-bit cardinal routing -- "
              "translation exists only for the representable subset (see per-cell verdict)",
    "priority": "NO Flex-Sub cell",
    "command": "NO Flex-Sub cell (live reprogramming is incompatible with fixed paths, #905)",
}


def _dirs(cfg, key):
    """Direction letters, normalised to upper case: ICM-VIX files write "N","S", the compiler's ICM v3 writes "n","s"."""
    v = cfg.get(key)
    if v is None:
        return []
    if isinstance(v, bool):
        return []
    if isinstance(v, int):
        # ICM v3 keeps some fields as RAW INTS: `upstream_dir` is a single direction CODE (0=N 1=S 2=E 3=W, icm_v3.py: "not a one-hot
        # mask"); every other direction field, as an int, is a one-hot bitmask with the same bit order (n=0, s=1, e=2, w=3).
        if key == "upstream_dir":
            return ["NSEW"[v]] if 0 <= v <= 3 else []
        return [d for b, d in enumerate("NSEW") if (v >> b) & 1]
    return [str(v).upper()] if isinstance(v, str) else [str(d).upper() for d in v]


class _FlatDoc:
    """Stand-in for IcmVixFile when the input is a flat ICM v3 file (no patterns, no advisory connections)."""
    def __init__(self, path):
        self.name = os.path.basename(path)

    def check_connections(self):
        return []


def load_records(path):
    """(doc, records) for either format: ICM-VIX (hierarchical, 'icm-vix-v1') or ICM v3 (flat, the LLVM
    compiler's output). Detected from the file's own format_version, never from its extension."""
    with open(path) as f:
        head = json.load(f)
    if str(head.get("format_version", "")).startswith("icm-vix"):
        import icm_vix_v1 as vix
        doc = vix.IcmVixFile.load(path)
        recs, _ = doc.flatten()
        return doc, recs
    from icm_v3 import IcmV3File
    f3 = IcmV3File.load(path)
    doc = _FlatDoc(path)
    doc.min_bit_width = f3.min_bit_width           # the design's declared minimum bit width (ledger #958); None = absent = 32
    return doc, f3.records


def extract(path):
    """Flatten the ICM-VIX file and derive the real netlist from masks + positions."""
    doc, recs = load_records(path)
    cells = {r.cell_id: r for r in recs}
    pos = {(r.row, r.col): r.cell_id for r in recs}
    edges, warnings = [], []
    inputs = collections.defaultdict(lambda: collections.defaultdict(list))   # dst -> role -> [(src, face_at_dst)]
    outputs = collections.defaultdict(list)                                   # src -> [dst]
    external_out = collections.defaultdict(list)                              # src -> [face leaving the grid]
    for r in recs:
        cfg = r.core_config or {}
        faces = collections.OrderedDict()                                     # face -> outcomes using it
        for d in _dirs(cfg, "downstream_mask"):
            faces.setdefault(d, [])
        if r.core == "nano":                                                  # nano's OUTPUT faces live in routing_mask
            for d in _dirs(cfg, "routing_mask"):
                faces.setdefault(d, [])
        if r.core == "branch":                                                # branch routes per OUTCOME, not by mask
            for k in ("low", "equal", "high"):
                for d in _dirs(cfg, f"route_{k}"):
                    faces.setdefault(d, []).append(k)
        for d, outcomes in faces.items():
            dr, dc = DELTA[d]
            dst_id = pos.get((r.row + dr, r.col + dc))
            if dst_id is None:
                external_out[r.cell_id].append(d)
                continue
            dst = cells[dst_id]
            dcfg = dst.core_config or {}
            role = next((INPUT_FIELDS[k] for k in INPUT_FIELDS if OPP[d] in _dirs(dcfg, k)), None)
            if role is None and dst.core == "nano":                          # nano has no upstream mask: it consumes from any face
                role = "in"
            if role is None:
                warnings.append(f"{r.cell_id} sends {d} but {dst_id} listens on no {OPP[d]} face (output dropped)")
                continue
            edges.append((r.cell_id, dst_id, d, role, tuple(outcomes)))
            inputs[dst_id][role].append((r.cell_id, OPP[d]))
            outputs[r.cell_id].append(dst_id)
    try:
        for w in doc.check_connections():
            warnings.append(f"advisory connection check: {w}")
    except Exception as e:                       # advisory only -- never block the analysis
        warnings.append(f"advisory connection check unavailable: {e}")
    return doc, recs, cells, edges, inputs, outputs, external_out, warnings


def hop_depths(cells, edges):
    """Longest hop count from any cell with no incoming edge. A hop is one tick in the VM (#cost = hops).
    Returns ({cell: depth or None}, has_cycle). None for cells on/after a cycle."""
    preds = collections.defaultdict(list)
    for e in edges:
        preds[e[1]].append(e[0])
    memo, state = {}, {}

    def go(c):
        if c in memo:
            return memo[c]
        if state.get(c) == 1:
            return None                          # on a cycle
        state[c] = 1
        ds = [go(p) for p in preds[c]]
        state[c] = 2
        memo[c] = 0 if not preds[c] else (None if any(x is None for x in ds) else 1 + max(ds))
        return memo[c]

    out = {c: go(c) for c in cells}
    return out, any(v is None for v in out.values())


FACE_ORDER = "NSEW"


def eliminate_priority(cells, inputs, outputs):
    """Rewrite `priority -> two-operand cell` into direct operand wiring (the fixed-port families have
    dedicated in_a/in_b, so the arbiter that serialised two operands onto ONE input is not needed).

    The operand order the arbiter would have produced (read from the VM's _deliver_priority, mode 0):
    it captures the FIRST arrival; among simultaneous candidates the LOWEST rank wins ("0 = highest"),
    ties broken N > S > E > W. So A = earlier-arriving source; on an arrival tie, lower rank, then
    N > S > E > W. Returns (cells, inputs, outputs, tiekeys, eliminated, problems); tiekeys[(cell, src)] =
    (rank, face_index) is the tie-break for the pair now feeding `cell`.
    Refused, with the reason: weighted round-robin / sequenced modes, a priority that does not feed exactly
    one two-operand cell as that cell's only source, and anything but exactly two candidates."""
    cells, inputs, outputs = dict(cells), {k: {r: list(v) for r, v in d.items()} for k, d in inputs.items()}, \
        {k: list(v) for k, v in outputs.items()}
    tiekeys, done, problems = {}, [], []
    for pid in [c for c, r in cells.items() if r.core == "priority"]:
        cfg = cells[pid].core_config or {}
        srcs = inputs.get(pid, {}).get("in", [])
        mode = cfg.get("scheduling_mode", 0)
        cons = outputs.get(pid, [])
        if mode != 0:
            problems.append(f"{pid}: priority scheduling_mode={mode} ({'weighted round-robin' if mode == 1 else 'sequenced channel'}) "
                            f"-- the arrival order depends on arbiter state, not wiring; only strict mode 0 is eliminable")
            continue
        if len(srcs) != 2 or len(cons) != 1:
            problems.append(f"{pid}: priority has {len(srcs)} source(s) and {len(cons)} consumer(s); eliminable only as 2 -> 1")
            continue
        c = cons[0]
        cin = inputs.get(c, {}).get("in", [])
        if cells[c].core not in TWO_OPERAND or [x for x, _ in cin] != [pid]:
            problems.append(f"{pid}: feeds {c} ({cells[c].core}) -- eliminable only when it is the SOLE source of a two-operand cell "
                            f"(a priority in front of a one-input cell is stream arbitration, which has no fixed-port form)")
            continue
        for src, face in srcs:
            tiekeys[(c, src)] = (cfg.get(f"priority_rank_{face.lower()}", 0), FACE_ORDER.index(face))
            outputs[src] = [c if x == pid else x for x in outputs[src]]
        inputs[c]["in"] = [(src, face) for src, face in srcs]
        del cells[pid], inputs[pid], outputs[pid]
        done.append(pid)
    return cells, inputs, outputs, tiekeys, done, problems


def analyse(path, family="flex"):
    import flexsub_assemble_v1 as fsa
    doc, recs, cells, edges, inputs, outputs, ext_out, warnings = extract(path)
    depth, cyclic = hop_depths(cells, edges)
    rep = {"file": path, "name": doc.name or os.path.basename(path), "family": family, "cells": len(recs), "edges": len(edges),
           "cyclic": cyclic, "cores": dict(collections.Counter(r.core for r in recs)),
           "warnings": warnings, "cell_verdicts": {}, "findings": collections.defaultdict(list)}
    supported = set(fsa.cells_for(family))
    for r in recs:
        cid, cfg = r.cell_id, (r.core_config or {})
        shape = CORE_TO_SHAPE.get(r.core, "?")
        v = {"core": r.core, "pos": [r.row, r.col], "shape": shape, "issues": []}
        if shape is None or shape == "?":
            v["issues"].append(f"no Flex-Sub cell for core {r.core!r}")
        elif shape not in supported:
            v["issues"].append(f"{shape!r} does not exist in the {family} family")
        if r.addon_config:
            v["issues"].append("addon_config present (shift/mask/invert fused on the cell): needs graph expansion "
                               "into separate cells (#905)")
        if r.core == "mul" and cfg.get("wide_mode") and family != "flex":
            v["issues"].append("mul wide_mode=1 has no v4s equivalent (the flex mul has it as a second output port, ledger #976)")
        if r.core == "adder" and cfg.get("carry_mode") and family != "flex":
            v["issues"].append("adder carry_mode=1 has no v4s equivalent (the flex adder has it as a second output port, ledger #976)")
        if r.core == "branch":
            vs = {cfg.get(f"value_source_{k}") for k in ("low", "equal", "high")}
            fv = {cfg.get(f"fixed_value_{k}") for k in ("low", "equal", "high")}
            em = {cfg.get(f"emit_{k}") for k in ("low", "equal", "high")}
            if len(vs) > 1 or (0 in vs and len(fv) > 1):
                v["issues"].append("branch per-outcome value_source/fixed_value differ -- v4sa has ONE shared emit_source")
            if em != {1}:
                v["issues"].append("branch emit_* not all 1 -- must be re-expressed as 'route to neither'")
            used = list(collections.OrderedDict.fromkeys(d for k in ("low", "equal", "high") for d in _dirs(cfg, f"route_{k}")))
            if len(used) > 2:
                v["issues"].append(f"branch routes to {len(used)} distinct faces {used}; v4sa has only out1/out2")
            else:
                port = {d: f"out{i + 1}" for i, d in enumerate(used)}
                v["branch_ports"] = {"faces->ports": port, "route_bits": {
                    k: sum(1 << (int(port[d][3]) - 1) for d in _dirs(cfg, f"route_{k}")) for k in ("low", "equal", "high")}}
        roles = inputs.get(cid, {})
        v["inputs"] = {role: [s for s, _ in srcs] for role, srcs in roles.items()}
        for role, srcs in roles.items():
            n = len(srcs)
            if r.core == "priority" and role == "in":
                mode = cfg.get("scheduling_mode", 0)
                ranks = {f: cfg.get(f"priority_rank_{f.lower()}", 0) for _, f in srcs}
                rep["findings"]["arbiter"].append(
                    f"{cid}: priority arbiter, {n} sources {[x for x, _ in srcs]}, scheduling_mode={mode}, ranks={ranks} "
                    f"-> serialises them one at a time (NOT an OR); eliminable when it feeds one two-operand cell and mode is 0")
                continue
            if n > 1 and not (r.core in TWO_OPERAND and role == "in"):
                rep["findings"]["merge"].append(f"{cid}: role {role!r} has {n} sources {[s for s, _ in srcs]} "
                                                f"(VM OR-combines them) -> OR glue on data and valid")
            if r.core in TWO_OPERAND and role == "in":
                ds = [depth.get(s) for s, _ in srcs]
                if n == 2:
                    if None in ds:
                        verdict = "arrival order UNKNOWN (cycle in the sources' history)"
                    elif ds[0] == ds[1]:
                        verdict = f"TIED at depth {ds[0]}: A/B undecidable statically (the VM would OR them as one arrival)"
                    else:
                        first = srcs[0][0] if ds[0] < ds[1] else srcs[1][0]
                        verdict = f"depths {ds}: {first} arrives first -> operand A (hop-count estimate; matched the VM on 7/7 completed adders in the shipped examples, tests/test_flexsub_icm_netlist_v1.py -- a small sample, not a proof)"
                    rep["findings"]["two_operand"].append(f"{cid} ({r.core}): 2 sources {[s for s, _ in srcs]}; {verdict}")
                elif n == 1:
                    rep["findings"]["two_operand"].append(
                        f"{cid} ({r.core}): ONE source {srcs[0][0]} -- both operands must arrive as successive values on "
                        f"one stream; no direct two-port equivalent (needs pairing/hold logic)")
                elif n > 2:
                    rep["findings"]["two_operand"].append(f"{cid} ({r.core}): {n} sources -- more than two operands")
        fan = len(outputs.get(cid, []))
        if fan > 1:
            rep["findings"]["fan_out"].append(f"{cid}: drives {fan} cells {outputs[cid]} -> wires (sub) / router cell or ack-join (flex)")
        if not roles and not any(e[1] == cid for e in edges):
            if r.preload_value is not None:
                rep["findings"]["constant"].append(f"{cid} ({r.core}): preload_value={r.preload_value} -> constant source (not a pin)")
            elif r.io_name:
                rep["findings"]["entry"].append(f"{cid} ({r.core}) io_name={r.io_name!r}: no incoming edge -> top-level input")
            elif r.core == "sequencer":
                rep["findings"]["tick"].append(f"{cid} (sequencer): no upstream -> tick-driven source: on sub an external advance pulse, on flex the downstream ack")
            elif r.core == "ram" and not _dirs(cfg, "upstream_mask"):
                rep["findings"]["entry"].append(f"{cid} (ram): no upstream face -> injection point (compiled-program input)")
            else:
                rep["findings"]["undriven"].append(f"{cid} ({r.core}): no incoming edge, no io_name, no preload -- source unclear")
        if not outputs.get(cid):
            rep["findings"]["exit"].append(f"{cid} ({r.core}) io_name={r.io_name!r}: no outgoing edge -> observed output"
                                           + (f" (faces leaving the grid: {ext_out[cid]})" if ext_out.get(cid) else ""))
        v["config"] = CONFIG_NOTES.get(r.core, "?")
        rep["cell_verdicts"][cid] = v
    rep["findings"] = dict(rep["findings"])
    rep["clean_cells"] = sum(1 for v in rep["cell_verdicts"].values() if not v["issues"])
    rep["blocked_cells"] = {c: v["issues"] for c, v in rep["cell_verdicts"].items() if v["issues"]}
    return rep


def format_report(rep):
    L = [f"ICM-VIX netlist: {rep['name']}  ({rep['file']})",
         f"  target family: {rep['family']}   cells: {rep['cells']}   edges derived from masks: {rep['edges']}   "
         f"cycles: {'YES' if rep['cyclic'] else 'no'}",
         f"  cores: {rep['cores']}",
         f"  cells with no blocking issue: {rep['clean_cells']}/{rep['cells']}"]
    for k, title in (("entry", "top-level inputs"), ("constant", "constant sources"), ("undriven", "UNDRIVEN sources"), ("tick", "tick-driven sources"),
                     ("arbiter", "priority arbiters"),
                     ("exit", "observed outputs"), ("merge", "merges (OR-combine)"),
                     ("fan_out", "fan-outs"), ("two_operand", "two-operand cells (operand roles)")):
        items = rep["findings"].get(k, [])
        L.append(f"  {title}: {len(items)}")
        for i in items[:6]:
            L.append(f"      - {i}")
        if len(items) > 6:
            L.append(f"      ... and {len(items) - 6} more")
    if rep["blocked_cells"]:
        L.append(f"  BLOCKED cells: {len(rep['blocked_cells'])}")
        for c, iss in list(rep["blocked_cells"].items())[:8]:
            L.append(f"      - {c}: " + "; ".join(iss))
    if rep["warnings"]:
        L.append(f"  warnings: {len(rep['warnings'])}")
        for w in rep["warnings"][:6]:
            L.append(f"      - {w}")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("icm")
    ap.add_argument("--family", default="flex", choices=["flex", "sub"])
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    rep = analyse(a.icm, a.family)
    print(json.dumps(rep, indent=1, default=str) if a.json else format_report(rep))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
