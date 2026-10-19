"""tests/vm/test_flexsub_oneshot_preload_v1.py -- ledger #1277, step 2 of the #1275 ruling.
tools/flexsub_icm_generate_v2.py + flexsub_icm_flex_v2.py: a ram with preload_value, fixed_mode 0 and nothing feeding it is a ONE-SHOT (the standard reading);
a permanent constant says fixed_mode 1. A ram that only starts a branch (the CORDIC zero references) stays a constant (the branch holds its first value).
1. v1 and v2 generate IDENTICAL flex Verilog for every example design except the old cordic_z_convergence (its adder constants are not fixed).
2. in RTL simulation, the old cordic (v2 generator) agrees with the ORIGINAL VM grid (FlexGrid v1: one word); cordic_z_convergence_v2 agrees with the card words.
3. the sub family refuses a preloaded, unfed, non-fixed ram with the reason."""
import glob, os, shutil, sys, tempfile
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "nano")); sys.path.insert(0, os.path.join(ROOT, "tools"))
import flexsub_icm_generate_v1 as g1  # noqa: E402
import flexsub_icm_generate_v2 as g2  # noqa: E402

EX = os.path.join(ROOT, "nano", "examples")
MAN = os.path.join(ROOT, "docs", "man", "kintex7-ypcb00338.man.json")


def _gen(G, path, family="flex"):
    with tempfile.TemporaryDirectory() as d:
        G.generate(path, os.path.join(d, "o"), family=family, rings=True)
        f = sorted(x for x in os.listdir(os.path.join(d, "o")) if x.endswith(("_flex.v", "_sub.v")))[0]
        return open(os.path.join(d, "o", f)).read()


def test_every_example_but_the_old_cordic_is_unchanged():
    files = sorted(glob.glob(EX + "/*.icm-hier.json") + glob.glob(EX + "/card_tested/*.icm.json"))
    assert len(files) >= 25
    def out(G, f):                      # a design the generator refuses must be refused the same way by both
        try:
            return _gen(G, f)
        except Exception as e:
            return "ERR " + str(e).replace("flexsub_icm_generate_v1", "X").replace("flexsub_icm_generate_v2", "X")
    changed = [os.path.basename(f) for f in files if out(g1, f) != out(g2, f)]
    assert changed == ["cordic_z_convergence.icm-hier.json"]


def test_sub_family_refuses_with_the_reason():
    with pytest.raises(Exception) as e:
        _gen(g2, os.path.join(EX, "cordic_z_convergence.icm-hier.json"), family="sub")
    assert "ONE-SHOT" in str(e.value) and "fixed_mode 1" in str(e.value)


@pytest.mark.skipif(not shutil.which("iverilog"), reason="needs iverilog")
def test_rtl_agrees_with_the_standard_reading():
    import flex_grid_v1, flex_grid_v2
    import kintex_icm_runner_v1 as kr
    import flexsub_assemble_v1 as fa
    man = fa.load_man_flexsub(MAN)

    def verdict(name):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(EX, name + ".icm-hier.json")
            g2.generate(p, os.path.join(d, "o"), family="flex", rings=True)
            return kr.wrap(os.path.join(d, "o"), p, man)["sim"]["verdict"]

    assert verdict("cordic_z_convergence_v2") == "PASS"                      # reference: FlexGrid2 (the card words)
    keep = flex_grid_v2.FlexGrid2
    flex_grid_v2.FlexGrid2 = flex_grid_v1.FlexGrid                           # reference: the ORIGINAL grid
    try:
        assert verdict("cordic_z_convergence") == "PASS"
    finally:
        flex_grid_v2.FlexGrid2 = keep
