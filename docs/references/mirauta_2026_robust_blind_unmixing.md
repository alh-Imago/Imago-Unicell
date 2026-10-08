# Robust blind unmixing: a geometric approach to overcoming basis variation

**Citation.** Dumitru Mirauta, Vladimir V. Gusev, Michael W. Gaultois, Matthew J. Rosseinsky
and Yannis Goulermas. *Robust blind unmixing: A geometric approach to overcoming basis
variation.* arXiv:2610.04091 [cs.LG], 2 October 2026. University of Liverpool (School of
Computer Science and Informatics; Materials Innovation Factory).
<https://arxiv.org/abs/2610.04091>

The paper itself is not stored here: it is on arXiv, and whether to republish the PDF is for its
authors to decide. These notes are our own summary, written to see which of its algorithms could
be built from UniCell cells (ledger #1034).

## What the paper does (our summary)

A measured signal, such as a powder X-ray diffraction (PXRD) pattern or a hyperspectral pixel,
is a mixture of **basis patterns**, one per pure component. Unmixing means recovering the basis
and the abundances. The difficulty the paper addresses is **basis variation**: from one mixture to
the next the same component's pattern changes. Its peaks shift and broaden, for example with
temperature or strain. Pointwise distances (Euclidean) treat a shifted peak as a different peak
and give many false local minima. Optimal-transport (Wasserstein) distances grow smoothly with
the shift.

The method treats patterns as points in a metric space and looks for decompositions whose
**basis variants cluster tightly**. It minimises the in-class Fréchet variance of the candidate
basis variants (eq. 12) by alternating two steps:

- **Averaging** (eq. 13, Algorithms 1-2): each basis becomes the W2 **barycentre** of its
  variants. A pairwise barycentre is a displacement (McCann) interpolation along the optimal
  transport plan. Many patterns are averaged with a hierarchical tree of pairwise barycentres,
  each level run in parallel.
- **Separation** (eqs. 17-21, Algorithm 3): for each mixture `c`, the abundances `a` minimise
  W2²(Σ aᵢ bᵢ, c), a convex problem in `a`. The optimal transport plan from the combined basis to
  the mixture then splits `c` into its varied bases.

Patterns are stored as **signatures**: N Diracs (positions plus weights), 64 in the experiments,
built by agglomerative clustering (section 4.2). The key enabler is section 4.1: in 1D, on
**sorted** signatures, the **north-west corner algorithm** (Algorithm 5) gives the exact optimal
plan in N+M−1 steps (Theorem 1), so no linear program is needed.

Experiments: random GMM datasets (K = 3 bases, M = 800 mixtures), simulated PXRD (K = 6,
M = 1275) and laboratory hyperspectral scenes. The method gives lower abundance and basis errors
than NMF and overlapping NMF, especially at high basis variation.

## How it maps onto UniCell cells

| Piece | Fit | How |
|---|---|---|
| 1D W2 distance and plan (Algorithm 5) | **good** | The north-west corner walk has data-dependent control flow, but its result equals a **merge of the two sorted lists of cumulative weights**, which is a fixed comparator network (Batcher odd-even merge). W2² = Σ Δt · (Q_μ − Q_ν)² over the merged segments: prefix sums (adder chains), the merge, then square, weight and sum (multipliers, adder tree). Data-independent and streaming. |
| Compare-exchange (the merge's unit) | good | d = a − b (subtract); s = [d ≥ 1] (comparator); min = a − d·s, max = b + d·s (multiply select, as in #987), and the same for a payload. About 9 cells. |
| Hierarchical barycentre (Algorithm 2) | good | A pairwise reduction tree, the same shape as `parallel_reduction_tree`. |
| Pairwise barycentre (Algorithm 1) | partial | The interpolation is multiply/add; the barycentric projection divides by a weight, which needs a fixed-point reciprocal or power-of-two weight totals (a shift). |
| Separation (Algorithm 3) | fabric as evaluator | The search over abundances stays outside (or is unrolled in space); the fabric scores candidates at pipeline rate. |
| Signature quantisation | host | Data-dependent clustering, once per pattern. |

**Precision.** Integer fixed-point fits: grid-index positions, weights scaled to a fixed total
T, a one-cell comparator per compare, exact results that can be checked bit for bit. The fp
blocks (about 1,500 cells each) would make a merge network far too large.

## Built so far

`tools/ot_w2_v1.py` (ledger #1034): the **1D W2 distance engine**. Two sorted signatures of `n`
Diracs each (integer positions, integer weights summing to `T`) go in, and the exact
`T · W2²` comes out. The trick that makes it a fixed network: each cumulative-weight breakpoint
carries one signed payload, the step in that signature's position (μ positive, ν negative).
After the merge, a running sum of the payloads gives Q_μ − Q_ν on every segment, so the
north-west corner walk needs no indexing. It is checked against two independent references (the
merge formula and a direct north-west corner implementation) and a numerical quantile integral.

The n = 4, T = 64 engine is **exact in FlexGrid**: 7 streamed items, all bit for bit, in 3,076
ticks. It uses 5,584 cells (4,813 ram/route, 605 cross, 80 adder, 78 mul, 8 comparator). The
longest path is 675 hops, so the latency is about 1,350 cycles per result, and the engine is
pipelined: a new item can go in every few hundred ticks. The design has no subtract, because
a − b is built as a + (−1)·b, so no operand order has to be balanced. A compare-exchange
between two pad lanes is decided at build time.

**Open.** The generated-RTL check is skipped. The flex generator refuses a same-tick operand
pair even on a commutative add or multiply, and the engine has two such ties (a square's two
copies). Either the generator accepts ties on commutative cores, or those two squares get a
spacer. See `tests/vm/test_ot_w2_v1.py`.

**Feeding it.** At 115 kbaud over JTAG one item (4n + 2 values) takes a few ms, so a host-fed
engine is limited by the link, not by the fabric. For real throughput the signatures would be
preloaded into the 8 MB RAM and streamed out through the Arria 10 RAM interface tree (ledger
#255–#271, one bus in and one out), with one engine per tile working in parallel.
