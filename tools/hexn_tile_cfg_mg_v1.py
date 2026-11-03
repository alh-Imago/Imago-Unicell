"""hexn_tile_cfg_mg_v1.py - pack / unpack the config word of sub/verilog/hexn_tile_mg_v1.v (3 Nov 2026). Faces 0 N, 1 E, 2 S, 3 W.
Layout (LSB first): ROUTE x FACES (3 bits each) | SELA 3 | SELB 3 | RMASK FACES | MODE 2 = 24 bits at four faces. MODE: 0 A only, 1 B only, 2 arbitrate, 3 join-OR."""
FACE = {"N": 0, "E": 1, "S": 2, "W": 3}


def width(faces=4):
    return 3 * faces + 6 + faces + 2


def pack(route=None, sela="W", selb="N", result_to=(), mode=2, faces=4):
    f = lambda x: FACE[x] if isinstance(x, str) else int(x)
    w = 0
    for out, src in (route or {}).items():
        assert 0 <= f(out) < faces and 0 <= f(src) < 8
        w |= f(src) << (3 * f(out))
    rw = 3 * faces
    w |= f(sela) << rw; w |= f(selb) << (rw + 3)
    for o in result_to: assert 0 <= f(o) < faces; w |= 1 << (rw + 6 + f(o))
    assert 0 <= mode <= 3
    return w | (mode << (rw + 6 + faces))


def unpack(w, faces=4):
    rw = 3 * faces
    return dict(route={j: (w >> (3 * j)) & 7 for j in range(faces)}, sela=(w >> rw) & 7, selb=(w >> (rw + 3)) & 7,
                result_to=[j for j in range(faces) if (w >> (rw + 6 + j)) & 1], mode=(w >> (rw + 6 + faces)) & 3)
