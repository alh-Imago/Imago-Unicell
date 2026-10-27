"""hexn_session_plan_v1: makes the RUN SHEET and the PLAN FILE for the layer-2 recording session (new file; Python only). Output: docs/hex-n/sessions/ROUTINES_RUN_SHEET_v1.md (what Alan presses, run by run) and docs/hex-n/sessions/routines_plan_v1.json (the same order as key numbers, read by tools/hexn_session_check_v1.py).
Design: 4 ROUTINES of 4 digit keys, built so that the goal key at the end depends on the FIRST key AND the MIDDLE keys together (no single earlier key decides it, and the last two keys before the goal are the same for two routines): A = 1 2 3 then 7; B = 4 2 3 then 8; C = 1 5 6 then 8; D = 4 5 6 then 7. Goal key 7 or 8 = the 'goal' of the routine (the goal marker is a real key press). After 2 3 the goal is 7 or 8 depending on whether the routine began with 1 or 4, so predicting the goal needs the history back to the first key (3 events before the goal: key 3 alone, keys 2 3, or 1 2 3 give different accuracy). Between routines Alan pauses about 3 seconds (a long dwell marks the end); inside a routine about 1 second between keys.
Each run = 16 routines (each routine 4 times, in a random order fixed by the seed, no routine twice in a row) = 64 presses, about 3 minutes. Three runs with different seeds. Digits only (no Power) so the TV is left alone.
Usage: python3 tools/hexn_session_plan_v1.py"""
import os, json, random
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "..", "docs", "hex-n", "sessions")
TABLE = [0x45, 0x46, 0x47, 0x44, 0x40, 0x43, 0x07, 0x15, 0x09, 0x16, 0x19, 0x0D, 0x0C, 0x18, 0x5E, 0x08, 0x1C, 0x5A, 0x42, 0x52, 0x4A]
NAME = ["Power", "Mode", "Mute", "Play/Pause", "Previous", "Next", "EQ", "minus", "plus", "0", "Loop", "U/SD", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
DIG = {d: NAME.index(str(d)) for d in range(1, 10)}
ROUTINES = {"A": [1, 2, 3, 7], "B": [4, 2, 3, 8], "C": [1, 5, 6, 8], "D": [4, 5, 6, 7]}
GOAL = {"A": 7, "B": 8, "C": 8, "D": 7}
def order(seed):
    r = random.Random(seed); pool = list("ABCD") * 4
    while True:
        r.shuffle(pool)
        if all(a != b for a, b in zip(pool, pool[1:])): return list(pool)
def main():
    os.makedirs(OUT, exist_ok=True); plan = {"routines": ROUTINES, "goal_key": GOAL, "table_index_of_digit": DIG, "runs": {}}
    md = ["# Layer 2 recording session v1: key routines (run sheet)\n",
          "You press keys on the MP3 remote in a planned order; the logger records the IR receiver (and the light, pot and thermistor, which stay connected and untouched). The planned order is known, so the recording can be checked press by press against it.\n",
          "## The four routines (digit keys only; leave Power alone)\n", "| Routine | Press in this order | Ends with (the goal key) |", "|---|---|---|"]
    for k, v in ROUTINES.items(): md.append("| %s | %s | %d |" % (k, " , ".join(map(str, v[:3])), v[3]))
    md += ["", "Why these: after the keys **2 3** the goal is 7 after a routine that began with 1 and 8 after one that began with 4 (and the other way round after 5 6), so the system has to look back to the first key.\n",
           "## How to press\n", "- Start the logger FIRST, wait for it to say it is logging, then start pressing.",
           "- One quick tap per key (no holding), about 1 second between keys inside a routine.",
           "- Pause about 3 seconds between routines (count 'one-two-three').",
           "- Press the sheet's routines in the order shown; tick them as you go. If you make a mistake, carry on and write the mistake on the sheet (do not restart): the checker can tell.",
           "- Leave the light sensor, pot and thermistor alone (no hands near them).\n",
           "## Logger command (one run)\n", "```", "python3 tools/hexn_esp_log_v2.py --port /dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0 --rate 200 --seconds 230 --label routines_run1 docs/hex-n/data/esp_run_20261027_ir_routines_run1.csv", "```",
           "Change `run1` to `run2` and `run3` in both places for the other runs. Each run writes the csv and an `_edges.csv` next to it.\n"]
    for run, seed in ((1, 101), (2, 202), (3, 303)):
        o = order(seed); keys = []
        for r in o: keys += ROUTINES[r]
        plan["runs"][str(run)] = {"seed": seed, "routine_order": o, "keys": keys, "table_index": [DIG[d] for d in keys]}
        md += ["## Run %d (%d routines, %d presses)\n" % (run, len(o), len(keys)), "| # | Routine | Press | Done |", "|---|---|---|---|"]
        for i, r in enumerate(o): md.append("| %d | %s | %s | [ ] |" % (i + 1, r, " , ".join(map(str, ROUTINES[r]))))
        md += ["", "As one line: `%s`\n" % " ".join("%s%s" % (r, "") for r in o)]
    md += ["## After the runs\n", "Send the csv files (the main and the `_edges.csv` of each run) and any notes about mistakes. Check with: `python3 tools/hexn_session_check_v1.py docs/hex-n/data/esp_run_20261027_ir_routines_run1_edges.csv 1`\n"]
    open(os.path.join(OUT, "ROUTINES_RUN_SHEET_v1.md"), "w").write("\n".join(md)); json.dump(plan, open(os.path.join(OUT, "routines_plan_v1.json"), "w"), indent=1)
    for run in plan["runs"]: print("run %s: %s" % (run, "".join(plan["runs"][run]["routine_order"])))
if __name__ == "__main__": main()
