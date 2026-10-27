# Hex-N layer interfaces v1 (intentions; 27 Oct 2026)

Status: DESIGN NOTE. Only the two blocks marked BUILT exist as RTL; everything else is intention. Layers 2 and 3 exist only as Python models, and the three sensors have never been recorded together.

## What each layer takes in and passes on

| Layer | Takes in | Passes on | Settings (host, at start-up) | Extra block |
|---|---|---|---|---|
| 1, one bank per sensor | coded sensor wires (18) | a class number, or NONE (15) for 'unknown / tie' | mode (trained or exact/direct), weights, thresholds (loader), hold N | **hold counter** (`hexn_hold_v1`, BUILT) on the bank's class output |
| 2, history | stable class + change event from one layer-1 bank | the last D stable classes, how long the current state has lasted (dwell), how long the previous one lasted | D, tick rate | **history + dwell counter** (`hexn_hist_v1`, BUILT) per channel; the path learning on top is NOT built |
| 3, inference | the latest stable class of each of three channels, read at one moment | an inference class and a deeper memory path | the combining rule | **channel alignment** (hold each channel's latest stable class, read all three on one strobe): NOT built |

## Rules fixed so far (Alan's decisions)
- Layer 1 has two modes, both set by the host at start-up: trained (noisy data) and exact/direct (machine codes, one bit different = unknown). Layer 2 only receives cleaned codes.
- A bypass of layer 1 for large code spaces (values, not patterns) is a later option; it is not designed.
- Hold N is set per bank: about 20 for the thermistor (model result), 1 to 3 for light and pot, 1 for the remote.

## Hold counter semantics (`hexn_hold_v1`)
The output keeps its last stable answer; it changes only after a new answer has been the input for N samples in a row on the sample strobe `en`. The first sample after reset is taken at once. N of 0 or 1 passes every change straight through. Class code 15 (NONE) is an answer like any other. This is the rule of `tools/hexn_hold_v1.py`.

## History + dwell semantics (`hexn_hist_v1`)
On a change event the new stable class is shifted into a depth-D list (newest first), the dwell of the state that just ended is stored as `prev_dwell`, and `dwell` restarts at 0. `dwell` counts the time ticks since the last change and saturates at its maximum.
