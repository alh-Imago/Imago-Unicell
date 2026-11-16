`timescale 1ns/1ps
// sdram_model.v - SIMULATION ONLY.  A behavioural 64 Mbit (2M x 32, 4 banks) SDR SDRAM with the checks that matter for a controller:
//   * the power-up sequence (precharge all, two auto-refreshes, load mode register) must come before the first ACTIVE
//   * a command needs the bank in the right state (READ/WRITE only to an active bank, ACTIVE only to a precharged one)
//   * tRCD >= 20 ns, tRP >= 20 ns (also after auto-precharge), tRFC >= 66 ns, tMRD >= 2 clocks, refresh at least every 20 us
//   * the read data appears CL clocks after the READ command, tAC (5.4 ns) after the clock edge, and is held for one clock: a controller that
//     samples at the wrong edge reads the wrong word
//   * mode register: burst length 1 only (the controller never uses bursts), CL taken from the mode register
// Every violation prints ERROR and counts in `errors`.  The clock is the SDRAM clock pin (possibly inverted by the controller).
module sdram_model (
    input  wire        clk, cke, cs_n, ras_n, cas_n, we_n,
    input  wire [3:0]  dqm,
    input  wire [10:0] addr,
    input  wire [1:0]  ba,
    inout  wire [31:0] dq
);
    parameter TAC = 5.4;
    integer errors = 0;
    reg [31:0] mem [0:2097151];
    reg        row_open [0:3];
    reg [10:0] row_of   [0:3];
    real       t_act [0:3];
    real       t_pre [0:3];             // time the bank became (or will become) precharged: tRP is counted from here
    real       t_ref, t_mrs, t_last_ref;
    integer    nref = 0; reg mrs_done = 0, pre_done = 0; integer cl = 2;
    reg [3:0]  cmd;
    reg        rd_v [0:3];
    reg [31:0] rd_d [0:3];
    reg        drv; reg [31:0] val;
    integer i;
    initial begin
        for (i = 0; i < 4; i = i + 1) begin row_open[i] = 0; row_of[i] = 0; t_act[i] = -1000; t_pre[i] = -1000; rd_v[i] = 0; rd_d[i] = 0; end
        t_ref = -1000; t_mrs = -1000; t_last_ref = 0; drv = 0; val = 0;
    end
    assign #0 dq = drv ? val : 32'bz;
    task err(input [255:0] msg); begin errors = errors + 1; $display("%0t SDRAM MODEL ERROR: %0s", $time, msg); end endtask
    wire [31:0] full_addr_dummy = 0;
    always @(posedge clk) if (cke) begin
        cmd = {cs_n, ras_n, cas_n, we_n};
        // read data pipeline: shift, then present what falls out
        drv <= #TAC rd_v[0]; val <= #TAC rd_d[0];
        rd_v[0] = rd_v[1]; rd_d[0] = rd_d[1]; rd_v[1] = rd_v[2]; rd_d[1] = rd_d[2]; rd_v[2] = rd_v[3]; rd_d[2] = rd_d[3]; rd_v[3] = 0;
        if (mrs_done && ($realtime - t_last_ref) > 20000.0) begin err("refresh overdue (more than 20 us since the last one)"); t_last_ref = $realtime; end
        case (cmd)
            4'b0111, 4'b1xxx: ;                                                        // NOP / deselected
            4'b0010: begin                                                              // PRECHARGE
                if (addr[10]) begin for (i = 0; i < 4; i = i + 1) begin row_open[i] = 0; t_pre[i] = $realtime; end pre_done = 1; nref = 0; end
                else begin row_open[ba] = 0; t_pre[ba] = $realtime; end
            end
            4'b0001: begin                                                              // AUTO REFRESH
                for (i = 0; i < 4; i = i + 1) if (row_open[i]) err("REFRESH with a bank open");
                if (($realtime - t_ref) < 66.0) err("tRFC violated (refresh too soon after the previous refresh)");
                for (i = 0; i < 4; i = i + 1) if (($realtime - t_pre[i]) < 20.0) err("tRP violated before REFRESH");
                t_ref = $realtime; t_last_ref = $realtime; if (pre_done) nref = nref + 1;
            end
            4'b0000: begin                                                              // LOAD MODE REGISTER
                for (i = 0; i < 4; i = i + 1) if (row_open[i]) err("MODE REGISTER SET with a bank open");
                if (!pre_done || nref < 2) err("MODE REGISTER SET before precharge-all and two refreshes");
                if (addr[2:0] != 3'd0) err("mode register: only burst length 1 is modelled");
                cl = addr[6:4]; if (cl != 2 && cl != 3) err("mode register: CAS latency must be 2 or 3");
                mrs_done = 1; t_mrs = $realtime; t_last_ref = $realtime;
            end
            4'b0011: begin                                                              // ACTIVE
                if (!mrs_done) err("ACTIVE before the power-up sequence is finished");
                if (($realtime - t_mrs) < 2 * 30.0) err("tMRD violated");
                if (row_open[ba]) err("ACTIVE to a bank that is already open");
                if (($realtime - t_pre[ba]) < 20.0) err("tRP violated (ACTIVE too soon after precharge)");
                if (($realtime - t_ref) < 66.0) err("tRFC violated (ACTIVE too soon after refresh)");
                row_open[ba] = 1; row_of[ba] = addr; t_act[ba] = $realtime;
            end
            4'b0101, 4'b0100: begin                                                     // READ / WRITE
                if (!row_open[ba]) err("READ/WRITE to a bank that is not active");
                else if (($realtime - t_act[ba]) < 20.0) err("tRCD violated");
                else begin : rw
                    reg [20:0] wa; wa = {ba, row_of[ba], addr[7:0]};
                    if (cmd == 4'b0100) begin
                        if (dqm[0] == 0) mem[wa][7:0]   = dq[7:0];
                        if (dqm[1] == 0) mem[wa][15:8]  = dq[15:8];
                        if (dqm[2] == 0) mem[wa][23:16] = dq[23:16];
                        if (dqm[3] == 0) mem[wa][31:24] = dq[31:24];
                    end else begin
                        // data leaves CL clock edges after this one; rd_v[k] falls out after k+1 more edges
                        rd_v[cl - 1] = 1; rd_d[cl - 1] = mem[wa];
                    end
                    if (addr[10]) begin row_open[ba] = 0; t_pre[ba] = $realtime + (cmd == 4'b0100 ? 14.0 : 0.0); end    // auto-precharge: write recovery first
                end
            end
            default: err("unknown command");
        endcase
    end
    initial begin : zero
        integer k; for (k = 0; k < 2097152; k = k + 1) mem[k] = 32'hxxxxxxxx;
    end
endmodule
