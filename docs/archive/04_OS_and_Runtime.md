# Imago UniCell — OS and Runtime
## Claudette v1.1 — Claudette OS

---

## Overview

> **v1.1 addressing note:** Shore V2 is a directory and fallback service in v1.1, not a routing component. Bridge cells carry full 64-bit destination addresses natively. Shore is consulted once for name resolution; after that routing is entirely in the bridge cell, with Shore out of the data path.


Claudette is the OS that runs on the Imago UniCell architecture. It is not a conventional OS — there is no kernel, no process scheduler in the traditional sense, and no memory allocator. Instead it is a set of persistent objects (COMPANION, Shore, ShoreKeeper) that manage the cell array on behalf of user programs.

The OS objects are themselves Ponds — they live in the same NOR cell fabric they manage. COMPANION is a HIDDEN LIBRARY Pond. Shore is a HIDDEN SHORE Pond. The OS is not separate from the hardware it manages; it is woven into it.

---

## Claudette OS Components

### COMPANION — The OS Anchor

COMPANION is the single permanent anchor of the entire system. One instance per card. HIDDEN security level. Cannot be destroyed without the heritage flag. Permanent anchor.

**Responsibilities:**
- Rule engine: receives Ward escalations, decides RESTART/ISOLATE/MIGRATE
- Key issuance and revocation: assigns auth tokens to new processes
- Template Pond cloning: provisions new user sessions
- Region allocation: assigns Pond address spaces

**The rule engine** runs on each Ward escalation in priority order:

```
1. STALLED  → try ACTION_RESTART → if restart fails → ACTION_ISOLATE
2. ISOLATED → try ACTION_MIGRATE → if migrate fails → stay ISOLATED
3. SILENT   → log + ACTION_ISOLATE (device disconnect)
4. THERMAL  → ACTION_MIGRATE (move to cooler stack)
```

COMPANION's `_execute_action()` calls `pond.restart()` directly for ACTION_RESTART, with automatic ISOLATE fallback if restart fails.

### Ward — The Health Monitor

One Ward per Pond. Runs on each heartbeat tick. Tracks:

**Emission history:** rolling window of how many cells fired per tick. Drops below threshold → STALLED detection.

**Thermal tracking:**
```
thermal_load:   current power dissipation estimate
thermal_limit:  Ward's threshold (set by ShoreKeeper zone)
thermal_trend:  rate of change per heartbeat

Thermal states:
  NOMINAL   — load < 100% of limit
  THROTTLE  — load ≥ 100% of limit
  FREEZE    — load ≥ 120% of limit
  MIGRATE   — sustained FREEZE → ShoreKeeper requests migration
```

**State machine:**
```
IDLE → HEALTHY (first emission detected)
HEALTHY → DEGRADED (emission rate drops, not yet stalled)
DEGRADED → STALLED (silence for N ticks)
HEALTHY/DEGRADED → SILENT (no data at bridge, device disconnect)
STALLED/SILENT → ISOLATED (COMPANION decision)
any → HEALTHY (normal emission resumes)
```

**Dissolve contracts:** see the Security Model document for full detail on the five condition types and three action types.

### ShoreV2 — The Card Registry

Shore is the card's address book. Every Pond, bridge, and tile is registered here at creation. Shore tracks:

- **Registry** (`_entries`): name → ShoreEntry with address, scope, object_id, Ward state
- **Connections** (`_connections`): live connections between resources
- **Translation** (`_translation`): legacy proxy table (retired — use register_extended_v2)

**Three-scope addressing:**
```
scope=LOCAL:    32-bit address — within this stack
scope=SHORE:    48-bit address — within this card
scope=EXTENDED: 64-bit address — beyond this card

ShoreEntry stores: local_address (lower 32) + object_id (upper 32)
Together: full_address = (object_id << 32) | local_address
```

**The proxy mechanism is retired.** The old `PROXY_BASE = 0xF0000000` range is freed (256MB per stack, 28GB per 12-layer card). New code uses `register_extended_v2(local_addr, config_upper)` which stores the (lower, upper) pair directly in ShoreEntry. Legacy `register_extended()` retained for loading v1/v2 VM images.

**Key methods:**
```python
shore.register(entry)                     # add to registry
shore.lookup(name)                        # by name
shore.lookup_address(local_address)       # by 32-bit address
shore.lookup_by_object_id(id, scope)      # by 64-bit object ID
shore.register_extended_v2(local, upper)  # new-style extended resource
shore.resolve_extended_v2(upper, local)   # new-style lookup
shore.resolve_full_addr(full_addr)        # searches both styles
shore.scope_summary()                     # counts per scope level
```

### ShoreKeeper — The Boundary Authority

One ShoreKeeper per card face (two per card). Responsibilities:

- Aggregate all Ward heartbeats into a single packet for HyperShore
- Validate all cross-card traffic (auth check + mask check at boundary)
- Map the four physical die row channels to four thermal zones
- Assign `object_id` values to SHORE-scope objects

**Heartbeat packet** sent to HyperShore each interval:
```
card_id, timestamp, tick_count
healthy_ponds, degraded_ponds, isolated_ponds, stalled_ponds
thermal_load, thermal_trend, peak_zone
armed_cells, bus_utilisation
local_objects, shore_objects, extended_objects  ← scope counts
escalations  ← non-empty = HyperCompanion needed
```

The cross-card bus carries only this summary — never raw cell states, PTT hidden fields, or auth tokens.

### HyperShore — The Global Registry

One HyperShore on the master card. Receives heartbeats from all ShoreKeepers. Maintains the global view:
- All cards, their health states, thermal loads
- Global object registry (EXTENDED scope objects)
- Cross-card routing table

HyperShore is managed by HyperCompanion — the planned cross-card policy authority (not yet implemented).

---

## Pond Management

### Pond types

| Type | Security | PTT mode | Migrate | Purpose |
|------|----------|----------|---------|---------|
| PROCESS | caller decides | STATIC | yes | running program |
| WORKSPACE | caller decides | INCREMENTAL | yes | document/session data |
| FILE | caller decides | STATIC | yes | file storage |
| PERIPHERAL | caller decides | STATIC | no | hardware device |
| LIBRARY | caller decides | STATIC | yes | shared read-only tiles |
| BOOT | caller decides | NONE | no | bootstrap ROM |
| COMPANION | HIDDEN | STATIC | no | OS anchor (single) |
| DEVICE | caller decides | STATIC | no | external hardware bridge |
| SHORE | HIDDEN | STATIC | yes | card registry |
| FS | caller decides | INCREMENTAL | yes | filesystem index |
| CONDITIONAL | caller decides | STATIC | yes | lifecycle contract |
| SHOREKEEPER | HIDDEN | STATIC | no | per-card boundary |
| HYPERSHORE | HIDDEN | STATIC | no | global registry |

### Scope and object_id

Every Pond has a `scope` (LOCAL/SHORE/EXTENDED) and an `object_id` (32-bit). The scope is auto-resolved from the type registry at creation — most Ponds default to SCOPE_LOCAL, FILE/LIBRARY/SHORE default to SCOPE_SHORE. The object_id is assigned by the ShoreKeeper on registration.

---

## Cast / Ripple Discovery

### Stone and ReturnWave

A Stone is a Cast in flight — a query thrown across the Pond network.

```python
stone = Stone(
    caster_id       = "process_alice",
    visibility      = VIS_ANONYMOUS,    # SILENT, ANONYMOUS, or IDENTIFIED
    query           = {"pond_type": "FILE"},
    collect_all     = False,            # stop at first match
    preferred_scope = SCOPE_LOCAL,      # search LOCAL first
)
```

A ReturnWave accumulates results as the Stone touches Ponds. Each result carries the Pond's resource record, the hop count, and the scope level it was found at.

### Scope-ordered search

Cast now searches scopes in order: LOCAL → SHORE → EXTENDED. The Stone stops at the nearest scope that has a matching result (unless `collect_all=True`). This means a local FILE Pond is always returned before a card-level one, which is always returned before a cross-card one.

```
For each scope in [LOCAL, SHORE, EXTENDED]:
    for each Pond at this scope:
        if mask check passes AND query matches:
            add to ReturnWave
            if not collect_all: return immediately
```

### Skipping Stone

A directed Cast that visits a specific list of Pond names in sequence. Each Pond does not know which other Ponds the Stone has visited — no covert channel.

```python
wave = caster.skipping_stone(
    caster_id  = "process_alice",
    pond_names = ["workspace_alice", "fs_docs", "display_main"],
)
```

### Visibility levels

```
VIS_SILENT:      stone passes through without announcing itself
                 Pond owner does not learn it was touched
                 (cannot be combined with actual contact — 
                  silence and contact are mutually exclusive)

VIS_ANONYMOUS:   stone announces it touched the Pond
                 Pond owner learns it was contacted, but not by whom

VIS_IDENTIFIED:  stone announces caster identity to Pond owner
```

---

## Migration — FREEZE_BODY

A live Pond can be moved to a different address range without data loss.

### Protocol

```
1. Shore.suspend_connections(pond_id)
   All connections enter SUSPENDED state
   Source Ponds keep firing — data goes nowhere briefly

2. Ward.freeze_body()
   Internal cells frozen (start_flag cleared)
   Bridge cells stay registered — they still accept connections
   Cell state captured to VM image

3. Allocate new region on destination stack

4. Commander loads cell map at new base_address

5. Shore.update_address(pond_id, new_base)
   ShoreEntry.local_address updated
   Bridge cells updated with new forwarding addresses

6. Shore.restore_connections(pond_id)
   Connections enter REROUTING then RESTORED
   Data flows again

Duration: ~95 array ticks (measured)
During migration: bridge cells live at old addresses but forward to new
```

### Hot migration trigger

Thermal state MIGRATE triggers hot migration:

```
Ward: sustained FREEZE thermal state → escalate to ShoreKeeper
ShoreKeeper: PTT score identifies coolest available stack
             ShoreKeeper requests COMPANION to migrate
COMPANION: issues FREEZE_BODY, reallocates, restores
Result: Pond moved to cooler stack, thermal load redistributed
```

---

## VM Images

### Format (v3)

```
HEADER:
  magic, format_version, created_at
  os_name: "Claudette", os_version: "1.1"
  cell_count, pond_count, shore_entry_count

CELL_MAP: [{address, gate_state, input_address, output_address,
            loop_mode, latch_mode, addr_latch, _config_upper,
            data, start_flag, ecc_enabled}]

POND_STATE: [{pond_id, name, type, security, scope, object_id,
              base_address, region_size, bridges, tokens}]

SHORE_STATE: {registry_entries, registry, connections,
              legacy_translations, extended_entries}
              ← both old-style proxy and new-style config_upper pairs

COMPANION_STATE: {keys, rules, anchor_id}
```

### Save and restore

```python
from vm_image import VMImage

# Save
img = VMImage.snapshot(ctrl, shore, companion)
img.save("/path/to/state.img")         # uncompressed
img.save("/path/to/state.img.gz")      # gzip compressed

# Restore
img = VMImage.load("/path/to/state.img")
img.restore(ctrl, shore, companion)
```

VM images are fully portable between cards with the same or higher architecture version. v1.0 images load correctly on v1.1 — the config register extension is backward-compatible.
