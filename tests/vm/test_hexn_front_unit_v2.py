"""tests/vm/test_hexn_front_unit_v2.py -- v2 additions (1 Nov 2026): first_wrong lists the rows where the unit and the reference differ (here forced by corrupting 3 reference answers; the model unit itself is right), is empty when all match, and header_warnings spots a file with no header row."""
import os, sys, glob
from types import SimpleNamespace
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_front_unit_v2 as F, hexn_open_host_v1 as H, hexn_open_emu_v1 as E
def test_first_wrong_and_header_warning():
    files = sorted(glob.glob(os.path.join(ROOT, "docs", "hex-n", "data", "ea_exe", "*.csv.gz"))); a = SimpleNamespace(label=None, rule=None, future="flow", q=0.9, hours=6.0, features="auto")
    pkg, rows, lab, exp = F.fit(files, a); u = H.OpenUnit(E.EmuLink())
    r = F.send_and_verify(u, pkg, rows, lab, exp, 200, None); assert r["judge_A_wrong_vs_reference"] == 0 and r["first_wrong"] == []
    pick = F.evenly(len(rows), 200); bad = [int(pick[3]), int(pick[50]), int(pick[120])]; exp2 = list(exp)
    for i in bad: exp2[i] ^= 0x80000001
    u = H.OpenUnit(E.EmuLink()); r = F.send_and_verify(u, pkg, rows, lab, exp2, 200, None)
    assert r["judge_A_wrong_vs_reference"] == 3 and [x["row"] for x in r["first_wrong"]] == bad
    x = r["first_wrong"][0]; assert int(x["got"], 16) ^ int(x["want"], 16) == 0x80000001 and len(x["bins"]) == 8
    assert F.header_warnings(["flow", "level"]) == [] and "NO HEADER ROW" in F.header_warnings(["95.1299972534179", "x"])[0]
