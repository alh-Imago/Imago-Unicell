"""Ledger #1250: the load-capable debug clones (v4g/v1g) differ from the debug clones (v4f/v1f, v4d/v1d) only by additions (the load port and branch) and renames; kit copies equal the files."""
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
V = os.path.join(ROOT, "fpga", "verilog")
PAIRS = [("adder_cell_v4f", "adder_cell_v4g"), ("adder_shell_v1f", "adder_shell_v1g"), ("ram_cell_v4d", "ram_cell_v4g"), ("ram_shell_v1d", "ram_shell_v1g")]


def test_load_clones_additive():
    for old, new in PAIRS:
        d = subprocess.run(["diff", os.path.join(V, old + ".v"), os.path.join(V, new + ".v")], capture_output=True, text=True).stdout.splitlines()
        removed = [l[2:] for l in d if l.startswith("< ")]
        assert len(removed) <= 5, (old, removed)
        for line in removed:
            s = line.strip()
            assert s.startswith(("module ", "//")) or "dbg_state" in s or "#(" in s or s.endswith(",") or "adder_cell_v4f" in s or "ram_cell_v4d" in s, (old, line)
        added = "\n".join(l[2:] for l in d if l.startswith("> "))
        assert "dbg_load_en" in added and "1250" in added


def test_kit_copies_equal():
    kit = os.path.join(ROOT, "fpga", "kintex7_tests", "k7_freeze_load", "rtl")
    for _, new in PAIRS:
        assert open(os.path.join(V, new + ".v")).read() == open(os.path.join(kit, new + ".sv")).read(), new
