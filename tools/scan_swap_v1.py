#!/usr/bin/env python3
"""tools/scan_swap_v1.py -- ledger #1151: swap a saved mid-flight state between the REAL card and the SIMULATED card (the same Verilog in iverilog) for the LaTeX-compiled design.
The image files are those of fpga/board_tests_scan_latex/scan_card_host.py (--capture-only --out / --restore-only --in).
  python3 tools/scan_swap_v1.py from-sim OUT.json [--cut 4:12:0]     run the simulated card to the cut, capture it (twice, checked), write OUT.json  -> restore on the card with --restore-only --in OUT.json
  python3 tools/scan_swap_v1.py to-sim IN.json [--k2 4]              reset the simulated card, restore IN.json (made on the real card) into it through the checked chunks, run on, compare with the model
Both refuse an image whose design name or register-layout fingerprint differs from this design's."""
import argparse, datetime, json, os, shutil, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools")); sys.path.insert(0, os.path.join(ROOT, "nano"))
import board_scan_v1 as v1, board_scan_v2 as b2, scan_host_v2 as h  # noqa: E402
from scan_flow_check_v2 import step_fn, model, Z0  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("mode", choices=["from-sim", "to-sim"]); ap.add_argument("file"); ap.add_argument("--cut", default="4:12:0"); ap.add_argument("--k2", type=int, default=4)
    a = ap.parse_args()
    work = tempfile.mkdtemp(prefix="scan_swap_")
    try:
        top, files, g, meta = b2.build_files(work, 8, 3000)
        layout = b2.layout_id(json.load(open(os.path.join(g, "SCAN_MAP.json"))))
        c = v1.SimCard(cpb=8, tmo=3000, built=(top, files, g)); card = h.Card(c, design=meta["name"], log=print)
        card.reset(); c.idle(1500)
        if a.mode == "from-sim":
            k1, lag, dly = [int(x) for x in a.cut.split(":")]
            card.configure(2, k1, dly, lag); card.load(Z0); card.wait_stopped()
            ses, img = card.capture_verified()
            json.dump(dict(ses=ses, image=img.hex(), cut=[k1, lag, dly], design=meta["name"], layout=layout, when=datetime.datetime.now().isoformat(), made_by="simulated card"), open(a.file, "w"), indent=1)
            print("captured from the simulated card:", h.parse_trailer(img), "-> written", a.file)
        else:
            d = json.load(open(a.file)); img = bytes.fromhex(d["image"]); tr = h.parse_trailer(img)
            if d.get("design") != meta["name"] or d.get("layout") != layout:
                sys.exit("REFUSED: image is from design %r layout %r; this design is %r layout %r" % (d.get("design"), d.get("layout"), meta["name"], layout))
            card.configure(2, a.k2, 3, 0); card.restore(d["ses"], img); card.go()
            q = card.wait_stopped(steps=tr["steps"] + a.k2)
            want = model(tr["steps"] + a.k2 + 1)[q["steps"] - 1]
            print("restored into the simulated card; ran to step %d: word %d, model %d -> %s %s" % (q["steps"], q["word"], want, "PASS" if q["word"] == want and q["held_valid"] else "FAIL", card.stats))
            sys.exit(0 if q["word"] == want else 1)
        c.close()
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
