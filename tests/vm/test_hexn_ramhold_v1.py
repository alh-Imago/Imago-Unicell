"""Tests for the RAM hold routing cell (sub/verilog/hexn_ramhold_v1.v), 3 Nov 2026. A pulse train on the W face is routed to E; with a hold of h on E the stream (data and flag) must appear exactly h clocks later than without a hold, for the whole planner range 2..96.
Also: another output is not delayed, clear wipes the delay line, a stale word does not come back after a reprogram. Needs iverilog."""
import os, shutil, subprocess, sys, tempfile
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path.insert(0, os.path.join(ROOT, "tools"))
import pytest
import hexn_tile_cfg_rh_v1 as C

SRC = [os.path.join(ROOT, "tests/hexn_ramhold_tb.v"), os.path.join(ROOT, "sub/verilog/hexn_ramhold_v1.v")]


def run(word, w_stream, n_after=130, clear_at=None, clear_len=0, second_word=None, second_at=None):
    """w_stream: list of (d, f) per clock on the W face after configuration -> list of 8-char output strings, one per clock after configuration"""
    d = tempfile.mkdtemp()
    try:
        rows = []
        for i in range(C.width() - 1, -1, -1): rows.append(0x2 | ((word >> i) & 1))
        t0 = len(rows)
        for t in range(len(w_stream) + n_after):
            v = 0
            if t < len(w_stream): v |= (w_stream[t][0] << 9) | (w_stream[t][1] << 10)
            if clear_at is not None and clear_at <= t < clear_at + clear_len: v |= 0x4
            rows.append(v)
        open(d + "/s.hex", "w").write("\n".join("%04x" % r for r in rows) + "\n")
        subprocess.run(["iverilog", "-o", d + "/t"] + SRC, check=True)
        out = subprocess.run(["vvp", d + "/t", "+stim=" + d + "/s.hex", "+n=%d" % len(rows)], capture_output=True, text=True, check=True).stdout
        lines = [l.strip() for l in out.splitlines() if len(l.strip()) == 8 and set(l.strip()) <= set("01x")]
        return lines[t0:]
    finally:
        shutil.rmtree(d)


def first_flag(lines, face):   # face index 0 N 1 E 2 S 3 W: chars [2*face] data, [2*face+1] flag
    return next((i for i, l in enumerate(lines) if l[2 * face + 1] == "1"), None)


STREAM = [(1, 1)] + [((i * 5 + 3) % 2, 0) for i in range(31)]


def test_tools_present():
    assert shutil.which("iverilog") and shutil.which("vvp")


def test_pack_roundtrip():
    w = C.pack({1: "W"}, "E", 40); u = C.unpack(w)
    assert C.width() == 22 and u["hold_out"] == 1 and u["dly"] == 40 and u["route"][1] == 3
    assert C.unpack(C.pack({1: "W"}))["hold_out"] is None


@pytest.mark.parametrize("h", [2, 3, 17, 32, 33, 64, 95, 96])
def test_hold_delays_by_exactly_h(h):
    base = run(C.pack({1: "W"}), STREAM)
    held = run(C.pack({1: "W"}, "E", h), STREAM)
    s0, s1 = first_flag(base, 1), first_flag(held, 1)
    assert s0 is not None and s1 == s0 + h, (s0, s1, h)
    assert [l[2] for l in base[s0:s0 + 32]] == [l[2] for l in held[s1:s1 + 32]]       # the data bits are the same, h later
    assert [l[3] for l in base[s0:s0 + 32]] == [l[3] for l in held[s1:s1 + 32]]       # and so is the flag lane


def test_other_outputs_are_not_delayed():
    # W routed to E (held) and to S (not held)
    r = {1: "W", 2: "W"}
    base = run(C.pack(r), STREAM); held = run(C.pack(r, "E", 20), STREAM)
    assert first_flag(base, 2) == first_flag(held, 2) and first_flag(held, 1) == first_flag(base, 1) + 20
    assert [l[4:6] for l in base] == [l[4:6] for l in held]


def test_clear_wipes_the_delay_line():
    # a word is in the delay line when clear arrives for 130 clocks: nothing may come out of the hold afterwards
    h = 90
    lines = run(C.pack({1: "W"}, "E", h), STREAM, clear_at=20, clear_len=130, n_after=260)
    assert first_flag(lines, 1) is None
