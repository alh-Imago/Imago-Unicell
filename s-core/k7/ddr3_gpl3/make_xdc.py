#!/usr/bin/env python3
"""make_xdc.py - write sc_k7_ddr3_v1.xdc for the DDR3 build (channel 0, 9 byte lanes).

Pins: the card's vendor MEMORY_CH0.ucf (../../../docs/man/kintex7-ypcb00338-ddr3/), checked on 2026-11-16 against LiteX-Boards' platform file for this card
(all 117 DDR3 pins of each channel identical).  I/O properties (IOSTANDARD, SLEW, IN_TERM): the lines of upstream's own example xdc for this card, kept
only when they are plain `set_property ... [get_ports {...}]` lines (nextpnr-xilinx cannot parse anything else), plus lane 8 (the ECC lane), which the
example does not use, given the same properties as the other lanes.  Our own pins (SYS_CLK, three LEDs) are the ones of the BRAM build.
GPL-3.0 folder: the property lines come from upstream/example_demo (see README.md).
"""
import os, re
here = os.path.dirname(os.path.abspath(__file__))
ucf_path = os.path.join(here, "..", "..", "..", "docs", "man", "kintex7-ypcb00338-ddr3", "MEMORY_CH0.ucf")
ex_path = os.path.join(here, "upstream", "example_demo", "ypcb_00338_1p1", "ypcb_00338_1p1_ddr3.xdc")

ucf = {m.group(1): m.group(2) for l in open(ucf_path) for m in [re.search(r'NET\s+"([^"]+)"\s+LOC\s*=\s*"?(\w+)"?', l)] if m}
def pin(n):
    return ucf.get(n) or ucf.get(n + "[0]")

keep = re.compile(r"^set_property (LOC|PACKAGE_PIN|IOSTANDARD|SLEW|IN_TERM) (\S+) \[get_ports \{?([^ {}]+)\}?\]\s*$")
lines, seen = [], set()
for l in open(ex_path):
    m = keep.match(l)
    if not m or not m.group(3).startswith("ddr3_"):
        continue
    prop, val, port = m.groups()
    if prop in ("LOC", "PACKAGE_PIN"):
        p = pin(port)
        assert p, "no pin for " + port
        lines.append("set_property LOC %s [get_ports {%s}]\n" % (p, port)); seen.add(port)
    else:
        lines.append("set_property %s %s [get_ports {%s}]\n" % (prop, val, port))
# lane 8 (ECC): DQ 64..71, DQS 8
for i in range(64, 72):
    n = "ddr3_dq[%d]" % i
    lines += ["set_property LOC %s [get_ports {%s}]\n" % (pin(n), n), "set_property IOSTANDARD SSTL15 [get_ports {%s}]\n" % n,
              "set_property SLEW FAST [get_ports {%s}]\n" % n, "set_property IN_TERM UNTUNED_SPLIT_40 [get_ports {%s}]\n" % n]
    seen.add(n)
for pn in "pn":
    n = "ddr3_dqs_%s[8]" % pn
    lines += ["set_property LOC %s [get_ports {%s}]\n" % (pin(n), n), "set_property IOSTANDARD DIFF_SSTL15 [get_ports {%s}]\n" % n,
              "set_property SLEW FAST [get_ports {%s}]\n" % n, "set_property IN_TERM UNTUNED_SPLIT_40 [get_ports {%s}]\n" % n]
    seen.add(n)
# our own pins
own = ["set_property LOC AA28 [get_ports {SYS_CLK}]\n", "set_property IOSTANDARD LVCMOS18 [get_ports {SYS_CLK}]\n"]
for i, p in enumerate(["P30", "M30", "N30"]):
    own += ["set_property LOC %s [get_ports {led[%d]}]\n" % (p, i), "set_property IOSTANDARD LVCMOS18 [get_ports {led[%d]}]\n" % i]
# every DDR3 port bit of the top must have a LOC
expect = (["ddr3_addr[%d]" % i for i in range(15)] + ["ddr3_ba[%d]" % i for i in range(3)] + ["ddr3_dq[%d]" % i for i in range(72)] +
          ["ddr3_dqs_p[%d]" % i for i in range(9)] + ["ddr3_dqs_n[%d]" % i for i in range(9)] +
          ["ddr3_ck_p", "ddr3_ck_n", "ddr3_cke", "ddr3_cs_n", "ddr3_odt", "ddr3_ras_n", "ddr3_cas_n", "ddr3_we_n", "ddr3_reset_n"])
missing = [n for n in expect if n not in seen]
assert not missing, "no LOC line for: %s" % missing
open(os.path.join(here, "sc_k7_ddr3_v1.xdc"), "w").writelines(own + lines)
print("wrote sc_k7_ddr3_v1.xdc: %d lines, %d DDR3 port bits located" % (len(own) + len(lines), len(expect)))
