"""Reference model of the card format and the log of hexn_tier_v5 (Python model only; no RTL yet). New file: v4 (tools/hexn_tier_ref_v4.py) is left untouched. The card here is REAL BYTES, so the block format is tested, not just described.
What is new against v4 (design row 28 Oct 2026, CARD_FORMAT_v1.md):
 * LOG BLOCK = 512 bytes: 16-byte header + 62 entries of 8 bytes. Header: byte 0 volume id, bytes 1-5 sequence number (40 bits, little endian, first block = 1), byte 6 entry count, byte 7 format version (1), bytes 8-9 magic 0x4858, bytes 10-11 CRC16 (CCITT, over the whole block with these two bytes zero), bytes 12-15 zero. Entry = tag word + value word, little endian. Tag: bit 31 set = live entry, bit 30 set = TOMBSTONE, low KW bits = the key hash; tag 0 = unused. The block position on the card is (sequence - 1) mod L.
 * TOMBSTONE: when a key is promoted away from the card (a GET or a PUT that finds it there) its old log entry stays on the card, so a tombstone is appended to the log; a restore replays the log in sequence order and a tombstone removes the key. Compaction drops tombstones (a tombstone is always newer than the entry it kills, and blocks are reclaimed oldest first).
 * SAVE (drain): every fast and SDRAM entry is moved down into the log and the open sector is written (flush). Entries that do not fit (CAP) are dropped and counted in log_full; save() returns how many were lost.
 * POWER LOSS and RESTORE BY SCAN (no checkpoint yet): RAM is lost, the card stays. restore() reads all L blocks (pass 1, finds valid blocks: magic, version, volume, CRC16, position), then replays the valid ones oldest sequence first (pass 2), live entry sets the index word, tombstone clears it. Fast table and SDRAM level start empty. Reads counted in scan_rd: L + the number of valid blocks. bad_blocks counts blocks whose magic field is non-zero but that fail a check (a block with an empty magic field is taken as never written, because the hardware cannot tell the two apart).
 * What a crash gives back: the state at the last durable block write. A GET or PUT that happened after it, and anything still in the fast table, the SDRAM level or the open sector, is gone. A key that was only in RAM is absent; a key that had been demoted to the card comes back with its last durable value, which can be older than the value it had in RAM. LOW must be at least 3: a compacted block's live entries are re-appended within the next two blocks and the old block is only overwritten LOW-1 blocks later, so a torn write of a block can only destroy entries that exist elsewhere."""
M32 = 0xFFFFFFFF
ODD = 0x9E3779B1 | 1
HDR, ESZ, BLK, EPB_MAX, MAGIC, FMT = 16, 8, 512, 62, 0x4858, 1
def hashk(k, KW):
    m = (k * ODD) & ((1 << KW) - 1); return m ^ (m >> (KW // 2))
def top(h, nb, KW): return (h >> (KW - nb)) if nb <= KW else h
def crc16(data, crc=0xFFFF):
    for b in data:
        crc ^= b << 8
        for _ in range(8): crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc
def make_block(vol, seq, ents):
    """ents: list of (kind, key hash, value), kind 'L' live or 'T' tombstone; at most 62."""
    assert len(ents) <= EPB_MAX
    b = bytearray(BLK); b[0] = vol; b[1:6] = seq.to_bytes(5, "little"); b[6] = len(ents); b[7] = FMT; b[8:10] = MAGIC.to_bytes(2, "little")
    for i, (kind, h, v) in enumerate(ents):
        tag = ((1 << 31) if kind == "L" else (1 << 30)) | h
        b[HDR + ESZ * i: HDR + ESZ * i + 4] = tag.to_bytes(4, "little"); b[HDR + ESZ * i + 4: HDR + ESZ * i + 8] = v.to_bytes(4, "little")
    b[10:12] = crc16(bytes(b)).to_bytes(2, "little"); return bytes(b)
def parse_block(raw, vol):
    """Returns (sequence, [(kind, hash, value), ...]) or None when the block is not a valid block of this volume."""
    if raw is None or len(raw) != BLK or int.from_bytes(raw[8:10], "little") != MAGIC or raw[7] != FMT or raw[0] != vol or raw[6] > EPB_MAX: return None
    z = bytearray(raw); z[10:12] = b"\0\0"
    if crc16(bytes(z)) != int.from_bytes(raw[10:12], "little"): return None
    ents = []
    for i in range(raw[6]):
        tag = int.from_bytes(raw[HDR + ESZ * i: HDR + ESZ * i + 4], "little"); v = int.from_bytes(raw[HDR + ESZ * i + 4: HDR + ESZ * i + 8], "little")
        if tag & (1 << 31): ents.append(("L", tag & ~(3 << 30) & M32, v))
        elif tag & (1 << 30): ents.append(("T", tag & ~(3 << 30) & M32, v))
        else: ents.append((None, 0, 0))
    return int.from_bytes(raw[1:6], "little"), ents
NAMES = ("fast_hit sdram_hit skip card_get card_rd card_wr rbuf_hit open_hit promote_sdram promote_card demote_sdram demote_card gc_rd gc_moved log_full found notfound put_update put_new "
         "tomb_wr tomb_dropped scan_rd replay_live replay_tomb bad_blocks drain_fast drain_sdram").split()
class PowerLoss(Exception): pass
class Tier5:
    def __init__(s, KW=18, FB=11, RAMB=12, LB=10, LOW=4, EPB=62, VOL=1):
        assert LOW >= 3 and 1 <= EPB <= EPB_MAX and KW <= 28
        s.KW, s.FB, s.RAMB, s.LB, s.LOW, s.EPB, s.VOL = KW, FB, RAMB, LB, LOW, EPB, VOL; s.L = 1 << LB; s.CAP = (s.L - LOW - 2) * EPB
        s.card = {}; s.n = {k: 0 for k in NAMES}; s.track = False; s.durable = {}; s.torn_at = None; s._reset_ram()
    def _reset_ram(s):
        s.fast = {}; s.sdram = {}; s.index = {}; s.obuf = []; s.open_id = 0; s.tail = 0; s.open_dirty = False; s.rbuf = None; s.in_gc = False
    def _h(s, k):
        h = hashk(k, s.KW)
        return h, h & ((1 << s.FB) - 1), top(h, s.RAMB, s.KW) & ((1 << s.RAMB) - 1)
    # ---- the log ----
    def _put_entry(s, kind, h, v):
        s.obuf.append((kind, h, v)); s.open_dirty = True
        if len(s.obuf) == s.EPB: s._close()
    def _append(s, h, v):
        s.index[h] = (s.open_id % s.L, len(s.obuf)); s._put_entry("L", h, v)
    def _append_tomb(s, h):
        s.n["tomb_wr"] += 1; s._put_entry("T", h, 0)
    def card_state(s):
        """What the index says the card level holds right now: {key hash: value}. For tests."""
        d = {}; cache = {}
        for h, (pos, i) in s.index.items():
            if pos == s.open_id % s.L and i < len(s.obuf): d[h] = s.obuf[i][2]
            else:
                if pos not in cache: cache[pos] = parse_block(s.card[pos], s.VOL)[1]
                d[h] = cache[pos][i][2]
        return d
    def _write_open(s):
        pos = s.open_id % s.L; img = make_block(s.VOL, s.open_id + 1, s.obuf); s.n["card_wr"] += 1; s.open_dirty = False
        if s.rbuf and s.rbuf[0] == pos: s.rbuf = None
        if s.torn_at is not None and s.n["card_wr"] == s.torn_at:
            bad = bytearray(img); bad[100] ^= 0xFF; s.card[pos] = bytes(bad); raise PowerLoss()
        s.card[pos] = img
        if s.track: s.durable = s.card_state()
    def _close(s):
        s._write_open(); s.obuf = []; s.open_id += 1
        if not s.in_gc:
            s.in_gc = True
            while s.open_id - s.tail > s.L - s.LOW: s._gc()
            s.in_gc = False
    def _gc(s):
        pos = s.tail % s.L; s.tail += 1; pb = parse_block(s.card.get(pos), s.VOL); seq, ents = pb if pb else (0, []); s.n["card_rd"] += 1; s.n["gc_rd"] += 1; s.rbuf = (pos, ents)
        for i, (kind, h, v) in enumerate(ents):
            if kind == "L" and s.index.get(h) == (pos, i): s.n["gc_moved"] += 1; s._append(h, v)
            elif kind == "T": s.n["tomb_dropped"] += 1
    def flush(s):
        if s.open_dirty and s.obuf: s._write_open()
    # ---- the levels (rules as in v4) ----
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
        s.n["card_get"] += 1; pos, i = loc
        if pos == s.open_id % s.L and i < len(s.obuf): v = s.obuf[i][2]; s.n["open_hit"] += 1
        else:
            if s.rbuf and s.rbuf[0] == pos: s.n["rbuf_hit"] += 1
            else: s.n["card_rd"] += 1; s.rbuf = (pos, parse_block(s.card[pos], s.VOL)[1])
            v = s.rbuf[1][i][2]
        del s.index[h]; s.n["promote_card"] += 1; s._append_tomb(h); return v
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
    # ---- save, power loss, restore ----
    def save(s):
        """Clean save: every fast and SDRAM entry goes down into the log, then the open sector is written. Returns the number of entries that did not fit (0 when all is safe)."""
        lost0 = s.n["log_full"]
        for f in sorted(s.fast): h, v = s.fast.pop(f); s.n["drain_fast"] += 1; s._ins_card(h, v)
        for sl in sorted(s.sdram): h, v = s.sdram.pop(sl); s.n["drain_sdram"] += 1; s._ins_card(h, v)
        s.flush(); return s.n["log_full"] - lost0
    def power_loss(s): s._reset_ram()
    def restore(s):
        """Rebuild the index from the card alone. Returns (number of valid blocks, newest sequence number)."""
        s._reset_ram(); good = []
        for pos in range(s.L):
            s.n["scan_rd"] += 1; raw = s.card.get(pos)
            if raw is None or raw[8:10] == b"\0\0": continue   # never written (the magic field is empty)
            p = parse_block(raw, s.VOL)
            if p is None or (p[0] - 1) % s.L != pos: s.n["bad_blocks"] += 1; continue
            good.append((p[0], pos, p[1]))
        good.sort(key=lambda t: t[0])
        for seq, pos, ents in good:
            s.n["scan_rd"] += 1
            for i, (kind, h, v) in enumerate(ents):
                if kind == "L": s.index[h] = (pos, i); s.n["replay_live"] += 1
                elif kind == "T": s.index.pop(h, None); s.n["replay_tomb"] += 1
        if good:
            s.open_id = good[-1][0]; s.tail = good[0][0] - 1
            s.in_gc = True
            while s.open_id - s.tail > s.L - s.LOW: s._gc()
            s.in_gc = False
        return len(good), (good[-1][0] if good else 0)
