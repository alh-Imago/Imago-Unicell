"""
SensorTrix format definition for the UniCell community.
See cell_format.py for the canonical definition.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from cell_format import SensorTrix, FormatRegistry
_reg = FormatRegistry.get_default()
_reg.register_class(SensorTrix)
__all__ = ["SensorTrix"]
