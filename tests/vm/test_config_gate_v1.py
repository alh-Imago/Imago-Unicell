"""tests/vm/test_config_gate_v1.py -- config gate v1 and the arithmetic-block prototype (1 Nov 2026), simulation only (iverilog). Spec: Project doc claude/config-gate-spec.md.
Gate: raw cell drops a word offered on the cfg clock (control); with the gate none is lost, in-flight words finish on the old config, a second request is flagged, a drain timeout keeps the old config, reset reopens. Run with SETTLE=1 and SETTLE=0. Arithmetic block: add / sub / signed >= against the arithmetic, shared and naive variants.
The slow-consumer test (T6) stands in for a busy divider; the real divider cell is NOT tested here."""
import os, shutil, subprocess
import pytest
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); S = os.path.join(ROOT, "sub", "verilog"); F = os.path.join(ROOT, "fpga", "verilog")
pytestmark = pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog missing")


def sim(tmp_path, files, params=()):
    out = str(tmp_path / "a.vvp")
    cmd = ["iverilog", "-g2012"] + [f"-P{p}" for p in params] + ["-o", out] + files
    r = subprocess.run(cmd, capture_output=True, text=True); assert r.returncode == 0, r.stderr
    return subprocess.run(["vvp", out], capture_output=True, text=True).stdout


@pytest.mark.parametrize("settle", [1, 0])
def test_config_gate(tmp_path, settle):
    o = sim(tmp_path, [f"{S}/config_gate_v1.v", f"{S}/tb_config_gate_v1.v", f"{S}/adder_cell_v4s.v", f"{S}/flex_sub_bridge_v1.v", f"{F}/adder_v1.v"], [f"tb_config_gate_v1.SETTLE={settle}"])
    assert f"ALL CONFIG GATE TESTS PASS (SETTLE={settle})" in o and "FAIL" not in o, o


def test_arith_block(tmp_path):
    o = sim(tmp_path, [f"{S}/arith_block_v1.v", f"{S}/tb_arith_block_v1.v", f"{S}/adder_cell_v4s.v", f"{F}/adder_v1.v"])
    assert "ALL ARITH BLOCK TESTS PASS" in o and "MISMATCH" not in o, o


def test_arith_block_v2(tmp_path):
    """v2: add, sub, ge, 3-way compare, accumulate; shared and naive vs the arithmetic, modes 0/1 vs adder_cell_v4s, accumulate vs the real accumulator_cell_v4s (continuous mode, 32-bit)."""
    o = sim(tmp_path, [f"{S}/arith_block_v2.v", f"{S}/tb_arith_block_v2.v", f"{S}/adder_cell_v4s.v", f"{S}/accumulator_cell_v4s.v", f"{F}/adder_v1.v"])
    assert "ALL ARITH BLOCK V2 TESTS PASS" in o and "MISMATCH" not in o, o


def test_arith_block_v3_fix(tmp_path):
    """v3 fixes a v2 bug found by the combined test: accumulate pulses were not qualified by valid_in. The v3 test leaves in_a STALE after each pulse; the same test must FAIL on v2."""
    o = sim(tmp_path, [f"{S}/arith_block_v3.v", f"{S}/tb_arith_block_v3.v", f"{S}/adder_cell_v4s.v", f"{S}/accumulator_cell_v4s.v", f"{F}/adder_v1.v"])
    assert "ALL ARITH BLOCK V3 TESTS PASS" in o and "MISMATCH" not in o, o
    v2tb = open(f"{S}/tb_arith_block_v3.v").read().replace("arith_block_v3", "arith_block_v2")
    p = tmp_path / "tb_v2_stale.v"; p.write_text(v2tb)
    o2 = sim(tmp_path, [f"{S}/arith_block_v2.v", str(p), f"{S}/adder_cell_v4s.v", f"{S}/accumulator_cell_v4s.v", f"{F}/adder_v1.v"])
    assert "FAILED" in o2 and "ALL ARITH" not in o2, o2


def test_gate_in_front_of_block(tmp_path):
    """Random stream of 1500 words with ~440 random reconfiguration requests through config_gate_v1 -> arith_block_v3 -> sub_to_flex_v1. Every word is processed under the config active when it was admitted, none lost, order kept. CONTROL (no gate, config driven straight in): corruption. PHASE 2: a word that yields no result stalls the one-word bridge; a later request times out (cfg_err[0])."""
    files = lambda: [f"{S}/config_gate_v1.v", f"{S}/arith_block_v3.v", f"{S}/tb_gate_block_v1.v", f"{S}/flex_sub_bridge_v1.v", f"{F}/adder_v1.v"]
    o = sim(tmp_path, files(), ["tb_gate_block_v1.GATED=1"])
    assert "ALL GATE+BLOCK TESTS PASS (1500 words" in o and "PHASE2 no-result word: admitted=1" in o and "cfg_err=01" in o, o
    c = sim(tmp_path, files(), ["tb_gate_block_v1.GATED=0"])
    assert "CONTROL SHOWS CORRUPTION" in c, c


def test_arith_block_v4_answers_every_word(tmp_path):
    """v4 (Alan, 03:04): every word gets a result. The v4 test checks the valid pulse for every word incl. an accumulate word with neither pulse; the same test on v3 must report NO ANSWER."""
    o = sim(tmp_path, [f"{S}/arith_block_v4.v", f"{S}/tb_arith_block_v4.v", f"{S}/adder_cell_v4s.v", f"{S}/accumulator_cell_v4s.v", f"{F}/adder_v1.v"])
    assert "ALL ARITH BLOCK V4 TESTS PASS" in o and "NO ANSWER" not in o, o
    t = open(f"{S}/tb_arith_block_v4.v").read().replace("arith_block_v4", "arith_block_v3"); p = tmp_path / "tb_v3_on_v4.v"; p.write_text(t)
    o3 = sim(tmp_path, [f"{S}/arith_block_v3.v", str(p), f"{S}/adder_cell_v4s.v", f"{S}/accumulator_cell_v4s.v", f"{F}/adder_v1.v"])
    assert "NO ANSWER" in o3, o3


def test_gate_v2_block_v4_and_watchdog(tmp_path):
    """Same random stream as the v1 test with config_gate_v2 + arith_block_v4: all words right; phase 2 a no-pulse word no longer stalls (admitted=2); phase 3 a dead region raises `fault` after the WATCHDOG (0 at 60 clocks, 1 at 180). Control (no gate) still corrupts."""
    files = [f"{S}/config_gate_v2.v", f"{S}/arith_block_v4.v", f"{S}/tb_gate_block_v2.v", f"{S}/flex_sub_bridge_v1.v", f"{F}/adder_v1.v"]
    o = sim(tmp_path, files, ["tb_gate_block_v2.GATED=1"])
    assert "ALL GATE+BLOCK TESTS PASS (1500 words" in o and "PHASE2 no-pulse word: admitted=2" in o, o
    assert "60 clocks: fault=0" in o and "180 clocks: fault=1" in o, o
    assert "CONTROL SHOWS CORRUPTION" in sim(tmp_path, files, ["tb_gate_block_v2.GATED=0"])


@pytest.mark.parametrize("gated", [1, 0])
def test_bridge_throughput_is_five_clocks_per_word(tmp_path, gated):
    """Measured: one word through producer -> (gate or plain bridge) -> adder cell -> sub_to_flex -> consumer takes 5 clocks (the bridge waits for each result to be taken); the adder cell alone takes a word every clock. The idle gate adds nothing."""
    o = sim(tmp_path, [f"{S}/config_gate_v1.v", f"{S}/tb_gate_throughput_v1.v", f"{S}/adder_cell_v4s.v", f"{S}/flex_sub_bridge_v1.v", f"{F}/adder_v1.v"], [f"tb_gate_throughput_v1.GATED={gated}"])
    assert "200 words, 200 results" in o and "= 5 clocks per word" in o, o


@pytest.mark.parametrize("scen,maxr", [(1, 2), (2, 1), (3, 1), (4, 2), (5, 2)])
def test_chain_of_three_units_with_fault_policy(tmp_path, scen, maxr):
    """Chain of three gate_v3 + arith_block_v4 + sub_to_flex units, joined by the flex hand-off, each stage checked against a model. 1 transient fault recovered (1 word lost, counted); 2 two far-apart faults recovered with MAX_RETRY=1 (retries forgiven); 3 persistent fault -> dead, neighbours untouched, upstream held; 4 a downstream stall longer than the watchdog causes NO fault or reset; 5 clean run with ~70 random reconfigurations of the middle unit."""
    o = sim(tmp_path, [f"{S}/config_gate_v3.v", f"{S}/arith_block_v4.v", f"{S}/tb_chain_v1.v", f"{S}/flex_sub_bridge_v1.v", f"{F}/adder_v1.v"], [f"tb_chain_v1.SCEN={scen}", f"tb_chain_v1.MAXR={maxr}"])
    assert f"CHAIN SCEN {scen} PASS" in o and "FAIL" not in o, o


@pytest.mark.parametrize("mut,scen,maxr", [("watchdog ignores a present result", 4, 2), ("no config replay", 1, 2), ("retries never forgiven", 2, 1), ("lost word not counted", 1, 2)])
def test_chain_tests_can_fail(tmp_path, mut, scen, maxr):
    """Mutation checks: each deliberate break of config_gate_v3 must make its chain scenario FAIL."""
    src = open(f"{S}/config_gate_v3.v").read()
    subs = {"watchdog ignores a present result": (" && !res_valid && (wd >= WATCHDOG);", " && (wd >= WATCHDOG);"),
            "no config replay": ("if (have_cfg) state <= REC_CFG; else state <= OPEN;", "state <= OPEN;"),
            "retries never forgiven": ("if (good >= GOOD_WORDS - 1)", "if (1'b0)"),
            "lost word not counted": ("resets <= resets + 8'd1; lost <= lost + 8'd1;", "resets <= resets + 8'd1;")}
    a, b = subs[mut]; assert a in src; p = tmp_path / "gate_mut.v"; p.write_text(src.replace(a, b))
    o = sim(tmp_path, [str(p), f"{S}/arith_block_v4.v", f"{S}/tb_chain_v1.v", f"{S}/flex_sub_bridge_v1.v", f"{F}/adder_v1.v"], [f"tb_chain_v1.SCEN={scen}", f"tb_chain_v1.MAXR={maxr}"])
    assert f"CHAIN SCEN {scen} FAILED" in o, o


def _v5(tmp_path, block_src=None, tb_extra=()):
    blk = block_src or f"{S}/arith_block_v5.v"
    return sim(tmp_path, [blk, f"{S}/tb_arith_block_v5.v", f"{S}/nano_cell_v4s.v", f"{F}/adder_v1.v"])


def test_arith_block_v5_shift_and_nano(tmp_path):
    """v5 adds an 18-bit shift left/right (mode 5/6, amount in_b[4:0], 18 or more gives 0) and the nano logic (mode 7: the 12 topologies of nano_cell_v4s; FLOW = in_a, HELD = in_b). Shared, naive and the truth-table nano variant all equal the reference; nano equals the REAL nano_cell_v4s for all 12 topologies; every word is answered."""
    o = _v5(tmp_path)
    assert "ALL ARITH BLOCK V5 TESTS PASS" in o and "MISMATCH" not in o and "NO ANSWER" not in o, o


@pytest.mark.parametrize("a,b", [("wire [17:0] sx = (mode == 3'd6) ? rev_in : in_a[17:0];", "wire [17:0] sx = (mode == 3'd5) ? rev_in : in_a[17:0];"),
                                 ("10'h0BC: tt = 4'b0110;", "10'h0BC: tt = 4'b1001;"),
                                 ("wire [17:0] sy = sx << sh;", "wire [17:0] sy = sx << (sh % 18);")])
def test_arith_block_v5_tests_can_fail(tmp_path, a, b):
    """Mutation checks: shared shifter direction swapped, XOR truth table wrong, shift amount wrapping instead of clearing at 18 or more - each must fail."""
    src = open(f"{S}/arith_block_v5.v").read(); assert a in src
    p = tmp_path / "blk_mut.v"; p.write_text(src.replace(a, b))
    assert "ARITH BLOCK V5 FAILED" in _v5(tmp_path, str(p))


@pytest.mark.parametrize("scen", [1, 2, 3, 4])
def test_join_stage(tmp_path, scen):
    """join_v1, the two-arrival front stage. 1 pair mode, operands arriving in random order (A first, B first), a lone operand never fires; 2 sticky B (the nano-cell behaviour: B is held and pairs with every later A); 3 join -> gate_v3 -> block v5 (nano XOR, sticky B) equals the REAL nano_cell_v4s fed load_hold / flow in the same order; 4 a new B offered while a pair waits must not change that pair."""
    o = sim(tmp_path, [f"{S}/join_v1.v", f"{S}/tb_join_v1.v", f"{S}/config_gate_v3.v", f"{S}/arith_block_v5.v", f"{S}/nano_cell_v4s.v", f"{S}/flex_sub_bridge_v1.v", f"{F}/adder_v1.v"], [f"tb_join_v1.SCEN={scen}"])
    assert f"JOIN SCEN {scen} PASS" in o and "FAIL" not in o, o


@pytest.mark.parametrize("a,b,scen", [("assign out_valid = have_a & have_b;", "assign out_valid = have_a;", 1),
                                      ("if (!STICKY_B) have_b <= 1'b0;", "have_b <= 1'b0;", 2),
                                      ("(STICKY_B ? ~out_valid : ~have_b)", "1'b1", 4)])
def test_join_tests_can_fail(tmp_path, a, b, scen):
    """Mutation checks: firing on one operand, clearing the held B after use, overwriting B under a waiting pair - each must fail."""
    src = open(f"{S}/join_v1.v").read(); assert a in src
    p = tmp_path / "join_mut.v"; p.write_text(src.replace(a, b))
    o = sim(tmp_path, [str(p), f"{S}/tb_join_v1.v", f"{S}/config_gate_v3.v", f"{S}/arith_block_v5.v", f"{S}/nano_cell_v4s.v", f"{S}/flex_sub_bridge_v1.v", f"{F}/adder_v1.v"], [f"tb_join_v1.SCEN={scen}"])
    assert f"JOIN SCEN {scen} FAILED" in o, o


def test_nano_truth_table_cell_is_identical(tmp_path):
    """nano_cell_v4s_tt (4-bit truth table decoded once) equals the original nano_cell_v4s every clock for all 1,024 topology words; a wrong table entry is caught."""
    files = [f"{S}/nano_cell_v4s.v", f"{S}/nano_cell_v4s_tt.v", f"{S}/tb_nano_tt_v1.v"]
    assert "NANO TT EQUIVALENT" in sim(tmp_path, files)
    src = open(f"{S}/nano_cell_v4s_tt.v").read(); a = "10'h0BC: tt = 4'b0110;"; assert a in src
    p = tmp_path / "ntt_mut.v"; p.write_text(src.replace(a, "10'h0BC: tt = 4'b0111;"))
    assert "NANO TT DIFFERS" in sim(tmp_path, [files[0], str(p), files[2]])


def test_mask_is_a_special_case_of_the_nano_and(tmp_path):
    """arith_block_v6 mode 7 with the held operand taken from the config (cfg_data[26]) and topology AND equals the REAL mask_cell_v4s for all 256 nibble masks x mask_en 0/1; the v5 test still passes on v6; inverted keep flags are caught."""
    files = [f"{S}/arith_block_v6.v", f"{S}/tb_arith_block_v6.v", f"{S}/mask_cell_v4s.v", f"{S}/nano_cell_v4s.v", f"{F}/nibble_mask_addon_v1.v", f"{F}/adder_v1.v"]
    assert "ALL ARITH BLOCK V6 TESTS PASS" in sim(tmp_path, files)
    src = open(f"{S}/arith_block_v6.v").read(); a = "wire [31:0] nh = heldsrc ? keep_exp : in_b;"; assert a in src
    p = tmp_path / "v6_mut.v"; p.write_text(src.replace(a, "wire [31:0] nh = heldsrc ? ~keep_exp : in_b;"))
    assert "ARITH BLOCK V6 FAILED" in sim(tmp_path, [str(p)] + files[1:])
    t5 = open(f"{S}/tb_arith_block_v5.v").read().replace("arith_block_v5", "arith_block_v6"); q = tmp_path / "tb5on6.v"; q.write_text(t5)
    assert "ALL ARITH BLOCK V5 TESTS PASS" in sim(tmp_path, [f"{S}/arith_block_v6.v", str(q), f"{S}/nano_cell_v4s.v", f"{F}/adder_v1.v"])


def test_arith_block_v7_fine_coarse_shift(tmp_path):
    """arith_block_v7 SHIFT_CF=1 (fine 0-3 then even coarse taps 0,4,8,12,16, same direction) equals the plain shift reference and the v6 shifter for every amount 0..31, both directions; a wrong tap is caught; the v5 test passes on v7."""
    files = [f"{S}/arith_block_v7.v", f"{S}/tb_arith_block_v7.v", f"{F}/adder_v1.v"]
    assert "ALL ARITH BLOCK V7 TESTS PASS" in sim(tmp_path, files)
    src = open(f"{S}/arith_block_v7.v").read(); a = "3'd2: coarse = fine << 8;"; assert a in src
    p = tmp_path / "v7_mut.v"; p.write_text(src.replace(a, "3'd2: coarse = fine << 7;"))
    assert "ARITH BLOCK V7 FAILED" in sim(tmp_path, [str(p)] + files[1:])
    t5 = open(f"{S}/tb_arith_block_v5.v").read().replace("arith_block_v5", "arith_block_v7"); q = tmp_path / "tb5on7.v"; q.write_text(t5)
    assert "ALL ARITH BLOCK V5 TESTS PASS" in sim(tmp_path, [f"{S}/arith_block_v7.v", str(q), f"{S}/nano_cell_v4s.v", f"{F}/adder_v1.v"])
