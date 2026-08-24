"""
test_cell_pipeline_explainer_v1.py — real, automated verification of
`tools/explainers/cell_pipeline_explainer.html` (points.md #489),
persisting the kind of manual cross-check `#376` did once by hand as a
real, repeatable, automated test: the explainer's own JS bit-packing
logic is run through a real `node` process and compared BYTE-FOR-BYTE
against `nano/icm_v3.py`'s own real Python encoder, for the real,
named nano gate-topology choices this entry added (`#489`).
"""
import os
import re
import shutil
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

import icm_v3 as v3  # noqa: E402
import unicell_gate_core as gate_core  # noqa: E402

EXPLAINER_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "tools", "explainers", "cell_pipeline_explainer.html"
)


def _read_explainer_js() -> str:
    with open(EXPLAINER_PATH) as f:
        html = f.read()
    m = re.search(r"<script>(.*)</script>", html, re.S)
    assert m is not None, "couldn't find the explainer's own <script> block"
    return m.group(1)


def _require_node():
    if shutil.which("node") is None:
        pytest.skip("node not available in this environment")


def test_explainer_html_loads_and_has_named_topology_choices():
    with open(EXPLAINER_PATH) as f:
        html = f.read()
    assert "PASS_A" in html and "XOR" in html and "AND" in html
    assert "custom (0x" in html   # the raw-value escape hatch, #489


def test_explainer_js_syntax_is_valid():
    _require_node()
    js = _read_explainer_js()
    result = subprocess.run(["node", "--check", "-"], input=js, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


def test_explainer_named_nano_topology_choices_match_real_gate_core_constants():
    """The real, load-bearing check: every named choice on the page's
    own nano/topology field must be exactly the real TOPO_* value
    `unicell_gate_core.py` defines -- not a hand-copied number that
    could silently drift from the real source of truth."""
    with open(EXPLAINER_PATH) as f:
        html = f.read()
    m = re.search(r"choices:\[(.*?)\]\s*\},\s*\n\s*\{name:'ready'", html, re.S)
    assert m is not None, "couldn't find the nano topology field's own choices array"
    pairs = re.findall(r"label:'(\w+)',\s*value:(\d+)", m.group(1))
    assert pairs, "no {label, value} choice pairs parsed from the explainer's own HTML"

    real = {name[len("TOPO_"):]: getattr(gate_core, name)
            for name in dir(gate_core) if name.startswith("TOPO_") and name != "TOPO_NOT_B"}
    found = {label: int(value) for label, value in pairs}
    assert found == real


def test_explainer_js_bit_packing_matches_real_python_encoder_for_named_topologies():
    """The real acceptance test for this whole tool, per #376's own
    established standard: does the JS's own bit-packing logic produce
    the EXACT SAME real SUPER_LATCH value the real Python encoder
    does, for real inputs -- not just 'looks right'. Run for every
    named gate topology this entry added, not just one representative
    case, since this is the concrete thing #489 changed."""
    _require_node()
    js = _read_explainer_js()

    real_topologies = {name[len("TOPO_"):]: getattr(gate_core, name)
                        for name in dir(gate_core) if name.startswith("TOPO_") and name != "TOPO_NOT_B"}

    for label, topo_value in real_topologies.items():
        # Real Python side: nano core, topology=topo_value, ready=1,
        # routing_mask=0x2A, cardinal_edge=0x15 -- arbitrary but
        # non-zero/non-symmetric values so a real bit-position bug
        # couldn't hide behind an all-zero or all-one input.
        py_core_config = {"topology": topo_value, "ready": 1, "routing_mask": 0x2A, "cardinal_edge": 0x15}
        py_value = v3.encode_super_latch("nano", py_core_config, {})

        # Real JS side: drive the actual page's own functions.
        script = js + f"""
currentCore = 0;
fieldValues['nano'] = {{
  topology: {topo_value}, ready: 1, routing_mask: 0x2A, cardinal_edge: 0x15
}};
recompute();
console.log(document.getElementById('finalHex').textContent);
"""
        # The explainer's own script touches `document` directly (it's
        # written to run in a real page) -- a tiny, honest DOM stub
        # covering exactly the elements/methods this script actually
        # calls, not a general jsdom dependency, keeps this test
        # self-contained.
        result = subprocess.run(["node", "-e", _DOM_STUB + script],
                                 capture_output=True, text=True, timeout=10)
        assert result.returncode == 0, f"[{label}] node error: {result.stderr}"
        js_hex = result.stdout.strip().splitlines()[-1]
        js_value = int(js_hex, 16)
        assert js_value == py_value, (
            f"[{label}] JS produced 0x{js_value:X}, real Python encoder produced 0x{py_value:X}"
        )


_DOM_STUB = """
class FakeClassList {
  constructor(el) { this.el = el; }
  add() {} remove() {} toggle() { return false; }
}
class FakeElement {
  constructor(tag) {
    this.tag = tag; this.children = []; this._text = ''; this._html = '';
    this.style = {}; this.dataset = {}; this.classList = new FakeClassList(this);
    this._listeners = {};
  }
  appendChild(c) { this.children.push(c); return c; }
  set textContent(v) { this._text = String(v); }
  get textContent() { return this._text; }
  set innerHTML(v) { this._html = String(v); this.children = []; }
  get innerHTML() { return this._html; }
  set onclick(fn) { this._onclick = fn; }
  set onchange(fn) { this._onchange = fn; }
  set oninput(fn) { this._oninput = fn; }
  querySelector() { return new FakeElement('div'); }
  querySelectorAll() { return []; }
}
const _elements = {};
function _byId(id) { if (!_elements[id]) _elements[id] = new FakeElement('div'); return _elements[id]; }
global.document = {
  getElementById: (id) => _byId(id),
  createElement: (tag) => new FakeElement(tag),
  querySelectorAll: () => [],
};
"""
