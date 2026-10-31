#!/usr/bin/env python3
"""hexn_front_unit_v2 (new file 1 Nov 2026): v1 of the front end (tools/hexn_front_unit_v1.py, untouched) PLUS two things the web page needs.
1. send_and_verify() as in v1, but the result also carries "first_wrong": up to 5 rows where judge A's answer differs from the reference, each as {row, got, want, bins} (hex words), so a failure can be looked at instead of only counted.
   Judge A's answers are what is checked, as in v1. Nothing else about the check changes.
2. header_warnings(): names of columns that look like numbers, which means the file's first data row was taken as the header (a file with no header row).
Everything else (derive_task, fit, evenly) is v1's, imported."""
import sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_front_unit_v1 as V1, hexn_scorer_ref_v1 as R, hexn_intake_v1 as I
from hexn_front_unit_v1 import derive_task, fit, evenly
def send_and_verify(unit, pkg, bin_rows, labels, exp, max_rows=1000, bias_b=None):
    pick = evenly(len(bin_rows), max_rows); rows = [bin_rows[i] for i in pick]; lab = [labels[i] for i in pick]; ex = [exp[i] for i in pick]
    unit.preset(4 if bias_b is not None else 3); table = [int(w, 16) for w in pkg["table_words"]]
    if bias_b is not None: unit.load_judges(table, 0, bias_b)
    else: unit.stream(table + [R.w_bias(0)])
    res = unit.stream([R.w_score(b) for b in rows]); k = 2 if bias_b is not None else 1
    A = res[0::k]; Bj = res[1::k] if k == 2 else None; bad = [i for i, (r, e) in enumerate(zip(A, ex)) if r != e]
    def counts(rs):
        c = {"caught": 0, "missed": 0, "false_alarms": 0, "correct_quiet": 0}
        for r, l in zip(rs, lab):
            p = r >> 31
            if l: c["caught" if p else "missed"] += 1
            else: c["false_alarms" if p else "correct_quiet"] += 1
        return c
    out = {"rows_sent": len(rows), "positives": int(sum(lab)), "judge_A_wrong_vs_reference": len(bad), "judge_A": counts(A),
           "first_wrong": [{"row": int(pick[i]), "got": "%08x" % A[i], "want": "%08x" % ex[i], "bins": rows[i]} for i in bad[:5]]}
    sA = np.array([R.unpack(r)[2] - R.unpack(r)[1] for r in A]); out["auc_from_unit_results_A"] = I.auc(sA, np.array(lab))
    if Bj is not None: out["judge_B_bias"] = bias_b; out["judge_B"] = counts(Bj)
    return out
def header_warnings(columns):
    """columns that parse as a number: the file probably has no header row"""
    bad = []
    for c in columns:
        try: float(str(c)); bad.append(str(c))
        except ValueError: pass
    return ["The file seems to have NO HEADER ROW: its first data row was read as the column names (%s). Add a header line to the file, or the sensor names and the task will be meaningless." % ", ".join(bad[:3])] if bad else []
