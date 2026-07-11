# =============================================================================
# clock_walk.sdc — Timing constraints for clock_walk_top
# (points.md #30, PLAN Step 2 -- throwaway PCIe refclk identification build)
# v2 (2026-07-11): expanded from 8 to 32 candidate refclk pins.
#
# Without this file Quartus calls `derive_clocks -period 1.0`, invents a 1 GHz
# clock on every unconstrained node, and times against it -- producing fake
# violations (same caution as Unicell-Q.sdc for the fabric builds).
# =============================================================================

# --- Board reference clock: 100 MHz, single-ended on PIN_E23 (proven pin) ---
create_clock -name CLK_100M -period 10.000 [get_ports CLK_100M]

# --- JTAG/probe-side clock: CLK = CLK_100M / 4 = 25 MHz ---------------------
create_generated_clock -name CLK -source [get_ports CLK_100M] -divide_by 4 \
    [get_registers {div_cnt[1]}]

# --- All 32 candidate PCIe refclk inputs ------------------------------------
# Each feeds ONE IOPLL instance's dedicated reference input only -- none of
# them touch general fabric logic, so a wrong guess here costs nothing timing-
# wise. Nominal PCIe refclk rate is 100 MHz; constrain all 32 at that rate
# regardless of which one (if any) is actually alive, so Quartus doesn't
# invent a 1 GHz assumption on the ones that turn out dead/unconnected.
create_clock -name refclk_1c_cht -period 10.000 [get_ports refclk_1c_cht]
create_clock -name refclk_1c_rx0 -period 10.000 [get_ports refclk_1c_rx0]
create_clock -name refclk_1c_rx1 -period 10.000 [get_ports refclk_1c_rx1]
create_clock -name refclk_1c_rx2 -period 10.000 [get_ports refclk_1c_rx2]
create_clock -name refclk_1c_rx3 -period 10.000 [get_ports refclk_1c_rx3]
create_clock -name refclk_1c_rx4 -period 10.000 [get_ports refclk_1c_rx4]
create_clock -name refclk_1c_rx5 -period 10.000 [get_ports refclk_1c_rx5]
create_clock -name refclk_1c_chb -period 10.000 [get_ports refclk_1c_chb]
create_clock -name refclk_1d_cht -period 10.000 [get_ports refclk_1d_cht]
create_clock -name refclk_1d_rx0 -period 10.000 [get_ports refclk_1d_rx0]
create_clock -name refclk_1d_rx1 -period 10.000 [get_ports refclk_1d_rx1]
create_clock -name refclk_1d_rx2 -period 10.000 [get_ports refclk_1d_rx2]
create_clock -name refclk_1d_rx3 -period 10.000 [get_ports refclk_1d_rx3]
create_clock -name refclk_1d_rx4 -period 10.000 [get_ports refclk_1d_rx4]
create_clock -name refclk_1d_rx5 -period 10.000 [get_ports refclk_1d_rx5]
create_clock -name refclk_1d_chb -period 10.000 [get_ports refclk_1d_chb]
create_clock -name refclk_1e_cht -period 10.000 [get_ports refclk_1e_cht]
create_clock -name refclk_1e_rx0 -period 10.000 [get_ports refclk_1e_rx0]
create_clock -name refclk_1e_rx1 -period 10.000 [get_ports refclk_1e_rx1]
create_clock -name refclk_1e_rx2 -period 10.000 [get_ports refclk_1e_rx2]
create_clock -name refclk_1e_rx3 -period 10.000 [get_ports refclk_1e_rx3]
create_clock -name refclk_1e_rx4 -period 10.000 [get_ports refclk_1e_rx4]
create_clock -name refclk_1e_rx5 -period 10.000 [get_ports refclk_1e_rx5]
create_clock -name refclk_1e_chb -period 10.000 [get_ports refclk_1e_chb]
create_clock -name refclk_1f_cht -period 10.000 [get_ports refclk_1f_cht]
create_clock -name refclk_1f_rx0 -period 10.000 [get_ports refclk_1f_rx0]
create_clock -name refclk_1f_rx1 -period 10.000 [get_ports refclk_1f_rx1]
create_clock -name refclk_1f_rx2 -period 10.000 [get_ports refclk_1f_rx2]
create_clock -name refclk_1f_rx3 -period 10.000 [get_ports refclk_1f_rx3]
create_clock -name refclk_1f_rx4 -period 10.000 [get_ports refclk_1f_rx4]
create_clock -name refclk_1f_rx5 -period 10.000 [get_ports refclk_1f_rx5]
create_clock -name refclk_1f_chb -period 10.000 [get_ports refclk_1f_chb]

# All clocks above are mutually asynchronous (independent physical sources, no
# shared logic between any of the 32 refclk-fed PLLs and the CLK_100M/CLK
# domain other than the double-flop synchronizer on each `locked` bit, which
# is exactly what a synchronizer is for).
set_clock_groups -asynchronous \
    -group {CLK_100M CLK} \
    -group {refclk_1c_cht} \
    -group {refclk_1c_rx0} \
    -group {refclk_1c_rx1} \
    -group {refclk_1c_rx2} \
    -group {refclk_1c_rx3} \
    -group {refclk_1c_rx4} \
    -group {refclk_1c_rx5} \
    -group {refclk_1c_chb} \
    -group {refclk_1d_cht} \
    -group {refclk_1d_rx0} \
    -group {refclk_1d_rx1} \
    -group {refclk_1d_rx2} \
    -group {refclk_1d_rx3} \
    -group {refclk_1d_rx4} \
    -group {refclk_1d_rx5} \
    -group {refclk_1d_chb} \
    -group {refclk_1e_cht} \
    -group {refclk_1e_rx0} \
    -group {refclk_1e_rx1} \
    -group {refclk_1e_rx2} \
    -group {refclk_1e_rx3} \
    -group {refclk_1e_rx4} \
    -group {refclk_1e_rx5} \
    -group {refclk_1e_chb} \
    -group {refclk_1f_cht} \
    -group {refclk_1f_rx0} \
    -group {refclk_1f_rx1} \
    -group {refclk_1f_rx2} \
    -group {refclk_1f_rx3} \
    -group {refclk_1f_rx4} \
    -group {refclk_1f_rx5} \
    -group {refclk_1f_chb}

derive_clock_uncertainty

# --- Status LEDs: not timing-critical ---------------------------------------
set_false_path -to [get_ports {LED0_N LED1_N}]
