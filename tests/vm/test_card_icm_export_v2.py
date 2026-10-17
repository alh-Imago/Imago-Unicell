"""tests/vm/test_card_icm_export_v2.py -- ledger #1179: v2 of test_card_icm_export_v1.py (untouched); adds the native cross/corner tiles design.
Every design tested on the real card exists as a plain ICM file, loads into the VM's FlexGrid and gives the words the card printed. Bites: a changed word, a hand-edited file, and the tiles built as plain relays (which mixes the streams) must each be caught. VM only, no iverilog."""
import copy
import json
import os
import random
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "nano"))
import board_tests_v1 as bt  # noqa: E402
import board_tiles_v1 as tl  # noqa: E402
import replay_card_icm_vm_v2 as rp  # noqa: E402
from icm_v3 import IcmV3File  # noqa: E402

DIR = os.path.join(ROOT, "nano", "examples", "card_tested")
IDX = json.load(open(os.path.join(DIR, "card_tested_index.json")))
ALL = IDX["designs"] + IDX["multi_stream_designs"]
TILES = IDX["multi_stream_designs"][0]


def test_every_board_test_and_the_tiles_are_exported():
    assert [d["name"] for d in IDX["designs"]] == [t[0] for t in bt.TESTS]
    assert [d["name"] for d in IDX["multi_stream_designs"]] == ["tiles_flex"]


@pytest.mark.parametrize("d", ALL, ids=[d["name"] for d in ALL])
def test_each_design_replays_in_the_vm_equal_to_the_card(d):
    ok, msg = rp.replay_one(d, DIR)
    assert ok, msg


def test_the_tiles_saved_file_is_what_the_builder_makes_now():
    g, _, _ = tl.build_grid()
    fresh = IcmV3File(name="tiles_flex", records=g.records(), description=TILES["description"]).to_dict()
    assert json.load(open(os.path.join(DIR, "tiles_flex.icm.json"))) == fresh


def test_the_tiles_input_words_are_the_board_tests_seeded_words():
    g, ents, _ = tl.build_grid()
    r = random.Random(1169)
    xs = [r.getrandbits(32) for _ in range(8 * len(ents))]
    assert TILES["input_words_in_order"] == xs


def test_bite_tiles_built_as_plain_relays_mix_the_streams():
    g, ents, exits = tl.build_grid("ram")
    words = rp.interleave(rp.run_streams(g.records(), TILES["entries"], exits), len(exits))
    assert words != TILES["input_words_in_order"], "plain relays must not reproduce the six streams in order"


def test_bite_a_changed_expected_word_is_caught():
    d = copy.deepcopy(TILES)
    d["vm_expected_words"][5] ^= 1
    ok, _ = rp.replay_one(d, DIR)
    assert not ok


def test_bite_a_hand_edited_icm_file_is_caught(tmp_path):
    raw = json.load(open(os.path.join(DIR, TILES["icm"])))
    rec = raw["records"][0]
    k = next(k for k, v in rec.items() if isinstance(v, int) and not isinstance(v, bool))
    rec[k] += 1
    (tmp_path / TILES["icm"]).write_text(json.dumps(raw))
    with pytest.raises(ValueError):
        rp.replay_one(TILES, str(tmp_path))
