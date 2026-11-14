// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design implementation internals
// See Vtb_sys5.h for the primary calling header

#include "Vtb_sys5__pch.h"
#include "Vtb_sys5_uc_core_v2s__W1.h"

VL_ATTR_COLD void Vtb_sys5_uc_core_v2s__W1___ctor_var_reset(Vtb_sys5_uc_core_v2s__W1* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_sys5__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+          Vtb_sys5_uc_core_v2s__W1___ctor_var_reset\n"); );
    // Body
    vlSelf->clk = VL_RAND_RESET_I(1);
    vlSelf->rst = VL_RAND_RESET_I(1);
    vlSelf->start = VL_RAND_RESET_I(1);
    vlSelf->entry = VL_RAND_RESET_I(32);
    vlSelf->ce = VL_RAND_RESET_I(1);
    vlSelf->halted = VL_RAND_RESET_I(1);
    vlSelf->trap = VL_RAND_RESET_I(1);
    vlSelf->imem_addr = VL_RAND_RESET_I(30);
    vlSelf->imem_data = VL_RAND_RESET_I(32);
    vlSelf->ra_addr = VL_RAND_RESET_I(10);
    vlSelf->ra_data = VL_RAND_RESET_I(1);
    vlSelf->rb_addr = VL_RAND_RESET_I(10);
    vlSelf->rb_data = VL_RAND_RESET_I(1);
    vlSelf->rw_en = VL_RAND_RESET_I(1);
    vlSelf->rw_addr = VL_RAND_RESET_I(10);
    vlSelf->rw_data = VL_RAND_RESET_I(1);
    vlSelf->d_addr = VL_RAND_RESET_Q(35);
    vlSelf->d_we = VL_RAND_RESET_I(1);
    vlSelf->d_wdata = VL_RAND_RESET_I(1);
    vlSelf->d_rdata = VL_RAND_RESET_I(1);
    vlSelf->__PVT__state = VL_RAND_RESET_I(3);
    vlSelf->__PVT__pc = VL_RAND_RESET_I(32);
    vlSelf->__PVT__ir = VL_RAND_RESET_I(32);
    vlSelf->__PVT__addr = VL_RAND_RESET_I(32);
    vlSelf->__PVT__imm_sr = VL_RAND_RESET_I(32);
    vlSelf->__PVT__k = VL_RAND_RESET_I(5);
    vlSelf->__PVT__j = VL_RAND_RESET_I(3);
    vlSelf->__PVT__cy = VL_RAND_RESET_I(1);
    vlSelf->__PVT__nz = VL_RAND_RESET_I(1);
    vlSelf->__PVT__f_eq = VL_RAND_RESET_I(1);
    vlSelf->__PVT__f_lt = VL_RAND_RESET_I(1);
    vlSelf->__PVT__f_ltu = VL_RAND_RESET_I(1);
    vlSelf->__PVT__sgn = VL_RAND_RESET_I(1);
    vlSelf->__PVT__shamt_w = VL_RAND_RESET_I(5);
    vlSelf->__PVT__halted_r = VL_RAND_RESET_I(1);
    vlSelf->__PVT__trap_r = VL_RAND_RESET_I(1);
    vlSelf->__PVT__opc = VL_RAND_RESET_I(7);
    vlSelf->__PVT__rs2 = VL_RAND_RESET_I(5);
    vlSelf->__PVT__is_sys = VL_RAND_RESET_I(1);
    vlSelf->__PVT__imm = VL_RAND_RESET_I(32);
    vlSelf->__PVT__sh_i = VL_RAND_RESET_I(1);
    vlSelf->__PVT__is_shift = VL_RAND_RESET_I(1);
    vlSelf->__PVT__is_sll = VL_RAND_RESET_I(1);
    vlSelf->__PVT__is_cmp = VL_RAND_RESET_I(1);
    vlSelf->__PVT__is_slt = VL_RAND_RESET_I(1);
    vlSelf->__PVT__bad = VL_RAND_RESET_I(1);
    vlSelf->__PVT__shx = VL_RAND_RESET_I(1);
    vlSelf->__PVT__last_up = VL_RAND_RESET_I(1);
    vlSelf->__PVT__pc_rot = VL_RAND_RESET_I(32);
    vlSelf->__PVT__imm_rot = VL_RAND_RESET_I(32);
    vlSelf->__PVT__ia = VL_RAND_RESET_I(9);
    vlSelf->__PVT__va = VL_RAND_RESET_I(1);
    vlSelf->__PVT__vb = VL_RAND_RESET_I(1);
    vlSelf->__PVT__a_val = VL_RAND_RESET_I(1);
    vlSelf->__PVT__fill = VL_RAND_RESET_I(1);
    vlSelf->__PVT__X = VL_RAND_RESET_I(1);
    vlSelf->__PVT__Yr = VL_RAND_RESET_I(1);
    vlSelf->__PVT__inv = VL_RAND_RESET_I(1);
    vlSelf->__PVT__sum_c = VL_RAND_RESET_I(2);
    vlSelf->__PVT__pc_ins = VL_RAND_RESET_I(32);
    vlSelf->__PVT__addr_ins = VL_RAND_RESET_I(32);
    vlSelf->__PVT__nz_n = VL_RAND_RESET_I(1);
    vlSelf->__PVT__wd = VL_RAND_RESET_I(1);
    vlSelf->__PVT__sll_dir = VL_RAND_RESET_I(1);
    vlSelf->__PVT__exec_done = VL_RAND_RESET_I(1);
    vlSelf->__Vlvbound_hb777f176__0 = VL_RAND_RESET_I(1);
    vlSelf->__VdfgTmp_h586768a0__0 = 0;
    vlSelf->__VdfgTmp_h18c46dac__0 = 0;
    vlSelf->__Vdly__pc = VL_RAND_RESET_I(32);
}
