"""hexn_tile_cfg_br_v1.py - pack / unpack the config word of sub/verilog/hexn_tile_br_v1.v (3 Nov 2026). Faces 0 N, 1 E, 2 S, 3 W.
Layout (LSB first): ROUTE x FACES (3 bits each) | SELA 3 | SELB 3 | R1MASK FACES | R2MASK FACES | ROUTE_LT 2 | ROUTE_EQ 2 | ROUTE_GT 2 | EMIT 2 | FIXED 32 = 66 bits at four faces.
Route code per outcome: bit 0 = out1, bit 1 = out2 (0 drop, 1 out1, 2 out2, 3 both). Emit: 0 fixed, 1 a, 2 b, 3 a - b."""
FACE = {"N": 0, "E": 1, "S": 2, "W": 3}


def width(faces=4):
    return 3 * faces + 6 + 2 * faces + 8 + 32


def pack(route=None, sela="W", selb="N", out1=(), out2=(), route_lt=1, route_eq=1, route_gt=2, emit=1, fixed=0, faces=4):
    f = lambda x: FACE[x] if isinstance(x, str) else int(x)
    w = 0
    for out, src in (route or {}).items():
        assert 0 <= f(out) < faces and 0 <= f(src) < 8
        w |= f(src) << (3 * f(out))
    rw = 3 * faces
    w |= f(sela) << rw; w |= f(selb) << (rw + 3)
    for o in out1: assert 0 <= f(o) < faces; w |= 1 << (rw + 6 + f(o))
    for o in out2: assert 0 <= f(o) < faces; w |= 1 << (rw + 6 + faces + f(o))
    p = rw + 6 + 2 * faces
    for i, v in enumerate((route_lt, route_eq, route_gt, emit)):
        assert 0 <= v <= 3; w |= v << (p + 2 * i)
    assert 0 <= fixed < (1 << 32)
    return w | (fixed << (p + 8))


def unpack(w, faces=4):
    rw = 3 * faces; p = rw + 6 + 2 * faces
    return dict(route={j: (w >> (3 * j)) & 7 for j in range(faces)}, sela=(w >> rw) & 7, selb=(w >> (rw + 3)) & 7,
                out1=[j for j in range(faces) if (w >> (rw + 6 + j)) & 1], out2=[j for j in range(faces) if (w >> (rw + 6 + faces + j)) & 1],
                route_lt=(w >> p) & 3, route_eq=(w >> (p + 2)) & 3, route_gt=(w >> (p + 4)) & 3, emit=(w >> (p + 6)) & 3, fixed=(w >> (p + 8)) & 0xFFFFFFFF)
