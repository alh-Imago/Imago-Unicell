# pre_opt.tcl — Pre-opt_design hook for XDMA 4.2 on 7-series
# Fixes Opt 31-67: undriven LUT inputs in pcie_block_i_i_10
# These are internal to the XDMA PCIe hard block and harmless.
# Without this hook opt_design treats them as errors and aborts.

# Find all LUT cells with undriven I0 pins in the PCIE2 block
set problem_cells [get_cells -quiet -hierarchical -filter {NAME =~ *pcie_block*}]

foreach cell $problem_cells {
    set pins [get_pins -quiet -of_objects $cell -filter {DIRECTION == IN}]
    foreach pin $pins {
        if {[get_nets -quiet -of_objects $pin] eq ""} {
            set_logic_zero $pin
        }
    }
}

# Also handle the specific known cell from the error message
set specific [get_cells -quiet \
    xdma_inst/inst/xdma_0_pcie2_to_pcie3_wrapper_i/pcie2_ip_i/inst/inst/pcie_block_i_i_10]
if {$specific ne ""} {
    set_logic_zero [get_pins -quiet -of_objects $specific -filter {DIRECTION == IN}]
}

puts "INFO: pre_opt.tcl complete — undriven PCIE2 LUT pins tied to GND"
