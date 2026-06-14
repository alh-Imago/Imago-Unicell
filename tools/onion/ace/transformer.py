"""
transformer.py  —  The Transformer (Execution Engine)
───────────────────────────────────────────────────────
compress / compress_files  — build and write .onion archives
decompress                 — read and extract .onion archives
set_meta                   — post-hoc metadata edit (no recompression)
verify                     — HMAC signature check
"""

import binascii
import os
import struct
import tempfile
from typing import Any, Dict, List, Optional, Tuple

from .instruction import AlgoID, InstructionSet, LayerDescriptor
from .header      import pack_header, unpack_header, pack_audit, unpack_audit
from .manifest    import pack as manifest_pack, unpack as manifest_unpack, \
                          is_manifest, extract as manifest_extract
from .meta        import (pack as meta_pack, unpack as meta_unpack,
                          build as meta_build, verify_hmac,
                          block_size as meta_block_size, is_meta)
from .algorithms  import (
    raw_compress,     raw_decompress,
    rle_compress,     rle_decompress,
    lz77_compress,    lz77_decompress,
    huffman_compress, huffman_decompress,
    aes256_compress,  aes256_decompress,
    delta_compress,   delta_decompress,
    lzma_compress,    lzma_decompress,
    lz4_compress,     lz4_decompress,
)

_COMPRESS = {
    AlgoID.RAW:     lambda d, pw: raw_compress(d),
    AlgoID.RLE:     lambda d, pw: rle_compress(d),
    AlgoID.LZ77:    lambda d, pw: lz77_compress(d),
    AlgoID.HUFFMAN: lambda d, pw: huffman_compress(d),
    AlgoID.AES256:  lambda d, pw: aes256_compress(d, pw),
    AlgoID.DELTA:   lambda d, pw: delta_compress(d),
    AlgoID.LZMA:    lambda d, pw: lzma_compress(d),
    AlgoID.LZ4:     lambda d, pw: lz4_compress(d),
}

_DECOMPRESS = {
    AlgoID.RAW:     lambda d, pw: raw_decompress(d),
    AlgoID.RLE:     lambda d, pw: rle_decompress(d),
    AlgoID.LZ77:    lambda d, pw: lz77_decompress(d),
    AlgoID.HUFFMAN: lambda d, pw: huffman_decompress(d),
    AlgoID.AES256:  lambda d, pw: aes256_decompress(d, pw),
    AlgoID.DELTA:   lambda d, pw: delta_decompress(d),
    AlgoID.LZMA:    lambda d, pw: lzma_decompress(d),
    AlgoID.LZ4:     lambda d, pw: lz4_decompress(d),
}


# ── Atomic write ──────────────────────────────────────────────────────────────

def _atomic_write(dest_path: str, data: bytes) -> None:
    dir_ = os.path.dirname(os.path.abspath(dest_path))
    os.makedirs(dir_, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=dir_, prefix=".onion_tmp_")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp, dest_path)
    except Exception:
        try: os.unlink(tmp)
        except Exception: pass
        raise


# ── Core compression pipeline ─────────────────────────────────────────────────

def _run_compress(
    data:     bytes,
    iset:     InstructionSet,
    password: str  = "",
    audit:    bool = True,
) -> Tuple[bytes, dict]:
    current = data
    recipe  = {
        "original_size": len(data),
        "entropy_score": iset.entropy_score,
        "layers":        [],
    }

    for layer in iset.layers:
        algo_name = AlgoID.name(layer.algo_id)
        pw        = password if layer.algo_id == AlgoID.AES256 else ""
        try:
            if layer.algo_id == AlgoID.DELTA:
                from .algorithms.delta import compress as _dc, MODE_STRIDE2, MODE_STRIDE4, MODE_BYTE
                stride = getattr(iset, 'delta_stride', 2)
                mode = {1: MODE_BYTE, 2: MODE_STRIDE2, 4: MODE_STRIDE4}.get(stride, MODE_STRIDE2)
                output = _dc(current, mode=mode)
            else:
                output = _COMPRESS[layer.algo_id](current, pw)
        except Exception as e:
            print(f"  [Transformer] {algo_name} FAILED ({e}) — skipping")
            layer.skipped = True
            recipe["layers"].append({"algo": algo_name, "result": "error", "reason": str(e)})
            continue

        gain = len(current) - len(output)
        if layer.algo_id not in (AlgoID.AES256, AlgoID.DELTA) and len(output) >= len(current):
            print(f"  [Transformer] {algo_name}: {len(current):,} → {len(output):,} "
                  f"(+{-gain:,} bytes) PRUNED")
            layer.skipped = True
            recipe["layers"].append({
                "algo": algo_name, "result": "pruned",
                "input": len(current), "output": len(output),
            })
            continue

        layer.compressed_size = len(output)
        layer.checksum        = binascii.crc32(output) & 0xFFFFFFFF
        current               = output
        ratio = (1 - len(current) / max(len(data), 1)) * 100
        print(f"  [Transformer] {algo_name}: {len(current)+gain:,} → {len(current):,} "
              f"(saved {gain:,} bytes, {ratio:.1f}% of original)")
        recipe["layers"].append({
            "algo": algo_name, "result": "applied",
            "input": len(current)+gain, "output": len(current), "gain": gain,
        })

    active = [l for l in iset.layers if not l.skipped]
    if not active:
        print("  [Transformer] All layers pruned — writing raw pass-through")
        from .instruction import LayerDescriptor as LD
        raw = LD(algo_id=AlgoID.RAW,
                 compressed_size=len(data),
                 checksum=binascii.crc32(data) & 0xFFFFFFFF)
        iset.layers = [raw]
        current     = data

    return current, recipe


def _assemble(
    iset:        InstructionSet,
    payload:     bytes,
    recipe:      dict,
    audit:       bool,
    meta_pairs:  Optional[Dict[str, Any]],
    sign_key:    Optional[str],
) -> bytes:
    """Build the complete archive bytes from parts."""
    header      = pack_header(iset, include_audit=audit)
    audit_block = pack_audit(recipe) if audit else b""
    core        = header + payload + audit_block

    if meta_pairs is not None:
        meta_dict  = meta_build(meta_pairs, core, sign_key)
        meta_block = meta_pack(meta_dict)
        return core + meta_block

    return core


# ── Public: single-stream compress ───────────────────────────────────────────

def compress(
    data:       bytes,
    iset:       InstructionSet,
    dest_path:  str,
    password:   str                     = "",
    audit:      bool                    = True,
    meta_pairs: Optional[Dict[str,Any]] = None,
    sign_key:   Optional[str]           = None,
) -> None:
    print(f"\n  [Transformer] Starting — {len(data):,} bytes")
    payload, recipe = _run_compress(data, iset, password, audit)
    archive = _assemble(iset, payload, recipe, audit, meta_pairs, sign_key)
    _atomic_write(dest_path, archive)
    ratio = (1 - len(payload) / max(len(data), 1)) * 100
    print(f"\n  [Transformer] Archive written → {dest_path}")
    print(f"  [Transformer] {len(data):,} → {len(archive):,} bytes  ({ratio:.1f}% reduction)")


# ── Public: multi-file compress ───────────────────────────────────────────────

def compress_files(
    files:      List[Tuple[str, bytes]],
    iset:       InstructionSet,
    dest_path:  str,
    password:   str                     = "",
    audit:      bool                    = True,
    meta_pairs: Optional[Dict[str,Any]] = None,
    sign_key:   Optional[str]           = None,
) -> None:
    bundle    = manifest_pack(files)
    total_raw = sum(len(d) for _, d in files)
    print(f"\n  [Transformer] Bundling {len(files)} file(s) — "
          f"{total_raw:,} bytes raw, {len(bundle):,} bytes manifest")

    iset.original_size = len(bundle)
    iset.original_crc  = binascii.crc32(bundle) & 0xFFFFFFFF

    print(f"  [Transformer] Starting compression — {len(bundle):,} bytes")
    payload, recipe = _run_compress(bundle, iset, password, audit)

    recipe["file_count"] = len(files)
    recipe["files"]      = [p for p, _ in files]

    archive = _assemble(iset, payload, recipe, audit, meta_pairs, sign_key)
    _atomic_write(dest_path, archive)

    ratio = (1 - len(payload) / max(total_raw, 1)) * 100
    print(f"\n  [Transformer] Archive written → {dest_path}")
    print(f"  [Transformer] {total_raw:,} bytes ({len(files)} files) → "
          f"{len(archive):,} bytes  ({ratio:.1f}% reduction)")
    if meta_pairs is not None:
        print(f"  [Transformer] Metadata block written ({len(meta_pairs)} key(s))")


# ── Public: decompress ────────────────────────────────────────────────────────

def decompress(
    src_path:  str,
    dest_path: str,
    password:  str = "",
) -> List[str]:
    with open(src_path, "rb") as f:
        archive = f.read()

    iset, payload_offset, has_audit = unpack_header(archive)
    total_payload = iset.layers[-1].compressed_size if iset.layers else 0
    payload       = archive[payload_offset: payload_offset + total_payload]

    print(f"\n  [Transformer] Decompressing {src_path}")
    print(f"  [Transformer] Layers: {iset.summary()}")

    if iset.layers:
        last = iset.layers[-1]
        actual_crc = binascii.crc32(payload) & 0xFFFFFFFF
        if actual_crc != last.checksum:
            raise ValueError("Payload checksum mismatch — archive may be corrupted")

    current = payload
    for layer in reversed(iset.layers):
        algo_name = AlgoID.name(layer.algo_id)
        pw        = password if layer.algo_id == AlgoID.AES256 else ""
        size_in   = len(current)
        try:
            current = _DECOMPRESS[layer.algo_id](current, pw)
        except ValueError as e:
            raise ValueError(f"Layer {algo_name} decompression failed: {e}")
        print(f"  [Transformer] {algo_name}: {size_in:,} → {len(current):,} bytes")

    actual_crc = binascii.crc32(current) & 0xFFFFFFFF
    if actual_crc != iset.original_crc:
        raise ValueError("Final CRC32 mismatch — decompressed data is corrupted")
    if len(current) != iset.original_size:
        raise ValueError(
            f"Size mismatch: expected {iset.original_size}, got {len(current)}")

    written = []
    if is_manifest(current):
        files = manifest_unpack(current)
        print(f"  [Transformer] Manifest: {len(files)} file(s) → {dest_path}/")
        os.makedirs(dest_path, exist_ok=True)
        written = manifest_extract(files, dest_path)
        for path in written:
            print(f"  [Transformer]   {os.path.relpath(path, dest_path)}")
    else:
        _atomic_write(dest_path, current)
        written = [dest_path]
        print(f"  [Transformer] Restored → {dest_path}  ({len(current):,} bytes)")

    # Trailing blocks
    trail_offset = payload_offset + total_payload
    if has_audit:
        from .header import unpack_audit, AUDIT_MAGIC
        audit_magic_size = 4
        audit_len_size   = 2
        if trail_offset + audit_magic_size + audit_len_size <= len(archive):
            aj_len = struct.unpack_from(">H", archive,
                                        trail_offset + audit_magic_size)[0]
            trail_offset += audit_magic_size + audit_len_size + aj_len

    if is_meta(archive, trail_offset):
        meta = meta_unpack(archive, trail_offset)
        if meta:
            import json
            print(f"\n  [Metadata]")
            for k, v in meta.items():
                if k == 'hmac_sha256':
                    print(f"    hmac_sha256 : {v[:16]}...  (use onion --verify to check)")
                else:
                    print(f"    {k:<16}: {v}")

    return written


# ── Public: post-hoc metadata edit ───────────────────────────────────────────

def set_meta(
    src_path:   str,
    new_pairs:  Dict[str, Any],
    sign_key:   Optional[str] = None,
    merge:      bool          = True,
) -> None:
    """
    Update the META block of an existing archive without recompressing.
    If merge=True, new_pairs are merged into existing metadata.
    If merge=False, new_pairs replace the metadata entirely.
    Writes atomically.
    """
    with open(src_path, "rb") as f:
        archive = f.read()

    # Find where trailing blocks start
    iset, payload_offset, has_audit = unpack_header(archive)
    total_payload  = iset.layers[-1].compressed_size if iset.layers else 0
    trail_offset   = payload_offset + total_payload

    # Skip past audit block if present
    if has_audit:
        from .header import AUDIT_MAGIC
        if archive[trail_offset:trail_offset+4] == AUDIT_MAGIC:
            aj_len = struct.unpack_from(">H", archive, trail_offset + 4)[0]
            trail_offset += 4 + 2 + aj_len

    # The "core" = everything before the META block
    if is_meta(archive, trail_offset):
        core = archive[:trail_offset]   # strip existing META
    else:
        core = archive                  # no existing META

    # Merge or replace
    existing: Dict[str, Any] = {}
    if merge and is_meta(archive, trail_offset):
        existing = meta_unpack(archive, trail_offset) or {}

    merged = {**existing, **new_pairs}
    meta_dict  = meta_build(merged, core, sign_key)
    meta_block = meta_pack(meta_dict)

    _atomic_write(src_path, core + meta_block)
    print(f"  [Meta] Updated metadata in {src_path}  ({len(meta_dict)} key(s))")


# ── Public: HMAC verify ───────────────────────────────────────────────────────

def verify(src_path: str, sign_key: str) -> bool:
    """
    Verify the HMAC-SHA256 signature of an archive.
    Returns True if valid, False if invalid, raises ValueError if no HMAC present.
    """
    with open(src_path, "rb") as f:
        archive = f.read()

    iset, payload_offset, has_audit = unpack_header(archive)
    total_payload = iset.layers[-1].compressed_size if iset.layers else 0
    trail_offset  = payload_offset + total_payload

    if has_audit:
        from .header import AUDIT_MAGIC
        if archive[trail_offset:trail_offset+4] == AUDIT_MAGIC:
            aj_len = struct.unpack_from(">H", archive, trail_offset + 4)[0]
            trail_offset += 4 + 2 + aj_len

    if not is_meta(archive, trail_offset):
        raise ValueError("Archive has no META block.")

    meta = meta_unpack(archive, trail_offset)
    if not meta:
        raise ValueError("Could not read META block.")

    # The bytes the HMAC was computed over = everything before META block
    core = archive[:trail_offset]
    return verify_hmac(meta, core, sign_key)
