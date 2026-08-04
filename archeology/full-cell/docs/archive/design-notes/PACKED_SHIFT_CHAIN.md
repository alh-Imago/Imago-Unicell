# Packed Word Shift-Chain Methodology

## Core Insight

The KS parallel prefix adder currently uses 32 columns × 5 stages = 160 prefix cells,
where each column holds one bit-position's G/P value as a 32-bit word.

But the G/P values for ALL 32 bit-positions can be PACKED into a single 32-bit word
(one bit per position). Then the KS prefix combine operation becomes a shift+AND+OR
inside a single cell — collapsing each entire stage into ONE cell.

Result: 5 prefix cells instead of 160. ~30× compression.

## The KS Prefix Operation (packed form)

Standard KS combine:
    G[i:j] = G[i:k] | (P[i:k] & G[k-1:j])

Packed into a 32-bit word where bit N = position N:
    G_new = G | (P & (G >> span))
    P_new = P & (P >> span)

Stage 1: span=1   →  G = G | (P & (G >> 1))
Stage 2: span=2   →  G = G | (P & (G >> 2))
Stage 3: span=4   →  G = G | (P & (G >> 4))
Stage 4: span=8   →  G = G | (P & (G >> 8))
Stage 5: span=16  →  G = G | (P & (G >> 16))

Each stage = 1 SHR + 1 AND + 1 OR = 3 cells chained.
5 stages × 3 cells = 15 prefix cells total (vs 160).
Plus ~6 cells for G/P extraction and XOR sum = ~21 cells total (vs 482).
