#!/usr/bin/env python3
"""board_run.py -- loads every <name>.fs next to this file with openFPGALoader, listens to the board's serial port for the test's result line, and writes ONE results file
(board_results.txt, plus board_results.csv). Ledger #1023.  usage: python board_run.py [COMPORT]"""
import csv
import glob
import json
import os
import re
import subprocess
import sys
import time
import datetime

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    sys.exit("pyserial is missing: run   pip install pyserial   and try again")

HERE = os.path.dirname(os.path.abspath(__file__))
BAUD = 115200
LISTEN_S = 6.0


def serial_ports():
    """every serial port the PC currently shows (the BL616 can come back under another name after the FPGA is reprogrammed)"""
    return sorted(p.device for p in list_ports.comports())


def pick_port(arg):
    if arg:
        return arg
    ports = [p for p in list_ports.comports()]
    if not ports:
        sys.exit("no serial port found: plug the board in, or name it:  python3 board_run.py /dev/ttyUSB1   (Windows: COM7)")
    ports.sort(key=lambda p: p.device)
    return ports[-1].device       # the Tang Nano 20K shows two ports; the FPGA UART is the second one


def load(fs):
    r = subprocess.run(["openFPGALoader", "-b", "tangnano20k", fs], capture_output=True, text=True)
    return r.returncode == 0, (r.stdout + r.stderr)[-1500:]


def read_lines(ser, seconds, name, sim_line=""):
    """read from an ALREADY OPEN port, collect well-formed result lines of THIS test (`UCT <name> res=.. w=..`), ignore everything else (boot text, another test's old lines, garbage while the chip reconfigures).
    Stops as soon as a line equals the simulation's (apart from the cycle count) or two well-formed lines were seen. returns (lines, other_lines_seen, port_vanished)"""
    mine, other = [], 0
    strip = lambda t: re.sub(r"last=[0-9A-F]+", "", t)
    t0, buf = time.time(), b""
    good = re.compile(r"UCT (\S+) res=[PF] n=[0-9A-F]{4} e=[0-9A-F]{4} bad=[0-9A-F]{4} to=[01] last=[0-9A-F]{8} sig=[0-9A-F]{8} w=[0-9A-F,]+$")
    while time.time() - t0 < seconds:
        try:
            buf += ser.read(256)
        except (serial.SerialException, OSError):
            return mine, other, True
        while b"\n" in buf:
            line, buf = buf.split(b"\n", 1)
            text = line.decode("ascii", "replace").strip()
            m = good.search(text)                      # junk bytes can sit in front of a good line (the chip's pins glitch while it reconfigures): find the good part
            if m and m.group(1) == name:
                text = m.group(0)
                mine.append(text)
                if (sim_line and strip(text) == strip(sim_line)) or len(mine) >= 2:
                    return mine, other, False
            elif "UCT" in text:
                other += 1
    return mine, other, False


def open_port(port):
    s = serial.Serial()
    s.port, s.baudrate, s.timeout = port, BAUD, 0.2
    s.dtr = False                       # do not toggle the bridge's modem lines
    s.rts = False
    s.open()
    return s


GOOD = re.compile(r"UCT (\S+) res=[PF] n=[0-9A-F]{4} e=[0-9A-F]{4} bad=[0-9A-F]{4} to=[01] last=[0-9A-F]{8} sig=[0-9A-F]{8} w=[0-9A-F,]+$")


def read_with_cat(port, name, sim_line, seconds=6):
    """Linux: do exactly what works by hand -- `stty -F PORT 115200 raw -echo`, then `cat PORT` for a few seconds -- and parse what came out. Returns (lines of THIS test, raw bytes received, other lines seen, first raw bytes)."""
    subprocess.run(["stty", "-F", port, "115200", "raw", "-echo"], capture_output=True)
    try:
        r = subprocess.run(["timeout", str(seconds), "cat", port], capture_output=True, timeout=seconds + 5)
        raw = r.stdout
    except subprocess.TimeoutExpired as e:
        raw = e.stdout or b""
    text = raw.decode("ascii", "replace")
    mine, other = [], 0
    for chunk in text.replace("\r", "\n").split("\n"):
        m = GOOD.search(chunk.strip())
        if m and m.group(1) == name:
            mine.append(m.group(0))
        elif "UCT" in chunk:
            other += 1
    return mine, len(raw), other, raw[:100]


def listen(ser, port, name, sim_line):
    """after a load: let the chip start, THROW AWAY everything buffered so far (the previous design's lines), then read this test's lines. If the held port is silent or gone, reopen it, then try every other port."""
    time.sleep(3.0)
    seen = serial_ports()
    try:
        ser.reset_input_buffer()
    except Exception:  # noqa: BLE001
        pass
    lines, other, gone = read_lines(ser, LISTEN_S, name, sim_line)
    if lines:
        return lines, ser, port, seen, "held-open port" + (f" ({other} lines of other tests ignored)" if other else "")
    note = ("held-open port vanished" if gone else f"held-open port had no line for this test ({other} lines of other tests seen)")
    try:
        ser.close()
    except Exception:  # noqa: BLE001
        pass
    for p in [port] + [x for x in seen if x != port]:
        try:
            ser = open_port(p)
        except (serial.SerialException, OSError):
            continue
        lines, other, gone = read_lines(ser, 3.0, name, sim_line)
        if lines:
            return lines, ser, p, seen, note + "; answered after reopening " + p
        ser.close()
    try:
        ser = open_port(port)
    except (serial.SerialException, OSError):
        ser = None
    return [], ser, port, seen, note + "; nothing on any port"


def main():
    port = pick_port(sys.argv[1] if len(sys.argv) > 1 else None)
    tests = sorted(glob.glob(os.path.join(HERE, "*.fs")))
    if not tests:
        sys.exit("no .fs files next to board_run.py")
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ser = open_port(port) if not sys.platform.startswith("linux") else None
    rows, out = [], [f"UniCell on-board test run  {stamp}   serial port {port}   {len(tests)} bitstreams   ports at start: {serial_ports()}", "=" * 100]
    for fs in tests:
        name = os.path.splitext(os.path.basename(fs))[0]
        meta = json.load(open(fs[:-3] + ".json")) if os.path.exists(fs[:-3] + ".json") else {}
        print(f"[{name}] loading ...", flush=True)
        ok, msg = load(fs)
        status, line, answered, seen, note = "NOLOAD", "", "", [], ""
        if ok:
            lines, note, answered, seen = [], "", "", serial_ports()
            if sys.platform.startswith("linux"):
                try:
                    ser.close()                   # the shell tools below must be the only readers
                except Exception:  # noqa: BLE001
                    pass
                time.sleep(3.0)
                lines, nraw, nother, head = read_with_cat(port, name, meta.get("sim_line", ""))
                note = f"stty+cat: {nraw} raw bytes, {nother} lines of other tests, first bytes {head!r}"
                answered = port
                if not lines:                      # one more try: the chip may need a moment longer
                    time.sleep(2.0)
                    lines, nraw2, nother2, head2 = read_with_cat(port, name, meta.get("sim_line", ""), 8)
                    note += f"; retry: {nraw2} raw bytes, {nother2} other lines, first bytes {head2!r}"
                ser = None
            if not lines and ser is not None:
                lines, ser, answered, seen, note2 = listen(ser, port, name, meta.get("sim_line", ""))
                note = (note + "; " if note else "") + note2
            line = lines[-1] if lines else ""
            if lines:
                port = answered
            m = re.search(r"res=([PF])", line)
            status = ("PASS" if m.group(1) == "P" else "FAIL") if m else "NOREPORT"
            if m and meta.get("sim_line"):
                same = re.sub(r"last=[0-9A-F]+", "", line) == re.sub(r"last=[0-9A-F]+", "", meta["sim_line"])
                if status == "PASS" and not same:
                    status = "PASS(line differs from simulation)"
        print(f"[{name}] {status}", flush=True)
        out += [f"{name:<22} {status}", f"   what     : {meta.get('what', '')}", f"   board    : {line or '(nothing received)'}", f"   simulated: {meta.get('sim_line', '')}"]
        out.append(f"   loader   : {'ok' if ok else 'FAILED'}; serial ports seen after loading: {seen}; {note}")
        if not ok or not status.startswith("PASS"):
            out.append("   loader output: " + msg.replace("\n", " | "))
        out.append(f"   built    : {meta.get('lut4', '?')} LUT4, {meta.get('dff', '?')} flip-flops, Fmax {meta.get('fmax_mhz', '?')} MHz (27 MHz needed)")
        out.append("")
        rows.append([name, status, line, meta.get("sim_line", ""), meta.get("lut4", ""), meta.get("dff", ""), meta.get("fmax_mhz", "")])
    npass = sum(1 for r in rows if r[1].startswith("PASS"))
    out += ["=" * 100, f"SUMMARY: {npass} of {len(rows)} passed"]
    open(os.path.join(HERE, "board_results.txt"), "w").write("\n".join(out) + "\n")
    with open(os.path.join(HERE, "board_results.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["test", "status", "board_line", "simulated_line", "lut4", "dff", "fmax_mhz"])
        w.writerows(rows)
    print("\n".join(out[-3:]))


if __name__ == "__main__":
    main()
