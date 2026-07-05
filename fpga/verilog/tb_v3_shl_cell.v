// tb_v3_shl_cell.v — verifies ONE cell can realize "SHL by span" using
// PASS_B (0x02C) + latch_in (fires on any single arrival) + shift_in_en
// (METH_SET_SHIFT_IN), before trusting this pattern across the 19-cell
// packed shift-adder placement. Confirms against the RTL trace:
// second_val = bus_data_shifted, and PASS_B gives computed_output=second_val.
`timescale 1ns/1ps
module tb_v3_shl_cell;
    reg clk=0, rst=0; reg [31:0] cmd_bus=0, cmd_data=0; reg cmd_valid=0;
    reg [15:0] bus_addr=0; reg [31:0] bus_data=0; reg bus_valid=0;
    always #5 clk=~clk;

    wire [31:0] out_addr, out_data; wire out_valid;
    wire [31:0] ceb,ced; wire cev;

    unicell64_v3 #(.CELL_ID(16'h0000)) dut (
        .clk(clk), .rst(rst),
        .cmd_bus(cmd_bus), .cmd_data(cmd_data), .cmd_valid(cmd_valid),
        .bus_addr(bus_addr), .bus_data(bus_data), .bus_valid(bus_valid),
        .out_addr(out_addr), .out_data(out_data), .out_valid(out_valid),
        .cmd_emit_bus(ceb), .cmd_emit_data(ced), .cmd_emit_valid(cev)
    );

    integer errors=0;
    integer i;
    task check32; input [31:0] got, want; input [255:0] msg; begin
        if (got===want) $display("  PASS: %0s (0x%08x)", msg, got);
        else begin $display("  FAIL: %0s got=0x%08x want=0x%08x", msg, got, want); errors=errors+1; end
    end endtask

    localparam [7:0] OP_LOAD_AT = 8'd23;
    localparam [7:0] METH_SET_SHIFT_IN = 8'd31;
    localparam [9:0] TOPO_PASS_B = 10'h02C;

    initial begin
        rst=1; repeat(4) @(posedge clk); #1; rst=0; repeat(2) @(posedge clk); #1;
        $display("=== SHL-via-cell: PASS_B + latch_in + shift_in_en ===");

        // Configure: topology=PASS_B, start_flag=1 (armed), latch_in=1 (fires
        // on any single arrival) via cmd_data[17], PLUS bank-2 methodology
        // METH_SET_SHIFT_IN with shift_amt=4 (a valid discrete value per the
        // RTL's supported set {1,2,4,8,12,16,20,24,28}).
        // Boot first -- bank-2 methodology on LOAD_AT only activates in RUN
        // mode (!physical_mode), which defaults to 1 (boot) until committed.
        @(negedge clk); bus_addr=16'h0000; cmd_bus={8'h0,8'd7}; cmd_data=32'h0000_0000; cmd_valid=1'b1;
        @(posedge clk); #1; cmd_valid=1'b0;
        repeat(2) @(posedge clk); #1;
        check32({31'h0,dut.physical_mode}, 32'h0, "booted into RUN (physical_mode cleared)");

        @(negedge clk); bus_addr=16'h0000;
        cmd_bus = 32'h0001_1F17; // bit16=1 (bank2 valid), [15:8]=METH_SET_SHIFT_IN(31=0x1F), [7:0]=LOAD_AT(23=0x17)
        // cmd_data: bit11=start_flag, bit17=latch_in, [9:0]=topology(PASS_B),
        // [30:23]=bank-2 shift payload=4. Computed directly (not via shifted
        // 1-bit constants -- that's the exact AUTH<<19 width-truncation bug
        // from earlier this session; a plain literal avoids repeating it).
        cmd_data = 32'h0202_082C;
        cmd_valid=1'b1;
        @(posedge clk); #1; cmd_valid=1'b0;
        repeat(2) @(posedge clk); #1;
        check32(dut.cmd_latch[9:0], TOPO_PASS_B, "topology = PASS_B");
        check32({31'h0,dut.cmd_latch[22]}, 32'h1, "start_flag (armed)");
        check32({31'h0,dut.cmd_latch[26]}, 32'h1, "latch_in set");
        check32({31'h0,dut.cmd_latch[47]}, 32'h1, "shift_in_en set (bank-2 methodology)");
        check32({26'h0,dut.cmd_latch[46:41]}, 32'd4, "shift_amt = 4 (valid discrete value)");

        // Prime it (preloaded-A pattern, per ICM_FORMAT.md): a cold cell's
        // first-ever value still needs a genuine two-arrival completion --
        // latch_in only keeps it re-armed AFTER the first real fire. Without
        // this, a one-shot relay cell (fires once on a single incoming value,
        // as every SHL-role cell in the packed adder does) would miss its
        // only real input. CMD_SWAP_AB (opcode 18) sets a_arrived directly.
        @(negedge clk); bus_addr=16'h0000; cmd_bus={8'h0,8'd18}; cmd_data=32'h0; cmd_valid=1'b1;
        @(posedge clk); #1; cmd_valid=1'b0;
        repeat(2) @(posedge clk); #1;
        check32({31'h0,dut.a_arrived}, 32'h1, "primed: a_arrived set before the real value arrives");

        // Fire: inject a single value on the data bus (latch_in means this
        // ALONE triggers the fire, no preload needed).
        @(negedge clk); bus_addr=16'h0000; bus_data=32'h0000_00F0; bus_valid=1'b1;
        @(posedge clk); #1; bus_valid=1'b0;
        for (i=0;i<4;i=i+1) begin
            $display("  dbg cyc %0d: out_valid=%0d out_data=0x%08x a_arrived=%0d", i, out_valid, out_data, dut.a_arrived);
            @(posedge clk); #1;
        end
        check32(out_data, 32'h0000_0F00, "output = input << 4  (0x000000F0 -> 0x00000F00)");
        check32({31'h0,out_valid===1'b0}, 32'h1, "out_valid settled back to 0 after the pulse");

        // A second, different value -- confirms it re-fires on every arrival
        // (latch_in), not just once.
        @(negedge clk); bus_addr=16'h0000; bus_data=32'h0000_0003; bus_valid=1'b1;
        @(posedge clk); #1; bus_valid=1'b0;
        repeat(4) @(posedge clk); #1;
        check32(out_data, 32'h0000_0030, "second fire: 0x3 << 4 = 0x30 (re-arms correctly)");

        if (errors==0) $display(">>> SHL-VIA-CELL PASS: PASS_B+latch_in+shift_in_en correctly realizes a left-shift cell");
        else $display(">>> SHL-VIA-CELL FAIL: %0d errors", errors);
        $finish;
    end
endmodule
