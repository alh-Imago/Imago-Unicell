"""tests/vm/test_plain_place_advice_v1.py -- ledger #1065: placer refusals say what to change, in plain words.

The technical text stays in `problem`; `why` and `try` are the reading of it. Checks the messages exist, name the fix (`routed_x`) where it helps, and that routed_x does not send you
back to itself."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
for sub in ("nano", "tools", os.path.join("tests", "vm")):
    sys.path.insert(0, os.path.join(ROOT, sub))

import llvm_dag_frontend_v1 as F  # noqa: E402
from test_fanout_relay_tree_v1 import many_readers_ir  # noqa: E402


def test_default_placer_refusal_points_at_routed_x_and_is_plain():
    res, diags = F.compile_llvm_via_dag(many_readers_ir(5))
    assert res is None
    d = diags[0]
    assert d.stage == "place" and "routed_x" in d.suggestion and "flat grid" in d.why
    assert "no free path" in d.problem                      # the technical text is still there


def test_routed_x_refusal_does_not_tell_you_to_use_routed_x():
    why, fix = F.plain_place_advice("routed_x", "negotiated congestion did not resolve in 40 iterations")
    assert "routed_x" not in fix and "split" in fix


def test_each_known_refusal_has_its_own_advice():
    kinds = ["x: every operand is a constant", "edge a->b: no free output or input face", "edge a->b: no free path",
             "negotiated congestion did not resolve", "the layout does not fit a 4x4 grid"]
    texts = {F.plain_place_advice("routed", k) for k in kinds}
    assert len(texts) == 4                                  # the two routing messages share one reading
    assert all(w and f for w, f in texts)


def test_literal_only_operation_message_mentions_the_fix():
    res, diags = F.compile_llvm_via_dag("define i32 @f(i32 %a) {\nentry:\n  %r = add i32 3, 4\n  ret i32 %r\n}\n")
    assert res is None and "routed_x" in diags[0].suggestion
