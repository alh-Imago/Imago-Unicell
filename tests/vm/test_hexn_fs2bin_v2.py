import os, subprocess, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import hexn_fs2bin_v2 as T
FS = os.path.join(ROOT, 'fpga/build/unicell_tang_nano_20k_smoke_v2.fs')


def test_crc_model_verifies_and_repairs():
    rows = T.read_lines(FS)
    _, c, s = T.crc_of_first_row(rows)
    assert c == s                                   # model reproduces the stored CRC
    b, j, old, fixed = T.convert(FS, 0x200000, [(0x25, 0xcc)])
    assert fixed and b[0x25] == 0xcc and b[j:j + 4] == bytes.fromhex('00200000')
    b0, _, _, f0 = T.convert(FS, 0x200000, [])
    assert not f0                                   # jump patch alone needs no CRC repair
