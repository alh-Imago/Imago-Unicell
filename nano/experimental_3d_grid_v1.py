"""POINTER (#1308): this file moved, unchanged, to experimental/three_d/experimental_3d_grid_v1.py. This stub loads it under the old module name so every import keeps working."""
import importlib.util, os, sys
_p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "experimental", "three_d", "experimental_3d_grid_v1.py")
_spec = importlib.util.spec_from_file_location(__name__, _p)
_mod = importlib.util.module_from_spec(_spec); sys.modules[__name__] = _mod; _spec.loader.exec_module(_mod)
