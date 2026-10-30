# Hex-N layer interfaces v3 (30 Oct 2026)

Clone of `LAYER_INTERFACES_v2.md` (27 Oct; left untouched). Reason for v3: Alan's layer numbering of 30 Oct 2026 (14:15 to 14:24): layer 3 is layer 2 over several inputs together, and the looking-ahead and goal-setting job moved to a new layer 4. The layer 3 row of v2 ("inference") is superseded by this file.

Status words: BUILT = RTL that passes in simulation (blocks of v2 unchanged unless noted); MODEL = Python only; IDEA = written down, nothing made. Nothing here has been checked against a card except the memory tier.

## 1. The layers

| Layer | Job | Takes in | Passes on | Status |
|---|---|---|---|---|
| 1, one bank per sensor | Turn raw sensor wires into a clean class | coded sensor wires (18) | class number, or NONE | BUILT (hold counter; bank loaded on the Tang in the October work, see `README.md`) |
| 2, history and paths, per sensor | Remember what followed what, with counts; flag the surprising | each new held class | predicted next event with counts and context length; a verdict (ok, contradiction, novel, start) | BUILT: history + dwell, store v2 (store v5 in the Tang work); reward values in the store: MODEL only |
| 3, history and paths across sensors (layer 2 "over several inputs") | Same as layer 2 for the combined situation: moments, snapshots, longer contexts, weighted possible next moments; chooses among options from learned values; takes reward | the stable class of each channel, aligned into moments | ranked possible next moments with weights; **a confidence report (section 2)**; the choice | MODEL (`tools/hexn_layer3_v1.py`, `v2.py`); no RTL; hardware plan in `LAYER3_HW_v1.md` |
| 4, strategist | Look ahead through a tree, set goals, suggest a step to layer 3 | the board or situation, layer 3's predictions and confidence | a suggestion (a goal event on its own channel into layer 3); forced win/block played directly | MODEL (Connect Four: `tools/hexn_connect4_layer4_v1.py` to `v3.py`, `hexn_connect4_suggest_v1.py`); no RTL |
| Memory tier (under layer 3) | Large store of keys and values, three levels | PUT, GET, FLUSH, COUNTERS, INFO, LEVEL, LINE, CLEAR (`hexn_tier7_cmd_v2.v`) | value or not found | BUILT; proven on the Kintex card with the reference model; not joined to the core |
| Neural helper (beside 3 and 4) | Judge unfinished positions; similarity; suggestions | both layers | judge to layer 4; similarity and suggestions to layer 3 on their own channel | IDEA only (`HEXN_DESIGN.md`, 10:25 and 14:35 rows) |

## 2. What layer 3 must report to layer 4 (decision proposed 14:22, to be confirmed by Alan)
Together with each ranked guess: (a) the **length of the context that matched**, (b) the **seen and contradicted counts** of the entry behind it (the layer 2 pair), and (c) a **confidence value** derived from them. Reason: layer 4's depth rule already uses a confidence. Evidence is WEAK and depth-dependent (`HEXN_DESIGN.md`, 14:50, 15:10 and 15:35 rows): on the noisy opponent at depth 4 the learned prediction played worse than none (0.74 / 0.81 against 0.98 / 0.98 wins) and a flat-spread blend helped; at depth 6 the three setups were within the noise (0.89 / 0.77, 0.85 / 0.77, 0.83 / 0.83 with 4 seeds x 50 games). So the report is a proposal, not something the measurements require yet.

## 3. Where inference lives (proposed 14:22; direction, not decided)
- Inference by LOOKUP in what has been seen: layer 3.
- Inference by IMAGINING what has not happened: layer 4.
- Inference by SIMILARITY: an extension of layer 3's lookup, in steps: exact context (built), masked contexts (built in the model), nearest key (not built), learned similarity (the helper; not built).

## 4. Neural helper connections (proposed 14:28; direction, not decided)
- Position judge: into layer 4 (it is the tree's evaluation of unfinished positions).
- Key maker, fallback predictor and its own move suggestions: into layer 3, each suggestion on its own channel with its own source, so that the reward can show how much to follow each adviser.

## 5. Shared data (design only: `DOUBLE_LAYER3_v1.md`)
One shared data set in the tier; a live front end (the only writer) and a planning front end (read only, with a no-promote read) for layer 4.

## 6. Open decisions (for Alan)
1. **What feeds layer 3:** the layer 1 classes directly (the 27 Oct plan, and what the Connect Four model does) or layer 2's outputs (predictions and surprise flags), or both.
2. Confirm the confidence report of section 2.
3. Confirm the split of section 3 and the helper connections of section 4.
4. Which of layer 2's refinements go into layer 3 (see the 14:50 row for the first measurement: the candidate stage and contradicted counts helped early, not later).
5. The items of `DOUBLE_LAYER3_v1.md` section 6.

## 7. NOT built
Everything marked MODEL or IDEA above has no RTL. Also not built: the output stage that carries out a choice on real hardware, a host front end for data in and results out, layer 3 channel alignment in hardware, the join of the tier to the core, per-bank holds.
