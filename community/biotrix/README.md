# BioTrix

Genomics and proteomics domain for UniCell. Covers DNA, RNA, and amino acid
sequences with compact packed encodings that map naturally to cell word widths.

---

## Formats

### DNA_4Base
2 bits per base (A=00, T=01, G=10, C=11), 16 bases per 32-bit cell word.
Complement is XOR with 0b11 — no arithmetic, purely structural.

### RNA_4Base
Same packing as DNA (A=00, U=01, G=10, C=11). U replaces T.
Transcription (DNA→RNA) is a tile operation, not a bridge — same bit width.

### Amino20
5 bits per residue, 6 residues per 32-bit cell word.
20 standard amino acids encoded 0–19. Codon→amino acid translation via
preloaded LUT cells (64-entry codon table, 3-base window input).

---

## Available Tiles

### DNA_4Base tiles
| Tile | Operation | Notes |
|------|-----------|-------|
| `DNA_COMPLEMENT` | XOR each 2-bit pair with 0b11 | A↔T, G↔C |
| `DNA_MATCH` | equality per base | 1-bit result per position |
| `DNA_HAMMING` | popcount of mismatches | counts differing bases |
| `DNA_REVERSE` | reverse base order | word-order + intra-word reversal |
| `DNA_WINDOW_4` | sliding 4-base (codon) window | feeds codon→amino LUT |
| `DNA_WINDOW_8` | sliding 8-base window | motif search |
| `DNA_GC_COUNT` | count G+C bases | bit[1]=1 for G and C |

### Amino20 tiles
| Tile | Operation | Notes |
|------|-----------|-------|
| `AMINO_HYDROPHOB` | hydrophobicity score lookup | Kyte-Doolittle scale |
| `AMINO_CHARGE` | charge at pH 7.4 | +1/0/-1 per residue |
| `AMINO_CODON_LUT` | DNA codon → amino acid | 64-entry preloaded table |
| `AMINO_MATCH` | sequence alignment score | identity matrix |

---

## Worked Examples

### 1. DNA Reverse Complement
The reverse complement is the sequence of the antiparallel strand.
For `ATGC` the reverse complement is `GCAT`.

```
Input:  ATGC  (packed: 00 01 10 11)
Step 1: DNA_COMPLEMENT → TACG (XOR each pair: 01 00 11 10)
Step 2: DNA_REVERSE    → GCAT (reverse word order)
Output: GCAT
```

Pipeline: `DNA_COMPLEMENT → DNA_REVERSE`
Validation: `reverse_complement(reverse_complement(seq)) == seq` for all seq.

### 2. GC Content
GC content = (G + C bases) / total bases. Used in primer design and
genome characterisation. G=10 and C=11 both have bit[1]=1 — the count
is a popcount on bit[1] of every 2-bit pair.

```
Input:  ATGCGCAT (8 bases)
DNA_GC_COUNT → 4 (G, C, G, C are bit[1]=1)
GC% = 4/8 = 50%
```

Pipeline: `DNA_GC_COUNT → MIF_DIV (÷ length)`
Model: `community/biotrix/models/gc_content.json`

### 3. Hamming Distance
Count mismatches between two sequences of equal length.
Used in error detection, SNP analysis, sequence similarity.

```
Seq A:  ATGC  (00 01 10 11)
Seq B:  ATTC  (00 01 01 11)
XOR:    0000 0000 1100 0000  → 1 mismatch (position 2: G vs T)
```

Pipeline: `DNA_HAMMING` (takes two inputs, fires mismatch count)
Model: `community/biotrix/models/hamming_distance.json`

### 4. Codon Scan → Amino Acid Translation
Translate a DNA sequence to a protein sequence via the genetic code.
`DNA_WINDOW_4` produces overlapping 3-base codons; `AMINO_CODON_LUT`
maps each codon to its amino acid via a 64-entry preloaded table.

```
Input DNA:  ATG GGT TCA  (Met-Gly-Ser)
WINDOW_4:   ATG → 0b00_01_10 = codon index 6
CODON_LUT:  6 → Met (amino acid index 12)
...
Output:     Met Gly Ser  (Amino20 packed)
```

Pipeline: `DNA_WINDOW_4 → AMINO_CODON_LUT`
Model: `community/biotrix/models/codon_scan.json`

---

## Adding a New BioTrix Model

Your model JSON goes in `community/biotrix/models/`. Minimal example:

```json
{
  "id":          "my_dna_model",
  "name":        "My DNA Model",
  "domain":      "BioTrix",
  "format":      "DNA_4Base",
  "description": "What this model computes",
  "author":      "your_name",
  "version":     "0.1.0",
  "created":     "2026-06-15",
  "tags":        ["dna", "my_tag"],
  "parameters": {
    "length": {"type": "int", "default": 32, "label": "Sequence length (bases)"}
  },
  "pipeline": [
    {"tile": "DNA_COMPLEMENT", "note": "complement each base"},
    {"tile": "DNA_REVERSE",    "note": "reverse the sequence"}
  ],
  "expected_output": "reverse complement (DNA_4Base packed)",
  "validation": "reverse_complement(ATGC) = GCAT"
}
```

Valid tiles are listed in `DNA_4Base.valid_tiles` in `cell_format.py`.
Mixing tiles from different formats (e.g. `DNA_4Base` + `Amino20`) requires
a bridge tile — see the bridge section in `community/README.md`.

---

## Adding a New BioTrix Format

If you need a format not covered here (IUPAC ambiguity codes, codons,
methylation marks, FASTQ quality scores), subclass `FormatDefinition`
in a new file and register it:

```python
from cell_format import FormatDefinition, FormatRegistry

class DNA_IUPAC(FormatDefinition):
    name             = "DNA_IUPAC"
    description      = "IUPAC ambiguity codes, 4 bits per base"
    domain           = "BioTrix"
    bits_per_symbol  = 4     # 4 bits: 16 IUPAC codes
    symbols_per_word = 8     # 8 bases per 32-bit word
    cell_words       = 1
    boundary_in      = "IUPAC_PACK"
    boundary_out     = "IUPAC_UNPACK"
    valid_tiles      = ["IUPAC_MATCH", "IUPAC_EXPAND"]
    symbol_lut       = {"A": 0b0001, "C": 0b0010, "G": 0b0100, "T": 0b1000,
                        "R": 0b0101, "Y": 0b1010, "N": 0b1111}  # etc.

FormatRegistry.get_default().register_class(DNA_IUPAC)
```

---

## Bridge Connections

BioTrix connects to ChemTrix and PhysTrix via built-in bridges:

| Bridge | Connection | Confidence |
|--------|-----------|-----------|
| `Bridge_DNA_to_Amino` | DNA_4Base → Amino20 | 1.0 (genetic code) |
| `Bridge_DNA_to_Chem` | DNA_4Base → ChemTrix | 0.9 (nucleotide chemistry) |
| `Bridge_Amino_to_Chem` | Amino20 → ChemTrix | 0.85 (residue formulas) |
| `Bridge_Chem_to_DNA` | ChemTrix → DNA_4Base | 0.9 (nucleotide synthesis) |

These are auto-discovered by the Region Connector. Connect a BioTrix
output port to a ChemTrix input and the bridge selector will offer them.

---

## Future Idea: a Physical Write-Out Bridge (noted 2026-07-12, not started)

BioTrix currently covers the DESIGN/computation layer only -- representing
and manipulating DNA/RNA/amino sequences digitally inside the fabric
(packing, complement, Hamming, codon LUTs). It has no physical write-out path
of its own, the same way SensorTrix/NetTrix don't compute anything by
themselves either -- they're bridges to the real world sitting on the other
side of a compute domain.

Worth remembering as a future direction: real hardware now exists that could
plausibly serve as exactly that bridge on BioTrix's side. Harvard (Ham lab,
SEAS) published a CMOS chip with 256 independently-addressable ring-electrode
sites that synthesizes real DNA in parallel via localized electrochemical pH
control -- 64 distinct sequences synthesized simultaneously in the reported
demo, water-based enzymatic chemistry rather than solvent-heavy phosphoramidite
synthesis (Jung, Jung et al., *"Parallel enzymatic DNA synthesis using a
semiconductor chip,"* Nature Electronics, 2026, DOI: 10.1038/s41928-026-01662-9).
The relationship would be CAD-to-3D-printer, not a merge -- BioTrix computes a
sequence digitally, a bridge like this would be what eventually writes it into
an actual physical molecule. Not started, no concrete plan yet -- just worth
keeping in mind, since it fits the same design→fabrication handoff pattern
already established elsewhere in the Trix ecosystem's bridges to physical
hardware.

---

## Running the Models

```python
from community.biotrix.format import DNA_4Base  # registers on import
from unicell_model_library import ModelLibrary

lib = ModelLibrary()
result = lib.run("dna_complement", {"sequence": "ATGCATGC"})
print(result)
```

Or via the server: start `unicell_server.py` and the BioTrix models
appear automatically in the browser frontend under the BioTrix domain.

---

*See also:*
- `cell_format.py` — DNA_4Base, RNA_4Base, Amino20 class definitions
- `community/README.md` — contribution guide and bridge tile reference
- `docs/FORMAT_DEFINITION_GUIDE.md` — how to write a new format
