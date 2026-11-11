#!/usr/bin/env python3
"""Host side of the speech chain behind the base controller, v2 (11 Nov 2026): adds the ON-CHIP EVENT RAM of sub/verilog/hexn_base_ctl_v6.v (commands w g v). Needs a card built with HEXN_BASE_VER=6.
hexn_chain_host_v1.py is untouched and its functions are used here (settings, recordings, result decoding).
  nix shell nixpkgs#openocd --command env OPENOCD=openocd HEXN_CHAIN=2 python3 ~/hexn-wt/tools/hexn_chain_host_v2.py kitram ~/hexn-wt/fpga/ypcb/hexn_speech/data [--repeat N]
'kitram': sends the trained chain ('k'), stores the recordings of DIR/prog.hex in the event RAM once ('w'), lets the controller replay them into the chain at the chain's own speed ('g'), reads every window result back ('v'),
decides each recording after window 3 and compares with DIR/lab.hex (262 of 300 expected). Prints the clocks the replay took, as counted on the chip, and what that is in recordings per second at the 50 MHz board clock.
Event RAM bytes: 0..253 an event, 254 start of a recording, 255 window end."""
import argparse, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import hexn_chain_host_v1 as C
CLOCK_HZ = 50_000_000; RAM_BYTES = 32768; RES_WORDS = 2048


def ram_image(recs):
    """recordings (lists of windows of event addresses) -> the bytes of the event RAM"""
    out = bytearray()
    for r in recs:
        out.append(254)
        for w in r: out += bytes(w) + b"\xff"
    return bytes(out)


def wcmds(image, addr=0, chunk=1024): return [b"w" + (addr + i).to_bytes(2, "big") + len(image[i:i + chunk]).to_bytes(2, "big") + image[i:i + chunk] for i in range(0, len(image), chunk)]


def gcmd(addr, n): return b"g" + addr.to_bytes(2, "big") + n.to_bytes(2, "big")


def vcmds(nwords): return [(b"v" + a.to_bytes(2, "big") + bytes([min(255, nwords - a)]), min(255, nwords - a)) for a in range(0, nwords, 255)]


def greply(b): return dict(status=chr(b[0]), clocks=int.from_bytes(b[1:5], "little"), results=int.from_bytes(b[5:7], "little"))


def word_result(b4):
    """4 bytes of a result RAM word -> the same dict as hexn_chain_host_v1.decode gives for a 'u' reply"""
    return C.decode(bytes([1]) + bytes(b4) + bytes([0]))


def score(words, lab, use_stop=False):
    """words: list of 4-byte results, 5 per recording -> (right, list of per-recording window results)"""
    res = [word_result(w) for w in words]; ok = 0
    for i in range(len(res) // C.NWIN):
        rr = res[C.NWIN * i:C.NWIN * i + C.NWIN]
        if [x["win"] for x in rr] != list(range(C.NWIN)): raise SystemExit("recording %d: window numbers out of step: %r" % (i, [x["win"] for x in rr]))
        ok += (C.decide(rr, use_stop)[0] == lab[i])
    return ok


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["kitram"]); ap.add_argument("dir"); ap.add_argument("--repeat", type=int, default=1); a = ap.parse_args()
    os.environ.setdefault("HEXN_CHAIN", "2")
    try: import serial
    except ImportError: import types; sys.modules["serial"] = types.ModuleType("serial")
    import hexn_jtag_host_v1 as J, hexn_kxarr_host_v1 as KA, hexn_kxbase_host_v1 as KB, hexn_hexcard_host_v1 as Hh
    cfg = C.config_cmds(a.dir); recs = C.recordings(os.path.join(a.dir, "prog.hex")); lab = C.hexwords(os.path.join(a.dir, "lab.hex")); img = ram_image(recs)
    if len(img) > RAM_BYTES or C.NWIN * len(recs) > RES_WORDS: raise SystemExit("too much for the chip's memories: %d event bytes (room %d), %d results (room %d)" % (len(img), RAM_BYTES, C.NWIN * len(recs), RES_WORDS))
    ex = J.OpenOCDExec(KA.find_cfg()); link = J.JtagLink(ex.scan, maxpoll=3000)
    try:
        print("base:", KB.info(link))
        t0 = time.time(); C.card_load(link, cfg); t1 = time.time(); print("chain settings sent: %d words, %.1f s" % (len(cfg), t1 - t0))
        for c in wcmds(img): link.write(c); Hh.k(link, "event RAM write")
        t2 = time.time(); print("event RAM filled: %d bytes (%d recordings, %d events), %.1f s" % (len(img), len(recs), sum(len(w) for r in recs for w in r), t2 - t1))
        for rep in range(a.repeat):
            ta = time.time(); link.write(gcmd(0, len(img))); g = greply(Hh.rd(link, 7, "replay")); tb = time.time()
            if g["status"] != "K" or g["results"] != C.NWIN * len(recs): raise SystemExit("replay failed: %r" % g)
            words = []
            for c, n in vcmds(g["results"]): link.write(c); b = Hh.rd(link, 4 * n, "result RAM read"); words += [b[4 * i:4 * i + 4] for i in range(n)]
            tc = time.time(); ok = score(words, lab); sec = g["clocks"] / CLOCK_HZ
            print("replay %d: %d clocks counted on the chip = %.3f ms at 50 MHz = %.0f recordings per second, %.1f clocks per recording; right %d of %d (%.1f%%); host time: replay command %.2f s, reading results %.2f s"
                  % (rep + 1, g["clocks"], 1000 * sec, len(recs) / sec, g["clocks"] / len(recs), ok, len(recs), 100.0 * ok / len(recs), tb - ta, tc - tb))
        exp = os.path.join(a.dir, "EXPECTED.txt")
        if os.path.exists(exp):
            want = int([l.split()[1] for l in open(exp) if l.startswith("correct")][0]); print("expected %d (Python reference): %s" % (want, "PASS" if want == ok else "FAIL"))
        print("link: %d scans, %d bad captures, %d resends" % (link.scans, link.bad, link.resends))
    finally:
        ex.close()


if __name__ == "__main__":
    main()
