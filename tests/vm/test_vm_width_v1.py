"""tests/vm/test_vm_width_v1.py -- the VM's data WIDTH parameter (ledger #961).

The VM computed in 32 bits only. `SuperGrid(records, width=W)` makes it compute in W bits (1-64): the first piece of "mirror mode" (Alan: in std mode the VM stays as it is; in mirror mode it
changes to reflect the target -- e.g. the Tang's native 18, or 36). The default is 32 and must behave EXACTLY as before (the whole tests/vm suite is the proof of that); the add-ons are defined on the
RTL's 32-bit lanes, so at any other width an ENABLED add-on is refused rather than guessed (known facts only).

The oracle here is a plain-Python statement of the intended meaning, written independently of the VM code: wrap at 2**W; the comparator reads a value as a signed W-bit number.
Covered at W != 32: ram, adder, subtract, multiplier (low word AND the high word), comparator. Threaded but NOT yet verified individually at W != 32 (they are exercised at 32 by the rest
of the suite): accumulator, branch, priority, nano.
"""
import os
import random
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "nano"))
import icm_width_v1 as w_mod  # noqa: E402
import unicell_super_automaton_v1 as vm  # noqa: E402
from icm_v3 import IcmV3Record  # noqa: E402

WIDTHS = (4, 8, 16, 18, 32, 36)


def ram(cid, r, c, up, down, **cfg):
    return IcmV3Record(cell_id=cid, row=r, col=c, core="ram", core_config={"upstream_mask": up, "downstream_mask": down, **cfg})


def signed(v, w):
    v &= (1 << w) - 1
    return v - (1 << w) if v >> (w - 1) else v


def run_two(core, cfg, a, b, width=None):
    """X(0,0) -> core(0,1) <- Y(1,1); core -> E(0,2). A is injected first and B later, so A is the first arrival. Returns (E's value or None, the core cell)."""
    recs = [ram("X", 0, 0, [], ["e"]), ram("Y", 1, 1, [], ["n"]),
            IcmV3Record(cell_id="C", row=0, col=1, core=core, core_config={"upstream_mask": ["w", "s"], "downstream_mask": ["e"], **cfg}),
            ram("E", 0, 2, ["w"], [])]
    g = vm.SuperGrid(recs) if width is None else vm.SuperGrid(recs, width=width)
    for _ in range(4):
        g.tick()
    g.inject(0, 0, a)
    for _ in range(12):
        g.tick()
    g.inject(1, 1, b)
    for _ in range(40):
        g.tick()
    e = g.cells[(0, 2)]
    return (e.ram_data_reg if e.ram_data_valid else None), g.cells[(0, 1)]


def run_one(core, cfg, a, width=None):
    recs = [ram("X", 0, 0, [], ["e"]), IcmV3Record(cell_id="C", row=0, col=1, core=core, core_config={"upstream_mask": ["w"], "downstream_mask": ["e"], **cfg}), ram("E", 0, 2, ["w"], [])]
    g = vm.SuperGrid(recs) if width is None else vm.SuperGrid(recs, width=width)
    for _ in range(4):
        g.tick()
    g.inject(0, 0, a)
    for _ in range(40):
        g.tick()
    e = g.cells[(0, 2)]
    return e.ram_data_reg if e.ram_data_valid else None


def operands(w, n=14, seed=0):
    r = random.Random(seed * 1000 + w)
    edge = [0, 1, (1 << w) - 1, 1 << (w - 1), (1 << (w - 1)) - 1]
    return [(x, y) for x in edge[:3] for y in edge[:3]] + [(r.getrandbits(w + 6), r.getrandbits(w + 6)) for _ in range(n)]     # includes values WIDER than w: they must be masked


@pytest.mark.parametrize("w", WIDTHS)
def test_ram_masks_to_the_width(w):
    for a, _ in operands(w):
        recs = [ram("X", 0, 0, [], ["e"]), ram("E", 0, 1, ["w"], [])]
        g = vm.SuperGrid(recs, width=w)
        for _ in range(4):
            g.tick()
        g.inject(0, 0, a)
        for _ in range(20):
            g.tick()
        assert g.cells[(0, 1)].ram_data_reg == a & ((1 << w) - 1), (w, a)


@pytest.mark.parametrize("w", WIDTHS)
def test_adder_and_subtract_wrap_at_the_width(w):
    m = (1 << w) - 1
    for a, b in operands(w):
        got, _ = run_two("adder", {}, a, b, w)
        assert got == ((a & m) + (b & m)) & m, ("add", w, a, b, got)
        got, _ = run_two("adder", {"subtract_mode": 1}, a, b, w)
        assert got == ((a & m) - (b & m)) & m, ("sub", w, a, b, got)


@pytest.mark.parametrize("w", WIDTHS)
def test_multiplier_low_word_and_high_word(w):
    m = (1 << w) - 1
    for a, b in operands(w, n=8):
        got, cell = run_two("mul", {}, a, b, w)
        full = (a & m) * (b & m)
        assert got == full & m, ("low", w, a, b, got)
        assert cell.mul_captured_hi == (full >> w) & m, ("hi", w, a, b, cell.mul_captured_hi)


@pytest.mark.parametrize("w", WIDTHS)
def test_comparator_reads_the_value_as_a_signed_w_bit_number(w):
    if w < 4:
        pytest.skip("threshold 5 needs 4+ bits")
    thr = 5
    m = (1 << w) - 1
    cases = [0, 4, 5, 6, (1 << (w - 1)) - 1, 1 << (w - 1), m, (1 << (w - 1)) + 3] + [random.Random(w).getrandbits(w) for _ in range(6)]
    for a in cases:
        got = run_one("comparator", {"threshold": thr}, a, w)
        assert got == (1 if signed(a, w) >= thr else 0), ("cmp", w, a, got)


def test_the_width_actually_bites_the_same_inputs_differ_between_widths():
    # 2**17 is -131072 as an 18-bit number but +131072 as a 32-bit one; 2**17 + 2**17 wraps to 0 at 18 bits.
    assert run_one("comparator", {"threshold": 5}, 1 << 17, 18) == 0
    assert run_one("comparator", {"threshold": 5}, 1 << 17, 32) == 1
    assert run_two("adder", {}, 1 << 17, 1 << 17, 18)[0] == 0
    assert run_two("adder", {}, 1 << 17, 1 << 17, 32)[0] == 1 << 18
    assert run_two("mul", {}, 0x3FFFF, 0x3FFFF, 18)[1].mul_captured_hi == ((0x3FFFF * 0x3FFFF) >> 18) & 0x3FFFF


def test_the_default_is_32_and_explicit_32_is_identical():
    for a, b in operands(32, n=10):
        for core, cfg in (("adder", {}), ("adder", {"subtract_mode": 1}), ("mul", {})):
            d, dc = run_two(core, cfg, a, b)
            e, ec = run_two(core, cfg, a, b, 32)
            assert d == e
            if core == "mul":
                assert dc.mul_captured_hi == ec.mul_captured_hi
        m = 0xFFFFFFFF
        assert run_two("adder", {}, a, b)[0] == ((a & m) + (b & m)) & m
    assert vm.SuperGrid([ram("X", 0, 0, [], [])]).width == 32 and vm.SuperGrid([ram("X", 0, 0, [], [])]).mask == 0xFFFFFFFF


@pytest.mark.parametrize("bad", [0, -1, 65, True, 18.5, "18", []])
def test_an_invalid_width_is_refused(bad):
    with pytest.raises(w_mod.IcmWidthError):
        vm.SuperGrid([ram("X", 0, 0, [], [])], width=bad)


def test_addons_are_32_bit_lane_definitions_and_refused_at_other_widths():
    def with_invert(w):
        # the add-on acts on what a cell EMITS, so the add-on cell C needs a downstream: X -> C(invert) -> E
        recs = [ram("X", 0, 0, [], ["e"]), IcmV3Record(cell_id="C", row=0, col=1, core="ram", core_config={"upstream_mask": ["w"], "downstream_mask": ["e"]}, addon_config={"invert_en": 1}),
                ram("E", 0, 2, ["w"], [])]
        g = vm.SuperGrid(recs, width=w)
        for _ in range(4):
            g.tick()
        g.inject(0, 0, 0x0F0F)
        for _ in range(30):
            g.tick()
        return g.cells[(0, 2)].ram_data_reg
    assert with_invert(32) == (~0x0F0F) & 0xFFFFFFFF            # the add-on works, and is unchanged, at 32
    with pytest.raises(ValueError, match="32-bit lanes only"):
        with_invert(18)
    recs = [ram("X", 0, 0, [], ["e"]), ram("E", 0, 1, ["w"], [])]              # no add-on enabled: fine at any width
    g = vm.SuperGrid(recs, width=18)
    for _ in range(4):
        g.tick()
    g.inject(0, 0, 0x3FFFF)
    for _ in range(20):
        g.tick()
    assert g.cells[(0, 1)].ram_data_reg == 0x3FFFF


def test_a_subclass_that_skips_the_parent_constructor_still_runs_at_32():
    assert vm.SuperGrid.width == 32 and vm.SuperGrid.mask == 0xFFFFFFFF


def test_the_nano_is_refused_at_other_widths_not_silently_computed_in_32_bits():
    nano = IcmV3Record(cell_id="N", row=0, col=0, core="nano", core_config={"topology": 0, "routing_mask": ["e"]})
    assert vm.SuperGrid([nano]).width == 32                                    # fine at 32, exactly as before
    with pytest.raises(ValueError, match="nano core is not available at width 18"):
        vm.SuperGrid([nano], width=18)


def test_cores_threaded_but_unverified_at_other_widths_warn_loudly():
    import warnings
    for core, cfg in (("accumulator", {}), ("branch", {}), ("priority", {})):
        rec = IcmV3Record(cell_id="U", row=0, col=0, core=core, core_config=cfg)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            try:
                vm.SuperGrid([rec], width=18)
            except Exception:
                pass                                   # a bare config may be rejected for other reasons; the warning is issued first
        assert any("NOT yet verified" in str(c.message) for c in caught), core
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        vm.SuperGrid([ram("X", 0, 0, [], [])], width=18)
    assert not [c for c in caught if "NOT yet verified" in str(c.message)]       # ram/adder/mul/comparator: verified, so silent
