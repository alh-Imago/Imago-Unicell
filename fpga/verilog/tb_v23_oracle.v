// tb_v23_oracle.v — drive the EXACT v2.3 silicon command words at the current
// cell and check whether SET_OUTPUT_ADDR lands. Isolates cell logic from the
// Arria 10 delivery path. Run: iverilog -o /tmp/o tb_v23_oracle.v unicell.v && vvp /tmp/o
`timescale 1ns/1ps
module tb_v23_oracle;
    reg clk=0, rst=0, cmd_valid=0, bus_valid=0;
    reg [31:0] cmd_bus=0, cmd_data=0, bus_addr=0, bus_data=0;
    wire [31:0] out_addr,out_data,dbg_cmd_latch,dbg_input_addr,dbg_output_addr,dbg_a_data;
    wire out_valid,dbg_start_flag,dbg_armed,dbg_frozen,dbg_priority,dbg_trace,dbg_breakpoint,dbg_output_set,dbg_a_arrived;
    wire [1:0] dbg_dtype;
    always #5 clk=~clk;

    unicell #(.CELL_ID(42), .ENABLE_LATCH_IN(1)) dut (
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

    initial begin
        rst=1; repeat(4) @(posedge clk); #1; rst=0; @(posedge clk); #1;
        $display("reset:       out_addr=0x%04x output_set=%0d armed=%0d", dbg_output_addr, dbg_output_set, dbg_armed);
        cmd(32'h00000007, 32'h00A50100);  // BOOT_COMMIT -> input_address=0x0100, auth=0xA5, RUN
        $display("BOOT_COMMIT: in_addr=0x%04x auth_mask=0x%02x", dbg_input_addr, (dbg_cmd_latch>>11)&8'hFF);
        // v3.1+ Option A: SET_OUTPUT_ADDR is addr_match-gated (one comparator). Present the
        // cell's address on the lane (in RUN that is input_address=0x0100), as the SET_TARGET
        // latch does on hardware. Hold it so bus_addr_r is settled when cmd_valid is sampled.
        bus_addr <= 32'h00000100; repeat(2) @(posedge clk); #1;
        cmd(32'h14A00003, 32'h00000200);  // SET_OUTPUT_ADDR  <- THE TEST (target on the lane)
        $display("SET_OUTPUT:  out_addr=0x%04x output_set=%0d   <<< expect out_addr=0x0200 output_set=1", dbg_output_addr, dbg_output_set);
        cmd(32'h14A00004, 32'h5280082C);  // RECONFIGURE PASS_B armed (broadcast+auth, no addr_match)
        $display("RECONFIGURE: armed=%0d output_set=%0d cmd_latch=0x%08x", dbg_armed, dbg_output_set, dbg_cmd_latch);
        $display("%s", (dbg_output_addr==16'h0200) ? ">>> CELL LOGIC OK: SET_OUTPUT lands -> silicon failure is DELIVERY" :
                                                     ">>> CELL-LEVEL: SET_OUTPUT did NOT land in sim either -> encoding/logic");
        $finish;
    end
endmodule
