"""tests/vm/test_hexn_front_web_v1.py -- the front end web page's server (1 Nov 2026): lists the data files, reads them, runs the full fit + stream on the software MODEL of the unit with two judges and gets 0 answers wrong, refuses paths that are not listed, reports a missing task as an error (not a crash)."""
import os, sys, json, threading, urllib.request, urllib.error
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); sys.path.insert(0, os.path.join(ROOT, "tools"))
from http.server import ThreadingHTTPServer
import hexn_front_web_v1 as W
def call(port, path, body=None):
    req = urllib.request.Request("http://127.0.0.1:%d%s" % (port, path), data=None if body is None else json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    try: return 200, json.loads(urllib.request.urlopen(req, timeout=300).read())
    except urllib.error.HTTPError as e: return e.code, json.loads(e.read())
def test_web_server_end_to_end_on_the_model():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), W.Handler); port = srv.server_address[1]; threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        page = urllib.request.urlopen("http://127.0.0.1:%d/" % port).read().decode(); assert "Hex-N Front End" in page
        c, j = call(port, "/api/files"); exr = [f for f in j["files"] if "ea_exe" in f and f.endswith(".csv.gz")]; assert c == 200 and len(exr) == 4
        c, j = call(port, "/api/inspect", {"files": exr}); assert c == 200 and "flow" in j["sensors"] and j["rows"] > 1000
        c, j = call(port, "/api/run", {"files": exr, "task": "future", "sensor": "flow", "q": 0.9, "hours": 6, "unit": "model", "max_rows": 300, "bias_b": -40})
        assert c == 200 and j["unit"]["judge_A_wrong_vs_reference"] == 0 and j["unit"]["rows_sent"] == 300 and "judge_B" in j["unit"] and len(j["package"]["detectors"]) == 8
        c, jm = call(port, "/api/run", {"files": exr, "task": "future", "sensor": "flow", "unit": "model", "max_rows": 50}); assert jm["warnings"] == [] and jm["unit"]["first_wrong"] == []
        oc = [f for f in call(port, "/api/files")[1]["files"] if f.endswith("Optode_Saturation_10-28_10-30_with_position.csv")]
        if oc: c, j2 = call(port, "/api/inspect", {"files": oc}); assert c == 200 and "NO HEADER ROW" in j2["warnings"][0]
        c, j = call(port, "/api/run", {"files": exr, "task": "future", "sensor": "flow", "unit": "none"}); assert c == 200 and "unit" not in j and j["package"]["auc_whole_numbers"] > 0.9
        c, j = call(port, "/api/run", {"files": ["/etc/passwd"], "task": "future", "sensor": "flow", "unit": "none"}); assert c == 400 and "not a listed" in j["error"]
        c, j = call(port, "/api/run", {"files": exr, "task": "rule", "rule": "", "unit": "none"}); assert c == 400 and "choose the task" in j["error"]
        c, j = call(port, "/api/run", {"files": exr, "task": "future", "sensor": "flow", "unit": "real", "port": ""}); assert c == 400 and "port" in j["error"]
    finally: srv.shutdown()
