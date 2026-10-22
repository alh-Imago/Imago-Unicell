"""WRITE RULE for the SAVE AND RECALL block (host policy on the board top v11 commands; no new hardware). Online learning: a stream of encounters (noisy, partly hidden, sometimes slightly changed views of 12 objects, popularity switching half way) arrives; for each one the host watches, recalls, and decides to (1) count a hit and strengthen the slot (familiar), or (2) store a new slot (novel). 8 slots only, so a rule for WHAT to keep is needed.
Rule parts (each switchable, to measure what it buys):  GUARD - store only from a nearly complete view (>= min_known wires visible), after extra look windows (acq), because a store writes 0 on every unseen wire;  EVICT - when full, overwrite the weakest slot;  FADE - every fade_every events every slot strength drops by 1, a hit adds gain (cap), so unused memories become the first to go.
Every board answer is compared with the Python copy of the block (MemRef), as in hexn_mem_host_v1.py.
Usage: python3 tools/hexn_mem_write_v1.py [SEEDS]   (Python only)"""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_mem_host_v1 as H
NB, M, P = H.NB, H.M, 12
FULL = (1 << NB) - 1
POLICIES = {   # name: (min_known, acq, evict, fade_every)
    "naive (store any, FIFO)":        (0, 1, "fifo", 0),
    "guard, stop when full":          (16, 4, "none", 0),
    "guard + weakest out (no fade)":  (16, 4, "weak", 0),
    "guard + weakest out + fade":     (16, 4, "weak", 10)}
def event_stream(seed, T):
    r = random.Random(seed * 7919 + 5); objs = [r.getrandbits(NB) for _ in range(P)]
    w1 = [6] * 4 + [2] * 4 + [1] * 4; w2 = [1] * 4 + [6] * 4 + [2] * 4
    return r, objs, w1, w2
def run(link, policy, seed=1, T=400, nc=3, qc=0.15, check=True):
    mk, acq, ev, fade = policy; d = H.Dev(link); ref = H.MemRef(); r, objs, w1, w2 = event_stream(seed, T)
    d.clrall(); ref.clrall(); owner = [None] * M; strength = [0] * M; age = [0] * M; fifo = 0
    bad = checks = 0; first_bad = []; log = []
    def chk(name, got, want):
        nonlocal bad, checks; checks += 1
        if got != want:
            bad += 1
            if len(first_bad) < 5: first_bad.append((name, got, want))
    for t in range(T):
        w = w1 if t < T // 2 else w2; k = r.choices(range(P), w)[0]; o = objs[k]
        if r.random() < 0.1: o ^= sum(1 << j for j in r.sample(range(NB), 2))      # a slightly changed view
        hide = r.choice([0.0, 0.0, 0.3]); known = [j for j in range(NB) if r.random() >= hide]
        if len(known) < 3: known = [0, 1, 2]
        mask = sum(1 << j for j in known)
        d.clr(); ref.clr()
        for _ in range(nc): b = H.noisy(r, o, qc); d.watch(b, mask); ref.watch(b, mask)
        got = d.recall(); chk("recall %d" % t, got, ref.recall()); bid, bm, kn, sm, cue, rec, dev = got
        fam = bid != 15 and bm > sm and bm >= 0.75 * kn; stored = k in owner
        if fam: log.append((t, k, "hit" if owner[bid] == k else ("wrong" if stored else "falsefam"))); strength[bid] = min(9, strength[bid] + 3); age[bid] = t
        else:
            log.append((t, k, "novel"))
            if len(known) >= mk:
                d.clr(); ref.clr()
                for _ in range(acq): b = H.noisy(r, o, qc); d.watch(b, mask); ref.watch(b, mask)
                free = [s for s in range(M) if owner[s] is None and not ref.valid[s]]
                if free: s = free[0]
                elif ev == "fifo": s = fifo % M; fifo += 1
                elif ev == "weak": s = min(range(M), key=lambda x: (strength[x], age[x]))
                else: s = None
                if s is not None:
                    d.save(s); ref.save(s); owner[s] = k; strength[s] = 3; age[s] = t; chk("dump %d" % t, d.dump(s), ref.dump(s))
        if fade and t % fade == fade - 1: strength = [max(0, x - 1) for x in strength]
    for s in range(M): chk("final dump %d" % s, d.dump(s), ref.dump(s))
    # scores
    late = [e for e in log if e[0] >= T * 3 // 4 and e[1] in (4, 5, 6, 7)]        # objects hot in phase 2, late in the run
    old = [e for e in log if e[0] >= T * 3 // 4 and e[1] in (0, 1, 2, 3)]
    allow = [e for e in log if e[0] >= T // 4 and e[0] < T // 2 and e[1] in (0, 1, 2, 3)]
    rate = lambda L: sum(1 for e in L if e[2] == "hit") / max(1, len(L))
    held = set(x for x in owner if x is not None); dup = M - len([s for s in range(M) if owner[s] is not None]) if False else sum(1 for x in held if owner.count(x) > 1)
    err = sum(H.pc((ref.slot[s] ^ objs[owner[s]]) & FULL) for s in range(M) if owner[s] is not None) / max(1, sum(1 for s in range(M) if owner[s] is not None))
    wrong = sum(1 for e in log if e[2] == "wrong") / len(log); ff = sum(1 for e in log if e[2] == "falsefam") / len(log)
    return dict(hot2=rate(late), hot1_early=rate(allow), old_late=rate(old), hold_hot2=len(held & {4, 5, 6, 7}), hold_hot1=len(held & {0, 1, 2, 3}), dup=sum(1 for x in held if owner.count(x) > 1), err=err, wrong=wrong, falsefam=ff, bad=bad, checks=checks, fb=first_bad)
def show(rows):
    print("%-34s | hot now: right slot found | hot1 early | old objects late | hot2 objects held (of 4) | old hot1 still held | duplicate slots | wires wrong per slot | wrong slot named | never-stored called familiar" % "policy")
    for name, a in rows:
        print("%-34s | %.2f | %.2f | %.2f | %.2f | %.2f | %.2f | %.2f | %.3f | %.3f" % (name, a["hot2"], a["hot1_early"], a["old_late"], a["hold_hot2"], a["hold_hot1"], a["dup"], a["err"], a["wrong"], a["falsefam"]))
class RefLink:
    """answers from the Python rules (for Python-only runs)"""
    def __init__(self): self.m = H.MemRef(); self.out = bytearray()
    def write(self, b):
        c = b[0]
        if c == 0x20: self.m.clr(); self.out.append(0xA5)
        elif c == 0x25: self.m.clrall(); self.out.append(0xA5)
        elif c == 0x21: self.m.watch(b[1] | (b[2] << 8) | (b[3] << 16), b[4] | (b[5] << 8) | (b[6] << 16)); self.out.append(0xA5)
        elif c == 0x22: self.m.save(b[1]); self.out.append(0xA5)
        elif c == 0x23: i, bm, kn, sm, cue, rec, dev = self.m.recall(); self.out += bytes([i, bm, kn, sm] + H.b3(cue) + H.b3(rec) + H.b3(dev))
        elif c == 0x24: v, bits = self.m.dump(b[1]); self.out += bytes([v] + H.b3(bits))
    def read(self, n): d = bytes(self.out[:n]); del self.out[:n]; return d
def study(link_factory, seeds, T=400):
    rows = []
    for name, pol in POLICIES.items():
        acc = None
        for sd in seeds:
            a = run(link_factory(), pol, sd, T)
            acc = {k: (acc[k] if acc else 0) + a[k] for k in a if k != "fb"} if acc else {k: a[k] for k in a if k != "fb"}
        rows.append((name, {k: v / len(seeds) for k, v in acc.items()}))
    return rows
if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    show(study(RefLink, range(1, n + 1)))
