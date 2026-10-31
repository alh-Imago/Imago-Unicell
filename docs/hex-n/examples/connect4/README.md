# Example load: Connect Four

The game used for all the 31 Oct tests. The folder holds the starting weights (the hand score), the settings, the player-detector data and the target. The game rules and the layer 1 line counters are not items: they are the example's test world (`tools/hexn_connect4_v1.py`).

Check it: `python3 tools/hexn_examples_v1.py check docs/hex-n/examples/connect4`

It plays 40 games with the loaded whole-number weights against the noisy opponent at search depth 3. The 31 Oct figures for the same set-up are in the ledger (13:30 and 16:00 rows). Learning is OFF in this example; the selector turns it on for a habit opponent.
