"""score_shell_v1: commands, job entry, save/open round trip, planning, a fake run, completion, live colouring, the help file.  No card.  python3 test_score_shell_v1.py"""
import os, sys, io, json, subprocess, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import score_shell_v1 as S, scbatch
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
# help file
text = S.help_markdown()
check('SHELL.md is exactly what the shell generates (no drift)', open(os.path.join(HERE, 'SHELL.md')).read() == text)
check('every command has a usage line and help text, and is in a group', all(u and t for _, u, t in S.COMMANDS.values()) and sorted(sum((n for _, n in S.GROUPS), [])) == sorted(S.COMMANDS))
check('SHELL.md mentions every command and every setting', all(('`%s' % c) in text for c in S.COMMANDS) and all(('`%s`' % k) in text for k in S.SETTINGS))
# the real program, from the command line, no terminal
r = subprocess.run([sys.executable, os.path.join(HERE, 'score_shell_v1.py'), '-q', '-c', 'add vsum 5 6 7; show'], capture_output=True, text=True, cwd=HERE)
check('command line: -c "add vsum 5 6 7; show" -q prints [18] with no colour codes when not a terminal', r.returncode == 0 and '[18]' in r.stdout and '\033[' not in r.stdout)
r = subprocess.run([sys.executable, os.path.join(HERE, 'score_shell_v1.py')], input='add vsum 1 1\nshow\n', capture_output=True, text=True, cwd=HERE)
check('commands piped in on standard input work', '[2]' in r.stdout)
print('FAILED %d' % bad if bad else 'ALL PASSED'); sys.exit(1 if bad else 0)
