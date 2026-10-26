"""hexn_engram_v1: STORE and RECALL a learned one-layer network as a two-part engram (Python model only; new file; imports the untouched hexn_depth_v1.py / hexn_layer_v2.py).
Two parts, after Alan's two-tier intention (26 Oct): the DEEP part = the network's settings packed into bits (per cell: 20 lanes x 2 bits + a 6-bit threshold = 46 bits);
the QUICK part (key) = the network's ACTIVATION PATTERN on P fixed probe patterns (which output cells fire, 1 bit per cell per probe).
ASSUMPTIONS (mine, not decided by Alan): the fixed probe set is shared by all engrams; the key is computed with clean probes when stored and with noisy probes when asked; recall = the stored key with the smallest Hamming distance.
Tests: (1) pack/unpack gives a network whose answers equal the original's on every presentation; the size in bits. (2) E learned networks (E different pattern sets) are stored; a network whose settings were DAMAGED (k random settings changed) is asked for its key with noisy probes (probe noise q);
the nearest stored key is recalled and its settings are loaded: how often is the right engram recalled, and does task accuracy return to the original?
Usage: python3 tools/hexn_engram_v1.py E M tries"""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_layer_v2 as L
import hexn_layer_learn_v2 as LL
import hexn_depth_v1 as D
TB = 6                                        # threshold bits
def pack(net):
    bits = []
    for w, t in net["l1"]:
        assert 0 <= t < (1 << TB)
        for s in w: bits += [s & 1, s >> 1]
        bits += [(t >> i) & 1 for i in range(TB)]
    return bits
def unpack(bits, ncell):
    cell = 2 * L.NIN + TB; l1 = []
    for c in range(ncell):
        b = bits[c * cell:(c + 1) * cell]; w = [b[2 * i] | (b[2 * i + 1] << 1) for i in range(L.NIN)]
        assert all(s in (0, 1, 2) for s in w); l1.append((w, sum(b[2 * L.NIN + i] << i for i in range(TB))))
    return {"l1": l1, "l2": []}
def learn(seed, M, tries, warm=30, per=4, q=0.1):
    rnd = random.Random(seed); pats = [[int(rnd.random() < 0.5) for _ in range(L.NIN)] for _ in range(M)]
    tr = random.Random(seed + 100); lr = random.Random(seed + 7)
    def rew(net, batch):
        s = 0.0
        for y, bits in batch:
            out = D.present1(net, bits); a = L.answer(out); oth = max([o for j, o in enumerate(out) if j != y] or [0])
            s += max(-1.0, min(1.0, (out[y] - oth) / 14.0)) + (1.0 if a == y else (-0.25 if a == -1 else -0.5))
        return s
    batch = lambda: LL.make_batch(tr, pats, per, q)
    best = max((D.rand1(lr, M) for _ in range(warm)), key=lambda n: rew(n, batch()))
    for _ in range(tries - warm):
        c = D.mutate1(best, lr); b = batch()
        if rew(c, b) >= rew(best, b): best = c
    return best, pats
def accuracy(net, pats, q, seed, per=60):
    r = random.Random(seed); ok = 0; n = 0
    for y, bits in LL.make_batch(r, pats, per, q): ok += L.answer(D.present1(net, bits)) == y; n += 1
    return ok / n
def fingerprint(net, probes): return [int(o > 0) for p in probes for o in D.present1(net, p)]
def damage(net, rnd, k):
    l1 = [(list(w), t) for w, t in net["l1"]]
    for _ in range(k):
        i = rnd.randrange(len(l1)); w, t = l1[i]
        if rnd.random() < 0.8: j = rnd.randrange(len(w)); w[j] = rnd.choice([s for s in (0, 1, 2) if s != w[j]])
        else: t = max(1, t + rnd.choice((-3, -2, -1, 1, 2, 3)))
        l1[i] = (w, t)
    return {"l1": l1, "l2": []}
if __name__ == "__main__":
    E, M, tries = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]); P = 6
    pr = random.Random(999); probes = [[int(pr.random() < 0.5) for _ in range(L.NIN)] for _ in range(P)]
    eng = []
    for e in range(E):
        net, pats = learn(e, M, tries); eng.append({"net": net, "pats": pats, "bits": pack(net), "key": fingerprint(net, probes)})
        print(f"engram {e}: learned, right at noise 0.1 = {accuracy(net, pats, 0.1, 5):.2f}", flush=True)
    nb = len(eng[0]["bits"]); print(f"\nDEEP part: {nb} bits per engram ({M} cells x {2 * L.NIN + TB}); QUICK key: {len(eng[0]['key'])} bits ({P} probes x {M} cells); 64-byte word = 512 bits -> {'fits' if nb <= 512 else 'does NOT fit'}")
    bad = 0
    for e, g in enumerate(eng):
        back = unpack(g["bits"], M); same = all(L.answer(D.present1(back, b)) == L.answer(D.present1(g["net"], b)) and D.present1(back, b) == D.present1(g["net"], b) for _, b in LL.make_batch(random.Random(3), g["pats"], 30, 0.15)); bad += not same
    print(f"TEST 1 pack/unpack: {E - bad} of {E} unpacked networks give identical output counts on 90 noisy presentations")
    ds = [sum(a != b for a, b in zip(eng[i]["key"], eng[j]["key"])) for i in range(E) for j in range(i)]
    print(f"stored keys: Hamming distance between pairs, min {min(ds)} mean {sum(ds) / len(ds):.1f} max {max(ds)} (of {len(eng[0]['key'])} bits)")
    print("\nTEST 2 recall of a DAMAGED network: k settings changed, probes noisy at q.  recalled = right engram; acc before/after = task accuracy (noise 0.1) of the damaged net / of the net loaded from the recalled engram; orig = undamaged")
    print(" k    q  | recalled | acc before | acc after | orig")
    rnd = random.Random(42)
    for k in (0, 3, 6, 12):
        for q in (0.0, 0.05, 0.1):
            hit = 0; n = 0; ab = aa = ao = 0.0
            for e, g in enumerate(eng):
                for rep in range(5):
                    dn = damage(g["net"], rnd, k); noisy_probes = [L.noisy(rnd, p, q) for p in probes]; fp = fingerprint(dn, noisy_probes)
                    cand = min(range(E), key=lambda j: sum(a != b for a, b in zip(fp, eng[j]["key"]))); hit += cand == e; n += 1
                    loaded = unpack(eng[cand]["bits"], M); ab += accuracy(dn, g["pats"], 0.1, 7); aa += accuracy(loaded, g["pats"], 0.1, 7); ao += accuracy(g["net"], g["pats"], 0.1, 7)
            print(f"{k:2d} {q:.2f} | {hit}/{n} | {ab / n:.2f} | {aa / n:.2f} | {ao / n:.2f}", flush=True)
