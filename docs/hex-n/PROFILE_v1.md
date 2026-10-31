# Hex-N usage profile and front-end menu, proposal v1 (31 Oct 2026)

**Status: proposal; nothing built.** Alan's direction (31 Oct, 14:46 and 14:50): the user picks a usage type at the front end; if the design already has weights for that usage, they are loaded; if not, it has to be told whether the target is a sensor or a game. Builds on `FRONT_END_v1.md` (boot shell: loads bitstreams and data from the SD card) and `UNIT_v1.md` (the unit and its blocks). Words as in UNIT_v1: BUILT / MODEL / DESIGNED / ESTIMATE.

## 1. What a profile is

One file (a volume on the card, `CARD_FORMAT_v1.md`) holding everything the unit needs to start in a usage, so that changing usage is changing the file, not the hardware.

| Field | Meaning | Game example (Connect Four, from the 31 Oct tests) | Sensor example (shadow height, 16:20 row) |
|---|---|---|---|
| `usage` | `game` or `sensor` | game | sensor |
| `layer1` | detectors / counters feeding the neural | 6 line counters + parity (MODEL; hardware for them not built) | 24 height bins of 8 cm (the detector bank exists in hardware; counts per window not built) |
| `neural.weights` | starting weights, whole numbers | Q14: 410, 1638, 3686, -410, -1638, -3686, parity 0, bias 0 (the hand score's weights) | prior scores from the stated table, floored at -8, one row per animal |
| `neural.rate` | learning step | 5 >> (29 - WB) of err x gain x count (WB 14), bias as input 64 | rate about 1.5 on the delta rule (0.15 was too slow) |
| `neural.learn` | learning on or off at start | off (the selector turns it on for a habit opponent) | on (the table may be wrong) |
| `teacher` | where the target comes from | the strategist's search value, the result at the end | the true label when given (right/wrong only: not tested) |
| `strategist` | mode and settings | search, depth 3, path cutoff, blend with confidence x hit rate, layer 2 gate 0.5 | goal setter, no search (30 Oct direction) |
| `detector` | style detector centroids and thresholds | the 4 features at 400 opponent moves (`detect.json`) | none |
| `memory` | look-back (default 3, build maximum 8), snapshot ID width, store sizes | look-back 3, index 256 slots, 128 rows | per feed |
| `target` | where the strategist runs | `esp` (Tang), `host`, or `onboard` (Kintex) | same |

## 2. The menu at the front end

1. **Pick usage:** game or sensor (later: more types). 2. **Look for a profile** of that name on the card. 3a. **Found:** load it (weights, settings, strategist target) and start. 3b. **Not found:** say so plainly ("no tuned weights for this usage"), load the generic profile for the chosen type, and start with learning ON for a sensor (where a prior is stated) or the hand weights with learning OFF for a game (a blank start collapsed against strong opponents, 13:30 row). 4. **Save:** at the end the learned weights can be written back as a new profile (never over the old one: clone and increment).

## 3. Loading any kind of data (Alan, 31 Oct 14:53)

A profile is not one block. The front end loads TYPED ITEMS, each on its own, from the card or the host, so goals can come from one file and weights from another. An item is a header (type, version, size, checksum, build limits it needs) plus its data.

| Item type | Holds | Path into the unit today |
|---|---|---|
| `goals` | the goal table (animal -> height and spread; or a game's target/win rule) | none: needs a table-to-weights step (the sensor test did it in Python: log density, floored at -8) |
| `weights` | neural weights and bias, whole numbers | BUILT in simulation: weight write port (`w_wr`, address, data) of `rtl/hexn_neural_v1.v` |
| `settings` | look-back, ID width, learning rate, depth, gate, thresholds | look-back and ID width are build/start-up variables (plan in `STORE_V7_LOOKBACK_v1.md`); the rest have no register yet |
| `detector` | style-detector centroids and scales | none (MODEL) |
| `history` | layer 2 / layer 3 store contents (pairs seen before) | the store has a LOAD command (pairs enter as seen once, `StoreV7` command 2); layer 3 has no RTL |
| `memory` | key/value contents of the memory tier | BUILT on the Kintex card (PUT / GET / FLUSH); not joined to the core |
| `target` | where the strategist runs (`esp`, `host`, `onboard`) | a setting of the strategist program |

Rules for any item: (1) the header is checked against the build before anything is written (inputs count, weight width WB, look-back maximum, store sizes) and a mismatch is refused with the reason, not truncated; (2) nothing is overwritten: saving writes a new item (clone and increment); (3) items can be combined freely, and the front end shows what is loaded and what is still the generic default; (4) a loaded item says where it came from (file, date, trained on what), so a user can see that a weight set was trained on weak opponents (the 10:05 row: learned weights depend on who produced the training games); (5) an item for a different usage type is refused unless the user says so.

NOT designed: the item header to the byte; how the host sends an item (the host link protocol is `esp32-bl616-link-protocol-v0.1.md`, items are not in it); a viewer for the loaded items.

## 4. What is and is not known

- Game profile: values are measured (Python); the line counters and the strategist are not hardware yet.
- Sensor profile: the shadow test is synthetic and layer 1 plus neural only. The prior alone gave .91 with a right table and the learner repaired a wrong table (.57 to .94); one cue cannot do an unknown sun factor (.72). There are no real sensor recordings behind it, and the whole-number arithmetic has not been run for the multi-output case.
- The profile format is not designed to the byte; the card format has no profile volume yet.
- Unknown: whether the user should ever be able to edit the table (animals, heights) at the menu; the front end could offer that for a sensor usage because the table IS the goal.
