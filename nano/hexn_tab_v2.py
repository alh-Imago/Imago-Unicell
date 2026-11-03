"""hexn_tab_v2.py = hexn_tab_v1.py (untouched) plus: a SEE YOUR PROGRAM page (/hexn/view: the UniCell view first, a switch to the Hex-N view; nano/hexn_view_v1.py) and an Assembler page that tells the truth about what is built (3 Nov 2026, Alan 10:07).
Original v1 docstring follows.

hexn_tab_v1.py - the Hex-N tab of the front panel (2 Nov 2026; Alan 18:22: 'switch to the Hex-N system so the relevant tools lie under that, the serial vm side, the assembler, the programmer etc').

A controller (no HTTP, so it can be tested without a socket, like composer_page_v1) plus the pages.  Each page calls the SAME tool the command line uses:
  /hexn/unit      tools/hexn_unit_file_v1 (check a unit file, the UniCell adapter view) and tools/hexn_pattern_ref_v1.check_reference
  /hexn/vm        tools/hexn_vm_v2.SerialVM (run an icm-hexn file or a unit file's program; a model of the Hex-N grid, not Verilog)
  /hexn/export    tools/hexn_icm_export_v2 on the built-in demo programs (hexn_bases_v2.all_tasks), optionally wrapped as a unit file
  /hexn/program   tools/hexn_unit_file_v1.plan_load: the load PLAN only - nothing is sent to any card
  /hexn/assembler honest status: the Hex-N assembler is scoped (docs/hex-n/HEXN_ASSEMBLER_SCOPING_v1.md), not built
The Python side stays stdlib plus the project's own tools."""
import html
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.join(HERE, "..", "tools")
sys.path.insert(0, TOOLS)
sys.path.insert(0, HERE)

import hexn_unit_file_v1 as U  # noqa: E402
import hexn_pattern_ref_v1 as PR  # noqa: E402
import hexn_icm_export_v2 as X  # noqa: E402
import hexn_vm_v2 as V  # noqa: E402
import hexn_bases_v2 as B  # noqa: E402
import ui_theme_v1 as ui  # noqa: E402
import hexn_view_v1 as VIEW  # noqa: E402

STATUS_WORDS = {U.OK: "ok", U.BAD_MAGIC: "bad format", U.BAD_SUM: "bad checksum (damaged or edited)", U.WRONG_TARGET: "names a different base or pattern", U.MISSING: "part missing"}

SUBTABS = [("overview", "Overview", "/hexn"), ("view", "See your program", "/hexn/view"), ("unit", "Unit file", "/hexn/unit"), ("vm", "Serial VM", "/hexn/vm"), ("export", "Demo programs / export", "/hexn/export"),
           ("program", "Programmer (plan)", "/hexn/program"), ("assembler", "Assembler", "/hexn/assembler")]


def _read_json(path):
    if not path or not os.path.isfile(path):
        raise ValueError("file not found: %s" % path)
    with open(path) as f:
        return json.load(f)


def _id_text(word):
    if word is None:
        return "none"
    t, v = U.unpack_id(word)
    return "%08X (type %04X, version %d)" % (word, t, v)


class HexnController:
    def check_unit(self, f):
        if not f.get("unit_path"):
            return dict(ok=False, error="missing required field(s): unit_path")
        try:
            unit = _read_json(f["unit_path"])
        except Exception as e:
            return dict(ok=False, error=str(e))
        st = U.check(unit, f.get("base") or None, f.get("pattern") or None)
        prog, rep = U.unicell_view(unit, f.get("base") or None, f.get("pattern") or None)
        h = unit.get("header", {}) if isinstance(unit, dict) else {}
        return dict(ok=True, name=h.get("name"), base=h.get("base"), pattern=h.get("pattern"), pattern_id=_id_text(h.get("pattern_id")),
                    status={k: "%d = %s" % (v, STATUS_WORDS.get(v, "?")) for k, v in st.items()},
                    judges=sorted(unit.get("weights", {})) if isinstance(unit.get("weights"), dict) else [],
                    unicell_adapter="program readable, %d judge part(s) skipped" % rep["weights_skipped"] if prog is not None else "program NOT usable (see status)",
                    cli="python3 -c \"import sys; sys.path.insert(0,'tools'); import hexn_unit_file_v1 as U; print(U.check(U.load('%s')))\"" % f["unit_path"])

    def check_reference(self, f):
        if not f.get("ref_path"):
            return dict(ok=False, error="missing required field(s): ref_path")
        try:
            ref = _read_json(f["ref_path"])
        except Exception as e:
            return dict(ok=False, error=str(e))
        problems = PR.check_reference(ref)
        return dict(ok=True, name=ref.get("name"), pattern_id=_id_text(ref.get("pattern_id")), kind=ref.get("kind"), size="%sx%s" % (ref.get("rows"), ref.get("cols")),
                    problems=problems)

    @staticmethod
    def _program_file(path):
        d = _read_json(path)
        if isinstance(d, dict) and d.get("header", {}).get("format") == U.MAGIC:      # a unit file: its program part is the ICM file
            st = U.check(d)
            if st["program"] != U.OK:
                raise ValueError("unit file program part refused: %s" % STATUS_WORDS.get(st["program"]))
            d = d["program"]
        return d

    def run_vm(self, f):
        if not f.get("path"):
            return dict(ok=False, error="missing required field(s): path")
        try:
            vm = V.SerialVM.load(self._program_file(f["path"]))
        except Exception as e:
            return dict(ok=False, error="could not load: %s" % e)
        info = dict(name=vm.name, grid="%dx%d" % (vm.n, vm.n), inputs=vm.inputs, outputs=vm.outputs)
        raw = (f.get("values") or "").strip()
        if not raw:
            return dict(ok=True, loaded=True, ran=False, **info)
        vals = {}
        try:
            for ln in raw.splitlines():
                ln = ln.strip()
                if not ln or ln.startswith("#"):
                    continue
                k, v = ln.split("=", 1)
                vals[k.strip()] = int(v.strip(), 0)
            ticks = int(f["ticks"]) if f.get("ticks") else 900
            cap = vm.run(vals, ticks=ticks)
        except Exception as e:
            return dict(ok=False, error=str(e), **info)
        return dict(ok=True, loaded=True, ran=True, results={o: [(int(t), int(w)) for t, w in cap[o]] for o in vm.outputs}, ticks=ticks, **info)

    def view(self, f):
        """the two views of a program from a unit file or an icm-hexn file (path), or of a built-in demo program (demo)"""
        try:
            if f.get("path"):
                d = _read_json(f["path"]); header = d.get("header") if isinstance(d, dict) and d.get("header", {}).get("format") == U.MAGIC else None
                prog = self._program_file(f["path"])
            elif f.get("demo") in B.all_tasks():
                t = B.all_tasks()[f["demo"]]; b = B.tailored(t); P = B.fits(b, t); prog = X.to_icm(B.program_of(b, P, t), f["demo"]); header = None
            else:
                return dict(ok=False, error="give a unit/ICM file path or pick a demo program")
            return dict(ok=True, body=VIEW.render(prog, header))
        except Exception as e:
            return dict(ok=False, error="could not draw: %s" % e)

    def demo_programs(self):
        return sorted(B.all_tasks())

    def make_demo(self, f):
        names = self.demo_programs()
        if f.get("demo") not in names or not f.get("output"):
            return dict(ok=False, error="pick a demo program and give an output path")
        try:
            t = B.all_tasks()[f["demo"]]
            b = B.tailored(t)
            P = B.fits(b, t)
            icm = X.to_icm(B.program_of(b, P, t), f["demo"])
            out = icm
            if f.get("as_unit"):
                out = U.unit_from_icm(icm, {}, "demo", description="demo program from hexn_bases_v2, no judge weights")
            with open(f["output"], "w") as fh:
                json.dump(out, fh, sort_keys=True, indent=1)
        except Exception as e:
            return dict(ok=False, error=str(e))
        return dict(ok=True, output=f["output"], kind="unit file (empty weights)" if f.get("as_unit") else "icm-hexn-v2 file", report=X.report(icm),
                    inputs=t[1], outputs=t[2])

    def plan(self, f):
        if not f.get("unit_path") or not f.get("card"):
            return dict(ok=False, error="missing required field(s): unit_path, card")
        try:
            unit = _read_json(f["unit_path"])
            lib = {}
            if f.get("library_path"):
                for e in _read_json(f["library_path"]):
                    lib.setdefault(e["card"], {})[(e["base"], e["pattern"])] = dict(pattern_id=e.get("pattern_id"), reference=e.get("reference"), file=e.get("file"), judges=e.get("judges", []))
            cid = int(f["card_pattern_id"], 16) if f.get("card_pattern_id") else None
        except Exception as e:
            return dict(ok=False, error=str(e))
        plan = U.plan_load(unit, f["card"], cid, lib, can_build=False)
        return dict(ok=True, steps=plan["steps"], problems=plan["problems"], needs=plan["needs"])


def _e(x):
    return html.escape(str(x))


def _sub(active):
    return '<p class="subnav">' + " &middot; ".join('<a href="%s"%s>%s</a>' % (p, ' style="font-weight:600"' if k == active else "", l) for k, l, p in SUBTABS) + "</p>"


def _err(r):
    return '<div class="result err"><b>Error:</b> %s</div>' % _e(r.get("error"))


def page_hexn_view(result=None):
    r = ""
    if result is not None:
        r = _err(result) if not result["ok"] else '<div class="result ok">%s</div>' % result["body"]
    demos = "".join('<option value="%s">%s</option>' % (_e(n), _e(n)) for n in sorted(B.all_tasks()))
    return ui.page("See your program", _sub("view") + """<h1>See your program</h1>
<p>Most programs are written for the UniCell side, so that view comes first: inputs, operations and what feeds what. The switch above the picture shows the <b>Hex-N side</b> of the same program:
which tile sits where on the grid, the routing, the RAM holds and the pads. It is one program, drawn two ways. Nothing is sent to a card.</p>
<form class="tool" method="post" action="/hexn/view">
<label>Unit file or icm-hexn file path<input name="path"></label>
<label>&hellip;or a built-in demo program<select name="demo"><option value="">(none)</option>%s</select></label>
<button type="submit" class="primary">Draw it</button></form><style>%s</style>%s""" % (demos, VIEW.CSS, r), active="hexn", narrow=False)


def page_hexn_overview():
    return ui.page("Hex-N", _sub("overview") + """<h1>Hex-N</h1>
<p>The Hex-N system is the base; the UniCell design sits alongside it with a bridge unit between. A full Hex-N program is <b>one loadable file</b>: a header and two
parts, the program (UCC side) and the judge weights. The tools below work on that file. Each page shows what it does and what is <b>not built yet</b>.</p>
<table class="fields"><tr><th>Tool</th><th>State</th><th>What it does</th></tr>
<tr><td><a href="/hexn/view">See your program</a></td><td>built, tested</td><td>draws a program two ways: the UniCell view (what you wrote) and, by a switch, the Hex-N view (tiles, routing, holds, pads)</td></tr>
<tr><td><a href="/hexn/unit">Unit file</a></td><td>built, tested</td><td>checks a unit file part by part (header, program, weights), shows the pattern ID, shows the UniCell adapter view (judge weights ignored); checks a pattern reference file</td></tr>
<tr><td><a href="/hexn/vm">Serial VM</a></td><td>built, tested</td><td>loads an icm-hexn file (or a unit file) from the file alone and runs it on the word-level serial model of the Hex-N grid. A model, not Verilog.</td></tr>
<tr><td><a href="/hexn/export">Demo programs / export</a></td><td>built, tested</td><td>turns a built-in demo program into an icm-hexn-v2 file (routing as native cross / corner / relay tiles) or a unit file</td></tr>
<tr><td><a href="/hexn/program">Programmer (plan)</a></td><td>plan only</td><td>works out the load steps: check the card's pattern ID, pull or build the bitstream, wipe, program, weights. <b>Sends nothing to a card.</b></td></tr>
<tr><td><a href="/hexn/assembler">Assembler</a></td><td>built, simulated end to end</td><td>pattern reference file in, card design out (Verilog, pins, build script); unit file in, config image out. Not yet built into a bitstream or run on a board.</td></tr></table>
""", active="hexn")


def page_hexn_unit(result=None, ref_result=None):
    r = ""
    if result is not None:
        if not result["ok"]:
            r = _err(result)
        else:
            r = '<div class="result ok"><b>%s</b> on base <code>%s</code>, pattern <code>%s</code>, pattern ID %s<br>%s<br>judges: %s<br>UniCell adapter: %s<h2>Equivalent CLI</h2><pre>%s</pre></div>' % (
                _e(result["name"]), _e(result["base"]), _e(result["pattern"]), _e(result["pattern_id"]),
                "<br>".join("%s: %s" % (_e(k), _e(v)) for k, v in result["status"].items()), _e(", ".join(result["judges"]) or "none (empty holding place)"),
                _e(result["unicell_adapter"]), _e(result["cli"]))
    rr = ""
    if ref_result is not None:
        if not ref_result["ok"]:
            rr = _err(ref_result)
        else:
            rr = '<div class="result %s"><b>%s</b> %s, %s, pattern ID %s<br>%s</div>' % ("ok" if not ref_result["problems"] else "err", _e(ref_result["name"]), _e(ref_result["kind"]), _e(ref_result["size"]), _e(ref_result["pattern_id"]),
                                                                                       "no problems found" if not ref_result["problems"] else "<br>".join(_e(p) for p in ref_result["problems"]))
    return ui.page("Hex-N unit file", _sub("unit") + """<h1>Unit file</h1>
<form class="tool" method="post" action="/hexn/unit">
<label>Unit file path<input name="unit_path" required></label>
<label>Must be for this base (optional)<input name="base"></label>
<label>Must be for this pattern (optional)<input name="pattern"></label>
<button type="submit" class="primary">Check unit file</button></form>%s
<h2>Pattern reference file</h2>
<form class="tool" method="post" action="/hexn/unit">
<label>Pattern reference file path<input name="ref_path" required></label>
<button type="submit" class="primary">Check reference file</button></form>%s""" % (r, rr), active="hexn")


def page_hexn_vm(result=None):
    r = ""
    if result is not None:
        if not result["ok"]:
            r = _err(result)
            if result.get("inputs"):
                r += "<p>Inputs this program needs: <code>%s</code></p>" % _e(", ".join(result["inputs"]))
        else:
            r = '<div class="result ok"><b>%s</b>, grid %s<br>inputs: <code>%s</code><br>outputs: <code>%s</code>' % (_e(result["name"]), result["grid"], _e(", ".join(result["inputs"])), _e(", ".join(result["outputs"])))
            if result["ran"]:
                r += "<h2>Result (%d ticks)</h2><pre>%s</pre>" % (result["ticks"], _e("\n".join("%s: %s" % (o, ", ".join("tick %d -> %d" % tw for tw in v) or "no word") for o, v in result["results"].items())))
            else:
                r += "<br>Loaded. Type the input values below and run."
            r += "</div>"
    return ui.page("Hex-N serial VM", _sub("vm") + """<h1>Serial VM</h1>
<div class="real">Real, working: runs on the word-level serial model of the Hex-N grid that was checked tick for tick against the RTL. It needs only the file. It is
<b>not</b> the parallel UniCell VM and does not run Verilog.</div>
<form class="tool" method="post" action="/hexn/vm">
<label>icm-hexn file or unit file path<input name="path" required></label>
<label>Input values (one per line, <code>name = number</code>; leave empty to just load and list the inputs)<textarea name="values" rows="4" placeholder="x = 5&#10;off = 7"></textarea></label>
<label>Ticks (default 900)<input name="ticks" type="number"></label>
<button type="submit" class="primary">Load / run</button></form>%s""" % r, active="hexn")


def page_hexn_export(result=None):
    r = ""
    if result is not None:
        if not result["ok"]:
            r = _err(result)
        else:
            r = '<div class="result ok"><b>Wrote</b> %s (%s)<br>inputs: <code>%s</code>, outputs: <code>%s</code><br>cells: %s<h2>Next</h2>Run it on the <a href="/hexn/vm">Serial VM</a> page.</div>' % (
                _e(result["output"]), _e(result["kind"]), _e(", ".join(result["inputs"])), _e(", ".join(result["outputs"])), _e(json.dumps(result["report"])))
    opts = "".join('<option>%s</option>' % _e(n) for n in HexnController().demo_programs())
    return ui.page("Hex-N demo programs", _sub("export") + """<h1>Demo programs / export</h1>
<p>Built-in demo programs from the planner, written out as real files so every other tool has something to work on. These are <b>demos</b>: the unit file's pattern name is
<code>demo</code> and its weights part is empty.</p>
<form class="tool" method="post" action="/hexn/export">
<label>Demo program<select name="demo">%s</select></label>
<label><input type="checkbox" name="as_unit" value="1"> wrap as a unit file (header + program + empty weights) instead of a bare icm-hexn file</label>
<label>Output path<input name="output" required></label>
<button type="submit" class="primary">Write file</button></form>%s""" % (opts, r), active="hexn")


def page_hexn_program(result=None):
    r = ""
    if result is not None:
        if not result["ok"]:
            r = _err(result)
        else:
            body = ""
            if result["problems"]:
                body += "<b>Nothing would be loaded:</b><ul>%s</ul>" % "".join("<li>%s</li>" % _e(p) for p in result["problems"])
            if result["needs"]:
                body += "<b>Needs to be in place first:</b><ul>%s</ul>" % "".join("<li>%s</li>" % _e(p) for p in result["needs"])
            if result["steps"]:
                body += "<b>Steps:</b><ol>%s</ol>" % "".join("<li>%s</li>" % _e(s) for s in result["steps"])
            r = '<div class="result %s">%s<br><i>This is the plan only. Nothing was sent to a card.</i></div>' % ("err" if result["problems"] else "ok", body)
    return ui.page("Hex-N programmer", _sub("program") + """<h1>Programmer (plan)</h1>
<div class="placeholder"><b>Explicit scope:</b> this works out <i>what the programmer would do</i> from the unit file, the card's pattern ID and a library of known bitstreams. The part
that talks to a card (wipe, program, weights over the bridge) and the assembler that would build a missing bitstream are not wired in here; the plan therefore says
&ldquo;needs to be in place first&rdquo; when the bitstream is neither on the card nor in the library.</div>
<form class="tool" method="post" action="/hexn/program">
<label>Unit file path<input name="unit_path" required></label>
<label>Card id (a bitstream is per card, e.g. tang-nano-20k)<input name="card" required></label>
<label>Pattern ID read from the card (hex, optional, e.g. 31010001)<input name="card_pattern_id"></label>
<label>Library file (optional): a json list of <code>{"card","base","pattern","pattern_id","reference","file","judges"}</code><input name="library_path"></label>
<button type="submit" class="primary">Work out the plan</button></form>%s""" % r, active="hexn")


def page_hexn_assembler():
    return ui.page("Hex-N assembler", _sub("assembler") + """<h1>Assembler</h1>
<div class="placeholder"><b>Built and run in simulation; not yet on a board.</b> <code>tools/hexn_assemble_v1.py</code>; design notes in <code>docs/hex-n/HEXN_ASSEMBLER_SCOPING_v1.md</code>.</div>
<p>The pattern creates the design (a reference file, one bitstream per card) and the program and weights sit on top as data. The assembler reads a pattern reference file and writes the card design:
every Verilog file the design needs, the generated pattern top, the card top with the pattern ID built in, the pin file read from the card's MAN file, a build script, and a record
with the file hashes. A second step turns a unit file into the configuration image, after checking the unit is for this pattern.</p>
<p>What has been shown: the whole path in simulation &mdash; wipe, load the program, put parallel words in, get parallel words and their timings out over the UART &mdash; with results equal to the serial VM.
What has <b>not</b> been done: running the build script (yosys, place and route, bitstream) on the finished card design, the flash write and reconfigure, and a run on the board.</p>
<pre>python3 tools/hexn_assemble_v1.py build docs/hex-n/data/patterns/&lt;pattern&gt;.json --out build_dir
python3 tools/hexn_assemble_v1.py image docs/hex-n/data/patterns/&lt;pattern&gt;.json my_unit.json --out program.bin</pre>""", active="hexn")
