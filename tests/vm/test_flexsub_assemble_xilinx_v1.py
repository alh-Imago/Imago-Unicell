"""Ledger #1251: the Flex-Sub assembler reads the Xilinx card's MAN build section and writes an openXC7 project (top, .sv cells, .xdc, Makefile); it refuses a Xilinx MAN without one."""
import json
import os
import shutil
import sys
import tempfile

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import flexsub_assemble_v1 as fa  # noqa: E402

MAN = os.path.join(ROOT, "docs", "man", "kintex7-ypcb00338.man.json")


def test_xilinx_project_written():
    out = tempfile.mkdtemp()
    try:
        r = fa.assemble_flexsub("flex", "adder", 4, out, man_path=MAN)
        top = r["top"]
        assert r["flow"] == "openxc7"
        names = set(os.listdir(out))
        assert {f"{top}.v", f"{top}.xdc", "Makefile", "ASSEMBLY.json"} <= names
        assert not any(n.endswith(".ys") or n == "build.sh" for n in names)       # no Gowin script
        assert all(n.endswith(".sv") for n in names if n not in (f"{top}.v", f"{top}.xdc", "Makefile", "ASSEMBLY.json", "kit.json"))
        v = open(os.path.join(out, f"{top}.v")).read()
        assert "input  wire CLK" in v and "output wire LED2" in v and "BTN_RST_N" in v and "synth_gowin" not in v
        x = open(os.path.join(out, f"{top}.xdc")).read()
        assert "AA28" in x and "P30" in x and "M30" in x and "N30" in x and "20.000" in x
        mk = open(os.path.join(out, "Makefile")).read()
        assert "PART    = xc7k480tffg1156-1" in mk and "include ../openXC7.mk" in mk and f"PROJECT = {top}" in mk
    finally:
        shutil.rmtree(out)


def test_xilinx_man_without_build_refused():
    man = json.load(open(MAN))
    del man["synthesis"]["build"]
    d = tempfile.mkdtemp()
    try:
        p = os.path.join(d, "m.json")
        json.dump(man, open(p, "w"))
        with pytest.raises(ValueError, match="no build flow"):
            fa.assemble_flexsub("flex", "adder", 2, os.path.join(d, "o"), man_path=p)
    finally:
        shutil.rmtree(d)


def test_gowin_output_unchanged():
    out = tempfile.mkdtemp()
    try:
        r = fa.assemble_flexsub("flex", "adder", 4, out, man_path=os.path.join(ROOT, "docs", "man", "tang-nano-20k.man.json"))
        assert "flow" not in r and os.path.exists(os.path.join(out, "build.sh"))
        assert "input  wire BOARD_CLK" in open(os.path.join(out, r["top"] + ".v")).read()
    finally:
        shutil.rmtree(out)


def test_flow_resolution_and_export_only():
    import tempfile
    a10 = os.path.join(ROOT, "docs", "man", "mustang-f100-a10.man.json")
    assert fa.resolve_flow(None) == "gowin-apicula"
    assert fa.resolve_flow(fa.load_man_flexsub(a10)) == "export-only"                 # vendor default for the existing Arria 10 card
    assert fa.resolve_flow(fa.load_man_flexsub(os.path.join(ROOT, "docs", "man", "tang-nano-20k.man.json"))) == "gowin-apicula"
    assert fa.resolve_flow(fa.load_man_flexsub(MAN)) == "openxc7"                      # stated in the MAN itself
    out = tempfile.mkdtemp()
    try:
        r = fa.assemble_flexsub("flex", "adder", 4, out, man_path=a10)
        names = set(os.listdir(out))
        assert r["flow"] == "export-only" and "README.md" in names and "kit.json" in names
        assert not any(n.endswith((".ys", ".cst", ".xdc")) or n in ("build.sh", "Makefile") for n in names)
        assert json.load(open(os.path.join(out, "kit.json")))["flow"] == "export-only"
    finally:
        shutil.rmtree(out)


def test_unknown_flow_refused_and_new_card_needs_only_a_man(tmp_path):
    man = json.load(open(MAN))
    man["synthesis"]["build"]["flow"] = "quartus-magic"
    p = tmp_path / "m.json"
    json.dump(man, open(p, "w"))
    with pytest.raises(ValueError, match="unknown build flow"):
        fa.assemble_flexsub("flex", "adder", 2, str(tmp_path / "o"), man_path=str(p))
    man["synthesis"]["build"]["flow"] = "export-only"                                  # the same card, declared closed: a Verilog folder, nothing else
    json.dump(man, open(p, "w"))
    r = fa.assemble_flexsub("flex", "adder", 2, str(tmp_path / "o2"), man_path=str(p))
    assert r["flow"] == "export-only"
