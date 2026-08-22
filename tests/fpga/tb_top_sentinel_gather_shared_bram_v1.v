// tb_top_sentinel_gather_shared_bram_v1.v — sim-first verification of
// top_sentinel_gather_shared_bram_v1.v before Quartus. Drives CLK_100M only, runs
// the fully autonomous self-test to completion, checks LED1_N never
// lights (active-low error).
`timescale 1ns / 1ps

module tb;
    reg clk = 0;
    always #5 clk = ~clk;   // 100 MHz

    wire led0_n, led1_n;

    top_sentinel_gather_shared_bram_v1 DUT (
        .CLK_100M(clk),
        .LED0_N(led0_n),
        .LED1_N(led1_n)
    );

    integer i;
    integer error_seen;
    reg [5:0] last_state = 6'd63;
    integer print_budget;
    reg h2rdy_prev = 0;
    reg [15:0] cyc2 = 0;
    integer h2_feed_count = 0;
    integer h2_ack_count = 0;
    always @(posedge DUT.clk) begin
        cyc2 <= cyc2 + 1;
        if (cyc2 < 50) begin
            $display("[EARLY] cyc=%0d st=%0d ac1=%0d ac1adv=%b sharedrdv=%b sharedrd=%0d readowner=%0d cmdvalid=%b cmdop=%b cmdaddr=%0d",
                cyc2, DUT.state, DUT.ac1_addr, DUT.ac1_advance_en, DUT.shared_rdata_valid,
                DUT.shared_rdata, DUT.read_owner, DUT.shared_cmd_valid, DUT.bram_cmd_op, DUT.shared_cmd_addr);
        end
        if (DUT.col_program_done) begin
            $display("[PROGDONE] t=%0t st=%0d seqidx=%0d round=%0d ac1=%0d ac2=%0d ac3=%0d",
                $time, DUT.state, DUT.seq_index, DUT.round_idx, DUT.ac1_addr, DUT.ac2_addr, DUT.ac3_addr);
        end
        if (DUT.h2_out_wrap_pulse) begin
            $display("[H2 WRAP-ACTUAL] t=%0t ac2=%0d ac2adv=%b", $time, DUT.ac2_addr, DUT.ac2_advance_en);
        end
        if (DUT.h2_arrived_n) begin
            h2_feed_count = h2_feed_count + 1;
            $display("[H2 FEED #%0d] cyc=%0d ac2addr_used=%0d", h2_feed_count, cyc2, DUT.shared_cmd_addr);
        end
        if (DUT.h2_ack_in_n) begin
            h2_ack_count = h2_ack_count + 1;
            $display("[H2 ACK #%0d] cyc=%0d", h2_ack_count, cyc2);
        end
        if (cyc2 > 125 && cyc2 < 140) begin
            $display("[DIFF TRACE] cyc=%0d feed=%b collect=%b diff=%0d ack=%b arr=%b",
                cyc2, DUT.SENT2.feed_pulse, DUT.SENT2.collect_pulse, DUT.SENT2.diff,
                DUT.h2_ack_in_n, DUT.h2_arrived_n);
        end
        if (DUT.h2_err) begin
            $display("[H2 ERR] t=%0t h2err=%b diffval=%0d", $time, DUT.h2_err, DUT.SENT2.diff);
        end
        if (DUT.h2_freeze_out || DUT.h2_results_ready) begin
            $display("[H2 FREEZE CHECK] t=%0t h2freezeout=%b h2resultsready=%b h2needdata=%b",
                $time, DUT.h2_freeze_out, DUT.h2_results_ready, DUT.h2_need_data);
        end
        if (DUT.shared_read_trigger) begin
            $display("[SHARED READ TRIG] t=%0t seqidx=%0d h2froz=%b thischainfroz=%b addr=%0d",
                $time, DUT.seq_index, DUT.h2_freeze_out, DUT.this_chain_frozen, DUT.shared_read_addr);
        end
        if (DUT.h2_ack_in_n) begin
            $display("[H2 ACK] t=%0t ac2_addr(before adv)=%0d h2acc=%0d", $time, DUT.ac2_addr, DUT.H2.CORE_ACC.accumulator);
        end
        if (DUT.h2_out_wrap_pulse) begin
            $display("[H2 WRAP] t=%0t ac2_addr=%0d h2acc=%0d", $time, DUT.ac2_addr, DUT.H2.CORE_ACC.accumulator);
        end
        if (DUT.h2_ready_in_n !== h2rdy_prev || DUT.col_program_done) begin
            $display("[h2rdy edge] t=%0t h2rdy=%b h2fire=%b h2dv=%b h2pend=%0d h2ack=%b colpend=%0d progdone=%b actidx=%0d fired=%b seqidx=%0d",
                $time, DUT.h2_ready_in_n, DUT.h2_fire_n, DUT.H2.CORE_ACC.data_valid,
                DUT.H2.CORE_ACC.pending_ack, DUT.h2_ack_in_n, DUT.COLLECTOR.CORE_NANO.pending_ack,
                DUT.col_program_done, DUT.active_dir_idx, DUT.fired_this_round, DUT.seq_index);
            h2rdy_prev <= DUT.h2_ready_in_n;
        end
        if (DUT.state !== last_state) begin
            $display("h2addr=%0d h2acc=%0d h2rdy=%b h2ack=%b h2freeze=%b h2wrap=%b ac2=%0d h2fire=%b h2dv=%b h2pend=%0d colpend=%0d",
                DUT.shared_cmd_addr, DUT.H2.CORE_ACC.accumulator, DUT.h2_ready_in_n,
                DUT.h2_ack_in_n, DUT.h2_freeze_out, DUT.h2_out_wrap_pulse, DUT.ac2_addr,
                DUT.h2_fire_n, DUT.H2.CORE_ACC.data_valid, DUT.H2.CORE_ACC.pending_ack,
                DUT.COLLECTOR.CORE_NANO.pending_ack);
            $display("t=%0t state=%0d round=%0d seq_index=%0d q_out=%0d h1_wrap=%b h2_wrap=%b h3_wrap=%b h1_safe=%b h2_safe=%b h3_safe=%b err=%b",
                $time, DUT.state, DUT.round_idx, DUT.seq_index, DUT.q_data_out_n,
                DUT.h1_out_wrap_pulse, DUT.h2_out_wrap_pulse, DUT.h3_out_wrap_pulse,
                DUT.h1_safe, DUT.h2_safe, DUT.h3_safe, DUT.err_sticky);
            last_state <= DUT.state;
        end
    end

    initial begin
        print_budget = 0;
        error_seen = 0;
        for (i = 0; i < 30000; i = i + 1) begin
            @(posedge clk);
            if (led1_n === 1'b0) error_seen = 1;
        end

        if (DUT.state !== DUT.S_DONE) begin
            $display("FAIL: FSM never reached S_DONE (stuck at state=%0d)", DUT.state);
            error_seen = 1;
        end else begin
            $display("PASS: FSM reached S_DONE");
        end

        if (error_seen) begin
            $display("FAIL: err_sticky / LED1_N indicated a real error at some point");
        end else begin
            $display("PASS: zero errors across the full self-test sequence");
        end

        $display("Final err_sticky = %b", DUT.err_sticky);
        $finish;
    end
endmodule
