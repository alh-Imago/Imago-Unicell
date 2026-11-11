"""The Kintex kit fpga/ypcb/hexn_speech2/ (v2 of the speech kit, with the JTAG count readout) in simulation: the replay runs to the end, then the 64-bit register is read with a capture and 64 shifts (BSCANE2 simulation model). After the replay finished the register must hold the magic word "SPCH", done = 1, pass = 1, total = 300, recordings started = 300 and the number correct of data/EXPECTED.txt (the model's figure, 262). A read taken while the replay still runs must show done = 0. Needs iverilog: FAILS (does not skip) without it."""
import os, sys, subprocess, shutil, re
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", "..")); KIT = os.path.join(ROOT, "fpga", "ypcb", "hexn_speech2"); DATA = os.path.join(ROOT, "fpga", "ypcb", "hexn_speech", "data")


def decode(v): return dict(correct=v & 0x1FF, total=(v >> 9) & 0x1FF, rec=(v >> 18) & 0x1FF, done=(v >> 27) & 1, pas=(v >> 28) & 1, zero=(v >> 29) & 7, magic=v >> 32)


def test_kit2_count_readout(tmp_path):
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is required"
    env = dict(os.environ, HEXN_REPO=ROOT)
    subprocess.run([sys.executable, "-I", os.path.join(KIT, "prebuild.py"), str(tmp_path)], check=True, env=env, capture_output=True)
    exp = dict(l.split() for l in open(os.path.join(DATA, "EXPECTED.txt")))
    subprocess.run(["iverilog", "-g2012", "-s", "tbk2", "-o", str(tmp_path / "sim"), os.path.join(HERE, "hexn_speech2_kit_tb.v"), os.path.join(KIT, "hexn_speech2.v"), os.path.join(ROOT, "rtl", "sim", "bscane2_model.v"),
                    str(tmp_path / "gen_00_chain.v"), str(tmp_path / "gen_01_rom.v")], check=True, capture_output=True)
    out = subprocess.run(["vvp", str(tmp_path / "sim")], capture_output=True, text=True, check=True).stdout
    e = decode(int(re.search(r"EARLY ([0-9a-f]+)", out).group(1), 16)); l = decode(int(re.search(r"LATE ([0-9a-f]+)", out).group(1), 16))
    assert e["magic"] == 0x53504348 and e["done"] == 0 and e["total"] < int(exp["recordings"]), (e, out)
    assert l["magic"] == 0x53504348 and l["zero"] == 0 and l["done"] == 1 and l["pas"] == 1, (l, out)
    assert l["total"] == l["rec"] == int(exp["recordings"]) and l["correct"] == int(exp["correct"]), (l, out)
