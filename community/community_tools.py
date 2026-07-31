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

# ── Contribution kinds ────────────────────────────────────────────────────────
# Trix-domain contributions define a FormatDefinition (format.py + domain).
# Raw-model contributions are models OUTSIDE the Trix system — individual .icm
# tiles/programs or a tile-builder library — with no FormatDefinition. They
# carry .icm files in models/ instead, each with a record_hash the strict
# loader requires (the same hash the walker produces).
KIND_TRIX = "trix-domain"
KIND_RAW  = "raw-model"
KIND_CARD = "card-descriptor"
VALID_KINDS = (KIND_TRIX, KIND_RAW, KIND_CARD)

# Card descriptors are grouped under one shared subfolder (community/cards/)
# rather than sitting flat alongside domain/raw-model contributions -- keeps
# them structurally separate (a card profile isn't a model, it's a target's
# hardware capabilities) while still being discovered by the SAME rglob-based
# register/search machinery, so it's one searchable resource either way.
CARDS_SUBDIR = "cards"

REQUIRED_FILES_BY_KIND = {
    KIND_TRIX: ["README.md", "format.py", "MANIFEST.json"],
    KIND_RAW:  ["README.md", "MANIFEST.json"],          # no format.py
    KIND_CARD: ["README.md", "MANIFEST.json", "card.json"],  # capability data lives in card.json
}
REQUIRED_MANIFEST_COMMON = [
    "name", "version", "created", "updated",
    "author", "license", "description", "hash", "tags",
    # "kind" is optional: absent -> trix-domain (back-compat). The raw-model
    # scaffold always writes it; a raw contribution that omits it would be
    # validated as trix-domain and fail on the missing format.py, which is the
    # correct signal to declare kind.
]
REQUIRED_MANIFEST_BY_KIND = {
    KIND_TRIX: ["domain", "requires", "formats", "models", "bridges"],
    KIND_RAW:  ["models"],                              # list of .icm models
    KIND_CARD: [],                                       # card.json carries the real content
}

# card.json required top-level fields -- deliberately minimal for now (the
# loader's actual consumption needs may refine this schema; adding fields
# later is additive/non-breaking, same discipline as everywhere else in this
# format). card_type/fpga_part identify the card; total_cells is the fabric
# budget the loader checks the "doesn't fit at all" hard case against;
# dsp_blocks/ram_blocks are counts the card-aware allocator claims against,
# largest-model-first, until exhausted.
REQUIRED_CARD_FIELDS = ["card_type", "fpga_part", "total_cells", "dsp_blocks", "ram_blocks"]


def _canon_records(records):
    """Canonical record string — byte-identical to the walker + composer canonR
    ({gs,in,init,out} order, no whitespace)."""
    return json.dumps(
        [{"gs": r["gs"], "in": r["in"], "init": r.get("init"), "out": r["out"]}
         for r in records],
        separators=(",", ":"),
    )


def validate_icm(path: Path):
    """Validate a raw .icm model file. Returns (ok, errors).

    dsp_blocks_used/ram_blocks_used are OPTIONAL fields (default 0 if
    absent) -- existing .icm files generated before these fields existed
    stay valid unchanged. When present, they must be non-negative ints,
    same card-aware-allocation meaning as ModelSpec's fields.
    """
    errs = []
    try:
        with open(path) as f:
            d = json.load(f)
    except Exception as e:
        return False, [f"{path.name}: not valid JSON: {e}"]
    for fld in ("program_id", "records", "cell_count"):
        if fld not in d:
            errs.append(f"{path.name}: missing '{fld}'")
    for fld in ("dsp_blocks_used", "ram_blocks_used"):
        if fld in d and (not isinstance(d[fld], int) or d[fld] < 0):
            errs.append(f"{path.name}: '{fld}' must be a non-negative integer, got {d[fld]!r}")
    recs = d.get("records", [])
    if "cell_count" in d and d["cell_count"] != len(recs):
        errs.append(f"{path.name}: cell_count {d['cell_count']} != {len(recs)} records")
    rh = d.get("record_hash")
    if not rh:
        errs.append(f"{path.name}: missing record_hash — the strict loader will refuse it "
                    f"(regenerate with the walker, which writes it)")
    elif recs:
        expect = hashlib.sha256(_canon_records(recs).encode("utf-8")).hexdigest()
        if rh != expect:
            errs.append(f"{path.name}: record_hash mismatch "
                        f"(stored {rh[:12]}…, computed {expect[:12]}…)")
    return (len(errs) == 0), errs


def validate_card_json(path: Path):
    """Validate a card.json capability descriptor. Returns (ok, errors)."""
    errs = []
    try:
        with open(path) as f:
            d = json.load(f)
    except Exception as e:
        return False, [f"{path.name}: not valid JSON: {e}"]
    for fld in REQUIRED_CARD_FIELDS:
        if fld not in d:
            errs.append(f"{path.name}: missing '{fld}'")
    if "total_cells" in d and (not isinstance(d["total_cells"], int) or d["total_cells"] <= 0):
        errs.append(f"{path.name}: 'total_cells' must be a positive integer")
    if "dsp_blocks" in d and (not isinstance(d["dsp_blocks"], int) or d["dsp_blocks"] < 0):
        errs.append(f"{path.name}: 'dsp_blocks' must be a non-negative integer")
    if "ram_blocks" in d and (not isinstance(d["ram_blocks"], int) or d["ram_blocks"] < 0):
        errs.append(f"{path.name}: 'ram_blocks' must be a non-negative integer")
    return (len(errs) == 0), errs


# ── Hash ──────────────────────────────────────────────────────────────────────

def compute_hash(folder: Path) -> str:
    """
    Compute SHA-256 over all .py, .json, .md files in a folder.
    Files are sorted for determinism. Hash excludes the hash field itself.
    """
    h = hashlib.sha256()
    files = sorted(
        f for f in folder.rglob("*")
        if f.is_file() and f.suffix in (".py", ".json", ".md", ".icm")
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

    # Peek manifest for contribution kind (default trix-domain, back-compat)
    kind = KIND_TRIX
    mpath0 = folder / "MANIFEST.json"
    if mpath0.exists():
        try:
            with open(mpath0) as f:
                kind = json.load(f).get("kind", KIND_TRIX)
        except Exception:
            pass
    if kind not in VALID_KINDS:
        errors.append(f"Unknown kind '{kind}' (valid: {', '.join(VALID_KINDS)})")
        kind = KIND_TRIX
    print(f"  kind: {kind}")

    # 1. Required files (per kind)
    for fname in REQUIRED_FILES_BY_KIND[kind]:
        if not (folder / fname).exists():
            errors.append(f"Missing required file: {fname}")
        else:
            print(f"  ✓ {fname}")

    # 2. models/ directory (not applicable to card descriptors -- their
    # content is card.json, validated separately in step 2b below)
    if kind != KIND_CARD:
        models_dir = folder / "models"
        model_glob = "*.icm" if kind == KIND_RAW else "*.json"
        if not models_dir.exists():
            errors.append("Missing models/ directory")
        else:
            model_files = list(models_dir.glob(model_glob))
            if not model_files:
                warnings.append(f"models/ has no {model_glob} files — add at least one")
            else:
                print(f"  ✓ models/ ({len(model_files)} {model_glob})")
    else:
        models_dir = None  # not used for cards, keeps step 5 below simple

    # 2b. card.json (card descriptors only)
    if kind == KIND_CARD:
        card_path = folder / "card.json"
        if card_path.exists():
            ok, errs = validate_card_json(card_path)
            if ok:
                print(f"  ✓ card.json (all required fields present)")
            else:
                errors.extend(errs)
        # (missing card.json is already caught by the REQUIRED_FILES_BY_KIND
        # check above, no need to duplicate the error here)

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
        required_fields = REQUIRED_MANIFEST_COMMON + REQUIRED_MANIFEST_BY_KIND[kind]
        missing = [f for f in required_fields if f not in manifest]
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

    # 4. format.py imports cleanly (trix-domain only)
    format_py = folder / "format.py"
    if kind == KIND_TRIX and format_py.exists():
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

    # 5. Models validate (per kind) -- not applicable to card descriptors
    if models_dir is not None and models_dir.exists():
        if kind == KIND_RAW:
            for mf in sorted(models_dir.glob("*.icm")):
                ok, errs = validate_icm(mf)
                if ok:
                    print(f"  ✓ models/{mf.name} (.icm valid, hash verified)")
                else:
                    errors.extend(errs)
        else:
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
        if m.get("kind") == KIND_CARD:
            domain = "Card Descriptors"
        else:
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
            lines.append(f"| Folder | `community/{folder.relative_to(COMMUNITY)}/` |")
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
            if m.get("kind") == KIND_CARD:
                card_path = folder / "card.json"
                if card_path.exists():
                    try:
                        with open(card_path) as f:
                            card = json.load(f)
                        lines.append(f"| Card Type | {card.get('card_type','-')} |")
                        lines.append(f"| FPGA Part | {card.get('fpga_part','-')} |")
                        lines.append(f"| Total Cells | {card.get('total_cells','-')} |")
                        lines.append(f"| DSP Blocks | {card.get('dsp_blocks','-')} |")
                        lines.append(f"| RAM Blocks | {card.get('ram_blocks','-')} |")
                        lines.append("")
                    except Exception:
                        pass
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
        haystack_parts = [
            manifest.get("name", ""),
            manifest.get("description", ""),
            manifest.get("domain", ""),
            " ".join(manifest.get("tags", [])),
            " ".join(manifest.get("formats", [])),
            " ".join(manifest.get("models", [])),
        ]
        if manifest.get("kind") == KIND_CARD:
            card_path = folder / "card.json"
            if card_path.exists():
                try:
                    with open(card_path) as f:
                        card = json.load(f)
                    haystack_parts.append(card.get("card_type", ""))
                    haystack_parts.append(card.get("fpga_part", ""))
                except Exception:
                    pass
        haystack = " ".join(haystack_parts).lower()

        if keyword in haystack:
            results.append((folder, manifest))

    if not results:
        print(f"  No results for '{keyword}'")
        return

    print(f"\n  Results for '{keyword}' ({len(results)} found):")
    print()
    for folder, m in results:
        tag = "card" if m.get("kind") == KIND_CARD else m.get("domain", "?")
        print(f"  {m.get('name','?'):<20} [{tag:<12}] "
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

def cmd_new(name: str, kind: str = KIND_TRIX) -> None:
    """Scaffold a new contribution folder with all required files."""
    name_clean = name.lower().replace(" ", "_").replace("-", "_")
    # Card descriptors are grouped under their own subfolder, kept separate
    # from domain/raw-model contributions, but still discovered by the same
    # rglob-based register/search machinery -- one searchable resource.
    if kind == KIND_CARD:
        folder = COMMUNITY / CARDS_SUBDIR / name_clean
    else:
        folder = COMMUNITY / name_clean

    if folder.exists():
        print(f"  ✗ Folder already exists: {folder}")
        return

    # ── Card-descriptor scaffold: capability data in card.json, no format.py,
    # no models/ -- lives under community/cards/<name>/ ──────────────────────
    if kind == KIND_CARD:
        folder.mkdir(parents=True)
        (folder / "README.md").write_text(f"""# {name}

A **card descriptor** -- the hardware capability profile a card-aware loader
consults when placing models: total fabric cell budget, DSP block count,
RAM block count. Not a model contribution; this is target-machine data.

## How to populate

Edit `card.json` with your card's actual capabilities (probe via the ISSP/
debug readback path, or read them off the datasheet/Quartus fit report):

```json
{{
  "card_type":   "{name}",
  "fpga_part":   "TODO: e.g. 10AX066H2F34E2SG",
  "total_cells": 0,
  "dsp_blocks":  0,
  "ram_blocks":  0,
  "notes":       ""
}}
```

## Submit

```bash
python3 community/community_tools.py hash community/{CARDS_SUBDIR}/{name_clean}/
python3 community/community_tools.py validate community/{CARDS_SUBDIR}/{name_clean}/
python3 community/community_tools.py register
```

If a reference file for your card already exists, check the registry first --
using an existing one saves you the characterization work.

## Author

TODO: your name / handle

## License

MIT
""")
        (folder / "card.json").write_text(json.dumps({
            "card_type":   name,
            "fpga_part":   "TODO",
            "total_cells": 0,
            "dsp_blocks":  0,
            "ram_blocks":  0,
            "notes":       "",
        }, indent=2))
        manifest = {
            "name":        name,
            "kind":        KIND_CARD,
            "version":     "0.1.0",
            "created":     date.today().isoformat(),
            "updated":     date.today().isoformat(),
            "author":      "TODO: your name",
            "license":     "MIT",
            "description": "TODO: one sentence description of this card",
            "hash":        "TODO: run community_tools.py hash to fill this",
            "tags":        [name_clean, "card"],
            "homepage":    "",
            "contact":     "",
        }
        (folder / "MANIFEST.json").write_text(json.dumps(manifest, indent=2))
        print(f"\n  ✓ Scaffolded card descriptor: community/{CARDS_SUBDIR}/{name_clean}/")
        print(f"    {folder/'README.md'}")
        print(f"    {folder/'card.json'}  (fill in the real capability values)")
        print(f"    {folder/'MANIFEST.json'}")
        return

    # ── Raw-model (non-Trix) scaffold: no format.py, .icm models in models/ ──
    if kind == KIND_RAW:
        folder.mkdir()
        (folder / "models").mkdir()
        (folder / "README.md").write_text(f"""# {name}

A **non-Trix** model contribution — individual `.icm` models or a tile library,
with no `FormatDefinition`. These are models *outside* the Trix system.

## How to populate

Generate `.icm` with the walker (it writes a valid `record_hash`, which the
strict loader requires) and drop them in `models/`:

```bash
# from a built-in tile
python3 examples/walker/walk_tiles.py --tile MIF_MUX --out community/{name_clean}/models

# or your whole builder library, the fp_tiles.py way
python3 examples/walker/walk_tiles.py --module my_models.py --out community/{name_clean}/models
```

## Submit

```bash
python3 community/community_tools.py hash community/{name_clean}/
python3 community/community_tools.py validate community/{name_clean}/
python3 community/community_tools.py register
```

## Author

TODO: your name / handle

## License

MIT
""")
        manifest = {
            "name":        name,
            "kind":        KIND_RAW,
            "version":     "0.1.0",
            "created":     date.today().isoformat(),
            "updated":     date.today().isoformat(),
            "author":      "TODO: your name",
            "license":     "MIT",
            "description": "TODO: one sentence description",
            "models":      [],   # filled with .icm filenames you add
            "hash":        "TODO: run community_tools.py hash to fill this",
            "tags":        [name_clean],
            "homepage":    "",
            "contact":     "",
        }
        (folder / "MANIFEST.json").write_text(json.dumps(manifest, indent=2))
        print(f"\n  ✓ Scaffolded raw-model contribution: community/{name_clean}/")
        print(f"    {folder/'README.md'}")
        print(f"    {folder/'MANIFEST.json'}")
        print(f"    {folder/'models'}/  (drop walker-generated .icm here)")
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
        "kind":        KIND_TRIX,
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
    p_new.add_argument("--kind", choices=list(VALID_KINDS), default=KIND_TRIX,
                       help="trix-domain (FormatDefinition) or raw-model (non-Trix .icm/tiles)")

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
        cmd_new(args.name, args.kind)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
