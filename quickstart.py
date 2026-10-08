#!/usr/bin/env python3
"""quickstart.py -- first thing to run after `git clone` (ledger #1036 addendum 12).

    python3 quickstart.py            check what is installed, run a 10-second self-test, say what to do next
    python3 quickstart.py --composer open the composer / front panel in your browser (pure Python)
    python3 quickstart.py --full     also run the whole VM test suite (several minutes)

It changes nothing on your machine. Python 3.12+ is needed; everything else is only needed for the part of the project you want to use."""
import argparse
import importlib
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))

# (what it is, how to test for it, which jobs need it, how to get it)
NEED = [
    ("Python 3.12+", lambda: sys.version_info >= (3, 12), "everything", "https://www.python.org/downloads/"),
    ("pytest", lambda: _py("pytest"), "tests", "pip install pytest"),
    ("numpy", lambda: _py("numpy"), "the VM", "pip install numpy"),
    ("llvmlite + pycparser", lambda: _py("llvmlite") and _py("pycparser"), "the C / LLVM front ends", "pip install llvmlite pycparser"),
    ("iverilog", lambda: shutil.which("iverilog"), "hardware simulation (without it tests SKIP, which looks like a pass)", "sudo apt install iverilog"),
    ("yosys", lambda: shutil.which("yosys"), "size checks", "sudo apt install yosys"),
    ("yowasp yosys + nextpnr + apycula", lambda: shutil.which("yowasp-yosys") and shutil.which("yowasp-nextpnr-himbaechel-gowin") and shutil.which("gowin_pack"),
     "BUILDING a Tang Nano bitstream", "pip install --break-system-packages yowasp-yosys yowasp-nextpnr-himbaechel-gowin apycula"),
    ("openFPGALoader", lambda: shutil.which("openFPGALoader"), "LOADING a bitstream onto the Tang Nano 20K", "sudo apt install openfpgaloader  (or see its project page)"),
    ("arduino-cli or Arduino IDE", lambda: shutil.which("arduino-cli"), "the ESP32 sketches (the IDE also works)", "https://arduino.github.io/arduino-cli/"),
]


def _py(mod):
    try:
        importlib.import_module(mod)
        return True
    except Exception:
        return False


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--composer", action="store_true", help="open the front panel (composer page) in a browser")
    ap.add_argument("--full", action="store_true", help="also run the whole VM test suite")
    a = ap.parse_args()
    if a.composer:
        os.execv(sys.executable, [sys.executable, os.path.join(ROOT, "nano", "frontend_v1.py")])
    print("Imago UniCell quickstart\n")
    missing = []
    for name, test, job, how in NEED:
        ok = bool(test())
        print(f"  [{'ok' if ok else '--'}] {name:34s} {job}")
        if not ok:
            missing.append((name, job, how))
    if missing:
        print("\nNot installed (only matters for the job named):")
        for name, job, how in missing:
            print(f"  {name}: {how}")
    print("\nSelf-test: the small unit (SD card + SPI bridge + two example designs) in simulation ...")
    if not shutil.which("iverilog"):
        print("  skipped: iverilog is not installed (see above)")
        code = 1
    else:
        tests = ["tests/vm/test_unit_designs_v1.py", "tests/vm/test_unit_bringup_v1.py"]
        code = subprocess.call([sys.executable, "-m", "pytest", "-q", "-x"] + tests, cwd=ROOT)
        print("  PASS" if code == 0 else "  FAILED (send the output above)")
    if a.full:
        code |= subprocess.call([sys.executable, "-m", "pytest", "-q", "tests/vm"], cwd=ROOT)
    print("""
What next (pick a job):
  see and edit designs      python3 quickstart.py --composer
  run a design on a board   docs/unit_bringup_guide.md   (Tang Nano 20K + ESP32; ready-made bitstream in fpga/build/unit_cordic_v1/)
  control the board by WiFi tools/esp32/unicell_unit_web/  (WiFi section of the same guide)
  build a bitstream         python3 tools/sd_unit_top_v1.py --icm nano/examples/<design>.icm-hier.json --output build/unit
                            tools/gowin_sizing/build_unit_bitstream.sh build/unit
  read the whole story      README.md, points/INDEX.md, current/latest.md""")
    return code


if __name__ == "__main__":
    sys.exit(main())
