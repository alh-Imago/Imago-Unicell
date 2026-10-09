# full_tree_system.sdc — points.md #273 continuation: real Quartus
# size/timing check for the complete assembled distribution system
# (2-level mux tree, real chains, real adders, 2-level combiner tree,
# real BRAM round trip). Same clocking convention as every other
# project here.

create_clock -name CLK_100M -period 10.000 [get_ports CLK_100M]

create_generated_clock -name clk_div -source [get_ports CLK_100M] -divide_by 4 \
    [get_registers {div_cnt[1]}]

derive_clock_uncertainty

set_false_path -to [get_ports {LED0_N LED1_N}]
