"""tools/composer_stdlib_v1.py -- builds the Composer's STANDARD LIBRARY (`nano/library_std/`): ready-made models a design can place as blocks, each an ICM file with io-named
ports and, beside it, `<model>.test.json`: reference test vectors recorded from the model itself in FlexGrid. A block placed from a model is "standard" while its insides
match the model; once edited, it is run on its own against these vectors, so the Composer can say whether its function still holds (ledger #1032).

    python3 tools/composer_stdlib_v1.py            # (re)build every model
    python3 tools/composer_stdlib_v1.py add lif4   # just these

Every model is built by code here (the same builders the tests use), so the library can always be regenerated and never drifts from the tools."""
import argparse
import os
import sys

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS_DIR)
sys.path.insert(0, os.path.join(TOOLS_DIR, "..", "nano"))
import flex_layout_view_v1 as flv  # noqa: E402
from flex_layout_v1 import Grid  # noqa: E402
from icm_v3 import IcmV3Record  # noqa: E402

STD_DIR = os.path.join(TOOLS_DIR, "..", "nano", "library_std")


def _two_input(core, name, cfg=None, minuend=False):
    lay = flv.Layout.new(12, 20, name)
    for nm, c, r, col, io in (("A", "ram", 2, 1, "a"), ("B", "ram", 6, 1, "b"), ("OP", core, 4, 8, None), ("R", "ram", 4, 14, "r")):
        assert lay.add_cell(c, r, col, name=nm, io=io)["ok"]
    if cfg:
        assert lay.set_config("OP", cfg=cfg)["ok"]
    for a, b in (("A", "OP"), ("B", "OP"), ("OP", "R")):
        assert lay.join(a, b)["ok"]
    if minuend:
        assert lay.set_minuend("OP", "A")["ok"]
    assert lay.balance()["ok"] and not lay.problems()
    return lay


def _from_grid(g, entries, exits, name):
    """A layout built by Python (a Grid) as a model: its entry and exit cells get io names (the ports)."""
    g.balance(limit=400)
    io = {c: n for n, c in entries.items()}
    io.update({c: n for n, c in exits.items()})
    recs = [IcmV3Record(cell_id=r.cell_id, row=r.row, col=r.col, core=r.core, core_config=r.core_config, addon_config=r.addon_config, io_name=io.get(r.cell_id),
                        preload_value=r.preload_value) for r in g.records()]
    return flv.Layout(recs, name=name)


def lif4():
    import lif_flex_v1 as lif
    g = Grid(rows=40, cols=200)
    ent, ex, _ = lif.lif_neuron(g, 4)
    return _from_grid(g, ent, ex, "lif4"), {f"I{t}": [0, 40, 100, 300, 7, 260, 255, 600] for t in range(4)}


def fp16_add():
    import fp_assembler_v1 as fa
    import fp_add_v1 as fadd
    g = Grid(rows=34, cols=330)
    ent, ex, _ = fadd.fp_add(g, fa.FP16)
    # 1.0 + 1.0, 1.5 + 2.25, 0 + 0, -1 + 1, 65504 + 1 (largest finite), a subnormal pair, 0.1 + 0.2, inf + 1
    a = [0x3C00, 0x3E00, 0x0000, 0xBC00, 0x7BFF, 0x0001, 0x2E66, 0x7C00]
    b = [0x3C00, 0x4080, 0x0000, 0x3C00, 0x3C00, 0x0001, 0x3266, 0x3C00]
    return _from_grid(g, {"a": ent["a"], "b": ent["b"]}, {"r": ex["R"]}, "fp16_add"), {"a": a, "b": b}


MODELS = {
    "add": (lambda: (_two_input("adder", "add"), None), "r = a + b (integer adder)"),
    "sub": (lambda: (_two_input("adder", "sub", {"subtract_mode": 1}, minuend=True), None), "r = a - b (integer subtract; a is the minuend)"),
    "mul": (lambda: (_two_input("mul", "mul"), None), "r = a * b (integer multiply, low word)"),
    "lif4": (lif4, "a leaky-integrate-and-fire neuron over 4 time steps (#1030): inputs I0..I3, spikes S0..S3, final membrane VF"),
    "fp16_add": (fp16_add, "IEEE half-precision add, round to nearest even (#990-#1007): a + b -> r"),
}


def build(names=None, out_dir=STD_DIR):
    os.makedirs(out_dir, exist_ok=True)
    done = []
    for n in names or MODELS:
        make, desc = MODELS[n]
        lay, inputs = make()
        lay.name, lay.description = n, desc
        path, vec = flv.save_model(lay, os.path.join(out_dir, f"{n}.icm.json"), vectors=flv.make_vectors(lay, inputs) if inputs else None)
        done.append((n, len(lay.grid.nodes), {k: len(v) for k, v in vec["outputs"].items()}))
    return done


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("names", nargs="*", choices=sorted(MODELS) + [[]], default=[])
    a = ap.parse_args()
    for n, cells, outs in build(a.names or None):
        print(f"{n}: {cells} cells, reference outputs {outs}")
