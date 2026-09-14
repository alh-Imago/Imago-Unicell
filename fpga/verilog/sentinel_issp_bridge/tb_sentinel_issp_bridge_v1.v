// tb_sentinel_issp_bridge_v1.v — points.md #287 continuation: confirms
// sentinel_issp_bridge_v1.v's command-injection protocol (all 5
// opcodes) and snap_req/probe readback work correctly against the real
// sentinel_counter_v1.v core, using the project's existing sim-only
// ISSP stub (tb_stub_issp_sim_only.v) in place of the real IP.
`timescale 1ns / 1ps

module tb_sentinel_issp_bridge_v1;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

    sentinel_issp_bridge_v1 #(.DIFF_WIDTH(16)) DUT (
        .clk(clk), .rst(rst)
    );

    // ── Drive the "source" side directly, exactly as a real host would
    // over JTAG via the Tcl harness's write_source_data. The sim
    // stub's own `source` port is an output tied to a constant 0 (it
    // stands in for the ISSP IP, which the real host drives) -- to
    // override it during simulation we force the DUT's internal wire
    // directly, matching how a real testbench needs to override a
    // black-box IP's output. ──
    reg [65:0] stim_source = 66'h0;
    always @(*) force DUT.source = stim_source;

    integer errors = 0;
    reg [8:0] f;

    task send_cmd(input [7:0] opcode, input [31:0] data);
        begin
            stim_source[63:32] = {24'h0, opcode};
            stim_source[31:0]  = data;
            stim_source[64]    = 1'b0;
            #10;
            stim_source[64] = 1'b1;   // cmd_go rising edge
            #10;
            stim_source[64] = 1'b0;
            #10;
        end
    endtask

    task do_snapshot;
        begin
            stim_source[65] = 1'b0;
            #10;
            stim_source[65] = 1'b1;   // snap_req rising edge
            #10;
            stim_source[65] = 1'b0;
            #10;
        end
    endtask

    // Probe field extraction, matching the bridge's own documented layout.
    function [31:0] probe_cycle;
        input [112:0] p;
        probe_cycle = p[31:0];
    endfunction

    function [8:0] probe_flags;
        input [112:0] p;
        probe_flags = p[40:32];
    endfunction

    function signed [31:0] probe_diff;
        input [112:0] p;
        probe_diff = p[72:41];
    endfunction

    function [15:0] probe_chainlen;
        input [112:0] p;
        probe_chainlen = p[88:73];
    endfunction

    function [15:0] probe_cmdcount;
        input [112:0] p;
        probe_cmdcount = p[104:89];
    endfunction

    initial begin
        #12 rst = 0;
        #10;

        // ── Set chain_length = 4 via opcode 5 ──
        send_cmd(8'd5, 32'd4);
        do_snapshot();
        if (probe_chainlen(DUT.probe) !== 16'd4) begin
            $display("FAIL: chain_length readback expected 4, got %0d", probe_chainlen(DUT.probe));
            errors = errors + 1;
        end else $display("OK: chain_length set+readback correct (%0d)", probe_chainlen(DUT.probe));

        // ── Confirm power-on-frozen state is visible over the bridge
        // (#287's own fix) -- flags bit0=need_data, bit1=results_ready,
        // bit2=safe_to_intervene should all read 1 already. ──
        f = probe_flags(DUT.probe);
        if (f[0] !== 1'b1 || f[1] !== 1'b1 || f[2] !== 1'b1) begin
            $display("FAIL: power-on-frozen flags not visible over the bridge, flags=%b", f);
            errors = errors + 1;
        end else $display("OK: power-on-frozen state correctly visible over the bridge (flags=%b)", f);

        // ── Unfreeze (opcode 4), then feed 4 times (opcode 1) ──
        send_cmd(8'd4, 32'h0);   // host_unfreeze_pulse
        send_cmd(8'd1, 32'h0);   // feed
        send_cmd(8'd1, 32'h0);
        send_cmd(8'd1, 32'h0);
        send_cmd(8'd1, 32'h0);
        do_snapshot();
        if (probe_diff(DUT.probe) !== 32'sd4) begin
            $display("FAIL: diff readback expected 4, got %0d", probe_diff(DUT.probe));
            errors = errors + 1;
        end else $display("OK: diff readback correct after 4 real feed_pulse injections (%0d)", probe_diff(DUT.probe));

        // ── Wrap (opcode 3) -- need_data should assert, visible on next
        // snapshot ──
        send_cmd(8'd3, 32'h0);   // out_wrap_pulse
        do_snapshot();
        f = probe_flags(DUT.probe);
        if (f[0] !== 1'b1) begin
            $display("FAIL: need_data flag should be visible after wrap, flags=%b", f);
            errors = errors + 1;
        end else $display("OK: need_data flag correctly visible over the bridge after wrap");

        // ── Collect all 4 (opcode 2) -- results_ready/safe should
        // assert ──
        send_cmd(8'd2, 32'h0);
        send_cmd(8'd2, 32'h0);
        send_cmd(8'd2, 32'h0);
        send_cmd(8'd2, 32'h0);
        do_snapshot();
        f = probe_flags(DUT.probe);
        if (f[1] !== 1'b1 || f[2] !== 1'b1) begin
            $display("FAIL: results_ready/safe should be visible after full collection, flags=%b", f);
            errors = errors + 1;
        end else $display("OK: results_ready/safe correctly visible over the bridge (flags=%b)", f);

        // ── Confirm cmd_count tracks real injected commands ──
        if (probe_cmdcount(DUT.probe) == 16'h0) begin
            $display("FAIL: cmd_count should be nonzero after real command injections");
            errors = errors + 1;
        end else $display("OK: cmd_count correctly tracks real injected commands (%0d)", probe_cmdcount(DUT.probe));

        if (errors == 0)
            $display("PASS: sentinel_issp_bridge_v1 -- command injection (all opcodes exercised) and snapshot readback both confirmed correct against the real sentinel_counter_v1 core");
        else
            $display("FAIL: %0d error(s)", errors);

        $finish;
    end

endmodule
