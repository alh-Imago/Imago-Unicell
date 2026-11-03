"""hexn_tile_cfg_pr_v2.py - pack / unpack the config word of sub/verilog/hexn_tile_pr_v2.v (3 Nov 2026; v1 untouched): the v1 word (hexn_tile_cfg_pr_v1) plus PSEL, 12 bits on top: the face (3 bits each) that core port 0, 1, 2, 3 reads; default (3, 0, 2, 1) = the v1 ports W, N, S, E at four faces. 53 bits at four faces."""
import hexn_tile_cfg_pr_v1 as V1
FACE = V1.FACE


def width(faces=4): return V1.width(faces) + 12


def pack(route=None, result_to=(), mask=15, ranks=(0, 0, 0, 0), mode=0, length=0, order=(0, 0, 0, 0), psel=(3, 0, 2, 1), faces=4):
    f = lambda x: FACE[x] if isinstance(x, str) else int(x)
    w = V1.pack(route, result_to, mask, ranks, mode, length, order, faces)
    for i, p in enumerate(psel): assert 0 <= f(p) < 8; w |= f(p) << (V1.width(faces) + 3 * i)
    return w


def unpack(w, faces=4):
    u = V1.unpack(w & ((1 << V1.width(faces)) - 1)); b = V1.width(faces)
    u["psel"] = [(w >> (b + 3 * i)) & 7 for i in range(4)]; return u
