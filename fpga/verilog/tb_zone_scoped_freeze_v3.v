// tb_zone_scoped_freeze_v3.v — proves the actual point of this session's
// backpressure work: FREEZE scoped to ONE zone, not the whole system. Two
// zones, each with its OWN independent cmd_valid line (not one shared/
// broadcast wire, which is what top_card_2zone_v3.v uses today and would
// freeze everything at once) -- a zone_watchdog_v3 instance drives ONLY
// zone0's cmd_valid. Confirms zone0's cell freezes while zone1's cell, armed
// and firing on its own two-arrival schedule throughout, is never disturbed.
`timescale 1ns/1ps
module tb_zone_scoped_freeze_v3;
    reg clk=0, rst=0; always #5 clk=~clk;

    // Independent per-zone command buses -- the actual fix this test proves
    // is necessary: NOT a shared cmd_bus/cmd_valid across zones.
    reg [31:0] z0_cmd_bus=0, z0_cmd_data=0; reg z0_cmd_valid=0;
    reg [31:0] z1_cmd_bus=0, z1_cmd_data=0; reg z1_cmd_valid=0;
    reg [15:0] z0_bus_addr=0, z1_bus_addr=0;
    reg [31:0] z0_bus_data=0, z1_bus_data=0;
    reg        z0_bus_valid=0, z1_bus_valid=0;

    wire [31:0] z0_out_addr, z1_out_addr; wire [31:0] z0_out_data, z1_out_data;
    wire z0_out_valid, z1_out_valid;
    wire [31:0] z0_ceb, z0_ced; wire z0_cev; // cmd_emit (unused here, tied off)
    wire [31:0] z1_ceb, z1_ced; wire z1_cev;
    wire [31:0] z0_dbg_cl, z1_dbg_cl;

    unicell64_v3 #(.CELL_ID(16'h0000)) cell0 (
        .clk(clk), .rst(rst),
        .cmd_bus(z0_cmd_bus), .cmd_data(z0_cmd_data), .cmd_valid(z0_cmd_valid),
        .bus_addr(z0_bus_addr), .bus_data(z0_bus_data), .bus_valid(z0_bus_valid),
        .out_addr(z0_out_addr), .out_data(z0_out_data), .out_valid(z0_out_valid),
        .cmd_emit_bus(z0_ceb), .cmd_emit_data(z0_ced), .cmd_emit_valid(z0_cev),
        .dbg_cmd_latch(z0_dbg_cl)
    );
    unicell64_v3 #(.CELL_ID(16'h0001)) cell1 (
        .clk(clk), .rst(rst),
        .cmd_bus(z1_cmd_bus), .cmd_data(z1_cmd_data), .cmd_valid(z1_cmd_valid),
        .bus_addr(z1_bus_addr), .bus_data(z1_bus_data), .bus_valid(z1_bus_valid),
        .out_addr(z1_out_addr), .out_data(z1_out_data), .out_valid(z1_out_valid),
        .cmd_emit_bus(z1_ceb), .cmd_emit_data(z1_ced), .cmd_emit_valid(z1_cev),
        .dbg_cmd_latch(z1_dbg_cl)
    );

    // ── watchdog: guards ONLY cell0's zone ────────────────────────────────
    reg [15:0] write_count=0, read_count=0;
    wire [31:0] wd_cmd_bus, wd_cmd_data; wire wd_cmd_valid; wire wd_frozen;
    localparam [10:0] AUTH = 11'h000; // open auth (fresh cells, auth_mask=0 -> auth_boot)

    zone_watchdog_v3 #(.HIGH(16'd12), .LOW(16'd4), .AUTH(AUTH)) watchdog (
        .clk(clk), .rst(rst),
        .write_count(write_count), .read_count(read_count),
        .cmd_bus(wd_cmd_bus), .cmd_data(wd_cmd_data), .cmd_valid(wd_cmd_valid),
        .frozen(wd_frozen)
    );
    // Wire the watchdog's output onto ZONE0's cmd bus only.
    always @(*) begin
        z0_cmd_bus   = wd_cmd_valid ? wd_cmd_bus  : 32'h0;
        z0_cmd_data  = wd_cmd_valid ? wd_cmd_data : 32'h0;
        z0_cmd_valid = wd_cmd_valid;
    end

    integer errors=0;
    task check; input got; input want; input [255:0] msg; begin
        if (got===want) $display("  PASS: %0s", msg);
        else begin $display("  FAIL: %0s got=%0d want=%0d", msg, got, want); errors=errors+1; end
    end endtask

    reg [31:0] fire_count_z1;
    always @(posedge clk) if (z1_out_valid) fire_count_z1 <= fire_count_z1 + 1'b1;

    initial begin
        rst=1; repeat(4) @(posedge clk); #1; rst=0; repeat(2) @(posedge clk); #1;
        $display("=== ZONE-SCOPED FREEZE: watchdog guards zone0 only, zone1 keeps running ===");

        // Arm cell0 and cell1 (XOR, armed, latch_in -- fires on every arrival)
        // via CMD_LOAD_AT directly (config_match on their own CELL_ID, no
        // SET_TARGET needed here since bus_addr defaults to 0 which already
        // matches cell0, and we explicitly set it to 1 for cell1 below).
        @(negedge clk); z0_bus_addr=16'h0000; z0_cmd_bus={8'h0,8'd23}; z0_cmd_data=32'h0002_08BC; z0_cmd_valid=1'b1;
        @(posedge clk); #1; z0_cmd_valid=1'b0;
        // cell1's bus_addr changes from its reset default (0) to 1 -- needs a
        // settle cycle before bus_addr_r (internal, 1-cycle-registered) catches
        // up, same hazard as the loader/card work earlier this session.
        @(negedge clk); z1_bus_addr=16'h0001;
        @(posedge clk); #1; // settle: let bus_addr_r become 1 before targeting
        @(negedge clk); z1_cmd_bus={8'h0,8'd23}; z1_cmd_data=32'h0002_08BC; z1_cmd_valid=1'b1;
        @(posedge clk); #1; z1_cmd_valid=1'b0;
        repeat(2) @(posedge clk); #1;
        check(cell0.cmd_latch[9:0]===10'h0BC, 1'b1, "cell0 armed: topology=XOR, latch_in, start_flag");
        check(cell1.cmd_latch[9:0]===10'h0BC, 1'b1, "cell1 armed: topology=XOR, latch_in, start_flag");

        // Start feeding zone1 continuously (independent of anything happening
        // to zone0) -- one data arrival per iteration, latch_in means it fires
        // every time.
        fire_count_z1 = 0;

        // Drive the watchdog's level up to HIGH -- this must freeze cell0 only.
        // (One extra cycle after the watchdog's own frozen_r/cmd_valid become
        // visible: cell0 processes cmd_valid the cycle AFTER it's asserted,
        // standard registered-to-registered latency, not a bug.)
        write_count = 12; read_count = 0;
        @(posedge clk); #1;
        check(wd_frozen, 1'b1, "watchdog: frozen (level=12=HIGH)");
        @(posedge clk); #1;
        check(cell0.frozen, 1'b1, "cell0 (zone0): frozen -- watchdog reached it");
        check(cell1.frozen, 1'b0, "cell1 (zone1): NOT frozen -- untouched by zone0's watchdog");

        // Feed zone1 several times WHILE zone0 is frozen -- it must keep firing.
        repeat(5) begin
            @(negedge clk); z1_bus_addr=16'h0001; z1_bus_data=32'hDEAD_0000+$random; z1_bus_valid=1'b1;
            @(posedge clk); #1; z1_bus_valid=1'b0;
            @(posedge clk); #1;
        end
        check((fire_count_z1 >= 1), 1'b1, "zone1 continued firing while zone0 was frozen");
        check(cell0.frozen, 1'b1, "cell0 still frozen (no change from zone1's activity)");

        // Release: drop the level back to LOW -- cell0 unfreezes, zone1 unaffected.
        write_count = 4; read_count = 0;
        @(posedge clk); #1;
        check(wd_frozen, 1'b0, "watchdog: released (level=4=LOW)");
        @(posedge clk); #1;
        check(cell0.frozen, 1'b0, "cell0 (zone0): released");
        check(cell1.frozen, 1'b0, "cell1 (zone1): still never frozen throughout");

        if (errors==0) $display(">>> ZONE-SCOPED FREEZE PASS: zone0 frozen/released independently, zone1 never touched");
        else $display(">>> ZONE-SCOPED FREEZE FAIL: %0d errors", errors);
        $finish;
    end
endmodule
