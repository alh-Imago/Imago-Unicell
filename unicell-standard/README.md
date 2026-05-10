# unicell-standard — Historical Archive

This directory contains the v1.2 reference snapshot of the Claudette standard
variant, preserved for historical reference.

The **active standard variant** is the repository root (`/`).

## Archive contents

```
archive/
  claudette_v1.2.patch         — diff from v1.1 to v1.2
  claudette_v1_documentation.md — v1 architecture documentation
  core_boot.img.gz             — v1.2 boot image snapshot
  update_claudette_v1.2.sh     — v1.2 update script
block_defs                     — v1 block definitions (block_defs DSL)
```

## Why this folder exists

The repository originally contained three variant directories:
- `unicell-standard/` — the reference implementation (now: root `/`)
- `unicell-latch/` — latch model (still active, self-contained)
- `unicell-edge/` — edge model (still active, self-contained)

In v2 the standard variant moved to the root. This directory is kept as
an archive of the v1.2 release snapshot.
