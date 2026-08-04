// tb_unicell64.v — golden test for the 64-bit cmd_latch variant (unicell64.v).
// Proves the methodology half loads and DRIVES the datapath: stored shift and
// stored nibble-mask, applied on a bare trigger (no transient bus modifiers).
// Methodology write = CMD_SET_METHOD (op 25), addr_match-gated on the held target,
// cmd_data -> cmd_latch[63:32]. Field map within cmd_data:
//   [7:0]  nibble_mask   [8] mask_en   [14:9] shift_amount   [15] in_shift_en   [16] out_shift_en
// Run: iverilog -o /tmp/o tb_unicell64.v unicell64.v && vvp /tmp/o
`timescale 1ns/1ps
module tb_unicell64;
    reg clk=0, rst=0, cmd_valid=0, bus_valid=0;
    reg [31:0] cmd_bus=0, cmd_data=0, bus_addr=0, bus_data=0;
    wire [31:0] out_addr,out_data,dbg_cmd_latch,dbg_input_addr,dbg_output_addr,dbg_a_data;
    wire out_valid,dbg_start_flag,dbg_armed,dbg_frozen,dbg_priority,dbg_trace,dbg_breakpoint,dbg_output_set,dbg_a_arrived;
    wire [1:0] dbg_dtype;
    integer fails=0;
    always #5 clk=~clk;

    unicell64 #(.CELL_ID(42), .ENABLE_LATCH_IN(1)) dut (
        .clk(clk),.rst(rst),.cmd_bus(cmd_bus),.cmd_data(cmd_data),.cmd_valid(cmd_valid),
        .bus_addr(bus_addr),.bus_data(bus_data),.bus_valid(bus_valid),
        .out_addr(out_addr),.out_data(out_data),.out_valid(out_valid),
        .dbg_cmd_latch(dbg_cmd_latch),.dbg_input_addr(dbg_input_addr),.dbg_input_addr_short(),
        .dbg_output_addr(dbg_output_addr),.dbg_start_flag(dbg_start_flag),.dbg_armed(dbg_armed),
        .dbg_frozen(dbg_frozen),.dbg_priority(dbg_priority),.dbg_trace(dbg_trace),
        .dbg_breakpoint(dbg_breakpoint),.dbg_dtype(dbg_dtype),
        .dbg_output_set(dbg_output_set),.dbg_a_arrived(dbg_a_arrived),.dbg_a_data(dbg_a_data)
    );

    task cmd; input [31:0] cb,cd; begin
        @(negedge clk); cmd_bus<=cb; cmd_data<=cd; cmd_valid<=1;
        @(posedge clk); #1; cmd_valid<=0; cmd_bus<=0; cmd_data<=0;
        @(posedge clk); #1;
    end endtask

    task chk32; input [31:0] got, want; input [255:0] label; begin
        $display("  %-40s 0x%08x (want 0x%08x)  %s", label, got, want, (got===want)?"PASS":"** FAIL **");
        if (got!==want) fails=fails+1;
    end endtask

    initial begin
        rst=1; repeat(4) @(posedge clk); #1; rst=0; @(posedge clk); #1;
        $display("=== unicell64: stored shift + nibble mask (methodology half) ===");

        // target this cell by physical CELL_ID on the address lane (boot/physical mode)
        bus_addr <= 32'd42; repeat(2) @(posedge clk); #1;

        // 1. Arm a PASS cell (CMD_LOAD_AT, op 23): topology=PASS(0), start_flag (bit11)
        cmd(32'h00000017, 32'h00000800);

        // 2. Methodology write (CMD_SET_METHOD, op 25): in_shift_en + shift_amount=4 (one nibble)
        //    cmd_data = (1<<15) | (4<<9) = 0x8800
        cmd(32'h00000019, 32'h00008800);
        $display("after SET_METHOD shift: cmd_latch[63:32]=0x%08x", dut.cmd_latch[63:32]);
        chk32({31'b0,dut.m_in_shift_en}, 32'h1, "stored in_shift_en set");
        chk32({26'b0,dut.m_shift_amt},   32'h4, "stored shift_amount = 4");
        chk32({31'b0,dut.shift_in_en},   32'h1, "effective shift_in_en (stored OR bus)");
        chk32({27'b0,dut.shift_amt},     32'h4, "effective shift_amt = 4");

        // drive a value on the bus; bus_data_shifted should be <<4 (one nibble)
        bus_data <= 32'h0000ABCD; bus_valid <= 1; @(posedge clk); #1; bus_valid <= 0; @(posedge clk); #1;
        chk32(dut.bus_data_shifted, 32'h000ABCD0, "input shifted LEFT 4 bits (stored shift)");

        // 3. Methodology write: mask_en + nibble_mask=0xF0 (BLOCK high 4 nibbles = high 16 bits)
        //    cmd_data = (1<<8) | 0xF0 = 0x1F0  (clears in_shift_en since [15]=0)
        cmd(32'h00000019, 32'h000001F0);
        chk32({31'b0,dut.m_mask_en},     32'h1, "stored mask_en set");
        chk32({24'b0,dut.m_nibble_mask}, 32'hF0, "stored nibble_mask = 0xF0");
        // with shift now off and mask blocking the high 16 bits of 0x0000ABCD -> 0x0000ABCD & 0x0000FFFF
        bus_data <= 32'hDEADABCD; bus_valid <= 1; @(posedge clk); #1; bus_valid <= 0; @(posedge clk); #1;
        chk32(dut.bus_data_masked, 32'h0000ABCD, "high 16 bits masked out (stored nibble mask)");

        if (fails==0) $display("  >>> PASS: methodology half loads and drives the datapath (shift + mask)");
        else          $display("  >>> FAIL: %0d check(s)", fails);
        $finish;
    end
endmodule
