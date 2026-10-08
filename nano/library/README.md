# The Composer's library

There are two libraries. `nano/library_std/` is the **standard library**,
built by `tools/composer_stdlib_v1.py` and read-only in the Composer. This
folder is **your library**. Every model can have reference test vectors
beside it (`<model>.test.json`). Save to library writes them: from the
values you just stepped through if any, otherwise from 8 values per input.
A block placed from a model shows whether it is still standard and, once
edited, whether its function still matches those vectors.

ICM files saved here with the Composer's **Save to library** button (front panel `/composer`) are
library models. Any design can place one as a single **block**: its cells move as one unit and its
`io_name` cells are the block's ports, where joins attach. The examples in `nano/examples/` are
listed after these.

Set `IMAGO_LIBRARY` to keep the library somewhere else. A model is an ordinary ICM v3 file, so it can
be shared by copying the file. A model that itself holds blocks is saved as
ICM-VIX (its blocks are placements), and is placed as one block, flat inside.
