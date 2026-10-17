#!/usr/bin/env python3
"""tools/export_card_icm_v1.py -- write the designs that were tested on the real card as plain ICM v3 files, so anyone can load them into the VM.

The ten group tests (ledger #1025 / #1167) were always BUILT as ICM records by tools/board_tests_v1.py, but only in a temporary folder. This saves them to nano/examples/card_tested/<name>.icm.json and writes an index (card_tested_index.json) with, per design: the input streams, the VM's expected output words (FlexGrid), and the line the real card printed (from docs/measurements/board_groups_1167/).
Nothing here changes a proven file. Re-run: python3 tools/export_card_icm_v1.py"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "nano"))
import board_tests_v1 as bt  # noqa: E402
from icm_v3 import IcmV3File  # noqa: E402

OUT = os.path.join(ROOT, "nano", "examples", "card_tested")
RESULTS = os.path.join(ROOT, "docs", "measurements", "board_groups_1167", "board_results_1167.txt")


def card_lines():
    """test name -> the 'board :' line the real card printed in the 13 Oct group run"""
    d = {}
    for ln in open(RESULTS):
        m = re.match(r"^   board    : (UCT (\S+) .*)$", ln.rstrip("\n"))
        if m:
            d[m.group(2)] = m.group(1)
    return d


def main():
    os.makedirs(OUT, exist_ok=True)
    cards = card_lines()
    index = []
    for name, desc, mk, streams, gaps, stalls in bt.TESTS:
        recs = mk()
        f = IcmV3File(name=name, records=recs, description=desc)
        f.save(os.path.join(OUT, name + ".icm.json"))
        words = bt.expected(recs, streams)
        line = cards.get(name, "")
        m = re.search(r" n=([0-9A-F]+) .* sig=([0-9A-F]+) w=(\S*)", line)
        index.append({"name": name, "description": desc, "icm": name + ".icm.json", "record_hash": f.record_hash(),
                      "entries": streams, "exit": "O", "random_gaps_on_inputs": gaps, "random_stalls_on_exit": stalls,
                      "vm_expected_words": words,
                      "card": {"ledger": "#1167", "line": line, "n_hex": m.group(1) if m else None,
                               "sig": m.group(2) if m else None,
                               "first_words_hex": m.group(3).split(",") if m else []}})
    json.dump({"about": "Designs tested on the real Tang Nano 20K. Load each icm with IcmV3File.load, run it in FlexGrid with the entry streams, compare the words at the exit cell O. Gaps/stalls only change timing on the card, never the words.",
               "designs": index}, open(os.path.join(OUT, "card_tested_index.json"), "w"), indent=1)
    print("wrote", len(index), "ICM files and the index to", os.path.relpath(OUT, ROOT))


if __name__ == "__main__":
    main()
