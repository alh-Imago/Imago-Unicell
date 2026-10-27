# Layer 2 recording session v1: key routines (run sheet)

You press keys on the MP3 remote in a planned order; the logger records the IR receiver (and the light, pot and thermistor, which stay connected and untouched). The planned order is known, so the recording can be checked press by press against it.

## The four routines (digit keys only; leave Power alone)

| Routine | Press in this order | Ends with (the goal key) |
|---|---|---|
| A | 1 , 2 , 3 | 7 |
| B | 4 , 2 , 3 | 8 |
| C | 1 , 5 , 6 | 8 |
| D | 4 , 5 , 6 | 7 |

Why these: after the keys **2 3** the goal is 7 after a routine that began with 1 and 8 after one that began with 4 (and the other way round after 5 6), so the system has to look back to the first key.

## How to press

- Start the logger FIRST, wait for it to say it is logging, then start pressing.
- One quick tap per key (no holding), about 1 second between keys inside a routine.
- Pause about 3 seconds between routines (count 'one-two-three').
- Press the sheet's routines in the order shown; tick them as you go. If you make a mistake, carry on and write the mistake on the sheet (do not restart): the checker can tell.
- Leave the light sensor, pot and thermistor alone (no hands near them).

## Logger command (one run)

```
python3 tools/hexn_esp_log_v2.py --port /dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0 --rate 200 --seconds 230 --label routines_run1 docs/hex-n/data/esp_run_20261027_ir_routines_run1.csv
```
Change `run1` to `run2` and `run3` in both places for the other runs. Each run writes the csv and an `_edges.csv` next to it.

## Run 1 (16 routines, 64 presses)

| # | Routine | Press | Done |
|---|---|---|---|
| 1 | A | 1 , 2 , 3 , 7 | [ ] |
| 2 | C | 1 , 5 , 6 , 8 | [ ] |
| 3 | B | 4 , 2 , 3 , 8 | [ ] |
| 4 | A | 1 , 2 , 3 , 7 | [ ] |
| 5 | B | 4 , 2 , 3 , 8 | [ ] |
| 6 | A | 1 , 2 , 3 , 7 | [ ] |
| 7 | D | 4 , 5 , 6 , 7 | [ ] |
| 8 | B | 4 , 2 , 3 , 8 | [ ] |
| 9 | D | 4 , 5 , 6 , 7 | [ ] |
| 10 | A | 1 , 2 , 3 , 7 | [ ] |
| 11 | C | 1 , 5 , 6 , 8 | [ ] |
| 12 | D | 4 , 5 , 6 , 7 | [ ] |
| 13 | C | 1 , 5 , 6 , 8 | [ ] |
| 14 | D | 4 , 5 , 6 , 7 | [ ] |
| 15 | C | 1 , 5 , 6 , 8 | [ ] |
| 16 | B | 4 , 2 , 3 , 8 | [ ] |

As one line: `A C B A B A D B D A C D C D C B`

## Run 2 (16 routines, 64 presses)

| # | Routine | Press | Done |
|---|---|---|---|
| 1 | D | 4 , 5 , 6 , 7 | [ ] |
| 2 | A | 1 , 2 , 3 , 7 | [ ] |
| 3 | C | 1 , 5 , 6 , 8 | [ ] |
| 4 | A | 1 , 2 , 3 , 7 | [ ] |
| 5 | D | 4 , 5 , 6 , 7 | [ ] |
| 6 | A | 1 , 2 , 3 , 7 | [ ] |
| 7 | B | 4 , 2 , 3 , 8 | [ ] |
| 8 | C | 1 , 5 , 6 , 8 | [ ] |
| 9 | B | 4 , 2 , 3 , 8 | [ ] |
| 10 | C | 1 , 5 , 6 , 8 | [ ] |
| 11 | B | 4 , 2 , 3 , 8 | [ ] |
| 12 | C | 1 , 5 , 6 , 8 | [ ] |
| 13 | D | 4 , 5 , 6 , 7 | [ ] |
| 14 | B | 4 , 2 , 3 , 8 | [ ] |
| 15 | D | 4 , 5 , 6 , 7 | [ ] |
| 16 | A | 1 , 2 , 3 , 7 | [ ] |

As one line: `D A C A D A B C B C B C D B D A`

## Run 3 (16 routines, 64 presses)

| # | Routine | Press | Done |
|---|---|---|---|
| 1 | C | 1 , 5 , 6 , 8 | [ ] |
| 2 | A | 1 , 2 , 3 , 7 | [ ] |
| 3 | B | 4 , 2 , 3 , 8 | [ ] |
| 4 | D | 4 , 5 , 6 , 7 | [ ] |
| 5 | A | 1 , 2 , 3 , 7 | [ ] |
| 6 | C | 1 , 5 , 6 , 8 | [ ] |
| 7 | A | 1 , 2 , 3 , 7 | [ ] |
| 8 | B | 4 , 2 , 3 , 8 | [ ] |
| 9 | D | 4 , 5 , 6 , 7 | [ ] |
| 10 | C | 1 , 5 , 6 , 8 | [ ] |
| 11 | B | 4 , 2 , 3 , 8 | [ ] |
| 12 | C | 1 , 5 , 6 , 8 | [ ] |
| 13 | D | 4 , 5 , 6 , 7 | [ ] |
| 14 | B | 4 , 2 , 3 , 8 | [ ] |
| 15 | D | 4 , 5 , 6 , 7 | [ ] |
| 16 | A | 1 , 2 , 3 , 7 | [ ] |

As one line: `C A B D A C A B D C B C D B D A`

## After the runs

Send the csv files (the main and the `_edges.csv` of each run) and any notes about mistakes. Check with: `python3 tools/hexn_session_check_v1.py docs/hex-n/data/esp_run_20261027_ir_routines_run1_edges.csv 1`
