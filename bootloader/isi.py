"""
bootloader/isi.py — Imago System Image (.isi) reader/writer.

Run from repo root:
    python3 bootloader/isi.py --help
"""

import struct
import zlib
import time
import uuid
import sys
import os
from dataclasses import dataclass, field
from typing import List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Constants ─────────────────────────────────────────────────────────────────

MAGIC       = b'IMAG'
MAGIC_END   = b'GAMI'
VERSION     = 0x0001

FLAG_STATIC     = 0x0001
FLAG_COMPRESSED = 0x0002
FLAG_SIGNED     = 0x0004
FLAG_PARTIAL    = 0x0008

REGION_PTT       = 0x01
REGION_SENTINEL  = 0x02
REGION_SHORE     = 0x04
REGION_READONLY  = 0x08
REGION_COMPANION = 0x10

HEADER_SIZE  = 64
REGION_SIZE  = 32
CELL_SIZE    = 16


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class CellRecord:
    gate_state:     int
    input_address:  int
    output_address: int
    initial_value:  int = 0

    def pack(self) -> bytes:
        return struct.pack('<IIII',
            self.gate_state & 0xFFFFFFFF,
            self.input_address & 0xFFFFFFFF,
            self.output_address & 0xFFFFFFFF,
            self.initial_value & 0xFFFFFFFF,
        )

    @staticmethod
    def unpack(data: bytes) -> 'CellRecord':
        gs, ia, oa, iv = struct.unpack('<IIII', data)
        return CellRecord(gs, ia, oa, iv)


@dataclass
class RegionEntry:
    name:   str
    base:   int
    length: int
    flags:  int = 0

    def pack(self) -> bytes:
        name_bytes = self.name.encode('utf-8')[:16].ljust(16, b'\x00')
        return struct.pack('<16sIII', name_bytes, self.base, self.length, self.flags) + b'\x00' * 4

    @staticmethod
    def unpack(data: bytes) -> 'RegionEntry':
        name_raw, base, length, flags = struct.unpack('<16sIII', data[:28])
        name = name_raw.rstrip(b'\x00').decode('utf-8')
        return RegionEntry(name, base, length, flags)


@dataclass
class SystemImage:
    flags:       int = FLAG_STATIC
    bus_width:   int = 32
    system_id:   bytes = field(default_factory=lambda: uuid.uuid4().bytes)
    entry_point: int = 0
    ptt_base:    int = 0x00010000
    created_at:  int = field(default_factory=lambda: int(time.time()))
    regions:     List[RegionEntry] = field(default_factory=list)
    cells:       List[CellRecord]  = field(default_factory=list)

    @property
    def is_static(self) -> bool:
        return bool(self.flags & FLAG_STATIC)

    @property
    def is_partial(self) -> bool:
        return bool(self.flags & FLAG_PARTIAL)

    @property
    def array_min(self) -> int:
        """Minimum cell count needed to restore this image."""
        if not self.cells:
            return 0
        max_addr = max(c.output_address for c in self.cells)
        return max_addr + 1


# ── Writer ────────────────────────────────────────────────────────────────────

def write_isi(image: SystemImage, path: str) -> int:
    """Write a SystemImage to a .isi file. Returns bytes written."""
    # Sort cells by input_address (restore order)
    cells = sorted(image.cells, key=lambda c: c.input_address)

    # Pack cell table
    cell_bytes = b''.join(c.pack() for c in cells)
    if image.flags & FLAG_COMPRESSED:
        cell_bytes = zlib.compress(cell_bytes, level=9)

    # Pack region table
    region_bytes = b''.join(r.pack() for r in image.regions)

    # Pack header (64 bytes total)
    header = struct.pack('<4sHHIIIIQ',
        MAGIC,
        VERSION,
        image.flags,
        len(cells),
        len(image.regions),
        image.bus_width,
        image.array_min,
        image.created_at,
    )                                          # 32 bytes so far
    sys_id = (image.system_id + b'\x00'*16)[:16]
    header += sys_id                           # +16 = 48
    header += struct.pack('<QII',
        image.entry_point,
        image.ptt_base,
        0,                                     # reserved
    )                                          # +16 = 64
    assert len(header) == HEADER_SIZE, f"Header size {len(header)} != {HEADER_SIZE}"

    body = header + region_bytes + cell_bytes

    # Checksum
    crc = zlib.crc32(body) & 0xFFFFFFFF
    footer = struct.pack('<I4s', crc, MAGIC_END)

    data = body + footer

    with open(path, 'wb') as f:
        f.write(data)

    return len(data)


# ── Reader ────────────────────────────────────────────────────────────────────

def read_isi(path: str) -> SystemImage:
    """Read a .isi file and return a SystemImage."""
    with open(path, 'rb') as f:
        data = f.read()

    # Validate footer
    footer = data[-8:]
    crc_stored, magic_end = struct.unpack('<I4s', footer)
    if magic_end != MAGIC_END:
        raise ValueError(f"Bad footer magic: {magic_end!r}")
    body = data[:-8]
    crc_actual = zlib.crc32(body) & 0xFFFFFFFF
    if crc_actual != crc_stored:
        raise ValueError(f"Checksum mismatch: stored={crc_stored:#010x} actual={crc_actual:#010x}")

    # Parse header
    hdr = data[:HEADER_SIZE]
    magic    = hdr[0:4]
    if magic != MAGIC:
        raise ValueError(f"Bad magic: {magic!r}")

    version  = struct.unpack_from('<H', hdr, 4)[0]
    flags    = struct.unpack_from('<H', hdr, 6)[0]
    n_cells  = struct.unpack_from('<I', hdr, 8)[0]
    n_regions= struct.unpack_from('<I', hdr, 12)[0]
    bus_w    = struct.unpack_from('<I', hdr, 16)[0]
    # array_min at 20 (read but not stored — derived)
    created  = struct.unpack_from('<Q', hdr, 24)[0]
    sys_id   = hdr[32:48]
    entry_pt = struct.unpack_from('<Q', hdr, 48)[0]
    ptt_base = struct.unpack_from('<I', hdr, 56)[0]

    # Parse regions
    region_offset = HEADER_SIZE
    regions = []
    for i in range(n_regions):
        r_data = data[region_offset + i*REGION_SIZE : region_offset + (i+1)*REGION_SIZE]
        regions.append(RegionEntry.unpack(r_data))

    # Parse cells
    cell_offset = region_offset + n_regions * REGION_SIZE
    cell_bytes = data[cell_offset:-8]
    if flags & FLAG_COMPRESSED:
        cell_bytes = zlib.decompress(cell_bytes)

    cells = []
    for i in range(n_cells):
        c_data = cell_bytes[i*CELL_SIZE : (i+1)*CELL_SIZE]
        cells.append(CellRecord.unpack(c_data))

    return SystemImage(
        flags=flags,
        bus_width=bus_w,
        system_id=sys_id,
        entry_point=entry_pt,
        ptt_base=ptt_base,
        created_at=created,
        regions=regions,
        cells=cells,
    )


# ── From controller records ───────────────────────────────────────────────────

def from_controller_records(records, regions=None, **kwargs) -> SystemImage:
    """
    Build a SystemImage from a list of CellMapRecord objects
    (as returned by compile_int32_function or load_map).
    """
    from controller import CellMapRecord
    cells = []
    for r in records:
        iv = r.initial_value if r.initial_value is not None else 0
        cells.append(CellRecord(
            gate_state     = r.gate_state,
            input_address  = r.input_address,
            output_address = r.output_address,
            initial_value  = iv & 0xFFFFFFFF,
        ))
    return SystemImage(
        regions = regions or [],
        cells   = cells,
        **kwargs
    )


# ── Info dump ─────────────────────────────────────────────────────────────────

def print_info(image: SystemImage, path: str = ''):
    import datetime
    print(f"Imago System Image{' — ' + path if path else ''}")
    print(f"  Version:    {VERSION:#06x}")
    print(f"  Created:    {datetime.datetime.fromtimestamp(image.created_at)}")
    print(f"  Flags:      {'STATIC ' if image.is_static else ''}{'PARTIAL ' if image.is_partial else ''}{'COMPRESSED ' if image.flags & FLAG_COMPRESSED else ''}")
    print(f"  Bus width:  {image.bus_width} bits")
    print(f"  Cells:      {len(image.cells):,}")
    print(f"  Array min:  {image.array_min:,}")
    print(f"  PTT base:   {image.ptt_base:#010x}")
    print(f"  Entry:      {image.entry_point:#010x}")
    print(f"  Regions ({len(image.regions)}):")
    for r in image.regions:
        flag_str = ' '.join([
            'PTT'       if r.flags & REGION_PTT       else '',
            'SENTINEL'  if r.flags & REGION_SENTINEL   else '',
            'SHORE'     if r.flags & REGION_SHORE      else '',
            'READONLY'  if r.flags & REGION_READONLY   else '',
            'COMPANION' if r.flags & REGION_COMPANION  else '',
        ]).strip()
        print(f"    {r.name:<20s} base={r.base:#010x} len={r.length:#010x}  [{flag_str}]")


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(description='Imago System Image tool')
    sub = p.add_subparsers(dest='cmd')

    si = sub.add_parser('info',  help='Print image info')
    si.add_argument('file')

    sv = sub.add_parser('verify', help='Verify checksum')
    sv.add_argument('file')

    args = p.parse_args()

    if args.cmd == 'info':
        img = read_isi(args.file)
        print_info(img, args.file)

    elif args.cmd == 'verify':
        try:
            img = read_isi(args.file)
            print(f"OK — {args.file} ({len(img.cells):,} cells)")
        except Exception as e:
            print(f"FAIL — {e}")
            sys.exit(1)

    else:
        p.print_help()
