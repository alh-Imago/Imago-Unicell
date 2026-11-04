import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import hexn_flashimg_v1 as F
A = os.path.join(ROOT, 'fpga/build/unicell_tang_nano_20k_smoke_v2.fs')
B = os.path.join(ROOT, 'fpga/build/unit_cordic_v1/unit_top.fs')


def test_ring_of_two():
    img, info = F.build([A, B])
    assert len(img) == 0x200000
    assert img[0x25] == 0xcc and img[0x100025] == 0xcc
    assert img[0x38:0x3c] == bytes.fromhex('00100000')            # slot 0 -> slot 1
    assert img[0x100038:0x10003c] == bytes.fromhex('00000000')    # slot 1 -> slot 0
    assert img[0x16:0x20] == bytes.fromhex('a5c3060000000000081b')
    assert img[0x100016:0x100020] == bytes.fromhex('a5c3060000000000081b')


def test_ring_of_three_wraps():
    img, _ = F.build([A, A, B])
    assert [img[k * 0x100000 + 0x39] for k in range(3)] == [0x10, 0x20, 0x00]
