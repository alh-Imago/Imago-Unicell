"""hexn_exact_v1: can the bank tell apart codes that differ by ONE bit, if each detector's threshold is set at its own exact total instead of the midpoint between own and other classes? (Python model only; no RTL; new file; uses hexn_layer1_v1, hexn_tang_script_v1.classify unchanged.)
Data: the 21 key command bytes of the MP3 remote (dense 8-bit codes, 24 pairs one bit apart), training samples = each press counted with its repeat frames (239 samples), as in hexn_layer1_v1.
Threshold rules (the weights are the bank's own learned weights in every case; only each detector's threshold changes; the loader can write any threshold, so the rule can run on the host):
  midpoint = the bank's rule (what the card's training bank does)
  exact    = threshold at the smallest forward total the detector gives its OWN class (slack 0): only an exact match fires
  graded   = exact minus 1 (slack 1): an exact match gives output 2, a code one wire off gives output 1, anything else 0  ->  answer 'exact' (2), 'close' (1) or 'unknown' (0)
  direct0 / direct1 = the weights are NOT learned but wired straight from each key's code (+1 where the bit is 1, -1 where it is 0, 0 on unused wires), threshold = the number of ones in the code minus the slack (0 or 1); the code table is the training data (slack is counted in WIRES: the bank's forward total is PL = 10 per wire, saturating at 127; a first version of this file used 1 forward unit instead of 1 wire, and a second let a code with a single 1-bit get threshold 0 (always on); both gave wrong numbers and are fixed (threshold at least 1); the loader can write such settings, as hexn_proto_v1 did for the model earlier)
Tests: (1) the 21 clean codes; (2) every single-bit flip of every code (168 cases), split into flips that land on ANOTHER VALID key (the bank cannot know it was an error: the dense code has no redundancy) and flips that land on an unused code; (3) 2000 random bytes that are at least 2 bits from every key.
Usage: python3 tools/hexn_exact_v1.py"""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_tang_script_v1 as S1, hexn_layer1_v1 as L
TABLE = [0x45, 0x46, 0x47, 0x44, 0x40, 0x43, 0x07, 0x15, 0x09, 0x16, 0x19, 0x0D, 0x0C, 0x18, 0x5E, 0x08, 0x1C, 0x5A, 0x42, 0x52, 0x4A]
def bits(c): return L.pad([(c >> j) & 1 for j in range(8)])
def model(rule):
    if rule.startswith("direct"):
        slack = int(rule[-1]); m = L.bank([(bits(c), i) for i, c in enumerate(TABLE)], 21)
        for k, c in enumerate(TABLE):
            m["wts"][k] = [1 if (c >> j) & 1 else -1 for j in range(8)] + [0] * 10; m["thr"][k] = max(1, S1.fwd_of(bin(c).count("1") - slack, m["AW"]))
        return m
    idx = {c: i for i, c in enumerate(TABLE)}; seen = L.ir_keys(True)
    train = [(bits(c), idx[c]) for c in seen if c in idx]; random.Random(0).shuffle(train); m = L.bank(train, 21)
    if rule != "midpoint":
        slack = 0 if rule == "exact" else 1
        for k in range(21):
            own = [S1.fwd_of(S1.net_of(m["wts"][k], b), m["AW"]) for b, y in train if y == k]; m["thr"][k] = max(1, min(own) - slack * S1.PL)
    return m
def answer(m, c):
    k, g = S1.classify(m, bits(c)); mx = max(g); return k, mx
def main():
    valid = set(TABLE); far = [x for x in range(256) if all(bin(x ^ c).count("1") >= 2 for c in TABLE)]; r = random.Random(1)
    print("21 key codes on 8 wires (24 pairs of codes are 1 bit apart); learned rules train on %d samples\n" % len(L.ir_keys(True)))
    print("rule     | clean right | 1-bit flips onto ANOTHER valid key (cannot be seen as errors): %d | 1-bit flips onto unused codes (120): unknown / ambiguous / answer = original / answer = other | random far codes: unknown" % sum(1 for c in TABLE for b in range(8) if c ^ (1 << b) in valid))
    for rule in ("midpoint", "exact", "graded", "direct0", "direct1"):
        m = model(rule); clean = sum(answer(m, c)[0] == i for i, c in enumerate(TABLE)); unk = amb = right = wrong = 0
        for i, c in enumerate(TABLE):
            for b in range(8):
                f = c ^ (1 << b)
                if f in valid: continue
                k, mx = answer(m, f)
                if mx == 0: unk += 1
                elif k == -1: amb += 1
                elif k == i: right += 1
                else: wrong += 1
        u = sum(answer(m, r.choice(far))[1] == 0 for _ in range(2000)) / 2000
        print("%-8s |   %2d / 21   |                                                              | %3d / %3d / %3d / %3d | %.2f" % (rule, clean, unk, amb, right, wrong, u))
if __name__ == "__main__": main()
