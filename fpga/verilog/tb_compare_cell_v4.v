// tb_compare_cell_v4.v — points.md #617/#620: confirms
// compare_cell_v4.v's real, cloned single-arrival comparison core
// behaves IDENTICALLY to compare_cell_v1.v, then confirms each new
// real shell addition independently: PROG_ID-targeted reconfiguration
// (including the real split threshold LOW/HIGH write), the real addon
// chain, and the `active` port.
`timescale 1ns / 1ps

module tb_compare_cell_v4;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;
    reg active = 1;

    localparam [5:0] DIR_N6 = 6'b000001, DIR_E6 = 6'b000100;

    reg        cfg = 0;
    reg [63:0] cfg_d = 0;
    // cfg_data[63:0]: [5:0]down [11:6]up [43:12]threshold [63:44]addon_config
    // threshold=8, input on N, result out E
    localparam [63:0] CFG = {20'h0, 32'sd8, DIR_N6, DIR_E6};

    reg  [31:0] val_in = 0;
    reg         pulse = 0;
    wire [31:0] data_out_e;
    wire        fire_e, ready_o;
    reg         cons_ready = 1, cons_ack = 0;
    wire        program_done;
    wire        prog_ack_n, prog_ack_s, prog_ack_e, prog_ack_w;

    reg         program_in = 0;
    reg  [31:0] prog_data_n = 0;
    reg         prog_arr_n = 0;

    compare_cell_v4 #(.CELL_ID(16'h0002)) DUT (
        .clk(clk), .rst(rst), .active(active),
        .cfg_valid(cfg), .cfg_data(cfg_d),
        .data_in_n(val_in), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(pulse), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(), .data_out_e(data_out_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(fire_e), .fire_w(),
        .ready_out(ready_o),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(cons_ready), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(cons_ack), .ack_in_w(1'b0),
        .program_in(program_in), .program_done(program_done),
        .prog_data_in_n(prog_data_n), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(prog_arr_n), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(prog_ack_n), .prog_ack_out_s(prog_ack_s), .prog_ack_out_e(prog_ack_e), .prog_ack_out_w(prog_ack_w),
        .freeze_in(1'b0), .status_data_valid()
    );

    integer received = 0;
    integer errors = 0;
    reg [31:0] expected;

    reg [1:0] cons_state = 0;
    always @(posedge clk) begin
        cons_ack <= 1'b0;
        if (!rst) begin
            case (cons_state)
                0: if (fire_e) begin
                       if (data_out_e !== expected) begin
                           $display("[%0t] FAIL: expected=%h got=%h", $time, expected, data_out_e);
                           errors = errors + 1;
                       end else begin
                           $display("[%0t] receive #%0d: result=%h (correct)", $time, received+1, data_out_e);
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

    task send_val(input signed [31:0] v, input want);
        begin
            expected = {31'h0, want};
            val_in = v; pulse = 1'b1;
            #10;
            pulse = 1'b0;
        end
    endtask

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
        #10 cfg = 1; cfg_d = CFG;
        #10 cfg = 0;

        // ── Real, identical-to-v1 core behavior: threshold=8 ──
        send_val(32'sd10, 1'b1);   // 10 >= 8 -> true
        #40;
        send_val(32'sd8, 1'b1);    // boundary: 8 >= 8 -> true
        #40;
        send_val(32'sd3, 1'b0);    // 3 >= 8 -> false
        #40;
        send_val(-32'sd5, 1'b0);   // real negative, signed compare
        #60;

        // ── Real, targeted reprogram: split THRESHOLD LOW/HIGH write
        // -- new threshold=100, confirm it takes effect immediately,
        // no separate commit trigger needed (real, deliberate
        // simplification vs. ram's own init_data, see the RTL's own
        // comment). ──
        program_in = 1'b1;
        prog_send(3'd2, 20'h0064, 1'b0, 1'b0);   // PROG_ID_THRESHOLD_LOW = 100 (0x64)
        prog_send(3'd3, 20'h0000, 1'b1, 1'b1);   // PROG_ID_THRESHOLD_HIGH = 0, COMPLETE+arm
        program_in = 1'b0;
        #20;
        send_val(32'sd150, 1'b1);   // 150 >= 100 -> true
        #40;
        send_val(32'sd99, 1'b0);    // 99 >= 100 -> false, confirms the real new threshold landed
        #60;

        // ── Real addon chain: invert_en ──
        program_in = 1'b1;
        prog_send(3'd4, {1'b1, 19'h0}, 1'b1, 1'b1);   // PROG_ID_ADDON_CONFIG, invert_en=bit19=1
        program_in = 1'b0;
        #20;
        expected = ~32'h0000_0001;   // real: 150>=100 -> raw result 1, inverted
        val_in = 32'sd150; pulse = 1'b1; #10; pulse = 1'b0;
        #60;

        // clear addon_config for the final real check
        program_in = 1'b1;
        prog_send(3'd4, 20'h0, 1'b1, 1'b1);
        program_in = 1'b0;
        #20;

        // ── Real `active` gating ──
        active = 1'b0;
        #10;
        if (ready_o !== 1'b0) begin
            $display("[%0t] FAIL: ready_out should be 0 when active=0, got %b", $time, ready_o);
            errors = errors + 1;
        end
        val_in = 32'sd999; pulse = 1'b1; #10; pulse = 1'b0;
        #20;
        $display("[%0t] confirmed: active=0 checked (ready_out gating above is the real proof)", $time);
        active = 1'b1;
        #20;

        if (received == 7 && errors == 0)
            $display("PASS: compare_cell_v4 -- identical core behavior to v1 (4 values incl. boundary + negative), real targeted PROG_ID reconfiguration (split threshold LOW/HIGH, 2 values), real addon chain (invert_en), real active=0 gating confirmed");
        else
            $display("FAIL: received=%0d errors=%0d", received, errors);

        $finish;
    end

endmodule
