# Model 4: the upper logic (stored maps, the tile, the monitor, the anomaly store, parts)

Base document, written 12 Nov 2026 for Alan. It gathers what is already recorded; nothing was re-measured for it. Every figure is copied from the source named beside it (section numbers are sections of `HEXN_DIRECTION_SCOPING_v1.md`). **Everything in this document is a Python model on made-up test patterns, 5 seeds, built on 11 and 12 Nov 2026. None of it is in hardware, and the one test on real data (section 7) did not succeed.**

## 1. What it is

The layer above whatever recognises the raw input. Alan's ideas of 11 Nov 2026 (sections 74, 79, 88, 95): a memory is a map that is rebuilt, kept apart from the cells that made it; several recognisers share a central memory of how their answers go together; what fits nothing is not thrown away but passed on and searched; a thing is known by its parts.

```
   bank 1    bank 2    bank 3    bank 4        each bank: a recogniser + its own stored maps
      \         |         |        /            up:   "which of my maps, and how sure"
       +----- shared memory ------+             down: a hint, scaled by confidence
                   |                            the monitor works out the hints
             anomaly store                      sideways: whatever nothing explained
```

One group of four banks around a shared memory is a **tile**. In the models a bank is the 3-layer cell network of Model 3 (192 cells, 48 input lines) with 8 known patterns.

## 2. The parts: how each is built and how it works

**Map blocks (sections 74, 77).** A map is an output of the cells, so it can be kept outside them. For each known pattern the bank stores the layer 2 cells that fired in at least 3 of 5 runs (about 4 cells) as the key, and the same for layer 3 as the payload. Recall = the stored key with the most overlap with the live map. Stored maps are never erased; only their rank moves, by how recently and how often they were recalled.

**The shared memory, or pool (sections 79, 80).** It holds the known wholes as short codes: 16 large maps, each one code of 3 bits per bank (12 bits). Each bank reports either its single best map (votes) or its score for every one of its maps (full scores); the pool names the whole that fits best.

**The monitor (sections 80, 87).** It sends a hint back down to each bank. The rule that keeps it honest: the hint for a bank is worked out from the OTHER banks only, so a bank's own answer is never evidence for its own hint. If all the others point to the same whole the hint is strong, if most do it is weak, otherwise none. One round; nothing loops. The hint is added to the bank's score for the map the whole expects, and the bank ranks again.

**The input check (Alan, section 87).** Before any cell fires, count the events that arrive at a bank and compare with that bank's normal count: full confidence at three quarters of normal or more, half at one half or more, none below. One counter and two comparisons. Each bank's vote is weighted by it.

**The line check (sections 89, 97).** Each bank keeps, for each of its patterns, the input lines that pattern normally uses (a 48-bit mask). The share of a run's active lines that fall in the best mask says whether the input is one of the bank's patterns at all. This is matching at the input, before the cells: a detector.

**The anomaly store (Alan, sections 88 to 91).** What a recall does not explain is the residue: the active input lines the recalled pattern does not normally use. Residues go to 16 counting slots. A residue joins the slot it resembles (at least 3 lines in common) or opens a new one. Real noise does not repeat; a hidden pattern keeps landing in the same slot. A slot with enough hits (8) and at least 4 lines is compared with what the main system knows: if 70% of its lines belong to one known pattern it is **known but weak** and scores in a separate weak table; otherwise it is **new** and stored as a new pattern, confirmed after 5 further sightings. Nothing is fed back to the main system.

**Identification by parts (Alan, sections 95, 97).** One bank per aspect (think colour, shape, size, kind), 8 values each; the shared memory holds 16 known things as combinations. A bank is clear (saw its part well and knows it), reports an unknown part (saw something well that fits none of its values), or is unsure. From the clear banks the answer is: **known** (one thing fits), a **shortlist**, a **new combination** ("new, made of these parts", plus the nearest known thing), an **unknown part** (and which aspect), or **unsure** (the three best guesses).

## 3. Results [all Python models, test patterns, 5 seeds]

Recall figures are percent right at 10 / 30 / 50 / 70% of input events dropped unless said otherwise.

**Stored maps beside the cells (section 77)**

| What the next layer reports | Right |
|---|---|
| Cells alone (layer 2 feeds layer 3) | 70 / 61 / 45 / 22 |
| Recall the block, replay its stored map into layer 3 | 87 / 82 / 69 / 40 |
| Recall the block, read its stored answer directly | 98 / 92 / 78 / 46 |

A hint that primes the recalled map's cells completes the map (overlap with the right block up by 0.10 to 0.20) while the answer barely moves; scaled by confidence it causes fewer false cells on never-seen input (0.43 per run against 0.69 and 1.18 for fixed hints). Rank by recency and frequency gains 8 to 11 points when use is uneven and comes in bursts, loses 1 to 4 when use is even, and costs the rarely used patterns up to 7.5 points.

**The tile: four banks, pool and monitor (sections 80, 86, 87)**

| Case | Result |
|---|---|
| Whole named right, all banks alike: votes / full scores / monitor | 98.3 / 99.9 / 99.8 at 10%; 83.4 / 92.3 / 88.4 at 50%; 40.2 / 51.9 / 44.2 at 70% |
| Local answers right, before / after the monitor | 94.5 / 99.3 at 10%; 72.5 / 86.2 at 50% |
| One bank nearly blind (90% dropped), others at 10% | that bank 14.6% right alone, 86.9% with the plain monitor, 94.7% with input-weighted votes |
| Two of four banks nearly blind | damaged banks 67.3% (plain monitor), 76.0% (weighted by recall clarity), 86.5% (weighted by the input check) |
| Three of four nearly blind | 35.1 / 41.7 / 49.2% |
| A combination the pool never stored | 1.6% of right local answers spoiled, 0.3% repaired (plain); 2.8 to 6.0% spoiled with weighted votes |
| All banks at 70%, input-weighted | 39.6% of local answers right against 49.0% plain: with every bank's weight at zero, nobody may hint |

For naming the whole, the pool reading full scores is best everywhere; the monitor's value is repairing the banks. The input check tracks the damage (mean weight 2.00 / 1.83 / 1.00 / 0.14 / 0.00 at 10 / 30 / 50 / 70 / 90% dropped); recall clarity is looser and about 3% of badly damaged banks are sure and wrong.

**The anomaly store (sections 89 to 91)**

| Test | Result |
|---|---|
| A hidden pattern, never taught, of 6 lines x 2 events (the known ones are 12 x 3), found within 200 runs | 30 of 30 streams (report at 8 hits); about 13 to 15 sightings needed |
| Weaker: 4 lines x 2 events / 3 lines x 1 event | 26 of 30 / 18 of 30 |
| Residue taken after the cells instead of at the input | much weaker: 24 of 30 even at 3 hits |
| With the compare step: a new pattern found and confirmed | 9 of 10 streams |
| A faint copy of a known pattern | never called new; weak table about 58 on the right pattern against 2 to 3 when absent |
| False "new" notes with nothing hidden | 0.0 per stream after the fix (1.3 before: chance templates of 2 to 4 noise lines) |
| Wrong "new" notes when two things are hidden at once | 1.7 per stream; not examined |

The hidden pattern itself lowers the main bank's recall a little (96.4% to 91.7%); the store does not, since nothing is fed back.

**Identification by parts (section 97)**

| Test | Banks judged by cells only | With the line check |
|---|---|---|
| All parts present, 10% dropped: named right | 68.8% (23.8% wrongly called unknown part) | 99.9% |
| 30% dropped: named right | 46.3% | 94.6% |
| One aspect missing altogether | 63.9% | 98.6% |
| One part swapped for another known value: called new | 53.6% | 99.6%, all four parts named correctly |
| One part never seen: called unknown part | 55.5% | 94.3%, the right aspect every time |

At 50% dropped it stops naming and answers "unsure", with the right thing among its three best in about 8 of 10 tests.

## 4. What was tried and found wanting

| Idea | Result | Source |
|---|---|---|
| First past the post: a firing cell holds the others down | Never better, usually worse (see Model 3) | section 96 |
| Adding a deeper layer of cells | Each deeper layer is worse; a recalled map passed on beats it | sections 49, 50, 77 |
| Judging "do I know this?" from the cells alone | Cannot tell an unknown part from a known part whose cells did not respond | section 97 |

## 5. What the results say

- The upper logic does jobs the recogniser underneath cannot: filling in a damaged or missing part from the others, saying how sure it is, naming a thing from its parts, and setting aside and sorting what fits nothing.
- It needs the banks underneath to be right most of the time. In these models they were (94% at 10% dropped).
- Wherever it improved, the gain came from confidence measured at the input (the event count, the line check) and from the shared memory, not from more cells. Nothing in the pool, monitor or anomaly store depends on the bank being a cell network: a bank only has to give a code and a confidence (section 94).
- Its standing weakness is a lean toward what is stored: wrong recalls get reinforced, and something new is pulled toward something known unless a check at the input says otherwise.

## 6. Size

| Part | Size | Basis |
|---|---|---|
| A tile's cells | 768 (4 banks of 192), 192 input lines, about 8,700 weights of 4 bits | the model |
| A tile's stored maps | 32 maps over 64 cells each, plus 16 large maps of 12 bits | the model |
| A tile in logic, if the banks are Model 3 cell networks | about 175,000 LUT sites, 29% of the Kintex chip | ESTIMATE: the one measured 192-cell build (43,741 sites, Model 3) times four; the pool, monitor and stores are not included and have never been built |

## 7. The one test on real data: it did not beat the chain (section 99)

The 5 time windows of a spoken digit were treated as parts, and the training recordings stored as known wholes (their five window answers). On the 1,079 test recordings: the speech chain 936 right (86.7%); the memory of wholes 855 to 880 (79 to 82%) by votes, full scores or input-weighted scores; a second look between the chain's top two digits repaired 18 and spoiled 21. In 117 of the chain's 143 errors the memory was wrong as well.

Why (Alan, 12 Nov): the detector does not only clean the data, it processes it, so the work is done before the upper logic sees it; and the chain already has its own way of tying its windows together. The upper logic has something of its own to add where there are several sources that fail independently and none has already decided for the others. No real data of that kind is in hand.

## 8. Limits and open points

- Python only; test patterns only; thresholds and hint sizes chosen by hand and not tuned (the unknown-part threshold was set after looking at 2 seeds).
- Not modelled: more than one tile (tiles of tiles, section 94); two things present at once (which colour goes with which shape, section 95); repeated rounds of hints; confidence relative to the other banks, for when all are damaged alike; a novelty check at the pool; retraining the cells on a newly stored pattern; fading of the hit counts.
- Not compared with one large network of the same cell count.
- Parked by Alan on 11 Nov 2026 as proving the idea to a point (section 92); picked up as a thought direction on 12 Nov (section 98).

## 9. Where the detail is

Direction doc sections 74, 77, 79, 80, 86 to 99; tools `tools/hexn_recall_blocks_v1.py` (stored maps, hint, rank), `hexn_recall_pool_v1.py`, `_v2.py`, `_v3.py` (tile, monitor, damaged banks, input check), `hexn_anomaly_tile_v1.py`, `_v2.py`, `_v3.py`, `hexn_anomaly_diag_v1.py` (anomaly store), `hexn_parts_v1.py`, `_v2.py` (parts), `hexn_chain_parts_v1.py` (real speech). Each prints its own table; run times are from a few seconds to about 9 minutes.
