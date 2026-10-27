`timescale 1ns/1ps
// sdram_model_v1.v -- Our own behavioural model AND RULE CHECKER of an SDR SDRAM (64 Mbit as 2K rows x 256 columns x 4 banks x 32 bits, burst length 1), written from the public Micron SDR SDRAM datasheet rules (command codes, mode register, start-up order, timing minimums, refresh), NOT from NESTang. For simulation only. It counts every rule violation in `errors` and prints the first ones. The timing minimums used are those of a generic 133-166 MHz SDR part (tRCD 20 ns, tRP 20 ns, tRC 66 ns, tRAS 44 ns, tWR 15 ns); the embedded Gowin part's own figures have not been read, so these are stand-ins.
module sdram_model_v1 #(parameter [2:0] CL = 3'd2, parameter real TAC = 6.0, parameter real tRCD = 20.0, parameter real tRP = 20.0, parameter real tRC = 66.0, parameter real tRAS = 44.0, parameter real tWR = 15.0, parameter real tREFI_MAX = 15600.0) (
    input wire CLK, input wire CKE, input wire CS_N, input wire RAS_N, input wire CAS_N, input wire WE_N, input wire [10:0] A, input wire [1:0] BA, input wire [3:0] DQM, inout wire [31:0] DQ);
    reg [31:0] mem [0:2097151];
    reg act [0:3]; reg [10:0] row [0:3]; real t_act [0:3]; real t_ready [0:3];
    integer errors = 0, refreshes = 0, reads = 0, writes = 0, i;
    reg got_pre = 0, mode_set = 0, inited = 0; integer nref_init = 0; real t_mrs = 0, last_ref = -1, max_gap = 0, last_edge = 0, period = 37.0;
    reg [2:0] cl_set = 3'd2;
    reg rdp_v [0:3]; reg [20:0] rdp_a [0:3];
    reg dq_oe = 0; reg [31:0] dq_val = 0;
    assign DQ = dq_oe ? dq_val : 32'bz;
    task err(input [255:0] msg); begin errors = errors + 1; if (errors <= 10) $display("SDRAM RULE VIOLATION at %0t: %0s", $time, msg); end endtask
    initial begin for (i = 0; i < 4; i = i + 1) begin act[i] = 0; row[i] = 0; t_act[i] = -1000.0; t_ready[i] = 0; rdp_v[i] = 0; rdp_a[i] = 0; end end
    reg [20:0] ra; reg [31:0] w; integer b;
    always @(posedge CLK) begin
        real now; now = $realtime; if (last_edge != 0) period = now - last_edge; last_edge = now;
        // read data pipeline: stage 1 is the oldest; data comes out when a read has aged CL clocks
        for (i = 0; i < 3; i = i + 1) begin rdp_v[i] <= rdp_v[i+1]; rdp_a[i] <= rdp_a[i+1]; end   // shift (stage 0 = output stage)
        rdp_v[3] <= 1'b0;
        if (rdp_v[(CL == 3) ? 1 : 0] && 0) ;
        dq_oe <= #2.0 1'b0;
        if (CKE && !CS_N) begin
            case ({RAS_N, CAS_N, WE_N})
            3'b011: begin                                   // ACTIVE
                if (!inited) err("ACTIVE before start-up finished");
                if (act[BA]) err("ACTIVE to a bank with an open row");
                if (now < t_ready[BA]) err("ACTIVE too early after precharge (tRP/tRAS)");
                if (now - t_act[BA] < tRC) err("ACTIVE to ACTIVE same bank under tRC");
                act[BA] <= 1; row[BA] <= A; t_act[BA] <= now;
            end
            3'b101, 3'b100: begin                           // READ / WRITE
                if (!inited) err("READ/WRITE before start-up finished");
                if (!act[BA]) err("READ/WRITE to a bank with no open row");
                if (now - t_act[BA] < tRCD) err("READ/WRITE under tRCD");
                ra = {BA, row[BA], A[7:0]};
                if (WE_N == 1'b0) begin                     // write, data on DQ now (burst 1)
                    w = mem[ra];
                    for (b = 0; b < 4; b = b + 1) if (!DQM[b]) w[b*8 +: 8] = DQ[b*8 +: 8];
                    mem[ra] <= w; writes = writes + 1;
                end else begin reads = reads + 1; rdp_v[CL-1] <= 1'b1; rdp_a[CL-1] <= ra; end
                if (A[10]) begin act[BA] <= 0; t_ready[BA] <= now + ((WE_N == 1'b0) ? period + tWR : period) + tRP; if (now - t_act[BA] < tRAS) t_ready[BA] <= t_act[BA] + tRAS + tRP; end
                else err("read/write without auto-precharge (not used by our controller)");
            end
            3'b010: begin                                   // PRECHARGE
                if (!A[10]) err("single-bank PRECHARGE not expected");
                for (b = 0; b < 4; b = b + 1) begin if (act[b] && now - t_act[b] < tRAS) err("PRECHARGE under tRAS"); act[b] <= 0; t_ready[b] <= now + tRP; end
                got_pre <= 1; nref_init = 0;
            end
            3'b001: begin                                   // AUTO REFRESH
                for (b = 0; b < 4; b = b + 1) begin if (act[b]) err("AUTO REFRESH with an open row"); if (now < t_ready[b]) err("AUTO REFRESH too early (tRP)"); t_ready[b] <= now + tRC; end
                refreshes = refreshes + 1; if (!inited) nref_init = nref_init + 1;
                if (last_ref >= 0 && now - last_ref > max_gap) max_gap = now - last_ref;
                if (inited && last_ref >= 0 && now - last_ref > tREFI_MAX) err("refresh gap above the limit");
                last_ref = now;
            end
            3'b000: begin                                   // LOAD MODE REGISTER
                for (b = 0; b < 4; b = b + 1) if (act[b] || now < t_ready[b]) err("MODE REGISTER SET with a bank busy");
                if (!got_pre || nref_init < 2) err("MODE REGISTER SET before PRECHARGE ALL and 2 refreshes");
                if (A[2:0] != 3'b000 || A[3] != 1'b0 || A[6:4] != CL || A[9] != 1'b0) err("unexpected mode register value");
                mode_set <= 1; t_mrs <= now; inited <= 0;
            end
            3'b111: ;
            endcase
            if (mode_set && !inited && now - t_mrs >= 2 * period) inited <= 1;
        end
        // data out: the read launched CL-1 stages ago leaves now
        if (rdp_v[0]) begin dq_val <= #TAC mem[rdp_a[0]]; dq_oe <= #TAC 1'b1; end
    end
endmodule
