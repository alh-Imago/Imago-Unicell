# Addressing — Current Limits and Future Silicon

## Current implementation: 32-bit addresses

The VM, compiler, FPGA bridge and all `.icm` files currently use
32-bit addresses throughout:

```
bus_addr:        32 bits  (0x00000000 – 0xFFFFFFFF)
input_address:   32 bits
output_address:  32 bits
gate_state:      32 bits
```

This gives 4 billion unique bus addresses — sufficient for current
iCEBreaker (8 cells) and Kintex-7 bring-up.

## Future silicon: 64-bit addressing

Full production silicon will use 64-bit addressing. The upper 32 bits
are already partially supported via gate_state flags:

```
GS_ADDR_LATCH (bit 23) -- extended address mode
```

When `GS_ADDR_LATCH` is set, the cell accepts a second config word
containing the upper 32 bits of the address. This is used mainly for
**bridge cells** that address across pond boundaries:

```
Lower 32 bits:  local address within the pond
Upper 32 bits:  pond/shore identifier (cross-pond addressing)
```

## Impact on programs

Programs written today using 32-bit addresses will run unchanged on
64-bit silicon. The address allocator handles the width internally.
No programmer action required.

## Bridge cells and cross-pond addressing

Bridge cells use the full 64-bit address to route packets between ponds:

```
Standard cell:  output_address  = 0x00000000_00002000  (local)
Bridge cell:    output_address  = 0x00000001_00000000  (remote pond 1)
```

The upper 32 bits identify the target pond via its Shore entry.
The lower 32 bits are the address within that pond's local address space.

## .icm format

The `.icm` format reserves fields for 64-bit addresses. Current files
use 32-bit values in those fields. When 64-bit silicon arrives, the
same `.icm` files load correctly — the reserved upper bits are zero,
which means local addressing, which is correct for existing programs.

---
*This is a forward-looking note. Current hardware: iCEBreaker (32-bit).
Full 64-bit addressing: planned for custom ASIC production silicon.*
