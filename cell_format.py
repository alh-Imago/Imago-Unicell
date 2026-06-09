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
                        Chemistry_Element]:
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
