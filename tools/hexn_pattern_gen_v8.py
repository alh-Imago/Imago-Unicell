"""hexn_pattern_gen_v8.py - PATTERN GENERATOR v8 (3 Nov 2026, Alan 10:07 "run through the other tiles"): v7 plus the PRIORITY tile (PR, hexn_tile_pr_v1 on hexn_prio_core_v2), the SEQUENCER tile (SQ, hexn_tile_sq_v1 on hexn_seq_core_v2) and the LATCH tile (LT, hexn_tile_lt_v1 on hexn_latch_core_v2). Faces: PR reads W, N, S (core ports 0..2; E spare), SQ is advanced by the flag lane of W, LT sets from W, clears from N, toggles from S; all send to E. v7 is untouched.
v7 text follows: PATTERN GENERATOR v7 (3 Nov 2026, Alan 09:50 "the general wipe command"): v6 on the WIPE-CAPABLE tiles and cores (clear input on every cell; hexn_tile_v3, _al_v2, _jn_v2, _br_v2, _mg_v2, hexn_rcore_flag_v3, hexn_ramhold_v1); the top's `clear` reaches every cell. v6 and earlier untouched.
v6 text follows: (3 Nov 2026): v5 plus the RAM ROUTING CELL with holds (hexn_ramhold_v1; Alan 09:50 "apply the ram side"). Every RAM position of the reference becomes a hold cell (22-bit word: route 12 + held output 3 + delay 7); program["holds"] sets the delay. v5 and earlier untouched.
v5 text follows: v4 plus the MERGE tile (MG: mode 0 A only, 1 B only, 2 arbitrate, 3 join-OR; Alan 09:36 "carry on with the merge side"). v4, v3, v2, v1 untouched.
v4 text follows: v3 plus the BRANCH tile (BR: 3-way signed compare, routes the emit word to out1 (E) and/or out2 (S); Alan 09:30 "start the branch side"). v3, v2, v1 untouched.
v3 text follows: v2 plus the JOIN tile (JN: add sub and or xor lt min max, any arrival order, two FIFO cells; Alan 09:01 order, join after AL). v2 and v1 are untouched.
v2 text follows: v1 plus the ALIGNED two-input tile (AL: add sub and or xor; Alan 09:01 approved the order AL then join). v1 is untouched.
Original v1 text follows (Alan 08:53: 'the pattern generator').
A pattern reference file (hexn-pattern-v2, tools/hexn_pattern_ref_v2.py) -> the Verilog TOP of that pattern: a ROWS x COLS grid in which every WORK position is a hexn_tile_v2 (routing cell + unary core) and every other position is a bare
routing cell with the flag lane (hexn_rcore_flag_v2). One config chain runs row-major through all positions, so the chain words have four widths (35 for a UN tile, 25 for an AL or JN tile, 66 for a BR tile, 24 for an MG tile, 12 for a routing cell).
Top module name is always `hexn_pattern_top` (one pattern per build). Ports: clk, clear, w_d / w_f (one data+flag input per row, west edge), e_d / e_f (one output per row, east edge), cfg_en, cfg_in, cfg_out. The header comment names the pattern and its ID.
SCOPE, stated plainly: work types UN (unary core), AL (aligned two-input core) and JN (join core) BR (branch core) and MG (merge core) have a tile; any other type and any RAM routing cell is REFUSED by name - no wrapper/RTL for them yet. Four faces only.
load_words(ref, program) -> the per-position config words and widths for a program (from a unit file) planned on this pattern; chain_bits(words, widths) -> the bit list, farthest position first."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import hexn_tile_cfg_v1 as C
import hexn_tile_cfg_al_v1 as CA
import hexn_tile_cfg_jn_v1 as CJ
import hexn_tile_cfg_br_v1 as CB
import hexn_tile_cfg_mg_v1 as CM
import hexn_tile_cfg_rh_v1 as CR
import hexn_tile_cfg_pr_v1 as CP
import hexn_tile_cfg_sq_v1 as CS
import hexn_tile_cfg_lt_v1 as CL

VDIR = os.path.join(ROOT, "sub", "verilog")
FILES = [os.path.join(VDIR, f) for f in ("hexn_rcore_flag_v3.v", "hexn_tile_v3.v", "hexn_unary_core_v2.v", "hexn_tile_al_v2.v", "hexn_aligned_core_v2.v", "hexn_tile_jn_v2.v", "hexn_join_core_v3.v", "hexn_tile_br_v2.v", "hexn_branch_core_v2.v", "hexn_tile_mg_v2.v", "hexn_merge_core_v2.v", "hexn_tile_pr_v1.v", "hexn_prio_core_v2.v", "hexn_tile_sq_v1.v", "hexn_seq_core_v2.v", "hexn_tile_lt_v1.v", "hexn_latch_core_v2.v", "hexn_ramhold_v1.v")]
SUPPORTED = {"UN": "hexn_tile_v3", "AL": "hexn_tile_al_v2", "JN": "hexn_tile_jn_v2", "BR": "hexn_tile_br_v2", "MG": "hexn_tile_mg_v2", "PR": "hexn_tile_pr_v1", "SQ": "hexn_tile_sq_v1", "LT": "hexn_tile_lt_v1"}
ALOPS = {"add", "sub", "and", "or", "xor"}
JNOPS = set(CJ.OPS)
BRCFG = ("route_lt", "route_eq", "route_gt", "emit", "fixed")
ROUTE_W = 12


def positions(ref):
    """-> {(r, c): 'UN' or None} for the whole grid; raises ValueError naming anything that cannot be built"""
    if ref.get("faces") != 4: raise ValueError("only four faces are supported")
    pos = {(r, c): None for r in range(ref["rows"]) for c in range(ref["cols"])}
    for rc in ref.get("ram_cells") or []: pos[tuple(rc)] = "RAM"
    for w in ref["work_cells"]:
        if w["type"] not in SUPPORTED:
            raise ValueError("work cell (%d,%d) is type %s: the tiles are UN, AL, JN, BR, MG, PR, SQ and LT only, no wrapper for %s yet" % (w["r"], w["c"], w["type"], w["type"]))
        pos[(w["r"], w["c"])] = w["type"]
    return pos


def widths_of(ref):
    pos = positions(ref)
    wd = {"UN": C.width(4), "AL": CA.width(4), "JN": CJ.width(4), "BR": CB.width(4), "MG": CM.width(4), "PR": CP.width(4), "SQ": CS.width(4), "LT": CL.width(4), "RAM": CR.width(4), None: ROUTE_W}
    return [wd[pos[(r, c)]] for r in range(ref["rows"]) for c in range(ref["cols"])]


def generate(ref):
    pos = positions(ref); R, Cn = ref["rows"], ref["cols"]
    L = ["`default_nettype none",
         "// hexn_pattern_top for pattern %s (ID %s, %dx%d, %d work tiles, %d bare routing cells), generated by tools/hexn_pattern_gen_v7.py from its reference file; do not edit." % (
             ref["name"], ref.get("pattern_id_hex", "?"), R, Cn, len(ref["work_cells"]), R * Cn - len(ref["work_cells"])),
         "module hexn_pattern_top (input wire clk, input wire clear, input wire [%d:0] w_d, input wire [%d:0] w_f, output wire [%d:0] e_d, output wire [%d:0] e_f, input wire cfg_en, input wire cfg_in, output wire cfg_out);" % ((R - 1,) * 4)]
    name = lambda r, c: "p_%d_%d" % (r, c)
    for r in range(R):
        for c in range(Cn):
            L.append("    wire [3:0] %s_d, %s_f; wire %s_i;" % ((name(r, c),) * 3))
    L.append("    wire c_in = cfg_in;")
    order = [(r, c) for r in range(R) for c in range(Cn)]
    for idx, (r, c) in enumerate(order):
        n = name(r, c)
        N = "%s_d[2]" % name(r - 1, c) if r > 0 else "1'b0"; NF = "%s_f[2]" % name(r - 1, c) if r > 0 else "1'b0"
        E = "%s_d[3]" % name(r, c + 1) if c < Cn - 1 else "1'b0"; EF = "%s_f[3]" % name(r, c + 1) if c < Cn - 1 else "1'b0"
        S = "%s_d[0]" % name(r + 1, c) if r < R - 1 else "1'b0"; SF = "%s_f[0]" % name(r + 1, c) if r < R - 1 else "1'b0"
        W = "%s_d[1]" % name(r, c - 1) if c > 0 else "w_d[%d]" % r; WF = "%s_f[1]" % name(r, c - 1) if c > 0 else "w_f[%d]" % r
        cin = "c_in" if idx == 0 else "%s_i" % name(*order[idx - 1])
        fi = ".fi_d({%s, %s, %s, %s}), .fi_f({%s, %s, %s, %s})" % (W, S, E, N, WF, SF, EF, NF)
        if pos[(r, c)] == "RAM":
            L.append("    hexn_ramhold_v1 #(.FACES(4)) %s (.clk(clk), .clear(clear), %s, .fo_d(%s_d), .fo_f(%s_f), .cfg_en(cfg_en), .cfg_in(%s), .cfg_out(%s_i));" % (n, fi, n, n, cin, n))
        elif pos[(r, c)] in ("AL", "JN", "BR", "MG", "PR", "SQ", "LT"):
            L.append("    " + SUPPORTED[pos[(r, c)]] + " #(.FACES(4)) %s (.clk(clk), .clear(clear), %s, .fo_d(%s_d), .fo_f(%s_f), .cfg_en(cfg_en), .cfg_in(%s), .cfg_out(%s_i));" % (n, fi, n, n, cin, n))
        elif pos[(r, c)] == "UN":
            L.append("    hexn_tile_v3 #(.FACES(4)) %s (.clk(clk), .clear(clear), %s, .fo_d(%s_d), .fo_f(%s_f), .cfg_en(cfg_en), .cfg_in(%s), .cfg_out(%s_i));" % (n, fi, n, n, cin, n))
        else:
            L.append("    hexn_rcore_flag_v3 #(.FACES(4)) %s (.clk(clk), .clear(clear), %s, .fo_d(%s_d), .fo_f(%s_f), .cfg_en(cfg_en), .cfg_in(%s), .cfg_out(%s_i));" % (n, fi, n, n, cin, n))
    for r in range(R):
        L.append("    assign e_d[%d] = %s_d[1]; assign e_f[%d] = %s_f[1];" % (r, name(r, Cn - 1), r, name(r, Cn - 1)))
    L.append("    assign cfg_out = %s_i;" % name(*order[-1]))
    L.append("endmodule")
    return "\n".join(L) + "\n"


def route_word(sel):
    """a 12-bit routing-cell word from {out face letter: in face letter}; unlisted outputs read index 7 (constant 0)"""
    w = 0
    for o in "NESW":
        src = sel[o] if o in sel else 7
        w |= (C.FACE[src] if isinstance(src, str) else src) << (3 * C.FACE[o])
    return w


def load_words(ref, program):
    """per-position words for `program` (the X.from_icm form) planned on this pattern -> (words, widths). Refuses a work cell of the program on a position the pattern does not give that type."""
    pos = positions(ref); words = []
    for (r, c) in sorted(pos):
        key = "%d,%d" % (r, c); cell = program["cells"].get(key)
        if pos[(r, c)] == "AL":
            if cell is None:
                words.append(CA.pack({}, "W", "N", (), "add"))                                      # idle AL tile
            else:
                if cell["type"] != "AL" or cell["kind"] not in ALOPS or cell.get("mode") != "aligned": raise ValueError("cell %s is %s/%s/%s: the AL tile has only the aligned add sub and or xor" % (key, cell["type"], cell["kind"], cell.get("mode")))
                words.append(CA.pack({}, "W", "N", ("E",), cell["kind"]))
        elif pos[(r, c)] == "MG":
            if cell is None:
                words.append(CM.pack({}, "W", "N", (), 0))                                          # idle MG tile
            else:
                if cell["type"] != "MG" or cell["kind"] != "merge": raise ValueError("cell %s is %s/%s: the MG tile has only the merge core" % (key, cell["type"], cell["kind"]))
                words.append(CM.pack({}, "W", "N", ("E",), (cell.get("cfg") or {}).get("mode", 2)))
        elif pos[(r, c)] == "BR":
            if cell is None:
                words.append(CB.pack({}, "W", "N", (), (), 0, 0, 0, 1, 0))                          # idle BR tile (route 0 = drop)
            else:
                if cell["type"] != "BR" or cell["kind"] != "branch": raise ValueError("cell %s is %s/%s: the BR tile has only the branch core" % (key, cell["type"], cell["kind"]))
                g = cell.get("cfg") or {}
                words.append(CB.pack({}, "W", "N", ("E",), ("S",), g.get("route_lt", 1), g.get("route_eq", 1), g.get("route_gt", 2), g.get("emit", 1), g.get("fixed", 0)))
        elif pos[(r, c)] == "PR":
            if cell is None:
                words.append(CP.pack({}, (), 0, (0, 0, 0, 0), 0, 0, (0, 0, 0, 0)))                  # idle PR tile (mask 0: nothing stored)
            else:
                if cell["type"] != "PR" or cell["kind"] != "prio": raise ValueError("cell %s is %s/%s: the PR tile has only the priority core" % (key, cell["type"], cell["kind"]))
                g = cell.get("cfg") or {}
                words.append(CP.pack({}, ("E",), g.get("mask", 15) & 7, tuple(g.get("ranks", (0, 0, 0, 0))), g.get("mode", 0), g.get("len", 0), tuple(g.get("order", (0, 0, 0, 0)))))
        elif pos[(r, c)] == "SQ":
            if cell is None:
                words.append(CS.pack({}, "W", (), [], 0))                                           # idle SQ tile (len 0 sends nothing)
            else:
                if cell["type"] != "SQ" or cell["kind"] != "seq": raise ValueError("cell %s is %s/%s: the SQ tile has only the sequencer core" % (key, cell["type"], cell["kind"]))
                g = cell.get("cfg") or {}
                words.append(CS.pack({}, "W", ("E",), g["vals"], g["len"]))
        elif pos[(r, c)] == "LT":
            if cell is None:
                words.append(CL.pack({}))                                                           # idle LT tile
            else:
                if cell["type"] != "LT" or cell["kind"] != "latch": raise ValueError("cell %s is %s/%s: the LT tile has only the latch core" % (key, cell["type"], cell["kind"]))
                words.append(CL.pack({}, "W", "N", "S", ("E",)))
        elif pos[(r, c)] == "JN":
            if cell is None:
                words.append(CJ.pack({}, "W", "N", (), "add"))                                      # idle JN tile
            else:
                if cell["type"] != "JN" or cell["kind"] not in JNOPS or cell.get("mode") != "join": raise ValueError("cell %s is %s/%s/%s: the JN tile has only the join add sub and or xor lt min max" % (key, cell["type"], cell["kind"], cell.get("mode")))
                words.append(CJ.pack({}, "W", "N", ("E",), cell["kind"]))
        elif pos[(r, c)] == "UN":
            if cell is None:
                words.append(C.pack({o: 7 for o in "NESW"}, "W", (), "cp", 0))                       # idle tile
            else:
                if cell["type"] != "UN" or cell["kind"] not in ("cp", "shl", "shr"): raise ValueError("cell %s is %s/%s: a UN tile has only the unary core (cp shl shr)" % (key, cell["type"], cell["kind"]))
                words.append(C.pack({o: 7 for o in "NESW"}, "W", ("E",), cell["kind"], cell["k"]))
        elif pos[(r, c)] == "RAM":
            if cell is not None: raise ValueError("the program puts a work cell at %s but the pattern has a RAM routing cell there" % key)
            h = (program.get("holds") or {}).get(key)
            words.append(CR.pack({o: C.FACE[s] for o, s in program["routing"].get(key, {}).items()}, h["out"] if h else None, h["dly"] if h else 0))
        else:
            if cell is not None: raise ValueError("the program puts a work cell at %s but the pattern has a bare routing cell there" % key)
            if (program.get("holds") or {}).get(key): raise ValueError("the program holds a stream at %s but the pattern has a bare routing cell there (no RAM)" % key)
            words.append(route_word(program["routing"].get(key, {})))
    return words, widths_of(ref)


def chain_bits(words, widths):
    bits = []
    for w, n in reversed(list(zip(words, widths))):
        bits += [(w >> i) & 1 for i in range(n - 1, -1, -1)]
    return bits
