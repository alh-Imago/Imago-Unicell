"""
example_user_models.py — a tiny user model library, the fp_tiles.py way

This shows the alternate authoring route: craft tiles by hand with the
NORBuilder primitives (exactly how fp_tiles.py builds the built-in tiles), put
several make_* builders in one file, and let the walker expand the whole file
into .icm — no full compiler needed:

    python3 examples/walker/walk_tiles.py --module examples/walker/example_user_models.py

Each make_* takes an optional base_address and returns a Tile. The walker
discovers every make_* that returns a Tile and emits one .icm per model, each
with a valid record_hash so the strict loader and the composer both accept it.
"""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from fp_tiles import TileAddressAllocator, NORBuilder, Tile, TileMetadata


def make_my_and3(base_address: int = 0x20000) -> Tile:
    """3-input AND: out = a & b & c (one bit). Toy example of the pattern."""
    alloc = TileAddressAllocator(base_address)
    a, b, c = alloc.alloc(), alloc.alloc(), alloc.alloc()
    bld = NORBuilder(alloc)
    for addr in (a, b, c):
        bld.depth_map[addr] = 0
    ab  = bld.AND2(a, b)
    out = bld.AND2(ab, c)
    return Tile(
        records=bld.records, in_a=[a, b], in_b=[c], out=[out],
        preload_map=getattr(bld, "preload_map", {}),
        metadata=TileMetadata(operation="MY_AND3", precision=1,
                              pipeline_depth=max(bld.depth_of(out), 1),
                              cell_count=len(bld.records)),
    )


def make_my_xnor(base_address: int = 0x20100) -> Tile:
    """1-bit XNOR: out = NOT(a XOR b) = (a & b) | (~a & ~b)."""
    alloc = TileAddressAllocator(base_address)
    a, b = alloc.alloc(), alloc.alloc()
    bld = NORBuilder(alloc)
    for addr in (a, b):
        bld.depth_map[addr] = 0
    na, nb = bld.NOT(a), bld.NOT(b)
    both   = bld.AND2(a, b)
    neither = bld.AND2(na, nb)
    out = bld.OR2(both, neither)
    return Tile(
        records=bld.records, in_a=[a], in_b=[b], out=[out],
        preload_map=getattr(bld, "preload_map", {}),
        metadata=TileMetadata(operation="MY_XNOR", precision=1,
                              pipeline_depth=max(bld.depth_of(out), 1),
                              cell_count=len(bld.records)),
    )
