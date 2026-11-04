"""tests/vm/test_hexn_kxarr_host_v1.py - the Kintex array host logic (selftest over a link object) against a pretend card; checks the framing and the verdicts only, NOT OpenOCD, the bridge or the hardware."""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import pytest
pytest.importorskip("serial")
import hexn_kxarr_host_v1 as K

VEC = {"pattern_id_hex": "90894555", "rows": 7, "tests": [{"name": "t", "chain_hex": "a1b2", "inputs": [[1, 5]], "mask": 2, "expected": [[3, 12, 40]]}]}


class Link:
    """a pretend card behind a read/write link: answers I, W, B, D, G, L like the frame"""
    def __init__(self, pid=0x90894555, rows=7, word=12): self.pid, self.rows, self.word, self.rx, self.out = pid, rows, word, bytearray(), bytearray()
    def reset_input_buffer(self): self.out.clear()
    def write(self, b):
        self.rx += b
        while self.rx:
            c = self.rx[0:1]
            if c == b"I": self.out += self.pid.to_bytes(4, "little") + bytes([self.rows]); del self.rx[:1]
            elif c == b"W": self.out += b"K"; del self.rx[:1]
            elif c == b"B":
                if len(self.rx) < 3: return
                self.out += b"K"; del self.rx[:3]
            elif c == b"D":
                if len(self.rx) < 6: return
                self.out += b"K"; del self.rx[:6]
            elif c == b"G":
                if len(self.rx) < 2: return
                self.out += b"K"; del self.rx[:2]
            elif c == b"L": self.out += bytes([1, 3]) + self.word.to_bytes(4, "little") + (40).to_bytes(2, "little"); del self.rx[:1]
            else: del self.rx[:1]
    def read(self, n):
        d = bytes(self.out[:n]); del self.out[:n]; return d


def test_pass(monkeypatch):
    monkeypatch.setattr(K.time, "sleep", lambda s: None); lines = []
    assert K.selftest(Link(), VEC, lines.append) and lines[-1] == "SELFTEST PASS"


def test_wrong_word_and_wrong_id_fail(monkeypatch):
    monkeypatch.setattr(K.time, "sleep", lambda s: None); lines = []
    assert not K.selftest(Link(word=13), VEC, lines.append) and lines[-1] == "SELFTEST FAIL"
    lines = []; assert not K.selftest(Link(pid=0x1234), VEC, lines.append) and any("ID MISMATCH" in l for l in lines)
