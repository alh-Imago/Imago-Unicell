// looped_cordic_pure_wrapper_v1.v -- ledger #1147. The USUAL-FPGA way of the same job as sub/verilog/looped_cordic_stop_wrapper_v3.v: plain Verilog, no cells.
// Same ports as that wrapper, so the same serial controller (tools/board_scan_v1.py) drives it. Core = fpga/baselines/cordic_z_v1/cordic_z_hs_frz_v2.v (v1 plus a busy output: four CORDIC steps with a valid/ack handshake,
// a freeze input and a 132-bit scan chain) plus the loop's drift added on the output (combinational, as the grid's drift adder is part of its loop). Closing register: same logic as the cell wrapper.
// Step counter and stop latch are plain registers (a counter with a threshold, and a set/clear flop). scan_hold / scan_en freeze the core and make the wrapper ignore it, exactly as in the cell wrapper.
`default_nettype none
`timescale 1ns / 1ps
module looped_cordic_pure_wrapper_v1 (
    input  wire clk, input  wire rst,
    input  wire cfg_grid,
    input  wire cfg_acc, input wire [15:0] n_steps,
    input  wire [1:0] mode, input wire [2:0] feed_delay, input wire [4:0] trig_lag,
    input  wire load_valid, input wire load_has, input wire [31:0] load_data,
    input  wire scan_hold, input wire scan_en, input wire scan_in, output wire scan_out,
    input  wire release_pulse,
    output wire busy, output wire stopped, output wire [15:0] steps_done,
    output wire [31:0] held_word, output wire held_valid,
    output wire take_o, output wire [31:0] take_data
);
    localparam signed [31:0] DRIFT = 32'sd1237;
    wire [31:0] c_d; wire o_v, o_a; wire [31:0] i_d; wire i_v, i_a;
    wire [31:0] o_d = c_d + DRIFT;
    reg [31:0] cw = 0; reg cv = 0; reg [3:0] age = 0; reg [15:0] cnt = 0;
    reg stop_r = 0; reg armed = 0; reg [15:0] acnt = 0, thr = 0;
    assign stopped = stop_r;
    wire gate = scan_en | scan_hold;
    wire fz = (mode[1] & stopped) | gate;
    wire bp = mode[0] & stopped;
    assign o_a = ~cv & ~load_valid & ~gate;
    wire take = o_v & o_a;
    assign take_o = take; assign take_data = o_d;
    assign i_d = cw;
    assign i_v = cv & (age >= {1'b0, feed_delay}) & ~bp & ~gate;
    assign steps_done = cnt; assign held_word = cw; assign held_valid = cv;
    always @(posedge clk) begin
        if (rst) begin cv <= 0; cw <= 0; age <= 0; cnt <= 0; end
        else begin
            if (load_valid) begin cw <= load_data; cv <= load_has; age <= 0; end
            else if (take) begin cw <= o_d; cv <= 1; age <= 0; cnt <= cnt + 1; end
            else if (cv && i_v && i_a) cv <= 0;
            else if (cv && age != 4'hF) age <= age + 1;
        end
    end
    cordic_z_hs_frz_v2 core (.clk(clk), .rst(rst), .freeze(fz), .scan_en(scan_en), .scan_in(scan_in), .scan_out(scan_out),
        .in_data(i_d), .in_valid(i_v), .in_ack(i_a), .out_data(c_d), .out_valid(o_v), .busy(busy), .out_ack(o_a));
    // self-stop: the take pulse (delayed by trig_lag) counts; at n_steps the latch is set; the host clears it with release_pulse
    reg [31:0] lagsr = 0; always @(posedge clk) lagsr <= {lagsr[30:0], take};
    wire inc = (trig_lag == 0) ? take : lagsr[trig_lag - 1];
    always @(posedge clk) begin
        if (rst || cfg_grid) begin stop_r <= 0; if (rst) begin armed <= 0; acnt <= 0; end end
        else begin
            if (release_pulse) stop_r <= 0;
            if (cfg_acc) begin armed <= 1; acnt <= 0; thr <= n_steps; end
            else if (armed && inc) begin
                acnt <= acnt + 1;
                if (acnt + 16'd1 == thr) begin armed <= 0; stop_r <= 1; end
            end
        end
    end
endmodule
