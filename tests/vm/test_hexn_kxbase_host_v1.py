"""tests/vm/test_hexn_kxbase_host_v1.py - byte framing of the base host commands (info, select, library write and load, judge word, result, mode) against a pretend card. NOT the card."""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_kxbase_host_v1 as H


class Link:
    def __init__(s, reply=b""): s.sent = bytearray(); s.out = bytearray(reply)
    def reset_input_buffer(s): pass
    def write(s, b): s.sent += b
    def read(s, n): d = bytes(s.out[:n]); del s.out[:n]; return d


def test_framing():
    l = Link(b"\x45\x53\x41\x42\x02\x04"); assert H.info(l) == dict(id="42415345", arrays=2, library_slots=4) and l.sent == b"N"
    l = Link(b"K"); H.select(l, 1); assert l.sent == b"A\x01"
    l = Link(b"K"); H.library_write(l, 2, b"\x01\x02\x03"); assert l.sent == b"P\x02\x00\x03\x01\x02\x03"
    l = Link(b"K"); H.library_load(l, 3); assert l.sent == b"Q\x03"
    l = Link(b"K"); H.judge_word(l, H.LOAD(1, 10, 9)); assert l.sent == b"J" + (0xC10A0009).to_bytes(4, "little")
    l = Link(bytes([1, 0x14, 0, 9, 0, 0])); assert H.judge_result(l) == (1, 0x00090014, 0) and l.sent == b"R"
    l = Link(b"K"); H.mode(l, 3); assert l.sent == b"M\x03"


def test_choice_framing():
    l = Link(b"K"); H.set_choice(l, 0, 1); assert l.sent == b"C\x00\x01"
    l = Link(b"K"); assert H.choose_and_load(l) is True and l.sent == b"Z"
    l = Link(b"E"); assert H.choose_and_load(l) is False
    l = Link(bytes([1, 2])); assert H.last_choice(l) == (1, 2) and l.sent == b"U"
