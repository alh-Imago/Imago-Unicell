"""
analyser.py  —  The Strategist
───────────────────────────────
Reads a raw byte payload and produces an InstructionSet that tells the
Transformer what to do and in what order.

Decision logic
──────────────
1. Measure Shannon entropy (0.0 – 8.0 bits/byte).
   • > 7.5  →  file is already compressed / encrypted → Raw only (+ optional AES)
2. Scan for RLE opportunity.
   • If runs of ≥ 3 identical bytes cover > 15 % of the file → RLE first.
3. Measure LZ77 compressibility via a fast token-frequency heuristic.
   • If top-256 byte-pair tokens cover > 60 % of content → LZ77 is a strong win.
4. After LZ77 (or RLE), symbol distribution will be skewed → Huffman is almost
   always worthwhile; add it unless entropy is already > 7.0 post-scan estimate.
5. AES-256-GCM is appended last if the caller requested encryption.
"""

import math
from collections import Counter
from typing import Tuple

from .instruction import AlgoID, InstructionSet, LayerDescriptor


# ── Thresholds ───────────────────────────────────────────────────────────────

ENTROPY_INCOMPRESSIBLE  = 7.5   # above this → skip compression entirely
ENTROPY_SKIP_HUFFMAN    = 7.0   # above this post-scan estimate → skip Huffman
RLE_COVERAGE_THRESHOLD  = 0.15  # 15 % of bytes in runs ≥ 3 → RLE worthwhile
DICT_COVERAGE_THRESHOLD = 0.60  # 60 % coverage by top-256 bigrams → LZ77 strong


# ── Entropy measurement ───────────────────────────────────────────────────────

def shannon_entropy(data: bytes) -> float:
    """Return Shannon entropy in bits per byte (0.0 – 8.0)."""
    if not data:
        return 0.0
    counts = Counter(data)
    length = len(data)
    entropy = 0.0
    for count in counts.values():
        p = count / length
        entropy -= p * math.log2(p)
    return entropy


# ── RLE opportunity scan ──────────────────────────────────────────────────────

def rle_coverage(data: bytes) -> float:
    """
    Return the fraction of bytes that sit inside a run of ≥ 3 identical bytes.
    Fast single-pass scan.
    """
    if len(data) < 3:
        return 0.0

    covered = 0
    i = 0
    n = len(data)

    while i < n:
        run_start = i
        b = data[i]
        while i < n and data[i] == b:
            i += 1
        run_len = i - run_start
        if run_len >= 3:
            covered += run_len

    return covered / n


# ── Dictionary/LZ77 opportunity heuristic ─────────────────────────────────────

def dict_coverage(data: bytes) -> float:
    """
    Approximate LZ77 compressibility by measuring what fraction of the file
    is covered by the top-256 most frequent byte-pair (bigram) tokens.

    This is a fast O(n) proxy — it doesn't run an actual LZ77 pass.
    """
    if len(data) < 2:
        return 0.0

    bigrams = Counter(zip(data, data[1:]))
    total_bigrams = len(data) - 1

    # Take the top 256 most common bigrams
    top256_count = sum(count for _, count in bigrams.most_common(256))
    return top256_count / total_bigrams


# ── Main Strategist entry point ───────────────────────────────────────────────

def analyse(data: bytes, encrypt: bool = False) -> InstructionSet:
    """
    Analyse *data* and return an InstructionSet for the Transformer.

    Parameters
    ----------
    data    : raw file bytes
    encrypt : whether to append an AES-256-GCM layer
    """
    import binascii

    iset = InstructionSet(
        original_size  = len(data),
        original_crc   = binascii.crc32(data) & 0xFFFFFFFF,
        encrypt        = encrypt,
    )

    # ── Step 1: entropy ───────────────────────────────────────────────────────
    entropy = shannon_entropy(data)
    iset.entropy_score = entropy

    print(f"  [Strategist] Entropy score : {entropy:.3f} bits/byte")

    if entropy > ENTROPY_INCOMPRESSIBLE:
        print(f"  [Strategist] File appears already compressed/encrypted → Raw only")
        iset.add(AlgoID.RAW)
        if encrypt:
            iset.add(AlgoID.AES256)
            iset.encrypt = True
        return iset

    # ── Step 2: RLE scan ──────────────────────────────────────────────────────
    rle_cov = rle_coverage(data)
    print(f"  [Strategist] RLE coverage  : {rle_cov:.1%}")

    if rle_cov > RLE_COVERAGE_THRESHOLD:
        print(f"  [Strategist] RLE is a viable first layer")
        iset.add(AlgoID.RLE)

    # ── Step 3: dictionary/LZ77 scan ─────────────────────────────────────────
    d_cov = dict_coverage(data)
    print(f"  [Strategist] Dict coverage : {d_cov:.1%}")

    if d_cov > DICT_COVERAGE_THRESHOLD:
        print(f"  [Strategist] LZ77 is a strong candidate")
        iset.add(AlgoID.LZ77)
    else:
        # Even with moderate coverage LZ77 is usually worth trying on general
        # text/code; the Gain Monitor will prune it if it doesn't help.
        print(f"  [Strategist] LZ77 added speculatively (Gain Monitor will prune if unhelpful)")
        iset.add(AlgoID.LZ77)

    # ── Step 4: Huffman ───────────────────────────────────────────────────────
    # After LZ77 the symbol distribution will be highly skewed; Huffman nearly
    # always wins unless the data was already near-random.
    if entropy < ENTROPY_SKIP_HUFFMAN:
        print(f"  [Strategist] Huffman added (entropy supports it)")
        iset.add(AlgoID.HUFFMAN)

    # ── Step 5: encryption (always last) ─────────────────────────────────────
    if encrypt:
        print(f"  [Strategist] AES-256-GCM appended as final layer")
        iset.add(AlgoID.AES256)
        iset.encrypt = True

    print(f"  [Strategist] Instruction set: {iset.summary()}")
    return iset
