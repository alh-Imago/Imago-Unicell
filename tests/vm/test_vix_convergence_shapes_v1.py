"""tests/vm/test_vix_convergence_shapes_v1.py — points.md #777: real
tests confirming the formalized shape catalog matches every rule
actually proven across `#750`-`#776`, not just a plausible-sounding
decision table.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "nano"))

from vix_convergence_shapes_v1 import ConvergenceShape, choose_convergence_shape  # noqa: E402


def test_no_real_convergence_uses_plain_chain():
    """#756's own already-proven case: a single, already-ordered
    dependency needs no arbitration cell at all."""
    shape = choose_convergence_shape(has_real_convergence=False, is_commutative=True,
                                      all_arrival_ticks_knowable=True)
    assert shape == ConvergenceShape.PLAIN_CHAIN
    # commutativity/timing are irrelevant once there's no real
    # convergence at all -- confirmed the same result either way.
    shape2 = choose_convergence_shape(has_real_convergence=False, is_commutative=False,
                                       all_arrival_ticks_knowable=False)
    assert shape2 == ConvergenceShape.PLAIN_CHAIN


def test_commutative_convergence_uses_priority():
    """#751/#765's own proven case: add/mul-style convergence needs
    only simple, rank-based priority -- no timing equalization at all,
    regardless of whether timing is knowable."""
    shape = choose_convergence_shape(has_real_convergence=True, is_commutative=True,
                                      all_arrival_ticks_knowable=True)
    assert shape == ConvergenceShape.PRIORITY
    shape2 = choose_convergence_shape(has_real_convergence=True, is_commutative=True,
                                       all_arrival_ticks_knowable=False)
    assert shape2 == ConvergenceShape.PRIORITY


def test_non_commutative_with_knowable_timing_uses_stagger():
    """#773's own proven case: subtract-style convergence where both
    real operands (leaves and/or composed results) have a computable
    real arrival tick -- relay-padding equalized to that tick is
    sufficient and has zero head-of-line-blocking cost."""
    shape = choose_convergence_shape(has_real_convergence=True, is_commutative=False,
                                      all_arrival_ticks_knowable=True)
    assert shape == ConvergenceShape.STAGGER


def test_non_commutative_with_unknowable_timing_uses_sequencer():
    """#774's own proven case: a genuinely dynamic operand's own
    arrival tick can't be computed at compile time at all -- stagger
    is structurally inapplicable there; sequencer is the only real
    shape that works, confirmed directly in #774."""
    shape = choose_convergence_shape(has_real_convergence=True, is_commutative=False,
                                      all_arrival_ticks_knowable=False)
    assert shape == ConvergenceShape.SEQUENCER


def test_the_four_real_shapes_are_mutually_exclusive_and_exhaustive():
    """Every real combination of the three real, compile-time-knowable
    facts maps to exactly one shape -- no ambiguous or undefined case."""
    seen = set()
    for conv in (True, False):
        for comm in (True, False):
            for known in (True, False):
                shape = choose_convergence_shape(conv, comm, known)
                assert isinstance(shape, ConvergenceShape)
                seen.add(shape)
    assert seen == set(ConvergenceShape)
