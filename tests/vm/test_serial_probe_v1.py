"""Ledger #1130: the serial probe's host checker tells a clean capture from loss and corruption, and the Verilog frames equal the host's frames."""
import os, sys, tempfile
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path.insert(0, os.path.join(ROOT, "tools"))
import board_serial_probe_v1 as P
ns = {}
exec(compile(P.CHECK, "check_probe", "exec"), ns)


def cap(frames, mut=None):
    d = b"".join(f.encode() for f in frames)
    return mut(d) if mut else d


def judge(data):
    p = tempfile.mktemp(suffix=".bin")
    open(p, "wb").write(data)
    return ns["judge"](p)[0]


def test_clean():
    r = judge(b"JUNK" + cap(P.frame(s) for s in range(100, 160)))     # a cut first piece is tolerated
    assert r["frames_valid"] >= 58 and r["frames_corrupt"] == 0 and r["missed_frames_between_valid"] == 0


def test_a_flipped_bit_is_a_corrupt_frame_with_one_differing_byte():
    frames = [P.frame(s) for s in range(60)]
    d = bytearray(cap(frames))
    pos = sum(len(f) for f in frames[:30]) + 20          # inside frame 30's data
    d[pos] ^= 0x01
    r = judge(bytes(d))
    assert r["frames_corrupt"] == 1 and r["differing_bytes_in_corrupt"] == 1


def test_a_lost_byte_and_a_lost_frame_are_counted():
    frames = [P.frame(s) for s in range(60)]
    d = bytearray(cap(frames[:20] + frames[22:]))        # two frames missing
    r = judge(bytes(d))
    assert r["missed_frames_between_valid"] == 2
    d2 = bytearray(cap(frames)); del d2[sum(len(f) for f in frames[:10]) + 40]       # one byte dropped
    r2 = judge(bytes(d2))
    assert r2["frames_corrupt"] >= 1


def test_the_word_mix_and_crc_are_the_documented_ones():
    import zlib
    f = P.frame(0)
    assert f.startswith("UCP seq=0000 d=ED22D7CD,09E60DB5") and f.rstrip("\r\n").endswith("crc=%08X" % (zlib.crc32(f[:f.index(" crc=")].encode()) & 0xFFFFFFFF))
