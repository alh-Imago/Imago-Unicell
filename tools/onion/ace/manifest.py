"""
manifest.py — Multi-file / directory bundler
─────────────────────────────────────────────
Packs a collection of (relative_path, data) pairs into a single byte stream
that can be fed to the Transformer as if it were one file.
Unpacks the same stream back into files, reconstructing the directory tree.

Manifest binary layout (all integers big-endian):
  [4]  Magic       b'MFST'
  [4]  File count  uint32
  per file:
    [2]  Path length  uint16
    [N]  Path         UTF-8 relative path (forward slashes, no leading /)
    [4]  Data length  uint32
    [N]  File data    raw bytes
"""

import os
import struct
from typing import List, Optional, Tuple

MAGIC      = b'MFST'
MAGIC_SIZE = 4


# ── Pack / Unpack ─────────────────────────────────────────────────────────────

def pack(files: List[Tuple[str, bytes]]) -> bytes:
    out = bytearray()
    out += MAGIC
    out += struct.pack(">I", len(files))
    for rel_path, data in files:
        norm       = rel_path.replace(os.sep, "/").lstrip("/")
        path_bytes = norm.encode("utf-8")
        out += struct.pack(">H", len(path_bytes))
        out += path_bytes
        out += struct.pack(">I", len(data))
        out += data
    return bytes(out)


def unpack(data: bytes) -> List[Tuple[str, bytes]]:
    if len(data) < MAGIC_SIZE + 4:
        raise ValueError("Manifest too short")
    if data[:MAGIC_SIZE] != MAGIC:
        raise ValueError(f"Not a manifest stream (bad magic: {data[:MAGIC_SIZE]!r})")
    i          = MAGIC_SIZE
    file_count = struct.unpack_from(">I", data, i)[0]; i += 4
    files: List[Tuple[str, bytes]] = []
    for _ in range(file_count):
        path_len  = struct.unpack_from(">H", data, i)[0]; i += 2
        rel_path  = data[i:i + path_len].decode("utf-8");  i += path_len
        data_len  = struct.unpack_from(">I", data, i)[0];  i += 4
        file_data = data[i:i + data_len];                  i += data_len
        files.append((rel_path, file_data))
    return files


def is_manifest(data: bytes) -> bool:
    return data[:MAGIC_SIZE] == MAGIC


# ── Collect files from disk ───────────────────────────────────────────────────

def collect(
    paths:   List[str],
    matcher: Optional[object] = None,   # IgnoreMatcher | None
) -> Tuple[List[Tuple[str, bytes]], str]:
    """
    Collect (relative_path, data) pairs from a list of file/directory paths.
    If *matcher* is supplied, paths matching it are skipped.
    Returns (files, label) where label suggests an archive filename.
    """
    entries: List[Tuple[str, bytes]] = []

    def _ignored(rel: str) -> bool:
        return matcher is not None and matcher.should_ignore(rel)

    def _read(full: str, rel: str):
        if _ignored(rel):
            return
        with open(full, "rb") as f:
            entries.append((rel, f.read()))

    def _walk(base: str, rel_prefix: str = ""):
        for root, dirs, files in os.walk(base):
            dirs.sort()
            rel_root = os.path.relpath(root, base)
            if rel_root == ".":
                rel_root = ""

            # Filter out ignored directories in-place so os.walk skips them
            dirs[:] = [
                d for d in dirs
                if not _ignored(
                    (rel_prefix + "/" + rel_root + "/" + d).lstrip("/") + "/"
                )
            ]

            for fn in sorted(files):
                rel = os.path.join(rel_root, fn) if rel_root else fn
                if rel_prefix:
                    rel = rel_prefix + "/" + rel
                rel = rel.replace(os.sep, "/")
                full = os.path.join(root, fn)
                _read(full, rel)

    if len(paths) == 1 and os.path.isdir(paths[0]):
        base  = os.path.abspath(paths[0])
        label = os.path.basename(base.rstrip(os.sep))
        _walk(base)
        return entries, label

    if len(paths) == 1 and os.path.isfile(paths[0]):
        full  = os.path.abspath(paths[0])
        label = os.path.basename(full)
        rel   = os.path.basename(full)
        if not _ignored(rel):
            with open(full, "rb") as f:
                entries.append((rel, f.read()))
        return entries, label

    # Multiple paths
    label = "archive"
    for path in paths:
        path = os.path.abspath(path)
        if os.path.isfile(path):
            rel = os.path.basename(path)
            if not _ignored(rel):
                with open(path, "rb") as f:
                    entries.append((rel, f.read()))
        elif os.path.isdir(path):
            prefix = os.path.basename(path.rstrip(os.sep))
            _walk(path, rel_prefix=prefix)
        else:
            raise FileNotFoundError(f"Path not found: {path}")

    return entries, label


# ── Extract files to disk ─────────────────────────────────────────────────────

def extract(files: List[Tuple[str, bytes]], dest_dir: str) -> List[str]:
    """
    Write (relative_path, data) pairs under dest_dir.
    Rejects paths with '..' (path traversal guard).
    Returns list of written absolute paths.
    """
    written = []
    for rel_path, data in files:
        parts = rel_path.replace("\\", "/").split("/")
        if ".." in parts or any(p == "" for p in parts[:-1]):
            raise ValueError(f"Unsafe path in archive: {rel_path!r}")
        full = os.path.join(dest_dir, *parts)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb") as f:
            f.write(data)
        written.append(full)
    return written
