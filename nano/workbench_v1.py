"""
workbench_v1.py — the new Unicell-S workbench. A thin HTTP layer
directly over `vm_ai_port_v1.VMSession` (`points.md #362`), built per
`docs/stripped-cell/design-notes/workbench_scope.md`'s own real audit of
the old `workbench.py`: everything address/`gate_state`-keyed there is
dead under the new system shape; the replacement DATA LAYER already
exists (`VMSession`, `#359`) and is reused here unchanged, not
reimplemented.

TWO REAL LAYERS, DELIBERATELY SEPARATE: `WorkbenchController` holds the
current `VMSession` and implements every real operation as a plain
Python method returning a JSON-ready dict -- it has NO knowledge of
HTTP at all, so it's directly, fully testable without a live socket.
`WorkbenchHandler` is a thin `http.server` request handler dispatching
onto a `WorkbenchController` instance -- the reusable part of the old
file's own shape (`http.server`/threading is genuine, addressing-
agnostic infrastructure, kept as the same real precedent, not
reinvented).

API, row/col-keyed throughout, never an address anywhere:
    GET  /               -- serves the HTML/JS page
    GET  /state           -- VMSession.describe(), as JSON
    POST /compile          -- {"source", "language": "dsl"|"python"}
    POST /step               -- {"n": 1}
    POST /deliver              -- {"row", "col", "direction", "value", "injected"}
    POST /inject                 -- {"row", "col", "value"}
"""

from __future__ import annotations

import http.server
import json
import os
import sys
import threading
import webbrowser
from typing import Any, Dict, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vm_ai_port_v1 import VMSession, CompileFailure
from dsl_diagnostics_v1 import CompileDiagnostic
from unicell_automaton_v1 import N, S, E, W

_DIRS = {"n": N, "s": S, "e": E, "w": W}


def _diag_to_dict(d: CompileDiagnostic) -> Dict[str, Any]:
    return {
        "severity": d.severity, "stage": d.stage, "what": d.what,
        "problem": d.problem, "why": d.why, "suggestion": d.suggestion,
        "span": list(d.span) if d.span else None,
    }


class WorkbenchController:
    """Holds the current `VMSession` and every real API operation --
    zero HTTP knowledge, directly testable. Not designed to represent
    multiple concurrent sessions; one workbench, one program at a time,
    matching the old workbench's own single-array model, just without
    the address-space baggage."""

    def __init__(self):
        self.session: Optional[VMSession] = None

    def compile(self, source: str, language: str = "dsl") -> Dict[str, Any]:
        try:
            if language == "python":
                session = VMSession.from_python(source)
            else:
                session = VMSession.from_dsl(source)
        except CompileFailure as e:
            return {"ok": False, "diagnostics": [_diag_to_dict(d) for d in e.diagnostics]}
        self.session = session
        return {
            "ok": True,
            "diagnostics": [_diag_to_dict(d) for d in session.diagnostics],
            "state": session.describe(),
        }

    def state(self) -> Dict[str, Any]:
        if self.session is None:
            return {"ok": False, "error": "no program compiled yet"}
        return {"ok": True, "state": self.session.describe()}

    def step(self, n: int = 1) -> Dict[str, Any]:
        if self.session is None:
            return {"ok": False, "error": "no program compiled yet"}
        self.session.tick(n)
        return {"ok": True, "state": self.session.describe()}

    def deliver(self, row: int, col: int, direction: Optional[str] = None,
                value: int = 0, injected: bool = False) -> Dict[str, Any]:
        if self.session is None:
            return {"ok": False, "error": "no program compiled yet"}
        try:
            if injected:
                accepted, _forward = self.session.deliver(row, col, {}, value)
            else:
                if direction not in _DIRS:
                    return {"ok": False, "error": f"unknown direction {direction!r}, "
                                                   f"expected one of n/s/e/w"}
                accepted, _forward = self.session.deliver(row, col, {_DIRS[direction]: value}, None)
        except KeyError as e:
            return {"ok": False, "error": str(e)}
        return {"ok": True, "accepted": accepted, "state": self.session.describe()}

    def inject(self, row: int, col: int, value: int) -> Dict[str, Any]:
        if self.session is None:
            return {"ok": False, "error": "no program compiled yet"}
        self.session.inject(row, col, value)
        return {"ok": True, "state": self.session.describe()}


WORKBENCH_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Unicell-S Workbench</title>
<style>
  body { font-family: monospace; background: #1a1a1a; color: #ddd; margin: 0; padding: 16px; }
  textarea { width: 100%; height: 140px; background: #111; color: #9f9; border: 1px solid #444; }
  button { background: #333; color: #ddd; border: 1px solid #555; padding: 6px 12px; margin: 4px 4px 4px 0; cursor: pointer; }
  button:hover { background: #444; }
  #grid { display: grid; gap: 4px; margin-top: 12px; }
  .cell { border: 1px solid #555; padding: 8px; min-width: 90px; font-size: 11px; }
  .cell .core { color: #6cf; font-weight: bold; }
  #diagnostics { color: #f88; white-space: pre-wrap; margin-top: 8px; }
  #tickcount { color: #9f9; }
</style>
</head>
<body>
<h2>Unicell-S Workbench</h2>
<textarea id="source" placeholder="program p { place r1 as ram_constant at (0,0) { out: e init_data: 42 } }"></textarea><br>
<button onclick="compileProgram()">Compile</button>
<button onclick="step(1)">Step</button>
<button onclick="step(10)">Step 10</button>
<button onclick="refresh()">Refresh</button>
<span id="tickcount"></span>
<div id="diagnostics"></div>
<div id="grid"></div>
<script>
async function post(path, body) {
  const r = await fetch(path, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body || {})});
  return r.json();
}
async function get(path) {
  const r = await fetch(path);
  return r.json();
}
function renderState(state) {
  document.getElementById("tickcount").textContent = "tick " + state.tick_count;
  const grid = document.getElementById("grid");
  grid.innerHTML = "";
  for (const key in state.cells) {
    const c = state.cells[key];
    const div = document.createElement("div");
    div.className = "cell";
    div.innerHTML = `<div class="core">${c.core} (${c.row},${c.col})</div>` +
      Object.entries(c[c.core] || {}).map(([k,v]) => `${k}: ${JSON.stringify(v)}`).join("<br>");
    grid.appendChild(div);
  }
}
function renderDiagnostics(diags) {
  document.getElementById("diagnostics").textContent =
    (diags || []).map(d => `${d.severity.toUpperCase()} [${d.stage}]: ${d.problem}`).join("\n");
}
async function compileProgram() {
  const source = document.getElementById("source").value;
  const result = await post("/compile", {source: source, language: "dsl"});
  renderDiagnostics(result.diagnostics);
  if (result.ok) renderState(result.state);
}
async function step(n) {
  const result = await post("/step", {n: n});
  if (result.ok) renderState(result.state);
}
async function refresh() {
  const result = await get("/state");
  if (result.ok) renderState(result.state);
}
</script>
</body>
</html>
"""


class WorkbenchHandler(http.server.BaseHTTPRequestHandler):
    controller: Optional[WorkbenchController] = None

    def _json_response(self, data: Dict[str, Any], status: int = 200) -> None:
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _html_response(self, html: str) -> None:
        body = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length))

    def do_GET(self):
        if self.path == "/state":
            self._json_response(self.controller.state())
        elif self.path in ("/", "/index.html"):
            self._html_response(WORKBENCH_HTML)
        else:
            self._json_response({"ok": False, "error": "not found"}, status=404)

    def do_POST(self):
        body = self._read_json_body()
        if self.path == "/compile":
            self._json_response(self.controller.compile(body.get("source", ""),
                                                          body.get("language", "dsl")))
        elif self.path == "/step":
            self._json_response(self.controller.step(body.get("n", 1)))
        elif self.path == "/deliver":
            self._json_response(self.controller.deliver(
                body.get("row"), body.get("col"), body.get("direction"),
                body.get("value", 0), body.get("injected", False)))
        elif self.path == "/inject":
            self._json_response(self.controller.inject(
                body.get("row"), body.get("col"), body.get("value", 0)))
        else:
            self._json_response({"ok": False, "error": "not found"}, status=404)

    def log_message(self, fmt, *args):
        pass   # quiet -- matches the old workbench's own convention


def serve(port: int = 7420, open_browser: bool = False) -> http.server.HTTPServer:
    WorkbenchHandler.controller = WorkbenchController()
    server = http.server.HTTPServer(("localhost", port), WorkbenchHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    if open_browser:
        webbrowser.open(f"http://localhost:{port}")
    return server


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 7420
    server = serve(port, open_browser=True)
    print(f"Unicell-S workbench serving at http://localhost:{port}")
    try:
        while True:
            pass
    except KeyboardInterrupt:
        server.shutdown()
