# NetTrix

Network packet processing and routing domain for UniCell.

**Status: Placeholder — full design review and creation cycle required.**

NetTrix covers network packet inspection, routing decisions, flow classification,
and protocol processing as parallel cell pipelines. The fabric's parallel firing
model maps naturally to per-packet and per-flow processing.

---

## Design Questions Outstanding

Before implementation, the following need to be resolved:

- **Address translation bridge:** fabric uses 16-bit logical addresses;
  network uses IP addresses, port numbers, packet identifiers. The
  NetTrix bridge must translate fabric fires to network destinations.
  See hierarchical address model in `PLAN.md`.

- **Format design:** what is the atomic unit? Per-packet (header fields),
  per-flow (aggregated state), or per-byte (deep inspection)?
  Each implies different cell word widths and tile granularity.

- **Timing model:** network packets arrive with variable inter-arrival
  times. The two-arrival model tolerates latency naturally, but
  the pipeline depth accounting assumes fixed latencies. Variable
  packet arrival needs careful treatment.

- **State management:** stateful flows (TCP reassembly, connection
  tracking) require persistent cell state across packets. This is
  the `latch_in` / `loop_back` model but at packet granularity —
  design needs to be worked out.

- **Integration with PCIe path:** packets arrive via PCIe from the
  host NIC. The PCIe DDR streaming path (post Arria 10 bring-up)
  is the input path. NetTrix cannot be designed until that path
  is characterised.

---

## Candidate Tiles (preliminary, not implemented)

| Tile | Operation |
|------|-----------|
| `NET_PACK` | pack header fields into cell words |
| `NET_UNPACK` | unpack cell words to header fields |
| `NET_MATCH_IP` | IP address match (preloaded prefix) |
| `NET_MATCH_PORT` | port range match |
| `NET_CLASSIFY` | flow classification (5-tuple hash) |
| `NET_RATE_LIMIT` | token bucket (preloaded rate) |
| `NET_COUNT` | packet/byte counter per flow |
| `NET_ROUTE` | next-hop selection (preloaded FIB) |

---

## Dependencies

- Arria 10 bring-up complete
- PCIe DDR streaming path working
- Address expansion bridge design resolved (see `PLAN.md`)
- Full format design review session

---

*This folder is reserved. Do not submit community contributions to
NetTrix until the format definition is published.*

---

## Primary Use Case: Transparent HA Routing with Stream Mirroring

The strongest near-term application for NetTrix is hardware-level high
availability routing with zero-impact failover. The card sits between
the WAN and the servers — routing intelligence lives in the fabric,
servers are just consumers.

### Architecture

```
WAN / Internet
      ↓
NetTrix fabric (UniCell card)
  ├── packet classification / inspection
  ├── rate limiting / QoS
  ├── route decision (preloaded FIB)
  ├──→ Primary server   (always receiving)
  └──→ Mirror server    (always receiving — shadow stream)

Primary fails:
  Heartbeat tile stops firing → failover cell fires
  Card stops routing to primary
  Mirror already has full state → zero user impact
  No TCP reset, no session loss, users see nothing

Primary recovers:
  Heartbeat resumes → card detects automatically
  Routing to primary resumes
  Mirror continues — resync is passive (mirror never stopped)
```

### Why this works on UniCell

- **Split output is free:** the two-arrival firing model produces both
  output paths in the same tick — mirroring costs no extra latency
- **Heartbeat detection is a cell pipeline:** a rate-monitoring tile
  watches for expected firing rate from primary. No software in the
  critical path, no management CPU round-trip
- **Reconfigurable without downtime:** change routes, thresholds, or
  mirror rules via CMD_RECONFIGURE — fabric keeps forwarding
- **Recovery is passive:** mirror server never stops receiving, so
  primary resync on recovery requires no explicit state transfer

### Comparison to existing solutions

| Approach | Failover time | Session loss | Reconfigurable |
|----------|--------------|-------------|----------------|
| Standard mirror switch | ~50ms | Yes (TCP reset) | No |
| Software HA (keepalived etc.) | 1–30s | Often | Yes |
| UniCell NetTrix | <1 tick (~40ns at 25MHz) | No | Yes |

### Throughput expectations

- At 25MHz bring-up clock: ~1GbE equivalent (1.86Mpps, 64-byte packets)
- At 200MHz target clock: ~8GbE equivalent (14.88Mpps)
- Scales linearly with clock — no logic changes needed

1GbE at 25MHz is already useful for industrial, embedded, and legacy
environments. 200MHz hits 10GbE line rate for 64-byte packets.

### Management plane

Data plane: pure fabric — zero software in critical path.
Management plane: UART/PCIe configuration via CMD_RECONFIGURE.
- Load new FIB (routing table) entries
- Update heartbeat thresholds
- Add/remove mirror destinations
- Change QoS parameters

All management operations take effect on the next cell reconfiguration
cycle — sub-millisecond with no traffic interruption.

### Product positioning

This is a Tier 2 product — sits transparently between NIC and host.
Natural fit alongside the UniCell Security Module concept (fabric
topology as root of trust). A card that simultaneously provides:
- Hardware routing / load balancing
- Transparent HA failover
- Packet inspection / filtering
- Security enforcement

With zero software in the data path and full reconfigurability from
the management plane.
