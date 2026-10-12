// looped_cordic_stop_wrapper_v2.v -- ledger #1098 (v2 = v1 + `busy` output, from the grid's busy_any port added by tools/flex_busy_port_v1.py; v1 untouched). Closes the open-ring looped CORDIC (icm_open_flex_fz) and adds a self-stop built from the family's own cells:
//   step counter  = accumulator_cell_v4sa in pulse mode (step 1, threshold N): fires once when N results have been taken;
//   stop latch    = latch_cell_v4sa: set by that fire, cleared by the host (`release_pulse`); its data_out[0] is the level the host reads as "stopped, safe to read".
// Two ways to stop, selectable together: mode[0] BACK PRESSURE (the loop-closing register stops feeding the grid; the grid runs itself down to quiet),
//                                        mode[1] FREEZE (the stop level drives `freeze_all`, every grid cell holds where it is).
// The loop-closing register `cw/cv` takes each result and feeds it back after `feed_delay` clocks (age counter); it can also be loaded by the host (`load_*`), which is how the first value is injected.
// The trigger cells (accumulator, latch) are NOT frozen, so the host can always release.
`default_nettype none
`timescale 1ns / 1ps
module looped_cordic_stop_wrapper_v2 (
    input  wire clk, input  wire rst,
    input  wire cfg_grid,                    // one pulse after reset: arms the grid cells and the latch
    input  wire cfg_acc, input wire [15:0] n_steps,   // one pulse: (re)start the step counter with threshold n_steps
    input  wire [1:0] mode, input wire [2:0] feed_delay, input wire [4:0] trig_lag,   // trig_lag: clocks the step pulse is delayed before it reaches the counter (the stop then lands that much later)
    input  wire load_valid, input wire [31:0] load_data,
    input  wire release_pulse,
    output wire busy,                        // any non-constant grid cell still holds a word (0 = quiet: the closing register holds the whole state)
    output wire stopped,                     // the latch level
    output wire [15:0] steps_done,           // results taken so far (hardware counter)
    output wire [31:0] held_word, output wire held_valid,
    output wire take_o, output wire [31:0] take_data
);
    wire [31:0] o_d; wire o_v, o_a; wire [31:0] i_d; wire i_v, i_a;
    reg [31:0] cw = 0; reg cv = 0; reg [3:0] age = 0; reg [15:0] cnt = 0;
    wire fz = mode[1] & stopped;
    wire bp = mode[0] & stopped;
    assign o_a = ~cv & ~load_valid;
    wire take = o_v & o_a;
    assign take_o = take; assign take_data = o_d;
    assign i_d = cw;
    assign i_v = cv & (age >= {1'b0, feed_delay}) & ~bp;
    assign steps_done = cnt; assign held_word = cw; assign held_valid = cv;
    always @(posedge clk) begin
        if (rst) begin cv <= 0; cw <= 0; age <= 0; cnt <= 0; end
        else begin
            if (load_valid) begin cw <= load_data; cv <= 1; age <= 0; end
            else if (take) begin cw <= o_d; cv <= 1; age <= 0; cnt <= cnt + 1; end
            else if (cv && i_v && i_a) cv <= 0;
            else if (cv && age != 4'hF) age <= age + 1;
        end
    end
    icm_open_flex_fz grid (.freeze_all(fz), .busy_any(busy), .clk(clk), .rst(rst), .cfg_valid(cfg_grid),
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
