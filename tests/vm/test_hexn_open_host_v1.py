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
class FakeSerial:
    """stands in for pyserial: the ESP32 greeting arrives first, as after the reset that opening the port causes; then it answers commands"""
    def __init__(self, greet_late=False):
        self.out = [] if greet_late else [b"OK hexn gateway ready\n"]; self.late = greet_late
    def readline(self): return self.out.pop(0) if self.out else b""
    def reset_input_buffer(self): pass
    def write(self, b):
        if self.late: self.out.append(b"OK hexn gateway ready\n"); self.late = False          # the greeting lands AFTER the command was sent
        self.out.append(b"OK 57320002\n" if b.startswith(b"ID") else b"OK\n")
def test_serial_link_skips_the_gateway_greeting():
    for late in (False, True):
        u = H.OpenUnit(H.SerialLink("fake", serial_obj=FakeSerial(greet_late=late))); assert u.id() == H.UNIT_ID
class GatewayModel:
    """pyserial stand-in that behaves like the gateway sketch (checksummed commands and replies, partial lines kept until a newline) in front of the unit model, with a FLAKY LINE:
    every 7th command has a character flipped, every 11th loses its newline (the gateway never answers), every 9th reply is damaged. The host must still get exactly the right words."""
    def __init__(self, flaky=True):
        self.emu = E.EmuLink(); self.out = [b"OK hexn gateway ready\n"]; self.buf = b""; self.n = 0; self.flaky = flaky
    def readline(self): return self.out.pop(0) if self.out else b""
    def reset_input_buffer(self): self.out = []
    def _reply(self, text):
        self.n += 1; line = "%s #%04X" % (text, sum(text.encode()) & 0xFFFF)
        if self.flaky and self.n % 9 == 0: line = line[:6] + "0" + line[7:]                       # damage one character of the reply
        self.out.append((line + "\n").encode())
    def write(self, b):
        for ch in b.decode():
            if ch not in "\r\n": self.buf += ch.encode(); continue
            line = self.buf.decode(); self.buf = b""
            if not line: continue
            h = line.rfind(" #")
            if h >= 0:
                try: want = int(line[h + 2:], 16)
                except ValueError: want = -1                                                       # a damaged checksum field is just a mismatch (strtoul in the sketch)
                if sum(line[:h].encode()) & 0xFFFF != want: self.out.append(b"ERR checksum\n"); continue
                line = line[:h]
            try: r = self.emu.cmd(line)
            except Exception: self.out.append(b"ERR bad command\n"); continue
            if r.startswith("OK"): self._reply(r)
            else: self.out.append((r + "\n").encode())
    def write_line(self, b):
        self.cmds = getattr(self, "cmds", 0) + 1
        if self.flaky and self.cmds % 7 == 0: b = b[:5] + (b"Z" if b[5:6] != b"Z" else b"Y") + b[6:]       # a character damaged on the way in
        if self.flaky and self.cmds % 11 == 0: b = b.rstrip(b"\n")                                             # the newline lost: no answer comes
        self._write(b)
    _write = write
    write = write_line
def test_flaky_serial_line_never_changes_a_word():
    gm = GatewayModel(flaky=True); link = H.SerialLink("fake", serial_obj=gm); u = H.OpenUnit(link); assert u.id() == H.UNIT_ID
    W = table(9); u.preset(4); u.load_judges(load_words(W), 0, -40); rs = rows(10, 150); r = u.stream([R.w_score(v) for v in rs]); exp = []
    for v in rs: exp += [R.score(W, 0, v)[0], R.score(W, -40, v)[0]]
    assert r == exp and link.retries > 3                                                                        # many exchanges were damaged, all were repaired by resending
