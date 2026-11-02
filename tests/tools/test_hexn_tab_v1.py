"""tests/tools/test_hexn_tab_v1.py - the Hex-N tab of the front panel (nano/hexn_tab_v1.py wired into frontend_v2), 2 Nov 2026."""
import json, os, sys, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "nano"))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import frontend_v2  # noqa: E402
import hexn_tab_v1 as T  # noqa: E402
import hexn_unit_file_v1 as U  # noqa: E402
import hexn_bases_v2 as B  # noqa: E402
import hexn_wrgrid_v11 as G  # noqa: E402

C = T.HexnController()


def _demo(tmp_path, name="old/scale_offset", unit=True):
    out = str(tmp_path / "d.json")
    r = C.make_demo({"demo": name, "output": out, "as_unit": "1" if unit else ""})
    assert r["ok"], r
    return out, r


def test_demo_unit_checks_clean_and_adapter_ignores_weights(tmp_path):
    out, _ = _demo(tmp_path)
    r = C.check_unit({"unit_path": out})
    assert r["ok"] and all(v.startswith("0 = ok") for v in r["status"].values()) and "program readable" in r["unicell_adapter"]
    assert C.check_unit({"unit_path": out, "pattern": "other"})["status"]["program"].startswith("5")


def test_damaged_unit_is_reported_not_hidden(tmp_path):
    out, _ = _demo(tmp_path)
    d = json.load(open(out)); d["program"]["name"] = "tampered"; json.dump(d, open(out, "w"))
    r = C.check_unit({"unit_path": out})
    assert r["status"]["program"].startswith("3") and "NOT usable" in r["unicell_adapter"]
    assert not C.check_unit({"unit_path": str(tmp_path / "none.json")})["ok"]


def test_vm_runs_demo_from_unit_and_from_bare_icm_and_matches_reference(tmp_path):
    for unit in (True, False):
        out, _ = _demo(tmp_path, unit=unit)
        t = B.all_tasks()["old/scale_offset"]
        listed = C.run_vm({"path": out})
        assert listed["ok"] and not listed["ran"] and listed["inputs"] == sorted(t[1])
        iv = {n: 5 + i for i, n in enumerate(t[1])}
        r = C.run_vm({"path": out, "values": "\n".join("%s = %d" % kv for kv in iv.items())})
        ref = G.ref9(t[0], iv)
        for o in t[2]:
            got = [w for _, w in r["results"][o]]
            assert sorted(got) == sorted(ref[o][1])


def test_vm_errors(tmp_path):
    out, _ = _demo(tmp_path)
    assert not C.run_vm({"path": out, "values": "nonsense"})["ok"]
    assert "no value" in C.run_vm({"path": out, "values": "# nothing\nzz = 1"})["error"]
    assert not C.run_vm({"path": str(tmp_path / "none.json")})["ok"]


def test_programmer_plan_refuses_when_nothing_in_place_and_plans_when_on_card(tmp_path):
    out, _ = _demo(tmp_path)
    u = json.load(open(out)); h = u["header"]
    r = C.plan({"unit_path": out, "card": "tang"})
    assert r["ok"] and r["problems"] and not r["steps"]                      # unknown pattern: loads nothing
    lib = tmp_path / "lib.json"
    json.dump([{"card": "tang", "base": h["base"], "pattern": h["pattern"], "pattern_id": None, "reference": "ref.json", "file": None, "judges": []}], open(lib, "w"))
    r = C.plan({"unit_path": out, "card": "tang", "library_path": str(lib)})
    assert r["needs"] and not r["steps"] and "in place" in r["problems"][0]  # reference but no bitstream and no assembler
    json.dump([{"card": "tang", "base": h["base"], "pattern": h["pattern"], "pattern_id": None, "reference": "ref.json", "file": "b.fs", "judges": []}], open(lib, "w"))
    r = C.plan({"unit_path": out, "card": "tang", "library_path": str(lib)})
    assert r["steps"][0].startswith("pull bitstream") and r["steps"][-1] == "ready for data"


def test_pages_post_over_http(tmp_path):
    srv = frontend_v2.serve(port=0)
    try:
        base = "http://localhost:%d" % srv.server_address[1]
        for p in ("/hexn", "/hexn/unit", "/hexn/vm", "/hexn/export", "/hexn/program", "/hexn/assembler"):
            page = urllib.request.urlopen(base + p).read().decode()
            assert "Hex-N" in page and 'href="/hexn"' in page                 # the tab is in the header on every page
        out = str(tmp_path / "h.json")
        post = lambda path, d: urllib.request.urlopen(urllib.request.Request(base + path, data=urllib.parse.urlencode(d).encode())).read().decode()
        assert "Wrote" in post("/hexn/export", {"demo": "old/scale_offset", "as_unit": "1", "output": out})
        assert "ok" in post("/hexn/unit", {"unit_path": out})
        assert "grid" in post("/hexn/vm", {"path": out})
        assert "Nothing was sent to a card" in post("/hexn/program", {"unit_path": out, "card": "tang"})
    finally:
        srv.shutdown()
