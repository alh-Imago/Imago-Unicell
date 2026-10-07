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
    return r.returncode == 0, (r.stdout + r.stderr)[-400:]


def listen_on(port, seconds):
    got = []
    try:
        with serial.Serial(port, BAUD, timeout=0.2) as s:
            s.reset_input_buffer()
            t0, buf = time.time(), b""
            while time.time() - t0 < seconds:
                buf += s.read(256)
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    text = line.decode("ascii", "replace").strip()
                    if text.startswith("UCT"):
                        got.append(text)
                        if len(got) >= 2:
                            return got
    except (serial.SerialException, OSError):
        pass
    return got


def listen(first_port):
    """listen on the usual port first, then on every other serial port (after a reprogram the board may reappear under a new name); returns (lines, port that answered, ports seen)"""
    time.sleep(1.0)
    seen = serial_ports()
    order = [first_port] + [p for p in seen if p != first_port]
    for port in order:
        lines = listen_on(port, 3.0 if port != first_port else LISTEN_S)
        if lines:
            return lines, port, seen
    return [], "", seen


def main():
    port = pick_port(sys.argv[1] if len(sys.argv) > 1 else None)
    tests = sorted(glob.glob(os.path.join(HERE, "*.fs")))
    if not tests:
        sys.exit("no .fs files next to board_run.py")
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows, out = [], [f"UniCell on-board test run  {stamp}   serial port {port}   {len(tests)} bitstreams   ports at start: {serial_ports()}", "=" * 100]
    for fs in tests:
        name = os.path.splitext(os.path.basename(fs))[0]
        meta = json.load(open(fs[:-3] + ".json")) if os.path.exists(fs[:-3] + ".json") else {}
        print(f"[{name}] loading ...", flush=True)
        ok, msg = load(fs)
        status, line, answered, seen = "NOLOAD", "", "", []
        if ok:
            lines, answered, seen = listen(port)
            line = lines[-1] if lines else ""
            if answered:
                port = answered                   # stay on the port that works
            m = re.search(r"res=([PF])", line)
            status = ("PASS" if m.group(1) == "P" else "FAIL") if m else "NOREPORT"
            if m and meta.get("sim_line"):
                same = re.sub(r"last=[0-9A-F]+", "", line) == re.sub(r"last=[0-9A-F]+", "", meta["sim_line"])
                if status == "PASS" and not same:
                    status = "PASS(line differs from simulation)"
        print(f"[{name}] {status}", flush=True)
        out += [f"{name:<22} {status}", f"   what     : {meta.get('what', '')}", f"   board    : {line or '(nothing received)'}", f"   simulated: {meta.get('sim_line', '')}"]
        out.append(f"   loader   : {'ok' if ok else 'FAILED'}; serial ports seen after loading: {seen}; answered on: {answered or '-'}")
        if not ok or status == "NOREPORT":
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
