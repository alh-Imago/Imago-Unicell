// tb_combiner_cell_v1.v — points.md #257/#258 continuation: confirms
// combiner_cell_v1.v's fixed round-robin scan correctly captures from
// whichever of 3 stub chains has data at the moment its slot comes up,
// stamps the correct 2-bit slot ID, skips genuinely empty slots (no
// write, no address advance — dense packing), correctly serializes
// simultaneous offers from multiple chains, and that reading the
// results back from real bram_controller_v1.v shows the exact expected
// {ID,DATA} sequence in write order.
`timescale 1ns / 1ps

module tb_combiner_cell_v1;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

    localparam [3:0] DIR_N = 4'b0001, DIR_S = 4'b0010, DIR_E = 4'b0100, DIR_W = 4'b1000;

    // Chain 0 (slot0) on N, chain 1 (slot1) on S, chain 2 (slot2) on E.
    // Fixed output (W, unused directly — wr_cmd_* drives bram_controller
    // directly per combiner_cell_v1.v's own design) reserved per the
    // module's field convention even though this draft doesn't route
    // wr_cmd_* through a cardinal port.
    localparam [63:0] CFG = {48'h0, DIR_E /*slot2*/, DIR_S /*slot1*/, DIR_N /*slot0*/, DIR_W /*downstream, unused*/};

    reg        cfg = 0;
    reg [63:0] cfg_d = 0;

    // Stub chains — each holds its offer (fire + data) until acked,
    // matching real upstream offer/drain discipline.
    reg        n_fire = 0, s_fire = 0, e_fire = 0;
    reg [31:0] n_data = 0, s_data = 0, e_data = 0;

    wire ack_n, ack_s, ack_e;
    wire wr_cmd_valid;
    wire [15:0] wr_cmd_addr;
    wire [39:0] wr_cmd_wdata;
    wire wr_write_done;
    wire [1:0] status_slot;

    // Clear a chain's offer the cycle its own ack fires.
    always @(posedge clk) begin
        if (ack_n) n_fire <= 1'b0;
        if (ack_s) s_fire <= 1'b0;
        if (ack_e) e_fire <= 1'b0;
    end

    combiner_cell_v1 #(.CELL_ID(16'h0008), .ADDR_WIDTH(16)) DUT (
        .clk(clk), .rst(rst), .cfg_valid(cfg), .cfg_data(cfg_d),
        .data_in_n(n_data), .data_in_s(s_data), .data_in_e(e_data), .data_in_w(32'h0),
        .arrived_n(n_fire), .arrived_s(s_fire), .arrived_e(e_fire), .arrived_w(1'b0),
        .ack_out_n(ack_n), .ack_out_s(ack_s), .ack_out_e(ack_e), .ack_out_w(),
        .wr_cmd_valid(wr_cmd_valid), .wr_cmd_addr(wr_cmd_addr), .wr_cmd_wdata(wr_cmd_wdata),
        .wr_write_done(wr_write_done),
        .freeze_in(1'b0),
        .status_slot(status_slot), .status_wrote_this_cycle()
    );

    wire        rdata_valid;
    wire [39:0] rdata;
    reg         rd_cmd_valid = 0;
    reg  [15:0] rd_cmd_addr = 0;

    // Shared memory: the combiner's writes and the testbench's own
    // read-back checks both go through THIS one bram_controller_v1
    // instance — a real single shared memory, not two separate
    // instances (the gap #256's own PARTS 1+2 test explicitly flagged
    // as still open). cmd_valid/cmd_op/cmd_addr/cmd_wdata are muxed
    // between the combiner's write path and the testbench's own
    // read-check path (never simultaneous in this test).
    reg mem_cmd_valid;
    reg mem_cmd_op;
    reg [15:0] mem_cmd_addr;
    reg [39:0] mem_cmd_wdata;
    always @(*) begin
        if (wr_cmd_valid) begin
            mem_cmd_valid = 1'b1; mem_cmd_op = 1'b1 /*WRITE*/;
            mem_cmd_addr = wr_cmd_addr; mem_cmd_wdata = wr_cmd_wdata;
        end else begin
            mem_cmd_valid = rd_cmd_valid; mem_cmd_op = 1'b0 /*READ*/;
            mem_cmd_addr = rd_cmd_addr; mem_cmd_wdata = 40'h0;
        end
    end

    bram_controller_v1 #(.ADDR_WIDTH(16), .DATA_WIDTH(40)) MEM (
        .clk(clk), .rst(rst),
        .cmd_valid(mem_cmd_valid), .cmd_op(mem_cmd_op), .cmd_addr(mem_cmd_addr), .cmd_wdata(mem_cmd_wdata),
        .rdata_valid(rdata_valid), .rdata(rdata), .write_done(wr_write_done)
    );

    integer errors = 0;

    initial begin
        #12 rst = 0;
        #10 cfg = 1; cfg_d = CFG;
        #10 cfg = 0;
        #10;

        // Chain N offers alone — should be captured at slot0, written
        // to address 0, ID=00.
        n_fire = 1'b1; n_data = 32'hAAAA_0000;
        #40;   // several full 3-slot scans — plenty of time for slot0 to come up
        n_fire = 1'b0;   // safety, though ack should have already cleared it
        #20;

        // Chain S offers alone — captured at slot1, written to address
        // 1 (write_addr only advances on genuine capture, so this lands
        // right after N's, densely packed, no gap).
        s_fire = 1'b1; s_data = 32'hBBBB_0001;
        #40;
        s_fire = 1'b0;
        #20;

        // Chain E offers alone — captured at slot2, address 2.
        e_fire = 1'b1; e_data = 32'hCCCC_0002;
        #40;
        e_fire = 1'b0;
        #20;

        // N and S offer SIMULTANEOUSLY — the round-robin must serialize
        // them correctly (whichever slot the free-running counter
        // reaches first gets captured first — the counter's phase at
        // this point in the test is NOT something this test
        // synchronizes to, so either N-then-S or S-then-N is a
        // genuinely correct outcome; what matters is that BOTH land,
        // each with its own correct ID, densely packed with no gap).
        n_fire = 1'b1; n_data = 32'hDDDD_0003;
        s_fire = 1'b1; s_data = 32'hEEEE_0004;
        #60;
        n_fire = 1'b0; s_fire = 1'b0;
        #40;

        // Now read back addresses 0-4 and confirm the exact expected
        // {ID,DATA} sequence.
        check_read(16'h0000, {2'd1, 2'b00, 4'b0, 32'hAAAA_0000}, "addr0 (N, slot0)");
        check_read(16'h0001, {2'd1, 2'b01, 4'b0, 32'hBBBB_0001}, "addr1 (S, slot1)");
        check_read(16'h0002, {2'd1, 2'b10, 4'b0, 32'hCCCC_0002}, "addr2 (E, slot2)");
        check_pair_either_order(16'h0003, 16'h0004,
            {2'd1, 2'b00, 4'b0, 32'hDDDD_0003},   // N's stamped word
            {2'd1, 2'b01, 4'b0, 32'hEEEE_0004});  // S's stamped word

        if (errors == 0)
            $display("PASS: combiner_cell_v1 -- fixed round-robin correctly serialized 5 real captures (incl. 2 simultaneous), correct slot-ID stamping every time, dense write-address packing (no gaps despite many empty-slot skips), read-back through the SAME shared memory bit-exact");
        else
            $display("FAIL: %0d error(s)", errors);

        $finish;
    end

    task check_read(input [15:0] addr, input [39:0] expected, input [255:0] label);
        begin
            @(posedge clk);
            rd_cmd_valid = 1'b1; rd_cmd_addr = addr;
            @(posedge clk);
            rd_cmd_valid = 1'b0;
            #1;
            if (!rdata_valid) begin
                $display("FAIL: %0s -- rdata_valid never asserted", label);
                errors = errors + 1;
            end else if (rdata !== expected) begin
                $display("FAIL: %0s -- expected=%h got=%h", label, expected, rdata);
                errors = errors + 1;
            end else begin
                $display("%0s: %h (correct)", label, rdata);
            end
            #10;
        end
    endtask

    reg [39:0] r0, r1;
    task check_pair_either_order(input [15:0] addr_a, input [15:0] addr_b,
                                  input [39:0] expected_x, input [39:0] expected_y);
        begin
            @(posedge clk);
            rd_cmd_valid = 1'b1; rd_cmd_addr = addr_a;
            @(posedge clk);
            rd_cmd_valid = 1'b0;
            #1; r0 = rdata;
            #10;
            @(posedge clk);
            rd_cmd_valid = 1'b1; rd_cmd_addr = addr_b;
            @(posedge clk);
            rd_cmd_valid = 1'b0;
            #1; r1 = rdata;
            #10;
            if ((r0 === expected_x && r1 === expected_y) ||
                (r0 === expected_y && r1 === expected_x)) begin
                $display("addr%0d/addr%0d (simultaneous N+S, either order): %h then %h (correct, both present)",
                    addr_a, addr_b, r0, r1);
            end else begin
                $display("FAIL: simultaneous-offer pair -- got %h,%h, expected some order of %h,%h",
                    r0, r1, expected_x, expected_y);
                errors = errors + 1;
            end
        end
    endtask

endmodule
