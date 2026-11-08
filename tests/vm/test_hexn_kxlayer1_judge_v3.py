"""tests/vm/test_hexn_kxlayer1_judge_v3.py - the v3 tool (v2 plus --clean, per-sensor cleaning). Fast checks; the judge itself is unchanged from v1/v2, whose end-to-end tests cover it. Slow end to end (about 5 minutes) with a per-sensor spec."""
import os, shutil, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); sys.path.insert(0, os.path.join(ROOT, "tools"))
import pytest
import hexn_kxlayer1_judge_v2 as L2, hexn_kxlayer1_judge_v3 as L3


def test_v3_data_weights_and_reference_equal_v2():
    a = L2.make_data(1, 3, noise=0.1, dwell=6); b = L3.make_data(1, 3, noise=0.1, dwell=6)
    assert a[1] == b[1] and a[2] == b[2] and a[3] == b[3]
    rows = [[0, 3, -1, 6, 1, 2, 5, 4]]; assert L2.expected_results(a[2], a[3], rows) == L3.expected_results(b[2], b[3], rows)


def test_clean_flag_is_parsed_and_old_carry_flag_kept():
    import inspect
    src = inspect.getsource(L3.main); assert '"--clean"' in src and '"--carry"' in src and "known:" in src and "auto" in src


@pytest.mark.skipif(not shutil.which("iverilog"), reason="needs iverilog")
def test_end_to_end_in_simulation_with_per_sensor_cleaning():
    spec = "carry3,none,carry3,none,carry3,none,carry3,none"
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "hexn_kxlayer1_judge_v3.py"), "sim", "--words", "4", "--dwell", "6", "--noise", "0.30", "--clean", spec], capture_output=True, text=True, timeout=3000)
    assert "0 differ from the model" in r.stdout and "0 differ from the reference" in r.stdout and "cleaning per sensor: s0=carry3 s1=none" in r.stdout and "LAYER 1 -> JUDGE PASS" in r.stdout, r.stdout + r.stderr[-800:]
