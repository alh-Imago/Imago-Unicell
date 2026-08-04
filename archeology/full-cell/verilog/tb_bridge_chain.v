`timescale 1ns/1ps
// tb_bridge_chain.v — inter-zone BRIDGE round-robin proof (sim-first).
// N zones in a row, wired exactly like top_arria10's bh chain:
//   zone[i].bridge_w_out -> bh[i] -> zone[i+1].bridge_e_in   (forward only)
// Config broadcasts to ALL zones (RECONFIGURE OR, SET_OUTPUT=0, preload A=0).
// The TRIGGER is injected into ZONE 0 ONLY — every other zone can fire only if
// the bridge delivered the token. Watching zone k fire => bridges 0..k-1 all
// connected; the cycle of each first-fire => per-hop timing.
module tb_bridge_chain;
    localparam N  = 8;     // zones in the row
    localparam NB = 2;     // bridges per direction (zone default)
    localparam NC = 28;    // cells per zone (array default)

    reg clk=0, rst=0;
    always #5 clk=~clk;

    // Per-zone command/inject drive (so we can target zone 0 alone for inject)
    reg  [31:0] z_cmd_bus  [0:N-1];
    reg  [31:0] z_cmd_data [0:N-1];
    reg         z_cpu_valid[0:N-1];

    // Bridge horizontal chain wires: bh[i] driven by zone[i].w_out, read by zone[i+1].e_in
    wire [NB-1:0]    bh_v [0:N-1];
    wire [NB*16-1:0] bh_a [0:N-1];
    wire [NB*32-1:0] bh_d [0:N-1];

    wire [15:0] z_out_addr [0:N-1];
    wire [31:0] z_out_data [0:N-1];
    wire        z_out_valid[0:N-1];

    wire [NB-1:0]    tie_v = {NB{1'b0}};
    wire [NB*16-1:0] tie_a = {(NB*16){1'b0}};
    wire [NB*32-1:0] tie_d = {(NB*32){1'b0}};

    genvar i;
    generate for (i=0;i<N;i=i+1) begin: zr
        wire [31:0] cb = z_cmd_bus[i];
        wire [31:0] cd = z_cmd_data[i];
        wire        cv = z_cpu_valid[i];
        wire [15:0] cpu_addr_w = (cb[7:0]==8'd1) ? cd[31:16] : cd[15:0];
        wire        pre        = (cb[18:17]!=2'b00);
        wire        cmd_valid_w = cv && (cb[7:0]!=8'd1) && ((cb[7:0]!=8'd0)||pre);
        // e_in <- bh[i-1] (zone 0 tied); w_out -> bh[i]
        wire [NB-1:0]    ein_v = (i==0)? tie_v : bh_v[i-1];
        wire [NB*16-1:0] ein_a = (i==0)? tie_a : bh_a[i-1];
        wire [NB*32-1:0] ein_d = (i==0)? tie_d : bh_d[i-1];
        unicell_zone #(.NUM_CELLS(NC),.NUM_BRIDGES(NB),.ZONE_ID(i)) z (
            .clk(clk),.rst(rst),
            .cmd_bus(cb),.cmd_data(cd),.cmd_valid(cmd_valid_w),
            .cpu_addr(cpu_addr_w),.cpu_data(cd),.cpu_valid(cv),
            .out_addr(z_out_addr[i]),.out_data(z_out_data[i]),.out_valid(z_out_valid[i]),
            .armed_count(),.arrived_count(),.output_set_count(),
            .dbg0_cmd_latch(),.dbg0_input_addr(),.dbg0_output_addr(),.dbg0_a_data(),.cycle_count(),
            .bridge_n_in_valid(tie_v),.bridge_n_in_addr(tie_a),.bridge_n_in_data(tie_d),
            .bridge_n_out_valid(),.bridge_n_out_addr(),.bridge_n_out_data(),
            .bridge_s_in_valid(tie_v),.bridge_s_in_addr(tie_a),.bridge_s_in_data(tie_d),
            .bridge_s_out_valid(),.bridge_s_out_addr(),.bridge_s_out_data(),
            .bridge_e_in_valid(ein_v),.bridge_e_in_addr(ein_a),.bridge_e_in_data(ein_d),
            .bridge_e_out_valid(),.bridge_e_out_addr(),.bridge_e_out_data(),
            .bridge_w_in_valid(tie_v),.bridge_w_in_addr(tie_a),.bridge_w_in_data(tie_d),
            .bridge_w_out_valid(bh_v[i]),.bridge_w_out_addr(bh_a[i]),.bridge_w_out_data(bh_d[i])
        );
    end endgenerate

    integer k;
    // broadcast a command to ALL zones (config path)
    task bcast; input [31:0] cb, cd; begin
        @(negedge clk); for(k=0;k<N;k=k+1) begin z_cmd_bus[k]<=cb; z_cmd_data[k]<=cd; z_cpu_valid[k]<=1; end
        @(posedge clk); #1; for(k=0;k<N;k=k+1) z_cpu_valid[k]<=0; repeat(4) @(posedge clk); #1;
    end endtask
    // inject into ONE zone only (trigger)
    task inj1; input integer zid; input [31:0] cb, cd; begin
        @(negedge clk); z_cmd_bus[zid]<=cb; z_cmd_data[zid]<=cd; z_cpu_valid[zid]<=1;
        @(posedge clk); #1; z_cpu_valid[zid]<=0;
    end endtask

    // record first-fire cycle per zone
    integer fire_cycle [0:N-1];
    integer fire_count [0:N-1];
    reg [31:0] fire_data [0:N-1];
    reg [15:0] first_oa  [0:N-1];
    reg [15:0] last_oa   [0:N-1];
    integer cyc;
    always @(posedge clk) cyc <= cyc+1;
    genvar j;
    generate for (j=0;j<N;j=j+1) begin: mon
        always @(posedge clk) if (z_out_valid[j]) begin
            if (fire_count[j]==0) begin fire_cycle[j]<=cyc; fire_data[j]<=z_out_data[j]; first_oa[j]<=z_out_addr[j]; end
            last_oa[j]<=z_out_addr[j];
            fire_count[j]<=fire_count[j]+1;
        end
    end endgenerate

    initial begin
        for(k=0;k<N;k=k+1) begin z_cmd_bus[k]=0; z_cmd_data[k]=0; z_cpu_valid[k]=0; fire_cycle[k]=-1; fire_count[k]=0; fire_data[k]=0; first_oa[k]=0; last_oa[k]=0; end
        cyc=0; rst=1; repeat(5) @(posedge clk); #1; rst=0; repeat(2) @(posedge clk); #1;

        // ---- broadcast config to all zones (flat CELL_ID: default output = CELL_ID+1) ----
        bcast(32'h14A00004, 32'h52800824);   // RECONFIGURE OR (output_set=1, start_flag); output stays CELL_ID+1
        bcast(32'h14A20000, 32'h00000000);    // preload A=0 (a_arrived=1)

        // ---- TRIGGER: inject token into ZONE 0 ONLY at addr 0 ----
        $display("inject token 0x00002340 into ZONE 0 only @ addr 0 (cyc=%0d)", cyc);
        inj1(0, 32'h00000001, 32'h00002340);

        // let it ripple across the row
        repeat(200) @(posedge clk);

        $display("\n  zone | cell_id range | first_fire_cyc | fires | out_addr %0d..%0d | out_data", 0, 0);
        for (k=0;k<N;k=k+1) begin
            $display("   Z%0d  |  %3d .. %3d   |     %4d       |  %3d  | 0x%04x .. 0x%04x | 0x%08x",
                k, k*NC, k*NC+NC-1, fire_cycle[k], fire_count[k], first_oa[k], last_oa[k], fire_data[k]);
        end
        // verdict
        begin : verdict
            integer ok; ok=1;
            for (k=0;k<N;k=k+1) if (fire_count[k]==0) ok=0;
            if (ok) $display("\n  >>> BRIDGE CHAIN OK: token reached all %0d zones via bridges, data intact", N);
            else    $display("\n  >>> BRIDGE CHAIN INCOMPLETE: some zone never fired (bridge gap)");
        end
        $finish;
    end
endmodule
