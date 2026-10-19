## k7_tree4_v1.xdc -- pins as proven by the blink in ledger #1197 (card YPCB-00338-1P1, xc7k480tffg1156)
set_property PACKAGE_PIN AA28      [get_ports CLK]
set_property IOSTANDARD  LVCMOS18  [get_ports CLK]
create_clock -period 20.000 -name sys_clk [get_ports CLK]

set_property PACKAGE_PIN P30       [get_ports LED0]
set_property PACKAGE_PIN M30       [get_ports LED1]
set_property PACKAGE_PIN N30       [get_ports LED2]
set_property IOSTANDARD  LVCMOS18  [get_ports LED0]
set_property IOSTANDARD  LVCMOS18  [get_ports LED1]
set_property IOSTANDARD  LVCMOS18  [get_ports LED2]
