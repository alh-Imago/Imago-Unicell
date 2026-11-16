// far_copy.v - copy engine between the cores' RAM and the far RAM (the onboard SDRAM).  The cores never see the SDRAM.
//   dir 0: shared data RAM  -> far RAM      dir 1: far RAM -> shared data RAM      dir 2: far RAM -> shared CODE store (program loading)
// It only uses the host port of the shared RAM (dh_*), which already yields to the cores: a copy takes the clocks the cores leave free and
// never delays a core.  The code store is written through the same port as the host's W command (imem_*).  One word at a time (about 15 clocks).
// Protection: the far range must lie inside the allowed window [lim_base, lim_base+lim_len) set by the host (length 0 = nothing allowed), the
// near range must lie inside the shared RAM (or the code store for dir 2).  A refused copy moves nothing and sets err:
//   0 none   1 far range outside the allowed window   2 near range past the end of the shared RAM / code store   3 far RAM not ready
//   4 bad direction   5 timeout (no answer from the far RAM or the shared RAM)
module far_copy #(parameter DSH = 256, parameter IMW = 128) (
    input  wire        clk, rst,
    input  wire        start,
    input  wire [1:0]  dir,
    input  wire [15:0] sh_a,
    input  wire [20:0] far_a,
    input  wire [15:0] count,
    input  wire [20:0] lim_base,
    input  wire [21:0] lim_len,
    input  wire        init_done,
    output reg         busy, done, ignored,
    output reg  [2:0]  err,
    output reg  [31:0] moved, clocks,
    // shared data RAM host port
    output reg         dh_we, dh_rd,
    output reg  [15:0] dh_a,
    output reg  [31:0] dh_wd,
    input  wire [31:0] dh_q,
    input  wire        dh_qv, dh_busy,
    // shared code store write port
    output reg         ie_we,
    output reg  [15:0] ie_wa,
    output reg  [31:0] ie_wd,
    // far RAM controller
    output reg         req_v, req_we,
    output reg  [20:0] req_a,
    output reg  [31:0] req_wd,
    input  wire        req_rdy, ack_v,
    input  wire [31:0] ack_d
);
    localparam [3:0] IDLE = 0, R0 = 1, R1 = 2, W0 = 3, W1 = 4, W2 = 5, F0 = 6, F1 = 7, F2 = 8, H0 = 9, H1 = 10, H2 = 11;
    reg [3:0]  st;
    reg [1:0]  d;
    reg [15:0] sa, left;
    reg [20:0] fa;
    reg [31:0] dat;
    reg [12:0] wd;                                   // clocks spent on the current word (timeout)
    wire [22:0] far_end  = {2'b0, far_a} + {7'b0, count};
    wire [22:0] lim_top  = {2'b0, lim_base} + {1'b0, lim_len};
    wire [16:0] near_end = {1'b0, sh_a} + {1'b0, count};
    wire        far_ok   = (far_a >= lim_base) && (far_end <= lim_top) && (lim_len != 22'd0);
    wire        near_ok  = (dir == 2'd2) ? (near_end <= IMW) : (near_end <= DSH);
    task fin(input [2:0] e); begin err <= e; busy <= 1'b0; done <= 1'b1; st <= IDLE; req_v <= 1'b0; end endtask
    task nextw; begin
        moved <= moved + 1'b1; wd <= 13'd0; sa <= sa + 1'b1; fa <= fa + 1'b1; left <= left - 1'b1;
        if (left == 16'd1) begin busy <= 1'b0; done <= 1'b1; st <= IDLE; end
        else st <= (d == 2'd0) ? R0 : F0;
    end endtask
    always @(posedge clk) begin
        dh_we <= 1'b0; dh_rd <= 1'b0; ie_we <= 1'b0;
        if (rst) begin st <= IDLE; busy <= 1'b0; done <= 1'b0; ignored <= 1'b0; err <= 3'd0; req_v <= 1'b0; req_we <= 1'b0; end
        else begin
            if (busy) begin clocks <= clocks + 1'b1; wd <= wd + 1'b1; if (wd == 13'h1FFF) fin(3'd5); end
            case (st)
                IDLE: if (start) begin
                    if (busy) ignored <= 1'b1;
                    else begin
                        ignored <= 1'b0; done <= 1'b0; moved <= 32'd0; clocks <= 32'd0; wd <= 13'd0;
                        d <= dir; sa <= sh_a; fa <= far_a; left <= count; err <= 3'd0;
                        if (dir == 2'd3)       begin err <= 3'd4; done <= 1'b1; end
                        else if (!init_done)   begin err <= 3'd3; done <= 1'b1; end
                        else if (!far_ok)      begin err <= 3'd1; done <= 1'b1; end
                        else if (!near_ok)     begin err <= 3'd2; done <= 1'b1; end
                        else if (count == 16'd0) done <= 1'b1;
                        else begin busy <= 1'b1; st <= (dir == 2'd0) ? R0 : F0; end
                    end
                end
                // shared RAM -> far RAM
                R0: if (!dh_busy) begin dh_rd <= 1'b1; dh_a <= sa; st <= R1; end
                R1: if (dh_qv) begin dat <= dh_q; req_a <= fa; req_wd <= dh_q; req_we <= 1'b1; req_v <= 1'b1; st <= W1; end
                W1: if (req_v && req_rdy) begin req_v <= 1'b0; st <= W2; end
                W2: if (ack_v) nextw;
                // far RAM -> shared RAM or code store
                F0: begin req_a <= fa; req_we <= 1'b0; req_v <= 1'b1; st <= F1; end
                F1: if (req_v && req_rdy) begin req_v <= 1'b0; st <= F2; end
                F2: if (ack_v) begin
                    dat <= ack_d;
                    if (d == 2'd2) begin ie_we <= 1'b1; ie_wa <= sa; ie_wd <= ack_d; nextw; end
                    else st <= H0;
                end
                H0: if (!dh_busy) begin dh_we <= 1'b1; dh_a <= sa; dh_wd <= dat; st <= H1; end
                H1: st <= H2;
                H2: if (!dh_busy) nextw;
                default: st <= IDLE;
            endcase
        end
    end
    initial begin st = IDLE; busy = 0; done = 0; ignored = 0; err = 0; moved = 0; clocks = 0; dh_we = 0; dh_rd = 0; dh_a = 0; dh_wd = 0; ie_we = 0; ie_wa = 0; ie_wd = 0; req_v = 0; req_we = 0; req_a = 0; req_wd = 0; wd = 0; end
endmodule
