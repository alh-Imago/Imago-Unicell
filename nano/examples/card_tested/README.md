# Designs tested on the real card, as plain ICM files

Eleven designs that ran on the Tang Nano 20K, as ordinary ICM v3 files (ledger #1177, #1179). Each `<name>.icm.json` loads with `IcmV3File.load`. `card_tested_index.json` lists, per design, the input streams, the words the VM produces, and the line the real card printed.

| design | what it shows | card result |
|---|---|---|
| relay_chain, relay_chain_stalled | four ram cells pass words through unchanged (the basic handshake), with and without random gaps and stalls | 13 Oct 2026, #1167, pass |
| adder_stream, adder_stalled, adder_constant | an adder joining two streams, or a stream and a constant | #1167, pass |
| ram_hold, ram_oneshot | the ram cell's hold and one-shot behaviours | #1167, pass |
| priority_strict, priority_weighted, priority_sequenced | the priority core's three modes | #1167, pass |
| tiles_flex | the native cross and corner cells: three tiles in one grid, six independent streams, each must leave by its own exit unchanged | 14 Oct 2026, #1170, pass |

**Try them in the VM** (from the repository root):

```
python3 tools/replay_card_icm_vm_v2.py
```

It loads every file into the VM's flex grid (`FlexGrid`), feeds the input streams, and checks the output words against the index and against the count and first words the card printed (the card line shows at most the first eight). The random gaps and stalls only change timing on the card, never the words. The tiles design has six entries and six exits; the card's shim reads them round-robin and the replay does the same.

**Regenerate** with `python3 tools/export_card_icm_v2.py` (the output is byte-identical each time). The v1 tools (`export_card_icm_v1.py`, `replay_card_icm_vm_v1.py`) still work on the ten group designs; the tiles are in a separate `multi_stream_designs` list in the index so that v1 is unchanged.

## Other ICM files that also ran on the card (in the parent folder, `nano/examples/`)

These already existed as ICM files. They are not replayed by the command above.

| ICM file | what ran on the card | built by |
|---|---|---|
| `mixed_flex_sub_flex_v1.icm-hier.json` | sub to flex mixed pipeline | `tools/board_loops_v1.py` |
| `mixed_flex_std_flex_v1.icm-hier.json`, `mixed_flex_carrier_flex_v1.icm-hier.json` | flex to standard and flex to carrier, through the adapters (#1168, #1169) | `tools/board_mixed_std_v1.py` |
| `mixed_flex_std_div_flex_v1.icm-hier.json`, `mixed_flex_carrier_div_flex_v1.icm-hier.json` | the division core in a standard / carrier region (#1171, #1172) | `tools/board_mixed_div_v1.py` |
| `looped_cordic_v1_open.icm-hier.json` | the open-ring looped CORDIC inside the sanity check (#1100) | `tools/board_saveload_v2.py` (the stop wrapper and serial front end are Verilog, not ICM) |

## Not replayable here yet

- **The mixed designs and the sanity check.** I have not yet checked how the VM's mixed grid takes the mixed files. The sanity check is a set of card mechanics (stop, freeze, save, reset, load) driven over a serial link; its existing VM-versus-card comparison is `python3 tools/flex_tang_bridge_v1.py compare vm_save_step300.json tang_result_A.json` (kit in `fpga/board_tests_saveload/`).
- **The older standard + carrier command-cell designs** (#1087-#1089): not exported.
