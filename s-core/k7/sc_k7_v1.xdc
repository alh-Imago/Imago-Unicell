# sc_top_k7_v1.xdc - pins for the S-Core pool on the YPCB-00338-1P1 (XC7K480T-FFG1156).  Taken from docs/man/kintex7-ypcb00338.xdc (CLK AA28, LEDs).
# The SYS_CLK name is the top port.  No other pins: the host link is the JTAG user register inside the chip.
# nextpnr-xilinx cannot parse trailing comments on a constraint line: keep them on their own lines.
set_property PACKAGE_PIN AA28 [get_ports SYS_CLK]
set_property IOSTANDARD LVCMOS18 [get_ports SYS_CLK]
set_property PACKAGE_PIN P30 [get_ports {led[0]}]
set_property PACKAGE_PIN M30 [get_ports {led[1]}]
set_property PACKAGE_PIN N30 [get_ports {led[2]}]
set_property IOSTANDARD LVCMOS18 [get_ports {led[0]}]
set_property IOSTANDARD LVCMOS18 [get_ports {led[1]}]
set_property IOSTANDARD LVCMOS18 [get_ports {led[2]}]
