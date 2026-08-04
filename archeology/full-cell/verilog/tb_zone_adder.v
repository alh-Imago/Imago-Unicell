`timescale 1ns/1ps
// tb_zone_adder.v — single zone (28 cells), physical-mode addressing (flat 0..27).
// Tests the half-adder primitive on a cell: bitwise XOR = sum bits, bitwise AND =
// carry bits, A and B delivered by preload + inject. Proves topology(A,B) compute,
// addressing (cell responds at its flat physical addr 0), and a multi-cell chain.
// No bootloader walk needed for one zone — physical CELL_ID 0..27 IS the flat map.
module tb_zone_adder;
    localparam NB=2;
    reg clk=0,rst=0; always #5 clk=~clk;
    reg [31:0] cbus=0,cdat=0; reg cv=0;
    wire [15:0] cpu_addr_w=(cbus[7:0]==8'd1)?cdat[31:16]:cdat[15:0];
    wire pre=(cbus[18:17]!=2'b00);
    wire cmv=cv&&(cbus[7:0]!=8'd1)&&((cbus[7:0]!=8'd0)||pre);
    wire [NB-1:0] tv=0; wire [NB*16-1:0] ta=0; wire [NB*32-1:0] td=0;
    wire [15:0] oa; wire [31:0] od; wire ov;
    unicell_zone #(.NUM_CELLS(28),.NUM_BRIDGES(NB),.ZONE_ID(0)) z(.clk(clk),.rst(rst),
      .cmd_bus(cbus),.cmd_data(cdat),.cmd_valid(cmv),.cpu_addr(cpu_addr_w),.cpu_data(cdat),.cpu_valid(cv),
      .out_addr(oa),.out_data(od),.out_valid(ov),.armed_count(),.arrived_count(),.output_set_count(),
      .dbg0_cmd_latch(),.dbg0_input_addr(),.dbg0_output_addr(),.dbg0_a_data(),.cycle_count(),
      .bridge_n_in_valid(tv),.bridge_n_in_addr(ta),.bridge_n_in_data(td),.bridge_n_out_valid(),.bridge_n_out_addr(),.bridge_n_out_data(),
      .bridge_s_in_valid(tv),.bridge_s_in_addr(ta),.bridge_s_in_data(td),.bridge_s_out_valid(),.bridge_s_out_addr(),.bridge_s_out_data(),
      .bridge_e_in_valid(tv),.bridge_e_in_addr(ta),.bridge_e_in_data(td),.bridge_e_out_valid(),.bridge_e_out_addr(),.bridge_e_out_data(),
      .bridge_w_in_valid(tv),.bridge_w_in_addr(ta),.bridge_w_in_data(td),.bridge_w_out_valid(),.bridge_w_out_addr(),.bridge_w_out_data());

    // capture last surfaced output
    reg [31:0] last_out; reg [15:0] last_oaddr; integer fires;
    always @(posedge clk) if (ov) begin last_out<=od; last_oaddr<=oa; fires<=fires+1; end

    task xact; input [31:0] cb,cd; begin
        @(negedge clk); cbus<=cb; cdat<=cd; cv<=1;
        @(posedge clk); #1; cv<=0; repeat(5)@(posedge clk); #1; end endtask
    task settle; begin repeat(20)@(posedge clk); #1; end endtask
    task hard_reset; begin @(negedge clk); rst<=1; repeat(4)@(posedge clk); #1; rst<=0; repeat(3)@(posedge clk); #1; end endtask

    // RECONFIGURE payload = 0x52800800 | topology  (armed, start_flag, output_set base)
    localparam [31:0] RC = 32'h52800800;
    localparam [9:0] T_XOR=10'h0BC, T_AND=10'h007, T_OR=10'h024;

    integer errors;
    initial begin
        errors=0; fires=0;
        rst=1; repeat(5)@(posedge clk); #1; rst=0; repeat(2)@(posedge clk); #1;

        $display("================ SINGLE-ZONE ADDER TEST (28 cells, physical flat 0..27) ================");

        // ---- HALF-ADDER SUM:  out = A XOR B ----
        // cell 0 @ physical addr 0, output 0x200; A=0x0000000C, B=0x0000000A -> sum=0x6
        fires=0;
        xact(32'h14A00003, 32'h00000200);          // SET_OUTPUT_ADDR=0x200
        xact(32'h14A00004, RC | T_XOR);             // RECONFIGURE topology=XOR, armed
        xact(32'h00000001, 32'h0000000C);           // inject A=0x0C @ addr 0 (1st arrival -> stored)
        xact(32'h00000001, 32'h0000000A);           // inject B=0x0A @ addr 0 (2nd arrival -> fire)
        settle;
        $display("  XOR(sum):  A=0x0C B=0x0A -> out=0x%08x  (expect 0x00000006)  addr=0x%04x", last_out, last_oaddr);
        if (last_out !== 32'h00000006) begin errors=errors+1; $display("    FAIL sum"); end
        hard_reset;

        // ---- HALF-ADDER CARRY: out = A AND B ----
        fires=0;
        xact(32'h14A00003, 32'h00000200);
        xact(32'h14A00004, RC | T_AND);             // topology=AND
        xact(32'h00000001, 32'h0000000C);           // inject A=0x0C
        xact(32'h00000001, 32'h0000000A);           // inject B=0x0A
        settle;
        $display("  AND(carry):A=0x0C B=0x0A -> out=0x%08x  (expect 0x00000008)  addr=0x%04x", last_out, last_oaddr);
        if (last_out !== 32'h00000008) begin errors=errors+1; $display("    FAIL carry"); end

        // ---- CHAIN + ADDRESSING: OR passthrough ripples cell-to-cell ----
        hard_reset;
        fires=0;
        xact(32'h14A00004, RC | T_OR);              // OR topology, default output CELL_ID+1
        xact(32'h14A20000, 32'h00000000);           // preload A=0 -> OR(0,B)=B passthrough
        xact(32'h00000001, 32'h00002340);           // inject B=0x2340 @ addr 0
        settle;
        $display("  CHAIN:     inject@0 0x2340 -> fires=%0d last_addr=0x%04x last_data=0x%08x (expect ripple, 0x2340)", fires, last_oaddr, last_out);
        if (fires < 2 || last_out !== 32'h00002340) begin errors=errors+1; $display("    FAIL chain"); end

        $display("========================================================================================");
        if (errors==0) $display("  >>> ADDER TEST OK: XOR sum + AND carry compute correctly, chain + addressing good");
        else           $display("  >>> %0d FAILURE(S)", errors);
        $finish;
    end
endmodule
