// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// bram_controller_v1.v — first real RTL draft of the BRAM command
// interface (points.md #248 task 3, first half — "a code plus the
// address"). DRAFT — sim-verified only, no Quartus data yet, and
// deliberately scoped to JUST the two commands Alan asked for: READ and
// WRITE. Does NOT yet solve the ≥4-chain distribution/arbitration
// question (task 3's other half, still fully open) or the chain-head-
// ack -> addr_counter_v1.v's advance_en wiring (#246's own open item) —
// this is the command mechanism those pieces will eventually drive.
//
// WIDTH, corrected in points.md #257: the original draft used
// DATA_WIDTH=32 as an arbitrary default. Checked directly against
// Intel's own M20K spec: a single M20K block's real native maximum-
// width configuration is 512 x 40 (20,480 bits total, including
// parity — usable as ordinary data bits if parity checking isn't
// needed), not 32. DATA_WIDTH now defaults to 40 to actually use the
// hardware's real native width — the 8 spare bits above the 32-bit
// payload are what `#257`/`#258`'s distribution-tree ID field packs
// into, natively, in the same single M20K access, no second read
// needed. Still fully parameterized — 40 is the new default, not a
// hard requirement.
//
// THE COMMAND: cmd_op is a 1-bit opcode — 1 bit is genuinely sufficient
// for 2 commands, but named as its own field (not folded into cmd_addr
// or inferred from context) so it reads clearly and leaves room if a
// third command is ever needed. cmd_addr is the target address —
// together, "a code plus the address" is exactly cmd_op + cmd_addr,
// asserted together with cmd_valid for one cycle per command.
//
// MEMORY INFERENCE: the single always block reading and writing the
// same `mem` array from one clocked process is the standard idiom
// Quartus recognizes for BRAM inference (M20K on Arria 10) — a genuine
// dual-purpose synchronous memory, not a LUT-RAM/register-file
// structure. NOT yet confirmed against a real Quartus fit (no M20K
// count in hand) — flagged, not assumed, same discipline as everything
// else here.
//
// LATENCY: this is a SINGLE-STAGE synchronous read — cmd_valid/cmd_addr
// must be stable BEFORE the clock edge, and rdata/rdata_valid are
// registered and visible immediately AFTER that same edge (the earliest
// a synchronous memory can respond; the real, standard M20K single-port
// read timing). Confirmed directly via iverilog against exact edge
// timing (`tb_bram_controller_v1.v`) after an earlier draft of that
// testbench itself miscounted by one cycle and wrongly flagged this as
// a DUT bug — it wasn't; the testbench's own check landed one edge too
// late. This one-registered-cycle figure is what `#243`'s own "BRAM
// read-latency absorption" open item will need to build against once a
// real consumer (a ram_cell_v1 chain head) is wired to this controller
// — not solved here, just established as a fixed, known quantity.
`default_nettype none
`timescale 1ns / 1ps

module bram_controller_v1 #(
    parameter ADDR_WIDTH = 16,
    parameter DATA_WIDTH = 40,
    parameter DEPTH       = (1 << ADDR_WIDTH)
) (
    input  wire                     clk,
    input  wire                     rst,

    // ── Command in — "a code plus the address" ─────────────────────────
    input  wire                     cmd_valid,
    input  wire                     cmd_op,      // 0=READ (OP_READ), 1=WRITE (OP_WRITE)
    input  wire [ADDR_WIDTH-1:0]    cmd_addr,
    input  wire [DATA_WIDTH-1:0]    cmd_wdata,   // only sampled when cmd_op==WRITE

    // ── Result out ───────────────────────────────────────────────────
    output reg                      rdata_valid, // pulses exactly 1 cycle after a READ command
    output reg  [DATA_WIDTH-1:0]    rdata,
    output reg                      write_done   // pulses the same cycle a WRITE genuinely lands
);

    localparam OP_READ  = 1'b0;
    localparam OP_WRITE = 1'b1;

    reg [DATA_WIDTH-1:0] mem [0:DEPTH-1];

    // Explicit zero-initialization — NOT part of the original draft.
    // Verilog reg arrays default to unknown ('x') until written, which
    // surfaced directly in tb_mem_interface_cell_v1.v's READ-mode test:
    // reading a never-written address returned 'x', correctly flagged
    // as a mismatch against an assumed-zero expected value. Real BRAM
    // content is genuinely undefined until written too, so the fix that
    // matters is making this controller's own behavior deterministic
    // (common practice for inferred BRAM, and Quartus supports this
    // `initial` idiom as M20K initial content in many cases) rather than
    // working around undefined reads in every consumer's test. NOT yet
    // confirmed this synthesizes to a real M20K initial-content load on
    // Arria 10 — flagged, not assumed.
    integer init_i;
    initial begin
        for (init_i = 0; init_i < DEPTH; init_i = init_i + 1)
            mem[init_i] = {DATA_WIDTH{1'b0}};
    end

    always @(posedge clk) begin
        rdata_valid <= 1'b0;
        write_done  <= 1'b0;
        if (rst) begin
            rdata_valid <= 1'b0;
            write_done  <= 1'b0;
        end else if (cmd_valid) begin
            if (cmd_op == OP_READ) begin
                rdata       <= mem[cmd_addr];
                rdata_valid <= 1'b1;
            end else begin // OP_WRITE
                mem[cmd_addr] <= cmd_wdata;
                write_done    <= 1'b1;
            end
        end
    end

endmodule
