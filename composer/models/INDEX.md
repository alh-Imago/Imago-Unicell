# Community Model Index

Models contributed to the Imago UniCell shared library.
Each entry links to a `.icm` file loadable by the VM or Composer.

Format: `ProgramImage.to_dict()` — load with `ProgramImage.from_dict()`.

---

## How to add a model

1. Place your `.icm` in the appropriate category folder
2. Add a row to the table below
3. PR to main

---

## Logic

| Model | File | Cells | Description | Author |
|:------|:-----|------:|:------------|:-------|
| NOT Gate | `../examples/not_gate.icm` | 1 | Single NOT cell — the primitive | Claudette |
| AND Gate | `../examples/and_gate.icm` | 1 | Two-input AND | Claudette |
| MUX | `../examples/mux.icm` | 5 | 2:1 multiplexer | Claudette |
| Parity 8 | `../examples/parity8.icm` | 7 | 8-input OR reduction, depth 3 | Claudette |
| Equal 32 | `../examples/equal32.icm` | 95 | 32-bit equality, all bits in parallel | Claudette |

## Arithmetic

| Model | File | Cells | Description | Author |
|:------|:-----|------:|:------------|:-------|
| INT32 Adder | `../examples/adder_int32.icm` | 483 | 32-bit Kogge-Stone adder, depth 2 | Claudette |
| Sum of Four | `../examples/sum4.icm` | 1,641 | Four int32 values via 3 chained adders | Claudette |
| Countdown | `../examples/countdown.icm` | 32 | 8-bit decrement counter with zero-detect | Claudette |

## Neural

| Model | File | Cells | Description | Author |
|:------|:-----|------:|:------------|:-------|
| LIF Neuron | `../examples/lif_neuron.icm` | 5 | Leaky integrate-and-fire, 1-bit model (5 cells) | Claudette |
| LIF Cascade | `../examples/lif_cascade.icm` | 15 | 3-neuron spike cascade, zero routing overhead | Claudette |

## Signal Processing

| Model | File | Cells | Description | Author |
|:------|:-----|------:|:------------|:-------|
| *(none yet)* | | | | |

## Cryptography

| Model | File | Cells | Description | Author |
|:------|:-----|------:|:------------|:-------|
| *(none yet)* | | | | |

## OS Primitives

| Model | File | Cells | Description | Author |
|:------|:-----|------:|:------------|:-------|
| *(none yet)* | | | | |

## Community Contributed

| Model | File | Cells | Description | Author |
|:------|:-----|------:|:------------|:-------|
| *(open for contributions)* | | | | |

---

*Index last updated: 2026-05-11*
