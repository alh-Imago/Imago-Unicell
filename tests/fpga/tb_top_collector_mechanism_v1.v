// tb_top_collector_mechanism_v1.v — sim-first verification of
// top_collector_mechanism_v1.v (points.md #403/#404) before it goes
// anywhere near Quartus. Drives CLK_100M only, runs the fully
// autonomous self-test FSM to completion, checks LED1_N never lights
// (active-low error) and that the design actually reaches S_DONE (not
// stuck). The per-cycle diagnostic trace (state/seq_index/queue/
// collector/header signals) is kept permanently, not stripped after
// debugging -- it was what actually found all five real bugs #404
// documents, and is exactly the kind of trace worth having on hand
// again for any future change to this mechanism.
`timescale 1ns / 1ps

module tb;
    reg clk = 0;
    always #5 clk = ~clk;   // 100 MHz

    wire led0_n, led1_n;

    top_collector_mechanism_v1 DUT (
        .CLK_100M(clk),
        .LED0_N(led0_n),
        .LED1_N(led1_n)
    );

    integer i;
    integer error_seen;
    reg [5:0] last_state = 6'd63;
    always @(posedge DUT.clk) begin
        if (DUT.state !== last_state) begin
            $display("t=%0t state=%0d seq_index=%0d q_reg=%0d q_valid=%b q_pend=%0d q_ackn=%b col_edge=%0d col_pend=%0d fire=%b err=%b h1data=%0d h2data=%0d h1rdy=%b h2rdy=%b actidx=%0d actvld=%b fired=%b progdone=%b progout=%b advtrig=%b",
                $time, DUT.state, DUT.seq_index,
                DUT.QUEUE.CORE_RAM.data_reg, DUT.QUEUE.CORE_RAM.data_valid,
                DUT.QUEUE.CORE_RAM.pending_ack, DUT.q_ack_in_n,
                DUT.COLLECTOR.CORE_NANO.cardinal_edge, DUT.COLLECTOR.CORE_NANO.pending_ack,
                DUT.col_fire_e, DUT.err_sticky, DUT.H1.CORE_ACC.accumulator,
                DUT.H2.CORE_ACC.accumulator, DUT.h1_ready_in_s, DUT.h2_ready_in_n,
                DUT.active_dir_idx, DUT.active_dir_valid, DUT.fired_this_round,
                DUT.col_program_done, DUT.seq_program_out, DUT.advance_trigger);
            last_state <= DUT.state;
        end
    end
    initial begin
        error_seen = 0;
        // Run long enough for the full FSM (config, 3 pre-increments,
        // 3 rounds + wraparound) to complete at the internal 25 MHz
        // fabric clock -- generous margin over the real settle budget.
        for (i = 0; i < 20000; i = i + 1) begin
            @(posedge clk);
            if (led1_n === 1'b0) error_seen = 1;   // LIT (active-low) = error
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
        $display("Final seq_index  = %0d", DUT.seq_index);
        $finish;
    end
endmodule
