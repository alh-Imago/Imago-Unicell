import os, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import hexn_multiout_int_v1 as MO, hexn_item_v1 as I, hexn_sensor_shadow_v1 as S
def test_whole_number_step_tracks_the_decimal_rule():
    g = I.goals_payload([("rat", 10, 2), ("cat", 28, 4), ("dog", 50, 10), ("sheep", 75, 8), ("deer", 110, 12), ("horse", 150, 12)], 24, 80); Wq = I.goals_to_weights(g, 8); S.LR = 1.5
    d_all = i_all = 0.0
    for sd in range(12):
        rng = np.random.default_rng(50 + sd); test = [(a, *S.observe(rng, a, "B")) for a in rng.integers(0, 6, 200)]; stream = [(a, *S.observe(rng, a, "B")) for a in rng.integers(0, 6, 60)]
        d = S.Arm("neural"); d.W = np.array(Wq, dtype=float) / 256.0; mi = MO.MultiOutInt(Wq)
        for a, x, m in stream: d.learn(x, m, a); mi.learn([int(v) for v in x], a)
        d_all += np.mean([d.predict(x, m) == a for a, x, m in test]); i_all += np.mean([mi.predict([int(v) for v in x]) == a for a, x, m in test])
        assert all(isinstance(v, int) for r in mi.W for v in r) and mi.wmax < 32768
    assert abs(d_all - i_all) / 12 < 0.02 and i_all / 12 > 0.8
