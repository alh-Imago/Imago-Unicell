"""(v3, clone of hexn_tiers_v2.py which is left untouched.) ISSUE 3: the fast tier compares only WF of the 64 wires (WF=18 is the existing 18-wire block, 8 slots) with a distance limit TF, so it can answer for the WRONG object. Counts wrong answers (hot or RAM) and never-seen arrivals called known. Python model only.
(v2 text follows.) The two hazards v1 only listed are now REAL in the model. Python model only; nothing here has run on a board.
Every object has a VALUE (a counter standing for what was learned) that really changes on an update. Copies: the fast block holds a copy, the RAM holds a copy in each of the T tables (one logical RAM value per object while any table copy exists).
Hazard 1, stale RAM copy: with write-back the RAM value is old until the pattern leaves the fast block. The main host never sees it (it asks the fast block first; this is CHECKED: 'stale main' must be 0). A SECOND READER that looks only at the RAM (another agent, a snapshot, a later power-up) does see it: 'stale other' = share of its reads that return an old value; 'at risk' = mean number of updated-but-not-yet-written patterns (lost if power fails).
Hazard 2, overwritten copy: a new arrival can overwrite an object in a full RAM bucket while the object is still in the fast block (an 'orphan': no RAM copy left). Write-back of an orphan: 'naive' = the update is lost and the object is forgotten; 'reinsert' = it is put back into the RAM first (which may overwrite another).
Update policies: through = write RAM at once; back = write on leaving the fast block (naive or reinsert); back+reinsert+flush = also write every dirty pattern every FLUSH lookups.
RAM costs as v1 (read together 9.9 + 2.22 x (T-1) MEASURED; write ASSUMED equal). Usage: python3 tools/hexn_tiers_v2.py [SEEDS]"""
import sys, numpy as np
W, T, B, THR, FLIPS = 64, 3, 4, 8, 2
RAM_COST = 9.9 + 2.22 * (T - 1)
def run(seed, S, policy, WF=64, TF=8, K=11, n=4000, q=5000, zipf=1.0, upd_p=0.2, other_p=0.05, flush=200, new_p=0.10):
    rng = np.random.default_rng(seed)
    objs = rng.integers(0, 2, (n + q, W), dtype=np.uint8); wires = [rng.choice(W, K, replace=False) for _ in range(T)]; fw = rng.choice(W, WF, replace=False); pw = 1 << np.arange(K)
    tab = -np.ones((T, 1 << K, B), dtype=np.int32); ptr = np.zeros((T, 1 << K), dtype=np.int32)
    copies = {}; ram_val = {}; val_true = {}; hot = []; hot_val = {}; dirty = set()
    st = dict(cycles=0.0, ram_w=0, ram_r=0, hits=0, orphans=0, lost=0, reinserts=0, stale_main=0, other_n=0, stale_other=0, risk=0.0, wrong=0, hotwrong=0, right=0, unk=0, kq=0, false_known=0, newq=0)
    def ram_insert(i, value):
        for t in range(T):
            a = int(objs[i][wires[t]] @ pw); slot = ptr[t, a] % B; old = int(tab[t, a, slot])
            if old >= 0:
                copies[old] -= 1
                if copies[old] == 0 and old in hot_val: st["orphans"] += 1            # its RAM copy is gone while the fast block still holds it
            tab[t, a, slot] = i; ptr[t, a] += 1; copies[i] = copies.get(i, 0) + 1
        ram_val[i] = value
    for i in range(n): val_true[i] = 0; ram_insert(i, 0)
    p = 1.0 / np.arange(1, n + 1) ** zipf; p /= p.sum(); order = [rng.permutation(n), rng.permutation(n)]; next_new = n
    def write_back(i):
        if copies.get(i, 0) > 0: ram_val[i] = hot_val[i]
        elif policy.startswith("back-naive"): st["lost"] += 1; st["cycles"] -= RAM_COST; st["ram_w"] -= 1      # nothing is written; the update is lost
        else: st["reinserts"] += 1; ram_insert(i, hot_val[i])
        st["cycles"] += RAM_COST; st["ram_w"] += 1
    def leave():
        while len(hot) > S:
            v = hot.pop(0)
            if v in dirty: dirty.discard(v); write_back(v)
            hot_val.pop(v, None)
    def ram_lookup(cue):
        cand = set()
        for t in range(T): cand.update(tab[t, int(cue[wires[t]] @ pw)].tolist())
        cand.discard(-1)
        if not cand: return None
        c = np.array(sorted(cand)); d = (objs[c] != cue).sum(1); j = int(d.argmin())
        return int(c[j]) if d[j] <= THR else None
    for k in range(q):
        is_new = rng.random() < new_p; st["cycles"] += 1
        i = (next_new if is_new else int(order[0 if k < q // 2 else 1][rng.choice(n, p=p)]))
        if is_new: next_new += 1
        cue = objs[i].copy(); cue[rng.choice(W, FLIPS, replace=False)] ^= 1; got = None; from_hot = False
        if hot:
            d = (objs[hot][:, fw] != cue[fw]).sum(1); j = int(d.argmin())
            if d[j] <= TF: got = hot[j]; from_hot = True; st["hits"] += 1; hot.append(hot.pop(j))
        if got is None:
            st["cycles"] += RAM_COST; st["ram_r"] += 1; got = ram_lookup(cue)
            if got is not None and S > 0:
                if got in hot_val: hot.remove(got); hot.append(got)      # already held (the narrow look missed it): move, never duplicate
                else: hot.append(got); hot_val[got] = ram_val[got]; leave()
        if is_new:
            st["newq"] += 1
            if got is not None: st["false_known"] += 1
            else:
                val_true[i] = 0; ram_insert(i, 0); st["ram_w"] += 1; st["cycles"] += RAM_COST
                if S > 0: hot.append(i); hot_val[i] = 0; leave()
        else:
            st["kq"] += 1
            if got is None: st["unk"] += 1
            else:
                st["right"] += got == i; st["wrong"] += got != i; st["hotwrong"] += from_hot and got != i
                seen = hot_val[got] if from_hot or got in hot_val else ram_val.get(got)
                st["stale_main"] += seen != val_true[got]
        if got is not None and not is_new and got == i and rng.random() < upd_p:      # a real update of the object's value
            val_true[i] += 1
            if i in hot_val:
                hot_val[i] = val_true[i]
                if policy == "through":
                    if copies.get(i, 0) > 0: ram_val[i] = val_true[i]; st["ram_w"] += 1; st["cycles"] += RAM_COST
                    else: st["reinserts"] += 1; ram_insert(i, val_true[i]); st["ram_w"] += 1; st["cycles"] += RAM_COST
                else: dirty.add(i)
            else: ram_val[i] = val_true[i]; st["ram_w"] += 1; st["cycles"] += RAM_COST
        if policy.endswith("flush") and (k + 1) % flush == 0:
            for v in list(dirty): dirty.discard(v); write_back(v)
        if rng.random() < other_p:                                                    # a second reader that only sees the RAM
            j = int(order[0 if k < q // 2 else 1][rng.choice(n, p=p)])
            if copies.get(j, 0) > 0: st["other_n"] += 1; st["stale_other"] += ram_val[j] != val_true[j]
        st["risk"] += len(dirty)
    kq = max(1, st["kq"])
    return dict(hit=st["hits"] / q, cycles=st["cycles"] / q, ram_w=st["ram_w"] / q, right=st["right"] / kq, wrong=st["wrong"] / kq, hotwrong=st["hotwrong"] / kq, false_known=st["false_known"] / max(1, st["newq"]), unknown=st["unk"] / kq, stale_main=st["stale_main"], stale_other=st["stale_other"] / max(1, st["other_n"]),
                at_risk=st["risk"] / q, orphans=1000 * st["orphans"] / q, lost=1000 * st["lost"] / q, reinserts=1000 * st["reinserts"] / q)
KEYS = ("hit", "cycles", "right", "wrong", "hotwrong", "false_known", "stale_main")
if __name__ == "__main__":
    seeds = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    print("policy back-reinsert, roomy RAM; fast tier compares WF wires with limit TF (cue has 2 flipped wires of 64)")
    print("fast slots | WF | TF | " + " | ".join(KEYS))
    for S, WF, TF in ((0, 64, 8), (8, 64, 8), (8, 18, 2), (8, 18, 1), (8, 32, 4), (32, 64, 8), (32, 18, 2), (32, 32, 4), (32, 48, 6), (128, 64, 8), (128, 18, 2), (128, 32, 4), (128, 48, 6)):
        r = [run(s, S, "back-reinsert", WF=WF, TF=TF) for s in range(seeds)]
        print(f"{S:<10} | {WF:<2} | {TF} | " + " | ".join("%.3f" % np.mean([x[k] for x in r]) for k in KEYS))
