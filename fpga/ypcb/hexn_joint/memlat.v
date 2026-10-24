// Hex-N RAM latency probe for a Wishbone DDR3 controller (UberDDR3 style: pipelined, stall + ack, acks in order).
// Same bus signals as designs/uberddr3/memtest.v (Alan's ypcb repo). READS ONLY, so nothing in the RAM is changed.
// mode 0: SINGLE      one random read at a time, `count` times. Per read: latency = clock edges from the request being
//                     accepted (stb high and stall low) to the edge that sees ack. Kept as min, max and sum.
//                     stall_sum = cycles a request waited with stall high before it was accepted.
// mode 1: PIPE-RANDOM `count` reads at random addresses issued back to back (stb held, next address as each is
//                     accepted). total_cycles = first request to last ack.
// mode 2: PIPE-SEQ    the same with consecutive addresses (what the 5 GB/s figure measures).
// Latency is in controller clock cycles; the host converts with the controller clock (not assumed here).
// Results are plain registers for a JTAG register file to read. In mode 1 and 2 lat_* are not used (min stays all ones).
module memlat #(
    parameter integer ADDR_BITS = 25,
    parameter integer DATA_BITS = 576
) (
    input wire clk,
    input wire ready,
    input wire start,                       // one-cycle pulse, ignored unless ready and idle
    input wire [1:0] mode,
    input wire [15:0] count,                // at least 1
    input wire [7:0] seed,
    output reg busy = 0,
    output reg [15:0] n_done = 0,
    output reg [31:0] lat_min = 32'hFFFFFFFF,
    output reg [31:0] lat_max = 0,
    output reg [31:0] lat_sum = 0,
    output reg [31:0] stall_sum = 0,
    output reg [31:0] total_cycles = 0,
    output reg [31:0] rd_fold = 0,          // read data folded so the reads cannot be optimised away
    output reg wb_stb = 0,
    output wire wb_we,
    output reg [ADDR_BITS - 1:0] wb_addr = 0,
    output wire [DATA_BITS - 1:0] wb_data,
    input wire wb_stall,
    input wire wb_ack,
    input wire [DATA_BITS - 1:0] wb_rdata
);
    assign wb_we = 1'b0;
    assign wb_data = {DATA_BITS{1'b0}};
    localparam [2:0] IDLE = 0, S_ISSUE = 1, S_ACCEPT = 2, S_ACK = 3, P_RUN = 4;
    reg [2:0] st = IDLE;
    reg [1:0] mode_q = 0;
    reg [15:0] count_q = 0, issued = 0, acked = 0;
    reg [31:0] rnd = 1, lat = 0, cyc = 0;
    reg [ADDR_BITS - 1:0] seqa = 0;

    function [31:0] xs32(input [31:0] x);
        reg [31:0] y;
        begin
            y = x ^ (x << 13);
            y = y ^ (y >> 17);
            xs32 = y ^ (y << 5);
        end
    endfunction

    wire accepted = wb_stb && !wb_stall;
    wire [31:0] rnd_next = xs32(rnd);
    wire [ADDR_BITS - 1:0] addr_next = (mode_q == 2) ? seqa + 1'b1 : rnd_next[ADDR_BITS - 1:0];

    always @(posedge clk) begin
        if (wb_ack) rd_fold <= rd_fold ^ wb_rdata[31:0] ^ wb_rdata[DATA_BITS - 1:DATA_BITS - 32];
        case (st)
        IDLE: begin
            wb_stb <= 0;
            if (start && ready) begin
                mode_q <= mode; count_q <= count; busy <= 1;
                n_done <= 0; lat_min <= 32'hFFFFFFFF; lat_max <= 0; lat_sum <= 0; stall_sum <= 0; total_cycles <= 0;
                issued <= 0; acked <= 0; cyc <= 0; seqa <= 0;
                rnd <= {24'hA5C3E1, seed} | 32'd1;
                st <= (mode == 0) ? S_ISSUE : P_RUN;
            end
        end
        // ---- one read at a time
        S_ISSUE: begin
            cyc <= cyc + 1;
            wb_stb <= 1;
            wb_addr <= (mode_q == 2) ? seqa : rnd[ADDR_BITS - 1:0];
            st <= S_ACCEPT;
        end
        S_ACCEPT: begin
            cyc <= cyc + 1;
            if (!wb_stall) begin            // accepted at this edge
                wb_stb <= 0; lat <= 1; st <= S_ACK;
                rnd <= rnd_next; seqa <= seqa + 1'b1;
            end else stall_sum <= stall_sum + 1;
        end
        S_ACK: begin
            cyc <= cyc + 1;
            if (wb_ack) begin
                lat_sum <= lat_sum + lat;
                if (lat < lat_min) lat_min <= lat;
                if (lat > lat_max) lat_max <= lat;
                n_done <= n_done + 1'b1;
                if (n_done + 1'b1 == count_q) begin
                    total_cycles <= cyc + 1; busy <= 0; st <= IDLE;
                end else st <= S_ISSUE;
            end else lat <= lat + 1;
        end
        // ---- pipelined run
        P_RUN: begin
            cyc <= cyc + 1;
            if (issued == 0 && !wb_stb && acked == 0 && cyc == 0) begin      // first request
                wb_stb <= 1; wb_addr <= (mode_q == 2) ? seqa : rnd[ADDR_BITS - 1:0];
            end else begin
                if (wb_stb && wb_stall) stall_sum <= stall_sum + 1;
                if (accepted) begin
                    issued <= issued + 1'b1; rnd <= rnd_next; seqa <= seqa + 1'b1;
                    if (issued + 1'b1 == count_q) wb_stb <= 0;
                    else wb_addr <= addr_next;
                end
                if (wb_ack) begin
                    acked <= acked + 1'b1; n_done <= n_done + 1'b1;
                    if (acked + 1'b1 == count_q) begin
                        total_cycles <= cyc + 1; busy <= 0; st <= IDLE;
                    end
                end
            end
        end
        default: st <= IDLE;
        endcase
    end
endmodule
