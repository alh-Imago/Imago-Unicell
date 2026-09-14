// tb_mul_cell_v4.v — points.md #724: the first real testbench for the
// 10th unified-carrier core. Confirms real core behavior (multiply,
// including the real low-32-bit truncation LLVM's own `mul` uses),
// real targeted PROG_ID reconfiguration, the real addon chain
// (invert_en), and real active=0 gating -- matching the exact
// coverage shape every other _v4 core's own testbench already has.
`timescale 1ns / 1ps

module tb_mul_cell_v4;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;
    reg active = 1;

    reg cfg = 0;
    reg [63:0] cfg_d = 0;

    localparam [5:0] DIR_N6 = 6'b000001, DIR_E6 = 6'b000100, DIR_W6 = 6'b001000;
    // cfg_data[63:0]: [5:0]down [11:6]up [12]reserved [32:13]addon_config [63:33]reserved
    localparam [63:0] CFG_DUT = {31'h0, 20'h0, (DIR_N6 | DIR_W6), DIR_E6};

    reg  [31:0] opA = 0, opB = 0;
    reg         pulse_a = 0, pulse_b = 0;

    wire [31:0] product_out_e;
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

    mul_cell_v4 #(.CELL_ID(16'h000A)) DUT (
        .clk(clk), .rst(rst), .active(active),
        .cfg_valid(cfg), .cfg_data(cfg_d),
        .data_in_n(opA), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(opB),
        .arrived_n(pulse_a), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(pulse_b),
        .data_out_n(), .data_out_s(), .data_out_e(product_out_e), .data_out_w(),
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
    reg [31:0] expected_product;

    reg [1:0] cons_state = 0;
    always @(posedge clk) begin
        cons_ack <= 1'b0;
        if (!rst) begin
            case (cons_state)
                0: if (fire_e) begin
                       if (product_out_e !== expected_product) begin
                           $display("[%0t] FAIL: expected product=%h got=%h", $time, expected_product, product_out_e);
                           errors = errors + 1;
                       end else begin
                           $display("[%0t] receive #%0d: product=%h (correct)", $time, received+1, product_out_e);
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
            expected_product = (a_val * b_val);   // Verilog's own 32x32 multiply, real reference, low 32 kept by the assignment width
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

        // ── Real core behavior, confirmed first, including the real
        // low-32-bit truncation LLVM's own `mul` uses. ──
        send_pair(32'd5, 32'd7);              // 35, no overflow
        #40;
        send_pair(32'hFFFFFFFF, 32'd2);       // -1 * 2 = -2 (0xFFFFFFFE), real wraparound
        #40;
        send_pair(32'h10000, 32'h10000);      // 0x100000000 truncates to 0 -- real overflow case
        #60;

        // ── Real, targeted reprogram: PROG_ID_UPSTREAM_MASK, confirms
        // it reaches the real programming channel correctly. ──
        program_in = 1'b1;
        prog_send(3'd1, {14'h0, DIR_N6}, 1'b1, 1'b1);   // swap upstream to N only
        program_in = 1'b0;
        #20;
        opA = 32'd0; opB = 32'd0;   // clear west's own stale operand role
        expected_product = 32'd6 * 32'd7;
        opA = 32'd6; pulse_a = 1'b1; #10; pulse_a = 1'b0;
        wait (status_aa == 1'b1);
        #10;
        opA = 32'd7; pulse_a = 1'b1; #10; pulse_a = 1'b0;   // second operand now via N too
        #60;

        // ── Real addon chain: invert_en ──
        program_in = 1'b1;
        prog_send(3'd3, {1'b1, 19'h0}, 1'b1, 1'b1);   // PROG_ID_ADDON_CONFIG, invert_en=bit19=1
        program_in = 1'b0;
        #20;
        expected_product = ~(32'd3 * 32'd4);
        opA = 32'd3; pulse_a = 1'b1; #10; pulse_a = 1'b0;
        wait (status_aa == 1'b1);
        #10;
        opA = 32'd4; pulse_a = 1'b1; #10; pulse_a = 1'b0;
        #60;

        // clear addon_config for the final real check
        program_in = 1'b1;
        prog_send(3'd3, 20'h0, 1'b1, 1'b1);
        program_in = 1'b0;
        #20;

        // ── Real `active` gating: drop active, confirm the cell goes
        // fully silent. ──
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

        if (received == 5 && errors == 0)
            $display("PASS: mul_cell_v4 -- real multiply including low-32-bit truncation (3 pairs), real targeted PROG_ID reconfiguration of upstream_mask (1 pair), real addon chain (invert_en, 1 pair), real active=0 gating confirmed");
        else
            $display("FAIL: received=%0d errors=%0d", received, errors);

        $finish;
    end

endmodule
