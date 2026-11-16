// batch_seq.v - the batch sequencer: runs a script of 4-word steps held in far RAM (format and rules: batch.py) so a chain of batches needs no host in between.
// It uses only what the host uses: it reads the steps from the far RAM, starts the copy engine (far_copy), and pulses the scheduler's own host commands
// (region / window / library / submit).  The dispatcher is not changed.  Polled, no interrupt: the host starts it and reads busy / done / err / steps / tag.
// Error codes: 0 ok, 1..5 copy engine, 6 wait timed out, 7 code or region change with jobs in flight, 8 bad opcode, 9 step limit (65535 steps).
// While it runs it owns the far RAM, the copy engine and the scheduler commands: the host must not issue those commands meanwhile.
module batch_seq (
    input  wire        clk, rst,
    input  wire        start,
    input  wire [20:0] start_a,
    input  wire        init_done,
    output reg         busy, done,
    output reg  [3:0]  err,
    output reg  [15:0] steps,
    output reg  [31:0] tag,
    // far RAM read port (read only)
    output reg         req_v,
    output reg  [20:0] req_a,
    input  wire        req_rdy, ack_v,
    input  wire [31:0] ack_d,
    // copy engine
    output reg         c_start,
    output reg  [1:0]  c_dir,
    output reg  [15:0] c_near,
    output reg  [20:0] c_far,
    output reg  [15:0] c_cnt,
    input  wire        c_busy, c_done,
    input  wire [2:0]  c_err,
    // scheduler host commands
    output reg         h_push,
    output reg  [15:0] h_tid, h_code,
    output reg  [2:0]  h_lw,
    output reg         h_crit,
    output reg  [5:0]  h_prog,
    output reg         rg_we,
    output reg  [5:0]  rg_prog,
    output reg  [15:0] rg_cbase, rg_clen, rg_dlen,
    output reg         rs_we,
    output reg  [5:0]  rs_prog,
    output reg  [15:0] rs_base, rs_len,
    output reg         lb_we,
    output reg  [15:0] lb_base, lb_len,
    input  wire [31:0] n_done
);
    localparam [3:0] IDLE = 0, FQ = 1, FR = 2, FA = 3, EX = 4, C1 = 5, C2 = 6, C3 = 7, WT = 8, WP = 9;
    localparam [3:0] END = 0, LCODE = 1, LDATA = 2, SAVE = 3, SUBMIT = 4, WAIT = 5, JUMP = 6, REGION = 7, WINDOW = 8, LIBRARY = 9;
    reg [3:0]  st;
    reg [20:0] pc;
    reg [1:0]  wi;
    reg [31:0] w0, w1, w2, w3;
    reg [15:0] pend, dbase, tleft;
    reg [9:0]  tick;
    wire [15:0] got = n_done[15:0] - dbase;
    task stop(input [3:0] e); begin err <= e; busy <= 1'b0; done <= 1'b1; st <= IDLE; req_v <= 1'b0; end endtask
    always @(posedge clk) begin
        c_start <= 1'b0; h_push <= 1'b0; rg_we <= 1'b0; rs_we <= 1'b0; lb_we <= 1'b0;
        if (rst) begin st <= IDLE; busy <= 1'b0; done <= 1'b0; err <= 4'd0; req_v <= 1'b0; end
        else case (st)
            IDLE: if (start && !busy) begin
                busy <= 1'b1; done <= 1'b0; err <= 4'd0; steps <= 16'd0; pend <= 16'd0; pc <= start_a; wi <= 2'd0;
                if (!init_done) stop(4'd3); else st <= FQ;
            end
            // read the four words of the step at pc
            FQ: begin req_a <= pc + {19'd0, wi}; req_v <= 1'b1; st <= FR; end
            FR: if (req_v && req_rdy) begin req_v <= 1'b0; st <= FA; end
            FA: if (ack_v) begin
                case (wi) 2'd0: w0 <= ack_d; 2'd1: w1 <= ack_d; 2'd2: w2 <= ack_d; default: w3 <= ack_d; endcase
                wi <= wi + 1'b1;
                if (wi == 2'd3) st <= EX; else st <= FQ;
            end
            EX: begin
                steps <= steps + 1'b1; pc <= pc + 21'd4; st <= FQ;
                if (steps == 16'hFFFF) stop(4'd9);
                else case (w0[3:0])
                    END:    begin tag <= w1; stop(4'd0); end
                    JUMP:   pc <= w1[20:0];
                    LCODE, LDATA, SAVE: if (w0[3:0] == LCODE && pend != 16'd0) stop(4'd7);
                            else begin c_dir <= (w0[3:0] == LCODE) ? 2'd2 : (w0[3:0] == LDATA) ? 2'd1 : 2'd0; c_near <= w1[15:0]; c_far <= w2[20:0]; c_cnt <= w3[15:0]; c_start <= 1'b1; st <= C1; end
                    REGION: if (pend != 16'd0) stop(4'd7); else begin rg_we <= 1'b1; rg_prog <= w1[5:0]; rg_cbase <= w1[31:16]; rg_clen <= w2[15:0]; rg_dlen <= w2[31:16]; end
                    WINDOW: if (pend != 16'd0) stop(4'd7); else begin rs_we <= 1'b1; rs_prog <= w1[5:0]; rs_base <= w2[15:0]; rs_len <= w2[31:16]; end
                    LIBRARY: if (pend != 16'd0) stop(4'd7); else begin lb_we <= 1'b1; lb_base <= w1[15:0]; lb_len <= w1[31:16]; end
                    SUBMIT: begin
                        h_push <= 1'b1; h_tid <= w1[15:0]; h_code <= w1[31:16]; h_prog <= w2[5:0]; h_lw <= w2[10:8]; h_crit <= w2[12];
                        if (pend == 16'd0) dbase <= n_done[15:0];
                        pend <= pend + 1'b1;
                    end
                    WAIT: begin tleft <= (w1[15:0] == 16'd0) ? 16'd4096 : w1[15:0]; tick <= 10'd0; st <= WT; end
                    default: stop(4'd8);
                endcase
            end
            // copy: let the engine take the start, then wait until it has finished
            C1: st <= C2;
            C2: st <= C3;
            C3: if (!c_busy && c_done) begin
                if (c_err != 3'd0) stop({1'b0, c_err}); else st <= FQ;
            end
            // wait for every job submitted since the last WAIT
            WT: begin
                if (pend == 16'd0 || got >= pend) begin pend <= 16'd0; st <= FQ; end
                else begin
                    tick <= tick + 1'b1;
                    if (tick == 10'd1023) begin tleft <= tleft - 1'b1; if (tleft == 16'd1) stop(4'd6); end
                end
            end
            default: st <= IDLE;
        endcase
    end
    initial begin st = IDLE; busy = 0; done = 0; err = 0; steps = 0; tag = 0; req_v = 0; req_a = 0; c_start = 0; c_dir = 0; c_near = 0; c_far = 0; c_cnt = 0;
        h_push = 0; h_tid = 0; h_code = 0; h_lw = 0; h_crit = 0; h_prog = 0; rg_we = 0; rg_prog = 0; rg_cbase = 0; rg_clen = 0; rg_dlen = 0; rs_we = 0; rs_prog = 0; rs_base = 0; rs_len = 0; lb_we = 0; lb_base = 0; lb_len = 0;
        pc = 0; wi = 0; w0 = 0; w1 = 0; w2 = 0; w3 = 0; pend = 0; dbase = 0; tleft = 0; tick = 0; end
endmodule
