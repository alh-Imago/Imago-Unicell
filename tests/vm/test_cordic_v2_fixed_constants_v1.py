"""tests/vm/test_cordic_v2_fixed_constants_v1.py -- ledger #1276.
nano/examples/cordic_z_convergence_v2.icm-hier.json = the CORDIC with fixed_mode 1 on its 8 adder constants (ICM rule of #1275: a permanent constant says fixed_mode 1).
1. exactly the 8 adder constants are fixed; the 4 zero references stay one-shot.
2. on the ORIGINAL VM grid (FlexGrid v1, no held-constant rule) it delivers the card's words (#1266) -- the old file gives one word there.
3. the flex Verilog generated from it is the same as from the old file, apart from the module name (the hardware does not change)."""
import os, re, sys, tempfile, warnings

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "nano")); sys.path.insert(0, os.path.join(ROOT, "tools"))
import flexsub_icm_netlist_v1 as nl  # noqa: E402
import flexsub_icm_generate_v1 as gen  # noqa: E402
import flex_grid_v1 as fg1  # noqa: E402

OLD = os.path.join(ROOT, "nano", "examples", "cordic_z_convergence.icm-hier.json")
NEW = os.path.join(ROOT, "nano", "examples", "cordic_z_convergence_v2.icm-hier.json")


def test_only_the_adder_constants_are_fixed():
    _, recs, *_ = nl.extract(NEW)
    pre = [r for r in recs if r.core == "ram" and r.preload_value is not None]
    fixed = sorted(r.cell_id for r in pre if (r.core_config or {}).get("fixed_mode"))
    assert len(pre) == 12 and len(fixed) == 8 and all(re.search(r"const_(pos|neg)$", c) for c in fixed)


def _run(path, words):
    _, recs, *_ = nl.extract(path)
    pos = {r.cell_id: (r.row, r.col) for r in recs}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        g = fg1.FlexGrid(recs)
    for _ in range(12):
        g.tick()
    c, e = g.cells[pos["s0.merge"]], g.cells[pos["s3.gather"]]
    e.ram_data_valid = False
    todo, seen = list(words), []
    for _ in range(2500):
        if todo and not c.ram_data_valid and not g._pending.get(pos["s0.merge"]):
            g.inject(*pos["s0.merge"], todo.pop(0))
        g.tick()
        if e.ram_data_valid:
            v = e.ram_data_reg
            seen.append(v - (1 << 32) if v >= 1 << 31 else v)
            e.ram_data_valid = False
    return seen


def test_original_grid_gives_the_card_words():
    assert _run(NEW, [10, 1, 2]) == [2736, 2727, 2728]
    assert _run(NEW, [14, 100, 3]) == [2740, 2826, 2729]
    assert len(_run(OLD, [10, 1, 2])) == 1                     # the old file on the original grid: constants used up (why v2 of the grid exists)


def test_generated_flex_verilog_is_unchanged():
    texts = []
    for p, mod in ((OLD, "cordic_z_convergence"), (NEW, "cordic_z_convergence_v2")):
        with tempfile.TemporaryDirectory() as d:
            gen.generate(p, os.path.join(d, "o"), family="flex", rings=True)
            f = [x for x in os.listdir(os.path.join(d, "o")) if x.endswith("_flex.v")][0]
            texts.append(open(os.path.join(d, "o", f)).read().replace(mod, "X"))
    assert texts[0] == texts[1]
