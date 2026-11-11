"""hexn_chain_fulldata_v1 (11 Nov 2026): the WHOLE test set as an event-RAM image for the card (controller v6, tools/hexn_chain_host_v3.py). Clone-in-spirit of hexn_chain_kitdata_v1.py (untouched): same data build, same training.
First checks that the chain trained here is word for word the kit's (fpga/ypcb/hexn_speech/data: wrom, thr, lp, cfg), so the kit's settings files are used unchanged on the card. Then writes to OUTDIR:
  events.bin   every test recording in order: byte 254, then per window its event addresses and byte 255 (the format of the event RAM)
  lab.hex      the label of each recording;  EXPECTED.txt  what the Python model gets right (decision after window 3) for all of them and per digit
Usage: python3 tools/hexn_chain_fulldata_v1.py DIR OUTDIR    (DIR holds shd_train.h5 and shd_test.h5)"""
import sys, os, tempfile, pathlib, importlib.util
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_chain_hw_v1 as M, hexn_det_shd_v1 as D, hexn_det_net_v1 as N, hexn_chain_host_v1 as C, hexn_chain_host_v2 as C2
sp = importlib.util.spec_from_file_location("tc", os.path.join(ROOT, "tests", "vm", "test_hexn_speech_chain_v1.py")); T = importlib.util.module_from_spec(sp); sp.loader.exec_module(T)
KIT = os.path.join(ROOT, "fpga", "ypcb", "hexn_speech", "data"); DECIDE_WIN = 2


def main(d, out):
    Xtr3, ytr, Xte3, yte, new = D.build(d, N.NIN, N.NBINS, N.TOPN); P = M.train(Xtr3, ytr, 5, N.NIN, gap=10)
    with tempfile.TemporaryDirectory() as t:
        T.write_files(pathlib.Path(t), P, [])
        for f in ("wrom.hex", "thr.hex", "lp.hex", "cfg.hex"):
            if open(os.path.join(t, f)).read().split() != open(os.path.join(KIT, f)).read().split(): raise SystemExit("the chain trained here differs from the kit's %s: stop" % f)
    print("trained chain equals the kit's settings files word for word")
    recs = []; ok = 0; per = {}; over = 0
    for i in range(len(yte)):
        ev = M.events_of(Xte3[i])
        try: res = M.run_recording(P, ev)
        except AssertionError: over += 1; raise SystemExit("recording %d overflows an 8-bit accumulator in the model" % i)
        hit = res[DECIDE_WIN]["pred"] == yte[i]; ok += hit; a = per.setdefault(int(yte[i]), [0, 0]); a[0] += hit; a[1] += 1
        recs.append([[(st % T.STEPS) * T.NL + ln for st, ln in sorted(e for e in ev if e[0] // T.STEPS == w)] for w in range(T.NWIN)])
    img = C2.ram_image(recs); o = pathlib.Path(out); o.mkdir(parents=True, exist_ok=True)
    (o / "events.bin").write_bytes(img); (o / "lab.hex").write_text("\n".join("%x" % v for v in yte) + "\n")
    (o / "EXPECTED.txt").write_text("recordings %d\ndecide_after_window %d\ncorrect %d\n" % (len(recs), DECIDE_WIN + 1, ok) + "".join("digit %d correct %d of %d\n" % (c, per[c][0], per[c][1]) for c in sorted(per)))
    print("wrote", o, "recordings", len(recs), "bytes", len(img), "events", sum(len(w) for r in recs for w in r), "most events in one recording", max(sum(len(w) for w in r) for r in recs),
          "correct after window %d: %d (%.1f%%)" % (DECIDE_WIN + 1, ok, 100.0 * ok / len(recs)))


if __name__ == "__main__": main(*sys.argv[1:3])
