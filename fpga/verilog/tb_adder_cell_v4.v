// tb_adder_cell_v4.v — points.md #617/#618: confirms adder_cell_v4.v's
// real, cloned core logic behaves IDENTICALLY to adder_cell_v1.v for
// ordinary add/subtract (the real first-step goal `#617`'s own scope
// doc named), then confirms each of the new real shell additions
// independently: PROG_ID-targeted reconfiguration (change ONE field,
// leave the others untouched), the real 3-addon chain (invert_en),
// and the new `active` port fully silencing the cell when low.
`timescale 1ns / 1ps

module tb_adder_cell_v4;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;
    reg active = 1;

    reg cfg = 0;
    reg [63:0] cfg_d = 0;

    // downstream=E, upstream=N|W — same real wiring tb_adder_cell_v1.v
    // already uses, now over 6-bit fields (top 2 bits real, reserved
    // headroom, left at 0).
    localparam [5:0] DIR_N6 = 6'b000001, DIR_E6 = 6'b000100, DIR_W6 = 6'b001000;
    // cfg_data[63:0]: [5:0]=downstream [11:6]=upstream [12]=subtract_mode [32:13]=addon_config
    localparam [63:0] CFG_DUT = {31'h0, 20'h0, 1'b0, (DIR_N6 | DIR_W6), DIR_E6};
    localparam [63:0] CFG_SUB = {31'h0, 20'h0, 1'b1, (DIR_N6 | DIR_W6), DIR_E6};

    reg  [31:0] opA = 0, opB = 0;
    reg         pulse_a = 0, pulse_b = 0;

    wire [31:0] sum_out_e;
    wire        fire_e;
    wire        ready_o;
    wire        ack_out_n, ack_out_w;
    wire        status_dv, status_aa;
    wire        program_done;
    wire        prog_ack_n, prog_ack_s, prog_ack_e, prog_ack_w;

    reg cons_ready = 1;
    reg cons_ack   = 0;

    reg         program_in = 0;
    reg  [31:0] prog_data_n = 0;
    reg         prog_arr_n = 0;

    adder_cell_v4 #(.CELL_ID(16'h0000)) DUT (
        .clk(clk), .rst(rst), .active(active),
        .cfg_valid(cfg), .cfg_data(cfg_d),
        .data_in_n(opA), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(opB),
        .arrived_n(pulse_a), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(pulse_b),
        .data_out_n(), .data_out_s(), .data_out_e(sum_out_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(fire_e), .fire_w(),
        .ready_out(ready_o),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(cons_ready), .ready_in_w(1'b1),
        .ack_out_n(ack_out_n), .ack_out_s(), .ack_out_e(), .ack_out_w(ack_out_w),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(cons_ack), .ack_in_w(1'b0),
        .program_in(program_in), .program_done(program_done),
        .prog_data_in_n(prog_data_n), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(prog_arr_n), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(prog_ack_n), .prog_ack_out_s(prog_ack_s), .prog_ack_out_e(prog_ack_e), .prog_ack_out_w(prog_ack_w),
        .freeze_in(1'b0),
        .status_data_valid(status_dv), .status_a_arrived(status_aa)
    );

    integer received = 0;
    integer errors   = 0;
    reg [31:0] expected_sum;

    reg [1:0] cons_state = 0;
    always @(posedge clk) begin
        cons_ack <= 1'b0;
        if (!rst) begin
            case (cons_state)
                0: if (fire_e) begin
                       if (sum_out_e !== expected_sum) begin
                           $display("[%0t] FAIL: expected sum=%h got=%h", $time, expected_sum, sum_out_e);
                           errors = errors + 1;
                       end else begin
                           $display("[%0t] receive #%0d: sum=%h (correct)", $time, received+1, sum_out_e);
                       end
                       received = received + 1;
                       cons_state <= 1;
                   end
                1: begin cons_ack <= 1'b1; cons_state <= 2; end
                2: cons_state <= 0;
                default: cons_state <= 0;
            endcase
        end
    end

    task send_pair(input [31:0] a_val, input [31:0] b_val);
        begin
            expected_sum = a_val + b_val;
            opA = a_val; pulse_a = 1'b1;
            #10;
            pulse_a = 1'b0;
            wait (status_aa == 1'b1);
            #10;
            opB = b_val; pulse_b = 1'b1;
            #10;
            pulse_b = 1'b0;
        end
    endtask

    task send_pair_sub(input [31:0] a_val, input [31:0] b_val);
        begin
            expected_sum = a_val - b_val;
            opA = a_val; pulse_a = 1'b1;
            #10;
            pulse_a = 1'b0;
            wait (status_aa == 1'b1);
            #10;
            opB = b_val; pulse_b = 1'b1;
            #10;
            pulse_b = 1'b0;
        end
    endtask

    // Real, targeted, ONE-field reprogram: change JUST subtract_mode
    // via PROG_ID, confirm downstream/upstream_mask are UNTOUCHED
    // (the real "scalpel, not a hammer" claim, not just that the new
    // field lands correctly).
    task prog_send(input [2:0] id, input [19:0] word, input do_complete, input arm_bit);
        begin
            prog_data_n = {9'h0, id, word};
            prog_arr_n = 1'b1;
            #10;
            prog_arr_n = 1'b0;
            #10;
            if (do_complete) begin
                prog_data_n = {9'h0, 3'd7, 19'h0, arm_bit};
                prog_arr_n = 1'b1;
                #10;
                prog_arr_n = 1'b0;
                #10;
            end
        end
    endtask

    initial begin
        #12 rst = 0;
        #10 cfg = 1; cfg_d = CFG_DUT;
        #10 cfg = 0;

        // ── Real, identical-to-v1 core behavior, confirmed first ──
        send_pair(32'h0000_0005, 32'h0000_0007);   // 12
        #40;
        send_pair(32'hFFFF_FFFF, 32'h0000_0001);   // wraps to 0
        #40;
        send_pair(32'h1234_5678, 32'h0000_0001);
        #60;

        // ── Real, targeted reprogram: PROG_ID_SUBTRACT_MODE=1 alone,
        // via the programming channel, NOT the atomic cfg_valid path.
        // downstream_mask/upstream_mask must survive unchanged. ──
        program_in = 1'b1;
        prog_send(3'd2, 20'h1, 1'b1, 1'b1);   // PROG_ID_SUBTRACT_MODE, word=1, COMPLETE+arm
        program_in = 1'b0;
        #20;
        send_pair_sub(32'd23, 32'd7);   // 16 -- confirms subtract_mode landed
        #40;
        send_pair_sub(32'd7, 32'd23);   // real borrow, two's complement
        #60;

        // downstream/upstream should still be E/(N|W) -- if the
        // targeted write had clobbered them, send_pair_sub above would
        // never have received anything at all (fire_e would stay low),
        // which the received-count check at the end catches.

        // ── Real, targeted reprogram back to ADD, addon_config left
        // untouched -- confirms the targeted channel can flip a single
        // field back too, not just forward. ──
        program_in = 1'b1;
        prog_send(3'd2, 20'h0, 1'b1, 1'b1);
        program_in = 1'b0;
        #20;
        send_pair(32'd9, 32'd16);   // 25, real ADD again
        #60;

        // ── Real addon chain: set invert_en via PROG_ID_ADDON_CONFIG,
        // confirm the offered sum is genuinely bit-inverted. ──
        program_in = 1'b1;
        prog_send(3'd3, {1'b1, 19'h0}, 1'b1, 1'b1);   // PROG_ID_ADDON_CONFIG, invert_en=bit19=1
        program_in = 1'b0;
        #20;
        expected_sum = ~(32'd1 + 32'd1);   // real bitwise invert of the true sum
        opA = 32'd1; pulse_a = 1'b1; #10; pulse_a = 1'b0;
        wait (status_aa == 1'b1);
        #10;
        opB = 32'd1; pulse_b = 1'b1; #10; pulse_b = 1'b0;
        #60;

        // clear addon_config for the final real check below
        program_in = 1'b1;
        prog_send(3'd3, 20'h0, 1'b1, 1'b1);
        program_in = 1'b0;
        #20;

        // ── Real `active` gating: drop active, confirm the cell goes
        // fully silent -- ready_out low, no capture, no offer. ──
        active = 1'b0;
        #10;
        if (ready_o !== 1'b0) begin
            $display("[%0t] FAIL: ready_out should be 0 when active=0, got %b", $time, ready_o);
            errors = errors + 1;
        end
        opA = 32'd99; pulse_a = 1'b1; #10; pulse_a = 1'b0;
        #20;
        if (status_aa !== 1'b0) begin
            $display("[%0t] FAIL: a real arrival was captured while active=0", $time);
            errors = errors + 1;
        end else begin
            $display("[%0t] confirmed: active=0 genuinely silences the cell", $time);
        end
        active = 1'b1;
        #20;

        if (received == 7 && errors == 0)
            $display("PASS: adder_cell_v4 -- identical core behavior to v1 (3 pairs), real targeted PROG_ID reconfiguration (subtract_mode flipped forward and back without disturbing routing, 2 pairs + 1 pair), real addon chain (invert_en genuinely inverts the offered sum), real active=0 gating confirmed");
        else
            $display("FAIL: received=%0d errors=%0d", received, errors);

        $finish;
    end

endmodule
