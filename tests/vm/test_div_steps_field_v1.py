"""Ledger #1077: K (quotient bits per clock) is a field of the divider's programming word, at the same bit position for every family.

The ICM word carries `steps` at bits 18..23 of the div record (0 = not set, the family default). Flex builds the cell with .STEPS(K) (checked here as real RTL,
several K); sub accepts only 32 and refuses the rest with the reason; the VM ignores it (its timing is data-driven). The LaTeX front end sets it for every
division cell (`div_steps=` / `--div-steps`). No Fmax or area claim is made here (see the #1072 sweep for measured sizes)."""
import json
import os
import re
import shutil
import sys
import tempfile

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (_HERE, os.path.join(_HERE, "..", "..", "nano"), os.path.join(_HERE, "..", "..", "tools")):
    sys.path.insert(0, _p)

import icm_v3  # noqa: E402
import latex_frontend_v1 as L  # noqa: E402
import target_capabilities_v1 as tc  # noqa: E402
import flex_rtl_harness_v1 as _h  # noqa: E402
from icm_v3 import IcmV3File  # noqa: E402

M32 = 0xFFFFFFFF
_VECS = [{"a": 100, "b": 7}, {"a": 5, "b": 0}, {"a": M32, "b": 3}, {"a": 0, "b": 4}, {"a": 1000, "b": 1000}, {"a": 7, "b": 100}, {"a": 4000000000, "b": 5}]


def test_the_field_sits_at_bits_18_to_23_and_round_trips():
    assert icm_v3._DIV_FIELDS["steps"] == (18, 23)
    for k in (0, 1, 4, 31, 32, 63):
        rec = icm_v3.IcmV3Record(cell_id="main.r", core=icm_v3.CORE_NAMES[icm_v3.SEL_DIV], core_config={"steps": k}, row=0, col=0)
        tmp = tempfile.mkdtemp()
        try:
            p = os.path.join(tmp, "x.icm")
            IcmV3File(name="x", records=[rec]).save(p)
            back = IcmV3File.load(p).records[0].core_config.get("steps", 0)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        assert back == k


def test_latex_sets_steps_on_every_division_cell_and_default_is_unset():
    r = L.compile_latex("a / b + c \\bmod d", div_steps=8)
    divs = [x for x in r.result.records if x.core == "div"]
    assert len(divs) == 2 and all(x.core_config["steps"] == 8 for x in divs)
    r0 = L.compile_latex("a / b")
    assert all("steps" not in (x.core_config or {}) for x in r0.result.records)
    for bad in (-1, 33, True, 2.5):
        with pytest.raises(L.LatexError):
            L.compile_latex("a / b", div_steps=bad)


def test_the_vm_ignores_steps():
    r = L.compile_latex("a / b", div_steps=7)
    assert [r.run(v) for v in _VECS] == [r.reference(v) for v in _VECS]


def test_capabilities_check():
    import types
    mk = lambda core, k: types.SimpleNamespace(cell_id="x", core=core, core_config={"steps": k}, addon_config=None)
    assert tc.check_records([mk("div", 4)], "flex") == [] and tc.check_records([mk("div", 4)], "std") == []
    assert tc.check_records([mk("div", 32)], "sub") == []
    assert any("32 bits per clock" in m for m in tc.check_records([mk("div", 4)], "sub"))
    assert any("1 to 32" in m for m in tc.check_records([mk("div", 33)], "flex"))
    assert any("only the divider" in m for m in tc.check_records([mk("adder", 4)], "flex"))


@pytest.mark.parametrize("k", [1, 4, 13, 32])
def test_flex_rtl_built_with_k_agrees_with_the_formula(k):
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED (this test must not skip silently)"
    r = L.compile_latex("a / b", div_steps=k)
    tmp = tempfile.mkdtemp(prefix="divk_")
    try:
        d, res = _h.build(tmp, "lx", r.result.records, 32)
        assert res.returncode == 0, (res.stderr or res.stdout)[:500]
        top = json.load(open(os.path.join(d, "ASSEMBLY.json")))["top"]
        text = open(os.path.join(d, top + ".v")).read()
        assert (f".STEPS({k})" in text) == True
        cmap = L._input_cells(r)
        streams = {}
        for name in sorted(set(re.findall(r"\bin_(\w+)_data", text))):
            cid = [c for c in cmap if c.replace(".", "_") == name]
            assert len(cid) == 1
            streams[name] = [v[cmap[cid[0]]] & M32 for v in _VECS]
        _, got = _h.run_level(d, streams, "plain", 3, settle=600, cycles=60000, width=32)
        (out,) = got.values()
        assert out == [r.reference(v) for v in _VECS], (k, out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_flex_refuses_k_above_the_built_width():
    r = L.compile_latex("a / b", div_steps=16)
    tmp = tempfile.mkdtemp(prefix="divkw_")
    try:
        p = os.path.join(tmp, "x.icm")
        IcmV3File(name="x", records=r.result.records).save(p)
        out = _h.cli("-s", "flex", "-w", "8", "--icm", p, "--output", os.path.join(tmp, "g"))
        assert out.returncode != 0 and "1 to 8" in (out.stderr + out.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_sub_refuses_k_other_than_32_and_accepts_32():
    tmp = tempfile.mkdtemp(prefix="divks_")
    try:
        for k, ok in ((4, False), (32, True)):
            r = L.compile_latex("a / b", div_steps=k)
            p = os.path.join(tmp, f"x{k}.icm")
            IcmV3File(name="x", records=r.result.records).save(p)
            out = _h.cli("-s", "sub", "--icm", p, "--output", os.path.join(tmp, f"g{k}"))
            assert (out.returncode == 0) == ok, (k, out.stderr or out.stdout)
            if not ok:
                assert "32 bits per clock" in (out.stderr + out.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_cli_flag_writes_steps():
    import subprocess
    tmp = tempfile.mkdtemp(prefix="divkc_")
    try:
        o = os.path.join(tmp, "x.icm")
        p = subprocess.run([sys.executable, os.path.join(_HERE, "..", "..", "nano", "latex_cli_v1.py"), "a / b", "--div-steps", "6", "-o", o], capture_output=True, text=True)
        assert p.returncode == 0, p.stderr
        assert [x.core_config["steps"] for x in IcmV3File.load(o).records if x.core == "div"] == [6]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
