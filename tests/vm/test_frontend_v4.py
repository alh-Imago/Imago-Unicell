"""Ledger #1255: the UniCell Bench front end -- whitelist, argument checks, design listing, build summary, result decoding, and a real pty shell receiving `cd`."""
import os
import shutil
import sys
import tempfile
import time

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "frontend"))
import unicell_frontend_v4 as fe  # noqa: E402

KIT = os.path.join(ROOT, "fpga", "kintex7_tests", "k7_freeze_load")


@pytest.fixture
def demo():
    d = tempfile.mkdtemp()
    shutil.copytree(KIT, os.path.join(d, "k7_freeze_load"), ignore=shutil.ignore_patterns("__pycache__"))
    os.makedirs(os.path.join(d, "not_a_design"))
    yield d
    shutil.rmtree(d)


def test_listing_and_buttons(demo):
    kits = fe.list_kits(demo)
    assert [k["name"] for k in kits] == ["k7_freeze_load"]
    b = kits[0]["buttons"]
    assert {"make", "load", "read", "saveload", "sweep", "release"} <= set(b)
    assert "clock" not in b                       # this kit has no measure_clock.sh


def test_no_button_writes_flash():
    for bid, (_, _, cmd, _) in fe.BUTTONS.items():
        assert "flash" not in cmd.lower(), bid
        assert "program" not in cmd or cmd == fe.LOAD_CMD, bid
    assert fe.LOAD_CMD == 'make program JTAG_LINK="-c ft232"'


def test_select_cd_run_and_refusals(demo):
    st = fe.State(demo)
    try:
        with pytest.raises(ValueError):
            st.select("../etc")
        with pytest.raises(ValueError):
            st.select("not_a_design")
        with pytest.raises(ValueError):
            st.run("make", [])                                   # nothing picked yet
        st.select("k7_freeze_load")
        with pytest.raises(ValueError):
            st.run("saveload", ["346", "1400; rm -rf /"])        # digits only
        with pytest.raises(ValueError):
            st.run("saveload", ["346"])
        with pytest.raises(ValueError):
            st.run("rm", [])
        q = st.terms["card"].subscribe()
        st.terms["card"].write(b"pwd\n")
        got = b""
        t0 = time.time()
        while time.time() - t0 < 5 and demo.encode() + b"/k7_freeze_load" not in got:
            try:
                got += q.get(timeout=0.5)
            except Exception:
                pass
        assert os.path.join(demo, "k7_freeze_load").encode() in got       # the shell really is in the chosen folder
    finally:
        for t in st.terms.values():
            t.close()


def test_build_summary_and_decode(demo):
    folder = os.path.join(demo, "k7_freeze_load")
    open(os.path.join(folder, "build.log"), "w").write("Info: Max frequency for clock 'CLK': 247.65 MHz (PASS at 50.00 MHz)\n")
    s = fe.build_summary(folder)
    assert s["verdict"] == "timing passed" and s["fmax"][0]["mhz"] == 247.65
    open(os.path.join(folder, "build.log"), "w").write("Info: Max frequency for clock 'CLK': 40.00 MHz (FAIL at 50.00 MHz)\n")
    assert "do not load" in fe.build_summary(folder)["verdict"]
    open(os.path.join(folder, "build.log"), "w").write("make: *** [x] Error 1\n")
    assert fe.build_summary(folder)["verdict"] == "NOT BUILT / FAILED"
    words = ["46525A33", "00000162", "01000000", "7FEF5298", "7FFFFEAA", "FFFFFFFF", "0000061A", "00000000"] + ["00000000"] * 78
    open(os.path.join(folder, "x.txt"), "w").write("SNAP live " + " ".join(words) + "\n")
    st = fe.State(demo)
    try:
        st.select("k7_freeze_load")
        v = st.view("x.txt")
        assert "magic 46525A33 OK" in v["decoded"]
        with pytest.raises(ValueError):
            st.view("../x.txt")
        with pytest.raises(ValueError):
            st.view("k7_freeze_v3.v")
    finally:
        for t in st.terms.values():
            t.close()


def test_make_command_keeps_the_real_log(tmp_path):
    import subprocess
    (tmp_path / "Makefile").write_text("all:\n\t@echo Info: Max frequency for clock 'CLK': 99.0 MHz '(PASS at 50.00 MHz)' >/dev/null\n\t@touch built\n")
    # first run: a real build -> build.log replaced; second: make has nothing to do -> build.log kept
    (tmp_path / "Makefile").write_text("built:\n\t@echo \"Info: Max frequency for clock 'CLK': 99.00 MHz (PASS at 50.00 MHz)\"; touch built\nall: built\n")
    subprocess.run(["bash", "-c", fe.MAKE_CMD], cwd=tmp_path, capture_output=True)
    assert "99.00 MHz" in (tmp_path / "build.log").read_text()
    r = subprocess.run(["bash", "-c", fe.MAKE_CMD], cwd=tmp_path, capture_output=True, text=True)
    assert "kept the earlier build.log" in r.stdout and "99.00 MHz" in (tmp_path / "build.log").read_text()
    assert not (tmp_path / ".build.tmp").exists()
    assert fe.build_summary(str(tmp_path))["verdict"] == "timing passed"
    (tmp_path / "build.log").write_text("make: Nothing to be done for 'all'.\n")
    assert "already built" in fe.build_summary(str(tmp_path))["verdict"]


def test_startup_command_default_and_user_override(demo, tmp_path, monkeypatch):
    import json
    monkeypatch.setattr(fe, "SETTINGS", str(tmp_path / "cfg" / "unicell_bench.json"))
    folder = os.path.join(demo, "k7_freeze_load")
    json.dump({"title": "t", "card_id": "cardX", "startup": {"command": "mytools enter", "prompt": "which?"}}, open(os.path.join(folder, "kit.json"), "w"))
    key, cmd, prompt, mine = fe.startup_for(folder)
    assert (key, cmd, prompt, mine) == ("cardX", "mytools enter", "which?", None)
    fe.save_settings({"startup": {"cardX": "my own enter"}})
    assert fe.startup_for(folder)[3] == "my own enter"
    st = fe.State(demo)
    try:
        st.select("k7_freeze_load")
        assert st.run("enter_nix", [])[1] == "my own enter"             # the user's own answer wins over the default
        assert "mytools" not in open(fe.SETTINGS).read()                # the default is never written into the user's file
    finally:
        for t in st.terms.values():
            t.close()
    assert fe.startup_for(os.path.join(demo, "nope"))[1] == fe.NIX_ENTER   # no kit.json: the Nix default


def test_icm_panel_lists_and_creates(tmp_path, monkeypatch):
    monkeypatch.setattr(fe, "SETTINGS", str(tmp_path / "cfg" / "unicell_bench.json"))
    demo = tmp_path / "demo"
    demo.mkdir()
    st = fe.State(str(demo), ROOT)
    try:
        assert st.repo == ROOT
        icms = fe.icm_files(ROOT)
        cards = fe.card_files(ROOT)
        assert any(i["name"] == "reduction_tree4_exit_v1" for i in icms)
        flows = {c["file"]: c["flow"] for c in cards}
        assert flows["kintex7-ypcb00338.man.json"] == "openxc7" and flows["mustang-f100-a10.man.json"] == "export-only" and flows["tang-nano-20k.man.json"] == "gowin-apicula"
        tree = next(i["path"] for i in icms if i["name"] == "reduction_tree4_exit_v1")
        kcard = next(c["path"] for c in cards if c["flow"] == "openxc7")
        with pytest.raises(ValueError):
            st.create_from_icm(tree, kcard, "../evil")
        with pytest.raises(ValueError):
            st.create_from_icm("/etc/passwd", kcard, "x")
        r = st.create_from_icm(tree, kcard, "tree_k7")
        assert r["ok"] and os.path.isfile(os.path.join(demo, "tree_k7", "run_vectors.sh"))
        kits = {k["name"]: k for k in fe.list_kits(str(demo))}
        assert {"run_v1", "run_v2", "run_read", "make", "load"} <= set(kits["tree_k7"]["buttons"])
        with pytest.raises(ValueError):
            st.create_from_icm(tree, kcard, "tree_k7")                   # never overwrites
        st.select("tree_k7")
        open(os.path.join(demo, "tree_k7", "run_vectors.log"), "w").write("SNAP result " + " ".join(["00000000"] * 91) + "\n")
        v = st.view("run_vectors.log")
        assert v["decoded"] and "WRONG" in v["decoded"]                # decoded by the folder's own decoder (a blank read is flagged)
    finally:
        for t in st.terms.values():
            t.close()


def test_out_of_date_repo_is_refused_and_shown(tmp_path, monkeypatch):
    """ledger #1273: an old clone (no Kintex runner) must not make a wrong folder quietly: the panel shows the repo commit and refuses with 'git pull'."""
    monkeypatch.setattr(fe, "SETTINGS", str(tmp_path / "cfg" / "unicell_bench.json"))
    demo = tmp_path / "demo"
    demo.mkdir()
    info = fe.repo_info(ROOT)
    assert info["path"] == ROOT and not info["missing"]                       # this repo has everything
    assert info["commit"] is None or len(info["commit"]) >= 7
    monkeypatch.setattr(fe, "NEEDED_FOR_FLOW", {"openxc7": ["tools/kintex_icm_runner_v4.py", "tools/does_not_exist_v9.py"]})
    assert fe.repo_info(ROOT)["missing"] == {"openxc7": ["tools/does_not_exist_v9.py"]}
    st = fe.State(str(demo), ROOT)
    try:
        icms, cards = fe.icm_files(ROOT), fe.card_files(ROOT)
        tree = next(i["path"] for i in icms if i["name"] == "reduction_tree4_exit_v1")
        kcard = next(c["path"] for c in cards if c["flow"] == "openxc7")
        with pytest.raises(ValueError, match="git pull"):
            st.create_from_icm(tree, kcard, "should_not_exist")
        assert not os.path.exists(os.path.join(demo, "should_not_exist"))
        tcard = next(c["path"] for c in cards if c["flow"] == "export-only")      # a flow with no missing files is unaffected
        r = st.create_from_icm(tree, tcard, "tree_export")
        assert r["ok"]
    finally:
        for t in st.terms.values():
            t.close()
