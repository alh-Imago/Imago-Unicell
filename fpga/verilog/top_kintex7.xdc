## top_kintex7.xdc — Constraints for YZCA-00338-104 / xc7k480tffg1156
## Pin assignments from part0_pins.xml
## ALL I/O: LVCMOS18 (1.8V banks)
##
## Note: No dedicated UART pins on this card.
##       Card is PCIe-only. UART stubbed in top_kintex7.v.
##       IIC pins N24/N25 connect to LM73 temp sensor — not usable as UART.
##
## Clock: 50MHz single-ended (simpler than 200MHz LVDS for initial bring-up)
## LEDs:  3 available (Red/Green/Yellow)
## Reset: SW_RESET button

## Clock — 50MHz single-ended
set_property PACKAGE_PIN AA28      [get_ports CLK]
set_property IOSTANDARD  LVCMOS18  [get_ports CLK]
create_clock -period 20.000 -name sys_clk [get_ports CLK]

## Reset — SW_RESET active low
set_property PACKAGE_PIN R28       [get_ports BTN_RST_N]
set_property IOSTANDARD  LVCMOS18  [get_ports BTN_RST_N]

## LEDs
set_property PACKAGE_PIN P30       [get_ports LED0]
set_property PACKAGE_PIN M30       [get_ports LED1]
set_property PACKAGE_PIN N30       [get_ports LED2]
set_property IOSTANDARD  LVCMOS18  [get_ports LED0]
set_property IOSTANDARD  LVCMOS18  [get_ports LED1]
set_property IOSTANDARD  LVCMOS18  [get_ports LED2]
