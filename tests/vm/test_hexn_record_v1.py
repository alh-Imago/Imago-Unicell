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


def test_sketch_header_agrees_with_reference():
    """The C++ header the ESP32 sketch includes (hexn_record.h) is compiled on the PC and must give the same code as the Python reference on valid and damaged records of every kind."""
    import shutil, subprocess, tempfile
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    assert shutil.which("g++"), "g++ is REQUIRED"
    d = tempfile.mkdtemp(prefix="hexnrec_"); exe = os.path.join(d, "h")
    c = subprocess.run(["g++", "-O1", "-o", exe, os.path.join(root, "tests", "hexn_record_host.cpp")], capture_output=True, text=True); assert c.returncode == 0, c.stderr[:1500]
    rnd = random.Random(9); n_checked = 0

    def cpp(rec, kind, sid):
        p = os.path.join(d, "r.txt"); open(p, "w").write("\n".join("%08x" % (w & H.M32) for w in rec) + "\n")
        return int(subprocess.run([exe, p, str(kind), str(sid)], capture_output=True, text=True).stdout)

    for k, (cap, wd) in H.KINDS.items():
        if k == 7: pass
        base = H.pack(k, [rnd.getrandbits(wd) for _ in range(cap // 2)], 0x55)
        cases = [list(base), base[:-1], base + [0], base[:4], []]
        for _ in range(40):
            b = list(base); b[rnd.randrange(len(b))] ^= 1 << rnd.randrange(32); cases.append(b)
            b = list(base); b[rnd.randrange(len(b) - 1)] ^= 1 << rnd.randrange(32); cases.append(fix(b))
        for rec in cases:
            for want, sid in ((k, 0x55), (k, 0x56), (0, 0x55), ((k % 7) + 1, 0x55)):
                got = cpp(rec, want, sid); exp = H.verify(rec, want or None, sid)[0]
                assert got == exp, (k, want, sid, got, exp); n_checked += 1
    assert n_checked > 1000
