"""
nettrix_runner.py — NetTrix reference implementations and demos

Demonstrates the ten NetTrix tile operations using reference Python
implementations. All topology IS computation — the TCP state machine
is a preloaded register + EQ + MUX, not a lookup table.

Run: python3 nettrix_runner.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cell_format import FormatRegistry, NetTrix

fmt = NetTrix()
reg = FormatRegistry.get_default()
reg.register_class(NetTrix)


# ── Reference tile implementations ────────────────────────────────────────────

def ref_flag_extract(word: int, mask: int) -> int:
    """NET_FLAG_EXTRACT: AND word with preloaded mask. 32c d1."""
    return word & mask

def ref_classify_proto(protocol: int, expected: int) -> int:
    """NET_CLASSIFY_PROTO: protocol == expected? 1/0. 95c d7."""
    return 1 if protocol == expected else 0

def ref_prefix_match(ip: int, mask: int, prefix: int) -> int:
    """NET_PREFIX_MATCH: (ip & mask) == prefix? 1/0. 127c d8."""
    return 1 if (ip & mask) == (prefix & mask) else 0

def ref_classify_port(port: int, allowed: int) -> int:
    """NET_CLASSIFY_PORT: port == allowed? 1/0 (one rule). 127c d8."""
    return 1 if port == allowed else 0

def ref_tcp_state(current_state: int, expected_flags: int,
                  actual_flags: int, next_state: int,
                  fallback_state: int) -> int:
    """
    NET_TCP_STATE: if (current_state flags match) → next_state else fallback.
    EQ (95c) + MUX (128c) = 223c d10.
    Preloaded: expected_flags, next_state, fallback_state.
    """
    flags_match = 1 if (actual_flags & expected_flags) == expected_flags else 0
    return next_state if flags_match else fallback_state

def ref_ttl_check(ttl: int) -> int:
    """NET_TTL_CHECK: ttl > 0? 1=forward, 0=drop. 518c d14."""
    return 1 if ttl > 0 else 0

def ref_checksum_step(accumulator: int, word16: int) -> int:
    """NET_CHECKSUM_STEP: acc + word16 (one step). 482c d10."""
    return (accumulator + word16) & 0xFFFFFFFF

def ref_parse_ipv4(words: list) -> dict:
    """
    NET_PARSE_IPV4: extract all IPv4 header fields from 5 bus words.
    12 parallel SHR+AND chains. 864c d9.
    """
    w0, w1, w2, src, dst = words[:5]
    return {
        'version':     (w0 >> 28) & 0xF,
        'ihl':         (w0 >> 24) & 0xF,
        'tos':         (w0 >> 16) & 0xFF,
        'total_len':    w0        & 0xFFFF,
        'id':          (w1 >> 16) & 0xFFFF,
        'flags':       (w1 >> 13) & 0x7,
        'frag_offset':  w1        & 0x1FFF,
        'ttl':         (w2 >> 24) & 0xFF,
        'protocol':    (w2 >> 16) & 0xFF,
        'checksum':     w2        & 0xFFFF,
        'src_ip':       src,
        'dst_ip':       dst,
    }

def ref_parse_tcp(words: list) -> dict:
    """NET_PARSE_TCP: extract all TCP header fields. 576c d7."""
    ports, seq, ack, fw = words[:4]
    return {
        'src_port':    (ports >> 16) & 0xFFFF,
        'dst_port':     ports        & 0xFFFF,
        'seq_num':      seq,
        'ack_num':      ack,
        'data_offset': (fw >> 28) & 0xF,
        'flags':       (fw >> 16) & 0x3F,
        'window':       fw        & 0xFFFF,
    }

def ref_parse_udp(words: list) -> dict:
    """NET_PARSE_UDP: extract UDP header fields. 288c d5."""
    w = words[0]
    return {
        'src_port': (w >> 16) & 0xFFFF,
        'dst_port':  w        & 0xFFFF,
    }


# ── TCP FSM reference ─────────────────────────────────────────────────────────

# Transition table: (state, flags_mask, flags_value) → next_state
# Topology IS the transition table — each row is a NET_TCP_STATE tile config
TCP_TRANSITIONS = {
    # (current_state, required_flags) : next_state
    (fmt.TCP_LISTEN,       fmt.FLAG_SYN):                    fmt.TCP_SYN_RECEIVED,
    (fmt.TCP_SYN_SENT,     fmt.FLAG_SYN | fmt.FLAG_ACK):    fmt.TCP_ESTABLISHED,
    (fmt.TCP_SYN_RECEIVED, fmt.FLAG_ACK):                    fmt.TCP_ESTABLISHED,
    (fmt.TCP_ESTABLISHED,  fmt.FLAG_FIN):                    fmt.TCP_CLOSE_WAIT,
    (fmt.TCP_FIN_WAIT_1,   fmt.FLAG_ACK):                    fmt.TCP_FIN_WAIT_2,
    (fmt.TCP_FIN_WAIT_2,   fmt.FLAG_FIN):                    fmt.TCP_TIME_WAIT,
    (fmt.TCP_CLOSE_WAIT,   fmt.FLAG_FIN):                    fmt.TCP_LAST_ACK,
    (fmt.TCP_LAST_ACK,     fmt.FLAG_ACK):                    fmt.TCP_CLOSED,
}

def tcp_fsm_step(state: int, flags: int) -> int:
    """Step the TCP FSM. Returns next state."""
    # RST from any state → CLOSED
    if flags & fmt.FLAG_RST:
        return fmt.TCP_CLOSED
    for (req_state, req_flags), next_st in TCP_TRANSITIONS.items():
        if state == req_state and (flags & req_flags) == req_flags:
            return next_st
    return state  # no matching transition → stay


# ── Demo 1: IPv4 + TCP header parsing ────────────────────────────────────────

def demo_parse():
    print("\n── Demo 1: IPv4 + TCP header parsing ──")

    # Build a SYN packet: 192.168.1.100 → 10.0.0.1:443
    src_ip = fmt.ip_to_int("192.168.1.100")
    dst_ip = fmt.ip_to_int("10.0.0.1")
    ip_words = fmt.pack_ipv4_header(src_ip, dst_ip, fmt.PROTO_TCP, ttl=64)
    tcp_words = fmt.pack_tcp_header(54321, 443, fmt.FLAG_SYN)

    ip  = ref_parse_ipv4(ip_words)
    tcp = ref_parse_tcp(tcp_words)

    print(f"  IPv4: {src_ip>>24 & 0xFF}.{src_ip>>16 & 0xFF}."
          f"{src_ip>>8 & 0xFF}.{src_ip & 0xFF} → "
          f"{dst_ip>>24 & 0xFF}.{dst_ip>>16 & 0xFF}."
          f"{dst_ip>>8 & 0xFF}.{dst_ip & 0xFF}")
    print(f"  Protocol: {ip['protocol']} (TCP=6 ✓)  TTL: {ip['ttl']}")
    print(f"  TCP: {tcp['src_port']} → {tcp['dst_port']}  "
          f"flags=0x{tcp['flags']:02x} (SYN ✓)")
    return ip, tcp


# ── Demo 2: Packet classification pipeline ────────────────────────────────────

def demo_classify(ip: dict, tcp: dict):
    print("\n── Demo 2: Classification pipeline ──")

    is_tcp   = ref_classify_proto(ip['protocol'], fmt.PROTO_TCP)
    ttl_ok   = ref_ttl_check(ip['ttl'])
    is_https = ref_classify_port(tcp['dst_port'], 443)
    in_subnet = ref_prefix_match(
        ip['src_ip'],
        fmt.subnet_mask(16),
        fmt.ip_to_int("192.168.0.0")
    )
    is_syn   = ref_classify_proto(tcp['flags'] & fmt.FLAG_SYN, fmt.FLAG_SYN)

    print(f"  is_tcp={is_tcp}  ttl_ok={ttl_ok}  is_https={is_https}  "
          f"in_subnet={in_subnet}  is_syn={is_syn}")

    accept = is_tcp & ttl_ok & is_https & in_subnet
    print(f"  Decision: {'ACCEPT ✓' if accept else 'DROP'} "
          f"(TCP+TTL+HTTPS+subnet={accept})")
    return accept


# ── Demo 3: TCP FSM — full connection lifecycle ───────────────────────────────

def demo_tcp_fsm():
    print("\n── Demo 3: TCP FSM — connection lifecycle ──")
    print(f"  {'Event':<20}  {'State transition'}")
    print(f"  {'-'*20}  {'-'*30}")

    state = fmt.TCP_LISTEN
    # Active open (client side): SYN_SENT path
    # Passive close: CLOSE_WAIT → send FIN → LAST_ACK → CLOSED
    events = [
        ("SYN received",       fmt.FLAG_SYN),
        ("ACK received",       fmt.FLAG_ACK),
        ("Data exchange",      0x00),
        ("Peer sends FIN",     fmt.FLAG_FIN),
        ("App sends FIN",      fmt.FLAG_FIN),
        ("Peer ACKs our FIN",  fmt.FLAG_ACK),
    ]
    for event, flags in events:
        prev = state
        state = tcp_fsm_step(state, flags)
        print(f"  {event:<20}  {fmt.tcp_state_name(prev)} → "
              f"{fmt.tcp_state_name(state)}")

    return state


# ── Demo 4: Checksum accumulation (temporal blocking) ─────────────────────────

def demo_checksum():
    print("\n── Demo 4: IP checksum verification (temporal blocking) ──")
    # Minimal IPv4 header with known checksum=0 (for demo — real would compute)
    # One NET_CHECKSUM_STEP tile, 10 passes (one per 16-bit word in 20-byte header)
    header_words_16 = [
        0x4500, 0x003C, 0x1C46, 0x4000,
        0x4006, 0x0000,  # checksum field = 0 for computation
        0xC0A8, 0x0164,  # 192.168.1.100
        0x0A00, 0x0001,  # 10.0.0.1
    ]
    acc = 0
    for i, word in enumerate(header_words_16):
        acc = ref_checksum_step(acc, word)
        print(f"    Pass {i+1:2d}: word=0x{word:04x}  acc=0x{acc:08x}")

    # One's complement fold
    while acc >> 16:
        acc = (acc & 0xFFFF) + (acc >> 16)
    checksum = (~acc) & 0xFFFF
    print(f"  Final checksum: 0x{checksum:04x}  "
          f"({'valid' if checksum == 0 else 'fill in header'})")
    return checksum


# ── Validation ────────────────────────────────────────────────────────────────

def run_validation():
    print("\n── Tile reference validation ──")
    PASS, FAIL = 0, 0

    def check(label, got, expected):
        nonlocal PASS, FAIL
        if got == expected:
            PASS += 1; print(f"  [PASS] {label}")
        else:
            FAIL += 1; print(f"  [FAIL] {label}  got={got!r}  expected={expected!r}")

    # Flag extract
    check("FLAG_SYN from 0x02",   ref_flag_extract(0x02, fmt.FLAG_SYN), fmt.FLAG_SYN)
    check("FLAG_ACK from 0x12",   ref_flag_extract(0x12, fmt.FLAG_ACK), fmt.FLAG_ACK)
    check("no SYN in 0x10",       ref_flag_extract(0x10, fmt.FLAG_SYN), 0)

    # Protocol classify
    check("TCP proto match",       ref_classify_proto(6, fmt.PROTO_TCP), 1)
    check("UDP proto no match",    ref_classify_proto(17, fmt.PROTO_TCP), 0)

    # Prefix match
    ip  = fmt.ip_to_int("192.168.1.100")
    net = fmt.ip_to_int("192.168.0.0")
    msk = fmt.subnet_mask(16)
    check("192.168.1.100 in /16", ref_prefix_match(ip, msk, net), 1)
    ip2 = fmt.ip_to_int("10.0.0.1")
    check("10.0.0.1 not in /16",  ref_prefix_match(ip2, msk, net), 0)

    # Port classify
    check("port 443 match",        ref_classify_port(443, 443), 1)
    check("port 80 no match",      ref_classify_port(80, 443), 0)

    # TTL check
    check("TTL 64 ok",             ref_ttl_check(64), 1)
    check("TTL 0 drop",            ref_ttl_check(0), 0)
    check("TTL 1 ok",              ref_ttl_check(1), 1)

    # TCP state transitions
    check("LISTEN+SYN→SYN_RCV",
          tcp_fsm_step(fmt.TCP_LISTEN, fmt.FLAG_SYN), fmt.TCP_SYN_RECEIVED)
    check("SYN_RCV+ACK→ESTABLISHED",
          tcp_fsm_step(fmt.TCP_SYN_RECEIVED, fmt.FLAG_ACK), fmt.TCP_ESTABLISHED)
    check("ESTABLISHED+FIN→CLOSE_WAIT",
          tcp_fsm_step(fmt.TCP_ESTABLISHED, fmt.FLAG_FIN), fmt.TCP_CLOSE_WAIT)
    check("any+RST→CLOSED",
          tcp_fsm_step(fmt.TCP_ESTABLISHED, fmt.FLAG_RST), fmt.TCP_CLOSED)
    check("no matching flags → same state",
          tcp_fsm_step(fmt.TCP_ESTABLISHED, 0x00), fmt.TCP_ESTABLISHED)

    # Parse helpers
    check("ip_to_int round-trip",
          fmt.ip_to_int("192.168.1.1"), 0xC0A80101)
    check("subnet_mask /24",
          fmt.subnet_mask(24), 0xFFFFFF00)
    check("subnet_mask /16",
          fmt.subnet_mask(16), 0xFFFF0000)

    # IPv4 parse
    src = fmt.ip_to_int("10.0.0.1")
    dst = fmt.ip_to_int("8.8.8.8")
    iw = fmt.pack_ipv4_header(src, dst, fmt.PROTO_UDP, ttl=128)
    parsed = ref_parse_ipv4(iw)
    check("parse: protocol=UDP",   parsed['protocol'], fmt.PROTO_UDP)
    check("parse: ttl=128",        parsed['ttl'], 128)
    check("parse: src_ip",         parsed['src_ip'], src)
    check("parse: dst_ip",         parsed['dst_ip'], dst)

    # TCP parse
    tw = fmt.pack_tcp_header(12345, 80, fmt.FLAG_SYN | fmt.FLAG_ACK)
    pt = ref_parse_tcp(tw)
    check("tcp: src_port=12345",   pt['src_port'], 12345)
    check("tcp: dst_port=80",      pt['dst_port'], 80)
    check("tcp: SYN+ACK flags",    pt['flags'] & (fmt.FLAG_SYN | fmt.FLAG_ACK),
          fmt.FLAG_SYN | fmt.FLAG_ACK)

    # FormatDefinition
    check("NetTrix registered",    reg.get("NetTrix") is not None, True)
    check("10 valid tiles",        len(fmt.valid_tiles), 10)
    check("boundary_in correct",   fmt.boundary_in, "NET_PARSE_IPV4")

    print(f"\n  Results: {PASS} passed, {FAIL} failed")
    return FAIL == 0


if __name__ == "__main__":
    print("⬡ NetTrix — network packet processing")
    print("=" * 55)

    ok = run_validation()
    ip, tcp = demo_parse()
    demo_classify(ip, tcp)
    final_state = demo_tcp_fsm()
    demo_checksum()

    print(f"\n{'='*55}")
    assert final_state == fmt.TCP_CLOSED, \
        f"FSM should end CLOSED, got {fmt.tcp_state_name(final_state)}"
    if ok:
        print("All demos passed ✓")
    else:
        print("SOME TESTS FAILED")
        sys.exit(1)
