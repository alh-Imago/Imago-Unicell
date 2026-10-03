// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// adder_cell_v4sa.v -- points.md #906: "v4s" plus a minimal, reintroduced ack and
// a global freeze, per Alan's own real design direction (2026-09-30 morning).
// Builds on adder_cell_v4s.v (kept unchanged, as the zero-wait alternative for
// anyone who genuinely needs guaranteed fixed-cycle throughput); this is the
// SEPARATE, ack-bearing sibling, not a replacement.
//
// THE REAL DISTINCTION FROM THE ORIGINAL CARDINAL FAMILY'S ACK (why this isn't a
// retreat from "physics, not control"): what made the original expensive wasn't
// having a backward signal at all -- #889/#899 found it was the ARBITRATION: a
// 4-way mask deciding WHICH direction to wait for and WHICH to route to, every
// cycle. This cell's ack is POINT-TO-POINT: one fixed sender, one fixed receiver,
// decided at build time, same as in_a/in_b. There is no "who" to decide here --
// the topology is still fixed by construction. This adds a cheap SYNCHRONISATION
// primitive on top of a graph that stays fixed; it does not reintroduce the
// runtime ROUTING decision that was the actual expensive part.
//
// A real, valuable consequence worth stating plainly: this likely removes the
// need for the static latency-padding work `adder_cell_v4s.v`'s own header named
// as the real next step. That scheme only works if every cell's latency is known
// at compile time, and breaks the moment any future cell has data-dependent
// timing. A local ack solves the same underlying problem (don't let a fast
// path's fresh value collide with a slow path's stale one) in a way that is
// robust to ANY timing, known or not, with zero static analysis required.
//
// ── ack protocol (standard ready/valid, not a one-shot pulse) ──────────────
//   ack_out = this cell is ready to accept a NEW (in_a, in_b, valid_in) --
//             true whenever it isn't already holding an unconsumed result.
//   valid_out = this cell IS holding a real, not-yet-consumed result -- stays
//             HIGH across multiple cycles if the downstream receiver isn't
//             ready yet, unlike adder_cell_v4s.v's one-shot pulse. This is the
//             real behavioural difference reintroducing ack requires.
//   ack_in  = the downstream receiver has taken the current result; this cell
//             may present a new one starting next cycle.
// Latency is no longer always exactly one cycle -- it is AT LEAST one cycle,
// more if the downstream receiver stalls. That is the real, honest trade this
// file makes in exchange for removing the static-timing requirement.
//
// ── freeze: GLOBAL, not per-cell (Alan's own real refinement) ──────────────
// One signal, broadcast identically to every cell in the whole assembled
// design by the assembler -- not part of the ICM connection graph, not wired
// cell-to-cell. Two real jobs, not one: (1) the original stated purpose --
// hold the WHOLE system still while configuration is loaded into every cell,
// so nothing processes a partial or inconsistent config mid-load; (2) a real,
// useful side effect of going global rather than local -- freezing the whole
// system at any later point gives a clean, synchronised pause where every
// cell's state can be safely read out and compared against the VM's own
// mirrored computation, which per-cell freeze could never offer as cleanly.
// `armed` keeps its own, separate, narrower meaning (has this cell EVER
// received real config -- a one-way latch); freeze is the new, orthogonal,
// re-triggerable hold, and gates the ENTIRE update -- including whether a
// fresh `cfg_valid` may take effect -- not just the data path, so config can
// be loaded safely while frozen and nothing else moves until release.
`default_nettype none
`timescale 1ns / 1ps

module adder_cell_v4sa #(
    parameter [15:0] CELL_ID = 16'h0000,
    parameter        WIDTH   = 32   // points.md #909: the real "flex" width parameter --
                                     // Alan's own direction. Defaults to 32 so every
                                     // existing #906/#908 measurement stays exactly valid
                                     // unchanged; the assembler (once built, #903-905's
                                     // standing plan) is meant to override this per the
                                     // target's own MAN-file-recorded native width (18 for
                                     // this card, per #903/#904's own finding). cfg_data
                                     // deliberately stays a fixed 32 bits regardless of
                                     // WIDTH -- it only ever needs to hold a 1-bit
                                     // subtract_mode flag here, and other v4s cells
                                     // (sequencer_cell_v4s) already needed a config bus
                                     // wider than their own data width, so tying the two
                                     // together would be the wrong coupling.
) (
    input  wire        clk,
    input  wire        rst,
    input  wire        freeze_in,   // global, fanned out identically to every cell

    input  wire         cfg_valid,
    input  wire [31:0]  cfg_data,

    input  wire [WIDTH-1:0]  in_a,
    input  wire [WIDTH-1:0]  in_b,
    input  wire              valid_in,
    output wire               ack_out,     // backward, to whoever feeds in_a/in_b

    output wire [WIDTH-1:0]  data_out,
    output wire               valid_out,   // stays high until ack_in, not a one-shot pulse
    input  wire               ack_in       // backward, from the one fixed downstream receiver
);

    reg             subtract_mode = 1'b0;
    reg             armed         = 1'b0;   // narrow, permanent: has real config ever loaded
    reg             pending       = 1'b0;   // holding a real, not-yet-consumed result
    reg [WIDTH-1:0] out_buffer    = {WIDTH{1'b0}};

    // ── The real arithmetic -- unchanged from adder_v1, the same primitive
    // adder_cell_v4/v4c/v4s already use, now genuinely width-generic ──────
    wire [WIDTH-1:0] adder_b_in = subtract_mode ? ~in_b : in_b;
    wire [WIDTH-1:0] adder_sum;
    wire             adder_cout;
    adder_v1 #(.WIDTH(WIDTH)) ADD (
        .a(in_a), .b(adder_b_in), .cin(subtract_mode),
        .sum(adder_sum), .cout(adder_cout)
    );

    assign data_out  = out_buffer;
    assign valid_out = pending;
    assign ack_out   = armed && !pending && !freeze_in;   // a frozen cell must not claim
                                                            // readiness -- nothing can move

    always @(posedge clk) begin
        if (rst) begin
            subtract_mode <= 1'b0;
            armed         <= 1'b0;
            pending       <= 1'b0;
            out_buffer    <= {WIDTH{1'b0}};
        end else if (cfg_valid) begin
            // Config load takes effect even while frozen -- loading safely
            // during a freeze is the whole point of freeze existing.
            subtract_mode <= cfg_data[0];
            armed         <= 1'b1;
            pending       <= 1'b0;   // discard any in-flight result on reconfigure
            out_buffer    <= {WIDTH{1'b0}};
        end else if (!freeze_in) begin
            // Normal operation, only when not frozen. Exactly one of "clear a
            // consumed result" or "capture a fresh one" ever happens per
            // cycle -- never both, since ack_out is only ever true when
            // pending is already false, so a correctly-behaving upstream
            // sender never presents valid_in while pending is still true.
            if (pending) begin
                if (ack_in) pending <= 1'b0;
            end else if (valid_in) begin
                out_buffer <= adder_sum;
                pending    <= 1'b1;
            end
        end
        // else: frozen, not resetting, not reconfiguring -- hold everything
        // exactly as it is, including `pending`/`out_buffer`/`ack_out`'s own
        // registered state. A real, true pause.
    end

endmodule
