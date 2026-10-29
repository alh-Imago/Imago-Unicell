"""The carrier build's Mode A: `-s carrier --keep CORES` (project_assemble_v7.py, std_icm_generate_v2.py) keeps the named cores in the trimmed carrier in addition to the cores the design uses.
The design's own cores (Mode B) are still always kept; unknown names are refused; --keep outside -s carrier is refused; the carrier with extra cores still parses."""
import json, os, shutil, subprocess, sys, tempfile
import pytest
ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
for p in ("tools", "nano", os.path.join("nano", "examples"), "."):
    sys.path.insert(0, os.path.join(ROOT, p))
import std_icm_generate_v2 as SG

TREE = os.path.join(ROOT, "nano", "examples", "parallel_reduction_tree.icm-hier.json")
MAN = os.path.join(ROOT, "docs", "man", "tang-nano-20k.man.json")
ASM = os.path.join(ROOT, "tools", "project_assemble_v7.py")


def _gen(extra=()):
    d = tempfile.mkdtemp()
    try:
        SG.generate(TREE, d, family="carrier", result_io="output", extra_keep=extra)
        return json.load(open(os.path.join(d, "GRID.json"))), open(os.path.join(d, "carrier_sub.v")).read(), d
    except Exception:
        shutil.rmtree(d, ignore_errors=True)
        raise


def test_default_keeps_only_the_design_cores():
    g, _, d = _gen()
    shutil.rmtree(d, ignore_errors=True)
    assert g["keep"] == ["adder", "ram"] and g["keep_extra"] == []


def test_extra_cores_are_added_and_named_both_ways():
    g, v, d = _gen(("multiplier", "comparator"))
    try:
        assert g["keep"] == ["adder", "compare", "mul", "ram"]
        assert g["keep_extra"] == ["compare", "mul"]
        assert "CORE_MUL" in v and "CORE_COMPARE" in v
        assert "cores kept: " in v
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_extra_core_already_used_is_not_listed_as_extra():
    g, _, d = _gen(("adder", "ram"))
    shutil.rmtree(d, ignore_errors=True)
    assert g["keep"] == ["adder", "ram"] and g["keep_extra"] == []


def test_unknown_core_refused_with_the_valid_list():
    with pytest.raises(ValueError) as e:
        SG.parse_extra_keep("mul,foo")
    assert "foo" in str(e.value) and "choose from" in str(e.value)


def test_keep_outside_carrier_refused():
    with pytest.raises(ValueError):
        SG.generate(TREE, tempfile.mkdtemp(), family="std", result_io="output", extra_keep=("mul",))
    r = subprocess.run([sys.executable, ASM, "-s", "flex", "--icm", TREE, "--man", MAN, "--keep", "mul", "--output", os.path.join(tempfile.mkdtemp(), "x")], capture_output=True, text=True)
    assert r.returncode != 0 and "--keep applies only to -s carrier" in r.stderr


def test_assembler_cli_writes_the_kept_set():
    d = os.path.join(tempfile.mkdtemp(), "o")
    r = subprocess.run([sys.executable, ASM, "-s", "carrier", "--icm", TREE, "--man", MAN, "--tap-io", "output", "--keep", "mul", "--output", d], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    g = json.load(open(os.path.join(d, "GRID.json")))
    assert g["keep"] == ["adder", "mul", "ram"]


@pytest.mark.skipif(shutil.which("yosys") is None, reason="yosys not installed")
def test_carrier_with_extra_core_parses():
    import verilog_deps_v1 as D
    g, v, d = _gen(("mul",))
    try:
        files = [os.path.join(ROOT, f) if not os.path.isabs(f) else f for f in D.deps("unicell_vixen_v1", [os.path.join(ROOT, "fpga", "verilog")])]
        files = [f for f in files if not f.endswith("unicell_vixen_v1.v")]
        cmd = "read_verilog -sv %s %s; hierarchy -check -top unicell_vixen_v1m" % (" ".join(files), os.path.join(d, "carrier_sub.v"))
        r = subprocess.run(["yosys", "-q", "-p", cmd], capture_output=True, text=True)
        assert r.returncode == 0, (r.stdout + r.stderr)[-800:]
    finally:
        shutil.rmtree(d, ignore_errors=True)
