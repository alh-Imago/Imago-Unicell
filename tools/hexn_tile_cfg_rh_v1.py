"""hexn_tile_cfg_rh_v1.py - pack / unpack the config word of sub/verilog/hexn_ramhold_v1.v (3 Nov 2026). Faces 0 N, 1 E, 2 S, 3 W.
An unlisted output reads 7 (constant 0).
Layout (LSB first): ROUTE x FACES (3 bits each) | HOUT 3 (7 = no hold) | DLY 7 = 22 bits at four faces. DLY 2..96 is the planner's hold range."""
FACE = {"N": 0, "E": 1, "S": 2, "W": 3}
HOLD_MIN, HOLD_MAX = 2, 96


def width(faces=4):
    return 3 * faces + 3 + 7


def pack(route=None, hold_out=None, dly=0, faces=4):
    f = lambda x: FACE[x] if isinstance(x, str) else int(x)
    w = 0
    for out in (route or {}):
        assert 0 <= f(out) < faces
    for out in range(faces):                                  # an output that is not listed reads index 7 (constant 0), NOT face 0
        src = {f(o): f(v) for o, v in (route or {}).items()}.get(out, 7)
        assert 0 <= src < 8
        w |= src << (3 * out)
    rw = 3 * faces
    if hold_out is None:
        assert dly == 0; ho = 7
    else:
        assert 0 <= f(hold_out) < faces and HOLD_MIN <= dly <= HOLD_MAX, (hold_out, dly); ho = f(hold_out)
    return w | (ho << rw) | (dly << (rw + 3))


def unpack(w, faces=4):
    rw = 3 * faces
    return dict(route={j: (w >> (3 * j)) & 7 for j in range(faces)}, hold_out=((w >> rw) & 7) if ((w >> rw) & 7) != 7 else None, dly=(w >> (rw + 3)) & 0x7F)
