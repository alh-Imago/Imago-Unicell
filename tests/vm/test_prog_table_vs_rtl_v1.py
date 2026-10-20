"""tests/vm/test_prog_table_vs_rtl_v1.py -- ledger #1284: the VM's per-core programming tables against the PROG_ID_* the standard RTL declares.
Six cores match id for id; the ONLY known gap is the adder's SECOND_OUTPUT (id 4) and SECOND_DOWNSTREAM_MASK (id 5), which the RTL has and the VM's word-programming table does not
(the VM reads those fields when it loads a design file; programming them by word raises an explicit error). If the gap closes or a new one opens, this test says so."""
import os, subprocess, sys, json

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Ledger #1305: the adder gap this guard was written to watch is closed (ids 4 and 5 are in the VM table now), so the expected gap set is empty. The v2 tool and
# tests/vm/test_prog_words_gap_close_v1.py cover the four other cores and command as well.
def test_tables_match_except_the_known_adder_gap():
    out = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "prog_table_vs_rtl_v1.py"), "--json"], capture_output=True, text=True, check=True).stdout
    res = json.loads(out)
    gaps = {c: (r["rtl_only"], r["vm_only"]) for c, r in res.items() if r["rtl_only"] or r["vm_only"]}
    assert gaps == {}, gaps
    assert set(res) == {"adder", "ram", "comparator", "accumulator", "latch", "sequencer", "branch"}
