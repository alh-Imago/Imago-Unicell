#!/usr/bin/env python3
"""
community_tools.py — UniCell Community Contribution Tools

Commands:
  validate <domain/>   Validate a contribution folder
  hash     <domain/>   Compute and update hash in MANIFEST.json
  register             Rebuild REGISTRY.md from all MANIFEST.json files
  search   <keyword>   Search registry and manifests
  new      <name>      Scaffold a new contribution folder

Usage:
  python community/community_tools.py validate community/biotrix/
  python community/community_tools.py hash community/biotrix/
  python community/community_tools.py register
  python community/community_tools.py search genomics
  python community/community_tools.py new mytrix
"""

from __future__ import annotations

import sys
import os
import json
import hashlib
import argparse
import importlib.util
from pathlib import Path
from datetime import date

# ── Paths ─────────────────────────────────────────────────────────────────────

REPO_ROOT  = Path(__file__).parent.parent
COMMUNITY  = Path(__file__).parent
REGISTRY   = COMMUNITY / "REGISTRY.md"

REQUIRED_FILES = ["README.md", "format.py", "MANIFEST.json"]
REQUIRED_MANIFEST_FIELDS = [
    "name", "domain", "version", "created", "updated",
    "author", "license", "description", "requires",
    "formats", "models", "bridges", "hash", "tags",
]


# ── Hash ──────────────────────────────────────────────────────────────────────

def compute_hash(folder: Path) -> str:
    """
    Compute SHA-256 over all .py, .json, .md files in a folder.
    Files are sorted for determinism. Hash excludes the hash field itself.
    """
    h = hashlib.sha256()
    files = sorted(
        f for f in folder.rglob("*")
        if f.is_file() and f.suffix in (".py", ".json", ".md")
        and f.name != "MANIFEST.json"   # exclude manifest itself
    )
    for f in files:
        h.update(f.name.encode())
        h.update(f.read_bytes())
    return f"sha256:{h.hexdigest()[:16]}"   # 16-char prefix, readable


def cmd_hash(folder: Path, write: bool = True) -> str:
    """Compute hash for a contribution folder and optionally write to MANIFEST."""
    folder = Path(folder)
    manifest_path = folder / "MANIFEST.json"

    digest = compute_hash(folder)

    if write and manifest_path.exists():
        with open(manifest_path) as f:
            manifest = json.load(f)
        manifest["hash"] = digest
        manifest["updated"] = date.today().isoformat()
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)
        print(f"  ✓ Hash updated in {manifest_path.name}: {digest}")
    else:
        print(f"  Hash: {digest}")

    return digest


# ── Validate ──────────────────────────────────────────────────────────────────

def cmd_validate(folder: Path) -> bool:
    """
    Validate a contribution folder. Returns True if valid.
    Prints all errors found.
    """
    folder = Path(folder)
    errors = []
    warnings = []

    print(f"\n  Validating: {folder.name}/")
    print(f"  {'─'*40}")

    # 1. Required files
    for fname in REQUIRED_FILES:
        if not (folder / fname).exists():
            errors.append(f"Missing required file: {fname}")
        else:
            print(f"  ✓ {fname}")

    # 2. models/ directory
    models_dir = folder / "models"
    if not models_dir.exists():
        errors.append("Missing models/ directory")
    else:
        model_files = list(models_dir.glob("*.json"))
        if not model_files:
            warnings.append("models/ is empty — add at least one example model")
        else:
            print(f"  ✓ models/ ({len(model_files)} models)")

    # 3. MANIFEST.json validity
    manifest_path = folder / "MANIFEST.json"
    manifest = None
    if manifest_path.exists():
        try:
            with open(manifest_path) as f:
                manifest = json.load(f)
        except json.JSONDecodeError as e:
            errors.append(f"MANIFEST.json is not valid JSON: {e}")

    if manifest:
        missing = [f for f in REQUIRED_MANIFEST_FIELDS if f not in manifest]
        if missing:
            errors.append(f"MANIFEST.json missing fields: {missing}")
        else:
            print(f"  ✓ MANIFEST.json (all required fields present)")

        # Version format
        v = manifest.get("version", "")
        parts = v.split(".")
        if len(parts) != 3 or not all(p.isdigit() for p in parts):
            errors.append(f"version must be MAJOR.MINOR.PATCH, got: '{v}'")

        # Domain consistency — only check if format.py defines formats directly
        # (reference implementations import from cell_format.py, so the
        # domain string lives there — this check applies to new contributions)
        declared_domain = manifest.get("domain", "")
        format_py = folder / "format.py"
        if format_py.exists() and declared_domain:
            content = format_py.read_text()
            defines_class = "class " in content and "FormatDefinition" in content
            if defines_class:
                if f'domain = "{declared_domain}"' not in content and \
                   f"domain = '{declared_domain}'" not in content:
                    warnings.append(
                        f"MANIFEST domain '{declared_domain}' not found in format.py — "
                        f"ensure format.py domain field matches"
                    )

        # Hash check
        expected_hash = manifest.get("hash", "")
        actual_hash   = compute_hash(folder)
        if expected_hash != actual_hash:
            warnings.append(
                f"Hash mismatch — run: python community/community_tools.py hash {folder.name}/"
                f"\n    Expected: {expected_hash}"
                f"\n    Actual:   {actual_hash}"
            )
        else:
            print(f"  ✓ Hash matches ({actual_hash})")

        # Semantic confidence on bridges
        bridges = manifest.get("bridges", [])
        if bridges:
            print(f"  ✓ Bridges declared: {bridges}")

    # 4. format.py imports cleanly
    format_py = folder / "format.py"
    if format_py.exists():
        try:
            spec = importlib.util.spec_from_file_location(
                f"community_{folder.name}_format", format_py
            )
            mod = importlib.util.module_from_spec(spec)
            sys.path.insert(0, str(REPO_ROOT))
            spec.loader.exec_module(mod)
            sys.path.pop(0)
            print(f"  ✓ format.py imports cleanly")
        except Exception as e:
            errors.append(f"format.py import error: {e}")

    # 5. Models validate
    if models_dir.exists():
        for mf in sorted(models_dir.glob("*.json")):
            try:
                with open(mf) as f:
                    model = json.load(f)
                required = ["id", "name", "domain", "description"]
                missing_m = [r for r in required if r not in model]
                if missing_m:
                    errors.append(f"Model {mf.name} missing fields: {missing_m}")
                else:
                    print(f"  ✓ models/{mf.name}")
            except json.JSONDecodeError as e:
                errors.append(f"Model {mf.name} is not valid JSON: {e}")

    # Report
    print()
    if warnings:
        for w in warnings:
            print(f"  ⚠ {w}")
    if errors:
        print()
        for e in errors:
            print(f"  ✗ {e}")
        print(f"\n  Result: INVALID ({len(errors)} errors, {len(warnings)} warnings)")
        return False
    else:
        print(f"  Result: VALID ✓" +
              (f" ({len(warnings)} warnings)" if warnings else ""))
        return True


# ── Register ──────────────────────────────────────────────────────────────────

def cmd_register() -> None:
    """
    Rebuild REGISTRY.md from all MANIFEST.json files in community/.
    Also validates each contribution hash before including it.
    """
    contributions = []

    for manifest_path in sorted(COMMUNITY.rglob("MANIFEST.json")):
        folder = manifest_path.parent
        if folder == COMMUNITY:
            continue
        try:
            with open(manifest_path) as f:
                manifest = json.load(f)
            contributions.append((folder, manifest))
        except Exception as e:
            print(f"  ⚠ Skipping {folder.name}: {e}")

    # Group by domain
    by_domain: dict[str, list] = {}
    for folder, m in contributions:
        domain = m.get("domain", "Unknown")
        by_domain.setdefault(domain, []).append((folder, m))

    lines = [
        "# UniCell Community Registry",
        "",
        f"*Auto-generated by community_tools.py — {date.today().isoformat()}*",
        f"*{len(contributions)} contribution(s) across "
        f"{len(by_domain)} domain(s)*",
        "",
        "---",
        "",
    ]

    for domain in sorted(by_domain):
        lines.append(f"## {domain}")
        lines.append("")
        for folder, m in sorted(by_domain[domain], key=lambda x: x[1].get("name","")):
            # Hash check
            actual = compute_hash(folder)
            hash_ok = actual == m.get("hash", "")
            hash_badge = "✓" if hash_ok else "⚠ hash mismatch"

            lines.append(f"### {m.get('name', folder.name)}")
            lines.append("")
            lines.append(f"| Field | Value |")
            lines.append(f"|-------|-------|")
            lines.append(f"| Folder | `community/{folder.name}/` |")
            lines.append(f"| Version | {m.get('version','-')} |")
            lines.append(f"| Author | {m.get('author','-')} |")
            lines.append(f"| License | {m.get('license','-')} |")
            lines.append(f"| Created | {m.get('created','-')} |")
            lines.append(f"| Updated | {m.get('updated','-')} |")
            lines.append(f"| Requires | {m.get('requires','-')} |")
            lines.append(f"| Hash | `{m.get('hash','-')}` {hash_badge} |")
            lines.append("")
            lines.append(f"{m.get('description','')}")
            lines.append("")

            if m.get("formats"):
                lines.append(f"**Formats:** {', '.join(f'`{f}`' for f in m['formats'])}")
                lines.append("")
            if m.get("models"):
                lines.append(f"**Models:** {', '.join(f'`{mid}`' for mid in m['models'])}")
                lines.append("")
            if m.get("bridges"):
                lines.append(f"**Bridges:** {', '.join(f'`{b}`' for b in m['bridges'])}")
                lines.append("")
            if m.get("tags"):
                lines.append(f"**Tags:** {', '.join(m['tags'])}")
                lines.append("")
            if m.get("homepage"):
                lines.append(f"**Homepage:** {m['homepage']}")
                lines.append("")

            lines.append("---")
            lines.append("")

    REGISTRY.write_text("\n".join(lines))
    print(f"  ✓ REGISTRY.md updated ({len(contributions)} contributions)")


# ── Search ────────────────────────────────────────────────────────────────────

def cmd_search(keyword: str) -> None:
    """Search all MANIFEST.json files for a keyword."""
    keyword = keyword.lower()
    results = []

    for manifest_path in sorted(COMMUNITY.rglob("MANIFEST.json")):
        folder = manifest_path.parent
        if folder == COMMUNITY:
            continue
        try:
            with open(manifest_path) as f:
                manifest = json.load(f)
        except Exception:
            continue

        # Search in name, description, domain, tags, formats, models
        haystack = " ".join([
            manifest.get("name", ""),
            manifest.get("description", ""),
            manifest.get("domain", ""),
            " ".join(manifest.get("tags", [])),
            " ".join(manifest.get("formats", [])),
            " ".join(manifest.get("models", [])),
        ]).lower()

        if keyword in haystack:
            results.append((folder, manifest))

    if not results:
        print(f"  No results for '{keyword}'")
        return

    print(f"\n  Results for '{keyword}' ({len(results)} found):")
    print()
    for folder, m in results:
        print(f"  {m.get('name','?'):<20} [{m.get('domain','?'):<12}] "
              f"v{m.get('version','?')}  —  {m.get('description','')}")
        matching_models = [mid for mid in m.get("models", [])
                           if keyword in mid.lower()]
        if matching_models:
            print(f"    Models: {', '.join(matching_models)}")
        matching_formats = [f for f in m.get("formats", [])
                            if keyword in f.lower()]
        if matching_formats:
            print(f"    Formats: {', '.join(matching_formats)}")
        print()


# ── Scaffold ──────────────────────────────────────────────────────────────────

def cmd_new(name: str) -> None:
    """Scaffold a new contribution folder with all required files."""
    name_clean = name.lower().replace(" ", "_").replace("-", "_")
    folder = COMMUNITY / name_clean

    if folder.exists():
        print(f"  ✗ Folder already exists: {folder}")
        return

    folder.mkdir()
    (folder / "models").mkdir()

    domain_display = name.title() + "Trix" if not name.endswith("trix") else name.title()

    # format.py
    (folder / "format.py").write_text(f'''"""
{domain_display} format definition for UniCell.

Edit this file to define your domain's internal representation.
Read docs/FORMAT_DEFINITION_GUIDE.md before starting.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from cell_format import FormatDefinition, FormatRegistry


class {domain_display}_Format(FormatDefinition):
    """
    {domain_display} internal format.

    TODO: describe your domain and why this packing makes sense.
    """
    name             = "{domain_display}"
    description      = "TODO: one sentence description"
    domain           = "{domain_display}"
    bits_per_symbol  = 8        # TODO: choose bits per symbol
    symbols_per_word = 4        # 32 / bits_per_symbol
    cell_words       = 1        # cells per logical value
    boundary_in      = "{name_clean.upper()}_PACK"
    boundary_out     = "{name_clean.upper()}_UNPACK"
    valid_tiles      = [
        # TODO: list tile names valid within this format
        # "{name_clean.upper()}_OP1",
        # "{name_clean.upper()}_OP2",
    ]
    symbol_lut = {{
        # TODO: map external symbols to internal codes
        # "A": 1, "B": 2,
    }}
    CONSTANTS = {{
        # TODO: fixed values this domain needs (preloaded into cells)
        # "my_constant": 42,
    }}
    constraints = {{
        "symbol_range": (1, 255),
    }}
    notes = "TODO: extended notes"


# Register on import
FormatRegistry.get_default().register_class({domain_display}_Format)
''')

    # README.md
    (folder / "README.md").write_text(f'''# {domain_display}

TODO: describe this domain and what it computes.

## Format

TODO: describe the internal representation.

## Tiles

TODO: list the valid tiles and what they do.

## Models

TODO: describe the example models.

## Constants

TODO: list the domain constants and their values.

## Usage

```python
from cell_format import FormatRegistry
reg = FormatRegistry.get_default()

# Import this folder to register the format
import importlib.util, sys
spec = importlib.util.spec_from_file_location(
    "{name_clean}_format",
    "community/{name_clean}/format.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

# Now the format is available
fmt = reg.get("{domain_display}")
print(fmt.to_dict())
```

## Author

TODO: your name / handle

## License

MIT
''')

    # Example model
    (folder / "models" / "example.json").write_text(json.dumps({
        "id":          f"{name_clean}_example",
        "name":        f"{domain_display} Example",
        "domain":      domain_display,
        "format":      domain_display,
        "description": "TODO: describe this model",
        "author":      "TODO: your name",
        "version":     "0.1.0",
        "created":     date.today().isoformat(),
        "base_model":  None,
        "parameters":  {
            "size":  {"type": "int", "default": 32, "label": "Size"},
            "steps": {"type": "int", "default": 50, "label": "Steps"},
        },
        "tile_config": {},
        "tags":        [name_clean, "example"],
        "notes":       "",
    }, indent=2))

    # MANIFEST.json
    manifest = {
        "name":        domain_display,
        "domain":      domain_display,
        "version":     "0.1.0",
        "created":     date.today().isoformat(),
        "updated":     date.today().isoformat(),
        "author":      "TODO: your name",
        "license":     "MIT",
        "description": "TODO: one sentence description",
        "requires":    "imago-vm>=0.2.0",
        "formats":     [domain_display],
        "models":      [f"{name_clean}_example"],
        "bridges":     [],
        "hash":        "TODO: run community_tools.py hash to fill this",
        "tags":        [name_clean],
        "homepage":    "",
        "contact":     "",
    }
    (folder / "MANIFEST.json").write_text(json.dumps(manifest, indent=2))

    print(f"\n  ✓ Scaffolded: community/{name_clean}/")
    print(f"    {folder/'README.md'}")
    print(f"    {folder/'format.py'}")
    print(f"    {folder/'MANIFEST.json'}")
    print(f"    {folder/'models'/'example.json'}")
    print(f"\n  Next steps:")
    print(f"    1. Edit community/{name_clean}/format.py — define your format")
    print(f"    2. Edit community/{name_clean}/README.md — document it")
    print(f"    3. Add models to community/{name_clean}/models/")
    print(f"    4. python community/community_tools.py hash community/{name_clean}/")
    print(f"    5. python community/community_tools.py validate community/{name_clean}/")
    print(f"    6. python community/community_tools.py register")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="community_tools.py",
        description="UniCell community contribution tools",
    )
    sub = parser.add_subparsers(dest="cmd")

    p_val = sub.add_parser("validate", help="Validate a contribution folder")
    p_val.add_argument("folder", help="Path to contribution folder")

    p_hash = sub.add_parser("hash", help="Compute and update hash")
    p_hash.add_argument("folder", help="Path to contribution folder")

    sub.add_parser("register", help="Rebuild REGISTRY.md")

    p_search = sub.add_parser("search", help="Search registry")
    p_search.add_argument("keyword", help="Search keyword")

    p_new = sub.add_parser("new", help="Scaffold a new contribution")
    p_new.add_argument("name", help="Domain name (e.g. 'geology', 'audio')")

    args = parser.parse_args()

    if args.cmd == "validate":
        ok = cmd_validate(Path(args.folder))
        sys.exit(0 if ok else 1)
    elif args.cmd == "hash":
        cmd_hash(Path(args.folder))
    elif args.cmd == "register":
        cmd_register()
    elif args.cmd == "search":
        cmd_search(args.keyword)
    elif args.cmd == "new":
        cmd_new(args.name)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
