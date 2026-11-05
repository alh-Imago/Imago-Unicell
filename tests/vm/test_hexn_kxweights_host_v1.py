"""Frames of tools/hexn_kxweights_host_v1.py against a scripted fake link (5 Nov 2026; no card, no RTL)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tools"))
import hexn_kxweights_host_v1 as W


class Fake:
    def __init__(self, replies): self.replies = list(replies); self.sent = []; self.rx = b""
    def write(self, b): self.sent.append(bytes(b)); self.rx += self.replies.pop(0) if self.replies else b""
    def read(self, n): b, self.rx = self.rx[:n], self.rx[n:]; return b


def test_save_load_index_frames():
    link = Fake([b"K", b"K", b"K"]); assert W.weights_save(link, 2) is True; W.weights_load(link, 3); W.weights_index(link, 1, 255)
    assert link.sent == [b"O\x02", b"F\x03", b"E\x01\xff"]


def test_read_is_split_into_requests_of_at_most_255_words():
    w = [i for i in range(257)]; raw = b"".join(x.to_bytes(4, "little") for x in w)
    link = Fake([raw[:4 * 255], raw[4 * 255:]]); got = W.weights_read(link, 1)
    assert got == w and link.sent == [b"r\x01\x00\x00\xff", b"r\x01\x00\xff\x02"]
