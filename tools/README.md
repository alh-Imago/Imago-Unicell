# Tools

Standalone utilities and offshoots built alongside the Imago UniCell project.
Each tool lives in its own subdirectory with its own README, setup, and dependencies.
None require the UniCell VM or hardware to run.

## onion/

**Onion 🧅 — Adaptive Layered Compression Engine**

A self-contained file compression engine with a layered pipeline architecture:
RLE → LZ77 → Huffman → AES-256-GCM. The Strategist analyses input entropy before
compressing; the Gain Monitor prunes layers that don't help. Archives are
fully self-describing with a signed metadata block.

See `onion/README.md` for full documentation.
