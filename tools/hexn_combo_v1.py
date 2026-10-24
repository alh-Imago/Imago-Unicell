"""TWO-INPUT TABLE AND CHAINING with the save/recall memory block (host policy only; the same commands as the write rules; Python model first).
Idea (Alan, 24 Oct): the long-term and near-term memory, plus a COMBINATION: a lookup that takes two inputs and returns the outcome stored for that pair.
A rule is stored as ONE 18-wire pattern: wires 0-5 = input 1, wires 6-11 = input 2, wires 12-17 = outcome. To use it, cue with inputs 1 and 2 only (the low 12
wires) and read the outcome from the recalled pattern's high 6 wires. A symbol is a random 6-wire code; any two codes differ in at least 3 wires (at most 8 such
codes exist, so the alphabet is tiny: this studies the mechanism, not capacity; the block has 8 slots). Symbol 0 is the 'none' code, used as input 2 of a
single-input rule.
World: a hidden rule h(x, b) and a hidden rule g(a) -> x, so the true answer for the pair (a, b) is h(g(a), b). 4 symbols for a, 2 for b, 2 for x, 2 for the outcome.
Tests (each wire of each look is flipped with chance q):
  DIRECT table: stores (a, b, outcome) for the pairs it is shown. Pairs it was NOT shown test the 'known or new' decision: the right behaviour is 'unknown'.
  CHAIN: stores rule 1 as (a, none, x) and rule 2 as (x, b, outcome); a pair never seen together is answered by two lookups: first (a, none) gives x, then (x, b) gives the outcome.
Learning stores a pair when the memory does not know it, OR knows a similar pair but gives a different outcome (first run of this model, without the second test, left pairs that differ in one input unstored). `fam_t` = how large a share of the known wires must match before the block is called familiar (0.75 is the block's old policy; a cue of two inputs needs more).
Every device answer is compared with MemRef (the Python copy of the block), so this can run on the card unchanged. Usage: python3 tools/hexn_combo_v1.py [SEEDS]"""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_mem_host_v1 as H
from hexn_mem_write_v1 import RefLink
W = 6; AM = (1 << W) - 1; LOW12 = (1 << 2 * W) - 1; FULLM = (1 << H.NB) - 1
def hd(a, b): return H.pc((a ^ b) & AM)
def codebook(r, n=7, dmin=3):
    while True:
        t = [r.getrandbits(W) for _ in range(n)]
        if all(hd(t[i], t[j]) >= dmin for i in range(n) for j in range(i)): return t
def view(r, v, q, bits): return sum((((v >> j) & 1) ^ (1 if r.random() < q else 0)) << j for j in range(bits))
def nearest(book, v): return min(range(len(book)), key=lambda s: hd(book[s], v))
def run(link, q, seed, acq=7, nc=3, hold=2, reps=14, fam_t=0.75, tol=2):
    r = random.Random(seed * 7919 + 11); book = codebook(r)
    A = [1, 2, 3, 4]; X = [5, 6]; B = [1, 2]; Y = [3, 4]; NONE = 0
    g = {a: X[i % 2] for i, a in enumerate(A)}; r.shuffle(A)
    g = {a: X[i % 2] for i, a in enumerate(sorted(A))}
    while True:
        h = {(x, b): r.choice(Y) for x in X for b in B}
        if len(set(h.values())) == 2: break
    truth = lambda a, b: h[(g[a], b)]
    pairs = [(a, b) for a in sorted(A) for b in B]; held = r.sample(pairs, hold); seen = [p for p in pairs if p not in held]
    d = H.Dev(link); ref = H.MemRef(); bad = checks = 0
    def chk(got, want):
        nonlocal bad, checks; checks += 1; bad += got != want
    def look(pats, mask):
        d.clr(); ref.clr()
        for p in pats: d.watch(p, mask); ref.watch(p, mask)
    def recall():
        got = d.recall(); chk(got, ref.recall()); bid, bm, kn, sm, cue, rec, dev = got
        fam = bid != 15 and bm > sm and bm >= fam_t * kn; tie = bid != 15 and bm == sm and bm >= fam_t * kn
        return fam, tie, (rec >> 2 * W) & AM
    def pat(i1, i2, o): return book[i1] | (book[i2] << W) | (book[o] << 2 * W)
    def learn(examples):
        d.clrall(); ref.clrall(); stored = 0
        for _ in range(reps):
            for (i1, i2, o) in r.sample(examples, len(examples)):
                look([view(r, pat(i1, i2, o), q, H.NB) for _ in range(acq)], FULLM); clean = ref.cue()
                look([clean & LOW12], LOW12); fam, tie, out = recall()
                new = (not fam and not tie) or (fam and hd(out, clean >> 2 * W) > tol)      # not known, or known but with a different outcome
                if new and stored < H.M:
                    look([clean], FULLM); d.save(stored); ref.save(stored); stored += 1
        return stored
    def ask(i1, i2):                                                          # noisy looks at the two inputs, low-12 cue, answer symbol or None
        look([view(r, book[i1] | (book[i2] << W), q, 2 * W) for _ in range(nc)], LOW12); fam, tie, out = recall()
        return ("tie", None) if tie else (("unknown", None) if not fam else ("ok", nearest(book, out)))
    res = {}
    def tally(name, outcomes):
        n = len(outcomes) or 1
        res[name + "_right"] = sum(o[0] == "ok" and o[1] == o[2] for o in outcomes) / n
        res[name + "_wrong"] = sum(o[0] == "ok" and o[1] != o[2] for o in outcomes) / n
        res[name + "_none"] = sum(o[0] != "ok" for o in outcomes) / n
    n_direct = learn([(a, b, truth(a, b)) for a, b in seen]); T = 30
    tally("direct_seen", [ask(a, b) + (truth(a, b),) for a, b in seen for _ in range(T)])
    tally("direct_held", [ask(a, b) + (truth(a, b),) for a, b in held for _ in range(T)])
    n_chain = learn([(a, NONE, g[a]) for a in sorted(A)] + [(x, b, h[(x, b)]) for x in X for b in B])
    def chain(a, b):
        s1, x = ask(a, NONE)
        if s1 != "ok": return (s1, None)
        return ask(x, b)                                                       # the recalled symbol is passed on exactly
    tally("chain_all", [chain(a, b) + (truth(a, b),) for a, b in pairs for _ in range(T)])
    tally("chain_held", [chain(a, b) + (truth(a, b),) for a, b in held for _ in range(T)])
    res.update(slots_direct=n_direct, slots_chain=n_chain, bad=bad, checks=checks)
    return res
KEYS = ("direct_seen_right", "direct_held_right", "direct_held_wrong", "direct_held_none", "chain_all_right", "chain_all_wrong", "chain_all_none", "chain_held_right", "chain_held_wrong", "chain_held_none", "slots_direct", "slots_chain")
def study(seeds, q, **kw):
    rows = [run(RefLink(), q, s, **kw) for s in range(seeds)]
    return {k: sum(x[k] for x in rows) / len(rows) for k in KEYS}, sum(x["bad"] for x in rows), sum(x["checks"] for x in rows)
if __name__ == "__main__":
    seeds = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    print("mean of %d seeds; noise q per wire; 7 looks to learn, 3 looks to ask; 2 of the 8 (a,b) pairs are never shown to the DIRECT table" % seeds)
    print("q    | " + " | ".join(KEYS))
    tb = tc = 0
    for ft in (0.75, 0.85, 0.92):
        for q in (0.0, 0.05, 0.10, 0.15):
            m, b, c = study(seeds, q, fam_t=ft); tb += b; tc += c
            print("%.2f | " % q + " | ".join(("%.2f" % m[k]) for k in KEYS) + "   (familiar at %.2f)" % ft)
    print("board answers that differ from the Python rules: %d of %d" % (tb, tc))
