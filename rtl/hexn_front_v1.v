`default_nettype none
// hexn_front_v1.v -- SIMULATION TOP for the interface test: K counted detectors (hexn_det_v3, weights and thresholds given directly) -> glue buffer (hexn_glue_v1) -> ONE full cell (hexn_cell_v2), with the run controller of five windows of PL clocks:
//   w0 detectors accumulate (ph_start at its first clock; glue cleared there) | w1 detectors send their bursts, the glue captures them | w2 the cell's forward phase, the glue replays the captured bursts into lanes 0..K-1 of the cell
//   w3 the cell's feedback phase (win_end at its last clock) | w4 the cell's forward phase again: its output burst on lane OUTL is counted (cell_cnt). done pulses at the end of w4.
// The cell's lane settings come from lane_cfg (2 bits per detector lane: 0 off, 1 positive, 2 negative) and cell_thr; the output lane OUTL is a sender with code 1 ("pass when the threshold is reached"). Detector rx is the same sample for all detectors.
module hexn_front_v1 #(parameter K = 19, NB = 18, AW = 7, PL = 10, OUTL = 20) (
    input  wire clk, input wire rst, input wire start, output reg busy, output reg done,
    input  wire [NB-1:0] s_bits, input wire [K*NB-1:0] w_pos, input wire [K*NB-1:0] w_neg, input wire [K*AW-1:0] thr_flat,
    input  wire [2*K-1:0] lane_cfg, input wire [AW-1:0] cell_thr,
    output reg [4:0] cell_cnt, output wire [3*K-1:0] cap_flat, output wire [K-1:0] det_tx, output wire [K-1:0] glue_out, output wire [AW-1:0] cell_fwd
);
    reg [3:0] t; reg [2:0] w;
    wire act = busy; wire t0 = act & (t == 0); wire tl = act & (t == PL - 1);
    always @(posedge clk) begin
        done <= 0;
        if (rst) begin busy <= 0; t <= 0; w <= 0; end
        else if (start && !busy) begin busy <= 1; t <= 0; w <= 0; end
        else if (busy) begin
            if (t == PL - 1) begin t <= 0; w <= w + 1'b1; if (w == 4) begin busy <= 0; done <= 1; end end else t <= t + 1'b1;
        end
    end
    wire det_ph = t0 & (w == 0 | w == 1);
    wire clr = start & !busy;
    wire cap_en = act & (w == 1);
    wire play = t0 & (w == 2);
    wire cph = (w == 3);                      // cell phase: 1 = feedback
    wire cph_start = t0 & (w == 2 | w == 4);
    wire cwin_end = tl & (w == 3);
    genvar g;
    generate for (g = 0; g < K; g = g + 1) begin : D
        hexn_det_v3 #(.NB(NB), .AW(AW)) det(.clk(clk), .rst(rst), .ph_start(det_ph), .rx(s_bits), .w_pos(w_pos[g*NB +: NB]), .w_neg(w_neg[g*NB +: NB]), .cfg_thr(thr_flat[g*AW +: AW]), .tx(det_tx[g]));
    end endgenerate
    hexn_glue_v1 #(.K(K)) glue(.clk(clk), .rst(rst), .clr(clr), .cap_en(cap_en), .play(play), .tx(det_tx), .out(glue_out), .cap_flat(cap_flat));
    reg [23:0] rx, act_l; reg [47:0] dirv, codev;
    integer i;
    always @* begin
        rx = 0; act_l = 0; dirv = 0; codev = 0;
        for (i = 0; i < K; i = i + 1) begin
            rx[i] = glue_out[i]; act_l[i] = (lane_cfg[2*i +: 2] != 0);
            codev[2*i +: 2] = (lane_cfg[2*i +: 2] == 2) ? 2'd3 : 2'd0;
        end
        act_l[OUTL] = 1'b1; dirv[2*OUTL +: 2] = 2'd1; codev[2*OUTL +: 2] = 2'd1;
    end
    wire [23:0] ctx;
    hexn_cell_v2 #(.FACES(6), .PAIRS(4), .AW(AW)) fcell(.clk(clk), .rst(rst), .phase(cph), .ph_start(cph_start), .win_end(cwin_end), .rx(rx), .tx(ctx), .cfg_active(act_l), .cfg_dir(dirv), .cfg_code(codev), .cfg_thr(cell_thr), .bias(16'd0));
    reg [AW-1:0] fwd_l; always @(posedge clk) if (cwin_end) fwd_l <= fcell.fwd_acc;
    assign cell_fwd = fwd_l;
    always @(posedge clk) begin
        if (rst || (start && !busy)) cell_cnt <= 0;
        else if (busy && w == 4 && ctx[OUTL]) cell_cnt <= cell_cnt + 1'b1;
    end
endmodule
`default_nettype wire
