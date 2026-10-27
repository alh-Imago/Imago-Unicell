"""hexn_system_page_v1: builds docs/hex-n/frontend/hexn_system_v1.html from hexn_system_v1.src.html by embedding a trace JSON (default docs/hex-n/sessions/system_trace_run3_v1.json, made by tools/hexn_system_trace_v1.py). The page is one self-contained file that shows the trace; the rules stay in the Python model.
Usage: python3 tools/hexn_system_page_v1.py [trace.json]"""
import os, sys, json
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "hex-n")
def build(trace=os.path.join(R, "sessions", "system_trace_run3_v1.json"), out=os.path.join(R, "frontend", "hexn_system_v1.html")):
    src = open(os.path.join(R, "frontend", "hexn_system_v1.src.html")).read(); tr = json.load(open(trace))
    html = src.replace("__TRACE__", json.dumps(tr, separators=(",", ":")).replace("</", "<\\/")); open(out, "w").write(html); return out, len(html)
if __name__ == "__main__":
    o, n = build(*sys.argv[1:2]); print("wrote %s (%d bytes)" % (os.path.normpath(o), n))
