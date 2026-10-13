"""Ledger #1151: in-flight capture / restore for a design written as ONE LINE OF LATEX (z -> (z^2 + 12345) mod 65521, iterated), through the same scan chain, protocol and host as the CORDIC; tools/board_scan_v2.py,
tools/scan_flow_check_v2.py, tools/scan_swap_v1.py, tools/flex_scan_net_v2.py (v1 plus mul and div cells)."""
import json
import os
import shutil
import subprocess
import sys
import tempfile

import pytest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "nano"))


def tool(*args, timeout=1500):
    if not (shutil.which("iverilog") and shutil.which("vvp")):
        pytest.fail("iverilog missing: this test must not pass by skipping")
    return subprocess.run([sys.executable, *args], capture_output=True, text=True, timeout=timeout, cwd=ROOT)


def test_host_model_equals_the_front_ends_own_reference():
    from latex_frontend_v1 import compile_latex
    import scan_flow_check_v2 as F
    r = compile_latex(r"y = (z^2 + 12345) \bmod 65521")
    for z in (0, 1, 7, 50000, 65520, 65521, 70000, 0xFFFFFFFF, 123456789):
        assert r.reference({"z": z}) == F.step_fn(z), z


def test_scan_chain_covers_mul_and_div_cells():
    import board_scan_v2 as b2
    w = tempfile.mkdtemp()
    try:
        top, files, g, meta = b2.build_files(w, 8, 3000)
        sm = json.load(open(os.path.join(g, "SCAN_MAP.json")))
        kinds = {c["type"] for c in sm["chain"]}
        assert {"mul", "div", "adder", "ram"} <= kinds and meta["scan_bits"] == sm["total_bits"] == 678
        div = next(c for c in sm["chain"] if c["type"] == "div")
        assert [r["name"] for r in div["regs"]] == ["busy", "pending", "pending_r", "remaining", "d_reg", "r_reg", "q_reg", "out_buffer", "rem_buffer"] and div["bits"] == 169    # 3 + 6 + 5*32
        assert b2.layout_id(sm) == b2.layout_id(json.load(open(os.path.join(g, "SCAN_MAP.json"))))
    finally:
        shutil.rmtree(w, ignore_errors=True)


def test_round_trip_mid_multiply_and_mid_division_and_with_wire_damage():
    # lag 3: the multiplier holds a result; lag 12: the divider is part-way through a division; then damage on the wire
    for args in (("--lag", "3", "--k1", "4"), ("--lag", "12", "--k1", "5", "--dly", "1"), ("--scenario", "mixed", "--lag", "12")):
        r = tool(os.path.join("tools", "scan_flow_check_v2.py"), *args)
        assert r.returncode == 0 and "PASS" in r.stdout and "FAIL" not in r.stdout, r.stdout[-900:] + r.stderr[-500:]


def test_persistent_damage_refused_for_the_latex_design():
    r = tool(os.path.join("tools", "scan_flow_check_v2.py"), "--scenario", "persistent_write")
    assert r.returncode == 0 and "ScanError" in r.stdout and "PASS" not in r.stdout, r.stdout[-600:]


def test_swap_image_through_a_file_and_refuse_a_foreign_layout():
    d = tempfile.mkdtemp()
    try:
        f = os.path.join(d, "img.json")
        r = tool(os.path.join("tools", "scan_swap_v1.py"), "from-sim", f, "--cut", "4:12:0")
        assert r.returncode == 0, r.stdout[-500:] + r.stderr[-500:]
        r = tool(os.path.join("tools", "scan_swap_v1.py"), "to-sim", f)
        assert r.returncode == 0 and "PASS" in r.stdout, r.stdout[-500:] + r.stderr[-500:]
        j = json.load(open(f)); j["layout"] = "0" * 16; json.dump(j, open(f, "w"))
        r = tool(os.path.join("tools", "scan_swap_v1.py"), "to-sim", f)
        assert r.returncode != 0 and "REFUSED" in (r.stdout + r.stderr)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_card_host_script_end_to_end_over_a_pseudo_serial_port_latex_design():
    bridge = subprocess.Popen([sys.executable, os.path.join(ROOT, "tools", "scan_pty_bridge_v1.py"), "latex"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    kit = os.path.join(ROOT, "fpga", "board_tests_scan_latex")
    try:
        port = bridge.stdout.readline().strip()
        r = subprocess.run([sys.executable, os.path.join(kit, "scan_card_host.py"), port, "--cuts", "4:12:0", "--damage"], capture_output=True, text=True, timeout=900)
        assert r.returncode == 0 and "ALL PASS" in r.stdout and "damage injected: 3" in r.stdout, r.stdout[-800:] + r.stderr[-500:]
    finally:
        bridge.stdin.close(); bridge.wait(timeout=30)
        shutil.rmtree(os.path.join(kit, "results"), ignore_errors=True)
