// sc_lane_sel: a lane whose controls and data come from EITHER its own slice's control (own_*) OR a block-level controller unit (unit_*), chosen by `adopted`
module sc_lane_sel (
    input  wire adopted,
    // from the slice's own control
    input  wire o_m, o_a, o_b, o_pcb, o_immb, o_c4b, o_use_rb, o_st_exec, o_st_wr2, o_st_pc, o_is_lui, o_is_auipc, o_is_jal, o_take, o_inv, o_is_logic,
    input  wire [2:0] o_f3, input wire o_cin,
    // from the controller unit
    input  wire u_m, u_a, u_b, u_pcb, u_immb, u_c4b, u_use_rb, u_st_exec, u_st_wr2, u_st_pc, u_is_lui, u_is_auipc, u_is_jal, u_take, u_inv, u_is_logic,
    input  wire [2:0] u_f3, input wire u_cin,
    output wire cout, sum_d, alu, xb, yb
);
    sc_lane lane (
        .m(adopted ? u_m : o_m), .a(adopted ? u_a : o_a), .b(adopted ? u_b : o_b), .pcb(adopted ? u_pcb : o_pcb), .immb(adopted ? u_immb : o_immb), .c4b(adopted ? u_c4b : o_c4b),
        .use_rb(adopted ? u_use_rb : o_use_rb), .st_exec(adopted ? u_st_exec : o_st_exec), .st_wr2(adopted ? u_st_wr2 : o_st_wr2), .st_pc(adopted ? u_st_pc : o_st_pc),
        .is_lui(adopted ? u_is_lui : o_is_lui), .is_auipc(adopted ? u_is_auipc : o_is_auipc), .is_jal(adopted ? u_is_jal : o_is_jal), .take(adopted ? u_take : o_take),
        .inv(adopted ? u_inv : o_inv), .is_logic(adopted ? u_is_logic : o_is_logic), .f3(adopted ? u_f3 : o_f3), .cin(adopted ? u_cin : o_cin),
        .cout(cout), .sum_d(sum_d), .alu(alu), .xb(xb), .yb(yb));
endmodule
