"""
tree_embedding_v1.py — points.md #808: PLACING the dispatch / gather trees on the 2D grid.

THE CONSTRAINT THAT MAKES THIS A REAL PROBLEM. The routing byte does not travel on the grid's ordinary data
path: `mux_cell_v1` has a dedicated `routing_in_<dir>` per face, driven by the neighbouring cell's
`routing_out`. So a parent and its child mux node MUST BE UNIT NEIGHBOURS -- a relay in between would carry the
32-bit data but not the routing byte. A chain, by contrast, hangs off a leaf face by an ordinary data route.

WHAT THAT DOES TO CAPACITY (measured, exhaustively over every tree shape): two nodes' faces can point at the
same neighbouring cell, and a face that points at a node cell can offer nothing, so some faces are dead.
    levels   abstract (3^L)   max leaves in 2D
       1           3                  3
       2           9                  7
       3          27                 13
The 2-bit count field could address 27 feeds; the GEOMETRY caps a 2D build at 13. The format reserves the third
axis (the nano's `routing_mask`/`cardinal_edge` are 6-bit slots "for a future up/down axis", only 4 bits wired),
which is what would lift it -- not built. Beyond 13 feeds this module refuses, with that reason.

`embed_tree(n)` picks, over all 473 three-level shapes, the one with the fewest levels then the fewest nodes that
still offers >= n leaves, numbers the destinations depth-first in ascending face-code order, and returns both the
GEOMETRY (cells, faces, first cells) and the abstract `DistributionTree` the routing-byte functions consume, so
the encode/decode already verified against hardware-proven bytes runs unchanged on a placed tree.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fixed_structures_v1 import DistributionTree, TreeNode, TreeError, MAX_LEVELS  # noqa: E402

Pos = Tuple[int, int]
STEP = {"n": (-1, 0), "s": (1, 0), "e": (0, 1), "w": (0, -1)}
OPP = {"n": "s", "s": "n", "e": "w", "w": "e"}
ORDER = ("n", "s", "e", "w")


def out_faces(up: str) -> List[str]:
    """The node's three usable faces in CODE order (code 0, 1, 2). For upstream W this is N, S, E -- exactly the
    proven #271/#273 configuration (`face_for_slot0 = N, slot1 = S, slot2 = E`)."""
    return [f for f in ORDER if f != up]


def _add(p: Pos, f: str) -> Pos:
    return (p[0] + STEP[f][0], p[1] + STEP[f][1])


@dataclass
class EmbNode:
    index: int
    pos: Pos
    up: str                                   # the face toward the parent (or the splitter / controller)
    level: int
    parent: Optional[Tuple[int, int]]         # (parent index, parent's face code)
    children: Dict[str, int] = field(default_factory=dict)      # face -> child node index


@dataclass
class EmbeddedTree:
    n: int
    up: str
    nodes: List[EmbNode]
    #: destination -> (node index, face, first cell of the route leaving that face)
    pins: Dict[int, Tuple[int, str, Pos]]
    tree: DistributionTree
    #: faces that COULD be leaves but are unused (surplus beyond n, or blocked by geometry)
    spare: int

    @property
    def levels(self) -> int:
        return max((nd.level for nd in self.nodes), default=0)

    def cells(self) -> List[Pos]:
        return [nd.pos for nd in self.nodes]


def _leaf_faces(nodes: List[EmbNode], reserved: frozenset) -> List[Tuple[int, str, Pos]]:
    occupied = {nd.pos for nd in nodes} | set(reserved)
    seen = set()
    out = []
    for nd in nodes:
        for f in out_faces(nd.up):
            if f in nd.children:
                continue
            c = _add(nd.pos, f)
            if c in occupied or c in seen:
                continue
            seen.add(c)
            out.append((nd.index, f, c))
    return out


@lru_cache(maxsize=None)
def _shapes(up: str):
    """Every unit-adjacency tree shape (root at (0,0), upstream face `up`, at most MAX_LEVELS levels), as
    tuples of (pos, up, level, parent, ((face, child), ...))."""
    reserved = frozenset({_add((0, 0), up)})
    found = []

    def rec(nodes: List[EmbNode], i: int) -> None:
        if i == len(nodes):
            found.append(tuple((nd.pos, nd.up, nd.level, nd.parent, tuple(sorted(nd.children.items())))
                               for nd in nodes))
            return
        nd = nodes[i]
        faces = out_faces(nd.up)
        if nd.level >= MAX_LEVELS:
            rec(nodes, i + 1)
            return
        for mask in range(8):
            chosen = [faces[k] for k in range(3) if mask >> k & 1]
            occupied = {m.pos for m in nodes} | set(reserved)
            new: List[EmbNode] = []
            ok = True
            for f in chosen:
                p = _add(nd.pos, f)
                if p in occupied or any(x.pos == p for x in new):
                    ok = False
                    break
                new.append(EmbNode(len(nodes) + len(new), p, OPP[f], nd.level + 1, (nd.index, faces.index(f))))
            if not ok:
                continue
            for f, x in zip(chosen, new):
                nd.children[f] = x.index
            rec(nodes + new, i + 1)
            nd.children.clear()
    rec([EmbNode(0, (0, 0), up, 1, None)], 0)
    return found


def _rebuild(shape) -> List[EmbNode]:
    nodes = [EmbNode(i, pos, up, level, parent, dict(children))
             for i, (pos, up, level, parent, children) in enumerate(shape)]
    return nodes


def max_feeds_2d(levels: int = MAX_LEVELS, up: str = "w") -> int:
    """The most leaf feeds a unit-adjacency tree of at most `levels` levels can offer in 2D."""
    best = 0
    for shape in _shapes(up):
        nodes = _rebuild(shape)
        if max(nd.level for nd in nodes) <= levels:
            best = max(best, len(_leaf_faces(nodes, frozenset({_add((0, 0), up)}))))
    return best


def embed_tree(n: int, up: str = "w") -> EmbeddedTree:
    """The tree with the FEWEST levels, then the fewest nodes, that offers at least `n` leaves in 2D."""
    if n < 1:
        raise TreeError("a tree needs at least one feed")
    reserved = frozenset({_add((0, 0), up)})
    if n == 1:
        return EmbeddedTree(1, up, [], {0: (-1, up, reserved and next(iter(reserved)))},
                            DistributionTree(1, [], {0: []}), 0)
    best = None
    for shape in _shapes(up):
        nodes = _rebuild(shape)
        leaves = _leaf_faces(nodes, reserved)
        if len(leaves) < n:
            continue
        # fewest levels, then fewest nodes; then prefer children on the HIGHEST face codes (the proven #271 tree
        # hangs its child off code 2 = E), then the most leaves
        key = (max(nd.level for nd in nodes), len(nodes),
               -sum(nd.parent[1] for nd in nodes if nd.parent), -len(leaves))
        if best is None or key < best[0]:
            best = (key, nodes, leaves)
    if best is None:
        raise TreeError(f"{n} feeds do not fit in 2D: a tree whose parent and child are unit neighbours (the routing "
                        f"byte rides dedicated wires between ADJACENT nodes) offers at most {max_feeds_2d(MAX_LEVELS, up)} "
                        f"leaves in {MAX_LEVELS} levels, though the 2-bit count could address 27. The format reserves "
                        f"a third axis (6-bit routing_mask/cardinal_edge slots), not built")
    _, nodes, leaves = best
    leaf_set = {(i, f) for i, f, _ in leaves}
    first = {(i, f): c for i, f, c in leaves}
    tnodes = [TreeNode(nd.index, nd.level, nd.parent) for nd in nodes]
    pins: Dict[int, Tuple[int, str, Pos]] = {}
    paths: Dict[int, List[int]] = {}
    counter = [0]

    def walk(nd: EmbNode, prefix: List[int]) -> None:
        for code, f in enumerate(out_faces(nd.up)):
            if f in nd.children:
                tnodes[nd.index].slots[code] = ("node", nd.children[f])
                walk(nodes[nd.children[f]], prefix + [code])
            elif (nd.index, f) in leaf_set and counter[0] < n:
                tnodes[nd.index].slots[code] = ("leaf", counter[0])
                paths[counter[0]] = prefix + [code]
                pins[counter[0]] = (nd.index, f, first[(nd.index, f)])
                counter[0] += 1
    walk(nodes[0], [])
    return EmbeddedTree(n, up, nodes, pins, DistributionTree(n, tnodes, paths), len(leaves) - n)
