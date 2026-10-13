"""Ledger #1138: the v2 board runner (Python reader opened before the load) works end to end against a simulated board: a fake openFPGALoader, a pty that
starts printing the design's own report line only AFTER the 'load', and the folder's board_collect.py.  Also checks that the old stty+cat lines are gone."""
import json, os, pty, shutil, subprocess, sys, tempfile, threading, time
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import board_runner_v2 as R


def test_convert_removes_stty_cat_reader():
    for d in ("board_tests_designs", "board_tests_loops", "board_tests"):
        src = os.path.join(ROOT, "fpga", d, "run_all.sh")
        if not os.path.exists(src):
            continue
        out = R.convert(open(src).read())
        assert "cat \"$Q\"" not in out and "timeout 7 cat" not in out
        assert "watch_serial.py" in out and "BOOTWAIT" in out


def test_end_to_end_with_simulated_board():
    d = os.path.join(ROOT, "fpga", "board_tests_designs")
    if not os.path.exists(os.path.join(d, "std_tree4.json")):
        return
    meta = json.load(open(os.path.join(d, "std_tree4.json")))
    line = meta["sim_line"]
    tmp = tempfile.mkdtemp()
    try:
        work = os.path.join(tmp, "run"); os.mkdir(work)
        for f in ("std_tree4.fs", "std_tree4.json", "board_collect.py"):
            shutil.copy(os.path.join(d, f), work)
        open(os.path.join(work, "run_all_v2.sh"), "w").write(R.convert(open(os.path.join(d, "run_all.sh")).read()))
        shutil.copy(os.path.join(ROOT, "tools", "serial_capture_v1.py"), os.path.join(work, "watch_serial.py"))
        bindir = os.path.join(tmp, "bin"); os.mkdir(bindir)
        flag = os.path.join(tmp, "loaded")
        open(os.path.join(bindir, "openFPGALoader"), "w").write("#!/bin/sh\nsleep 1\ntouch %s\nexit 0\n" % flag)
        os.chmod(os.path.join(bindir, "openFPGALoader"), 0o755)
        m, s = pty.openpty(); port = os.ttyname(s)
        stop = []
        def board():
            while not stop:
                if os.path.exists(flag):
                    try: os.write(m, (line + "\r\n").encode())
                    except OSError: return
                time.sleep(0.05)
        th = threading.Thread(target=board, daemon=True); th.start()
        env = dict(os.environ, PATH=bindir + os.pathsep + os.environ["PATH"], BOOTWAIT="1", SECS="5", ONLY="std_tree4")
        r = subprocess.run(["sh", "run_all_v2.sh", port], cwd=work, env=env, capture_output=True, text=True, timeout=120)
        stop.append(1)
        assert "[std_tree4] PASS" in r.stdout, r.stdout + r.stderr
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
