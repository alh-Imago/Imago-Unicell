"""
gol.py — Conway's Game of Life on the Imago UniCell VM

Each GoL cell is ~50 UniCells:
  - 6-stage Wallace tree: 8 1-bit neighbour inputs → 4-bit count (32 cells)
  - count==2 comparator (4 cells)
  - count==3 comparator (4 cells)
  - GoL rule: born, survive, next_state (5 cells)
  - State placeholder (pre-injected each generation, not a real cell)
  TOTAL: ~45 cells per GoL cell

Per generation, all STATE addresses are pre-injected as known_values
so every SYNC_WAIT cell fires immediately — purely combinational pass.

Wallace tree (verified against all 256 inputs):
  Stage 1: 4 half-adders on pairs → 4 w1 sums + 4 w2 carries
  Stage 2: 1 full-adder on 3 w1 sums → 1 w1 sum + 1 w2 carry  
  Stage 3: 1 half-adder → bit0 + 1 w2 carry
  Stage 4: 2 full-adders on 6 w2 bits → 2 w2 sums + 2 w4 carries
  Stage 5: 1 half-adder → bit1 + 1 w4 carry
  Stage 6: 1 full-adder → bit2 + bit3(overflow, always 0 for ≤8)

Usage:
    python3 gol.py --width 15 --height 15 --ticks 20 --pattern glider
    python3 gol.py --width 34 --height 34 --ticks 100 --pattern random
    python3 gol.py --width 48 --height 48 --cells 200000 --pattern r_pentomino
"""

import argparse, random, time
import imago_log
imago_log.set_level(imago_log.SILENT)

from gate_states import (GS_NOT, GS_PASS, GS_AND_V2, GS_OR_V2, GS_XOR_V2,
                         GS_SYNC_WAIT, GS_OUT_POSEDGE)
from controller import ImagoController, CellMapRecord

# ── Address layout ────────────────────────────────────────────────────────────
STRIDE = 64  # address slots per GoL cell

def gbase(r, c, W, H):
    return 0x10000 + ((r % H) * W + (c % W)) * STRIDE

def A(r, c, W, H, off):
    return gbase(r, c, W, H) + off

# Named offsets — every GoL cell uses these relative to its base
OFF_STATE  = 0    # pre-injected: current alive/dead state
# Wallace tree intermediates
OFF_S10=2; OFF_C10=3  # HA(n0,n1): weight-1 sum, weight-2 carry
OFF_S11=4; OFF_C11=5  # HA(n2,n3)
OFF_S12=6; OFF_C12=7  # HA(n4,n5)
OFF_S13=8; OFF_C13=9  # HA(n6,n7)
OFF_FA2S=10; OFF_FA2C=11  # FA(s10,s11,s12): w1→w1+w2
OFF_BIT0=12; OFF_B0C=13   # HA(fa2s,s13): → bit0 + carry
# 6 weight-2 bits: C10,C11,C12,C13,FA2C,B0C
OFF_FA4AS=14; OFF_FA4AC=15  # FA(c10,c11,c12)
OFF_FA4BS=16; OFF_FA4BC=17  # FA(c13,fa2c,b0c)
OFF_BIT1=18; OFF_B1C=19     # HA(fa4as,fa4bs): → bit1 + carry
OFF_BIT2=20                  # FA(fa4ac,fa4bc,b1c) → bit2
# Comparators
OFF_NB0=21; OFF_NB2=22      # NOT(bit0), NOT(bit2)
OFF_EQ2A=23; OFF_EQ2=24     # count==2
OFF_EQ3A=25; OFF_EQ3=26     # count==3
# Rule
OFF_OR23=27; OFF_SURV=28; OFF_NALV=29; OFF_BORN=30; OFF_NEXT=31
# Temporaries for full adder internals (5 per FA)
OFF_T = 32  # 32–62 available


def AND(a, b, out):
    return [CellMapRecord(GS_AND_V2|GS_SYNC_WAIT|GS_OUT_POSEDGE,
                          a, out, input_b_address=b)]

def OR(a, b, out):
    return [CellMapRecord(GS_OR_V2|GS_SYNC_WAIT|GS_OUT_POSEDGE,
                          a, out, input_b_address=b)]

def XOR(a, b, out):
    return [CellMapRecord(GS_XOR_V2|GS_SYNC_WAIT|GS_OUT_POSEDGE,
                          a, out, input_b_address=b)]

def NOT(a, out):
    return [CellMapRecord(GS_NOT|GS_OUT_POSEDGE, a, out)]

def HA(a, b, s, c):
    """Half adder: s=a^b, c=a&b. 2 cells."""
    return XOR(a,b,s) + AND(a,b,c)

def FA(a, b, cin, s, cout, t):
    """Full adder using temps t, t+1, t+2. 5 cells."""
    return (XOR(a, b, t) +
            XOR(t, cin, s) +
            AND(a, b, t+1) +
            AND(cin, t, t+2) +
            OR(t+1, t+2, cout))


def build_gol_cell(r, c, W, H):
    """Build ~45 CellMapRecords for one GoL cell at (r,c)."""
    def a(off): return A(r, c, W, H, off)
    def t(i):   return a(OFF_T + i)

    # 8 neighbour STATE addresses (toroidal)
    dirs = [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]
    N = [A(r+dr, c+dc, W, H, OFF_STATE) for dr,dc in dirs]

    recs = []

    # Stage 1: 4 half-adders on pairs of neighbours
    recs += HA(N[0], N[1], a(OFF_S10), a(OFF_C10))
    recs += HA(N[2], N[3], a(OFF_S11), a(OFF_C11))
    recs += HA(N[4], N[5], a(OFF_S12), a(OFF_C12))
    recs += HA(N[6], N[7], a(OFF_S13), a(OFF_C13))

    # Stage 2: FA(s10, s11, s12) → fa2_s (w1), fa2_c (w2)
    recs += FA(a(OFF_S10), a(OFF_S11), a(OFF_S12),
               a(OFF_FA2S), a(OFF_FA2C), t(0))

    # Stage 3: HA(fa2_s, s13) → bit0, carry-to-w2
    recs += HA(a(OFF_FA2S), a(OFF_S13), a(OFF_BIT0), a(OFF_B0C))

    # Stage 4: 2 full-adders on 6 weight-2 bits
    # FA(c10, c11, c12) → fa4a_s, fa4a_c
    recs += FA(a(OFF_C10), a(OFF_C11), a(OFF_C12),
               a(OFF_FA4AS), a(OFF_FA4AC), t(5))
    # FA(c13, fa2c, b0c) → fa4b_s, fa4b_c
    recs += FA(a(OFF_C13), a(OFF_FA2C), a(OFF_B0C),
               a(OFF_FA4BS), a(OFF_FA4BC), t(10))

    # Stage 5: HA(fa4a_s, fa4b_s) → bit1, carry-to-w4
    recs += HA(a(OFF_FA4AS), a(OFF_FA4BS), a(OFF_BIT1), a(OFF_B1C))

    # Stage 6: FA(fa4a_c, fa4b_c, b1c) → bit2 (bit3 ignored: max count=8)
    recs += FA(a(OFF_FA4AC), a(OFF_FA4BC), a(OFF_B1C),
               a(OFF_BIT2), t(15), t(16))  # cout goes to t(15), unused

    # Comparators: count==2 and count==3
    recs += NOT(a(OFF_BIT0), a(OFF_NB0))
    recs += NOT(a(OFF_BIT2), a(OFF_NB2))
    # eq2: bit1=1 AND NOT(bit0) AND NOT(bit2)
    recs += AND(a(OFF_BIT1), a(OFF_NB0),  a(OFF_EQ2A))
    recs += AND(a(OFF_EQ2A), a(OFF_NB2),  a(OFF_EQ2))
    # eq3: bit1=1 AND bit0=1 AND NOT(bit2) = eq3a AND NOT(bit2)
    recs += AND(a(OFF_BIT1), a(OFF_BIT0), a(OFF_EQ3A))
    recs += AND(a(OFF_EQ3A), a(OFF_NB2),  a(OFF_EQ3))

    # GoL rule: next = (eq3 AND NOT alive) OR (OR(eq2,eq3) AND alive)
    recs += OR( a(OFF_EQ2),   a(OFF_EQ3),   a(OFF_OR23))
    recs += AND(a(OFF_OR23),  a(OFF_STATE),  a(OFF_SURV))
    recs += NOT(a(OFF_STATE),               a(OFF_NALV))
    recs += AND(a(OFF_EQ3),   a(OFF_NALV),  a(OFF_BORN))
    recs += OR( a(OFF_SURV),  a(OFF_BORN),  a(OFF_NEXT))

    return recs


def build_grid(W, H, initial):
    all_recs, state_addrs, next_addrs = [], {}, {}
    for r in range(H):
        for c in range(W):
            all_recs.extend(build_gol_cell(r, c, W, H))
            state_addrs[(r,c)] = A(r, c, W, H, OFF_STATE)
            next_addrs[(r,c)]  = A(r, c, W, H, OFF_NEXT)
    return all_recs, state_addrs, next_addrs


# ── Patterns ──────────────────────────────────────────────────────────────────

def p_glider(W, H):
    cells = [(1,2),(2,3),(3,1),(3,2),(3,3)]
    return {(r%H,c%W):1 for r,c in cells}

def p_blinker(W, H):
    r,c = H//2, W//2
    return {(r,c):1,(r,c+1):1,(r,c+2):1}

def p_random(W, H, density=0.3, seed=42):
    rng = random.Random(seed)
    return {(r,c):1 for r in range(H) for c in range(W) if rng.random()<density}

def p_rpentomino(W, H):
    r,c = H//2, W//2
    cells = [(r,c+1),(r,c+2),(r+1,c),(r+1,c+1),(r+2,c+1)]
    return {(r2%H,c2%W):1 for r2,c2 in cells}


# ── Renderer ──────────────────────────────────────────────────────────────────

def render(state_addrs, state, W, H, tick, ms, live):
    lines = [f"\033[H\033[2J  GoL {W}×{H}  gen={tick}  "
             f"live={live}/{W*H}  {ms:.0f}ms/gen"]
    for r in range(H):
        row = "  "
        for c in range(W):
            row += "█" if state.get(state_addrs[(r,c)],0) else "·"
        lines.append(row)
    print("\n".join(lines))


# ── Runner ────────────────────────────────────────────────────────────────────

def run_gol(W=15, H=15, ticks=20, pattern="glider", cell_count=None, delay=0.05):
    pats = {"glider":p_glider,"blinker":p_blinker,"random":p_random,"r_pentomino":p_rpentomino}
    initial = pats.get(pattern, p_random)(W, H)

    print(f"Building {W}×{H} GoL grid...")
    records, state_addrs, next_addrs = build_grid(W, H, initial)
    print(f"  {len(records):,} UniCells  ({len(records)//(W*H)} per GoL cell)")

    current = {addr:0 for addr in state_addrs.values()}
    for (r,c),live in initial.items():
        if live: current[state_addrs[(r,c)]] = 1

    n_cells = cell_count or (len(records)+5000)
    ctrl = ImagoController(cell_count=n_cells)
    ctrl.array._segments[0].lane_count = len(records)*3

    capture = list(next_addrs.values())
    print(f"Running {ticks} generations... (Ctrl+C to stop)")
    import time; time.sleep(0.3)

    for tick in range(ticks):
        t0 = time.time()
        rid = ctrl.load_map(records, "gol", known_values=dict(current))
        result = ctrl.run(rid, inputs={}, capture_addresses=capture,
                          max_cycles=len(records)*5)

        new = {}
        for (r,c) in state_addrs:
            val = 1 if (result and result.get(next_addrs[(r,c)],0)) else 0
            new[state_addrs[(r,c)]] = val
        current = new

        ms = (time.time()-t0)*1000
        live = sum(current.values())
        render(state_addrs, current, W, H, tick+1, ms, live)
        if delay > 0: time.sleep(max(0, delay - ms/1000))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Conway's Game of Life on UniCell VM")
    p.add_argument("--width",   "-W", type=int, default=15)
    p.add_argument("--height",  "-H", type=int, default=15)
    p.add_argument("--ticks",   "-t", type=int, default=20)
    p.add_argument("--pattern", "-p", default="glider",
                   choices=["glider","blinker","random","r_pentomino"])
    p.add_argument("--cells",   type=int, default=None)
    p.add_argument("--delay",   type=float, default=0.05)
    args = p.parse_args()
    run_gol(args.width, args.height, args.ticks, args.pattern, args.cells, args.delay)
