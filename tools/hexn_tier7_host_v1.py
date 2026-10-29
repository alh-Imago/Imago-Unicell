"""Host side of the Kintex memory tier command set (rtl/hexn_tier7_cmd_v1.v): command builders, reply parsers, a Tier7Dev that works on any link with write(bytes) / read(n) (the JTAG link of tools/hexn_jtag_host_v1.py, or the simulation), and dump_all() which reads out every level and saves it to a JSON file.
All numbers little-endian. See the header of rtl/hexn_tier7_cmd_v1.v for the command list. Entry format (all levels): word0 = {1'b1 valid, zeros, hash h} (0 = empty), word1 = value; a DDR3 line holds 8 entries, 8 bytes each (word0, word1)."""
import json
OP_PUT, OP_GET, OP_FLUSH, OP_COUNTERS, OP_INFO, OP_LEVEL, OP_LINE = 0x40, 0x41, 0x42, 0x43, 0x44, 0x45, 0x46
REPLY_LEN = {OP_PUT: 1, OP_GET: 5, OP_FLUSH: 1, OP_COUNTERS: 68, OP_INFO: 8, OP_LEVEL: 8, OP_LINE: 74}
NAMES = ["fast_hit", "sdram_hit", "skip", "sd_get", "fp", "sd_blk_rd", "sd_blk_wr", "buf_hit", "promote_sdram", "promote_sd", "demote_sdram", "demote_sd", "sd_full", "found", "notfound", "put_update", "put_new"]
def u32(v): return (v & 0xFFFFFFFF).to_bytes(4, "little")
def cmd_put(key, val): return bytes([OP_PUT]) + u32(key) + u32(val)
def cmd_get(key): return bytes([OP_GET]) + u32(key)
def cmd_flush(): return bytes([OP_FLUSH])
def cmd_counters(): return bytes([OP_COUNTERS])
def cmd_info(): return bytes([OP_INFO])
def cmd_level(lvl, idx): return bytes([OP_LEVEL, lvl]) + u32(idx)
def cmd_line(n): return bytes([OP_LINE]) + u32(n)
def status(b): return dict(found=b & 1, ddr_err=(b >> 1) & 1, ready=(b >> 2) & 1)
def parse_get(r): return dict(status(r[0]), value=int.from_bytes(r[1:5], "little"))
def parse_counters(r): return {n: int.from_bytes(r[4 * i:4 * i + 4], "little") for i, n in enumerate(NAMES)}
def parse_info(r): return dict(status(r[0]), KW=r[1], VW=r[2], FB=r[3], BMB=r[4], RAMB=r[5], SB=r[6], bucket=r[7])
def parse_level(r): return int.from_bytes(r[0:4], "little"), int.from_bytes(r[4:8], "little")
def parse_line(r):
    ents = [(int.from_bytes(r[2 + 8 * i:6 + 8 * i], "little"), int.from_bytes(r[6 + 8 * i:10 + 8 * i], "little")) for i in range(8)]
    return dict(status(r[0]), written=r[1] & 1, entries=ents)
class Tier7Dev:
    def __init__(self, link): self.l = link
    def _do(self, c): self.l.write(c); return bytes(self.l.read(REPLY_LEN[c[0]]))
    def put(self, k, v): return status(self._do(cmd_put(k, v))[0])
    def get(self, k): return parse_get(self._do(cmd_get(k)))
    def flush(self): return status(self._do(cmd_flush())[0])
    def counters(self): return parse_counters(self._do(cmd_counters()))
    def info(self): return parse_info(self._do(cmd_info()))
    def level(self, lvl, idx): return parse_level(self._do(cmd_level(lvl, idx)))
    def line(self, n): return parse_line(self._do(cmd_line(n)))
    def dump_all(self, path=None, progress=None):
        """Flush, then read levels 0 and 1 and every DDR3 line. Only non-empty entries are kept. Returns (and optionally writes as JSON) the whole store."""
        inf = self.info(); self.flush(); out = dict(info=inf, level0={}, level1={}, lines={}, counters=self.counters())
        for lv, bits, key in ((0, inf["FB"], "level0"), (1, inf["RAMB"], "level1")):
            for i in range(1 << bits):
                w0, w1 = self.level(lv, i)
                if w0 >> 31: out[key][i] = [w0, w1]
                if progress and i % 4096 == 0: progress(key, i)
        for n in range(1 << inf["SB"]):
            d = self.line(n)
            if d["written"]: out["lines"][n] = d["entries"]
            if d["ddr_err"]: out["ddr_err"] = 1
            if progress and n % 4096 == 0: progress("lines", n)
        if path:
            with open(path, "w") as f: json.dump(out, f)
        return out
