"""
Phystrix format definition.
Reference implementation — formats defined in cell_format.py.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from cell_format import FormatRegistry
# Formats are registered in cell_format.py built-ins.
# This file exists so the community structure is complete
# and the validator can import it cleanly.
_reg = FormatRegistry.get_default()
FORMATS = [_reg.get("SI_Physics")]
