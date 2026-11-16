#!/usr/bin/env python3
"""ddr3test.py - read and write test of the far RAM from the host, to tell a marginal DDR3 lane or a wrapper bug from a pool bug.
  python3 ddr3test.py jtag [words]          (words: how many words from address 0, default 2048 = 128 lines of 16 words; the far RAM window is 2M words)
Tests, each over the same words: 1 a pseudo-random pattern, 2 its complement (a stuck bit shows here), 3 the first pattern again, then read twice (a read
that changes between two reads is a timing fault, not a write fault), 4 words at addresses 2**k (a wrong address bit shows as an alias).
Errors are reported per byte of the 64-byte line (word a is slot a % 16 of line a // 16, byte b of the word is line byte 4 * slot + b) and per bit.
Exit code 0 = no error at all.  Uses the host commands 'w' and 'r' of the bridge (board version 10 and up); io= lets tests pass a model board."""
import sys, time
import host_sc as hs, sdt_host as H


def pattern(a, which):
    x = (a * 0x9E3779B1 + 0x7F4A7C15) & 0xFFFFFFFF
    x ^= x >> 15; x = (x * 0x2C1B3C6D) & 0xFFFFFFFF; x ^= x >> 12
    return x if which == 0 else (~x & 0xFFFFFFFF)


def main(port, words=2048, io=None, say=print):
    b = io if io is not None else hs.Board(port)
    v = b.version(); say('board version %d' % v['version'])
    if v['version'] < 10: say('not a far-RAM board'); return 2

    def put(c): b.s.write(c); b.s.flush()
    def wr(addrs, f):
        for a in addrs: b.s.write(H.c_w(a, f(a)))
        b.s.flush(); time.sleep(0.3)
    def rd(a): put(H.c_r(a)); return H.dec_r(b._rd(4))
    total_bad = 0

    def report(name, got, want, addrs):
        nonlocal total_bad
        bad = [(a, want[a], got[a]) for a in addrs if got[a] != want[a]]
        total_bad += len(bad)
        if not bad: say('%-46s ok (%d words)' % (name, len(addrs))); return []
        bylb, bybit = {}, [0] * 32
        for a, w, g in bad:
            x = w ^ g
            for k in range(4):
                if (x >> (8 * k)) & 0xFF: bylb[4 * (a % 16) + k] = bylb.get(4 * (a % 16) + k, 0) + 1
            for k in range(32):
                if (x >> k) & 1: bybit[k] += 1
        say('%-46s FAIL: %d of %d words wrong' % (name, len(bad), len(addrs)))
        say('   line bytes with errors (byte: count): ' + ', '.join('%d: %d' % (k, bylb[k]) for k in sorted(bylb)))
        say('   word bits with errors (bit: count): ' + ', '.join('%d: %d' % (k, bybit[k]) for k in range(32) if bybit[k]))
        for a, w, g in bad[:6]: say('   word %#x wrote %08x read %08x xor %08x' % (a, w, g, w ^ g))
        # where the wrong words sit: lost whole groups point to the write path, scattered bits to a lane
        say('   wrong words in aligned groups of 4 (word address / 4): ' + ', '.join('%#x' % k for k in sorted({a // 4 for a, _, _ in bad})[:16]))
        if name.endswith('complement of A'):
            say('   wrong word equals pattern A (the old value, so the new write never showed): %d of %d' % (sum(1 for a, w, g in bad if g == pattern(a, 0)), len(bad)))
        return [a for a, _, _ in bad]

    addrs = list(range(words))
    t0 = time.time()
    for which, label in ((0, 'pattern A'), (1, 'complement of A'), (0, 'pattern A again')):
        wr(addrs, lambda a, w=which: pattern(a, w))
        want = {a: pattern(a, which) for a in addrs}
        got = {a: rd(a) for a in addrs}
        bad_a = report('write + read: ' + label, got, want, addrs)
        if bad_a:
            # follow-up: read the wrong words again (a read fault changes, a lost write does not), then write each one alone and read it back
            again = {a: rd(a) for a in bad_a}
            fixed = [a for a in bad_a if again[a] == want[a]]
            say('   read again: %d of %d now right  (right = the first read was wrong, the write had landed; still wrong = the write was lost)' % (len(fixed), len(bad_a)))
            alone = 0
            for a in bad_a:
                wr([a], lambda x, w=which: pattern(x, w))
                if rd(a) == want[a]: alone += 1
            say('   written one at a time, then read: %d of %d right  (right = the fault depends on write speed or order, not on the address)' % (alone, len(bad_a)))
        if which == 0 and label == 'pattern A again':
            got2 = {a: rd(a) for a in addrs}
            changed = [a for a in addrs if got2[a] != got[a]]
            total_bad += len(changed)
            say('%-46s %s' % ('read the same words twice', 'ok' if not changed else 'FAIL: %d words changed between two reads, first at %#x' % (len(changed), changed[0])))
    ks = [0] + [1 << k for k in range(21)]
    wr(ks, lambda a: 0xA5000000 ^ (a * 0x01010101 & 0x00FFFFFF) ^ 0x1234)
    want = {a: 0xA5000000 ^ (a * 0x01010101 & 0x00FFFFFF) ^ 0x1234 for a in ks}
    report('addresses 0 and 2**k (alias check)', {a: rd(a) for a in ks}, want, ks)
    say('%s in %.1f s' % ('ALL OK' if not total_bad else '%d wrong words in all' % total_bad, time.time() - t0))
    return 0 if not total_bad else 1


if __name__ == '__main__':
    p = sys.argv[1] if len(sys.argv) > 1 else 'jtag'
    sys.exit(main(p, int(sys.argv[2]) if len(sys.argv) > 2 else 2048))
