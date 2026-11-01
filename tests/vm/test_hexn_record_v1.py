"""tests/vm/test_hexn_record_v1.py -- Hex-N guarded record v1 (host side reference, 1 Nov 2026): round trip for every kind, each refusal code (1 to 5) with only that fault present, and that no single flipped bit anywhere in a record is accepted."""
import os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "tools"))
import hexn_record_v1 as H  # noqa: E402


def fix(r): r[-1] = sum(r[:-1]) & H.M32; return r


def test_round_trip_all_kinds():
    rnd = random.Random(3)
    for k, (cap, wd) in H.KINDS.items():
        for n in (1, cap // 2, cap):
            p = [rnd.getrandbits(wd) for _ in range(n)]; c, q = H.verify(H.pack(k, p, 0x1234), k, 0x1234); assert c == 0 and q == p, (k, n, c)


def test_each_refusal_code():
    p = list(range(1, 9)); r = H.pack(6, p, 7)
    b = list(r); b[0] ^= 1 << 20; assert H.verify(fix(b), 6, 7)[0] == 1                       # magic
    b = list(r); b[0] = (b[0] & ~0xFF) | 9; assert H.verify(fix(b), 6, 7)[0] == 1             # unknown kind
    assert H.verify(r, 5, 7)[0] == 1                                                         # a record of another kind than wanted
    b = list(r); b[1] = (8 << 16) | (32 << 8); assert H.verify(fix(b), 6, 7)[0] == 2         # wrong entry width
    b = H.pack(4, [1] * 8, 0); b[1] = (65 << 16) | (8 << 8); assert H.verify(fix(b), 4)[0] == 2   # count above the capacity
    b = list(r); b[5] ^= 1; assert H.verify(b, 6, 7)[0] == 3                                 # checksum only
    assert H.verify(r[:-3], 6, 7)[0] == 4 and H.verify(r + [0], 6, 7)[0] == 4 and H.verify([], 6, 7)[0] == 4      # truncated, too long, empty
    b = list(r); b[4] |= 1 << 20; assert H.verify(fix(b), 6, 7)[0] == 4                      # a stray bit above the 16-bit width, valid checksum
    assert H.verify(r, 6, 8)[0] == 5                                                         # other structure
    assert H.verify(H.pack(6, p, 7), 6, 7)[0] == 0


def test_no_single_bit_flip_accepted():
    rnd = random.Random(5)
    for k in (3, 6, 7):
        cap, wd = H.KINDS[k]; r = H.pack(k, [rnd.getrandbits(wd) for _ in range(cap // 2)], 0xBEEF)
        for i in range(len(r)):
            for bit in range(32):
                b = list(r); b[i] ^= 1 << bit; assert H.verify(b, k, 0xBEEF)[0] != 0, (k, i, bit)
