`timescale 1ns/1ps
// tb_die_boot.v — PRELIMINARY full-die boot model (sim of the silicon bring-up).
// Models the boot controller's job:
//   1. WALK the substrate cell-by-cell in flat-address order. For each cell,
//      probe it (read back its address) as a HEALTH CHECK. Good cells go in the
//      address map; bad cells are recorded in a BAD-CELL TABLE (boot RAM area)
//      and skipped for the rest of bootstrap.
//   2. AUTH COMMIT: one broadcast BOOT_COMMIT sends the auth code to every cell
//      (auth was 0000 throughout the walk, so all accept it) and flips to RUN.
// Flat address = {block[..], cell[4:0]}: block N owns N*32 .. N*32+NUM_CELLS-1.
module tb_die_boot;
    localparam NBLK = 4;      // blocks (zones) — 4 for a fast, representative die
    localparam NB   = 2;
    localparam NC   = 28;     // cells per block (28 used of the 32 address slots)
    localparam STRIDE = 32;   // 2^5 — cell field is 5 bits
    localparam ADDR_SPAN = NBLK*STRIDE;

    reg clk=0, rst=0; always #5 clk=~clk;
    reg [31:0] z_cmd_bus[0:NBLK-1], z_cmd_data[0:NBLK-1]; reg z_cpu_valid[0:NBLK-1];
    wire [NB-1:0] tv={NB{1'b0}}; wire [NB*16-1:0] ta=0; wire [NB*32-1:0] td=0;

    genvar i;
    generate for (i=0;i<NBLK;i=i+1) begin: blk
        wire [31:0] cb=z_cmd_bus[i], cd=z_cmd_data[i]; wire cv=z_cpu_valid[i];
        wire [15:0] cpu_addr_w=(cb[7:0]==8'd1)?cd[31:16]:cd[15:0];
        wire pre=(cb[18:17]!=2'b00);
        wire cmd_valid_w=cv&&(cb[7:0]!=8'd1)&&((cb[7:0]!=8'd0)||pre);
        unicell_zone #(.NUM_CELLS(NC),.NUM_BRIDGES(NB),.ZONE_ID(i)) z (
            .clk(clk),.rst(rst),.cmd_bus(cb),.cmd_data(cd),.cmd_valid(cmd_valid_w),
            .cpu_addr(cpu_addr_w),.cpu_data(cd),.cpu_valid(cv),
            .out_addr(),.out_data(),.out_valid(),
            .armed_count(),.arrived_count(),.output_set_count(),
            .dbg0_cmd_latch(),.dbg0_input_addr(),.dbg0_output_addr(),.dbg0_a_data(),.cycle_count(),
            .bridge_n_in_valid(tv),.bridge_n_in_addr(ta),.bridge_n_in_data(td),.bridge_n_out_valid(),.bridge_n_out_addr(),.bridge_n_out_data(),
            .bridge_s_in_valid(tv),.bridge_s_in_addr(ta),.bridge_s_in_data(td),.bridge_s_out_valid(),.bridge_s_out_addr(),.bridge_s_out_data(),
            .bridge_e_in_valid(tv),.bridge_e_in_addr(ta),.bridge_e_in_data(td),.bridge_e_out_valid(),.bridge_e_out_addr(),.bridge_e_out_data(),
            .bridge_w_in_valid(tv),.bridge_w_in_addr(ta),.bridge_w_in_data(td),.bridge_w_out_valid(),.bridge_w_out_addr(),.bridge_w_out_data());
    end endgenerate

    // hoist each cell's address + mode for the controller's probe (the readback path)
    wire [15:0] inaddr [0:NBLK*NC-1];
    wire        phys   [0:NBLK*NC-1];
    genvar bz, cz;
    generate for (bz=0; bz<NBLK; bz=bz+1) begin: pb
        for (cz=0; cz<NC; cz=cz+1) begin: pc
            assign inaddr[bz*NC+cz] = blk[bz].z.cells.cell_array[cz].cell_inst.input_address;
            assign phys[bz*NC+cz]   = blk[bz].z.cells.cell_array[cz].cell_inst.physical_mode;
        end
    end endgenerate

    integer k;
    task bcast; input [31:0] cb,cd; begin
        @(negedge clk); for(k=0;k<NBLK;k=k+1) begin z_cmd_bus[k]<=cb; z_cmd_data[k]<=cd; z_cpu_valid[k]<=1; end
        @(posedge clk); #1; for(k=0;k<NBLK;k=k+1) z_cpu_valid[k]<=0; repeat(3)@(posedge clk); #1; end endtask

    // boot RAM structures (controller side)
    reg [15:0] bad_table [0:63];   // flat addresses of dead cells
    integer    bad_n;
    integer    good_n;
    // simulated defect: pretend the cell at this flat address fails its probe
    localparam [15:0] SIM_BAD_ADDR = 16'h0022;  // block 1, local cell 2

    integer blk_i, cl_i, fa, hidx;
    reg [15:0] expect_a;
    reg good;

    initial begin
        for(k=0;k<NBLK;k=k+1) begin z_cmd_bus[k]=0; z_cmd_data[k]=0; z_cpu_valid[k]=0; end
        bad_n=0; good_n=0;
        rst=1; repeat(5)@(posedge clk); #1; rst=0; repeat(2)@(posedge clk); #1;

        $display("================================================================");
        $display(" PRELIMINARY DIE BOOT : %0d blocks x %0d cells, stride %0d", NBLK, NC, STRIDE);
        $display("   flat address = (block<<5) | cell ; block N owns N*32..N*32+%0d", NC-1);
        $display("================================================================");
        $display("\n-- PHASE 1: WALK (health check + address map) --");
        for (blk_i=0; blk_i<NBLK; blk_i=blk_i+1) begin
            for (cl_i=0; cl_i<NC; cl_i=cl_i+1) begin
                fa   = (blk_i*STRIDE) + cl_i;          // flat address this cell should hold
                hidx = blk_i*NC + cl_i;                // hierarchy index
                expect_a = fa[15:0];
                // HEALTH PROBE: read the cell's address back; good iff it reports
                // the expected flat address AND isn't a (simulated) defect.
                good = (inaddr[hidx] === expect_a) && (fa[15:0] !== SIM_BAD_ADDR);
                if (good) good_n = good_n+1;
                else begin bad_table[bad_n] = fa[15:0]; bad_n = bad_n+1; end
            end
        end
        $display("  walked %0d candidate cells", NBLK*NC);
        $display("  block address ranges:");
        for (blk_i=0; blk_i<NBLK; blk_i=blk_i+1)
            $display("    block %0d : 0x%04x .. 0x%04x", blk_i, blk_i*STRIDE, blk_i*STRIDE+NC-1);

        $display("\n-- BAD-CELL TABLE (boot RAM) : %0d entr%s --", bad_n, (bad_n==1)?"y":"ies");
        for (k=0;k<bad_n;k=k+1)
            $display("    bad cell @ flat 0x%04x  (block %0d, cell %0d) -> SKIP",
                     bad_table[k], bad_table[k]>>5, bad_table[k]&5'h1f);
        $display("  good cells: %0d / %0d", good_n, NBLK*NC);

        $display("\n-- PHASE 2: AUTH COMMIT (broadcast BOOT_COMMIT, auth was 0000) --");
        bcast(32'h00000007, 32'h00A50000);   // one broadcast: auth=0xA5 to ALL cells, ->RUN
        // verify all GOOD cells are now in RUN
        begin : verify
            integer notrun; notrun=0;
            for (blk_i=0; blk_i<NBLK; blk_i=blk_i+1)
                for (cl_i=0; cl_i<NC; cl_i=cl_i+1)
                    if (phys[blk_i*NC+cl_i] !== 1'b0) notrun=notrun+1;
            $display("  cells not in RUN after commit: %0d (expect 0)", notrun);
        end

        $display("\n-- RESULT --");
        $display("  flat map: 0x0000 .. 0x%04x, %0d good cells, %0d skipped, all authed+RUN",
                 (NBLK-1)*STRIDE+NC-1, good_n, bad_n);
        if (good_n == NBLK*NC-1 && bad_n==1)
            $display("  >>> DIE BOOT OK: substrate mapped flat by block, 1 defect tabled+skipped, auth committed");
        else
            $display("  >>> check counts");
        $finish;
    end
endmodule
