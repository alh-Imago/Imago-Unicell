# Distributed UniCell Fabric Architecture

## Concept

The same address-matching primitive that routes between local ponds
can route between physically remote UniCell fabrics. A cell firing in
Fabric A propagates its output address — if that address resolves to
a remote fabric, the signal crosses the network boundary transparently.

The wired-OR bus becomes a network bus. Same topology, same primitive,
longer wires.

---

## Latency Tiers

| Scope       | Medium              | Latency      |
|-------------|---------------------|--------------|
| Local       | Wired-OR on silicon | Nanoseconds  |
| Chassis     | PCIe/AXI bridge     | Microseconds |
| Remote LAN  | Network bridge      | ~100µs       |
| Remote WAN  | Network bridge      | Milliseconds |
| Distributed | Multi-fabric mesh   | Variable     |

The model is identical at every tier. Only the latency changes.

---

## Connection Lifecycle (Virtual Circuit Model)

### Phase 1 — Discovery (Shore lookup, one-time cost)
- Fabric A sends address query through Shore routing table
- Lookup finds Fabric B has matching cells / available address space
- Route parameters exchanged, both ends notified
- Similar to TCP SYN/SYN-ACK but at fabric level

### Phase 2 — Bridge Instantiation
- Fabric A allocates a bridge cell pointing to Fabric B's address space
- Fabric B allocates a reciprocal bridge cell pointing back to Fabric A
- Both bridge cells registered with their local Shore
- Shore lookup table updated: "address range X → Fabric B bridge cell"
- Direct path now open — Shore not involved in data flow

### Phase 3 — Flowing Data (Shore bypassed)
- Cell fires in Fabric A → output address matches bridge cell
- Bridge cell forwards signal to Fabric B's bus directly
- Fabric B cell matching that address fires
- Bidirectional, symmetric, continuous flow
- No lookup overhead per packet — route is in the topology

### Phase 4 — Teardown
- Either end deregisters its bridge cell
- Shore cleans up routing table entries
- Address space reclaimed

---

## Key Properties

**Single primitive**: Bridge cells are ordinary UniCell cells. Their output
address happens to resolve to a remote bus. The fabric doesn't know or care
that the "wire" is a network link.

**Virtual circuit**: Lookup cost is O(1) at connection time, O(0) during
data flow. Equivalent to ATM virtual circuits or MPLS label switching,
but implemented in fabric topology rather than network hardware.

**Symmetric**: Both ends open bridges simultaneously. Either end can
initiate teardown. No client/server distinction.

**Composable**: A chain of fabrics — Fabric A bridges to B bridges to C.
From A's perspective, C is just an address. Intermediate topology transparent.

**Scalable**: 64-bit address space (32-bit local + 32-bit pond/shore via
GS_ADDR_LATCH). Remote fabric identity in upper 32 bits.

---

## Distributed Computation Model

A computation too large for one fabric spills naturally into connected fabrics:
1. Compiler allocates cells across available fabrics
2. Cross-fabric connections become bridge cells automatically
3. Execution proceeds — cells fire without knowing physical location
4. Results return via the same bridge topology

No MPI, no RPC, no serialisation. The topology IS the distribution.

---

## Security Implications

Each bridge is a registered connection with known topology. Shore maintains
the routing table — unauthorised connections have no entry and cannot reach
the fabric. Combined with the rolling auth / fabric topology security model:

- **Discovery-resistant**: No address responds without a valid route entry
- **Connection-authenticated**: Bridge instantiation requires auth handshake
- **Topology-bound**: Bridge cell gate configuration is part of auth —
  cloning the address without matching topology doesn't work

---

## Relationship to Existing Architecture

- **Shore**: already routing authority for local ponds — extends to remote fabric routing
- **64-bit addressing**: upper 32 bits (GS_ADDR_LATCH) already planned — remote fabric ID lives here
- **Bridge cells**: already exist for inter-zone connections — same mechanism at network scope
- **Pond**: becomes unit of remote addressability — "connect to Pond X on Fabric Y"

---

## The Fundamental Truth

Ponds don't connect. Shores don't connect. Networks don't connect.
**Only cells connect.** Everything else is addressing abstraction.

A "pond-to-pond" connection is always two bridge cells — one in each pond —
with an address that spans whatever distance lies between them.
The fabric is cell-to-cell all the way from local silicon to global network.

---

*Noted: 2026-06-02, during Kintex-7 PCIe bring-up session*
