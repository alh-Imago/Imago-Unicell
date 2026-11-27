"""score_shell_v2 (clone of test_score_shell_v1.py plus the build store tests, ledger #1534): commands, job entry, save/open round trip, planning, a fake run, completion, live colouring, the help file.  No card.  python3 test_score_shell_v2.py"""
import os, sys, io, json, subprocess, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import score_shell_v2 as S, scbatch
bad = 0
def check(name, cond):
    global bad
    print('%-108s %s' % (name, 'ok' if cond else 'FAIL')); bad += (not cond)
def fresh():
    buf = io.StringIO(); sh = S.Shell(out=buf); return sh, buf
def do(sh, buf, text): buf.truncate(0); buf.seek(0); sh.run_lines(text); return buf.getvalue()

sh, buf = fresh()
o = do(sh, buf, 'add vsum 1 2 3 4')
check('add vsum 1 2 3 4: added, expected answer [10] shown at once', 'added job 0' in o and '[10]' in o)
o = do(sh, buf, 'add vmax seq 5 80 3'); check('add vmax seq 5 80 3: the library program comes in by itself, answer 242', '[242]' in o and 'vmax' in sh.programs)
o = do(sh, buf, 'add vxor 1 2 3 arg=255'); check('add with arg=: vxor answer [254, 253, 252]', '[254, 253, 252]' in o)
o = do(sh, buf, 'add vsum 0x10 0x20'); check('hex numbers: 0x10 + 0x20 = 48', '[48]' in o)
o = do(sh, buf, 'add nosuch 1'); check('an unknown kind is an error naming the kinds, nothing added', 'unknown kind' in o and len(sh.jobs) == 4)
o = do(sh, buf, 'add vsum 12abc'); check('a bad number is an error, nothing added', 'not a number' in o and len(sh.jobs) == 4)
o = do(sh, buf, 'add vsum seq 1 5'); check('seq with a missing argument is an error', 'seq needs' in o and len(sh.jobs) == 4)
o = do(sh, buf, 'add vsum 1 2 lw=9'); check('a width the compiler refuses is an error from the host (nothing added)', 'lw must be' in o and len(sh.jobs) == 4)
o = do(sh, buf, 'foo'); check('an unknown command is an error with a hint', 'unknown command' in o)
o = do(sh, buf, 'list'); check('list shows 4 jobs numbered, not saved', '  3  ' in o and '4 job(s)' in o and 'not saved' in o)
o = do(sh, buf, 'show'); check('show prints the answers', '[10]' in o and '[242]' in o)
o = do(sh, buf, 'dup 0 2; remove 5'); check('dup 0 2 adds two copies; remove 5 removes one (4 + 2 - 1 = 5 jobs)', len(sh.jobs) == 5)
sh3, buf3 = fresh()
o = do(sh3, buf3, 'add vsum seq 1 300 1'); check('a job too long for the shared RAM (300 words, build of 256) is added with a warning that says why and the limit (247)', 'added job 0' in o and 'warning' in o and '247' in o)
o = do(sh3, buf3, 'plan'); check('plan refuses it on the default size (the compiler says it cannot fit)', 'cannot fit' in o)
o = do(sh3, buf3, 'set dsh 1024; plan'); check('set dsh 1024: plan accepts the same job (a bigger build)', 'cannot fit' not in o and 'shared 309/1024' in o)
o = do(sh3, buf3, 'add vsum 1 2 3'); check('no warning for a job that fits', 'warning' not in o)
# save / open round trip, and the file works with the existing tools
d = tempfile.mkdtemp(); f = os.path.join(d, 'mine.json')
o = do(sh, buf, 'save %s' % f); check('save writes a job file', 'saved 5 job(s)' in o and os.path.exists(f))
tasks = scbatch.load_jobs(f); check('the saved file loads with scbatch.load_jobs (the tool scblocks.py uses): 5 jobs, same answers', [t.expected() for t in tasks] == [[10], [242], [254, 253, 252], [48], [10]])
sh2, buf2 = fresh(); o = do(sh2, buf2, 'open %s' % f); check('open reads it back: 5 jobs, programs restored', 'opened 5 job(s)' in o and 'vmax' in sh2.programs and 'vxor' in sh2.programs)
check('the round trip keeps the jobs exactly', sh2.jobs == sh.jobs)
o = do(sh2, buf2, 'open /nonexistent.json'); check('open of a missing file is an error, not a crash', 'error' in o)
# quit warning
sh3, buf3 = fresh(); do(sh3, buf3, 'add vsum 1; quit'); check('quit with unsaved jobs warns once', not sh3.quit and 'not saved' in buf3.getvalue())
do(sh3, buf3, 'quit'); check('...and the second quit leaves', sh3.quit)
# settings and plan
o = do(sh, buf, 'set blocks 1; set lw 2; set order width; set estimate off'); check('set: blocks, lw, order accepted', sh.set['blocks'] == 1 and sh.set['lw'] == 2 and sh.set['order'] == 'width')
o = do(sh, buf, 'set order sideways'); check('set order with a bad value is an error', 'auto, kind or width' in o)
o = do(sh, buf, 'set nosuch 1'); check('set of an unknown setting is an error', 'unknown setting' in o)
o = do(sh, buf, 'plan'); check('plan prints batches', 'batch 0' in o and 'jobs (' in o)
shp, bp = fresh(); do(shp, bp, 'open jobs_order_test2.json') if False else None
doc = json.load(open(os.path.join(HERE, 'jobs_order_test2.json')))
shp.jobs = doc['jobs']; shp.programs = {p['name']: p for p in doc['programs']}
o = do(shp, bp, 'set lw auto; set profile example_2x8_nu3_v2; set estimate on; set slices 8; set unit-lw 3; plan')
check('plan with the estimate: vsum lw2, the vgain jobs lw0, vsum submitted first (the choice of #1411)', 'vsum:lw2' in o and 'vgain:lw0' in o and 'submit order: vsum lw2' in o)
# register a program of your own
sh4, buf4 = fresh()
o = do(sh4, buf4, 'register mycount programs/vcount.s expect=programs.examples_v3:vcount_ref out=1; add mycount 1 2 300 arg=100')
check('register your own program, then add a job of that kind (answer [1])', 'registered mycount' in o and '[1]' in o)
o = do(sh4, buf4, 'register bad programs/nosuchfile.s'); check('register of a missing file is an error', 'error' in o)
o = do(sh4, buf4, 'programs'); check('programs lists yours', 'mycount' in o)
# run with a fake link: the shell passes the right arguments, writes through --out and compares
sh5, buf5 = fresh(); do(sh5, buf5, 'add vsum 1 2 3 4; add vmax 7 99 42 13; set blocks 1; set unit-lw 3')
seen = {}
def fake(args):
    seen['args'] = args; out = args[args.index('--out') + 1]
    json.dump([{'job': 0, 'kind': 'vsum', 'result': [10]}, {'job': 1, 'kind': 'vmax', 'result': [99]}], open(out, 'w'))
    return 0, '2 of 2 jobs correct\n'
sh5._call_scblocks = fake; sh5.set['out'] = os.path.join(d, 'r.json')
o = do(sh5, buf5, 'run')
check('run: calls scblocks with port jtag, blocks, submit order, --out; then compares: 2 jobs MATCH', seen['args'][0] == 'jtag' and '--blocks' in seen['args'] and '--out' in seen['args'] and o.count('MATCH') == 2 and '2 of 2 jobs match' in o)
def fake_bad(args):
    out = args[args.index('--out') + 1]; json.dump([{'job': 0, 'kind': 'vsum', 'result': [11]}, {'job': 1, 'kind': 'vmax', 'result': [99]}], open(out, 'w')); return 0, '1 of 2 jobs correct\n'
sh5._call_scblocks = fake_bad; o = do(sh5, buf5, 'run'); check('run with a wrong card number: DIFFERENT shown', 'DIFFERENT' in o and '1 of 2 jobs match' in o)
sh5._call_scblocks = lambda args: (1, 'board not found\n'); o = do(sh5, buf5, 'run'); check('run that fails: error, no compare', 'did not finish' in o and 'MATCH' not in o)
# completion
sh6, _ = fresh()
check('completion: first word = the commands', 'add' in S.completions(sh6, 'ad') and 'plan' in S.completions(sh6, ''))
check('completion: after add = the kinds', 'vmax' in S.completions(sh6, 'add ') and 'vsum' in S.completions(sh6, 'add v'))
check('completion: after add KIND = the options', 'arg=' in S.completions(sh6, 'add vsum 1 ') and 'seq' in S.completions(sh6, 'add vmax '))
check('completion: set, then the values of a setting', 'estimate' in S.completions(sh6, 'set ') and 'auto' in S.completions(sh6, 'set lw '))
check('completion: help lists commands; file names for open', 'save' in S.completions(sh6, 'help ') and any(x.startswith('ladder_1') for x in S.completions(sh6, 'open ladder_1')))
# live colouring (pure function, no terminal needed)
tk = S.tokenize(sh6, 'add vmax 5 0x10 arg=100')
check('colouring: command, kind, numbers, option', [s for s, t in tk if s != 'ws'] == ['command', 'kind', 'number', 'number', 'option'])
check('colouring: an unknown command and an unknown kind are marked bad', S.tokenize(sh6, 'zzz')[0][0] == 'badcommand' and S.tokenize(sh6, 'add zzz 1')[2][0] == 'badcommand')
check('colouring: the coloured line carries ANSI codes and the same text', S.render(sh6, 'add vsum 1').count('\033[') >= 4 and S.render(sh6, 'add vsum 1').replace('\033[0m', '').replace('\033[32m', '').replace('\033[36m', '').replace('\033[33m', '') == 'add vsum 1')

# ---------------- the build store: store, builds, target, fit, use, load (fake loader and fake card, no hardware)
import make_manifest_v2 as M, score_store_v1 as ST, types
sd = tempfile.mkdtemp(prefix='score_store_test_')
os.environ['SCORE_SHELL_CONFIG'] = os.path.join(sd, 'cfg.json')
HDR = '    WNS(ns)      TNS(ns)  TNS Failing Endpoints  TNS Total Endpoints      WHS(ns)      THS(ns)  THS Failing Endpoints  THS Total Endpoints\n    -------      -------  ---------------------  -------------------      -------      -------  ---------------------  -------------------\n'
def mkbuild(nb, s, ulw, imem, slack=None, bit=True):
    p, m = M.write(nb, s, ulw, 1, imem, outdir=sd); n = m['build']
    os.makedirs(os.path.join(sd, 'vivado_out_' + n), exist_ok=True)
    if bit: open(os.path.join(sd, 'vivado_out_%s' % n, n + '.bit'), 'w').write('fake bitstream')
    if slack is not None:
        open(os.path.join(sd, 'vivado_out_%s' % n, 'timing_summary.txt'), 'w').write(HDR + '   %.3f        0.000   %5d               129794        %.3f        0.000                      0               129794\n' % (slack[0], 0 if slack[0] > 0 else 7, slack[1]))
    return n
good = mkbuild(2, 8, 0, 128, (0.358, 0.048)); failed = mkbuild(2, 8, 4, 128, (-0.210, 0.030)); unknown = mkbuild(2, 4, 0, 128, None); nobit = mkbuild(2, 16, 0, 128, (0.5, 0.05), bit=False)
fakeloader = os.path.join(sd, 'fakeloader'); open(fakeloader, 'w').write('x')
check('parse_timing reads Vivado\'s table: setup, hold, failing endpoints', ST.parse_timing(os.path.join(sd, 'vivado_out_%s' % good, 'timing_summary.txt')) == {'setup': 0.358, 'hold': 0.048, 'fail': 0}
      and ST.parse_timing(os.path.join(sd, 'vivado_out_%s' % failed, 'timing_summary.txt'))['setup'] == -0.21)
sh7, buf7 = fresh()
o = do(sh7, buf7, 'store ' + sd)
check('store: sets and remembers the folder (config file written)', sd in o and json.load(open(os.environ['SCORE_SHELL_CONFIG']))['store'] == sd)
sh7b, buf7b = fresh(); check('a new shell finds the folder again from the config file', sh7b.cfg.get('store') == sd)
o = do(sh7, buf7, 'builds')
check('builds: lists the store\'s builds and the repo builds, with the bitfile column', good in o and failed in o and unknown in o and 'hk8s32u32n1i1024' in o and 'recommended' in o)
check('target: both boards, Tang marked as having no S-Core build', 'kintex_xc7k480t' in do(sh7, buf7, 'target') and 'tang_nano_20k' in do(sh7, buf7, 'target') and 'fit is unknown' in do(sh7, buf7, 'target'))
o = do(sh7, buf7, 'fit 8 32 5 1 1024'); check('fit: 8 x 32 with 32-lane units is tight on the Kintex card and unknown on the Tang', 'tight' in o and 'unknown' in o and '256 slices' in o)
o = do(sh7, buf7, 'fit 8 4 2 1'); check('fit: a unit size that was not measured is said so, no number invented', 'not known' in o and 'not measured' in o)
o = do(sh7, buf7, 'use ' + good); check('use: sets blocks, slices, unit-lw (none without a unit) and imem', sh7.set['blocks'] == 2 and sh7.set['slices'] == 8 and sh7.set['unit-lw'] is None and sh7.set['imem'] == 128 and 'timing: setup +0.358' in o)
o = do(sh7, buf7, 'use hk8s32u32n1i1024'); check('use: a 32-lane build sets unit-lw 5 and imem 1024', sh7.set['unit-lw'] == 5 and sh7.set['imem'] == 1024 and sh7.set['blocks'] == 8)
o = do(sh7, buf7, 'use nothing'); check('use: an unknown name says so with no crash', 'no build' in o)
check('scargs passes --imem and --unit-lw to the planner', all(x in sh7.scargs('x.json', True) for x in ('--imem', '1024', '--unit-lw', '5')))
# load: fake loader and fake card
calls = []
card = {'S': 8, 'imem_words': 128, 'healthy': True}
def fake_runner(cmd, **kw):
    calls.append(list(cmd))
    if cmd[0] == fakeloader: return types.SimpleNamespace(returncode=0, stdout='Load SRAM: 100%\nDone\nir: 1 isc_done 1 isc_ena 0 init 1 done 1\n', stderr='')
    txt = "# board version {'version': 12, 'S': %d, 'imem_words': %d, 'dmem_words': 16}  block 0\n" % (card['S'], card['imem_words'])
    txt += 'read order 5 7 0 5 0 gave: B C A B A\nhealthy B C A B A | address stuck at 0: A A A A A\n' if card['healthy'] else 'read order 5 7 0 5 0 gave: A A A A A\n'
    return types.SimpleNamespace(returncode=0, stdout=txt, stderr='')
sh7.set['loader'] = fakeloader; sh7.runner = fake_runner
o = do(sh7, buf7, 'load ' + failed); check('load: a build whose timing failed is refused and the loader is not called', 'refused: timing failed' in o and not calls)
o = do(sh7, buf7, 'load ' + unknown); check('load: unknown timing needs the word confirm; not called without it', 'not known' in o and 'confirm' in o and not calls)
o = do(sh7, buf7, 'load ' + nobit); check('load: no bitstream in the store is said plainly', 'no bitstream found' in o and not calls)
o = do(sh7, buf7, 'load ' + good)
check('load: good build is loaded (SRAM only: exactly loader -c ft232 FILE), then the first-read test; the board matches', calls[0] == [fakeloader, '-c', 'ft232', os.path.join(sd, 'vivado_out_%s' % good, good + '.bit')] and 'first-read test healthy' in o and 'loaded %s' % good in o)
check('load: no flash or write option is ever in the loader command', all(not any('flash' in a.lower() or a in ('-f', '-w', '--write-flash') for a in c) for c in calls))
calls.clear(); card['S'] = 16; o = do(sh7, buf7, 'load ' + good); check('load: a board that reports the wrong slices per block is reported as a mismatch', 'has 16 slices per block' in o)
card['S'] = 8; card['healthy'] = False; o = do(sh7, buf7, 'load ' + good); check('load: an unhealthy first-read test is reported', 'not healthy' in o)
card['healthy'] = True; card['imem_words'] = 1024; o = do(sh7, buf7, 'load ' + good); check('load: wrong code-word count on the board is reported', 'has 1024 code words' in o)
calls.clear(); card['imem_words'] = 128; o = do(sh7, buf7, 'load %s confirm' % unknown); card['S'] = 4; o2 = do(sh7, buf7, 'load %s confirm' % unknown)
check('load: unknown timing with confirm is loaded', calls and calls[0][0] == fakeloader and 'loaded %s' % unknown in o)
def bad_loader(cmd, **kw): return types.SimpleNamespace(returncode=1, stdout='', stderr='mpsse_store: fails to first flush -1 usb bulk write failed\n')
sh7.runner = bad_loader; o = do(sh7, buf7, 'load ' + good); check('load: a USB write failure is reported with the advice to reconnect, not as a success', 'usb bulk write failed' in o and 'reconnect' in o and 'loaded' not in o)
check('find_loader prefers the nix loader over PATH, and a set loader over both', ST.find_loader({'loader': fakeloader}) == fakeloader and (ST.find_loader({}) in (ST.NIX_LOADER, None) or not os.path.isfile(ST.NIX_LOADER)))
def idcode(cmd, **kw): return types.SimpleNamespace(returncode=1, stdout='', stderr='JTAG init failed with: Unknown device with IDCODE: 0x23751093\n')
sh7.runner = idcode; o = do(sh7, buf7, 'load ' + good); check('load: an unknown-IDCODE failure names the loader used and says to use the nix one', 'does not know the chip' in o and fakeloader in o)
check('completion: use and load offer the build names', good in S.completions(sh7, 'use ') and 'confirm' in S.completions(sh7, 'load %s ' % good))
# help file
text = S.help_markdown()
check('SHELL_v2.md is exactly what the shell generates (no drift)', open(os.path.join(HERE, 'SHELL_v2.md')).read() == text)
check('every command has a usage line and help text, and is in a group', all(u and t for _, u, t in S.COMMANDS.values()) and sorted(sum((n for _, n in S.GROUPS), [])) == sorted(S.COMMANDS))
check('SHELL_v2.md mentions every command and every setting', all(('`%s' % c) in text for c in S.COMMANDS) and all(('`%s`' % k) in text for k in S.SETTINGS))
# the real program, from the command line, no terminal
r = subprocess.run([sys.executable, os.path.join(HERE, 'score_shell_v2.py'), '-q', '-c', 'add vsum 5 6 7; show'], capture_output=True, text=True, cwd=HERE)
check('command line: -c "add vsum 5 6 7; show" -q prints [18] with no colour codes when not a terminal', r.returncode == 0 and '[18]' in r.stdout and '\033[' not in r.stdout)
r = subprocess.run([sys.executable, os.path.join(HERE, 'score_shell_v2.py')], input='add vsum 1 1\nshow\n', capture_output=True, text=True, cwd=HERE)
check('commands piped in on standard input work', '[2]' in r.stdout)
print('FAILED %d' % bad if bad else 'ALL PASSED'); sys.exit(1 if bad else 0)
