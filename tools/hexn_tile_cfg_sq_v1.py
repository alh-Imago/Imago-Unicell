"""hexn_tile_cfg_sq_v1.py - pack / unpack the config word of sub/verilog/hexn_tile_sq_v1.v (3 Nov 2026). Faces 0 N, 1 E, 2 S, 3 W.
Layout (LSB first): ROUTE x FACES (3 bits each) | SEL 3 (face whose flag lane advances the sequencer) | RMASK FACES | LEN 3 | VALS 128 (four 32-bit values, value 0 lowest) = 150 bits at four faces."""
FACE = {"N": 0, "E": 1, "S": 2, "W": 3}


def width(faces=4):
    return 3 * faces + 3 + faces + 3 + 128


def pack(route=None, sel="W", result_to=(), vals=(), length=None, faces=4):
    f = lambda x: FACE[x] if isinstance(x, str) else int(x)
    vals = list(vals) + [0] * (4 - len(vals)); assert len(vals) == 4 and all(0 <= v < 1 << 32 for v in vals)
    length = len([v for v in vals]) if length is None else length
    assert 0 <= length <= 4
    w = 0
    for out, src in (route or {}).items():
        assert 0 <= f(out) < faces and 0 <= f(src) < 8
        w |= f(src) << (3 * f(out))
    rw = 3 * faces
    w |= f(sel) << rw
    for o in result_to: assert 0 <= f(o) < faces; w |= 1 << (rw + 3 + f(o))
    w |= length << (rw + 3 + faces)
    for i, v in enumerate(vals): w |= v << (rw + 6 + faces + 32 * i)
    return w


def unpack(w, faces=4):
    rw = 3 * faces; g = lambda lo, n: (w >> lo) & ((1 << n) - 1)
    return dict(route={j: g(3 * j, 3) for j in range(faces)}, sel=g(rw, 3), result_to=[j for j in range(faces) if g(rw + 3 + j, 1)],
                length=g(rw + 3 + faces, 3), vals=tuple(g(rw + 6 + faces + 32 * i, 32) for i in range(4)))
