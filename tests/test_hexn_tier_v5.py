"""Tests for the card format and log of hexn_tier_v5 (Python reference only, tools/hexn_tier_ref_v5.py; no RTL yet): block format, dictionary behaviour with compaction and tombstones, clean save then power loss then restore by scan, the state after a crash being exactly the last durable block write, and a torn block write."""
import os, random, sys
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_tier_ref_v5 as R
def test_block_format():
    ents = [("L" if i % 3 else "T", (i * 977) & 0x3FFFF, (i * 12345) & 0xFFFFFFFF) for i in range(62)]
    raw = R.make_block(7, 0x123456789A, ents)
    assert len(raw) == 512 and raw[0] == 7 and int.from_bytes(raw[1:6], "little") == 0x123456789A and raw[6] == 62 and raw[7] == 1
    assert raw[8:10] == bytes([0x58, 0x48]) and raw[12:16] == bytes(4)
    seq, back = R.parse_block(raw, 7)
    assert seq == 0x123456789A and back == ents
    assert R.parse_block(raw, 8) is None   # another volume
    for bit in (0, 7, 8 * 6, 8 * 20, 8 * 300, 8 * 511 + 7):   # one flipped bit anywhere is caught (header fields, entries, last byte)
        bad = bytearray(raw); bad[bit // 8] ^= 1 << (bit % 8); assert R.parse_block(bytes(bad), 7) is None, bit
    assert R.parse_block(R.make_block(1, 5, []), 1) == (5, [])
def run(t, d, steps, keys, seed, putp=0.4, vw=18):
    random.seed(seed)
    for _ in range(steps):
        k = random.choice(keys)
        if random.random() < putp: v = random.getrandbits(vw); t.put(k, v); d[k] = v
        else:
            f, v = t.get(k)
            if f: assert v == d[k]
def test_dictionary_with_compaction_and_tombstones():
    for LB, LOW, nk in ((6, 4, 800), (5, 3, 600)):
        random.seed(LB); t = R.Tier5(18, 4, 4, LB, LOW); d = {}; keys = random.sample(range(1 << 18), nk)
        run(t, d, 30000, keys, LB)
        assert t.n["gc_rd"] > 0 and t.n["tomb_wr"] > 0 and t.n["tomb_dropped"] > 0 and t.n["log_full"] == 0, t.n
def test_save_power_loss_restore_gives_back_everything():
    for LB, LOW, nk, steps in ((8, 4, 500, 20000), (5, 3, 200, 30000)):
        random.seed(LB + 100); t = R.Tier5(18, 4, 4, LB, LOW); d = {}; keys = random.sample(range(1 << 18), nk)
        run(t, d, steps, keys, LB + 100)
        assert t.n["gc_rd"] > 0 or LB == 8
        assert t.save() == 0
        t.power_loss(); nb, newest = t.restore()
        assert nb > 0 and t.n["scan_rd"] >= t.L
        for k in keys:
            f, v = t.get(k)
            assert f == (k in d) and (not f or v == d[k]), (LB, k)
def test_crash_state_is_the_last_durable_block_write():
    keys = random.Random(5).sample(range(1 << 18), 400)
    for LB, LOW, crash in ((5, 3, 1500), (5, 3, 9000), (5, 4, 25000), (7, 4, 12000)):
        t = R.Tier5(18, 4, 4, LB, LOW); t.track = True; d = {}
        run(t, d, crash, keys, crash)
        want = dict(t.durable); t.power_loss(); t.restore()
        assert t.card_state() == want, (LB, LOW, crash, len(want), len(t.card_state()))
        f, v = t.get(keys[0])   # and the tier keeps working after the restore
def test_flush_makes_the_card_level_durable():
    keys = random.Random(6).sample(range(1 << 18), 300); t = R.Tier5(18, 4, 4, 6, 4); t.track = True; d = {}
    run(t, d, 8000, keys, 6); t.flush(); want = t.card_state(); assert want == t.durable
    t.power_loss(); t.restore(); assert t.card_state() == want
def test_torn_block_write_falls_back_to_the_previous_durable_state():
    keys = random.Random(7).sample(range(1 << 18), 400); seen = 0
    for torn in (3, 20, 70, 150):
        t = R.Tier5(18, 4, 4, 5, 3); t.track = True; d = {}; t.torn_at = torn
        try: run(t, d, 40000, keys, torn); raise AssertionError("no torn write reached")
        except R.PowerLoss: pass
        want = dict(t.durable); t.power_loss(); t.restore()
        assert t.n["bad_blocks"] == 1 and t.card_state() == want, (torn, t.n["bad_blocks"], len(want), len(t.card_state())); seen += 1
    assert seen == 4
def test_save_reports_entries_that_did_not_fit():
    keys = random.Random(8).sample(range(1 << 18), 1500); t = R.Tier5(18, 3, 3, 4, 3); d = {}
    run(t, d, 20000, keys, 8, putp=0.7)
    lost = t.save(); assert lost > 0 and t.n["log_full"] > 0
    t.power_loss(); t.restore()
    for k in keys:
        f, v = t.get(k)
        if f: assert v == d[k]
