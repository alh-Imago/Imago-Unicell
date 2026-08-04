`timescale 1ns/1ps
// tb_freeze_loop_v3.v -- Alan's framing: CMD_FREEZE was designed for
// programming/error-state use, not mid-computation stalling, and the real
// risk shows up in a LOOP GROUP: freeze a self-referencing dut (loop_back)
// at different phase offsets relative to its own trigger timing and see if
// the accumulator's state changes/corrupts depending on exactly when you
// freeze.
//
// ONE dut, CELL_ID=0, topology=XOR (hot/armed) + latch_in + loop_back.
// This makes it a running XOR accumulator: each external trigger B_k does
//   a_data_(k) = a_data_(k-1) XOR B_k
// which is easy to predict by hand (a running XOR-fold), unlike a 3-dut
// chain -- and it needs only ONE bus_addr line (no auto-forward wiring
// fighting with command-targeting, which is what broke the earlier 3-dut
// chain attempt: two always-blocks driving the same reg).
//
// cmd_data = 0x0042_08BC: same proven topology/start_flag/latch_in payload
// as tb_zone_scoped_freeze_v3.v (0x0002_08BC), OR'd with bit22 (loop_back,
// cmd_latch[31]<=cmd_data[22] -> upper halfword bit6 -> 0x0040).

module tb_freeze_loop_v3;
    reg clk=0, rst=0;
    always #5 clk=~clk;

    reg  [15:0] bus_addr=0; reg [31:0] bus_data=0; reg bus_valid=0;
    reg  [31:0] cmd_bus=0, cmd_data=0; reg cmd_valid=0;
    wire [31:0] out_addr, out_data; wire out_valid;

    unicell64_v3 #(.CELL_ID(16'h0000)) dut (
        .clk(clk), .rst(rst),
        .cmd_bus(cmd_bus), .cmd_data(cmd_data), .cmd_valid(cmd_valid),
        .bus_addr(bus_addr), .bus_data(bus_data), .bus_valid(bus_valid),
        .out_addr(out_addr), .out_data(out_data), .out_valid(out_valid),
        .cmd_emit_bus(), .cmd_emit_data(), .cmd_emit_valid(), .dbg_cmd_latch()
    );

    integer errors=0;
    task check; input got; input want; input [511:0] msg; begin
        if (got===want) $display("  PASS: %0s", msg);
        else begin $display("  FAIL: %0s got=%0d want=%0d", msg, got, want); errors=errors+1; end
    end endtask
    task checkhex; input [31:0] got; input [31:0] want; input [511:0] msg; begin
        if (got===want) $display("  PASS: %0s (0x%08x)", msg, got);
        else begin $display("  FAIL: %0s got=0x%08x want=0x%08x", msg, got, want); errors=errors+1; end
    end endtask

    // one bus arrival, own address, no settle needed (single dut, always addr=0)
    task trig; input [31:0] d; begin
        @(negedge clk); bus_addr=16'h0000; bus_data=d; bus_valid=1'b1;
        @(posedge clk); #1; bus_valid=1'b0;
    end endtask

    task freeze_now; begin
        @(negedge clk); cmd_bus={8'h0,8'd5}; cmd_data=32'h0; cmd_valid=1'b1;
        @(posedge clk); #1; cmd_valid=1'b0;
    end endtask
    task release_now; begin
        @(negedge clk); cmd_bus={8'h0,8'd6}; cmd_data=32'h0; cmd_valid=1'b1;
        @(posedge clk); #1; cmd_valid=1'b0;
    end endtask

    // track fires -- accumulator model computed in parallel for comparison
    reg [31:0] acc;             // testbench's own predicted accumulator
    reg [31:0] last_out;
    integer fire_count;
    always @(posedge clk) if (out_valid) begin last_out<=out_data; fire_count<=fire_count+1; end

    initial begin
        rst=1; repeat(4) @(posedge clk); #1; rst=0; repeat(4) @(posedge clk); #1;
        fire_count=0;
        $display("=== FREEZE-LOOP: freeze a loop_back accumulator at different phase offsets ===");

        // arm: topology=XOR(hot,0x0BC) + start_flag + latch_in (NO loop_back
        // yet -- see below for why it can't go in this first LOAD_AT).
        @(negedge clk); bus_addr=16'h0000;
        @(posedge clk); #1; // settle (not strictly needed, addr already 0, but consistent practice)
        @(negedge clk); cmd_bus={8'h0,8'd23}; cmd_data=32'h0002_08BC; cmd_valid=1'b1;
        @(posedge clk); #1; cmd_valid=1'b0;
        repeat(4) @(posedge clk); #1;

        // BOOT_COMMIT to exit physical_mode. Necessary because loop_back
        // lives at cmd_data[22], which falls INSIDE cmd_data[30:20] --
        // the exact range CMD_LOAD_AT also writes to auth_mask while
        // physical_mode=1 (boot state, see unicell64_v3.v CMD_LOAD_AT case:
        // "if (physical_mode) cmd_latch[63:53] <= cmd_data[30:20]"). Setting
        // loop_back in the SAME LOAD_AT that's still in physical_mode would
        // silently corrupt auth_mask to a non-zero value, which then breaks
        // auth_ok (auth_boot = auth_mask==0) for every later command
        // including CMD_FREEZE -- this is exactly what happened on the
        // first attempt at this test (auth_mask came out 0x004, frozen
        // never asserted). BOOT_COMMIT with cmd_data=0 keeps auth_mask=0
        // and flips physical_mode off, so a SECOND LOAD_AT can add
        // loop_back without touching the (now-inactive) auth-write branch.
        @(negedge clk); cmd_bus={8'h0,8'd7}; cmd_data=32'h0; cmd_valid=1'b1;
        @(posedge clk); #1; cmd_valid=1'b0;
        repeat(4) @(posedge clk); #1;
        check(dut.physical_mode, 1'b0, "BOOT_COMMIT: exited physical_mode (RUN state)");
        check(dut.auth_mask, 11'h0, "BOOT_COMMIT: auth_mask still 0");

        // second LOAD_AT: now add loop_back (bit22) safely -- physical_mode
        // is 0, so the auth-write branch is skipped, auth_mask stays clean.
        @(negedge clk); cmd_bus={8'h0,8'd23}; cmd_data=32'h0042_08BC; cmd_valid=1'b1;
        @(posedge clk); #1; cmd_valid=1'b0;
        repeat(4) @(posedge clk); #1;
        check(dut.auth_mask, 11'h0, "second LOAD_AT: auth_mask STILL 0 (not corrupted this time)");
        check(dut.cmd_latch[9:0]===10'h0BC, 1'b1, "armed: topology=XOR");
        check(dut.cmd_latch[26], 1'b1, "armed: latch_in set");
        check(dut.cmd_latch[31], 1'b1, "armed: loop_back set");

        // prime (first arrival: sets a_data=A0, a_arrived=1, no fire)
        trig(32'hAAAA0001);
        repeat(4) @(posedge clk); #1;
        acc = 32'hAAAA0001;
        check(dut.a_arrived, 1'b1, "primed: a_arrived set");
        checkhex(dut.a_data, acc, "primed: a_data == A0");

        // ── baseline: two clean triggers, no freeze, confirm accumulator math ──
        trig(32'h11110001);
        repeat(4) @(posedge clk); #1;
        acc = acc ^ 32'h11110001;
        checkhex(last_out, acc, "trigger1 (no freeze): accumulator correct");
        checkhex(dut.a_data, acc, "trigger1 (no freeze): a_data (loop_back) updated correctly");

        trig(32'h22220002);
        repeat(4) @(posedge clk); #1;
        acc = acc ^ 32'h22220002;
        checkhex(last_out, acc, "trigger2 (no freeze): accumulator correct");

        // ── PHASE A: freeze well BEFORE the next trigger, plenty of settle ──
        freeze_now();
        repeat(3) @(posedge clk); #1;
        check(dut.frozen, 1'b1, "phase A: frozen (well before trigger)");
        begin : phaseA
            reg [31:0] acc_before; reg [31:0] fc_before;
            acc_before = dut.a_data; fc_before = fire_count;
            trig(32'hDEAD0003);   // attempted trigger WHILE frozen
            repeat(3) @(posedge clk); #1;
            checkhex(dut.a_data, acc_before, "phase A: a_data UNCHANGED by frozen attempt");
            check(fire_count, fc_before, "phase A: no new fire while frozen");
        end
        release_now();
        repeat(4) @(posedge clk); #1;
        check(dut.frozen, 1'b0, "phase A: released");
        // resume: next trigger should continue from the PRE-FREEZE accumulator,
        // NOT incorporate the dropped DEAD0003 attempt
        trig(32'h33330003);
        repeat(4) @(posedge clk); #1;
        acc = acc ^ 32'h33330003;   // dropped trigger contributes nothing
        checkhex(last_out, acc, "phase A resume: accumulator correct (dropped trigger truly gone, not corrupting)");

        // ── PHASE B: freeze issued in the SAME immediate window as a trigger
        // (adjacent cycles, minimal gap) -- tests the registration-boundary
        // case Alan is specifically flagging: does timing-dependent overlap
        // between the freeze command and an in-flight trigger produce a
        // DIFFERENT (corrupted) result than phase A's well-separated freeze.
        begin : phaseB
            reg [31:0] acc_before; reg [31:0] fc_before;
            acc_before = dut.a_data; fc_before = fire_count;
            // issue freeze and the next trigger back-to-back, minimal gap
            freeze_now();
            trig(32'hBEEF0004);   // attempted immediately after freeze, same cadence
            repeat(3) @(posedge clk); #1;
            checkhex(dut.a_data, acc_before, "phase B: a_data UNCHANGED (freeze+trigger issued back-to-back)");
            check(fire_count, fc_before, "phase B: no new fire (freeze+trigger issued back-to-back)");
        end
        release_now();
        repeat(4) @(posedge clk); #1;
        trig(32'h44440004);
        repeat(4) @(posedge clk); #1;
        acc = acc ^ 32'h44440004;
        checkhex(last_out, acc, "phase B resume: accumulator correct -- SAME behavior as phase A, no phase-dependent corruption");

        if (errors==0) $display("\n>>> FREEZE-LOOP PASS: freeze cleanly skips in-flight triggers regardless of timing phase, accumulator never corrupts");
        else           $display("\n>>> FREEZE-LOOP FAIL: %0d errors -- phase-dependent corruption found, this is the exact hazard Alan flagged", errors);
        $finish;
    end
endmodule
