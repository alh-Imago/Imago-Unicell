#!/usr/bin/env python3
"""hexn_esp_log_v2: clone of hexn_esp_log_v1.py (left untouched) for the v2 sketch (tools/esp32/hexn_logger_v2): as v1, plus the IR receiver's edge lines 'E,<us>,<level>', written to a second file <out>_edges.csv (columns esp_us,level,host_s) so the sample CSV keeps v1's columns. v2 not run on hardware yet. Usage:
  python3 tools/hexn_esp_log_v2.py --port /dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0 --rate 1000 --seconds 60 --label dark_room_mains out.csv
  python3 tools/hexn_esp_log_v2.py --selftest
CSV columns: seq, esp_us, host_s, a35, a36, a39, d16, d17.  The first line is a '#' comment with the label, rate, start time.
After the run it prints dropped samples (gaps in seq) and the real mean spacing, so the rate is known, not assumed."""
import argparse, sys, time

def parse(line):
    p = line.strip().split(",")
    if len(p) != 8 or p[0] != "S":
        return None
    try:
        return [int(x) for x in p[1:]]
    except ValueError:
        return None

def summarise(rows):
    if len(rows) < 2:
        return "too few samples"
    seqs = [r[0] for r in rows]
    drops = sum(max(0, b - a - 1) for a, b in zip(seqs, seqs[1:]))
    us = [r[1] for r in rows]
    dts = [((b - a) & 0xFFFFFFFF) for a, b in zip(us, us[1:])]
    mean = sum(dts) / len(dts)
    return f"{len(rows)} samples, {drops} dropped, mean spacing {mean:.1f} us ({1e6/mean:.1f} Hz), max gap {max(dts)} us"

def parse_edge(line):
    p = line.strip().split(",")
    if len(p) != 3 or p[0] != "E":
        return None
    try:
        return int(p[1]), int(p[2])
    except ValueError:
        return None

def record(lines, out, label, rate, seconds, clock=time.time, edge_out=None):
    t0 = clock(); rows = []
    if edge_out is not None:
        edge_out.write("esp_us,level,host_s\n")
    nedge = 0
    out.write(f"# hexn_esp_log_v2 label={label} rate={rate} start={time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    out.write("seq,esp_us,host_s,a35,a36,a39,d16,d17\n")
    for ln in lines:
        now = clock() - t0
        if seconds and now > seconds:
            break
        e = parse_edge(ln)
        if e and edge_out is not None:
            edge_out.write(f"{e[0]},{e[1]},{now:.4f}\n"); nedge += 1
            continue
        r = parse(ln)
        if r:
            rows.append(r); out.write(f"{r[0]},{r[1]},{now:.4f},{r[2]},{r[3]},{r[4]},{r[5]},{r[6]}\n")
    record.edges = nedge
    return rows

def serial_lines(port, rate):
    import serial  # pip install pyserial
    s = serial.Serial(port, 921600, timeout=2)
    time.sleep(1.5); s.reset_input_buffer()
    s.write(f"rate {rate}\n".encode()); time.sleep(0.2); s.write(b"go\n")
    try:
        while True:
            yield s.readline().decode(errors="replace")
    finally:
        s.write(b"stop\n"); s.close()

def selftest():
    import io, random
    random.seed(1)
    fake = [f"S,{i},{i*1000},{2000+random.randint(-40,40)},{1500},{900},0,1" for i in range(500) if i != 250]
    fake += ["I,junk", "S,bad", "S,x,1,2,3,4,5,6", "E,1000,0", "E,1560,1", "E,x,1", "E,5,2,3"]
    out = io.StringIO(); eo = io.StringIO(); rows = record(iter(fake), out, "selftest", 1000, 0, edge_out=eo)
    assert len(rows) == 499, len(rows)
    assert record.edges == 2 and eo.getvalue().splitlines()[1].startswith("1000,0,"), eo.getvalue()
    msg = summarise(rows); assert "499 samples, 1 dropped" in msg and "max gap 2000" in msg, msg
    print("selftest ok:", msg)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("out", nargs="?"); ap.add_argument("--port"); ap.add_argument("--rate", type=int, default=1000)
    ap.add_argument("--seconds", type=float, default=60); ap.add_argument("--label", default="unlabelled")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest(); sys.exit(0)
    if not (a.out and a.port):
        ap.error("need --port and an output file")
    edge_name = (a.out[:-4] if a.out.endswith(".csv") else a.out) + "_edges.csv"
    with open(a.out, "w") as f, open(edge_name, "w") as fe:
        rows = record(serial_lines(a.port, a.rate), f, a.label, a.rate, a.seconds, edge_out=fe)
    print(summarise(rows), "->", a.out, "|", record.edges, "IR edges ->", edge_name)
