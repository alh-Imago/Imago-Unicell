#!/usr/bin/env python3
"""hexn_kxlayer1_judge_v2 (8 Nov 2026, a clone of v1 with CARRY-FORWARD added; v1 is kept as it was, card-proven 6 Nov): LAYER 1 DETECTOR (core v2) -> BATCH JUDGE, WITH THE HOST IN THE MIDDLE (5 Nov 2026; Alan 23:01 and 23:04: keep the host in the middle, start with the v2 side).
Two phases, two bitstreams loaded in turn (the detector build fpga/ypcb/hexn on USER1, the base on USER2):
  classes  (detector loaded, HEXN_CHAIN=1)  trains the bank, runs every sensor sample, writes the classes to a JSON file
  judge    (base loaded, HEXN_CHAIN=2)      reads that file, loads the weight table and bias into the judge, packs eight classes per word, scores every word and compares with the Python reference
  sim      both phases in iverilog (detector bench + base), end to end, no card
One time-shared bank serves all eight sensors (same 7 classes on every sensor: a test shape, not the final one). A sensor with no class (the bank's NONE) is sent as bin NONE_BIN (default 11, a bin that 7 classes never use): an ASSUMPTION of this tool, to be settled with Alan.
CARRY-FORWARD (--carry K, off by default; Alan 8 Nov 00:13: apply and test it): at the judge stage, where a sensor has no class, the host repeats that sensor's last class if it was seen at most K words ago (`carry` in tools/hexn_selftrain_v1.py, the function the self-training experiment sections 18 measured at about +0.05). It is applied to the classes after the detector phase, so the detector phase and the saved classes file are unchanged. It assumes a sensor keeps its class for a while (use --dwell 6 or more); with --dwell 1 (a new random class every step) it would only copy stale classes.
Reference: tools/hexn_scorer_ref_v1.py (the word formats), tools/hexn_bank_model_v2.py (the detector's rules)."""
import argparse, json, os, random, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
try: import numpy      # the scorer reference imports numpy for its random-vector maker only; the nix shell on the card machine has none, so a stand-in is enough here
except ImportError:
    import types; sys.modules["numpy"] = types.ModuleType("numpy")
import hexn_bank_model_v2 as M, hexn_scorer_ref_v1 as R
NS = 8; K = 7; NB = 18; AW = 7; NONE_BIN = 11
CORE_SRCS = ["rtl/hexn_core_v2.v", "rtl/hexn_mem_v1.v", "rtl/gen/hexn_lattice_hex7_w18_v16.v", "rtl/hexn_bank_v17.v", "rtl/hexn_det_v3.v", "rtl/hexn_glue_v1.v", "rtl/hexn_cell_v5.v", "rtl/hexn_trainbank_v9.v", "rtl/hexn_cfgbank_v2.v", "rtl/hexn_sdiv_v1.v"]


def mask(bits): return sum(1 << j for j, b in enumerate(bits) if b)


def make_data(seed, nwords, noise=0.10, dwell=1):
    """-> (model, samples[nwords][NS] = (bits, true class), weight table W[2][NS][16], bias).
    dwell 1: a new random class for every sensor at every step (the v2 runs of 5 and 6 Nov, kept identical). dwell > 1: each sensor keeps its class for dwell to 2 x dwell steps, so a hold counter has something to hold."""
    m = M.make(seed, K, NB, AW, 16, 0.15); rnd = random.Random(seed + 77); samples = []; cur = [None] * NS; left = [0] * NS
    for _ in range(nwords):
        row = []
        for s in range(NS):
            if dwell <= 1: y = rnd.randrange(K)
            else:
                if left[s] <= 0: cur[s] = rnd.randrange(K); left[s] = rnd.randint(dwell, 2 * dwell)
                left[s] -= 1; y = cur[s]
            row.append((M.sample(rnd, m["tpl"][y], noise), y))
        samples.append(row)
    wr = random.Random(seed + 5); W = [[[wr.randint(-127, 127) for _ in range(16)] for _ in range(NS)] for _ in range(2)]; bias = wr.randint(-300, 299)
    return m, samples, W, bias


def bins_of(classes): return [c if c >= 0 else NONE_BIN for c in classes]


def expected_results(W, bias, classes_rows):
    return [R.score(W, bias, bins_of(r))[0] for r in classes_rows]


# ---- detector side ----
SRCS_V9 = ["rtl/hexn_core_v9.v", "rtl/hexn_mem_v1.v", "rtl/gen/hexn_lattice_hex7_w18_v18.v", "rtl/hexn_bank_v19.v", "rtl/hexn_det_v3.v", "rtl/hexn_glue_v1.v", "rtl/hexn_cell_v5.v", "rtl/hexn_trainbank_v9.v", "rtl/hexn_cfgbank_v2.v", "rtl/hexn_sdiv_v1.v", "rtl/hexn_loader_v1.v", "rtl/hexn_hold_v1.v", "rtl/hexn_hold_v2.v", "rtl/hexn_store_v5.v"]


def detector_sim_link(core="v2"):
    sys.path.insert(0, HERE); import hexn_jtag_host_v1 as J, hexn_jtag_check_v1 as C
    d = tempfile.mkdtemp(prefix="kxl1_"); tb = open(os.path.join(ROOT, "rtl", "tb_hexn_jtag_v1.v")).read().replace("hexn_core_v1 core", "hexn_core_%s core" % core); tbp = os.path.join(d, "tb_core_v2.v"); open(tbp, "w").write(tb)
    out = os.path.join(d, "s.vvp")
    cmd = ["iverilog", "-g2012", "-o", out, "-DFSP=128", "-DREALCORE", "-DLATMOD=hexn_lattice_hex7_v%d" % (18 if core == "v9" else 16), "-DNBW=%d" % NB, "-DAWB=%d" % AW, "-DNCLS=%d" % K, "-DNCELL=1", "-DACCMODE=0", tbp, os.path.join(ROOT, "rtl/hexn_jtag_bridge_v1.v"), os.path.join(ROOT, "rtl/sim/bscane2_model.v")] + [os.path.join(ROOT, f) for f in (SRCS_V9 if core == "v9" else CORE_SRCS)]
    r = subprocess.run(cmd, capture_output=True, text=True); assert r.returncode == 0, r.stderr[:1500]
    ex = J.SimExec(out); return ex, J.JtagLink(ex.scan)


def detector_card_link():
    os.environ.setdefault("HEXN_CHAIN", "1")      # the detector build's bridge is on USER1; hexn_kxarr_host_v1 would otherwise default the chain to 2 (the base) when it is imported
    import hexn_jtag_host_v1 as J, hexn_kxarr_host_v1 as KA
    ex = J.OpenOCDExec(KA.find_cfg()); return ex, J.JtagLink(ex.scan, maxpoll=3000)


def run_classes(link, m, samples, core="v2", hold=3):
    """train the bank, run every sample; -> classes[nwords][NS], and the number of answers that differ from the model.
    v2: the bank's class per sample (no class = -1). v9: one stream per sensor with the HOLD counter (n samples in a row before the class changes; SETHOLD resets it per sensor); the held class (15 = none, -1 here) and its change flag are checked against the hold reference."""
    import hexn_tang_host_v3 as H, hexn_hold_card_v1 as HC
    b = (HC.HB if core == "v9" else H.Board)(link, K, NB)
    if not b.sync(): raise SystemExit("the detector does not answer (is the detector build loaded, HEXN_CHAIN=1?)")
    b.train(m); bad = 0; nw = len(samples)
    if core == "v9":
        classes = [[-1] * NS for _ in range(nw)]
        for s in range(NS):
            b.sethold(hold); raws = []; got = []
            for t in range(nw):
                bits, y = samples[t][s]; hc, fl, raw = b.runhold(H.mask(bits)); got.append((hc, fl & 1, (fl >> 1) & 1))
                rc = M.classify(m, [(bits, y)])[0][0]; raws.append(15 if rc < 0 else rc)
            ref = HC.hold_ref(raws, hold); bad += sum(1 for g, (rc_, rch) in zip(got, ref) if g != (rc_, 1, rch))
            for t in range(nw): classes[t][s] = got[t][0] if (got[t][1] and got[t][0] < 12) else -1
        return classes, bad
    classes = []
    for row in samples:
        got = []
        for bits, y in row:
            c, _ = b.run(H.mask(bits)); got.append(c)
            bad += (M.classify(m, [(bits, y)])[0][0] != c)
        classes.append(got)
    return classes, bad


# ---- judge side ----
def judge_cmds(W, bias, classes):
    J = lambda w: ("raw", b"J" + w.to_bytes(4, "little"), 1)
    cmds = [("raw", b"M\x02", 1)] + [J(w) for w in R.table_words(W)] + [J(R.w_bias(bias))]
    for row in classes: cmds += [J(R.w_score(bins_of(row))), ("raw", b"R", 6)]
    return cmds


def check_results(replies, W, bias, classes):
    """replies: the 6-byte R answers, one per word -> (words checked, words that differ, none-class count)"""
    exp = expected_results(W, bias, classes); bad = 0
    for e, r in zip(exp, replies):
        got = int.from_bytes(r[1:5], "little"); bad += (r[0] & 15) < 1 or got != e
    return len(exp), bad


def judge_sim(W, bias, classes):
    import hexn_bytecard_sim_v1 as B
    d = tempfile.mkdtemp(prefix="kxl1b_"); env = dict(os.environ, HEXN_DA="4", HEXN_RA="3", HEXN_RMARGIN="2")
    try:
        r = subprocess.run([sys.executable, os.path.join(HERE, "hexn_kxbase_v4.py"), "sim", os.path.join(ROOT, "docs/hex-n/data/hexrefs/hex5.json"), d], env=env, capture_output=True, text=True); assert r.returncode == 0, r.stderr[-1500:]
        res = B.ByteSim(os.path.join(d, "src")).run(judge_cmds(W, bias, classes))
        return check_results([x for x in res if isinstance(x, bytes) and len(x) == 6], W, bias, classes)
    finally: shutil.rmtree(d, ignore_errors=True)


def judge_card(W, bias, classes):
    import hexn_jtag_host_v1 as J, hexn_kxarr_host_v1 as KA, hexn_kxbase_host_v1 as KB
    ex = J.OpenOCDExec(KA.find_cfg()); link = J.JtagLink(ex.scan, maxpoll=3000); rep = []
    try:
        print("base:", KB.info(link)); KB.mode(link, 2)
        for w in R.table_words(W) + [R.w_bias(bias)]: KB.judge_word(link, w)
        for row in classes:
            KB.judge_word(link, R.w_score(bins_of(row))); n, r, lost = KB.judge_result(link); rep.append(bytes([n]) + r.to_bytes(4, "little") + bytes([lost]))
        print("frames: %d scans, %d bad captures (CRC), %d resent" % (link.scans, link.bad, link.resends))
    finally: ex.close()
    return check_results(rep, W, bias, classes)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["classes", "judge", "sim"]); ap.add_argument("--seed", type=int, default=1); ap.add_argument("--words", type=int, default=40); ap.add_argument("--file", default="kxl1_classes.json"); ap.add_argument("--core", choices=["v2", "v9"], default="v2"); ap.add_argument("--hold", type=int, default=3); ap.add_argument("--dwell", type=int, default=None, help="steps each sensor keeps a class (default 1 for v2, 6 for v9)"); ap.add_argument("--carry", type=int, default=0, help="carry-forward: repeat a sensor's last class over up to K words of no class (default off)"); ap.add_argument("--noise", type=float, default=0.10)
    a = ap.parse_args(); dwell = a.dwell if a.dwell is not None else (6 if a.core == "v9" else 1); m, samples, W, bias = make_data(a.seed, a.words, noise=a.noise, dwell=dwell)
    if a.cmd in ("classes", "sim"):
        ex, link = detector_sim_link(a.core) if a.cmd == "sim" else detector_card_link()
        try: classes, bad = run_classes(link, m, samples, a.core, a.hold)
        finally: ex.close()
        truth = [[y for _, y in row] for row in samples]; right = sum(c == t for cr, tr in zip(classes, truth) for c, t in zip(cr, tr)); tot = a.words * NS; none = sum(c < 0 for r in classes for c in r)
        print("detector: %d samples, %d differ from the model, %d match the true class (%.1f%%), %d with no class" % (tot, bad, right, 100.0 * right / tot, none))
        if a.cmd == "classes":
            json.dump(dict(seed=a.seed, words=a.words, core=a.core, hold=a.hold, dwell=dwell, classes=classes), open(a.file, "w")); print("wrote %s" % a.file); sys.exit(0 if bad == 0 else 1)
    else:
        d = json.load(open(a.file)); assert d["seed"] == a.seed and d["words"] == a.words, "the file was made with another --seed / --words"; classes = d["classes"]; bad = 0
    if a.carry > 0:
        from hexn_selftrain_v1 import carry
        cc = carry(classes, a.carry); filled = sum(1 for r0, r1 in zip(classes, cc) for x, y in zip(r0, r1) if x < 0 <= y); left = sum(1 for r in cc for x in r if x < 0)
        print("carry-forward %d: %d no-class slots filled, %d still no class" % (a.carry, filled, left)); classes = cc
    n, jb = judge_sim(W, bias, classes) if a.cmd == "sim" else judge_card(W, bias, classes)
    print("judge: %d words scored, %d differ from the reference" % (n, jb))
    ok = bad == 0 and jb == 0; print("LAYER 1 -> JUDGE %s" % ("PASS" if ok else "FAIL")); sys.exit(0 if ok else 1)


if __name__ == "__main__": main()
