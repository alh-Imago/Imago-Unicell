// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
// blink_test.v — Minimal LED blink test for iCEBreaker
// No UART, no cells — just a counter driving LEDs.
// If this works, the FPGA is running and LEDs are wired correctly.
// Red LED blinks at ~1.4Hz, Green at ~0.7Hz.

`default_nettype none

module top (
    input  wire CLK,      // 12MHz
    output wire LEDR_N,   // Red LED (active low)
    output wire LEDG_N    // Green LED (active low)
);

reg [23:0] counter;

always @(posedge CLK)
    counter <= counter + 1;

// counter[23] toggles at 12MHz/2^24 = ~0.7Hz
// counter[22] toggles at ~1.4Hz
assign LEDR_N = ~counter[22];  // Red blinks fast
assign LEDG_N = ~counter[23];  // Green blinks slow

endmodule
