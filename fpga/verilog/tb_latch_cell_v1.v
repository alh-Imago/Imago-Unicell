// tb_latch_cell_v1.v — points.md #295/#296 continuation: confirms
// latch_cell_v1.v's own real claims -- stays latched across MULTIPLE
// downstream reads (genuinely sticky, not just a one-shot value), CLEAR
// takes priority when both set and clear arrive the same cycle
// (matching #279/#284's own established rule), and reconfiguration
// reset.
`timescale 1ns / 1ps

module tb_latch_cell_v1;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

    localparam [3:0] DIR_N = 4'b0001, DIR_S = 4'b0010, DIR_E = 4'b0100;
    // set on N, clear on S, offer on E
    localparam [63:0] CFG = {52'h0, DIR_E, DIR_S, DIR_N};

    reg        cfg = 0;
    reg [63:0] cfg_d = 0;

    reg set_pulse = 0, clr_pulse = 0;
    reg [31:0] set_data = 32'h1;   // must genuinely carry a 1 now that latch_cell_v1.v
                                    // correctly gates on the arriving VALUE, not just
                                    // whether something arrived at all (real bug fix,
                                    // found via the 3-cell integration test)
    wire [31:0] data_out_e;
    wire        fire_e, status_lat;
    reg         cons_ready = 1, cons_ack = 0;

    latch_cell_v1 #(.CELL_ID(16'h0005)) DUT (
        .clk(clk), .rst(rst), .cfg_valid(cfg), .cfg_data(cfg_d),
        .data_in_n(set_data), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(set_pulse), .arrived_s(clr_pulse), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(), .data_out_e(data_out_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(fire_e), .fire_w(),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(cons_ready), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(cons_ack), .ack_in_w(1'b0),
        .freeze_in(1'b0), .ready_out(), .status_latched(status_lat)
    );

    integer errors = 0;

    task drain;
        begin
            wait (fire_e);
            @(posedge clk); cons_ack = 1; @(posedge clk); cons_ack = 0;
            #20;
        end
    endtask

    initial begin
        #12 rst = 0;
        #10 cfg = 1; cfg_d = CFG;
        #10 cfg = 0;
        #10;

        // ── PART 1: set, then confirm it STAYS latched across THREE
        // separate reads, not just the first one. ──
        set_pulse = 1; #10; set_pulse = 0; #10;
        drain;
        if (data_out_e[0] !== 1'b1) begin $display("FAIL: expected latched=1 after set, got %0d", data_out_e[0]); errors=errors+1; end
        else $display("OK: correctly latched to 1 after set");

        drain;   // read AGAIN, no new set in between
        if (data_out_e[0] !== 1'b1) begin $display("FAIL: should STILL be 1 (sticky), got %0d", data_out_e[0]); errors=errors+1; end
        else $display("OK: correctly STAYED at 1 across a second read (genuinely sticky, not one-shot)");

        drain;   // and a THIRD time
        if (data_out_e[0] !== 1'b1) begin $display("FAIL: should STILL be 1 after a third read, got %0d", data_out_e[0]); errors=errors+1; end
        else $display("OK: correctly STAYED at 1 across a third read -- PART 1 confirms genuine sticky behavior");

        // ── PART 2: clear ──
        clr_pulse = 1; #10; clr_pulse = 0; #10;
        drain;
        if (data_out_e[0] !== 1'b0) begin $display("FAIL: expected latched=0 after clear, got %0d", data_out_e[0]); errors=errors+1; end
        else $display("OK: correctly cleared to 0");

        // ── PART 3: CLEAR TAKES PRIORITY -- pulse both set and clear
        // the SAME cycle. ──
        set_pulse = 1; clr_pulse = 1; #10; set_pulse = 0; clr_pulse = 0; #10;
        drain;
        if (data_out_e[0] !== 1'b0) begin $display("FAIL: clear should take priority when both arrive same cycle, got %0d", data_out_e[0]); errors=errors+1; end
        else $display("OK: clear correctly took priority when both set and clear arrived the same cycle");

        // ── PART 4: reconfiguration resets ──
        set_pulse = 1; #10; set_pulse = 0; #10;
        cfg = 1; cfg_d = CFG; #10; cfg = 0; #10;
        if (DUT.latched !== 1'b0) begin $display("FAIL: reconfiguration should reset the latch, got %0d", DUT.latched); errors=errors+1; end
        else $display("OK: reconfiguration correctly resets the latch");

        if (errors == 0)
            $display("PASS: latch_cell_v1 -- genuinely sticky across multiple reads, clear correctly takes priority, reconfiguration reset correct");
        else
            $display("FAIL: %0d error(s)", errors);

        $finish;
    end

endmodule
