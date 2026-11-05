"""JTAG speed test for the Kintex card (read-only; changes nothing in the card's state).

Run from ~/ypcb-00338-1p1, inside the nix shell, with a base bitstream loaded:
  nix shell nixpkgs#openocd --command env OPENOCD=openocd HEXN_CHAIN=2 python3 ~/hexn-wt/tools/hexn_jtag_speed_v1.py [--khz 2000,6000,10000] [--scans 500] [--infos 100]

For each TCK setting it prints:
  1. what OpenOCD says the adapter speed is afterwards (the setting may be lowered by the cable);
  2. RAW scans per second: 160-bit scans of all zeros (a frame with a wrong CRC, which the bridge ignores), so this is the cost of one scan with no protocol work;
  3. the wire time one scan should take at that TCK (160 bits / TCK), for comparison;
  4. PROTOCOL rate: the base's 'N' info command repeated (1 byte sent, 6 read back, with the bridge's CRC, sequence and ack), as scans per info, infos per second and bytes per second.
If the raw scans per second stay the same while the TCK changes, the limit is the per-scan overhead (OpenOCD, USB), not the TCK."""
import argparse, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
os.environ.setdefault("HEXN_CHAIN", "2")
try: import serial
except ImportError: import types; sys.modules["serial"] = types.ModuleType("serial")
import hexn_jtag_host_v1 as J


def measure_raw(scan, n):
    """n scans of zeros; returns (seconds, scans per second)."""
    t = time.perf_counter()
    for _ in range(n): scan(0)
    dt = time.perf_counter() - t
    return dt, n / dt if dt > 0 else float("inf")


def measure_info(link, scan_counter, n, info):
    """n runs of the base 'N' info command; returns dict with infos/s, scans per info, bytes/s (6 bytes read per info + 1 sent)."""
    scan_counter[0] = 0; t = time.perf_counter()
    for _ in range(n): info(link)
    dt = time.perf_counter() - t
    return dict(seconds=dt, infos_per_s=n / dt, scans_per_info=scan_counter[0] / n, bytes_per_s=7 * n / dt)


def set_speed(cmd, khz):
    for c in ("adapter speed %d" % khz, "adapter_khz %d" % khz):
        r = cmd(c)
        if "invalid" not in r.lower() and "unknown" not in r.lower() and "not found" not in r.lower(): break
    return cmd("adapter speed")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--khz", default="2000,6000,10000"); ap.add_argument("--scans", type=int, default=500); ap.add_argument("--infos", type=int, default=100); a = ap.parse_args()
    import hexn_kxarr_host_v1 as KA, hexn_kxbase_host_v1 as KB
    ex = J.OpenOCDExec(KA.find_cfg()); cnt = [0]
    def scan(v): cnt[0] += 1; return ex.scan(v)
    link = J.JtagLink(scan, maxpoll=3000)
    try:
        print("OpenOCD speed as configured:", ex.cmd("adapter speed"))
        print("%-9s %-34s %-12s %-14s %-12s %-12s %-10s" % ("asked kHz", "OpenOCD reports", "raw scans/s", "wire us/scan", "infos/s", "scans/info", "bytes/s"))
        for khz in [int(x) for x in a.khz.split(",")]:
            rep = set_speed(ex.cmd, khz)
            dt, sps = measure_raw(ex.scan, a.scans)
            wire = 160 / (khz * 1000.0) * 1e6
            r = measure_info(link, cnt, a.infos, KB.info)
            print("%-9d %-34s %-12.0f %-14.1f %-12.1f %-12.2f %-10.0f" % (khz, rep[:34], sps, wire, r["infos_per_s"], r["scans_per_info"], r["bytes_per_s"]))
    finally:
        ex.close()


if __name__ == "__main__": main()
