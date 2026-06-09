"""
cell_format.py — Format Definition System for UniCell Frontends
===============================================================
A format definition is a design-time contract that describes how data is
represented internally across cells, what operations are valid within that
representation, and how to translate at the boundary to/from external data.

The pattern was discovered in MIF (MathTrix Internal Float):
  - External: IEEE-754 32-bit float
  - Internal: two 32-bit cells (control + mantissa), split for efficient arithmetic
  - Boundary: MIF_UNPACK (external → internal) / MIF_PACK (internal → external)
  - Benefit: exponent compare is a nibble read; mantissa untouched for routing

This module generalises that pattern. Any domain can define its own compact
internal representation. The cells themselves are unchanged — NOR universal,
always. The format is a layer above the cells.

Examples:
---------
  MIF        — IEEE-754 split into control+mantissa pair. Exponent arithmetic
               fast because exponent lives alone in control cell nibbles.

  DNA_4Base  — nucleotides packed 2 bits per base (A=00 T=01 G=10 C=11),
               16 bases per 32-bit word. Complement is XOR with 0b11.
               Window operations slide over packed words.

  BCD_Digit  — decimal digits packed 4 bits per digit (BCD), 8 per word.
               Addition with carry handled in nibble arithmetic.

  Amino20    — 20 standard amino acids packed 5 bits per residue, 6 per word.
               Codon→amino acid via preloaded LUT in cells.

  ChessBoard — 13 piece types (6 × 2 colours + empty) packed 4 bits per square,
               8 squares per word. Legal move generation as tile operations.

The format definition tells:
  1. How data is packed into cells (bits per symbol, cells per value)
  2. What LUT translates external ↔ internal
  3. Which tiles are valid within this format
  4. What constitutes an invalid cell value
  5. Where the boundary tiles are

Model library uses this to:
  - Validate tile placement at design time (wrong tile for format → error)
  - Auto-suggest compatible tiles in the Composer
  - Label PTT output with format metadata so deployed servers know how to decode

Architecture:
-------------
    External data (string, float, int, ...)
          ↓  boundary_in tile (PACK/ENCODE)
    Internal cell representation
          ↓  valid_tiles only
    Internal cell representation
          ↓  boundary_out tile (UNPACK/DECODE)
    External data

Usage:
------
    from cell_format import FormatDefinition, FormatRegistry

    # Use a built-in format
    reg = FormatRegistry.get_default()
    mif = reg.get("MIF")
    dna = reg.get("DNA_4Base")

    # Validate a tile against a format
    ok, reason = mif.validate_tile("MIF_ADD")   # → (True, "")
    ok, reason = mif.validate_tile("DNA_MATCH") # → (False, "tile not in MIF format")

    # Encode external data to internal representation
    packed = dna.encode("ATCG")   # → list of cell values

    # Define a new format
    @FormatRegistry.register
    class Protein_Amino20(FormatDefinition):
        name             = "Amino20"
        description      = "20 standard amino acids, 5 bits per residue"
        domain           = "BioTrix"
        bits_per_symbol  = 5
        symbols_per_word = 6      # 30 bits used, 2 bits padding
        cell_words       = 1      # one 32-bit cell per 6 residues
        boundary_in      = "AMINO_PACK"
        boundary_out     = "AMINO_UNPACK"
        symbol_lut = {
            "A":0,"R":1,"N":2,"D":3,"C":4,"Q":5,"E":6,"G":7,"H":8,"I":9,
            "L":10,"K":11,"M":12,"F":13,"P":14,"S":15,"T":16,"W":17,"Y":18,"V":19,
        }
        valid_tiles = ["AMINO_MATCH","AMINO_WINDOW","AMINO_HYDROPHOBIC","AMINO_CHARGE"]
        constraints = {"symbol_range": (0, 19), "padding_bits": 2}
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Any
import math


# ── Base class ────────────────────────────────────────────────────────────────

class FormatDefinition:
    """
    Base class for all UniCell internal data formats.

    Subclass and set class attributes to define a new format.
    Register with FormatRegistry to make it available to the model library
    and Composer.

    Required attributes:
        name             : str   — unique format name (e.g. "MIF", "DNA_4Base")
        description      : str   — one-line description
        domain           : str   — which frontend domain uses this (e.g. "MathTrix")
        bits_per_symbol  : int   — bits used per symbol in packed representation
        symbols_per_word : int   — symbols packed into one 32-bit cell word
        cell_words       : int   — cell words per logical value (MIF=2, DNA=1)
        boundary_in      : str   — tile name for external→internal conversion
        boundary_out     : str   — tile name for internal→external conversion
        valid_tiles      : list  — tile names valid within this format
        symbol_lut       : dict  — {external_symbol: internal_code} or None

    Optional:
        constraints      : dict  — validation rules (symbol_range, padding, etc.)
        pack_order       : str   — "lsb_first" or "msb_first" (default: lsb_first)
        notes            : str   — extended documentation
    """

    # Required — subclass must set these
    name:             str  = ""
    description:      str  = ""
    domain:           str  = "General"
    bits_per_symbol:  int  = 1
    symbols_per_word: int  = 32
    cell_words:       int  = 1
    boundary_in:      str  = ""
    boundary_out:     str  = ""
    valid_tiles:      list = []
    symbol_lut:       dict = None   # None = numeric, no LUT needed

    # Optional
    constraints:      dict = {}
    pack_order:       str  = "lsb_first"
    notes:            str  = ""

    # ── Validation ────────────────────────────────────────────────────────────

    def validate_tile(self, tile_name: str) -> tuple[bool, str]:
        """
        Check whether a tile is valid within this format.
        Returns (ok, reason). reason is "" when ok.
        """
        if tile_name in (self.boundary_in, self.boundary_out):
            return True, ""
        if tile_name in self.valid_tiles:
            return True, ""
        return False, (
            f"Tile '{tile_name}' is not valid in format '{self.name}'. "
            f"Valid tiles: {self.boundary_in}, {self.boundary_out}, "
            f"{', '.join(self.valid_tiles[:5])}{'...' if len(self.valid_tiles)>5 else ''}"
        )

    def validate_symbol(self, symbol) -> tuple[bool, str]:
        """Check whether a symbol is valid for this format."""
        if self.symbol_lut is not None:
            if symbol not in self.symbol_lut:
                return False, f"Symbol '{symbol}' not in {self.name} LUT"
            return True, ""
        r = self.constraints.get("symbol_range")
        if r is not None:
            lo, hi = r
            if not (lo <= int(symbol) <= hi):
                return False, f"Symbol {symbol} out of range [{lo},{hi}] for {self.name}"
        return True, ""

    # ── Encoding ──────────────────────────────────────────────────────────────

    def encode(self, data) -> list[int]:
        """
        Pack external data into a list of 32-bit cell word values.

        data: string (for LUT formats) or list of ints (for numeric formats)
        Returns: list of int, one per cell word needed.

        Example:
            dna = FormatRegistry.get_default().get("DNA_4Base")
            dna.encode("ATCG ATCG ATCG ATCG")  # 16 bases → 1 word
        """
        if isinstance(data, str):
            symbols = list(data.replace(" ", ""))
        else:
            symbols = list(data)

        # Validate all symbols
        for s in symbols:
            ok, reason = self.validate_symbol(s)
            if not ok:
                raise ValueError(f"encode error: {reason}")

        # Map to codes
        if self.symbol_lut is not None:
            codes = [self.symbol_lut[s] for s in symbols]
        else:
            codes = [int(s) for s in symbols]

        # Pack into 32-bit words
        words = []
        spw = self.symbols_per_word
        bps = self.bits_per_symbol
        for word_idx in range(0, len(codes), spw):
            chunk = codes[word_idx:word_idx + spw]
            word = 0
            for i, code in enumerate(chunk):
                if self.pack_order == "lsb_first":
                    word |= (code & ((1 << bps) - 1)) << (i * bps)
                else:
                    word |= (code & ((1 << bps) - 1)) << ((spw - 1 - i) * bps)
            words.append(word)

        return words

    def decode(self, words: list[int]) -> list:
        """
        Unpack cell word values back to external symbols.
        Inverse of encode().
        """
        spw = self.symbols_per_word
        bps = self.bits_per_symbol
        mask = (1 << bps) - 1

        codes = []
        for word in words:
            for i in range(spw):
                if self.pack_order == "lsb_first":
                    code = (word >> (i * bps)) & mask
                else:
                    code = (word >> ((spw - 1 - i) * bps)) & mask
                codes.append(code)

        # Reverse LUT if available
        if self.symbol_lut is not None:
            rev = {v: k for k, v in self.symbol_lut.items()}
            return [rev.get(c, f"?{c}") for c in codes]
        return codes

    # ── Metadata ──────────────────────────────────────────────────────────────

    def capacity(self, n_symbols: int) -> dict:
        """Return cell cost for encoding n_symbols."""
        words = math.ceil(n_symbols / self.symbols_per_word)
        cells = words * self.cell_words
        return {
            "symbols":      n_symbols,
            "words":        words,
            "cells":        cells,
            "bits_used":    n_symbols * self.bits_per_symbol,
            "bits_total":   words * 32 * self.cell_words,
            "efficiency":   round(n_symbols * self.bits_per_symbol /
                                  (words * 32 * self.cell_words) * 100, 1),
        }

    def to_dict(self) -> dict:
        """Serialise format definition for model library / PTT metadata."""
        return {
            "name":             self.name,
            "description":      self.description,
            "domain":           self.domain,
            "bits_per_symbol":  self.bits_per_symbol,
            "symbols_per_word": self.symbols_per_word,
            "cell_words":       self.cell_words,
            "boundary_in":      self.boundary_in,
            "boundary_out":     self.boundary_out,
            "valid_tiles":      self.valid_tiles,
            "symbol_lut":       self.symbol_lut,
            "constraints":      self.constraints,
            "pack_order":       self.pack_order,
        }


# ── Built-in format definitions ───────────────────────────────────────────────

class MIF_Format(FormatDefinition):
    """
    MathTrix Internal Float.

    IEEE-754 split into two cells: control (exponent+flags) and mantissa.
    Exponent arithmetic is fast because exponent lives alone in control cell
    nibbles — no decompose tree needed. Mantissa cell untouched for routing
    and compare-only operations.

    This is the reference implementation of the format definition pattern.
    MIF was designed first; the pattern was abstracted from it.
    """
    name             = "MIF"
    description      = "MathTrix Internal Float — IEEE-754 split into control+mantissa pair"
    domain           = "MathTrix"
    bits_per_symbol  = 32     # each cell word is 32 bits
    symbols_per_word = 1
    cell_words       = 2      # control cell + mantissa cell per float value
    boundary_in      = "MIF_UNPACK"
    boundary_out     = "MIF_PACK"
    valid_tiles      = [
        "MIF_ADD", "MIF_SUB", "MIF_MUL", "MIF_DIV", "MIF_SQRT",
        "MIF_MADD", "MIF_ABS", "MIF_NEG", "MIF_MIN", "MIF_MAX",
        "MIF_CMP_EQ", "MIF_CMP_LT", "MIF_CMP_GT",
        "MIF_CMP_LE", "MIF_CMP_GE",
    ]
    symbol_lut = None   # numeric format, not symbol-based
    constraints = {
        "cell_layout": {
            "control": {
                "[31:24]": "exponent (biased-127)",
                "[23]":    "sign",
                "[22]":    "is_nan",
                "[21]":    "is_inf",
                "[20]":    "is_zero",
                "[19:16]": "guard bits",
                "[15:0]":  "unused",
            },
            "mantissa": {
                "[23:0]":  "significand (implicit-1 expanded)",
                "[31:24]": "unused",
            },
        },
        "always_normalised": True,
        "subnormal_handling": "flush_to_zero",  # upgrade to "full" later
    }
    notes = (
        "Boundary cost paid once at MathTrix region entry/exit. "
        "All internal arithmetic runs in MIF format. "
        "LUT initial guesses used in MIF_DIV/SQRT for faster NR convergence."
    )


class DNA_4Base(FormatDefinition):
    """
    DNA nucleotide format.

    Two bits per base — maximally compact. 16 bases per 32-bit cell word.
    Complement is trivially XOR with 0b11 (A↔T, G↔C).
    Hamming distance counts XOR bits in parallel across the bus.
    """
    name             = "DNA_4Base"
    description      = "DNA nucleotides, 2 bits per base (A=00 T=01 G=10 C=11)"
    domain           = "BioTrix"
    bits_per_symbol  = 2
    symbols_per_word = 16     # 16 bases per 32-bit cell word
    cell_words       = 1
    boundary_in      = "DNA_PACK"
    boundary_out     = "DNA_UNPACK"
    valid_tiles      = [
        "DNA_COMPLEMENT",   # XOR each 2-bit pair with 0b11 — A↔T G↔C
        "DNA_MATCH",        # equality of two sequences (1-bit result per base)
        "DNA_HAMMING",      # popcount of mismatches
        "DNA_REVERSE",      # reverse complement
        "DNA_WINDOW_4",     # sliding 4-base (codon) window
        "DNA_WINDOW_8",     # sliding 8-base window
        "DNA_GC_COUNT",     # count G+C bases (G=10 or C=11, bit[1]=1)
    ]
    symbol_lut = {"A": 0b00, "T": 0b01, "G": 0b10, "C": 0b11,
                  "a": 0b00, "t": 0b01, "g": 0b10, "c": 0b11}
    constraints = {
        "symbol_range":  (0, 3),
        "invalid_guard": True,   # values 4-255 are invalid
        "complement_xor": 0b11,  # XOR mask for complement operation
    }
    notes = (
        "GC count: bit[1] of each 2-bit pair is 1 for G and C. "
        "Popcount of odd bits gives GC content directly. "
        "Complement XOR mask 0b11 applied across all 16 bases simultaneously."
    )


class RNA_4Base(FormatDefinition):
    """RNA nucleotide format — same packing as DNA, U replaces T."""
    name             = "RNA_4Base"
    description      = "RNA nucleotides, 2 bits per base (A=00 U=01 G=10 C=11)"
    domain           = "BioTrix"
    bits_per_symbol  = 2
    symbols_per_word = 16
    cell_words       = 1
    boundary_in      = "RNA_PACK"
    boundary_out     = "RNA_UNPACK"
    valid_tiles      = [
        "RNA_COMPLEMENT", "RNA_MATCH", "RNA_HAMMING",
        "RNA_WINDOW_3",   # codon window (3 bases)
        "RNA_GC_COUNT",
    ]
    symbol_lut = {"A": 0b00, "U": 0b01, "G": 0b10, "C": 0b11,
                  "a": 0b00, "u": 0b01, "g": 0b10, "c": 0b11}
    constraints = {"symbol_range": (0, 3), "complement_xor": 0b11}


class BCD_Decimal(FormatDefinition):
    """
    Binary-Coded Decimal.

    4 bits per digit, 8 digits per 32-bit word.
    Nibble arithmetic — add with carry propagation between nibbles.
    Natural for financial, measurement, and display applications.
    """
    name             = "BCD_Decimal"
    description      = "BCD — 4 bits per decimal digit, 8 digits per word"
    domain           = "General"
    bits_per_symbol  = 4
    symbols_per_word = 8
    cell_words       = 1
    boundary_in      = "BCD_PACK"
    boundary_out     = "BCD_UNPACK"
    valid_tiles      = [
        "BCD_ADD",    # nibble addition with carry
        "BCD_SUB",    # nibble subtraction with borrow
        "BCD_CMP",    # digit-by-digit comparison
        "BCD_SHIFT",  # decimal shift (multiply/divide by 10)
    ]
    symbol_lut = {str(i): i for i in range(10)}   # "0"→0 .. "9"→9
    constraints = {
        "symbol_range":  (0, 9),
        "invalid_guard": True,   # values 10-15 are invalid BCD
        "nibble_carry":  True,   # addition must handle nibble carry
    }


class Amino20(FormatDefinition):
    """
    Standard amino acids — 5 bits per residue, 6 per word.

    Codon→amino acid translation via preloaded LUT cells.
    Hydrophobicity and charge properties encoded in tile operations.
    """
    name             = "Amino20"
    description      = "20 standard amino acids, 5 bits per residue, 6 per word"
    domain           = "BioTrix"
    bits_per_symbol  = 5
    symbols_per_word = 6      # 30 bits used, 2 bits padding per word
    cell_words       = 1
    boundary_in      = "AMINO_PACK"
    boundary_out     = "AMINO_UNPACK"
    valid_tiles      = [
        "AMINO_MATCH",        # sequence alignment
        "AMINO_WINDOW",       # sliding window
        "AMINO_HYDROPHOBIC",  # classify residue hydrophobicity
        "AMINO_CHARGE",       # classify residue charge (+/-/0)
        "AMINO_BLOSUM",       # BLOSUM62 substitution score via LUT
    ]
    symbol_lut = {
        "A":0, "R":1, "N":2, "D":3, "C":4, "Q":5, "E":6, "G":7,
        "H":8, "I":9, "L":10,"K":11,"M":12,"F":13,"P":14,"S":15,
        "T":16,"W":17,"Y":18,"V":19,
        # lower case aliases
        "a":0, "r":1, "n":2, "d":3, "c":4, "q":5, "e":6, "g":7,
        "h":8, "i":9, "l":10,"k":11,"m":12,"f":13,"p":14,"s":15,
        "t":16,"w":17,"y":18,"v":19,
    }
    constraints = {
        "symbol_range": (0, 19),
        "padding_bits": 2,
        "invalid_guard": True,
    }


class FixedPoint_Q8_24(FormatDefinition):
    """
    Q8.24 fixed-point — 8 bits integer, 24 bits fraction.

    Two 32-bit cells: integer part and fractional part.
    Mixed fixed-point/float pipelines: use MIF for computation,
    FixedPoint at boundary for integer-domain interfaces.
    """
    name             = "FixedPoint_Q8_24"
    description      = "Q8.24 fixed-point — 8 integer bits, 24 fraction bits"
    domain           = "General"
    bits_per_symbol  = 32
    symbols_per_word = 1
    cell_words       = 2      # integer cell + fraction cell
    boundary_in      = "FIXED_PACK"
    boundary_out     = "FIXED_UNPACK"
    valid_tiles      = [
        "FIXED_ADD",   # fixed-point addition with carry between cells
        "FIXED_SUB",   # fixed-point subtraction
        "FIXED_MUL",   # fixed-point multiply (shifts result)
        "FIXED_CMP",   # comparison
        "FIXED_TO_MIF","FIXED_FROM_MIF",  # conversion to/from MIF
    ]
    symbol_lut = None
    constraints = {
        "integer_bits":  8,
        "fraction_bits": 24,
        "signed":        True,
        "overflow":      "saturate",
    }


# ── Registry ──────────────────────────────────────────────────────────────────

class FormatRegistry:
    """
    Registry of all known format definitions.

    Built-in formats are registered at module load.
    User formats can be added via register() or register_class().

    Usage:
        reg = FormatRegistry.get_default()
        mif = reg.get("MIF")
        all_formats = reg.list()
        bio_formats = reg.list(domain="BioTrix")
    """

    _default: Optional["FormatRegistry"] = None
    _formats: dict[str, FormatDefinition] = {}

    def __init__(self):
        self._formats = {}

    @classmethod
    def get_default(cls) -> "FormatRegistry":
        """Return the singleton default registry, pre-loaded with built-ins."""
        if cls._default is None:
            cls._default = cls()
            cls._default._load_builtins()
        return cls._default

    def _load_builtins(self):
        for fmt_cls in [MIF_Format, DNA_4Base, RNA_4Base,
                        BCD_Decimal, Amino20, FixedPoint_Q8_24]:
            self.register_class(fmt_cls)

    def register_class(self, fmt_cls) -> None:
        """Register a FormatDefinition subclass."""
        instance = fmt_cls()
        if not instance.name:
            raise ValueError(f"Format class {fmt_cls.__name__} has no name")
        self._formats[instance.name] = instance

    def register(self, fmt_cls):
        """Decorator for registering a format definition."""
        self.register_class(fmt_cls)
        return fmt_cls

    def get(self, name: str) -> FormatDefinition:
        """Get format by name. Raises KeyError if not found."""
        if name not in self._formats:
            raise KeyError(
                f"Format '{name}' not registered. "
                f"Available: {list(self._formats.keys())}"
            )
        return self._formats[name]

    def list(self, domain: str = None) -> list[dict]:
        """List all registered formats, optionally filtered by domain."""
        fmts = list(self._formats.values())
        if domain:
            fmts = [f for f in fmts if f.domain == domain]
        return [f.to_dict() for f in fmts]

    def domains(self) -> list[str]:
        """All domains with registered formats."""
        return sorted(set(f.domain for f in self._formats.values()))

    def validate_model(self, model: dict) -> list[str]:
        """
        Validate a model dict against its declared format.

        model must have:
          "format": format name (optional — skips validation if absent)
          "tiles":  list of tile names used

        Returns list of validation errors (empty = valid).
        """
        fmt_name = model.get("format")
        if not fmt_name:
            return []   # no format declared, no validation

        try:
            fmt = self.get(fmt_name)
        except KeyError as e:
            return [str(e)]

        errors = []
        for tile in model.get("tiles", []):
            ok, reason = fmt.validate_tile(tile)
            if not ok:
                errors.append(reason)
        return errors


# ── Demo ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    reg = FormatRegistry.get_default()

    print("⬡ UniCell Format Registry")
    print("=" * 50)
    print(f"\nRegistered formats ({len(reg._formats)}):")
    for name, fmt in reg._formats.items():
        print(f"  {name:<22} [{fmt.domain:<10}] {fmt.description}")

    print("\n" + "─" * 50)
    print("DNA_4Base encoding:")
    dna = reg.get("DNA_4Base")
    seq = "ATCGATCGATCGATCG"   # 16 bases = exactly 1 word
    words = dna.encode(seq)
    print(f"  Input:   {seq}")
    print(f"  Packed:  0x{words[0]:08X}  ({len(words)} word)")
    decoded = dna.decode(words)
    print(f"  Decoded: {''.join(decoded)}")
    assert ''.join(decoded).upper() == seq.upper(), "Round-trip failed"
    print(f"  Round-trip: ✓")

    cap = dna.capacity(1000)
    print(f"\n  1000-base sequence needs:")
    print(f"    {cap['words']} words / {cap['cells']} cells")
    print(f"    {cap['efficiency']}% bit efficiency")

    print("\n" + "─" * 50)
    print("MIF format tiles:")
    mif = reg.get("MIF")
    for tile in ["MIF_ADD", "MIF_DIV", "DNA_MATCH", "FIXED_ADD"]:
        ok, reason = mif.validate_tile(tile)
        print(f"  {'✓' if ok else '✗'} {tile:<20} {reason if not ok else ''}")

    print("\n" + "─" * 50)
    print("Amino20 encoding:")
    amino = reg.get("Amino20")
    peptide = "ACDEFG"   # 6 residues = 1 word
    words = amino.encode(peptide)
    print(f"  Input:   {peptide}")
    print(f"  Packed:  0x{words[0]:08X}")
    decoded = amino.decode(words)
    print(f"  Decoded: {''.join(decoded[:6])}")

    print("\n" + "─" * 50)
    print("BCD encoding:")
    bcd = reg.get("BCD_Decimal")
    number = "12345678"   # 8 digits = 1 word
    words = bcd.encode(number)
    print(f"  Input:   {number}")
    print(f"  Packed:  0x{words[0]:08X}")
    decoded = bcd.decode(words)
    print(f"  Decoded: {''.join(decoded)}")

    print("\n" + "─" * 50)
    print("Format domains:")
    for domain in reg.domains():
        fmts = [f["name"] for f in reg.list(domain=domain)]
        print(f"  {domain:<12}: {', '.join(fmts)}")

    print("\nAll demos passed ✓")
