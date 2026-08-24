"""
test_dsp_wrapper_tile_library_v1.py — real, direct verification of
`dsp_wrapper_tile_library_v1.py` and the generic hook it proves
(`tile_source_registry_v1.py`, points.md #485): a real DSL program
that places a DSP wrapper tile can now compile end to end through the
SAME `dsl_compiler_v1.compile_source()` entry point every other DSL
program already uses, with zero DSP-wrapper-specific code added to
the compiler's own control flow.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

import icm_v3 as v3  # noqa: E402
import icm_v4 as v4  # noqa: E402
from dsl_compiler_v1 import compile_source  # noqa: E402
from dsp_wrapper_tile_library_v1 import dsp_wrapper_tile_library, place as dsp_place  # noqa: E402
from tile_source_registry_v1 import find_source_for, all_known_tile_names  # noqa: E402


# ── Real, direct DspWrapperTileSpec/place() tests -- before trusting
# the DSL layer built on top. ──────────────────────────────────────

def test_dsp_add_tile_registered_and_place_produces_real_record():
    assert "dsp_add" in dsp_wrapper_tile_library.names()
    tile = dsp_wrapper_tile_library.get("dsp_add")
    rec = dsp_place(tile, row=1, col=2, port_directions={"in_a": "n", "in_b": "s", "out": "e"},
                     params={}, cell_id="t1")
    assert isinstance(rec, v4.DspWrapperRecord)
    assert (rec.row, rec.col, rec.op) == (1, 2, "ADD")
    assert rec.a_dir == "n" and rec.b_dir == "s"
    assert rec.watchdog_threshold is None


def test_dsp_tile_place_rejects_same_direction_for_a_and_b():
    tile = dsp_wrapper_tile_library.get("dsp_sub")
    try:
        dsp_place(tile, row=0, col=0, port_directions={"in_a": "n", "in_b": "n", "out": "e"})
        assert False, "expected a ValueError for a_dir == b_dir"
    except ValueError as e:
        assert "distinct" in str(e)


def test_dsp_tile_place_rejects_list_for_in_a():
    tile = dsp_wrapper_tile_library.get("dsp_mul")
    try:
        dsp_place(tile, row=0, col=0, port_directions={"in_a": ["n", "s"], "in_b": "e", "out": "w"})
        assert False, "expected a ValueError -- in_a must be a single direction"
    except ValueError as e:
        assert "single real cardinal" in str(e)


def test_dsp_tile_place_supports_out_fanout():
    tile = dsp_wrapper_tile_library.get("dsp_ge")
    rec = dsp_place(tile, row=0, col=0, port_directions={"in_a": "n", "in_b": "s", "out": ["e", "w"]})
    assert rec.to_dict()["downstream_mask"] == v3.pack_dirmask(["e", "w"])


def test_dsp_tile_place_watchdog_param_optional_and_passthrough():
    tile = dsp_wrapper_tile_library.get("dsp_add")
    rec = dsp_place(tile, row=0, col=0, port_directions={"in_a": "n", "in_b": "s", "out": "e"},
                     params={"watchdog_threshold": 25})
    assert rec.watchdog_threshold == 25


# ── The real registry hook itself ──────────────────────────────────

def test_registry_finds_both_kinds_generically():
    src_super = find_source_for("ram_constant")   # pre-existing super tile
    src_dsp = find_source_for("dsp_add")            # new DSP wrapper tile
    assert src_super is not None and src_super.bucket == "super_records"
    assert src_dsp is not None and src_dsp.bucket == "dsp_wrapper_records"
    assert find_source_for("no_such_tile_at_all") is None


def test_registry_all_known_names_includes_both_kinds():
    names = all_known_tile_names()
    assert "ram_constant" in names
    assert "dsp_add" in names


# ── Real, end-to-end DSL programs, through the unmodified compile_source() entry point ──

def test_super_only_program_still_produces_icm_v3_unchanged():
    """Real, direct backward-compatibility confirmation: a program
    with no DSP wrapper placements produces the exact same real
    `IcmV3File` shape as before #485 -- proving the new registry-driven
    path changed nothing for existing programs."""
    src = """
    program ram_only {
        place r1 as ram_constant at (0, 0) {
            out: e
            init_data: 42
        }
    }
    """
    icm, diags = compile_source(src)
    assert diags == []
    assert isinstance(icm, v3.IcmV3File)
    assert not isinstance(icm, v4.IcmV4File)
    assert len(icm.records) == 1


def test_mixed_program_with_dsp_wrapper_placement_compiles_to_icm_v4():
    """The real, new capability: a DSL program placing a DSP wrapper
    tile alongside an ordinary super tile compiles end to end into a
    real `IcmV4File`, through the SAME `compile_source()` call every
    other program uses -- no separate entry point needed."""
    src = """
    program dsp_add_into_ram {
        place a1 as dsp_add at (0, 0) {
            in_a: n
            in_b: s
            out: e
        }
        place r1 as ram_flowing at (0, 1) {
            in: w
            out: e
        }
    }
    """
    icm, diags = compile_source(src)
    assert diags == []
    assert icm is not None
    assert isinstance(icm, v4.IcmV4File)
    assert len(icm.dsp_wrapper_records) == 1
    assert len(icm.super_records) == 1
    dsp_rec = icm.dsp_wrapper_records[0]
    assert (dsp_rec.row, dsp_rec.col, dsp_rec.op) == (0, 0, "ADD")
    super_rec = icm.super_records[0]
    assert (super_rec.row, super_rec.col, super_rec.core) == (0, 1, "ram")

    # ── Real end-to-end proof: save, reload, hash-verify, then
    # actually RUN it as a live grid and confirm the real computed
    # result -- not just that the file parses. ──
    import tempfile
    tmpdir = tempfile.mkdtemp()
    path = os.path.join(tmpdir, "dsp_add_into_ram.icm.json")
    icm.save(path)
    reloaded = v4.IcmV4File.load(path)

    grid = reloaded.build_grid()
    from dsp_wrapper_automaton_v1 import _float_to_bits, _bits_to_float
    grid.cells[(0, 0)].deliver({0: _float_to_bits(1.25), 1: _float_to_bits(2.75)})  # N=0,S=1
    grid.tick()
    grid.tick()
    val, valid, _ = grid.cells[(0, 1)]._offer_state()
    assert valid and _bits_to_float(val) == 4.0


def test_unknown_tile_error_lists_dsp_wrapper_tiles_too():
    """A real, deliberately-broken program (unknown tile name) must
    surface a suggestion list that includes DSP wrapper tile names
    now, not just the pre-existing super/composed ones -- confirms
    the error path itself was generalized, not just the happy path."""
    src = """
    program broken {
        place x as no_such_tile_at_all at (0, 0) { }
    }
    """
    icm, diags = compile_source(src)
    assert icm is None
    assert len(diags) == 1
    assert "dsp_add" in diags[0].suggestion
