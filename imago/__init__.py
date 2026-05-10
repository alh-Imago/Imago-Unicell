"""
imago — Imago UniCell VM

A compute architecture built from a single, universal cell.
Every logic function is one cell, one cycle. Programs are portable
.icm files that run identically on the Python VM, FPGA, and future ASIC.

Quick start:
    from imago import VM, run_icm, compile_function

    # Run an .icm program
    result = run_icm("not_gate.icm", inputs={"a": 1})
    print(result)   # {"result": 0}

    # Compile and run Python source
    vm = VM()
    vm.load_source("def add(a, b): return a and b", "add")
    vm.set("a", 1)
    vm.set("b", 1)
    print(vm.run())   # {"output": 1}

    # Launch the workbench browser UI
    from imago import workbench
    workbench.serve()   # opens http://localhost:7420
"""

__version__ = "0.1.0"
__author__  = "Imago UniCell Project"

# ── Core imports ──────────────────────────────────────────────────────────────

import sys
import os

# Add parent directory to path so imago can find the core VM files
# when installed as a package (editable or otherwise)
_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.dirname(_here)
if _root not in sys.path:
    sys.path.insert(0, _root)


def _lazy(module_path, attr):
    """Return a lazy loader for a module attribute."""
    import importlib
    def _load():
        mod = importlib.import_module(module_path)
        return getattr(mod, attr)
    return _load


# ── Public API ────────────────────────────────────────────────────────────────

class VM:
    """
    The Imago UniCell VM. One instance = one array + one workspace.

    Usage:
        vm = VM()
        vm.load("not_gate.icm")
        vm.set("a", 1)
        print(vm.run())   # {"result": 0}
    """

    def __init__(self, cell_count: int = 4096):
        from controller import ImagoController
        from workspace import WorkspacePond
        self._ctrl = ImagoController(cell_count=cell_count)
        self._ws   = WorkspacePond(self._ctrl, name="default")

    def load(self, path: str) -> dict:
        """Load a .icm file. Returns {ok, name, inputs, outputs, cells}."""
        return self._ws.load_icm(path)

    def load_example(self, name: str) -> dict:
        """
        Load a bundled example program by name.

        Available: not_gate, and_gate, add, adder_int32, mux
        """
        examples_dir = os.path.join(os.path.dirname(__file__), "examples")
        path = os.path.join(examples_dir, name + ".icm")
        if not os.path.exists(path):
            available = [f[:-4] for f in os.listdir(examples_dir) if f.endswith(".icm")]
            raise FileNotFoundError(
                f"Example '{name}' not found. Available: {available}"
            )
        return self._ws.load_icm(path)

    def load_source(self, source: str, fn_name: str,
                    int32: bool = False,
                    port_names: dict = None) -> dict:
        """Compile and load. int32=True for 32-bit functions.
        port_names: optional {original_param: new_name} renaming."""
        if int32:
            return self._ws.compile_int32(source, fn_name)
        return self._ws.compile(source, fn_name, port_names=port_names)

    def set(self, name: str, value) -> None:
        """Set a named input value."""
        self._ws.set(name, value)

    def get(self, name: str):
        """Get a named value (input or output)."""
        r = self._ws.get(name)
        return r.get("value") if r.get("ok") else None

    def run(self, **inputs) -> dict:
        """
        Run the loaded program. Named kwargs set inputs before running.

        Returns {name: value} for all outputs.
        """
        for k, v in inputs.items():
            self._ws.set(k, v)
        result = self._ws.run()
        if not result.get("ok"):
            raise RuntimeError(result.get("error", "Run failed"))
        return result.get("outputs", {})

    def values(self) -> dict:
        """Return current named values: {inputs: {...}, outputs: {...}}."""
        r = self._ws.values()
        return {"inputs": r.get("inputs", {}), "outputs": r.get("outputs", {})}

    def status(self) -> dict:
        """Return workspace status."""
        return self._ws.status()

    @property
    def workspace(self):
        """Direct access to the WorkspacePond for advanced use."""
        return self._ws

    @property
    def controller(self):
        """Direct access to ImagoController for advanced use."""
        return self._ctrl


def run_icm(path: str, inputs: dict = None, cell_count: int = 4096) -> dict:
    """
    One-shot: load a .icm file, inject inputs, run, return outputs.

    Example:
        result = run_icm("not_gate.icm", inputs={"a": 1})
        print(result)  # {"result": 0}
    """
    vm = VM(cell_count=cell_count)
    r = vm.load(path)
    if not r.get("ok"):
        raise RuntimeError(r.get("error", f"Failed to load {path}"))
    return vm.run(**(inputs or {}))


def compile_function(source: str, fn_name: str,
                     int32: bool = False,
                     cell_count: int = 4096,
                     port_names: dict = None) -> "VM":
    """
    Compile a Python function and return a ready-to-run VM.

    port_names: optional {original_name: new_name} to rename ports before
                the .icm is written. e.g. {"a": "input_a", "output": "sum"}

    Example:
        vm = compile_function("def add(a, b): return a and b", "add")
        print(vm.run(a=1, b=1))   # {"output": 1}
    """
    vm = VM(cell_count=cell_count)
    r = vm.load_source(source, fn_name, int32=int32, port_names=port_names)
    if not r.get("ok"):
        raise RuntimeError(r.get("error", "Compile failed"))
    return vm


def set_verbose(verbose: bool = True) -> None:
    """
    Control VM diagnostic output.

    set_verbose(False) — silence all [CONTROLLER], [POND], [SHORE] etc. messages.
    set_verbose(True)  — restore normal output (default).

    Can also be set via environment variable before importing:
        IMAGO_VERBOSE=0 python3 my_script.py
    """
    import imago_log
    imago_log.set_level(imago_log.INFO if verbose else imago_log.SILENT)


def set_log_level(level: int) -> None:
    """
    Set fine-grained log level.

    Levels: imago.SILENT, imago.ERROR, imago.WARN, imago.INFO, imago.DEBUG
    """
    import imago_log
    imago_log.set_level(level)


# Log level constants — re-exported for convenience
SILENT = 0
ERROR  = 1
WARN   = 2
INFO   = 3
DEBUG  = 4


def examples() -> list:
    """List bundled example program names."""
    d = os.path.join(os.path.dirname(__file__), "examples")
    return sorted(f[:-4] for f in os.listdir(d) if f.endswith(".icm"))


def example_path(name: str) -> str:
    """Return the full path to a bundled example .icm file."""
    return os.path.join(os.path.dirname(__file__), "examples", name + ".icm")
