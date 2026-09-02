"""
frontend_v1.py — points.md #557: the real "main front end" Alan asked
for, walking a user through this project's own real, step-by-step
build process. Same two-layer architecture as `workbench_v1.py`
(`WorkbenchController`/`WorkbenchHandler`), reused deliberately, not
reinvented: a plain-Python Controller with zero HTTP knowledge, and a
thin `http.server` Handler dispatching onto it.

REAL, HONEST SCOPE, matching this project's own standing discipline of
naming what's explicitly not built rather than faking it:
- Welcome, MAN-file generation, cell-creation, and the Walker page are
  all REAL -- they call directly into `tools/man_generate_v1.py`,
  `tools/project_assemble_v1.py`, and `vm_ai_port_v1.py`/
  `walker_sim_v1.py`'s own real functions, the same code paths their
  CLIs use, never a separate, parallel implementation that could drift
  out of sync. The Walker page is explicit that it's the SIMULATED
  version (points.md #602) -- a VM-mirrored grid, not real silicon.
- The Composer link is a REAL, HONEST PLACEHOLDER. No real code exists
  behind it yet -- its own real scope (`docs/stripped-cell/design-
  notes/composer_scope.md`) is a visual placement-review tool with RTL
  generation explicitly excluded. This slot exists now, deliberately,
  so wiring in the real thing later needs no restructuring -- but it
  says plainly "not built yet" rather than pretending to work.
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
import manual_generate_v1  # noqa: E402
import vm_ai_port_v1  # noqa: E402
import walker_sim_v1  # noqa: E402


class FrontendController:
    """Zero HTTP knowledge, matching WorkbenchController's own real
    precedent -- every real operation is a plain Python method
    returning a JSON-ready dict, fully testable without a live socket."""

    @staticmethod
    def _parse_pin_table(raw: str) -> Dict[str, Dict[str, str]]:
        """points.md #599: real, user-supplied pin-location table --
        one 'group.name = LOCATION' per line, e.g. 'jtag.tck = PIN_AH12'.
        Never auto-parsed from a .pin file or any other source; this only
        parses what the user directly typed. group must be jtag/config/
        extra -- anything else (or no dot) is routed to extra. Raises
        ValueError with a line-specific message on malformed input."""
        groups: Dict[str, Dict[str, str]] = {"jtag": {}, "config": {}, "extra": {}}
        for lineno, line in enumerate(raw.splitlines(), start=1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                raise ValueError(f"pin table line {lineno}: expected 'group.name = LOCATION', got: {line!r}")
            key, loc = line.split("=", 1)
            key, loc = key.strip(), loc.strip()
            if not loc:
                raise ValueError(f"pin table line {lineno}: missing location for {key!r}")
            if "." in key:
                group, name = key.split(".", 1)
            else:
                group, name = "extra", key
            group = group.strip().lower()
            name = name.strip()
            if group not in groups:
                group = "extra"
                name = key  # keep the original, unrecognized group prefix visible in the name
            groups[group][name] = loc
        return groups

    def generate_man(self, fields: Dict[str, Any]) -> Dict[str, Any]:
        required = ["card_id", "part", "alm_total", "dsp_total", "clk_pin", "led0_pin", "led1_pin", "output"]
        missing = [k for k in required if not fields.get(k)]
        if missing:
            return {"ok": False, "error": f"missing required field(s): {', '.join(missing)}"}
        try:
            pins = self._parse_pin_table(fields.get("pin_table") or "")
        except ValueError as e:
            return {"ok": False, "error": str(e)}
        try:
            man = man_generate_v1.build_man(
                card_id=fields["card_id"], part=fields["part"],
                family=fields.get("family") or "Arria 10",
                jtag_idcode=fields.get("jtag_idcode") or None,
                alm_total=int(fields["alm_total"]), dsp_total=int(fields["dsp_total"]),
                m20k_bits=int(fields["m20k_bits"]) if fields.get("m20k_bits") else None,
                clk_pin=fields["clk_pin"], led0_pin=fields["led0_pin"], led1_pin=fields["led1_pin"],
                jtag_pins=pins["jtag"], config_pins=pins["config"], extra_pins=pins["extra"],
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
        for name, loc in pins["jtag"].items():
            cli += f" --jtag-pin {name}={loc}"
        for name, loc in pins["config"].items():
            cli += f" --config-pin {name}={loc}"
        for name, loc in pins["extra"].items():
            cli += f" --extra-pin {name}={loc}"
        return {"ok": True, "output": fields["output"], "cli_equivalent": cli}

    def create_project(self, fields: Dict[str, Any]) -> Dict[str, Any]:
        required = ["man_path", "cells", "output"]
        missing = [k for k in required if not fields.get(k)]
        if missing:
            return {"ok": False, "error": f"missing required field(s): {', '.join(missing)}"}
        single_core = fields.get("single_core") or None
        core_path = fields.get("core_path") or None
        probe_name = fields.get("probe_name") or None
        shell = fields.get("shell") or "v3"
        logiclock = bool(fields.get("logiclock"))
        ll_fixed_alm = float(fields["ll_fixed_alm"]) if fields.get("ll_fixed_alm") else None
        ll_headroom = float(fields["ll_headroom"]) if fields.get("ll_headroom") else 1.25
        shell_file = fields.get("shell_file") or None
        shell_module = fields.get("shell_module") or None
        file_list = fields.get("file_list") or None
        files_string = fields.get("files") or None

        # Real, direct mirror of main()'s own CLI-side check (points.md
        # #590) -- assemble() itself doesn't enforce this, so any real
        # caller bypassing main() (this frontend included) must.
        if shell_file and not shell_module:
            return {"ok": False, "error": "shell file given without shell module: --shell-file requires the real module name inside that file (--shell-module)"}

        try:
            result = project_assemble_v1.assemble(
                fields["man_path"], int(fields["cells"]), fields["output"],
                top=fields.get("top") or None,
                single_core=single_core, core_path=core_path, probe_name=probe_name,
                shell=shell, logiclock=logiclock, ll_fixed_alm=ll_fixed_alm, ll_headroom=ll_headroom,
                shell_file=shell_file, shell_module=shell_module,
                file_list=file_list, files_string=files_string,
            )
        except Exception as e:
            return {"ok": False, "error": str(e)}

        cli = f"python3 tools/project_assemble_v1.py --man {fields['man_path']} --cells {fields['cells']} --output {fields['output']}"
        if fields.get("top"):
            cli += f" --top {fields['top']}"
        if single_core:
            cli += f" -S {single_core}"
        if core_path:
            cli += f" -x {core_path}"
        if probe_name:
            cli += f" -P {probe_name}"
        if not single_core:
            if shell != "v3":
                cli += f" --shell {shell}"
            if logiclock:
                cli += " --logiclock"
            if ll_fixed_alm is not None:
                cli += f" --ll-fixed-alm {ll_fixed_alm}"
            if fields.get("ll_headroom"):
                cli += f" --ll-headroom {ll_headroom}"
            if shell_file:
                cli += f" --shell-file {shell_file} --shell-module {shell_module}"
            if file_list:
                cli += f" --file-list {file_list}"
            if files_string:
                cli += f' --files "{files_string}"'
        result["ok"] = True
        result["cli_equivalent"] = cli
        return result

    def run_walker(self, fields: Dict[str, Any]) -> Dict[str, Any]:
        """points.md #602: real, simulated Walker -- MAN -> mirrored VM
        (#601) -> real ping-protocol discovery -> real SHAPE file.
        Honest, explicit scope, matching the page's own wording: this
        is the SIMULATED version (a VM-mirrored grid, not real
        silicon/JTAG) -- the real hardware discovery-mode RTL mechanism
        (#501's own core_select=31 sentinel) remains unbuilt."""
        required = ["man_path", "cells", "dsl", "output"]
        missing = [k for k in required if not fields.get(k)]
        if missing:
            return {"ok": False, "error": f"missing required field(s): {', '.join(missing)}"}
        try:
            cells = int(fields["cells"])
            start_row = int(fields.get("start_row") or 0)
            start_col = int(fields.get("start_col") or 0)
        except ValueError as e:
            return {"ok": False, "error": f"invalid number: {e}"}

        try:
            session = vm_ai_port_v1.VMSession.from_man(fields["man_path"], cells, dsl=fields["dsl"])
        except vm_ai_port_v1.CompileFailure as e:
            return {"ok": False, "error": f"program did not compile:\n{e.format()}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

        try:
            result = walker_sim_v1.walk(session, start=(start_row, start_col))
        except walker_sim_v1.NoTargetError as e:
            return {"ok": False, "error": str(e)}

        shape = walker_sim_v1.to_shape(result, session.mirror_bounds.card_id)
        try:
            with open(fields["output"], "w") as f:
                json.dump(shape, f, indent=2)
        except OSError as e:
            return {"ok": False, "error": str(e)}

        dsl_note = " (paste the same DSL into a --dsl-file first)" if "\n" in fields["dsl"] else ""
        cli = (
            f"python3 tools/walker_sim_cli_v1.py --man {fields['man_path']} --cells {cells} "
            f"--dsl-file <path-to-your-dsl-source>{dsl_note} --start-row {start_row} --start-col {start_col} "
            f"-o {fields['output']}"
        )
        return {
            "ok": True, "card_id": session.mirror_bounds.card_id,
            "cells_discovered": len(result.discovered), "edges_discovered": len(result.edges),
            "ping_count": result.ping_count, "output": fields["output"],
            "cli_equivalent": cli,
        }


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


def help_link(anchor: str) -> str:
    """Real, reused help icon -- opens the manual (regenerated fresh
    from this project's own real docs, #558) at the relevant section,
    per Alan's own 'one button reuse of something built' idea. Never
    new help text written by hand here -- always a link into the
    real, existing documentation."""
    return f'<a href="/manual#{anchor}" target="_blank" title="Help" style="float:right; text-decoration:none; font-size:1.3em;">&#9432;</a>'


def page_welcome() -> str:
    return f"""<!doctype html><html><head><title>Imago UniCell</title>{PAGE_CSS}</head><body>
{NAV}
<h1>Imago UniCell -- getting started{help_link('doc0-imago-unicell')}</h1>
<p>This tool walks through the real, current steps for taking a card
from "nothing generated yet" to a real, buildable Quartus project,
matching the order this project's own build process actually follows:</p>
<ol>
<li><b>Card / MAN file</b> -- describe your card's own real capabilities once.</li>
<li><b>Create cells</b> -- generate a real, importable Quartus project for N cells.</li>
<li><b>Walker</b> -- simulated, live discovery of a VM-mirrored design's own topology (real hardware discovery is a separate, later step).</li>
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
<h1>Step 1: describe your card{help_link('doc1-man-files')}</h1>
<div class="real">Real, working -- generates an actual, schema-compatible MAN
file via <code>tools/man_generate_v1.py</code> (points.md #557).</div>

<h2>What's actually needed, and why</h2>
<p>This table states plainly which fields the real build pipeline
(<code>project_assemble_v1.py</code>'s own <code>load_man()</code>)
actually reads today, versus what's real but only documentation --
so nothing here is asked for without a stated reason.</p>
<table style="width:100%; border-collapse:collapse; font-size:0.9em;">
<tr style="text-align:left; border-bottom:1px solid #ccc;"><th>Field</th><th>Required to build a project</th><th>Why</th></tr>
<tr><td>Card ID</td><td>Yes</td><td>identifies the card in generated projects</td></tr>
<tr><td>Device part</td><td>Yes</td><td>Quartus device setting</td></tr>
<tr><td>Quartus FAMILY string</td><td>No</td><td>the build tool always uses the literal "Arria 10" regardless -- kept here for documentation only</td></tr>
<tr><td>Total ALMs</td><td>Yes</td><td>capacity checks (N cells vs. real budget)</td></tr>
<tr><td>Total DSP blocks</td><td>Yes</td><td>capacity checks, DSP-aware placement</td></tr>
<tr><td>Total M20K bits</td><td>No</td><td>documentation only -- no column-level detail is stored by this generator</td></tr>
<tr><td>CLK_100M pin</td><td>Yes</td><td>SDC/QSF pin assignment</td></tr>
<tr><td>LED0_N / LED1_N pins</td><td>Yes</td><td>heartbeat / array-alive indicators wired into every generated top</td></tr>
<tr><td>JTAG IDCODE</td><td>No</td><td>documentation only, not read by the build pipeline today</td></tr>
<tr><td>Additional pin locations (below)</td><td>No</td><td>not consumed by the build pipeline today -- real documentation for JTAG device pins, configuration pins, or anything else, kept for future tools (e.g. Walker)</td></tr>
</table>

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
<label>JTAG IDCODE (optional, e.g. 0x02E250DD)<input name="jtag_idcode"></label>
<label>Additional pin locations (optional -- one per line, <code>group.name = LOCATION</code>.
Recognized groups: <code>jtag</code> (device pins, e.g. <code>jtag.tck = PIN_AH12</code>),
<code>config</code> (configuration pins, e.g. <code>config.nCONFIG = PIN_AF13</code>),
or anything else (e.g. <code>extra.pcie_refclk_p = PIN_AB28</code>).
This is a real, user-supplied table -- it is NEVER auto-parsed from a .pin file or any other source.
<textarea name="pin_table" rows="6" style="width:100%; padding:6px; box-sizing:border-box; margin-top:2px; font-family:monospace;" placeholder="jtag.tck = PIN_AH12&#10;jtag.tdi = PIN_AH13&#10;config.nCONFIG = PIN_AF13&#10;extra.pcie_refclk_p = PIN_AB28"></textarea></label>
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
            core_line = f'Core type: {result["single_core"]} (resolved to {result["resolved_file"]})<br>' if result.get("single_core") else ""
            probe_line = f'ISSP probe: {result["probe_name"]} -- remember to generate the real issp IP in Quartus before compiling<br>' if result.get("probe_name") else "No ISSP probe (LED-based anti-pruning check works independently)<br>"
            shell_line = ""
            if not result.get("single_core"):
                shell_line = f'Shell: {result.get("shell")}<br>'
                if result.get("logiclock"):
                    shell_line += "LogicLock: ON<br>"
            warnings_html = ""
            if result.get("compat_warnings"):
                items = "".join(f"<li>{w}</li>" for w in result["compat_warnings"])
                warnings_html = (
                    '<div class="placeholder"><b>Compatibility warnings</b> '
                    '(points.md #590 -- a real, advisory, heuristic scan, NOT a substitute '
                    f'for a real compile; double-check, don\'t assume either way):<ul>{items}</ul></div>'
                )
            result_html = (
                f'<div class="result {cls}"><b>Wrote {result["files_written"]} files to:</b> {result["output"]}<br>'
                f'Grid: {result["rows"]}x{result["cols"]}, real ALM budget: {result["alm_total"]:,}<br>'
                f'{core_line}{shell_line}{probe_line}'
                f'<h2>Equivalent CLI</h2><pre>{result["cli_equivalent"]}</pre></div>'
                f'{warnings_html}'
            )
        else:
            result_html = f'<div class="result {cls}"><b>Error:</b> {result.get("error")}</div>'
    core_options = "".join(f'<option value="{c}">{c}</option>' for c in project_assemble_v1.CORE_REGISTRY)
    shell_options = "".join(f'<option value="{s}">{s}</option>' for s in sorted(project_assemble_v1.SHELL_REGISTRY))
    return f"""<!doctype html><html><head><title>Create cells</title>{PAGE_CSS}</head><body>
{NAV}
<h1>Step 2: generate a real Quartus project{help_link('doc3-project-assemble-v1py-real-n-cell-quartus-project-generator')}</h1>
<div class="real">Real, working -- generates a complete, importable Quartus
project for N cells via <code>tools/project_assemble_v1.py</code>
(points.md #552/#554/#555). One real, unconstrained input feeds the
array, every cell's own outputs XOR-reduce into one observable output,
and every cell genuinely loads a real, unpredictable configuration
once at boot -- guarding directly against Quartus proving the array's
own logic constant and collapsing it away (a real failure this project
hit and fixed, #554).</div>

<h2>What's actually needed, and why</h2>
<table style="width:100%; border-collapse:collapse; font-size:0.9em;">
<tr style="text-align:left; border-bottom:1px solid #ccc;"><th>Field</th><th>Required</th><th>Why</th></tr>
<tr><td>MAN file path</td><td>Yes</td><td>real card capabilities (Step 1's own output)</td></tr>
<tr><td>Cell count</td><td>Yes</td><td>how many cells to array into the grid</td></tr>
<tr><td>Output folder</td><td>Yes</td><td>must be outside this repo (#556) -- prevents build artifacts landing in the tracked tree by accident</td></tr>
<tr><td>Top-level module name</td><td>No</td><td>auto-generated from cell count/shell if left blank</td></tr>
<tr><td>Single core type</td><td>No</td><td>array ONE real core type instead of the full 8-core shell (#567) -- shell/LogicLock options below are ignored when this is set</td></tr>
<tr><td>Core source path</td><td>No</td><td>default <code>fpga/verilog</code>; matches by base name, newest real version wins</td></tr>
<tr><td>ISSP probe name</td><td>No</td><td>omitted by default (#569) -- the LED-based anti-pruning check works without it</td></tr>
<tr><td>Shell</td><td>No</td><td>which real 8-core shell to array (default v3); ignored with a single core type</td></tr>
<tr><td>LogicLock</td><td>No</td><td>real per-cell placement region, fixing cross-die scattering (#582); ignored with a single core type</td></tr>
<tr><td>LogicLock fixed ALM / headroom</td><td>No</td><td>only meaningful with LogicLock ON -- switches from AUTO_SIZE to a real, measured fixed size (#583)</td></tr>
<tr><td>Custom shell file / module</td><td>No</td><td>target a shell not in the registry (e.g. a hand-built mixed-version shell, #587/#590) -- module name required if a file is given</td></tr>
<tr><td>Dependency file list / inline files</td><td>No</td><td>override the shell's own registered dependency list explicitly (#590)</td></tr>
</table>

<form method="post" action="/cells">
<label>MAN file path<input name="man_path" required></label>
<label>Cell count<input name="cells" type="number" required></label>
<label>Output folder (outside this repo -- required, #556)<input name="output" required></label>
<label>Top-level module name (optional)<input name="top"></label>
<label>Single core type (optional -- leave blank for the full 8-core shell, #567)
<select name="single_core"><option value="">(full 8-core shell)</option>{core_options}</select></label>
<label>Core source path (optional, default fpga/verilog -- #567, matches by base name, newest version wins)<input name="core_path"></label>
<label>ISSP probe name (optional -- omitted by default, #569; the LED-based check works without it)<input name="probe_name" placeholder="e.g. DEBUG_PROBE"></label>

<h2>Shell / placement options (ignored if a single core type is set above)</h2>
<label>Shell (default v3, #578)<select name="shell">{shell_options}</select></label>
<label><input name="logiclock" type="checkbox" style="width:auto; display:inline; margin-right:6px;">Enable per-cell LogicLock placement regions (#582)</label>
<label>LogicLock fixed ALM/cell (optional -- leave blank for AUTO_SIZE, #583)<input name="ll_fixed_alm" type="number" step="0.01"></label>
<label>LogicLock headroom multiplier (default 1.25 = 25%, #583)<input name="ll_headroom" type="number" step="0.01" value="1.25"></label>

<h2>Custom shell / dependency override (optional, advanced, #590)</h2>
<label>Custom shell file (e.g. fpga/verilog/unicell_super_v7.v)<input name="shell_file"></label>
<label>Custom shell module name (required if a custom shell file is given)<input name="shell_module"></label>
<label>Dependency file list path (one real filename per line)<input name="file_list"></label>
<label>Inline dependency list (comma-separated filenames -- takes precedence over the file list above)<input name="files"></label>

<button type="submit">Generate project</button>
</form>
{result_html}
</body></html>"""


def page_walker(result: Optional[Dict[str, Any]] = None) -> str:
    result_html = ""
    if result is not None:
        cls = "ok" if result.get("ok") else "err"
        if result.get("ok"):
            result_html = (
                f'<div class="result {cls}"><b>Wrote SHAPE file to:</b> {result["output"]}<br>'
                f'Card: {result["card_id"]}<br>'
                f'Cells discovered: {result["cells_discovered"]}, edges discovered: {result["edges_discovered"]}, '
                f'real pings taken: {result["ping_count"]}<br>'
                f'<h2>Equivalent CLI</h2><pre>{result["cli_equivalent"]}</pre></div>'
            )
        else:
            result_html = f'<div class="result {cls}"><b>Error:</b><pre>{result.get("error")}</pre></div>'
    return f"""<!doctype html><html><head><title>Walker</title>{PAGE_CSS}</head><body>
{NAV}
<h1>Step 3: the Walker{help_link('doc3-tools')}</h1>
<div class="real">Real, working -- the SIMULATED Walker (points.md #602):
runs the exact same real ping protocol #501 designed for real hardware
(self answers with its own identity; a cardinal ping relays exactly one
hop to whatever's really, physically connected there; all walk
intelligence stays host-side), but against a VM-mirrored grid instead
of real silicon over JTAG. Starting at a known cell, it walks outward
hop by hop, discovering only what pinging actually reveals -- never a
static, RTL-source guess -- and writes a real SHAPE file.</div>
<div class="placeholder"><b>Explicit, honest scope:</b> this is the
SIMULATED version. The real hardware discovery-mode RTL mechanism
(#501's own <code>core_select=31</code> sentinel, relay logic on the
real <code>cmd_in</code>/<code>cmd_out</code> ports) remains unbuilt --
a real, separate, later step once this VM-side methodology is
confirmed useful.</div>

<h2>What's actually needed, and why</h2>
<table style="width:100%; border-collapse:collapse; font-size:0.9em;">
<tr style="text-align:left; border-bottom:1px solid #ccc;"><th>Field</th><th>Required</th><th>Why</th></tr>
<tr><td>MAN file path</td><td>Yes</td><td>the real card this session mirrors -- see Step 1</td></tr>
<tr><td>Cell count</td><td>Yes</td><td>must match the real N-cell layout your program's own placements were written against</td></tr>
<tr><td>Program (Unicell-S DSL)</td><td>Yes</td><td>the design to load and discover -- compiled fresh each run, same discipline as the manual page</td></tr>
<tr><td>Start row/col</td><td>No (default 0,0)</td><td>the Walker's own known, trusted origin -- must have a real cell placed there or the walk fails immediately (#602's own honest NoTargetError, matching Alan's own "the VM has to be in place first" point)</td></tr>
<tr><td>Output path</td><td>Yes</td><td>where the real SHAPE file is written</td></tr>
</table>

<form method="post" action="/walker">
<label>MAN file path<input name="man_path" required></label>
<label>Cell count<input name="cells" type="number" required></label>
<label>Program (Unicell-S DSL source)<textarea name="dsl" rows="10" required style="width:100%; padding:6px; box-sizing:border-box; margin-top:2px; font-family:monospace;" placeholder="program my_design {{&#10;    place r1 as ram_constant at (0, 0) {{&#10;        out: e&#10;        init_data: 1&#10;    }}&#10;}}"></textarea></label>
<label>Start row (optional, default 0)<input name="start_row" type="number" value="0"></label>
<label>Start col (optional, default 0)<input name="start_col" type="number" value="0"></label>
<label>Output SHAPE path (e.g. docs/shapes/my-design.shape.json)<input name="output" required></label>
<button type="submit">Run simulated Walker</button>
</form>
{result_html}
</body></html>"""


def page_menu() -> str:
    return f"""<!doctype html><html><head><title>Other tools</title>{PAGE_CSS}</head><body>
{NAV}
<h1>Step 4: the rest of the toolchain{help_link('doc0-whats-built-on-top-of-it-and-how-its-verified')}</h1>

<h2>VM / Workbench -- real, working</h2>
<div class="real">A real, already-working browser tool: compile a
program, watch it run, drive individual cells.</div>
<div class="real">points.md #605: the workbench's grid can now be a real,
CHECKED reflection of an actual assembler config -- set a MAN file
path + cell count in the "Real target" panel, and every program/region
loaded from then on is validated against the exact real N-cell layout
<code>tools/project_assemble_v1.py</code> would build for that card,
via the same real mirroring /man, /cells, and /walker already use
(<code>vm_mirror_v1.py</code>, #601). Leave it unset for free mode --
no real card correspondence claimed, same as before this entry.</div>
<div class="real">points.md #606: the "Real target" panel also now takes an
optional shell version (v1-v8, real ones discovered directly on disk) --
Composer's own real concern, per Alan's own words: "a version1 may not
work with a version3." A cell whose core type isn't actually
instantiated in the selected shell's real RTL is rejected outright
(checked directly against the .v files, e.g. v1/v2 genuinely lack
branch/sequencer); every cell's own configured cardinal in/out
directions are shown on the grid, and a real, non-blocking hint appears
whenever a cell broadcasts toward a neighbor that isn't configured to
listen for it.</div>
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
        elif self.path.startswith("/manual"):
            # Regenerated fresh from the current repo state every time
            # -- never a stale, separately hand-maintained copy (#558).
            self._html_response(manual_generate_v1.generate_manual(manual_generate_v1.DEFAULT_SOURCES))
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
        elif self.path == "/walker":
            result = self.controller.run_walker(fields)
            self._html_response(page_walker(result))
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
