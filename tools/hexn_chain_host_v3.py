#!/usr/bin/env python3
"""Host side of the speech chain behind the base controller, v3 (11 Nov 2026): a WHOLE recording set through the on-chip event RAM in batches (controller v6, the bitstream of HEXN_BASE_VER=6). v1 and v2 untouched, their functions are used.
  nix shell nixpkgs#openocd --command env OPENOCD=openocd HEXN_CHAIN=2 python3 ~/hexn-wt/tools/hexn_chain_host_v3.py full ~/hexn-wt/fpga/ypcb/hexn_speech/data_full [--settings ~/hexn-wt/fpga/ypcb/hexn_speech/data]
'full': sends the trained chain from the settings folder (wrom.hex thr.hex lp.hex cfg.hex), then takes DIR/events.bin (every recording: byte 254, its windows' events, byte 255 per window; written by tools/hexn_chain_fulldata_v1.py)
in batches that fit the event RAM (32,768 bytes) and the result RAM (2,048 results): fill ('w'), replay ('g'), read results ('v'). Decides each recording after window 3, compares with DIR/lab.hex and DIR/EXPECTED.txt
(total and per digit), and prints the clocks counted on the chip."""
import argparse, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import hexn_chain_host_v1 as C, hexn_chain_host_v2 as C2


def split_recordings(img):
    """event-RAM image -> list of per-recording byte strings (each starts with 254 and holds NWIN bytes 255)"""
    out = []; a = 0
    assert img[:1] == b"\xfe", "the image must start with a recording start (254)"
    while a < len(img):
        b = img.find(b"\xfe", a + 1); b = len(img) if b < 0 else b; r = img[a:b]
        assert r.count(b"\xff") == C.NWIN, "recording %d does not have %d window ends" % (len(out), C.NWIN)
        out.append(r); a = b
    return out


def batches(recs, ram=C2.RAM_BYTES, res=C2.RES_WORDS):
    """-> list of lists of recordings; each batch fits the event RAM and the result RAM"""
    out = [[]]; size = 0
    for r in recs:
        assert len(r) <= ram, "one recording is larger than the event RAM"
        if size + len(r) > ram or C.NWIN * (len(out[-1]) + 1) > res: out.append([]); size = 0
        out[-1].append(r); size += len(r)
    return out


def expected(path):
    tot = None; per = {}
    for l in open(path):
        w = l.split()
        if w[0] == "correct": tot = int(w[1])
        if w[0] == "digit": per[int(w[1])] = (int(w[3]), int(w[5]))
    return tot, per


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["full"]); ap.add_argument("dir"); ap.add_argument("--settings"); a = ap.parse_args()
    sett = a.settings or os.path.join(os.path.dirname(os.path.abspath(a.dir.rstrip("/"))), "data")
    os.environ.setdefault("HEXN_CHAIN", "2")
    try: import serial
    except ImportError: import types; sys.modules["serial"] = types.ModuleType("serial")
    import hexn_jtag_host_v1 as J, hexn_kxarr_host_v1 as KA, hexn_kxbase_host_v1 as KB, hexn_hexcard_host_v1 as Hh
    cfg = C.config_cmds(sett); recs = split_recordings(open(os.path.join(a.dir, "events.bin"), "rb").read()); lab = C.hexwords(os.path.join(a.dir, "lab.hex")); bt = batches(recs)
    if len(lab) != len(recs): raise SystemExit("%d labels for %d recordings" % (len(lab), len(recs)))
    want, wper = expected(os.path.join(a.dir, "EXPECTED.txt"))
    ex = J.OpenOCDExec(KA.find_cfg()); link = J.JtagLink(ex.scan, maxpoll=3000)
    try:
        print("base:", KB.info(link)); t0 = time.time(); C.card_load(link, cfg); print("chain settings sent from %s: %d words, %.1f s" % (sett, len(cfg), time.time() - t0))
        print("%d recordings, %d bytes, in %d batches" % (len(recs), sum(len(r) for r in recs), len(bt)))
        ok = 0; clocks = 0; i0 = 0; per = {}; t1 = time.time()
        for bi, b in enumerate(bt):
            img = b"".join(b)
            for c in C2.wcmds(img): link.write(c); Hh.k(link, "event RAM write")
            link.write(C2.gcmd(0, len(img))); g = C2.greply(Hh.rd(link, 7, "replay"))
            if g["status"] != "K" or g["results"] != C.NWIN * len(b): raise SystemExit("batch %d: replay failed: %r" % (bi + 1, g))
            words = []
            for c, n in C2.vcmds(g["results"]): link.write(c); x = Hh.rd(link, 4 * n, "result RAM read"); words += [x[4 * i:4 * i + 4] for i in range(n)]
            res = [C2.word_result(w) for w in words]; bok = 0
            for i in range(len(b)):
                rr = res[C.NWIN * i:C.NWIN * i + C.NWIN]
                if [x["win"] for x in rr] != list(range(C.NWIN)): raise SystemExit("batch %d recording %d: window numbers out of step" % (bi + 1, i))
                hit = C.decide(rr, False)[0] == lab[i0 + i]; bok += hit; p = per.setdefault(lab[i0 + i], [0, 0]); p[0] += hit; p[1] += 1
            ok += bok; clocks += g["clocks"]; i0 += len(b)
            print("   batch %d: %d recordings, %d bytes, %d clocks on the chip, right %d" % (bi + 1, len(b), len(img), g["clocks"], bok))
        sec = clocks / C2.CLOCK_HZ
        print("recordings %d, right %d (%.1f%%); %d clocks counted on the chip = %.2f ms at 50 MHz = %.0f recordings per second, %.1f clocks per recording; host time for all batches %.1f s"
              % (len(recs), ok, 100.0 * ok / len(recs), clocks, 1000 * sec, len(recs) / sec, clocks / len(recs), time.time() - t1))
        print("per digit (right of total; Python reference in brackets): " + "  ".join("%d: %d/%d (%s)" % (c, per[c][0], per[c][1], wper[c][0] if c in wper else "?") for c in sorted(per)))
        same = all(c in wper and tuple(per[c]) == wper[c] for c in per)
        print("expected %d (Python reference): %s; per digit: %s" % (want, "PASS" if want == ok else "FAIL", "all equal" if same else "DIFFERENT"))
        print("link: %d scans, %d bad captures, %d resends" % (link.scans, link.bad, link.resends))
    finally:
        ex.close()


if __name__ == "__main__":
    main()
