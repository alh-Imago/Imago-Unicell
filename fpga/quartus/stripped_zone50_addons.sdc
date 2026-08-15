# stripped_zone50_addons.sdc — points.md #312: addon-cost comparison
# variant of stripped_zone50.sdc (#148's 50-cell zone base figure).
# IDENTICAL clocking template to the baseline -- this is a same-scale,
# same-clock-structure comparison, only the addon wiring differs.

create_clock -name CLK_100M -period 10.000 [get_ports CLK_100M]

create_generated_clock -name clk_div -source [get_ports CLK_100M] -divide_by 4 \
    [get_registers {div_cnt[1]}]

derive_clock_uncertainty

set_false_path -to [get_ports {LED0_N LED1_N}]
