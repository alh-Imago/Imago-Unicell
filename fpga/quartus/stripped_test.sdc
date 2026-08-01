# stripped_test.sdc — timing constraints for top_stripped_ring_test_v1
# (points.md #83/#88-#94 stripped-cell first-silicon-fit check)
#
# Same board reference clock as every other project on this card: 100.00 MHz
# single-ended on CLK_100M (E23), confirmed on-card 21 Jun 2026 (see
# Unicell-Q.sdc). The design divides it by 4 internally to a 25 MHz fabric
# clock -- WITHOUT this file Quartus assumes a fake 1 GHz clock on every
# node and reports meaningless numbers; this is what makes the Fmax report
# real.

create_clock -name CLK_100M -period 10.000 [get_ports CLK_100M]

create_generated_clock -name clk_div -source [get_ports CLK_100M] -divide_by 4 \
    [get_registers {div_cnt[1]}]

derive_clock_uncertainty

set_false_path -to [get_ports {LED0_N LED1_N}]
