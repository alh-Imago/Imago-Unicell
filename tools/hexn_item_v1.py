"""hexn_item_v1: THE LOADABLE ITEM (40-byte header + payload) AND THE GOALS-TO-WEIGHTS STEP IN WHOLE NUMBERS (Python; model only; new file 31 Oct 2026). Alan, 14:55: 'yes thanks' to designing the item header and the goals-to-weights step (docs/hex-n/PROFILE_v1.md section 3; byte layout in docs/hex-n/ITEM_FORMAT_v1.md).
Header, little-endian, 40 bytes: 0 magic 'HXI1' | 4 type u8 | 5 usage u8 | 6 item version u16 | 8 payload length u32 | 12 needs: nin u8, wb u8, lmax u8, flags u8 | 16 parent id u32 | 20 created u32 | 24 trained-on tag 8 ascii bytes | 32 payload crc32 u32 | 36 header crc32 u32 (over bytes 0 to 35).
Types: 1 goals, 2 weights, 3 settings, 4 detector, 5 history, 6 memory, 7 target. Usage: 0 any, 1 game, 2 sensor. 'needs' of 0 means no requirement. parent id = crc32 of the parent item's whole bytes (0 = none).
Payloads fixed here: goals (K u8, nbins u8, bin width in tenths of a unit u16, then K x [name 8 ascii, mean u16 tenths, sd u16 tenths]); weights (nout u8, nin u8, wb u8, pad u8, then per output nin x i16 and one i32 bias); settings (count u8, then count x [key u8, value i32]); target (u8: 0 esp, 1 host, 2 onboard). Types 4, 5, 6 carry an opaque payload for now (format not yet fixed).
validate(item, build, usage) returns (ok, reason): refuses a bad magic, a bad header or payload checksum, a payload length that does not match, an item whose needs exceed the build, or one for another usage than the user chose.
goals_to_weights(payload, wb) is the integer version of the shadow test's prior: score(animal, bin) = max(-z^2/2, -8) - ln(max(sd, 3)) with z = (bin centre - mean) / max(sd, 3); only integer arithmetic (z^2 as an integer ratio, ln from the bit length with a straight-line fraction)."""
import struct, zlib
MAGIC = b"HXI1"; T_GOALS, T_WEIGHTS, T_SETTINGS, T_DETECTOR, T_HISTORY, T_MEMORY, T_TARGET = 1, 2, 3, 4, 5, 6, 7
def pack(type_, payload, usage=0, version=1, nin=0, wb=0, lmax=0, flags=0, parent=0, created=0, trained=b""):
    h = MAGIC + struct.pack("<BBHIBBBBII8sI", type_, usage, version, len(payload), nin, wb, lmax, flags, parent, created, trained[:8].ljust(8, b" "), zlib.crc32(payload) & 0xFFFFFFFF)
    return h + struct.pack("<I", zlib.crc32(h) & 0xFFFFFFFF) + payload
def unpack(b):
    if len(b) < 40: raise ValueError("short")
    f = struct.unpack("<4sBBHIBBBBII8sII", b[:40]); return dict(magic=f[0], type=f[1], usage=f[2], version=f[3], length=f[4], nin=f[5], wb=f[6], lmax=f[7], flags=f[8], parent=f[9], created=f[10], trained=f[11].decode("ascii", "replace").strip(), pcrc=f[12], hcrc=f[13], payload=b[40:])
def item_id(b): return zlib.crc32(b) & 0xFFFFFFFF
def validate(b, build, usage=0):
    try: h = unpack(b)
    except ValueError: return False, "item shorter than its header"
    if h["magic"] != MAGIC: return False, "bad magic"
    if zlib.crc32(b[:36]) & 0xFFFFFFFF != h["hcrc"]: return False, "header checksum"
    if len(h["payload"]) != h["length"]: return False, "payload length %d, header says %d" % (len(h["payload"]), h["length"])
    if zlib.crc32(h["payload"]) & 0xFFFFFFFF != h["pcrc"]: return False, "payload checksum"
    for k in ("nin", "wb", "lmax"):
        if h[k] and h[k] > build.get(k, 0) and k != "wb": return False, "needs %s %d, build has %d" % (k, h[k], build.get(k, 0))
    if h["wb"] and h["wb"] != build.get("wb", 0) and h["type"] == T_WEIGHTS: return False, "weights are Q%d, this build is Q%d" % (h["wb"], build.get("wb", 0))
    if usage and h["usage"] and h["usage"] != usage: return False, "item is for usage %d, chosen usage is %d" % (h["usage"], usage)
    return True, "ok"
def goals_payload(table, nbins, bw10):
    p = struct.pack("<BBH", len(table), nbins, bw10)
    for name, mu, sd in table: p += struct.pack("<8sHH", name.encode()[:8].ljust(8, b" "), int(round(mu * 10)), int(round(sd * 10)))
    return p
def weights_payload(W, B, wb):
    nout, nin = len(W), len(W[0]); p = struct.pack("<BBBB", nout, nin, wb, 0)
    for k in range(nout): p += struct.pack("<%dh" % nin, *W[k]) + struct.pack("<i", B[k])
    return p
def read_weights(p):
    nout, nin, wb, _ = struct.unpack("<BBBB", p[:4]); o = 4; W = []; B = []
    for k in range(nout): W.append(list(struct.unpack_from("<%dh" % nin, p, o))); o += 2 * nin; B.append(struct.unpack_from("<i", p, o)[0]); o += 4
    return W, B, wb
def settings_payload(d): return struct.pack("<B", len(d)) + b"".join(struct.pack("<Bi", k, v) for k, v in d.items())
def read_settings(p): n = p[0]; return {struct.unpack_from("<Bi", p, 1 + 5 * i)[0]: struct.unpack_from("<Bi", p, 1 + 5 * i)[1] for i in range(n)}
def ln_q8(x):
    """natural log of an integer x >= 1 in Q8, straight-line between powers of two"""
    l2 = x.bit_length() - 1; fr = ((x - (1 << l2)) << 8) >> l2; return ((l2 << 8) + fr) * 177 >> 8
def goals_to_weights(p, wb=8):
    K, nb, bw10 = struct.unpack("<BBH", p[:4]); W = []
    for k in range(K):
        _, mu10, sd10 = struct.unpack_from("<8sHH", p, 4 + 12 * k); sd10 = max(sd10, 30); row = []
        for b in range(nb):
            c10 = (2 * b + 1) * bw10 // 2                       # bin centre in tenths
            z2 = ((c10 - mu10) ** 2 << 8) // (sd10 * sd10)      # z^2 in Q8
            s = max(-(z2 >> 1), -8 * 256) - ln_q8(sd10)          # Q8 score
            row.append(int(round(s * (1 << wb) / 256.0)))
        W.append(row)
    return W
