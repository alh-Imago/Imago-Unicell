#!/usr/bin/env python3
"""Host side of the SPEECH CHAIN behind the Kintex base controller (sub/verilog/hexn_base_ctl_v5.v, commands k e u; 11 Nov 2026). Needs a card loaded with a base built with HEXN_BASE_VER=5 (tools/hexn_kxbase_v5.py).
Here the HOST holds the data: the chain's settings (weights, thresholds, count tables, shift codes) and the recordings are sent over JTAG, and every window's result is read back. Nothing is baked into the bitstream.
  nix shell nixpkgs#openocd --command env OPENOCD=openocd HEXN_CHAIN=2 python3 ~/hexn-wt/tools/hexn_chain_host_v1.py kit ~/hexn-wt/fpga/ypcb/hexn_speech/data [--first N] [--stop]
'kit': loads the trained chain from DIR (wrom.hex thr.hex lp.hex cfg.hex), replays the recordings of DIR/prog.hex, decides each recording after window 3 (or at the first window whose stop flag is set, with --stop)
and compares with DIR/lab.hex. The same 300 recordings gave 262 right in the Python reference, in iverilog and on the card with the data baked in (direction doc section 75).
The functions here are also used by the simulation test tests/vm/test_hexn_base_v5_chain_v1.py (same bytes, sent to the iverilog model of the design).
Formats: 'k' sel ah al d0..d9 -> 'K' (sel 0 WROM, 1 THR, 2 LP, 3 CFG; sel 7 = start of a recording); 'e' nh nl bytes -> 'K' (byte 255 = window end, else event = step-in-window * 48 + line); 'u' -> 6 bytes."""
import argparse, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
DECIDE_WIN = 2          # decide after the third window (index 2), as the kit does
NWIN = 5


def kcmd(sel, addr, word): return b"k" + bytes([sel, (addr >> 8) & 255, addr & 255]) + int(word).to_bytes(10, "little")


START = kcmd(7, 0, 0)


def ecmd(events): body = bytes(events) + b"\xff"; return b"e" + len(body).to_bytes(2, "big") + body


def hexwords(path): return [int(x, 16) for x in open(path).read().split()]


def config_cmds(d):
    """-> list of 'k' commands for the four tables of the chain, from the kit's hex files"""
    out = []
    for sel, name in ((0, "wrom.hex"), (1, "thr.hex"), (2, "lp.hex"), (3, "cfg.hex")):
        out += [kcmd(sel, a, w) for a, w in enumerate(hexwords(os.path.join(d, name)))]
    return out


def recordings(prog_path):
    """prog.hex (0x4000 = start, 0x8000 = window end, 0xFFFF = end, else an event address) -> list of recordings, each a list of windows, each a list of event addresses"""
    recs = []
    for w in hexwords(prog_path):
        if w == 0xFFFF: break
        if w & 0x4000: recs.append([[]])
        elif w & 0x8000: recs[-1].append([])
        else: recs[-1][-1].append(w & 255)
    for r in recs:
        assert r[-1] == [] and len(r) == NWIN + 1, "a recording must be %d windows, each closed by a window end" % NWIN
        r.pop()
    return recs


def decode(b):
    """6 reply bytes of 'u' -> dict (None if nothing was waiting)"""
    if b[0] == 0: return None
    v = int.from_bytes(b[1:5], "little"); gap = (v >> 11) & 0x1FFFF
    return dict(win=v & 7, cls=(v >> 3) & 15, pred=(v >> 7) & 15, gap=gap - (1 << 17) if gap >> 16 else gap, stop=(v >> 28) & 1, waiting=b[0], lost=b[5])


def decide(res, use_stop):
    """final digit and windows used, from the 5 window results of one recording"""
    if use_stop:
        for w, r in enumerate(res):
            if r["stop"]: return r["pred"], w + 1
    return res[DECIDE_WIN]["pred"], DECIDE_WIN + 1


# ---------------- card side
def card_load(link, cmds, batch=16):
    import hexn_hexcard_host_v1 as Hh
    for i in range(0, len(cmds), batch):
        part = cmds[i:i + batch]; link.write(b"".join(part)); b = Hh.rd(link, len(part), "chain config")
        if b != b"K" * len(part): raise SystemExit("chain config: expected %d x K, got %r" % (len(part), b))


def card_recording(link, windows):
    import hexn_hexcard_host_v1 as Hh
    link.write(START + b"".join(ecmd(w) for w in windows)); b = Hh.rd(link, 1 + len(windows), "recording")
    if b != b"K" * (1 + len(windows)): raise SystemExit("recording: expected K for the start and every window, got %r" % b)
    b = b""
    for i in range(0, len(windows), 3):                  # 3 results (18 bytes) per write: the bridge's output queue holds 28 bytes, and a reply that has to wait would make the controller miss the next command
        n = min(3, len(windows) - i); link.write(b"u" * n); b += Hh.rd(link, 6 * n, "chain results")
    res = [decode(b[6 * i:6 * i + 6]) for i in range(len(windows))]
    if any(r is None for r in res) or [r["win"] for r in res] != list(range(len(windows))) or any(r["lost"] for r in res):
        raise SystemExit("chain results out of step: %r" % (res,))
    return res


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["kit"]); ap.add_argument("dir"); ap.add_argument("--first", type=int); ap.add_argument("--stop", action="store_true"); a = ap.parse_args()
    os.environ.setdefault("HEXN_CHAIN", "2")
    try: import serial
    except ImportError: import types; sys.modules["serial"] = types.ModuleType("serial")
    import hexn_jtag_host_v1 as J, hexn_kxarr_host_v1 as KA, hexn_kxbase_host_v1 as KB
    cfg = config_cmds(a.dir); recs = recordings(os.path.join(a.dir, "prog.hex")); lab = hexwords(os.path.join(a.dir, "lab.hex"))
    if a.first: recs = recs[:a.first]
    ex = J.OpenOCDExec(KA.find_cfg()); link = J.JtagLink(ex.scan, maxpoll=3000)
    try:
        print("base:", KB.info(link))
        t0 = time.time(); card_load(link, cfg); t1 = time.time()
        print("chain settings sent: %d words, %d bytes, %.1f s" % (len(cfg), 14 * len(cfg), t1 - t0))
        link.write(b"u"); import hexn_hexcard_host_v1 as Hh
        while decode(Hh.rd(link, 6, "u")) is not None: link.write(b"u")          # empty the result queue of anything an earlier run left
        ok = 0; used = 0; nev = 0
        for i, r in enumerate(recs):
            res = card_recording(link, r); pred, w = decide(res, a.stop); ok += (pred == lab[i]); used += w; nev += sum(len(x) for x in r)
            if (i + 1) % 50 == 0: print("   %d recordings, %d right so far" % (i + 1, ok))
        t2 = time.time()
        print("recordings %d, events sent %d, right %d (%.1f%%), windows used on average %.2f, time %.1f s (%.0f recordings per second over JTAG)" % (len(recs), nev, ok, 100.0 * ok / len(recs), used / len(recs), t2 - t1, len(recs) / max(1e-9, t2 - t1)))
        exp = os.path.join(a.dir, "EXPECTED.txt")
        if os.path.exists(exp) and not a.first and not a.stop:
            want = int([l.split()[1] for l in open(exp) if l.startswith("correct")][0]); print("expected %d (Python reference): %s" % (want, "PASS" if want == ok else "FAIL"))
        print("link: %d scans, %d bad captures, %d resends" % (link.scans, link.bad, link.resends))
    finally:
        ex.close()


if __name__ == "__main__":
    main()
