"""tests/vm/test_hexn_front_unit_v1.py -- the front end's data-file-to-unit step (hexn_front_unit_v1), 1 Nov 2026, on the REAL River Exe files against the Python model of the unit. The detectors are chosen on the training part only,
at most 8 are kept, the whole-number table costs little against floats, the unit model's results equal the bit-exact reference on every streamed row, two judges give two answers per row, and the package survives a JSON round trip. Model only: no hardware."""
import argparse, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_front_unit_v1 as F, hexn_open_host_v1 as H, hexn_open_emu_v1 as E  # noqa: E402
D = os.path.join(ROOT, "docs", "hex-n", "data", "ea_exe")
FILES = [os.path.join(D, f) for f in ("thorverton_exe_level_15min_2022_2023.csv.gz", "thorverton_exe_flow_15min_2022_2023.csv.gz", "thorverton_exe_rain_killerton_15min_2022_2023.csv.gz", "thorverton_exe_rain_tiverton_15min_2022_2023.csv.gz")]
def args(): return argparse.Namespace(label=None, rule=None, future="flow", q=0.9, hours=6.0, features="auto")
def test_river_exe_file_to_unit():
    pkg, rows, lab, exp = F.fit(FILES, args())
    assert 1 <= len(pkg["detectors"]) <= 8 and pkg["detectors_available"] == 16 and len(pkg["table_words"]) == 192
    assert pkg["auc_whole_numbers"] > 0.93 and abs(pkg["auc_float_selected"] - pkg["auc_whole_numbers"]) < 0.01          # whole numbers cost almost nothing
    json.loads(json.dumps(pkg))
    u = H.OpenUnit(E.EmuLink()); u.id()
    r = F.send_and_verify(u, pkg, rows, lab, exp, max_rows=400)
    assert r["judge_A_wrong_vs_reference"] == 0 and r["rows_sent"] == 400
    r2 = F.send_and_verify(u, pkg, rows, lab, exp, max_rows=400, bias_b=-40)
    assert r2["judge_A_wrong_vs_reference"] == 0 and r2["judge_B"]["false_alarms"] < r2["judge_A"]["false_alarms"]         # a lower bias on B means fewer alarms
    assert sum(r2["judge_B"].values()) == 400
