#!/usr/bin/env python3
"""tools/export_card_icm_v2.py -- v2 of tools/export_card_icm_v1.py (ledger #1179): the same ten group-test designs PLUS the native cross and corner tiles (#1169/#1170), written as plain ICM v3 files in nano/examples/card_tested/ with one index.
v1 is untouched: the ten stay in "designs" exactly as v1 wrote them (so v1 tools and test still pass), the tiles go in "multi_stream_designs". The tiles design is the one the board test uses (tools/board_tiles_v1.py build_grid: three tiles, six streams, 8 words per stream, seed 1169); on the card a shim interleaves the six streams, so the expected output equals the input in order.
Re-run: python3 tools/export_card_icm_v2.py"""
import json
import os
import random
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "nano"))
import board_tests_v1 as bt  # noqa: E402
import board_tiles_v1 as tl  # noqa: E402
import replay_card_icm_vm_v2 as rp  # noqa: E402
from icm_v3 import IcmV3File  # noqa: E402

OUT = os.path.join(ROOT, "nano", "examples", "card_tested")
GROUPS = os.path.join(ROOT, "docs", "measurements", "board_groups_1167", "board_results_1167.txt")
TILES = os.path.join(ROOT, "docs", "measurements", "board_tiles_1170", "board_results.txt")
N_WORDS = 8          # per stream, the board test's default (--n 8)


def card_lines(path):
    d = {}
    for ln in open(path):
        m = re.match(r"^\s+board\s+: (UCT (\S+) .*)$", ln.rstrip("\n"))
        if m:
            d[m.group(2)] = m.group(1)
    return d


def card_block(ledger, line):
    m = re.search(r" n=([0-9A-F]+) .* sig=([0-9A-F]+) w=(\S*)", line)
    return {"ledger": ledger, "line": line, "n_hex": m.group(1) if m else None, "sig": m.group(2) if m else None,
            "first_words_hex": m.group(3).split(",") if m else []}


def main():
    os.makedirs(OUT, exist_ok=True)
    groups, tiles = card_lines(GROUPS), card_lines(TILES)
    index = []
    for name, desc, mk, streams, gaps, stalls in bt.TESTS:
        recs = mk()
        f = IcmV3File(name=name, records=recs, description=desc)
        f.save(os.path.join(OUT, name + ".icm.json"))
        index.append({"name": name, "description": desc, "icm": name + ".icm.json", "record_hash": f.record_hash(),
                      "entries": streams, "exit": "O", "random_gaps_on_inputs": gaps, "random_stalls_on_exit": stalls,
                      "vm_expected_words": bt.expected(recs, streams), "card": card_block("#1167", groups.get(name, ""))})
    # the native cross and corner tiles (flex)
    g, ents, exits = tl.build_grid()
    recs = g.records()
    desc = ("three native tiles in one flex grid: a CROSS (W to E and N to S) and two CORNERS (turn 0: W to S and E to N; turn 1: W to N and E to S); "
            "six independent streams, each must come out of its own exit unchanged (a tile that mixed or swapped streams would change the words)")
    f = IcmV3File(name="tiles_flex", records=recs, description=desc)
    f.save(os.path.join(OUT, "tiles_flex.icm.json"))
    r = random.Random(1169)
    xs = [r.getrandbits(32) for _ in range(N_WORDS * len(ents))]
    streams = {e: xs[k::len(ents)] for k, e in enumerate(ents)}      # the shim hands word i to stream i % 6
    words = rp.interleave(rp.run_streams(recs, streams, exits), len(ents))
    multi = [{"name": "tiles_flex", "kind": "interleaved", "description": desc, "icm": "tiles_flex.icm.json", "record_hash": f.record_hash(),
                  "entries": streams, "exits": exits, "random_gaps_on_inputs": False, "random_stalls_on_exit": True,
                  "vm_expected_words": words, "input_words_in_order": xs, "card": card_block("#1170", tiles.get("tiles_flex", ""))}]
    json.dump({"about": "Designs tested on the real Tang Nano 20K. Load each icm with IcmV3File.load, run it in FlexGrid with the entry streams, compare the words at the exit(s). designs: one exit cell O each. multi_stream_designs: several entries and exits, read round-robin in the order listed (on the card a shim does this). Gaps/stalls only change timing on the card, never the words.",
               "designs": index, "multi_stream_designs": multi}, open(os.path.join(OUT, "card_tested_index.json"), "w"), indent=1)
    print("wrote", len(index) + len(multi), "ICM files and the index to", os.path.relpath(OUT, ROOT))


if __name__ == "__main__":
    main()
