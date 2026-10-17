## blink_k7_v1.xdc - pins for the first bring-up design (DRAFT, not yet tried on the card)
## Taken from archeology/full-cell/verilog/top_kintex7.xdc (board-file pins, LVCMOS18).
## No reset button is used here on purpose: fewer pins that could be wrong.

set_property PACKAGE_PIN AA28      [get_ports CLK]
set_property IOSTANDARD  LVCMOS18  [get_ports CLK]
create_clock -period 20.000 -name sys_clk [get_ports CLK]

set_property PACKAGE_PIN P30       [get_ports LED0]
set_property PACKAGE_PIN M30       [get_ports LED1]
set_property PACKAGE_PIN N30       [get_ports LED2]
set_property IOSTANDARD  LVCMOS18  [get_ports LED0]
set_property IOSTANDARD  LVCMOS18  [get_ports LED1]
set_property IOSTANDARD  LVCMOS18  [get_ports LED2]
