"""Bit-true reference of the 4-level tier hexn_tier_v4 (fast table / SDRAM victim level / SD CARD as a LOG with an exact index in RAM). Python model of the algorithm only. v3 (tools/hexn_tier_ref_v3.py, read-modify-write of hashed sectors) is left untouched; the comparison that led here is tools/hexn_batch_model_v1.py (design row 28 Oct 2026).
Rules for FAST and SDRAM are exactly those of v3 (every key in exactly one level; a new or promoted key takes its fast slot, the resident moves to its SDRAM slot, the SDRAM occupant moves to the card; a GET that finds a key below promotes it; a PUT removes any lower copy first).
CARD LEVEL = LOG. Demoted entries are appended to the OPEN sector (a 64-entry, 512-byte buffer in block RAM); when it is full it is written to the card as ONE whole block (no read first) and the next block is opened. The card holds L = 2^LB blocks used as a circular log (block number = SD_BASE + sector id mod L). An INDEX in RAM (one word per key hash, direct-indexed by the KW-bit hash) says where each card-level key is: (sector id mod L, entry number). So a lookup knows exactly whether the key is on the card (no false alarms, no presence counter) and reads exactly one block, or none when it is in the open sector or in the read buffer (the last block read). A promoted key's index word is cleared and its log entry is dead. When the log gets short of room (open id - tail > L - LOW after a close) the oldest block is read and each of its entries is checked against the index; live ones are re-appended (compaction), then the tail moves on; this runs once at a time (a close during compaction does not start another). If live card entries would exceed CAP = (L - LOW - 2) * 64, a demotion to the card is DROPPED and counted (log_full). flush() writes the open sector as it is (kept open). Reads of a block invalidate the read buffer if that block is later rewritten."""
M = 0xFFFFFFFF
ODD = 0x9E3779B1 | 1
def hashk(k, KW):
    m = (k * ODD) & ((1 << KW) - 1); return m ^ (m >> (KW // 2))
def top(h, nb, KW): return (h >> (KW - nb)) if nb <= KW else h
NAMES = "fast_hit sdram_hit skip card_get card_rd card_wr rbuf_hit open_hit promote_sdram promote_card demote_sdram demote_card gc_rd gc_moved log_full found notfound put_update put_new".split()
class Tier4:
    def __init__(s, KW=18, FB=11, RAMB=12, LB=10, LOW=4, SPS=64):
        s.KW, s.FB, s.RAMB, s.LB, s.LOW, s.SPS = KW, FB, RAMB, LB, LOW, SPS; s.L = 1 << LB; s.CAP = (s.L - LOW - 2) * SPS
        s.fast = {}; s.sdram = {}; s.index = {}; s.blocks = {}; s.obuf = []; s.open_id = 0; s.tail = 0; s.open_dirty = False
        s.rbuf_id = None; s.in_gc = False; s.n = {k: 0 for k in NAMES}
    def _h(s, k):
        h = hashk(k, s.KW)
        return h, h & ((1 << s.FB) - 1), top(h, s.RAMB, s.KW) & ((1 << s.RAMB) - 1)
    def _append(s, h, v):
        s.obuf.append((h, v)); s.index[h] = (s.open_id % s.L, len(s.obuf) - 1); s.open_dirty = True
        if len(s.obuf) == s.SPS: s._close()
    def _write_open(s):
        sid = s.open_id % s.L; s.blocks[sid] = list(s.obuf) + [None] * (s.SPS - len(s.obuf)); s.n["card_wr"] += 1; s.open_dirty = False
        if s.rbuf_id == sid: s.rbuf_id = None
    def _close(s):
        s._write_open(); s.obuf = []; s.open_id += 1
        if not s.in_gc:
            s.in_gc = True
            while s.open_id - s.tail > s.L - s.LOW: s._gc()
            s.in_gc = False
    def _gc(s):
        sid = s.tail % s.L; s.tail += 1; ent = s.blocks[sid]; s.n["card_rd"] += 1; s.n["gc_rd"] += 1; s.rbuf_id = sid
        for i in range(s.SPS):
            e = ent[i]
            if e is not None and s.index.get(e[0]) == (sid, i): s.n["gc_moved"] += 1; s._append(e[0], e[1])
    def flush(s):
        if s.open_dirty and s.obuf: s._write_open()
    def _ins_fast(s, h, v):
        f = h & ((1 << s.FB) - 1); old = s.fast.get(f); s.fast[f] = (h, v)
        if old is not None: s._ins_sdram(*old)
    def _ins_sdram(s, h, v):
        s.n["demote_sdram"] += 1
        sl = top(h, s.RAMB, s.KW) & ((1 << s.RAMB) - 1); old = s.sdram.get(sl); s.sdram[sl] = (h, v)
        if old is not None: s._ins_card(*old)
    def _ins_card(s, h, v):
        s.n["demote_card"] += 1
        if len(s.index) >= s.CAP: s.n["log_full"] += 1; return
        s._append(h, v)
    def _locate(s, h, sl):
        e = s.sdram.get(sl)
        if e is not None and e[0] == h:
            del s.sdram[sl]; s.n["sdram_hit"] += 1; s.n["promote_sdram"] += 1; return e[1]
        loc = s.index.get(h)
        if loc is None: s.n["skip"] += 1; return None
        s.n["card_get"] += 1; sid, i = loc
        if sid == s.open_id % s.L: v = s.obuf[i][1]; s.n["open_hit"] += 1
        else:
            if s.rbuf_id == sid: s.n["rbuf_hit"] += 1
            else: s.n["card_rd"] += 1; s.rbuf_id = sid
            v = s.blocks[sid][i][1]
        del s.index[h]; s.n["promote_card"] += 1; return v
    def get(s, k):
        h, f, sl = s._h(k); e = s.fast.get(f)
        if e is not None and e[0] == h: s.n["fast_hit"] += 1; s.n["found"] += 1; return True, e[1]
        v = s._locate(h, sl)
        if v is None: s.n["notfound"] += 1; return False, 0
        s.n["found"] += 1; s._ins_fast(h, v); return True, v
    def put(s, k, v):
        h, f, sl = s._h(k); e = s.fast.get(f)
        if e is not None and e[0] == h: s.fast[f] = (h, v); s.n["put_update"] += 1; return
        s.n["put_new"] += 1; s._locate(h, sl); s._ins_fast(h, v)
