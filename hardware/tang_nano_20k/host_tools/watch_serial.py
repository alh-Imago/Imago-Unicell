#!/usr/bin/env python3
"""serial_capture_v1.py (shipped into run folders as watch_serial.py) -- ledger #1133/#1138: open the card's serial port BEFORE the bitstream is loaded, keep re-opening it when the USB device vanishes and returns (the load makes it do that), and log WHEN every chunk of bytes arrives.
  python3 watch_serial.py /dev/ttyUSB1 out.bin SECONDS      -> writes out.bin (all bytes) and out.bin.log (time since start, chunk size)"""
import os, select, sys, termios, time
port, out, secs = sys.argv[1], sys.argv[2], float(sys.argv[3])
t0 = time.time(); fd = None; total = 0; opens = 0; log = open(out + ".log", "w"); data = open(out, "wb")
def op():
    global fd, opens
    f = os.open(port, os.O_RDONLY | os.O_NOCTTY | os.O_NONBLOCK)
    a = termios.tcgetattr(f)
    a[0] = 0; a[1] = 0; a[2] = termios.CS8 | termios.CREAD | termios.CLOCAL; a[3] = 0; a[4] = a[5] = termios.B115200
    a[6][termios.VMIN] = 0; a[6][termios.VTIME] = 0
    termios.tcsetattr(f, termios.TCSANOW, a)
    fd = f; opens += 1
    log.write("%.3f open #%d\n" % (time.time() - t0, opens)); log.flush()
while time.time() - t0 < secs:
    if fd is None:
        try:
            op()
        except OSError:
            time.sleep(0.05); continue
    try:
        r, _, _ = select.select([fd], [], [], 0.2)
        if r:
            b = os.read(fd, 4096)
            if b:
                data.write(b); data.flush(); total += len(b)
                log.write("%.3f %d\n" % (time.time() - t0, len(b))); log.flush()
            else:
                time.sleep(0.02)
    except OSError as e:
        log.write("%.3f lost (%s)\n" % (time.time() - t0, e.__class__.__name__)); log.flush()
        try: os.close(fd)
        except OSError: pass
        fd = None; time.sleep(0.05)
print("watch: %d bytes in %.1f s, opened %d time(s); first byte at %s s, last at %s s" % (total, time.time() - t0, opens, *( (lambda L: (L[0], L[-1]) if L else ("-", "-"))([l.split()[0] for l in open(out + ".log") if len(l.split()) == 2 and l.split()[1].isdigit()]) )))
