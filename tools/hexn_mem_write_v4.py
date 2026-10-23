"""(v4: clone of hexn_mem_write_v3.py, left untouched; the policy list is changed to compare 4 looks with 7 looks (an ODD number of looks cannot tie, and the block turns a tie into 0). See tools/hexn_mem_write_odd_v1.py.)"""
"""WRITE RULE v3 (= v2, but a slot number outside 0..M-1 from the board counts as a differing answer and the run goes on; v2 crashed on it) = v1 (tools/hexn_mem_write_v1.py) plus MERGE ON STORE. Host policy on the same memory commands, no new hardware.
Why: in v1 an object judged new from a noisy view was sometimes stored a second time; two near-identical slots then tie, so neither is 'strictly ahead' and the object is never called familiar again (and a third copy may follow).
Merge rule: when a new object is about to be stored (view >= min_known wires, after acq look windows), DUMP every slot and find the slots within md wires of the acquired view. If there are some, do not take a new slot: blend the nearest one (watch its stored bits wold times, then the new view's windows, SAVE back to the same slot), and retire any other near slot (KILL: save the complement of the merged pattern, strength 0, so it is reused first and can no longer tie). The block has no clear-one-slot command, hence the complement. If none is near, store as in v1.
Policies: (min_known, acq, evict, fade, md, kill)  with md = 0 meaning no merge.
Usage: python3 tools/hexn_mem_write_v3.py [SEEDS]   (Python only)"""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_mem_host_v1 as H
from hexn_mem_write_v1 import RefLink, event_stream
NB, M, P = H.NB, H.M, 12
FULL = (1 << NB) - 1
WOLD = 2
POLICIES = {
    "v1: 4 looks (the old default)":               (16, 4, "weak", 10, 0, False),
    "v1: 7 looks":                                 (16, 7, "weak", 10, 0, False),
    "merge md2 retire, 4 looks (old)":             (16, 4, "weak", 10, 2, True),
    "merge md2 retire, 7 looks":                   (16, 7, "weak", 10, 2, True),
    "merge md3 retire, 4 looks (old best)":        (16, 4, "weak", 10, 3, True),
    "merge md3 retire, 7 looks":                   (16, 7, "weak", 10, 3, True)}
def run(link, policy, seed=1, T=400, nc=3, qc=0.15):
    mk, acq, ev, fade, md, kill = policy; d = H.Dev(link); ref = H.MemRef(); r, objs, w1, w2 = event_stream(seed, T)
    d.clrall(); ref.clrall(); owner = [None] * M; dead = [False] * M; strength = [0] * M; age = [0] * M; fifo = 0
    bad = checks = 0; first_bad = []; log = []; merges = wrongmerge = 0
    def chk(name, got, want):
        nonlocal bad, checks; checks += 1
        if got != want:
            bad += 1
            if len(first_bad) < 5: first_bad.append((name, got, want))
    def put(s, pattern):          # store an exact pattern in slot s (one watch window, counters become +-1)
        d.clr(); ref.clr(); d.watch(pattern, FULL); ref.watch(pattern, FULL); d.save(s); ref.save(s); chk("dump put", d.dump(s), ref.dump(s))
    for t in range(T):
        w = w1 if t < T // 2 else w2; k = r.choices(range(P), w)[0]; o = objs[k]
        if r.random() < 0.1: o ^= sum(1 << j for j in r.sample(range(NB), 2))
        hide = r.choice([0.0, 0.0, 0.3]); known = [j for j in range(NB) if r.random() >= hide]
        if len(known) < 3: known = [0, 1, 2]
        mask = sum(1 << j for j in known)
        d.clr(); ref.clr()
        for _ in range(nc): b = H.noisy(r, o, qc); d.watch(b, mask); ref.watch(b, mask)
        got = d.recall(); chk("recall %d" % t, got, ref.recall()); bid, bm, kn, sm, cue, rec, dev = got
        fam = bid < M and bm > sm and bm >= 0.75 * kn; stored = k in owner
        if fam and not dead[bid]: log.append((t, k, "hit" if owner[bid] == k else ("wrong" if stored else "falsefam"))); strength[bid] = min(9, strength[bid] + 3); age[bid] = t
        else:
            log.append((t, k, "novel"))
            if len(known) >= mk:
                d.clr(); ref.clr()
                for _ in range(acq): b = H.noisy(r, o, qc); d.watch(b, mask); ref.watch(b, mask)
                view = ref.cue(); near = []
                if md:
                    for s in range(M):
                        if ref.valid[s] and not dead[s]:
                            got_d = d.dump(s); chk("scan %d" % t, got_d, ref.dump(s))
                            dist = H.pc((got_d[1] ^ view) & mask)
                            if dist <= md: near.append((dist, s))
                if near:
                    near.sort(); s = near[0][1]; merges += 1; wrongmerge += owner[s] != k
                    old = ref.slot[s]; d.clr(); ref.clr()
                    for _ in range(WOLD): d.watch(old, FULL); ref.watch(old, FULL)
                    for _ in range(acq): b = H.noisy(r, o, qc); d.watch(b, mask); ref.watch(b, mask)
                    d.save(s); ref.save(s); chk("merge dump %d" % t, d.dump(s), ref.dump(s)); strength[s] = min(9, strength[s] + 3); age[s] = t
                    if kill:
                        merged = ref.slot[s]
                        for _, s2 in near[1:]: put(s2, (~merged) & FULL); dead[s2] = True; owner[s2] = None; strength[s2] = 0; age[s2] = -1
                else:
                    free = [s for s in range(M) if (owner[s] is None and not ref.valid[s]) or dead[s]]
                    if free: s = free[0]
                    elif ev == "fifo": s = fifo % M; fifo += 1
                    elif ev == "weak": s = min(range(M), key=lambda x: (strength[x], age[x]))
                    else: s = None
                    if s is not None:
                        d.clr(); ref.clr()
                        for _ in range(acq): b = H.noisy(r, o, qc); d.watch(b, mask); ref.watch(b, mask)
                        d.save(s); ref.save(s); owner[s] = k; dead[s] = False; strength[s] = 3; age[s] = t; chk("dump %d" % t, d.dump(s), ref.dump(s))
        if fade and t % fade == fade - 1: strength = [max(0, x - 1) for x in strength]
    for s in range(M): chk("final dump %d" % s, d.dump(s), ref.dump(s))
    late = [e for e in log if e[0] >= T * 3 // 4 and e[1] in (4, 5, 6, 7)]; old = [e for e in log if e[0] >= T * 3 // 4 and e[1] in (0, 1, 2, 3)]
    early = [e for e in log if T // 4 <= e[0] < T // 2 and e[1] in (0, 1, 2, 3)]
    rate = lambda L: sum(1 for e in L if e[2] == "hit") / max(1, len(L))
    live = [s for s in range(M) if owner[s] is not None and not dead[s]]; held = set(owner[s] for s in live)
    err = sum(H.pc((ref.slot[s] ^ objs[owner[s]]) & FULL) for s in live) / max(1, len(live))
    return dict(hot2=rate(late), hot1_early=rate(early), old_late=rate(old), hold_hot2=len(held & {4, 5, 6, 7}), hold_hot1=len(held & {0, 1, 2, 3}),
                dup=sum(1 for x in held if [owner[s] for s in live].count(x) > 1), err=err, wrong=sum(1 for e in log if e[2] == "wrong") / len(log),
                falsefam=sum(1 for e in log if e[2] == "falsefam") / len(log), merges=merges, wrongmerge=wrongmerge, dead=sum(dead), bad=bad, checks=checks, fb=first_bad)
KEYS = ("hot2", "hot1_early", "old_late", "hold_hot2", "hold_hot1", "dup", "err", "wrong", "falsefam", "merges", "wrongmerge", "dead")
def show(rows):
    print("%-46s | hot now: right slot | hot1 early | old late | hot2 held/4 | hot1 held | duplicates | wires wrong/slot | wrong slot named | never-stored called familiar | merges | merges of two DIFFERENT objects | retired slots at end" % "policy")
    for name, a in rows: print("%-46s | %.2f | %.2f | %.2f | %.2f | %.2f | %.2f | %.2f | %.3f | %.3f | %.1f | %.2f | %.1f" % ((name,) + tuple(a[k] for k in KEYS)))
def study(link_factory, seeds, T=400):
    rows = []
    for name, pol in POLICIES.items():
        acc = {}
        for sd in seeds:
            a = run(link_factory(), pol, sd, T)
            for k in KEYS: acc[k] = acc.get(k, 0) + a[k] / len(seeds)
        rows.append((name, acc))
    return rows
if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    show(study(RefLink, range(1, n + 1)))
