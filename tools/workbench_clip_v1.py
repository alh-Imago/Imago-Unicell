#!/usr/bin/env python3
"""Clean demo clip of the Workbench grid: CORDIC under a (simulated-card) SHAPE target. Shows only the grid panel; no paths, no desktop."""
import glob, json, os, subprocess, sys, shutil, tempfile  # ledger #1302: usage  python3 tools/workbench_clip_v1.py OUTNAME  (writes OUTNAME.webm and OUTNAME.mp4; needs iverilog, playwright+Chromium, ffmpeg)
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
for d in ("nano", "tools", "tests/vm"):
    sys.path.insert(0, os.path.join(ROOT, d))
import kintex_icm_runner_v6 as kr, walker_card_v2 as wk
from test_workbench_card_shape_v1 import snap_from_sim, ICM, KMAN
import workbench_v7 as w7
from playwright.sync_api import sync_playwright

work = tempfile.mkdtemp(prefix="clipwork_")
out = os.path.join(work, "o")
assert subprocess.run([sys.executable, f"{ROOT}/tools/project_assemble_v6.py", "-s", "flex", "--icm", ICM, "--man", KMAN, "--output", out], capture_output=True).returncode == 0
d = json.load(open(f"{out}/design.json")); exp = json.load(open(f"{out}/expected.json"))
entries = [(e["name"], e["width"]) for e in d["entries"]]; exits = [(e["name"], e["width"]) for e in d["exits"]]
e = {n: exp["vectors_wide.txt"]["exits"][n]["words"] for n, _ in exits}
log = snap_from_sim(out, d, [(kr.wide_vectors(entries), e)])[0]
shape = os.path.join(out, "card.shape.json")
assert wk.main([out, log, "--shape", shape]) == 0

os.environ["XDG_CACHE_HOME"] = os.path.join(work, "cache")
srv = w7.serve(port=7510, open_browser=False)
vid = os.path.join(work, "vid"); os.makedirs(vid)
with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1100, "height": 640}, record_video_dir=vid, record_video_size={"width": 1100, "height": 640})
    pg = ctx.new_page()
    pg.goto("http://localhost:7510/"); pg.wait_for_timeout(500)
    # hide everything except the grid panel (no paths, status lines or file names on screen)
    pg.add_style_tag(content="header, nav, footer, .topnav, .row > .col:first-child, h1, .eyebrow, .sub, .foot { display: none !important; } .row { display: block !important; } body { padding: 16px; }")
    pg.evaluate("async (s) => { await post('/set_target_shape', {shape_path: s}); TARGET_KIND = 'card_shape'; }", shape)
    pg.evaluate("async (p) => { await post('/load_icm_vix', {path: p}); const r = await get('/state'); renderState(r.state); }", ICM)
    pg.wait_for_timeout(1500)
    step = "async () => { const r = await post('/step', {n: 1}); renderState(r.state || r); }"
    for i in range(10):
        pg.evaluate(step); pg.wait_for_timeout(900)
    pg.click(".tile.has >> nth=0"); pg.wait_for_timeout(2200)            # ghost trail of one tile
    pg.click(".tile.sel"); pg.wait_for_timeout(300)
    for i in range(8):
        pg.evaluate(step); pg.wait_for_timeout(900)
    pg.evaluate("async () => { const r = await post('/reset', {}); PREV_FIELDS = {}; renderState(r.state); }"); pg.wait_for_timeout(1500)   # reset to tick 0
    for i in range(6):
        pg.evaluate(step); pg.wait_for_timeout(900)
    pg.wait_for_timeout(800)
    ctx.close(); b.close()
srv.shutdown()
v = glob.glob(vid + "/*.webm")[0]
shutil.copy(v, sys.argv[1] + ".webm")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", v, "-c:v", "libx264", "-pix_fmt", "yuv420p", sys.argv[1] + ".mp4"])
print("done")
