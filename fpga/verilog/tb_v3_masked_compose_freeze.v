// tb_v3_masked_compose_freeze.v — tests CMD_FREEZE_AT/CMD_RELEASE_AT
// (points.md #63 follow-up, 2026-07-30) using exactly the test vehicle Alan
// proposed: build the proven masked-compose model (tb_v3_masked_compose.v),
// confirm it works, THEN freeze one contributing cell and refire -- a hole
// should appear in the composed data exactly where the frozen cell's nibble
// belongs, while the other three cells' contributions still land correctly.
//
// IMPORTANT, discovered building this test (not a bug -- a real property of
// command-emit cells worth remembering): cell4's fire drives its ENTIRE
// a_data onto cmd_emit_buf_bus (unicell64_v3.v line ~1420, `cmd_emit_buf_bus
// <= a_data`), and the array's emit-arbiter broadcasts that AS A REAL,
// EXECUTED COMMAND to every cell (cmd_opcode = a_data[7:0]). The first
// version of this test used 0x00001234 as an arbitrary "data" value; its low
// byte (0x34=52) happens to equal CMD_TOPO_NOR_COLD (armed=0), silently
// disarming EVERY cell in the array the moment cell4 fired it. This is
// exactly what command-emit cells are FOR (composing and broadcasting real
// commands), not a defect -- but it means test values must be chosen so
// their low byte doesn't collide with a real opcode, or the test measures
// the wrong thing entirely. Fixed here by keeping nibble0 (the byte's low
// nibble) at 0 and choosing nibble1 values whose combination with it stays
// outside the real opcode range (0-71) or lands exactly on CMD_NONE (0).
//
// Round 1: all 4 source cells active, compose a safe word, confirm it works.
// Freeze cell1 (owns nibble1, bits[7:4]) via CMD_FREEZE_AT -- TARGETED, so
//          cells 0/2/3 and cell4 (command-emit) are unaffected.
// Round 2: refire with a NEW safe value -- cell1 (frozen) contributes
//          NOTHING; expect a hole at nibble1, other three nibbles present.
// Release cell1 (CMD_RELEASE_AT), round 3: refire once more to confirm
//          cell1 rejoins cleanly -- full circle, proves CMD_RELEASE_AT too.
`timescale 1ns/1ps
module tb_v3_masked_compose_freeze;
    reg clk=0, rst=0;
    reg [31:0] cmd_bus=0, cmd_data=0; reg cmd_valid=0;
    reg [15:0] inj_addr=0; reg [31:0] inj_data=0; reg inj_valid=0;
    always #5 clk=~clk;

    wire [15:0] out_addr; wire [31:0] out_data; wire out_valid;

    unicell_array64_v3 #(.NUM_CELLS(5), .CELL_BASE(0)) arr (
        .clk(clk), .rst(rst),
        .cmd_bus(cmd_bus), .cmd_data(cmd_data), .cmd_valid(cmd_valid),
        .cpu_addr(inj_addr), .cpu_data(inj_data), .cpu_valid(inj_valid),
        .out_addr(out_addr), .out_data(out_data), .out_valid(out_valid),
        .out_routing(), .out_transit(),
        .obs_bus_valid(), .obs_bus_addr(), .obs_bus_data(),
        .armed_count(), .arrived_count(), .output_set_count(), .emit_count(),
        .dbg0_cmd_latch(), .dbg0_input_addr(), .dbg0_output_addr(), .dbg0_a_data(),
        .cycle_count()
    );

    integer errors=0;
    task check32; input [31:0] got, want; input [255:0] msg; begin
        if (got===want) $display("  PASS: %0s (0x%08h)", msg, got);
        else begin $display("  FAIL: %0s got=0x%08h want=0x%08h", msg, got, want); errors=errors+1; end
    end endtask
    task check1; input got, want; input [255:0] msg; begin
        if (got===want) $display("  PASS: %0s (%b)", msg, got);
        else begin $display("  FAIL: %0s got=%b want=%b", msg, got, want); errors=errors+1; end
    end endtask

    localparam [7:0] OP_SET_IN_ADDR  = 8'd2;
    localparam [7:0] OP_SET_OUT_ADDR = 8'd3;
    localparam [7:0] OP_RECONFIGURE  = 8'd4;
    localparam [7:0] OP_BOOT_COMMIT  = 8'd7;
    localparam [7:0] OP_METH_SET_MASK = 8'd30;
    localparam [7:0] OP_LOAD_AT      = 8'd23;
    localparam [7:0] OP_FREEZE_AT    = 8'd39;
    localparam [7:0] OP_RELEASE_AT   = 8'd40;

    localparam [15:0] TRIG_ADDR = 16'h0010;
    localparam [15:0] CMD_ADDR  = 16'h0020;

    task boot_all; begin
        @(negedge clk); cmd_bus={8'h0,OP_BOOT_COMMIT}; cmd_data={16'h0, TRIG_ADDR}; cmd_valid=1'b1;
        @(posedge clk); #1; cmd_valid=1'b0; repeat(2) @(posedge clk); #1;
    end endtask

    task hold_target; input [15:0] target; begin
        @(negedge clk); inj_addr=target; inj_data=32'h0; inj_valid=1'b1;
        @(posedge clk); #1; inj_valid=1'b0; repeat(2) @(posedge clk); #1;
    end endtask

    task retarget_cell4; begin
        hold_target(16'd4);
        @(negedge clk); cmd_bus={8'h0,OP_SET_IN_ADDR}; cmd_data={16'h0, CMD_ADDR}; cmd_valid=1'b1;
        @(posedge clk); #1; cmd_valid=1'b0; repeat(2) @(posedge clk); #1;
    end endtask

    task config_source_common; begin
        @(negedge clk); cmd_bus={8'h0,OP_RECONFIGURE}; cmd_data = 32'h0000_082C; cmd_valid=1'b1;
        @(posedge clk); #1; cmd_valid=1'b0; repeat(2) @(posedge clk); #1;
    end endtask

    task set_output_addr; input [2:0] cell_id; input [15:0] addr; begin
        hold_target({13'h0, cell_id});
        @(negedge clk); cmd_bus={8'h0,OP_SET_OUT_ADDR}; cmd_data={16'h0, addr}; cmd_valid=1'b1;
        @(posedge clk); #1; cmd_valid=1'b0; repeat(2) @(posedge clk); #1;
    end endtask

    task set_nibble_mask; input [2:0] cell_id; input [7:0] mask; begin
        hold_target({13'h0, cell_id});
        @(negedge clk); cmd_bus={8'h0,OP_METH_SET_MASK}; cmd_data={24'h0, mask}; cmd_valid=1'b1;
        @(posedge clk); #1; cmd_valid=1'b0; repeat(2) @(posedge clk); #1;
    end endtask

    task config_cell4_emit; begin
        hold_target(16'd4);
        @(negedge clk); cmd_bus={8'h0,OP_LOAD_AT}; cmd_data = 32'h0000_0C00; cmd_valid=1'b1;
        @(posedge clk); #1; cmd_valid=1'b0; repeat(2) @(posedge clk); #1;
    end endtask

    // TARGETED freeze/release -- the new opcodes under test.
    task freeze_cell; input [2:0] cell_id; begin
        hold_target({13'h0, cell_id});
        @(negedge clk); cmd_bus={8'h0,OP_FREEZE_AT}; cmd_data=32'h0; cmd_valid=1'b1;
        @(posedge clk); #1; cmd_valid=1'b0; repeat(2) @(posedge clk); #1;
    end endtask
    task release_cell; input [2:0] cell_id; begin
        hold_target({13'h0, cell_id});
        @(negedge clk); cmd_bus={8'h0,OP_RELEASE_AT}; cmd_data=32'h0; cmd_valid=1'b1;
        @(posedge clk); #1; cmd_valid=1'b0; repeat(2) @(posedge clk); #1;
    end endtask

    task prime_sources; begin
        @(negedge clk); inj_addr=TRIG_ADDR; inj_data=32'h0; inj_valid=1'b1;
        @(posedge clk); #1; inj_valid=1'b0; repeat(2) @(posedge clk); #1;
    end endtask

    task fire_sources; input [31:0] value; begin
        @(negedge clk); inj_addr=TRIG_ADDR; inj_data=value; inj_valid=1'b1;
        @(posedge clk); #1; inj_valid=1'b0;
    end endtask

    // NOTE: cell4's fire drives its WHOLE a_data onto the command bus as a
    // REAL command (cmd_opcode = a_data[7:0]) -- this trigger word's low
    // byte must stay safely outside the real opcode range (0-71) or land
    // exactly on CMD_NONE(0), or it will (correctly, by design) reconfigure
    // every cell in the array. 0xBEEF's low byte is 0xEF=239 -- safe.
    task fire_cell4; begin
        @(negedge clk); inj_addr=CMD_ADDR; inj_data=32'h0000_BEEF; inj_valid=1'b1;
        @(posedge clk); #1; inj_valid=1'b0;
    end endtask

    // Watches for cell4's emit pulse (single cycle) and returns the word.
    task watch_emit; output [31:0] word; output got; begin
        integer k;
        got=1'b0; word=32'h0;
        for (k=0;k<20;k=k+1) begin
            if (arr.cell_emit_valid[4]) begin got=1'b1; word=arr.cell_emit_bus[4]; end
            @(posedge clk); #1;
        end
    end endtask

    reg [31:0] emit_word; reg saw_emit;

    initial begin
        rst=1; repeat(4) @(posedge clk); #1; rst=0; repeat(2) @(posedge clk); #1;
        $display("=== CMD_FREEZE_AT / CMD_RELEASE_AT: freeze one contributor, look for the hole ===");

        boot_all;
        retarget_cell4;
        set_output_addr(3'd0, CMD_ADDR);
        set_output_addr(3'd1, CMD_ADDR);
        set_output_addr(3'd2, CMD_ADDR);
        set_output_addr(3'd3, CMD_ADDR);
        set_nibble_mask(3'd0, 8'b1111_1110);  // nibble0 (bits3:0)
        set_nibble_mask(3'd1, 8'b1111_1101);  // nibble1 (bits7:4) -- cell1, the one we'll freeze
        set_nibble_mask(3'd2, 8'b1111_1011);  // nibble2 (bits11:8)
        set_nibble_mask(3'd3, 8'b1111_0111);  // nibble3 (bits15:12)
        config_source_common;
        config_cell4_emit;

        // ---- ROUND 1: confirm the model works ----
        // Value 0x0056F0: nibble0=0(cell0, kept 0 for opcode safety),
        // nibble1=F(cell1 -- will show a hole when frozen), nibble2=6,
        // nibble3=5. Low byte = 0xF0 = 240, well outside the real opcode
        // range (0-71) -- safe when cell4 fires this as a command.
        $display("--- ROUND 1: baseline, all 4 cells active ---");
        prime_sources;
        fire_sources(32'h0000_56F0);
        repeat(10) @(posedge clk); #1;
        $display("  composed: a_data=0x%08h a_arrived=%b", arr.cell_adata[4], arr.cell_arrived[4]);
        check32(arr.cell_adata[4], 32'h0000_56F0, "ROUND1: composed word correct, all 4 nibbles present");

        fire_cell4;
        watch_emit(emit_word, saw_emit);
        check1(saw_emit, 1'b1, "ROUND1: cell4 emitted");
        check32(emit_word, 32'h0000_56F0, "ROUND1: emitted word correct");

        // ---- FREEZE cell1 (targeted) ----
        $display("--- Freezing cell1 (targeted, CMD_FREEZE_AT) ---");
        freeze_cell(3'd1);
        check1(arr.cell_array[1].cell_inst.frozen, 1'b1, "cell1 is frozen");
        check1(arr.cell_array[0].cell_inst.frozen, 1'b0, "cell0 UNAFFECTED -- targeted, not broadcast");
        check1(arr.cell_array[2].cell_inst.frozen, 1'b0, "cell2 UNAFFECTED");
        check1(arr.cell_array[3].cell_inst.frozen, 1'b0, "cell3 UNAFFECTED");
        check1(arr.cell_array[4].cell_inst.frozen, 1'b0, "cell4 (command-emit) UNAFFECTED");

        // ---- ROUND 2: refire with a NEW value -- expect a hole at nibble1 ----
        // 0x00009300: nibble0=0, nibble1=HOLE(cell1 frozen, contributes
        // nothing), nibble2=3, nibble3=9. Low byte = 0x00 = CMD_NONE -- safe.
        $display("--- ROUND 2: cell1 frozen, refire -- expect a hole at nibble1 ---");
        prime_sources;   // cell1 won't respond (frozen); cells 0/2/3 re-arm normally
        fire_sources(32'h0000_9300);
        repeat(10) @(posedge clk); #1;
        $display("  composed: a_data=0x%08h a_arrived=%b", arr.cell_adata[4], arr.cell_arrived[4]);
        check32(arr.cell_adata[4], 32'h0000_9300, "ROUND2: hole at nibble1 -- cell1's contribution missing, others present");

        fire_cell4;
        watch_emit(emit_word, saw_emit);
        check1(saw_emit, 1'b1, "ROUND2: cell4 emitted");
        check32(emit_word, 32'h0000_9300, "ROUND2: emitted word shows the hole too");

        // ---- RELEASE cell1, ROUND 3: confirm it rejoins cleanly ----
        // 0x0027A0: nibble0=0, nibble1=A(cell1 rejoined, nonzero again),
        // nibble2=7, nibble3=2. Low byte = 0xA0 = 160 -- safe.
        $display("--- Releasing cell1 (CMD_RELEASE_AT), ROUND 3: refire -- confirm rejoin ---");
        release_cell(3'd1);
        check1(arr.cell_array[1].cell_inst.frozen, 1'b0, "cell1 un-frozen");

        prime_sources;
        fire_sources(32'h0000_27A0);
        repeat(10) @(posedge clk); #1;
        $display("  composed: a_data=0x%08h a_arrived=%b", arr.cell_adata[4], arr.cell_arrived[4]);
        check32(arr.cell_adata[4], 32'h0000_27A0, "ROUND3: cell1 rejoined cleanly -- no hole, full word composed");

        if (errors==0) $display(">>> FREEZE_AT PASS: targeted freeze produces exactly the hole predicted, targeted release restores it cleanly");
        else           $display(">>> FREEZE_AT FAIL: %0d errors", errors);
        $finish;
    end
endmodule
