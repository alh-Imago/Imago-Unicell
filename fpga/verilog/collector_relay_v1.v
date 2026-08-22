// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// collector_relay_v1.v — a real, dedicated replacement for the
// COLLECTOR role in `top_sentinel_gather_shared_bram_v1.v` (#413-
// #415), built directly from `#257`'s own already-designed "combiner
// core" (2026-08-09, never built until now) rather than the general-
// purpose `unicell_super_v1` shell running nano in relay mode.
//
// THE REAL PRINCIPLE (#427, Alan's own framing): the BRAM interface is
// dedicated, one-time infrastructure -- a card has ONE of these, then
// fills the rest with actual super carrier cells where the shell's own
// reconfigurability genuinely earns its cost (the user's own program
// substrate). This piece will NEVER need to become a different core at
// runtime, so paying the shell's own general-purpose overhead here
// (core_select mux, addon chain, 80-bit SUPER_LATCH) buys nothing --
// confirmed directly in the real numbers (#426): nano alone cost 68.8
// ALM, the single largest line item in the whole 347 ALM design, to
// deliver ONE narrow behavior (relay-mode pass-through) out of six
// possible cores it will never actually switch between.
//
// A REAL SIMPLIFICATION beyond just replacing nano, found by checking
// the actual wiring rather than assumed: the collector's 3 inputs
// (H1->N, H2->S, H3->W) are ALREADY wired simultaneously and gated by
// the SAME externally-driven round-robin readiness signals that
// already guarantee only one header can ever actually fire at a time
// (`#413`-`#415`'s own `fired_this_round`/`active_dir_idx` mutual
// exclusion). A STATIC-input combiner needs no runtime reprogramming
// at all to exploit that -- eliminating `cell_command_sequencer_v1`'s
// own real role in this specific spot too (9.5 ALM, #426), not just
// nano's. Matches `#257`'s own real design exactly: "arrival direction
// alone tells [it] which chain the data came from -- no ID needs to
// travel WITH the data at all."
//
// Real, deliberate scope: THIS module only implements the single-
// active-source case (#413-#415's own real usage, where the upstream
// round-robin already guarantees mutual exclusion) -- it does NOT
// implement #257's own separate "contention" handling (the write-side
// combiner's chain-select counter, needed only when MULTIPLE sources
// could genuinely arrive the same cycle). That real, harder case is
// explicitly NOT this module's job.
`default_nettype none
`timescale 1ns / 1ps

module collector_relay_v1 (
    input  wire        clk,
    input  wire        rst,

    // Three static cardinal inputs -- direction alone is the identity,
    // no ID/tag travels with the data at all.
    input  wire [31:0] data_in_a,  data_in_b,  data_in_c,
    input  wire        arrived_a,  arrived_b,  arrived_c,

    output wire        ack_out_a,  ack_out_b,  ack_out_c,

    // One fixed output.
    output wire [31:0] data_out,
    output wire        fire,
    input  wire        ready_in,
    input  wire        ack_in
);

    reg [31:0] out_buffer  = 32'h0;
    reg        data_valid  = 1'b0;   // set the cycle AFTER capture, matching
                                       // #257's own documented 2-cycle latency
                                       // (cycle 1: capture; cycle 2: offer) --
                                       // a real bug found and fixed in THIS
                                       // module's own first draft: `fire`
                                       // could assert the SAME cycle as
                                       // capture, before `out_buffer`'s own
                                       // NBA update had actually taken
                                       // effect, offering stale data for
                                       // one cycle. Fixed by gating the
                                       // offer on a flag that becomes valid
                                       // only once the capture has genuinely
                                       // landed.

    // Ack is CONDITIONAL on being ready to capture (`!data_valid`) --
    // a second real bug found and fixed before ever testing this: an
    // unconditional ack (accumulator's own pattern, correct there
    // because its internal state is always-live and never blocked)
    // would silently lose data here, since THIS module holds a single
    // buffer that can genuinely be full. Matches `ram_cell_v1.v`'s own
    // real discipline instead -- only ack an arrival this cycle
    // actually captures.
    wire any_arrival = (arrived_a || arrived_b || arrived_c) && !data_valid;
    assign ack_out_a = arrived_a && !data_valid;
    assign ack_out_b = arrived_b && !data_valid;
    assign ack_out_c = arrived_c && !data_valid;

    wire [31:0] captured_data = arrived_a ? data_in_a :
                                 arrived_b ? data_in_b :
                                             data_in_c;

    // Offer-holds-until-acked, same discipline as every other core.
    wire want_to_offer = data_valid;
    wire will_fire = want_to_offer && ready_in;

    assign fire = will_fire;
    assign data_out = out_buffer;

    always @(posedge clk) begin
        if (rst) begin
            out_buffer  <= 32'h0;
            data_valid  <= 1'b0;
        end else begin
            if (any_arrival) begin
                out_buffer <= captured_data;
                data_valid <= 1'b1;
            end else if (will_fire && ack_in) begin
                data_valid <= 1'b0;
            end
        end
    end

endmodule
