"""Ledger #1119: the board package's own parsers must accept the line its own wrappers print (the #1118 package shipped with parsers that rejected the loop tests' extra n0=/st= fields)."""
import json, os, re
ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
PKG = os.path.join(ROOT, "fpga", "board_tests_loops")




def test_every_simulated_line_is_accepted_by_the_packaged_parsers():
    run = open(os.path.join(PKG, "board_run.py")).read()
    col = open(os.path.join(PKG, "board_collect.py")).read()
    assert "n0=[0-9A-F]{4} st=[0-9A-F]" in run and "n0=[0-9A-F]{4} st=[0-9A-F]" in col
    good = re.compile(r"UCT (\S+) res=[PF] n=[0-9A-F]{4} e=[0-9A-F]{4} bad=[0-9A-F]{4} to=[01](?: n0=[0-9A-F]{4} st=[0-9A-F])? last=[0-9A-F]{8} sig=[0-9A-F]{8} w=[0-9A-F,]+$")
    for name in ("flex_ring", "sub_ring", "std_ring", "mixed_pipe"):
        line = json.load(open(os.path.join(PKG, name + ".json")))["sim_line"]
        assert good.search(line) and " res=P " in line + " ", name
