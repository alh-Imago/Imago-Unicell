"""Checks the system trace and the viewer page built from it."""
import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import hexn_system_trace_v1 as T, hexn_system_page_v1 as P
def test_trace_shape():
    t = T.build()
    assert t["summary"]["events"] == len(t["events"]) == 65
    assert t["events"][0]["verdict"] in ("start", "novel", "ok")
    assert all(e["verdict"] in ("ok", "contradiction", "novel", "start") for e in t["events"])
    assert t["summary"]["known_at_end"] == len(t["known"])
def test_page_embeds_trace():
    import tempfile
    out = os.path.join(tempfile.mkdtemp(), "p.html"); o, n = P.build(out=out); h = open(out).read()
    assert "__TRACE__" not in h and '"events"' in h and "<title>Hex-N System View</title>" in h
if __name__ == "__main__": test_trace_shape(); test_page_embeds_trace(); print("ok")
