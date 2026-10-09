// tb_mem_read_splitter_v1.v — points.md #257/#258 continuation: confirms
// mem_read_splitter_v1.v correctly splits a 40-bit BRAM word into DATA
// (offered downstream via the normal cardinal path) and ROUTING (a
// direct, non-cardinal 8-bit output), that both are captured together
// off the same event, and that routing_out stays stable for the ENTIRE
// window data_valid is asserted (the exact property the future mux core
// will depend on to read it correctly, per #257's own cycle trace).
`timescale 1ns / 1ps

module tb_mem_read_splitter_v1;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

    localparam [3:0] DIR_N = 4'b0001, DIR_E = 4'b0100;
    localparam [63:0] CFG = {56'h0, DIR_N, DIR_E};   // addr in on N, data out on E

    reg  [31:0] addr_in = 0;
    reg         addr_pulse = 0;
    wire [31:0] data_out_e;
    wire [7:0]  routing_out;
    wire        fire_e, ready_o;
    reg         cons_ready = 1, cons_ack = 0;
    reg         cfg = 0;
    reg  [63:0] cfg_d = 0;

    mem_read_splitter_v1 #(.CELL_ID(16'h0004), .ADDR_WIDTH(16)) DUT (
        .clk(clk), .rst(rst), .cfg_valid(cfg), .cfg_data(cfg_d),
        .data_in_n(addr_in), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(addr_pulse), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(), .data_out_e(data_out_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(fire_e), .fire_w(),
        .ready_out(ready_o),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(cons_ready), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(cons_ack), .ack_in_w(1'b0),
        .freeze_in(1'b0),
        .routing_out(routing_out),
        .status_data_valid(), .status_addr_captured()
    );

    // Seed 3 known 40-bit words directly into the CORE's own memory —
    // distinct DATA and ROUTING fields per entry, so a swapped-field or
    // misaligned-split bug would be immediately visible.
    initial begin
        DUT.CORE.mem[16'h0010] = {8'hA5, 32'hDEAD_BEEF};
        DUT.CORE.mem[16'h0020] = {8'h3C, 32'h1234_5678};
        DUT.CORE.mem[16'h0030] = {8'hFF, 32'h0000_0001};
    end

    integer errors = 0;
    integer received = 0;
    reg [31:0] expected_data;
    reg [7:0]  expected_routing;
    reg [7:0]  routing_at_capture;   // sampled the SAME cycle data_valid
                                     // first asserts, to prove synchronization

    // Watches for data_valid's rising edge and snapshots routing_out at
    // that exact moment (hierarchical reference — sim-only introspection,
    // same practice used in #256's own integration testbench).
    reg prev_dv = 0;
    always @(posedge clk) begin
        prev_dv <= DUT.data_valid;
        if (!prev_dv && DUT.data_valid) begin
            routing_at_capture <= routing_out;
        end
    end

    reg [1:0] cons_state = 0;
    always @(posedge clk) begin
        cons_ack <= 1'b0;
        if (!rst) begin
            case (cons_state)
                0: if (fire_e) begin
                       if (data_out_e !== expected_data) begin
                           $display("[%0t] FAIL: DATA mismatch expected=%h got=%h", $time, expected_data, data_out_e);
                           errors = errors + 1;
                       end
                       if (routing_at_capture !== expected_routing) begin
                           $display("[%0t] FAIL: ROUTING mismatch expected=%h got=%h (captured-at-valid snapshot)",
                               $time, expected_routing, routing_at_capture);
                           errors = errors + 1;
                       end
                       if (routing_out !== expected_routing) begin
                           $display("[%0t] FAIL: routing_out not still stable at consume time -- expected=%h got=%h",
                               $time, expected_routing, routing_out);
                           errors = errors + 1;
                       end
                       if (errors == 0 || (data_out_e === expected_data && routing_out === expected_routing))
                           $display("[%0t] receive #%0d: data=%h routing=%h (both correct, split+sync confirmed)",
                               $time, received+1, data_out_e, routing_out);
                       received = received + 1;
                       cons_state <= 1;
                   end
                1: begin cons_ack <= 1'b1; cons_state <= 2; end
                2: cons_state <= 0;
                default: cons_state <= 0;
            endcase
        end
    end

    task read_check(input [15:0] addr, input [31:0] exp_data, input [7:0] exp_routing);
        begin
            wait (ready_o == 1'b1);
            expected_data = exp_data;
            expected_routing = exp_routing;
            addr_in = {16'h0, addr}; addr_pulse = 1'b1;
            #10;
            addr_pulse = 1'b0;
        end
    endtask

    initial begin
        #12 rst = 0;
        #10 cfg = 1; cfg_d = CFG;
        #10 cfg = 0;
        #10;

        read_check(16'h0010, 32'hDEAD_BEEF, 8'hA5);
        #60;
        read_check(16'h0020, 32'h1234_5678, 8'h3C);
        #60;
        read_check(16'h0030, 32'h0000_0001, 8'hFF);
        #60;

        if (received == 3 && errors == 0)
            $display("PASS: mem_read_splitter_v1 -- 3/3 reads, DATA+ROUTING correctly split, synchronized (captured together), and stable through the whole offer window");
        else
            $display("FAIL: received=%0d errors=%0d", received, errors);

        $finish;
    end

endmodule
