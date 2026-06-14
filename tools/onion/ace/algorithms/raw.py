"""raw.py — Pass-through layer (no compression)."""

def compress(data: bytes) -> bytes:
    return data

def decompress(data: bytes) -> bytes:
    return data
