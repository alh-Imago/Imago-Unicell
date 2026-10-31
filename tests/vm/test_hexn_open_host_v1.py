"""tests/vm/test_hexn_open_host_v1.py -- the PC side of the Hex-N front end (hexn_open_host_v1) against the Python model of the unit (hexn_open_emu_v1), 1 Nov 2026. No hardware and no iverilog needed.
Checks that the host sends the right register words, tables, presets and streams in the right order, and that results come back in the right order for one and two judges, including streams longer than one run. The register word encodings are
the ones the Verilog tests use (tests/hexn_open4, tests/hexn_open5). The model proves the host side only; the unit itself is proven by the Verilog simulations and the board runs."""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_open_host_v1 as H, hexn_open_emu_v1 as E, hexn_scorer_ref_v1 as R  # noqa: E402
def unit():
    e = E.EmuLink(); return H.OpenUnit(e), e
def table(seed, lo=-60, hi=61):
    rng = np.random.default_rng(seed); W = np.zeros((2, 8, 16), dtype=int); W[:, :, :12] = rng.integers(lo, hi, size=(2, 8, 12)); return W
def load_words(W): return [R.w_load(c, s, b, W[c][s][b]) for c in range(2) for s in range(8) for b in range(12)]
def rows(seed, n):
    rng = np.random.default_rng(seed); return [[int(x) for x in rng.integers(0, 12, size=8)] for _ in range(n)]
def test_encodings_match_the_verilog_tests():
    assert H.input_pins_word(btn1=31, btn2=85, btn3=80) == 9 | (11 << 4) | (9 << 8)        # tests/hexn_open4 and 5: buttons on pool pins 9, 10, 11
    assert H.output_pins_word(buzz=42) == (12 ^ 6) << 12                                    # buzzer on pool pin 12
    assert H.input_pins_word() == 0 and H.output_pins_word() == 0                           # defaults = the old wiring
    assert H.binning_word("log") == 0 and H.binning_word("linear", 5, 0) == 0x51            # fast key: linear, 32 ms bins
    assert H.control_word(True, "A") == 0xE0000001 and H.control_word(True, "B") == 0xE0000003 and H.control_word(False, "both") == 0xE0000004
def test_modes_presets_tables_and_pins():
    u, e = unit(); assert u.id() == H.UNIT_ID
    u.preset(1); s = u.status(); assert s["mode"] == 1 and s["preset_active"]
    u.mode(2); s = u.status(); assert s["mode"] == 2 and not s["preset_active"]
    words = [R.w_load(1, 1, b, -b) for b in range(12)] + [R.w_bias(3)]
    u.load_space("react", words); assert e.spaces[1] == words
    u.define_preset(6, mode=1, inputs=H.input_pins_word(btn1=31), outputs=H.output_pins_word(buzz=54))
    assert e.presets[40:48] == [1, 0, 0, 0, 9, 15 ^ 6 << 12 if False else (15 ^ 6) << 12, 0, 0] and e.presets[0] == 1 and e.presets[8] == 2     # preset 6 set, factory presets kept
    u.set_inputs(btn1=31); assert e.reg[26] == 9
    u.pins_default(); assert e.reg[26] == 0 and e.reg[27] == 0
    u.binning("press", "linear", 5, 0); assert e.reg[21] == 0x51
    u.restore(); assert e.presets[40:48] == [0] * 8 and u.presets[40:48] == [0] * 8
def test_single_judge_stream_equals_the_reference():
    u, e = unit(); W = table(1); u.preset(3)
    r = u.stream(load_words(W) + [R.w_bias(25)] + [R.w_score(v) for v in rows(2, 60)])
    assert r == [R.score(W, 25, v)[0] for v in rows(2, 60)]
def test_two_judges_and_long_streams_are_split_correctly():
    u, e = unit(); W = table(3); u.preset(4)
    u.load_judges(load_words(W), bias_a=0, bias_b=-40)                                      # 192 + 1 + 1 + 192 + 1 + 1 words: split over two runs
    rs = rows(4, 450); r = u.stream([R.w_score(v) for v in rs])                             # 450 rows, two judges: 900 results over several runs
    exp = []
    for v in rs: exp += [R.score(W, 0, v)[0], R.score(W, -40, v)[0]]
    assert len(r) == 900 and r == exp
def test_control_words_inside_one_stream():
    u, e = unit(); WA, WB = table(5), table(6); u.preset(4)
    s = load_words(WA) + [H.control_word_raw(3)] + load_words(WB) + [R.w_bias(-17), H.control_word_raw(1), R.w_bias(25)]
    rs = rows(7, 30); r = u.stream(s + [R.w_score(v) for v in rs]); exp = []
    for v in rs: exp += [R.score(WA, 25, v)[0], R.score(WB, -17, v)[0]]
    assert r == exp
