#!/usr/bin/env python3
"""hexn_twins_v1: word-level Python twins of the serial branch / merge / priority / sequencer cores (2 Nov 2026), for the grid planner.
They are NOT bit-for-bit copies of the RTL: each one keeps the words it receives and applies timing laws that were MEASURED on the RTL with tools/hexn_rtl_probe_v1.py:
  merge / priority : a word that starts at tick s and finds the cell free leaves at s + 4 (first bit visible); when several words wait, the next one leaves 34 ticks after the last one (go = last + 30, + 4); a cell takes a new word only from 30 ticks after its word left.
  branch           : both words in, result starts at (later start) + 38; the cells take new words from 30 ticks after the result started.
  sequencer        : result starts at (advance start) + 2; a new advance is taken from 31 ticks after the last result started.
  join-OR merge    : (later start) + 4.
tests/vm/test_hexn_twins_v1.py compares every twin with the RTL on random stimuli (start ticks and words), word for word and tick for tick.
A twin is stepped once per tick like a grid core:  outs = twin.step(t, {face: (bit, flag)});  outs is {out_face: (bit, flag)} to be seen by the NEXT tick (the registered outputs)."""
W = 32
MASK = (1 << W) - 1


class Twin:
    INS = ()
    OUTS = ("E",)
    def __init__(s):
        s.rx = {}                    # face -> dict(start, bits, rel)   the word the cell holds (rel = tick its result started, or None)
        s.free_at = {}               # face -> tick from which the cell takes a new word
        s.sched = _Sched()           # out face -> list of (vis_start, bitlist): the next word may be set up while the last bit of the one before is still on its way
        s.last_out = -10 ** 9
    def _arrive(s, t, ins):
        for f, c in list(s.rx.items()):          # a cell whose word has left is empty again from free_at (before this tick's arrival is looked at)
            if c["rel"] is not None and t >= s.free_at[f]: del s.rx[f]
        for f in s.INS:
            bit, flag = ins.get(f, (0, 0))
            if flag:
                cur = s.rx.get(f)
                if cur is None and t >= s.free_at.get(f, -10 ** 9):
                    s.rx[f] = dict(start=t, bits=[bit], rel=None)
            else:
                cur = s.rx.get(f)
                if cur is not None and len(cur["bits"]) < W and t - cur["start"] == len(cur["bits"]): cur["bits"].append(bit)
    def _emit(s, t):
        outs = {}
        for of in s.OUTS:
            outs[of] = (0, 0)
            for (S, bits) in s.sched.lst(of):
                k = t + 1 - S
                if 0 <= k < W: outs[of] = (bits[k], 1 if k == 0 else 0)
            s.sched.drop_done(of, t + 1)
        return outs
    def step(s, t, ins):
        s._arrive(t, ins); s.logic(t); return s._emit(t)
    @staticmethod
    def word(bits): return sum(b << i for i, b in enumerate(bits))


class MergeTwin(Twin):
    INS = ("W", "N")             # A on W, B on N
    def __init__(s, mode):
        super().__init__(); s.mode = mode; s.lastb = 1
    def logic(s, t):
        m = s.mode; A, B = s.rx.get("W"), s.rx.get("N")
        if m == 3:
            if A and B and A["rel"] is None and B["rel"] is None:
                S = max(A["start"], B["start"]) + 4
                s._release("W", S, B_too=True)
                s.sched["E"] = (S, [A["bits"][i] | B["bits"][i] if i < len(A["bits"]) and i < len(B["bits"]) else 0 for i in range(W)]) if False else (S, _LazyOr(A, B))
            return
        if t < s.last_out + 30: return
        cand = []
        if m != 1 and A and A["rel"] is None: cand.append("W")
        if m != 0 and B and B["rel"] is None: cand.append("N")
        if not cand: return
        f = cand[0] if len(cand) == 1 else ("N" if not s.lastb else "W") if m == 2 else cand[0]
        if m == 2: s.lastb = 1 if f == "N" else 0
        S = t + 4; s._release(f, S)
        s.sched["E"] = (S, _Lazy(s.rx[f]))
    def _release(s, f, S, B_too=False):
        for g in (("W", "N") if B_too else (f,)):
            s.rx[g]["rel"] = S; s.free_at[g] = S + 30
        s.last_out = S


class _Sched:
    def __init__(s): s.d = {}
    def __setitem__(s, of, v): s.d.setdefault(of, []).append(v)
    def lst(s, of): return s.d.get(of, [])
    def drop_done(s, of, vis): s.d[of] = [x for x in s.d.get(of, []) if vis - x[0] < W - 1]
    def keys(s): return [k for k, v in s.d.items() if v]
class _Lazy:
    """bits of a word that is still arriving"""
    def __init__(s, c): s.c = c
    def __getitem__(s, k): b = s.c["bits"]; return b[k] if k < len(b) else 0
class _LazyOr:
    def __init__(s, a, b): s.a, s.b = _Lazy(a), _Lazy(b)
    def __getitem__(s, k): return s.a[k] | s.b[k]


class PrioTwin(Twin):
    INS = ("N", "S", "E", "W")     # faces 0 n, 1 s, 2 e, 3 w  (the cell's face codes; in the grid the planner assigns the real faces)
    def __init__(s, mask=15, ranks=(0, 0, 0, 0), mode=0, length=0, order=(0, 0, 0, 0)):
        super().__init__(); s.mask, s.rk, s.mode, s.len, s.order = mask, list(ranks), mode, length, list(order); s.cr = [0] * 4; s.sidx = 0
    def _arrive(s, t, ins):
        ins = {f: v for i, f in enumerate(s.INS) for v in [ins.get(f, (0, 0))] if (s.mask >> i) & 1 or not v[1]}
        super()._arrive(t, {f: v for f, v in ins.items()})
        for i, f in enumerate(s.INS):
            if not (s.mask >> i) & 1: s.rx.pop(f, None)
    def logic(s, t):
        if t < s.last_out + 30: return
        if s.mode == 2 and s.len == 0: return
        due = s.order[s.sidx % 4] if s.mode == 2 else None
        cand = [(s.INS[i] in s.rx and s.rx[s.INS[i]]["rel"] is None and (s.mask >> i) & 1 and (s.mode != 2 or due == i)) for i in range(4)]
        if not any(cand): return
        inc = [s.cr[i] + s.rk[i] if cand[i] else s.cr[i] for i in range(4)]
        tw = sum(s.rk[i] for i in range(4) if cand[i])
        sc = [inc[i] if s.mode == 1 else 3 - s.rk[i] for i in range(4)]
        win = next(i for i in range(4) if cand[i] and all((not cand[j]) or sc[i] >= sc[j] for j in range(4) if j != i))
        # the RTL's own tie rule N > S > E > W is the first index that is not beaten
        if s.mode == 2: s.sidx = 0 if s.sidx + 1 >= s.len else s.sidx + 1
        if s.mode == 1: s.cr = [(max(inc[i] - tw, 0) if i == win else inc[i]) for i in range(4)]
        f = s.INS[win]; S = t + 4
        s.rx[f]["rel"] = S; s.free_at[f] = S + 30; s.last_out = S
        s.sched["E"] = (S, _Lazy(s.rx[f]))


class BranchTwin(Twin):
    INS = ("W", "N")
    OUTS = ("E", "S")             # out1 on E, out2 on S
    def __init__(s, route_lt=1, route_eq=1, route_gt=2, emit=1, fixed=0):
        super().__init__(); s.rt = dict(lt=route_lt, eq=route_eq, gt=route_gt); s.emit, s.fixed = emit, fixed
    def logic(s, t):
        A, B = s.rx.get("W"), s.rx.get("N")
        if not (A and B) or A["rel"] is not None or B["rel"] is not None: return
        S = max(A["start"], B["start"]) + 38
        if t < max(A["start"], B["start"]) + W - 1: return          # decide when both words are complete
        a, b = s.word(A["bits"]), s.word(B["bits"])
        sg = lambda x: x - (1 << W) if x >> (W - 1) else x
        route = s.rt["eq"] if a == b else s.rt["lt"] if sg(a) < sg(b) else s.rt["gt"]
        val = [s.fixed, a, b, (a - b) & MASK][s.emit]
        bits = [(val >> i) & 1 for i in range(W)]
        for g in ("W", "N"): s.rx[g]["rel"] = S; s.free_at[g] = S + 30
        if route & 1: s.sched["E"] = (S, bits)
        if route & 2: s.sched["S"] = (S, bits)


class SeqTwin(Twin):
    INS = ("W",)
    def __init__(s, vals, length):
        super().__init__(); s.vals, s.len, s.idx, s.prevf, s.next_ok = list(vals), length, 0, 0, -10 ** 9
    def _arrive(s, t, ins):
        f = ins.get("W", (0, 0))[1]
        s.adv = bool(f) and t >= s.next_ok and s.len != 0
    def logic(s, t):
        if s.adv:
            S = t + 2; v = s.vals[s.idx]; s.idx = (s.idx + 1) % s.len if s.idx + 1 < s.len else 0
            s.sched["E"] = (S, [(v >> i) & 1 for i in range(W)]); s.next_ok = S + 31
