"""tests/tools/test_hexn_models_v1.py - the Hex-N page 'The four models' (nano/hexn_models_v1.py, hexn_tab_v3.py, frontend_v4.py), 12 Nov 2026.
Checks: every item belongs to one of the four models, names an existing tool or kit file and a base document that exists; the build sheet gives the commands the records give (base v6 with the chosen arrays and the
test-set run; the bus network shape and version; the stand-alone kit); options are checked (bad numbers, bad paths, unknown shapes are refused); only Python items can be run, a card item cannot; a small match is
really run through the controller and through the served page; the other Hex-N pages still answer and carry the new sub-menu entry."""
import os, sys, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "nano")); sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_models_v1 as M  # noqa: E402
import hexn_tab_v3 as T3  # noqa: E402
import frontend_v4  # noqa: E402

C = M.ModelsController()


def test_catalogue_is_whole_and_points_at_real_files():
    assert [m["n"] for m in M.MODELS] == [1, 2, 3, 4] and all(os.path.isfile(os.path.join(ROOT, m["doc"])) for m in M.MODELS)
    assert {i["model"] for i in M.ITEMS} == {1, 2, 3, 4} and len({i["key"] for i in M.ITEMS}) == len(M.ITEMS)
    for i in M.ITEMS:
        assert i["kind"] in ("card", "run", "sim")
        if i["kind"] == "run": assert os.path.isfile(os.path.join(ROOT, "tools", M.TOOL[i["key"]])), i["key"]
    for f in ("fpga/ypcb/hexn_arr/run_arr.sh", "fpga/ypcb/hexn_bnet/run_bnet.sh", "fpga/ypcb/hexn_speech2/run_speech2.sh", "fpga/ypcb/hexn_speech2/check.py", "tools/hexn_chain_host_v1.py", "tools/hexn_chain_host_v2.py",
              "tools/hexn_chain_host_v3.py", "tools/hexn_kxbase_host_v1.py", "tools/hexn_kxbase_v6.py", "tools/hexn_kxbase_v4.py", "fpga/ypcb/hexn_speech/data_full/events.bin"):
        assert os.path.exists(os.path.join(ROOT, f)), f


def test_build_sheet_commands():
    r = C.sheet({"pick_m2_card": "on", "pick_m3_card": "on", "pick_m2_kit": "on", "pick_m1_base": "on", "arr_hex6": "on", "arr_hex5": "on", "shape": "4:16:48:3", "netv": "v2", "out": "/data/b", "speech_test": "kitram"})
    assert r["ok"] and [i["key"] for i in r["items"]] == ["m1_base", "m2_card", "m2_kit", "m3_card"]
    it = {i["key"]: i for i in r["items"]}
    c = "\n".join(it["m2_card"]["commands"])
    assert "OUT=/data/b HEXN_BASE=hex6,hex5 HEXN_BASE_VER=6 HEXN_NORAM=1 bash ~/hexn-wt/fpga/ypcb/hexn_arr/run_arr.sh" in c and "/data/b/arr_base_b6_noram/hexn_arr.bit" in c
    assert "hexn_chain_host_v2.py kitram" in c and "86079" in it["m2_card"]["expect"] and not it["m2_card"]["runnable"]
    assert "HEXN_BASE_VER=4" in "\n".join(it["m1_base"]["commands"]) and "arr_base_b4_noram" in "\n".join(it["m1_base"]["commands"])
    c3 = "\n".join(it["m3_card"]["commands"])
    assert "HEXN_OUT=/data/b HEXN_NETV=v2 bash ~/hexn-wt/fpga/ypcb/hexn_bnet/run_bnet.sh 4:16:48:3" in c3 and "/data/b/bnet_4x16_n48_q3/hexn_bnet.bit" in c3 and "34,777" in it["m3_card"]["expect"]
    assert "run_speech2.sh" in "\n".join(it["m2_kit"]["commands"]) and "/data/b/speech2/hexn_speech2.bit" in "\n".join(it["m2_kit"]["commands"])
    r = C.sheet({"pick_m3_card": "on", "shape": "4:16:48:3", "netv": "v5"})
    assert "No build of this shape with this version is on record" in r["items"][0]["expect"]                 # an unbuilt choice is said to be unknown, not guessed
    r = C.sheet({"pick_m2_card": "on"}); c = "\n".join(r["items"][0]["commands"])
    assert "HEXN_BASE=hex7_off2_mix,hex6" in c and "hexn_chain_host_v3.py full" in c and "936" in r["items"][0]["expect"]      # the defaults are the build that ran on the card


def test_options_are_checked():
    assert not C.sheet({})["ok"]
    for bad in ({"seeds": "9"}, {"seeds": "x"}, {"games": "1"}, {"out": "/x; rm -rf ~"}, {"data": "a b"}, {"shape": "9:9:9:9"}, {"netv": "v9"}, {"speech_test": "nope"}):
        r = C.sheet(dict(bad, pick_m4_parts="on")); assert not r["ok"] and r["error"], bad
    assert not C.run({"key": "m2_card"})["ok"] and not C.run({"key": "nope"})["ok"] and not C.run({"key": "m2_sim"})["ok"]
    r = C.run({"key": "m2_err", "data": "/nonexistent_dir_for_test"}); assert not r["ok"] and "shd_train.h5" in r["error"]


def test_run_a_match_from_the_controller_and_the_page():
    r = C.run({"key": "m1_c4", "games": "2", "seeds": "1"})
    assert r["ok"] and r["code"] == 0 and "plain3" in r["output"] and "hex3" in r["output"] and r["command"] == "python3 tools/hexn_connect4_blend_v2.py habit2 plain3 hex3 --games 2 --seeds 1"
    srv = frontend_v4.serve(port=0); base = "http://localhost:%d" % srv.server_address[1]
    try:
        page = urllib.request.urlopen(base + "/hexn/models").read().decode()
        assert "The four models" in page and all("Model %d:" % n in page for n in (1, 2, 3, 4)) and all("pick_" + i["key"] in page for i in M.ITEMS)
        post = lambda path, d: urllib.request.urlopen(base + path, urllib.parse.urlencode(d).encode()).read().decode()
        sheet = post("/hexn/models", {"pick_m4_parts": "on", "pick_m2_card": "on", "seeds": "2"})
        assert "Build sheet" in sheet and "python3 tools/hexn_parts_v2.py 2" in sheet and "HEXN_BASE_VER=6" in sheet and "Run it now" in sheet and sheet.count("Run it now") == 1
        out = post("/hexn/models/run", {"key": "m1_dr", "games": "2", "seeds": "1"})
        assert "plain2" in out and "hex2" in out and "exit 0" in out
        assert "nothing was ticked" in post("/hexn/models", {"seeds": "1"})
        ov = urllib.request.urlopen(base + "/hexn").read().decode(); assert "/hexn/models" in ov and "See your program" in ov
        asm = urllib.request.urlopen(base + "/hexn/assembler").read().decode(); assert "The four models" in asm and "Assembler" in asm       # the sub-menu entry is on the other Hex-N pages
        assert "Hex-N" in urllib.request.urlopen(base + "/").read().decode()
    finally:
        srv.shutdown()
