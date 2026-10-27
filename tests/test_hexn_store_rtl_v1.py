"""RTL store (rtl/hexn_store_v1.v) against the bit-true model (tools/hexn_store_v2.py): every command's outputs and the final tables must match in four cases. Refuses to pass without iverilog (a SKIP would look like a pass). About 3 s."""
import os, sys, shutil, subprocess
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(ROOT, "tools"))
def test_toolchain_present():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog/vvp missing"
def test_rtl_matches_model_in_all_cases():
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools/hexn_store_rtl_check_v1.py")], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.count("mismatches 0") == 4, r.stdout
def test_model_v2_agrees_with_v1_on_real_run3():
    import hexn_store_v2 as M, hexn_layer2_v2 as V
    V.R = V.runs(); runs = [[k - 12 for k, _ in r] for r in V.R]; st = M.StoreV2(N=3, W=80)
    for r in runs[:2]:
        st.step(M.CLR)
        for x in r: st.step(M.LOAD, x, 0)
    st.step(M.CLR); fl = [i + 1 for i, x in enumerate(runs[2]) if st.step(M.OBS, x, 1000 + i)["verdict"] in (1, 2)]
    assert fl == [22] and st.n_known == 70 and st.n_cand == 6
