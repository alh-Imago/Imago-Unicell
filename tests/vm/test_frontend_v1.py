"""Ledger #1255: the UniCell Bench front end -- whitelist, argument checks, design listing, build summary, result decoding, and a real pty shell receiving `cd`."""
import os
import shutil
import sys
import tempfile
import time

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "frontend"))
import unicell_frontend_v1 as fe  # noqa: E402

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
