"""tests/vm/test_replay_card_icm_vm_v3_v1.py -- the replay tool on FlexGrid v2 (ledger #1272): all 11 card-tested designs equal the card's count and first words, and the printed result is
identical, line for line, to tools/replay_card_icm_vm_v2.py (the version on FlexGrid v1)."""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _run(name):
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", name)], capture_output=True, text=True, cwd=ROOT)
    return r.returncode, r.stdout


def test_v3_equals_the_card_and_equals_v2():
    c3, o3 = _run("replay_card_icm_vm_v3.py")
    c2, o2 = _run("replay_card_icm_vm_v2.py")
    assert c3 == 0 and "11 of 11 replay equal" in o3, o3[-800:]
    assert c2 == 0
    assert o3 == o2
