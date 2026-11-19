#!/usr/bin/env python3
"""scbatch.py - front end for big runs: a job file in, results out.  It compiles the jobs (jobcomp.py) into a chain of batches, loads the scripts and images into far
RAM, starts the chain and collects the results.  The board does the chaining (hardware batch sequencer, board version 11: build_tang.sh --pool 10) or, with --host,
the host walks the same scripts over the serial link (any far-RAM board, version 10: --pool 9).

    python3 scbatch.py --plan jobs.json                    compile only: show the batches (no board needed)
    python3 scbatch.py /dev/ttyUSB1 jobs.json              run on the board (hardware sequencer), verify against the Python answer
    python3 scbatch.py /dev/ttyUSB1 jobs.json --host       same with the host walking the scripts (version 10 board)
    python3 scbatch.py /dev/ttyUSB1 --demo 40              40 random jobs instead of a file
    options: --out results.json (write every job's result words), --imem 128 --dsh 256 (board sizes; read from the board when it is connected)

Job file (JSON):  {"programs": [ {"name": "vmax", "source": "programs/vmax.s", "expect": "programs.examples:vmax_ref", "out": 1} ],     # optional: your own programs
                    "jobs": [ {"kind": "vsum", "inputs": [1, 2, 3]},
                             {"kind": "vscale", "inputs": {"seq": [100, 10, 7]}},          # start, count, step
                             {"kind": "vstress", "inputs": [5, 6, 7], "arg": 9, "out_len": 1} ]}
Programs: the built-in ones (%s) and any listed under programs in the file (see progs.py, programs/template.s; expect is iss or a Python function).  Results are compared with the answer computed in Python; a job that the board refused or trapped is reported by name.""" 
import sys, os, json, time, random, argparse
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'fpga'))
import host_sc as hs, sdt_host as H, batch as B, jobio as J, jobcomp_v2 as C, progs
__doc__ = __doc__ % ', '.join(sorted(J.KINDS))

def c_J(a): return b'J' + a.to_bytes(3, 'little')
CLK_HZ = 27_000_000
def dec_A(b):
    """status of the sequencer: 8 bytes (board version 11) or 24 bytes (version 12: clock counters and the current step as well)"""
    d = dict(busy=b[0] & 1, done=(b[0] >> 1) & 1, err=b[1], steps=b[2] | b[3] << 8, tag=int.from_bytes(bytes(b[4:8]), 'little'))
    if len(b) >= 24:
        le = lambda x: int.from_bytes(bytes(x), 'little')
        d.update(clk=le(b[8:12]), clk_copy=le(b[12:16]), clk_wait=le(b[16:20]), pc=le(b[20:23]), op=b[23] & 15)
    return d
def a_len(version): return 24 if version >= 12 else 8
SEQ_ERR = {0: 'none', 1: 'a far RAM range outside the copy window', 2: 'a near range past the end', 3: 'far RAM not ready', 4: 'bad copy direction', 5: 'a copy timed out',
           6: 'a WAIT timed out (a job did not finish in time)', 7: 'code or region change with jobs in flight', 8: 'bad opcode in the script', 9: 'step limit'}

def load_jobs(path):
    d = json.load(open(path)); base = os.path.dirname(os.path.abspath(path)); tasks = []
    for pr in d.get('programs', []):
        try: progs.register(pr['name'], pr['source'], expect=pr.get('expect', 'iss'), out=pr.get('out', 1), base_dir=base, replace=True)
        except (progs.ProgramRegistryError, KeyError) as e: raise C.JobCompError('program %s: %s' % (pr.get('name', '?'), e))
    for n, j in enumerate(d['jobs']):
        ins = j['inputs']
        if isinstance(ins, dict): st, cnt, step = ins['seq']; ins = [(st + k * step) & J.M32 for k in range(cnt)]
        try: tasks.append(C.Task(j['kind'], ins, j.get('out_len'), j.get('arg', 0), lw=j.get('lw', 0), crit=j.get('crit', 0)))
        except (C.JobCompError, ValueError) as e: raise C.JobCompError('job %d: %s' % (n, e))
        except Exception as e: raise C.JobCompError('job %d (%s): %s' % (n, j['kind'], e))
    return tasks

def demo_jobs(n, seed=1):
    r = random.Random(seed); tasks = []
    for _ in range(n):
        k = r.choice(['vsum', 'vscale', 'vstress']); m = r.randint(2, 14)
        tasks.append(C.Task(k, [r.randrange(1 << 32) if k != 'vstress' else r.randrange(1000) for _ in range(m)], arg=r.randint(1, 2)))
    return tasks

def run(port, tasks, host=False, io=None, out=None, imem=None, dsh=None, poll_timeout=600.0, say=print):
    b = io if io is not None else hs.Board(port)
    clk_hz = 50_000_000 if str(port).startswith('jtag') else CLK_HZ      # the Kintex card runs at 50 MHz, the Tang at 27 MHz
    v = b.version(); say('board version %d, %d slices, %d code words' % (v['version'], v['S'], v['imem_words']))
    if v['version'] < 10: say('Not a far-RAM board (need version 10 or 11).'); return 2
    if not host and v['version'] < 11: say('This board has no hardware sequencer (version %d). Use --host, or load a --pool 10 build.' % v['version']); return 2
    imem = imem or v['imem_words']
    plan = C.compile(tasks, imem=imem, dsh=dsh or 256, wait_k=0xFFFF); say(plan.report())
    def put(c): b.s.write(c); b.s.flush()
    def far_r(a): put(H.c_r(a)); return H.dec_r(b._rd(4))
    put(b'R'); time.sleep(0.2); put(hs.cmd_G()); put(H.c_D(*plan.window))
    t0 = time.time()
    for a in sorted(plan.image): b.s.write(H.c_w(a, plan.image[a]))
    b.s.flush(); time.sleep(0.3); t_load = time.time() - t0
    say('loaded %d words into far RAM in %.1f s' % (len(plan.image), t_load))
    starts = plan.script_addrs
    t0 = time.time()
    if host:
        err, tag, steps = B.LiveExec(b, step_limit=100000).run(plan.entry)
    else:
        put(c_J(plan.entry)); time.sleep(0.02); last = -1; shown = time.time()
        while True:
            put(b'A'); a = dec_A(b._rd(a_len(v['version'])))
            if a['done'] and not a['busy']: break
            if time.time() - t0 > poll_timeout: say('sequencer did not finish in %.0f s' % poll_timeout); return 1
            if 'pc' in a and (a['steps'] != last and time.time() - shown > 0.5 or time.time() - shown > 2.0):
                k = max([i for i, ad in enumerate(starts) if ad <= a['pc']] or [0])
                say('  running: batch %d of %d, step %d of %d (%s), %.2f s of board time so far' % (k + 1, len(plan.batches), a['steps'], plan.steps, B.NAMES[a['op']] if a['op'] < len(B.NAMES) else '?', a['clk'] / clk_hz))
                last = a['steps']; shown = time.time()
            time.sleep(0.05)
        err, tag, steps = a['err'], a['tag'], a['steps']
    t_run = time.time() - t0
    if err or tag != plan.tag:
        say('batch stopped: error %s (%s) after %s steps; end tag %s' % (err, SEQ_ERR.get(err, '?'), steps, tag)); return 1
    say('chain finished: %d steps in %.2f s (%s)' % (steps, t_run, 'host walking the scripts' if host else 'hardware sequencer'))
    if not host and 'clk' in a:
        c = a['clk']; other = c - a['clk_copy'] - a['clk_wait']
        say('board time: %d clocks = %.2f ms (%.0f MHz): %.1f%% copying, %.1f%% waiting for jobs, %.1f%% fetching/decoding steps; %.1f clocks per step' % (
            c, 1000.0 * c / clk_hz, clk_hz / 1e6, 100.0 * a['clk_copy'] / c, 100.0 * a['clk_wait'] / c, 100.0 * other / c, c / max(1, steps)))
        say('  %d jobs in %.2f ms of board time = %.0f jobs per second through the chain' % (len(tasks), 1000.0 * c / clk_hz, len(tasks) * clk_hz / c))
    elif not host: say('(this board version has no clock counters; load a --pool 11 build for the timing report)')
    bad = plan.verify(far_r)
    for i, kind, why in bad: say('  job %d (%s): %s' % (i, kind, why))
    say('%d of %d jobs correct' % (len(tasks) - len(bad), len(tasks)))
    if out:
        json.dump([{'job': i, 'kind': t.kind, 'result': [far_r(plan.results[i][1] + k) for k in range(plan.results[i][2])]} for i, t in enumerate(tasks)], open(out, 'w'))
        say('results written to %s' % out)
    return 1 if bad else 0

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0]); ap.add_argument('port', nargs='?'); ap.add_argument('jobs', nargs='?')
    ap.add_argument('--plan', metavar='JOBS'); ap.add_argument('--demo', type=int); ap.add_argument('--host', action='store_true'); ap.add_argument('--out')
    ap.add_argument('--imem', type=int, default=128); ap.add_argument('--dsh', type=int, default=256)
    a = ap.parse_args(argv)
    if a.plan:
        plan = C.compile(load_jobs(a.plan), imem=a.imem, dsh=a.dsh); print(plan.report()); return 0
    if not a.port or not (a.jobs or a.demo): ap.print_help(); return 2
    tasks = demo_jobs(a.demo) if a.demo else load_jobs(a.jobs)
    return run(a.port, tasks, host=a.host, out=a.out, imem=a.imem, dsh=a.dsh)

if __name__ == '__main__': sys.exit(main())
