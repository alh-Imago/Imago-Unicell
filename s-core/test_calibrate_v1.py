"""sc_calibrate_v1: fit, best width, wrong-answer guard, save/load, and the sweep with a fake card (ledger #1398).  No board.  python3 test_calibrate_v1.py"""
import os, re, sys, tempfile, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import sc_calibrate_v1 as K
bad = 0
def check(name, cond):
    global bad
    print('%-100s %s' % (name, 'ok' if cond else 'FAIL')); bad += (not cond)

# 1. the real card data of 19 Nov (ledger #1397): 52 runs, 2 blocks x 8 slices, 8-lane units, 3 units
raw = open(os.path.join(HERE, 'profiles', 'example_2x8_nu3.raw.txt')).read()
card = {'slices': 8, 'blocks': 2, 'unit_lw': 3, 'units': 3, 'bitstream': 'sc_k7_fu2s8u8n3.bit'}
t = K.parse_raw(raw); p = K.make_profile('t', t, card)
check('52 runs parsed from 13 files', sum(len(v) for v in t.values()) == 52 and len(t) == 13)
check('speed-up lw1/2/3 about 1.92 / 3.57 / 6.2 (within 2%)', all(abs(a - b) / b < 0.02 for a, b in zip(p['speedup'], [1, 1.92, 3.57, 6.25])))
check('jobs at once: lw1 2, lw2 2, lw3 1', p['at_once'] == {'1': 2, '2': 2, '3': 1})
check('fit error on the real data: largest under 6%, mean under 2%', p['fit']['max_err'] < 0.06 and p['fit']['mean_err'] < 0.02)
check('best width measured: N = 1, 2, 4, 8 -> 3, 2, 2, 0', [K.best_width(p, n) for n in (1, 2, 4, 8)] == [3, 2, 2, 0])
check('predictions of #1397: N = 3, 5, 6, 7 -> 3, 3, 2, 0', [K.best_width(p, n) for n in (3, 5, 6, 7)] == [3, 3, 2, 0])

# 2. a wrong answer must never become a number
try: K.parse_raw('jobs_curve_L8_N2.json lw1 clocks=1000  1 of 2 jobs correct\n'); ok = False
except ValueError: ok = True
check('a run with a wrong job is refused by the parser', ok)
try: K.fit({(8, 2): {0: 100, 1: 60}}, 8); ok = False
except ValueError: ok = True
check('a fit without an N = 1 file is refused', ok)

# 3. save / load round trip
with tempfile.TemporaryDirectory() as d:
    path = K.save(p, d); q = K.load_profile(path)
    check('profile saved and loaded back unchanged', q == p and q['format'] == K.FORMAT)

# 4. the sweep with a fake card: 4 slices, 4-lane units (unit_lw 2), 2 units; true speed-ups 1, 1.9, 3.4; lw1 two at once, lw2 one at once
S_TRUE, SP, AT = 4, [1, 1.9, 3.4], {1: 2, 2: 1}
asked = []
def fake(f, w):
    L, N = (int(x) for x in re.match(r'jobs_curve_L(\d+)_N(\d+)', f).groups())
    asked.append((f, w)); t0 = 25000 * L
    c = math.ceil(N / (min(N, S_TRUE) if w == 0 else AT[w])) * t0 / SP[w]
    return str(int(c)), '%d of %d jobs correct' % (N, N), S_TRUE
lines = K.sweep(fake, K.QUICK, lambda s: min(2, int(math.log2(s))), lambda x: None)
check('sweep asked every file at widths 0..2 only (unit 2**2 lanes): 4 files x 3 widths', len(asked) == 12 and {w for _, w in asked} == {0, 1, 2})
p2 = K.make_profile('fake', K.parse_raw(lines), {'slices': 4, 'blocks': 1, 'unit_lw': 2, 'units': 2, 'bitstream': ''})
check('fit recovers the fake card: speed-ups within 1%, at once {1: 2, 2: 1}', all(abs(a - b) / b < 0.01 for a, b in zip(p2['speedup'], SP)) and p2['at_once'] == {'1': 2, '2': 1})
check('fake card best widths: N = 1 -> 2, N = 2 -> 1, N = 4 -> 0', [K.best_width(p2, n) for n in (1, 2, 4)] == [2, 1, 0])
print('FAILED %d' % bad if bad else 'ALL PASSED'); sys.exit(1 if bad else 0)
