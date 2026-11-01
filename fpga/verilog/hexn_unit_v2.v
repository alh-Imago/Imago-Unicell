`default_nettype none
`timescale 1ns / 1ps
// hexn_unit_v2.v -- Hex-N open unit stage 9 (new file 1 Nov 2026; hexn_unit_v1 left as it was): a CHAIN of N gated units with a BYPASS SWITCH per unit, driven from the pattern bank (Alan, 19:19: 'start with the chain side ... like the chained dsp units on the arria 10, but here you define the steps, and when you have what you need, it just passes it through, so it's a core/cell bypass switch').
// DATA: a word is a pair {a, x} (W bits each). Stage i computes a' = f_i(a, b_i) and passes x on unchanged; b_i is chosen by the stage's config (bsrc = cfg[28:27]): 0 the side operand x, 1 the 8-bit step constant, 2 a itself. cfg[31] = BYPASS: 1 = this stage hands {a, x} straight to the next stage (a wire: no gate, no clocks, no block).
// config word of a stage = the arith_block_v10 word (mode [2:0], step [15:8], topology [25:16], held-mask [26], bsrc [28:27]) plus bypass [31]. A stage is reconfigured only through its own config_gate_v3, so a change never catches a word half way; a bypassed stage keeps its gate (it is switched back on the same way).
// COMMAND cfg18 (any NEW value starts it): [31:28] op, [27:24] sequence, [23:14] scratch base, [13:4] count (RUN), [11:8] unit (op 1) or number of units (op 3; 0 = all N), [5:0] slot (ops 1 and 3).
//   op 1 APPLY slot to unit: one stage, one status word at scratch[base].
//   op 3 PROGRAM: unit u gets pattern-bank slot (slot + u) for u = 0..n-1, one status word per unit at scratch[base+u]. Refused (ignored) if slot + n > 64 or n > N.
//   op 2 RUN count: operand pairs a = scratch[base+2k], x = scratch[base+2k+1]; the chain's result (a part of the last stage) is written to scratch[base+2*count+k]; 800 clocks without an answer writes 32'hFFFFFFFF and ends the run. Ignored if it would pass the end of the scratch RAM.
//   status word: [1:0] cfg_err, [2] fault, [3] dead, [4] engine time-out, [15:8] lost words, [23:16] region resets.
module hexn_stage_v1 #(parameter W = 18) (
    input  wire clk, input wire rst,
    input  wire [2*W-1:0] in_data, input wire in_valid, output wire in_ack,
    output wire [2*W-1:0] out_data, output wire out_valid, input wire out_ack,
    input  wire cfg_req, input wire [31:0] cfg_word, output wire cfg_done, output wire [31:0] status, output wire byp_o
);
    reg byp = 1'b0; assign byp_o = byp;
    wire g_ack, cfg_v, region_valid, done, cfg_busy, fault, dead, blocked, region_rst, b_valid, bv; wire [1:0] cfg_err; wire [7:0] resets, lost; wire [31:0] cfg_d; wire [2*W-1:0] region_data; wire [W-1:0] bo; wire [2*W-1:0] bd;
    wire rr = rst | region_rst;
    config_gate_v3 #(.WIDTH(2*W), .CFG_W(32), .SETTLE(1), .DRAIN_TIMEOUT(64), .WATCHDOG(100), .MAX_RETRY(2), .GOOD_WORDS(16)) G (
        .clk(clk), .rst(rst), .in_data(in_data), .in_valid(in_valid & ~byp), .in_ack(g_ack), .region_data(region_data), .region_valid(region_valid),
        .done(done), .res_valid(b_valid), .cfg_req(cfg_req), .cfg_word_in(cfg_word), .cfg_valid(cfg_v), .cfg_data(cfg_d), .cfg_busy(cfg_busy), .cfg_done(cfg_done), .cfg_err(cfg_err),
        .region_rst(region_rst), .fault(fault), .dead(dead), .blocked(blocked), .resets(resets), .lost(lost));
    arith_block_v10 #(.WIDTH(W)) B (.clk(clk), .rst(rr), .cfg_valid(cfg_v), .cfg_data(cfg_d), .in_a(region_data[2*W-1:W]), .in_b_side(region_data[W-1:0]), .valid_in(region_valid), .data_out(bo), .valid_out(bv));
    sub_to_flex_v1 #(.WIDTH(2*W)) O (.clk(clk), .rst(rr), .sub_data({bo, region_data[W-1:0]}), .sub_valid(bv), .out_data(bd), .out_valid(b_valid), .out_ack(out_ack & ~byp), .done(done));
    always @(posedge clk) if (rst) byp <= 1'b0; else if (cfg_v) byp <= cfg_d[31];     // changed only while the gate has drained and closed
    assign in_ack    = byp ? out_ack : g_ack;
    assign out_valid = byp ? in_valid : b_valid;
    assign out_data  = byp ? in_data  : bd;
    assign status = {resets, lost, 8'd0, 3'd0, 1'b0, dead, fault, cfg_err} ;
endmodule

module hexn_unit_v2 #(parameter N = 4, parameter W = 18) (
    input  wire clk, input wire rst, input wire [31:0] cmd,
    output wire busy,
    output reg  [9:0] ra, input wire [31:0] rd,
    output wire we, output wire [9:0] wa, output wire [31:0] wd,
    output reg  [5:0] pat_addr, input wire [31:0] pat_data,
    output wire [N-1:0] byp_flags
);
    localparam E_IDLE = 0, E_PA = 1, E_PB = 2, E_PC = 3, E_PW = 4, E_SW = 5, E_RA = 6, E_RB = 7, E_RC = 8, E_RD = 9, E_RE = 10, E_RF = 11, E_RG = 12, E_RH = 13, E_RW = 14, E_RN = 15, E_TO = 16, E_PN = 17;
    reg [4:0] st = E_IDLE; reg [31:0] cmd_q = 0; reg [9:0] base, cnt, k; reg [5:0] slot; reg [3:0] unit, nun, u; reg [W-1:0] a, b, res; reg [15:0] tmo; reg tmo_flag; reg [31:0] cfg_word; reg in_valid, out_ack; reg [N-1:0] cfg_req;
    // ---- the chain: d[i] is the word entering stage i
    wire [2*W-1:0] d [0:N]; wire v [0:N]; wire ack [0:N]; wire [N-1:0] cdone; wire [31:0] stat [0:N-1];
    assign d[0] = {a, b}; assign v[0] = in_valid; assign ack[N] = out_ack;
    genvar i;
    generate for (i = 0; i < N; i = i + 1) begin : S
        hexn_stage_v1 #(.W(W)) ST (.clk(clk), .rst(rst), .in_data(d[i]), .in_valid(v[i]), .in_ack(ack[i]), .out_data(d[i+1]), .out_valid(v[i+1]), .out_ack(ack[i+1]),
            .cfg_req(cfg_req[i]), .cfg_word(cfg_word), .cfg_done(cdone[i]), .status(stat[i]), .byp_o(byp_flags[i]));
    end endgenerate
    wire in_ack = ack[0]; wire out_valid = v[N]; wire [W-1:0] out_a = d[N][2*W-1:W];
    wire [3:0] op = cmd[31:28]; wire [9:0] c_base = cmd[23:14], c_cnt = cmd[13:4]; wire [3:0] c_unit = cmd[11:8]; wire [5:0] c_slot = cmd[5:0];
    wire [4:0] n_eff = (c_unit == 0) ? N : c_unit;
    wire ok = ((op == 4'd1) && (c_unit < N)) || ((op == 4'd3) && (n_eff <= N) && ({1'b0, c_slot} + n_eff <= 7'd64)) ||
              ((op == 4'd2) && (c_cnt != 0) && ({2'b00, c_base} + {1'b0, c_cnt, 1'b0} + {2'b00, c_cnt} <= 12'd1024));
    wire [31:0] cur_stat = stat[unit];
    assign busy = (st != E_IDLE);
    assign we = (st == E_SW) || (st == E_RW) || (st == E_TO);
    assign wa = (st == E_SW) ? base + {6'd0, u} : base + {cnt[8:0], 1'b0} + k;
    assign wd = (st == E_SW) ? (cur_stat | {27'd0, tmo_flag, 4'd0}) : (st == E_TO) ? 32'hFFFFFFFF : {{(32-W){1'b0}}, res};
    always @(posedge clk) begin
        cmd_q <= cmd; cfg_req <= {N{1'b0}}; out_ack <= 1'b0;
        if (rst) begin st <= E_IDLE; in_valid <= 1'b0; tmo_flag <= 1'b0; tmo <= 0; ra <= 0; pat_addr <= 0; k <= 0; cnt <= 0; base <= 0; u <= 0; unit <= 0; end
        else case (st)
            E_IDLE: if (cmd != cmd_q && ok) begin base <= c_base; cnt <= c_cnt; slot <= c_slot; k <= 0; u <= 0; tmo <= 0; tmo_flag <= 1'b0;
                if (op == 4'd1) begin unit <= c_unit; nun <= 4'd1; st <= E_PA; end
                else if (op == 4'd3) begin unit <= 4'd0; nun <= n_eff[3:0]; st <= E_PA; end
                else st <= E_RA; end
            // ---- APPLY / PROGRAM: slot (+ u) of the bank to unit
            E_PA: begin pat_addr <= slot + {2'b00, u}; st <= E_PB; end
            E_PB: st <= E_PC;
            E_PC: begin cfg_word <= pat_data; cfg_req[unit] <= 1'b1; tmo <= 0; st <= E_PW; end
            E_PW: begin tmo <= tmo + 1'b1; if (cdone[unit]) st <= E_SW; else if (tmo == 16'd4000) begin tmo_flag <= 1'b1; st <= E_SW; end end
            E_SW: st <= E_PN;                                          // the status word is written this cycle (we)
            E_PN: begin if (u + 4'd1 >= nun) st <= E_IDLE; else begin u <= u + 4'd1; unit <= unit + 4'd1; tmo_flag <= 1'b0; st <= E_PA; end end
            // ---- RUN
            E_RA: begin ra <= base + {k[8:0], 1'b0}; st <= E_RB; end
            E_RB: st <= E_RC;
            E_RC: begin a <= rd[W-1:0]; ra <= base + {k[8:0], 1'b0} + 10'd1; st <= E_RD; end
            E_RD: st <= E_RE;
            E_RE: begin b <= rd[W-1:0]; in_valid <= 1'b1; tmo <= 0; st <= E_RF; end
            E_RF: begin tmo <= tmo + 1'b1; if (in_ack) begin in_valid <= 1'b0; tmo <= 0; st <= E_RG; end
                       else if (out_valid) begin tmo <= 0; st <= E_RG; end              // the whole chain is bypassed: the word flows through wires and is acked only when the result is taken (E_RW)
                       else if (tmo == 16'd800) begin in_valid <= 1'b0; st <= E_TO; end end
            E_RG: begin tmo <= tmo + 1'b1; if (out_valid) st <= E_RH; else if (tmo == 16'd800) st <= E_TO; end
            E_RH: begin res <= out_a; out_ack <= 1'b1; st <= E_RW; end
            E_RW: begin in_valid <= 1'b0; st <= E_RN; end                  // out_ack is high this cycle: a word that flowed through bypassed stages is consumed now
            E_RN: if (k + 1'b1 >= cnt) st <= E_IDLE; else begin k <= k + 1'b1; st <= E_RA; end
            E_TO: begin tmo_flag <= 1'b1; st <= E_IDLE; end
            default: st <= E_IDLE;
        endcase
    end
endmodule
