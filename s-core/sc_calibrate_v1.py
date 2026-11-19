#!/usr/bin/env python3
"""sc_calibrate_v1.py - card setup program: measure how this card (this build, this user's setup) speeds up jobs at each width, fit a small
model, and store the numbers as a profile.  (ledger #1398; method and data: #1397)

    nix shell nixpkgs#openocd --command python3 sc_calibrate_v1.py run --name mycard --blocks 2 --unit-lw 3 --units 3 [--quick]
        runs the width sweep on the card (the files jobs_curve_L*_N*.json, one block, widths 0..the widest the build allows),
        writes profiles/<name>.raw.txt (one line per run) and profiles/<name>.json (the fitted profile)
    python3 sc_calibrate_v1.py fit --from-text profiles/example_2x8_nu3.raw.txt --name x --slices 8 --blocks 2 --unit-lw 3 --units 3
        fits from a saved raw file; no card needed
    python3 sc_calibrate_v1.py show profiles/<name>.json         print the profile and the best width for 1..2*slices jobs in a batch

What is fitted (model of #1397, for a batch of N identical jobs on one block of S slices, widths w = 0..W):
    time(N, w) = rounds x (time of one job at width w),   rounds = ceil(N / at_once(w, N))
    one job at width w is speedup[w] times faster than at width 0 (measured from the N = 1 files, median over lengths);
    at_once(0, N) = min(N, S); at_once(w >= 1) is fitted per width (the number of jobs that really run side by side; limited by the slices
    divided by 2**w and by the fusion units; it can come out lower than expected, as lw 1 did in #1397).
best_width(profile, N) = the width with the smallest time(N, w) / time(1, 0), ties to the narrower width.
The units are not reported by the board, so --blocks, --unit-lw, --units (and --bitstream, a free note) are given by the user and stored.
This is a model fitted to identical jobs of one program (crc32); mixed lengths in one batch are NOT in it (#1397 open item)."""
import sys, os, re, json, math, time, argparse, statistics, io, contextlib
HERE = os.path.dirname(os.path.abspath(__file__))
PROFILE_DIR = os.environ.get('SC_PROFILE_DIR', os.path.join(HERE, 'profiles'))
FORMAT = 'sc_profile_v1'
LINE = re.compile(r'jobs_curve_L(\d+)_N(\d+)\.json\s+lw(\d)\s+clocks=(\d+)\s+(\d+) of (\d+) jobs correct')
FULL = ['jobs_curve_L8_N%d.json' % n for n in range(1, 9)] + ['jobs_curve_L20_N%d.json' % n for n in (1, 2, 4, 8)]
QUICK = ['jobs_curve_L8_N%d.json' % n for n in (1, 2, 4, 8)]

def parse_raw(text):
    """raw lines -> {(L, N): {w: clocks}}; a line whose jobs are not all correct is an error (a wrong answer must never become a number)."""
    t = {}
    for m in LINE.finditer(text):
        L, N, w, c, ok, n = (int(x) for x in m.groups())
        if ok != n or n != N: raise ValueError('run L%d N%d lw%d: %d of %d jobs correct (expected all %d)' % (L, N, w, ok, n, N))
        t.setdefault((L, N), {})[w] = c
    return t

def rounds(n, per): return -(-n // per)

def fit(table, S):
    """table {(L, N): {w: clocks}} -> (speedup list, at_once dict {w: jobs at once} for w >= 1, error stats)."""
    widths = sorted({w for v in table.values() for w in v})
    if widths[0] != 0 or widths != list(range(len(widths))): raise ValueError('need widths 0..W without gaps, got %s' % widths)
    ones = {L: v for (L, N), v in table.items() if N == 1}
    if not ones: raise ValueError('need at least one N = 1 file to measure the speed-up')
    sp = [1.0] + [statistics.median(v[0] / v[w] for v in ones.values() if w in v and 0 in v) for w in widths[1:]]
    at = {}
    for w in widths[1:]:
        best = None
        for c in range(1, max(1, S >> w) + 1):
            err = sum(abs(rounds(N, c) * ones[L][w] - v[w]) / v[w] for (L, N), v in table.items() if N >= 2 and L in ones and w in v)
            if best is None or err < best[0] - 1e-12: best = (err, c)      # a tie keeps the smaller count (the conservative choice)
        at[w] = best[1]
    errs = [abs(predict_time(N, w, ones[L][0], sp, at, S) - v[w]) / v[w] for (L, N), v in table.items() if L in ones for w in v]
    return sp, at, {'runs': len(errs), 'files': len(table), 'max_err': max(errs), 'mean_err': sum(errs) / len(errs)}

def predict_time(N, w, t1_lw0, sp, at, S):
    per = min(N, S) if w == 0 else at[w]
    return rounds(N, per) * t1_lw0 / sp[w]

def best_width(p, N):
    """the width with the smallest predicted time for a batch of N identical jobs on one block of this card (ties -> narrower)."""
    S = p['card']['slices']; sp = p['speedup']; at = {int(k): v for k, v in p['at_once'].items()}
    return min(range(len(sp)), key=lambda w: (predict_time(N, w, 1.0, sp, at, S), w))

def make_profile(name, table, card, raw=None):
    sp, at, err = fit(table, card['slices'])
    ones = [v for (L, N), v in table.items() if N == 1 and 0 in v]
    cpw = statistics.median(v[0] / L for (L, N), v in table.items() if N == 1 and 0 in v)
    return {'format': FORMAT, 'name': name, 'date': time.strftime('%Y-%m-%d %H:%M'), 'card': card, 'widths': list(range(len(sp))),
            'speedup': [round(x, 3) for x in sp], 'at_once': {str(k): v for k, v in at.items()}, 'fit': {k: (round(v, 4) if isinstance(v, float) else v) for k, v in err.items()},
            'lw0_clocks_per_word_crc32': round(cpw), 'program': 'crc32 (identical jobs, one batch, one block)',
            'note': 'model of ledger #1397; not valid for mixed job lengths in one batch',
            'raw': [[L, N, [v[w] for w in sorted(v)]] for (L, N), v in sorted(table.items())]}

def save(p, directory=None):
    d = directory or PROFILE_DIR; os.makedirs(d, exist_ok=True)
    path = os.path.join(d, p['name'] + '.json'); json.dump(p, open(path, 'w'), indent=1); return path

def load_profile(path_or_name):
    path = path_or_name if os.path.exists(path_or_name) else os.path.join(PROFILE_DIR, path_or_name + ('' if path_or_name.endswith('.json') else '.json'))
    p = json.load(open(path))
    if p.get('format') != FORMAT: raise ValueError('%s is not a %s file' % (path, FORMAT))
    return p

def sweep(runner, files, wmax_of, log):
    """runner(file, lw) -> (clocks, ok_text, slices); wmax_of(slices) -> widest width to try.  Returns raw text (one line per run)."""
    lines = []; wmax = None
    for f in files:
        w = 0
        while wmax is None or w <= wmax:
            clk, ok, S = runner(f, w)
            if wmax is None: wmax = wmax_of(S)
            line = '%s lw%d clocks=%s  %s' % (f, w, clk, ok); lines.append(line); log(line); w += 1
    return '\n'.join(lines) + '\n'

def card_runner(port, blocks_arg, unit_lw):
    """the real runner: one block, scblocks on the card (must run inside `nix shell nixpkgs#openocd` for the JTAG port)."""
    sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'fpga')); import scblocks
    def run(f, w):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf): scblocks.main([port, f, '--blocks', '1', '--lw', str(w), '--unit-lw', str(unit_lw)])
        out = buf.getvalue()
        m = re.search(r'^  block 0: .*steps, (\d+) clocks', out, re.M); k = re.findall(r'(\d+ of \d+ jobs correct)', out)
        s = re.search(r'(\d+) slices per block', out)
        if not (m and k and s): raise RuntimeError('run %s lw%d gave no result line:\n%s' % (f, w, out[-600:]))
        return m.group(1), k[-1], int(s.group(1))
    return run

def show(p, out=print):
    c = p['card']
    out('profile %s (%s): %d blocks x %d slices, unit 2**%d lanes, %d units, %s' % (p['name'], p['date'], c['blocks'], c['slices'], c['unit_lw'], c['units'], c.get('bitstream') or 'bitstream not named'))
    out('speed-up of one job by width: ' + ', '.join('lw%d %.2fx' % (w, s) for w, s in enumerate(p['speedup'])))
    out('jobs running at once by width: lw0 min(N, %d), ' % c['slices'] + ', '.join('lw%s %d' % (k, v) for k, v in p['at_once'].items()))
    out('fit: %d runs, largest error %.1f%%, mean %.1f%%' % (p['fit']['runs'], 100 * p['fit']['max_err'], 100 * p['fit']['mean_err']))
    out('best width for a batch of N identical jobs: ' + ', '.join('N=%d -> lw%d' % (n, best_width(p, n)) for n in range(1, 2 * c['slices'] + 1)))

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0]); sub = ap.add_subparsers(dest='cmd', required=True)
    for name in ('run', 'fit'):
        s = sub.add_parser(name); s.add_argument('--name', required=True); s.add_argument('--blocks', type=int, required=True); s.add_argument('--unit-lw', type=int, required=True)
        s.add_argument('--units', type=int, required=True); s.add_argument('--bitstream', default=''); s.add_argument('--dir')
        if name == 'run': s.add_argument('--port', default='jtag'); s.add_argument('--quick', action='store_true')
        else: s.add_argument('--from-text', required=True); s.add_argument('--slices', type=int, required=True)
    sh = sub.add_parser('show'); sh.add_argument('profile')
    a = ap.parse_args(argv)
    if a.cmd == 'show': show(load_profile(a.profile)); return 0
    if a.cmd == 'run':
        os.chdir(HERE); files = QUICK if a.quick else FULL
        missing = [f for f in files if not os.path.exists(f)]
        if missing: print('missing job files (python3 make_curve_jobs_v1.py and v2):', ' '.join(missing)); return 2
        S = {}
        raw = sweep(card_runner(a.port, a.blocks, a.unit_lw), files, lambda s: (S.setdefault('S', s), min(a.unit_lw, int(math.log2(s))))[1], print)
        slices = S['S']
    else:
        raw = open(a.from_text).read(); slices = a.slices
    card = {'version': None, 'slices': slices, 'blocks': a.blocks, 'unit_lw': a.unit_lw, 'units': a.units, 'bitstream': a.bitstream}
    p = make_profile(a.name, parse_raw(raw), card)
    d = a.dir or PROFILE_DIR; os.makedirs(d, exist_ok=True)
    if a.cmd == 'run': open(os.path.join(d, a.name + '.raw.txt'), 'w').write(raw)
    print('saved', save(p, d)); show(p); return 0

if __name__ == '__main__': sys.exit(main())
