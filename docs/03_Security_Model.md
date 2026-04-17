# Imago UniCell — Security Model
## Claudette v1.1

---

## Overview

The Claudette security model is built on a single primitive applied at every layer:

```
(process_mask & resource_mask) != 0
```

One bitwise AND. If it passes, the resource is visible. If it fails, the resource is **absent** — not denied, not visible, not detectable. An attacker cannot even learn that a protected resource exists.

There are nine security layers. Each enforces the same primitive at a different level of the architecture, from the raw silicon cell up to the cross-card federation. No layer requires knowledge of any other layer to function correctly.

---

## The Address Space and Programming Model

### What a user process can address

A user process runs inside a Pond. Its address space is bounded by that Pond's `base_address` and `region_size`. All cell addresses issued by user code are PTT-relative — they are offsets from the Pond's base, not raw system addresses.

```
User process issues address: 0x0010
PTT resolves to:  base_address + 0x0010 = 0x00200010  (absolute bus address)

User process cannot issue:   0x00500000  (Shore registry address)
                             0x00C00000  (keyboard bridge address)
                             0x00F00000  (display region)
```

**This is the sandbox.** User code physically cannot construct an absolute address that escapes its Pond region — the PTT translation is the only path from user address to bus address, and the PTT only maps offsets within the Pond's allocated range.

### What protects the config register

The config register (gate_state, mode flags, auth mask, _config_upper) is written only by CMD_RECONFIGURE — command code 3. This command is system-only: it requires the 12-bit auth token in Bus 1 bits 4-14. The cell silently rejects CMD_RECONFIGURE without the correct token.

A user process running inside a Pond:
- Uses the user CommandInterface, which issues PTT-relative addresses
- Does NOT have the auth token
- Cannot issue CMD_RECONFIGURE even if it constructs the right bus format
- Cannot alter any cell's gate_state, mode flags, or auth mask

**The config register is the protected latch.** User code can write data to cells (CMD_DATA_WRITE) and read outputs, but cannot reconfigure the cells themselves. The cell topology, the loop mode flags, the auth mask — all locked at boot by the BIOS-Plus sequence, accessible only to the system CommandInterface with the 12-bit token.

### The _config_upper extension

The 64-bit config register adds `_config_upper` (bits 32-63). This stores the upper 32 bits of a 64-bit forwarding address for bridge cells. It is also protected by CMD_RECONFIGURE + scope=EXTENDED — same auth requirement, same silent rejection on mismatch.

User code cannot set `_config_upper`. It cannot make a bridge cell forward to an arbitrary 64-bit address. Only the OS (via the system CommandInterface with the auth token) can configure bridge cell routing.

---

## Layer 1 — Hardware: Cell Auth Token

The BIOS-Plus chip generates a 12-bit random auth token at power-on from its hardware RNG. This token is distributed to every cell on the card during the boot sequence via CMD_RECONFIGURE.

**Enforcement:** CMD_RECONFIGURE carries the auth token in Bus 1 bits 4-14. The cell silently rejects the command if the token does not match. Silent rejection is deliberate — no error signal means an attacker cannot probe for the correct token.

**Scope:** card-level. All cells on one card share the same token. A program on one card cannot reconfigure cells on another card without that card's token.

---

## Layer 2 — Data: Salt Key Encryption

The BIOS-Plus chip generates a 64-bit salt key at power-on from the same entropy source. The salt key never leaves the BIOS chip — destroyed on physical tamper.

**Uses:**
- HIDDEN Pond encryption — data unreadable without the card's BIOS chip
- Licensed tile programs — encrypted against a specific card's salt key (hardware DRM without a separate DRM system)

Both the auth token and salt key derive from the same entropy pool at boot. The auth token protects cell reconfiguration (command level). The salt key protects data and intellectual property (content level). They are independent secrets.

---

## Layer 3 — Addressing: PTT Hidden Process Mask

Every process has a hidden `process_mask` (32-bit) in its PTT entry. The mask is set by COMPANION at process creation and is **never readable by the process itself**.

```
Mask layout (32 bits):
  bits  0-7:   tenant ID        (which user/organisation)
  bits  8-15:  role flags       (admin, user, service, etc.)
  bits 16-23:  feature flags    (which capabilities enabled)
  bits 24-31:  reserved

Scope mapping:
  bits  0-7:   LOCAL PTT scope membership
  bits  8-15:  SHORE PTT visibility
  bits 16-23:  EXTENDED PTT reachability
```

**Inheritance:** every object a process creates inherits the creator's mask. There is no escalation path. A process with tenant-3 bits can only create objects that also belong to tenant-3.

---

## Layer 4 — Discovery: Mask-Filtered Cast/Ripple

Cast and Ripple queries discover resources across the system. Before a Stone can touch a Pond, the check `(process_mask & bridge.access_mask) != 0` is evaluated.

**The critical property:** a failing mask check causes the Pond to be **absent from results**, not denied. The query returns exactly as if the Pond does not exist. The querying process cannot even learn that a protected resource is present.

This is enforced in `_touch_pond()` before the owner announcement — the Pond owner does not learn about the query if the mask check fails.

**Scope-ordered search:** Cast now searches LOCAL scope first, SHORE second, EXTENDED last. The Stone stops at the nearest scope that returns a match (unless collect_all=True).

---

## Layer 5 — Bridge Access: Bidirectional Mask Check

Every bridge has a 32-bit `access_mask` checked in both directions:

```
Inbound:  (process_mask & bridge.access_mask) != 0
Outbound: (process_mask & bridge.access_mask) != 0
```

Both checks happen. Both must pass. O(1) per check regardless of system size.

**Why bidirectional:** inbound-only allows a low-privilege process to receive data it shouldn't see via the outbound path. Bidirectional closes that covert channel.

The mask check happens before the whitelist check. If the mask fails, no log entry is written and no acknowledgement is sent.

---

## Layer 6 — Identity Inheritance: Mask Lineage

```
User account (mask set at account creation)
  → Session (inherits user mask)
    → COMPANION instance (inherits session mask)
      → Pond (inherits COMPANION mask)
        → Bridge (inherits Pond mask)
          → FS Pond (inherits Bridge mask)
            → File (inherits FS Pond mask)
```

No object can have a higher mask than its creator. Monotonically non-increasing from creator to created object.

---

## Layer 7 — Session Provisioning: Template Pond Cloning

When a user joins, COMPANION clones a Template Pond matched to the user's mask pattern. Each user gets their own private namespace — same template, completely separate address spaces. User A's Ponds are never visible to User B.

Template Ponds are stored in the ShoreKeeper's hidden table, keyed by mask pattern. Users cannot see or access the template table.

---

## Layer 8 — Filesystem: Mask-Shaped Views

The filesystem is a collection of FS Ponds. Each path entry is a bridge. Directory listings are filtered by the caller's mask — if `(process_mask & bridge.access_mask) == 0`, the path is **absent** from the listing.

Two users with different masks see different directory structures. A file added to a protected directory cannot accidentally expose itself to unprivileged users — the bridge mask on the directory entry controls visibility.

With 64-bit addressing (`_config_upper` on the FS bridge cell), files larger than 4GB are addressed directly. No split files, no indirect tables. The bridge IS the file pointer.

---

## Layer 9 — Card Boundary: ShoreKeeper Validation

All cross-card traffic is validated at both ends:

1. **Auth check:** source card's auth token must be known to the destination ShoreKeeper
2. **Mask check:** `(process_mask & bridge.access_mask) != 0` in both directions
3. **PTT translation:** PTT-relative addresses translated to raw addresses per card

The cross-card bus carries only pre-validated data and aggregated heartbeat summaries. Individual cell states, PTT hidden fields, auth tokens, salt keys, and raw Ward data never cross card boundaries.

Neither ShoreKeeper trusts the other blindly — the auth check at the destination ensures the source card is legitimate.

---

## Scaling Property

The cost of security enforcement does not increase with system size:

```
Layer 1 — auth token:    1 comparison per command
Layer 3 — process mask:  1 lookup per operation
Layer 4 — cast filter:   1 AND per discovered item
Layer 5 — bridge check:  1 AND per bridge transit
Layer 6 — inheritance:   0 cost (mask copied at creation)
Layer 9 — card boundary: 1 AND per hop
```

No security operation is O(n) in the number of users, processes, or resources. A system with one million Ponds has the same per-operation security cost as one with ten Ponds.

---

## Conditional Ponds — Lifecycle Contracts

A CONDITIONAL Pond carries an explicit lifecycle contract set at creation. This is one of the more distinctive features of the Claudette OS — a Pond that knows how and when to end itself.

### Why it matters

Most OS resource management is reactive — a process dies, the OS cleans up its resources. CONDITIONAL Ponds are proactive — the resource itself carries the contract specifying its own lifecycle. The Ward evaluates the contract on each heartbeat. When the condition is met, the action fires once and the contract is consumed.

This is particularly useful for:
- **Session Ponds:** dissolve when the session closes (DISSOLVE_EXTERNAL)
- **Work queues:** freeze state when the job completes (ACTION_CHECKPOINT + DISSOLVE_COMPLETE)
- **Time-bounded resources:** dissolve after N ticks (DISSOLVE_TIME)
- **Dependent resources:** dissolve when another process returns (DISSOLVE_RETURN)

### Contract structure

```python
pond.ward.set_dissolve_contract(
    condition = DISSOLVE_TIME,    # when to act
    action    = ACTION_DISSOLVE   # what to do
)
```

**Five condition types:**

| Condition | Meaning |
|-----------|---------|
| `DISSOLVE_TIME` | After N ticks have elapsed |
| `DISSOLVE_RETURN` | When process P returns value V |
| `DISSOLVE_COMPLETE` | When process P finishes |
| `DISSOLVE_EXTERNAL` | When session/connection closes |
| `DISSOLVE_COMPOUND` | ANY(...) or ALL(...) of the above |

**Three action types:**

| Action | Meaning |
|--------|---------|
| `ACTION_DISSOLVE` | Clean termination — release all cells |
| `ACTION_FREEZE` | Halt cells, preserve state for debug |
| `ACTION_CHECKPOINT` | Save VM image snapshot, then dissolve |

### Contract evaluation

The contract is stored as a hidden field on the Ward — not readable by the Pond itself. The Ward evaluates `evaluate_dissolve(context)` on each heartbeat. When the condition is met, the action fires exactly once and the contract is consumed.

COMPOUND conditions allow combining conditions with ANY (first to trigger wins) or ALL (all must be true simultaneously):

```python
# Dissolve when EITHER time limit reached OR external connection closes
pond.ward.set_dissolve_contract(
    condition = DISSOLVE_COMPOUND,
    action    = ACTION_CHECKPOINT,
    sub_conditions = [
        (DISSOLVE_TIME,     {'ticks': 100_000}),
        (DISSOLVE_EXTERNAL, {'session_id': 'user_alice'}),
    ],
    compound_mode = 'ANY'
)
```

### Security

The contract is hidden from the Pond — it cannot read its own dissolve conditions. This prevents a Pond from trying to extend its own lifetime by manipulating the contract. Only COMPANION can set or clear a dissolve contract (through the Ward, via auth-protected command).

---

## Mask System Summary

```
32-bit process_mask:
  bits  0-7:   tenant      — LOCAL PTT scope
  bits  8-15:  role        — SHORE PTT visibility  
  bits 16-23:  feature     — EXTENDED PTT reachability
  bits 24-31:  reserved

Check at every boundary: (process_mask & resource_mask) != 0
Fail result: absent (not denied, not visible, not logged)

The same primitive at 9 levels:
  cell auth, salt key, PTT mask, cast filter,
  bridge check, inheritance, template clone,
  FS view, card boundary
```
