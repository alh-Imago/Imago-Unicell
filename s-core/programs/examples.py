"""Python answers for the example programs (used as "expect": "programs.examples:vmax_ref" in a job file)."""
M32 = 0xFFFFFFFF
def vmax_ref(inputs, arg, out_len): return [max(inputs) if inputs else 0]
def vprefix_ref(inputs, arg, out_len):
    s, out = 0, []
    for x in inputs: s = (s + x) & M32; out.append(s)
    return out

import struct, zlib
def crc32_ref(inputs, arg, out_len):
    """the real CRC-32 from Python's zlib, over the words as little-endian bytes: independent of this project's code"""
    return [zlib.crc32(struct.pack('<%dI' % len(inputs), *inputs)) & M32]
def vgain_ref(inputs, arg, out_len): return [((x * (arg & 255)) & M32) >> 8 for x in inputs]
