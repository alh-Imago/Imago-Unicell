"""tests/vm/test_dsl_family_v1.py -- ledger #1115: `family: flex|sub` (and `io_name:`) on a DSL `place`; `dsl_cli_v1.py --target`. A program that uses `family:` is compiled with the VIX backend into ICM-VIX
(one placement per family), which the Flex-Sub assembler splits and bridges (#1114). Needs iverilog for the end-to-end test (fails loudly without it, #965)."""
import json
import os
import shutil
import subprocess
import sys
import tempfile

import pytest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
for sub in ("tools", "nano"):
    sys.path.insert(0, os.path.join(ROOT, sub))

UC = os.path.join(ROOT, "nano", "examples", "mixed_flex_sub_flex_v1.uc")
TB = os.path.join(ROOT, "sub", "verilog", "tb_mixed_flex_sub_flex_v1.v")
CLI = [sys.executable, os.path.join(ROOT, "nano", "dsl_cli_v1.py")]
ASM = [sys.executable, os.path.join(ROOT, "tools", "project_assemble_v1.py")]


def parse(src):
    import dsl_lexer_v1 as lx
    import dsl_parser_v1 as ps
    t = lx.tokenize(src)
    toks = t[0] if isinstance(t, tuple) else t
    prog, d = ps.parse_source(toks)
    assert prog is not None and not [x for x in d if x.severity == "error"], d
    return prog


def test_the_example_compiles_to_one_placement_per_family():
    from vix_compiler_v1 import compile_program_ir_vix
    icm, d = compile_program_ir_vix(parse(open(UC).read()), target="flex")
    assert icm is not None, d
    assert sorted((p.instance, p.family) for p in icm.placements) == [("flex_part", "flex"), ("sub_part", "sub")]
    recs, _ = icm.flatten()
    assert len(recs) == 12 and {r.io_name for r in recs if r.io_name} == {"x_in", "y_out"}


def test_a_program_without_family_is_compiled_exactly_as_before():
    from vix_compiler_v1 import compile_program_ir_vix
    src = "program p {\n    place r as ram_constant at (0, 0) {\n        out: e\n        init_data: 7\n    }\n}\n"
    icm, d = compile_program_ir_vix(parse(src))
    assert icm is not None and [(p.instance, p.family) for p in icm.placements] == [("main", None)]


def test_a_bad_family_is_refused_with_its_reason():
    from vix_compiler_v1 import compile_program_ir_vix
    src = "program p {\n    place r as ram_constant at (0, 0) {\n        out: e\n        init_data: 7\n        family: nano\n    }\n}\n"
    icm, d = compile_program_ir_vix(parse(src))
    assert icm is None and any("not 'flex' or 'sub'" in x.problem for x in d)


def test_a_block_is_checked_against_its_own_familys_abilities():
    from vix_compiler_v1 import compile_program_ir_vix
    src = "program p {\n    place a as adder at (1, 1) {\n        in_a: w\n        in_b: n\n        out: e\n        second_output: 1\n        family: %s\n    }\n}\n"
    ok, _ = compile_program_ir_vix(parse(src % "flex"), target="std")        # flex can deliver the carry, whatever the default target
    bad, d = compile_program_ir_vix(parse(src % "sub"), target="flex")        # sub cannot
    assert ok is not None and bad is None and any("second_output" in x.problem for x in d)


def test_the_command_line_routes_by_the_parsed_program_not_by_comments(tmp_path):
    plain = tmp_path / "plain.uc"
    plain.write_text("# a comment that says family: sub must not switch the backend\nprogram p {\n    place r as ram_constant at (0, 0) {\n        out: e\n        init_data: 7\n    }\n}\n")
    r = subprocess.run(CLI + [str(plain), "-o", str(tmp_path / "plain.icm")], capture_output=True, text=True)
    assert r.returncode == 0 and "VIX backend" not in r.stdout
    r2 = subprocess.run(CLI + [UC, "-o", str(tmp_path / "m.icm-hier.json")], capture_output=True, text=True)
    assert r2.returncode == 0 and "families: flex, sub" in r2.stdout


def test_dsl_to_assembler_to_simulation_end_to_end(tmp_path):
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is required (see current/START.md)"
    hier = tmp_path / "m.icm-hier.json"
    assert subprocess.run(CLI + [UC, "--target", "flex", "-o", str(hier)], capture_output=True, text=True).returncode == 0
    out = tmp_path / "out"
    r = subprocess.run(ASM + ["-s", "flex", "--icm", str(hier), "--top", "mix", "--output", str(out)], capture_output=True, text=True)
    assert r.returncode == 0 and "Bridges inserted: 2" in r.stdout, r.stderr[-400:]
    srcs = [str(out / f) for f in os.listdir(out) if f.endswith(".v")]
    exe = str(tmp_path / "t.vvp")
    c = subprocess.run(["iverilog", "-g2012", "-DTOP=mix", "-DN=30", "-DSTALL=1", "-o", exe, TB] + srcs, capture_output=True, text=True)
    assert c.returncode == 0, c.stderr[-400:]
    o = subprocess.run(["vvp", exe], capture_output=True, text=True, timeout=300).stdout
    vals = [int(l.split()[2]) for l in o.splitlines() if l.startswith("O ")]
    assert vals == [100 + 7 * k + 1239 for k in range(30)]


def test_the_composer_and_workbench_read_the_dsl_output(tmp_path):
    import flex_layout_view_v1 as flv
    import workbench_v1 as w
    hier = tmp_path / "m.icm-hier.json"
    assert subprocess.run(CLI + [UC, "-o", str(hier)], capture_output=True, text=True).returncode == 0
    c = w.WorkbenchController()
    r = c.load_icm_vix(str(hier))
    assert r["ok"] and r["families"] == ["flex", "sub"]
