# clock_walk_b.sdc — timing constraints for clock_walk_top_b (Build B of 2)
create_clock -name CLK_100M -period 10.000 [get_ports CLK_100M]
create_generated_clock -name CLK -source [get_ports CLK_100M] -divide_by 4 \
    [get_registers {div_cnt[1]}]

create_clock -name refclk_1e_rx0 -period 10.000 [get_ports refclk_1e_rx0]
create_clock -name refclk_1e_rx1 -period 10.000 [get_ports refclk_1e_rx1]
create_clock -name refclk_1e_rx2 -period 10.000 [get_ports refclk_1e_rx2]
create_clock -name refclk_1e_rx3 -period 10.000 [get_ports refclk_1e_rx3]
create_clock -name refclk_1e_rx4 -period 10.000 [get_ports refclk_1e_rx4]
create_clock -name refclk_1e_rx5 -period 10.000 [get_ports refclk_1e_rx5]
create_clock -name refclk_1f_rx0 -period 10.000 [get_ports refclk_1f_rx0]
create_clock -name refclk_1f_rx1 -period 10.000 [get_ports refclk_1f_rx1]
create_clock -name refclk_1f_rx2 -period 10.000 [get_ports refclk_1f_rx2]
create_clock -name refclk_1f_rx3 -period 10.000 [get_ports refclk_1f_rx3]
create_clock -name refclk_1f_rx4 -period 10.000 [get_ports refclk_1f_rx4]
create_clock -name refclk_1f_rx5 -period 10.000 [get_ports refclk_1f_rx5]

set_clock_groups -asynchronous \
    -group {CLK_100M CLK} \
    -group {refclk_1e_rx0} -group {refclk_1e_rx1} -group {refclk_1e_rx2} \
    -group {refclk_1e_rx3} -group {refclk_1e_rx4} -group {refclk_1e_rx5} \
    -group {refclk_1f_rx0} -group {refclk_1f_rx1} -group {refclk_1f_rx2} \
    -group {refclk_1f_rx3} -group {refclk_1f_rx4} -group {refclk_1f_rx5}

derive_clock_uncertainty
set_false_path -to [get_ports {LED0_N LED1_N}]
