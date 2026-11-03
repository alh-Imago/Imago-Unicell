"""tests/tools/test_hexn_tab_v2.py - 'See your program' (nano/hexn_view_v1.py, hexn_tab_v2, frontend_v3), 3 Nov 2026: the UniCell view first with a switch to the Hex-N view, from a unit file, a bare icm file and a demo program, and over HTTP.
Checks the content (what the user would see), not the pixels: the UniCell pane names every operation and every input and output; the Hex-N pane has a tile for every work cell, the pads, and a table of places."""
import json, os, sys, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "nano")); sys.path.insert(0, os.path.join(ROOT, "tools")); sys.path.insert(0, os.path.join(ROOT, "tests", "vm"))
import frontend_v3  # noqa: E402
import hexn_tab_v2 as T  # noqa: E402
import hexn_view_v1 as V  # noqa: E402
import hexn_bases_v2 as B  # noqa: E402
import hexn_icm_export_v3 as X  # noqa: E402
import hexn_unit_file_v1 as U  # noqa: E402

C = T.HexnController()


def test_demo_view_has_both_panes_unicell_first():
    r = C.view({"demo": "old/scale_offset"})
    assert r["ok"], r
    body = r["body"]
    assert body.index('id="hv-u" checked') < body.index('id="hv-h"') and "UniCell view" in body and "Hex-N view" in body
    t = B.all_tasks()["old/scale_offset"]
    uni = body[body.index('hv-pane hv-u'):body.index('hv-pane hv-h')]
    for name in list(t[1]) + list(t[2]): assert ("in  " + name in uni) or ("out " + name in uni), name
    for n in t[0]: assert n.kind in uni, n.kind
    hexn = body[body.index('hv-pane hv-h'):]
    assert hexn.count("<svg") >= 2 and "<table" in hexn and "in " + sorted(t[1])[0] in hexn


def test_view_from_unit_file_shows_pattern_header_and_matches_program(tmp_path):
    out = str(tmp_path / "u.json"); assert C.make_demo({"demo": "old/scale_offset", "output": out, "as_unit": "1"})["ok"]
    r = C.view({"path": out}); assert r["ok"], r
    unit = json.load(open(out))
    assert "Pattern" in r["body"] and unit["header"]["base"] in r["body"]
    prog = X.from_icm(unit["program"])
    for key, c in prog["cells"].items(): assert "%s" % c["type"] in r["body"]
    assert r["body"].count('class="route"') == sum(len(v) for v in prog["routing"].values())


def test_view_from_bare_icm_and_errors(tmp_path):
    out = str(tmp_path / "i.json"); assert C.make_demo({"demo": "old/scale_offset", "output": out})["ok"]
    assert C.view({"path": out})["ok"]
    assert not C.view({})["ok"] and not C.view({"path": str(tmp_path / "none.json")})["ok"]


def test_prsq_program_is_drawn_with_new_tiles():
    import test_hexn_pattern_prsq_v1 as P
    prog = P._program(P.TASKS["sequenced_yxz"])
    html = V.render(prog)
    assert "PR" in html and "sequenced" in html and "priority" in html


def test_pages_over_http(tmp_path):
    srv = frontend_v3.serve(port=0)
    try:
        base = "http://localhost:%d" % srv.server_address[1]
        for p in ("/hexn", "/hexn/view", "/hexn/assembler", "/hexn/unit"):
            page = urllib.request.urlopen(base + p).read().decode()
            assert "Hex-N" in page and "See your program" in page
        assert "not yet on a board" in urllib.request.urlopen(base + "/hexn/assembler").read().decode()
        post = lambda path, d: urllib.request.urlopen(urllib.request.Request(base + path, data=urllib.parse.urlencode(d).encode())).read().decode()
        page = post("/hexn/view", {"demo": "old/scale_offset"})
        assert "UniCell view" in page and "<svg" in page
        assert "Error" in post("/hexn/view", {})
    finally:
        srv.shutdown()
