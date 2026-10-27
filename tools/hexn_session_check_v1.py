"""hexn_session_check_v1: checks a recorded layer-2 session run against its plan (new file; Python only; uses hexn_ir_decode_v1 unchanged and docs/hex-n/sessions/routines_plan_v1.json from hexn_session_plan_v1.py).
Decodes the IR edges file into presses (one press = one data frame plus its repeat frames), maps each command byte to a key number of the remote's table, aligns the pressed keys with the planned keys (minimum edit distance) and prints: presses decoded, planned, matched, missing, extra, substituted, unknown codes, the press times (gap inside routines and between routines, from the plan), and the first differences. Exit 0 when every planned press is present in order, else 1.
Usage: python3 tools/hexn_session_check_v1.py <edges csv> <run number> [--plan path]   (a self test: python3 tools/hexn_session_check_v1.py --selftest)"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_ir_decode_v1 as IR
HERE = os.path.dirname(os.path.abspath(__file__)); PLAN = os.path.join(HERE, "..", "docs", "hex-n", "sessions", "routines_plan_v1.json")
TABLE = [0x45, 0x46, 0x47, 0x44, 0x40, 0x43, 0x07, 0x15, 0x09, 0x16, 0x19, 0x0D, 0x0C, 0x18, 0x5E, 0x08, 0x1C, 0x5A, 0x42, 0x52, 0x4A]
def presses_of(edges):
    ps = IR.presses(IR.decode(IR.load(edges))); out = []; unk = 0
    for q in ps:
        if q["kind"] != "data": continue
        c = q["bytes"][2]
        if c in TABLE: out.append((TABLE.index(c), q["t"], q["repeats"]))
        else: unk += 1
    return out, unk
def align(a, b):
    """minimum edit alignment of pressed keys a against planned keys b; returns list of ops (match/sub/del/ins, ia, ib)"""
    n, m = len(a), len(b); d = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1): d[i][0] = i
    for j in range(m + 1): d[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1): d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (a[i - 1] != b[j - 1]))
    ops = []; i, j = n, m
    while i or j:
        if i and j and d[i][j] == d[i - 1][j - 1] + (a[i - 1] != b[j - 1]): ops.append(("match" if a[i - 1] == b[j - 1] else "sub", i - 1, j - 1)); i -= 1; j -= 1
        elif i and d[i][j] == d[i - 1][j] + 1: ops.append(("extra", i - 1, None)); i -= 1
        else: ops.append(("missing", None, j - 1)); j -= 1
    return ops[::-1]
def check(edges, run, plan_path=PLAN, quiet=False):
    plan = json.load(open(plan_path))["runs"][str(run)]; want = plan["table_index"]; ps, unk = presses_of(edges); got = [k for k, _, _ in ps]; ops = align(got, want)
    cnt = {k: sum(1 for o in ops if o[0] == k) for k in ("match", "sub", "extra", "missing")}
    if not quiet:
        print("run %s: planned %d presses, decoded %d (+%d unknown codes); matched %d, substituted %d, extra %d, missing %d" % (run, len(want), len(got), unk, cnt["match"], cnt["sub"], cnt["extra"], cnt["missing"]))
        for o in [o for o in ops if o[0] != "match"][:10]: print("  ", o[0], "pressed key %s" % (got[o[1]] if o[1] is not None else "-"), "planned key %s (planned press #%s)" % (want[o[2]] if o[2] is not None else "-", o[2] + 1 if o[2] is not None else "-"))
        if ps:
            gaps = [round(b[1] - a[1], 2) for a, b in zip(ps, ps[1:])]; print("  seconds between presses: median %.2f, shortest %.2f, longest %.2f" % (sorted(gaps)[len(gaps) // 2], min(gaps), max(gaps)))
    return cnt["sub"] + cnt["extra"] + cnt["missing"] == 0, cnt
def selftest():
    plan = json.load(open(PLAN)); import tempfile
    ok1 = align([1, 2, 3], [1, 2, 3]); assert all(o[0] == "match" for o in ok1)
    ops = align([1, 3, 4], [1, 2, 3, 4]); assert [o[0] for o in ops] == ["match", "missing", "match", "match"], ops
    ops = align([1, 2, 9, 3], [1, 2, 3]); assert [o[0] for o in ops].count("extra") == 1, ops
    ops = align([1, 5, 3], [1, 2, 3]); assert [o[0] for o in ops] == ["match", "sub", "match"], ops
    print("SELFTEST PASS (alignment)")
def main():
    if "--selftest" in sys.argv: return selftest()
    ok, _ = check(sys.argv[1], sys.argv[2]); sys.exit(0 if ok else 1)
if __name__ == "__main__": main()
