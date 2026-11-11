"""tests/vm/test_hexn_chain_host_v3.py - the batching of tools/hexn_chain_host_v3.py on the full test set image (fpga/ypcb/hexn_speech/data_full/events.bin), no hardware and no simulator (11 Nov 2026):
the image splits into 1,079 recordings of 5 windows each; the batches cover every recording once and in order, and each fits the event RAM (32,768 bytes) and the result RAM (2,048 results);
EXPECTED.txt parses (936 right, per-digit counts add up); the kit's 300 recordings (fed the v1 way in the earlier tests) are all found among the full set, byte for byte."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_chain_host_v1 as C, hexn_chain_host_v2 as C2, hexn_chain_host_v3 as C3
FULL = os.path.join(ROOT, "fpga", "ypcb", "hexn_speech", "data_full"); KIT = os.path.join(ROOT, "fpga", "ypcb", "hexn_speech", "data")


def test_batches_and_expected():
    img = open(os.path.join(FULL, "events.bin"), "rb").read(); recs = C3.split_recordings(img); lab = C.hexwords(os.path.join(FULL, "lab.hex"))
    assert len(recs) == 1079 == len(lab) and b"".join(recs) == img and max(max(r[1:].replace(b"\xff", b"\x00")) for r in recs) < 192
    bt = C3.batches(recs); assert [r for b in bt for r in b] == recs
    assert all(sum(len(r) for r in b) <= C2.RAM_BYTES and C.NWIN * len(b) <= C2.RES_WORDS and b for b in bt)
    small = C3.batches(recs[:10], ram=400, res=15); assert [r for b in small for r in b] == recs[:10] and all(len(b) <= 3 and sum(len(r) for r in b) <= 400 for b in small) and len(small) > 3
    tot, per = C3.expected(os.path.join(FULL, "EXPECTED.txt"))
    assert tot == 936 == sum(v[0] for v in per.values()) and sum(v[1] for v in per.values()) == 1079 and sorted(per) == list(range(10))
    assert all(sum(1 for x in lab if x == c) == per[c][1] for c in per)
    kit = C3.split_recordings(C2.ram_image(C.recordings(os.path.join(KIT, "prog.hex")))); full = set(recs)
    assert len(kit) == 300 and all(k in full for k in kit)
