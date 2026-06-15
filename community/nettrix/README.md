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
