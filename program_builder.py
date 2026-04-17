"""
program_builder.py — Full program spatial map assembler.

The ProgramBuilder walks a program's complete dependency tree across
source files and libraries, resolves all references, and assembles a
single unified CellMapRecord list that the controller can load as one
image.

This is the component that realises the library model described in the
compiler docstring:
  - Each source file is a compilation unit
  - Only referenced functions are placed (zero treeshaking pass needed)
  - The tile registry caches compiled functions across files
  - Address assignment is global across the whole program image
  - The result is one flat spatial map spanning all required computation

Usage:
    builder = ProgramBuilder()
    builder.add_source("mylib.py")          # register a library
    builder.add_source("main.py")           # register the entry point
    records, info = builder.build("main", "entry_function")
    region_id = controller.load_map(records, image_name="my_program")

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PROGRAM BUILDER — THE DEPENDENCY WALK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The builder walks the dependency tree as follows:

  1. Start at the named entry function in the named source file.
  2. Compile that function. The compiler inlines direct calls it can
     resolve within the same source. For calls to external functions
     (defined in other registered source files), the builder intercepts
     them, compiles the external function, and places it as a tile.
  3. Each compiled function becomes a named tile in the tile registry:
     a CellMapRecord list with known input and output addresses.
  4. When the same function is called from multiple places, the registry
     returns the existing tile rather than recompiling. Each call site
     receives its own address-assigned copy (addresses must be unique
     per placement), but the compilation work is done once.
  5. The walk terminates when all referenced functions have been
     compiled and placed.

The resulting image contains exactly the union of everything reachable
from the entry point. Nothing else is placed.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import ast
import json
import hashlib
import time
import os
from typing import Optional
from compiler import ImagoCompiler
from ir import IRGraph, lower_to_cell_map, AddressAllocator
from controller import CellMapRecord
from gate_states import GS_PASS


# ── BuildInfo ─────────────────────────────────────────────────────────────────

class BuildInfo:
    """
    Result metadata from a ProgramBuilder.build() call.
    Contains the information needed to inject inputs and read outputs.
    """
    def __init__(
        self,
        entry_function:  str,
        total_cells:     int,
        input_addresses: dict[str, int],    # param_name -> bus address
        output_addresses: list[int],         # result bus addresses
        tiles_placed:    list[str],          # function names placed
        tile_cell_counts: dict[str, int],   # function_name -> cell count
        image_path:      Optional[str] = None,  # path to .icm file if saved
        checksum:        Optional[str] = None,  # SHA-256 of image file
    ):
        self.entry_function   = entry_function
        self.total_cells      = total_cells
        self.input_addresses  = input_addresses
        self.output_addresses = output_addresses
        self.tiles_placed     = tiles_placed
        self.tile_cell_counts = tile_cell_counts
        self.image_path       = image_path
        self.checksum         = checksum

    def __repr__(self) -> str:
        img = f" image={self.image_path}" if self.image_path else ""
        return (
            f"BuildInfo(entry={self.entry_function} "
            f"cells={self.total_cells} "
            f"inputs={self.input_addresses} "
            f"outputs={[hex(a) for a in self.output_addresses]} "
            f"tiles={self.tiles_placed}{img})"
        )


# ── TileRegistry ─────────────────────────────────────────────────────────────

class TileRegistry:
    """
    Cache of compiled function tiles.
    A tile is a (CellMapRecord list, input_map, output_addresses) triple.
    Functions are compiled once and retrieved by name for subsequent
    call sites.
    """

    def __init__(self):
        # name -> (records, input_map, output_addrs, ir_graph)
        self._tiles: dict[str, tuple] = {}

    def has(self, name: str) -> bool:
        return name in self._tiles

    def store(
        self,
        name:         str,
        records:      list[CellMapRecord],
        input_map:    dict[str, int],
        output_addrs: list[int],
        graph:        IRGraph,
    ) -> None:
        self._tiles[name] = (records, input_map, output_addrs, graph)

    def get(self, name: str) -> Optional[tuple]:
        return self._tiles.get(name)

    def names(self) -> list[str]:
        return list(self._tiles.keys())

    def cell_count(self, name: str) -> int:
        tile = self._tiles.get(name)
        return len(tile[0]) if tile else 0


# ── ProgramBuilder ────────────────────────────────────────────────────────────

class ProgramBuilder:
    """
    Assembles a complete spatial program image from one or more source files.

    Register source files with add_source(). Call build() with the entry
    point function name to produce the final CellMapRecord list.
    """

    def __init__(self):
        # Registered source files: filename -> source text
        self._sources: dict[str, str] = {}

        # All function definitions found across all sources
        # function_name -> (source_text, filename)
        self._function_registry: dict[str, tuple[str, str]] = {}

        # Tile registry: compiled function tiles
        self._tile_registry = TileRegistry()

        # Global address allocator — shared across all tiles in one build
        # so no two tiles share addresses
        self._allocator = AddressAllocator()

        # Build log
        self._log: list[str] = []

    # ── source registration ───────────────────────────────────────────────────

    def add_source(self, source: str, filename: str = "<string>") -> int:
        """
        Register a source file. Parses the source and indexes all
        function definitions. Returns count of functions registered.
        """
        self._sources[filename] = source
        tree = ast.parse(source)
        count = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if node.name in self._function_registry:
                    existing_file = self._function_registry[node.name][1]
                    self._log.append(
                        f"WARNING: function '{node.name}' in '{filename}' "
                        f"shadows definition in '{existing_file}'"
                    )
                self._function_registry[node.name] = (source, filename)
                count += 1
        self._log.append(
            f"Registered '{filename}': {count} function(s) indexed"
        )
        return count

    def add_source_file(self, path: str) -> int:
        """Register a source file by filesystem path."""
        with open(path, 'r') as f:
            source = f.read()
        return self.add_source(source, filename=path)

    # ── build ─────────────────────────────────────────────────────────────────

    def build(
        self,
        entry_function: str,
        source_hint: Optional[str] = None,
        output_dir: Optional[str] = None,
        image_name: Optional[str] = None,
    ) -> tuple[list[CellMapRecord], BuildInfo]:
        """
        Build the complete spatial map for the program and optionally
        save it as a .icm image file.

        entry_function: name of the top-level function to compile
        source_hint:    filename to search first (optional)
        output_dir:     directory to write the .icm file (optional).
                        If None, no file is written.
        image_name:     base name for the .icm file (optional).
                        Defaults to entry_function if not provided.

        Returns (records, build_info).
        records is the flat CellMapRecord list to pass to controller.load_map().
        build_info contains input/output addresses, build statistics,
        and the image_path if a file was written.
        """
        if entry_function not in self._function_registry:
            available = list(self._function_registry.keys())
            raise ValueError(
                f"Entry function '{entry_function}' not found. "
                f"Available: {available}"
            )

        self._log.append(f"Building '{entry_function}'...")
        self._allocator = AddressAllocator()  # fresh addresses for each build
        self._tile_registry = TileRegistry()  # fresh registry for each build

        # Compile the entry function (and recursively all it references)
        records, input_map, output_addrs = self._compile_function(entry_function)

        tiles_placed = self._tile_registry.names()
        tile_counts  = {n: self._tile_registry.cell_count(n) for n in tiles_placed}

        # Write .icm image file if output_dir specified
        image_path = None
        checksum   = None
        if output_dir is not None:
            image_path, checksum = self._write_image(
                records, entry_function,
                output_dir, image_name or entry_function,
                input_map, output_addrs,
            )
            self._log.append(f"Image saved: {image_path} (SHA-256: {checksum[:16]}...)")

        info = BuildInfo(
            entry_function   = entry_function,
            total_cells      = len(records),
            input_addresses  = input_map,
            output_addresses = output_addrs,
            tiles_placed     = tiles_placed,
            tile_cell_counts = tile_counts,
            image_path       = image_path,
            checksum         = checksum,
        )

        self._log.append(
            f"Build complete: {len(records)} cells, "
            f"{len(tiles_placed)} tile(s) placed"
        )
        return records, info

    # ── image file I/O ───────────────────────────────────────────────────────

    def _write_image(
        self,
        records:      list[CellMapRecord],
        entry_function: str,
        output_dir:   str,
        base_name:    str,
        input_map:    dict[str, int],
        output_addrs: list[int],
    ) -> tuple[str, str]:
        """
        Serialise a CellMapRecord list to a .icm JSON file.

        File format (per Implementation Guide):
          {
            "entry_function": str,
            "compiled_at": float,
            "input_addresses": {name: address, ...},
            "output_addresses": [address, ...],
            "cell_map": [
              {"gate_state": int, "input_address": int, "output_address": int},
              ...
            ]
          }

        Returns (file_path, sha256_checksum).
        """
        os.makedirs(output_dir, exist_ok=True)

        cell_map_data = [
            {
                "gate_state":     r.gate_state,
                "input_address":  r.input_address,
                "output_address": r.output_address,
            }
            for r in records
        ]

        image_data = {
            "entry_function":  entry_function,
            "compiled_at":     time.time(),
            "input_addresses": input_map,
            "output_addresses": output_addrs,
            "cell_map":        cell_map_data,
        }

        filename  = f"{base_name}.icm"
        filepath  = os.path.join(output_dir, filename)

        # Write atomically: write to temp file then rename
        tmp_path  = filepath + ".tmp"
        json_text = json.dumps(image_data, indent=2)
        with open(tmp_path, 'w') as f:
            f.write(json_text)
        os.replace(tmp_path, filepath)

        # Compute checksum
        checksum = hashlib.sha256(json_text.encode()).hexdigest()
        return filepath, checksum

    @staticmethod
    def load_image(
        filepath: str,
    ) -> tuple[list[CellMapRecord], dict[str, int], list[int], str]:
        """
        Load a .icm image file and return:
          (records, input_addresses, output_addresses, entry_function)

        Verifies the file is readable and well-formed.
        Raises ValueError if the file is malformed.
        Raises FileNotFoundError if the file does not exist.
        """
        with open(filepath, 'r') as f:
            data = json.load(f)

        required = {"entry_function", "cell_map", "input_addresses", "output_addresses"}
        missing = required - set(data.keys())
        if missing:
            raise ValueError(
                f"Malformed .icm file '{filepath}': missing fields {missing}"
            )

        records = [
            CellMapRecord(
                cell["gate_state"],
                cell["input_address"],
                cell["output_address"],
            )
            for cell in data["cell_map"]
        ]

        return (
            records,
            data["input_addresses"],
            data["output_addresses"],
            data["entry_function"],
        )

    # ── recursive compilation ─────────────────────────────────────────────────

    def _compile_function(
        self,
        name: str,
        _depth: int = 0,
    ) -> tuple[list[CellMapRecord], dict[str, int], list[int]]:
        """
        Compile a named function and all functions it references.
        Returns (records, input_map, output_addresses).

        Uses the tile registry to avoid recompiling the same function twice.
        Each call site gets its own address-assigned copy of the tile,
        but the compilation work is done only once.
        """
        indent = "  " * _depth

        # Retrieve source for this function
        source, filename = self._function_registry[name]

        self._log.append(f"{indent}Compiling '{name}' from '{filename}'")

        # Combine all registered sources into one compilation unit.
        # The compiler inlines all calls it can see in the combined source.
        # This allows cross-file function calls to be resolved naturally
        # through the compiler's existing inlining mechanism.
        combined_source = "\n\n".join(self._sources.values())

        compiler = ImagoCompiler()
        compiler_records, graph, input_map, output_addrs = \
            compiler.compile_function(
                combined_source,
                name,
                list(_get_param_names(source, name))
            )

        # Re-assign addresses using the global allocator to avoid collisions
        # between tiles compiled by different ImagoCompiler instances
        records, input_map, output_addrs = self._reassign_addresses(
            compiler_records, graph, input_map, output_addrs
        )

        # Check for cross-file calls and compile those too
        cross_calls = self._find_cross_file_calls(source, name)
        for called_name in cross_calls:
            if called_name not in self._function_registry:
                self._log.append(
                    f"{indent}  WARNING: '{called_name}' referenced but not "
                    f"registered — skipping"
                )
                continue
            if not self._tile_registry.has(called_name):
                self._compile_function(called_name, _depth + 1)

        # Store in tile registry
        self._tile_registry.store(name, records, input_map, output_addrs, graph)

        cell_count = len(records)
        self._log.append(
            f"{indent}Placed '{name}': {cell_count} cell(s), "
            f"inputs={list(input_map.keys())}, "
            f"output(s)={[hex(a) for a in output_addrs]}"
        )

        return records, input_map, output_addrs

    def _reassign_addresses(
        self,
        records:      list[CellMapRecord],
        graph:        IRGraph,
        input_map:    dict[str, int],
        output_addrs: list[int],
    ) -> tuple[list[CellMapRecord], dict[str, int], list[int]]:
        """
        Reassign all addresses in a compiled tile using the global allocator.
        This ensures no two tiles share addresses, even if compiled
        independently by different ImagoCompiler instances.

        Builds a remapping table from old addresses to new global addresses,
        then applies it to all records, input_map, and output_addrs.
        """
        # Collect all unique addresses in the tile
        old_addrs: set[int] = set()
        for r in records:
            old_addrs.add(r.input_address)
            old_addrs.add(r.output_address)
        for addr in input_map.values():
            old_addrs.add(addr)
        for addr in output_addrs:
            old_addrs.add(addr)

        # Assign new global addresses
        remap: dict[int, int] = {}
        for old in sorted(old_addrs):
            remap[old] = self._allocator.alloc()

        # Remap records
        new_records = [
            CellMapRecord(
                r.gate_state,
                remap[r.input_address],
                remap[r.output_address],
            )
            for r in records
        ]

        # Remap input_map
        new_input_map = {
            name: remap[addr]
            for name, addr in input_map.items()
        }

        # Remap output_addrs
        new_output_addrs = [remap[a] for a in output_addrs]

        return new_records, new_input_map, new_output_addrs

    def _find_cross_file_calls(self, source: str, function_name: str) -> list[str]:
        """
        Find calls within function_name that reference functions
        registered from other source files.
        Returns list of called function names that exist in the registry
        but not in the same source.
        """
        # Get all function names defined in this source
        local_tree = ast.parse(source)
        local_functions = {
            node.name for node in ast.walk(local_tree)
            if isinstance(node, ast.FunctionDef)
        }

        # Find all Call nodes within this specific function
        for node in ast.walk(local_tree):
            if isinstance(node, ast.FunctionDef) and node.name == function_name:
                calls = []
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        if isinstance(child.func, ast.Name):
                            called = child.func.id
                            if (called not in local_functions and
                                    called in self._function_registry):
                                calls.append(called)
                return calls
        return []

    # ── convenience methods ───────────────────────────────────────────────────

    def build_and_run(
        self,
        entry_function: str,
        inputs:         dict[str, int],
        controller,
        image_name:     Optional[str] = None,
    ) -> tuple[Optional[dict[int, int]], BuildInfo]:
        """
        Build the program, load it into the controller, run it with the
        given named inputs, and return (outputs, build_info).

        inputs: {parameter_name: value} — named inputs for the entry function
        controller: an ImagoController instance

        Returns (output_dict, build_info) where output_dict maps output
        bus addresses to their values.
        """
        records, info = self.build(entry_function)
        if not records:
            return None, info

        name = image_name or entry_function
        region_id = controller.load_map(records, image_name=name)
        if region_id is None:
            return None, info

        # Map named inputs to bus addresses
        bus_inputs = {
            info.input_addresses[k]: v
            for k, v in inputs.items()
            if k in info.input_addresses
        }

        outputs = controller.run(
            region_id,
            inputs=bus_inputs,
            capture_addresses=info.output_addresses,
        )
        return outputs, info

    def print_log(self) -> None:
        """Print the build log."""
        for line in self._log:
            print(f"  [BUILD] {line}")

    def summary(self) -> str:
        """Return a one-line build summary."""
        tiles = self._tile_registry.names()
        total = sum(self._tile_registry.cell_count(n) for n in tiles)
        return (
            f"{len(tiles)} tile(s) placed, "
            f"{total} cells total, "
            f"address space: 0x{AddressAllocator.BASE:08X} — "
            f"0x{self._allocator._next - 1:08X}"
        )


# ── helpers ───────────────────────────────────────────────────────────────────

def _get_param_names(source: str, function_name: str) -> list[str]:
    """Extract parameter names from a function definition."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            return [arg.arg for arg in node.args.args]
    return []
