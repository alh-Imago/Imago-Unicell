# The hp / hq builds: high half, byte and halfword loads, byte stores, timing fix (ledger #1598)

Nothing here has been built with Vivado or run on a card yet. It is tested in simulation (iverilog) and on the host interpreter. Read ledger #1590 to #1598 first.

## What is new (all in `sc_sys_v27.v`, parameter `MULU` = the multiply LEVEL)
| level | line | what the build has |
|---|---|---|
| 0 | hk | no multiply unit (sc_sys_v22, as before) |
| 1 | hm | low half of the product (sc_sys_v23, as before) |
| 2 | hq | + high half (load at +12), 4 DSP per block, + byte/half loads, + fit search fed from registers |
| 3 | hp | + the byte-store unit (sb / sh) |
- **High half:** device window byte 0x20000: store A (+0), store B (+4), load low (+8), load high (+12). Library routine `lib_mulhu32` (`jobio/lib_mulhu_unit.s` on level 2 and 3, `jobio/lib_mulhu.s` shift-and-add elsewhere); linked only into jobs that mention it.
- **Byte and halfword loads** (`lb lh lbu lhu`): the core `uc_core_v2w.v` accepts them; the slice picks the bits (no new state, same clocks). Unfused tasks only: a fused task (lw 1 and up) TRAPS on them. A halfword at an odd address is read as if aligned down.
- **Byte-store unit** (level 3): `sb` and `sh` are not core instructions (the core still traps on them); the assembler (`asm_ext_v1.py`) expands each into 5 instructions that use the unit: `addi t1,rs1,off; lui t0,0x20; sw t1,16(t0); sw rs2,20(t0) [24 for sh]; lw zero,16(t0)`. **They clobber t0 and t1**; rs2 must not be t0 or t1. A block-level engine reads the word, replaces the byte, and writes it back while holding the shared-RAM port for two clocks, so stores from different slices into one word cannot lose each other's bytes.
- **Timing fix:** `fit_search_tree_v2.v` and the registers for the job width in `sc_sys_v27.v` (the worst path of hm8s32u32n1i1024, #1592, started at `cur_lw`). Whether it is enough is only known from a build.

## Build files
`fpga/sc_block_v8.v`, `fpga/sc_top_k7_v20.v`, `k7/make_mb_v15.py` (6th argument = level 0 to 3), `k7/stage_mb_v14.sh`, `make_manifest_v4.py` (fields `mul_units` = level, `narrow_loads`, `byte_store_unit`). Host: `jobio_ext_v2.py`, `jobiss_v3.py`, `asm_ext_v1.py`, `score_store_v3.py`, `score_shell_v12.py`, `scwin_v23.py`.

## Build it (small first, on your machine)
Inside `s-core/k7` after `git pull`:
1. `python3 make_mb_v15.py 4 16 4 1 1024 3`     (the build `hp4s16u16n1i1024`; the known comparison build is `hm4s16u16n1i1024`)
2. `S_CORE=$HOME/Imago-Unicell-score/s-core sh stage_mb_v14.sh`
3. `sh run_builds_v1.sh hp4s16u16n1i1024`
Read the summary: **timing must pass before loading (never load a failed-timing bitstream).** Compare LUTs, DSP count and worst slack with hm4s16u16n1i1024. The expected DSP count is 16 (4 per block) plus the one stray block of #1589.
Then on the card: `batch batches/hp_test.score`. The 8-block build is the same command with `8 32 5 1 1024 3` (`hp8s32u32n1i1024`), about 1.5 hours.

## Tests that pass
`test_sys27.py S ULW FZ NU` (pool test of everything at S 4 and S 8), `test_fit_equiv_v2.py`, `test_hostext_v2.py`, `test_divc_v1.py`, shell v12 and window v23 tests; the three programs `vmulhu`, `vbyte`, `vbswap` register in the shell against an hp manifest and agree with their Python answers on the interpreter.

## Not done / not known
Area and timing on the Kintex; any card run; fused tasks with the byte-store unit (not tested) or narrow loads (they trap); the pool test above S 8; a negative control for the byte-store race test; sb/sh as real core instructions (they are expanded by the assembler, so compiler output with sb/sh needs the same expansion).
