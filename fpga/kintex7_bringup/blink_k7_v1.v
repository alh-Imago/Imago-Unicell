// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// blink_k7_v1.v - first bring-up design for the Kintex-7 XC7K480T card
// (YPCB-00338-1P1, xc7k480tffg1156-2) once it is powered stand-alone and
// reached over JTAG.  DRAFT, never built or loaded on the card yet.
//
// Three LEDs blink at three different rates from the 50 MHz clock, so one
// look at the card tells you the design loaded AND the clock is running:
//   LED0 (P30) toggles about every 0.34 s   (counter bit 24)
//   LED1 (M30) toggles about every 0.17 s   (counter bit 23)
//   LED2 (N30) toggles about every 0.084 s  (counter bit 22)
// Blinking looks the same whether the LEDs are active high or low.
// Pins and 50 MHz clock come from the old board file (part0_pins.xml);
// they have not been measured on this card.

`default_nettype none

module top #(
    parameter BASE = 22          // lowest counter bit shown (sim uses a small value)
) (
    input  wire CLK,             // 50 MHz, AA28, LVCMOS18
    output wire LED0,
    output wire LED1,
    output wire LED2
);

    reg [BASE+2:0] counter = 0;
    always @(posedge CLK) counter <= counter + 1'b1;

    assign LED0 = counter[BASE+2];
    assign LED1 = counter[BASE+1];
    assign LED2 = counter[BASE];

endmodule
