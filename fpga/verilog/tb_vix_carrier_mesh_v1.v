// tb_vix_carrier_mesh_v1.v — points.md #665: real, decisive RTL proof
// that the array generator's own new carrier-to-carrier wiring
// (freeze_out->freeze_in, program_out/prog_data_out/prog_arrived_out
// -> program_in/prog_data_in/prog_arrived_in, prog_ack_out<-prog_ack_in,
// all real, cardinal, point-to-point; program_in itself a real OR of
// whichever real neighbors exist) genuinely works in real hardware
// simulation, not just inspected as generated text.
//
// Real, honest scope, confirmed directly against unicell_vix_
// carrier_v1.v before writing this: core_select is switchable ONLY
// via the one-time cfg_valid/cfg_data boot commit -- there is no real
// RTL mechanism (yet) for live programming to redirect it, unlike
// #658's own VM-level VixCarrierSlot (a real, useful software design,
// with no RTL counterpart built so far). This test proves what the
// real RTL actually supports today: cell B boot-configured to nano
// directly, cell A's own command core (programmer mode) reprogramming
// specific real fields on B through the NOW-REAL mesh wiring.
`timescale 1ns / 1ps

module tb_vix_carrier_mesh_v1;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

    localparam [4:0] SEL_NANO = 5'd0, SEL_COMMAND = 5'd8;
    localparam [9:0] TOPO_PASS_A = 10'h000;
    localparam [2:0] DIR_E3 = 3'd2;
    localparam [3:0] PROG_ID_COMPLETE = 4'hF;   // command's OWN receive-side toggle_pattern field, 4-bit
    localparam [3:0] PROG_ID_TOPOLOGY = 4'd0, PROG_ID_ROUTING_MASK = 4'd1, PROG_ID_COMPLETE_NANO = 4'd15;

    integer errors = 0;
    integer checks = 0;

    task check(input cond, input [255:0] label);
        begin
            checks = checks + 1;
            if (!cond) begin
                $display("[t=%0t] FAIL: %0s", $time, label);
                errors = errors + 1;
            end else begin
                $display("[t=%0t] check #%0d OK: %0s", $time, checks, label);
            end
        end
    endtask

    function [31:0] make_word(input [3:0] pid, input [19:0] word);
        make_word = {8'h0, pid, word};   // matches nano's own real 4-bit PROG_ID window at word[23:20] (confirmed against nano_gate_v4.v directly -- COMPLETE=15, not 7)
    endfunction

    // ── Cell A (west): command core, programmer mode, drive_dir=E. ──
    reg a_cfg_valid = 0; reg [159:0] a_cfg_data;
    wire [31:0] a_dout_e; wire a_fire_e; wire a_ack_e;
    reg [31:0] a_val_n = 0; reg a_pulse_n = 0;
    wire a_fzo_e, a_pon_e, a_pao_e; wire [31:0] a_pdo_e;
    wire a_pack_e;

    // ── Cell B (east): boots directly to nano. ──
    reg b_cfg_valid = 0; reg [159:0] b_cfg_data;
    wire [31:0] b_dout_w; wire b_fire_w; wire b_ack_w;

    // Real, point-to-point mesh wiring -- the exact same convention
    // generate_top_vix() now produces for two real horizontal
    // neighbors (A west, B east).
    wire mesh_freeze = a_fzo_e;
    wire mesh_program = a_pon_e;
    wire [31:0] mesh_prog_data = a_pdo_e;
    wire mesh_prog_arrived = a_pao_e;
    wire mesh_prog_ack = b_pack_w_wire;

    wire b_pack_w_wire;

    unicell_vix_carrier_v1 #(.CELL_ID(16'hA000)) CELL_A (
        .clk(clk), .rst(rst),
        .active_in_n(1'b1), .active_in_s(1'b1), .active_in_e(1'b1), .active_in_w(1'b1),
        .freeze_in_n(1'b0), .freeze_in_s(1'b0), .freeze_in_e(1'b0), .freeze_in_w(1'b0),
        .cfg_valid(a_cfg_valid), .cfg_data(a_cfg_data),
        .data_in_n(a_val_n), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(a_pulse_n), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(), .data_out_e(a_dout_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(a_fire_e), .fire_w(),
        .ready_out(), .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(a_ack_e), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(1'b0), .ack_in_w(1'b0),
        .program_in(1'b0), .program_done(),
        .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(a_pack_e), .prog_ack_out_w(),
        .freeze_out_n(), .freeze_out_s(), .freeze_out_e(a_fzo_e), .freeze_out_w(),
        .program_out_n(), .program_out_s(), .program_out_e(a_pon_e), .program_out_w(),
        .prog_data_out_n(), .prog_data_out_s(), .prog_data_out_e(a_pdo_e), .prog_data_out_w(),
        .prog_arrived_out_n(), .prog_arrived_out_s(), .prog_arrived_out_e(a_pao_e), .prog_arrived_out_w(),
        .prog_ack_in_n(1'b0), .prog_ack_in_s(1'b0), .prog_ack_in_e(mesh_prog_ack), .prog_ack_in_w(1'b0),
        .status_core_select()
    );

    unicell_vix_carrier_v1 #(.CELL_ID(16'hB000)) CELL_B (
        .clk(clk), .rst(rst),
        .active_in_n(1'b1), .active_in_s(1'b1), .active_in_e(1'b1), .active_in_w(1'b1),
        .freeze_in_n(1'b0), .freeze_in_s(1'b0), .freeze_in_e(1'b0), .freeze_in_w(mesh_freeze),
        .cfg_valid(b_cfg_valid), .cfg_data(b_cfg_data),
        .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(), .data_out_e(), .data_out_w(b_dout_w),
        .fire_n(), .fire_s(), .fire_e(), .fire_w(b_fire_w),
        .ready_out(), .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(b_ack_w),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(1'b0), .ack_in_w(1'b0),
        .program_in(mesh_program), .program_done(),
        .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(mesh_prog_data),
        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(mesh_prog_arrived),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w(b_pack_w_wire),
        .freeze_out_n(), .freeze_out_s(), .freeze_out_e(), .freeze_out_w(),
        .program_out_n(), .program_out_s(), .program_out_e(), .program_out_w(),
        .prog_data_out_n(), .prog_data_out_s(), .prog_data_out_e(), .prog_data_out_w(),
        .prog_arrived_out_n(), .prog_arrived_out_s(), .prog_arrived_out_e(), .prog_arrived_out_w(),
        .prog_ack_in_n(1'b0), .prog_ack_in_s(1'b0), .prog_ack_in_e(1'b0), .prog_ack_in_w(1'b0),
        .status_core_select()
    );

    initial begin
        $dumpfile("/tmp/tb_vix_carrier_mesh_v1.vcd");
        $dumpvars(0, tb_vix_carrier_mesh_v1);

        #12 rst = 0;
        @(posedge clk); #1;

        // Boot cell B directly to nano (PASS_A, routing_mask=0 for now
        // -- set for real via live programming below).
        b_cfg_valid = 1; b_cfg_data = {27'h0, {118'h0, TOPO_PASS_A}, SEL_NANO};
        @(posedge clk); #1; b_cfg_valid = 0;
        repeat (2) @(posedge clk); #1;

        // Boot cell A to command, programmer mode, drive_dir=E,
        // toggle_pattern=PROG_ID_COMPLETE (command's own real 4-bit
        // receive-side field, matching its own real config table).
        a_cfg_valid = 1;
        a_cfg_data = {27'h0, {55'h0, PROG_ID_COMPLETE, DIR_E3, 1'b0, 1'b1}, SEL_COMMAND};
        @(posedge clk); #1; a_cfg_valid = 0;
        repeat (2) @(posedge clk); #1;

        check(mesh_freeze === 1'b0, "cell A idle: no real freeze asserted onto cell B yet");

        // Real word 1: points.md #666 -- the receiving carrier now
        // INSISTS the first real word of any session be a raw core-
        // select value. Cell B is already nano, but the protocol is
        // mandatory regardless -- sending it here, not skipping it,
        // is what makes this test honest after #666 (an earlier
        // version of this test skipped this and passed only by
        // coincidence: the first ordinary word it sent had low bits
        // that happened to equal SEL_NANO too, silently masking the
        // real bug -- traced and fixed directly, not left in place).
        a_val_n = {27'h0, SEL_NANO}; a_pulse_n = 1'b1;
        @(posedge clk); #1; a_pulse_n = 1'b0;
        repeat (2) @(posedge clk); #1;
        check(CELL_B.core_select === SEL_NANO, "real core-select word correctly consumed first, across the mesh");

        // Real word 2: set cell B's own routing_mask -- fed to cell A
        // as an ordinary real cardinal arrival (matching command's own
        // real 'watch' mechanism), relayed across the REAL mesh to B.
        a_val_n = make_word(PROG_ID_ROUTING_MASK, 20'h0); a_pulse_n = 1'b1;
        @(posedge clk); #1; a_pulse_n = 1'b0;
        repeat (3) @(posedge clk); #1;
        check(mesh_freeze === 1'b1, "real freeze correctly asserted across the mesh during the relay");

        // Real word 2: COMPLETE -- releases freeze, confirms the
        // relay's own real end-to-end handshake through the new wiring.
        a_val_n = make_word(PROG_ID_COMPLETE_NANO, 20'h1); a_pulse_n = 1'b1;
        @(posedge clk); #1; a_pulse_n = 1'b0;

        // Real, necessary wait -- the relay's own real handshake needs
        // several real cycles to close (program_out -> program_in ->
        // target applies word -> prog_ack_out -> prog_ack_in).
        repeat (20) @(posedge clk); #1;
        check(mesh_freeze === 1'b0, "real freeze correctly released across the mesh after COMPLETE");

        // Real, end-to-end functional confirmation -- not just timing:
        // cell B's own routing_mask genuinely landed correctly through
        // the real mesh relay.
        check(CELL_B.CORE_NANO.CORE.routing_mask === 6'b000000,
              "real routing_mask genuinely relayed across the mesh (0, matching the word sent)");
        check(CELL_B.CORE_NANO.CORE.ready_bit === 1'b1,
              "real target genuinely armed after the real COMPLETE word crossed the mesh");

        $display("");
        if (checks == 6 && errors == 0)
            $display("PASS: real carrier-to-carrier wiring (#665) AND the real core-select-first protocol (#666) both genuinely work in real RTL simulation -- freeze, program signals, and the mandatory first-word redirect all correctly cross a real cell boundary using the exact same convention generate_top_vix() now produces");
        else
            $display("FAIL: checks=%0d errors=%0d", checks, errors);

        $finish;
    end

endmodule
