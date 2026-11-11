// hexn_speech2 (10 Nov 2026): the speech chain (rtl/hexn_speech_chain_v1.v: window detectors, count/log-probability store, decision) on the YPCB-00338-1P1 (Kintex-7 XC7K480T), openXC7 flow.
// A SELF-CHECKING replay: the 300 test recordings of the Heidelberg spoken digits (as folded events) sit in a ROM and are fed to the chain one word per few clocks; after window DECIDE (3 windows heard) the chain's predicted digit is compared with the recording's label.
// led[0] = heartbeat (~1.5 Hz), led[1] = replay finished, led[2] = PASS (finished and at least 5/6 of the recordings right; the model says 262 of 300 = 87.3%, so a working chain passes). Pins as hexn_bnet (SYS_CLK, led[2:0]).
// Nothing is read back over JTAG; the LEDs are the only result. The data (weights, thresholds, store, recordings, labels) is generated into Verilog by prebuild.py from the hex files in data/ (the card flow's yosys cannot be trusted to find data files).
module hexn_speech2 (input SYS_CLK, output [2:0] led);
    reg [31:0] count = 0; always @(posedge SYS_CLK) count <= count + 1;
    wire [15:0] w; wire [3:0] ld;
    reg [15:0] pc = 0; reg [8:0] lab_a = 0, rec = 0; reg [8:0] correct = 0, total = 0; reg done = 0; reg [2:0] st = 0; reg [1:0] idle = 0;
    reg start = 0, ev_valid = 0, win_end = 0; reg [7:0] ev_idx = 0;
    wire out_valid; wire [2:0] out_win; wire [3:0] out_cls, out_pred; wire signed [16:0] out_gap; wire out_stop;
    hexn_speech_rom rom (.clk(SYS_CLK), .pa(pc), .pw(w), .la(lab_a), .ld(ld));
    hexn_speech_chain_v1 chain (.clk(SYS_CLK), .rst(1'b0), .cfg_we(1'b0), .cfg_sel(3'd0), .cfg_addr(16'd0), .cfg_data(80'd0), .start(start), .ev_valid(ev_valid), .ev_idx(ev_idx), .win_end(win_end),
        .out_valid(out_valid), .out_win(out_win), .out_cls(out_cls), .out_pred(out_pred), .out_gap(out_gap), .out_stop(out_stop));
    always @(posedge SYS_CLK) begin
        start <= 0; ev_valid <= 0; win_end <= 0;
        case (st)
            3'd0: st <= 3'd1;                                             // the ROM output for pc is valid next clock
            3'd1: begin
                if (w == 16'hFFFF) begin done <= 1; st <= 3'd7; end
                else if (w[14]) begin start <= 1; lab_a <= rec; rec <= rec + 9'd1; pc <= pc + 16'd1; st <= 3'd0; end
                else if (w[15]) begin idle <= 2'd0; st <= 3'd2; end
                else begin ev_valid <= 1; ev_idx <= w[7:0]; pc <= pc + 16'd1; st <= 3'd0; end
            end
            3'd2: begin idle <= idle + 2'd1; if (idle == 2'd2) begin win_end <= 1; st <= 3'd3; end end      // >= 2 idle clocks after the last event of the window
            3'd3: if (out_valid) begin
                if (out_win == 3'd2) begin total <= total + 9'd1; if (out_pred == ld) correct <= correct + 9'd1; end
                pc <= pc + 16'd1; st <= 3'd0;
            end
            default: ;
        endcase
    end
    wire pass = ({correct, 2'b00} + {correct, 1'b0}) >= ({total, 2'b00} + total);       // correct x 6 >= total x 5
    assign led = {done & pass, done, count[25]};
    // ---- v2: read-only JTAG register (BSCANE2 USER2 = IR 0x03, 64 bits, bit 0 shifted out first). A capture takes a snapshot of: [8:0] correct, [17:9] total, [26:18] recordings started, [27] done, [28] pass, [31:29] 0, [63:32] 0x53504348 ("SPCH", so the host knows which design it is reading).
    // The counts only change while the replay runs; once done (bit 27) is 1 they are stable, so the snapshot (taken on the JTAG clock, unsynchronised) is exact. Before done a snapshot can be torn; the host ignores it. Nothing is written to the card through this register.
    wire capture, drck, sel, shift, tdi, update;
    reg [63:0] sr = 0; wire [63:0] snap = {32'h53504348, 3'b000, pass, done, rec, total, correct};
    BSCANE2 #(.JTAG_CHAIN(2)) bscan (.CAPTURE(capture), .DRCK(drck), .RESET(), .RUNTEST(), .SEL(sel), .SHIFT(shift), .TCK(), .TDI(tdi), .TMS(), .UPDATE(update), .TDO(sr[0]));
    always @(posedge drck) if (capture) sr <= snap; else if (shift) sr <= {tdi, sr[63:1]};
endmodule
