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
DICT_COVERAGE_THRESHOLD = 0.60
DELTA_SMOOTHNESS_THRESHOLD = 0.70  # smoothness fraction (per plane) → delta worthwhile
DELTA_ENTROPY_FLOOR = 5.0           # below this entropy = text/code, skip delta
LZMA_ENTROPY_CEILING = 6.5          # above this = too random for LZMA to help
LZMA_MIN_SIZE        = 2048         # below this = LZMA header overhead not worth it  # 60 % coverage by top-256 bigrams → LZ77 strong


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



# ── Delta smoothness scan ─────────────────────────────────────────────────────

def delta_smoothness(data: bytes) -> tuple:
    """
    Detect whether data is smooth numerical data that benefits from delta
    encoding. Returns (score, stride) where score is 0.0-1.0 and stride
    is the recommended byte stride (1, 2, or 4).

    Checks stride-2 and stride-4 interleaved planes first (handles packed
    int16/int32/float32). Falls back to byte-level check.

    High score (> 0.5) means delta encoding will reduce entropy before LZ77.
    """
    if len(data) < 8:
        return 0.0, 1

    def _plane_smoothness(plane: bytes) -> float:
        if len(plane) < 2:
            return 0.0
        deltas = [abs(plane[i] - plane[i-1]) for i in range(1, len(plane))]
        return sum(1 for d in deltas if d <= 16) / len(deltas)

    # Try stride-4 (int32 / float32)
    if len(data) % 4 == 0:
        planes = [data[i::4] for i in range(4)]
        score4 = sum(_plane_smoothness(p) for p in planes) / 4
        if score4 > 0.5:
            return score4, 4

    # Try stride-2 (int16)
    if len(data) % 2 == 0:
        planes = [data[i::2] for i in range(2)]
        score2 = sum(_plane_smoothness(p) for p in planes) / 2
        if score2 > 0.5:
            return score2, 2

    # Byte-level
    score1 = _plane_smoothness(data)
    return score1, 1


# ── Main Strategist entry point ───────────────────────────────────────────────

def analyse(data: bytes, encrypt: bool = False, fast: bool = False, encrypt_only: bool = False) -> InstructionSet:
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

    # ── Step 1a: encrypt-only (skip all compression) ────────────────────────
    if encrypt_only:
        if not encrypt:
            raise ValueError("encrypt_only=True requires encrypt=True")
        print(f"  [Strategist] Encrypt-only mode: AES-256-GCM only, no compression")
        iset.add(AlgoID.AES256)
        iset.encrypt = True
        return iset

    # ── Step 1b: fast mode (LZ4) ─────────────────────────────────────────────
    if fast:
        from .algorithms.lz4_layer import available as lz4_available
        if lz4_available():
            print(f"  [Strategist] Fast mode: LZ4 selected (speed over ratio)")
            iset.add(AlgoID.LZ4)
            if encrypt:
                iset.add(AlgoID.AES256)
                iset.encrypt = True
            return iset
        else:
            print(f"  [Strategist] Fast mode requested but lz4 not installed — continuing normally")

    # ── Step 2: RLE scan ──────────────────────────────────────────────────────
    rle_cov = rle_coverage(data)
    print(f"  [Strategist] RLE coverage  : {rle_cov:.1%}")

    if rle_cov > RLE_COVERAGE_THRESHOLD:
        print(f"  [Strategist] RLE is a viable first layer")
        iset.add(AlgoID.RLE)

    # ── Step 2b: delta pre-conditioner scan ─────────────────────────────────
    smoothness, delta_stride = delta_smoothness(data)
    print(f"  [Strategist] Delta smooth  : {smoothness:.1%} (stride={delta_stride})")
    if smoothness > DELTA_SMOOTHNESS_THRESHOLD and entropy > DELTA_ENTROPY_FLOOR:
        print(f"  [Strategist] Delta encoding worthwhile (stride={delta_stride})")
        iset.add(AlgoID.DELTA)
        iset.delta_stride = delta_stride

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

    # ── Step 4b: LZMA (high-ratio alternative to LZ77+Huffman) ──────────────
    # Use LZMA instead of LZ77+Huffman when:
    #   - structured text/code/JSON (low entropy, high redundancy)
    #   - file large enough to amortise LZMA's ~100 byte header
    #   - delta pre-conditioner did NOT run (delta+LZ77 already optimal)
    # LZMA replaces LZ77+Huffman — it doesn't stack on top.
    delta_ran = any(l.algo_id == AlgoID.DELTA for l in iset.layers)
    if (not delta_ran
            and len(data) >= LZMA_MIN_SIZE
            and entropy < LZMA_ENTROPY_CEILING):
        # Replace LZ77 + Huffman + RLE with LZMA — LZMA handles runs natively
        iset.layers = [l for l in iset.layers
                       if l.algo_id not in (AlgoID.LZ77, AlgoID.HUFFMAN, AlgoID.RLE)]
        active_ids = [l.algo_id for l in iset.layers]
        replaced = [n for a,n in [(AlgoID.LZ77,"LZ77"),(AlgoID.HUFFMAN,"Huffman"),(AlgoID.RLE,"RLE")] if a not in active_ids]
        replaced_str = "+".join(replaced) if replaced else "LZ77+Huffman"
        print(f"  [Strategist] LZMA selected (replaces {replaced_str}, entropy={entropy:.2f})")
        iset.add(AlgoID.LZMA)
    else:
        if delta_ran:
            print(f"  [Strategist] LZMA skipped (delta pre-conditioner active, LZ77 sufficient)")
        elif len(data) < LZMA_MIN_SIZE:
            print(f"  [Strategist] LZMA skipped (file too small: {len(data)} bytes)")
        else:
            print(f"  [Strategist] LZMA skipped (entropy {entropy:.2f} > ceiling {LZMA_ENTROPY_CEILING})")

    # ── Step 5: encryption (always last) ─────────────────────────────────────
    if encrypt:
        print(f"  [Strategist] AES-256-GCM appended as final layer")
        iset.add(AlgoID.AES256)
        iset.encrypt = True

    print(f"  [Strategist] Instruction set: {iset.summary()}")
    return iset
