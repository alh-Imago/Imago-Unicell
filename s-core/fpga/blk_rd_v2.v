// blk_rd_v2.v - blk_rd_v1 with every status signal passed to the byte function as an extra (unused) argument.  In simulation a function called from an assign is only
//   re-evaluated when its ARGUMENTS change, so a status signal that settles a clock after cmd / idx (the job ID q_tid with the new command bus, ledger #1459) gave the previous
//   value in byte 0 of an E reply.  Synthesis ignores the argument, so the hardware is the same.  Cloned from blk_rd_v1.v (left as proven).
// blk_rd_v1.v - the status-reading half of host_bridge_v11, moved INTO each block's side of the top so that only ONE BYTE per block (rbyte) crosses to the bridge
//   instead of about 1,600 (8 slices) or 2,200 (16 slices) status wires per block (ledger #1457; the reading of #1456).  The byte function is the text of
//   host_bridge_v11's rbyte for the classes Q C T U E N A, copied unchanged by the generator (gen_v12.py); the snapshots (cyc, qc, qb, busy/leader counts, hold,
//   the 40-bit slice count) are taken here on the same clock edges as the bridge took them (snap / lat are combinational from the bridge, gated by the block select).
//   rbyte is combinational from cmd and idx, so the timing of a reply byte is the same as in v11.   Needs: nothing else.
module blk_rd_v2 #(parameter S = 8) (
    input  wire        clk,
    input  wire [7:0]  cmd,
    input  wire [9:0]  idx,
    input  wire        snap,           // a C, U or T command arrives (this block selected)
    input  wire        lat,            // U, slice record: latch its whole 40-bit count with its first byte
    input  wire        hold,
    input  wire        f_init,
    input  wire [31:0] q_start, q_end, q_a0, q_arr,
    input  wire        q_trap,
    input  wire [1:0]  q_state,
    input  wire [5:0]  q_slot,
    input  wire [24:0] q_pred,
    input  wire [31:0] o_cyc, o_done, o_lerr, o_disp,
    input  wire [63:0] o_busy, o_blocked, o_tail, o_search,
    input  wire [S-1:0] o_busy_l,
    input  wire [32*S-1:0] st_sl,
    input  wire [15:0] st_qc, st_qb,
    input  wire [40*S-1:0] st_bs,
    input  wire [2:0]  q_cause,
    input  wire [15:0] q_taddr,
    input  wire        f_busy, f_done, f_ign,
    input  wire [2:0]  f_err,
    input  wire [31:0] f_moved, f_clocks,
    input  wire        s_busy, s_done,
    input  wire [3:0]  s_err,
    input  wire [15:0] s_steps,
    input  wire [31:0] s_tag, s_clk, s_cclk, s_wclk,
    input  wire [20:0] s_pc,
    input  wire [3:0]  s_op,
    output wire [7:0]  rbyte
);
    reg [31:0] cyc_s = 0;
    reg [39:0] cur_bs = 0;
    reg [15:0] snap_qc = 0, snap_qb = 0;
    reg [7:0]  snap_nb = 0, snap_nl = 0;
    reg        snap_hold = 0;
    integer    ni;
    reg [7:0]  nb_c, nl_c;
    always @(posedge clk) begin
        if (snap) begin
            cyc_s <= o_cyc; snap_qc <= st_qc; snap_qb <= st_qb; snap_hold <= hold;
            nb_c = 0; nl_c = 0;
            for (ni = 0; ni < S; ni = ni + 1) begin nb_c = nb_c + st_sl[ni*32]; nl_c = nl_c + st_sl[ni*32+1]; end
            snap_nb <= nb_c; snap_nl <= nl_c;
        end
        if (lat) cur_bs <= st_bs[40 * ((idx - 8) >> 3) +: 40];
    end
    function [7:0] rbyte_f(input [7:0] c, input [9:0] i, input [4095:0] dep);      // dep is not used inside: it only makes the call re-evaluate when any status signal changes (v2, ledger #1459)
        reg [63:0] w;
        begin
            w = 64'd0; rbyte_f = 8'd0;
            if (c == "Q") begin
                case (i[6:2])
                    0: w = q_start;  1: w = q_end;  2: w = q_a0;  3: w = q_arr;  4: w = {7'b0, q_pred};
                    default: w = 64'd0;
                endcase
                if (i < 20) rbyte_f = w >> (8 * i[1:0]);
                else if (i == 20) rbyte_f = {5'b0, q_state, q_trap};
                else rbyte_f = {2'b0, q_slot};
            end else if (c == "C") begin
                case (i[6:2])
                    0: rbyte_f = cyc_s >> (8 * i[1:0]);
                    1: rbyte_f = o_done >> (8 * i[1:0]);
                    2: rbyte_f = o_lerr >> (8 * i[1:0]);
                    3: rbyte_f = o_disp >> (8 * i[1:0]);
                    4,5:   rbyte_f = o_busy    >> (8 * (i - 16));
                    6,7:   rbyte_f = o_blocked >> (8 * (i - 24));
                    8,9:   rbyte_f = o_tail    >> (8 * (i - 32));
                    10,11: rbyte_f = o_search  >> (8 * (i - 40));
                    default: rbyte_f = ({{(64-S){1'b0}}, o_busy_l}) >> (8 * (i - 48));
                endcase
            end else if (c == "T") begin
                if (i < 8) begin
                    case (i[2:0])
                        0: rbyte_f = snap_qc[7:0]; 1: rbyte_f = snap_qc[15:8]; 2: rbyte_f = snap_qb[7:0]; 3: rbyte_f = snap_qb[15:8];
                        4: rbyte_f = snap_nb; 5: rbyte_f = snap_nl; 6: rbyte_f = {7'b0, snap_hold}; default: rbyte_f = 8'd0;
                    endcase
                end else rbyte_f = st_sl[8 * (i - 8) +: 8];
            end else if (c == "U") begin
                if (i < 8) rbyte_f = (i < 4) ? (cyc_s >> (8 * i[1:0])) : 8'd0;
                else if (i[2:0] == 0) rbyte_f = st_bs[40 * ((i - 8) >> 3) +: 8];
                else if (i[2:0] < 5)  rbyte_f = cur_bs >> (8 * i[2:0]);
                else rbyte_f = 8'd0;
            end else if (c == "E") begin
                if (i == 0) rbyte_f = {5'b0, q_cause};
                else rbyte_f = {16'b0, q_taddr} >> (8 * (i - 1));
            end else if (c == "N") begin
                case (i[3:0])
                    0: rbyte_f = {5'd0, f_ign, f_done, f_busy}; 1: rbyte_f = {5'd0, f_err}; 2: rbyte_f = {7'd0, f_init}; 3: rbyte_f = 8'd0;
                    4,5,6,7:     rbyte_f = f_moved  >> (8 * (i[1:0]));
                    default:     rbyte_f = f_clocks >> (8 * (i[1:0]));
                endcase
            end else if (c == "A") begin
                case (i[4:0])
                    0: rbyte_f = {6'd0, s_done, s_busy}; 1: rbyte_f = {4'd0, s_err}; 2: rbyte_f = s_steps[7:0]; 3: rbyte_f = s_steps[15:8];
                    4: rbyte_f = s_tag[7:0]; 5: rbyte_f = s_tag[15:8]; 6: rbyte_f = s_tag[23:16]; 7: rbyte_f = s_tag[31:24];
                    8: rbyte_f = s_clk[7:0]; 9: rbyte_f = s_clk[15:8]; 10: rbyte_f = s_clk[23:16]; 11: rbyte_f = s_clk[31:24];
                    12: rbyte_f = s_cclk[7:0]; 13: rbyte_f = s_cclk[15:8]; 14: rbyte_f = s_cclk[23:16]; 15: rbyte_f = s_cclk[31:24];
                    16: rbyte_f = s_wclk[7:0]; 17: rbyte_f = s_wclk[15:8]; 18: rbyte_f = s_wclk[23:16]; 19: rbyte_f = s_wclk[31:24];
                    20: rbyte_f = s_pc[7:0]; 21: rbyte_f = s_pc[15:8]; 22: rbyte_f = {3'd0, s_pc[20:16]}; default: rbyte_f = {4'd0, s_op};
                endcase
            end
        end
    endfunction
    assign rbyte = rbyte_f(cmd, idx, {q_start, q_end, q_a0, q_arr, q_trap, q_state, q_slot, q_pred, o_cyc, o_done, o_lerr, o_disp, o_busy, o_blocked, o_tail, o_search, o_busy_l, st_sl, st_qc, st_qb, st_bs, q_cause, q_taddr, f_busy, f_done, f_ign, f_err, f_moved, f_clocks, s_busy, s_done, s_err, s_steps, s_tag, s_clk, s_cclk, s_wclk, s_pc, s_op, hold, f_init, cyc_s, cur_bs, snap_qc, snap_qb, snap_nb, snap_nl, snap_hold});
endmodule
