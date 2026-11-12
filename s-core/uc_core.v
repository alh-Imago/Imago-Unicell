// uc_core.v - width-selectable, digit-serial RV32I core (prototype)
//
// One ISA (RV32I subset), one binary, any datapath width W = 1,2,4,8,16,32
// bits per cycle.  "Fusing slices" == raising W: same results, fewer cycles.
//
// Everything is streamed one W-bit digit per cycle, least-significant digit
// first (except SLL, which runs most-significant first so it can work in place):
//   - register file is a W-wide RAM, depth 32*2^KW, address {reg, digit}
//   - data memory is a W-wide RAM,      address {word, digit}
//   - the only arithmetic is ONE W-bit adder with a carry flop
//   - pc is incremented / branched through the same adder (extra pass)
//   - shifts are a single funnel pass over the digit stream
//
// Per instruction: FETCH(1) SETUP(1) [PRE] EXEC(N) [WR2(N)] PC(N), N = 32/W
//
// Not supported (prototype): LB/LH/LBU/LHU/SB/SH, misaligned access, FENCE,
// CSRs, interrupts (by design).  EBREAK/ECALL halt.  Anything else traps.

module uc_core #(
    parameter W   = 4,
    parameter N   = 32 / W,
    parameter KW  = (N > 1) ? $clog2(N) : 1,
    parameter M   = (5 + W - 1) / W,       // digits needed for a 5-bit shift amount
    parameter SHW = M * W
) (
    input  wire              clk,
    input  wire              rst,
    output wire              halted,
    output wire              trap,
    // instruction memory: 32-bit words, async read
    output wire [29:0]       imem_addr,
    input  wire [31:0]       imem_data,
    // register file RAM: W wide, two async read ports, one write port
    output wire [KW+4:0]     ra_addr,
    input  wire [W-1:0]      ra_data,
    output wire [KW+4:0]     rb_addr,
    input  wire [W-1:0]      rb_data,
    output wire              rw_en,
    output wire [KW+4:0]     rw_addr,
    output wire [W-1:0]      rw_data,
    // data memory: W wide, async read
    output wire [KW+29:0]    d_addr,
    output wire              d_we,
    output wire [W-1:0]      d_wdata,
    input  wire [W-1:0]      d_rdata
);

    localparam S_FETCH = 3'd0, S_SETUP = 3'd1, S_PRE = 3'd2, S_EXEC = 3'd3,
               S_WR2   = 3'd4, S_PC    = 3'd5, S_HALT = 3'd6;

    reg [2:0]     state;
    reg [31:0]    pc, ir, addr;
    reg [KW-1:0]  k;
    reg [2:0]     j;
    reg           cy, nz, f_eq, f_lt, f_ltu, sgn;
    reg [SHW-1:0] shamt_w;
    reg           halted_r, trap_r;

    assign halted = halted_r;
    assign trap   = trap_r;
    assign imem_addr = pc[31:2];

    // ------------------------------------------------------------ decode
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

    // ------------------------------------------------------------ digit select
    wire in_pre  = (state == S_PRE);
    wire in_exec = (state == S_EXEC);
    wire in_wr2  = (state == S_WR2);
    wire in_pc   = (state == S_PC);
    wire shx     = in_exec & is_shift;

    wire first   = (k == 0);
    wire last_up = (k == N - 1);

    wire [W-1:0] pc_d  = pc  >> (k * W);
    wire [W-1:0] imm_d = imm >> (k * W);
    wire [W-1:0] c4_d  = 32'd4 >> (k * W);

    // shift amount -> digit offset q and bit offset r
    wire [4:0] shamt = shamt_w[4:0];
    wire [4:0] q = shamt / W;
    wire [4:0] r = shamt % W;

    wire signed [8:0] ks = $signed({{(9-KW){1'b0}}, k});
    wire signed [8:0] qs = $signed({4'b0, q});
    // left shift (descending k): hi=src[k-q] lo=src[k-q-1]
    // right shift (ascending k): lo=src[k+q] hi=src[k+q+1]
    wire signed [8:0] ia = is_sll ? (ks - qs)     : (ks + qs);
    wire signed [8:0] ib = is_sll ? (ks - qs - 1) : (ks + qs + 1);
    wire va = (ia >= 0) && (ia <= N - 1);
    wire vb = (ib >= 0) && (ib <= N - 1);

    wire [KW-1:0] j_k   = j;     // j < M <= N, so it always fits
    wire [KW-1:0] a_idx = in_pre ? (N - 1) : shx ? ia[KW-1:0] : k;
    wire [KW-1:0] b_idx = in_pre ? j_k : shx ? ib[KW-1:0] : k;
    assign ra_addr = {rs1, a_idx};
    assign rb_addr = {(shx ? rs1 : rs2), b_idx};

    wire a_zero = (rs1 == 5'd0);
    wire b_zero = shx ? (rs1 == 5'd0) : (rs2 == 5'd0);
    wire [W-1:0] a_val = a_zero ? {W{1'b0}} : ra_data;
    wire [W-1:0] b_val = b_zero ? {W{1'b0}} : rb_data;

    // ------------------------------------------------------------ shift funnel
    wire [W-1:0] fill = (is_sra & sgn) ? {W{1'b1}} : {W{1'b0}};
    wire [W-1:0] hi   = is_sll ? (va ? a_val : {W{1'b0}}) : (vb ? b_val : fill);
    wire [W-1:0] lo   = is_sll ? (vb ? b_val : {W{1'b0}}) : (va ? a_val : fill);
    wire [5:0]   fsh  = is_sll ? (W - r) : r;
    wire [2*W-1:0] cat = {hi, lo};
    wire [2*W-1:0] shd = cat >> fsh;
    wire [W-1:0] out_sh = shd[W-1:0];

    // ------------------------------------------------------------ the one adder
    reg  [W-1:0] X, Yr;
    reg          inv;
    always @* begin
        X   = a_val;
        Yr  = use_rb ? b_val : imm_d;
        inv = 1'b0;
        case (state)
            S_EXEC: begin
                if (is_lui)        X = {W{1'b0}};
                else if (is_auipc) X = pc_d;
                else if (is_jal) begin X = pc_d; Yr = c4_d; end
                else if (is_sub | is_cmp) inv = 1'b1;
            end
            S_WR2: begin X = pc_d; Yr = c4_d; end                 // jalr link
            S_PC:  begin X = pc_d; Yr = take ? imm_d : c4_d; end
            default: ;
        endcase
    end
    wire [W-1:0] Y   = inv ? ~Yr : Yr;
    wire         cin = first ? inv : cy;
    wire [W:0]   sum_c = {1'b0, X} + {1'b0, Y} + cin;

    reg [W-1:0] lg;
    always @* case (f3)
        3'b100:  lg = X ^ Yr;
        3'b110:  lg = X | Yr;
        default: lg = X & Yr;
    endcase
    wire [W-1:0] alu_out = is_logic ? lg : sum_c[W-1:0];

    // compare flags (valid after the last digit of an is_cmp pass)
    wire nz_n = (first ? 1'b0 : nz) | (sum_c[W-1:0] != 0);

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

    // ------------------------------------------------------------ writes
    reg          we;
    reg [W-1:0]  wd;
    always @* begin
        we = 1'b0;
        wd = alu_out;
        case (state)
            S_EXEC: begin
                if (is_shift)                         begin we = 1'b1; wd = out_sh; end
                else if (is_lui | is_auipc | is_jal)  we = 1'b1;
                else if ((is_opi | is_op) & ~is_cmp)  we = 1'b1;
            end
            S_WR2: begin
                if (is_ld)       begin we = 1'b1; wd = d_rdata; end
                else if (is_slt) begin we = 1'b1; wd = {W{1'b0}}; wd[0] = first & slt_flag; end
                else if (is_jalr) begin we = 1'b1; wd = sum_c[W-1:0]; end
            end
            default: ;
        endcase
    end
    assign rw_en   = we & (rd != 5'd0);
    assign rw_addr = {rd, k};
    assign rw_data = wd;

    assign d_addr  = {addr[31:2], k};
    assign d_we    = in_wr2 & is_st;
    assign d_wdata = b_val;

    // ------------------------------------------------------------ sequencer
    wire sll_dir   = is_shift & is_sll;
    wire exec_done = sll_dir ? (k == 0) : last_up;

    always @(posedge clk) begin
        if (rst) begin
            state <= S_FETCH; pc <= 32'd0; ir <= 32'd0; addr <= 32'd0;
            k <= 0; j <= 0; cy <= 1'b0; nz <= 1'b0;
            f_eq <= 1'b0; f_lt <= 1'b0; f_ltu <= 1'b0; sgn <= 1'b0;
            shamt_w <= 0; halted_r <= 1'b0; trap_r <= 1'b0;
        end else begin
            case (state)
                S_FETCH: begin
                    ir    <= imem_data;
                    state <= S_SETUP;
                end

                S_SETUP: begin
                    j       <= 0;
                    shamt_w <= sh_i ? rs2 : 0;
                    if (bad)         begin trap_r <= 1'b1; halted_r <= 1'b1; state <= S_HALT; end
                    else if (is_sys) begin halted_r <= 1'b1; state <= S_HALT; end
                    else if (is_shift) state <= S_PRE;
                    else begin k <= 0; state <= S_EXEC; end
                end

                S_PRE: begin   // gather shift amount (register shifts) and sign
                    sgn <= a_val[W-1];
                    if (is_op) shamt_w[j*W +: W] <= b_val;
                    if (j == (is_op ? M - 1 : 0)) begin
                        state <= S_EXEC;
                        k     <= is_sll ? (N - 1) : 0;
                    end else j <= j + 1;
                end

                S_EXEC: begin
                    cy <= sum_c[W];
                    if (is_cmp) begin
                        nz <= nz_n;
                        if (last_up) begin
                            f_eq  <= ~nz_n;
                            f_ltu <= ~sum_c[W];
                            f_lt  <= (X[W-1] != Yr[W-1]) ? X[W-1] : ~sum_c[W];
                        end
                    end
                    if (is_ld | is_st | is_jalr) addr[k*W +: W] <= sum_c[W-1:0];
                    if (exec_done) begin
                        k     <= 0;
                        state <= (is_ld | is_st | is_jalr | is_slt) ? S_WR2 : S_PC;
                    end else k <= sll_dir ? k - 1 : k + 1;
                end

                S_WR2: begin
                    cy <= sum_c[W];
                    if (last_up) begin k <= 0; state <= S_PC; end
                    else k <= k + 1;
                end

                S_PC: begin
                    if (is_jalr) begin
                        pc    <= {addr[31:1], 1'b0};
                        state <= S_FETCH;
                    end else begin
                        pc[k*W +: W] <= sum_c[W-1:0];
                        cy <= sum_c[W];
                        if (last_up) begin k <= 0; state <= S_FETCH; end
                        else k <= k + 1;
                    end
                end

                default: ;   // S_HALT
            endcase
        end
    end
endmodule
