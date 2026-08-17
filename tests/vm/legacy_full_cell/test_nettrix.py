"""
test_nettrix.py — NetTrix format and reference implementation tests

Run: python3 tests/vm/test_nettrix.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from cell_format import FormatRegistry, NetTrix
from fp_tiles import TileLibrary
from nettrix_runner import (
    ref_flag_extract, ref_classify_proto, ref_prefix_match,
    ref_classify_port, ref_tcp_state, ref_ttl_check,
    ref_checksum_step, ref_parse_ipv4, ref_parse_tcp, ref_parse_udp,
    tcp_fsm_step, run_validation
)

PASS, FAIL = 0, 0
def check(label, cond, detail=""):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  [PASS] {label}")
    else:    FAIL += 1; print(f"  [FAIL] {label}" + (f" — {detail}" if detail else ""))

fmt = NetTrix()
reg = FormatRegistry.get_default()
lib = TileLibrary()
BUDGET = 900

print("\n=== NetTrix FormatDefinition ===")
check("registered",              reg.get("NetTrix") is not None)
check("domain is NetTrix",       fmt.domain == "NetTrix")
check("boundary_in correct",     fmt.boundary_in == "NET_PARSE_IPV4")
check("boundary_out is None",    fmt.boundary_out is None)
check("10 valid tiles",          len(fmt.valid_tiles) == 10)
for tile in fmt.valid_tiles:
    check(f"valid_tiles has {tile}", tile in fmt.valid_tiles)

print("\n=== Protocol constants ===")
check("PROTO_TCP == 6",   fmt.PROTO_TCP  == 6)
check("PROTO_UDP == 17",  fmt.PROTO_UDP  == 17)
check("PROTO_ICMP == 1",  fmt.PROTO_ICMP == 1)
check("FLAG_SYN == 0x02", fmt.FLAG_SYN   == 0x02)
check("FLAG_ACK == 0x10", fmt.FLAG_ACK   == 0x10)
check("FLAG_FIN == 0x01", fmt.FLAG_FIN   == 0x01)
check("FLAG_RST == 0x04", fmt.FLAG_RST   == 0x04)

print("\n=== Helper methods ===")
check("ip_to_int 192.168.1.1",   fmt.ip_to_int("192.168.1.1") == 0xC0A80101)
check("ip_to_int 10.0.0.1",      fmt.ip_to_int("10.0.0.1")   == 0x0A000001)
check("subnet_mask /24",          fmt.subnet_mask(24) == 0xFFFFFF00)
check("subnet_mask /16",          fmt.subnet_mask(16) == 0xFFFF0000)
check("subnet_mask /32",          fmt.subnet_mask(32) == 0xFFFFFFFF)
check("tcp_state_name ESTABLISHED",
      fmt.tcp_state_name(fmt.TCP_ESTABLISHED) == "ESTABLISHED")
check("tcp_state_name CLOSED",
      fmt.tcp_state_name(fmt.TCP_CLOSED) == "CLOSED")

print("\n=== Tile reference implementations (from runner) ===")
ok = run_validation()
check("run_validation() 30/30", ok)

print("\n=== TCP FSM completeness ===")
# Full active-open + passive-close lifecycle
state = fmt.TCP_LISTEN
steps = [
    (fmt.FLAG_SYN,              fmt.TCP_SYN_RECEIVED),
    (fmt.FLAG_ACK,              fmt.TCP_ESTABLISHED),
    (0x00,                      fmt.TCP_ESTABLISHED),
    (fmt.FLAG_FIN,              fmt.TCP_CLOSE_WAIT),
    (fmt.FLAG_FIN,              fmt.TCP_LAST_ACK),
    (fmt.FLAG_ACK,              fmt.TCP_CLOSED),
]
for flags, expected_next in steps:
    state = tcp_fsm_step(state, flags)
    check(f"FSM → {fmt.tcp_state_name(expected_next)}", state == expected_next,
          f"got {fmt.tcp_state_name(state)}")
check("RST from any state → CLOSED",
      tcp_fsm_step(fmt.TCP_ESTABLISHED, fmt.FLAG_RST) == fmt.TCP_CLOSED)
check("no transition → same state",
      tcp_fsm_step(fmt.TCP_ESTABLISHED, 0x00) == fmt.TCP_ESTABLISHED)

print("\n=== Packet parsing ===")
src = fmt.ip_to_int("192.168.1.100")
dst = fmt.ip_to_int("10.0.0.1")
iw = fmt.pack_ipv4_header(src, dst, fmt.PROTO_TCP, ttl=64)
p  = ref_parse_ipv4(iw)
check("IPv4: src_ip correct",   p['src_ip']   == src)
check("IPv4: dst_ip correct",   p['dst_ip']   == dst)
check("IPv4: protocol=TCP",     p['protocol'] == fmt.PROTO_TCP)
check("IPv4: ttl=64",           p['ttl']      == 64)
check("IPv4: version=4",        p['version']  == 4)

tw = fmt.pack_tcp_header(54321, 443, fmt.FLAG_SYN)
tp = ref_parse_tcp(tw)
check("TCP: src_port=54321",    tp['src_port'] == 54321)
check("TCP: dst_port=443",      tp['dst_port'] == 443)
check("TCP: SYN flag set",      bool(tp['flags'] & fmt.FLAG_SYN))

print(f"\n{'='*55}")
print(f"Results: {PASS} passed, {FAIL} failed out of {PASS+FAIL} tests")
if FAIL == 0: print("ALL TESTS PASSED")
else:         print("SOME TESTS FAILED"); sys.exit(1)
