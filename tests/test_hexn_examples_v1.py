import os, sys, subprocess
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_examples_v1 as E
def test_examples_load_and_run():
    for name in ("shadow_animals", "connect4"): assert E.check(os.path.join(E.EX, name)) is True
def test_a_tampered_item_is_refused(tmp_path):
    import shutil
    d = str(tmp_path / "shadow_animals"); shutil.copytree(os.path.join(E.EX, "shadow_animals"), d)
    b = bytearray(open(os.path.join(d, "02_weights.hxi"), "rb").read()); b[60] ^= 1; open(os.path.join(d, "02_weights.hxi"), "wb").write(bytes(b))
    assert E.check(d) is False
