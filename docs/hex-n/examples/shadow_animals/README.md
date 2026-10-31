# Example load: shadow height to animal

Synthetic sensor example (no real shadow recordings). Everything needed to start this usage is in this folder: the goals, the starting weights made from them, the settings, the target, and two sample runs of labelled passings.

Check it: `python3 tools/hexn_examples_v1.py check docs/hex-n/examples/shadow_animals`

Expected (see the 16:20 ledger row): with the table right the loaded weights classify about .92 of fresh passings with nothing learned; with the table wrong (world B) about .58, and learning from the first 60 labelled passings lifts the rest to about .85. The learning step in this check is in decimals; the whole-number multi-output step is not done.

To make your own: change the goal table (animals, heights, spreads), rebuild with `hexn_item_v1.goals_payload` and `goals_to_weights`, and load the new items; or load only the weights item from another run.
