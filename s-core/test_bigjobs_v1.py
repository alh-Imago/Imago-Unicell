"""bigjobs_v1 + the shell's `addbig`: long data cut into pieces, the pieces' answers combined.  The combining is checked against the reference INTERPRETER (the whole data run as one
job in a big shared RAM against the pieces run as small jobs and combined), for every kind and rule.  No card.  python3 test_bigjobs_v1.py"""
import os, sys, io, json, glob, random, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bigjobs_v1 as BG, score_shell_v1 as S, jobio as J, jobiss, progs, scbatch
bad = 0
def check(name, cond):
    global bad
    print('%-112s %s' % (name, 'ok' if cond else 'FAIL')); bad += (not cond)
def fresh():
    buf = io.StringIO(); return S.Shell(out=buf), buf
def do(sh, buf, text): buf.truncate(0); buf.seek(0); sh.run_lines(text); return buf.getvalue()
def iss(kind, inputs, arg, shared=8192):
    job = J.Job(0, kind, inputs, progs.default_out_len(kind, len(inputs)), arg=arg)
    lk = J.build_link([job], shared_words=shared); st, n, out, steps = jobiss.reference(lk, job)
    assert st == 1, (kind, st); return out
made = []
try:
    # pure
    check('split: 10 words in pieces of 4 = 4, 4, 2', [len(p) for p in BG.split(list(range(10)), 4)] == [4, 4, 2])
    check('split pairs: both halves cut at the same places; whole() puts them back', BG.whole(BG.split(list(range(12)), 4, True), True) == list(range(12)) and BG.split(list(range(12)), 4, True)[0] == [0, 1, 6, 7])
    check('combine prefix: each piece plus the sum of the pieces before', BG.combine('prefix', [[1, 3], [3, 7]], [[1, 2], [3, 4]]) == [1, 3, 6, 10])
    for k, why in [('crc32', 'cannot be split'), ('nosuchkind', 'combine=')]:
        try: BG.rule_for(k); ok = False
        except BG.BigError as e: ok = why in str(e)
        check('rule_for(%s) is refused: %s' % (k, why), ok)
    sh, buf = fresh()
    # recipes made for the test
    for name, recipe in [('zz_bsum', 'add 3 xor arg then sum'), ('zz_bmin', 'rol 5 then min'), ('zz_bmax', 'mul 7 then max'), ('zz_bxor', 'shl 1 then xor'), ('zz_bor', 'and 0xFF then or'), ('zz_band', 'or 0xF0 then and'),
                         ('zz_bmap', 'add 1 xor arg'), ('zz_pmap', 'pair add'), ('zz_pdot', 'pair mul then sum'), ('zz_pre', 'prefix'), ('zz_dif', 'diff')]:
        made.append(name); o = do(sh, buf, 'make %s %s' % (name, recipe)); assert 'made %s' % name in o, o
    rng = random.Random(1428); data = [rng.getrandbits(rng.choice([8, 16, 32])) for _ in range(300)]
    cases = [('vsum', 0), ('vscale', 0), ('vstress', 9), ('vgain', 77), ('vmax', 0), ('vmin', 0), ('vxor', 0xA5A5), ('vcount', 1000), ('vprefix', 0),
             ('zz_bsum', 12345), ('zz_bmin', 0), ('zz_bmax', 0), ('zz_bxor', 0), ('zz_bor', 0), ('zz_band', 0), ('zz_bmap', 99), ('zz_pmap', 0), ('zz_pdot', 0)]
    for kind, arg in cases:
        d = [x & 0xFFFFFF for x in data] if kind == 'vgain' else data                      # vgain needs inputs below 2**24
        o = do(sh, buf, 'addbig %s %s arg=%d chunk=40' % (kind, ' '.join(map(str, d)), arg)); ok = 'added long job' in o
        gid = sh._newbig_id() - 1; idx = sh.big_groups().get(gid, [])
        rule, pair = BG.rule_for(kind); parts = [sh.jobs[i]['inputs'] for i in idx]
        whole = BG.whole(parts, pair)
        want = iss(kind, whole, arg); res = [iss(kind, p, arg) for p in parts]            # the INTERPRETER, whole against pieces
        check('%-9s %-7s %3d words in %2d pieces: pieces combined (%s) = the whole run on the interpreter' % (kind, 'arg %d' % arg, len(d), len(idx), rule), ok and BG.combine(rule, res, parts) == want)
    # refusals through the shell
    for line, frag in [('addbig crc32 1 2 3', 'cannot be split'), ('addbig zz_pre 1 2 3', 'cannot be split exactly'), ('addbig zz_dif 1 2 3', 'cannot be split exactly'), ('addbig vsum', 'usage'), ('addbig vsum 1 2 chunk=0', 'at least 1'),
                       ('addbig vsum seq 1 500 1 chunk=300', 'still too big')]:
        n0 = len(sh.jobs); o = do(sh, buf, line); check('refused: %s' % line, frag in o and len(sh.jobs) == n0)
    # list, remove, dup
    n = len(sh.jobs); o = do(sh, buf, 'list'); check('list shows one line per long job (not one per piece)', o.count('long job') == len(cases) and o.count('\n') < len(cases) + 4)
    o = do(sh, buf, 'dup 0'); check('dup of a piece is refused (use addbig again)', 'addbig' in o and len(sh.jobs) == n)
    first = [i for i, j in enumerate(sh.jobs) if (j.get('big') or {}).get('id') == 0]; o = do(sh, buf, 'remove %d' % first[2]); check('remove of one piece removes the whole long job', 'removed long job 0' in o and len(sh.jobs) == n - len(first))
    # a result file: right answers -> MATCH, one piece wrong -> DIFFERENT, one missing -> DIFFERENT
    sh2, buf2 = fresh(); do(sh2, buf2, 'addbig vsum seq 1 300 1 chunk=100; addbig vprefix seq 1 150 3 chunk=64; add vsum 1 2 3')
    tasks = sh2.tasks(); res = [{'job': i, 'kind': t.kind, 'result': t.expected()} for i, t in enumerate(tasks)]
    f = tempfile.mktemp(suffix='.json'); json.dump(res, open(f, 'w')); o = do(sh2, buf2, 'check %s' % f)
    sh2.check_big(f); o = buf2.getvalue()
    check('check_big with the right answers: both long jobs MATCH', o.count('MATCH') >= 2 and 'DIFFERENT' not in o)
    res[1]['result'] = [res[1]['result'][0] + 1]; json.dump(res, open(f, 'w')); buf2.truncate(0); buf2.seek(0); sh2.check_big(f); o = buf2.getvalue()
    check('check_big with one wrong piece: that long job is DIFFERENT, the other MATCH', 'DIFFERENT' in o and 'MATCH' in o)
    json.dump([r for r in res if r['job'] != 2], open(f, 'w')); buf2.truncate(0); buf2.seek(0); sh2.check_big(f); o = buf2.getvalue()
    check('check_big with a missing piece: DIFFERENT, says results missing', 'results missing' in o)
    # save / open keep the grouping; other tools ignore it
    d = tempfile.mkdtemp(); p = os.path.join(d, 'big.json'); do(sh2, buf2, 'save %s' % p)
    sh3, buf3 = fresh(); do(sh3, buf3, 'open %s' % p); check('save / open keep the long jobs (grouped), and scbatch loads the file', len(sh3.big_groups()) == 2 and len(scbatch.load_jobs(p)) == len(sh2.jobs))
    o = do(sh3, buf3, 'set dsh 4096; plan'); check('plan on a bigger build still works with the pieces', 'cannot fit' not in o and 'batch' in o)
finally:
    for n in set(made):
        for f in glob.glob(os.path.join(S.MADE, n + '.*')): os.remove(f)
print('FAILED %d' % bad if bad else 'all ok'); sys.exit(1 if bad else 0)
