"""Bit-true reference of the 4-level tier hexn_tier_v3 (fast table / SDRAM / SD card, with a presence counter for the card). Python model of the algorithm only; the RTL is checked against it by tests/test_hexn_tier_v3.py.
Alan, 28 Oct 2026: long-term patterns on the card, the fast table built into the design, the next level in the RAM (the three-tier decision), now with the hardware-simple moving rules chosen here (NOT the weight-based rules of tools/hexn_layer3_tiers_v1.py, which need a search of whole tiers):
 - Every key lives in exactly ONE level. FAST: direct-mapped by the low FB bits of the reversible hash h (tag = the other bits). SDRAM: direct-mapped by the top RAMB bits of h (a victim level for the fast table). CARD: sectors of 64 entries (512 bytes, 8 bytes each), the sector chosen by the top SB bits of h, any free entry in the sector.
 - Insert into FAST (a put of a new key, or a key promoted by a lookup): the key takes its fast slot, the previous resident (if any) moves DOWN to its SDRAM slot, whose previous occupant (if any) moves down to its card sector. A card sector that is full drops the entry (counted: sd_full).
 - GET: fast hit -> answer. Else SDRAM slot holds the key -> answer, the entry is PROMOTED (inserted into FAST, cascade as above). Else the presence counter of the key's bucket (BMB bits, 4-bit, saturating at 15 and then sticky) is 0 -> not found without touching the card (skip). Else the sector is searched (one card read unless it is in the one-sector write-back buffer): found -> removed from the sector and promoted; not found -> false alarm (fp).
 - PUT: fast slot holds the key -> value replaced. Else the key is looked for in SDRAM and on the card exactly as a GET does (and removed there), then inserted into FAST with the new value.
 - Card access goes through ONE sector buffer with write-back: asking for a sector that is not in the buffer first writes the buffer back if it was changed (sd_blk_wr), then reads the wanted sector (sd_blk_rd) unless the sector was never written (then the buffer starts empty). flush() writes the buffer back."""
M = 0xFFFFFFFF
ODD = 0x9E3779B1 | 1
def hashk(k, KW):
    m = (k * ODD) & ((1 << KW) - 1); return m ^ (m >> (KW // 2))
def top(h, nb, KW): return (h >> (KW - nb)) if nb <= KW else h
class Tier3:
    def __init__(s, KW=18, FB=11, BMB=16, RAMB=12, SB=10, SPS=64):
        s.KW, s.FB, s.BMB, s.RAMB, s.SB, s.SPS = KW, FB, BMB, RAMB, SB, SPS
        s.fast = {}; s.sdram = {}; s.sec = {}; s.written = set(); s.cnt = {}
        s.cur = None; s.buf = None; s.dirty = False
        s.n = dict(fast_hit=0, sdram_hit=0, skip=0, sd_get=0, fp=0, sd_blk_rd=0, sd_blk_wr=0, buf_hit=0, promote_sdram=0, promote_sd=0, demote_sdram=0, demote_sd=0, sd_full=0, found=0, notfound=0, put_update=0, put_new=0)
    def _h(s, k):
        h = hashk(k, s.KW)
        return h, h & ((1 << s.FB) - 1), top(h, s.RAMB, s.KW) & ((1 << s.RAMB) - 1), top(h, s.SB, s.KW) & ((1 << s.SB) - 1), (h ^ top(h, s.BMB, s.KW)) & ((1 << s.BMB) - 1)
    def _access(s, sec):
        if s.cur == sec: s.n["buf_hit"] += 1; return
        if s.cur is not None and s.dirty:
            s.sec[s.cur] = list(s.buf); s.written.add(s.cur); s.n["sd_blk_wr"] += 1
        if sec in s.written: s.buf = list(s.sec[sec]); s.n["sd_blk_rd"] += 1
        else: s.buf = [None] * s.SPS
        s.cur = sec; s.dirty = False
    def flush(s):
        if s.cur is not None and s.dirty:
            s.sec[s.cur] = list(s.buf); s.written.add(s.cur); s.n["sd_blk_wr"] += 1; s.dirty = False
    def _cnt(s, hb, d):
        c = s.cnt.get(hb, 0)
        if c == 15: return
        s.cnt[hb] = c + d
    def _bucket(s, h): return (h ^ top(h, s.BMB, s.KW)) & ((1 << s.BMB) - 1)
    def _ins_fast(s, h, v):
        f = h & ((1 << s.FB) - 1); old = s.fast.get(f); s.fast[f] = (h, v)
        if old is not None: s._ins_sdram(*old)
    def _ins_sdram(s, h, v):
        s.n["demote_sdram"] += 1
        sl = top(h, s.RAMB, s.KW) & ((1 << s.RAMB) - 1); old = s.sdram.get(sl); s.sdram[sl] = (h, v)
        if old is not None: s._ins_sd(*old)
    def _ins_sd(s, h, v):
        s.n["demote_sd"] += 1
        sec = top(h, s.SB, s.KW) & ((1 << s.SB) - 1); s._access(sec)
        for i in range(s.SPS):
            if s.buf[i] is None:
                s.buf[i] = (h, v); s.dirty = True; s._cnt(s._bucket(h), +1); return
        s.n["sd_full"] += 1
    def _locate(s, h, sl, sec, hb):
        """Look below the fast level; remove and return the value if found, else None."""
        e = s.sdram.get(sl)
        if e is not None and e[0] == h:
            del s.sdram[sl]; s.n["sdram_hit"] += 1; s.n["promote_sdram"] += 1; return e[1]
        if s.cnt.get(hb, 0) == 0: s.n["skip"] += 1; return None
        s.n["sd_get"] += 1; s._access(sec)
        for i in range(s.SPS):
            if s.buf[i] is not None and s.buf[i][0] == h:
                v = s.buf[i][1]; s.buf[i] = None; s.dirty = True; s._cnt(hb, -1); s.n["promote_sd"] += 1; return v
        s.n["fp"] += 1; return None
    def get(s, k):
        h, f, sl, sec, hb = s._h(k); e = s.fast.get(f)
        if e is not None and e[0] == h: s.n["fast_hit"] += 1; s.n["found"] += 1; return True, e[1]
        v = s._locate(h, sl, sec, hb)
        if v is None: s.n["notfound"] += 1; return False, 0
        s.n["found"] += 1; s._ins_fast(h, v); return True, v
    def put(s, k, v):
        h, f, sl, sec, hb = s._h(k); e = s.fast.get(f)
        if e is not None and e[0] == h: s.fast[f] = (h, v); s.n["put_update"] += 1; return
        s.n["put_new"] += 1; s._locate(h, sl, sec, hb); s._ins_fast(h, v)
