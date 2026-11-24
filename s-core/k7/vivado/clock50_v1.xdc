# clock50_v1.xdc - 50 MHz (20 ns) on the SYS_CLK port, the same target as the open builds (nextpnr --freq 50). Read after sc_k7_v1.xdc.
create_clock -period 20.000 -name SYS_CLK [get_ports SYS_CLK]
