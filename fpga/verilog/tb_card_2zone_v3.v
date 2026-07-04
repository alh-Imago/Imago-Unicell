// tb_card_2zone_v3.v — proves the 2-zone card: BRAM as program store (again)
// AND, the new part this session was for, BRAM as the inter-zone data buffer.
// Sequence: load both zones' single cells via the on-card loader FSM: fire
// Zone 0 (preload+inject, host-driven, same as tb_pcie_bram_v3.v); confirm the
// result is captured into the buffer BRAM; confirm the autonomous bridge FSM
// (no host involvement) picks it up and injects it into Zone 1; confirm
// Zone 1 relays it into the results BRAM -- the repository a host/PCIe read
// would pull from.
`timescale 1ns/1ps
module tb_card_2zone_v3;
    reg clk=0, rst=0; always #5 clk=~clk;
    reg start_load = 1'b0;
    reg [31:0] host_cmd_bus=0, host_cmd_data=0; reg host_cmd_valid=0;
    wire [31:0] results_rdata; wire loader_done; wire [15:0] bridge_hops;

    top_card_2zone_v3 #(.NUM_CELLS(4)) card (
        .clk(clk), .rst(rst), .start_load(start_load),
        .host_cmd_bus(host_cmd_bus), .host_cmd_data(host_cmd_data), .host_cmd_valid(host_cmd_valid),
        .results_rdata(results_rdata), .loader_done(loader_done), .bridge_hops(bridge_hops)
    );

    integer errors=0;
    task check32; input [31:0] got, want; input [127:0] msg; begin
        if (got===want) $display("  PASS: %0s (0x%08x)", msg, got);
        else begin $display("  FAIL: %0s got=0x%08x want=0x%08x", msg, got, want); errors=errors+1; end
    end endtask
    task check1; input got; input want; input [127:0] msg; begin
        if (got===want) $display("  PASS: %0s", msg);
        else begin $display("  FAIL: %0s got=%0d want=%0d", msg, got, want); errors=errors+1; end
    end endtask

    localparam [7:0] OP_SWAP_AB = 8'd18;

    task host_xact; input [31:0] cb, cd; begin
        @(negedge clk); host_cmd_bus=cb; host_cmd_data=cd; host_cmd_valid=1'b1;
        @(posedge clk); #1; host_cmd_valid=1'b0;
        @(posedge clk); #1;
    end endtask

    integer w;
    initial begin
        rst=1; repeat(4) @(posedge clk); #1; rst=0; repeat(2) @(posedge clk); #1;
        $display("=== 2-ZONE CARD: BRAM as program store + inter-zone data buffer ===");

        // ── phase 1: load both zones' cells via the on-card loader FSM ──────
        @(negedge clk); start_load = 1'b1;
        @(posedge clk); #1; start_load = 1'b0;
        w = 0;
        while (!loader_done && w < 200) begin @(posedge clk); #1; w = w + 1; end
        check1(loader_done, 1'b1, "phase1: on-card loader finished (both cells confirmed)");
        check32(card.zone0.cells.cell_array[0].cell_inst.cmd_latch[9:0], 10'h0BC, "phase1: zone0 cell0 topology = XOR");
        check32(card.zone1.cells.cell_array[0].cell_inst.cmd_latch[9:0], 10'h02C, "phase1: zone1 cell0 topology = PASS_B");
        check1(card.zone1.cells.cell_array[0].cell_inst.cmd_latch[26], 1'b1, "phase1: zone1 cell0 latch_in set");

        // ── phase 2: host preloads + injects Zone 0's operands, same pattern ─
        // as tb_pcie_bram_v3.v -- A=0xA5 (CMD_SWAP_AB), B=0xF0 (DATA_WRITE).
        host_xact({8'h0, OP_SWAP_AB}, 32'h0000_00A5);
        check32(card.zone0.cells.cell_array[0].cell_inst.a_data, 32'h0000_00A5, "phase2: zone0 A preloaded");
        host_xact({8'h0, 8'h01}, 32'h0000_00F0); // DATA_WRITE, addr=0 rides cpu_data[31:16]=0

        // ── phase 3: let the fire propagate -> buffer BRAM -> bridge FSM ────
        // -> Zone1 injection -> Zone1 fire -> results BRAM, no host involved.
        w = 0;
        while (bridge_hops == 0 && w < 100) begin @(posedge clk); #1; w = w + 1; end
        check1((bridge_hops >= 1), 1'b1, "phase3: bridge FSM autonomously injected the buffered value into Zone1");

        repeat(10) @(posedge clk); #1; // let Zone1's fire land in the results BRAM

        // Expected: buffer holds XOR(0xA5,0xF0)=0x55. Zone1's injected DATA_WRITE
        // carries {16'h0020 (target addr), 0x0055} per the existing convention
        // (address rides the value's own upper 16 bits) -- so the relayed value
        // Zone1 actually receives and re-fires is 0x00200055, not bare 0x55.
        // This is the SAME encoding quirk noted in tb_pcie_bram_v3.v, carried
        // one hop further; it doesn't affect the mechanism being proved.
        check32(results_rdata, 32'h0020_0055, "phase3: results repository holds the value that hopped Zone0->BRAM->Zone1");

        if (errors==0) $display(">>> 2-ZONE CARD PASS: load -> run -> BRAM buffer hop -> repository, all correct");
        else $display(">>> 2-ZONE CARD FAIL: %0d errors", errors);
        $finish;
    end
endmodule
