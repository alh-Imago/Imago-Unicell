# Hex-N: stimulus + expected result from the Python counted-detector model for the RTL check (tools/hexn_tally_rtl_check_v1.sh)
import sys, random, importlib.util, os
sys.path.insert(0, '/home/claude/hexn-wt/tools')
sp = importlib.util.spec_from_file_location('t4', '/home/claude/hexn-wt/tools/hexn_tally_v4.py'); t4 = importlib.util.module_from_spec(sp); sp.loader.exec_module(t4)
t3 = t4.t3; v12 = t4.v12; NB = t4.NB; CAP = t4.CAP
seed = int(sys.argv[1]); K = 4; S = 16; q = 0.15; det = int(sys.argv[2])
rnd = random.Random(seed); tpl = t4.templates(rnd, K, 4)
train = [(v12.sample(rnd, tpl[y], q), y) for y in range(K) for _ in range(S)]
sh = random.Random(seed + 5); test = [(v12.sample(rnd, tpl[y], q), y) for y in range(K) for _ in range(50)]; sh.shuffle(train)
cnt = [0] * NB; T = 8
for bits, y in train:
    for j in range(NB):
        if bits[j]: cnt[j] = max(-CAP, min(CAP, cnt[j] + ((K - 1) if y == det else -1)))
w = [1 if c >= T else -1 if c <= -T else 0 for c in cnt]
ao = ac = no = nc = 0
with open('/tmp/tally_stim.txt', 'w') as f:
    for bits, y in train: f.write("%d %s\n" % (int(y == det), ''.join(str(bits[NB - 1 - j]) for j in range(NB))))
for bits, y in train:
    sc = sum(w[j] * bits[j] for j in range(NB))
    if y == det: ao += sc; no += 1
    else: ac += sc; nc += 1
wp = sum(1 << j for j in range(NB) if w[j] > 0); wn = sum(1 << j for j in range(NB) if w[j] < 0)
print(wp, wn, ao, ac, no, nc)
