# User Library — Sharing and Reusing Programs

The user library is a personal folder of `.icm` programs that persists
across sessions and is available everywhere — the CLI, the Python API,
and the workbench.

---

## Location

```
~/.imago/library/
    README.md           — this file
    logic/              — gates, mux, comparators
    arithmetic/         — adders, multipliers, counters
    neural/             — LIF neurons, Izhikevich, cascades
    sorting/            — sort networks
    custom/             — anything else
```

This is your personal library. It is never modified by `pip install imago-vm`
or by any project update. Your programs stay there permanently.

---

## First-time setup

```bash
imago init
```

Creates `~/.imago/library/` with category subdirectories and a README.
Safe to run multiple times — never overwrites existing files.

---

## Adding programs

```bash
# Add to the default category (custom/)
imago library add my_adder.icm

# Add to a specific category
imago library add my_adder.icm --category arithmetic
imago library add lif_custom.icm --category neural
imago library add my_comparator.icm --category logic
```

The file is copied into the library. The original is unchanged.
The program name in the library is the filename without `.icm`.

---

## Running library programs

```bash
# By name — the CLI searches: file path → bundled examples → user library
imago run my_adder
imago run my_adder a=5 b=3

# Run a bundled example (same command)
imago run not_gate a=1
```

---

## Listing and managing

```bash
imago library list               # show all programs with cell counts
imago library remove my_adder    # remove by name
imago library path               # print ~/.imago/library path
imago info                       # shows library location and count
```

---

## Python API

```python
import imago

# See what's in the library
print(imago.library_programs())   # ['my_adder', 'lif_custom', ...]
print(imago.library_path())       # /home/user/.imago/library

# Load and run a library program
vm = imago.VM()
vm.load_library("my_adder")
print(vm.run(a=5, b=3))          # {"result": 8}

# Or one-shot
result = imago.run_icm(
    imago.library_path() + "/arithmetic/my_adder.icm",
    inputs={"a": 5, "b": 3}
)
```

---

## Sharing programs

An `.icm` file is completely self-contained — share it directly:

```bash
# Share a file
cp ~/.imago/library/arithmetic/my_adder.icm ./my_adder.icm
# ... send to someone ...

# They add it to their library
imago library add my_adder.icm --category arithmetic
imago run my_adder a=5 b=3
```

No dependencies, no version pinning. The `.icm` contains the complete
cell configuration and runs identically on any VM, FPGA, or ASIC.

---

## Community contributions

The repository has a structured community contribution space at `community/`.
Two contribution kinds are supported: **trix-domain** (a full FormatDefinition
with format.py, models, bridges) and **raw-model** (raw `.icm` or builder
library files, no FormatDefinition required).

Use `community_tools.py` to contribute:

```bash
# Validate your contribution
python community/community_tools.py validate my_contribution/

# Scaffold a new raw-model contribution
python community/community_tools.py new --kind raw-model --name my_tiles

# Scaffold a new Trix domain
python community/community_tools.py new --kind trix-domain --name MyTrix

# Search existing contributions
python community/community_tools.py search dna

# Register a contribution (adds to REGISTRY.md)
python community/community_tools.py register my_contribution/
```

The contribution index is at `community/REGISTRY.md`.
See `community/mathtrix/` for the reference trix-domain implementation and
`examples/walker/` for the raw-model authoring route (builder → walker → hashed `.icm`).

To contribute a program:
1. Scaffold with `community_tools.py new`
2. Add your models/`.icm` files
3. Run `community_tools.py validate` — must pass
4. Open a PR to https://github.com/alh-Imago/Imago-Unicell

---

## What makes a good library program

A library program should:
- Have named `inputs` and `outputs` (not just raw addresses)
- Have a `description` field explaining what it does
- Have `tags` for discoverability
- Work correctly across all inputs (not just the test cases it was built with)

See [docs/ICM_FORMAT.md](ICM_FORMAT.md) for the full `.icm` specification.

Example of a well-formed library `.icm`:

```json
{
  "name": "my_adder",
  "description": "32-bit integer adder using Kogge-Stone. Inputs: a, b. Output: result.",
  "tags": ["arithmetic", "int32", "addition"],
  "inputs":  {"a": 4096, "b": 4128},
  "outputs": {"result": 8192},
  "input_types":  {"a": "numeric", "b": "numeric"},
  "output_types": {"result": "numeric"},
  "models": ["INT32_ADD"],
  "records": [ ... ]
}
```

---

## Library vs bundled examples

| | Bundled examples | User library |
|---|---|---|
| Location | Inside `imago` package | `~/.imago/library/` |
| Survives `pip upgrade` | No | **Yes** |
| Editable | No | **Yes** |
| Shared by default | Yes (with package) | No (you share explicitly) |
| Available via CLI | `imago run not_gate` | `imago run my_program` |

The bundled examples (`not_gate`, `adder_int32`, `lif_cascade`, etc.)
are included in the package for first-run demos. Your library is for
programs you create and want to keep.
