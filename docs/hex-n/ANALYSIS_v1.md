# Front end intake and analysis engine (proposal v1, 31 Oct 2026)

Alan, 17:16: "this is the kind of data the frontend needs to accept, and then there is the things you want highlighted, almost an analysis engine." This note says what the prototype `tools/hexn_intake_v1.py` does, what it was run on, and what is not built. Python on the host; nothing on a card.

## 1. What the front end has to accept (all seen so far, all real)

| Shape | Example | What makes it awkward |
|---|---|---|
| Labelled rows, no header, text cells | UCI Connect-4 (42 squares x/o/b + win/loss/draw) | categorical cells, label last, no names |
| One file per sensor, no header | ocean raw files (time, value, GeoJSON position, time) | position packed as JSON, repeated time |
| Merged table, called "labelled" but without a label | ocean `Labeled_PreProcessed_Dataset.csv` | the name promises a label that is not there |
| Long format, one measure per file | Environment Agency (measure URL, dateTime, date, value, completeness, quality, qcode) | the same column name `value` in every file; empty or repeated columns |
| Device log with comment header | ESP logs (`# hexn_esp_log_v2 label=...`, seq, esp_us, host_s, a35.., d16, d17) | counter clock in microseconds, constant pins, comment lines |

## 2. What the intake does (built, prototype)

1. Reads CSV or CSV.gz, skips `#` lines, detects a missing header.
2. Gives every column a role: **time** (dates), **counter** (increasing numbers, including the clocks), **position** (GeoJSON), **label** (few classes, or a name that says so), **sensor**, **digital** (two values), **meta** (quality, completeness, measure id), **constant**.
3. Merges several files on time with an inner join (the dataset author's own rule) and names each sensor from its file name when the column is just `value`, after stripping the part every file name shares.
4. Does not guess a label. If none is present it says so and offers the **task menu** below.

## 3. What is highlighted (built, in the order of importance shown to the user)

- spikes beyond 8 median deviations (count, largest value against the median);
- drift: median of the second half against the first, in units of the spread;
- stuck sensors (the same value repeated), missing values;
- columns that never change (wiring or sensor not connected);
- redundant pairs (|r| above 0.97), for example conductivity and salinity, or flow and level;
- cadence, gaps, and the time span; counters give the cadence too;
- label balance and the number of **episodes** of the rarer class, with a plain warning when there are fewer than 10 ("treat every number as rough").

## 4. Task menu and analysis (built, prototype)

If the file has a label column it is used. Otherwise the user states one of: `--rule 'expr'` (a stated rule), `--future SENSOR --q 0.9 --hours 6` (the sensor will cross its own 90th-percentile line within 6 hours; rows already above are left out). The analysis then makes counted detectors (12 bins over a loaded range; for time series also the 1-hour and 3-hour change and the 1-hour sum of every sensor), runs the table refresh against logistic regression and the nearest class mean, and prints the learning curve, the chronological split used, and **which detectors carry the signal** (each alone).

## 5. Runs so far (the engine, not the tests in the ledger)

- Ocean merged file, stated rule: 6 drift flags, the redundant pair conductivity/salinity, 4 gaps; table refresh AUC 1.000 on 4 test minutes in 2 episodes; the engine warns that this is few. **Flow carries the signal alone (AUC 1.000)** because the rule uses it.
- River Exe, four raw files, `--future flow`: merged to 70,080 rows x 5 columns with no setup; table refresh AUC **0.976**, logistic regression 0.973, nearest mean 0.977 (the hand-built test of the ledger gave .973 and .982); flow and level redundant (|r| 0.98); 24 test episodes.
- ESP pot-sweep log: found three constant pins and the cadence from the microsecond counter; one drifting sensor.

## 6. Not built (and open)

- the cell does not run these checks itself: this is the host/ESP side, the 'analysis engine' beside the cell, not in it;
- categorical features (the Connect-4 squares) and the game path;
- the typed items of `ITEM_FORMAT_v1.md`: results are not yet saved as a settings or weights item;
- the choice of bias, the learning switch and the stages on a real stream (they exist in earlier tools);
- a screen: the output is text and the intake has no menu of its own;
- units, names and plain-word captions for sensors (the front end only has the column names).
