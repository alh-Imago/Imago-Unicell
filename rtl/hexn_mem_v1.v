`default_nettype none
// hexn_mem_v1.v -- Hex-N SAVE AND RECALL memory block (model: tools/hexn_saverecall_model_v1.py). NB wires, M slots.
// Per wire a saturating up/down counter (4 bits, clamp +-7): WATCH adds +1 (wire high) or -1 (wire low) for every wire whose mask bit is 1 and adds the mask to the 'known' set. The integrated (cleaned) pattern is bit = (counter > 0), a tie or an unwatched wire gives 0.
// SAVE copies the integrated pattern into slot sel and marks it valid. RECALL compares the integrated pattern with every VALID slot over the KNOWN wires only (matches = known wires equal), slot after slot (M clocks), keeps the best and the second best match count
// (a tie sets second = best; the lowest-numbered slot wins a tie for best), then gives: best slot id (15 = none), best matches, second matches, number of known wires, the integrated cue, the recalled slot, and the deviation mask = (cue XOR recalled) AND known.
// No policy here (the familiar / not familiar decision belongs to the host). CLR clears counters and known, CLRALL clears the valid flags.
module hexn_mem_v1 #(parameter NB = 18, parameter M = 8) (
    input  wire clk, input wire rst,
    input  wire op_clr, input wire op_clrall, input wire op_watch, input wire [NB-1:0] w_bits, input wire [NB-1:0] w_mask,
    input  wire op_save, input wire [2:0] sv_slot, input wire op_recall, output reg done,
    input  wire [2:0] rd_slot, output wire rd_valid, output wire [NB-1:0] rd_bits,
    output reg [3:0] best_id, output reg [7:0] best_m, output reg [7:0] second_m, output wire [7:0] known_cnt,
    output wire [NB-1:0] cue_bits, output wire [NB-1:0] rec_bits, output wire [NB-1:0] dev_mask
);
    reg signed [3:0] c [0:NB-1]; reg [NB-1:0] known; reg [NB-1:0] slot [0:M-1]; reg [M-1:0] valid;
    reg [NB-1:0] cue; integer j;
    always @* for (j = 0; j < NB; j = j + 1) cue[j] = (c[j] > 0);
    assign cue_bits = cue;
    function [7:0] pc(input [NB-1:0] v); integer q; begin pc = 0; for (q = 0; q < NB; q = q + 1) pc = pc + v[q]; end endfunction
    assign known_cnt = pc(known);
    assign rd_valid = valid[rd_slot]; assign rd_bits = slot[rd_slot];
    reg [3:0] s; reg run; wire [NB-1:0] cur = slot[s[2:0]]; wire [7:0] mcur = pc(~(cue ^ cur) & known);
    assign rec_bits = (best_id < M) ? slot[best_id[2:0]] : {NB{1'b0}};
    assign dev_mask = (cue ^ rec_bits) & known;
    integer k;
    always @(posedge clk) begin
        if (rst) begin for (k = 0; k < NB; k = k + 1) c[k] <= 0; known <= 0; valid <= 0; run <= 0; done <= 0; best_id <= 4'd15; best_m <= 0; second_m <= 0; s <= 0; end
        else begin
            if (op_clrall) valid <= 0;
            if (op_clr) begin for (k = 0; k < NB; k = k + 1) c[k] <= 0; known <= 0; end
            else if (op_watch) begin
                known <= known | w_mask;
                for (k = 0; k < NB; k = k + 1) if (w_mask[k]) c[k] <= w_bits[k] ? ((c[k] == 4'sd7) ? c[k] : c[k] + 4'sd1) : ((c[k] == -4'sd7) ? c[k] : c[k] - 4'sd1);
            end
            if (op_save) begin slot[sv_slot] <= cue; valid[sv_slot] <= 1'b1; end
            if (op_recall) begin run <= 1; done <= 0; s <= 0; best_id <= 4'd15; best_m <= 0; second_m <= 0; end
            else if (run) begin
                if (valid[s[2:0]]) begin
                    if (mcur > best_m) begin second_m <= best_m; best_m <= mcur; best_id <= s; end
                    else if (mcur > second_m) second_m <= mcur;
                end
                if (s == M - 1) begin run <= 0; done <= 1; end else s <= s + 1'b1;
            end
        end
    end
endmodule
`default_nettype wire
