"""hexn_pattern_gen_hex_v1.py - the HEX PATTERN GENERATOR (3 Nov 2026, H4; Alan 20:24 'by row is fine'). Not a clone of gen_v10 (four faces, untouched): same job at SIX faces.
A hex pattern reference ('hexn-pattern-hex-v1', make_ref below) names a ROWS x COLS odd-r grid, the work-colour offset and the type of every work position (tools/hexn_hexgeom_v1.py). generate(ref) writes `hexn_pattern_top`: every work position is the tile of its type at FACES=6,
every other position a bare routing cell (hexn_rcore_flag_v3, FACES=6). Neighbours follow the odd-r rule: face f of a cell reads the neighbour's face (f+3)%6. West pads: face W of column 0, row r = w_d[r]/w_f[r]; east pads: face E of the last column = e_d[r]/e_f[r]. Every other outside face reads 0.
CONFIG CHAIN: row-major through all positions (Alan: 'by row is fine'); word widths at six faces: UN 43, AL 33, JN 33, BR 76, MG 32, PR 61, SQ 158, LT 33, routing 18. load_words(ref, program) -> words for a program (the icm-hexn-v4 form); chain_bits as in gen_v10.
SCOPE: RAM hold cells are NOT built at six faces (refused by name); no id registry scheme yet - pattern_id here is the first 8 hex digits of the content hash (provisional); simulated against the hex VM in tests/vm/test_hexn_hexgen_v1.py, not placed and routed, no board."""
import hashlib, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import hexn_hexgeom_v1 as HX
import hexn_tile_cfg_v1 as C, hexn_tile_cfg_al_v1 as CA, hexn_tile_cfg_jn_v1 as CJ, hexn_tile_cfg_br_v1 as CB, hexn_tile_cfg_mg_v1 as CM, hexn_tile_cfg_pr_v2 as CP, hexn_tile_cfg_sq_v1 as CS, hexn_tile_cfg_lt_v1 as CL

VDIR = os.path.join(ROOT, "sub", "verilog")
FILES = [os.path.join(VDIR, f) for f in ("hexn_rcore_flag_v3.v", "hexn_tile_v3.v", "hexn_unary_core_v2.v", "hexn_tile_al_v2.v", "hexn_aligned_core_v2.v", "hexn_tile_jn_v2.v", "hexn_join_core_v3.v", "hexn_tile_br_v2.v", "hexn_branch_core_v2.v",
                                      "hexn_tile_mg_v2.v", "hexn_merge_core_v2.v", "hexn_tile_pr_v2.v", "hexn_prio_core_v2.v", "hexn_tile_sq_v1.v", "hexn_seq_core_v2.v", "hexn_tile_lt_v2.v", "hexn_latch_core_v3.v")]
SUPPORTED = {"UN": "hexn_tile_v3", "AL": "hexn_tile_al_v2", "JN": "hexn_tile_jn_v2", "BR": "hexn_tile_br_v2", "MG": "hexn_tile_mg_v2", "PR": "hexn_tile_pr_v2", "SQ": "hexn_tile_sq_v1", "LT": "hexn_tile_lt_v2"}
WIDTH = {"UN": C.width(6), "AL": CA.width(6), "JN": CJ.width(6), "BR": CB.width(6), "MG": CM.width(6), "PR": CP.width(6), "SQ": CS.width(6), "LT": CL.width(6), None: 18}
FORMAT = "hexn-pattern-hex-v1"
F = {n: i for i, n in enumerate(HX.NAMES)}                                    # E 0, SE 1, SW 2, W 3, NW 4, NE 5
HSTD_IN = {"W": "W", "N": "NW", "S": "SW", "E": "NE"}                           # the planner's standard hex faces for the abstract roles (hexn_wrgrid_hex_v3)
HSTD_OUT = {"E": "E", "S": "SE"}
ALOPS = {"add", "sub", "and", "or", "xor"}
_canon = lambda x: json.dumps(x, sort_keys=True, separators=(",", ":"))


def make_ref(name, rows, cols, offset, types):
    """types: {(r, c): type letters} for every work position of the grid at this offset"""
    wc = [(r, c) for r in range(rows) for c in range(cols) if HX.colour(r, c) == offset]
    if sorted(types) != sorted(wc): raise ValueError("types must name exactly the %d work positions of a %dx%d grid at offset %d" % (len(wc), rows, cols, offset))
    for k, t in types.items():
        if t not in SUPPORTED: raise ValueError("work cell %s is type %s: no six-face tile for it" % (k, t))
    body = dict(format=FORMAT, name=name, rows=rows, cols=cols, faces=6, offset=offset, work_cells=[dict(r=r, c=c, type=types[(r, c)]) for (r, c) in sorted(types)])
    h = hashlib.sha256(_canon(body).encode()).hexdigest()
    return dict(body, content_hash=h, pattern_id=int(h[:8], 16), pattern_id_hex=h[:8].upper())


def check_reference(ref):
    if ref.get("format") != FORMAT or ref.get("faces") != 6: return ["not a %s file" % FORMAT]
    body = {k: v for k, v in ref.items() if k not in ("content_hash", "pattern_id", "pattern_id_hex")}
    return [] if hashlib.sha256(_canon(body).encode()).hexdigest() == ref.get("content_hash") else ["content hash does not match: file damaged or edited"]


def positions(ref):
    pr = check_reference(ref)
    if pr: raise ValueError(pr[0])
    pos = {(r, c): None for r in range(ref["rows"]) for c in range(ref["cols"])}
    for w in ref["work_cells"]:
        if HX.colour(w["r"], w["c"]) != ref["offset"]: raise ValueError("work cell (%d,%d) is not a work position at offset %d" % (w["r"], w["c"], ref["offset"]))
        if w["type"] not in SUPPORTED: raise ValueError("work cell (%d,%d) is type %s: no six-face tile for it" % (w["r"], w["c"], w["type"]))
        pos[(w["r"], w["c"])] = w["type"]
    return pos


def order(ref): return [(r, c) for r in range(ref["rows"]) for c in range(ref["cols"])]          # the chain: row-major
def widths_of(ref): pos = positions(ref); return [WIDTH[pos[p]] for p in order(ref)]
def chain_len(ref): return sum(widths_of(ref))


def generate(ref):
    pos = positions(ref); R, Cn = ref["rows"], ref["cols"]; nm = lambda r, c: "p_%d_%d" % (r, c)
    L = ["`default_nettype none",
         "// hexn_pattern_top for hex pattern %s (ID %s, %dx%d, offset %d, %d work tiles, %d bare routing cells, 6 faces), generated by tools/hexn_pattern_gen_hex_v1.py; do not edit." % (
             ref["name"], ref["pattern_id_hex"], R, Cn, ref["offset"], len(ref["work_cells"]), R * Cn - len(ref["work_cells"])),
         "module hexn_pattern_top (input wire clk, input wire clear, input wire [%d:0] w_d, input wire [%d:0] w_f, output wire [%d:0] e_d, output wire [%d:0] e_f, input wire cfg_en, input wire cfg_in, output wire cfg_out);" % ((R - 1,) * 4)]
    for r in range(R):
        for c in range(Cn): L.append("    wire [5:0] %s_d, %s_f; wire %s_i;" % ((nm(r, c),) * 3))
    seq = order(ref)
    for idx, (r, c) in enumerate(seq):
        n = nm(r, c); d, f = [], []
        for face in range(5, -1, -1):
            q = HX.neighbour(r, c, face)
            if HX.inside(R, Cn, q): d.append("%s_d[%d]" % (nm(*q), (face + 3) % 6)); f.append("%s_f[%d]" % (nm(*q), (face + 3) % 6))
            elif face == 3 and c == 0: d.append("w_d[%d]" % r); f.append("w_f[%d]" % r)
            else: d.append("1'b0"); f.append("1'b0")
        cin = "cfg_in" if idx == 0 else "%s_i" % nm(*seq[idx - 1])
        mod = SUPPORTED[pos[(r, c)]] if pos[(r, c)] else "hexn_rcore_flag_v3"
        L.append("    %s #(.FACES(6)) %s (.clk(clk), .clear(clear), .fi_d({%s}), .fi_f({%s}), .fo_d(%s_d), .fo_f(%s_f), .cfg_en(cfg_en), .cfg_in(%s), .cfg_out(%s_i));" % (mod, n, ", ".join(d), ", ".join(f), n, n, cin, n))
    for r in range(R): L.append("    assign e_d[%d] = %s_d[0]; assign e_f[%d] = %s_f[0];" % (r, nm(r, Cn - 1), r, nm(r, Cn - 1)))
    L.append("    assign cfg_out = %s_i;" % nm(*seq[-1])); L.append("endmodule")
    return "\n".join(L) + "\n"


def route_word(sel):
    """18-bit routing-cell word from {out face name: in face name}; unlisted outputs read 7 (constant 0)"""
    w = 0
    for o in range(6): w |= (F[sel[HX.NAMES[o]]] if HX.NAMES[o] in sel else 7) << (3 * o)
    return w


def _faces(cell, roles_in):
    """(fi, fo) as hex face INDICES for the roles in roles_in / outputs E, S: the planner's choice (cfg fi / fo) where stored, else the standard hex face; an unused role in a chosen set reads 7 for the latch"""
    cfg = cell.get("cfg") or {}; fi, fo = cfg.get("fi") or {}, cfg.get("fo") or {}
    return ({r: F[fi[r]] if r in fi else F[HSTD_IN[r]] for r in roles_in}, {r: F[fo[r]] if r in fo else F[HSTD_OUT[r]] for r in ("E", "S")})


def load_words(ref, program):
    """per-position words, row-major, for a program (icm-hexn-v4 form) planned on this pattern -> (words, widths)"""
    pos = positions(ref); words = []; R7 = {o: 7 for o in range(6)}
    if (program["rows"], program["cols"], program["offset"]) != (ref["rows"], ref["cols"], ref["offset"]): raise ValueError("program is for a %dx%d grid at offset %d, the pattern is %dx%d at offset %d" % (program["rows"], program["cols"], program["offset"], ref["rows"], ref["cols"], ref["offset"]))
    if program.get("holds"): raise ValueError("the program holds a stream: RAM hold cells are not built at six faces")
    for (r, c) in order(ref):
        key = "%d,%d" % (r, c); cell = program["cells"].get(key); t = pos[(r, c)]
        if t is None:
            if cell is not None: raise ValueError("the program puts a work cell at %s but the pattern has a bare routing cell there" % key)
            words.append(route_word(program["routing"].get(key, {}))); continue
        if cell is not None and cell["type"] != t: raise ValueError("cell %s is %s but the pattern has a %s tile there" % (key, cell["type"], t))
        if cell is None:                                                        # idle tile
            idle = {"UN": lambda: C.pack(R7, 3, (), "cp", 0, faces=6), "AL": lambda: CA.pack({}, 3, 4, (), "add", faces=6), "JN": lambda: CJ.pack({}, 3, 4, (), "add", faces=6),
                    "MG": lambda: CM.pack({}, 3, 4, (), 0, faces=6), "BR": lambda: CB.pack({}, 3, 4, (), (), 0, 0, 0, 1, 0, faces=6), "PR": lambda: CP.pack({}, (), 0, (0, 0, 0, 0), 0, 0, (0, 0, 0, 0), faces=6),
                    "SQ": lambda: CS.pack({}, 3, (), [], 0, faces=6), "LT": lambda: CL.pack({}, faces=6)}
            words.append(idle[t]()); continue
        g = cell.get("cfg") or {}; k = cell["kind"]
        if t == "UN":
            if k not in ("cp", "shl", "shr"): raise ValueError("cell %s: a UN tile has only cp shl shr" % key)
            fi, fo = _faces(cell, ("W",)); words.append(C.pack(R7, fi["W"], (fo["E"],), k, cell["k"], faces=6))
        elif t == "AL":
            if k not in ALOPS or cell.get("mode") != "aligned": raise ValueError("cell %s: the AL tile has only the aligned add sub and or xor" % key)
            fi, fo = _faces(cell, ("W", "N")); words.append(CA.pack({}, fi["W"], fi["N"], (fo["E"],), k, faces=6))
        elif t == "JN":
            if k not in CJ.OPS or cell.get("mode") != "join": raise ValueError("cell %s: the JN tile has only the join ops" % key)
            fi, fo = _faces(cell, ("W", "N")); words.append(CJ.pack({}, fi["W"], fi["N"], (fo["E"],), k, faces=6))
        elif t == "MG":
            if k != "merge": raise ValueError("cell %s: the MG tile has only the merge core" % key)
            fi, fo = _faces(cell, ("W", "N")); words.append(CM.pack({}, fi["W"], fi["N"], (fo["E"],), g.get("mode", 2), faces=6))
        elif t == "BR":
            if k != "branch": raise ValueError("cell %s: the BR tile has only the branch core" % key)
            fi, fo = _faces(cell, ("W", "N")); words.append(CB.pack({}, fi["W"], fi["N"], (fo["E"],), (fo["S"],), g.get("route_lt", 1), g.get("route_eq", 1), g.get("route_gt", 2), g.get("emit", 1), g.get("fixed", 0), faces=6))
        elif t == "PR":
            if k != "prio": raise ValueError("cell %s: the PR tile has only the priority core" % key)
            fi, fo = _faces(cell, ("W", "N", "S", "E")); words.append(CP.pack({}, (fo["E"],), g.get("mask", 15) & 15, tuple(g.get("ranks", (0, 0, 0, 0))), g.get("mode", 0), g.get("len", 0), tuple(g.get("order", (0, 0, 0, 0))), (fi["W"], fi["N"], fi["S"], fi["E"]), faces=6))
        elif t == "SQ":
            if k != "seq": raise ValueError("cell %s: the SQ tile has only the sequencer core" % key)
            fi, fo = _faces(cell, ("W",)); words.append(CS.pack({}, fi["W"], (fo["E"],), g["vals"], g["len"], faces=6))
        elif t == "LT":
            if k != "latch": raise ValueError("cell %s: the LT tile has only the latch core" % key)
            fi = (g.get("fi") or {}); fo = _faces(cell, ())[1]
            nv = lambda role: F[fi[role]] if role in fi else (F[HSTD_IN[role]] if not fi else 7)
            words.append(CL.pack({}, nv("W"), nv("N"), nv("S"), (fo["E"],), faces=6))
    return words, widths_of(ref)


def chain_bits(words, widths):
    bits = []
    for w, n in reversed(list(zip(words, widths))): bits += [(w >> i) & 1 for i in range(n - 1, -1, -1)]
    return bits
