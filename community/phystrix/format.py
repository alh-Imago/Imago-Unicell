"""
PhysTrix (SI Physics) format definitions for UniCell.
These are the reference implementations of the format definition pattern.
See docs/FORMAT_DEFINITION_GUIDE.md for how to create your own.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from cell_format import FormatDefinition, FormatRegistry

# Import the format classes from the central registry
# (defined in cell_format.py — single source of truth)
from cell_format import SI_Physics

# Register on import — makes formats available to any code that
# imports this module, without duplicating the definition.
_reg = FormatRegistry.get_default()
_reg.register_class(SI_Physics)  # SI_Physics — PhysTrix

__all__ = ["SI_Physics"]
