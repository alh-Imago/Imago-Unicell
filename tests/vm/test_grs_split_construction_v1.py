"""
test_grs_split_construction_v1.py -- points.md #846: a real, placed
SuperGrid construction proving the "split by fan-out, not by a new
core" shape discussed for FP32 rounding metadata (G/R/S riding in a
value's unused top byte).

Real topology, five cells:

    (0,0) producer --east--> (0,1) raw sink
      |
    south (RAW, unmasked -- fan-out is one value broadcast identically,
      |    confirmed directly against the real offer-path code before
      |    building this: apply_addons() runs ONCE per cell, before
      |    broadcasting to every downstream direction simultaneously --
      |    a producer cannot hand one neighbor a masked value and
      |    another the raw one. The mask has to live on a SEPARATE
      |    relay hop instead.)
      v
    (1,0) relay (nibble_mask clears the top byte on ITS OWN output)
      |
    south (masked)
      v
    (2,0) masked sink

Real, honest scope: this proves the MECHANISM shape (fan-out + one
masked relay hop reuses existing addon capability, no new core needed)
using an injected test pattern standing in for a real significand +
G/R/S word -- it does not yet connect to fp32_add_v1.py's own actual
arithmetic, which is separate, later integration work.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

import icm_v3 as v3  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402


def _rec(cell_id, row, col, core, core_config=None, addon_config=None):
    return v3.IcmV3Record(cell_id=cell_id, row=row, col=col, core=core,
                           core_config=core_config or {}, addon_config=addon_config or {})


# Real test pattern: a 24-bit "significand" (0xABCDEF, arbitrary,
# distinctive) with a real G/R/S pattern (G=1, R=0, S=1 -> 0b101) riding
# in bits [26:24] -- the free space confirmed directly against the real
# RTL (adder_cell_v4.v's own 32-bit adder, compare_cell_v4.v's own
# 32-bit compare) neither of which masks or ignores those bits on its
# own; masking is a routing discipline, not automatic.
_SIGNIFICAND = 0xABCDEF
_GRS = 0b101
_RAW_VALUE = (_GRS << 24) | _SIGNIFICAND
_MASKED_VALUE = _SIGNIFICAND   # top byte cleared, low 24 bits unchanged


def test_fan_out_gives_both_paths_the_identical_raw_value():
    """Confirms directly, before the more interesting masked-relay
    check: a single producer's fan-out really is one broadcast value,
    not two independently controllable outputs -- the real constraint
    that makes the relay-hop design necessary in the first place."""
    producer = _rec("producer", 0, 0, "ram",
                     {"downstream_mask": ["e", "s"], "fixed_mode": 1,
                      "load_data_valid": 1, "init_data": _RAW_VALUE})
    raw_sink = _rec("raw_sink", 0, 1, "ram", {"upstream_mask": ["w"]})
    relay = _rec("relay", 1, 0, "ram", {"upstream_mask": ["n"], "downstream_mask": ["s"]})

    grid = SuperGrid([producer, raw_sink, relay])
    for _ in range(5):
        grid.tick()

    assert grid.cells[(0, 1)].ram_data_reg == _RAW_VALUE, "east path must receive the raw, unmasked word"
    assert grid.cells[(1, 0)].ram_data_reg == _RAW_VALUE, "the relay's OWN captured value is also raw -- masking happens on ITS offer, not on capture"


def test_split_by_fan_out_and_one_masked_relay_hop():
    """The real, decisive construction: one path stays raw (direct to
    a sink), the other passes through a single relay cell configured
    to mask its own output before continuing -- no new core, no new
    bus capability, just an existing relay hop with addon_config set."""
    producer = _rec("producer", 0, 0, "ram",
                     {"downstream_mask": ["e", "s"], "fixed_mode": 1,
                      "load_data_valid": 1, "init_data": _RAW_VALUE})
    raw_sink = _rec("raw_sink", 0, 1, "ram", {"upstream_mask": ["w"]})
    # The relay: an ordinary ram_flowing cell, nothing new -- its
    # addon_config (nibble_mask=0b11000000, mask_en=1) is the EXACT
    # same configuration fp32_boundary_v1.extract_mantissa's own
    # stage 1 already uses to clear the top two nibbles, reused here
    # verbatim rather than re-derived.
    relay = _rec("relay", 1, 0, "ram",
                  {"upstream_mask": ["n"], "downstream_mask": ["s"]},
                  {"mask_en": 1, "nibble_mask": 0b11000000})
    masked_sink = _rec("masked_sink", 2, 0, "ram", {"upstream_mask": ["n"]})

    grid = SuperGrid([producer, raw_sink, relay, masked_sink])
    for _ in range(6):
        grid.tick()

    # The real, decisive assertions: same origin, same originally
    # broadcast value, two genuinely different results at the two
    # sinks -- one raw, one masked -- with no new core type anywhere
    # in this grid (every cell here is "ram").
    assert grid.cells[(0, 1)].ram_data_reg == _RAW_VALUE, "direct path: untouched, G/R/S intact"
    assert grid.cells[(2, 0)].ram_data_reg == _MASKED_VALUE, "relayed path: top byte cleared, clean for real arithmetic"
    assert grid.cells[(2, 0)].ram_data_reg & 0xFF000000 == 0, "specifically confirms bits[31:24] are genuinely zero after the relay"
    assert grid.cells[(2, 0)].ram_data_reg & 0x00FFFFFF == _SIGNIFICAND, "and the real 24-bit significand survived the mask intact"


def test_the_relay_hop_costs_one_real_extra_tick():
    """The real, honest cost this design incurs, measured directly
    rather than assumed: the masked path is genuinely one hop longer
    than the direct path, confirmed by checking when each sink's data
    actually becomes valid -- relevant to #544's equal-hop-count rule
    once this is built for real, not just noted in prose."""
    producer = _rec("producer", 0, 0, "ram",
                     {"downstream_mask": ["e", "s"], "fixed_mode": 1,
                      "load_data_valid": 1, "init_data": _RAW_VALUE})
    raw_sink = _rec("raw_sink", 0, 1, "ram", {"upstream_mask": ["w"]})
    relay = _rec("relay", 1, 0, "ram",
                  {"upstream_mask": ["n"], "downstream_mask": ["s"]},
                  {"mask_en": 1, "nibble_mask": 0b11000000})
    masked_sink = _rec("masked_sink", 2, 0, "ram", {"upstream_mask": ["n"]})
    grid = SuperGrid([producer, raw_sink, relay, masked_sink])

    grid.tick()
    grid.tick()   # real, measured: direct delivery takes 2 ticks (offer, then deliver/capture), not 1
    assert grid.cells[(0, 1)].ram_data_valid is True, "direct path: valid after 2 ticks"
    assert grid.cells[(2, 0)].ram_data_valid is False, "masked path: NOT valid yet -- it's one real hop behind"

    grid.tick()   # tick 3: relay's own offer reaches the masked sink
    assert grid.cells[(2, 0)].ram_data_valid is True, "masked path: valid one tick later, confirming the real extra hop"
    assert grid.cells[(2, 0)].ram_data_reg == _MASKED_VALUE
