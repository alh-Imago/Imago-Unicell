"""
experimental_3d_crossing_demo_v1.py — the real, concrete test of the
architecture question: can a 6-cardinal fabric build a shape that's
structurally IMPOSSIBLE in a pure 4-cardinal one?

THE SHAPE: Path A runs east-west along row=2, layer=0 (a straight
relay chain). Path B runs north-south along col=2, but DIPS DOWN to
layer=-1 for exactly the one row where it would otherwise collide with
Path A's own cell at (2,2,0) -- passing physically underneath it, then
back up. In a top-down PROJECTION (ignoring layer), the two paths
visibly cross at (row=2, col=2) -- but they never share a physical
cell, and never interfere. That's the real, honest proof: with only
four cardinals, single-hop-only, no-relay wiring, this exact crossing
would force both paths through the SAME physical cell at (2,2) -- a
genuine conflict, not just an inconvenience (this project's own
established constraint: one cell, one wired role at a time).
"""

from experimental_3d_grid_v1 import Grid3D, ToyCell3D, N, S, E, W, U, D, pack_dirmask

grid = Grid3D()

# ── Path A: straight east-west relay chain, row=2, layer=0, col 0..4 ──
for col in range(5):
    listen = pack_dirmask([W]) if col > 0 else 0
    downstream = pack_dirmask([E]) if col < 4 else 0
    grid.place(ToyCell3D(row=2, col=col, layer=0, mode="relay",
                          listen_mask=listen, downstream_mask=downstream))

# ── Path B: north-south at col=2, dipping to layer=-1 for row=2 only ──
path_b_nodes = [
    (0, 2, 0), (1, 2, 0), (1, 2, -1), (2, 2, -1), (3, 2, -1), (3, 2, 0), (4, 2, 0),
]
path_b_links = [  # (from, to, direction_from_to)
    ((0, 2, 0), (1, 2, 0), S),
    ((1, 2, 0), (1, 2, -1), D),
    ((1, 2, -1), (2, 2, -1), S),
    ((2, 2, -1), (3, 2, -1), S),
    ((3, 2, -1), (3, 2, 0), U),
    ((3, 2, 0), (4, 2, 0), S),
]
listen_of = {pos: 0 for pos in path_b_nodes}
downstream_of = {pos: 0 for pos in path_b_nodes}
for src, dst, direction in path_b_links:
    downstream_of[src] |= pack_dirmask([direction])
    from experimental_3d_grid_v1 import _OPPOSITE
    listen_of[dst] |= pack_dirmask([_OPPOSITE[direction]])
for pos in path_b_nodes:
    r, c, l = pos
    grid.place(ToyCell3D(row=r, col=c, layer=l, mode="relay",
                          listen_mask=listen_of[pos], downstream_mask=downstream_of[pos]))

print(f"Grid built: {len(grid.cells)} cells "
      f"(Path A: 5 cells at layer=0, Path B: 7 cells spanning layer=0/-1)")
print(f"Cell at (2,2,0) [Path A's crossing point] is NOT in Path B's node list: "
      f"{(2, 2, 0) not in path_b_nodes}")

# ── Fire both paths simultaneously -- the real test ──
# ── Fire both paths simultaneously -- the real test. Source cells have
# no real upstream neighbor, so seed their own state directly (the
# generic offer pass then carries it forward on the very next tick,
# same mechanism every other hop already uses). ──
grid.cells[(2, 0, 0)].relay_value = 0xAAAA
grid.cells[(2, 0, 0)].relay_valid = True
grid.cells[(0, 2, 0)].relay_value = 0xBBBB
grid.cells[(0, 2, 0)].relay_valid = True

ticks = 0
while ticks < 50:
    grid.tick()
    ticks += 1
    if not grid._pending and grid.cells[(2, 4, 0)].pending_ack == 0 \
            and grid.cells[(4, 2, 0)].pending_ack == 0:
        break

a_end = grid.cells[(2, 4, 0)]
b_end = grid.cells[(4, 2, 0)]

print(f"\nRan {ticks} ticks to quiescence.")
print(f"Path A's east end (2,4,0): relay_value={a_end.relay_value:#06x}, "
      f"correct={a_end.relay_value == 0xAAAA}")
print(f"Path B's south end (4,2,0): relay_value={b_end.relay_value:#06x}, "
      f"correct={b_end.relay_value == 0xBBBB}")

# The crossing cell itself must show ONLY Path A's value -- Path B never
# touched it, confirming zero interference at the projected crossing point.
crossing = grid.cells[(2, 2, 0)]
print(f"\nThe crossing point (2,2,0) itself: relay_value={crossing.relay_value:#06x} "
      f"(Path A's value only, {crossing.relay_value == 0xAAAA} -- Path B genuinely "
      f"never touched this cell)")

if a_end.relay_value == 0xAAAA and b_end.relay_value == 0xBBBB:
    print("\nPASS: two independent signal paths crossed in projected 2D space "
          "with ZERO shared cells and zero interference -- a shape with no "
          "2D equivalent under this project's own single-hop, one-role-per-cell "
          "cardinal wiring constraint.")
else:
    print("\nFAIL: crossing did not resolve cleanly")
