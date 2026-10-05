#!/usr/bin/env python3
"""
flexsub_icm_flex_v1.py -- the FLEX family emitter for `--icm` (Alan, 4 Oct 2026: "the flex side ... hopefully this will be slightly easier as it has
the ack side, which is in the nano version"). Reached through project_assemble_v1.py:   -s flex --icm FILE.icm --output DIR

THE FLEX HANDSHAKE (read from adder_cell_v4sa.v / ram_cell_v4sa.v, not assumed):
  capture : an edge where valid_in is high and the cell is not `pending` (that is its `ack_out`, "ready"): it registers the result and sets `pending`
  offer   : valid_out = pending, data_out = out_buffer, HELD until ack_in is high at an edge (ack_in = the downstream's READY level)
  So a TRANSFER is an edge where the source's valid_out and the consumer's ready are both high; a cell cannot capture in the cycle it releases (one item
  per two cycles). Because a handshake absorbs any difference in arrival time, NO latency alignment and NO padding is needed (unlike sub).

WHAT THE EMITTER BUILDS (all of it plain valid/ready glue around the cells):
  * entries/exits -- the top level has a handshake on every port: in_<n>_data/_valid and an OUTPUT in_<n>_ack (ready); out_<n>_data/_valid and an INPUT out_<n>_ack
  * single consumer -- the source's ack_in is the consumer's ready; valid goes straight across
  * FAN-OUT (the "ack join", Alan #924) -- an EAGER FORK: one flop per consumer, `taken`, set when that consumer has accepted the item; valid to a consumer is
    valid & ~taken; the source's ack_in is high only when every consumer has taken it (this cycle or before), then all flags clear. The flops are what make it
    safe: a purely combinational "all ready at once" fork forms a combinational LOOP in a diamond (two sources each feeding two adders).
  * two-operand join (adder, mul) -- valid_in = vA & vB; ack to A = ready & vB; ack to B = ready & vA, so both sources transfer exactly when the cell captures.
  * add-on chains (mask/shift/invert) -- pure wiring on the data, as on sub (valid and handshake untouched).

  * CONSTANTS (stage 2) -- a constant source (a ram with preload_value or fixed_mode) is a FIXED-MODE ram: valid_out = armed (always valid once configured), always ready,
    data loaded from cfg_data at configuration. It is offered to every consumer with NO fork and NO ack (it is never "used up"), and a join that includes one simply
    waits for the live operand. A cell fed only by constants is an ordinary cell that keeps re-capturing. An OUTPUT that depends only on constants is refused:
    nothing live would pace it.

  * NANO (stage 3) -- the first core whose two operands are NOT symmetric. nano_cell_v4sa has a HELD operand A that is only a LOAD STROBE (`load_hold` overwrites the
    held register on any edge, with NO handshake and regardless of `pending`) and a FLOWING operand B on the ordinary valid/ready; the gate reads the held register's
    CURRENT value at capture, so a hold loaded on the same edge is not yet visible (the "A one cycle before B" rule, #932). One flag per nano, `aload` = "A is loaded
    for the current pair": A's ready is `~aload & armed` and the load is `vA & ready` (allowed while the previous result is still pending, so the next pair's setup
    overlaps the drain); B's ready is `aload & ack_out`, and its capture clears `aload`. `armed` = ack_out | valid_out. Arrival ORDER no longer matters: a B that comes
    first just waits -- which is why a handshake design needs none of sub's padding.

  * COMPARATOR (stage 4) -- compare_cell_v4sa is a single-input cell (signed(data) >= threshold -> 0/1, threshold in cfg_data), so its handshake is exactly a relay's.

  * ACCUMULATOR and LATCH (stage 5, the LEVEL SOURCES). Their pulse inputs (inc/dec, set/clear/toggle) are bare strobes with NO handshake, and in the cells the total / state
    ALWAYS updates on a pulse while the output snapshot (`out_buffer`) is captured only when the cell is not `pending` -- so a pulse landing while pending is counted but its
    snapshot is silently LOST and data_out goes stale. The emitter therefore GATES every pulse by the cell's ready: a pulse is `source valid & ack_out` and the source is acked at
    that same moment, so every event is both counted and snapshotted and data_out always equals the true total. Several sources on one role OR together (one event, all acked);
    a latch `set` also needs bit 0 of the arriving value (the value is consumed either way, as in the VM). LEVEL mode (a continuous accumulator, any latch -- g.is_level): valid is
    held high once armed (`ack_out | valid_out`), the cell's own ack_in is tied high so it never stalls, and consumers never ack it (the #938 rule, for a handshake design). A
    PULSE-MODE accumulator is an ordinary event source (fork, acks) but still pulse-gated. A level/constant source into an accumulator's inc/dec or a latch's toggle is refused
    (rate-dependent), exactly as on sub.

  * BRANCH (stage 6). branch_cell_v4sa has TWO output ports, each with its own valid/ack but sharing one out_buffer -- so each port is a separate SOURCE with its own eager fork
    (named <cell>_p1 / <cell>_p2); an outcome routed to neither port is swallowed (no output). Inputs: a FIXED input is a LOAD STROBE (loads whenever its valid is high, regardless of
    busy, like the nano's hold) so its source is acked at once; a FLOWING input is valid/ready with the single ack_out (low while either port is pending), and two flowing inputs form
    a join. The ICM branch's three input modes (lowered by lower_branches, shared with sub): const_ref -- the stream is in1, the constant is in2 (flowing, valid always high), the stream
    is acked only when the cell fires; ENTRY variant -- the branch absorbed the merge that carried the io_name, so it IS the entry point (cordic's z_input); ROLLING -- the stream feeds
    both inputs with in2 held. Rolling needs a glue flag the pulse-fed sub cell did not: a handshake stream's valid is HELD, so the first arrival (no reference yet, no output in the VM)
    would stay valid and one cycle later fire against the reference it just loaded -- a spurious EQUAL event. So: the first arrival only LOADS (in2 strobe, stream acked at once, flag set);
    later arrivals load and compare on the SAME edge (so the compare reads the OLD reference), acked only when the cell is ready.

  * MERGE (stage 7, a CORE). Several sources feeding one input. The first version was arbiter GLUE emitted into the top level; Alan's ruling is that the system is built from KNOWN
    core designs and arbitrary hand-woven glue at particular points goes against that, so the merge is a core: merge_cell_v4sa, with its own bench and mutation checks, four selectable
    modes (0 A only, 1 B only, 2 ARBITRATE round-robin, 3 JOIN-OR = wait for both then OR). The emitter inserts one in front of each merge's consumer (a small graph rewrite; the
    existing fork/edge machinery then treats it as just another cell). Why not the VM's plain OR: under a handshake two sources can both stay valid while a cell is busy, so an OR would
    fuse two separate items into one corrupt value. Default mode is ARBITRATE (right when the paths are alternatives, e.g. a branch's two outcomes rejoining -- the cordic's `gather`);
    `merge_mode="join-or"` is for two paths that are HALVES of one item to be combined (the "free OR" used as a feature -- now deterministic). Two sources only; a merge including a
    constant is refused by the planner. ORDER: no cell can restore the order of items between two paths (it would need per-item tags), so an arbitrating merge is only well-defined
    with at most one item in flight in its region.

  * SEQUENCER (stage 8). An internal free-running source paced by the consumer's ack; sequencer_cell_v4sa still advances only on advance_in (the ack merely stops it advancing while an offer is
    pending), so advance_in is tied to the cell's own READY and the stored values are rotated one step. A sequencer into a two-operand cell pairs ONE value per stream item (item k with
    VALUE_(k mod n)) -- deliberate and deterministic, and DIFFERENT from the VM, whose arrival-paired adder pairs the sequence with ITSELF (#937). Recorded as a test.

STAGES 1-8 SCOPE (everything else is refused by plan(family="flex") with its reason, never silently mistranslated): ram, adder, mul, nano, comparator, accumulator, latch, branch,
two-source merges (as a core), the sequencer and constants -- every ICM core the planner translates (a genuine `priority` arbiter, not the compiler's eliminated ones, is the one left). Operand identity (A vs B) comes from the same rules as sub (ranks, then arrival-order estimate).
"""
import json
import os
import re
import shutil
import sys

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS_DIR)
import flexsub_assemble_v1 as fsa  # noqa: E402
import flexsub_icm_generate_v1 as g  # noqa: E402

FLEX_MODULES = {"ram": "ram_cell_v4sa", "adder": "adder_cell_v4sa", "mul": "mul_cell_v4sa", "nano": "nano_cell_v4sa", "comparator": "compare_cell_v4sa", "accumulator": "accumulator_cell_v4sa", "latch": "latch_cell_v4sa", "branch": "branch_cell_v4sa", "merge": "merge_cell_v4sa", "sequencer": "sequencer_cell_v4sa"}


def _pname(io, cid):
    return re.sub(r"[^A-Za-z0-9_]", "_", io or cid)


def emit_top_flex(top, p, merge_mode="arbitrate"):
    cells, inputs, roles = p["cells"], p["inputs"], p["adder_roles"]
    branch_plans, branch_port = p["branch_plans"], p["branch_port"]
    order, exits_l, addons = p["order"], list(p["exits"]), p["addons"]
    mode_code = {"arbitrate": 2, "join-or": 3}[merge_mode]
    merge_cells = {}
    if p["merges"]:
        # Each ICM merge (several sources into one input) becomes a real merge CORE in front of its consumer: a graph rewrite, so the fork / edge / ack machinery below
        # treats it as just another cell.
        cells, inputs, roles, order, branch_port = dict(cells), {k: dict(v) for k, v in inputs.items()}, dict(roles), list(order), dict(branch_port)
        for dst, srcs in p["merges"].items():
            if len(srcs) != 2:
                raise g.IcmGenError(f"{dst}: a merge of {len(srcs)} sources is not translated on flex (the merge core has two inputs)")
            mid = f"{dst}.merge"
            flat = [(q, f) for lst in inputs[dst].values() for q, f in lst]
            cells[mid] = type(cells[dst])(cell_id=mid, row=cells[dst].row, col=cells[dst].col, core="merge", core_config={})
            inputs[mid] = {"in": flat[:2]}
            inputs[dst] = {"in": [(mid, flat[0][1])]}
            roles[mid] = {"A": flat[0][0], "B": flat[1][0]}
            order.insert(order.index(dst), mid)
            for q, _ in flat:
                if q in branch_plans:
                    branch_port[(mid, q)] = branch_port[(dst, q)]
            merge_cells[mid] = [q for q, _ in flat]
    exits = set(exits_l)
    idx = {c: k for k, c in enumerate(order)}
    ident = g._ident
    const = p["const"]
    roots = {c for c in const if not inputs.get(c)}                 # constant SOURCES (rams with preload_value / fixed_mode)
    entries = [c for c in order if not inputs.get(c) and c not in roots and cells[c].core != "sequencer"]
    L = []
    a = L.append
    a(f"// {top}.v -- GENERATED by tools/flexsub_icm_flex_v1.py (-s flex --icm); do not hand-edit.")
    a(f"// Source ICM: {p['doc'].name or '(unnamed)'}; {len(cells)} cells. FLEX family: every cell is a valid/ready (ack) cell; fan-out is an eager fork,")
    a("// a two-operand cell is a join. No latency alignment and no padding: the handshake absorbs differences in arrival time.")
    a("`default_nettype none")
    a("`timescale 1ns / 1ps")
    a(f"module {top} (")
    a("    input  wire clk,")
    a("    input  wire rst,")
    a("    input  wire cfg_valid,")
    ports = []
    for c in entries:
        n = _pname(cells[c].io_name, c)
        ports += [f"    input  wire [31:0] in_{n}_data", f"    input  wire        in_{n}_valid", f"    output wire        in_{n}_ack"]
    for c in exits_l:
        n = _pname(cells[c].io_name, c)
        ports += [f"    output wire [31:0] out_{n}_data", f"    output wire        out_{n}_valid", f"    input  wire        out_{n}_ack"]
    a(",\n".join(ports))
    a(");")

    # ---- edges: one per (source -> consumer slot) ----
    levels = {c for c in cells if g.is_level(cells[c])}             # always-valid sources: a continuous accumulator, any latch
    edges, cons, by_dst, edge_role = [], {c: [] for c in order}, {c: [] for c in order}, {}
    for c in branch_plans:                                           # a branch's two output ports are two separate sources
        cons[(c, 1)], cons[(c, 2)] = [], []
    for dst in order:
        r = cells[dst]
        rl = []
        if r.core in ("adder", "mul", "nano", "merge"):
            srcs = [roles[dst]["A"], roles[dst]["B"]]
        elif r.core in ("accumulator", "latch"):
            srcs = [q for role in sorted(inputs.get(dst, {})) for q, _ in inputs[dst][role]]
            rl = [role for role in sorted(inputs.get(dst, {})) for _ in inputs[dst][role]]
        else:
            srcs = [q for lst in inputs.get(dst, {}).values() for q, _ in lst]
        for slot, src in enumerate(srcs):
            e = f"e{len(edges)}"
            if rl:
                edge_role[e] = rl[slot]
            edges.append((e, src, dst, slot))
            cons[(src, branch_port[(dst, src)]) if src in branch_plans else src].append(e)
            by_dst[dst].append(e)
    for c in order:
        i = ident(c)
        a(f"wire [31:0] {i}_d; wire {i}_v; wire {i}_rdy; wire {i}_ai; wire {i}_vin;")
        if c in addons:
            a(f"wire [31:0] {i}_rd;")
        if c in branch_plans:
            a(f"wire {i}_p1_v, {i}_p1_ai, {i}_p2_v, {i}_p2_ai; wire [31:0] {i}_d2u;")
        if c in merge_cells:
            a(f"wire {i}_rdya, {i}_rdyb;")
    for e, *_ in edges:
        a(f"wire {e}_v; wire {e}_a;")
    a("")

    forks, joins = [], []
    # ---- source side: how each cell's valid_out is offered to its consumers, and where its ack_in comes from ----
    sources = []
    for c in order:
        if c in branch_plans:
            if c in exits:
                raise g.IcmGenError(f"{c}: a branch as a design OUTPUT is not translated on flex (stage 6)")
            sources += [((c, 1), f"{ident(c)}_p1"), ((c, 2), f"{ident(c)}_p2")]
        else:
            sources.append((c, ident(c)))
    for key, i in sources:
        src = key[0] if isinstance(key, tuple) else key
        es = cons[key]
        if src in levels:
            if src in exits:
                n = _pname(cells[src].io_name, src)
                a(f"assign out_{n}_data = {i}_d;")
                a(f"assign out_{n}_valid = {i}_rdy | {i}_v;           // a level is always valid once armed; the host's ack is ignored")
            for e in es:
                a(f"assign {e}_v = {i}_rdy | {i}_v;                  // LEVEL source: always valid, never 'used up': no fork, no ack")
            a(f"assign {i}_ai = 1'b1;                                // the cell's own pending clears at once (consumers do not ack a level)")
            continue
        if src in roots:
            if src in exits:
                raise g.IcmGenError(f"{src}: an output that is only a constant")
            for e in es:
                a(f"assign {e}_v = {i}_v;                  // a constant is always valid and is never 'used up': no fork, no ack")
            a(f"assign {i}_ai = 1'b1;")
            continue
        if src in exits:
            n = _pname(cells[src].io_name, src)
            if es:
                raise g.IcmGenError(f"{src}: an output cell that also feeds other cells is not translated on flex (stage 1)")
            a(f"assign {i}_ai = out_{n}_ack;")
            a(f"assign out_{n}_data = {i}_d;")
            a(f"assign out_{n}_valid = {i}_v;")
        elif not es:
            a(f"assign {i}_ai = 1'b1;   // nothing downstream")
        elif len(es) == 1:
            a(f"assign {es[0]}_v = {i}_v;")
            a(f"assign {i}_ai = {es[0]}_a;")
        else:
            forks.append({"source": i if isinstance(key, tuple) else src, "consumers": len(es)})
            for e in es:
                a(f"reg {e}_t = 1'b0;                       // `taken`: this consumer has accepted the current item")
                a(f"assign {e}_v = {i}_v & ~{e}_t;")
                a(f"wire {e}_acc = {e}_v & {e}_a;")
            a(f"wire {i}_done = {i}_v & " + " & ".join(f"({e}_t | {e}_acc)" for e in es) + ";   // every consumer has taken it")
            a(f"assign {i}_ai = {i}_done;")
            clr = " ".join(f"{e}_t <= 1'b0;" for e in es)
            upd = " ".join(f"{e}_t <= {e}_t | {e}_acc;" for e in es)
            a(f"always @(posedge clk) begin if (rst) begin {clr} end else if ({i}_done) begin {clr} end else begin {upd} end end   // eager fork of {src}")
    a("")

    # ---- consumer side: how each cell's valid_in is formed and what ready each source sees ----
    for dst in order:
        i, es, r = ident(dst), by_dst[dst], cells[dst]
        if r.core == "sequencer":                                   # an INTERNAL source (not a host entry): nothing feeds it
            a(f"assign {i}_vin = 1'b0;")
            continue
        if r.core == "branch":
            bp, rd = branch_plans[dst], f"{i}_rdy"
            if bp["stream"] is None:                                  # the branch absorbed the merge that carried the io_name: it IS the entry point
                n = _pname(r.io_name, dst)
                sv, sd, sack = f"in_{n}_valid", f"in_{n}_data", f"in_{n}_ack"
            else:
                (e_s,) = es
                sv, sd, sack = f"{e_s}_v", ident(edges[int(e_s[1:])][1]) + "_d", f"{e_s}_a"
            joins.append({"cell": dst, "kind": f"branch ({bp['mode']})"})
            if bp["mode"] == "const_ref":
                k = ident(bp["const_ref"])
                a(f"assign {sack} = {rd} & {k}_v;                          // the stream is consumed when the cell fires, and needs the constant reference present")
                a(f"wire {i}_in1v = {sv}, {i}_in2v = {k}_v; wire [31:0] {i}_in1d = {sd}, {i}_in2d = {k}_d;")
                bp_in2_fixed = 0
            else:                                                     # rolling: the stream feeds both inputs, in2 is a HELD copy
                a(f"reg {i}_ld = 1'b0;                                    // the reference has been loaded")
                a(f"wire {i}_first = {sv} & ~{i}_ld;                      // the first arrival only becomes the reference: no event, no output (VM)")
                a(f"wire {i}_fire = {sv} & {i}_ld & {rd};                 // later arrivals load AND compare on the same edge (the compare reads the OLD reference)")
                a(f"assign {sack} = ~{i}_ld | {rd};")
                a(f"always @(posedge clk) begin if (rst) {i}_ld <= 1'b0; else if ({i}_first) {i}_ld <= 1'b1; end")
                a(f"wire {i}_in1v = {i}_fire, {i}_in2v = {i}_fire | {i}_first; wire [31:0] {i}_in1d = {sd}, {i}_in2d = {sd};")
                bp_in2_fixed = 1
            bp["_in2_fixed"] = bp_in2_fixed
            continue
        if dst in roots:
            a(f"assign {i}_vin = 1'b0;")
            a(f"wire [31:0] {i}_ind = 32'h0;")
            continue
        if not es:                                                  # an entry: the host drives it through the top-level handshake
            n = _pname(r.io_name, dst)
            a(f"assign {i}_vin = in_{n}_valid;")
            a(f"assign in_{n}_ack = {i}_rdy;")
            a(f"wire [31:0] {i}_ind = in_{n}_data;")
            continue
        srcdata = {e: ident(s) + "_d" for e, s, d, _ in edges if d == dst}
        if r.core == "nano":
            eA, eB = es                                               # slot order is [A (held), B (flowing)] from the plan's operand identity
            joins.append({"cell": dst, "kind": "nano hold/flow"})
            a(f"reg {i}_aload = 1'b0;                                  // A has been loaded for the current pair")
            a(f"wire {i}_armed = {i}_rdy | {i}_v;                      // armed = ack_out | valid_out (ack_out = armed & ~pending, valid_out = pending)")
            a(f"wire {i}_ldA = {eA}_v & ~{i}_aload & {i}_armed;        // load strobe for the held operand")
            a(f"wire {i}_cap = {eB}_v & {i}_aload & {i}_rdy;           // the flowing operand is captured")
            a(f"assign {eA}_a = ~{i}_aload & {i}_armed;")
            a(f"assign {eB}_a = {i}_aload & {i}_rdy;")
            a(f"assign {i}_vin = {eB}_v & {i}_aload;")
            a(f"always @(posedge clk) begin if (rst) {i}_aload <= 1'b0; else if ({i}_cap) {i}_aload <= 1'b0; else if ({i}_ldA) {i}_aload <= 1'b1; end")
            a(f"wire [31:0] {i}_inh = {srcdata[eA]}, {i}_inf = {srcdata[eB]};")
        elif r.core == "merge":
            eA, eB = es
            joins.append({"cell": dst, "kind": f"merge core ({merge_mode})", "sources": merge_cells[dst]})
            a(f"assign {i}_vin = 1'b0;")
            a(f"assign {eA}_a = {i}_rdya;                              // the CORE arbitrates / joins; here the two inputs are simply connected")
            a(f"assign {eB}_a = {i}_rdyb;")
            a(f"wire [31:0] {i}_ina = {srcdata[eA]}, {i}_inb = {srcdata[eB]};")
        elif r.core in ("accumulator", "latch"):
            joins.append({"cell": dst, "kind": f"{r.core} pulse inputs"})
            byrole = {}
            for e in es:
                byrole.setdefault(edge_role[e], []).append(e)
            a(f"assign {i}_vin = 1'b0;")
            for role in sorted(byrole):
                for e in byrole[role]:
                    a(f"assign {e}_a = {i}_rdy;   // a pulse is accepted only when the cell can SNAPSHOT it, so no event is ever counted but lost")
            for role in ("inc", "dec", "set", "clear", "toggle"):
                if r.core == "accumulator" and role in ("set", "clear", "toggle") or r.core == "latch" and role in ("inc", "dec"):
                    continue
                terms = [(f"({e}_v & {srcdata[e]}[0])" if (r.core == "latch" and role == "set") else f"{e}_v") for e in byrole.get(role, [])]
                a(f"wire {i}_p_{role} = ({' | '.join(terms) if terms else chr(49) + chr(39) + 'b0'}) & {i}_rdy;")
        elif r.core in ("adder", "mul"):
            eA, eB = es
            joins.append({"cell": dst})
            a(f"assign {i}_vin = {eA}_v & {eB}_v;      // join: both operands must be present")
            a(f"assign {eA}_a = {i}_rdy & {eB}_v;")
            a(f"assign {eB}_a = {i}_rdy & {eA}_v;")
            a(f"wire [31:0] {i}_ina = {srcdata[eA]}, {i}_inb = {srcdata[eB]};")
        else:
            (e,) = es
            a(f"assign {i}_vin = {e}_v;")
            a(f"assign {e}_a = {i}_rdy;")
            a(f"wire [31:0] {i}_ind = {srcdata[e]};")
    a("")

    # ---- the cells ----
    for c in order:
        r, i = cells[c], ident(c)
        cfg = r.core_config or {}
        mod = FLEX_MODULES[r.core]
        dout = f"{i}_rd" if c in addons else f"{i}_d"
        common = (f".clk(clk), .rst(rst), .freeze_in(1'b0), .cfg_valid(cfg_valid), .ack_out({i}_rdy), .data_out({dout}), "
                  f".valid_out({i}_v), .ack_in({i}_ai)")
        if r.core == "branch":
            bp = branch_plans[c]
            rb = bp["route_bits"]
            word = (bp["_in2_fixed"] << 1) | (bp["emit_source"] << 2) | (rb["low"] << 4) | (rb["equal"] << 6) | (rb["high"] << 8)
            a(f"{mod} #(.CELL_ID(16'd{idx[c]})) {i} (.clk(clk), .rst(rst), .freeze_in(1'b0), .cfg_valid(cfg_valid), .cfg_data(32'h{word:X}), "
              f".cfg_emit_fixed_value(32'h{bp['emit_fixed'] & 0xFFFFFFFF:08X}), .in1_data({i}_in1d), .in1_valid({i}_in1v), .in2_data({i}_in2d), .in2_valid({i}_in2v), "
              f".ack_out({i}_rdy), .data_out_1({dout}), .valid_out_1({i}_p1_v), .ack_in_1({i}_p1_ai), .data_out_2({i}_d2u), .valid_out_2({i}_p2_v), .ack_in_2({i}_p2_ai));")
        elif r.core == "merge":
            eA, eB = by_dst[c]
            a(f"{mod} #(.CELL_ID(16'd{idx[c]})) {i} (.clk(clk), .rst(rst), .freeze_in(1'b0), .cfg_valid(cfg_valid), .cfg_data(32'h{mode_code}), .in_a({i}_ina), .valid_in_a({eA}_v), "
              f".ack_out_a({i}_rdya), .in_b({i}_inb), .valid_in_b({eB}_v), .ack_out_b({i}_rdyb), .data_out({dout}), .valid_out({i}_v), .ack_in({i}_ai));   // mode {mode_code}: {merge_mode}")
        elif r.core == "ram" and c in roots:
            val = (r.preload_value if r.preload_value is not None else cfg.get("init_data", 0)) & 0xFFFFFFFF
            a(f"{mod} #(.CELL_ID(16'd{idx[c]})) {i} ({common}, .cfg_data(32'h{val:08X}), .cfg_fixed_mode(1'b1), .data_in({i}_ind), .valid_in({i}_vin));   // CONSTANT {val}")
        elif r.core == "ram":
            fm = 1 if cfg.get("fixed_mode", 0) else 0
            a(f"{mod} #(.CELL_ID(16'd{idx[c]})) {i} ({common}, .cfg_data(32'h0), .cfg_fixed_mode(1'b{fm}), .data_in({i}_ind), .valid_in({i}_vin));")
        elif r.core == "sequencer":
            # Free-running, paced by the CONSUMER's ack (Alan: the consumer clears, the sequencer sees it, switches to the next value and waits). advance_in is tied to the cell's own
            # READY (armed & not pending), so it offers a new value whenever the previous one has been taken -- the VM's "advance when drained". The cell pulses the NEXT index's value, so the
            # stored values are rotated one step (new[j] = V[(j-1) mod n]) and the sequence starts at VALUE_0 and wraps like the VM's -- exactly as on sub (#937).
            vals = [int(cfg.get(f"VALUE_{k}", 0)) & 0xFF for k in range(4)]
            len_m1 = int(cfg.get("SEQUENCE_LEN", 0)) & 3
            n_vals = len_m1 + 1
            rot = [vals[(j - 1) % n_vals] if j < n_vals else 0 for j in range(4)]
            word = rot[0] | (rot[1] << 8) | (rot[2] << 16) | (rot[3] << 24)
            a(f"{mod} #(.CELL_ID(16'd{idx[c]})) {i} ({common}, .cfg_data(32'h{word:08X}), .cfg_seq_len_m1(2'd{len_m1}), .advance_in({i}_rdy));   // free-running, paced by the consumer's ack")
        elif r.core == "accumulator":
            word = (int(cfg.get("step_amount", 0)) & 0xFF) | ((1 if cfg.get("pulse_mode", 0) else 0) << 8) | ((int(cfg.get("threshold", 0)) & 0xFFFF) << 9)
            a(f"{mod} #(.CELL_ID(16'd{idx[c]})) {i} ({common}, .cfg_data(32'h{word:08X}), .inc_pulse({i}_p_inc), .dec_pulse({i}_p_dec));   "
              f"// {'LEVEL (continuous)' if c in levels else 'event source (pulse mode)'}")
        elif r.core == "latch":
            a(f"{mod} #(.CELL_ID(16'd{idx[c]})) {i} ({common}, .cfg_data(32'h0), .set_in({i}_p_set), .clear_in({i}_p_clear), .toggle_in({i}_p_toggle));   // LEVEL")
        elif r.core == "comparator":
            thr = int(cfg.get("threshold", 0)) & 0xFFFFFFFF                # signed(data) >= threshold -> 0/1, exactly as the VM (a single-input cell like a relay)
            a(f"{mod} #(.CELL_ID(16'd{idx[c]})) {i} ({common}, .cfg_data(32'h{thr:08X}), .data_in({i}_ind), .valid_in({i}_vin));   // threshold {thr}")
        elif r.core == "nano":
            a(f"{mod} #(.CELL_ID(16'd{idx[c]})) {i} ({common}, .cfg_data(32'h{int(cfg.get('topology', 0)):X}), .hold_in_data({i}_inh), .load_hold({i}_ldA), "
              f".flow_in_data({i}_inf), .valid_in({i}_vin));")
        else:
            word = 1 if (r.core == "adder" and cfg.get("subtract_mode", 0)) else 0
            a(f"{mod} #(.CELL_ID(16'd{idx[c]})) {i} ({common}, .cfg_data(32'h{word}), .in_a({i}_ina), .in_b({i}_inb), .valid_in({i}_vin));")
        if c in addons:
            a(f"assign {i}_d = {g.addon_expr(addons[c], dout)};   // addon chain as pure wiring: data only; valid and the handshake are untouched")
    a("endmodule")
    return "\n".join(L) + "\n", forks, joins


def generate_flex(icm_path, output, top=None, cell_dir=None, man_path=None, nowidelut=None, merge_mode="arbitrate"):
    man = fsa.load_man_flexsub(man_path) if man_path else None
    nowidelut, nowidelut_why = fsa.resolve_nowidelut(nowidelut, man)
    p = g.plan(icm_path, True, family="flex", nowidelut=nowidelut)
    levels = {c for c in p["cells"] if g.is_level(p["cells"][c])}
    only_const = sorted(c for c in p["exits"] if c in p["const"] and c not in levels)
    if only_const:
        raise g.IcmGenError(f"cannot generate flex Verilog from {os.path.basename(icm_path)}:\n  - output(s) {only_const} depend only on constants: nothing live "
                            f"would pace them, so the design would stream the same value for ever")
    stem = re.sub(r"[^A-Za-z0-9_]", "_", os.path.basename(icm_path).split(".")[0])
    top = top or f"icm_{stem}_flex"
    cell_dir = cell_dir or fsa.DEFAULT_CELL_DIR
    os.makedirs(output, exist_ok=True)
    text, forks, joins = emit_top_flex(top, p, merge_mode)
    top_path = os.path.join(output, f"{top}.v")
    open(top_path, "w").write(text)
    dep_pairs = fsa._derive_deps(top_path, cell_dir)
    for fname, src in dep_pairs:
        shutil.copy2(os.path.join(src, fname), os.path.join(output, fname))
    files = [f"{top}.v"] + [f for f, _ in dep_pairs]
    open(os.path.join(output, f"{top}.ys"), "w").write(
        f"read_verilog -sv {' '.join(files)}\nhierarchy -top {top}\nsynth_gowin -top {top}{' -nowidelut' if nowidelut else ''} -json {top}.json\nstat\n")
    rec = {"generator": "tools/flexsub_icm_flex_v1.py", "family": "flex", "source": os.path.basename(icm_path), "top": top,
           "cells": len(p["cells"]), "forks": forks, "joins": joins, "merge_mode": merge_mode if p["merges"] else None, "merges": {m: srcs for m, srcs in p["merges"].items()}, "branches": {c: {k: v for k, v in bp.items() if not k.startswith("_")} for c, bp in p["branch_plans"].items()},
           "constants": sorted(c for c in p["const"] if not p["inputs"].get(c) and c not in levels), "level_sources": sorted(levels), "const_derived": sorted(c for c in p["const"] if p["inputs"].get(c)), "exit_rule": p["exit_rule"], "pruned_dead_cells": p["pruned"],
           "exits": list(p["exits"]), "adder_roles": p["adder_roles"], "eliminated_priority_cells": p["eliminated_priority"],
           "addon_wiring": {c: {k: v for k, v in (p["cells"][c].addon_config or {}).items() if v} for c in p["addons"]},
           "note": "handshake design: every port has valid/ack; no latency alignment, no padding", "synth_flags": "-nowidelut" if nowidelut else "(wide-LUT mapping)", "synth_flags_reason": nowidelut_why, "files": files + [f"{top}.ys"]}
    json.dump(rec, open(os.path.join(output, "ASSEMBLY.json"), "w"), indent=2)
    return rec
