"""tests/vm/test_card_icm_export_v1.py -- ledger #1177: every design tested on the real card exists as a plain ICM file in nano/examples/card_tested/, loads into the VM's FlexGrid, and gives the words the card printed.
Bites: a changed expected word and a hand-edited ICM file must each be caught. Needs no iverilog (VM only)."""
import copy
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "nano"))
import board_tests_v1 as bt  # noqa: E402
import replay_card_icm_vm_v1 as rp  # noqa: E402
from icm_v3 import IcmV3File  # noqa: E402

DIR = os.path.join(ROOT, "nano", "examples", "card_tested")
INDEX = json.load(open(os.path.join(DIR, "card_tested_index.json")))["designs"]


def test_every_board_test_is_exported():
    assert [d["name"] for d in INDEX] == [t[0] for t in bt.TESTS], "a board test has no exported ICM (re-run tools/export_card_icm_v1.py)"


@pytest.mark.parametrize("d", INDEX, ids=[d["name"] for d in INDEX])
def test_each_design_replays_in_the_vm_equal_to_the_card(d):
    ok, msg = rp.replay_one(d, DIR)
    assert ok, msg


@pytest.mark.parametrize("t", bt.TESTS, ids=[t[0] for t in bt.TESTS])
def test_saved_file_is_what_the_builder_makes_now(t):
    name, desc, mk, *_ = t
    fresh = IcmV3File(name=name, records=mk(), description=desc).to_dict()
    assert json.load(open(os.path.join(DIR, name + ".icm.json"))) == fresh


def test_bite_a_changed_expected_word_is_caught():
    d = copy.deepcopy(INDEX[0])
    d["vm_expected_words"][3] ^= 1
    ok, _ = rp.replay_one(d, DIR)
    assert not ok


def test_bite_a_hand_edited_icm_file_is_caught(tmp_path):
    d = INDEX[2]
    raw = json.load(open(os.path.join(DIR, d["icm"])))
    rec = raw["records"][0]
    k = next(k for k, v in rec.items() if isinstance(v, int) and not isinstance(v, bool))
    rec[k] += 1
    (tmp_path / d["icm"]).write_text(json.dumps(raw))
    with pytest.raises(ValueError):
        rp.replay_one(d, str(tmp_path))
