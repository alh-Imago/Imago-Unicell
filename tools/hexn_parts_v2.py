"""hexn_parts_v2 (11 Nov 2026: clone of hexn_parts_v1.py with a LINE CHECK at each bank's input. v1 found that 'input good but the cells match nothing' cannot tell an unknown part from a known part whose cells
simply did not respond (24% of known things were called 'unknown part'). ADDED per bank: for each of its 8 values the share of the run's active input lines that the value normally uses (the 48-bit line masks of
hexn_anomaly_tile_v1). LINE FIT = the best share. New bank states: UNKNOWN PART = input weight 2 and line fit below 0.6 (the lines themselves fit none of my values; 0.6 was set after looking at the fits of known and never-given patterns on 2 seeds: known 0.57 to 0.94, never-given 0.31 to 0.69; a first run with 0.45 caught only 35% of unknown parts); CLEAR = input weight 2 and a value is given by the cells
(match weight 2) or, when the cells are not clear, by the lines (fit at least 0.6 and 0.15 ahead of the second value); if cells and lines both give a value and disagree: UNSURE. Both rule sets (v1 = cells only, v2 = with
the line check) are run on the same tests. Earlier text:) IDENTIFYING A THING FROM ITS PARTS. Alan 19:22, 19:25, 19:41 (direction doc sections 95 and 97): a 'red ball' ties colour, shape and object together; the parts of the object become the inputs,
they generate maps, and each aspect brings its own map to the whole. Simulation only, toy patterns; every number is a property of this toy. Earlier tools untouched.
Model: 4 ASPECT banks (think colour, shape, size, kind). Each bank is the 3-layer network of section 49 with its own inputs and its own map blocks (hexn_recall_blocks_v1) for the 8 VALUES of its aspect (8 colours, 8 shapes, ...).
The shared memory holds 16 KNOWN THINGS, each one value per aspect (4 codes of 3 bits), drawn at random, so values are shared between things as they fall (some colour belongs to three things, another to one).
Each bank gives: its overlap score for each of its 8 values, and two weights 0..2 that need no knowledge of the answer (section 87): INPUT (events arrived against normal) and MATCH (how clear its own recall is).
A bank is CLEAR (input 2 and match 2: 'I saw my part well and I know it'), UNKNOWN PART (input 2 but match 0: 'I saw something well and it is none of my values'), or UNSURE (anything else).
The identification, from the clear banks' values only:
  KNOWN            exactly one known thing has all the clear values                 -> that thing
  SHORTLIST        several known things have them                                   -> those things, best first by the banks' summed scores (weighted by input weight)
  NEW COMBINATION  no known thing has them                                          -> 'new: these parts', plus the nearest known thing
  UNKNOWN PART     a bank reports an unknown part                                   -> which aspect, plus the parts the other banks saw
  UNSURE           no bank is clear                                                 -> the 3 best known things by score
Tests: A all parts present (10/30/50% dropped); B one aspect missing (its bank gets only the random noise events) or badly damaged (90%); C a known thing with ONE or TWO parts swapped for other known values, giving a
combination that is not stored; D one part that is not any stored value (a pattern the bank was never given), the other three from a known thing.
Usage: python3 tools/hexn_parts_v1.py [SEEDS]"""
import random, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_busnet_v1 as B, hexn_busnet_train_v1 as T, hexn_recall_blocks_v1 as R, hexn_recall_pool_v3 as P3, hexn_anomaly_tile_v1 as A1

NB = 4; NTH = 16; NS = 10; NTEST = 20; DROPS = (0.1, 0.3, 0.5, 0.9, 1.0); NV = T.NPAT
best = P3.best


def bank_state(o, lines):
    """-> (state, value). o = (scores, input weight, match weight, line fits per value)"""
    sc, wi, wm, lf = o; top = best(sc)
    if not lines: return ("clear" if wi == 2 and wm == 2 else "unknown" if wi == 2 and wm == 0 else "unsure"), top
    lo = sorted(range(len(lf)), key=lambda v: (-lf[v], v)); lv = lo[0] if lf[lo[0]] >= 0.6 and lf[lo[0]] - lf[lo[1]] >= 0.15 else None
    if wi != 2: return "unsure", top
    if lf[lo[0]] < 0.6: return "unknown", top
    if wm == 2: return ("clear" if lv is None or lv == top else "unsure"), top
    return ("clear", lv) if lv is not None else ("unsure", top)


def identify(obs, things, lines=True):
    """obs: per bank (scores, input weight, match weight, line fits) -> (verdict, payload)"""
    bs = [bank_state(o, lines) for o in obs]; top = [x[1] for x in bs]; state = [x[0] for x in bs]
    score = [sum(obs[b][1] * obs[b][0][th[b]] for b in range(NB)) for th in things]; order = sorted(range(len(things)), key=lambda j: (-score[j], j))
    clear = [b for b in range(NB) if state[b] == "clear"]; parts = {b: top[b] for b in clear}
    if "unknown" in state: return "UNKNOWN PART", dict(banks=[b for b in range(NB) if state[b] == "unknown"], parts=parts, near=order[:3])
    if not clear: return "UNSURE", dict(short=order[:3], parts=parts)
    fit = [j for j in order if all(things[j][b] == top[b] for b in clear)]
    if len(fit) == 1: return "KNOWN", dict(thing=fit[0], parts=parts)
    if len(fit) > 1: return "SHORTLIST", dict(short=fit, parts=parts)
    return "NEW COMBINATION", dict(parts=parts, near=order[:3])


def main(seeds):
    res = {}
    def add(case, key, n=1):
        d = res.setdefault(case, {}); d[key] = d.get(key, 0) + n
    for s in seeds:
        pool = []; normal = []; novel = []
        for b in range(NB):
            pats = [B.pattern(random.Random(100 + 50 * b + k)) for k in range(NV)]; net = R.build(10 * s + b, pats); kb = [x[0] for x in R.make_blocks(net, pats)]; lmask, _ = A1.learn_masks(net, pats)
            normal.append(sum(sum(len(v) for v in B.noisy(pats[k], random.Random(31000 + 13 * k + j), drop=0.1, jit=3).values()) for k in range(NV) for j in range(5)) / (5.0 * NV))
            def obs_of(p, seed, d):
                ev = B.noisy(p, random.Random(seed), drop=d, jit=3); m2 = B.map_of(T.fresh_run(net, ev), (2,)); sc = [R.acc_int(m2, x) for x in kb]
                act = {i for v in ev.values() for i in v}
                return (sc, P3.w_input(sum(len(v) for v in ev.values()), normal[b]), P3.w_match(sc), [len(act & m) / max(1, len(act)) for m in lmask])
            pool.append({(k, d): [obs_of(pats[k], 71000 + 1000 * b + 97 * k + j + int(1000 * d), d) for j in range(NS)] for k in range(NV) for d in DROPS})
            novel.append([obs_of(B.pattern(random.Random(800 + 50 * b + q)), 91000 + 100 * b + 10 * q + j, 0.1) for q in range(4) for j in range(5)])       # 4 patterns the bank was never given
        r = random.Random(700 + s); things = []
        while len(things) < NTH:
            t = tuple(r.randrange(NV) for _ in range(NB))
            if t not in things: things.append(t)
        known = set(things)
        def get(truth, drops): return [pool[b][(truth[b], drops[b])][r.randrange(NS)] for b in range(NB)]
        def score_known(case, j, obs, hidden=None):
            for lines in (False, True): score_known1(("v2 " if lines else "v1 ") + case, j, obs, lines)
        def score_known1(case, j, obs, lines):
            v, p = identify(obs, things, lines); add(case, "n")
            if v == "KNOWN": add(case, "known right" if p["thing"] == j else "known WRONG")
            elif v == "SHORTLIST": add(case, "short has it" if j in p["short"] else "short misses it"); add(case, "short size", len(p["short"])); add(case, "short n"); add(case, "short first", p["short"][0] == j)
            elif v == "UNSURE": add(case, "unsure has it" if j in p["short"] else "unsure misses it")
            else: add(case, "false " + v.lower())
            add(case, "parts wrong", sum(1 for b, val in p["parts"].items() if val != things[j][b])); add(case, "parts given", len(p["parts"]))
        for d in (0.1, 0.3, 0.5):
            for j in range(NTH):
                for _ in range(NTEST): score_known("A all parts, %d%% dropped" % (100 * d), j, get(things[j], [d] * NB))
        for nm, dm in (("B one aspect MISSING, others 10%", 1.0), ("B one aspect at 90%, others 10%", 0.9)):
            for j in range(NTH):
                for _ in range(NTEST):
                    drops = [0.1] * NB; drops[r.randrange(NB)] = dm; score_known(nm, j, get(things[j], drops))
        for nsw in (1, 2):
            case = "C %d part(s) swapped (not a stored thing)" % nsw
            for j in range(NTH):
                for _ in range(NTEST):
                    while True:
                        t = list(things[j])
                        for b in r.sample(range(NB), nsw): t[b] = r.choice([v for v in range(NV) if v != things[j][b]])
                        if tuple(t) not in known: break
                    ob = get(t, [0.1] * NB)
                    for lines in (False, True):
                        c2 = ("v2 " if lines else "v1 ") + case; v, p = identify(ob, things, lines); add(c2, "n"); add(c2, "verdict " + v)
                        if v == "NEW COMBINATION":
                            add(c2, "new n"); add(c2, "new all parts right", all(val == t[b] for b, val in p["parts"].items())); add(c2, "new parts given", len(p["parts"])); add(c2, "new nearest is original", p["near"][0] == j)
        case = "D one part not a stored value"
        for j in range(NTH):
            for _ in range(NTEST):
                obs = get(things[j], [0.1] * NB); ub = r.randrange(NB); obs[ub] = novel[ub][r.randrange(len(novel[ub]))]
                for lines in (False, True):
                    c2 = ("v2 " if lines else "v1 ") + case; v, p = identify(obs, things, lines); add(c2, "n"); add(c2, "verdict " + v)
                    if v == "UNKNOWN PART": add(c2, "right bank", p["banks"] == [ub])
    pc = lambda d, k: 100.0 * d.get(k, 0) / d["n"]
    print("%d seeds, 16 known things, %d tests per thing per case; percent of tests" % (len(seeds), NTEST))
    print("\n%-39s %-7s %-22s %-10s %-12s %-10s %-10s %s" % ("known thing shown", "NAMED", "SHORTLIST (has it,", "UNSURE", "named", "called", "called", "parts reported"))
    print("%-39s %-7s %-22s %-10s %-12s %-10s %-10s %s" % ("", "right", "size, it is first)", "(has it)", "WRONG", "new", "unk. part", "wrong"))
    for case, d in res.items():
        if not case[3] in "AB": continue
        sn = max(1, d.get("short n", 0))
        print("%-39s %5.1f   %5.1f  (%.1f, %3.0f%%)      %5.1f      %5.1f        %5.1f      %5.1f      %.1f%%" % (case, pc(d, "known right"), pc(d, "short has it"), d.get("short size", 0) / sn, 100.0 * d.get("short first", 0) / sn,
              pc(d, "unsure has it"), pc(d, "known WRONG") + pc(d, "short misses it") + pc(d, "unsure misses it"), pc(d, "false new combination"), pc(d, "false unknown part"), 100.0 * d.get("parts wrong", 0) / max(1, d.get("parts given", 0))))
    for case, d in res.items():
        if case[3] not in "CD": continue
        print("\n%s: verdicts: %s" % (case, "; ".join("%s %.1f%%" % (k[8:], pc(d, k)) for k in sorted(d) if k.startswith("verdict "))))
        if "new n" in d: print("   when called new: every reported part right %.1f%%; parts reported %.1f of 4; nearest known thing is the one it was made from %.1f%%" % (100.0 * d["new all parts right"] / d["new n"], d["new parts given"] / d["new n"], 100.0 * d["new nearest is original"] / d["new n"]))
        if "right bank" in d: print("   when called unknown part: the right aspect named %.1f%%" % (100.0 * d["right bank"] / max(1, d.get("verdict UNKNOWN PART", 0))))


if __name__ == "__main__":
    main(tuple(range(1, 1 + (int(sys.argv[1]) if len(sys.argv) > 1 else 5))))
