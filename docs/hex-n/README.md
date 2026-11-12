# Hex-N

**This branch is not intended to be merged into `main`.** Hex-N is a separate project that shares lineage and some ideas with Imago UniCell, but it is its own architecture with its own direction. It lives on this branch for convenience. If GitHub offers a pull request against `main`, ignore it.

Rewritten 12 Nov 2026. The earlier README is kept as `README_OLD_v1.md`.

## What Hex-N is

A set of small hardware designs for recognising patterns in streams of events, built from counting and adding only (no multipliers), taught on the PC and run on an FPGA. It began in October 2026 as a hex-cell neuron idea on a Tang Nano 20K and now runs on a Kintex-7 card. Alan Hill designs it; the logic, models and records are written with Claude.

Four models have come out of the work. Each has its own base document.

| Model | What it is | Where it stands | Base document |
|---|---|---|---|
| **1. The layered model** | Nested layers: detectors outside, history and prediction inside, a strategist that looks ahead, a helper network and a batch judge. Played Connect Four and draughts | Layers 1 and 2, the batch judge and the memory tier are built and ran on boards. Layers 3, 4 and the helper are Python models | [`MODEL_1_LAYERED_v1.md`](MODEL_1_LAYERED_v1.md) |
| **2. The detector system and the speech chain** | Detectors with three-valued weights, taught by counting; widened into a chain that recognises spoken digits | **On the Kintex card, on real data: 936 of 1,079 test recordings right (86.7%), every digit equal to the Python reference** | [`MODEL_2_DETECTOR_v1.md`](MODEL_2_DETECTOR_v1.md) |
| **3. The neural bus network** | Neuron-like cells on small shared buses; the answer is a map of which cells fired | Works on made-up test patterns; built as logic and loaded on the card; at chance on real speech | [`MODEL_3_NEURAL_BUS_v1.md`](MODEL_3_NEURAL_BUS_v1.md) |
| **4. The upper logic** | Stored maps beside the cells, four banks around a shared memory (the tile), a monitor, an input check, a store for anomalies, identification by parts | Python models on test patterns only. Does well what the recognisers cannot (missing parts, confidence, novelty); did not improve the speech chain | [`MODEL_4_UPPER_LOGIC_v1.md`](MODEL_4_UPPER_LOGIC_v1.md) |

## The short version of what has been shown

- **Detection works on real data and on real hardware.** The speech chain on the card gives exactly the reference result, and from on-chip memory it takes 286 clocks per recording (counted on the chip, equal to the simulation to the clock). At the board's nominal 50 MHz that is about 174,000 recordings per second, a computed figure; over JTAG it is fed at 74 per second, so the input path is the limit.
- **The detector's ceiling on this task is known.** "One" is heard as "nine" in 36 of its 40 errors. A memory on top of the chain, a second look, and several templates per digit were each tried and none lifted the 86.7%.
- **The cell network recognises damaged versions of patterns it was taught** (95 / 90 / 75 / 44% right with 10 / 30 / 50 / 70% of the input dropped) but adds nothing with depth, and its maps carried no usable information on real speech.
- **The upper logic fills in what is missing.** In the models a bank that is nearly blind goes from 15% to 87% right with the help of the other three, and to 95% when each bank's vote is weighted by a simple check of its own input; a hidden weak pattern is found in the noise by counting what comes back; a thing is named from its parts (99.9%), also with one part missing (98.6%), and a changed or unknown part is reported as such.
- **What is not shown:** the upper logic on real data or in hardware; the layers run together as one system; any learning on the chip; live input (the front end that turns sound into events runs on the PC).

## Hardware

| Board | Used for |
|---|---|
| Tang Nano 20K (Gowin GW2AR-18) with an ESP32 front end | The first detectors, the batch judge and the open unit, confirmed on the board stage by stage (`OPEN_UNIT_v1.md`, `FRONT_END_UNIT_v1.md`) |
| Kintex-7 card YPCB-00338-1P1 (XC7K480T), open tools (openXC7), JTAG | The base: two pattern arrays, the batch judge, stores and, since 11 Nov 2026, the speech chain and its event memory (`HEXN_KINTEX_BASE_PICTURE_v1.md`, `HEXN_SPEECH_CHAIN_KINTEX_v1.md`); the bus network as a stand-alone build |

A real data port (PCIe) waits for another card and PC.

## Where the records are

| File | What it holds |
|---|---|
| `HEXN_DESIGN.md` | The ledger: every decision, measurement and correction, dated, append-only |
| `HEXN_DIRECTION_SCOPING_v1.md` | The direction document: numbered sections (100 so far) with each idea, test, result and reading, including the ones that failed |
| The four `MODEL_*_v1.md` files | The base documents: how each model is built, how it works, its figures, its limits |
| `LAYER_INTERFACES_v4.md`, `HEXN_NEURAL_BUS_DESIGN_v1.md`, `HEXN_TILE_SPEC_v1.md`, `CRIB_SHEET.md` | Design notes behind the models |

## Running things

Simulation and models (needs Python 3, numpy, and `iverilog` for the logic tests; without `iverilog` the logic tests fail and do not skip):

```
python3 -m pytest tests/vm/test_hexn_speech_chain_v1.py tests/vm/test_hexn_base_v6_evram_v1.py -q    # the speech chain and the base, in simulation
python3 tools/hexn_recall_pool_v3.py                                                                  # the tile with the monitor and the input check
python3 tools/hexn_parts_v2.py                                                                        # identification by parts
```

On the Kintex card (the speech chain behind the base controller; build in the openXC7 shell, load and run from an ordinary terminal; details in direction doc sections 76, 82 and 84):

```
cd ~/ypcb-00338-1p1
HEXN_BASE=hex7_off2_mix,hex6 HEXN_BASE_VER=6 HEXN_NORAM=1 bash ~/hexn-wt/fpga/ypcb/hexn_arr/run_arr.sh
~/openFPGALoader/build/openFPGALoader -c digilent_hs2 /media/alan/InternalHDD/hexn_builds/arr_base_b6_noram/hexn_arr.bit
nix shell nixpkgs#openocd --command env OPENOCD=openocd HEXN_CHAIN=2 python3 ~/hexn-wt/tools/hexn_chain_host_v3.py full ~/hexn-wt/fpga/ypcb/hexn_speech/data_full
```

Expected last lines: `right 936 (86.7%)` and `expected 936 (Python reference): PASS; per digit: all equal`.

## How the work is recorded

- Logic and measurements are the ground truth. A figure is tagged as measured on the card, simulated, modelled in Python, or a tool's estimate; clock figures from place and route are estimates, never silicon timing.
- Proven files are cloned and given a new version, never edited in place. Corrections are new rows that point at what they correct.
- Wrong guesses and failed tests are written down as plainly as the successes.
