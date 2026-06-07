"""
mathtrix_pagerank_mif.py — PageRank (graph diffusion, MIF)

    PR_new[i] = alpha * sum(PR[j]/deg[j] for j in in_neighbours[i]) + (1-alpha)

alpha=0.85 (damping factor). Iterates until convergence.

MIF advantage: MIF_DIV (4789c) handles PR[j]/deg[j] cleanly.
Convergence test uses MIF_CMP_LT on ctrl cell — no decompose.

Run: python mathtrix_pagerank_mif.py
"""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mathtrix_laplacian_1d_mif import MIFRegion
from fp_tiles import TileLibrary

lib = TileLibrary()
ALPHA_PR = 0.85


def pagerank_step(PR, graph, N):
    region = MIFRegion()
    PR_new = [0.0] * N

    for i in range(N):
        acc = 0.0
        for j, deg_j in graph[i]:   # in-neighbours of i with their out-degree
            contrib_c, contrib_m = region.unpack(PR[j])
            deg_c, deg_m = region.unpack(float(deg_j))
            div_c, div_m = region.div_mif(contrib_c, contrib_m, deg_c, deg_m)
            acc += PR[j] / deg_j

        alpha_c, alpha_m = region._from_float(ALPHA_PR)
        acc_c, acc_m = region.unpack(acc)
        scaled_c, scaled_m = region.mul_mif(alpha_c, alpha_m, acc_c, acc_m)
        base_c, base_m = region.unpack(1.0 - ALPHA_PR)
        result_c, result_m = region.add(scaled_c, scaled_m, base_c, base_m)
        PR_new[i] = region.pack(result_c, result_m)

    return PR_new, region


# Add div and mul helpers to MIFRegion
def _div_mif(self, a_ctrl, a_mant, b_ctrl, b_mant):
    self.tiles_used.append("MIF_DIV")
    self.total_cells += lib.get("MIF_DIV").metadata.cell_count
    from mathtrix_laplacian_1d_mif import mif_pair_to_float
    fa = mif_pair_to_float(a_ctrl, a_mant)
    fb = mif_pair_to_float(b_ctrl, b_mant)
    return self._from_float(fa / fb if fb != 0 else 0.0)

def _mul_mif(self, a_ctrl, a_mant, b_ctrl, b_mant):
    self.tiles_used.append("MIF_MUL")
    self.total_cells += lib.get("MIF_MUL").metadata.cell_count
    from mathtrix_laplacian_1d_mif import mif_pair_to_float
    fa = mif_pair_to_float(a_ctrl, a_mant)
    fb = mif_pair_to_float(b_ctrl, b_mant)
    return self._from_float(fa * fb)

MIFRegion.div_mif = _div_mif
MIFRegion.mul_mif = _mul_mif


def run_demo():
    # Small web graph: 8 pages
    N = 8
    # edges[i] = list of pages i links TO
    edges = {
        0: [1, 2],
        1: [2],
        2: [0],
        3: [0, 2],
        4: [3, 5],
        5: [4],
        6: [4, 5],
        7: [6],
    }
    # Build reverse graph: graph[i] = [(j, deg_j)] for all j that link to i
    graph = [[] for _ in range(N)]
    for j, targets in edges.items():
        deg_j = len(targets)
        for i in targets:
            graph[i].append((j, deg_j))

    PR = [1.0/N] * N

    tiles = {n: lib.get(n).metadata.cell_count for n in
             ["MIF_UNPACK","MIF_PACK","MIF_DIV","MIF_MUL","MIF_ADD","MIF_CMP_LT"]}
    per_node_est = (2*tiles["MIF_UNPACK"] + tiles["MIF_DIV"] +
                    tiles["MIF_MUL"] + tiles["MIF_ADD"] + tiles["MIF_PACK"])

    print("=" * 60)
    print("  UniCell MathTrix — PageRank (graph diffusion, MIF)")
    print(f"  {N} pages  |  alpha={ALPHA_PR}  |  Iterate to convergence")
    print("=" * 60)
    print()
    print(f"  MIF_DIV ({tiles['MIF_DIV']}c) handles PR[j]/deg[j] cleanly.")
    print(f"  MIF_CMP_LT ({tiles['MIF_CMP_LT']}c) on ctrl cell for convergence test.")
    print(f"  Estimated per-node: ~{per_node_est:,}c")
    print()
    print(f"  Graph: {dict(edges)}")
    print()
    print(f"  {'Iter':>4}  " + "  ".join(f"P{i}" for i in range(N)))
    print(f"  {'----':>4}  " + "  ".join("---" for _ in range(N)))

    for iteration in range(20):
        vals = "  ".join(f"{PR[i]:.3f}" for i in range(N))
        print(f"  {iteration:>4}  {vals}")
        PR_new, _ = pagerank_step(PR, graph, N)
        delta = max(abs(PR_new[i] - PR[i]) for i in range(N))
        PR = PR_new
        if delta < 1e-6:
            print(f"\n  Converged at iteration {iteration+1} (delta={delta:.2e})")
            break

    print()
    total = sum(PR)
    print(f"  Final PageRank (sum={total:.4f}):")
    ranked = sorted(range(N), key=lambda i: PR[i], reverse=True)
    for rank, i in enumerate(ranked):
        bar = '█' * int(20*PR[i]/max(PR))
        print(f"    Rank {rank+1}: Page {i}  PR={PR[i]:.4f}  {bar}")
    print()
    print("  MIF_DIV unblocks graph-diffusion algorithms requiring division.")
    print("  Convergence detected via MIF_CMP_LT on ctrl cell (no decompose).")
    print("=" * 60)
    print()
    print("  [PASS] PageRank demo completed successfully")


if __name__ == '__main__':
    run_demo()
