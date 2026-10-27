# Hex-N layer interfaces v2 (27 Oct 2026, end of the store and reward steps)

Clone of `LAYER_INTERFACES_v1.md` (left untouched). Status: what is BUILT means RTL that passes in simulation; nothing here is on a card yet (no bitstream with core v5, v6 or v7 exists). Layer 3 is still only intention.

## What each layer takes in and passes on

| Layer | Takes in | Passes on | Host settings | Blocks (status) |
|---|---|---|---|---|
| 1, one bank per sensor | coded sensor wires (18) | a class number, or NONE (all ones) for unknown or tie | mode (trained or exact), weights, thresholds (loader 0x13), hold N | **hold counter** `hexn_hold_v2` (BUILT, core v6 commands 0x14 SETHOLD, 0x16 RUNHOLD, 0x17 SETHOLDM) |
| 2, history and paths | each NEW held class (and the first after reset) | the predicted next event with its counts and context length; a verdict on each event (ok, contradiction, novel, start) | **promotion level N (sightings) and window W (events)**, set by the host from the data (tools/hexn_host_promote_v1.py), store mode (off, observe, host load) | **history + dwell** `hexn_hist_v1` (BUILT); **store and retrieve** `hexn_store_v2` (BUILT, block-RAM style tables, core v7 commands 0x18 to 0x1D); **reward-driven goal read** (model only, no RTL) |
| 3, inference | the latest stable class of each of three channels at one moment | an inference class and a deeper memory path | the combining rule | channel alignment: NOT built |

## Rules fixed so far (Alan's decisions)
- Layer 1 has two modes set by the host at start-up (trained, exact); layer 2 only receives cleaned codes. A bypass of layer 1 is a later option.
- Hold N is per bank (about 20 for the thermistor, 1 to 3 for light and pot, 1 with ignore-unknown for the remote).
- A routine needs at least 3 events to be identified or predicted (the goal depends on the first key).
- A wrong last event on a known sequence is logged as an anomaly and stored as a CANDIDATE; a repeat is reinforcement; at the promotion level it becomes a known sequence and keeps its count.
- The promotion level is a host setting that must follow the data analysed (part of the training set-up); it is a rate (N sightings inside W events), not a running total, because a running total eventually promotes every noise variant.
- The counts (seen, contradicted) are kept per stored sequence and are the confidence.

## Store semantics (`hexn_store_v2`; reference `tools/hexn_store_v2.py`)
Two tables. KNOWN (128 slots): key = context length (1 to 3), the last events (newest in the low bits), next event; seen and contra counts (8 bit, saturating). CAND (32 slots): key, count (4 bit), start time. Commands: CLR (clear history), OBS (predict, self-check, update), LOAD (host load: add or seen+1, no candidates), RD (retrieve only). The first event after CLR only enters the history. Retrieve uses the longest known context; best next event = highest count, ties to the lowest event. A pair not known gets a sighting at all three context lengths; N sightings inside W events promote it; a sighting at least W after the start restarts the count. Full tables overwrite the weakest slot (KNOWN lowest seen; CAND lowest count, then oldest by age, which is safe when the 16-bit clock wraps). Time is a 16-bit count from the host (the core counts OBS and LOAD commands).

## Core v7 commands added (no earlier command changed)
0x18 STORECFG [n wlo whi mode] (mode 0 off, 1 observe, 2 host load), 0x19 STORECLR, 0x1A STORECMD [cmd event], 0x1B STORERD [table slot] (raw word), 0x1C STORESTAT (5 counters), 0x1D STORELAST (verdict, levels, best event, counts). RUNHOLD (0x16) feeds the store when the held class is a change or the first sample and is not NONE; its 3-byte reply is unchanged.

## Reward side (model only: `tools/hexn_reward_v1.py`)
Each stored entry would carry a value, the average reward of the routines that went through it; the reward is a teacher signal given only when a routine ends in a goal (desired goal +1, other -0.5). The goal read picks, among the possible next keys, the one with the highest value (explore 10 percent). Results: reaches the desired goal about 0.95 of the time (ceiling with 10 percent exploration), a short context (1 event) learns fastest when keys are misread, the teacher may be wrong up to 40 percent but not 50, and the value must use a constant step (not a running mean) or the system cannot be re-steered when the desired goal changes.

## NOT built
Reward values in the store RTL; layer 3 channel alignment and combining; per-bank holds (one hold per core); a host front end for data in and results out (results from layer 3, layers 1 and 2 optional beside it); anything on a card; LUT or clock figures (the sandbox's synthesis does not finish).
