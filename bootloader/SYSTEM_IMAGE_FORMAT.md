# Imago System Image Format (.isi)

A full-system snapshot of a configured Imago array.
For static deployments (ECUs, controllers, embedded) this is the entire
firmware artefact — boot is a memory copy followed by an arm signal.

## Philosophy

The bus address space IS the program. Every cell knows its input address,
its output address, and its gate state. A saved image captures all of
that. Restoring it to any compatible array (same or larger cell count,
same or wider bus) produces an identical running system.

No recompilation. No relinking. One copy, one arm, running.

## File Structure

```
[HEADER]
[ADDRESS MAP]  — reserved regions, pond boundaries, PTT layout
[CELL TABLE]   — flat list of cell records (the actual program)
[CHECKSUM]
```

---

## Header (fixed 64 bytes)

```
offset  len  field
  0      4   magic        "IMAG" (0x494D4147)
  4      2   version      format version, currently 0x0001
  6      2   flags        see below
  8      4   cell_count   number of cell records in CELL TABLE
 12      4   region_count number of entries in ADDRESS MAP
 16      4   bus_width    address space width in bits (32)
 20      4   array_min    minimum cell count required to restore
 24      8   created_at   unix timestamp (uint64)
 32     16   system_id    uuid of the source system (or zeros)
 48      8   entry_point  first PTT address to arm after load (or 0)
 56      4   ptt_base     base address of PTT region
 60      4   reserved     zero
```

**Flags:**
```
bit 0   static     1 = no Companion, no Shore, no dynamic pond creation
bit 1   compressed 1 = cell table is zlib compressed
bit 2   signed     1 = image has signature block appended
bit 3   partial    1 = this is a pond image, not a full system image
bits 4-15  reserved, zero
```

---

## Address Map

One entry per named region, `region_count` entries, each 32 bytes:

```
offset  len  field
  0     16   name         UTF-8, null-padded (e.g. "shore", "ptt", "pond_0")
 16      4   base         first address in region
 20      4   length       address count
 24      4   flags        region flags (see below)
 28      4   reserved     zero
```

**Region flags:**
```
bit 0   ptt        this region is PTT space (bus-readable by all)
bit 1   sentinel   this region holds Sentinel counter/compare cells
bit 2   shore      this region is the Shore pond
bit 3   readonly   do not write to this region at runtime
bit 4   companion  this region is the Companion's working space
```

---

## Cell Table

Flat binary array, one record per cell, `cell_count` records.
Each record is 16 bytes:

```
offset  len  field
  0      4   gate_state      cmd_latch word (32-bit)
  4      4   input_address   bus address this cell listens on
  8      4   output_address  bus address this cell emits to
 12      4   initial_value   a_data preload (0xFFFFFFFF, 0, or 0 if unused)
```

Records are ordered by input_address ascending. This is the restore
order — loading in address order ensures no cell fires before its
upstream neighbours are configured.

**gate_state encoding** (per gate_states.py, plus new bits):
```
bits  9-0   topology        NOR gate wiring (one-hot, 10 values)
bit   10    edge_mode       0=two-arrival, 1=edge triggered
bits 21-11  auth_mask       zeroed in image (hardware-only)
bit   22    start_flag      1=armed (set this to arm on restore)
bits 24-23  dtype           output type (NUMERIC/SIGNED/ALPHA/DATETIME)
bits 26-25  cell_type       standard/latch/posedge/negedge
bit   27    priority        schedule first each tick
bit   28    trace           log to Ward trace buffer
bit   29    breakpoint      halt on fire
bit   30    one_shot        fire once then disarm
bit   31    loop_back       feed output back as next a_data
```

*Two new bits (pending Verilog update):*
```
NEW: bit A   a_preload_en   1 = load a_latch from a_preload_val on arm
NEW: bit B   a_preload_val  0 = load 0x00000000, 1 = load 0xFFFFFFFF
```
These replace the entire preloaded-A software sequence.
When set, the cell self-loads a_data at configure time.
No separate preload pass needed.

*Two new shift bits (pending Verilog update):*
```
NEW: bit C   shift_in_en    1 = incoming data shifted before gate tree
NEW: bit D   shift_out_en   1 = output shifted before bus emission
     (shift amount encoded in nibble gating bits)
```

---

## Restore Sequence (static image)

1. Validate header magic and version
2. Check `array_min` <= available cell count
3. Load ADDRESS MAP — reserve regions in allocator
4. Load CELL TABLE — write each record to array in order
5. If `entry_point` != 0 — send arm pulse to that address
6. Done. System is running.

For static targets (flag `static=1`), steps 1-5 are the entire boot.
No OS, no Companion, no pond creation. Total boot time is bounded by
the DMA copy speed of the cell table.

---

## Pond Image (flag `partial=1`)

Same format, but CELL TABLE contains only one pond's cells.
ADDRESS MAP contains only that pond's regions.
The Shore and PTT entries reference absolute addresses on the target
system — the loader must remap these if the target system's Shore/PTT
base differs.

Pond images are the unit of migration — copy a pond from one system
to another of the same or larger bus width.

---

## Checksum

Final 8 bytes of file:
```
offset  len  field
  0      4   crc32       CRC32 of everything before this block
  4      4   magic_end   "GAMI" (0x47414D49) — inverse of header magic
```

---

## File Extension

`.isi` — Imago System Image

Static embedded targets typically ship as `.isi` files.
Pond images use `.ipi` — Imago Pond Image.
ICM files (`.icm`) remain for single compiled functions — the unit
of compilation, not deployment.

---

## Size Estimate

For an iCEBreaker (iCE40UP5K, ~1000 usable cell equivalents):
- Header: 64 bytes
- Address map: ~10 regions × 32 bytes = 320 bytes
- Cell table: 1000 cells × 16 bytes = 16 KB
- Total: ~16.5 KB

For a Kintex-7 (target ~150,000 cells):
- Cell table: 150,000 × 16 bytes = 2.4 MB
- Total: ~2.4 MB

Both fit in the flash of any modern embedded target.
