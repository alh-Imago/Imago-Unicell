"""The JTAG speed tool's measuring functions, against a fake scan (no card)."""
import os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tools"))
import hexn_jtag_speed_v1 as S


def test_raw_rate_counts_scans():
    n = [0]
    def scan(v): n[0] += 1; time.sleep(0.001); return 0
    dt, sps = S.measure_raw(scan, 20)
    assert n[0] == 20 and 20 < sps < 1100 and dt > 0.015


def test_info_rate_counts_scans_per_info():
    cnt = [0]
    def info(link): cnt[0] += 3; time.sleep(0.001)
    r = S.measure_info(None, cnt, 10, info)
    assert abs(r["scans_per_info"] - 3.0) < 1e-9 and r["infos_per_s"] > 0 and r["bytes_per_s"] == 7 * r["infos_per_s"]


def test_set_speed_falls_back_to_old_command():
    seen = []
    def cmd(c): seen.append(c); return "invalid command name" if c.startswith("adapter speed ") and c != "adapter speed" else "adapter speed: 6000 kHz"
    out = S.set_speed(cmd, 6000)
    assert seen[:2] == ["adapter speed 6000", "adapter_khz 6000"] and "6000" in out
