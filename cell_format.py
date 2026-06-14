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

    # What this format's tiles produce and consume — for bridge validation.
    # produces: {concept: [tile_names_that_output_this]}
    # consumes: {concept: [tile_names_that_accept_this_as_input]}
    # Concepts are physical quantities: "temperature","mass","rate","count"...
    # The bridge validator checks: source.produces[X] ∩ target.consumes[X] ≠ ∅
    produces:  dict = {}
    consumes:  dict = {}

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
        "MIF_ADD", "MIF_SUB", "MIF_MUL", "MIF_DIV", "MIF_RECIP", "MIF_SQRT", "MIF_RSQRT",
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
    produces = {
        "base_sequence":    ["DNA_COMPLEMENT", "DNA_REVERSE"],
        "match_result":     ["DNA_MATCH", "DNA_HAMMING"],
        "gc_count":         ["DNA_GC_COUNT"],
        "codon":            ["DNA_WINDOW_4"],
        "base_count":       ["DNA_GC_COUNT", "DNA_MATCH"],
    }
    consumes = {
        "base_sequence":    ["DNA_COMPLEMENT", "DNA_MATCH", "DNA_HAMMING",
                             "DNA_REVERSE", "DNA_WINDOW_4", "DNA_WINDOW_8"],
        "mutation_prob":    ["DNA_WINDOW_4", "DNA_MATCH"],  # from mutagen
        "temperature":      ["DNA_GC_COUNT"],  # denaturation state
    }


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
    produces = {
        "residue_sequence": ["AMINO_MATCH", "AMINO_WINDOW"],
        "hydrophobicity":   ["AMINO_HYDROPHOBIC"],
        "charge":           ["AMINO_CHARGE"],
        "substitution_score": ["AMINO_BLOSUM"],
        "partition_coeff":  ["AMINO_HYDROPHOBIC"],  # hydrophobicity→partitioning
    }
    consumes = {
        "residue_sequence": ["AMINO_MATCH", "AMINO_WINDOW", "AMINO_HYDROPHOBIC",
                             "AMINO_CHARGE", "AMINO_BLOSUM"],
        "codon":            ["AMINO_MATCH"],  # from DNA codon translation
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


# ── Chemistry format ─────────────────────────────────────────────────────────

class Chemistry_Element(FormatDefinition):
    """
    Chemical element format — periodic table as a compact LUT.

    8 bits per element code, 4 elements per 32-bit cell word.
    The code IS the atomic number for standard elements.
    Properties (density, mass, valence, electronegativity) are NOT stored
    in cells — they live in the fabric as preloaded-A constants, keyed
    by atomic number. The cell holds the code; the fabric holds the lookup.

    Code space (8 bits = 256 values):
      0       : empty / vacuum
      1-118   : standard elements (H=1 .. Og=118), code = atomic number
      119-127 : user-defined (isotopes, pseudo-atoms, custom species)
      128-255 : molecular groups (H2O=128, CO2=129, NH3=130, ...)

    Symbols are human aliases for the code — H, He, Li, etc.
    Single-letter symbols (H, C, N, O, S, P, ...) or two-letter (He, Li, ...).

    Why 8-bit over 7-bit:
      - Byte-aligned: trivial masking with 0xFF
      - Room for 137 molecular groups (128-255)
      - Simple nibble arithmetic for valence checks
      - No bit-packing overhead at boundary

    Property LUT (preloaded at configure time):
      Each property is a separate tile that reads atomic_number → property_value
      using the preloaded-A pattern. No memory access — values in cell registers.
      Properties expand as needed — density, mass, valence, electronegativity,
      melting point, oxidation states, group, period.
    """
    name             = "Chemistry_Element"
    description      = "Periodic table elements, 8-bit atomic number, 4 per word"
    domain           = "ChemTrix"
    bits_per_symbol  = 8
    symbols_per_word = 4
    cell_words       = 1
    boundary_in      = "CHEM_PACK"
    boundary_out     = "CHEM_UNPACK"
    valid_tiles      = [
        # Composition
        "CHEM_BOND",           # form bond between two elements (valence check)
        "CHEM_UNBOND",         # break bond
        "CHEM_VALENCE",        # look up valence electrons (preloaded LUT)
        # Properties (all LUT-based — atomic number → property value)
        "CHEM_MASS",           # atomic mass lookup
        "CHEM_DENSITY",        # density lookup
        "CHEM_ELECTRONEGATIVITY", # Pauling electronegativity
        "CHEM_GROUP",          # periodic table group (1-18)
        "CHEM_PERIOD",         # periodic table period (1-7)
        # Reactions
        "CHEM_OXIDISE",        # apply oxidation state
        "CHEM_REDUCE",         # apply reduction
        "CHEM_MATCH",          # element equality
        "CHEM_IS_METAL",       # metal/nonmetal classification
        "CHEM_IS_NOBLE",       # noble gas check (group 18)
        # Molecular groups
        "CHEM_MOLECULE_PACK",  # pack formula into molecular group code
        "CHEM_MOLECULE_UNPACK",# expand molecular group code to elements
    ]
    symbol_lut = {
        # Period 1
        "H":1,   "He":2,
        # Period 2
        "Li":3,  "Be":4,  "B":5,   "C":6,   "N":7,   "O":8,   "F":9,   "Ne":10,
        # Period 3
        "Na":11, "Mg":12, "Al":13, "Si":14, "P":15,  "S":16,  "Cl":17, "Ar":18,
        # Period 4
        "K":19,  "Ca":20, "Sc":21, "Ti":22, "V":23,  "Cr":24, "Mn":25, "Fe":26,
        "Co":27, "Ni":28, "Cu":29, "Zn":30, "Ga":31, "Ge":32, "As":33, "Se":34,
        "Br":35, "Kr":36,
        # Period 5
        "Rb":37, "Sr":38, "Y":39,  "Zr":40, "Nb":41, "Mo":42, "Tc":43, "Ru":44,
        "Rh":45, "Pd":46, "Ag":47, "Cd":48, "In":49, "Sn":50, "Sb":51, "Te":52,
        "I":53,  "Xe":54,
        # Period 6
        "Cs":55, "Ba":56,
        "La":57, "Ce":58, "Pr":59, "Nd":60, "Pm":61, "Sm":62, "Eu":63, "Gd":64,
        "Tb":65, "Dy":66, "Ho":67, "Er":68, "Tm":69, "Yb":70, "Lu":71,
        "Hf":72, "Ta":73, "W":74,  "Re":75, "Os":76, "Ir":77, "Pt":78, "Au":79,
        "Hg":80, "Tl":81, "Pb":82, "Bi":83, "Po":84, "At":85, "Rn":86,
        # Period 7
        "Fr":87, "Ra":88,
        "Ac":89, "Th":90, "Pa":91, "U":92,  "Np":93, "Pu":94, "Am":95, "Cm":96,
        "Bk":97, "Cf":98, "Es":99, "Fm":100,"Md":101,"No":102,"Lr":103,
        "Rf":104,"Db":105,"Sg":106,"Bh":107,"Hs":108,"Mt":109,"Ds":110,"Rg":111,
        "Cn":112,"Nh":113,"Fl":114,"Mc":115,"Lv":116,"Ts":117,"Og":118,
        # Empty
        "_":0, "":0,
        # Common molecular groups (extensible)
        "H2O":128, "CO2":129, "NH3":130, "CH4":131, "O2":132,
        "N2":133,  "HCl":134, "NaCl":135,"H2SO4":136,"HNO3":137,
    }
    constraints = {
        "symbol_range":    (0, 255),
        "element_range":   (1, 118),   # standard elements
        "group_range":     (128, 255), # molecular groups
        "invalid_guard":   False,      # codes 119-127 are user-defined, not invalid
        "byte_aligned":    True,
    }
    produces = {
        "mass":          ["CHEM_MASS"],
        "valence":       ["CHEM_VALENCE"],
        "density":       ["CHEM_DENSITY"],
        "group":         ["CHEM_GROUP"],
        "period":        ["CHEM_PERIOD"],
        "bond":          ["CHEM_BOND"],
        "reaction_rate": ["CHEM_OXIDISE", "CHEM_REDUCE"],
        "partition_coeff": ["CHEM_BOND"],
        "mutation_prob":  ["CHEM_MUTAGEN_TO_DNA"],  # chemical → DNA mutation
    }
    consumes = {
        "element_code":  ["CHEM_BOND", "CHEM_UNBOND", "CHEM_VALENCE",
                          "CHEM_MASS", "CHEM_DENSITY", "CHEM_GROUP"],
        "temperature":   ["CHEM_OXIDISE", "CHEM_REDUCE"],  # Arrhenius
        "partition_coeff": ["CHEM_BOND"],  # from amino acid hydrophobicity
    }
    notes = (
        "Property LUTs (density, mass, valence, electronegativity) are "
        "separate tiles that use the preloaded-A pattern — atomic number "
        "is the address, property value is preloaded into the cell. "
        "No memory access; values live in the fabric at configure time. "
        "Molecular group codes 128-255 are extensible — add entries to "
        "symbol_lut and register corresponding CHEM_MOLECULE_* tiles. "
        "Isotopes: use codes 119-127 with user_lut extension."
    )

    # Property tables — preloaded into fabric at configure time
    # Format: atomic_number → value (scaled integer for cell representation)
    # These feed directly into the preloaded-A pattern for CHEM_MASS etc.

    ATOMIC_MASS = {
        1:1,   2:4,   3:7,   4:9,   5:11,  6:12,  7:14,  8:16,  9:19,  10:20,
        11:23, 12:24, 13:27, 14:28, 15:31, 16:32, 17:35, 18:40, 19:39, 20:40,
        26:56, 29:64, 30:65, 47:108,79:197,82:207,92:238,  # key metals
    }  # rounded to nearest integer, extend as needed

    VALENCE = {
        1:1,  2:0,  3:1,  4:2,  5:3,  6:4,  7:3,  8:2,  9:1,  10:0,
        11:1, 12:2, 13:3, 14:4, 15:3, 16:2, 17:1, 18:0,
        19:1, 20:2, 26:2, 29:1, 30:2,  # common metals
    }

    GROUP = {  # periodic table group 1-18
        1:1,  2:18, 3:1,  4:2,  5:13, 6:14, 7:15, 8:16, 9:17, 10:18,
        11:1, 12:2, 13:13,14:14,15:15,16:16,17:17,18:18,
        19:1, 20:2, 26:8, 29:11,30:12,
    }

    def property_lut(self, prop: str) -> dict:
        """
        Return the property LUT for preloading into the fabric.
        The returned dict maps atomic_number → cell_value.
        Used by CHEM_MASS, CHEM_VALENCE, CHEM_GROUP tiles at configure time.
        """
        luts = {
            "mass":    self.ATOMIC_MASS,
            "valence": self.VALENCE,
            "group":   self.GROUP,
        }
        if prop not in luts:
            raise KeyError(f"Unknown property '{prop}'. Available: {list(luts)}")
        return luts[prop]

    def formula_to_codes(self, formula: str) -> list[int]:
        """
        Parse a chemical formula string to a list of element codes.
        Simple parser - no parentheses, handles H2O, CH4, NaCl etc.
        """
        import re
        tokens = re.findall(r'([A-Z][a-z]?)(\d*)', formula)
        codes = []
        for symbol, count in tokens:
            if not symbol:
                continue
            n = int(count) if count else 1
            code = self.symbol_lut.get(symbol, 0)
            codes.extend([code] * n)
        return codes


# ── Physics format ───────────────────────────────────────────────────────────

class SI_Physics(FormatDefinition):
    """
    SI unit system with physical constants.

    Values stored as MIF pairs internally (reuses MIF).
    Unit dimensions stored as 7×4-bit exponent vector in a third cell:
      [m, kg, s, A, K, mol, cd] exponents packed 4 bits each (signed -7..+7)
    This enables dimensional analysis at compile time — SI_CHECK tile
    validates unit consistency before the computation runs.

    Physical constants preloaded into cells at configure time.
    """
    name             = "SI_Physics"
    description      = "SI units with dimensional analysis and physical constants"
    domain           = "PhysTrix"
    bits_per_symbol  = 4       # 4 bits per unit exponent (-7 to +7)
    symbols_per_word = 7       # 7 SI base dimensions per word (28 bits used)
    cell_words       = 3       # value_ctrl, value_mant, unit_dimensions
    boundary_in      = "SI_PACK"
    boundary_out     = "SI_UNPACK"
    valid_tiles      = [
        "SI_ADD",        # add quantities (requires matching units)
        "SI_SUB",        # subtract quantities
        "SI_MUL",        # multiply (adds unit exponents)
        "SI_DIV",        # divide (subtracts unit exponents)
        "SI_SQRT",       # square root (halves unit exponents)
        "SI_CONVERT",    # unit conversion via preloaded factor cell
        "SI_CHECK",      # dimensional consistency → 1-bit result
        "SI_CONST_C",    # emit speed of light (preloaded)
        "SI_CONST_G",    # emit gravitational constant
        "SI_CONST_H",    # emit Planck constant
        "SI_CONST_KB",   # emit Boltzmann constant
        "SI_CONST_NA",   # emit Avogadro number
        "SI_CONST_E",    # emit elementary charge
        # Bridge tiles — cross-domain connections
        "SI_HAWKING_TEMP",   # T = ℏc³/8πGMkB  gravity→thermal  confidence=1.0
        "SI_SCHWARZSCHILD",  # rs = 2GM/c²      mass→radius      confidence=1.0
        "SI_STEFAN_BOLTZMANN", # P = σAT⁴       thermal→radiated confidence=1.0
        "SI_ARRHENIUS",      # k = Ae^(-Ea/RT)  thermal→chemical confidence=1.0
    ]
    symbol_lut = None
    # Physical constants — preloaded into fabric at configure time.
    # Values scaled to MIF format. Each constant occupies one preloaded cell.
    # Address is fixed; value is loaded by the configure transaction.
    CONSTANTS = {
        "c":         299_792_458,    # speed of light, m/s (exact)
        "G":         6.674_30e-11,   # gravitational constant, m³/kg/s²
        "h":         6.626_070e-34,  # Planck constant, J·s
        "hbar":      1.054_572e-34,  # reduced Planck, J·s
        "kB":        1.380_649e-23,  # Boltzmann constant, J/K (exact)
        "NA":        6.022_141e23,   # Avogadro number, mol⁻¹ (exact)
        "e":         1.602_177e-19,  # elementary charge, C (exact)
        "epsilon0":  8.854_188e-12,  # vacuum permittivity, F/m
        "mu0":       1.256_637e-6,   # vacuum permeability, H/m
        "R":         8.314_463,      # gas constant, J/mol/K (exact)
        "sigma":     5.670_374e-8,   # Stefan-Boltzmann, W/m²/K⁴
        "me":        9.109_384e-31,  # electron mass, kg
        "mp":        1.672_622e-27,  # proton mass, kg
        "mn":        1.674_927e-27,  # neutron mass, kg
        "alpha":     7.297_353e-3,   # fine structure constant (dimensionless)
        "a0":        5.291_772e-11,  # Bohr radius, m
        "Ry":        2.179_872e-18,  # Rydberg energy, J
    }
    constraints = {
        "dimensional_check":   True,
        "unit_exponent_range": (-7, 7),
        "codata_year":         2018,   # CODATA 2018 values
    }
    produces = {
        "temperature":   ["SI_ADD", "SI_MUL", "SI_HAWKING_TEMP",
                          "SI_FOURIER_HEAT", "SI_NAVIER_STOKES_TEMP"],
        "mass":          ["SI_MUL", "SI_DIV"],
        "energy":        ["SI_MUL", "SI_ADD"],
        "velocity":      ["SI_MUL", "SI_ADD"],
        "power":         ["SI_STEFAN_BOLTZMANN"],
        "rate":          ["SI_ARRHENIUS"],
        "length":        ["SI_SCHWARZSCHILD", "SI_MUL"],
        "viscosity":     ["SI_MUL", "SI_DIV"],   # kinematic/dynamic viscosity
    }
    consumes = {
        "temperature":   ["SI_ADD", "SI_MUL", "SI_STEFAN_BOLTZMANN",
                          "SI_ARRHENIUS", "SI_CHECK"],
        "mass":          ["SI_HAWKING_TEMP", "SI_SCHWARZSCHILD", "SI_MUL"],
        "energy":        ["SI_MUL", "SI_ADD", "SI_CHECK"],
        "length":        ["SI_MUL", "SI_CHECK"],
        "base_count":    ["SI_TEMP_TO_DNA_STATE"],  # GC count → Tm
    }
    notes = (
        "Constants are CODATA 2018 values. Reconfigurable at runtime — "
        "update a constant by rewriting the preloaded cell without "
        "recompiling the cell map. "
        "Dimensional analysis: SI_CHECK tile reads unit_dimensions cell "
        "and validates exponent vector before computation. "
        "Catches m + kg errors at design time, not at runtime."
    )


class Finance_Currency(FormatDefinition):
    """
    Financial instrument and currency format.

    8-bit code per currency/instrument, 4 per word.
    Values stored as Q16.16 fixed-point (separate cell).
    Operations include compound interest, discounting, yield calculation.

    Constants (risk-free rate, basis points) are reconfigured daily
    without recompiling cell maps — preloaded-A pattern makes this free.
    """
    name             = "Finance_Currency"
    description      = "Currency codes and financial instruments, 8-bit, 4 per word"
    domain           = "FinTrix"
    bits_per_symbol  = 8
    symbols_per_word = 4
    cell_words       = 2       # code cell + Q16.16 value cell
    boundary_in      = "FIN_PACK"
    boundary_out     = "FIN_UNPACK"
    valid_tiles      = [
        "FIN_CONVERT",        # currency conversion via rate LUT
        "FIN_COMPOUND",       # compound interest: P*(1+r)^n
        "FIN_DISCOUNT",       # present value: FV/(1+r)^n
        "FIN_YIELD",          # yield to maturity
        "FIN_SPREAD",         # basis point spread calculation
        "FIN_MARK_TO_MARKET", # mark portfolio to current prices
        "FIN_DURATION",       # Macaulay/modified duration
        "FIN_VaR",            # Value at Risk (parametric)
        "FIN_CMP_RATE",       # compare rates
    ]
    symbol_lut = {
        # Major currencies (ISO 4217 inspired, compact codes)
        "USD":1,  "EUR":2,  "GBP":3,  "JPY":4,  "CHF":5,
        "AUD":6,  "CAD":7,  "NZD":8,  "CNY":9,  "HKD":10,
        "SGD":11, "NOK":12, "SEK":13, "DKK":14, "MXN":15,
        "BRL":16, "INR":17, "KRW":18, "TWD":19, "ZAR":20,
        # Instrument types (128-200)
        "BOND":128, "EQUITY":129, "FUTURE":130, "OPTION":131,
        "SWAP":132, "FWD":133,    "CDS":134,    "ETF":135,
        "REPO":136, "TBILL":137,  "NOTE":138,   "GILT":139,
    }
    # Market constants — reconfigured daily, no recompile needed
    CONSTANTS = {
        "risk_free_rate":  0.05,    # 5% p.a. (updated daily)
        "basis_point":     0.0001,  # 1 bp = 0.01%
        "days_per_year":   365,
        "trading_days":    252,
        "settlement_days": 2,       # T+2 standard
    }
    constraints = {
        "symbol_range":  (1, 200),
        "byte_aligned":  True,
        "value_format":  "Q16.16",  # 16 integer + 16 fraction bits
    }
    notes = (
        "Market constants (risk_free_rate etc.) are reconfigured daily "
        "by writing to preloaded cells — no cell map recompile needed. "
        "This is the preloaded-A pattern applied to live market data. "
        "FIN_COMPOUND uses the risk_free_rate constant cell directly. "
        "Currency conversion rates similarly reconfigured without recompile."
    )


class FlowTrix_D2Q9(FormatDefinition):
    """
    Lattice Boltzmann D2Q9 fluid format.

    The flagship "topology IS computation" demonstration. LBM has two steps:
      COLLIDE  — purely local arithmetic on a site's 9 distribution functions
      STREAM   — each distribution moves one hop to its neighbour in its
                 direction of travel

    On UniCell, STREAM is NOT an operation and does NOT appear in valid_tiles.
    Streaming is the wiring. The fabric topology carries each distribution to
    its neighbour; the format only describes what a site DOES (collide,
    moments, boundary), never where things GO. This is the cleanest validation
    of the format-definition concept itself: format = behaviour, fabric = flow.

    Internal representation — fixed-point, one cell per distribution:
      9 distribution functions f0..f8, each a single Q8.24 fixed-point cell.
      Total 9 cells per lattice site. (A MIF-pair variant would double this to
      18 cells for IEEE-grade precision; for vortex shedding at Re~100-200
      modest fixed-point precision is sufficient and LBM is forgiving there.)
      The precision choice is not cosmetic: fewer cells per site means more
      sites resident in the fabric, which means fewer temporal-blocking swaps,
      which means a lower halo-recompute tax. Precision couples directly to
      the MLUPS-per-watt story.

    Velocity set (D2Q9), index → (ex, ey):
      0:( 0, 0)  rest      4:( 0,-1)         8:( 1,-1)
      1:( 1, 0)            5:( 1, 1)
      2:( 0, 1)            6:(-1, 1)
      3:(-1, 0)            7:(-1,-1)
    The rest population f0 has velocity (0,0): it never streams, it is a
    self-loop on its own cell. 8 of 9 distributions stream to neighbours; 1
    stays put.

    Bounce-back (solid obstacle) is the OPPOSITE-INDEX permutation below: a
    wall cell reflects each incoming distribution back the way it came. On the
    fabric a wall cell and a fluid cell differ ONLY in which neighbour each
    output wire targets — the obstacle geometry is literally the wiring, not
    data a program tests against. Reshaping the obstacle is a reconfiguration,
    not a recompile. Note that bounce-back and streaming share the same
    topological object: the velocity set and its negation.
    """
    name             = "FlowTrix_D2Q9"
    description      = "Lattice Boltzmann D2Q9 — 9 distributions per site, streaming is topology"
    domain           = "FlowTrix"
    bits_per_symbol  = 32      # each distribution is one fixed-point cell word
    symbols_per_word = 1
    cell_words       = 9       # 9 distribution cells per lattice site (Q8.24)
    boundary_in      = "LBM_INIT"     # macroscopic (rho,u) → equilibrium distributions
    boundary_out     = "LBM_MOMENTS"  # distributions → macroscopic (rho,u) for output
    valid_tiles      = [
        "LBM_COLLIDE",        # BGK relaxation: f += (feq - f)/tau
        "LBM_EQUILIBRIUM",    # compute feq from local rho, u
        "LBM_DENSITY",        # rho = sum f_i        (OR-reduction sum tree)
        "LBM_VELOCITY",       # u = (1/rho) sum e_i f_i  (weighted sum)
        "LBM_BOUNCEBACK",     # solid wall: swap each f_i with f_opposite(i)
        "LBM_INLET",          # inflow boundary (prescribed velocity)
        "LBM_OUTLET",         # outflow boundary (zero-gradient)
        "LBM_VORTICITY",      # curl of velocity field — for shedding detection
        # NOTE: there is deliberately NO "LBM_STREAM" tile. Streaming is the
        # fabric topology, not a site operation. Its absence is the point.
    ]
    symbol_lut = None   # numeric format, distributions are fixed-point values

    # D2Q9 lattice constants — preloaded into the cell decode table at
    # configure time (same mechanism as SI_Physics CONSTANTS / preloaded-A).
    # No value travels on the bus; the selector indexes the table.
    WEIGHTS = {
        0: 4/9,
        1: 1/9,  2: 1/9,  3: 1/9,  4: 1/9,
        5: 1/36, 6: 1/36, 7: 1/36, 8: 1/36,
    }
    VELOCITIES = {
        0: ( 0,  0),
        1: ( 1,  0), 2: ( 0,  1), 3: (-1,  0), 4: ( 0, -1),
        5: ( 1,  1), 6: (-1,  1), 7: (-1, -1), 8: ( 1, -1),
    }
    # Opposite-direction permutation. This table IS bounce-back, and is also
    # the streaming wiring's reversal at a wall. Pure topology as a lookup.
    OPPOSITE = {0: 0, 1: 3, 2: 4, 3: 1, 4: 2, 5: 7, 6: 8, 7: 5, 8: 6}
    CS2 = 1/3          # lattice speed of sound squared, cs^2 = 1/3

    constraints = {
        "value_format":   "Q8.24",       # fixed-point per distribution
        "n_distributions": 9,
        "cs2":            "1/3",
        "stability":      "tau > 0.5 required (nu = cs2*(tau-0.5) >= 0)",
        "incompressible_limit": "Mach << 1 (|u| << cs)",
    }
    # Bridge concepts: what FlowTrix produces / consumes across a domain edge.
    produces = {
        "velocity":   ["LBM_VELOCITY"],
        "density":    ["LBM_DENSITY"],
        "vorticity":  ["LBM_VORTICITY"],
        "pressure":   ["LBM_DENSITY"],        # p = cs^2 * rho in LBM
    }
    consumes = {
        "viscosity":  ["LBM_COLLIDE"],        # tau encodes kinematic viscosity
        "velocity":   ["LBM_INLET", "LBM_EQUILIBRIUM"],
        "force":      ["LBM_COLLIDE"],        # body force (e.g. gravity) term
    }
    notes = (
        "Streaming is topology, not a tile — see valid_tiles. "
        "Obstacle = bounce-back wiring (OPPOSITE table), reconfigurable "
        "without recompile. tau <-> viscosity <-> Reynolds is a "
        "FlowTrix->PhysTrix bridge (nu = cs2*(tau-1/2), exact in the "
        "Chapman-Enskog limit). Demo: flow past cylinder at Re~100-200, "
        "validated against the published Strouhal number. Timing is "
        "deterministic: ticks/update = collide pipeline depth + 1 hop stream, "
        "predictable from the compiler before silicon."
    )

    # ── Domain operations (reference Python — single-site, for VM validation) ──
    # These let the format self-validate (mass/momentum conservation, the
    # feq->moments round trip) and provide ground truth the tiles must match.

    def equilibrium(self, rho: float, ux: float, uy: float) -> list:
        """
        Maxwell-Boltzmann equilibrium distributions feq_i for given
        macroscopic density and velocity. This is what LBM_INIT and the
        feq half of LBM_COLLIDE compute.

            feq_i = w_i * rho * [1 + 3(e.u) + 4.5(e.u)^2 - 1.5|u|^2]
        """
        usqr = ux * ux + uy * uy
        feq = []
        for i in range(9):
            ex, ey = self.VELOCITIES[i]
            eu = ex * ux + ey * uy
            feq.append(
                self.WEIGHTS[i] * rho *
                (1.0 + 3.0 * eu + 4.5 * eu * eu - 1.5 * usqr)
            )
        return feq

    def moments(self, f: list) -> tuple:
        """
        Macroscopic moments from the 9 distributions. This is LBM_MOMENTS /
        LBM_DENSITY+LBM_VELOCITY.
            rho = sum f_i
            u   = (1/rho) sum e_i f_i
        Returns (rho, ux, uy).
        """
        rho = sum(f)
        if rho == 0:
            return 0.0, 0.0, 0.0
        ux = sum(self.VELOCITIES[i][0] * f[i] for i in range(9)) / rho
        uy = sum(self.VELOCITIES[i][1] * f[i] for i in range(9)) / rho
        return rho, ux, uy

    def collide(self, f: list, tau: float) -> list:
        """
        One BGK collision step (purely local). LBM_COLLIDE.
            f_i <- f_i + (feq_i - f_i)/tau
        tau is the relaxation time; nu = cs2*(tau - 1/2).
        """
        rho, ux, uy = self.moments(f)
        feq = self.equilibrium(rho, ux, uy)
        return [f[i] + (feq[i] - f[i]) / tau for i in range(9)]

    def bounceback(self, f: list) -> list:
        """
        Full bounce-back at a solid wall. LBM_BOUNCEBACK.
        Each distribution is swapped with its opposite — the OPPOSITE table.
        This is a pure permutation; on the fabric it is wiring, not arithmetic.
        """
        return [f[self.OPPOSITE[i]] for i in range(9)]

    @classmethod
    def viscosity_from_tau(cls, tau: float) -> float:
        """Kinematic viscosity (lattice units) from relaxation time."""
        return cls.CS2 * (tau - 0.5)

    @classmethod
    def reynolds(cls, u_char: float, l_char: float, tau: float) -> float:
        """Reynolds number Re = U L / nu, with nu from tau."""
        nu = cls.viscosity_from_tau(tau)
        if nu <= 0:
            raise ValueError(f"tau={tau} gives non-positive viscosity (need tau>0.5)")
        return u_char * l_char / nu

    @classmethod
    def tau_for_reynolds(cls, re: float, u_char: float, l_char: float) -> float:
        """Inverse: relaxation time tau to hit a target Reynolds number."""
        nu = u_char * l_char / re
        return nu / cls.CS2 + 0.5


class MidiTrix(FormatDefinition):
    """
    MIDI -> spiking input for LIF neurons (a NeuroTrix front-end).  [iteration 1]

    A way to "play music to LIF cells": a MIDI event stream becomes timed input
    current to a tonotopic bank of leaky integrate-and-fire neurons, one input
    line per MIDI note. A note-on injects current into its neuron (scaled by
    velocity); a note-off releases it; the neuron integrates and fires. The
    cells thereby *respond to* the music -- the first, simplest "understanding".

    WHY MIDI FIRST. It is already the shape a spiking network wants: a discrete,
    finite-alphabet, explicitly-timed event stream. No signal-processing front
    end is needed -- a note-on IS a spike, pitch IS an input line, velocity IS a
    current, the delta-times ARE the schedule. MIDI is also a mature, instrument-
    agnostic standard, so the same encoding drives a piano, a flute or a drum kit
    unchanged. That makes it the cleanest on-ramp for others entering the area.

    TONOTOPY IS TOPOLOGY. MIDI note number 0..127 is a log-frequency axis, so the
    pitch->neuron map is a tonotopic layout for free -- the organisation the
    auditory cortex uses. Crucially that map is the FABRIC WIRING, not an
    operation: there is deliberately no MIDI_ROUTE tile, exactly as FlowTrix has
    no LBM_STREAM tile. Which neuron a note drives is where its wire goes.

    FIRST ITERATION -- stated plainly. This encodes notes, velocity and timing:
    the cells learn WHEN and WHICH note. It does NOT model timbre, harmony,
    beating or consonance -- those live in the frequency domain and need a
    spectral / cochlear (FFT / filterbank) front-end. That deeper layer is left
    open BY DESIGN for others to build; note_to_hz() below is the tonotopic
    frequency anchor such a front-end would bridge onto. The LIF dynamics
    themselves belong to NeuroTrix; MidiTrix only produces the drive it consumes.
    """
    name             = "MidiTrix"
    description      = "MIDI events -> timed input current for a tonotopic LIF bank (first iteration)"
    domain           = "MidiTrix"
    bits_per_symbol  = 16     # packed note event: pitch:7 | velocity:7 | on/off:1 | spare:1
    symbols_per_word = 1
    cell_words       = 1      # one event cell; the neuron bank itself is NeuroTrix's cells
    boundary_in      = "MIDI_DECODE"   # raw MIDI message -> (pitch, velocity, on/off)
    boundary_out     = "MIDI_GATE"     # gated per-pitch drive handed to the LIF bank
    valid_tiles      = [
        "MIDI_DECODE",   # unpack a note message into pitch / velocity / on-off
        "MIDI_GAIN",     # velocity (0..127) -> input current (velocity/127 * scale)
        "MIDI_GATE",     # note-on latches the per-pitch drive, note-off releases it
        # NOTE: there is deliberately NO "MIDI_ROUTE" tile. The pitch->neuron
        # tonotopic mapping is the fabric wiring (topology), exactly as FlowTrix
        # streaming is. Which neuron a note drives is where its wire goes, not a
        # value a program computes.
    ]
    symbol_lut = None   # events are numeric (pitch / velocity); see note_to_hz()

    # ── Fixed constants — preloaded in the decode table, never on the bus ──
    A4_HZ         = 440.0   # concert-pitch reference
    A4_NOTE       = 69      # MIDI note number of A4
    EDO           = 12      # twelve-tone equal temperament
    VELOCITY_MAX  = 127     # 7-bit MIDI velocity
    CURRENT_SCALE = 0.5     # full-velocity per-tick input current (tunable)

    constraints = {
        "pitch_range":    "0..127 (MIDI note number)",
        "velocity_range": "0..127 (0 = note-off by convention)",
        "tuning":         "equal temperament, A4 = 440 Hz",
        "input_mode":     "impulse drive into NeuroTrix LIF (current per active note)",
    }
    # MidiTrix is a SOURCE / front-end: it produces the drive NeuroTrix consumes,
    # and consumes nothing on the bus (events enter from outside).
    produces = {
        "input_current":    ["MIDI_GAIN"],    # current handed to LIF neurons
        "spike_input":      ["MIDI_GATE"],    # gated note-on/off as drive
        "pitch_frequency":  ["MIDI_DECODE"],  # note -> Hz, anchor for a freq front-end
    }
    consumes = {}
    notes = (
        "First iteration: notes, velocity, timing -> tonotopic LIF drive. MIDI is "
        "mature and instrument-agnostic, so the same encoding drives any "
        "instrument output -- a clean on-ramp. Tonotopy is topology (no MIDI_ROUTE "
        "tile, as FlowTrix has no LBM_STREAM). Timbre / harmony / consonance are "
        "out of scope and need a spectral (FFT/filterbank) front-end, left open by "
        "design for others; note_to_hz() is the anchor it would bridge onto. LIF "
        "dynamics belong to NeuroTrix."
    )

    # ── Reference Python (VM validation / ground truth) ──
    @classmethod
    def note_to_hz(cls, note: int) -> float:
        """MIDI note number -> frequency (Hz), equal temperament, A4 = 440."""
        return cls.A4_HZ * (2.0 ** ((note - cls.A4_NOTE) / cls.EDO))

    @classmethod
    def velocity_to_current(cls, velocity: int) -> float:
        """MIDI velocity (0..127) -> per-tick input current for the LIF neuron."""
        v = max(0, min(cls.VELOCITY_MAX, velocity))
        return (v / cls.VELOCITY_MAX) * cls.CURRENT_SCALE

    @classmethod
    def pack_event(cls, pitch: int, velocity: int, on: bool) -> int:
        """Pack a note event into the 16-bit symbol (pitch:7 | velocity:7 | on:1)."""
        return (pitch & 0x7F) | ((velocity & 0x7F) << 7) | ((1 if on else 0) << 14)

    @classmethod
    def unpack_event(cls, word: int):
        """Inverse of pack_event -> (pitch, velocity, on)."""
        return (word & 0x7F, (word >> 7) & 0x7F, bool((word >> 14) & 1))


# ── SensorTrix format ─────────────────────────────────────────────────────────

class SensorTrix(FormatDefinition):
    """
    SensorTrix — unified format for all physical sensor inputs.

    The key insight: every physical sensor reduces to (location, amount).

      location — which sensor in the array, which axis, which channel,
                 which contact point. A 16-bit index. Examples:
                   touch:         contact ID (0-15) + axis flag (X=0,Y=1)
                   accelerometer: axis (0=X, 1=Y, 2=Z)
                   magnetometer:  axis (0=X, 1=Y, 2=Z)
                   microphone:    channel (0=left, 1=right, 2..N=array element)
                   temperature:   sensor node ID
                   light/proximity: channel ID
                   pressure/force: contact ID

      amount   — the ADC reading, field strength, pressure, amplitude, lux,
                 acceleration magnitude. A 16-bit unsigned integer, scaled
                 to [0, 65535] by the bridge from the device's native range.

    WIRE ENCODING (32-bit bus word):
      bits 31-16:  amount   (16-bit unsigned, device-scaled)
      bits 15-0:   location (16-bit unsigned, sensor/axis/channel index)

    A sensor ARRAY (stack) is N readings of the same format on N consecutive
    bus addresses, one word per sensor element. The location field carries
    the array index so the fabric can route without needing separate address
    ranges per sensor. Robotics: a 12-DOF arm is 12 readings, one stream.

    VALID TILES:
      SENSOR_UNPACK     — split 32-bit word into location + amount fields
      SENSOR_THRESHOLD  — fire when amount >= preloaded threshold T
      SENSOR_DELTA      — change in amount since preloaded previous reading
      SENSOR_STACK_MAX  — maximum amount across N consecutive readings
      SENSOR_STACK_SUM  — accumulated sum across N readings (mean filter step)

    BRIDGE CONCEPTS:
      produces: amount -> NeuroTrix (amount as LIF drive current)
                location -> any routing tile (address-as-identity)
      consumes: raw_word from SensorBridge on the bus

    The same FormatDefinition covers: touch array, IMU (accel+gyro+mag),
    microphone array, tactile skin, motor encoder array, sonar array,
    any N-channel ADC. A sensor stack IS a sensor array — the same stream,
    the same tiles, the same bridge. Only the device on the host side differs.
    """

    name            = "SensorTrix"
    domain          = "SensorTrix"
    bits_per_symbol = 32          # one (location, amount) word per reading
    boundary_in     = "SENSOR_UNPACK"
    boundary_out    = None        # sensors are source-only; no output conversion

    # No symbol LUT — amount and location are raw integers, not an alphabet.
    # The format is numeric: any 16-bit value is valid for both fields.
    symbol_lut = None

    # Tile names legal in SensorTrix programs
    valid_tiles = [
        "SENSOR_UNPACK",
        "SENSOR_THRESHOLD",
        "SENSOR_DELTA",
        "SENSOR_STACK_MAX",
        "SENSOR_STACK_SUM",
    ]

    # Bridge data flow contracts
    produces = {
        "amount":    ["SENSOR_UNPACK", "SENSOR_THRESHOLD", "SENSOR_DELTA",
                      "SENSOR_STACK_MAX", "SENSOR_STACK_SUM"],
        "location":  ["SENSOR_UNPACK"],
        "threshold_fired": ["SENSOR_THRESHOLD"],
        "delta":     ["SENSOR_DELTA"],
        "stack_max": ["SENSOR_STACK_MAX"],
        "stack_sum": ["SENSOR_STACK_SUM"],
    }

    consumes = {
        "raw_word":  ["SENSOR_UNPACK"],
        "amount":    ["SENSOR_THRESHOLD", "SENSOR_DELTA",
                      "SENSOR_STACK_MAX", "SENSOR_STACK_SUM"],
    }

    notes = (
        "Unified sensor format: every physical input is (location, amount). "
        "A sensor array (stack) is N readings of the same format on N "
        "consecutive bus addresses — location carries the array index. "
        "Robotics 101: a 12-DOF arm is 12 readings, one stream, one format. "
        "Covers: touch, IMU, microphone array, tactile skin, motor encoder, "
        "sonar, any N-channel ADC. Bridge is a thin extension of MouseBridge."
    )

    # ── Encoding helpers ──────────────────────────────────────────────────────

    AMOUNT_SHIFT   = 16
    AMOUNT_MASK    = 0xFFFF
    LOCATION_MASK  = 0xFFFF

    @classmethod
    def pack(cls, location: int, amount: int) -> int:
        """Pack (location, amount) into a 32-bit bus word."""
        return ((amount & cls.AMOUNT_MASK) << cls.AMOUNT_SHIFT) | \
               (location & cls.LOCATION_MASK)

    @classmethod
    def unpack(cls, word: int):
        """Unpack a 32-bit bus word -> (location, amount)."""
        amount   = (word >> cls.AMOUNT_SHIFT) & cls.AMOUNT_MASK
        location = word & cls.LOCATION_MASK
        return location, amount

    @classmethod
    def pack_stack(cls, readings: list) -> list:
        """Pack a list of (location, amount) tuples into bus words."""
        return [cls.pack(loc, amt) for loc, amt in readings]

    @classmethod
    def unpack_stack(cls, words: list) -> list:
        """Unpack a list of bus words -> [(location, amount), ...]."""
        return [cls.unpack(w) for w in words]


# ── Bridge Contract ──────────────────────────────────────────────────────────

class BridgeContract:
    """
    Formal contract for a cross-domain bridge tile.

    A bridge tile connects two format domains within a single cell map.
    The contract declares the physical relationship, the domain contexts
    on both sides, the confidence in that relationship, and whether the
    user must verify intent before the compiler places the bridge.

    semantic_confidence:
        1.0 — discovered (law of nature, derived from first principles)
        0.8 — well-established empirically (measured, validated, accepted)
        0.5 — model or approximation (works within range, not fundamental)
        0.2 — speculative (useful in context, no general physical basis)
        0.0 — no established connection (compiler refuses auto-placement)

    Compiler placement policy:
        conf >= 0.95 AND context_match  → auto-place, log
        conf >= 0.80 AND context_match  → warn, place on confirmation
        conf >= 0.60 OR context_mismatch → require explicit verification
        conf <  0.60                    → reject, require custom bridge

    The user's bridge selection is recorded permanently in model metadata:
        bridge, confidence, context_verified_by, verified_date, formula
    This makes the model self-documenting about its physical assumptions.
    """

    # Required
    name:                 str   = ""
    source_format:        str   = ""
    target_format:        str   = ""
    source_context:       str   = ""   # physical context of input
    target_context:       str   = ""   # physical context of output
    formula:              str   = ""   # the physical relationship
    constants_used:       list  = []   # domain constants consumed
    input_units:          str   = ""   # SI unit string
    output_units:         str   = ""   # SI unit string
    output_dimension:     list  = []   # [m,kg,s,A,K,mol,cd] exponents
    semantic_confidence:  float = 0.0
    requires_verification: bool = True
    notes:                str   = ""

    def to_dict(self) -> dict:
        return {
            "name":                 self.name,
            "source_format":        self.source_format,
            "target_format":        self.target_format,
            "source_context":       self.source_context,
            "target_context":       self.target_context,
            "formula":              self.formula,
            "constants_used":       self.constants_used,
            "input_units":          self.input_units,
            "output_units":         self.output_units,
            "output_dimension":     self.output_dimension,
            "semantic_confidence":  self.semantic_confidence,
            "requires_verification":self.requires_verification,
        }

    @property
    def context_match(self) -> bool:
        """True if source and target contexts are compatible."""
        return self.source_context == self.target_context

    @property
    def compiler_policy(self) -> str:
        """What the compiler should do with this bridge."""
        if self.semantic_confidence < 0.60:
            return "reject"
        if self.semantic_confidence < 0.80 or not self.context_match:
            return "require_verification"
        if self.semantic_confidence < 0.95:
            return "warn_and_place"
        return "auto_place"


# ── Fundamental bridge contracts ──────────────────────────────────────────────
# These are the known high-confidence bridges between physical domains.
# Each one was discovered, not invented.

class Bridge_Hawking(BridgeContract):
    """
    Hawking radiation: black hole mass → event horizon temperature.
    T = ℏc³ / (8πGMkB)
    Connects gravitational domain to thermal domain.
    confidence=1.0 — derived from QFT in curved spacetime.
    """
    name                = "SI_HAWKING_TEMP"
    source_format       = "SI_Physics"
    target_format       = "SI_Physics"
    source_context      = "gravitational"
    target_context      = "thermal_quantum"
    formula             = "T = hbar*c**3 / (8*pi*G*M*kB)"
    constants_used      = ["hbar", "c", "G", "kB"]
    input_units         = "kg"
    output_units        = "K"
    output_dimension    = [0,0,0,0,1,0,0]   # pure temperature
    semantic_confidence = 1.0
    requires_verification = False
    notes = (
        "Hawking 1974. Exact result from QFT in curved spacetime. "
        "Not an approximation. context=thermal_quantum — this temperature "
        "is NOT bulk thermal temperature. Cannot feed directly into "
        "bulk fluid models without a further context bridge."
    )


class Bridge_Navier_Stokes_Temp(BridgeContract):
    """
    Bulk fluid temperature under Newtonian gravity.
    Connects SI_Physics gravitational to bulk thermal context.
    Valid for tea, oceans, atmosphere — not for event horizons.
    """
    name                = "SI_NAVIER_STOKES_TEMP"
    source_format       = "SI_Physics"
    target_format       = "SI_Physics"
    source_context      = "gravitational"
    target_context      = "bulk_fluid"
    formula             = "rho*(dv/dt + v*grad_v) = -grad_p + mu*lap_v + rho*g"
    constants_used      = ["G"]   # Newtonian g preloaded
    input_units         = "kg/m³, m/s, Pa"
    output_units        = "K"
    output_dimension    = [0,0,0,0,1,0,0]
    semantic_confidence = 0.95
    requires_verification = False
    notes = (
        "Standard fluid mechanics under gravity. "
        "Appropriate for bulk fluids (tea, water, atmosphere). "
        "context=bulk_fluid — compatible with MathTrix thermal diffusion."
    )


class Bridge_Arrhenius(BridgeContract):
    """
    Arrhenius equation: temperature → chemical reaction rate.
    k = A * exp(-Ea / RT)
    Bridges thermal domain to chemical kinetics domain.
    """
    name                = "SI_ARRHENIUS"
    source_format       = "SI_Physics"
    target_format       = "Chemistry_Element"
    source_context      = "bulk_fluid"
    target_context      = "chemical_kinetics"
    formula             = "k = A * exp(-Ea / (R*T))"
    constants_used      = ["R", "kB"]
    input_units         = "K"
    output_units        = "s⁻¹"
    output_dimension    = [0,0,-1,0,0,0,0]   # frequency/rate
    semantic_confidence = 1.0
    requires_verification = False
    notes = (
        "Arrhenius 1889. Well-established physical chemistry. "
        "A (pre-exponential factor) and Ea (activation energy) are "
        "reaction-specific — declared as model parameters, not constants."
    )


class Bridge_Stefan_Boltzmann(BridgeContract):
    """
    Stefan-Boltzmann: temperature → radiated power.
    P = σ * A * T⁴
    Bridges bulk thermal to radiative domain.
    """
    name                = "SI_STEFAN_BOLTZMANN"
    source_format       = "SI_Physics"
    target_format       = "SI_Physics"
    source_context      = "bulk_fluid"
    target_context      = "radiative"
    formula             = "P = sigma * A * T**4"
    constants_used      = ["sigma"]
    input_units         = "K"
    output_units        = "W"
    output_dimension    = [2,1,-3,0,0,0,0]   # power = kg⋅m²/s³
    semantic_confidence = 1.0
    requires_verification = False
    notes = (
        "Stefan 1879, Boltzmann 1884. Exact for blackbody radiation. "
        "sigma already in SI_Physics.CONSTANTS."
    )


# ── Biological and chemical bridges ──────────────────────────────────────────

class Bridge_DNA_to_Amino(BridgeContract):
    """
    Codon translation: DNA triplet → amino acid code.
    Every 3 DNA bases (codon) maps to one of 20 amino acids.
    Standard genetic code — discovered, not invented.
    """
    name                = "DNA_CODON_TO_AMINO"
    source_format       = "DNA_4Base"
    target_format       = "Amino20"
    source_context      = "molecular"
    target_context      = "molecular"
    formula             = "codon(b1,b2,b3) → amino_acid via genetic_code_lut"
    constants_used      = []   # genetic code LUT preloaded in cells
    input_units         = "codon"
    output_units        = "residue"
    output_dimension    = []
    semantic_confidence = 1.0
    requires_verification = False
    notes = (
        "Standard genetic code. 64 codons → 20 amino acids + stop codons. "
        "LUT preloaded into cells at configure time. "
        "3 DNA bases consumed per output residue."
    )


class Bridge_DNA_to_Chem(BridgeContract):
    """
    GC content → melting temperature (Tm).
    Higher GC content raises the DNA melting temperature.
    Wallace rule: Tm = 2(A+T) + 4(G+C) °C
    """
    name                = "DNA_GC_TO_MELTING_TEMP"
    source_format       = "DNA_4Base"
    target_format       = "SI_Physics"
    source_context      = "molecular"
    target_context      = "bulk_fluid"
    formula             = "Tm = 2*(A+T) + 4*(G+C)"
    constants_used      = []
    input_units         = "base_counts"
    output_units        = "K"
    output_dimension    = [0,0,0,0,1,0,0]
    semantic_confidence = 0.85
    requires_verification = False
    notes = (
        "Wallace rule for short oligonucleotides. "
        "Approximate — valid for sequences 14-20 bases. "
        "More precise models exist (nearest-neighbour) but require more constants."
    )


class Bridge_Amino_to_Chem(BridgeContract):
    """
    Amino acid hydrophobicity → chemical partition coefficient.
    Hydrophobic residues partition into lipid phase.
    """
    name                = "AMINO_TO_CHEM_PARTITION"
    source_format       = "Amino20"
    target_format       = "Chemistry_Element"
    source_context      = "molecular"
    target_context      = "molecular"
    formula             = "logP ~ hydrophobicity_lut[residue]"
    constants_used      = []
    input_units         = "residue"
    output_units        = "log(partition_coefficient)"
    output_dimension    = []
    semantic_confidence = 0.75
    requires_verification = True
    notes = (
        "Kyte-Doolittle hydrophobicity scale. "
        "Approximate — empirically derived from measured partition coefficients. "
        "Useful for membrane protein prediction."
    )


class Bridge_Chem_to_DNA(BridgeContract):
    """
    Chemical mutagen → DNA mutation probability.
    Certain chemicals cause specific base substitutions.
    """
    name                = "CHEM_MUTAGEN_TO_DNA"
    source_format       = "Chemistry_Element"
    target_format       = "DNA_4Base"
    source_context      = "molecular"
    target_context      = "molecular"
    formula             = "P(mutation | chemical) via mutagen_specificity_lut"
    constants_used      = []
    input_units         = "element_code"
    output_units        = "mutation_probability"
    output_dimension    = []
    semantic_confidence = 0.7
    requires_verification = True
    notes = (
        "Chemical mutagenesis — specific chemicals cause specific base changes. "
        "EMS causes G→A transitions, UV causes C→T at dipyrimidines. "
        "LUT maps chemical code to mutation type and probability."
    )


class Bridge_SI_to_DNA(BridgeContract):
    """
    Temperature → DNA denaturation state.
    Above melting temperature, double-stranded DNA separates.
    """
    name                = "SI_TEMP_TO_DNA_STATE"
    source_format       = "SI_Physics"
    target_format       = "DNA_4Base"
    source_context      = "bulk_fluid"
    target_context      = "molecular"
    formula             = "state = 1 if T > Tm else 0  (denatured/native)"
    constants_used      = ["kB"]
    input_units         = "K"
    output_units        = "state"
    output_dimension    = []
    semantic_confidence = 0.90
    requires_verification = False
    notes = (
        "DNA denaturation above melting temperature. "
        "Sharp transition — sigmoid approximation at Tm. "
        "Tm supplied as model parameter (sequence-dependent)."
    )


class Bridge_LBM_Viscosity(BridgeContract):
    """
    Physical kinematic viscosity → LBM relaxation time (and Reynolds number).

    The lattice Boltzmann collision relaxation time tau encodes viscosity:
        nu_lattice = cs^2 * (tau - 1/2),   cs^2 = 1/3
    This identity is EXACT in the Chapman-Enskog expansion that recovers the
    Navier-Stokes equations from LBM — it is derived, not fitted. Reynolds
    number then follows from Re = U L / nu.

    Confidence note (honest): the dimensionless identity nu=cs^2(tau-1/2) is
    exact (confidence 1.0). But this bridge spans unit systems — a PHYSICAL
    viscosity in m^2/s becomes a LATTICE viscosity only after choosing the
    lattice spacing dx and timestep dt (the non-dimensionalisation). That
    choice is a modelling decision, not a law of nature, so the cross-domain
    contract is rated 0.95, not 1.0. The 1.0-exact part lives entirely inside
    FlowTrix (viscosity_from_tau); the 0.95 reflects the unit mapping at the
    domain boundary. Stated plainly so the model records the assumption.
    """
    name                = "LBM_VISCOSITY_TAU"
    source_format       = "SI_Physics"
    target_format       = "FlowTrix_D2Q9"
    source_context      = "bulk_fluid"
    target_context      = "bulk_fluid"
    formula             = "nu = cs2*(tau - 1/2); Re = U*L/nu; cs2 = 1/3"
    constants_used      = []           # cs2 is a lattice constant, in-format
    input_units         = "m^2/s (kinematic viscosity), m, m/s"
    output_units        = "dimensionless (tau)"
    output_dimension    = [0,0,0,0,0,0,0]   # tau is dimensionless
    semantic_confidence = 0.95
    requires_verification = False
    notes = (
        "Chapman-Enskog recovers Navier-Stokes; nu=cs2*(tau-1/2) is exact "
        "in that limit. Cross-unit mapping (physical->lattice) needs dx,dt "
        "-> rated 0.95. This is the bridge that sets the demo's Reynolds "
        "number: pick Re~100-200, derive tau, configure LBM_COLLIDE."
    )


FUNDAMENTAL_BRIDGES = [
    # Physics bridges (confidence 1.0 — discovered)
    Bridge_Hawking,
    Bridge_Navier_Stokes_Temp,
    Bridge_Arrhenius,
    Bridge_Stefan_Boltzmann,
    # Biology / chemistry bridges
    Bridge_DNA_to_Amino,
    Bridge_DNA_to_Chem,
    Bridge_Amino_to_Chem,
    Bridge_Chem_to_DNA,
    Bridge_SI_to_DNA,
    # Fluid dynamics bridge
    Bridge_LBM_Viscosity,
]


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
                        BCD_Decimal, Amino20, FixedPoint_Q8_24,
                        Chemistry_Element, SI_Physics, Finance_Currency,
                        FlowTrix_D2Q9, MidiTrix]:
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

    def discover_bridges(self, source_format: str,
                         target_format: str) -> dict:
        """
        Discover valid bridges between two formats.

        Validation is grounded in what the format definitions actually declare
        — not guesses, not word-matching, not hope.

        A bridge is VALID if and only if:
          1. source_format.produces[concept] exists — source CAN produce this
          2. target_format.consumes[concept] exists — target CAN accept this
          3. All bridge.constants_used exist in source OR target CONSTANTS
          4. The bridge is registered in FUNDAMENTAL_BRIDGES

        If a registered bridge fails validation, it is returned with
        valid=False and a specific reason. The compiler MUST NOT place
        invalid bridges.

        Returns:
          {
            bridges:         [BridgeContract instances, valid only]
            invalid:         [{bridge, reason}] — registered but cannot be placed
            shared_concepts: concepts source produces AND target consumes
            missing_data:    what would be needed for invalid bridges to work
            explanation:     plain-language description
            max_confidence:  highest confidence of valid bridges
          }
        """
        src_fmt = self._formats.get(source_format)
        tgt_fmt = self._formats.get(target_format)

        if not src_fmt or not tgt_fmt:
            return {
                "bridges": [], "invalid": [],
                "shared_concepts": [], "missing_data": [],
                "max_confidence": 0.0,
                "explanation": "One or both formats not registered.",
            }

        src_produces = src_fmt.produces  # {concept: [tiles]}
        tgt_consumes = tgt_fmt.consumes  # {concept: [tiles]}
        src_consts   = set(getattr(src_fmt, 'CONSTANTS', {}).keys())
        tgt_consts   = set(getattr(tgt_fmt, 'CONSTANTS', {}).keys())
        all_consts   = src_consts | tgt_consts

        # What can source produce that target can consume?
        shared_concepts = sorted(
            set(src_produces.keys()) & set(tgt_consumes.keys())
        )

        # Validate each registered bridge
        valid_bridges   = []
        invalid_bridges = []
        missing_data    = []

        for cls in FUNDAMENTAL_BRIDGES:
            b = cls()
            if b.source_format != source_format: continue
            if b.target_format != target_format:  continue

            reasons = []

            # Check 1: all required constants must exist in the formats
            for const in b.constants_used:
                if const not in all_consts:
                    reasons.append(
                        f"constant '{const}' not declared in "
                        f"{source_format}.CONSTANTS or {target_format}.CONSTANTS"
                    )
                    missing_data.append(
                        f"{const} must be added to {source_format} or "
                        f"{target_format} CONSTANTS"
                    )

            # Check 2: the bridge must connect concepts that are declared
            # We verify by checking that at least one shared concept exists
            # OR the bridge has confidence 1.0 (discovered physics)
            if not shared_concepts and b.semantic_confidence < 1.0:
                reasons.append(
                    f"no declared produces/consumes overlap between "
                    f"{source_format} and {target_format}"
                )

            if reasons:
                invalid_bridges.append({
                    "bridge":  b.name,
                    "formula": b.formula,
                    "confidence": b.semantic_confidence,
                    "reasons": reasons,
                })
            else:
                valid_bridges.append(b)

        valid_bridges.sort(key=lambda b: b.semantic_confidence, reverse=True)

        # Build explanation
        if valid_bridges:
            max_conf   = max(b.semantic_confidence for b in valid_bridges)
            conf_label = (
                "exact physics (discovered, not invented)"
                    if max_conf >= 1.0 else
                "well-established empirically"
                    if max_conf >= 0.85 else
                "empirical model (use with care)"
                    if max_conf >= 0.7 else
                "speculative — requires explicit verification"
            )
            best = valid_bridges[0]
            explanation = (
                f"{source_format} → {target_format}: "
                f"{len(valid_bridges)} valid bridge(s). "
                f"Confidence: {conf_label}. "
                + (f"Shared concepts: {', '.join(shared_concepts)}. "
                   if shared_concepts else "")
                + f"Best: {best.name} — {best.formula}"
            )
        elif shared_concepts:
            max_conf = 0.0
            explanation = (
                f"{source_format} → {target_format}: "
                f"Shared concepts exist ({', '.join(shared_concepts)}) "
                f"but no registered bridge covers them yet. "
                f"Define a BridgeContract with semantic_confidence "
                f"and add to FUNDAMENTAL_BRIDGES."
            )
        else:
            max_conf = 0.0
            explanation = (
                f"{source_format} → {target_format}: "
                f"No valid connection. "
                f"{source_format} does not produce anything "
                f"{target_format} declares it can consume. "
                f"These domains are not physically connected. "
                f"No bridge is possible without adding new declarations "
                f"to the format definitions."
            )

        return {
            "bridges":         valid_bridges,
            "bridge_names":    [b.name for b in valid_bridges],
            "invalid":         invalid_bridges,
            "shared_concepts": shared_concepts,
            "missing_data":    missing_data,
            "max_confidence":  max_conf,
            "explanation":     explanation,
            "source_domain":   src_fmt.domain,
            "target_domain":   tgt_fmt.domain,
        }

    def find_bridge(self, source_format: str,
                    target_format: str,
                    source_context: str = None) -> list[BridgeContract]:
        """
        Find all registered bridges between two format domains.

        Returns list of BridgeContract instances, sorted by confidence
        descending. Filters by source_context if provided.

        The compiler calls this when adjacent tiles have mismatched formats.
        The user selects from the returned list. Their selection is recorded
        permanently in the model metadata.

        Example:
            bridges = reg.find_bridge("SI_Physics", "Chemistry_Element")
            # → [Bridge_Arrhenius (conf=1.0), ...]

            bridges = reg.find_bridge("SI_Physics", "SI_Physics",
                                      source_context="gravitational")
            # → [Bridge_Hawking (thermal_quantum, conf=1.0),
            #    Bridge_Navier_Stokes_Temp (bulk_fluid, conf=0.95)]
        """
        candidates = []
        for bridge_cls in FUNDAMENTAL_BRIDGES:
            b = bridge_cls()
            if b.source_format != source_format:
                continue
            if b.target_format != target_format:
                continue
            if source_context and b.source_context != source_context:
                continue
            candidates.append(b)
        return sorted(candidates,
                      key=lambda b: b.semantic_confidence,
                      reverse=True)

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

    print("\n" + "─" * 50)
    print("Chemistry encoding:")
    chem = reg.get("Chemistry_Element")

    # Reverse LUT for display (atomic_number → symbol)
    rev = {v: k for k, v in chem.symbol_lut.items()
           if 1 <= v <= 118 and 1 <= len(k) <= 2}

    # Water: H2O — encode via symbol string
    words = chem.encode(["H", "H", "O", "_"])
    print(f"  H2O → packed 0x{words[0]:08X}")
    decoded_codes = chem.decode(words)[:3]
    int_codes = [(chem.symbol_lut.get(str(c),c) if isinstance(c,str) else c) for c in decoded_codes]
    symbols = [rev.get(ic, f"#{ic}") for ic in int_codes if ic > 0]
    print(f"  Decoded: {symbols}")

    # Methane: CH4 via formula parser
    codes = chem.formula_to_codes("CH4")
    print(f"  CH4 → atomic numbers {codes}")
    words = [sum((codes[i] & 0xFF) << (i*8) for i in range(min(4, len(codes))))]
    print(f"       → packed 0x{words[0]:08X}")
    cap = chem.capacity(1000)
    print(f"  1000-element sequence: {cap['cells']} cells ({cap['efficiency']}% efficient)")

    # Property LUT
    valence = chem.property_lut("valence")
    print(f"  Valence: H={valence[1]} C={valence[6]} O={valence[8]} Na={valence[11]}")

    # Tile validation
    for tile in ["CHEM_VALENCE", "CHEM_BOND", "MIF_ADD"]:
        ok, reason = chem.validate_tile(tile)
        print(f"  {'✓' if ok else '✗'} {tile}")

print("\nAll demos passed ✓")
