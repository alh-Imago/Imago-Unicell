#!/usr/bin/env python3
"""unicell_frontend_v1.py -- local front end for building and running designs on a card (ledger #1255).

Runs on Alan's own PC (Linux), standard library only. Serves one browser page on 127.0.0.1 with
  * a picker listing the design folders in the demo folder,
  * two REAL shells (Build and Card) shown in the page; choosing a design sends `cd <folder>` to both,
  * buttons that send fixed, whitelisted commands into those shells (make, make program, the OpenOCD scripts),
  * a results window: build summary (timing lines) and decoded card reads, from the files the scripts write.
It never installs anything and never builds on its own. The Build shell is where the user enters the openXC7 Nix shell
(button "Enter openXC7 shell" types the command; the user can also type it). The card is loaded into SRAM only: no button writes flash.

  python3 tools/frontend/unicell_frontend_v1.py --demo ~/openFPGALoader/build/demo-projects
"""
import argparse
import base64
import fcntl
import json
import os
import pty
import queue
import re
import secrets
import select
import signal
import struct
import subprocess
import sys
import termios
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
NIX_ENTER = "nix develop github:openxc7/toolchain-nix"
LOAD_CMD = 'make program JTAG_LINK="-c ft232"'          # SRAM only (the MAN's build.load_command); no button writes flash
OPENOCD = "nix shell nixpkgs#openocd --command sh "
ENV_CHECK = ('for t in yosys nextpnr-xilinx openFPGALoader make; do command -v $t >/dev/null && echo "ok       $t" || echo "MISSING  $t"; done; '
             'echo "KINTEX7_CHIPDB=${KINTEX7_CHIPDB:-<not set>}"')

# ---- the whitelist: id -> (terminal, label, command template, argument spec or None). Arguments are digits only.
BUTTONS = {
    "enter_nix":  ("build", "Enter openXC7 shell", NIX_ENTER, None),
    "env_check":  ("build", "Check environment", ENV_CHECK, None),
    "make":       ("build", "Build (make)", "make 2>&1 | tee build.log", None),
    "load":       ("build", "Load into the card (SRAM)", LOAD_CMD, None),
    "card_env":   ("card", "Check OpenOCD", "nix shell nixpkgs#openocd --command openocd --version 2>&1 | head -1", None),
    "read":       ("card", "Read state", OPENOCD + "freeze_read.sh", None),
    "freeze_at":  ("card", "Freeze at count", OPENOCD + "freeze_at.sh {0}", ["count"]),
    "release":    ("card", "Release", OPENOCD + "freeze_release.sh", None),
    "save":       ("card", "Save (freeze at count)", OPENOCD + "freeze_save.sh {0}", ["count"]),
    "load_saved": ("card", "Load saved state", OPENOCD + "freeze_load.sh saved_{0}.txt", ["count"]),
    "load_run":   ("card", "Load saved state and run", OPENOCD + "freeze_load.sh saved_{0}.txt run", ["count"]),
    "saveload":   ("card", "Save / load round trip", OPENOCD + "freeze_saveload_test.sh {0} {1}", ["count", "other count"]),
    "sweep":      ("card", "Sweep counts", OPENOCD + "freeze_sweep.sh {0} {1} {2}", ["from", "to", "step"]),
    "clock":      ("card", "Measure clock", OPENOCD + "measure_clock.sh", None),
    "user1":      ("card", "Read USER1", OPENOCD + "read_user1.sh", None),
}
# which buttons a design folder offers: build buttons if it has a Makefile; card buttons by the scripts it contains
CARD_NEEDS = {"read": "freeze_read.sh", "freeze_at": "freeze_at.sh", "release": "freeze_release.sh", "save": "freeze_save.sh",
              "load_saved": "freeze_load.sh", "load_run": "freeze_load.sh", "saveload": "freeze_saveload_test.sh", "sweep": "freeze_sweep.sh",
              "clock": "measure_clock.sh", "user1": "read_user1.sh"}


def kit_info(folder):
    """What a design folder offers. A kit.json in the folder (optional) gives title/description; the buttons follow from the files."""
    info = {"name": os.path.basename(folder), "title": os.path.basename(folder), "description": "", "buttons": []}
    kj = os.path.join(folder, "kit.json")
    if os.path.isfile(kj):
        try:
            info.update({k: v for k, v in json.load(open(kj)).items() if k in ("title", "description")})
        except (OSError, ValueError):
            pass
    elif os.path.isfile(os.path.join(folder, "README.md")):
        for line in open(os.path.join(folder, "README.md"), errors="replace"):
            if line.startswith("#"):
                info["title"] = line.lstrip("# ").strip()[:200]
                break
    has_make = os.path.isfile(os.path.join(folder, "Makefile"))
    for bid in ("env_check", "make", "load"):
        if has_make:
            info["buttons"].append(bid)
    for bid, need in CARD_NEEDS.items():
        if os.path.isfile(os.path.join(folder, need)):
            info["buttons"].append(bid)
    return info


def list_kits(demo):
    out = []
    try:
        names = sorted(os.listdir(demo))
    except OSError:
        return out
    for n in names:
        p = os.path.join(demo, n)
        if os.path.isdir(p) and (os.path.isfile(os.path.join(p, "Makefile")) or os.path.isfile(os.path.join(p, "kit.json"))):
            out.append(kit_info(p))
    return out


class Term:
    """A real shell on a pty. Output is kept in a ring so a reloaded page can catch up."""
    def __init__(self, name):
        self.name = name
        self.pid, self.fd = pty.fork()
        if self.pid == 0:
            env = dict(os.environ, TERM="xterm-256color", PS1=f"[{name}] \\w $ ")
            os.execvpe("bash", ["bash", "--norc", "-i"], env)
        self.buf = bytearray()
        self.lock = threading.Lock()
        self.subs = []
        self.resize(24, 100)
        threading.Thread(target=self._reader, daemon=True).start()

    def _reader(self):
        while True:
            try:
                r, _, _ = select.select([self.fd], [], [], 1.0)
                if not r:
                    continue
                data = os.read(self.fd, 65536)
            except OSError:
                break
            if not data:
                break
            with self.lock:
                self.buf += data
                if len(self.buf) > 400000:
                    del self.buf[:len(self.buf) - 300000]
                for q in list(self.subs):
                    q.put(data)

    def write(self, data):
        os.write(self.fd, data)

    def resize(self, rows, cols):
        fcntl.ioctl(self.fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))

    def subscribe(self):
        q = queue.Queue()
        with self.lock:
            q.put(bytes(self.buf))
            self.subs.append(q)
        return q

    def unsubscribe(self, q):
        with self.lock:
            if q in self.subs:
                self.subs.remove(q)

    def close(self):
        try:
            os.kill(self.pid, signal.SIGHUP)
        except OSError:
            pass


class State:
    def __init__(self, demo):
        self.demo = os.path.abspath(os.path.expanduser(demo))
        self.terms = {"build": Term("build"), "card": Term("card")}
        self.selected = None
        self.t_selected = 0.0
        self.token = secrets.token_urlsafe(16)

    def select(self, name):
        kits = {k["name"]: k for k in list_kits(self.demo)}
        if name not in kits:
            raise ValueError("not a design folder in the demo folder")
        folder = os.path.join(self.demo, name)
        for t in self.terms.values():
            t.write(("cd " + shell_quote(folder) + "\n").encode())
        self.selected = name
        self.t_selected = time.time()
        return kits[name]

    def run(self, bid, args):
        if bid not in BUTTONS:
            raise ValueError("unknown button")
        term, _, tmpl, spec = BUTTONS[bid]
        spec = spec or []
        if len(args) != len(spec) or not all(re.fullmatch(r"[0-9]{1,6}", str(a)) for a in args):
            raise ValueError("this button needs %d whole number(s)" % len(spec))
        if self.selected is None and bid != "enter_nix":
            raise ValueError("pick a design first")
        if bid in CARD_NEEDS and not os.path.isfile(os.path.join(self.demo, self.selected, CARD_NEEDS[bid])):
            raise ValueError("this design has no " + CARD_NEEDS[bid])
        cmd = tmpl.format(*args) if spec else tmpl      # templates without arguments are sent as they are (they contain shell braces)
        self.terms[term].write((cmd + "\n").encode())
        return term, cmd

    def results(self):
        if not self.selected:
            return {"files": [], "build": None}
        folder = os.path.join(self.demo, self.selected)
        files = []
        for n in sorted(os.listdir(folder)):
            p = os.path.join(folder, n)
            if os.path.isfile(p) and re.search(r"\.(log|txt|csv)$", n):
                files.append({"name": n, "mtime": os.path.getmtime(p), "new": os.path.getmtime(p) >= self.t_selected, "size": os.path.getsize(p)})
        return {"files": files, "build": build_summary(folder)}

    def view(self, fname):
        folder = os.path.join(self.demo, self.selected or "")
        if not self.selected or fname != os.path.basename(fname) or not re.search(r"\.(log|txt|csv)$", fname):
            raise ValueError("not a result file")
        p = os.path.join(folder, fname)
        raw = open(p, errors="replace").read()
        decoded = None
        if "SNAP " in raw and os.path.isfile(os.path.join(folder, "decode_freeze.py")):
            if re.match(r"freeze_saveload_", fname) and os.path.isfile(os.path.join(folder, "check_saveload.py")):
                decoded = run_py(folder, "check_saveload.py", p)
            else:
                decoded = run_py(folder, "decode_freeze.py", p)
        return {"name": fname, "text": raw[-200000:], "decoded": decoded}


def run_py(folder, script, path):
    try:
        r = subprocess.run([sys.executable, "-I", os.path.join(folder, script), path], cwd=folder, capture_output=True, text=True, timeout=30)
        return (r.stdout + r.stderr)[-60000:]
    except (OSError, subprocess.TimeoutExpired) as e:
        return "decoder failed: %s" % e


def build_summary(folder):
    p = os.path.join(folder, "build.log")
    if not os.path.isfile(p):
        return None
    txt = open(p, errors="replace").read()
    fmax = re.findall(r"Max frequency for clock\s+'([^']+)':\s*([0-9.]+) MHz \((PASS|FAIL) at ([0-9.]+) MHz\)", txt)
    last = fmax[-3:] if fmax else []
    return {"mtime": os.path.getmtime(p), "fmax": [{"clock": c, "mhz": float(m), "verdict": v, "target": float(t)} for c, m, v, t in last],
            "errors": len(re.findall(r"(?m)^(make: \*\*\*|ERROR|Error:)", txt)),
            "verdict": ("NOT BUILT / FAILED" if not fmax else ("TIMING FAILED - do not load" if any(v == "FAIL" for _, _, v, _ in fmax[-3:]) else "timing passed"))}


def shell_quote(s):
    return "'" + s.replace("'", "'\\''") + "'"


PAGE = open(os.path.join(HERE, "page_v1.html")).read() if os.path.isfile(os.path.join(HERE, "page_v1.html")) else "page missing"


class H(BaseHTTPRequestHandler):
    st = None

    def log_message(self, *a):
        pass

    def _ok_host(self):
        host = (self.headers.get("Host") or "").split(":")[0]
        return host in ("127.0.0.1", "localhost")

    def _auth(self, qs=None):
        qs = qs if qs is not None else parse_qs(urlparse(self.path).query)
        return self._ok_host() and (qs.get("t", [""])[0] == self.st.token or self.headers.get("X-Token") == self.st.token)

    def _send(self, code, body, ctype="application/json"):
        b = body if isinstance(body, bytes) else body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        u = urlparse(self.path)
        qs = parse_qs(u.query)
        if not self._auth(qs):
            return self._send(403, "forbidden", "text/plain")
        if u.path == "/":
            return self._send(200, PAGE.replace("__TOKEN__", self.st.token), "text/html; charset=utf-8")
        if u.path == "/api/state":
            kits = list_kits(self.st.demo)
            return self._send(200, json.dumps({"demo": self.st.demo, "kits": kits, "selected": self.st.selected, "nix_enter": NIX_ENTER,
                                               "buttons": {k: {"term": v[0], "label": v[1], "args": v[3] or []} for k, v in BUTTONS.items()}}))
        if u.path == "/api/results":
            return self._send(200, json.dumps(self.st.results()))
        if u.path == "/api/file":
            try:
                return self._send(200, json.dumps(self.st.view(qs.get("name", [""])[0])))
            except (ValueError, OSError) as e:
                return self._send(400, json.dumps({"error": str(e)}))
        if u.path.startswith("/vendor/") and os.path.basename(u.path) in ("xterm.css", "xterm.js", "xterm-addon-fit.js"):
            ct = "text/css" if u.path.endswith(".css") else "application/javascript"
            return self._send(200, open(os.path.join(HERE, "vendor", os.path.basename(u.path)), "rb").read(), ct)
        m = re.fullmatch(r"/api/term/(build|card)/stream", u.path)
        if m:
            term = self.st.terms[m.group(1)]
            q = term.subscribe()
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            try:
                while True:
                    try:
                        data = q.get(timeout=15)
                        self.wfile.write(b"data: " + base64.b64encode(data) + b"\n\n")
                    except queue.Empty:
                        self.wfile.write(b": keepalive\n\n")
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass
            finally:
                term.unsubscribe(q)
            return
        self._send(404, "not found", "text/plain")

    def do_POST(self):
        if not self._auth():
            return self._send(403, "forbidden", "text/plain")
        n = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            return self._send(400, json.dumps({"error": "bad json"}))
        u = urlparse(self.path)
        try:
            if u.path == "/api/select":
                return self._send(200, json.dumps(self.st.select(str(body.get("name", "")))))
            if u.path == "/api/run":
                term, cmd = self.st.run(str(body.get("id", "")), [str(a) for a in body.get("args", [])])
                return self._send(200, json.dumps({"term": term, "command": cmd}))
            m = re.fullmatch(r"/api/term/(build|card)/(input|resize)", u.path)
            if m:
                t = self.st.terms[m.group(1)]
                if m.group(2) == "input":
                    t.write(base64.b64decode(body.get("data", "")))
                else:
                    t.resize(int(body.get("rows", 24)), int(body.get("cols", 100)))
                return self._send(200, "{}")
        except (ValueError, OSError, KeyError, IndexError) as e:
            return self._send(400, json.dumps({"error": str(e)}))
        self._send(404, "{}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--demo", default="~/openFPGALoader/build/demo-projects", help="the demo folder that holds the design folders")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true")
    a = ap.parse_args()
    H.st = State(a.demo)
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), H)
    url = "http://127.0.0.1:%d/?t=%s" % (a.port, H.st.token)
    print("Imago UniCell front end.  Demo folder:", H.st.demo)
    print("Open this address in your browser:\n  " + url)
    if not a.no_browser:
        try:
            subprocess.Popen(["xdg-open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError:
            pass
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        for t in H.st.terms.values():
            t.close()


if __name__ == "__main__":
    main()
