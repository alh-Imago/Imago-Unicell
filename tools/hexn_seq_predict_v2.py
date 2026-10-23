"""(v2: clone of hexn_seq_predict_v1.py, left untouched. Learner variants: an ODD number of look windows (an even number leaves ties, and a tied wire becomes 0, which biases the stored pattern), and a stricter test before a second slot is stored for a state: the conflicting views must AGREE with each other (a real branch shows the same alternative again and again; noise shows a different one every time) and must be confirmed `need` times.)
SEQUENCE PREDICTION with the save/recall memory block (host policy only; the same commands as the write rules, no new hardware). Python model first.
Idea: the block recalls a whole stored pattern from a partial cue. Store each TRANSITION as one pattern: the 9 wires of the state just left (low half) and the 9 wires of the state just entered (high half) = 18 wires, one slot. To predict, cue with the current state on the low half only (the high half is unknown) and the block hands back the stored pattern; its high half is the predicted next state. Chaining the prediction (use the predicted half as the next cue) predicts several steps ahead.
World: S states, each a random 9-wire pattern (any two differ in >= 3 wires), seen through noise q on every wire. 'cycle' = 0->1->...->S-1->0. 'branch' = the same cycle, but state 0 goes to 1 (70 percent) or 2 (30 percent): the first-order memory cannot say which, and the model measures how it behaves (it must say 'ambiguous', not guess).
Learning (online): each step the host sees the new state through `acq` look windows (majority = the clean view), cues the memory with the previous clean view; if the memory does not know it, the transition is stored in the next free slot; if it knows it but the high half disagrees with what was seen (> tol wires), that counts as a conflict and the second confirmed conflict stores the transition as another slot (this is how a branch gets its second slot). No eviction (v1).
Testing: fresh noisy looks (nc windows) at the current state, low-half cue; answer = nearest state to the recalled high half; 'ambiguous' if the best two slots tie; 'unknown' if the block does not recognise the cue (best slot must be strictly ahead and match >= 75 percent of the known wires, as in the write rules).
Every device answer is compared with the Python copy of the block (MemRef), so this can later run on the card unchanged (links as in tools/hexn_mem_write_v1.py).
Usage: python3 tools/hexn_seq_predict_v1.py [SEEDS]"""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_mem_host_v1 as H
from hexn_mem_write_v1 import RefLink
NB, M, HALF = H.NB, H.M, 9
AM = (1 << HALF) - 1; FULLM = (1 << NB) - 1
def hd(a, b): return H.pc((a ^ b) & AM)
def templates(r, S, dmin=3):
    while True:
        t = [r.getrandbits(HALF) for _ in range(S)]
        if all(hd(t[i], t[j]) >= dmin for i in range(S) for j in range(i)): return t
def successors(kind, S):
    succ = {s: [((s + 1) % S, 1.0)] for s in range(S)}
    if kind == "branch": succ[0] = [(1, 0.7), (2, 0.3)]
    return succ
def step(r, succ, s):
    x = r.random(); acc = 0.0
    for n, p in succ[s]:
        acc += p
        if x < acc: return n
    return succ[s][-1][0]
def view(r, t, q): return sum((((t >> j) & 1) ^ (1 if r.random() < q else 0)) << j for j in range(HALF))
def nearest(tmpl, v): return min(range(len(tmpl)), key=lambda s: hd(tmpl[s], v))
def run(link, kind, S, q, seed, T_learn=150, T_test=240, acq=4, nc=3, tol=3, need=2, consistent=False):
    r = random.Random(seed * 104729 + S); tmpl = templates(r, S); succ = successors(kind, S); d = H.Dev(link); ref = H.MemRef(); d.clrall(); ref.clrall()
    bad = checks = 0
    def chk(got, want):
        nonlocal bad, checks; checks += 1; bad += got != want
    def look(pats, mask):
        d.clr(); ref.clr()
        for p in pats: d.watch(p, mask); ref.watch(p, mask)
    def recall():
        got = d.recall(); chk(got, ref.recall()); bid, bm, kn, sm, cue, rec, dev = got
        fam = bid != 15 and bm > sm and bm >= 0.75 * kn; tie = bid != 15 and bm == sm and bm >= 0.75 * kn
        return fam, tie, (rec >> HALF) & AM, bid
    stored = 0; conflicts = {}; s = 0; prev = None
    for t in range(T_learn):
        s = step(r, succ, s); looks = [view(r, tmpl[s], q) for _ in range(acq)]; look(looks, AM); cur = ref.cue() & AM
        if prev is not None:
            look([prev], AM); fam, tie, pb, bid = recall()
            put = False
            if not fam and not tie: put = True
            elif fam and hd(pb, cur) > tol:
                n0, alt = conflicts.get(bid, (0, cur))
                if consistent and n0 and hd(alt, cur) > tol: n0, alt = 0, cur           # a different alternative: start counting again
                conflicts[bid] = (n0 + 1, alt); put = n0 + 1 >= need
                if put: conflicts[bid] = (0, cur)
            if put and stored < M:
                look([prev | (cur << HALF)], FULLM); d.save(stored); ref.save(stored); stored += 1
        prev = cur
    n = ans = ok = amb = unk = 0; hz = {h: [0, 0] for h in (2, 3, 4)}; main_ok = 0
    s = r.randrange(S)
    for t in range(T_test):
        look([view(r, tmpl[s], q) for _ in range(nc)], AM); fam, tie, pb, bid = recall(); n += 1
        poss = [x for x, _ in succ[s]]
        if tie: amb += 1
        elif not fam: unk += 1
        else:
            ans += 1; guess = nearest(tmpl, pb); ok += guess in poss; main_ok += guess == poss[0]
            if kind == "cycle":
                g = guess; truth = s
                for h in range(2, 5):
                    look([tmpl_cue for tmpl_cue in [tmpl[g]]], AM)      # chain: the predicted state, exact, as the next cue
                    f2, t2, pb2, _ = recall(); truth = (s + h) % S
                    if f2 and not t2: g = nearest(tmpl, pb2); hz[h][0] += g == truth; hz[h][1] += 1
                    else: break
        s = step(r, succ, s)
    return dict(answered=ans / n, right=ok / max(1, ans), ambiguous=amb / n, unknown=unk / n, slots=stored, h2=hz[2][0] / max(1, hz[2][1]), h3=hz[3][0] / max(1, hz[3][1]), h4=hz[4][0] / max(1, hz[4][1]), bad=bad, checks=checks)
KEYS = ("answered", "right", "ambiguous", "unknown", "slots", "h2", "h3", "h4")
POLICIES = {"v1: 4 looks, 2 conflicts": dict(acq=4, need=2, consistent=False), "5 looks, 2 conflicts": dict(acq=5, need=2, consistent=False), "5 looks, 3 agreeing conflicts": dict(acq=5, need=3, consistent=True), "7 looks, 3 agreeing conflicts": dict(acq=7, need=3, consistent=True), "7 looks, 4 agreeing conflicts": dict(acq=7, need=4, consistent=True)}
WORLDS = [("cycle", 4, .05), ("cycle", 4, .15), ("cycle", 6, .15), ("cycle", 6, .25), ("cycle", 8, .15), ("branch", 6, .05), ("branch", 6, .15)]
def study(link_factory, seeds, pol):
    rows = []
    for kind, S, q in WORLDS:
        acc = dict.fromkeys(KEYS + ("bad", "checks"), 0)
        for sd in seeds:
            x = run(link_factory(), kind, S, q, sd, **pol)
            for k in acc: acc[k] += x[k] / len(seeds)
        rows.append(("%s S=%d noise %.2f" % (kind, S, q), acc))
    return rows
def show(rows):
    print("%-22s | answered | right when answered | said ambiguous | unknown | slots used | right 2 steps ahead | 3 steps | 4 steps" % "world")
    for name, a in rows: print("%-22s | %.2f | %.2f | %.2f | %.2f | %.1f | %.2f | %.2f | %.2f" % ((name,) + tuple(a[k] for k in KEYS)))
if __name__ == "__main__":
    seeds = range(1, (int(sys.argv[1]) if len(sys.argv) > 1 else 5) + 1); bad = checks = 0
    for name, pol in POLICIES.items():
        rows = study(RefLink, seeds, pol); print("== learner: " + name); show(rows); bad += sum(a["bad"] for _, a in rows); checks += sum(a["checks"] for _, a in rows)
    print("device vs Python-copy differences: %d of %d" % (bad, checks))
