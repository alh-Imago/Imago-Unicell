"""tests/vm/test_hexn_flagtest_ring_v1.py - the flag-test ring: slot layout, per-slot flag and jump, first-row CRC valid in every slot. Uses the 3 Nov/4 Nov .fs files only if they exist (/tmp/hexfit/...); otherwise skipped."""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import pytest
import hexn_flagtest_ring_v1 as R, hexn_fs2bin_v2 as T

F7, F6, F5 = "/tmp/hexfit/v3hex7/hexn.fs", "/tmp/hexfit/v3hex6/hexn.fs", "/tmp/hexfit/v3hex5/hexn.fs"


def test_plan_layout():
    assert R.plan([0xee, 0x8c, 0xce]) == [(7, 0xcc, 1), (6, 0xee, 2), (5, 0xcc, 3), (6, 0x8c, 4), (5, 0xcc, 5), (6, 0xce, 6), (5, 0xcc, 0)]
    assert R.plan([0xee]) == [(7, 0xcc, 1), (6, 0xee, 2), (5, 0xcc, 0)]


@pytest.mark.skipif(not all(os.path.exists(f) for f in (F7, F6, F5)), reason="needs the built .fs files")
def test_image_headers_and_crc():
    img, info = R.build(F7, F6, F5, [0xee, 0x8c, 0xce]); assert len(img) == 7 * R.SLOT
    for k, kind, flag, nxt, ln in info:
        h = img[k * R.SLOT:k * R.SLOT + 0x50]
        assert h[0x16:0x18].hex() == "a5c3" and h[0x25] == flag and int.from_bytes(h[0x38:0x3c], "big") == nxt * R.SLOT
