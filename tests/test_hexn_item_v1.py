import os, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import hexn_item_v1 as I, hexn_sensor_shadow_v1 as S
BUILD = dict(nin=24, wb=8, lmax=8)
TABLE = [("rat", 10, 2), ("cat", 28, 4), ("dog", 50, 10), ("sheep", 75, 8), ("deer", 110, 12), ("horse", 150, 12)]
def test_roundtrip_and_lineage():
    p = I.weights_payload([[1, -2, 3]], [-5], 8); a = I.pack(I.T_WEIGHTS, p, usage=1, nin=3, wb=8, trained=b"hand")
    assert I.validate(a, BUILD, 1) == (True, "ok"); h = I.unpack(a); assert h["trained"] == "hand" and I.read_weights(h["payload"]) == ([[1, -2, 3]], [-5], 8)
    b = I.pack(I.T_WEIGHTS, p, usage=1, version=2, nin=3, wb=8, parent=I.item_id(a)); assert I.unpack(b)["parent"] == I.item_id(a)
    assert I.read_settings(I.settings_payload({1: 3, 2: -7})) == {1: 3, 2: -7}
def test_refusals():
    p = I.weights_payload([[1, 2]], [0], 8); a = bytearray(I.pack(I.T_WEIGHTS, p, usage=2, nin=2, wb=8))
    assert not I.validate(bytes(a[:30]), BUILD)[0]
    for pos in (0, 10, 36, 41): c = bytearray(a); c[pos] ^= 1; assert not I.validate(bytes(c), BUILD)[0], pos
    assert "usage" in I.validate(bytes(a), BUILD, 1)[1]
    assert "needs nin" in I.validate(I.pack(I.T_WEIGHTS, p, nin=40, wb=8), BUILD)[1]
    assert "Q14" in I.validate(I.pack(I.T_WEIGHTS, p, nin=2, wb=14), BUILD)[1]
    assert "needs lmax" in I.validate(I.pack(I.T_SETTINGS, I.settings_payload({1: 3}), lmax=9), BUILD)[1]
def test_goals_to_weights_matches_float():
    g = I.goals_payload(TABLE, 24, 80); W = np.array(I.goals_to_weights(g, 8), dtype=float) / 256.0; F = S.prior_w()
    d = W - F; assert d.max() - d.min() < 0.4   # the integer table works in tenths, so it carries a common offset of about ln(10); the spread around that offset is the real difference
    for world in ("A", "B"):
        rng = np.random.default_rng(5); ok = okf = 0
        for _ in range(600):
            a = int(rng.integers(0, 6)); x, _m = S.observe(rng, a, world); ok += int(np.argmax(W @ x)) == a; okf += int(np.argmax(F @ x)) == a
        assert abs(ok - okf) / 600 < 0.02, (world, ok, okf)
