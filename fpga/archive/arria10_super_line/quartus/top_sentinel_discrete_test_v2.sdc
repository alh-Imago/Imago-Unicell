# top_sentinel_discrete_test_v2.sdc — points.md #306/#307 continuation:
# standalone real-hardware test of the sentinel's discrete-cell
# decomposition (accumulator_cell_v1.v + compare_cell_v1.v +
# latch_cell_v1.v). Same clocking convention as every other project
# here: 100.00 MHz single-ended on CLK_100M, divided by 4 internally
# to a 25 MHz fabric clock via div_cnt[1].
#
# WITHOUT this file Quartus assumes a fake ~1GHz clock on every node
# and reports meaningless timing numbers (the exact failure signature
# already documented at points.md #171/#241: a phantom auto-derived
# clock, ALM counts unaffected, timing verdicts meaningless) — this is
# what makes the Fmax/slack report real.

create_clock -name CLK_100M -period 10.000 [get_ports CLK_100M]

create_generated_clock -name clk_div -source [get_ports CLK_100M] -divide_by 4 \
    [get_registers {div_cnt[1]}]

derive_clock_uncertainty

set_false_path -to [get_ports {LED0_N LED1_N}]
