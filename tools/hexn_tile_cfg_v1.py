"""hexn_tile_cfg_v1.py - pack / unpack the config word of sub/verilog/hexn_tile_v1.v (2 Nov 2026).
Faces: 0 N, 1 E, 2 S, 3 W.  Layout (LSB first): ROUTE x FACES (3 bits each), SELA 3, RMASK FACES, OP 3, K 5, MASK 8.
OPS are the unary core's: cp 0, shl 1, shr 2, mask 3, inv 4, acc 5.  chain_bits(words) -> the bit list to shift in, FARTHEST tile first, MSB of each word first."""
FACE = {"N": 0, "E": 1, "S": 2, "W": 3}
OPS = {"cp": 0, "shl": 1, "shr": 2, "mask": 3, "inv": 4, "acc": 5}


def width(faces=4):
    return 3 * faces + 3 + faces + 3 + 5 + 8


def pack(route=None, sela="W", result_to=(), op="cp", k=0, mask=0xFF, faces=4):
    """route: {out face: in face} (letters or indices; unlisted outputs read input 0); result_to: output faces that carry the core's result"""
    f = lambda x: FACE[x] if isinstance(x, str) else int(x)
    w = 0
    for out, src in (route or {}).items():
        assert 0 <= f(out) < faces and 0 <= f(src) < 8
        w |= f(src) << (3 * f(out))
    rw = 3 * faces
    w |= f(sela) << rw
    for o in result_to:
        assert 0 <= f(o) < faces
        w |= 1 << (rw + 3 + f(o))
    assert op in OPS and 0 <= k < 32 and 0 <= mask < 256
    w |= OPS[op] << (rw + 3 + faces)
    w |= k << (rw + 6 + faces)
    w |= mask << (rw + 11 + faces)
    return w


def unpack(w, faces=4):
    rw = 3 * faces
    ops = {v: n for n, v in OPS.items()}
    return dict(route={j: (w >> (3 * j)) & 7 for j in range(faces)}, sela=(w >> rw) & 7, result_to=[j for j in range(faces) if (w >> (rw + 3 + j)) & 1],
                op=ops.get((w >> (rw + 3 + faces)) & 7, "acc"), k=(w >> (rw + 6 + faces)) & 31, mask=(w >> (rw + 11 + faces)) & 255)


def chain_bits(words, faces=4):
    """words: config words in chain order, NEAREST the chain input first. The farthest tile (last) is shifted in first."""
    n = width(faces)
    bits = []
    for w in reversed(list(words)):
        bits += [(w >> i) & 1 for i in range(n - 1, -1, -1)]
    return bits
