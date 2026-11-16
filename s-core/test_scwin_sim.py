"""Drives scwin.py (the browser window's server) against the simulated v12 board: press RUN with the default commands and data, poll the
page's state while it runs, and check the jobs, the core view and the words read back.  Usage: python3 test_scwin_sim.py [S]"""
import os, sys, json, time, threading, urllib.request
os.environ['POOL'] = '8'
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_cli_sim as tc, scwin, sccli

def get(port, path): return json.loads(urllib.request.urlopen('http://127.0.0.1:%d%s' % (port, path)).read())
def post(port, path, obj):
    req = urllib.request.Request('http://127.0.0.1:%d%s' % (port, path), data=json.dumps(obj).encode(), method='POST')
    try: return json.loads(urllib.request.urlopen(req).read())
    except urllib.error.HTTPError as e: return json.loads(e.read())

def main(S=3):
    sess, ser, lines = tc.make(S)
    app = scwin.App(sess, HERE); sess.connect()
    srv = scwin.serve(app, 0); port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    bad = []
    page = urllib.request.urlopen('http://127.0.0.1:%d/' % port).read().decode()
    if 'S-Core' not in page or '__CMDS__' in page or 'load cli_demo/demo.scs' not in page: bad.append('page not served properly')
    r = post(port, '/api/run', dict(commands=scwin.DEFAULT_COMMANDS.replace('wait', 'wait 3000'),   # the simulation is slow in real time, not in board time
         data=scwin.DEFAULT_DATA, read_addr='0', read_n='8'))
    if not r['ok']: bad.append('run refused: %s' % r)
    if post(port, '/api/run', dict(commands='', data=''))['ok']: bad.append('a second run while running should be refused')
    seen_running = False; t0 = time.time()
    while time.time() - t0 < 600:
        st = get(port, '/api/state')
        if st['cores'] and any(c['state'] == 'running' for c in st['cores']): seen_running = True
        if not st['running']: break
        time.sleep(1)
    st = get(port, '/api/state')
    print('\n'.join(st['log'][-6:]))
    print('cores:', st['cores']); print('queue:', st['queue'])
    if st['running']: bad.append('run did not finish')
    if st['error']: bad.append('error: %s' % st['error'])
    states = {j['name']: [] for j in st['jobs']}
    for j in st['jobs']: states[j['name']].append((j['state'], j['a0'], j['why']))
    want = {'spin': ('done', 200), 'fib': ('done', 144), 'sum': ('done', 136)}
    for n, (sta, a0) in want.items():
        for x in states.get(n, []):
            if x[0] != sta or x[1] != a0: bad.append('%s: %s' % (n, x))
    if len(st['jobs']) != 7: bad.append('7 jobs expected, got %d' % len(st['jobs']))
    if not any(x[0] == 'trap' and x[2] for x in states.get('bad', [])): bad.append('bad job should trap with a reason: %s' % states.get('bad'))
    if st['ram']['words'] != [1, 2, 3, 4, 5, 6, 7, 8]: bad.append('words read back: %s' % st['ram'])
    if not seen_running: print('note: the polling never caught a core running (the page would still show it live)')
    if not st['cores'] or len(st['cores']) != S: bad.append('core view missing')
    print('RESULT', 'PASS' if not bad else 'FAIL'); [print('  ' + m) for m in bad]
    return not bad

if __name__ == '__main__': sys.exit(0 if main(int(sys.argv[1]) if len(sys.argv) > 1 else 3) else 1)
