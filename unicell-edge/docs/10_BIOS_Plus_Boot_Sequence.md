# Imago UniCell — BIOS-Plus Specification
## Claudette v1.1

---

## Overview

The BIOS-Plus chip is the root of trust for the entire UniCell system. It is the first thing that runs at power-on and the last thing that hands control to the cell fabric. Everything that happens after it finishes is either a consequence of what it configured or a Pond running in the fabric it set up.

The BIOS-Plus chip has one job: get the system to a state where it can run. Every step of the boot sequence exists to achieve that goal in a way that is secure, honest, and verifiable.

This document specifies the complete boot sequence, the responsibilities of each step, and the VM implementation that models it.

---

## BIOS-Plus Responsibilities

```
1. Generate secrets          — auth token, salt key from hardware RNG
2. Dead cell survey          — scan array, build defect map
3. Allocate address space    — assign addresses around dead cells
4. Distribute auth token     — configure every live cell with the token
5. Load and verify Tier 2    — COMPANION, Shore, ShoreKeeper
6. Load and verify Tier 3    — Core Ponds (compiler, tile library, etc.)
7. Hand off                  — assert start flags, system running
```

Nothing runs before the BIOS-Plus finishes. Nothing changes the cell configuration after it hands off without the auth token it generated.

---

## Step 1 — Generate Secrets

At power-on the BIOS-Plus chip reads from its hardware random number generator. Two secrets are generated:

**Auth Token — 12 bits**
The configuration gate for every cell on the card. CMD_RECONFIGURE (command code 3) carries this token on Bus 1 bits 4–14. A cell silently rejects any CMD_RECONFIGURE that does not carry the matching token. The token never leaves the BIOS-Plus chip in plaintext — it is distributed to cells during the boot sequence and thereafter exists only in cell configuration registers, which are write-only from outside.

**Salt Key — 64 bits**
Used for HIDDEN Pond encryption and licensed tile DRM. Never distributed to cells. Stored in a tamper-evident register in the BIOS-Plus chip. Destroyed on physical tamper detection. The salt key means that a stolen card cannot have its HIDDEN Ponds read on another system, and a licensed tile cannot be moved to an unlicensed card.

Both secrets derive from the same entropy pool. They are independent — compromising one does not compromise the other.

In the VM:
```python
import secrets
auth_token = secrets.randbits(12)        # 12-bit hardware RNG
salt_key   = secrets.randbits(64)        # 64-bit hardware RNG
```

Currently the VM uses a fixed machine key `0xDEADC0DEBEEF1234`. The production implementation uses the hardware RNG path above.

---

## Step 2 — Dead Cell Survey

Before any addresses are assigned, the BIOS-Plus chip scans the entire cell array and identifies defective cells — cells that do not respond correctly to a test configuration write or that fail the ECC check on readback.

The survey produces a **defect map** — a list of cell addresses that must not be allocated to any program, OS component, or tile.

```
For each cell address in range(0, total_cells):
    Write test pattern via CMD_RECONFIGURE (requires auth token)
    Read back via CMD_PING
    If no response or ECC error:
        Mark address as defective
        Add to defect_map[]
```

The defect map is loaded into the controller before any allocation occurs. The allocator skips defective addresses silently — they are simply not available. User programs never know they exist.

In the VM:
```python
ctrl = ImagoController(cell_count=cell_count)
ctrl.load_defect_map(defective_addresses)
# All subsequent allocations skip defective addresses automatically
```

**Why this matters:** a dead cell that is allocated to a tile will cause that tile to produce wrong results. Discovering and mapping defects before allocation ensures that every allocated cell is a working cell. This is standard practice in DRAM manufacturing (row/column remapping) applied to the cell array.

---

## Step 3 — Address Space Allocation

With the defect map loaded, the BIOS-Plus chip establishes the address layout for the card. The address space is partitioned into reserved regions before any user allocation occurs:

```
Address Map — 32-bit local space (64-bit system space via slot<<32 | local)
─────────────────────────────────────────────────────────────────────────
0x00000000 – 0x000FFFFF   RESERVED — null address, BIOS internal
0x00100000 – 0x001FFFFF   BIOS Boot Image (Tier 2 Ponds)
0x00200000 – 0x002FFFFF   FUNCTION_LOAD_PATTERN protected zone
                          (addresses containing 0xA5A5A5A5 excluded)
0x00300000 – 0x004FFFFF   Available — user Pond allocation
0x00500000 – 0x005FFFFF   Shore V2 registry
0x00600000 – 0x006FFFFF   Core Pond zone (Tier 3)
  0x00600000              COMPILER_POND
  0x00610000              INT32_COMPILER_POND
  0x00620000              LLVM_COMPILER_POND
  0x00630000              SEQUENCER_POND
  0x00640000              TILE_LIBRARY_POND
  0x00650000              MODEL_LIBRARY_POND
  0x00660000              PROGRAM_BUILDER_POND
0x00700000 – 0x00AFFFFF   Available — user Pond allocation
0x00B00000 – 0x00B0FFFF   Keyboard bridge
0x00C00000 – 0x00C0FFFF   Mouse bridge
0x00D00000 – 0x00D0FFFF   Storage bridge
0x00E00000 – 0x00E0FFFF   Network bridge
0x00F00000 – 0x00F0FFFF   Console bridge
0x00F10000 – 0xFFFFFFFF   Available — expansion
─────────────────────────────────────────────────────────────────────────
```

Any defective addresses within reserved regions cause the BIOS-Plus to attempt relocation within the region. If a critical region cannot be populated due to defects, boot halts with a hardware fault code.

---

## Step 4 — Distribute Auth Token

With the address map established and defect map loaded, the BIOS-Plus distributes the auth token to every live cell on the card via CMD_RECONFIGURE.

```
For each live cell address (not in defect_map):
    Build Bus 1: cmd=CMD_RECONFIGURE, auth=auth_token, scope=LOCAL
    Build Bus 2: auth_mask_value = auth_token (the token IS the mask)
    Build Bus 3: cell_address
    Drive all three buses simultaneously
    Cell stores auth_token in its write-only auth_mask register
```

After this step:
- Every live cell has the auth token in its auth_mask register
- No cell's auth_mask is readable from outside
- Any subsequent CMD_RECONFIGURE must carry the matching token or be silently rejected
- User code running in Ponds cannot issue CMD_RECONFIGURE at all — it lacks the token

The auth token distribution is the last thing that happens before cells can be configured for computation. After this step, the BIOS-Plus is the only entity that can change cell topology.

In the VM:
```python
# CommandInterface holds the auth token and appends it to all system commands
sys_cmd = CommandInterface(controller, auth_token=auth_token)
# All subsequent cell configuration goes through sys_cmd
```

---

## Step 5 — Load Tier 2 (BIOS Boot Image)

The BIOS-Plus now loads the Tier 2 Ponds from its internal storage (flash memory on the BIOS chip itself, not the cell array). These are the minimum OS Ponds needed to bring the system to a self-hosting state.

**Load order:**
```
1. COMPANION     — boot first, permanent anchor
                   Address: BIOS internal allocation
                   Security: HIDDEN, heritage flag set
                   Cannot be destroyed without heritage flag

2. Shore V2      — card registry
                   Address: 0x00500000
                   Security: HIDDEN
                   COMPANION registered as first entry

3. ShoreKeeper   — boundary authority, heartbeat aggregation
                   Wired to Shore on boot
                   Begins heartbeat cycle

4. CommandInterface — three-bus protocol translator
                   Auth token embedded at boot
                   User CommandInterface (no auth) available for Pond use
```

For each Pond:
```
a. Load CellMapRecord list from BIOS flash
b. Run security gate check (FUNCTION_LOAD_PATTERN, address validation)
c. Allocate cell region from address map
d. Write config packets to each cell via CMD_RECONFIGURE + auth_token
e. Register with Shore
f. Assign Ward
g. Assert start flags — Pond armed
h. Verify: ping each bridge, check Ward reports HEALTHY
```

If any Tier 2 Pond fails to load or fails health check — boot halts. Tier 2 is mandatory. The system cannot operate without COMPANION and Shore.

In the VM: `run_companion.py` `boot_system()` function covers this step.

---

## Step 6 — Load Tier 3 (Core Ponds)

With Tier 2 running, the BIOS-Plus hands off to COMPANION to load the Tier 3 Core Ponds. COMPANION reads the boot manifest — a list of Core Pond specifications — and loads each one in boot order.

The boot manifest is the `_CORE_POND_MODELS` list in `model_library.py`, sorted by `boot_order` in metadata.

**Load order (from model_library.py):**
```
Order 1: COMPILER_POND         — 0x00600000  mandatory
Order 2: INT32_COMPILER_POND   — 0x00610000  mandatory
Order 3: LLVM_COMPILER_POND    — 0x00620000  optional (requires llvmlite)
Order 4: SEQUENCER_POND        — 0x00630000  mandatory
Order 5: TILE_LIBRARY_POND     — 0x00640000  mandatory
Order 6: MODEL_LIBRARY_POND    — 0x00650000  mandatory
Order 7: PROGRAM_BUILDER_POND  — 0x00660000  mandatory
```

For each Core Pond:
```
a. Read ModelSpec from MODEL_LIBRARY_POND (boot_tier=3)
b. Locate cell map on UniFlex storage (or BIOS flash for minimal boot)
c. Run security gate check
d. Allocate region at specified base_address
e. Load via CMD_RECONFIGURE + auth_token
f. Register with Shore as LIBRARY type
g. Issue COMPILE key to COMPANION for this Pond
h. Assign Ward — stall_threshold higher than normal (compiler jobs take longer)
i. Assert start flags — Core Pond armed
j. Verify: test compile job, check result
```

Optional Ponds (LLVM_COMPILER_POND) log a warning if load fails but do not halt boot.

After all mandatory Core Ponds are loaded and verified:

```
[BOOT] Tier 3 complete
[BOOT] Core Ponds armed:
[BOOT]   COMPILER_POND         @ 0x00600000  HEALTHY
[BOOT]   INT32_COMPILER_POND   @ 0x00610000  HEALTHY
[BOOT]   SEQUENCER_POND        @ 0x00630000  HEALTHY
[BOOT]   TILE_LIBRARY_POND     @ 0x00640000  HEALTHY
[BOOT]   MODEL_LIBRARY_POND    @ 0x00650000  HEALTHY
[BOOT]   PROGRAM_BUILDER_POND  @ 0x00660000  HEALTHY
[BOOT] System self-hosting
```

---

## Step 7 — Hand Off

The BIOS-Plus performs final checks and hands control to COMPANION:

```
1. Verify all mandatory Ponds report Ward state HEALTHY
2. Verify Shore registry contains all expected entries
3. Verify ShoreKeeper heartbeat is running
4. Log boot completion timestamp and cell inventory to COMPANION
5. Set BOOT_COMPLETE flag in COMPANION status register
6. BIOS-Plus enters monitoring mode:
     - Continues to manage auth token distribution for new cells (hot-add)
     - Responds to CMD_PING from ShoreKeeper
     - Does NOT participate in normal computation
     - Watches for tamper signals (physical security)
```

From this point the system is running. COMPANION handles all OS decisions. The BIOS-Plus is present but passive unless a new card is added, a hardware fault occurs, or a tamper event triggers salt key destruction.

---

## VM Implementation

### Current state

The VM currently implements a simplified version of this sequence in `run_companion.py`:

```python
arr, ctrl, shore, companion, devices, search_index = boot_system(
    cell_count=args.cells,
    load_image=args.load,
)
```

This covers Steps 4–5 in simplified form. Steps 1–3 (secrets, dead cell survey, address map) and Step 6 (Core Pond loading) are not yet implemented.

### Target boot sequence for VM

```python
def boot_full(cell_count: int = 100_000,
              defect_map: list = None,
              load_image: str = None):
    """
    Full BIOS-Plus boot sequence.
    """
    import secrets as _secrets

    print("=" * 60)
    print("  Imago UniCell — BIOS-Plus Boot")
    print("=" * 60)

    # Step 1 — Generate secrets
    auth_token = _secrets.randbits(12)
    salt_key   = _secrets.randbits(64)
    print(f"[BIOS] Auth token generated (12-bit)")
    print(f"[BIOS] Salt key generated (64-bit)")

    # Step 2 — Dead cell survey
    from unicell_array import UniCellArray
    arr = UniCellArray(cell_count)
    defects = defect_map or []
    print(f"[BIOS] Dead cell survey: {len(defects)} defective addresses")

    # Step 3 — Address space allocation
    from controller import ImagoController
    ctrl = ImagoController(cell_count=cell_count)
    ctrl.load_defect_map(defects)
    print(f"[BIOS] Address space allocated — {cell_count - len(defects)} live cells")

    # Step 4 — Distribute auth token
    from command_interface import CommandInterface
    sys_cmd = CommandInterface(ctrl, auth_token=auth_token)
    print(f"[BIOS] Auth token distributed to all live cells")

    # Step 5 — Load Tier 2
    from shore_v2 import ShoreV2
    from companion import Companion
    shore = ShoreV2("shore_0", base_address=0x00500000,
                    initial_capacity=64, controller=ctrl, array=arr)
    companion = Companion.boot(arr, shore, ctrl)
    shore.attach_companion(companion.handle_ward_flag)
    print(f"[BIOS] Tier 2 complete — COMPANION, Shore, ShoreKeeper armed")

    # Step 6 — Load Tier 3 (Core Ponds)
    core_ponds = boot_core_ponds(arr, ctrl, shore, companion, auth_token)
    print(f"[BIOS] Tier 3 complete — system self-hosting")

    # Step 7 — Hand off
    print(f"[BIOS] Boot complete — handing off to COMPANION")
    print(f"[BIOS] BOOT_COMPLETE")

    return arr, ctrl, shore, companion, core_ponds
```

### Next steps

- [ ] Add `auth_token` parameter to `ImagoController.__init__`
- [ ] Implement auth token distribution loop in controller
- [ ] Implement dead cell survey using CMD_PING
- [ ] Implement `boot_core_ponds()` function loading Tier 3 from model_library
- [ ] Add `--boot-full` flag to `run_companion.py`
- [ ] Test: full boot sequence in VM
- [ ] Test: dead cell simulation — introduce artificial defects, verify allocation skips them
- [ ] Test: Tier 3 Core Pond loading and health check
- [ ] Snapshot: save fully booted system as `core_boot.img.gz`

---

## Security Properties After Boot

Once boot completes:

| Property | Mechanism |
|---|---|
| Cell topology immutable | auth_token required for CMD_RECONFIGURE — only BIOS-Plus holds it |
| User code sandboxed | PTT-relative addressing — cannot escape Pond region |
| Hidden Ponds encrypted | salt_key in BIOS chip — unreadable without physical chip |
| Defective cells excluded | defect_map loaded before any allocation |
| Boot image verified | security gate checks every cell map before loading |
| Tamper response | salt_key destroyed on physical tamper — HIDDEN Ponds become unreadable |

---

*This document will expand as the VM boot sequence is implemented and tested.*

*Companion documents:*
- `09_Standalone_Boot_and_Self_Hosting.md` — self-hosting layer and Core Ponds
- `02_Core_Architecture.md` — command bus three-bus protocol
- `03_Security_Model.md` — auth token, salt key, mask primitive
- `04_OS_and_Runtime.md` — COMPANION, Shore, Ward
