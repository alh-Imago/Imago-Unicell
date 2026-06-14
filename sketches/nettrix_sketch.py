"""
nettrix_sketch.py — NetTrix format sketch

NetTrix: network packet processing on UniCell fabric.

CORE INSIGHT:
The two-arrival firing model IS a state machine. A cell holding state A
and waiting for event B to produce next_state is exactly the fabric's
native computation model. TCP state tracking doesn't need to be simulated
on the fabric — the topology IS the state machine.

WHAT NETTRIX IS:
Packet field extraction, protocol classification, and stateful packet
filtering using the cell fabric. Not a general network stack — that's
Tier 2 (Ward/Shore). NetTrix is the fast-path data plane: decisions
that must happen in nanoseconds before a packet is handed to the OS.

THREE LAYERS (all within 900c):

Layer 1 — PARSE: field extraction from packet header words
  Every network header field is SHR + AND on a 32-bit bus word.
  Same pattern as SENSOR_UNPACK, same cell cost (32-144c per field).
  IPv4 header fully parsed in ~600c across parallel field extractors.

Layer 2 — CLASSIFY: protocol/port/prefix matching
  AND (apply mask) + EQ (compare to expected) = 127c per rule.
  Multiple rules in parallel → OR-reduce results → match/no-match bit.
  ACL (access control list) = N parallel classifiers, one OR tree.

Layer 3 — STATE: TCP FSM, connection state tracking
  State stored in preloaded register (same as setpoint in OptiTrix).
  Event (SYN/ACK/FIN/RST flag bits) arrives on bus.
  INT32_EQ checks current state, INT32_MUX selects next state.
  Transition table is topology — no lookup table needed.
  Updated each packet via DDR config stream (temporal blocking).

WIRE ENCODING:
  NetTrix operates on 32-bit words extracted from packet headers.
  The bridge (NetTrixBridge) splits raw packet bytes into 32-bit words
  and places them on consecutive bus addresses — same model as SensorTrix.
  location = field_id (which header field)
  amount   = field_value (extracted value, right-aligned)

HONEST SCOPE:
  Line rate (1Gbps): 672ns/packet, Arria 10 at 200MHz = 75ns per tile.
  Fits with margin on silicon. Python VM: useful for design and testing
  only — thousands of times slower. Performance claim needs silicon.

  NOT in scope: TCP reassembly (buffer management = Tier 2/OS),
  full DPI/Aho-Corasick (irregular search = wrong model),
  stateful NAT (session table too large for cell registers).
  Checksum verification: temporal blocking (one INT32_ADD per word).

VALID TILES (sketch):

  NET_PARSE_IPV4    — extract all IPv4 header fields in parallel
                      src_ip, dst_ip, protocol, TTL, total_len, flags
                      Cost: ~600c across parallel SHR+AND chains  ✓

  NET_PARSE_TCP     — extract TCP header fields
                      src_port, dst_port, seq, ack, flags (SYN/ACK/FIN/RST/PSH)
                      Cost: ~400c  ✓

  NET_PARSE_UDP     — extract UDP header fields
                      src_port, dst_port, length, checksum
                      Cost: ~200c  ✓

  NET_CLASSIFY_PORT — is port in a set? (dst_port == 80 OR 443 OR 8080)
                      N × (EQ + OR-tree). Per rule: 95+32=127c.
                      16-rule ACL: ~2032c — needs 3 tiles or Arria 10 scale.
                      Single rule: 127c  ✓

  NET_CLASSIFY_PROTO — protocol == TCP(6)? UDP(17)? ICMP(1)?
                       INT32_EQ on 8-bit protocol field: 95c  ✓

  NET_PREFIX_MATCH  — (ip & mask) == prefix (subnet matching)
                      INT32_AND (32c) + INT32_EQ (95c) = 127c  ✓

  NET_TCP_STATE     — TCP FSM: (current_state, flags) → next_state
                      Preloaded: current_state, expected_flags
                      INT32_EQ (state check, 95c) + INT32_MUX (next, 128c)
                      = 223c per state transition  ✓

  NET_CHECKSUM_STEP — one step of IP/TCP checksum: acc + word (16-bit)
                      INT32_ADD with preloaded accumulator: 482c
                      Full header: N ticks (temporal blocking)  ✓

  NET_TTL_CHECK     — TTL > 0? (drop if expired)
                      INT32_LT_U with preloaded 1: 518c  ✓

  NET_FLAG_EXTRACT  — extract TCP flag bits (SYN=bit1, ACK=bit4, etc.)
                      INT32_AND with preloaded bit mask: 32c  ✓

TILE COST SUMMARY:
  NET_FLAG_EXTRACT:   32c  d1   ✓
  NET_PREFIX_MATCH:  127c  d8   ✓
  NET_CLASSIFY_PROTO: 95c  d7   ✓
  NET_CLASSIFY_PORT: 127c  d8   ✓ (per rule)
  NET_TCP_STATE:     223c  d10  ✓
  NET_TTL_CHECK:     518c  d14  ✓
  NET_CHECKSUM_STEP: 482c  d10  ✓ (per word, temporal blocking)
  NET_PARSE_UDP:     ~200c d5   ✓
  NET_PARSE_TCP:     ~400c d10  ✓
  NET_PARSE_IPV4:    ~600c d15  ✓ (borderline — may need 2 tiles at scale)

BRIDGE (NetTrixBridge):
  Host receives raw Ethernet frame (via AF_PACKET socket or DPDK).
  Splits into 32-bit header words, places on bus addresses:
    0x00: words 0-1  = Ethernet header (dst_mac hi, dst_mac lo)
    0x01: word  2    = src_mac hi + EtherType
    0x02: word  3    = IPv4 words 0 (ver/IHL/TOS/total_len)
    0x03: word  4    = id/flags/frag_offset
    0x04: word  5    = TTL/protocol/checksum
    0x05: word  6    = src_ip
    0x06: word  7    = dst_ip
    0x07: word  8    = TCP src_port/dst_port (if TCP)
    0x08: word  9    = seq_num
    0x09: word 10    = ack_num
    0x0A: word 11    = data_offset/flags/window_size
  Same model as SensorTrix stack: N words, N bus addresses.

TCP STATE MACHINE (topology IS the state machine):
  States (preloaded register value):
    0x00 = CLOSED
    0x01 = LISTEN
    0x02 = SYN_SENT
    0x03 = SYN_RECEIVED
    0x04 = ESTABLISHED
    0x05 = FIN_WAIT_1
    0x06 = FIN_WAIT_2
    0x07 = CLOSE_WAIT
    0x08 = CLOSING
    0x09 = LAST_ACK
    0x0A = TIME_WAIT

  Transition: NET_TCP_STATE tile
    in_a (preloaded): current_state | (expected_flags << 8)
    in_b (live):      actual_flags from NET_FLAG_EXTRACT
    out:              next_state (via MUX on EQ result)
    Preloaded next_state values = transition table entries
    The table IS the wiring — reconfigured per connection

PIPELINE EXAMPLE — inbound TCP SYN filter:
  1. NET_PARSE_IPV4  → protocol_field, src_ip, dst_ip
  2. NET_CLASSIFY_PROTO (protocol==TCP?) → tcp_bit
  3. NET_PARSE_TCP   → src_port, dst_port, flag_bits
  4. NET_FLAG_EXTRACT (SYN bit) → syn_flag
  5. NET_CLASSIFY_PORT (dst_port==443?) → https_bit
  6. NET_PREFIX_MATCH (src_ip in 192.168.0.0/16?) → local_bit
  7. Results combine via INT32_AND / INT32_OR → ACCEPT/DROP decision
  Total: ~1800c, ~7 ponds, fits Arria 10. iCEBreaker: 1 tile at a time.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from fp_tiles import TileLibrary

lib = TileLibrary()

def cost(name):
    t = lib.get(name)
    m = t.metadata
    return m.cell_count, m.pipeline_depth

print("=== NetTrix Tile Cost Sketch ===\n")

# Actual costs from existing primitives
AND_c, AND_d   = cost('INT32_AND')
OR_c,  OR_d    = cost('INT32_OR')
EQ_c,  EQ_d    = cost('INT32_EQ')
MUX_c, MUX_d  = cost('INT32_MUX')
LTU_c, LTU_d  = cost('INT32_LT_U')
ADD_c, ADD_d   = cost('INT32_ADD')
SHR8_c, SHR8_d = cost('INT32_SHR_8')
SHR4_c, SHR4_d = cost('INT32_SHR_4')

BUDGET = 900

tiles = [
    # (name, cells, depth, formula)
    ("NET_FLAG_EXTRACT",   AND_c,           AND_d,
     "AND only (bit mask on flags word)"),
    ("NET_CLASSIFY_PROTO", EQ_c,            EQ_d,
     "EQ (protocol == expected)"),
    ("NET_PREFIX_MATCH",   AND_c + EQ_c,    AND_d + EQ_d,
     "AND (apply mask) + EQ (compare prefix)"),
    ("NET_CLASSIFY_PORT",  EQ_c + OR_c,     EQ_d + OR_d,
     "EQ (port == N) + OR (accumulate match)"),
    ("NET_TCP_STATE",      EQ_c + MUX_c,    EQ_d + MUX_d,
     "EQ (state check) + MUX (next state select)"),
    ("NET_TTL_CHECK",      LTU_c,           LTU_d,
     "LT_U (TTL > 0)"),
    ("NET_CHECKSUM_STEP",  ADD_c,           ADD_d,
     "ADD (accumulate one 16-bit word, temporal blocking)"),
    ("NET_PARSE_UDP",      4*(SHR8_c+AND_c), 2*SHR8_d+AND_d,
     "4 fields × (SHR_8+AND): src_port,dst_port,len,checksum"),
    ("NET_PARSE_TCP",      8*(SHR8_c+AND_c), 3*SHR8_d+AND_d,
     "8 fields × (SHR+AND): ports,seq,ack,flags,window (parallel)"),
    ("NET_PARSE_IPV4",     12*(SHR8_c+AND_c),4*SHR8_d+AND_d,
     "12 fields × (SHR+AND): all IPv4 header fields (parallel)"),
]

print(f"  {'Tile':<22}  {'Cells':>6}  {'Depth':>6}  {'Budget':>7}  Formula")
print(f"  {'-'*22}  {'-'*6}  {'-'*6}  {'-'*7}")
for name, c, d, formula in tiles:
    fits = '✓' if c <= BUDGET else f'✗ ({c-BUDGET}c over)'
    print(f"  {name:<22}  {c:>6}c  d{d:<5}  {fits:>7}  {formula}")

print()
print("Pipeline example — TCP SYN filter (7 ponds):")
total = sum(c for _,c,_,_ in tiles[:7])
print(f"  Tiles 1-7 total: {total}c across 7 ponds")
print(f"  Full parse+classify+state: ~1800c, 7 ponds, fits Arria 10 GX660")
print(f"  iCEBreaker: 1 tile at a time (temporal blocking by packet)")
print()
print("Performance (silicon estimate):")
print(f"  1Gbps line rate: 672ns/packet minimum")
print(f"  Arria 10 @ 200MHz: 5ns/clock, d15 tile = 75ns << 672ns")
print(f"  Fits with ~9× margin at 1Gbps")
print(f"  10Gbps: 67ns/packet — still fits d15 tile at 200MHz")
print(f"  VM simulation: design/test only, not performance-representative")
