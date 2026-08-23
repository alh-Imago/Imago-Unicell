#!/usr/bin/env python3
"""
shape_extract_v1.py — points.md #449/#451: the "logical walk" tool.

Extracts a SHAPE file (real cell-to-cell adjacency, per the compiled
design's own actual RTL structure) from a top-level Verilog file, per
the MAN/ICM/SHAPE/BITSTREAM four-artifact architecture (#19/#23).

REAL, DELIBERATE SCOPE: this is a pragmatic extractor for THIS project's
own consistent RTL conventions (module_type #(params) INSTANCE (
.port(net), ... );), not a general Verilog parser. It works by finding
every named wire that connects exactly two instance ports within a
top-level file's own instantiation list -- since in a structural
netlist, two ports sharing the same net name IS the physical connection
-- and skips anything it can't confidently resolve (constants,
concatenations, bit-selects, nets touching more than 2 ports) rather
than guessing.

Confirms directly, not assumed: CELL_ID is a real, compile-time-only
identity tag (#19's own "compile-time constants baked into the
bitstream"); this tool reads it back out of the source, it does not
invent or renumber it.

Also classifies each cell's own real ROLE, per #253 (SHELL/CORE/ADDON)
and #293 (HOST-INTERFACE) -- an already-decided taxonomy, not invented
here: "programmable_substrate" (a reconfigurable unicell_super_v1 "super
carrier" shell, its own behavior chosen at ICM-load time, genuinely part
of the user-programmable field), "host_interface" (#293's own fourth
category -- no cardinal ports, bridges to something outside the fabric,
"used sparingly"), or "connection_point" (everything else -- fixed
behavior baked in at synthesis time, never reprogrammed).

Usage:
    python3 shape_extract_v1.py <verilog_file> --card-id <id> [--top <module_name>]
"""
import argparse
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

# Cardinal-direction port name patterns, matching this project's own
# real, consistent naming convention throughout unicell_super_v1.v and
# every top-level built this session (data_out_n, arrived_s, fire_e,
# ack_in_w, ready_in_n, ...).
DIRECTION_SUFFIX_RE = re.compile(r"_(n|s|e|w)(\[\d+(:\d+)?\])?$")

# Matches: module_type [#( ... )] INSTANCE_NAME ( ... );
# DOTALL so a multi-line port list is captured in one match. Every
# group is named explicitly -- nested named groups shift positional
# indices in a way that's easy to get wrong (caught directly by
# testing against real output before trusting this, not assumed
# correct from reading the pattern alone).
#
# The leading negative lookahead is load-bearing, not decorative: a
# post-hoc filter on the matched keyword is NOT enough on its own,
# because re.finditer's next search position still starts from
# wherever a REJECTED match ended -- if `else if (h1_arrived_n)
# h1_fresh <= 1'b1;` is allowed to match at all (module_type='else',
# instance_name='if'), its own match span can extend far enough
# forward to swallow a real instantiation sitting just after it,
# silently dropping it from the output. Confirmed directly: this
# exact case dropped `SENT1` from a real extraction run before this
# fix was added. The lookahead stops the match from ever starting at
# a keyword, so the engine's scan simply continues past it instead.
_KEYWORD_ALT = "|".join([
    "if", "else", "always", "assign", "begin", "end", "case",
    "function", "task", "wire", "reg", "localparam", "parameter",
    "module", "endmodule", "generate", "for", "while", "default",
    "initial", "endfunction", "endtask", "endcase", "endgenerate",
])
INSTANCE_RE = re.compile(
    rf"^\s*(?!(?:{_KEYWORD_ALT})\b)"
    r"(?P<module_type>\w+)\s*(?:#\s*\((?P<params>.*?)\))?\s+"
    r"(?P<instance_name>\w+)\s*\((?P<ports>.*?)\)\s*;",
    re.MULTILINE | re.DOTALL,
)

# Matches one .port(expr) pair inside a port list. Handles one level of
# nested parens (e.g. a concatenation used as an argument) but does not
# attempt to fully resolve concatenations/bit-selects as connections --
# those are recorded as "unresolved", not guessed at.
PORT_CONN_RE = re.compile(r"\.(\w+)\s*\(((?:[^()]|\([^()]*\))*)\)")

CELL_ID_RE = re.compile(r"\.CELL_ID\s*\(\s*(16'h[0-9A-Fa-f]+|\d+)\s*\)")

# Verilog keywords/constructs that occasionally match the instance
# pattern loosely but are not real module instantiations.
NOT_A_MODULE = {"if", "else", "always", "assign", "begin", "end", "case",
                 "function", "task", "wire", "reg", "localparam",
                 "parameter", "module", "endmodule", "generate",
                 "for", "while", "default", "initial", "endfunction",
                 "endtask", "endcase", "endgenerate"}

# Nets that are structural/global infrastructure, not point-to-point
# data adjacency, even though they legitimately fan out to many ports.
INFRA_NET_NAMES = {"clk", "rst"}

# ── Cell-role classification, per #253 (SHELL/CORE/ADDON) and #293
# (the fourth category, HOST-INTERFACE), not a fresh taxonomy invented
# for this tool. Alan's own question, decoded: does the loader need to
# know not just WHICH cell this is, but WHAT KIND -- a reconfigurable
# "super carrier" (SHELL+swappable-CORE+ADDON, its own behavior chosen
# at ICM-load time via core_select, genuinely part of the user-
# programmable field) versus a fixed CONNECTION POINT (behavior baked
# in at synthesis time, never reprogrammed -- #427's own "dedicated,
# one-time infrastructure" principle). HOST-INTERFACE (#293: no
# cardinal ports, doesn't join the fabric mesh, bridges to something
# OUTSIDE it, "used sparingly" per its own real recompile cost) is kept
# as its own distinct sub-category rather than flattened into
# `connection_point` -- collapsing it would lose a real, already-
# decided architectural distinction. ──
PROGRAMMABLE_SUBSTRATE_TYPES = {"unicell_super_v1"}
HOST_INTERFACE_TYPES = {
    "host_bridge_bram_icm_v1", "host_bridge_sentinel_gather_v1",
    "sentinel_issp_bridge_v1", "unicell_issp_bridge",
}


def classify_role(module_type: str) -> str:
    if module_type in PROGRAMMABLE_SUBSTRATE_TYPES:
        return "programmable_substrate"
    if module_type in HOST_INTERFACE_TYPES:
        return "host_interface"
    return "connection_point"


def is_simple_identifier(expr: str) -> bool:
    """True if expr is a bare identifier or identifier[bit-select] --
    the only forms this tool resolves into a real net-based edge."""
    return re.fullmatch(r"\w+(\[\d+(:\d+)?\])?", expr.strip()) is not None


def base_net_name(expr: str) -> str:
    return re.match(r"\w+", expr.strip()).group(0)


def direction_of(port_name: str) -> str | None:
    m = DIRECTION_SUFFIX_RE.search(port_name)
    return m.group(1).upper() if m else None


def parse_instances(rtl_text: str):
    """Real extraction pass over one top-level file's own instantiations."""
    instances = []
    for m in INSTANCE_RE.finditer(rtl_text):
        module_type = m.group("module_type")
        instance_name = m.group("instance_name")
        if module_type in NOT_A_MODULE or instance_name in NOT_A_MODULE:
            continue
        params_text = m.group("params") or ""
        ports_text = m.group("ports")
        # Real instantiations in this project's own RTL always use named
        # port connections exclusively (.port(net), never positional).
        # A construct like `if (expr) stmt;` has NO leading '.', so this
        # single check catches the whole class of control-flow false
        # matches directly, rather than trying to enumerate every
        # possible keyword up front.
        if not ports_text.lstrip().startswith("."):
            continue

        cell_id = None
        cid_match = CELL_ID_RE.search(params_text)
        if cid_match:
            cell_id = cid_match.group(1)

        ports = {}
        for pm in PORT_CONN_RE.finditer(ports_text):
            port_name, expr = pm.group(1), pm.group(2).strip()
            ports[port_name] = expr

        instances.append({
            "instance": instance_name,
            "module_type": module_type,
            "cell_id": cell_id,
            "role": classify_role(module_type),
            "ports": ports,
        })
    return instances


def build_net_map(instances):
    """net_base_name -> [(instance, port, direction), ...]"""
    net_map = {}
    unresolved = []
    for inst in instances:
        for port_name, expr in inst["ports"].items():
            if not is_simple_identifier(expr):
                unresolved.append({"instance": inst["instance"], "port": port_name, "expr": expr})
                continue
            net = base_net_name(expr)
            net_map.setdefault(net, []).append(
                (inst["instance"], port_name, direction_of(port_name))
            )
    return net_map, unresolved


def build_edges(net_map):
    """A net connecting EXACTLY two distinct instance ports is a real,
    confident point-to-point structural edge. Infra nets (clk/rst) and
    any net touching >2 ports (or the same instance twice, e.g. a
    self-loop through an intermediate wire) are excluded here, not
    guessed at -- recorded separately as fan-out/infra nets instead."""
    edges = []
    fanout_nets = {}
    for net, uses in net_map.items():
        if net in INFRA_NET_NAMES:
            continue
        distinct_instances = {u[0] for u in uses}
        if len(uses) == 2 and len(distinct_instances) == 2:
            (inst_a, port_a, dir_a), (inst_b, port_b, dir_b) = uses
            edges.append({
                "net": net,
                "from": {"instance": inst_a, "port": port_a, "direction": dir_a},
                "to": {"instance": inst_b, "port": port_b, "direction": dir_b},
            })
        else:
            fanout_nets[net] = uses
    return edges, fanout_nets


def find_boundary_cells(instances, edges, set_piece_types):
    """Any instance with a real edge directly touching a fixed set-piece
    module type (e.g. bram_controller_v1) is a boundary cell -- exactly
    #431's own "which cells border the set-piece's own connection
    points" question, answered directly from the real edge list rather
    than assumed."""
    set_piece_instances = {i["instance"] for i in instances if i["module_type"] in set_piece_types}
    boundary = {}
    for e in edges:
        a, b = e["from"]["instance"], e["to"]["instance"]
        if a in set_piece_instances and b not in set_piece_instances:
            boundary.setdefault(a, set()).add(b)
        elif b in set_piece_instances and a not in set_piece_instances:
            boundary.setdefault(b, set()).add(a)
    return {k: sorted(v) for k, v in boundary.items()}


def git_commit_hash(repo_root: Path) -> str | None:
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=repo_root,
                              capture_output=True, text=True, timeout=5)
        return out.stdout.strip() if out.returncode == 0 else None
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("verilog_file")
    ap.add_argument("--card-id", required=True, help="matches a MAN file's own card_id")
    ap.add_argument("--top", default=None, help="top-level module name, for the output metadata only")
    ap.add_argument("--set-piece-types", default="bram_controller_v1",
                     help="comma-separated module types treated as fixed set-pieces for boundary-cell detection")
    ap.add_argument("-o", "--output", default=None)
    args = ap.parse_args()

    rtl_path = Path(args.verilog_file)
    rtl_text = rtl_path.read_text()

    instances = parse_instances(rtl_text)
    net_map, unresolved = build_net_map(instances)
    edges, fanout_nets = build_edges(net_map)
    set_piece_types = {t.strip() for t in args.set_piece_types.split(",") if t.strip()}
    boundary_cells = find_boundary_cells(instances, edges, set_piece_types)

    repo_root = rtl_path.resolve().parents[2] if len(rtl_path.resolve().parents) >= 2 else rtl_path.resolve().parent
    commit = git_commit_hash(repo_root)

    shape = {
        "shape_version": "1.0",
        "card_id": args.card_id,
        "generated": datetime.date.today().isoformat(),
        "source_file": str(rtl_path),
        "top_module": args.top or rtl_path.stem,
        "git_commit": commit,
        "cells": [
            {"instance": i["instance"], "module_type": i["module_type"],
             "cell_id": i["cell_id"], "role": i["role"]}
            for i in instances
        ],
        "role_summary": {
            role: sorted(i["instance"] for i in instances if i["role"] == role)
            for role in sorted({i["role"] for i in instances})
        },
        "edges": edges,
        "boundary_cells": boundary_cells,
        "set_piece_types": sorted(set_piece_types),
        "unresolved_ports": unresolved,
        "fanout_nets": {k: [{"instance": u[0], "port": u[1], "direction": u[2]} for u in v]
                         for k, v in fanout_nets.items()},
    }

    out_text = json.dumps(shape, indent=2)
    if args.output:
        Path(args.output).write_text(out_text)
        print(f"Wrote {args.output}", file=sys.stderr)
    else:
        print(out_text)


if __name__ == "__main__":
    main()
