# VM Test Suite (`tests/vm/`)

*Rewritten 2026-10-06 (ledger #996). The previous version listed 42 test
files from the archived full-cell line (`test_array.py`,
`test_fp_tiles.py`, …), and none of them exist here any more.*

```bash
python3 -m pytest tests/vm -q              # the whole suite (~1,764 tests as of #995)
python3 -m pytest tests/vm/test_icm_v3.py  # one file
```

`pyproject.toml` excludes `legacy/`, `legacy_full_cell/` and `archive/`
from collection. Those folders test archived modules and are kept for
reference only (see the README in each).

**Before trusting a run**, see `tests/README.md`. Many files here drive
generated RTL through `iverilog` and skip without it. Six tests need
`apycula`/`networkx`.

The groups below use filename patterns rather than per-file lists, so
the map stays true as tests are added. Each test file's own docstring
names its ledger entry.

| area | files | what they cover |
|---|---|---|
| **Program formats** | `test_icm_v3`, `test_icm_v4`, `test_icm_vix_v1`, `test_generic_field_codec_v1`, `test_root_definition_extractor_v1`, `test_shell_compat_v1` | ICM encode/decode against RTL test vectors; the JSON schema vs the hand-typed field tables; shell versions |
| **The std VM** | `test_unicell_super_automaton_v1`, `test_unicell_automaton_v1`, `test_vm_width_v1`, `test_vm_*`, `test_*_semantics_v1`, `test_*_roles_v1`, `test_*_core_v1` | `SuperGrid`/`SuperCell` behaviour per core; the data-width parameter (#961); introspection, autosize, mirror, the AI port |
| **FlexGrid (the flex mirror)** | `test_flex_grid_*_v1`, `test_flex_second_port_v1`, `test_flex_free_shift_v1`, `test_target_shift_capability_v1` | each flex core against the **generated flex RTL** at W = 4…36 (#965-#986); second ports; any-amount shift; per-target capability refusals. Helper: `flex_rtl_harness_v1.py` |
| **fp on cells** | `test_fp32_*_stage*_v1`, `test_fp32_*_chain_v1`, `test_fp32_stage_map_cells_v1`, `test_fp_blocks_v1`, `test_fp_add_v1`, `test_cross_tile_v1` | unpack, carry/high-word bumps, left-normalise, sticky, RNE, align with sticky, in RTL == FlexGrid (#982-#988); the open fp assembler's parametric blocks for fp32 and fp16 (#989, ~90 s); the whole fp adder (#990) and the crossing tile (#999), ~60 s together. Helpers: `fp32_stage_builder_v1.py`, `fp_block_runner_v1.py`; since then the adder's specials, subnormals and rounding modes (`test_fp_special_v1`, `test_fp_normalise_clamp_v1`, `test_fp_round_modes_v1`, #1001/#1006/#1007), the multiplier and comparator (`test_fp_mul_v1`, `test_fp_compare_v1`, #1008/#1009), wider words (`test_fp_wide_v1`, #1011), and the tight placements (`test_fp_*_tight_v1`, #1012-#1027). Helper: `fp_round_ref_v1.py` (exact references in every rounding mode) |
| **fp32 Python models** | `test_fp32_add_v1`, `_mul_`, `_div_`, `_compare_`, `_min_max_`, `_boundary_v1` | the reference models the cell designs are checked against |
| **VIX Carrier generation** | `test_vix_*`, `test_command_*`, `test_priority_*`, `test_mul_dispatch_v1`, `test_sequencer_core_v1` | the 11-core carrier VM, command core, priority arbiter, tile and opcode libraries, DAG dispatcher |
| **Compilers and frontends** | `test_dsl_compiler_v1`, `test_python_*frontend_v1`, `test_c_frontend_v1`, `test_llvm_*`, `test_dag_*`, `test_compiler_second_output_flag_v1` | DSL, Python-AST, C, LLVM IR (loop, DAG, VIX target) frontends; the second-output request |
| **Tile libraries** | `test_super_tile_library_v1`, `test_composed_*`, `test_user_tile_loader_v1`, `test_tile_designer_v1`, `test_loop_tiles_v1` | Tier-0/Tier-1 tiles, user models, composed tiles |
| **Grid-native mechanisms** | `test_fold_*`, `test_reconfig_loop_*`, `test_grid_native_*`, `test_pass_aware_drain_v1`, `test_section_drain_signal_v1`, `test_stage_pipeline_vs_fold_v1`, `test_branch_change_detector_v1`, `test_bounded_loop_ring_v1` | the reconfiguration loop and fold (#862-#885), drain events, loops built from cells |
| **Routing, layout and lanes** | `test_rats_nest_*`, `test_lane_*`, `test_*_layout_v1`, `test_*orientation_v1`, `test_t_tree_broadcast_v1`, `test_fanout_via_rats_nest_v1`, `test_connection_check_v1` | routing, timing, fan-out, lane split/recombine, stream layout |
| **DSP wrappers and BRAM** | `test_dsp_*`, `test_sentinel_*`, `test_shared_*`, `test_hierarchical_27leaf_collector_v1` | DSP wrapper VM and chain placement; sentinel/BRAM collectors |
| **Cards and tools** | `test_man_tang_nano_20k_v1`, `test_card_fit_v1`, `test_walker_sim_v1`, `test_workbench_v1`, `test_cell_pipeline_explainer_v1`, `test_host_*`, `test_loader_v1` | the generated Tang MAN, card fit, the simulated Walker, the workbench, the explainer page |
| **Priority, ram modes, board tests** | `test_priority_*_v1`, `test_ram_modes_flex_v1`, `test_ram_offer_preload_v1`, `test_flex_grid_priority_hold_v1`, `test_board_tests_v1`, `test_board_groups_v1` | the flex priority core in all three modes (#1017/#1018), the ram's constant / one-shot / hold behaviours (#1021), FlexGrid against them (#1022), and the on-board test package and its grouped bitstreams (#1023-#1025) |
| **Optimal transport** | `test_ot_w2_v1` | the 1D W2 engine (#1034): the merge formula vs the north-west corner algorithm vs a quantile integral, the merge network, and the n = 4 engine streamed in FlexGrid (the RTL test is skipped: generator ties) |

Not in this folder: the flex/sub generator suites are plain scripts in
`tests/test_flexsub_*.py`, and the front-end and assembler tests are in
`tests/tools/`. See `tests/README.md`.

| **corner tile and HOLD ram (#1035)** | `test_corner_tile_v1` (flex VM + generated RTL + ICM codec), `test_vix_corner_v1` (std VM `SuperGrid` + introspection), `test_vix_ram_hold_v1` (std VM HOLD), `test_rtl_hold_corner_v1` (iverilog: `tb_ram_hold_v4` on `ram_cell_v4`/`v4c`, `tb_corner_cell_v4` on `corner_cell_v4`/`v4c`, the existing ram testbenches, and both carriers with core 12 added) | the turning wiring tile (E-N/W-S or E-S/W-N) and the ram HOLD mode (fixed + upstream = hold, offer repeatedly, replace on arrival) in every model. NOT yet driven through the carrier's `core_select` 12 end to end: the carriers compile with it and their existing testbenches pass |
| **cross, second outputs, merge (#1036)** | `test_vix_corner_v1` (cross too), `test_vix_merge_v1` (std VM, 4 modes), `test_flex_merge_core_v1` (flex RTL == FlexGrid, modes 0/1 and sub refused), `test_flex_grid_second_port_v1` / `test_flex_grid_second_route_v1` (the std grid now accepts the flag), `test_rtl_hold_corner_v1` (iverilog: `tb_cross_cell_v4`, `tb_adder_second_v4`, `tb_mul_second_v5`, `tb_merge_cell_v4`, and `tb_vix_carrier_new_cores_v1`: the carrier drives corner 12, cross 13, merge 14 and the adder's carry end to end, v1 and v1d) | the straight wiring tile, the optional second output word and the merge core in every model and in the v4/v4c hardware |
- `test_flex_commutative_tie_v1.py` -- ledger #1036: the flex generator accepts a same-tick operand pair on mul / add (RTL = arithmetic, plain and stalled) and still refuses it for subtract.
- `test_playout_v1.py` -- ledger #1036: playout_v1 / capture_v1 (block-RAM feed and capture): lanes get their words in order under stalls; the 4-point W2 engine runs playout -> engine -> capture and equals the reference.
- `test_sd_spi_v1.py` -- ledger #1036: sd_spi_v1 against a behavioural SD card (bring-up, read, write, SDHC and byte-addressed) and the whole small unit card -> RAM -> 4-point W2 engine -> RAM -> card (about 4.5 min).
- `test_spi_bridge_v1.py` -- ledger #1036: spi_bridge_v1 / sd_unit_v1 with a simulated ESP32 (registers, words over SPI, SD load/play/save over SPI, and the 4-point W2 engine driven only over SPI, ~5.5 min).
- `test_sd_unit_top_v1.py` -- ledger #1036: tools/sd_unit_top_v1.py output (pins, simulated load/play/read/save, Gowin synthesis).
- `test_unit_bringup_v1.py` -- ledger #1036: the committed CORDIC unit bitstream package, the ESP32 sketch's pins/registers and the wiring sheet agree with the generator and the SPI bridge.
