"""
uniflex_fs.py — UniFlex Filesystem Compatibility Layer

Implements Sections 4–6 of the Pond, UniFlex & Discovery Specification v0.1.

UniFlex presents a unified interface to the rest of the system regardless of
the underlying storage format. FAT32, NTFS, ext4, APFS, and exFAT all appear
identically to UniFlex consumers: as token-addressed resources in a Storage Pond.

Architecture:
  FsDecoderStub  — tile metadata stub for each supported filesystem.
                   In hardware: NOR-network spatial programs.
                   In simulator: delegate to Python pathlib.
  StoragePond    — Pond(STORAGE) backed by a mounted volume.
                   Files registered as PointerTokens at mount time.
  UniFlex        — top-level manager. Detects FS type, creates StoragePonds,
                   manages the shared decoder tile registry.

Section 5.3 — shared library: multiple StoragePonds of the same FS type
reference the same decoder stub. No per-mount copy.

Section 6.4 — cross-compatibility: all BASE-tier FS decoders are available
from boot. Imago can mount any standard filesystem without special tooling.
"""

from __future__ import annotations
import imago_log

import os
import hashlib
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

from unicell_array import UniCellArray
from pond import (Pond, PondManager, PondBridge,
                  OPEN, PRIVATE, HIDDEN, STORAGE,
                  PointerToken, TokenSpace,
                  RT_FILE, RT_HANDLER)


# ── Filesystem type constants ─────────────────────────────────────────────────

FS_FAT32  = "FAT32"
FS_NTFS   = "NTFS"
FS_EXT4   = "ext4"
FS_APFS   = "APFS"
FS_EXFAT  = "exFAT"
FS_NATIVE = "NATIVE"   # simulator: delegate to host OS

FS_TYPES  = (FS_FAT32, FS_NTFS, FS_EXT4, FS_APFS, FS_EXFAT, FS_NATIVE)


# ── FS Decoder Tile stubs (Section 5.2) ──────────────────────────────────────

@dataclass
class FsDecoderStub:
    """
    Metadata stub for a filesystem decoder tile.

    In hardware: a pre-compiled NOR network — raw sector data in,
    parsed directory entries and file streams out.

    In the simulator: Python pathlib handles the actual parsing.
    Tile metadata (pipeline_depth, cell_count) is estimated from
    NOR synthesis of a typical FS parser for that format.

    license_tier: all BASE-tier FS decoders available from ROM (Section 6.2).
    """
    name:           str
    fs_type:        str
    pipeline_depth: int    # cycles from sector input to parsed output
    cell_count:     int    # estimated NOR-network cells
    license_tier:   str = "BASE"
    notes:          str = ""

    def describe(self) -> str:
        return (f"{self.name} ({self.fs_type}) "
                f"depth={self.pipeline_depth} cells={self.cell_count} "
                f"tier={self.license_tier}")


# Shared singleton registry — Section 5.3: all mounts of the same FS type
# reference the same stub, not a per-mount copy.
FS_DECODER_REGISTRY: dict[str, FsDecoderStub] = {
    FS_FAT32:  FsDecoderStub("FAT32_DECODER",  FS_FAT32,  120,    8_400,
        notes="Primary boot FS. Reads directories, files, boot records. Required in ROM."),
    FS_NTFS:   FsDecoderStub("NTFS_DECODER",   FS_NTFS,   180,   14_200,
        notes="Windows volumes. MFT, file extents, directory trees."),
    FS_EXT4:   FsDecoderStub("EXT4_DECODER",   FS_EXT4,   160,   12_600,
        notes="Linux volumes. Inodes, extent trees, directory entries."),
    FS_APFS:   FsDecoderStub("APFS_DECODER",   FS_APFS,   220,   18_800,  license_tier="INTEGER",
        notes="macOS volumes. B-trees, snapshots, clones."),
    FS_EXFAT:  FsDecoderStub("EXFAT_DECODER",  FS_EXFAT,  100,    7_200,
        notes="Large removable media. Allocation bitmap, directory tree."),
    FS_NATIVE: FsDecoderStub("NATIVE_DECODER", FS_NATIVE,   0,        0,
        notes="Simulator stub: delegates FS parsing to host OS."),
}


# ── FileEntry ─────────────────────────────────────────────────────────────────

@dataclass
class FileEntry:
    """One file or directory registered in a StoragePond."""
    token:    PointerToken
    path:     str       # relative to mount root
    size:     int       # bytes (0 for directories)
    is_dir:   bool
    modified: float     # Unix timestamp


# ── StoragePond ───────────────────────────────────────────────────────────────

class StoragePond(Pond):
    """
    A typed STORAGE Pond backed by a mounted filesystem volume.

    Extends Pond with:
      - Mount path and filesystem type
      - File token registry (relative path → FileEntry)
      - Shared FS decoder stub (Section 5.3)
      - File I/O via token: read_file, write_file
      - Directory listing
      - Type-specific resource_record fields

    All file access passes through the INBOUND bridge — identity is
    checked before any operation.
    """

    def __init__(self,
                 name: str,
                 array: UniCellArray,
                 owner_id: str,
                 mount_path: str,
                 fs_type: str = FS_NATIVE,
                 security_level: str = OPEN,
                 bridge_count: int = 2,
                 token_reservation: int = 65536):

        super().__init__(
            name               = name,
            array              = array,
            owner_id           = owner_id,
            security_level     = security_level,
            pond_type          = STORAGE,
            bridge_count       = bridge_count,
            token_reservation  = token_reservation,
            # STORAGE defaults: 4 inbound (reads), 2 outbound (writes)
            # These match the STORAGE_HANDLER tile metadata and the
            # type default table in Bridge Interface Contract Spec §3.3.
            inbound_lanes      = 4,
            outbound_lanes     = 2,
        )
        self.mount_path = str(mount_path)
        self.fs_type    = fs_type
        # Shared decoder stub — not a per-instance copy (Section 5.3)
        self.decoder    = FS_DECODER_REGISTRY.get(
            fs_type, FS_DECODER_REGISTRY[FS_NATIVE])

        self._file_registry: dict[str, FileEntry] = {}
        self._scan_volume()

        imago_log.info(f"[UNIFLEX] Mounted '{self.mount_path}' "
              f"fs={self.fs_type} "
              f"→ StoragePond '{name}' "
              f"({len(self._file_registry)} entries)")

    # ── Volume scan ───────────────────────────────────────────────────────────

    def _scan_volume(self):
        """
        Walk the mount path and register every file/directory as a token.

        In hardware: the FS decoder tile does this spatially on mount.
        In simulator: Python pathlib. physical_ref is a hash of the path
        (stable across renames if we treat path as canonical for now).
        """
        root = Path(self.mount_path)
        if not root.exists():
            return
        for item in root.rglob("*"):
            try:
                self._register_path(item, root)
            except (PermissionError, OSError):
                pass

    def _register_path(self, item: Path, root: Path) -> FileEntry:
        rel  = str(item.relative_to(root))
        stat = item.stat()
        phys = int(hashlib.md5(rel.encode()).hexdigest()[:8], 16) & 0xFFFFFFFF
        tok  = self.tokens.register(RT_FILE, phys, label=rel)
        entry = FileEntry(
            token    = tok,
            path     = rel,
            size     = stat.st_size if item.is_file() else 0,
            is_dir   = item.is_dir(),
            modified = stat.st_mtime,
        )
        self._file_registry[rel] = entry
        return entry

    # ── Directory listing ─────────────────────────────────────────────────────

    def list_directory(self, identity_id: str,
                       path: str = "") -> tuple[list[FileEntry], str]:
        """
        List direct children of `path` within the mount.
        Returns (entries, reason). Empty list on denial or missing path.
        """
        admitted, reason = self._get_bridge(
            PondBridge.INBOUND).check_access(identity_id)
        if not admitted:
            return [], reason

        prefix = (path.rstrip("/") + "/") if path else ""
        results = []
        for rel, entry in self._file_registry.items():
            if prefix:
                if not rel.startswith(prefix):
                    continue
                remainder = rel[len(prefix):]
                if "/" in remainder:
                    continue   # skip deeper entries
            else:
                if "/" in rel:
                    continue   # skip subdirectory entries
            results.append(entry)
        return results, "OK"

    # ── File I/O ──────────────────────────────────────────────────────────────

    def resolve_path(self, path: str) -> Optional[FileEntry]:
        """Look up a FileEntry by path. No access check — internal use."""
        return self._file_registry.get(path)

    def read_file(self, identity_id: str,
                  token_id: int) -> tuple[Optional[bytes], str]:
        """
        Read a file by token_id. Returns (data, reason).
        data is None on failure.
        """
        admitted, reason = self._get_bridge(
            PondBridge.INBOUND).check_access(identity_id)
        if not admitted:
            return None, reason

        tok = self.tokens.resolve(token_id)
        if tok is None:
            return None, "TOKEN_NOT_FOUND"
        if not tok.is_valid():
            return None, "TOKEN_CORRUPT"

        full = Path(self.mount_path) / tok.label
        if not full.exists() or full.is_dir():
            return None, "NOT_A_FILE"
        try:
            return full.read_bytes(), "OK"
        except OSError as e:
            return None, f"IO_ERROR:{e}"

    def write_file(self, identity_id: str,
                   path: str, data: bytes) -> tuple[Optional[int], str]:
        """
        Write bytes to `path` within the mount. Creates file if absent.
        Returns (token_id, reason). token_id is None on failure.
        """
        admitted, reason = self._get_bridge(
            PondBridge.INBOUND).check_access(identity_id)
        if not admitted:
            return None, reason

        full = Path(self.mount_path) / path
        try:
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_bytes(data)
        except OSError as e:
            return None, f"IO_ERROR:{e}"

        if path in self._file_registry:
            tok = self._file_registry[path].token
            # Update size
            self._file_registry[path].size = len(data)
        else:
            phys = int(hashlib.md5(path.encode()).hexdigest()[:8], 16) & 0xFFFFFFFF
            tok  = self.tokens.register(RT_FILE, phys, label=path)
            self._file_registry[path] = FileEntry(
                token    = tok,
                path     = path,
                size     = len(data),
                is_dir   = False,
                modified = full.stat().st_mtime,
            )
        return tok.token_id, "OK"

    def delete_file(self, identity_id: str,
                    token_id: int) -> tuple[bool, str]:
        """Delete a file by token_id. Returns (success, reason)."""
        admitted, reason = self._get_bridge(
            PondBridge.INBOUND).check_access(identity_id)
        if not admitted:
            return False, reason

        tok = self.tokens.resolve(token_id)
        if tok is None:
            return False, "TOKEN_NOT_FOUND"

        full = Path(self.mount_path) / tok.label
        try:
            full.unlink(missing_ok=True)
        except OSError as e:
            return False, f"IO_ERROR:{e}"

        self._file_registry.pop(tok.label, None)
        self.tokens.deregister(token_id)
        return True, "OK"

    # ── Type-specific resource record ─────────────────────────────────────────

    def resource_record(self) -> dict:
        rec = super().resource_record()
        rec.update({
            "mount_path":    self.mount_path,
            "fs_type":       self.fs_type,
            "decoder":       self.decoder.name,
            "decoder_depth": self.decoder.pipeline_depth,
            "decoder_cells": self.decoder.cell_count,
            "file_count":    sum(1 for e in self._file_registry.values()
                                 if not e.is_dir),
            "dir_count":     sum(1 for e in self._file_registry.values()
                                 if e.is_dir),
        })
        return rec


# ── UniFlex top-level manager ─────────────────────────────────────────────────

class UniFlex:
    """
    Top-level UniFlex filesystem manager.

    Mounts filesystem volumes as StoragePonds. Manages the shared FS
    decoder tile registry. Multiple mounts of the same FS type share
    the same decoder stub (Section 5.3).

    In the simulator: fs_type defaults to NATIVE (host OS delegation).
    In hardware: fs_type detected from the volume's boot sector signature.
    """

    def __init__(self, array: UniCellArray, owner_id: str,
                 pond_manager: Optional[PondManager] = None):
        self._array   = array
        self._owner   = owner_id
        self._manager = pond_manager or PondManager(array)
        self._mounts: dict[str, StoragePond] = {}  # mount_path → StoragePond

    # ── Mount / unmount ───────────────────────────────────────────────────────

    def mount(self,
              mount_path: str,
              name: Optional[str] = None,
              fs_type: str        = FS_NATIVE,
              security_level: str = OPEN,
              bridge_count: int   = 2,
              token_reservation: int = 65536) -> StoragePond:
        """
        Mount a filesystem volume as a StoragePond.

        mount_path:  directory root (simulator) or device path
        name:        Pond name; defaults to basename of mount_path
        fs_type:     FS_FAT32 / FS_NTFS / FS_EXT4 / FS_NATIVE / etc.
        """
        if mount_path in self._mounts:
            raise ValueError(f"'{mount_path}' is already mounted")
        if fs_type not in FS_TYPES:
            raise ValueError(
                f"Unknown fs_type '{fs_type}'. Must be one of {FS_TYPES}.")

        pond_name = name or Path(mount_path).name or "volume"

        pond = StoragePond(
            name               = pond_name,
            array              = self._array,
            owner_id           = self._owner,
            mount_path         = mount_path,
            fs_type            = fs_type,
            security_level     = security_level,
            bridge_count       = bridge_count,
            token_reservation  = token_reservation,
        )
        self._mounts[mount_path]             = pond
        self._manager._ponds[pond.pond_id]   = pond
        self._manager._name_index[pond_name] = pond.pond_id
        return pond

    def unmount(self, mount_path: str) -> bool:
        """Unmount a volume. Returns True if found and removed."""
        pond = self._mounts.pop(mount_path, None)
        if pond is None:
            return False
        self._manager._ponds.pop(pond.pond_id, None)
        self._manager._name_index.pop(pond.name, None)
        imago_log.info(f"[UNIFLEX] Unmounted '{mount_path}'")
        return True

    # ── Inspection ────────────────────────────────────────────────────────────

    def get_mount(self, mount_path: str) -> Optional[StoragePond]:
        return self._mounts.get(mount_path)

    def list_mounts(self) -> list[dict]:
        return [p.resource_record() for p in self._mounts.values()]

    def available_decoders(self) -> list[dict]:
        """Return metadata for all registered FS decoder stubs."""
        return [
            {
                "name":           s.name,
                "fs_type":        s.fs_type,
                "pipeline_depth": s.pipeline_depth,
                "cell_count":     s.cell_count,
                "license_tier":   s.license_tier,
                "notes":          s.notes,
            }
            for s in FS_DECODER_REGISTRY.values()
        ]

    @property
    def pond_manager(self) -> PondManager:
        return self._manager
