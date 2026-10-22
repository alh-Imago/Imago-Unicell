"""Host side of the SAVE AND RECALL memory test (board top v11, rtl/hexn_mem_v1.v). One suite, several links: the real serial port (tools/hexn_tang_mem_v1.py), the simulation (tools/hexn_mem_check_v1.py, rtl/tb_hexn_bytes_v1.v) and a Python stand-in (--selftest). Commands: 0x20 CLR, 0x21 WATCH [b0 b1 b2 m0 m1 m2], 0x22 SAVE [n], 0x23 RECALL -> 13 bytes, 0x24 DUMP [n] -> 4 bytes, 0x25 CLRALL; each of CLR/WATCH/SAVE/CLRALL answers 0xA5.
The suite never depends on what the board answers while it runs (so it can be recorded and replayed), then compares EVERY answer with MemRef, a Python copy of the block's exact rules, and tabulates what the host policy (familiar if the best slot's matches / known wires >= 0.75, the best strictly ahead of the second; margin variant 0.12) makes of it."""
import random
NB, M = 18, 8
def pc(v): return bin(v).count("1")
class MemRef:
    def __init__(self): self.c = [0] * NB; self.known = 0; self.slot = [0] * M; self.valid = [0] * M
    def clr(self): self.c = [0] * NB; self.known = 0
    def clrall(self): self.valid = [0] * M
    def watch(self, bits, mask):
        self.known |= mask
        for j in range(NB):
            if mask >> j & 1: self.c[j] = max(-7, min(7, self.c[j] + (1 if bits >> j & 1 else -1)))
    def cue(self): return sum(1 << j for j in range(NB) if self.c[j] > 0)
    def save(self, n): self.slot[n] = self.cue(); self.valid[n] = 1
    def recall(self):
        cue = self.cue(); best_id, best, second = 15, 0, 0
        for s in range(M):
            if self.valid[s]:
                m = pc(~(cue ^ self.slot[s]) & self.known & ((1 << NB) - 1))
                if m > best: second, best, best_id = best, m, s
                elif m > second: second = m
        rec = self.slot[best_id] if best_id < M else 0
        return (best_id, best, pc(self.known), second, cue, rec, (cue ^ rec) & self.known)
    def dump(self, n): return (self.valid[n], self.slot[n])
def b3(v): return [v & 255, (v >> 8) & 255, (v >> 16) & 255]
def from3(d): return d[0] | (d[1] << 8) | (d[2] << 16)
class Dev:
    """a link plus the commands"""
    def __init__(self, link): self.l = link
    def ack(self): return self.l.read(1)[0]
    def clr(self): self.l.write(bytes([0x20])); return self.ack()
    def clrall(self): self.l.write(bytes([0x25])); return self.ack()
    def watch(self, bits, mask): self.l.write(bytes([0x21] + b3(bits) + b3(mask))); return self.ack()
    def save(self, n): self.l.write(bytes([0x22, n])); return self.ack()
    def recall(self):
        self.l.write(bytes([0x23])); d = self.l.read(13); return (d[0], d[1], d[2], d[3], from3(d[4:7]), from3(d[7:10]), from3(d[10:13]))
    def dump(self, n): self.l.write(bytes([0x24, n])); d = self.l.read(4); return (d[0] & 1, from3(d[1:4]))
ROWS = [(1, .15, 1, .15, 0, 0), (3, .15, 1, .15, 0, 0), (8, .15, 1, .15, 0, 0), (8, .15, 3, .15, 0, 0), (8, .15, 1, .15, .3, 0), (8, .15, 1, .15, .5, 0), (8, .15, 3, .15, .5, 0), (8, .15, 3, .15, 0, 2), (8, .15, 3, .15, 0, 4), (8, .25, 3, .25, .3, 2)]
def noisy(r, obj, q): return sum(((obj >> j & 1) ^ (1 if r.random() < q else 0)) << j for j in range(NB))
def suite(link, tries, seed=1, rows=ROWS):
    d = Dev(link); ref = MemRef(); bad = checks = 0; table = []; first_bad = []
    def chk(name, got, want):
        nonlocal bad, checks; checks += 1
        if got != want:
            bad += 1
            if len(first_bad) < 5: first_bad.append((name, got, want))
    for ri, (ws, qs, nc, qc, hide, chg) in enumerate(rows):
        r = random.Random(seed * 1000 + ri); objs = [r.getrandbits(NB) for _ in range(M)]; d.clrall(); ref.clrall()
        for n in range(M):
            d.clr(); ref.clr()
            for _ in range(ws): b = noisy(r, objs[n], qs); d.watch(b, (1 << NB) - 1); ref.watch(b, (1 << NB) - 1)
            d.save(n); ref.save(n); chk("dump slot %d" % n, d.dump(n), ref.dump(n))
        res = {"id": 0, "fam": 0, "dev": 0, "tchg": 0, "idok": 0}; novel = {0: 0, 12: 0}
        for t in range(tries):
            k = r.randrange(M); o = objs[k]; known = [j for j in range(NB) if r.random() >= hide]
            if len(known) < 3: known = [0, 1, 2]
            mask = sum(1 << j for j in known); ch = r.sample(range(NB), chg) if chg else []
            for j in ch: o ^= 1 << j
            d.clr(); ref.clr()
            for _ in range(nc): b = noisy(r, o, qc); d.watch(b, mask); ref.watch(b, mask)
            got = d.recall(); want = ref.recall(); chk("recall row %d try %d" % (ri, t), got, want)
            bid, bm, kn, sm, cue, rec, dev = got
            ok = bid != 15 and bm > sm and bm >= 0.75 * kn
            res["fam"] += ok; res["id"] += ok and bid == k
            if ok and bid == k: res["dev"] += pc(dev); res["tchg"] += sum(1 for j in ch if j in known); res["idok"] += 1
            for mg in (0, 12):
                ok2 = ok and (bm - sm) * 100 >= mg * kn
                novel[mg] += 0   # filled by the novel pass below
        nv = {0: 0, 12: 0}
        for t in range(tries):
            o = r.getrandbits(NB); known = [j for j in range(NB) if r.random() >= hide]
            if len(known) < 3: known = [0, 1, 2]
            mask = sum(1 << j for j in known); d.clr(); ref.clr()
            for _ in range(nc): b = noisy(r, o, qc); d.watch(b, mask); ref.watch(b, mask)
            got = d.recall(); want = ref.recall(); chk("novel row %d try %d" % (ri, t), got, want)
            bid, bm, kn, sm, cue, rec, dev = got
            for mg in (0, 12): nv[mg] += bid != 15 and bm > sm and bm >= 0.75 * kn and (bm - sm) * 100 >= mg * kn
        n = max(1, res["idok"]); table.append((ws, qs, nc, qc, hide, chg, res["id"] / tries, res["dev"] / n, res["tchg"] / n, nv[0] / tries, nv[12] / tries))
    return bad, checks, table, first_bad
def show(table):
    print("save: WS windows at noise qs | cue: NC windows, noise qc, hide share, changed wires | right slot found (best strictly ahead, matches >= 0.75 of known) | deviation reported vs true changed | never-saved object called familiar (no margin / margin 12 percent)")
    for ws, qs, nc, qc, hide, chg, idr, dv, tc, n0, n12 in table: print("WS=%d qs=%.2f | NC=%d qc=%.2f hide=%.1f chg=%d | ID %.3f | dev %.2f vs true %.2f | novel %.3f / %.3f" % (ws, qs, nc, qc, hide, chg, idr, dv, tc, n0, n12))
