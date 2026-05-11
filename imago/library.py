"""
imago/library.py — User ICM library management.

The user library lives at ~/.imago/library/ and is automatically scanned
at startup. Any .icm file placed there is available as a named program
via `imago run`, `VM.load()`, and (if the file declares models[]) as a
tile the compiler can use.

Directory layout:
    ~/.imago/
        library/
            README.md           — explains the library format
            logic/              — gates, mux, comparators
            arithmetic/         — adders, multipliers, counters
            neural/             — LIF neurons, Izhikevich, cascades
            sorting/            — sort networks
            custom/             — user-defined programs
        config.json             — user preferences (future)

Programs are plain .icm files. The library does not sign or verify them
beyond confirming they are valid JSON with a 'records' key.
"""

import os
import json
import shutil
from pathlib import Path
from typing import Optional


# ── Paths ─────────────────────────────────────────────────────────────────────

def library_root() -> Path:
    """Return ~/.imago/library, creating it if needed."""
    root = Path.home() / ".imago" / "library"
    root.mkdir(parents=True, exist_ok=True)
    return root


def imago_home() -> Path:
    """Return ~/.imago, creating it if needed."""
    home = Path.home() / ".imago"
    home.mkdir(parents=True, exist_ok=True)
    return home


CATEGORIES = ["logic", "arithmetic", "neural", "sorting", "custom"]


# ── Initialisation ────────────────────────────────────────────────────────────

def init_library(verbose: bool = True) -> Path:
    """
    Create ~/.imago/library/ with category subdirectories and README.
    Safe to call multiple times — never overwrites existing files.
    Returns the library root path.
    """
    root = library_root()

    # Create category directories
    for cat in CATEGORIES:
        (root / cat).mkdir(exist_ok=True)

    # Write README if not present
    readme = root / "README.md"
    if not readme.exists():
        readme.write_text("""\
# Imago UniCell — User Library

Place `.icm` files here to make them available across all sessions.

    ~/.imago/library/
        logic/       — gates, mux, comparators
        arithmetic/  — adders, multipliers, counters
        neural/      — LIF neurons, Izhikevich, cascades
        sorting/     — sort networks
        custom/      — anything else

## Using your library

    imago run my_program              # run by name (no .icm extension)
    imago run my_program a=5 b=3      # run with inputs

    imago library list                # list all library programs
    imago library add my_file.icm     # add a program (copies to custom/)
    imago library add my_file.icm --category neural
    imago library remove my_program   # remove by name

## Sharing

An `.icm` file is self-contained — share it directly. To contribute
to the community index, add it to composer/models/INDEX.md and open
a PR to https://github.com/alh-Imago/Imago-Unicell

## In Python

    import imago
    vm = imago.VM()
    vm.load_library("my_program")     # load from user library
    vm.run(a=5, b=3)

    # All library programs are also returned by:
    imago.library_programs()

## Format

Each file is a standard .icm JSON file. See docs/ICM_FORMAT.md for
the full specification. The minimum valid file:

    {
      "name": "my_program",
      "inputs":  {"a": 4096},
      "outputs": {"result": 4097},
      "models":  [],
      "records": [{"gs": 1, "in": 4096, "out": 4097,
                   "inB": null, "alt": null, "stor": false, "init": null}]
    }
""")

    if verbose:
        print(f"Library: {root}")
        for cat in CATEGORIES:
            print(f"  {cat}/")

    return root


# ── Scanning ──────────────────────────────────────────────────────────────────

def scan_library() -> dict:
    """
    Scan ~/.imago/library/ for .icm files.
    Returns {name: {"path": Path, "category": str, "cells": int,
                     "inputs": [...], "outputs": [...], "description": str}}
    Names are derived from the filename (without .icm extension).
    Duplicate names across categories: last one wins (alphabetical category order).
    """
    root = library_root()
    found = {}

    # Scan root itself first, then categories
    search_dirs = [("", root)] + [(cat, root / cat) for cat in CATEGORIES]

    for category, d in search_dirs:
        if not d.exists():
            continue
        for path in sorted(d.glob("*.icm")):
            try:
                icm = json.loads(path.read_text())
                if "records" not in icm:
                    continue
                name = path.stem
                found[name] = {
                    "path":        path,
                    "category":    category or "root",
                    "cells":       len(icm.get("records", [])),
                    "inputs":      list(icm.get("inputs", {}).keys()),
                    "outputs":     list(icm.get("outputs", {}).keys()),
                    "description": icm.get("description", ""),
                    "models":      icm.get("models", []),
                    "icm":         icm,
                }
            except (json.JSONDecodeError, OSError):
                pass  # skip corrupt files silently

    return found


# ── Add / Remove ──────────────────────────────────────────────────────────────

def add_program(source_path: str,
                category: str = "custom",
                name: Optional[str] = None,
                verbose: bool = True) -> dict:
    """
    Copy a .icm file into ~/.imago/library/<category>/.
    Validates the file is a valid .icm before copying.
    Returns the library entry dict.
    """
    src = Path(source_path)
    if not src.exists():
        raise FileNotFoundError(f"File not found: {source_path}")

    try:
        icm = json.loads(src.read_text())
    except json.JSONDecodeError as e:
        raise ValueError(f"Not a valid JSON file: {e}")

    if "records" not in icm:
        raise ValueError("Not a valid .icm file: missing 'records' key")

    if category not in CATEGORIES + ["root"]:
        raise ValueError(f"Unknown category '{category}'. "
                         f"Choose from: {', '.join(CATEGORIES)}")

    program_name = name or icm.get("name") or src.stem
    dest_dir = library_root() / (category if category != "root" else "")
    dest_dir.mkdir(exist_ok=True)
    dest = dest_dir / f"{program_name}.icm"

    shutil.copy2(src, dest)

    if verbose:
        cells = len(icm.get("records", []))
        print(f"Added '{program_name}' ({cells} cells) → {dest}")

    return {
        "name": program_name,
        "path": dest,
        "category": category,
        "cells": len(icm.get("records", [])),
    }


def remove_program(name: str, verbose: bool = True) -> bool:
    """
    Remove a program from the user library by name.
    Searches all category directories. Returns True if found and removed.
    """
    lib = scan_library()
    if name not in lib:
        if verbose:
            print(f"'{name}' not found in user library.")
        return False

    path = lib[name]["path"]
    path.unlink()
    if verbose:
        print(f"Removed '{name}' from {path.parent.name}/")
    return True


def get_program_path(name: str) -> Optional[Path]:
    """Return the Path to a named program in the user library, or None."""
    lib = scan_library()
    entry = lib.get(name)
    return entry["path"] if entry else None


# ── Library info ──────────────────────────────────────────────────────────────

def list_programs(verbose: bool = True) -> dict:
    """Print and return all programs in the user library."""
    lib = scan_library()
    if not lib:
        if verbose:
            print("User library is empty.")
            print(f"Add programs with: imago library add <file.icm>")
            print(f"Library location:  {library_root()}")
        return {}

    if verbose:
        print(f"User library ({library_root()}):")
        by_cat = {}
        for name, entry in sorted(lib.items()):
            cat = entry["category"]
            by_cat.setdefault(cat, []).append((name, entry))
        for cat in ["root"] + CATEGORIES:
            if cat not in by_cat:
                continue
            print(f"\n  {cat}/")
            for name, entry in by_cat[cat]:
                ins  = entry["inputs"]
                outs = entry["outputs"]
                desc = entry["description"][:50] if entry["description"] else ""
                print(f"    {name:<20} {entry['cells']:>5} cells  "
                      f"in={ins} out={outs}")
                if desc:
                    print(f"    {'':20} {desc}")

    return lib
