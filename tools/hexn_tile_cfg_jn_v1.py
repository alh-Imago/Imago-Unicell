"""hexn_tile_cfg_jn_v1.py - pack / unpack the config word of sub/verilog/hexn_tile_jn_v1.v (JOIN core; same word as the AL tile, OP adds lt 5, min 6, max 7) (3 Nov 2026). Faces 0 N, 1 E, 2 S, 3 W.
Layout (LSB first): ROUTE x FACES (3 bits each), SELA 3, SELB 3, RMASK FACES, OP 3 = 25 bits at four faces. OPS: add 0, sub 1, and 2, or 3, xor 4."""
FACE = {"N": 0, "E": 1, "S": 2, "W": 3}
OPS = {"add": 0, "sub": 1, "and": 2, "or": 3, "xor": 4, "lt": 5, "min": 6, "max": 7}


def width(faces=4):
    return 3 * faces + 6 + faces + 3


def pack(route=None, sela="W", selb="N", result_to=(), op="add", faces=4):
    f = lambda x: FACE[x] if isinstance(x, str) else int(x)
    w = 0
    for out, src in (route or {}).items():
        assert 0 <= f(out) < faces and 0 <= f(src) < 8
        w |= f(src) << (3 * f(out))
    rw = 3 * faces
    w |= f(sela) << rw
    w |= f(selb) << (rw + 3)
    for o in result_to:
        assert 0 <= f(o) < faces
        w |= 1 << (rw + 6 + f(o))
    assert op in OPS
    w |= OPS[op] << (rw + 6 + faces)
    return w


def unpack(w, faces=4):
    rw = 3 * faces; ops = {v: n for n, v in OPS.items()}
    return dict(route={j: (w >> (3 * j)) & 7 for j in range(faces)}, sela=(w >> rw) & 7, selb=(w >> (rw + 3)) & 7,
                result_to=[j for j in range(faces) if (w >> (rw + 6 + j)) & 1], op=ops[(w >> (rw + 6 + faces)) & 7])
