#!/usr/bin/env python3
"""tools/replay_card_icm_vm_v1.py -- load every card-tested ICM file (nano/examples/card_tested/) into the VM's flex grid, feed its input streams, and compare
(1) the words at the exit with the words stored in the index, and (2) the count and first eight words with the line the REAL CARD printed.
Prints one line per design and exits 1 if any differs.  Usage: python3 tools/replay_card_icm_vm_v1.py [--dir DIR]"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "nano"))
import board_tests_v1 as bt  # noqa: E402
from icm_v3 import IcmV3File  # noqa: E402


def replay_one(d, folder):
    f = IcmV3File.load(os.path.join(folder, d["icm"]))          # also checks the stored record hash
    if f.record_hash() != d["record_hash"]:
        return False, "record hash differs from the index"
    words = bt.expected(f.records, d["entries"], d["exit"])
    if words != d["vm_expected_words"]:
        return False, f"VM words differ from the index ({len(words)} vs {len(d['vm_expected_words'])})"
    c = d["card"]
    if c.get("n_hex") is None:
        return False, "no card line in the index"
    if int(c["n_hex"], 16) != len(words):
        return False, f"card counted {int(c['n_hex'], 16)} words, VM produced {len(words)}"
    first = ["%08X" % w for w in words[:len(c["first_words_hex"])]]
    if first != c["first_words_hex"]:
        return False, "first words differ from the card's"
    return True, f"{len(words)} words, equal to the card's count and first {len(first)} words"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=os.path.join(ROOT, "nano", "examples", "card_tested"))
    a = ap.parse_args()
    idx = json.load(open(os.path.join(a.dir, "card_tested_index.json")))
    bad = 0
    for d in idx["designs"]:
        ok, msg = replay_one(d, a.dir)
        bad += (not ok)
        print(("PASS " if ok else "FAIL ") + d["name"].ljust(22) + msg)
    print(f"{len(idx['designs']) - bad} of {len(idx['designs'])} replay equal")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
