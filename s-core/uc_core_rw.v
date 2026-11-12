// uc_core_rw.v - runtime-width digit-serial RV32I core (simulation model)
//
// Same micro-architecture and the same cycle counts as uc_core_v2, but the
// datapath width is chosen when a task STARTS (lw_in = log2 of bits per cycle,
// 0..5 -> 1..32) instead of at build time.  This models "fusing 1/2/4/8/16/32
// slices into one core at task start".  It is a behavioural model for system
// simulation: it works on 32-bit buses masked to the current width and is not
// meant to be area-optimal.
//
// Idle/finished cores sit in S_HALT with halted=1.  A `start` pulse while
// halted loads the entry pc and width and begins running.  EBREAK/ECALL end
// the task (halted=1 again); an illegal instruction ends it with trap=1.

module uc_core_rw (
    input  wire         clk,
    input  wire         rst,
    input  wire         start,
    input  wire [31:0]  entry,
    input  wire [2:0]   lw_in,
    output wire         halted,
    output wire         trap,
    output wire [2:0]   lw_cur,
    output wire [29:0]  imem_addr,
    input  wire [31:0]  imem_data,
    output wire [9:0]   ra_addr,
    input  wire [31:0]  ra_data,
    output wire [9:0]   rb_addr,
    input  wire [31:0]  rb_data,
    output wire         rw_en,
    output wire [9:0]   rw_addr,
    output wire [31:0]  rw_data,
    output wire [34:0]  d_addr,
    output wire         d_we,
    output wire [31:0]  d_wdata,
    input  wire [31:0]  d_rdata
);
    localparam S_FETCH = 3'd0, S_SETUP = 3'd1, S_PRE = 3'd2, S_EXEC = 3'd3,
               S_WR2   = 3'd4, S_PC    = 3'd5, S_HALT = 3'd6;

    reg [2:0]  state;
    reg [31:0] pc, ir, addr, imm_sr, shamt_w;
    reg [4:0]  k;
    reg [2:0]  j, lw_r;
    reg        cy, nz, f_eq, f_lt, f_ltu, sgn, halted_r, trap_r;

    assign halted    = halted_r;
    assign trap      = trap_r;
    assign lw_cur    = lw_r;
    assign imem_addr = pc[31:2];

    // ---- runtime width
    wire [5:0]  w    = 6'd1 << lw_r;
    wire [5:0]  nd   = 6'd32 >> lw_r;
    wire [5:0]  wm1  = w - 6'd1;
    wire [31:0] mask = (lw_r == 3'd5) ? 32'hFFFF_FFFF : ((32'd1 << w) - 32'd1);
    wire [4:0]  kmax = nd[4:0] - 5'd1;           // nd=32 wraps to 31
    wire [5:0]  m_rt = (6'd5 + w - 6'd1) / w;     // digits needed for a 5-bit shift amount

    // ---- decode
    wire [6:0] opc = ir[6:0];
    wire [2:0] f3  = ir[14:12];
    wire [6:0] f7  = ir[31:25];
    wire [4:0] rd  = ir[11:7];
    wire [4:0] rs1 = ir[19:15];
    wire [4:0] rs2 = ir[24:20];

    wire is_lui   = opc == 7'b0110111;
    wire is_auipc = opc == 7'b0010111;
    wire is_jal   = opc == 7'b1101111;
    wire is_jalr  = opc == 7'b1100111;
    wire is_br    = opc == 7'b1100011;
    wire is_ld    = opc == 7'b0000011;
    wire is_st    = opc == 7'b0100011;
    wire is_opi   = opc == 7'b0010011;
    wire is_op    = opc == 7'b0110011;
    wire is_sys   = opc == 7'b1110011;

    wire [31:0] imm_i = {{20{ir[31]}}, ir[31:20]};
    wire [31:0] imm_s = {{20{ir[31]}}, ir[31:25], ir[11:7]};
    wire [31:0] imm_b = {{19{ir[31]}}, ir[31], ir[7], ir[30:25], ir[11:8], 1'b0};
    wire [31:0] imm_u = {ir[31:12], 12'b0};
    wire [31:0] imm_j = {{11{ir[31]}}, ir[31], ir[19:12], ir[20], ir[30:21], 1'b0};
    wire [31:0] imm   = (is_lui | is_auipc) ? imm_u :
                         is_jal             ? imm_j :
                         is_br              ? imm_b :
                         is_st              ? imm_s : imm_i;

    wire sh_i     = is_opi & (f3 == 3'b001 | f3 == 3'b101);
    wire sh_r     = is_op  & (f3 == 3'b001 | f3 == 3'b101);
    wire is_shift = sh_i | sh_r;
    wire is_sll   = is_shift & (f3 == 3'b001);
    wire is_sra   = is_shift & (f3 == 3'b101) & f7[5];
    wire is_cmp   = is_br | ((is_opi | is_op) & (f3 == 3'b010 | f3 == 3'b011));
    wire is_slt   = is_cmp & ~is_br;
    wire is_logic = (is_opi | is_op) & (f3 == 3'b100 | f3 == 3'b110 | f3 == 3'b111);
    wire is_sub   = is_op & (f3 == 3'b000) & f7[5];
    wire use_rb   = is_op | is_br;

    wire bad = ~(is_lui | is_auipc | is_jal | is_jalr | is_br | is_ld | is_st |
                 is_opi | is_op | is_sys)
             | (is_jalr & f3 != 3'b000)
             | (is_br & (f3 == 3'b010 | f3 == 3'b011))
             | ((is_ld | is_st) & f3 != 3'b010)
             | (is_opi & f3 == 3'b001 & f7 != 7'b0000000)
             | (is_opi & f3 == 3'b101 & f7 != 7'b0000000 & f7 != 7'b0100000)
             | (is_op & f7 != 7'b0000000 &
                ~(f7 == 7'b0100000 & (f3 == 3'b000 | f3 == 3'b101)));

    // ---- digit select
    wire in_pre  = (state == S_PRE);
    wire in_exec = (state == S_EXEC);
    wire in_wr2  = (state == S_WR2);
    wire shx     = in_exec & is_shift;

    wire first   = (k == 5'd0);
    wire last_up = (k == kmax);

    wire [31:0] pc_d  = pc & mask;
    wire [31:0] imm_d = imm_sr & mask;
    wire [5:0]  kw    = k * w;
    wire [31:0] c4_d  = (32'd4 >> kw) & mask;

    wire [4:0] shamt = shamt_w[4:0];
    wire [4:0] q = shamt >> lw_r;
    wire [4:0] r = shamt & wm1[4:0];

    wire signed [8:0] ks   = $signed({4'b0, k});
    wire signed [8:0] qs   = $signed({4'b0, q});
    wire signed [8:0] nds1 = $signed({3'b0, nd}) - 9'sd1;
    wire signed [8:0] ia = is_sll ? (ks - qs)     : (ks + qs);
    wire signed [8:0] ib = is_sll ? (ks - qs - 1) : (ks + qs + 1);
    wire va = (ia >= 0) && (ia <= nds1);
    wire vb = (ib >= 0) && (ib <= nds1);

    wire [4:0] a_idx = in_pre ? kmax : shx ? ia[4:0] : k;
    wire [4:0] b_idx = in_pre ? {2'b0, j} : shx ? ib[4:0] : k;
    assign ra_addr = {rs1, a_idx};
    assign rb_addr = {(shx ? rs1 : rs2), b_idx};

    wire a_zero = (rs1 == 5'd0);
    wire b_zero = shx ? (rs1 == 5'd0) : (rs2 == 5'd0);
    wire [31:0] a_val = a_zero ? 32'd0 : (ra_data & mask);
    wire [31:0] b_val = b_zero ? 32'd0 : (rb_data & mask);

    // ---- shift funnel
    wire [31:0] fill = (is_sra & sgn) ? mask : 32'd0;
    wire [31:0] hi   = is_sll ? (va ? a_val : 32'd0) : (vb ? b_val : fill);
    wire [31:0] lo   = is_sll ? (vb ? b_val : 32'd0) : (va ? a_val : fill);
    wire [5:0]  fsh  = is_sll ? (w - {1'b0, r}) : {1'b0, r};
    wire [63:0] cat  = ({32'b0, hi} << w) | {32'b0, lo};
    wire [63:0] shd  = cat >> fsh;
    wire [31:0] out_sh = shd[31:0] & mask;

    // ---- the one adder
    reg  [31:0] X, Yr;
    reg         inv;
    always @* begin
        X = a_val; Yr = use_rb ? b_val : imm_d; inv = 1'b0;
        case (state)
            S_EXEC: begin
                if (is_lui)        X = 32'd0;
                else if (is_auipc) X = pc_d;
                else if (is_jal) begin X = pc_d; Yr = c4_d; end
                else if (is_sub | is_cmp) inv = 1'b1;
            end
            S_WR2: begin X = pc_d; Yr = c4_d; end
            S_PC:  begin X = pc_d; Yr = take ? imm_d : c4_d; end
            default: ;
        endcase
    end
    wire [31:0] Y        = inv ? (~Yr & mask) : Yr;
    wire        cin      = first ? inv : cy;
    wire [32:0] sum_full = {1'b0, X} + {1'b0, Y} + {32'b0, cin};
    wire [31:0] sum_d    = sum_full[31:0] & mask;
    wire [32:0] sfs      = sum_full >> w;
    wire        cout     = sfs[0];

    wire [31:0] pc_rot   = (pc     >> w) | (pc     << (6'd32 - w));
    wire [31:0] imm_rot  = (imm_sr >> w) | (imm_sr << (6'd32 - w));
    wire [31:0] pc_ins   = (pc     >> w) | (sum_d  << (6'd32 - w));
    wire [31:0] addr_ins = (addr   >> w) | (sum_d  << (6'd32 - w));

    reg [31:0] lg;
    always @* case (f3)
        3'b100:  lg = X ^ Yr;
        3'b110:  lg = X | Yr;
        default: lg = X & Yr;
    endcase
    wire [31:0] alu_out = is_logic ? lg : sum_d;

    wire nz_n = (first ? 1'b0 : nz) | (sum_d != 32'd0);
    wire [31:0] xsh = X >> wm1;
    wire [31:0] ysh = Yr >> wm1;

    reg cond;
    always @* case (f3)
        3'b000:  cond = f_eq;
        3'b001:  cond = ~f_eq;
        3'b100:  cond = f_lt;
        3'b101:  cond = ~f_lt;
        3'b110:  cond = f_ltu;
        3'b111:  cond = ~f_ltu;
        default: cond = 1'b0;
    endcase
    wire take     = is_jal | (is_br & cond);
    wire slt_flag = (f3 == 3'b010) ? f_lt : f_ltu;

    // ---- register-file write
    reg         we;
    reg [31:0]  wd;
    always @* begin
        we = 1'b0; wd = alu_out;
        case (state)
            S_EXEC: begin
                if (is_shift)                         begin we = 1'b1; wd = out_sh; end
                else if (is_lui | is_auipc | is_jal)  we = 1'b1;
                else if ((is_opi | is_op) & ~is_cmp)  we = 1'b1;
            end
            S_WR2: begin
                if (is_ld)        begin we = 1'b1; wd = d_rdata & mask; end
                else if (is_slt)  begin we = 1'b1; wd = 32'd0; wd[0] = first & slt_flag; end
                else if (is_jalr) begin we = 1'b1; wd = sum_d; end
            end
            default: ;
        endcase
    end
    assign rw_en   = we & (rd != 5'd0) & ~halted_r;
    assign rw_addr = {rd, k};
    assign rw_data = wd;

    assign d_addr  = {addr[31:2], k};
    assign d_we    = in_wr2 & is_st;
    assign d_wdata = b_val;

    // ---- sequencer
    wire exec_done = is_sll ? (k == 5'd0) : last_up;
    wire [5:0] mlast = m_rt - 6'd1;
    wire [5:0] jw    = {3'b0, j} * w;

    always @(posedge clk) begin
        if (rst) begin
            state <= S_HALT; pc <= 0; ir <= 0; addr <= 0; imm_sr <= 0; shamt_w <= 0;
            k <= 0; j <= 0; lw_r <= 0; cy <= 0; nz <= 0;
            f_eq <= 0; f_lt <= 0; f_ltu <= 0; sgn <= 0;
            halted_r <= 1'b1; trap_r <= 1'b0;
        end else if (start && state == S_HALT) begin
            pc <= entry; lw_r <= lw_in; k <= 0; halted_r <= 1'b0; trap_r <= 1'b0;
            state <= S_FETCH;
        end else begin
            case (state)
                S_FETCH: begin ir <= imem_data; state <= S_SETUP; end

                S_SETUP: begin
                    j       <= 0;
                    imm_sr  <= imm;
                    shamt_w <= sh_i ? {27'b0, rs2} : 32'd0;
                    if (bad)         begin trap_r <= 1'b1; halted_r <= 1'b1; state <= S_HALT; end
                    else if (is_sys) begin halted_r <= 1'b1; state <= S_HALT; end
                    else if (is_shift) state <= S_PRE;
                    else begin k <= 0; state <= S_EXEC; end
                end

                S_PRE: begin
                    sgn <= a_val[wm1[4:0]];
                    if (is_op) shamt_w <= (shamt_w & ~(mask << jw)) | (b_val << jw);
                    if ({3'b0, j} == (is_op ? mlast : 6'd0)) begin
                        state <= S_EXEC;
                        k     <= is_sll ? kmax : 5'd0;
                    end else j <= j + 3'd1;
                end

                S_EXEC: begin
                    cy <= cout;
                    if (is_cmp) begin
                        nz <= nz_n;
                        if (last_up) begin
                            f_eq  <= ~nz_n;
                            f_ltu <= ~cout;
                            f_lt  <= (xsh[0] != ysh[0]) ? xsh[0] : ~cout;
                        end
                    end
                    if (is_ld | is_st | is_jalr) addr <= addr_ins;
                    pc     <= pc_rot;
                    imm_sr <= imm_rot;
                    if (exec_done) begin
                        k     <= 0;
                        state <= (is_ld | is_st | is_jalr | is_slt) ? S_WR2 : S_PC;
                    end else k <= is_sll ? k - 5'd1 : k + 5'd1;
                end

                S_WR2: begin
                    cy <= cout;
                    pc <= pc_rot;
                    if (last_up) begin k <= 0; state <= S_PC; end
                    else k <= k + 5'd1;
                end

                S_PC: begin
                    if (is_jalr) begin
                        pc    <= {addr[31:1], 1'b0};
                        state <= S_FETCH;
                    end else begin
                        pc     <= pc_ins;
                        imm_sr <= imm_rot;
                        cy     <= cout;
                        if (last_up) begin k <= 0; state <= S_FETCH; end
                        else k <= k + 5'd1;
                    end
                end

                default: ;
            endcase
        end
    end
endmodule
