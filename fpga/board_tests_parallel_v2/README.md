# Tang Nano 20K — "no interrupts" and "parallel" tests (ledger #1180, corrected #1182)

**v2 (#1182): the first run's storm lanes (iso_s4, iso_s8) were deleted by the synthesis tool, so group P was rebuilt with the storm outputs kept (8,123 LUT4 and 4,158 flip-flops against 6,429 and 2,116 before). Groups Q and R are unchanged and already passed on the card. Run only group P: `sudo ONLY=P ./run_groups_parallel_v2.sh`. The collector will say T4 and T5 are incomplete for a P-only run; that is expected.**

Tests T1, T4, T5 of `docs/NO_INTERRUPT_PARALLEL_TEST_PLAN_v1.md`. They need only the Tang Nano 20K on USB (no extra parts). T2, T3 and C1 need the ESP32 parts and are not here.

**The job** is one small lane of flex cells: entry → relay → adder (+5) → exit. 64 words go in, each must come out as input + 5. Nothing random: no gaps, no exit stalls, so the number of clocks the job takes (`last=` in the report line) is exact and must equal the simulation.

| Test | Designs | Question | Pass looks like |
|---|---|---|---|
| T1 isolation | `iso_s0`, `iso_s4`, `iso_s8` | Does the job's clock count change when 0, 4 or 8 other lanes are being hammered (a new word offered on every clock)? | all three equal (simulation: 131) |
| T4 copies | `ind_0`..`ind_3` | Do four independent copies running at once each finish as fast as the single job? | all equal to `iso_s0` |
| T5 shared port | `sh_k2`, `sh_k4`, `sh_k8` (and `iso_s0` as 1 lane) | The same 64 words through 1, 2, 4, 8 lanes behind ONE input and ONE output: where does adding lanes stop helping? | simulation already says: no gain, because one lane fills the bench's single port (one word per two clocks) |

Honest scope: T5 as built shows the port limit, not a speed-up first; the lanes are not the bottleneck. T1 and T4 show the cells do not slow each other; the clock, reset and report line are the only things shared. The bench's own exit port and serial line are shared resources and do queue.

## Run
Unzip the whole zip into one folder (it has a `groups` folder). Three bitstreams (P, Q, R), each loaded once after a fresh power-up:

    sudo ./run_groups_parallel_v2.sh [/dev/ttyUSB1]

It asks you to switch the board off/on before each group. Each bitstream reports its tests in turn on the serial line (about 0.6 s each). Results: `board_results.txt`. Send that file back.

Needs `openFPGALoader`, python3, root.

## Files
`groups/group_{P,Q,R}.{fs,json,v,cst}` bitstreams and the simulated report lines; `board_collect_parallel_v1.py` (compares the full line including `last=`); built by `tools/board_parallel_v1.py`.
