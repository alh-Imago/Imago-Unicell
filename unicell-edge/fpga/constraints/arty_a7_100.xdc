# arty_a7_100.xdc — Arty A7-100T Constraints
# Imago UniCell — Claudette v1.1
# Artix-7 XC7A100T-1CSG324C
#
# Pinout is identical to A7-35 — same PCB, different FPGA device.
# Use top_arty_a7.v with `define ARTY_A7_100 for 1024-cell array.

## Clock
set_property PACKAGE_PIN E3 [get_ports CLK]
set_property IOSTANDARD LVCMOS33 [get_ports CLK]
create_clock -add -name sys_clk_pin -period 10.00 -waveform {0 5} [get_ports CLK]

## UART (USB-UART via FTDI)
set_property PACKAGE_PIN A9  [get_ports RX]
set_property PACKAGE_PIN D10 [get_ports TX]
set_property IOSTANDARD LVCMOS33 [get_ports RX]
set_property IOSTANDARD LVCMOS33 [get_ports TX]

## Push buttons
set_property PACKAGE_PIN D9 [get_ports {BTN[0]}]
set_property PACKAGE_PIN C9 [get_ports {BTN[1]}]
set_property PACKAGE_PIN B9 [get_ports {BTN[2]}]
set_property PACKAGE_PIN B8 [get_ports {BTN[3]}]
set_property IOSTANDARD LVCMOS33 [get_ports {BTN[*]}]

## Slide switches
set_property PACKAGE_PIN A8  [get_ports {SW[0]}]
set_property PACKAGE_PIN C11 [get_ports {SW[1]}]
set_property PACKAGE_PIN C10 [get_ports {SW[2]}]
set_property PACKAGE_PIN A10 [get_ports {SW[3]}]
set_property IOSTANDARD LVCMOS33 [get_ports {SW[*]}]

## User LEDs
set_property PACKAGE_PIN H5  [get_ports {LED[0]}]
set_property PACKAGE_PIN J5  [get_ports {LED[1]}]
set_property PACKAGE_PIN T9  [get_ports {LED[2]}]
set_property PACKAGE_PIN T10 [get_ports {LED[3]}]
set_property IOSTANDARD LVCMOS33 [get_ports {LED[*]}]

## RGB LED 0
set_property PACKAGE_PIN G6 [get_ports {LED0_RGB[0]}]
set_property PACKAGE_PIN F6 [get_ports {LED0_RGB[1]}]
set_property PACKAGE_PIN E1 [get_ports {LED0_RGB[2]}]
set_property IOSTANDARD LVCMOS33 [get_ports {LED0_RGB[*]}]

## RGB LED 1
set_property PACKAGE_PIN G3 [get_ports {LED1_RGB[0]}]
set_property PACKAGE_PIN J4 [get_ports {LED1_RGB[1]}]
set_property PACKAGE_PIN G4 [get_ports {LED1_RGB[2]}]
set_property IOSTANDARD LVCMOS33 [get_ports {LED1_RGB[*]}]
