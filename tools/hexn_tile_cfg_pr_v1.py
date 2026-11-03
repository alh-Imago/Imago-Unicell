"""hexn_tile_cfg_pr_v1.py - pack / unpack the config word of sub/verilog/hexn_tile_pr_v1.v (3 Nov 2026). Faces 0 N, 1 E, 2 S, 3 W.
Layout (LSB first): ROUTE x FACES (3 bits each) | RMASK FACES | MASK 4 | RANKS 8 | MODE 2 | LEN 3 | ORDER 8 = 41 bits at four faces.
Core ports are indexed 0 W, 1 N, 2 S, 3 E (the planner's input order W N S); MASK bit i, RANKS field i and ORDER entries refer to those ports. MODE 0 strict, 1 weighted, 2 sequenced."""
FACE = {"N": 0, "E": 1, "S": 2, "W": 3}


def width(faces=4):
    return 3 * faces + faces + 4 + 8 + 2 + 3 + 8


def pack(route=None, result_to=(), mask=15, ranks=(0, 0, 0, 0), mode=0, length=0, order=(0, 0, 0, 0), faces=4):
    f = lambda x: FACE[x] if isinstance(x, str) else int(x)
    w = 0
    for out, src in (route or {}).items():
        assert 0 <= f(out) < faces and 0 <= f(src) < 8
        w |= f(src) << (3 * f(out))
    rw = 3 * faces
    for o in result_to: assert 0 <= f(o) < faces; w |= 1 << (rw + f(o))
    assert 0 <= mask <= 15 and 0 <= mode <= 2 and 0 <= length <= 4
    w |= mask << (rw + faces)
    for i, k in enumerate(ranks): assert 0 <= k <= 3; w |= k << (rw + faces + 4 + 2 * i)
    w |= mode << (rw + faces + 12); w |= length << (rw + faces + 14)
    for i, k in enumerate(order): assert 0 <= k <= 3; w |= k << (rw + faces + 17 + 2 * i)
    return w


def unpack(w, faces=4):
    rw = 3 * faces; g = lambda lo, n: (w >> lo) & ((1 << n) - 1)
    return dict(route={j: g(3 * j, 3) for j in range(faces)}, result_to=[j for j in range(faces) if g(rw + j, 1)], mask=g(rw + faces, 4),
                ranks=tuple(g(rw + faces + 4 + 2 * i, 2) for i in range(4)), mode=g(rw + faces + 12, 2), length=g(rw + faces + 14, 3),
                order=tuple(g(rw + faces + 17 + 2 * i, 2) for i in range(4)))
