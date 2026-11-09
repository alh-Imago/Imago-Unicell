"""hexn_shd_frontend_v1 (9 Nov 2026): the front end that folds the Heidelberg spoken digits (SHD, 700 channels, thousands of spikes) down to what the bus network can take (NIN lines, about one event per clock). Alan 22:07 and 22:11 (real data test). Direction doc section 55. Simulation / host side only.
Fold: channel c goes to line c * NIN // 700 (neighbouring channels share a line, so a line is a band of frequency); time 0..1 s is cut into NBINS bins, one bin = CPB clocks (the toy used a window of 40 clocks). In every bin the lines are ranked by their spike count (optionally divided by the line's average count over the training set, so that a loud channel does not always win) and only the TOPN best, with at least MINCOUNT spikes, send ONE event each. TOPN is the 'cleaner': the network carries about one packet per bus per clock, so a recording of 8,000 spikes cannot go in whole.
Baseline (no network): a template per class (mean of the folded event matrix over the training set), a test recording is given to the class whose template it overlaps most (normalised dot product). It says how much a front end keeps BEFORE the network touches it, so network results can be read against it. Chance for 10 classes is 10%.
Classes 0-9 are the English digits, 10-19 German. Training speakers 0-3, 6-11; test also has speakers 4 and 5 who are never in training.
Usage: python3 tools/hexn_shd_frontend_v1.py DIR     (DIR holds shd_train.h5 and shd_test.h5)"""
import sys, itertools
import numpy as np

NCH = 700


def load(path, classes=range(10)):
    import h5py
    f = h5py.File(path, "r"); lab = f["labels"][:]; sp = f["extra/speaker"][:]; idx = [i for i in range(len(lab)) if lab[i] in classes]
    t = f["spikes/times"]; u = f["spikes/units"]
    return [(np.asarray(u[i]), np.asarray(t[i])) for i in idx], lab[idx].astype(int), sp[idx].astype(int)


def counts(units, times, nin, nbins, tmax=1.0):
    lines = (units.astype(np.int64) * nin) // NCH; b = np.minimum((times / tmax * nbins).astype(np.int64), nbins - 1); m = np.zeros((nbins, nin))
    np.add.at(m, (b, lines), 1); return m


def line_mean(data, nin, nbins):
    return sum(counts(u, t, nin, nbins).sum(axis=0) for u, t in data) / (len(data) * nbins) + 1e-9


def select(m, topn, mincount, scale=None):
    """m: bins x lines spike counts -> bins x lines 0/1 (at most topn per bin)"""
    s = m / scale if scale is not None else m; out = np.zeros_like(m)
    for b in range(m.shape[0]):
        order = np.argsort(-s[b], kind="stable")[:topn]
        for l in order:
            if m[b, l] >= mincount: out[b, l] = 1
    return out


def events(mat, cpb=1):
    """0/1 matrix -> {clock: [line ids]} as the network takes it"""
    ev = {}
    for b, l in zip(*np.nonzero(mat)): ev.setdefault(int(b) * cpb, []).append(int(l))
    return ev


def front(data, nin=48, nbins=40, topn=2, mincount=2, norm=True, scale=None):
    sc = (scale if scale is not None else line_mean(data, nin, nbins)) if norm else None
    return [select(counts(u, t, nin, nbins), topn, mincount, sc) for u, t in data], sc


def baseline(train, ytr, test, yte, nin, nbins, topn, mincount, norm, ncl=10):
    xtr, sc = front(train, nin, nbins, topn, mincount, norm); xte, _ = front(test, nin, nbins, topn, mincount, norm, scale=sc)
    tpl = np.stack([np.mean([x for x, y in zip(xtr, ytr) if y == c], axis=0).ravel() for c in range(ncl)]); tpl /= np.linalg.norm(tpl, axis=1, keepdims=True)
    pred = [int(np.argmax(tpl @ (x.ravel() / (np.linalg.norm(x) + 1e-9)))) for x in xte]
    return float(np.mean(np.array(pred) == yte)), float(np.mean([x.sum() for x in xte]))


def main(d):
    train, ytr, _ = load(d + "/shd_train.h5"); test, yte, ste = load(d + "/shd_test.h5")
    print("train %d  test %d recordings (English digits)" % (len(train), len(test)))
    print("%-5s %-6s %-4s %-6s %-5s | %-9s %s" % ("lines", "bins", "topn", "minct", "norm", "events/rec", "template accuracy %"))
    for nin, nbins, topn, mc, norm in itertools.product((48, 96), (40,), (1, 2, 4), (2,), (False, True)):
        a, ev = baseline(train, ytr, test, yte, nin, nbins, topn, mc, norm)
        print("%-5d %-6d %-4d %-6d %-5s | %-9.0f %.1f" % (nin, nbins, topn, mc, norm, ev, 100 * a), flush=True)


if __name__ == "__main__":
    main(sys.argv[1])
