"""tests/vm/test_vixen_tools_v1.py -- ledger #1105: the tool chain knows VIXeN. The join pass, the "vixen" compile target, the capability table and the assembler's `--shell vixen`."""
import os
import shutil
import subprocess
import sys
import tempfile

import pytest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
for sub in ("tools", "nano", os.path.join("nano", "examples")):
    sys.path.insert(0, os.path.join(ROOT, sub))
import join_pass_v1 as J  # noqa: E402
import looped_cordic_v1 as L  # noqa: E402
import target_capabilities_v1 as TC  # noqa: E402
from icm_v3 import IcmV3Record as Rec  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402


def test_join_pass_marks_exactly_the_adders_a_fixed_constant_feeds():
    recs = L.build_records(join=False)
    changed = J.apply(recs)
    hand = L.build_records(join=True)
    assert sorted(changed) == sorted(r.cell_id for r in hand if r.core == "adder")
    by = {r.cell_id: r.core_config for r in recs}
    assert all(by[r.cell_id].get("join_mode") == 1 for r in hand if r.core == "adder")


def test_join_pass_result_runs_the_cordic_in_the_vm():
    recs = L.build_records(join=False)
    J.apply(recs)
    g = SuperGrid(recs)
    for _ in range(L.SETTLE_TICKS):
        g.tick()
    inp = next(r for r in recs if r.io_name == "z_input")
    g.inject(inp.row, inp.col, L.Z0)
    assert [v for _, v in L.run_steps(g, 20)] == L.model(20)


def test_join_pass_leaves_other_cells_alone():
    ram = lambda cid, r, c, fixed, dm: Rec(cell_id=cid, row=r, col=c, core="ram", core_config={"fixed_mode": fixed, "downstream_mask": dm}, addon_config={}, io_name=None, preload_value=None)
    add = lambda cid, r, c, up, extra=None: Rec(cell_id=cid, row=r, col=c, core="adder", core_config=dict({"upstream_mask": up, "downstream_mask": ["E"]}, **(extra or {})), addon_config={}, io_name=None, preload_value=None)
    recs = [ram("k", 0, 0, 1, ["E"]), add("a_const", 0, 1, ["W", "S"]),                  # fixed constant on W: join
            ram("p", 2, 0, 0, ["E"]), add("a_plain", 2, 1, ["W", "S"]),                   # one-shot source: untouched
            ram("k2", 4, 0, 1, ["E"]), add("a_one_face", 4, 1, ["W"]),                    # one upstream face: untouched
            ram("k3", 6, 0, 1, ["E"]), add("a_set", 6, 1, ["W", "S"], {"join_mode": 0})]  # explicit value kept
    assert J.apply(recs) == ["a_const"]
    cfg = {r.cell_id: r.core_config for r in recs}
    assert cfg["a_plain"].get("join_mode") is None and cfg["a_one_face"].get("join_mode") is None and cfg["a_set"]["join_mode"] == 0


def test_capabilities_vixen_has_join_and_the_older_targets_refuse_it():
    r = [Rec(cell_id="a", row=0, col=0, core="adder", core_config={"upstream_mask": ["W", "S"], "downstream_mask": ["E"], "join_mode": 1}, addon_config={}, io_name=None, preload_value=None)]
    assert TC.check_records(r, "vixen") == [] and TC.check_records(r, "flex") == []
    assert TC.check_records(r, "std") and TC.check_records(r, "sub")
    assert TC.check_records(r, None) == []


def test_compile_target_vixen_calls_the_pass_and_other_targets_do_not():
    import vix_dag_dispatcher_v1 as D
    ins = [D.DagInstr(name="t1", opcode="add", operands=[D.DagOperand(kind="dynamic"), D.DagOperand(kind="const", value=5)])]
    for tgt in (None, "std", "vixen"):                       # the dispatcher's constants are one-shot, so nothing to join: the output is the same and valid for every target
        icm, *_ = D.compile_dag(ins, tgt)
        assert [r.core_config.get("join_mode") for r in icm.flatten()[0] if r.core == "adder"] == [None]


@pytest.mark.parametrize("shell,module", [("vixen", "unicell_vixen_v1"), ("vix", "unicell_vix_carrier_v1")])
def test_assembler_shell_vixen_builds_an_array_of_the_vixen_carrier(shell, module):
    assert shutil.which("iverilog"), "iverilog is required (see current/START.md)"
    out = tempfile.mkdtemp()
    c = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "project_assemble_v1.py"), "--man", os.path.join(ROOT, "docs", "man", "mustang-f100-a10.man.json"),
                        "--cells", "4", "--output", os.path.join(out, "o"), "--shell", shell, "--target", "yosys"], capture_output=True, text=True)
    assert c.returncode == 0, c.stderr[-500:]
    d = os.path.join(out, "o")
    tops = [f for f in os.listdir(d) if f.startswith("top_array_") and f.endswith(".v")]
    assert tops and f"{module} " in open(os.path.join(d, tops[0])).read()
    srcs = [os.path.join(d, f) for f in os.listdir(d) if f.endswith(".v") and not f.startswith("tb_")]
    r = subprocess.run(["iverilog", "-g2012", "-o", os.path.join(out, "t.vvp")] + srcs, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-500:]


# ---- tiles, dispatcher parameter, composer panel (ledger #1105, the rest of the tool chain) ----

@pytest.mark.parametrize("tile", ["adder", "subtractor", "mul", "div", "rem"])
def test_vix_tiles_take_join_mode_as_an_optional_flag(tile):
    import vix_tile_library_v1 as vtl
    t = vtl.vix_tile_library[tile]
    base = {"second_output": 0} if tile == "mul" else {}                      # the mul tile requires second_output as a param
    c = vtl.place(t, {"in_a": "w", "in_b": "n", "out": "e"}, params={**base, "join_mode": 1})
    assert c.core_config["join_mode"] == 1
    assert "join_mode" not in vtl.place(t, {"in_a": "w", "in_b": "n", "out": "e"}, params=base).core_config      # default: absent


def test_dispatcher_instruction_param_join_mode():
    import vix_dag_dispatcher_v1 as D
    def cfg(op, params):
        icm, *_ = D.compile_dag([D.DagInstr("a", op, [D.DagOperand("dynamic"), D.DagOperand("dynamic")], params)])
        return [r for r in icm.flatten()[0] if r.cell_id == "main.a"][0].core_config
    assert cfg("add", {"join_mode": 1})["join_mode"] == 1 and cfg("mul", {"join_mode": 1})["join_mode"] == 1
    assert "join_mode" not in cfg("add", {}) and "join_mode" not in cfg("add", {"join_mode": 0})
    with pytest.raises(ValueError, match="join_mode"):
        cfg("xor", {"join_mode": 1})


def test_dsl_place_statement_with_join_mode_compiles_for_the_vixen_target():
    from program_ir_v1 import ProgramIR, PlaceIR, FieldIR
    from vix_compiler_v1 import compile_program_ir_vix
    prog = ProgramIR(name="p", statements=[PlaceIR(name="c", tile_name="adder", row=0, col=0, fields=[FieldIR(k, v) for k, v in dict(in_a="w", in_b="n", out="e", join_mode=1).items()])])
    icm, d = compile_program_ir_vix(prog, target="vixen")
    assert icm is not None, d
    assert icm.flatten()[0][0].core_config["join_mode"] == 1
    icm2, d2 = compile_program_ir_vix(prog, target="std")           # the older line refuses it, with a reason
    assert icm2 is None and any("join_mode" in x.problem for x in d2)


def test_composer_panel_lists_join_mode_for_adder_mul_div():
    import flex_layout_view_v1 as flv
    cores = flv.core_meta()["cores"]
    for core in ("adder", "mul", "div"):
        fields = {f["name"]: f for f in cores[core]["fields"]}
        assert fields["join_mode"]["kind"] == "toggle" and fields["join_mode"]["lo"] == 24


def test_dsl_source_text_with_join_mode_compiles():
    import dsl_lexer_v1 as lx, dsl_parser_v1 as ps
    from vix_compiler_v1 import compile_program_ir_vix
    src = "program j {\n    place a as adder at (0, 0) {\n        in_a: w\n        in_b: n\n        out: e\n        join_mode: 1\n    }\n}\n"
    toks, d0 = lx.tokenize(src) if isinstance(lx.tokenize(src), tuple) else (lx.tokenize(src), [])
    prog, d1 = ps.parse_source(toks)
    assert prog is not None, (d0, d1)
    icm, d2 = compile_program_ir_vix(prog, target="vixen")
    assert icm is not None, d2
    assert icm.flatten()[0][0].core_config["join_mode"] == 1
