// looped_cordic_stop_wrapper_v3.v -- v3 = v2 + a SCAN port (in-flight capture / restore; v2 untouched). Differences from v2:
//   scan_hold: freeze the grid and make the wrapper ignore it (no results taken, nothing fed) while the host loads the closing register and prepares a restore; scan_en implies it.
//   scan_en  : while high the whole grid is frozen (freeze_all forced), the wrapper ignores grid results and does not feed the grid, and the grid's scan chain shifts one bit per clock
//              (scan_in -> chain -> scan_out). Recirculating (scan_in = scan_out for N clocks) reads the state without changing it; shifting a saved stream in restores it.
//   load_has : with load_valid, says whether the loop-closing register holds a word after the load (1 = as v2; 0 = empty, the word is inside the grid).
//   The grid is icm_open_flex_fz_scan (tools/flex_scan_net_v1.py). Constant cells are not in the chain (they have no dynamic state to carry; checked by the A/B simulation).
`default_nettype none
`timescale 1ns / 1ps
module looped_cordic_stop_wrapper_v3 (
    input  wire clk, input  wire rst,
    input  wire cfg_grid,                    // one pulse after reset: arms the grid cells and the latch
    input  wire cfg_acc, input wire [15:0] n_steps,   // one pulse: (re)start the step counter with threshold n_steps
    input  wire [1:0] mode, input wire [2:0] feed_delay, input wire [4:0] trig_lag,   // trig_lag: clocks the step pulse is delayed before it reaches the counter (the stop then lands that much later)
    input  wire load_valid, input wire load_has, input wire [31:0] load_data,
    input  wire scan_hold, input wire scan_en, input wire scan_in, output wire scan_out,
    input  wire release_pulse,
    output wire busy,                        // any non-constant grid cell still holds a word (0 = quiet: the closing register holds the whole state)
    output wire stopped,                     // the latch level
    output wire [15:0] steps_done,           // results taken so far (hardware counter)
    output wire [31:0] held_word, output wire held_valid,
    output wire take_o, output wire [31:0] take_data
);
    wire [31:0] o_d; wire o_v, o_a; wire [31:0] i_d; wire i_v, i_a;
    reg [31:0] cw = 0; reg cv = 0; reg [3:0] age = 0; reg [15:0] cnt = 0;
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
    icm_open_flex_fz_scan grid (.scan_en(scan_en), .scan_in(scan_in), .scan_out(scan_out), .freeze_all(fz), .busy_any(busy), .clk(clk), .rst(rst), .cfg_valid(cfg_grid),
        .in_z_input_data(i_d), .in_z_input_valid(i_v), .in_z_input_ack(i_a),
        .out_result_data(o_d), .out_result_valid(o_v), .out_result_ack(o_a));
    // the self-stop, from the family's own cells
    reg [31:0] lagsr = 0; always @(posedge clk) lagsr <= {lagsr[30:0], take};
    wire inc = (trig_lag == 0) ? take : lagsr[trig_lag - 1];
    wire acc_v, acc_ack_in, lat_ack, lat_v; wire [31:0] acc_d, lat_d;
    wire set_ev = acc_v & lat_ack;
    assign acc_ack_in = lat_ack;
    accumulator_cell_v4sa #(.CELL_ID(16'd900)) u_cnt (.clk(clk), .rst(rst), .freeze_in(1'b0), .cfg_valid(cfg_acc), .cfg_data({7'b0, n_steps, 1'b1, 8'd1}),
        .inc_pulse(inc), .dec_pulse(1'b0), .ack_out(), .data_out(acc_d), .valid_out(acc_v), .ack_in(acc_ack_in));
    latch_cell_v4sa #(.CELL_ID(16'd901)) u_stop (.clk(clk), .rst(rst), .freeze_in(1'b0), .cfg_valid(cfg_grid), .cfg_data(32'b0),
        .set_in(set_ev), .clear_in(release_pulse), .toggle_in(1'b0), .ack_out(lat_ack), .data_out(lat_d), .valid_out(lat_v), .ack_in(1'b1));
    assign stopped = lat_d[0];
endmodule
