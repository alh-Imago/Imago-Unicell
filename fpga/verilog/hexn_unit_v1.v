`default_nettype none
`timescale 1ns / 1ps
// hexn_unit_v1.v -- Hex-N open unit stage 8 (new file 1 Nov 2026): ONE GATED MUTABLE UNIT = config_gate_v3 -> arith_block_v9 (WIDTH 18) -> sub_to_flex_v1, plus a small engine that (1) APPLIES a pattern from the pattern bank (table space 7) to the block through the gate, and (2) RUNS a batch of operand pairs through the unit, all from the scratch RAM. (Alan, 18:35: 'move on and upwards'; 18:09: the patterns are the save / load part.)
// Command word cfg18 (any NEW value starts it): [31:28] op, [27:24] sequence (change it to repeat a command), [23:14] scratch base, [13:4] count, [5:0] slot (op 1).
//   op 1 APPLY slot: read pat[slot], send it through the gate as a reconfiguration (the gate drains, programs, settles, reopens), then write ONE status word at scratch[base]: [1:0] cfg_err, [2] fault, [3] dead, [4] engine timeout, [15:8] lost words, [23:16] region resets.
//   op 2 RUN count: for k in 0..count-1: operands a = scratch[base+2k], b = scratch[base+2k+1] (low 18 bits each) go through the gate and the block; the result (18 bits, zero-extended) is written to scratch[base+2*count+k]. A word that gets no answer within the time limit writes 32'hFFFFFFFF there and ends the run.
//   Needs base+2*count+count <= 1024 for RUN; a command that would run past the scratch RAM, or an unknown op, is ignored (busy never goes high).
// busy is high from the clock after a command is accepted until it is finished. The scratch RAM write/read ports are owned by this engine while busy (like the raw engine).
module hexn_unit_v1 #(parameter W = 18) (
    input  wire clk, input wire rst, input wire [31:0] cmd,
    output wire busy,
    output reg  [9:0] ra, input wire [31:0] rd,              // scratch read: address, data one cycle later
    output wire we, output wire [9:0] wa, output wire [31:0] wd,
    output reg  [5:0] pat_addr, input wire [31:0] pat_data   // pattern bank read: data one cycle later
);
    localparam E_IDLE = 0, E_PA = 1, E_PB = 2, E_PC = 3, E_PW = 4, E_SW = 5, E_RA = 6, E_RB = 7, E_RC = 8, E_RD = 9, E_RE = 10, E_RF = 11, E_RG = 12, E_RH = 13, E_RW = 14, E_RN = 15, E_TO = 16;
    reg [4:0] st = E_IDLE; reg [31:0] cmd_q = 0; reg [9:0] base, cnt, k; reg [5:0] slot; reg [W-1:0] a, b, res; reg [15:0] tmo; reg tmo_flag; reg cfg_req; reg [31:0] cfg_word;
    wire [W*2-1:0] in_data = {a, b}; reg in_valid, out_ack;
    wire in_ack, out_valid; wire [W-1:0] out_data;
    wire cfg_done, cfg_busy, fault, dead, blocked, region_rst; wire [1:0] cfg_err; wire [7:0] resets, lost;
    wire rr = rst | region_rst;
    wire [W*2-1:0] region_data; wire region_valid, done; wire cfg_v; wire [31:0] cfg_d; wire [W-1:0] bo; wire bv;
    config_gate_v3 #(.WIDTH(W*2), .CFG_W(32), .SETTLE(1), .DRAIN_TIMEOUT(64), .WATCHDOG(100), .MAX_RETRY(2), .GOOD_WORDS(16)) G (
        .clk(clk), .rst(rst), .in_data(in_data), .in_valid(in_valid), .in_ack(in_ack), .region_data(region_data), .region_valid(region_valid),
        .done(done), .res_valid(out_valid), .cfg_req(cfg_req), .cfg_word_in(cfg_word), .cfg_valid(cfg_v), .cfg_data(cfg_d), .cfg_busy(cfg_busy), .cfg_done(cfg_done), .cfg_err(cfg_err),
        .region_rst(region_rst), .fault(fault), .dead(dead), .blocked(blocked), .resets(resets), .lost(lost));
    arith_block_v9 #(.WIDTH(W)) B (.clk(clk), .rst(rr), .cfg_valid(cfg_v), .cfg_data(cfg_d), .in_a(region_data[W*2-1:W]), .in_b(region_data[W-1:0]), .valid_in(region_valid), .data_out(bo), .valid_out(bv));
    sub_to_flex_v1 #(.WIDTH(W)) O (.clk(clk), .rst(rr), .sub_data(bo), .sub_valid(bv), .out_data(out_data), .out_valid(out_valid), .out_ack(out_ack), .done(done));
    wire [3:0] op = cmd[31:28]; wire [9:0] c_base = cmd[23:14], c_cnt = cmd[13:4];
    wire ok = (op == 4'd1) || ((op == 4'd2) && (c_cnt != 0) && ({2'b00, c_base} + {1'b0, c_cnt, 1'b0} + {2'b00, c_cnt} <= 12'd1024));
    assign busy = (st != E_IDLE);
    assign we = (st == E_SW) || (st == E_RW) || (st == E_TO);
    assign wa = (st == E_SW) ? base : base + {cnt[8:0], 1'b0} + k;
    assign wd = (st == E_SW) ? {resets, lost, 3'd0, tmo_flag, dead, fault, cfg_err} : (st == E_TO) ? 32'hFFFFFFFF : {{(32-W){1'b0}}, res};
    always @(posedge clk) begin
        cmd_q <= cmd; cfg_req <= 1'b0; out_ack <= 1'b0;
        if (rst) begin st <= E_IDLE; in_valid <= 1'b0; tmo_flag <= 1'b0; tmo <= 0; ra <= 0; pat_addr <= 0; k <= 0; cnt <= 0; base <= 0; end
        else case (st)
            E_IDLE: if (cmd != cmd_q && ok) begin base <= c_base; cnt <= c_cnt; slot <= cmd[5:0]; k <= 0; tmo <= 0; tmo_flag <= 1'b0; st <= (op == 4'd1) ? E_PA : E_RA; end
            // ---- APPLY
            E_PA: begin pat_addr <= slot; st <= E_PB; end
            E_PB: st <= E_PC;                                          // the RAM read happens at this edge
            E_PC: begin cfg_word <= pat_data; cfg_req <= 1'b1; tmo <= 0; st <= E_PW; end
            E_PW: begin tmo <= tmo + 1'b1; if (cfg_done) st <= E_SW; else if (tmo == 16'd4000) begin tmo_flag <= 1'b1; st <= E_SW; end end
            E_SW: st <= E_IDLE;                                        // the status word is written this cycle (we)
            // ---- RUN
            E_RA: begin ra <= base + {k[8:0], 1'b0}; st <= E_RB; end
            E_RB: st <= E_RC;
            E_RC: begin a <= rd[W-1:0]; ra <= base + {k[8:0], 1'b0} + 10'd1; st <= E_RD; end
            E_RD: st <= E_RE;
            E_RE: begin b <= rd[W-1:0]; in_valid <= 1'b1; tmo <= 0; st <= E_RF; end
            E_RF: begin tmo <= tmo + 1'b1; if (in_ack) begin in_valid <= 1'b0; tmo <= 0; st <= E_RG; end else if (tmo == 16'd800) begin in_valid <= 1'b0; st <= E_TO; end end
            E_RG: begin tmo <= tmo + 1'b1; if (out_valid) st <= E_RH; else if (tmo == 16'd800) st <= E_TO; end
            E_RH: begin res <= out_data; out_ack <= 1'b1; st <= E_RW; end
            E_RW: st <= E_RN;                                          // the result word is written this cycle (we)
            E_RN: if (k + 1'b1 >= cnt) st <= E_IDLE; else begin k <= k + 1'b1; st <= E_RA; end
            E_TO: begin tmo_flag <= 1'b1; st <= E_IDLE; end            // the timeout marker is written this cycle (we)
            default: st <= E_IDLE;
        endcase
    end
endmodule
