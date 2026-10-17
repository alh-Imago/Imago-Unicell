# Designs tested on the real card, as plain ICM files

These are the ten group-test designs run on the Tang Nano 20K on 13 Oct 2026 (ledger #1167, 10 of 10 pass; #1177 exports them). Each `<name>.icm.json` is an ordinary ICM v3 file. `card_tested_index.json` lists, per design, the input streams, the words the VM produces, and the line the real card printed.

| design | what it shows |
|---|---|
| relay_chain, relay_chain_stalled | four ram cells pass words through unchanged (the basic handshake), with and without random gaps and stalls |
| adder_stream, adder_stalled, adder_constant | an adder joining two streams, or a stream and a constant |
| ram_hold, ram_oneshot | the ram cell's hold and one-shot behaviours |
| priority_strict, priority_weighted, priority_sequenced | the priority core's three modes |

**Try one in the VM** (from the repository root):

```
python3 tools/replay_card_icm_vm_v1.py
```

It loads every file into the VM's flex grid (`FlexGrid`), feeds the input streams, and checks the output words against the index and against the count and first words the card printed. The random gaps and stalls only change timing on the card, never the words.

**Regenerate** the files and index from the board-test definitions with `python3 tools/export_card_icm_v1.py` (output is byte-identical each time).

Not here yet: the native cross and corner tiles (#1170), the sanity check (#1100), and the older standard + carrier command-cell designs. The mixed flex / standard / carrier designs are in the parent folder (`mixed_*.icm-hier.json`); they have not been replayed in the VM from here, and I have not yet checked how the VM's mixed grid takes them.
