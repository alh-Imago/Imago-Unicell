"""The Kintex kit fpga/ypcb/hexn_speech/ in simulation: prebuild.py writes the chain and the ROM as plain Verilog, the kit top replays the 300 recordings of data/, and the number it counts as right after window 3 must equal data/EXPECTED.txt (the model's figure) and the PASS led must be on. Also checks that the generated Verilog contains no file reads (the card flow cannot be trusted to find data files). Needs iverilog: FAILS (does not skip) without it."""
import os, sys, subprocess, shutil, re
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", "..")); KIT = os.path.join(ROOT, "fpga", "ypcb", "hexn_speech")


def test_kit_replay_matches_model(tmp_path):
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is required"
    env = dict(os.environ, HEXN_REPO=ROOT)
    subprocess.run([sys.executable, "-I", os.path.join(KIT, "prebuild.py"), str(tmp_path)], check=True, env=env, capture_output=True)
    gen = (tmp_path / "gen_00_chain.v").read_text() + (tmp_path / "gen_01_rom.v").read_text()
    assert "$readmemh" not in re.sub(r"//[^\n]*", "", gen)          # comments may mention it; code may not
    exp = dict(l.split() for l in open(os.path.join(KIT, "data", "EXPECTED.txt")))
    subprocess.run(["iverilog", "-g2012", "-s", "tbk", "-o", str(tmp_path / "sim"), os.path.join(HERE, "hexn_speech_kit_v1_tb.v"), os.path.join(KIT, "hexn_speech.v"), str(tmp_path / "gen_00_chain.v"), str(tmp_path / "gen_01_rom.v")], check=True, capture_output=True)
    out = subprocess.run(["vvp", str(tmp_path / "sim")], capture_output=True, text=True, check=True).stdout
    m = re.search(r"KIT done=(\d) pass=(\d) correct=(\d+) total=(\d+)", out); assert m, out
    done, pas, correct, total = (int(x) for x in m.groups())
    assert done == 1 and total == int(exp["recordings"]) and correct == int(exp["correct"]) and pas == 1, out
