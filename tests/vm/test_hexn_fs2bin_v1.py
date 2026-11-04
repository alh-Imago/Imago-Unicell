import os, subprocess, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FS = os.path.join(ROOT, 'fpga/build/unicell_tang_nano_20k_smoke_v2.fs')


def test_convert_and_patch_jump():
    with tempfile.TemporaryDirectory() as t:
        o = os.path.join(t, 'a.bin')
        r = subprocess.run([sys.executable, os.path.join(ROOT, 'tools/hexn_fs2bin_v1.py'), FS, o, '--jump', '0x200000'],
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        b = open(o, 'rb').read()
        assert len(b) == 577178                      # packed size measured earlier
        assert b[0x16:0x20] == bytes.fromhex('a5c3060000000000081b')
        assert b[0x34:0x3c] == bytes.fromhex('d200ffff00200000')
