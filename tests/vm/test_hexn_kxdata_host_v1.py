"""Entry encoding and flow of tools/hexn_kxdata_host_v1.py against a scripted fake link (5 Nov 2026; no card, no RTL)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tools"))
import hexn_kxdata_host_v1 as D


class Fake:
    def __init__(self, replies): self.replies = list(replies); self.sent = []; self.rx = b""
    def write(self, b): self.sent.append(bytes(b)); self.rx += self.replies.pop(0) if self.replies else b""
    def read(self, n): b, self.rx = self.rx[:n], self.rx[n:]; return b


def test_entries_match_the_rtl_format():
    assert D.entry_d(6, 0x11223344) == bytes([6, 0x44, 0x33, 0x22, 0x11, 0, 0, 0])
    assert D.entry_g(0x55, 2000) == bytes([0xd5, 0xd0, 0x07, 0, 0, 0, 0, 0])
    t = dict(inputs=[(0, 1), (2, 3)], mask=5); e = D.entries_for(t, 3, 100)
    assert len(e) == 5 and e[:2] == [D.entry_d(0, 1), D.entry_d(2, 3)] and e[2:] == [D.entry_g(5, 100)] * 3 and all(len(x) == 8 for x in e)


def test_store_and_run_frames():
    link = Fake([b"K"]); D.data_store(link, 0x0102, [D.entry_g(1, 2)]); assert link.sent == [b"T\x01\x02\x00\x01" + D.entry_g(1, 2)]
    link = Fake([b"F\x06\x00"]); assert D.data_run(link, 4, 9) == ("F", 6) and link.sent == [b"H\x00\x04\x00\x09"]
