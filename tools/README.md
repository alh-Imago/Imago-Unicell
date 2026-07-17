# Tools

Standalone utilities and offshoots built alongside the Imago UniCell project.
Each tool lives in its own subdirectory with its own README, setup, and dependencies.
None require the UniCell VM or hardware to run.

## onion/ (git submodule → github.com/alh-Imago/Onion)

**Onion 🧅 — Adaptive Layered Compression Engine**

A self-contained file compression engine with a layered pipeline architecture:
RLE → LZ77 → Huffman → AES-256-GCM. The Strategist analyses input entropy before
compressing; the Gain Monitor prunes layers that don't help. Archives are
fully self-describing with a signed metadata block.

This directory is a git submodule pointing at its own repository
(`github.com/alh-Imago/Onion`), not a plain copy — the tool is developed
there independently and updates pull straight through here. After cloning
this repo fresh, run `git submodule update --init --recursive` to populate
it (it will appear empty otherwise). See `onion/README.md` for full
documentation once populated.
