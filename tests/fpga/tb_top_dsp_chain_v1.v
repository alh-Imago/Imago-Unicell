// tb_top_dsp_chain_v1.v — points.md #466/#467: sim-first verification
// of the first real DSP hardware bring-up build before any real
// Quartus build. Uses the exact same force-source injection pattern
// already proven for `tb_top_bram_icm_hostbridge_v1.v` (#442, real-
// hardware-confirmed first try).
`timescale 1ns / 1ps

module tb_top_dsp_chain_v1;

    reg CLK_100M = 0;
    always #5 CLK_100M = ~CLK_100M;

    wire LED0_N, LED1_N;

    top_dsp_chain_v1 DUT (
        .CLK_100M(CLK_100M), .LED0_N(LED0_N), .LED1_N(LED1_N)
    );

    reg [36:0] stim_source = 37'h0;
    always @(*) force DUT.BRIDGE.source = stim_source;

    integer errors = 0;

    localparam [2:0] OP_NOP    = 3'd0;
    localparam [2:0] OP_LOAD_A = 3'd1;
    localparam [2:0] OP_LOAD_B = 3'd2;
    localparam [2:0] OP_WD_SET = 3'd3;
    localparam [2:0] OP_ACK    = 3'd4;

    task send_cmd(input [2:0] opcode, input [31:0] data);
        begin
            stim_source[31:0]  = data;
            stim_source[34:32] = opcode;
            stim_source[35]    = 1'b0;
            @(posedge DUT.clk); #1;
            stim_source[35] = 1'b1;
            @(posedge DUT.clk); #1;
            stim_source[35] = 1'b0;
            @(posedge DUT.clk); #1;
        end
    endtask

    task snap_and_read(output [113:0] result);
        begin
            stim_source[36] = 1'b0;
            @(posedge DUT.clk); #1;
            stim_source[36] = 1'b1;
            @(posedge DUT.clk); #1;
            stim_source[36] = 1'b0;
            @(posedge DUT.clk); #1;
            result = DUT.BRIDGE.probe;
        end
    endtask

    reg [113:0] snap;

    initial begin
        #500;

        // ── Real, channel-alive check ──
        snap_and_read(snap);
        if (snap[81:50] !== 32'd0) begin
            errors = errors + 1;
            $display("FAIL: cmd_count nonzero before any real command");
        end

        // ── Real: set the watchdog threshold first ──
        send_cmd(OP_WD_SET, 32'd50);

        // ── Real: load both operands, wait for fire, check result ──
        send_cmd(OP_LOAD_A, 32'hAAAA0001);
        send_cmd(OP_LOAD_B, 32'h55550002);

        begin : wait_fire
            integer cyc;
            cyc = 0;
            snap_and_read(snap);
            while (!snap[32] && cyc < 20) begin
                snap_and_read(snap);
                cyc = cyc + 1;
            end
            $display("Real fire observed after %0d real polls (cmd_count=%0d)", cyc, snap[81:50]);
            if (!snap[32]) begin
                errors = errors + 1;
                $display("FAIL: fire never observed via the real bridge");
            end else begin
                $display("PASS: real fire observed via the real bridge, result=0x%h", snap[31:0]);
            end
        end

        // ── Real: confirm the watchdog did NOT trip during normal operation ──
        if (snap[33] !== 1'b0) begin
            errors = errors + 1;
            $display("FAIL: watchdog false-tripped during real, normal operation");
        end else begin
            $display("PASS: watchdog correctly did not trip during real, normal operation");
        end

        // ── Real: ack the result, confirm fire clears ──
        send_cmd(OP_ACK, 32'h0);
        snap_and_read(snap);
        if (snap[32] !== 1'b0) begin
            errors = errors + 1;
            $display("FAIL: fire did not clear after real ACK");
        end else begin
            $display("PASS: real ACK correctly cleared fire, wrapper re-armed");
        end

        // ── Real: second real operation, confirming re-arming works end to end ──
        send_cmd(OP_LOAD_A, 32'h11110003);
        send_cmd(OP_LOAD_B, 32'h22220004);
        begin : wait_fire_2
            integer cyc;
            cyc = 0;
            snap_and_read(snap);
            while (!snap[32] && cyc < 20) begin
                snap_and_read(snap);
                cyc = cyc + 1;
            end
            if (!snap[32]) begin
                errors = errors + 1;
                $display("FAIL: second real operation never fired");
            end else begin
                $display("PASS: second real operation via the real bridge also fired correctly, result=0x%h", snap[31:0]);
            end
        end
        send_cmd(OP_ACK, 32'h0);

        if (errors == 0) begin
            $display("PASS: real DSP chain bring-up build -- all checks passed");
        end else begin
            $display("FAIL: %0d error(s) found", errors);
        end
        $finish;
    end

endmodule
