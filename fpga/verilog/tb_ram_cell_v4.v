// tb_ram_cell_v4.v — points.md #617/#619: confirms ram_cell_v4.v's
// real, cloned single-arrival-capture core behaves IDENTICALLY to
// ram_cell_v1.v, then confirms each new real shell addition
// independently: PROG_ID-targeted reconfiguration (including the real
// split init_data LOW/HIGH write this core's own wider field needed),
// the real addon chain, and the `active` port.
`timescale 1ns / 1ps

module tb_ram_cell_v4;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;
    reg active = 1;

    reg cfg = 0;
    reg [79:0] cfg_d = 0;

    // downstream=E, upstream=W — flowing mode, matches
    // tb_ram_cell_v1_chain.v's own real R1/R2 wiring convention.
    localparam [5:0] DIR_E6 = 6'b000100, DIR_W6 = 6'b001000;
    // cfg_data[79:0]: [5:0]down [11:6]up [12]fixed [13]load_valid [45:14]init_data [65:46]addon_config [79:66]reserved
    localparam [79:0] CFG_FLOWING = {14'h0, 20'h0, 32'h0, 1'b0, 1'b0, DIR_W6, DIR_E6};

    reg  [31:0] opW = 0;
    reg         pulse_w = 0;

    wire [31:0] dout_e;
    wire        fire_e;
    wire        ready_o;
    wire        ack_out_w;
    wire        status_dv;
    wire        program_done;
    wire        prog_ack_n, prog_ack_s, prog_ack_e, prog_ack_w;

    reg cons_ready = 1;
    reg cons_ack   = 0;

    reg         program_in = 0;
    reg  [31:0] prog_data_n = 0;
    reg         prog_arr_n = 0;

    ram_cell_v4 #(.CELL_ID(16'h0000)) DUT (
        .clk(clk), .rst(rst), .active(active),
        .cfg_valid(cfg), .cfg_data(cfg_d),
        .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(opW),
        .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(pulse_w),
        .data_out_n(), .data_out_s(), .data_out_e(dout_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(fire_e), .fire_w(),
        .ready_out(ready_o),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(cons_ready), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(ack_out_w),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(cons_ack), .ack_in_w(1'b0),
        .program_in(program_in), .program_done(program_done),
        .prog_data_in_n(prog_data_n), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(prog_arr_n), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(prog_ack_n), .prog_ack_out_s(prog_ack_s), .prog_ack_out_e(prog_ack_e), .prog_ack_out_w(prog_ack_w),
        .freeze_in(1'b0), .status_data_valid(status_dv)
    );

    integer received = 0;
    integer errors   = 0;
    reg [31:0] expected_val;

    reg [1:0] cons_state = 0;
    always @(posedge clk) begin
        cons_ack <= 1'b0;
        if (!rst) begin
            case (cons_state)
                0: if (fire_e) begin
                       if (dout_e !== expected_val) begin
                           $display("[%0t] FAIL: expected=%h got=%h", $time, expected_val, dout_e);
                           errors = errors + 1;
                       end else begin
                           $display("[%0t] receive #%0d: val=%h (correct)", $time, received+1, dout_e);
                       end
                       received = received + 1;
                       cons_state <= 1;
                   end
                1: begin cons_ack <= 1'b1; cons_state <= 2; end
                2: cons_state <= 0;
                default: cons_state <= 0;
            endcase
        end
    end

    task send_val(input [31:0] v);
        begin
            expected_val = v;
            opW = v; pulse_w = 1'b1;
            #10;
            pulse_w = 1'b0;
        end
    endtask

    task prog_send(input [2:0] id, input [19:0] word, input do_complete, input arm_bit);
        begin
            prog_data_n = {9'h0, id, word};
            prog_arr_n = 1'b1;
            #10;
            prog_arr_n = 1'b0;
            #10;
            if (do_complete) begin
                prog_data_n = {9'h0, 3'd7, 19'h0, arm_bit};
                prog_arr_n = 1'b1;
                #10;
                prog_arr_n = 1'b0;
                #10;
            end
        end
    endtask

    initial begin
        #12 rst = 0;
        #10 cfg = 1; cfg_d = CFG_FLOWING;
        #10 cfg = 0;

        // ── Real, identical-to-v1 core behavior: flowing capture and
        // re-offer, several values in a row ──
        send_val(32'h0000_00AA);
        #40;
        send_val(32'hDEAD_BEEF);
        #40;
        send_val(32'h0000_0001);
        #60;

        // ── Real, targeted reprogram: PROG_ID_FIXED_MODE — real
        // confirmation routing survives (still receives afterward). ──
        program_in = 1'b1;
        prog_send(3'd2, 20'h0, 1'b1, 1'b1);   // PROG_ID_FIXED_MODE=0 (no-op value, re-arms)
        program_in = 1'b0;
        #20;
        send_val(32'h1234_5678);
        #60;

        // ── Real, targeted reprogram: split init_data LOW/HIGH write,
        // then an explicit real PROG_ID_LOAD_DATA_VALID commit, then
        // COMPLETE — confirms the real two-half-write protocol this
        // core's own wider field genuinely needed, that committing the
        // staged value is a real, separate, explicit action (not an
        // implicit COMPLETE side effect -- see the real bug this
        // caught, in the RTL's own comment), and that COMPLETE alone
        // never disturbs data_reg/data_valid. Uses the SAME generic
        // consumer FSM as every other real receive in this test,
        // rather than a separate manual ack -- an earlier draft double
        // -drove cons_ack from two places at once, a real testbench
        // race, not a DUT bug (caught by the sim itself). ──
        expected_val = 32'hCAFE_BEEF;
        program_in = 1'b1;
        prog_send(3'd3, 20'hBEEF, 1'b0, 1'b0);      // PROG_ID_INIT_DATA_LOW = 0xBEEF
        prog_send(3'd4, 20'hCAFE, 1'b0, 1'b0);      // PROG_ID_INIT_DATA_HIGH = 0xCAFE
        prog_send(3'd6, 20'h1,    1'b0, 1'b0);      // PROG_ID_LOAD_DATA_VALID = 1 -- the real commit
        prog_send(3'd7, 20'h1,    1'b0, 1'b0);      // COMPLETE, word[0]=1 (arm)
        program_in = 1'b0;
        #60;

        // ── Real addon chain: invert_en via PROG_ID_ADDON_CONFIG ──
        program_in = 1'b1;
        prog_send(3'd5, {1'b1, 19'h0}, 1'b1, 1'b1);   // PROG_ID_ADDON_CONFIG, invert_en=bit19=1
        program_in = 1'b0;
        #20;
        send_val(32'h0000_00FF);   // will arrive INVERTED at the output
        // note: send_val sets expected_val to the RAW value; override
        // to the real, inverted expectation before it's checked.
        expected_val = ~32'h0000_00FF;
        #60;

        // clear addon_config for the final real check
        program_in = 1'b1;
        prog_send(3'd5, 20'h0, 1'b1, 1'b1);
        program_in = 1'b0;
        #20;

        // ── Real `active` gating ──
        active = 1'b0;
        #10;
        if (ready_o !== 1'b0) begin
            $display("[%0t] FAIL: ready_out should be 0 when active=0, got %b", $time, ready_o);
            errors = errors + 1;
        end
        opW = 32'd7; pulse_w = 1'b1; #10; pulse_w = 1'b0;
        #20;
        if (status_dv !== 1'b0) begin
            $display("[%0t] FAIL: a real arrival was captured while active=0", $time);
            errors = errors + 1;
        end else begin
            $display("[%0t] confirmed: active=0 genuinely silences the cell", $time);
        end
        active = 1'b1;
        #20;

        if (received == 6 && errors == 0)
            $display("PASS: ram_cell_v4 -- identical core behavior to v1 (3 values), real targeted PROG_ID reconfiguration surviving routing, real split init_data LOW/HIGH write correctly reconstructed, real addon chain (invert_en), real active=0 gating confirmed");
        else
            $display("FAIL: received=%0d errors=%0d", received, errors);

        $finish;
    end

endmodule
