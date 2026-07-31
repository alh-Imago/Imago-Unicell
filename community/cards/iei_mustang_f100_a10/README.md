# IEI Mustang-F100-A10

A **card descriptor** -- the hardware capability profile a card-aware loader
consults when placing models: total fabric cell budget, DSP block count,
RAM block count. Not a model contribution; this is target-machine data.

## How to populate

Edit `card.json` with your card's actual capabilities (probe via the ISSP/
debug readback path, or read them off the datasheet/Quartus fit report):

```json
{
  "card_type":   "IEI Mustang-F100-A10",
  "fpga_part":   "TODO: e.g. 10AX066H2F34E2SG",
  "total_cells": 0,
  "dsp_blocks":  0,
  "ram_blocks":  0,
  "notes":       ""
}
```

## Submit

```bash
python3 community/community_tools.py hash community/cards/iei_mustang_f100_a10/
python3 community/community_tools.py validate community/cards/iei_mustang_f100_a10/
python3 community/community_tools.py register
```

If a reference file for your card already exists, check the registry first --
using an existing one saves you the characterization work.

## Author

TODO: your name / handle

## License

MIT
