`timescale 1ns/1ps
// tb_boot_walk.v — serial boot walk that lays the flat address map over the
// fabric, then reads it back. For each physical CELL_ID (flat, 0..N*NC-1):
//   BOOT_COMMIT targeted at that ID -> logical input_address := ID, auth := 0xA5,
//   physical_mode := 0 (RUN). Walk to the next. (For basic testing logical==
//   physical, so the cpu_addr selector and the address payload coincide.)
// Then read back every cell's input_address + physical_mode to confirm the map.
module tb_boot_walk;
    localparam N=2, NB=2, NC=28;
    localparam TOTAL = N*NC;
    reg clk=0, rst=0; always #5 clk=~clk;
    reg [31:0] z_cmd_bus[0:N-1], z_cmd_data[0:N-1]; reg z_cpu_valid[0:N-1];
    wire [NB-1:0] bh_v[0:N-1]; wire [NB*16-1:0] bh_a[0:N-1]; wire [NB*32-1:0] bh_d[0:N-1];
    wire [15:0] z_out_addr[0:N-1]; wire [31:0] z_out_data[0:N-1]; wire z_out_valid[0:N-1];
    wire [NB-1:0] tv={NB{1'b0}}; wire [NB*16-1:0] ta=0; wire [NB*32-1:0] td=0;
    genvar i;
    generate for (i=0;i<N;i=i+1) begin: zr
        wire [31:0] cb=z_cmd_bus[i], cd=z_cmd_data[i]; wire cv=z_cpu_valid[i];
        wire [15:0] cpu_addr_w=(cb[7:0]==8'd1)?cd[31:16]:cd[15:0];
        wire pre=(cb[18:17]!=2'b00);
        wire cmd_valid_w=cv&&(cb[7:0]!=8'd1)&&((cb[7:0]!=8'd0)||pre);
        wire [NB-1:0] ein_v=(i==0)?tv:bh_v[i-1];
        wire [NB*16-1:0] ein_a=(i==0)?ta:bh_a[i-1];
        wire [NB*32-1:0] ein_d=(i==0)?td:bh_d[i-1];
        unicell_zone #(.NUM_CELLS(NC),.NUM_BRIDGES(NB),.ZONE_ID(i)) z (
            .clk(clk),.rst(rst),.cmd_bus(cb),.cmd_data(cd),.cmd_valid(cmd_valid_w),
            .cpu_addr(cpu_addr_w),.cpu_data(cd),.cpu_valid(cv),
            .out_addr(z_out_addr[i]),.out_data(z_out_data[i]),.out_valid(z_out_valid[i]),
            .armed_count(),.arrived_count(),.output_set_count(),
            .dbg0_cmd_latch(),.dbg0_input_addr(),.dbg0_output_addr(),.dbg0_a_data(),.cycle_count(),
            .bridge_n_in_valid(tv),.bridge_n_in_addr(ta),.bridge_n_in_data(td),.bridge_n_out_valid(),.bridge_n_out_addr(),.bridge_n_out_data(),
            .bridge_s_in_valid(tv),.bridge_s_in_addr(ta),.bridge_s_in_data(td),.bridge_s_out_valid(),.bridge_s_out_addr(),.bridge_s_out_data(),
            .bridge_e_in_valid(ein_v),.bridge_e_in_addr(ein_a),.bridge_e_in_data(ein_d),.bridge_e_out_valid(),.bridge_e_out_addr(),.bridge_e_out_data(),
            .bridge_w_in_valid(tv),.bridge_w_in_addr(ta),.bridge_w_in_data(td),.bridge_w_out_valid(bh_v[i]),.bridge_w_out_addr(bh_a[i]),.bridge_w_out_data(bh_d[i]));
    end endgenerate

    // hoist every cell's logical input_address + physical_mode
    wire [15:0] inaddr [0:TOTAL-1];
    wire        phys   [0:TOTAL-1];
    genvar zz, cc;
    generate for (zz=0; zz<N; zz=zz+1) begin: pz
        for (cc=0; cc<NC; cc=cc+1) begin: pc
            assign inaddr[zz*NC+cc] = zr[zz].z.cells.cell_array[cc].cell_inst.input_address;
            assign phys[zz*NC+cc]   = zr[zz].z.cells.cell_array[cc].cell_inst.physical_mode;
        end
    end endgenerate

    integer k;
    task bcast; input [31:0] cb,cd; begin
        @(negedge clk); for(k=0;k<N;k=k+1) begin z_cmd_bus[k]<=cb; z_cmd_data[k]<=cd; z_cpu_valid[k]<=1; end
        @(posedge clk); #1; for(k=0;k<N;k=k+1) z_cpu_valid[k]<=0; repeat(3)@(posedge clk); #1; end endtask

    integer c; integer bad;
    initial begin
        for(k=0;k<N;k=k+1) begin z_cmd_bus[k]=0; z_cmd_data[k]=0; z_cpu_valid[k]=0; end
        rst=1; repeat(5)@(posedge clk); #1; rst=0; repeat(2)@(posedge clk); #1;

        $display("=== BOOT WALK: %0d cells, BOOT_COMMIT targeted per flat CELL_ID ===", TOTAL);
        for (c=0;c<TOTAL;c=c+1) begin
            // opcode 7 (BOOT_COMMIT), cmd_data = {group=0, auth=0xA5, logical=c}
            // cpu_addr derived = cmd_data[15:0] = c -> targets physical CELL_ID c
            bcast(32'h00000007, (32'h00A50000 | c));
        end

        $display("=== READBACK: logical input_address + mode per cell ===");
        bad=0;
        for (c=0;c<TOTAL;c=c+1) begin
            if (inaddr[c]!==c[15:0] || phys[c]!==1'b0) begin
                bad=bad+1;
                if (bad<=8) $display("  MISMATCH cell %0d: input_addr=0x%04x (want 0x%04x) phys=%b (want 0)", c, inaddr[c], c[15:0], phys[c]);
            end
        end
        $display("  sample: cell0 in=0x%04x phys=%b | cell27 in=0x%04x phys=%b | cell28 in=0x%04x phys=%b | cell55 in=0x%04x phys=%b",
                 inaddr[0],phys[0], inaddr[27],phys[27], inaddr[28],phys[28], inaddr[55],phys[55]);
        if (bad==0) $display("\n  >>> BOOT WALK OK: all %0d cells hold logical addr == flat physical ID, all in RUN", TOTAL);
        else        $display("\n  >>> BOOT WALK FAIL: %0d cells wrong", bad);
        $finish;
    end
endmodule
