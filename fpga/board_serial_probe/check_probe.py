#!/usr/bin/env python3
"""check_probe.py -- ledger #1130: judge a capture of the serial_probe bitstreams.  python3 check_probe.py capture.bin [more.bin ...]
Counts frames received, valid (format + CRC-32 + the words the frame must carry), corrupt, missed frames (gaps in the 16-bit sequence between valid frames) and, for corrupt frames whose sequence number is readable, how many bytes differ from the frame that should have arrived."""
import re, sys, zlib
M = 0xFFFFFFFF
def mix(seq, k):
    x = (seq * 0x9E3779B1 + k * 0x85EBCA6B + 0x1234567) & M
    x ^= x >> 15
    x = (x * 0x2C1B3C6D) & M
    x ^= x >> 12
    return x & M
def frame(seq):
    body = "UCP seq=%04X d=%s" % (seq, ",".join("%08X" % mix(seq, k) for k in range(8)))
    return body + " crc=%08X\r\n" % (zlib.crc32(body.encode()) & M)
PAT = re.compile(rb"^UCP seq=([0-9A-F]{4}) d=((?:[0-9A-F]{8},){7}[0-9A-F]{8}) crc=([0-9A-F]{8})\r$")
def judge(path):
    data = open(path, "rb").read()
    lines = data.split(b"\n")
    ok = bad = 0; seqs = []; diffbytes = 0; partial = 0; bad_examples = []
    for ln in lines[1:-1] if len(lines) > 2 else []:      # the first and last pieces may be cut by the start/stop of the capture
        m = PAT.match(ln)
        good = False
        if m:
            seq = int(m.group(1), 16)
            body = ln[:ln.index(b" crc=")]
            if int(m.group(3), 16) == zlib.crc32(body) & M and ln + b"\n" == frame(seq).encode():
                ok += 1; seqs.append(seq); good = True
        if not good:
            bad += 1
            m2 = re.match(rb"^UCP seq=([0-9A-F]{4})", ln)
            if m2:
                exp = frame(int(m2.group(1), 16)).encode()
                got = ln + b"\n"
                diffbytes += sum(1 for a, b in zip(exp, got) if a != b) + abs(len(exp) - len(got))
            else:
                partial += 1
            if len(bad_examples) < 3:
                bad_examples.append(ln[:120])
    missed = sum(((b - a - 1) & 0xFFFF) for a, b in zip(seqs, seqs[1:]) if ((b - a) & 0xFFFF) < 1000)
    res = dict(file=path, bytes=len(data), frames_valid=ok, frames_corrupt=bad, corrupt_unreadable_header=partial, differing_bytes_in_corrupt=diffbytes, missed_frames_between_valid=missed,
               first_seq=(seqs[0] if seqs else None), last_seq=(seqs[-1] if seqs else None))
    return res, bad_examples
if __name__ == "__main__":
    worst = 0
    for p in sys.argv[1:]:
        r, ex = judge(p)
        print(" ".join("%s=%s" % kv for kv in r.items()))
        for e in ex:
            print("   corrupt example:", e)
        verdict = "CLEAN" if r["frames_valid"] > 20 and r["frames_corrupt"] == 0 and r["missed_frames_between_valid"] == 0 else ("SILENT" if r["bytes"] == 0 else "DEGRADED")
        print("   verdict:", verdict)
        worst = max(worst, 0 if verdict == "CLEAN" else 1)
    sys.exit(worst)
