"""Tests for tools/hexn_feedback_v1.py (Python model: small detector with online local update / feedback bit)."""
import importlib.util, os, statistics as st
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sp = importlib.util.spec_from_file_location("fb", os.path.join(ROOT, "tools", "hexn_feedback_v1.py")); F = importlib.util.module_from_spec(sp); sp.loader.exec_module(F)

def test_deterministic():
    assert F.run(1, "A", "loc", S=2, N=1000) == F.run(1, "A", "loc", S=2, N=1000)

def test_local_rule_beats_frozen_from_tiny_start():
    f = st.mean(st.mean(F.run(s, "A", "frozen", S=2, N=1500)[-2:]) for s in range(6))
    l = st.mean(st.mean(F.run(s, "A", "loc", S=2, N=1500)[-2:]) for s in range(6))
    assert l > f + 0.05  # recorded: 0.64 -> 0.78

def test_frozen_arm_never_changes_weights():
    import random
    r = F.R; rnd = random.Random(0); tpl = r.templates(rnd, 4, 12, 4)
    tr = [(r.sample(rnd, tpl[c], 0.1), c) for c in range(4) for _ in range(4)]
    m = F.Online([x for x, _ in tr], [c for _, c in tr], 4, 4); w0 = [row[:] for row in m.w]
    m.answer(tr[0][0]); assert m.w == w0
