#!/usr/bin/env python3
"""link_check_v2.py - is the JTAG link to the card sound? (ledger #1564; v2, ledger #1568: advice for the all-ones read, "unable to claim usb device" and "no device found", found when Alan pulled the header board; specific texts are tried before the loader's own generic hint, which names "usb bulk write failed" in every load error)

Three checks and a translator, all in plain words:
  adapter()          is the FT232H adapter (USB 0403:6014) on the bus, and which device number does it have (read from /sys, no root needed)
  Watch.check()      compare the device number with the last check: a changed number means the adapter dropped off the bus and came back
                     (a loose header board or lead does this: ledger #1563, dmesg "USB disconnect, device number N")
  ping()             `python3 link_check_v2.py ping`: open the link, read the board's version reply, say what answered (needs openocd)
  diagnose(text)     turn a LinkError / loader error text into a sentence that says what to look at

What it cannot do: it cannot tell a loose connection from a dying cable or a card power fault; it says what it saw and what to check first.
    python3 link_check_v2.py ping            exit 0 = the board answered, 1 = it did not (the reason is printed)
    python3 link_check_v2.py usb             only the USB state, no openocd
"""
import os, sys

SYSFS = '/sys/bus/usb/devices'
VID, PID = '0403', '6014'

def adapter(sysfs=SYSFS, vid=VID, pid=PID):
    """-> dict(found, devnum, busnum, name); found False when no such device is on the bus"""
    try: names = sorted(os.listdir(sysfs))
    except OSError: return dict(found=False, devnum=None, busnum=None, name=None, why='cannot read ' + sysfs)
    for n in names:
        p = os.path.join(sysfs, n)
        try:
            if open(os.path.join(p, 'idVendor')).read().strip() == vid and open(os.path.join(p, 'idProduct')).read().strip() == pid:
                return dict(found=True, devnum=int(open(os.path.join(p, 'devnum')).read().strip()), busnum=int(open(os.path.join(p, 'busnum')).read().strip()), name=n, why='')
        except (OSError, ValueError): continue
    return dict(found=False, devnum=None, busnum=None, name=None, why='no USB device %s:%s on the bus' % (vid, pid))

class Watch:
    """remembers the adapter's device number between checks"""
    def __init__(self, sysfs=SYSFS): self.sysfs, self.last = sysfs, None
    def check(self):
        """-> (status, message): 'ok' | 'first' (nothing to compare with yet) | 'dropped' | 'missing'"""
        a = adapter(self.sysfs)
        if not a['found']:
            self.last = None
            return 'missing', 'the JTAG adapter is not on the USB bus (%s): check the USB lead and the header board, then plug it in again' % (a['why'] or 'not found')
        prev, self.last = self.last, (a['busnum'], a['devnum'])
        if prev is None: return 'first', 'the adapter is on USB (bus %d, device %d)' % self.last
        if prev != self.last:
            return 'dropped', 'the JTAG adapter dropped off USB and came back since the last check (device %d -> %d): look for a loose header board or lead; anything that ran in between may have been cut off' % (prev[1], self.last[1])
        return 'ok', 'the adapter is on USB (bus %d, device %d), unchanged' % self.last

_RULES = [
    ('unable to claim usb device', 'the loader could not take the USB adapter: something else holds it (another shell or window, or a leftover openocd: `pgrep -af openocd`, then `pkill openocd`), or the adapter has just dropped and come back: wait a few seconds and try again'),
    ('no device found', 'the adapter is on USB but sees no FPGA on the JTAG chain: is the card powered, and is the JTAG header board seated on the card? (a card that was power-cycled has lost its design: `load` a build afterwards)'),
    ('usb bulk write failed', 'the loader could not talk to the USB adapter: reseat the USB lead and the header board, and check nothing else (another shell, a window, openocd) holds the adapter'),
    ('unable to config pins', 'the loader could not talk to the USB adapter: reseat the USB lead and the header board, and check nothing else holds the adapter'),
    ('execute failed', 'the JTAG scan failed in the middle of a transfer: the adapter or its connection to the card dropped (a loose header board gave this in ledger #1563). Reseat the header board, quit and restart the shell (a stuck connection does not recover by itself), then try again'),
    ('unexpected drscan', 'the JTAG scan failed in the middle of a transfer: the adapter or its connection to the card dropped (a loose header board gave this in ledger #1563). Reseat the header board, quit and restart the shell (a stuck connection does not recover by itself), then try again'),
    ('closed the connection', 'the openocd helper stopped answering: quit and restart the shell; if it keeps happening check the USB lead and header board'),
    ('openocd exited', 'openocd stopped on its own: the adapter is probably not reachable (loose lead or header board); see the openocd log named in the message'),
    ('cannot reach openocd', 'could not reach openocd: is another program holding the adapter (a window, another shell)? Quit it and try again'),
    ('openocd not found', 'openocd is not available: start the shell as `nix shell nixpkgs#openocd --command python3 score_shell_v9.py` (or `set openocd PATH` to name one)'),
    ('wrong marker', 'the scan did not read the S-Core marker: either the JTAG header board is off or loose (a pulled header reads as all ones, 0xf), or the card has no S-Core design (it was power-cycled, or nothing is loaded yet). Seat the header board first; if the card was powered off, `load` a build'),
    ('idcode', 'the JTAG chain shows a different chip than expected: is the right card on the adapter and powered?'),
]
def diagnose(text):
    """-> a sentence that says what to look at, or None when the text is not a link problem"""
    t = (text or '').lower()
    for key, msg in _RULES:
        if key in t: return msg
    return None

def ping(port='jtag'):
    """open the link and read the board's version reply -> (ok, text).  Needs openocd (run it in a process of its own)."""
    try:
        import card_label_v1 as CL
        i = CL.CardLink(port).info()
        return True, 'the board answered: version %d, %d slices per block, %d code words, shared RAM %d words' % (i['version'], i['S'], i['imem_words'], i['shared_words'])
    except Exception as e:
        return False, '%s: %s' % (type(e).__name__, e)

def main(argv=None):
    a = list(sys.argv[1:] if argv is None else argv)
    if not a or a[0] not in ('ping', 'usb'): print(__doc__); return 2
    st, msg = Watch().check()
    print('USB %s: %s' % (st, msg))
    if a[0] == 'usb': return 1 if st == 'missing' else 0
    if st == 'missing': return 1
    ok, text = ping()
    print(('PING ok: ' if ok else 'PING FAILED: ') + text)
    if not ok:
        d = diagnose(text)
        if d: print('WHAT TO CHECK: ' + d)
    return 0 if ok else 1

if __name__ == '__main__': sys.exit(main())
