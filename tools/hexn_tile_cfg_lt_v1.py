"""hexn_tile_cfg_lt_v1.py - pack / unpack the config word of sub/verilog/hexn_tile_lt_v1.v (3 Nov 2026). Faces 0 N, 1 E, 2 S, 3 W.
Layout (LSB first): ROUTE x FACES (3 bits each) | SELS 3 | SELC 3 | SELT 3 (faces whose flag lane sets / clears / toggles; 7 = never) | RMASK FACES = 25 bits at four faces."""
FACE = {"N": 0, "E": 1, "S": 2, "W": 3}


def width(faces=4):
    return 3 * faces + 9 + faces


def pack(route=None, sels=7, selc=7, selt=7, result_to=(), faces=4):
    f = lambda x: FACE[x] if isinstance(x, str) else int(x)
    w = 0
    for out, src in (route or {}).items():
        assert 0 <= f(out) < faces and 0 <= f(src) < 8
        w |= f(src) << (3 * f(out))
    rw = 3 * faces
    w |= f(sels) << rw; w |= f(selc) << (rw + 3); w |= f(selt) << (rw + 6)
    for o in result_to: assert 0 <= f(o) < faces; w |= 1 << (rw + 9 + f(o))
    return w


def unpack(w, faces=4):
    rw = 3 * faces; g = lambda lo, n: (w >> lo) & ((1 << n) - 1)
    return dict(route={j: g(3 * j, 3) for j in range(faces)}, sels=g(rw, 3), selc=g(rw + 3, 3), selt=g(rw + 6, 3), result_to=[j for j in range(faces) if g(rw + 9 + j, 1)])
