// uc_core_v2w2.v - uc_core_v2w with its ring rotations and the constant 4 written as explicit two-way choices (was: variable shift amounts, which the synthesiser built as barrel shifters).
// Same behaviour and clock counts as uc_core_v2w (ledger #1355).  Original header follows.
// uc_core_v2w.v - uc_core_v2 with the datapath width chosen at run time: input fz = 0 -> W=1, fz = 1 -> W=2 (a fused PAIR).
// F1 of the fusion plan (FUSION_PLAN.md, ledger #1354).  uc_core_v2 is NOT changed; this is a clone.
//   - the datapath is built 2 lanes wide (WM = 2); lane 1 is masked off when fz = 0, so unfused it must behave exactly as uc_core_v2 W=1
//   - fz must be held steady while a task runs (the pool version will latch it at task start)
//   - memory ports are 2 bits wide, addressed {register/word, digit k} with k 0..31 (unfused) or 0..15 (fused); WHAT sits at digit k
//     is the memory's business: a testbench RAM of whole 32-bit words returns bits [W*k +: W], so the stored data layout does not
//     depend on the width (open question 1 of the plan)
//   - the same FSM, so the same cycle counts: unfused = uc_core_v2 W=1, fused = uc_core_v2 W=2
// uc_core_v2.v - width-selectable, digit-serial RV32I core (prototype), v2
// v2 = v1 with pc, immediate and address held as digit shift registers
// (rotate / insert-at-top) instead of 32-bit registers behind variable-index muxes.
// Behaviour and cycle counts are identical to v1; only the area differs.
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

module uc_core_v2w2 #(
    parameter W   = 2,                     // lanes built (max width); this version supports W = 2 only
    parameter KW  = 5,                     // digit index width: k runs to 31 when unfused
    parameter SHW = 6
) (
    input  wire              clk,
    input  wire              rst,
    input  wire              fz,           // 1 = fused (2 bits per cycle), 0 = 1 bit per cycle
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
    reg [31:0]    pc, ir, addr, imm_sr;
    reg [KW-1:0]  k;
    reg [2:0]     j;
    wire [1:0]    lm   = fz ? 2'b11 : 2'b01;     // lane mask
    wire [2:0]    WE   = fz ? 3'd2 : 3'd1;       // effective width
    wire [5:0]    NE   = fz ? 6'd16 : 6'd32;     // digits per word
    wire [2:0]    ME   = fz ? 3'd3 : 3'd5;       // digits holding a 5-bit shift amount
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
    wire last_up = (k == NE - 1);

    wire [W-1:0] pc_d  = pc[W-1:0] & lm;             // head of the pc ring
    wire [W-1:0] imm_d = imm_sr[W-1:0] & lm;         // head of the immediate ring
    wire [W-1:0] c4_d  = (fz ? ((32'd4 >> (k * 2)) & 32'd3) : ((32'd4 >> k) & 32'd1));

    // ring helpers: rotate by one digit, or shift right inserting a new top digit
    // (written with shifts so W=32 degenerates cleanly: rotate = hold, insert = load)
    wire [31:0] pc_rot   = (fz ? {pc[1:0], pc[31:2]} : {pc[0], pc[31:1]});
    wire [31:0] imm_rot  = (fz ? {imm_sr[1:0], imm_sr[31:2]} : {imm_sr[0], imm_sr[31:1]});

    // shift amount -> digit offset q and bit offset r
    wire [4:0] shamt = shamt_w[4:0];
    wire [4:0] q = fz ? {1'b0, shamt[4:1]} : shamt;
    wire [4:0] r = fz ? {4'b0, shamt[0]} : 5'd0;

    wire signed [8:0] ks = $signed({{(9-KW){1'b0}}, k});
    wire signed [8:0] qs = $signed({4'b0, q});
    // left shift (descending k): hi=src[k-q] lo=src[k-q-1]
    // right shift (ascending k): lo=src[k+q] hi=src[k+q+1]
    wire signed [8:0] ia = is_sll ? (ks - qs)     : (ks + qs);
    wire signed [8:0] ib = is_sll ? (ks - qs - 1) : (ks + qs + 1);
    wire va = (ia >= 0) && (ia <= $signed({3'b0, NE}) - 1);
    wire vb = (ib >= 0) && (ib <= $signed({3'b0, NE}) - 1);

    wire [KW-1:0] j_k   = j;     // j < M <= N, so it always fits
    wire [KW-1:0] a_idx = in_pre ? (NE - 1) : shx ? ia[KW-1:0] : k;
    wire [KW-1:0] b_idx = in_pre ? j_k : shx ? ib[KW-1:0] : k;
    assign ra_addr = {rs1, a_idx};
    assign rb_addr = {(shx ? rs1 : rs2), b_idx};

    wire a_zero = (rs1 == 5'd0);
    wire b_zero = shx ? (rs1 == 5'd0) : (rs2 == 5'd0);
    wire [W-1:0] a_val = a_zero ? {W{1'b0}} : (ra_data & lm);
    wire [W-1:0] b_val = b_zero ? {W{1'b0}} : (rb_data & lm);

    // ------------------------------------------------------------ shift funnel
    wire [W-1:0] fill = (is_sra & sgn) ? lm : {W{1'b0}};
    wire [W-1:0] hi   = is_sll ? (va ? a_val : {W{1'b0}}) : (vb ? b_val : fill);
    wire [W-1:0] lo   = is_sll ? (vb ? b_val : {W{1'b0}}) : (va ? a_val : fill);
    wire [5:0]   fsh  = is_sll ? (WE - r) : r;
    wire [2*W-1:0] cat = fz ? {hi, lo} : {2'b00, hi[0], lo[0]};
    wire [2*W-1:0] shd = cat >> fsh;
    wire [W-1:0] out_sh = shd[W-1:0] & lm;

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
    wire [W-1:0] Y   = (inv ? ~Yr : Yr) & lm;
    wire         cin = first ? inv : cy;
    wire [W:0]   sum_c = {1'b0, X} + {1'b0, Y} + cin;
    wire [W-1:0] sum_d = sum_c[W-1:0] & lm;
    wire         cout  = fz ? sum_c[W] : sum_c[W-1];

    wire [31:0] pc_ins   = (fz ? {sum_d, pc[31:2]} : {sum_d[0], pc[31:1]});
    wire [31:0] addr_ins = (fz ? {sum_d, addr[31:2]} : {sum_d[0], addr[31:1]});

    reg [W-1:0] lg;
    always @* case (f3)
        3'b100:  lg = X ^ Yr;
        3'b110:  lg = X | Yr;
        default: lg = X & Yr;
    endcase
    wire [W-1:0] alu_out = is_logic ? (lg & lm) : sum_d;

    // compare flags (valid after the last digit of an is_cmp pass)
    wire nz_n = (first ? 1'b0 : nz) | (sum_d != 0);

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
                if (is_ld)       begin we = 1'b1; wd = d_rdata & lm; end
                else if (is_slt) begin we = 1'b1; wd = {W{1'b0}}; wd[0] = first & slt_flag; end
                else if (is_jalr) begin we = 1'b1; wd = sum_d; end
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
            state <= S_FETCH; pc <= 32'd0; ir <= 32'd0; addr <= 32'd0; imm_sr <= 32'd0;
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
                    imm_sr  <= imm;
                    shamt_w <= sh_i ? rs2 : 0;
                    if (bad)         begin trap_r <= 1'b1; halted_r <= 1'b1; state <= S_HALT; end
                    else if (is_sys) begin halted_r <= 1'b1; state <= S_HALT; end
                    else if (is_shift) state <= S_PRE;
                    else begin k <= 0; state <= S_EXEC; end
                end

                S_PRE: begin   // gather shift amount (register shifts) and sign
                    sgn <= fz ? a_val[1] : a_val[0];
                    if (is_op) begin if (fz) shamt_w[2*j +: 2] <= b_val; else shamt_w[j] <= b_val[0]; end
                    if (j == (is_op ? ME - 1 : 0)) begin
                        state <= S_EXEC;
                        k     <= is_sll ? (NE - 1) : 0;
                    end else j <= j + 1;
                end

                S_EXEC: begin
                    cy <= cout;
                    if (is_cmp) begin
                        nz <= nz_n;
                        if (last_up) begin
                            f_eq  <= ~nz_n;
                            f_ltu <= ~cout;
                            f_lt  <= ((fz ? X[1] : X[0]) != (fz ? Yr[1] : Yr[0])) ? (fz ? X[1] : X[0]) : ~cout;
                        end
                    end
                    if (is_ld | is_st | is_jalr) addr <= addr_ins;
                    pc     <= pc_rot;        // full N-step rotation = identity
                    imm_sr <= imm_rot;
                    if (exec_done) begin
                        k     <= 0;
                        state <= (is_ld | is_st | is_jalr | is_slt) ? S_WR2 : S_PC;
                    end else k <= sll_dir ? k - 1 : k + 1;
                end

                S_WR2: begin
                    cy <= cout;
                    pc <= pc_rot;
                    if (last_up) begin k <= 0; state <= S_PC; end
                    else k <= k + 1;
                end

                S_PC: begin
                    if (is_jalr) begin
                        pc    <= {addr[31:1], 1'b0};
                        state <= S_FETCH;
                    end else begin
                        pc     <= pc_ins;
                        imm_sr <= imm_rot;
                        cy <= cout;
                        if (last_up) begin k <= 0; state <= S_FETCH; end
                        else k <= k + 1;
                    end
                end

                default: ;   // S_HALT
            endcase
        end
    end
endmodule
