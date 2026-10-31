#!/usr/bin/env python3
"""hexn_open_host_v1: THE PC SIDE OF THE FRONT END FOR THE OPEN UNIT (new file 1 Nov 2026). Drives the whole open unit (build v5; stages 1 to 4b of docs/hex-n/OPEN_UNIT_v1.md) through the ESP32 gateway sketch (tools/esp32/hexn_gateway):
  modes and presets, loadable tables (reaction, Morse, decode, glyph, presets), the three binning words, the pin matrix, the raw word stream with one or two judges, and the live pin levels.
Usage:   from hexn_open_host_v1 import OpenUnit, SerialLink;   u = OpenUnit(SerialLink('/dev/ttyUSB0'));   u.preset(1)
A link is any object with .cmd(line) -> reply line; SerialLink talks to the ESP32 (pyserial), tools/hexn_open_emu_v1.py has a Python model of the unit for testing without hardware.
Register map (docs/hex-n/OPEN_UNIT_v1.md): 16 mode, 17 copy control, 19 copy go, 20/21/22 binning react/press/gap, 23 restore, 24 raw control {out_base, count}, 25 raw go, 26 input pins, 27 output pins, 28 raw judge control, 29 preset select; status = register 10."""
import time
MODE, COPYCTL, COPYGO, BIN_REACT, BIN_PRESS, BIN_GAP, RESTORE, RAWCTL, RAWGO, PIN_IN, PIN_OUT, JUDGE, PRESET, STATUS = 16, 17, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 10
SPACES = {"react": 1, "morse": 2, "decode": 3, "glyph": 4, "presets": 5}
POOL = [72, 71, 86, 25, 26, 27, 28, 29, 30, 31, 85, 80, 42, 41, 56, 54]                 # Tang pin of pool index 0..15
OUT_DEFAULT = {"latch": 3, "clk": 4, "data": 5, "buzz": 6}
UNIT_ID = 0x57320002
class SerialLink:
    """The real link to the ESP32 gateway. Opening the port resets the ESP32 (it prints 'OK hexn gateway ready' about a second later), so wait for that greeting, then throw away anything else.
    Every command goes out with ' #HHHH' (16-bit sum of its bytes) and every OK reply is checked the same way; a damaged or missing exchange is resent (up to 4 tries), so a character lost on the line can never silently change a word."""
    BANNER = "OK hexn gateway ready"
    def __init__(self, port, baud=460800, timeout=3.0, serial_obj=None):
        if serial_obj is None:
            import serial; serial_obj = serial.Serial(port, baud, timeout=timeout)
        self.s = serial_obj; self.retries = 0; t0 = time.time()
        while time.time() - t0 < 4.0:                                   # up to 4 s for the greeting after the reset
            if self.BANNER in self.s.readline().decode(errors="replace"): break
        time.sleep(0.1); self.s.reset_input_buffer()
    def _read_reply(self):
        for _ in range(4):
            r = self.s.readline().decode(errors="replace").strip()
            if r == self.BANNER: continue                               # a late greeting, not the answer
            return r
        return ""
    def cmd(self, line, tries=4):
        msg = ("%s #%04X\n" % (line, sum(line.encode()) & 0xFFFF)).encode(); why = ""
        for attempt in range(tries):
            self.s.write(msg); r = self._read_reply()
            if not r: why = "no reply"
            elif r.startswith("ERR checksum"): why = "gateway saw a damaged command"
            elif r.startswith("ERR"): raise IOError("gateway said %r to %r" % (r, line[:60]))
            else:
                body, sep, tail = r.rpartition(" #")
                if not sep: return r                                    # no checksum on this reply (an older gateway)
                try: good = (int(tail, 16) == (sum(body.encode()) & 0xFFFF))
                except ValueError: good = False
                if good and body.startswith("OK"): return body
                why = "damaged reply"
            self.retries += 1; self.s.write(b"\n"); time.sleep(0.05); self.s.reset_input_buffer()          # clear a half-received line on both sides, then resend
        raise IOError("no good answer to %r after %d tries (%s)" % (line[:60], tries, why))
def binning_word(kind="log", shift=0, low_ms=0):
    """0 = log2 of the milliseconds; 'linear' = (ms - low) >> shift, capped at 11"""
    return 0 if kind == "log" else 1 | ((shift & 15) << 4) | ((low_ms & 0xFFF) << 16)
def input_pins_word(btn1=None, btn2=None, btn3=None):
    """Tang pin number for each button (None = its normal pin 72, 71, 86); returns the cfg26 / preset word 4"""
    w = 0
    for k, pin in enumerate((btn1, btn2, btn3)):
        if pin is None: continue
        w |= (POOL.index(pin) ^ k) << (4 * k)
    return w
def output_pins_word(latch=None, clk=None, data=None, buzz=None):
    w = 0
    for k, (n, pin) in enumerate((("latch", latch), ("clk", clk), ("data", data), ("buzz", buzz))):
        if pin is None: continue
        w |= (POOL.index(pin) ^ OUT_DEFAULT[n]) << (4 * k)
    return w
def control_word(two_judges=False, loads_to="A"):
    """judge control word for the raw stream (top nibble 14): bit 0 two judges; bits 2:1 where LOAD / BIAS words go (A, B or both)"""
    return (14 << 28) | (1 if two_judges else 0) | ({"A": 0, "B": 1, "both": 2}[loads_to] << 1)
def judge_value(two_judges=False, loads_to="A"): return control_word(two_judges, loads_to) & 7
class OpenUnit:
    def __init__(self, link):
        self.link = link; self.seq = 1000; self.presets = self.factory_presets()
    # ---- registers and scratch words
    def reg_read(self, r): return int(self.link.cmd("R %x" % r).split()[1], 16)
    def reg_write(self, r, v): self.link.cmd("W %x %x" % (r, v & 0xFFFFFFFF))
    def write_words(self, addr, words):
        for i in range(0, len(words), 255): self.link.cmd("WW %x %s" % (addr + i, " ".join("%x" % (w & 0xFFFFFFFF) for w in words[i:i + 255])))
    def read_words(self, addr, n):
        out = []
        for i in range(0, n, 255): out += [int(x, 16) for x in self.link.cmd("RW %x %x" % (addr + i, min(255, n - i))).split()[1:]]
        return out
    def id(self):
        v = int(self.link.cmd("ID").split()[1], 16)
        if v != UNIT_ID: raise IOError("not the open unit: id %08x" % v)
        return v
    def status(self):
        s = self.reg_read(STATUS)
        return {"raw": s, "mode": s & 3, "react_ready": bool(s >> 2 & 1), "morse_ready": bool(s >> 3 & 1), "copy_busy": bool(s >> 4 & 1), "defaults_loaded": bool(s >> 5 & 1),
                "raw_busy": bool(s >> 6 & 1), "preset_active": bool(s >> 7 & 1), "raw_results": s >> 8 & 255, "pin_levels": {POOL[i]: (s >> (16 + i)) & 1 for i in range(16)}}
    def _wait(self, key, tries=2000):
        for _ in range(tries):
            if not self.status()[key]: return
        raise IOError("unit still %s" % key)
    # ---- personalities
    active_preset = 0
    def mode(self, m): self.reg_write(PRESET, 0); self.active_preset = 0; self.reg_write(MODE, m)
    def preset(self, n): self.reg_write(PRESET, 0); self.reg_write(PRESET, n); self.active_preset = n if 1 <= n <= 8 else 0      # 0 = none (direct registers), 1..8
    def effective_judge(self):
        """the judge control a run starts with: the active preset's word 6, else register 28"""
        return (self.presets[(self.active_preset - 1) * 8 + 6] & 7) if self.active_preset else (self.reg_read(JUDGE) & 7)
    def restore(self): self.seq += 1; self.reg_write(RESTORE, self.seq); self._wait("copy_busy"); self.presets = self.factory_presets()
    # ---- tables
    def load_space(self, space, words):
        sp = SPACES[space] if isinstance(space, str) else space
        self.write_words(0, words); self.reg_write(COPYCTL, (sp << 28) | len(words)); self.seq += 1; self.reg_write(COPYGO, self.seq); self._wait("copy_busy")
    def binning(self, channel, kind="log", shift=0, low_ms=0): self.reg_write({"react": BIN_REACT, "press": BIN_PRESS, "gap": BIN_GAP}[channel], binning_word(kind, shift, low_ms))
    # ---- pins
    def set_inputs(self, **kw): self.reg_write(PIN_IN, input_pins_word(**kw))
    def set_outputs(self, **kw): self.reg_write(PIN_OUT, output_pins_word(**kw))
    def pins_default(self): self.reg_write(PIN_IN, 0); self.reg_write(PIN_OUT, 0)
    def pin_levels(self): return self.status()["pin_levels"]
    # ---- presets (eight words each: mode, bins react, press, gap, input pins, output pins, judge control, reserved)
    @staticmethod
    def factory_presets():
        p = [0] * 64; p[0] = 1; p[8] = 2; p[16] = 3; p[24] = 3; p[24 + 6] = 1; return p
    def define_preset(self, n, mode=0, bin_react=0, bin_press=0, bin_gap=0, inputs=0, outputs=0, judge=0):
        assert 1 <= n <= 8; self.presets[(n - 1) * 8:(n - 1) * 8 + 8] = [mode, bin_react, bin_press, bin_gap, inputs, outputs, judge, 0]; self.load_space("presets", self.presets)
    # ---- the raw word stream
    MAX_IN = 200; OUT_BASE = 600                       # 200 input words give at most 400 results, which fit the scratch RAM above address 600
    def stream(self, words, jc=None):
        """Feed scorer words (SCORE / LOAD / BIAS / CONTROL in any mix) to the unit (mode 3 must be selected, e.g. preset 3 or 4); returns all result words in order.
        A long stream is cut into runs of at most MAX_IN words. The unit restarts every run at its register / preset judge control, so each run after the first starts with a control word
        carrying the value the previous run ended with. The number of results is counted here (SCORE words, twice when two judges are on) because the unit's own counter stops at 255."""
        cur = self.effective_judge(); out = []; i = 0; first = True
        if jc is not None: words = [control_word_raw(jc)] + list(words)
        while i < len(words):
            chunk = [] if first else [control_word_raw(cur)]
            part = words[i:i + self.MAX_IN - len(chunk)]; i += len(part); chunk += part; first = False; expect = 0
            for w in chunk:
                t = w >> 28
                if t == 14: cur = w & 7
                elif t < 12: expect += 2 if cur & 1 else 1
            self.write_words(0, chunk); self.reg_write(RAWCTL, (self.OUT_BASE << 16) | len(chunk)); self.seq += 1; self.reg_write(RAWGO, self.seq); self._wait("raw_busy")
            if expect:
                seen = self.status()["raw_results"]
                if seen != min(255, expect): raise IOError("unit counted %d results, expected %d" % (seen, min(255, expect)))
                out += self.read_words(self.OUT_BASE, expect)
        return out
    def load_judges(self, table_words, bias_a=0, bias_b=None):
        """table_words: LOAD words of one table (no BIAS). Judge A gets the table and bias_a; if bias_b is given judge B gets the same table with that bias. Leaves jc = two judges, loads to A when bias_b is given."""
        w = [control_word_raw(judge_value(bias_b is not None, "A"))] + list(table_words) + [(13 << 28) | (bias_a & 0xFFFF)]
        if bias_b is not None: w += [control_word_raw(judge_value(True, "B"))] + list(table_words) + [(13 << 28) | (bias_b & 0xFFFF), control_word_raw(judge_value(True, "A"))]
        self.stream(w)
def control_word_raw(jc): return (14 << 28) | (jc & 7)
