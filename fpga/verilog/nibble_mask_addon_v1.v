// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// nibble_mask_addon_v1.v — second real ADDON in the nano/stripped line
// (points.md #253/#303/#309-#311). A genuine data-path wrapper, never
// touches gate computation — per-nibble BLOCK(1)/PASS(0) on a 32-bit
// word. Faithfully ported from `archeology/full-cell/verilog/
// unicell64_v3.v` (`m_nibble_mask`/`m_mask_en`), which applies this
// AFTER its own shift and BEFORE the gate on the input side — but
// unlike lane-cut (coupled specifically to shift-out, see
// `shift_lane_addon_v1.v`'s own header), nibble masking is genuinely
// independent of shift: it's a pure AND against a per-nibble keep
// mask, with no dependency on shift_amt or direction at all. Usable
// on either side of the cell's own data work, matching Alan's own
// placement-flexible framing.
//
// cfg bits, deliberately NOT cmd_latch bits (per #174's own resolved
// addon-delivery decision):
//   mask_en       — 1=apply the mask this cycle, 0=pass through
//   nibble_mask[7:0] — one bit per nibble (bit0=nibble[3:0], ...,
//                    bit7=nibble[31:28]); 1=BLOCK (zero that nibble),
//                    0=PASS (keep it unchanged)
`default_nettype none
`timescale 1ns / 1ps

module nibble_mask_addon_v1 (
    input  wire        mask_en,
    input  wire [7:0]  nibble_mask,
    input  wire [31:0] data_in,
    output wire [31:0] data_out
);

    wire [31:0] nibble_keep = {{4{~nibble_mask[7]}}, {4{~nibble_mask[6]}},
                                {4{~nibble_mask[5]}}, {4{~nibble_mask[4]}},
                                {4{~nibble_mask[3]}}, {4{~nibble_mask[2]}},
                                {4{~nibble_mask[1]}}, {4{~nibble_mask[0]}}};

    assign data_out = mask_en ? (data_in & nibble_keep) : data_in;

endmodule
