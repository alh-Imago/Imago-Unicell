"""Tests for tools/hexn_intake_v1.py (31 Oct 2026): roles, headerless files, comment lines, merge on time, constant columns."""
import os, sys, tempfile
import numpy as np, pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import hexn_intake_v1 as I
def w(path, text):
    with open(path, "w") as f: f.write(text)
def test_roles_and_merge():
    d = tempfile.mkdtemp(); t = pd.date_range("2024-01-01", periods=300, freq="15min"); rng = np.random.default_rng(1)
    for nm in ("a", "b"):
        pd.DataFrame({"measure": "http://x/" + nm, "dateTime": t.strftime("%Y-%m-%dT%H:%M:%S"), "value": rng.normal(size=300), "quality": "Good"}).to_csv(os.path.join(d, "11111111-site_%s_15min.csv" % nm), index=False)
    df, infos, R = I.load([os.path.join(d, "11111111-site_a_15min.csv"), os.path.join(d, "11111111-site_b_15min.csv")])
    assert len(df) == 300 and set(c for c, r in R.items() if r == "sensor") == {"a", "b"}
def test_comment_header_counter_constant():
    d = tempfile.mkdtemp(); p = os.path.join(d, "log.csv"); rows = "\n".join("%d,%d,%.4f,%d,4095,0" % (i, 1000000 + 5000 * i, 1.7 + 0.005 * i, 100 + (i % 7)) for i in range(200))
    w(p, "# hexn_esp_log_v2 label=test\nseq,esp_us,host_s,a35,a39,d16\n" + rows + "\n")
    df, infos, R = I.load([p]); assert R["esp_us"] == "counter" and R["a35"] == "sensor" and R["a39"] == "constant" and R["d16"] == "constant"
    H = I.highlights(df, R, infos); assert any("never changes" in h[1] for h in H) and any("median step 0.005" in h[1] for h in H)
def test_headerless():
    d = tempfile.mkdtemp(); p = os.path.join(d, "raw.csv"); w(p, "\n".join("%d,%.2f" % (i, i * 0.5) for i in range(50)) + "\n")
    assert list(I.read_any(p).columns) == ["col0", "col1"]
