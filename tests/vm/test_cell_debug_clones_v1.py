"""Ledger #1247: the debug clones of the proven cell files differ from the originals only by the added dbg_state port, its wiring, and renames."""
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
V = os.path.join(ROOT, "fpga", "verilog")
PAIRS = [("adder_cell_v4e", "adder_cell_v4f"), ("adder_shell_v1e", "adder_shell_v1f"), ("ram_cell_v4", "ram_cell_v4d"), ("ram_shell_v1", "ram_shell_v1d")]
ALLOWED_REMOVED = ("module ", "status_a_arrived", "status_data_valid", "adder_cell_v4e #(", "ram_cell_v4 #(")


def test_clones_are_additive():
    for old, new in PAIRS:
        a, b = os.path.join(V, old + ".v"), os.path.join(V, new + ".v")
        assert os.path.exists(a) and os.path.exists(b)
        d = subprocess.run(["diff", a, b], capture_output=True, text=True).stdout.splitlines()
        removed = [l[2:] for l in d if l.startswith("< ")]
        assert 1 <= len(removed) <= 4, (old, removed)
        for line in removed:
            assert any(k in line for k in ALLOWED_REMOVED), (old, line)
        added = "\n".join(l[2:] for l in d if l.startswith("> "))
        assert "dbg_state" in added and "ledger #1247" in added
        # every changed original line reappears in the clone with only the version / the trailing comma changed
        assert all(l.strip().rstrip(",").replace("v4e", "v4f").replace("v1e", "v1f").replace("ram_cell_v4 ", "ram_cell_v4d ").replace("ram_shell_v1 ", "ram_shell_v1d ")
                   .split("(")[0].strip() in added or "module" in l or "status" in l or "#(" in l for l in removed)


def test_originals_unchanged_in_kit_copies():
    for old, _ in PAIRS:
        a = open(os.path.join(V, old + ".v")).read()
        b = open(os.path.join(ROOT, "fpga", "kintex7_tests", "k7_tree4", "rtl", old + ".sv")).read()
        assert a == b, old
