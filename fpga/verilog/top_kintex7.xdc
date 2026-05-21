## top_kintex7.xdc — Constraints for YZCA-00338-104 Kintex-7 card
## Pin assignments from blinky-ypcb003381p1/ypcb003381p1.xdc
## openXC7 toolchain
##
## TODO: Fill in exact pin assignments from the blinky XDC file:
##   ~/demo-projects/blinky-ypcb003381p1/ypcb003381p1.xdc
##
## Template — replace ??? with actual pin numbers from that file

## Clock — differential LVDS
set_property PACKAGE_PIN ???    [get_ports CLK_P]
set_property PACKAGE_PIN ???    [get_ports CLK_N]
set_property IOSTANDARD  LVDS   [get_ports CLK_P]
set_property IOSTANDARD  LVDS   [get_ports CLK_N]

## Timing constraint — adjust MHz to match actual clock
create_clock -period 10.000 -name sys_clk [get_ports CLK_P]

## UART
set_property PACKAGE_PIN ???        [get_ports UART_RX]
set_property PACKAGE_PIN ???        [get_ports UART_TX]
set_property IOSTANDARD  LVCMOS33   [get_ports UART_RX]
set_property IOSTANDARD  LVCMOS33   [get_ports UART_TX]

## Reset button
set_property PACKAGE_PIN ???        [get_ports BTN_RST_N]
set_property IOSTANDARD  LVCMOS33   [get_ports BTN_RST_N]

## LEDs
set_property PACKAGE_PIN ???        [get_ports LED0]
set_property PACKAGE_PIN ???        [get_ports LED1]
set_property PACKAGE_PIN ???        [get_ports LED2]
set_property PACKAGE_PIN ???        [get_ports LED3]
set_property IOSTANDARD  LVCMOS33   [get_ports LED0]
set_property IOSTANDARD  LVCMOS33   [get_ports LED1]
set_property IOSTANDARD  LVCMOS33   [get_ports LED2]
set_property IOSTANDARD  LVCMOS33   [get_ports LED3]
