"""
frontend_v1.py — points.md #557: the real "main front end" Alan asked
for, walking a user through this project's own real, step-by-step
build process. Same two-layer architecture as `workbench_v1.py`
(`WorkbenchController`/`WorkbenchHandler`), reused deliberately, not
reinvented: a plain-Python Controller with zero HTTP knowledge, and a
thin `http.server` Handler dispatching onto it.

REAL, HONEST SCOPE, matching this project's own standing discipline of
naming what's explicitly not built rather than faking it:
- Welcome, MAN-file generation, and cell-creation pages are REAL --
  they call directly into `tools/man_generate_v1.py` and
  `tools/project_assemble_v1.py`'s own real functions, the same code
  path the CLI itself uses (`assemble()`/`build_man()`), never a
  separate, parallel implementation that could drift out of sync.
- The Walker page and the Composer link are REAL, HONEST PLACEHOLDERS.
  Neither has any real code behind it yet -- the Walker's own design is
  fully converged (`points.md` #501) but unbuilt; Composer's own real
  scope (`docs/stripped-cell/design-notes/composer_scope.md`) is a
  visual placement-review tool with RTL generation explicitly excluded,
  also unbuilt. These slots exist now, deliberately, so wiring in the
  real thing later needs no restructuring -- but they say plainly
  "not built yet" rather than pretending to work.
- Every real, action-performing page ALSO shows the exact equivalent
  CLI command, per Alan's own explicit request -- some people will
  always prefer the command line.
"""

import http.server
import json
import os
import sys
import threading
import webbrowser
from typing import Any, Dict, Optional

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))

import man_generate_v1  # noqa: E402
import project_assemble_v1  # noqa: E402


class FrontendController:
    """Zero HTTP knowledge, matching WorkbenchController's own real
    precedent -- every real operation is a plain Python method
    returning a JSON-ready dict, fully testable without a live socket."""

    def generate_man(self, fields: Dict[str, Any]) -> Dict[str, Any]:
        required = ["card_id", "part", "alm_total", "dsp_total", "clk_pin", "led0_pin", "led1_pin", "output"]
        missing = [k for k in required if not fields.get(k)]
        if missing:
            return {"ok": False, "error": f"missing required field(s): {', '.join(missing)}"}
        try:
            man = man_generate_v1.build_man(
                card_id=fields["card_id"], part=fields["part"],
                family=fields.get("family") or "Arria 10",
                jtag_idcode=fields.get("jtag_idcode") or None,
                alm_total=int(fields["alm_total"]), dsp_total=int(fields["dsp_total"]),
                m20k_bits=int(fields["m20k_bits"]) if fields.get("m20k_bits") else None,
                clk_pin=fields["clk_pin"], led0_pin=fields["led0_pin"], led1_pin=fields["led1_pin"],
            )
            with open(fields["output"], "w") as f:
                json.dump(man, f, indent=2)
        except Exception as e:
            return {"ok": False, "error": str(e)}

        cli = (
            f"python3 tools/man_generate_v1.py --card-id {fields['card_id']} "
            f"--part {fields['part']} --family \"{fields.get('family') or 'Arria 10'}\" "
            f"--alm-total {fields['alm_total']} --dsp-total {fields['dsp_total']} "
            f"--clk-pin {fields['clk_pin']} --led0-pin {fields['led0_pin']} --led1-pin {fields['led1_pin']} "
            f"-o {fields['output']}"
        )
        return {"ok": True, "output": fields["output"], "cli_equivalent": cli}

    def create_project(self, fields: Dict[str, Any]) -> Dict[str, Any]:
        required = ["man_path", "cells", "output"]
        missing = [k for k in required if not fields.get(k)]
        if missing:
            return {"ok": False, "error": f"missing required field(s): {', '.join(missing)}"}
        try:
            result = project_assemble_v1.assemble(
                fields["man_path"], int(fields["cells"]), fields["output"],
                top=fields.get("top") or None,
            )
        except Exception as e:
            return {"ok": False, "error": str(e)}

        cli = f"python3 tools/project_assemble_v1.py --man {fields['man_path']} --cells {fields['cells']} --output {fields['output']}"
        if fields.get("top"):
            cli += f" --top {fields['top']}"
        result["ok"] = True
        result["cli_equivalent"] = cli
        return result


# ── Real HTML, one block per page. Deliberately plain -- this is a
# real, working tool, not a design showcase. ─────────────────────────

PAGE_CSS = """
<style>
body { font-family: -apple-system, sans-serif; max-width: 760px; margin: 40px auto; padding: 0 20px; color: #222; line-height: 1.5; }
h1 { font-size: 1.4em; } h2 { font-size: 1.1em; margin-top: 2em; }
nav a { margin-right: 16px; }
.placeholder { background: #f5f5f0; border-left: 4px solid #c9a227; padding: 12px 16px; margin: 16px 0; }
.real { background: #f0f5f0; border-left: 4px solid #4a8; padding: 12px 16px; margin: 16px 0; }
label { display: block; margin-top: 10px; font-size: 0.9em; }
input { width: 100%; padding: 6px; box-sizing: border-box; margin-top: 2px; }
button { margin-top: 16px; padding: 8px 20px; }
pre { background: #f4f4f4; padding: 10px; overflow-x: auto; font-size: 0.85em; }
.result { margin-top: 16px; padding: 10px; }
.result.ok { background: #eafaf0; } .result.err { background: #faeaea; }
</style>
"""

NAV = '<nav><a href="/">Start</a> <a href="/man">1. Card / MAN file</a> <a href="/cells">2. Create cells</a> <a href="/walker">3. Walker</a> <a href="/menu">4. Other tools</a></nav>'


def page_welcome() -> str:
    return f"""<!doctype html><html><head><title>Imago UniCell</title>{PAGE_CSS}</head><body>
{NAV}
<h1>Imago UniCell -- getting started</h1>
<p>This tool walks through the real, current steps for taking a card
from "nothing generated yet" to a real, buildable Quartus project,
matching the order this project's own build process actually follows:</p>
<ol>
<li><b>Card / MAN file</b> -- describe your card's own real capabilities once.</li>
<li><b>Create cells</b> -- generate a real, importable Quartus project for N cells.</li>
<li><b>Walker</b> -- (not yet built) real, live discovery of a programmed chip's own topology.</li>
<li><b>Other tools</b> -- the real VM/workbench, the compiler, and (not yet built) Composer.</li>
</ol>
<p>Every real, action-performing page here also shows the exact
equivalent command-line invocation -- this tool is a convenience, not
the only way to do any of this.</p>
</body></html>"""


def page_man(result: Optional[Dict[str, Any]] = None) -> str:
    result_html = ""
    if result is not None:
        cls = "ok" if result.get("ok") else "err"
        if result.get("ok"):
            result_html = f'<div class="result {cls}"><b>Wrote:</b> {result["output"]}<h2>Equivalent CLI</h2><pre>{result["cli_equivalent"]}</pre></div>'
        else:
            result_html = f'<div class="result {cls}"><b>Error:</b> {result.get("error")}</div>'
    return f"""<!doctype html><html><head><title>Card / MAN file</title>{PAGE_CSS}</head><body>
{NAV}
<h1>Step 1: describe your card</h1>
<div class="real">Real, working -- generates an actual, schema-compatible MAN
file via <code>tools/man_generate_v1.py</code> (points.md #557).</div>
<form method="post" action="/man">
<label>Card ID<input name="card_id" required></label>
<label>Device part (e.g. 10AX066H2F34E2SG)<input name="part" required></label>
<label>Quartus FAMILY string (e.g. "Arria 10" -- the exact value Quartus expects)<input name="family" value="Arria 10"></label>
<label>Total ALMs<input name="alm_total" type="number" required></label>
<label>Total DSP blocks<input name="dsp_total" type="number" required></label>
<label>Total M20K bits (optional)<input name="m20k_bits" type="number"></label>
<label>CLK_100M pin (e.g. PIN_E23)<input name="clk_pin" required></label>
<label>LED0_N pin (e.g. PIN_AE7)<input name="led0_pin" required></label>
<label>LED1_N pin (e.g. PIN_AH2)<input name="led1_pin" required></label>
<label>Output path (e.g. docs/man/my-card.man.json)<input name="output" required></label>
<button type="submit">Generate MAN file</button>
</form>
{result_html}
</body></html>"""


def page_cells(result: Optional[Dict[str, Any]] = None) -> str:
    result_html = ""
    if result is not None:
        cls = "ok" if result.get("ok") else "err"
        if result.get("ok"):
            result_html = (
                f'<div class="result {cls}"><b>Wrote {result["files_written"]} files to:</b> {result["output"]}<br>'
                f'Grid: {result["rows"]}x{result["cols"]}, real ALM budget: {result["alm_total"]:,}'
                f'<h2>Equivalent CLI</h2><pre>{result["cli_equivalent"]}</pre></div>'
            )
        else:
            result_html = f'<div class="result {cls}"><b>Error:</b> {result.get("error")}</div>'
    return f"""<!doctype html><html><head><title>Create cells</title>{PAGE_CSS}</head><body>
{NAV}
<h1>Step 2: generate a real Quartus project</h1>
<div class="real">Real, working -- generates a complete, importable Quartus
project for N cells via <code>tools/project_assemble_v1.py</code>
(points.md #552/#554/#555). One real, unconstrained input feeds the
array, every cell's own outputs XOR-reduce into one observable output,
and every cell genuinely loads a real, unpredictable configuration
once at boot -- guarding directly against Quartus proving the array's
own logic constant and collapsing it away (a real failure this project
hit and fixed, #554).</div>
<form method="post" action="/cells">
<label>MAN file path<input name="man_path" required></label>
<label>Cell count<input name="cells" type="number" required></label>
<label>Output folder (outside this repo -- required, #556)<input name="output" required></label>
<label>Top-level module name (optional)<input name="top"></label>
<button type="submit">Generate project</button>
</form>
{result_html}
</body></html>"""


def page_walker() -> str:
    return f"""<!doctype html><html><head><title>Walker</title>{PAGE_CSS}</head><body>
{NAV}
<h1>Step 3: the Walker</h1>
<div class="placeholder"><b>Not built yet.</b> This slot exists so the
real thing can be wired in later without restructuring this tool --
what's below is the real, already fully-converged DESIGN
(points.md #501), not a working feature.</div>
<p>Once built, the Walker will be a real, live, host-driven discovery
tool: starting at a known cell, it pings each real cardinal direction
in turn -- a cell answers with its own real ID and type if the ping
targets "self," or relays the ping unchanged out one physical port if
it targets a direction. The host walks outward, one real hop at a
time, building a genuine, live map of a PROGRAMMED chip's own actual
topology -- deliberately not a static, RTL-source guess (see points.md
#551 for why that distinction matters), and not fooled by a build that
compiled clean while actually being the wrong design (points.md #535,
#445 -- both real, lived examples of exactly that risk).</p>
<p>Specialist hardware (BRAM, DSP) is never itself a ping-answering
endpoint -- a real, dedicated header cell answers on its behalf, so
the walk never needs to understand what's behind it.</p>
<p>This build is explicitly gated on a real, full-card array existing
first (Step 2) -- there's nothing meaningful to walk on a single cell.</p>
</body></html>"""


def page_menu() -> str:
    return f"""<!doctype html><html><head><title>Other tools</title>{PAGE_CSS}</head><body>
{NAV}
<h1>Step 4: the rest of the toolchain</h1>

<h2>VM / Workbench -- real, working</h2>
<div class="real">A real, already-working browser tool: compile a
program, watch it run, drive individual cells.</div>
<pre>python3 nano/workbench_v1.py
# -&gt; http://localhost:7420</pre>

<h2>Compiler / DSL -- real, working</h2>
<div class="real">The real Unicell-S DSL and compiler --
see <code>docs/stripped-cell/UNICELL_S_DSL_MANUAL.md</code> for the
language reference.</div>
<pre>python3 nano/dsl_cli_v1.py your_program.uc -o out.icm</pre>

<h2>Composer -- not built yet</h2>
<div class="placeholder">This slot exists for later, deliberately not
faked. Composer's own real, decided scope
(<code>docs/stripped-cell/design-notes/composer_scope.md</code>) is a
visual PLACEMENT-REVIEW tool for an already-compiled model -- letting
a person see where the automated loader put things and adjust it
before committing. RTL generation is explicitly, deliberately excluded
from its own scope -- that job belongs to Step 2's own real generator
instead. No code exists for Composer yet.</div>
</body></html>"""


class FrontendHandler(http.server.BaseHTTPRequestHandler):
    controller: Optional[FrontendController] = None

    def _html_response(self, html: str, status: int = 200) -> None:
        body = html.encode()
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_form_body(self) -> Dict[str, str]:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length).decode()
        out = {}
        for pair in raw.split("&"):
            if "=" in pair:
                k, v = pair.split("=", 1)
                out[_url_unquote(k)] = _url_unquote(v)
        return out

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._html_response(page_welcome())
        elif self.path == "/man":
            self._html_response(page_man())
        elif self.path == "/cells":
            self._html_response(page_cells())
        elif self.path == "/walker":
            self._html_response(page_walker())
        elif self.path == "/menu":
            self._html_response(page_menu())
        else:
            self._html_response("<h1>404</h1>", status=404)

    def do_POST(self):
        fields = self._read_form_body()
        if self.path == "/man":
            result = self.controller.generate_man(fields)
            self._html_response(page_man(result))
        elif self.path == "/cells":
            result = self.controller.create_project(fields)
            self._html_response(page_cells(result))
        else:
            self._html_response("<h1>404</h1>", status=404)

    def log_message(self, fmt, *args):
        pass


def _url_unquote(s: str) -> str:
    s = s.replace("+", " ")
    out, i = [], 0
    while i < len(s):
        if s[i] == "%" and i + 2 < len(s):
            out.append(chr(int(s[i + 1:i + 3], 16)))
            i += 3
        else:
            out.append(s[i])
            i += 1
    return "".join(out)


def serve(port: int = 7421, open_browser: bool = False) -> http.server.HTTPServer:
    FrontendHandler.controller = FrontendController()
    server = http.server.HTTPServer(("localhost", port), FrontendHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    if open_browser:
        webbrowser.open(f"http://localhost:{port}")
    return server


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 7421
    server = serve(port, open_browser=True)
    print(f"Imago UniCell front end serving at http://localhost:{port}")
    try:
        while True:
            pass
    except KeyboardInterrupt:
        server.shutdown()
