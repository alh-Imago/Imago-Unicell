"""
BioTrix (DNA, RNA, Amino20) format definitions for UniCell.
These are the reference implementations of the format definition pattern.
See docs/FORMAT_DEFINITION_GUIDE.md for how to create your own.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from cell_format import FormatDefinition, FormatRegistry

# Import the format classes from the central registry
# (defined in cell_format.py — single source of truth)
from cell_format import DNA_4Base, RNA_4Base, Amino20

# Register on import — makes formats available to any code that
# imports this module, without duplicating the definition.
_reg = FormatRegistry.get_default()
_reg.register_class(DNA_4Base)  # DNA_4Base — BioTrix
_reg.register_class(RNA_4Base)  # RNA_4Base — BioTrix
_reg.register_class(Amino20)  # Amino20 — BioTrix

__all__ = ["DNA_4Base", "RNA_4Base", "Amino20"]
