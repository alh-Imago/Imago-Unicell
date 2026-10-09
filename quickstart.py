#!/usr/bin/env python3
"""quickstart.py -- first thing to run after `git clone` (ledger #1036 addendum 12).

    python3 quickstart.py            check what is installed, run a 10-second self-test, say what to do next
    python3 quickstart.py --composer open the composer / front panel in your browser (pure Python)
    python3 quickstart.py --full     also run the whole VM test suite (several minutes)
    python3 quickstart.py --install  one-stop install: makes a private Python environment (.venv in this folder) and installs everything pip can supply
                                     (numpy, llvmlite, pycparser, pytest and the YoWASP yosys / nextpnr / apycula bitstream tools), then runs the self-test.
                                     Add --dry-run to see the plan only, --venv DIR to put it somewhere else.

Without --install it changes nothing on your machine. Python 3.12+ is needed; everything else is only needed for the part of the project you want to use.
After --install every later quickstart run (and the build scripts it starts) uses the private environment automatically.
Two things pip cannot supply are listed with the command for your system: iverilog (simulation) and openFPGALoader (loading a bitstream onto the board)."""
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


PIP_PACKAGES = ["numpy", "pycparser", "llvmlite", "pytest", "yowasp-yosys", "yowasp-nextpnr-himbaechel-gowin", "apycula"]
DEFAULT_VENV = os.path.join(ROOT, ".venv")


def _venv_bin(venv):
    return os.path.join(venv, "Scripts" if os.name == "nt" else "bin")


def _venv_python(venv):
    return os.path.join(_venv_bin(venv), "python.exe" if os.name == "nt" else "python")


def _use_private_env():
    """If a private environment made by --install exists and we are not already inside it, re-run this script with it (so the checks and the build scripts see its tools)."""
    py = _venv_python(DEFAULT_VENV)
    if os.path.exists(py) and os.path.realpath(sys.prefix) != os.path.realpath(DEFAULT_VENV) and not os.environ.get("UNICELL_NO_VENV"):
        env = dict(os.environ, PATH=_venv_bin(DEFAULT_VENV) + os.pathsep + os.environ.get("PATH", ""), UNICELL_NO_VENV="1")
        sys.exit(subprocess.call([py] + sys.argv, env=env))
    if os.path.realpath(sys.prefix) == os.path.realpath(DEFAULT_VENV):
        os.environ["PATH"] = _venv_bin(DEFAULT_VENV) + os.pathsep + os.environ.get("PATH", "")


def _system_hints():
    """What pip cannot supply, with the command for this operating system (printed, never run: it needs administrator rights)."""
    if sys.platform.startswith("win"):
        return ["iverilog (simulation):    install Icarus Verilog from https://bleyer.org/icarus/ and tick 'add to PATH'",
                "openFPGALoader (loading):  download a release from https://github.com/trabucayre/openFPGALoader/releases and add it to PATH"]
    if sys.platform == "darwin":
        return ["iverilog (simulation):    brew install icarus-verilog", "openFPGALoader (loading):  brew install openfpgaloader"]
    return ["iverilog (simulation):    sudo apt install iverilog   (Debian / Ubuntu / Raspberry Pi OS)", "openFPGALoader (loading):  sudo apt install openfpgaloader   (or a release from https://github.com/trabucayre/openFPGALoader)"]


def install(venv, dry):
    print(f"One-stop install into {venv}\n")
    print("  1. make a private Python environment (nothing outside this folder is touched)")
    print("  2. pip install:", " ".join(PIP_PACKAGES))
    print("  3. run the self-test\n")
    if dry:
        print("(dry run: nothing was done)")
        return 0
    if sys.version_info < (3, 12):
        print("Python 3.12 or newer is needed: https://www.python.org/downloads/")
        return 1
    if not os.path.exists(_venv_python(venv)):
        r = subprocess.call([sys.executable, "-m", "venv", venv])
        if r:
            print("Could not make the environment. On Debian / Ubuntu try: sudo apt install python3-venv")
            return r
    py = _venv_python(venv)
    subprocess.call([py, "-m", "pip", "install", "--upgrade", "pip"])
    r = subprocess.call([py, "-m", "pip", "install"] + PIP_PACKAGES)
    if r:
        print("\npip could not install everything (needs internet). Packages tried:", " ".join(PIP_PACKAGES))
        return r
    print("\nInstalled. Still to get by hand, only if you need them:")
    for h in _system_hints():
        print("  " + h)
    print("\nRunning quickstart in the new environment ...\n")
    env = dict(os.environ, PATH=_venv_bin(venv) + os.pathsep + os.environ.get("PATH", ""), UNICELL_NO_VENV="1")
    return subprocess.call([py, os.path.join(ROOT, "quickstart.py")], env=env)


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
    ap.add_argument("--install", action="store_true", help="one-stop install into a private environment (.venv), then self-test")
    ap.add_argument("--dry-run", action="store_true", help="with --install: show the plan, do nothing")
    ap.add_argument("--venv", default=DEFAULT_VENV, help="with --install: where to put the private environment")
    a = ap.parse_args()
    if a.install:
        return install(os.path.abspath(a.venv), a.dry_run)
    _use_private_env()
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
        if any(n not in ("iverilog", "openFPGALoader", "arduino-cli or Arduino IDE", "yosys") for n, _, _ in missing):
            print("\nEasiest: python3 quickstart.py --install   (private environment; installs everything pip can supply)")
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
