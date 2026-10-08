# `synth_gowin -nowidelut` sweeps (ledger #950)

Raw output of the three sweeps behind the ledger entry. Reproduce with:

| log | tool |
|---|---|
| `synth_sub_and_original_family.log` | `tools/measure_flag_across_families_v1.py` (the flex part of that run failed for want of a width; fixed afterwards) |
| `synth_flex_family.log` | the flex part of the same tool, rerun with WIDTH 32 |
| `pnr_lfsr_wrapped_sub_flex.log` | `tools/measure_flag_pnr_v1.py` (real nextpnr place-and-route, registered-input wrappers) |

Caveats: one run per configuration; yosys 0.33; the place-and-route Fmax is nextpnr's estimator against a 27 MHz target, many default-flow readings sit at
exactly 616.9 MHz (looks like an estimator ceiling), and seven cells report no Fmax (nextpnr: "no interior timing paths"). Not silicon.
An earlier bare-cell place-and-route sweep was discarded: its Fmax column read up to 1,493 MHz (unregistered IO; only register-to-register paths were timed).
