"""Store with reward values: RTL (rtl/hexn_store_v3.v) against the bit-true model (tools/hexn_store_v3.py) in four cases, and the model driven closed-loop on the reward world (tools/hexn_reward_store_v1.py): learns to steer, re-steers after a goal change, inverts when the teacher is wrong most of the time. Needs iverilog."""
import os, sys, shutil, subprocess
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_store_v3 as M, hexn_reward_store_v1 as R
from hexn_reward_v1 import curve
def test_value_update_reaches_the_reward_both_ways():
    for sh in (2, 3, 5, 7):
        st = M.StoreV3(vshift=sh); st.k[0] = [((1, (0,), 1)), 1, 0]; 
        for r, want in ((64, 64), (-32, -32)):
            for _ in range(600): st.q.append(0); st.step(M.REW, r=r)
            assert st.val[0] == want, (sh, r, st.val[0])
def test_rtl_matches_model():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog/vvp missing"
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools/hexn_store_rtl_check_v2.py")], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.count("mismatches 0") == 4, r.stdout
def test_store_model_learns_to_steer_and_resteers():
    hs = [R.run(seed=s, n=500)[0] for s in range(4)]; assert sum(curve(h, 400, 500) for h in hs) / 4 > 0.88
    hs = [R.run(seed=s, n=500, flip=300)[0] for s in range(4)]; assert sum(curve(h, 400, 500) for h in hs) / 4 > 0.85
def test_teacher_wrong_most_of_the_time_inverts():
    hs = [R.run(seed=s, n=500, q=0.6)[0] for s in range(4)]; assert sum(curve(h, 400, 500) for h in hs) / 4 < 0.3
