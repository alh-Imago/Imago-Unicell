"""Parsing and flow of tools/hexn_kxresults_host_v1.py against a scripted fake link (5 Nov 2026; no card, no RTL)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tools"))
import hexn_kxresults_host_v1 as R


class Fake:
    def __init__(self, replies): self.replies = list(replies); self.sent = []; self.rx = b""
    def write(self, b): self.sent.append(bytes(b)); self.rx += self.replies.pop(0) if self.replies else b""
    def read(self, n): b, self.rx = self.rx[:n], self.rx[n:]; return b


def rec(kind, array, row, tick, word, idx): return bytes([(kind << 7) | (array << 5) | row]) + tick.to_bytes(2, "little") + word.to_bytes(4, "little") + bytes([idx])


def test_parse_status_and_records():
    s = R.parse_status(bytes([6, 1, 2, 3, 4, 0, 5])); assert s == dict(count=262, lost=2, full=True, armed=True, read_pointer=4, refused=5)
    r = R.parse_records(bytes([2]) + rec(0, 1, 3, 43, 0x6bdc696a, 0) + rec(1, 1, 0, 0, 0x00090014, 1))
    assert r[0] == dict(kind="word", array=1, row=3, tick=43, word=0x6bdc696a, index=0) and r[1]["kind"] == "judge" and r[1]["word"] == 0x00090014


def test_results_read_loops_until_empty_and_start_run_sees_refusal():
    link = Fake([bytes([2]) + rec(0, 0, 1, 5, 7, 0) + rec(0, 0, 2, 6, 8, 1), bytes([0])])
    got = R.results_read(link); assert len(got) == 2 and link.sent == [b"V\x20", b"V\x20"]
    t = dict(chain_hex="00", inputs=[(0, 1)], mask=1)
    assert R.start_run(Fake([b"K", b"K"]), t, load_chain=False) is True
    assert R.start_run(Fake([b"K", b"F"]), t, load_chain=False) is False
