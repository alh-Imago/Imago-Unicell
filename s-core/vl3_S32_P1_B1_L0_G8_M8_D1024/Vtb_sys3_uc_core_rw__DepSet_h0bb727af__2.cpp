// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design implementation internals
// See Vtb_sys3.h for the primary calling header

#include "Vtb_sys3__pch.h"
#include "Vtb_sys3__Syms.h"
#include "Vtb_sys3_uc_core_rw.h"

extern const VlUnpacked<CData/*0:0*/, 64> Vtb_sys3__ConstPool__TABLE_h2a0441a0_0;

VL_INLINE_OPT void Vtb_sys3_uc_core_rw___nba_sequent__TOP__tb_sys3__DOT__dut__DOT__slot__BRA__22__KET____DOT__core__0(Vtb_sys3_uc_core_rw* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_sys3__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+          Vtb_sys3_uc_core_rw___nba_sequent__TOP__tb_sys3__DOT__dut__DOT__slot__BRA__22__KET____DOT__core__0\n"); );
    // Init
    CData/*0:0*/ __PVT__shx;
    __PVT__shx = 0;
    IData/*31:0*/ __PVT__pc_d;
    __PVT__pc_d = 0;
    IData/*31:0*/ __PVT__imm_d;
    __PVT__imm_d = 0;
    IData/*31:0*/ __PVT__c4_d;
    __PVT__c4_d = 0;
    SData/*8:0*/ __PVT__qs;
    __PVT__qs = 0;
    SData/*8:0*/ __PVT__ia;
    __PVT__ia = 0;
    CData/*0:0*/ __PVT__va;
    __PVT__va = 0;
    CData/*0:0*/ __PVT__vb;
    __PVT__vb = 0;
    IData/*31:0*/ __PVT__fill;
    __PVT__fill = 0;
    IData/*31:0*/ __PVT__X;
    __PVT__X = 0;
    IData/*31:0*/ __PVT__Yr;
    __PVT__Yr = 0;
    CData/*0:0*/ __PVT__inv;
    __PVT__inv = 0;
    QData/*32:0*/ __PVT__sum_full;
    __PVT__sum_full = 0;
    IData/*31:0*/ __PVT__sum_d;
    __PVT__sum_d = 0;
    CData/*0:0*/ __PVT__cond;
    __PVT__cond = 0;
    CData/*0:0*/ __VdfgExtracted_h62388771__0;
    __VdfgExtracted_h62388771__0 = 0;
    IData/*31:0*/ __VdfgTmp_h41a48239__0;
    __VdfgTmp_h41a48239__0 = 0;
    CData/*0:0*/ __VdfgTmp_h2cd83c5b__0;
    __VdfgTmp_h2cd83c5b__0 = 0;
    CData/*0:0*/ __VdfgTmp_he83b8d53__0;
    __VdfgTmp_he83b8d53__0 = 0;
    CData/*0:0*/ __VdfgTmp_h18c46dac__0;
    __VdfgTmp_h18c46dac__0 = 0;
    CData/*0:0*/ __VdfgTmp_hd9b60348__0;
    __VdfgTmp_hd9b60348__0 = 0;
    CData/*5:0*/ __VdfgTmp_h933689ae__0;
    __VdfgTmp_h933689ae__0 = 0;
    CData/*5:0*/ __Vtableidx23;
    __Vtableidx23 = 0;
    CData/*2:0*/ __Vdly__state;
    __Vdly__state = 0;
    IData/*31:0*/ __Vdly__addr;
    __Vdly__addr = 0;
    IData/*31:0*/ __Vdly__shamt_w;
    __Vdly__shamt_w = 0;
    CData/*4:0*/ __Vdly__k;
    __Vdly__k = 0;
    CData/*2:0*/ __Vdly__j;
    __Vdly__j = 0;
    // Body
    __Vdly__addr = vlSelf->__PVT__addr;
    __Vdly__j = vlSelf->__PVT__j;
    __Vdly__shamt_w = vlSelf->__PVT__shamt_w;
    __Vdly__state = vlSelf->__PVT__state;
    __Vdly__k = vlSelf->__PVT__k;
    if (vlSymsp->TOP.tb_sys3__DOT__rst) {
        __Vdly__state = 6U;
        vlSelf->__PVT__pc = 0U;
        vlSelf->__PVT__ir = 0U;
        __Vdly__addr = 0U;
        vlSelf->__PVT__imm_sr = 0U;
        __Vdly__shamt_w = 0U;
        __Vdly__k = 0U;
        __Vdly__j = 0U;
        vlSelf->__PVT__lw_r = 0U;
        vlSelf->__PVT__cy = 0U;
        vlSelf->__PVT__nz = 0U;
        vlSelf->__PVT__f_eq = 0U;
        vlSelf->__PVT__f_lt = 0U;
        vlSelf->__PVT__f_ltu = 0U;
        vlSelf->__PVT__sgn = 0U;
        vlSelf->__PVT__halted_r = 1U;
        vlSelf->__PVT__trap_r = 0U;
    } else if (((vlSymsp->TOP.tb_sys3__DOT__dut__DOT__start_v 
                 >> 0x16U) & (6U == (IData)(vlSelf->__PVT__state)))) {
        vlSelf->__PVT__pc = vlSymsp->TOP.tb_sys3__DOT__dut__DOT__launch_entry;
        vlSelf->__PVT__lw_r = vlSymsp->TOP.tb_sys3__DOT__dut__DOT__launch_lw;
        __Vdly__k = 0U;
        vlSelf->__PVT__halted_r = 0U;
        vlSelf->__PVT__trap_r = 0U;
        __Vdly__state = 0U;
    } else if ((4U & (IData)(vlSelf->__PVT__state))) {
        if ((1U & (~ ((IData)(vlSelf->__PVT__state) 
                      >> 1U)))) {
            if ((1U & (IData)(vlSelf->__PVT__state))) {
                if ((0x67U == (IData)(vlSelf->__PVT__opc))) {
                    vlSelf->__PVT__pc = (0xfffffffeU 
                                         & vlSelf->__PVT__addr);
                    __Vdly__state = 0U;
                } else {
                    vlSelf->__PVT__pc = (vlSelf->__VdfgTmp_he4828306__0 
                                         | vlSelf->__VdfgTmp_h7980eff3__0);
                    vlSelf->__PVT__imm_sr = vlSelf->__PVT__imm_rot;
                    vlSelf->__PVT__cy = vlSelf->__PVT__cout;
                    if (vlSelf->__PVT__last_up) {
                        __Vdly__k = 0U;
                        __Vdly__state = 0U;
                    } else {
                        __Vdly__k = (0x1fU & ((IData)(1U) 
                                              + (IData)(vlSelf->__PVT__k)));
                    }
                }
            } else {
                vlSelf->__PVT__cy = vlSelf->__PVT__cout;
                vlSelf->__PVT__pc = vlSelf->__PVT__pc_rot;
                if (vlSelf->__PVT__last_up) {
                    __Vdly__k = 0U;
                    __Vdly__state = 5U;
                } else {
                    __Vdly__k = (0x1fU & ((IData)(1U) 
                                          + (IData)(vlSelf->__PVT__k)));
                }
            }
        }
    } else if ((2U & (IData)(vlSelf->__PVT__state))) {
        if ((1U & (IData)(vlSelf->__PVT__state))) {
            vlSelf->__PVT__cy = vlSelf->__PVT__cout;
            if (vlSelf->__PVT__is_cmp) {
                vlSelf->__PVT__nz = vlSelf->__PVT__nz_n;
                if (vlSelf->__PVT__last_up) {
                    vlSelf->__PVT__f_eq = (1U & (~ (IData)(vlSelf->__PVT__nz_n)));
                    vlSelf->__PVT__f_ltu = (1U & (~ (IData)(vlSelf->__PVT__cout)));
                    vlSelf->__PVT__f_lt = (1U & (((1U 
                                                   & vlSelf->__PVT__xsh) 
                                                  != 
                                                  (1U 
                                                   & vlSelf->__PVT__ysh))
                                                  ? vlSelf->__PVT__xsh
                                                  : 
                                                 (~ (IData)(vlSelf->__PVT__cout))));
                }
            }
            if ((((3U == (IData)(vlSelf->__PVT__opc)) 
                  | (0x23U == (IData)(vlSelf->__PVT__opc))) 
                 | (0x67U == (IData)(vlSelf->__PVT__opc)))) {
                __Vdly__addr = vlSelf->__PVT__addr_ins;
            }
            vlSelf->__PVT__pc = vlSelf->__PVT__pc_rot;
            vlSelf->__PVT__imm_sr = vlSelf->__PVT__imm_rot;
            if (vlSelf->__PVT__exec_done) {
                __Vdly__k = 0U;
                __Vdly__state = (((((3U == (IData)(vlSelf->__PVT__opc)) 
                                    | (0x23U == (IData)(vlSelf->__PVT__opc))) 
                                   | (0x67U == (IData)(vlSelf->__PVT__opc))) 
                                  | (IData)(vlSelf->__PVT__is_slt))
                                  ? 4U : 5U);
            } else {
                __Vdly__k = (0x1fU & ((IData)(vlSelf->__PVT__is_sll)
                                       ? ((IData)(vlSelf->__PVT__k) 
                                          - (IData)(1U))
                                       : ((IData)(1U) 
                                          + (IData)(vlSelf->__PVT__k))));
            }
        } else {
            if ((0x33U == (IData)(vlSelf->__PVT__opc))) {
                __Vdly__shamt_w = ((vlSelf->__PVT__shamt_w 
                                    & (~ VL_SHIFTL_III(32,32,6, vlSelf->__PVT__mask, (IData)(vlSelf->__PVT__jw)))) 
                                   | VL_SHIFTL_III(32,32,6, vlSelf->d_wdata, (IData)(vlSelf->__PVT__jw)));
            }
            vlSelf->__PVT__sgn = (1U & (vlSelf->__PVT__a_val 
                                        >> (0x1fU & (IData)(vlSelf->__PVT__wm1))));
            if (((IData)(vlSelf->__PVT__j) == ((0x33U 
                                                == (IData)(vlSelf->__PVT__opc))
                                                ? (IData)(vlSelf->__PVT__mlast)
                                                : 0U))) {
                __Vdly__state = 3U;
                __Vdly__k = ((IData)(vlSelf->__PVT__is_sll)
                              ? (0x1fU & ((IData)(vlSelf->__PVT__nd) 
                                          - (IData)(1U)))
                              : 0U);
            } else {
                __Vdly__j = (7U & ((IData)(1U) + (IData)(vlSelf->__PVT__j)));
            }
        }
    } else if ((1U & (IData)(vlSelf->__PVT__state))) {
        __Vdly__j = 0U;
        vlSelf->__PVT__imm_sr = vlSelf->__PVT__imm;
        __Vdly__shamt_w = ((IData)(vlSelf->__PVT__sh_i)
                            ? (IData)(vlSelf->__PVT__rs2)
                            : 0U);
        if (vlSelf->__PVT__bad) {
            vlSelf->__PVT__trap_r = 1U;
            vlSelf->__PVT__halted_r = 1U;
            __Vdly__state = 6U;
        } else if (vlSelf->__PVT__is_sys) {
            vlSelf->__PVT__halted_r = 1U;
            __Vdly__state = 6U;
        } else if (vlSelf->__PVT__is_shift) {
            __Vdly__state = 2U;
        } else {
            __Vdly__k = 0U;
            __Vdly__state = 3U;
        }
    } else {
        vlSelf->__PVT__ir = vlSymsp->TOP.tb_sys3__DOT__dut__DOT__slot__BRA__22__KET____DOT__id;
        __Vdly__state = 1U;
    }
    vlSelf->__PVT__addr = __Vdly__addr;
    vlSelf->__PVT__j = __Vdly__j;
    vlSelf->__PVT__shamt_w = __Vdly__shamt_w;
    vlSelf->__PVT__state = __Vdly__state;
    vlSelf->__PVT__k = __Vdly__k;
    vlSelf->d_addr = (((QData)((IData)((vlSelf->__PVT__addr 
                                        >> 2U))) << 5U) 
                      | (QData)((IData)(vlSelf->__PVT__k)));
    vlSelf->__PVT__wm1 = (0x3fU & (((IData)(1U) << (IData)(vlSelf->__PVT__lw_r)) 
                                   - (IData)(1U)));
    vlSelf->__PVT__mlast = (0x3fU & (VL_DIV_III(6, 
                                                (0x3fU 
                                                 & ((IData)(4U) 
                                                    + 
                                                    ((IData)(1U) 
                                                     << (IData)(vlSelf->__PVT__lw_r)))), 
                                                (0x3fU 
                                                 & ((IData)(1U) 
                                                    << (IData)(vlSelf->__PVT__lw_r)))) 
                                     - (IData)(1U)));
    vlSelf->__PVT__nd = (0x3fU & (0x20U >> (IData)(vlSelf->__PVT__lw_r)));
    vlSelf->__PVT__jw = (0x3fU & ((IData)(vlSelf->__PVT__j) 
                                  * (0x3fU & ((IData)(1U) 
                                              << (IData)(vlSelf->__PVT__lw_r)))));
    vlSelf->__PVT__imm_rot = (VL_SHIFTR_III(32,32,6, vlSelf->__PVT__imm_sr, 
                                            (0x3fU 
                                             & ((IData)(1U) 
                                                << (IData)(vlSelf->__PVT__lw_r)))) 
                              | VL_SHIFTL_III(32,32,6, vlSelf->__PVT__imm_sr, 
                                              (0x3fU 
                                               & ((IData)(0x20U) 
                                                  - 
                                                  ((IData)(1U) 
                                                   << (IData)(vlSelf->__PVT__lw_r))))));
    vlSelf->__PVT__last_up = ((IData)(vlSelf->__PVT__k) 
                              == (0x1fU & ((0x3fU & 
                                            (0x20U 
                                             >> (IData)(vlSelf->__PVT__lw_r))) 
                                           - (IData)(1U))));
    vlSelf->__VdfgTmp_he4828306__0 = VL_SHIFTR_III(32,32,6, vlSelf->__PVT__pc, 
                                                   (0x3fU 
                                                    & ((IData)(1U) 
                                                       << (IData)(vlSelf->__PVT__lw_r))));
    __VdfgTmp_h933689ae__0 = (0x1fU & (vlSelf->__PVT__shamt_w 
                                       & ((0x3fU & 
                                           ((IData)(1U) 
                                            << (IData)(vlSelf->__PVT__lw_r))) 
                                          - (IData)(1U))));
    __PVT__qs = (0x1fU & ((0x1fU & vlSelf->__PVT__shamt_w) 
                          >> (IData)(vlSelf->__PVT__lw_r)));
    vlSelf->__PVT__mask = ((5U == (IData)(vlSelf->__PVT__lw_r))
                            ? 0xffffffffU : (VL_SHIFTL_III(32,32,6, (IData)(1U), 
                                                           (0x3fU 
                                                            & ((IData)(1U) 
                                                               << (IData)(vlSelf->__PVT__lw_r)))) 
                                             - (IData)(1U)));
    vlSelf->__PVT__rs2 = (0x1fU & (vlSelf->__PVT__ir 
                                   >> 0x14U));
    vlSelf->__PVT__is_sys = (0x73U == (0x7fU & vlSelf->__PVT__ir));
    vlSelf->__PVT__opc = (0x7fU & vlSelf->__PVT__ir);
    __VdfgTmp_h2cd83c5b__0 = ((0x37U == (0x7fU & vlSelf->__PVT__ir)) 
                              | (0x17U == (0x7fU & vlSelf->__PVT__ir)));
    __Vtableidx23 = (((IData)(vlSelf->__PVT__f_eq) 
                      << 5U) | (((IData)(vlSelf->__PVT__f_lt) 
                                 << 4U) | (((IData)(vlSelf->__PVT__f_ltu) 
                                            << 3U) 
                                           | (7U & 
                                              (vlSelf->__PVT__ir 
                                               >> 0xcU)))));
    __PVT__cond = Vtb_sys3__ConstPool__TABLE_h2a0441a0_0
        [__Vtableidx23];
    __VdfgTmp_hd9b60348__0 = ((2U == (7U & (vlSelf->__PVT__ir 
                                            >> 0xcU))) 
                              | (3U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))));
    __VdfgTmp_h18c46dac__0 = ((0x13U == (0x7fU & vlSelf->__PVT__ir)) 
                              | (0x33U == (0x7fU & vlSelf->__PVT__ir)));
    __VdfgTmp_he83b8d53__0 = ((1U == (7U & (vlSelf->__PVT__ir 
                                            >> 0xcU))) 
                              | (5U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))));
    vlSelf->__PVT__pc_rot = (vlSelf->__VdfgTmp_he4828306__0 
                             | VL_SHIFTL_III(32,32,6, vlSelf->__PVT__pc, 
                                             (0x3fU 
                                              & ((IData)(0x20U) 
                                                 - 
                                                 ((IData)(1U) 
                                                  << (IData)(vlSelf->__PVT__lw_r))))));
    __PVT__pc_d = (vlSelf->__PVT__pc & vlSelf->__PVT__mask);
    __PVT__imm_d = (vlSelf->__PVT__imm_sr & vlSelf->__PVT__mask);
    __PVT__c4_d = (VL_SHIFTR_III(32,32,6, 4U, (0x3fU 
                                               & ((IData)(vlSelf->__PVT__k) 
                                                  * 
                                                  (0x3fU 
                                                   & ((IData)(1U) 
                                                      << (IData)(vlSelf->__PVT__lw_r)))))) 
                   & vlSelf->__PVT__mask);
    vlSelf->__PVT__imm = ((IData)(__VdfgTmp_h2cd83c5b__0)
                           ? (0xfffff000U & vlSelf->__PVT__ir)
                           : ((0x6fU == (0x7fU & vlSelf->__PVT__ir))
                               ? (((- (IData)((vlSelf->__PVT__ir 
                                               >> 0x1fU))) 
                                   << 0x15U) | ((0x100000U 
                                                 & (vlSelf->__PVT__ir 
                                                    >> 0xbU)) 
                                                | ((0xff000U 
                                                    & vlSelf->__PVT__ir) 
                                                   | ((0x800U 
                                                       & (vlSelf->__PVT__ir 
                                                          >> 9U)) 
                                                      | (0x7feU 
                                                         & (vlSelf->__PVT__ir 
                                                            >> 0x14U))))))
                               : ((0x63U == (0x7fU 
                                             & vlSelf->__PVT__ir))
                                   ? (((- (IData)((vlSelf->__PVT__ir 
                                                   >> 0x1fU))) 
                                       << 0xdU) | (
                                                   (0x1000U 
                                                    & (vlSelf->__PVT__ir 
                                                       >> 0x13U)) 
                                                   | ((0x800U 
                                                       & (vlSelf->__PVT__ir 
                                                          << 4U)) 
                                                      | ((0x7e0U 
                                                          & (vlSelf->__PVT__ir 
                                                             >> 0x14U)) 
                                                         | (0x1eU 
                                                            & (vlSelf->__PVT__ir 
                                                               >> 7U))))))
                                   : ((0x23U == (0x7fU 
                                                 & vlSelf->__PVT__ir))
                                       ? (((- (IData)(
                                                      (vlSelf->__PVT__ir 
                                                       >> 0x1fU))) 
                                           << 0xcU) 
                                          | ((0xfe0U 
                                              & (vlSelf->__PVT__ir 
                                                 >> 0x14U)) 
                                             | (0x1fU 
                                                & (vlSelf->__PVT__ir 
                                                   >> 7U))))
                                       : (((- (IData)(
                                                      (vlSelf->__PVT__ir 
                                                       >> 0x1fU))) 
                                           << 0xcU) 
                                          | (vlSelf->__PVT__ir 
                                             >> 0x14U))))));
    __VdfgExtracted_h62388771__0 = ((IData)(__VdfgTmp_h2cd83c5b__0) 
                                    | (0x6fU == (0x7fU 
                                                 & vlSelf->__PVT__ir)));
    vlSelf->__PVT__is_cmp = ((0x63U == (0x7fU & vlSelf->__PVT__ir)) 
                             | ((IData)(__VdfgTmp_h18c46dac__0) 
                                & (IData)(__VdfgTmp_hd9b60348__0)));
    vlSelf->__PVT__sh_i = ((0x13U == (0x7fU & vlSelf->__PVT__ir)) 
                           & (IData)(__VdfgTmp_he83b8d53__0));
    vlSelf->__PVT__bad = (1U & ((~ ((IData)(__VdfgExtracted_h62388771__0) 
                                    | ((0x67U == (0x7fU 
                                                  & vlSelf->__PVT__ir)) 
                                       | ((0x63U == 
                                           (0x7fU & vlSelf->__PVT__ir)) 
                                          | ((3U == 
                                              (0x7fU 
                                               & vlSelf->__PVT__ir)) 
                                             | ((0x23U 
                                                 == 
                                                 (0x7fU 
                                                  & vlSelf->__PVT__ir)) 
                                                | ((0x13U 
                                                    == 
                                                    (0x7fU 
                                                     & vlSelf->__PVT__ir)) 
                                                   | ((0x33U 
                                                       == 
                                                       (0x7fU 
                                                        & vlSelf->__PVT__ir)) 
                                                      | (0x73U 
                                                         == 
                                                         (0x7fU 
                                                          & vlSelf->__PVT__ir)))))))))) 
                                | (((0x67U == (0x7fU 
                                               & vlSelf->__PVT__ir)) 
                                    & (0U != (7U & 
                                              (vlSelf->__PVT__ir 
                                               >> 0xcU)))) 
                                   | (((0x63U == (0x7fU 
                                                  & vlSelf->__PVT__ir)) 
                                       & (IData)(__VdfgTmp_hd9b60348__0)) 
                                      | ((((3U == (0x7fU 
                                                   & vlSelf->__PVT__ir)) 
                                           | (0x23U 
                                              == (0x7fU 
                                                  & vlSelf->__PVT__ir))) 
                                          & (2U != 
                                             (7U & 
                                              (vlSelf->__PVT__ir 
                                               >> 0xcU)))) 
                                         | ((IData)(
                                                    ((0x1013U 
                                                      == 
                                                      (0x707fU 
                                                       & vlSelf->__PVT__ir)) 
                                                     & (0U 
                                                        != 
                                                        (vlSelf->__PVT__ir 
                                                         >> 0x19U)))) 
                                            | ((IData)(
                                                       ((0x5013U 
                                                         == 
                                                         (0x707fU 
                                                          & vlSelf->__PVT__ir)) 
                                                        & ((0U 
                                                            != 
                                                            (vlSelf->__PVT__ir 
                                                             >> 0x19U)) 
                                                           & (0x20U 
                                                              != 
                                                              (vlSelf->__PVT__ir 
                                                               >> 0x19U))))) 
                                               | ((0x33U 
                                                   == 
                                                   (0x7fU 
                                                    & vlSelf->__PVT__ir)) 
                                                  & ((~ 
                                                      ((0x20U 
                                                        == 
                                                        (vlSelf->__PVT__ir 
                                                         >> 0x19U)) 
                                                       & ((0U 
                                                           == 
                                                           (7U 
                                                            & (vlSelf->__PVT__ir 
                                                               >> 0xcU))) 
                                                          | (5U 
                                                             == 
                                                             (7U 
                                                              & (vlSelf->__PVT__ir 
                                                                 >> 0xcU)))))) 
                                                     & (0U 
                                                        != 
                                                        (vlSelf->__PVT__ir 
                                                         >> 0x19U)))))))))));
    vlSelf->__PVT__is_slt = ((0x63U != (0x7fU & vlSelf->__PVT__ir)) 
                             & (IData)(vlSelf->__PVT__is_cmp));
    __PVT__inv = 0U;
    vlSelf->__PVT__is_shift = ((IData)(vlSelf->__PVT__sh_i) 
                               | ((0x33U == (0x7fU 
                                             & vlSelf->__PVT__ir)) 
                                  & (IData)(__VdfgTmp_he83b8d53__0)));
    vlSelf->__PVT__we = 0U;
    __PVT__fill = (((IData)(vlSelf->__PVT__is_shift) 
                    & (IData)(((0x40005000U == (0x40007000U 
                                                & vlSelf->__PVT__ir)) 
                               & (IData)(vlSelf->__PVT__sgn))))
                    ? vlSelf->__PVT__mask : 0U);
    __PVT__shx = ((3U == (IData)(vlSelf->__PVT__state)) 
                  & (IData)(vlSelf->__PVT__is_shift));
    vlSelf->__PVT__is_sll = ((IData)(vlSelf->__PVT__is_shift) 
                             & (0x1000U == (0x7000U 
                                            & vlSelf->__PVT__ir)));
    if (vlSelf->__PVT__is_sll) {
        vlSelf->__PVT__exec_done = (0U == (IData)(vlSelf->__PVT__k));
        __PVT__ia = (0x1ffU & ((IData)(vlSelf->__PVT__k) 
                               - (IData)(__PVT__qs)));
        __VdfgTmp_h41a48239__0 = ((VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__k)) 
                                   - VL_EXTENDS_II(32,9, (IData)(__PVT__qs))) 
                                  - (IData)(1U));
    } else {
        vlSelf->__PVT__exec_done = vlSelf->__PVT__last_up;
        __PVT__ia = (0x1ffU & ((IData)(vlSelf->__PVT__k) 
                               + (IData)(__PVT__qs)));
        __VdfgTmp_h41a48239__0 = ((IData)(1U) + (VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__k)) 
                                                 + 
                                                 VL_EXTENDS_II(32,9, (IData)(__PVT__qs))));
    }
    __PVT__va = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, (IData)(__PVT__ia))) 
                 & VL_LTES_III(9, (IData)(__PVT__ia), 
                               (0x1ffU & ((0x3fU & 
                                           (0x20U >> (IData)(vlSelf->__PVT__lw_r))) 
                                          - (IData)(1U)))));
    vlSelf->__PVT__a_val = ((0U == (0x1fU & (vlSelf->__PVT__ir 
                                             >> 0xfU)))
                             ? 0U : (vlSymsp->TOP.tb_sys3__DOT__dut__DOT__slot__BRA__22__KET____DOT__rf
                                     [((0x3e0U & (vlSelf->__PVT__ir 
                                                  >> 0xaU)) 
                                       | (0x1fU & (
                                                   (2U 
                                                    == (IData)(vlSelf->__PVT__state))
                                                    ? 
                                                   ((0x3fU 
                                                     & (0x20U 
                                                        >> (IData)(vlSelf->__PVT__lw_r))) 
                                                    - (IData)(1U))
                                                    : 
                                                   ((IData)(__PVT__shx)
                                                     ? (IData)(__PVT__ia)
                                                     : (IData)(vlSelf->__PVT__k)))))] 
                                     & vlSelf->__PVT__mask));
    __PVT__vb = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, 
                                                   (0x1ffU 
                                                    & __VdfgTmp_h41a48239__0))) 
                 & VL_LTES_III(9, (0x1ffU & __VdfgTmp_h41a48239__0), 
                               (0x1ffU & ((0x3fU & 
                                           (0x20U >> (IData)(vlSelf->__PVT__lw_r))) 
                                          - (IData)(1U)))));
    vlSelf->d_wdata = (((IData)(__PVT__shx) ? (0U == 
                                               (0x1fU 
                                                & (vlSelf->__PVT__ir 
                                                   >> 0xfU)))
                         : (0U == (0x1fU & (vlSelf->__PVT__ir 
                                            >> 0x14U))))
                        ? 0U : (vlSymsp->TOP.tb_sys3__DOT__dut__DOT__slot__BRA__22__KET____DOT__rf
                                [((0x3e0U & (((IData)(__PVT__shx)
                                               ? (vlSelf->__PVT__ir 
                                                  >> 0xfU)
                                               : (vlSelf->__PVT__ir 
                                                  >> 0x14U)) 
                                             << 5U)) 
                                  | (0x1fU & ((2U == (IData)(vlSelf->__PVT__state))
                                               ? (IData)(vlSelf->__PVT__j)
                                               : ((IData)(__PVT__shx)
                                                   ? __VdfgTmp_h41a48239__0
                                                   : (IData)(vlSelf->__PVT__k)))))] 
                                & vlSelf->__PVT__mask));
    __PVT__X = vlSelf->__PVT__a_val;
    __PVT__Yr = (((0x33U == (0x7fU & vlSelf->__PVT__ir)) 
                  | (0x63U == (0x7fU & vlSelf->__PVT__ir)))
                  ? vlSelf->d_wdata : __PVT__imm_d);
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if ((0x37U != (0x7fU & vlSelf->__PVT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->__PVT__ir))) {
                if ((0x6fU != (0x7fU & vlSelf->__PVT__ir))) {
                    if (((IData)((0x40000033U == (0x4000707fU 
                                                  & vlSelf->__PVT__ir))) 
                         | (IData)(vlSelf->__PVT__is_cmp))) {
                        __PVT__inv = 1U;
                    }
                }
            }
        }
        if (vlSelf->__PVT__is_shift) {
            vlSelf->__PVT__we = 1U;
        } else if (__VdfgExtracted_h62388771__0) {
            vlSelf->__PVT__we = 1U;
        } else if (((~ (IData)(vlSelf->__PVT__is_cmp)) 
                    & (IData)(__VdfgTmp_h18c46dac__0))) {
            vlSelf->__PVT__we = 1U;
        }
        if ((0x37U == (0x7fU & vlSelf->__PVT__ir))) {
            __PVT__X = 0U;
        } else if ((0x17U == (0x7fU & vlSelf->__PVT__ir))) {
            __PVT__X = __PVT__pc_d;
        } else if ((0x6fU == (0x7fU & vlSelf->__PVT__ir))) {
            __PVT__X = __PVT__pc_d;
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        if ((3U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__we = 1U;
        } else if (vlSelf->__PVT__is_slt) {
            vlSelf->__PVT__we = 1U;
        } else if ((0x67U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__we = 1U;
        }
        __PVT__X = __PVT__pc_d;
    } else if ((5U == (IData)(vlSelf->__PVT__state))) {
        __PVT__X = __PVT__pc_d;
    }
    vlSelf->__PVT__xsh = VL_SHIFTR_III(32,32,6, __PVT__X, 
                                       (0x3fU & (((IData)(1U) 
                                                  << (IData)(vlSelf->__PVT__lw_r)) 
                                                 - (IData)(1U))));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if ((0x37U != (0x7fU & vlSelf->__PVT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->__PVT__ir))) {
                if ((0x6fU == (0x7fU & vlSelf->__PVT__ir))) {
                    __PVT__Yr = __PVT__c4_d;
                }
            }
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        __PVT__Yr = __PVT__c4_d;
    } else if ((5U == (IData)(vlSelf->__PVT__state))) {
        __PVT__Yr = (((0x6fU == (0x7fU & vlSelf->__PVT__ir)) 
                      | ((0x63U == (0x7fU & vlSelf->__PVT__ir)) 
                         & (IData)(__PVT__cond))) ? __PVT__imm_d
                      : __PVT__c4_d);
    }
    vlSelf->__PVT__ysh = VL_SHIFTR_III(32,32,6, __PVT__Yr, 
                                       (0x3fU & (((IData)(1U) 
                                                  << (IData)(vlSelf->__PVT__lw_r)) 
                                                 - (IData)(1U))));
    __PVT__sum_full = (0x1ffffffffULL & ((QData)((IData)(__PVT__X)) 
                                         + ((QData)((IData)(
                                                            ((IData)(__PVT__inv)
                                                              ? 
                                                             ((~ __PVT__Yr) 
                                                              & vlSelf->__PVT__mask)
                                                              : __PVT__Yr))) 
                                            + (QData)((IData)(
                                                              ((0U 
                                                                == (IData)(vlSelf->__PVT__k))
                                                                ? (IData)(__PVT__inv)
                                                                : (IData)(vlSelf->__PVT__cy)))))));
    vlSelf->__PVT__cout = (1U & (IData)((0x1ffffffffULL 
                                         & (__PVT__sum_full 
                                            >> (0x3fU 
                                                & ((IData)(1U) 
                                                   << (IData)(vlSelf->__PVT__lw_r)))))));
    __PVT__sum_d = ((IData)(__PVT__sum_full) & vlSelf->__PVT__mask);
    vlSelf->__PVT__nz_n = (((0U != (IData)(vlSelf->__PVT__k)) 
                            & (IData)(vlSelf->__PVT__nz)) 
                           | (0U != __PVT__sum_d));
    vlSelf->__VdfgTmp_h7980eff3__0 = VL_SHIFTL_III(32,32,6, __PVT__sum_d, 
                                                   (0x3fU 
                                                    & ((IData)(0x20U) 
                                                       - 
                                                       ((IData)(1U) 
                                                        << (IData)(vlSelf->__PVT__lw_r)))));
    vlSelf->__PVT__wd = (((IData)(__VdfgTmp_h18c46dac__0) 
                          & ((4U == (7U & (vlSelf->__PVT__ir 
                                           >> 0xcU))) 
                             | ((6U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))) 
                                | (7U == (7U & (vlSelf->__PVT__ir 
                                                >> 0xcU))))))
                          ? ((4U == (7U & (vlSelf->__PVT__ir 
                                           >> 0xcU)))
                              ? (__PVT__X ^ __PVT__Yr)
                              : ((6U == (7U & (vlSelf->__PVT__ir 
                                               >> 0xcU)))
                                  ? (__PVT__X | __PVT__Yr)
                                  : (__PVT__X & __PVT__Yr)))
                          : __PVT__sum_d);
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if (vlSelf->__PVT__is_shift) {
            vlSelf->__PVT__wd = ((IData)(((((QData)((IData)(
                                                            ((IData)(vlSelf->__PVT__is_sll)
                                                              ? 
                                                             ((IData)(__PVT__va)
                                                               ? vlSelf->__PVT__a_val
                                                               : 0U)
                                                              : 
                                                             ((IData)(__PVT__vb)
                                                               ? vlSelf->d_wdata
                                                               : __PVT__fill)))) 
                                            << (0x3fU 
                                                & ((IData)(1U) 
                                                   << (IData)(vlSelf->__PVT__lw_r)))) 
                                           | (QData)((IData)(
                                                             ((IData)(vlSelf->__PVT__is_sll)
                                                               ? 
                                                              ((IData)(__PVT__vb)
                                                                ? vlSelf->d_wdata
                                                                : 0U)
                                                               : 
                                                              ((IData)(__PVT__va)
                                                                ? vlSelf->__PVT__a_val
                                                                : __PVT__fill))))) 
                                          >> (0x3fU 
                                              & ((IData)(vlSelf->__PVT__is_sll)
                                                  ? 
                                                 (((IData)(1U) 
                                                   << (IData)(vlSelf->__PVT__lw_r)) 
                                                  - (IData)(__VdfgTmp_h933689ae__0))
                                                  : (IData)(__VdfgTmp_h933689ae__0))))) 
                                 & vlSelf->__PVT__mask);
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        if ((3U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__wd = (vlSymsp->TOP.tb_sys3__DOT__dut__DOT__slot__BRA__22__KET____DOT__dm
                                 [(0x7fffU & (IData)(vlSelf->d_addr))] 
                                 & vlSelf->__PVT__mask);
        } else if (vlSelf->__PVT__is_slt) {
            vlSelf->__PVT__wd = 0U;
            vlSelf->__PVT__wd = ((0xfffffffeU & vlSelf->__PVT__wd) 
                                 | ((0U == (IData)(vlSelf->__PVT__k)) 
                                    & ((2U == (7U & 
                                               (vlSelf->__PVT__ir 
                                                >> 0xcU)))
                                        ? (IData)(vlSelf->__PVT__f_lt)
                                        : (IData)(vlSelf->__PVT__f_ltu))));
        } else if ((0x67U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__wd = __PVT__sum_d;
        }
    }
    vlSelf->__PVT__addr_ins = (VL_SHIFTR_III(32,32,6, vlSelf->__PVT__addr, 
                                             (0x3fU 
                                              & ((IData)(1U) 
                                                 << (IData)(vlSelf->__PVT__lw_r)))) 
                               | vlSelf->__VdfgTmp_h7980eff3__0);
}

VL_INLINE_OPT void Vtb_sys3_uc_core_rw___nba_sequent__TOP__tb_sys3__DOT__dut__DOT__slot__BRA__23__KET____DOT__core__0(Vtb_sys3_uc_core_rw* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_sys3__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+          Vtb_sys3_uc_core_rw___nba_sequent__TOP__tb_sys3__DOT__dut__DOT__slot__BRA__23__KET____DOT__core__0\n"); );
    // Init
    CData/*0:0*/ __PVT__shx;
    __PVT__shx = 0;
    IData/*31:0*/ __PVT__pc_d;
    __PVT__pc_d = 0;
    IData/*31:0*/ __PVT__imm_d;
    __PVT__imm_d = 0;
    IData/*31:0*/ __PVT__c4_d;
    __PVT__c4_d = 0;
    SData/*8:0*/ __PVT__qs;
    __PVT__qs = 0;
    SData/*8:0*/ __PVT__ia;
    __PVT__ia = 0;
    CData/*0:0*/ __PVT__va;
    __PVT__va = 0;
    CData/*0:0*/ __PVT__vb;
    __PVT__vb = 0;
    IData/*31:0*/ __PVT__fill;
    __PVT__fill = 0;
    IData/*31:0*/ __PVT__X;
    __PVT__X = 0;
    IData/*31:0*/ __PVT__Yr;
    __PVT__Yr = 0;
    CData/*0:0*/ __PVT__inv;
    __PVT__inv = 0;
    QData/*32:0*/ __PVT__sum_full;
    __PVT__sum_full = 0;
    IData/*31:0*/ __PVT__sum_d;
    __PVT__sum_d = 0;
    CData/*0:0*/ __PVT__cond;
    __PVT__cond = 0;
    CData/*0:0*/ __VdfgExtracted_h62388771__0;
    __VdfgExtracted_h62388771__0 = 0;
    IData/*31:0*/ __VdfgTmp_h41a48239__0;
    __VdfgTmp_h41a48239__0 = 0;
    CData/*0:0*/ __VdfgTmp_h2cd83c5b__0;
    __VdfgTmp_h2cd83c5b__0 = 0;
    CData/*0:0*/ __VdfgTmp_he83b8d53__0;
    __VdfgTmp_he83b8d53__0 = 0;
    CData/*0:0*/ __VdfgTmp_h18c46dac__0;
    __VdfgTmp_h18c46dac__0 = 0;
    CData/*0:0*/ __VdfgTmp_hd9b60348__0;
    __VdfgTmp_hd9b60348__0 = 0;
    CData/*5:0*/ __VdfgTmp_h933689ae__0;
    __VdfgTmp_h933689ae__0 = 0;
    CData/*5:0*/ __Vtableidx24;
    __Vtableidx24 = 0;
    CData/*2:0*/ __Vdly__state;
    __Vdly__state = 0;
    IData/*31:0*/ __Vdly__addr;
    __Vdly__addr = 0;
    IData/*31:0*/ __Vdly__shamt_w;
    __Vdly__shamt_w = 0;
    CData/*4:0*/ __Vdly__k;
    __Vdly__k = 0;
    CData/*2:0*/ __Vdly__j;
    __Vdly__j = 0;
    // Body
    __Vdly__addr = vlSelf->__PVT__addr;
    __Vdly__j = vlSelf->__PVT__j;
    __Vdly__shamt_w = vlSelf->__PVT__shamt_w;
    __Vdly__state = vlSelf->__PVT__state;
    __Vdly__k = vlSelf->__PVT__k;
    if (vlSymsp->TOP.tb_sys3__DOT__rst) {
        __Vdly__state = 6U;
        vlSelf->__PVT__pc = 0U;
        vlSelf->__PVT__ir = 0U;
        __Vdly__addr = 0U;
        vlSelf->__PVT__imm_sr = 0U;
        __Vdly__shamt_w = 0U;
        __Vdly__k = 0U;
        __Vdly__j = 0U;
        vlSelf->__PVT__lw_r = 0U;
        vlSelf->__PVT__cy = 0U;
        vlSelf->__PVT__nz = 0U;
        vlSelf->__PVT__f_eq = 0U;
        vlSelf->__PVT__f_lt = 0U;
        vlSelf->__PVT__f_ltu = 0U;
        vlSelf->__PVT__sgn = 0U;
        vlSelf->__PVT__halted_r = 1U;
        vlSelf->__PVT__trap_r = 0U;
    } else if (((vlSymsp->TOP.tb_sys3__DOT__dut__DOT__start_v 
                 >> 0x17U) & (6U == (IData)(vlSelf->__PVT__state)))) {
        vlSelf->__PVT__pc = vlSymsp->TOP.tb_sys3__DOT__dut__DOT__launch_entry;
        vlSelf->__PVT__lw_r = vlSymsp->TOP.tb_sys3__DOT__dut__DOT__launch_lw;
        __Vdly__k = 0U;
        vlSelf->__PVT__halted_r = 0U;
        vlSelf->__PVT__trap_r = 0U;
        __Vdly__state = 0U;
    } else if ((4U & (IData)(vlSelf->__PVT__state))) {
        if ((1U & (~ ((IData)(vlSelf->__PVT__state) 
                      >> 1U)))) {
            if ((1U & (IData)(vlSelf->__PVT__state))) {
                if ((0x67U == (IData)(vlSelf->__PVT__opc))) {
                    vlSelf->__PVT__pc = (0xfffffffeU 
                                         & vlSelf->__PVT__addr);
                    __Vdly__state = 0U;
                } else {
                    vlSelf->__PVT__pc = (vlSelf->__VdfgTmp_he4828306__0 
                                         | vlSelf->__VdfgTmp_h7980eff3__0);
                    vlSelf->__PVT__imm_sr = vlSelf->__PVT__imm_rot;
                    vlSelf->__PVT__cy = vlSelf->__PVT__cout;
                    if (vlSelf->__PVT__last_up) {
                        __Vdly__k = 0U;
                        __Vdly__state = 0U;
                    } else {
                        __Vdly__k = (0x1fU & ((IData)(1U) 
                                              + (IData)(vlSelf->__PVT__k)));
                    }
                }
            } else {
                vlSelf->__PVT__cy = vlSelf->__PVT__cout;
                vlSelf->__PVT__pc = vlSelf->__PVT__pc_rot;
                if (vlSelf->__PVT__last_up) {
                    __Vdly__k = 0U;
                    __Vdly__state = 5U;
                } else {
                    __Vdly__k = (0x1fU & ((IData)(1U) 
                                          + (IData)(vlSelf->__PVT__k)));
                }
            }
        }
    } else if ((2U & (IData)(vlSelf->__PVT__state))) {
        if ((1U & (IData)(vlSelf->__PVT__state))) {
            vlSelf->__PVT__cy = vlSelf->__PVT__cout;
            if (vlSelf->__PVT__is_cmp) {
                vlSelf->__PVT__nz = vlSelf->__PVT__nz_n;
                if (vlSelf->__PVT__last_up) {
                    vlSelf->__PVT__f_eq = (1U & (~ (IData)(vlSelf->__PVT__nz_n)));
                    vlSelf->__PVT__f_ltu = (1U & (~ (IData)(vlSelf->__PVT__cout)));
                    vlSelf->__PVT__f_lt = (1U & (((1U 
                                                   & vlSelf->__PVT__xsh) 
                                                  != 
                                                  (1U 
                                                   & vlSelf->__PVT__ysh))
                                                  ? vlSelf->__PVT__xsh
                                                  : 
                                                 (~ (IData)(vlSelf->__PVT__cout))));
                }
            }
            if ((((3U == (IData)(vlSelf->__PVT__opc)) 
                  | (0x23U == (IData)(vlSelf->__PVT__opc))) 
                 | (0x67U == (IData)(vlSelf->__PVT__opc)))) {
                __Vdly__addr = vlSelf->__PVT__addr_ins;
            }
            vlSelf->__PVT__pc = vlSelf->__PVT__pc_rot;
            vlSelf->__PVT__imm_sr = vlSelf->__PVT__imm_rot;
            if (vlSelf->__PVT__exec_done) {
                __Vdly__k = 0U;
                __Vdly__state = (((((3U == (IData)(vlSelf->__PVT__opc)) 
                                    | (0x23U == (IData)(vlSelf->__PVT__opc))) 
                                   | (0x67U == (IData)(vlSelf->__PVT__opc))) 
                                  | (IData)(vlSelf->__PVT__is_slt))
                                  ? 4U : 5U);
            } else {
                __Vdly__k = (0x1fU & ((IData)(vlSelf->__PVT__is_sll)
                                       ? ((IData)(vlSelf->__PVT__k) 
                                          - (IData)(1U))
                                       : ((IData)(1U) 
                                          + (IData)(vlSelf->__PVT__k))));
            }
        } else {
            if ((0x33U == (IData)(vlSelf->__PVT__opc))) {
                __Vdly__shamt_w = ((vlSelf->__PVT__shamt_w 
                                    & (~ VL_SHIFTL_III(32,32,6, vlSelf->__PVT__mask, (IData)(vlSelf->__PVT__jw)))) 
                                   | VL_SHIFTL_III(32,32,6, vlSelf->d_wdata, (IData)(vlSelf->__PVT__jw)));
            }
            vlSelf->__PVT__sgn = (1U & (vlSelf->__PVT__a_val 
                                        >> (0x1fU & (IData)(vlSelf->__PVT__wm1))));
            if (((IData)(vlSelf->__PVT__j) == ((0x33U 
                                                == (IData)(vlSelf->__PVT__opc))
                                                ? (IData)(vlSelf->__PVT__mlast)
                                                : 0U))) {
                __Vdly__state = 3U;
                __Vdly__k = ((IData)(vlSelf->__PVT__is_sll)
                              ? (0x1fU & ((IData)(vlSelf->__PVT__nd) 
                                          - (IData)(1U)))
                              : 0U);
            } else {
                __Vdly__j = (7U & ((IData)(1U) + (IData)(vlSelf->__PVT__j)));
            }
        }
    } else if ((1U & (IData)(vlSelf->__PVT__state))) {
        __Vdly__j = 0U;
        vlSelf->__PVT__imm_sr = vlSelf->__PVT__imm;
        __Vdly__shamt_w = ((IData)(vlSelf->__PVT__sh_i)
                            ? (IData)(vlSelf->__PVT__rs2)
                            : 0U);
        if (vlSelf->__PVT__bad) {
            vlSelf->__PVT__trap_r = 1U;
            vlSelf->__PVT__halted_r = 1U;
            __Vdly__state = 6U;
        } else if (vlSelf->__PVT__is_sys) {
            vlSelf->__PVT__halted_r = 1U;
            __Vdly__state = 6U;
        } else if (vlSelf->__PVT__is_shift) {
            __Vdly__state = 2U;
        } else {
            __Vdly__k = 0U;
            __Vdly__state = 3U;
        }
    } else {
        vlSelf->__PVT__ir = vlSymsp->TOP.tb_sys3__DOT__dut__DOT__slot__BRA__23__KET____DOT__id;
        __Vdly__state = 1U;
    }
    vlSelf->__PVT__addr = __Vdly__addr;
    vlSelf->__PVT__j = __Vdly__j;
    vlSelf->__PVT__shamt_w = __Vdly__shamt_w;
    vlSelf->__PVT__state = __Vdly__state;
    vlSelf->__PVT__k = __Vdly__k;
    vlSelf->d_addr = (((QData)((IData)((vlSelf->__PVT__addr 
                                        >> 2U))) << 5U) 
                      | (QData)((IData)(vlSelf->__PVT__k)));
    vlSelf->__PVT__wm1 = (0x3fU & (((IData)(1U) << (IData)(vlSelf->__PVT__lw_r)) 
                                   - (IData)(1U)));
    vlSelf->__PVT__mlast = (0x3fU & (VL_DIV_III(6, 
                                                (0x3fU 
                                                 & ((IData)(4U) 
                                                    + 
                                                    ((IData)(1U) 
                                                     << (IData)(vlSelf->__PVT__lw_r)))), 
                                                (0x3fU 
                                                 & ((IData)(1U) 
                                                    << (IData)(vlSelf->__PVT__lw_r)))) 
                                     - (IData)(1U)));
    vlSelf->__PVT__nd = (0x3fU & (0x20U >> (IData)(vlSelf->__PVT__lw_r)));
    vlSelf->__PVT__jw = (0x3fU & ((IData)(vlSelf->__PVT__j) 
                                  * (0x3fU & ((IData)(1U) 
                                              << (IData)(vlSelf->__PVT__lw_r)))));
    vlSelf->__PVT__imm_rot = (VL_SHIFTR_III(32,32,6, vlSelf->__PVT__imm_sr, 
                                            (0x3fU 
                                             & ((IData)(1U) 
                                                << (IData)(vlSelf->__PVT__lw_r)))) 
                              | VL_SHIFTL_III(32,32,6, vlSelf->__PVT__imm_sr, 
                                              (0x3fU 
                                               & ((IData)(0x20U) 
                                                  - 
                                                  ((IData)(1U) 
                                                   << (IData)(vlSelf->__PVT__lw_r))))));
    vlSelf->__PVT__last_up = ((IData)(vlSelf->__PVT__k) 
                              == (0x1fU & ((0x3fU & 
                                            (0x20U 
                                             >> (IData)(vlSelf->__PVT__lw_r))) 
                                           - (IData)(1U))));
    vlSelf->__VdfgTmp_he4828306__0 = VL_SHIFTR_III(32,32,6, vlSelf->__PVT__pc, 
                                                   (0x3fU 
                                                    & ((IData)(1U) 
                                                       << (IData)(vlSelf->__PVT__lw_r))));
    __VdfgTmp_h933689ae__0 = (0x1fU & (vlSelf->__PVT__shamt_w 
                                       & ((0x3fU & 
                                           ((IData)(1U) 
                                            << (IData)(vlSelf->__PVT__lw_r))) 
                                          - (IData)(1U))));
    __PVT__qs = (0x1fU & ((0x1fU & vlSelf->__PVT__shamt_w) 
                          >> (IData)(vlSelf->__PVT__lw_r)));
    vlSelf->__PVT__mask = ((5U == (IData)(vlSelf->__PVT__lw_r))
                            ? 0xffffffffU : (VL_SHIFTL_III(32,32,6, (IData)(1U), 
                                                           (0x3fU 
                                                            & ((IData)(1U) 
                                                               << (IData)(vlSelf->__PVT__lw_r)))) 
                                             - (IData)(1U)));
    vlSelf->__PVT__rs2 = (0x1fU & (vlSelf->__PVT__ir 
                                   >> 0x14U));
    vlSelf->__PVT__is_sys = (0x73U == (0x7fU & vlSelf->__PVT__ir));
    vlSelf->__PVT__opc = (0x7fU & vlSelf->__PVT__ir);
    __VdfgTmp_h2cd83c5b__0 = ((0x37U == (0x7fU & vlSelf->__PVT__ir)) 
                              | (0x17U == (0x7fU & vlSelf->__PVT__ir)));
    __Vtableidx24 = (((IData)(vlSelf->__PVT__f_eq) 
                      << 5U) | (((IData)(vlSelf->__PVT__f_lt) 
                                 << 4U) | (((IData)(vlSelf->__PVT__f_ltu) 
                                            << 3U) 
                                           | (7U & 
                                              (vlSelf->__PVT__ir 
                                               >> 0xcU)))));
    __PVT__cond = Vtb_sys3__ConstPool__TABLE_h2a0441a0_0
        [__Vtableidx24];
    __VdfgTmp_hd9b60348__0 = ((2U == (7U & (vlSelf->__PVT__ir 
                                            >> 0xcU))) 
                              | (3U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))));
    __VdfgTmp_h18c46dac__0 = ((0x13U == (0x7fU & vlSelf->__PVT__ir)) 
                              | (0x33U == (0x7fU & vlSelf->__PVT__ir)));
    __VdfgTmp_he83b8d53__0 = ((1U == (7U & (vlSelf->__PVT__ir 
                                            >> 0xcU))) 
                              | (5U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))));
    vlSelf->__PVT__pc_rot = (vlSelf->__VdfgTmp_he4828306__0 
                             | VL_SHIFTL_III(32,32,6, vlSelf->__PVT__pc, 
                                             (0x3fU 
                                              & ((IData)(0x20U) 
                                                 - 
                                                 ((IData)(1U) 
                                                  << (IData)(vlSelf->__PVT__lw_r))))));
    __PVT__pc_d = (vlSelf->__PVT__pc & vlSelf->__PVT__mask);
    __PVT__imm_d = (vlSelf->__PVT__imm_sr & vlSelf->__PVT__mask);
    __PVT__c4_d = (VL_SHIFTR_III(32,32,6, 4U, (0x3fU 
                                               & ((IData)(vlSelf->__PVT__k) 
                                                  * 
                                                  (0x3fU 
                                                   & ((IData)(1U) 
                                                      << (IData)(vlSelf->__PVT__lw_r)))))) 
                   & vlSelf->__PVT__mask);
    vlSelf->__PVT__imm = ((IData)(__VdfgTmp_h2cd83c5b__0)
                           ? (0xfffff000U & vlSelf->__PVT__ir)
                           : ((0x6fU == (0x7fU & vlSelf->__PVT__ir))
                               ? (((- (IData)((vlSelf->__PVT__ir 
                                               >> 0x1fU))) 
                                   << 0x15U) | ((0x100000U 
                                                 & (vlSelf->__PVT__ir 
                                                    >> 0xbU)) 
                                                | ((0xff000U 
                                                    & vlSelf->__PVT__ir) 
                                                   | ((0x800U 
                                                       & (vlSelf->__PVT__ir 
                                                          >> 9U)) 
                                                      | (0x7feU 
                                                         & (vlSelf->__PVT__ir 
                                                            >> 0x14U))))))
                               : ((0x63U == (0x7fU 
                                             & vlSelf->__PVT__ir))
                                   ? (((- (IData)((vlSelf->__PVT__ir 
                                                   >> 0x1fU))) 
                                       << 0xdU) | (
                                                   (0x1000U 
                                                    & (vlSelf->__PVT__ir 
                                                       >> 0x13U)) 
                                                   | ((0x800U 
                                                       & (vlSelf->__PVT__ir 
                                                          << 4U)) 
                                                      | ((0x7e0U 
                                                          & (vlSelf->__PVT__ir 
                                                             >> 0x14U)) 
                                                         | (0x1eU 
                                                            & (vlSelf->__PVT__ir 
                                                               >> 7U))))))
                                   : ((0x23U == (0x7fU 
                                                 & vlSelf->__PVT__ir))
                                       ? (((- (IData)(
                                                      (vlSelf->__PVT__ir 
                                                       >> 0x1fU))) 
                                           << 0xcU) 
                                          | ((0xfe0U 
                                              & (vlSelf->__PVT__ir 
                                                 >> 0x14U)) 
                                             | (0x1fU 
                                                & (vlSelf->__PVT__ir 
                                                   >> 7U))))
                                       : (((- (IData)(
                                                      (vlSelf->__PVT__ir 
                                                       >> 0x1fU))) 
                                           << 0xcU) 
                                          | (vlSelf->__PVT__ir 
                                             >> 0x14U))))));
    __VdfgExtracted_h62388771__0 = ((IData)(__VdfgTmp_h2cd83c5b__0) 
                                    | (0x6fU == (0x7fU 
                                                 & vlSelf->__PVT__ir)));
    vlSelf->__PVT__is_cmp = ((0x63U == (0x7fU & vlSelf->__PVT__ir)) 
                             | ((IData)(__VdfgTmp_h18c46dac__0) 
                                & (IData)(__VdfgTmp_hd9b60348__0)));
    vlSelf->__PVT__sh_i = ((0x13U == (0x7fU & vlSelf->__PVT__ir)) 
                           & (IData)(__VdfgTmp_he83b8d53__0));
    vlSelf->__PVT__bad = (1U & ((~ ((IData)(__VdfgExtracted_h62388771__0) 
                                    | ((0x67U == (0x7fU 
                                                  & vlSelf->__PVT__ir)) 
                                       | ((0x63U == 
                                           (0x7fU & vlSelf->__PVT__ir)) 
                                          | ((3U == 
                                              (0x7fU 
                                               & vlSelf->__PVT__ir)) 
                                             | ((0x23U 
                                                 == 
                                                 (0x7fU 
                                                  & vlSelf->__PVT__ir)) 
                                                | ((0x13U 
                                                    == 
                                                    (0x7fU 
                                                     & vlSelf->__PVT__ir)) 
                                                   | ((0x33U 
                                                       == 
                                                       (0x7fU 
                                                        & vlSelf->__PVT__ir)) 
                                                      | (0x73U 
                                                         == 
                                                         (0x7fU 
                                                          & vlSelf->__PVT__ir)))))))))) 
                                | (((0x67U == (0x7fU 
                                               & vlSelf->__PVT__ir)) 
                                    & (0U != (7U & 
                                              (vlSelf->__PVT__ir 
                                               >> 0xcU)))) 
                                   | (((0x63U == (0x7fU 
                                                  & vlSelf->__PVT__ir)) 
                                       & (IData)(__VdfgTmp_hd9b60348__0)) 
                                      | ((((3U == (0x7fU 
                                                   & vlSelf->__PVT__ir)) 
                                           | (0x23U 
                                              == (0x7fU 
                                                  & vlSelf->__PVT__ir))) 
                                          & (2U != 
                                             (7U & 
                                              (vlSelf->__PVT__ir 
                                               >> 0xcU)))) 
                                         | ((IData)(
                                                    ((0x1013U 
                                                      == 
                                                      (0x707fU 
                                                       & vlSelf->__PVT__ir)) 
                                                     & (0U 
                                                        != 
                                                        (vlSelf->__PVT__ir 
                                                         >> 0x19U)))) 
                                            | ((IData)(
                                                       ((0x5013U 
                                                         == 
                                                         (0x707fU 
                                                          & vlSelf->__PVT__ir)) 
                                                        & ((0U 
                                                            != 
                                                            (vlSelf->__PVT__ir 
                                                             >> 0x19U)) 
                                                           & (0x20U 
                                                              != 
                                                              (vlSelf->__PVT__ir 
                                                               >> 0x19U))))) 
                                               | ((0x33U 
                                                   == 
                                                   (0x7fU 
                                                    & vlSelf->__PVT__ir)) 
                                                  & ((~ 
                                                      ((0x20U 
                                                        == 
                                                        (vlSelf->__PVT__ir 
                                                         >> 0x19U)) 
                                                       & ((0U 
                                                           == 
                                                           (7U 
                                                            & (vlSelf->__PVT__ir 
                                                               >> 0xcU))) 
                                                          | (5U 
                                                             == 
                                                             (7U 
                                                              & (vlSelf->__PVT__ir 
                                                                 >> 0xcU)))))) 
                                                     & (0U 
                                                        != 
                                                        (vlSelf->__PVT__ir 
                                                         >> 0x19U)))))))))));
    vlSelf->__PVT__is_slt = ((0x63U != (0x7fU & vlSelf->__PVT__ir)) 
                             & (IData)(vlSelf->__PVT__is_cmp));
    __PVT__inv = 0U;
    vlSelf->__PVT__is_shift = ((IData)(vlSelf->__PVT__sh_i) 
                               | ((0x33U == (0x7fU 
                                             & vlSelf->__PVT__ir)) 
                                  & (IData)(__VdfgTmp_he83b8d53__0)));
    vlSelf->__PVT__we = 0U;
    __PVT__fill = (((IData)(vlSelf->__PVT__is_shift) 
                    & (IData)(((0x40005000U == (0x40007000U 
                                                & vlSelf->__PVT__ir)) 
                               & (IData)(vlSelf->__PVT__sgn))))
                    ? vlSelf->__PVT__mask : 0U);
    __PVT__shx = ((3U == (IData)(vlSelf->__PVT__state)) 
                  & (IData)(vlSelf->__PVT__is_shift));
    vlSelf->__PVT__is_sll = ((IData)(vlSelf->__PVT__is_shift) 
                             & (0x1000U == (0x7000U 
                                            & vlSelf->__PVT__ir)));
    if (vlSelf->__PVT__is_sll) {
        vlSelf->__PVT__exec_done = (0U == (IData)(vlSelf->__PVT__k));
        __PVT__ia = (0x1ffU & ((IData)(vlSelf->__PVT__k) 
                               - (IData)(__PVT__qs)));
        __VdfgTmp_h41a48239__0 = ((VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__k)) 
                                   - VL_EXTENDS_II(32,9, (IData)(__PVT__qs))) 
                                  - (IData)(1U));
    } else {
        vlSelf->__PVT__exec_done = vlSelf->__PVT__last_up;
        __PVT__ia = (0x1ffU & ((IData)(vlSelf->__PVT__k) 
                               + (IData)(__PVT__qs)));
        __VdfgTmp_h41a48239__0 = ((IData)(1U) + (VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__k)) 
                                                 + 
                                                 VL_EXTENDS_II(32,9, (IData)(__PVT__qs))));
    }
    __PVT__va = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, (IData)(__PVT__ia))) 
                 & VL_LTES_III(9, (IData)(__PVT__ia), 
                               (0x1ffU & ((0x3fU & 
                                           (0x20U >> (IData)(vlSelf->__PVT__lw_r))) 
                                          - (IData)(1U)))));
    vlSelf->__PVT__a_val = ((0U == (0x1fU & (vlSelf->__PVT__ir 
                                             >> 0xfU)))
                             ? 0U : (vlSymsp->TOP.tb_sys3__DOT__dut__DOT__slot__BRA__23__KET____DOT__rf
                                     [((0x3e0U & (vlSelf->__PVT__ir 
                                                  >> 0xaU)) 
                                       | (0x1fU & (
                                                   (2U 
                                                    == (IData)(vlSelf->__PVT__state))
                                                    ? 
                                                   ((0x3fU 
                                                     & (0x20U 
                                                        >> (IData)(vlSelf->__PVT__lw_r))) 
                                                    - (IData)(1U))
                                                    : 
                                                   ((IData)(__PVT__shx)
                                                     ? (IData)(__PVT__ia)
                                                     : (IData)(vlSelf->__PVT__k)))))] 
                                     & vlSelf->__PVT__mask));
    __PVT__vb = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, 
                                                   (0x1ffU 
                                                    & __VdfgTmp_h41a48239__0))) 
                 & VL_LTES_III(9, (0x1ffU & __VdfgTmp_h41a48239__0), 
                               (0x1ffU & ((0x3fU & 
                                           (0x20U >> (IData)(vlSelf->__PVT__lw_r))) 
                                          - (IData)(1U)))));
    vlSelf->d_wdata = (((IData)(__PVT__shx) ? (0U == 
                                               (0x1fU 
                                                & (vlSelf->__PVT__ir 
                                                   >> 0xfU)))
                         : (0U == (0x1fU & (vlSelf->__PVT__ir 
                                            >> 0x14U))))
                        ? 0U : (vlSymsp->TOP.tb_sys3__DOT__dut__DOT__slot__BRA__23__KET____DOT__rf
                                [((0x3e0U & (((IData)(__PVT__shx)
                                               ? (vlSelf->__PVT__ir 
                                                  >> 0xfU)
                                               : (vlSelf->__PVT__ir 
                                                  >> 0x14U)) 
                                             << 5U)) 
                                  | (0x1fU & ((2U == (IData)(vlSelf->__PVT__state))
                                               ? (IData)(vlSelf->__PVT__j)
                                               : ((IData)(__PVT__shx)
                                                   ? __VdfgTmp_h41a48239__0
                                                   : (IData)(vlSelf->__PVT__k)))))] 
                                & vlSelf->__PVT__mask));
    __PVT__X = vlSelf->__PVT__a_val;
    __PVT__Yr = (((0x33U == (0x7fU & vlSelf->__PVT__ir)) 
                  | (0x63U == (0x7fU & vlSelf->__PVT__ir)))
                  ? vlSelf->d_wdata : __PVT__imm_d);
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if ((0x37U != (0x7fU & vlSelf->__PVT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->__PVT__ir))) {
                if ((0x6fU != (0x7fU & vlSelf->__PVT__ir))) {
                    if (((IData)((0x40000033U == (0x4000707fU 
                                                  & vlSelf->__PVT__ir))) 
                         | (IData)(vlSelf->__PVT__is_cmp))) {
                        __PVT__inv = 1U;
                    }
                }
            }
        }
        if (vlSelf->__PVT__is_shift) {
            vlSelf->__PVT__we = 1U;
        } else if (__VdfgExtracted_h62388771__0) {
            vlSelf->__PVT__we = 1U;
        } else if (((~ (IData)(vlSelf->__PVT__is_cmp)) 
                    & (IData)(__VdfgTmp_h18c46dac__0))) {
            vlSelf->__PVT__we = 1U;
        }
        if ((0x37U == (0x7fU & vlSelf->__PVT__ir))) {
            __PVT__X = 0U;
        } else if ((0x17U == (0x7fU & vlSelf->__PVT__ir))) {
            __PVT__X = __PVT__pc_d;
        } else if ((0x6fU == (0x7fU & vlSelf->__PVT__ir))) {
            __PVT__X = __PVT__pc_d;
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        if ((3U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__we = 1U;
        } else if (vlSelf->__PVT__is_slt) {
            vlSelf->__PVT__we = 1U;
        } else if ((0x67U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__we = 1U;
        }
        __PVT__X = __PVT__pc_d;
    } else if ((5U == (IData)(vlSelf->__PVT__state))) {
        __PVT__X = __PVT__pc_d;
    }
    vlSelf->__PVT__xsh = VL_SHIFTR_III(32,32,6, __PVT__X, 
                                       (0x3fU & (((IData)(1U) 
                                                  << (IData)(vlSelf->__PVT__lw_r)) 
                                                 - (IData)(1U))));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if ((0x37U != (0x7fU & vlSelf->__PVT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->__PVT__ir))) {
                if ((0x6fU == (0x7fU & vlSelf->__PVT__ir))) {
                    __PVT__Yr = __PVT__c4_d;
                }
            }
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        __PVT__Yr = __PVT__c4_d;
    } else if ((5U == (IData)(vlSelf->__PVT__state))) {
        __PVT__Yr = (((0x6fU == (0x7fU & vlSelf->__PVT__ir)) 
                      | ((0x63U == (0x7fU & vlSelf->__PVT__ir)) 
                         & (IData)(__PVT__cond))) ? __PVT__imm_d
                      : __PVT__c4_d);
    }
    vlSelf->__PVT__ysh = VL_SHIFTR_III(32,32,6, __PVT__Yr, 
                                       (0x3fU & (((IData)(1U) 
                                                  << (IData)(vlSelf->__PVT__lw_r)) 
                                                 - (IData)(1U))));
    __PVT__sum_full = (0x1ffffffffULL & ((QData)((IData)(__PVT__X)) 
                                         + ((QData)((IData)(
                                                            ((IData)(__PVT__inv)
                                                              ? 
                                                             ((~ __PVT__Yr) 
                                                              & vlSelf->__PVT__mask)
                                                              : __PVT__Yr))) 
                                            + (QData)((IData)(
                                                              ((0U 
                                                                == (IData)(vlSelf->__PVT__k))
                                                                ? (IData)(__PVT__inv)
                                                                : (IData)(vlSelf->__PVT__cy)))))));
    vlSelf->__PVT__cout = (1U & (IData)((0x1ffffffffULL 
                                         & (__PVT__sum_full 
                                            >> (0x3fU 
                                                & ((IData)(1U) 
                                                   << (IData)(vlSelf->__PVT__lw_r)))))));
    __PVT__sum_d = ((IData)(__PVT__sum_full) & vlSelf->__PVT__mask);
    vlSelf->__PVT__nz_n = (((0U != (IData)(vlSelf->__PVT__k)) 
                            & (IData)(vlSelf->__PVT__nz)) 
                           | (0U != __PVT__sum_d));
    vlSelf->__VdfgTmp_h7980eff3__0 = VL_SHIFTL_III(32,32,6, __PVT__sum_d, 
                                                   (0x3fU 
                                                    & ((IData)(0x20U) 
                                                       - 
                                                       ((IData)(1U) 
                                                        << (IData)(vlSelf->__PVT__lw_r)))));
    vlSelf->__PVT__wd = (((IData)(__VdfgTmp_h18c46dac__0) 
                          & ((4U == (7U & (vlSelf->__PVT__ir 
                                           >> 0xcU))) 
                             | ((6U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))) 
                                | (7U == (7U & (vlSelf->__PVT__ir 
                                                >> 0xcU))))))
                          ? ((4U == (7U & (vlSelf->__PVT__ir 
                                           >> 0xcU)))
                              ? (__PVT__X ^ __PVT__Yr)
                              : ((6U == (7U & (vlSelf->__PVT__ir 
                                               >> 0xcU)))
                                  ? (__PVT__X | __PVT__Yr)
                                  : (__PVT__X & __PVT__Yr)))
                          : __PVT__sum_d);
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if (vlSelf->__PVT__is_shift) {
            vlSelf->__PVT__wd = ((IData)(((((QData)((IData)(
                                                            ((IData)(vlSelf->__PVT__is_sll)
                                                              ? 
                                                             ((IData)(__PVT__va)
                                                               ? vlSelf->__PVT__a_val
                                                               : 0U)
                                                              : 
                                                             ((IData)(__PVT__vb)
                                                               ? vlSelf->d_wdata
                                                               : __PVT__fill)))) 
                                            << (0x3fU 
                                                & ((IData)(1U) 
                                                   << (IData)(vlSelf->__PVT__lw_r)))) 
                                           | (QData)((IData)(
                                                             ((IData)(vlSelf->__PVT__is_sll)
                                                               ? 
                                                              ((IData)(__PVT__vb)
                                                                ? vlSelf->d_wdata
                                                                : 0U)
                                                               : 
                                                              ((IData)(__PVT__va)
                                                                ? vlSelf->__PVT__a_val
                                                                : __PVT__fill))))) 
                                          >> (0x3fU 
                                              & ((IData)(vlSelf->__PVT__is_sll)
                                                  ? 
                                                 (((IData)(1U) 
                                                   << (IData)(vlSelf->__PVT__lw_r)) 
                                                  - (IData)(__VdfgTmp_h933689ae__0))
                                                  : (IData)(__VdfgTmp_h933689ae__0))))) 
                                 & vlSelf->__PVT__mask);
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        if ((3U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__wd = (vlSymsp->TOP.tb_sys3__DOT__dut__DOT__slot__BRA__23__KET____DOT__dm
                                 [(0x7fffU & (IData)(vlSelf->d_addr))] 
                                 & vlSelf->__PVT__mask);
        } else if (vlSelf->__PVT__is_slt) {
            vlSelf->__PVT__wd = 0U;
            vlSelf->__PVT__wd = ((0xfffffffeU & vlSelf->__PVT__wd) 
                                 | ((0U == (IData)(vlSelf->__PVT__k)) 
                                    & ((2U == (7U & 
                                               (vlSelf->__PVT__ir 
                                                >> 0xcU)))
                                        ? (IData)(vlSelf->__PVT__f_lt)
                                        : (IData)(vlSelf->__PVT__f_ltu))));
        } else if ((0x67U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__wd = __PVT__sum_d;
        }
    }
    vlSelf->__PVT__addr_ins = (VL_SHIFTR_III(32,32,6, vlSelf->__PVT__addr, 
                                             (0x3fU 
                                              & ((IData)(1U) 
                                                 << (IData)(vlSelf->__PVT__lw_r)))) 
                               | vlSelf->__VdfgTmp_h7980eff3__0);
}

VL_INLINE_OPT void Vtb_sys3_uc_core_rw___nba_sequent__TOP__tb_sys3__DOT__dut__DOT__slot__BRA__24__KET____DOT__core__0(Vtb_sys3_uc_core_rw* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_sys3__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+          Vtb_sys3_uc_core_rw___nba_sequent__TOP__tb_sys3__DOT__dut__DOT__slot__BRA__24__KET____DOT__core__0\n"); );
    // Init
    CData/*0:0*/ __PVT__shx;
    __PVT__shx = 0;
    IData/*31:0*/ __PVT__pc_d;
    __PVT__pc_d = 0;
    IData/*31:0*/ __PVT__imm_d;
    __PVT__imm_d = 0;
    IData/*31:0*/ __PVT__c4_d;
    __PVT__c4_d = 0;
    SData/*8:0*/ __PVT__qs;
    __PVT__qs = 0;
    SData/*8:0*/ __PVT__ia;
    __PVT__ia = 0;
    CData/*0:0*/ __PVT__va;
    __PVT__va = 0;
    CData/*0:0*/ __PVT__vb;
    __PVT__vb = 0;
    IData/*31:0*/ __PVT__fill;
    __PVT__fill = 0;
    IData/*31:0*/ __PVT__X;
    __PVT__X = 0;
    IData/*31:0*/ __PVT__Yr;
    __PVT__Yr = 0;
    CData/*0:0*/ __PVT__inv;
    __PVT__inv = 0;
    QData/*32:0*/ __PVT__sum_full;
    __PVT__sum_full = 0;
    IData/*31:0*/ __PVT__sum_d;
    __PVT__sum_d = 0;
    CData/*0:0*/ __PVT__cond;
    __PVT__cond = 0;
    CData/*0:0*/ __VdfgExtracted_h62388771__0;
    __VdfgExtracted_h62388771__0 = 0;
    IData/*31:0*/ __VdfgTmp_h41a48239__0;
    __VdfgTmp_h41a48239__0 = 0;
    CData/*0:0*/ __VdfgTmp_h2cd83c5b__0;
    __VdfgTmp_h2cd83c5b__0 = 0;
    CData/*0:0*/ __VdfgTmp_he83b8d53__0;
    __VdfgTmp_he83b8d53__0 = 0;
    CData/*0:0*/ __VdfgTmp_h18c46dac__0;
    __VdfgTmp_h18c46dac__0 = 0;
    CData/*0:0*/ __VdfgTmp_hd9b60348__0;
    __VdfgTmp_hd9b60348__0 = 0;
    CData/*5:0*/ __VdfgTmp_h933689ae__0;
    __VdfgTmp_h933689ae__0 = 0;
    CData/*5:0*/ __Vtableidx25;
    __Vtableidx25 = 0;
    CData/*2:0*/ __Vdly__state;
    __Vdly__state = 0;
    IData/*31:0*/ __Vdly__addr;
    __Vdly__addr = 0;
    IData/*31:0*/ __Vdly__shamt_w;
    __Vdly__shamt_w = 0;
    CData/*4:0*/ __Vdly__k;
    __Vdly__k = 0;
    CData/*2:0*/ __Vdly__j;
    __Vdly__j = 0;
    // Body
    __Vdly__addr = vlSelf->__PVT__addr;
    __Vdly__j = vlSelf->__PVT__j;
    __Vdly__shamt_w = vlSelf->__PVT__shamt_w;
    __Vdly__state = vlSelf->__PVT__state;
    __Vdly__k = vlSelf->__PVT__k;
    if (vlSymsp->TOP.tb_sys3__DOT__rst) {
        __Vdly__state = 6U;
        vlSelf->__PVT__pc = 0U;
        vlSelf->__PVT__ir = 0U;
        __Vdly__addr = 0U;
        vlSelf->__PVT__imm_sr = 0U;
        __Vdly__shamt_w = 0U;
        __Vdly__k = 0U;
        __Vdly__j = 0U;
        vlSelf->__PVT__lw_r = 0U;
        vlSelf->__PVT__cy = 0U;
        vlSelf->__PVT__nz = 0U;
        vlSelf->__PVT__f_eq = 0U;
        vlSelf->__PVT__f_lt = 0U;
        vlSelf->__PVT__f_ltu = 0U;
        vlSelf->__PVT__sgn = 0U;
        vlSelf->__PVT__halted_r = 1U;
        vlSelf->__PVT__trap_r = 0U;
    } else if (((vlSymsp->TOP.tb_sys3__DOT__dut__DOT__start_v 
                 >> 0x18U) & (6U == (IData)(vlSelf->__PVT__state)))) {
        vlSelf->__PVT__pc = vlSymsp->TOP.tb_sys3__DOT__dut__DOT__launch_entry;
        vlSelf->__PVT__lw_r = vlSymsp->TOP.tb_sys3__DOT__dut__DOT__launch_lw;
        __Vdly__k = 0U;
        vlSelf->__PVT__halted_r = 0U;
        vlSelf->__PVT__trap_r = 0U;
        __Vdly__state = 0U;
    } else if ((4U & (IData)(vlSelf->__PVT__state))) {
        if ((1U & (~ ((IData)(vlSelf->__PVT__state) 
                      >> 1U)))) {
            if ((1U & (IData)(vlSelf->__PVT__state))) {
                if ((0x67U == (IData)(vlSelf->__PVT__opc))) {
                    vlSelf->__PVT__pc = (0xfffffffeU 
                                         & vlSelf->__PVT__addr);
                    __Vdly__state = 0U;
                } else {
                    vlSelf->__PVT__pc = (vlSelf->__VdfgTmp_he4828306__0 
                                         | vlSelf->__VdfgTmp_h7980eff3__0);
                    vlSelf->__PVT__imm_sr = vlSelf->__PVT__imm_rot;
                    vlSelf->__PVT__cy = vlSelf->__PVT__cout;
                    if (vlSelf->__PVT__last_up) {
                        __Vdly__k = 0U;
                        __Vdly__state = 0U;
                    } else {
                        __Vdly__k = (0x1fU & ((IData)(1U) 
                                              + (IData)(vlSelf->__PVT__k)));
                    }
                }
            } else {
                vlSelf->__PVT__cy = vlSelf->__PVT__cout;
                vlSelf->__PVT__pc = vlSelf->__PVT__pc_rot;
                if (vlSelf->__PVT__last_up) {
                    __Vdly__k = 0U;
                    __Vdly__state = 5U;
                } else {
                    __Vdly__k = (0x1fU & ((IData)(1U) 
                                          + (IData)(vlSelf->__PVT__k)));
                }
            }
        }
    } else if ((2U & (IData)(vlSelf->__PVT__state))) {
        if ((1U & (IData)(vlSelf->__PVT__state))) {
            vlSelf->__PVT__cy = vlSelf->__PVT__cout;
            if (vlSelf->__PVT__is_cmp) {
                vlSelf->__PVT__nz = vlSelf->__PVT__nz_n;
                if (vlSelf->__PVT__last_up) {
                    vlSelf->__PVT__f_eq = (1U & (~ (IData)(vlSelf->__PVT__nz_n)));
                    vlSelf->__PVT__f_ltu = (1U & (~ (IData)(vlSelf->__PVT__cout)));
                    vlSelf->__PVT__f_lt = (1U & (((1U 
                                                   & vlSelf->__PVT__xsh) 
                                                  != 
                                                  (1U 
                                                   & vlSelf->__PVT__ysh))
                                                  ? vlSelf->__PVT__xsh
                                                  : 
                                                 (~ (IData)(vlSelf->__PVT__cout))));
                }
            }
            if ((((3U == (IData)(vlSelf->__PVT__opc)) 
                  | (0x23U == (IData)(vlSelf->__PVT__opc))) 
                 | (0x67U == (IData)(vlSelf->__PVT__opc)))) {
                __Vdly__addr = vlSelf->__PVT__addr_ins;
            }
            vlSelf->__PVT__pc = vlSelf->__PVT__pc_rot;
            vlSelf->__PVT__imm_sr = vlSelf->__PVT__imm_rot;
            if (vlSelf->__PVT__exec_done) {
                __Vdly__k = 0U;
                __Vdly__state = (((((3U == (IData)(vlSelf->__PVT__opc)) 
                                    | (0x23U == (IData)(vlSelf->__PVT__opc))) 
                                   | (0x67U == (IData)(vlSelf->__PVT__opc))) 
                                  | (IData)(vlSelf->__PVT__is_slt))
                                  ? 4U : 5U);
            } else {
                __Vdly__k = (0x1fU & ((IData)(vlSelf->__PVT__is_sll)
                                       ? ((IData)(vlSelf->__PVT__k) 
                                          - (IData)(1U))
                                       : ((IData)(1U) 
                                          + (IData)(vlSelf->__PVT__k))));
            }
        } else {
            if ((0x33U == (IData)(vlSelf->__PVT__opc))) {
                __Vdly__shamt_w = ((vlSelf->__PVT__shamt_w 
                                    & (~ VL_SHIFTL_III(32,32,6, vlSelf->__PVT__mask, (IData)(vlSelf->__PVT__jw)))) 
                                   | VL_SHIFTL_III(32,32,6, vlSelf->d_wdata, (IData)(vlSelf->__PVT__jw)));
            }
            vlSelf->__PVT__sgn = (1U & (vlSelf->__PVT__a_val 
                                        >> (0x1fU & (IData)(vlSelf->__PVT__wm1))));
            if (((IData)(vlSelf->__PVT__j) == ((0x33U 
                                                == (IData)(vlSelf->__PVT__opc))
                                                ? (IData)(vlSelf->__PVT__mlast)
                                                : 0U))) {
                __Vdly__state = 3U;
                __Vdly__k = ((IData)(vlSelf->__PVT__is_sll)
                              ? (0x1fU & ((IData)(vlSelf->__PVT__nd) 
                                          - (IData)(1U)))
                              : 0U);
            } else {
                __Vdly__j = (7U & ((IData)(1U) + (IData)(vlSelf->__PVT__j)));
            }
        }
    } else if ((1U & (IData)(vlSelf->__PVT__state))) {
        __Vdly__j = 0U;
        vlSelf->__PVT__imm_sr = vlSelf->__PVT__imm;
        __Vdly__shamt_w = ((IData)(vlSelf->__PVT__sh_i)
                            ? (IData)(vlSelf->__PVT__rs2)
                            : 0U);
        if (vlSelf->__PVT__bad) {
            vlSelf->__PVT__trap_r = 1U;
            vlSelf->__PVT__halted_r = 1U;
            __Vdly__state = 6U;
        } else if (vlSelf->__PVT__is_sys) {
            vlSelf->__PVT__halted_r = 1U;
            __Vdly__state = 6U;
        } else if (vlSelf->__PVT__is_shift) {
            __Vdly__state = 2U;
        } else {
            __Vdly__k = 0U;
            __Vdly__state = 3U;
        }
    } else {
        vlSelf->__PVT__ir = vlSymsp->TOP.tb_sys3__DOT__dut__DOT__slot__BRA__24__KET____DOT__id;
        __Vdly__state = 1U;
    }
    vlSelf->__PVT__addr = __Vdly__addr;
    vlSelf->__PVT__j = __Vdly__j;
    vlSelf->__PVT__shamt_w = __Vdly__shamt_w;
    vlSelf->__PVT__state = __Vdly__state;
    vlSelf->__PVT__k = __Vdly__k;
    vlSelf->d_addr = (((QData)((IData)((vlSelf->__PVT__addr 
                                        >> 2U))) << 5U) 
                      | (QData)((IData)(vlSelf->__PVT__k)));
    vlSelf->__PVT__wm1 = (0x3fU & (((IData)(1U) << (IData)(vlSelf->__PVT__lw_r)) 
                                   - (IData)(1U)));
    vlSelf->__PVT__mlast = (0x3fU & (VL_DIV_III(6, 
                                                (0x3fU 
                                                 & ((IData)(4U) 
                                                    + 
                                                    ((IData)(1U) 
                                                     << (IData)(vlSelf->__PVT__lw_r)))), 
                                                (0x3fU 
                                                 & ((IData)(1U) 
                                                    << (IData)(vlSelf->__PVT__lw_r)))) 
                                     - (IData)(1U)));
    vlSelf->__PVT__nd = (0x3fU & (0x20U >> (IData)(vlSelf->__PVT__lw_r)));
    vlSelf->__PVT__jw = (0x3fU & ((IData)(vlSelf->__PVT__j) 
                                  * (0x3fU & ((IData)(1U) 
                                              << (IData)(vlSelf->__PVT__lw_r)))));
    vlSelf->__PVT__imm_rot = (VL_SHIFTR_III(32,32,6, vlSelf->__PVT__imm_sr, 
                                            (0x3fU 
                                             & ((IData)(1U) 
                                                << (IData)(vlSelf->__PVT__lw_r)))) 
                              | VL_SHIFTL_III(32,32,6, vlSelf->__PVT__imm_sr, 
                                              (0x3fU 
                                               & ((IData)(0x20U) 
                                                  - 
                                                  ((IData)(1U) 
                                                   << (IData)(vlSelf->__PVT__lw_r))))));
    vlSelf->__PVT__last_up = ((IData)(vlSelf->__PVT__k) 
                              == (0x1fU & ((0x3fU & 
                                            (0x20U 
                                             >> (IData)(vlSelf->__PVT__lw_r))) 
                                           - (IData)(1U))));
    vlSelf->__VdfgTmp_he4828306__0 = VL_SHIFTR_III(32,32,6, vlSelf->__PVT__pc, 
                                                   (0x3fU 
                                                    & ((IData)(1U) 
                                                       << (IData)(vlSelf->__PVT__lw_r))));
    __VdfgTmp_h933689ae__0 = (0x1fU & (vlSelf->__PVT__shamt_w 
                                       & ((0x3fU & 
                                           ((IData)(1U) 
                                            << (IData)(vlSelf->__PVT__lw_r))) 
                                          - (IData)(1U))));
    __PVT__qs = (0x1fU & ((0x1fU & vlSelf->__PVT__shamt_w) 
                          >> (IData)(vlSelf->__PVT__lw_r)));
    vlSelf->__PVT__mask = ((5U == (IData)(vlSelf->__PVT__lw_r))
                            ? 0xffffffffU : (VL_SHIFTL_III(32,32,6, (IData)(1U), 
                                                           (0x3fU 
                                                            & ((IData)(1U) 
                                                               << (IData)(vlSelf->__PVT__lw_r)))) 
                                             - (IData)(1U)));
    vlSelf->__PVT__rs2 = (0x1fU & (vlSelf->__PVT__ir 
                                   >> 0x14U));
    vlSelf->__PVT__is_sys = (0x73U == (0x7fU & vlSelf->__PVT__ir));
    vlSelf->__PVT__opc = (0x7fU & vlSelf->__PVT__ir);
    __VdfgTmp_h2cd83c5b__0 = ((0x37U == (0x7fU & vlSelf->__PVT__ir)) 
                              | (0x17U == (0x7fU & vlSelf->__PVT__ir)));
    __Vtableidx25 = (((IData)(vlSelf->__PVT__f_eq) 
                      << 5U) | (((IData)(vlSelf->__PVT__f_lt) 
                                 << 4U) | (((IData)(vlSelf->__PVT__f_ltu) 
                                            << 3U) 
                                           | (7U & 
                                              (vlSelf->__PVT__ir 
                                               >> 0xcU)))));
    __PVT__cond = Vtb_sys3__ConstPool__TABLE_h2a0441a0_0
        [__Vtableidx25];
    __VdfgTmp_hd9b60348__0 = ((2U == (7U & (vlSelf->__PVT__ir 
                                            >> 0xcU))) 
                              | (3U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))));
    __VdfgTmp_h18c46dac__0 = ((0x13U == (0x7fU & vlSelf->__PVT__ir)) 
                              | (0x33U == (0x7fU & vlSelf->__PVT__ir)));
    __VdfgTmp_he83b8d53__0 = ((1U == (7U & (vlSelf->__PVT__ir 
                                            >> 0xcU))) 
                              | (5U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))));
    vlSelf->__PVT__pc_rot = (vlSelf->__VdfgTmp_he4828306__0 
                             | VL_SHIFTL_III(32,32,6, vlSelf->__PVT__pc, 
                                             (0x3fU 
                                              & ((IData)(0x20U) 
                                                 - 
                                                 ((IData)(1U) 
                                                  << (IData)(vlSelf->__PVT__lw_r))))));
    __PVT__pc_d = (vlSelf->__PVT__pc & vlSelf->__PVT__mask);
    __PVT__imm_d = (vlSelf->__PVT__imm_sr & vlSelf->__PVT__mask);
    __PVT__c4_d = (VL_SHIFTR_III(32,32,6, 4U, (0x3fU 
                                               & ((IData)(vlSelf->__PVT__k) 
                                                  * 
                                                  (0x3fU 
                                                   & ((IData)(1U) 
                                                      << (IData)(vlSelf->__PVT__lw_r)))))) 
                   & vlSelf->__PVT__mask);
    vlSelf->__PVT__imm = ((IData)(__VdfgTmp_h2cd83c5b__0)
                           ? (0xfffff000U & vlSelf->__PVT__ir)
                           : ((0x6fU == (0x7fU & vlSelf->__PVT__ir))
                               ? (((- (IData)((vlSelf->__PVT__ir 
                                               >> 0x1fU))) 
                                   << 0x15U) | ((0x100000U 
                                                 & (vlSelf->__PVT__ir 
                                                    >> 0xbU)) 
                                                | ((0xff000U 
                                                    & vlSelf->__PVT__ir) 
                                                   | ((0x800U 
                                                       & (vlSelf->__PVT__ir 
                                                          >> 9U)) 
                                                      | (0x7feU 
                                                         & (vlSelf->__PVT__ir 
                                                            >> 0x14U))))))
                               : ((0x63U == (0x7fU 
                                             & vlSelf->__PVT__ir))
                                   ? (((- (IData)((vlSelf->__PVT__ir 
                                                   >> 0x1fU))) 
                                       << 0xdU) | (
                                                   (0x1000U 
                                                    & (vlSelf->__PVT__ir 
                                                       >> 0x13U)) 
                                                   | ((0x800U 
                                                       & (vlSelf->__PVT__ir 
                                                          << 4U)) 
                                                      | ((0x7e0U 
                                                          & (vlSelf->__PVT__ir 
                                                             >> 0x14U)) 
                                                         | (0x1eU 
                                                            & (vlSelf->__PVT__ir 
                                                               >> 7U))))))
                                   : ((0x23U == (0x7fU 
                                                 & vlSelf->__PVT__ir))
                                       ? (((- (IData)(
                                                      (vlSelf->__PVT__ir 
                                                       >> 0x1fU))) 
                                           << 0xcU) 
                                          | ((0xfe0U 
                                              & (vlSelf->__PVT__ir 
                                                 >> 0x14U)) 
                                             | (0x1fU 
                                                & (vlSelf->__PVT__ir 
                                                   >> 7U))))
                                       : (((- (IData)(
                                                      (vlSelf->__PVT__ir 
                                                       >> 0x1fU))) 
                                           << 0xcU) 
                                          | (vlSelf->__PVT__ir 
                                             >> 0x14U))))));
    __VdfgExtracted_h62388771__0 = ((IData)(__VdfgTmp_h2cd83c5b__0) 
                                    | (0x6fU == (0x7fU 
                                                 & vlSelf->__PVT__ir)));
    vlSelf->__PVT__is_cmp = ((0x63U == (0x7fU & vlSelf->__PVT__ir)) 
                             | ((IData)(__VdfgTmp_h18c46dac__0) 
                                & (IData)(__VdfgTmp_hd9b60348__0)));
    vlSelf->__PVT__sh_i = ((0x13U == (0x7fU & vlSelf->__PVT__ir)) 
                           & (IData)(__VdfgTmp_he83b8d53__0));
    vlSelf->__PVT__bad = (1U & ((~ ((IData)(__VdfgExtracted_h62388771__0) 
                                    | ((0x67U == (0x7fU 
                                                  & vlSelf->__PVT__ir)) 
                                       | ((0x63U == 
                                           (0x7fU & vlSelf->__PVT__ir)) 
                                          | ((3U == 
                                              (0x7fU 
                                               & vlSelf->__PVT__ir)) 
                                             | ((0x23U 
                                                 == 
                                                 (0x7fU 
                                                  & vlSelf->__PVT__ir)) 
                                                | ((0x13U 
                                                    == 
                                                    (0x7fU 
                                                     & vlSelf->__PVT__ir)) 
                                                   | ((0x33U 
                                                       == 
                                                       (0x7fU 
                                                        & vlSelf->__PVT__ir)) 
                                                      | (0x73U 
                                                         == 
                                                         (0x7fU 
                                                          & vlSelf->__PVT__ir)))))))))) 
                                | (((0x67U == (0x7fU 
                                               & vlSelf->__PVT__ir)) 
                                    & (0U != (7U & 
                                              (vlSelf->__PVT__ir 
                                               >> 0xcU)))) 
                                   | (((0x63U == (0x7fU 
                                                  & vlSelf->__PVT__ir)) 
                                       & (IData)(__VdfgTmp_hd9b60348__0)) 
                                      | ((((3U == (0x7fU 
                                                   & vlSelf->__PVT__ir)) 
                                           | (0x23U 
                                              == (0x7fU 
                                                  & vlSelf->__PVT__ir))) 
                                          & (2U != 
                                             (7U & 
                                              (vlSelf->__PVT__ir 
                                               >> 0xcU)))) 
                                         | ((IData)(
                                                    ((0x1013U 
                                                      == 
                                                      (0x707fU 
                                                       & vlSelf->__PVT__ir)) 
                                                     & (0U 
                                                        != 
                                                        (vlSelf->__PVT__ir 
                                                         >> 0x19U)))) 
                                            | ((IData)(
                                                       ((0x5013U 
                                                         == 
                                                         (0x707fU 
                                                          & vlSelf->__PVT__ir)) 
                                                        & ((0U 
                                                            != 
                                                            (vlSelf->__PVT__ir 
                                                             >> 0x19U)) 
                                                           & (0x20U 
                                                              != 
                                                              (vlSelf->__PVT__ir 
                                                               >> 0x19U))))) 
                                               | ((0x33U 
                                                   == 
                                                   (0x7fU 
                                                    & vlSelf->__PVT__ir)) 
                                                  & ((~ 
                                                      ((0x20U 
                                                        == 
                                                        (vlSelf->__PVT__ir 
                                                         >> 0x19U)) 
                                                       & ((0U 
                                                           == 
                                                           (7U 
                                                            & (vlSelf->__PVT__ir 
                                                               >> 0xcU))) 
                                                          | (5U 
                                                             == 
                                                             (7U 
                                                              & (vlSelf->__PVT__ir 
                                                                 >> 0xcU)))))) 
                                                     & (0U 
                                                        != 
                                                        (vlSelf->__PVT__ir 
                                                         >> 0x19U)))))))))));
    vlSelf->__PVT__is_slt = ((0x63U != (0x7fU & vlSelf->__PVT__ir)) 
                             & (IData)(vlSelf->__PVT__is_cmp));
    __PVT__inv = 0U;
    vlSelf->__PVT__is_shift = ((IData)(vlSelf->__PVT__sh_i) 
                               | ((0x33U == (0x7fU 
                                             & vlSelf->__PVT__ir)) 
                                  & (IData)(__VdfgTmp_he83b8d53__0)));
    vlSelf->__PVT__we = 0U;
    __PVT__fill = (((IData)(vlSelf->__PVT__is_shift) 
                    & (IData)(((0x40005000U == (0x40007000U 
                                                & vlSelf->__PVT__ir)) 
                               & (IData)(vlSelf->__PVT__sgn))))
                    ? vlSelf->__PVT__mask : 0U);
    __PVT__shx = ((3U == (IData)(vlSelf->__PVT__state)) 
                  & (IData)(vlSelf->__PVT__is_shift));
    vlSelf->__PVT__is_sll = ((IData)(vlSelf->__PVT__is_shift) 
                             & (0x1000U == (0x7000U 
                                            & vlSelf->__PVT__ir)));
    if (vlSelf->__PVT__is_sll) {
        vlSelf->__PVT__exec_done = (0U == (IData)(vlSelf->__PVT__k));
        __PVT__ia = (0x1ffU & ((IData)(vlSelf->__PVT__k) 
                               - (IData)(__PVT__qs)));
        __VdfgTmp_h41a48239__0 = ((VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__k)) 
                                   - VL_EXTENDS_II(32,9, (IData)(__PVT__qs))) 
                                  - (IData)(1U));
    } else {
        vlSelf->__PVT__exec_done = vlSelf->__PVT__last_up;
        __PVT__ia = (0x1ffU & ((IData)(vlSelf->__PVT__k) 
                               + (IData)(__PVT__qs)));
        __VdfgTmp_h41a48239__0 = ((IData)(1U) + (VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__k)) 
                                                 + 
                                                 VL_EXTENDS_II(32,9, (IData)(__PVT__qs))));
    }
    __PVT__va = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, (IData)(__PVT__ia))) 
                 & VL_LTES_III(9, (IData)(__PVT__ia), 
                               (0x1ffU & ((0x3fU & 
                                           (0x20U >> (IData)(vlSelf->__PVT__lw_r))) 
                                          - (IData)(1U)))));
    vlSelf->__PVT__a_val = ((0U == (0x1fU & (vlSelf->__PVT__ir 
                                             >> 0xfU)))
                             ? 0U : (vlSymsp->TOP.tb_sys3__DOT__dut__DOT__slot__BRA__24__KET____DOT__rf
                                     [((0x3e0U & (vlSelf->__PVT__ir 
                                                  >> 0xaU)) 
                                       | (0x1fU & (
                                                   (2U 
                                                    == (IData)(vlSelf->__PVT__state))
                                                    ? 
                                                   ((0x3fU 
                                                     & (0x20U 
                                                        >> (IData)(vlSelf->__PVT__lw_r))) 
                                                    - (IData)(1U))
                                                    : 
                                                   ((IData)(__PVT__shx)
                                                     ? (IData)(__PVT__ia)
                                                     : (IData)(vlSelf->__PVT__k)))))] 
                                     & vlSelf->__PVT__mask));
    __PVT__vb = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, 
                                                   (0x1ffU 
                                                    & __VdfgTmp_h41a48239__0))) 
                 & VL_LTES_III(9, (0x1ffU & __VdfgTmp_h41a48239__0), 
                               (0x1ffU & ((0x3fU & 
                                           (0x20U >> (IData)(vlSelf->__PVT__lw_r))) 
                                          - (IData)(1U)))));
    vlSelf->d_wdata = (((IData)(__PVT__shx) ? (0U == 
                                               (0x1fU 
                                                & (vlSelf->__PVT__ir 
                                                   >> 0xfU)))
                         : (0U == (0x1fU & (vlSelf->__PVT__ir 
                                            >> 0x14U))))
                        ? 0U : (vlSymsp->TOP.tb_sys3__DOT__dut__DOT__slot__BRA__24__KET____DOT__rf
                                [((0x3e0U & (((IData)(__PVT__shx)
                                               ? (vlSelf->__PVT__ir 
                                                  >> 0xfU)
                                               : (vlSelf->__PVT__ir 
                                                  >> 0x14U)) 
                                             << 5U)) 
                                  | (0x1fU & ((2U == (IData)(vlSelf->__PVT__state))
                                               ? (IData)(vlSelf->__PVT__j)
                                               : ((IData)(__PVT__shx)
                                                   ? __VdfgTmp_h41a48239__0
                                                   : (IData)(vlSelf->__PVT__k)))))] 
                                & vlSelf->__PVT__mask));
    __PVT__X = vlSelf->__PVT__a_val;
    __PVT__Yr = (((0x33U == (0x7fU & vlSelf->__PVT__ir)) 
                  | (0x63U == (0x7fU & vlSelf->__PVT__ir)))
                  ? vlSelf->d_wdata : __PVT__imm_d);
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if ((0x37U != (0x7fU & vlSelf->__PVT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->__PVT__ir))) {
                if ((0x6fU != (0x7fU & vlSelf->__PVT__ir))) {
                    if (((IData)((0x40000033U == (0x4000707fU 
                                                  & vlSelf->__PVT__ir))) 
                         | (IData)(vlSelf->__PVT__is_cmp))) {
                        __PVT__inv = 1U;
                    }
                }
            }
        }
        if (vlSelf->__PVT__is_shift) {
            vlSelf->__PVT__we = 1U;
        } else if (__VdfgExtracted_h62388771__0) {
            vlSelf->__PVT__we = 1U;
        } else if (((~ (IData)(vlSelf->__PVT__is_cmp)) 
                    & (IData)(__VdfgTmp_h18c46dac__0))) {
            vlSelf->__PVT__we = 1U;
        }
        if ((0x37U == (0x7fU & vlSelf->__PVT__ir))) {
            __PVT__X = 0U;
        } else if ((0x17U == (0x7fU & vlSelf->__PVT__ir))) {
            __PVT__X = __PVT__pc_d;
        } else if ((0x6fU == (0x7fU & vlSelf->__PVT__ir))) {
            __PVT__X = __PVT__pc_d;
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        if ((3U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__we = 1U;
        } else if (vlSelf->__PVT__is_slt) {
            vlSelf->__PVT__we = 1U;
        } else if ((0x67U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__we = 1U;
        }
        __PVT__X = __PVT__pc_d;
    } else if ((5U == (IData)(vlSelf->__PVT__state))) {
        __PVT__X = __PVT__pc_d;
    }
    vlSelf->__PVT__xsh = VL_SHIFTR_III(32,32,6, __PVT__X, 
                                       (0x3fU & (((IData)(1U) 
                                                  << (IData)(vlSelf->__PVT__lw_r)) 
                                                 - (IData)(1U))));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if ((0x37U != (0x7fU & vlSelf->__PVT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->__PVT__ir))) {
                if ((0x6fU == (0x7fU & vlSelf->__PVT__ir))) {
                    __PVT__Yr = __PVT__c4_d;
                }
            }
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        __PVT__Yr = __PVT__c4_d;
    } else if ((5U == (IData)(vlSelf->__PVT__state))) {
        __PVT__Yr = (((0x6fU == (0x7fU & vlSelf->__PVT__ir)) 
                      | ((0x63U == (0x7fU & vlSelf->__PVT__ir)) 
                         & (IData)(__PVT__cond))) ? __PVT__imm_d
                      : __PVT__c4_d);
    }
    vlSelf->__PVT__ysh = VL_SHIFTR_III(32,32,6, __PVT__Yr, 
                                       (0x3fU & (((IData)(1U) 
                                                  << (IData)(vlSelf->__PVT__lw_r)) 
                                                 - (IData)(1U))));
    __PVT__sum_full = (0x1ffffffffULL & ((QData)((IData)(__PVT__X)) 
                                         + ((QData)((IData)(
                                                            ((IData)(__PVT__inv)
                                                              ? 
                                                             ((~ __PVT__Yr) 
                                                              & vlSelf->__PVT__mask)
                                                              : __PVT__Yr))) 
                                            + (QData)((IData)(
                                                              ((0U 
                                                                == (IData)(vlSelf->__PVT__k))
                                                                ? (IData)(__PVT__inv)
                                                                : (IData)(vlSelf->__PVT__cy)))))));
    vlSelf->__PVT__cout = (1U & (IData)((0x1ffffffffULL 
                                         & (__PVT__sum_full 
                                            >> (0x3fU 
                                                & ((IData)(1U) 
                                                   << (IData)(vlSelf->__PVT__lw_r)))))));
    __PVT__sum_d = ((IData)(__PVT__sum_full) & vlSelf->__PVT__mask);
    vlSelf->__PVT__nz_n = (((0U != (IData)(vlSelf->__PVT__k)) 
                            & (IData)(vlSelf->__PVT__nz)) 
                           | (0U != __PVT__sum_d));
    vlSelf->__VdfgTmp_h7980eff3__0 = VL_SHIFTL_III(32,32,6, __PVT__sum_d, 
                                                   (0x3fU 
                                                    & ((IData)(0x20U) 
                                                       - 
                                                       ((IData)(1U) 
                                                        << (IData)(vlSelf->__PVT__lw_r)))));
    vlSelf->__PVT__wd = (((IData)(__VdfgTmp_h18c46dac__0) 
                          & ((4U == (7U & (vlSelf->__PVT__ir 
                                           >> 0xcU))) 
                             | ((6U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))) 
                                | (7U == (7U & (vlSelf->__PVT__ir 
                                                >> 0xcU))))))
                          ? ((4U == (7U & (vlSelf->__PVT__ir 
                                           >> 0xcU)))
                              ? (__PVT__X ^ __PVT__Yr)
                              : ((6U == (7U & (vlSelf->__PVT__ir 
                                               >> 0xcU)))
                                  ? (__PVT__X | __PVT__Yr)
                                  : (__PVT__X & __PVT__Yr)))
                          : __PVT__sum_d);
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if (vlSelf->__PVT__is_shift) {
            vlSelf->__PVT__wd = ((IData)(((((QData)((IData)(
                                                            ((IData)(vlSelf->__PVT__is_sll)
                                                              ? 
                                                             ((IData)(__PVT__va)
                                                               ? vlSelf->__PVT__a_val
                                                               : 0U)
                                                              : 
                                                             ((IData)(__PVT__vb)
                                                               ? vlSelf->d_wdata
                                                               : __PVT__fill)))) 
                                            << (0x3fU 
                                                & ((IData)(1U) 
                                                   << (IData)(vlSelf->__PVT__lw_r)))) 
                                           | (QData)((IData)(
                                                             ((IData)(vlSelf->__PVT__is_sll)
                                                               ? 
                                                              ((IData)(__PVT__vb)
                                                                ? vlSelf->d_wdata
                                                                : 0U)
                                                               : 
                                                              ((IData)(__PVT__va)
                                                                ? vlSelf->__PVT__a_val
                                                                : __PVT__fill))))) 
                                          >> (0x3fU 
                                              & ((IData)(vlSelf->__PVT__is_sll)
                                                  ? 
                                                 (((IData)(1U) 
                                                   << (IData)(vlSelf->__PVT__lw_r)) 
                                                  - (IData)(__VdfgTmp_h933689ae__0))
                                                  : (IData)(__VdfgTmp_h933689ae__0))))) 
                                 & vlSelf->__PVT__mask);
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        if ((3U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__wd = (vlSymsp->TOP.tb_sys3__DOT__dut__DOT__slot__BRA__24__KET____DOT__dm
                                 [(0x7fffU & (IData)(vlSelf->d_addr))] 
                                 & vlSelf->__PVT__mask);
        } else if (vlSelf->__PVT__is_slt) {
            vlSelf->__PVT__wd = 0U;
            vlSelf->__PVT__wd = ((0xfffffffeU & vlSelf->__PVT__wd) 
                                 | ((0U == (IData)(vlSelf->__PVT__k)) 
                                    & ((2U == (7U & 
                                               (vlSelf->__PVT__ir 
                                                >> 0xcU)))
                                        ? (IData)(vlSelf->__PVT__f_lt)
                                        : (IData)(vlSelf->__PVT__f_ltu))));
        } else if ((0x67U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__wd = __PVT__sum_d;
        }
    }
    vlSelf->__PVT__addr_ins = (VL_SHIFTR_III(32,32,6, vlSelf->__PVT__addr, 
                                             (0x3fU 
                                              & ((IData)(1U) 
                                                 << (IData)(vlSelf->__PVT__lw_r)))) 
                               | vlSelf->__VdfgTmp_h7980eff3__0);
}

VL_INLINE_OPT void Vtb_sys3_uc_core_rw___nba_sequent__TOP__tb_sys3__DOT__dut__DOT__slot__BRA__25__KET____DOT__core__0(Vtb_sys3_uc_core_rw* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_sys3__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+          Vtb_sys3_uc_core_rw___nba_sequent__TOP__tb_sys3__DOT__dut__DOT__slot__BRA__25__KET____DOT__core__0\n"); );
    // Init
    CData/*0:0*/ __PVT__shx;
    __PVT__shx = 0;
    IData/*31:0*/ __PVT__pc_d;
    __PVT__pc_d = 0;
    IData/*31:0*/ __PVT__imm_d;
    __PVT__imm_d = 0;
    IData/*31:0*/ __PVT__c4_d;
    __PVT__c4_d = 0;
    SData/*8:0*/ __PVT__qs;
    __PVT__qs = 0;
    SData/*8:0*/ __PVT__ia;
    __PVT__ia = 0;
    CData/*0:0*/ __PVT__va;
    __PVT__va = 0;
    CData/*0:0*/ __PVT__vb;
    __PVT__vb = 0;
    IData/*31:0*/ __PVT__fill;
    __PVT__fill = 0;
    IData/*31:0*/ __PVT__X;
    __PVT__X = 0;
    IData/*31:0*/ __PVT__Yr;
    __PVT__Yr = 0;
    CData/*0:0*/ __PVT__inv;
    __PVT__inv = 0;
    QData/*32:0*/ __PVT__sum_full;
    __PVT__sum_full = 0;
    IData/*31:0*/ __PVT__sum_d;
    __PVT__sum_d = 0;
    CData/*0:0*/ __PVT__cond;
    __PVT__cond = 0;
    CData/*0:0*/ __VdfgExtracted_h62388771__0;
    __VdfgExtracted_h62388771__0 = 0;
    IData/*31:0*/ __VdfgTmp_h41a48239__0;
    __VdfgTmp_h41a48239__0 = 0;
    CData/*0:0*/ __VdfgTmp_h2cd83c5b__0;
    __VdfgTmp_h2cd83c5b__0 = 0;
    CData/*0:0*/ __VdfgTmp_he83b8d53__0;
    __VdfgTmp_he83b8d53__0 = 0;
    CData/*0:0*/ __VdfgTmp_h18c46dac__0;
    __VdfgTmp_h18c46dac__0 = 0;
    CData/*0:0*/ __VdfgTmp_hd9b60348__0;
    __VdfgTmp_hd9b60348__0 = 0;
    CData/*5:0*/ __VdfgTmp_h933689ae__0;
    __VdfgTmp_h933689ae__0 = 0;
    CData/*5:0*/ __Vtableidx26;
    __Vtableidx26 = 0;
    CData/*2:0*/ __Vdly__state;
    __Vdly__state = 0;
    IData/*31:0*/ __Vdly__addr;
    __Vdly__addr = 0;
    IData/*31:0*/ __Vdly__shamt_w;
    __Vdly__shamt_w = 0;
    CData/*4:0*/ __Vdly__k;
    __Vdly__k = 0;
    CData/*2:0*/ __Vdly__j;
    __Vdly__j = 0;
    // Body
    __Vdly__addr = vlSelf->__PVT__addr;
    __Vdly__j = vlSelf->__PVT__j;
    __Vdly__shamt_w = vlSelf->__PVT__shamt_w;
    __Vdly__state = vlSelf->__PVT__state;
    __Vdly__k = vlSelf->__PVT__k;
    if (vlSymsp->TOP.tb_sys3__DOT__rst) {
        __Vdly__state = 6U;
        vlSelf->__PVT__pc = 0U;
        vlSelf->__PVT__ir = 0U;
        __Vdly__addr = 0U;
        vlSelf->__PVT__imm_sr = 0U;
        __Vdly__shamt_w = 0U;
        __Vdly__k = 0U;
        __Vdly__j = 0U;
        vlSelf->__PVT__lw_r = 0U;
        vlSelf->__PVT__cy = 0U;
        vlSelf->__PVT__nz = 0U;
        vlSelf->__PVT__f_eq = 0U;
        vlSelf->__PVT__f_lt = 0U;
        vlSelf->__PVT__f_ltu = 0U;
        vlSelf->__PVT__sgn = 0U;
        vlSelf->__PVT__halted_r = 1U;
        vlSelf->__PVT__trap_r = 0U;
    } else if (((vlSymsp->TOP.tb_sys3__DOT__dut__DOT__start_v 
                 >> 0x19U) & (6U == (IData)(vlSelf->__PVT__state)))) {
        vlSelf->__PVT__pc = vlSymsp->TOP.tb_sys3__DOT__dut__DOT__launch_entry;
        vlSelf->__PVT__lw_r = vlSymsp->TOP.tb_sys3__DOT__dut__DOT__launch_lw;
        __Vdly__k = 0U;
        vlSelf->__PVT__halted_r = 0U;
        vlSelf->__PVT__trap_r = 0U;
        __Vdly__state = 0U;
    } else if ((4U & (IData)(vlSelf->__PVT__state))) {
        if ((1U & (~ ((IData)(vlSelf->__PVT__state) 
                      >> 1U)))) {
            if ((1U & (IData)(vlSelf->__PVT__state))) {
                if ((0x67U == (IData)(vlSelf->__PVT__opc))) {
                    vlSelf->__PVT__pc = (0xfffffffeU 
                                         & vlSelf->__PVT__addr);
                    __Vdly__state = 0U;
                } else {
                    vlSelf->__PVT__pc = (vlSelf->__VdfgTmp_he4828306__0 
                                         | vlSelf->__VdfgTmp_h7980eff3__0);
                    vlSelf->__PVT__imm_sr = vlSelf->__PVT__imm_rot;
                    vlSelf->__PVT__cy = vlSelf->__PVT__cout;
                    if (vlSelf->__PVT__last_up) {
                        __Vdly__k = 0U;
                        __Vdly__state = 0U;
                    } else {
                        __Vdly__k = (0x1fU & ((IData)(1U) 
                                              + (IData)(vlSelf->__PVT__k)));
                    }
                }
            } else {
                vlSelf->__PVT__cy = vlSelf->__PVT__cout;
                vlSelf->__PVT__pc = vlSelf->__PVT__pc_rot;
                if (vlSelf->__PVT__last_up) {
                    __Vdly__k = 0U;
                    __Vdly__state = 5U;
                } else {
                    __Vdly__k = (0x1fU & ((IData)(1U) 
                                          + (IData)(vlSelf->__PVT__k)));
                }
            }
        }
    } else if ((2U & (IData)(vlSelf->__PVT__state))) {
        if ((1U & (IData)(vlSelf->__PVT__state))) {
            vlSelf->__PVT__cy = vlSelf->__PVT__cout;
            if (vlSelf->__PVT__is_cmp) {
                vlSelf->__PVT__nz = vlSelf->__PVT__nz_n;
                if (vlSelf->__PVT__last_up) {
                    vlSelf->__PVT__f_eq = (1U & (~ (IData)(vlSelf->__PVT__nz_n)));
                    vlSelf->__PVT__f_ltu = (1U & (~ (IData)(vlSelf->__PVT__cout)));
                    vlSelf->__PVT__f_lt = (1U & (((1U 
                                                   & vlSelf->__PVT__xsh) 
                                                  != 
                                                  (1U 
                                                   & vlSelf->__PVT__ysh))
                                                  ? vlSelf->__PVT__xsh
                                                  : 
                                                 (~ (IData)(vlSelf->__PVT__cout))));
                }
            }
            if ((((3U == (IData)(vlSelf->__PVT__opc)) 
                  | (0x23U == (IData)(vlSelf->__PVT__opc))) 
                 | (0x67U == (IData)(vlSelf->__PVT__opc)))) {
                __Vdly__addr = vlSelf->__PVT__addr_ins;
            }
            vlSelf->__PVT__pc = vlSelf->__PVT__pc_rot;
            vlSelf->__PVT__imm_sr = vlSelf->__PVT__imm_rot;
            if (vlSelf->__PVT__exec_done) {
                __Vdly__k = 0U;
                __Vdly__state = (((((3U == (IData)(vlSelf->__PVT__opc)) 
                                    | (0x23U == (IData)(vlSelf->__PVT__opc))) 
                                   | (0x67U == (IData)(vlSelf->__PVT__opc))) 
                                  | (IData)(vlSelf->__PVT__is_slt))
                                  ? 4U : 5U);
            } else {
                __Vdly__k = (0x1fU & ((IData)(vlSelf->__PVT__is_sll)
                                       ? ((IData)(vlSelf->__PVT__k) 
                                          - (IData)(1U))
                                       : ((IData)(1U) 
                                          + (IData)(vlSelf->__PVT__k))));
            }
        } else {
            if ((0x33U == (IData)(vlSelf->__PVT__opc))) {
                __Vdly__shamt_w = ((vlSelf->__PVT__shamt_w 
                                    & (~ VL_SHIFTL_III(32,32,6, vlSelf->__PVT__mask, (IData)(vlSelf->__PVT__jw)))) 
                                   | VL_SHIFTL_III(32,32,6, vlSelf->d_wdata, (IData)(vlSelf->__PVT__jw)));
            }
            vlSelf->__PVT__sgn = (1U & (vlSelf->__PVT__a_val 
                                        >> (0x1fU & (IData)(vlSelf->__PVT__wm1))));
            if (((IData)(vlSelf->__PVT__j) == ((0x33U 
                                                == (IData)(vlSelf->__PVT__opc))
                                                ? (IData)(vlSelf->__PVT__mlast)
                                                : 0U))) {
                __Vdly__state = 3U;
                __Vdly__k = ((IData)(vlSelf->__PVT__is_sll)
                              ? (0x1fU & ((IData)(vlSelf->__PVT__nd) 
                                          - (IData)(1U)))
                              : 0U);
            } else {
                __Vdly__j = (7U & ((IData)(1U) + (IData)(vlSelf->__PVT__j)));
            }
        }
    } else if ((1U & (IData)(vlSelf->__PVT__state))) {
        __Vdly__j = 0U;
        vlSelf->__PVT__imm_sr = vlSelf->__PVT__imm;
        __Vdly__shamt_w = ((IData)(vlSelf->__PVT__sh_i)
                            ? (IData)(vlSelf->__PVT__rs2)
                            : 0U);
        if (vlSelf->__PVT__bad) {
            vlSelf->__PVT__trap_r = 1U;
            vlSelf->__PVT__halted_r = 1U;
            __Vdly__state = 6U;
        } else if (vlSelf->__PVT__is_sys) {
            vlSelf->__PVT__halted_r = 1U;
            __Vdly__state = 6U;
        } else if (vlSelf->__PVT__is_shift) {
            __Vdly__state = 2U;
        } else {
            __Vdly__k = 0U;
            __Vdly__state = 3U;
        }
    } else {
        vlSelf->__PVT__ir = vlSymsp->TOP.tb_sys3__DOT__dut__DOT__slot__BRA__25__KET____DOT__id;
        __Vdly__state = 1U;
    }
    vlSelf->__PVT__addr = __Vdly__addr;
    vlSelf->__PVT__j = __Vdly__j;
    vlSelf->__PVT__shamt_w = __Vdly__shamt_w;
    vlSelf->__PVT__state = __Vdly__state;
    vlSelf->__PVT__k = __Vdly__k;
    vlSelf->d_addr = (((QData)((IData)((vlSelf->__PVT__addr 
                                        >> 2U))) << 5U) 
                      | (QData)((IData)(vlSelf->__PVT__k)));
    vlSelf->__PVT__wm1 = (0x3fU & (((IData)(1U) << (IData)(vlSelf->__PVT__lw_r)) 
                                   - (IData)(1U)));
    vlSelf->__PVT__mlast = (0x3fU & (VL_DIV_III(6, 
                                                (0x3fU 
                                                 & ((IData)(4U) 
                                                    + 
                                                    ((IData)(1U) 
                                                     << (IData)(vlSelf->__PVT__lw_r)))), 
                                                (0x3fU 
                                                 & ((IData)(1U) 
                                                    << (IData)(vlSelf->__PVT__lw_r)))) 
                                     - (IData)(1U)));
    vlSelf->__PVT__nd = (0x3fU & (0x20U >> (IData)(vlSelf->__PVT__lw_r)));
    vlSelf->__PVT__jw = (0x3fU & ((IData)(vlSelf->__PVT__j) 
                                  * (0x3fU & ((IData)(1U) 
                                              << (IData)(vlSelf->__PVT__lw_r)))));
    vlSelf->__PVT__imm_rot = (VL_SHIFTR_III(32,32,6, vlSelf->__PVT__imm_sr, 
                                            (0x3fU 
                                             & ((IData)(1U) 
                                                << (IData)(vlSelf->__PVT__lw_r)))) 
                              | VL_SHIFTL_III(32,32,6, vlSelf->__PVT__imm_sr, 
                                              (0x3fU 
                                               & ((IData)(0x20U) 
                                                  - 
                                                  ((IData)(1U) 
                                                   << (IData)(vlSelf->__PVT__lw_r))))));
    vlSelf->__PVT__last_up = ((IData)(vlSelf->__PVT__k) 
                              == (0x1fU & ((0x3fU & 
                                            (0x20U 
                                             >> (IData)(vlSelf->__PVT__lw_r))) 
                                           - (IData)(1U))));
    vlSelf->__VdfgTmp_he4828306__0 = VL_SHIFTR_III(32,32,6, vlSelf->__PVT__pc, 
                                                   (0x3fU 
                                                    & ((IData)(1U) 
                                                       << (IData)(vlSelf->__PVT__lw_r))));
    __VdfgTmp_h933689ae__0 = (0x1fU & (vlSelf->__PVT__shamt_w 
                                       & ((0x3fU & 
                                           ((IData)(1U) 
                                            << (IData)(vlSelf->__PVT__lw_r))) 
                                          - (IData)(1U))));
    __PVT__qs = (0x1fU & ((0x1fU & vlSelf->__PVT__shamt_w) 
                          >> (IData)(vlSelf->__PVT__lw_r)));
    vlSelf->__PVT__mask = ((5U == (IData)(vlSelf->__PVT__lw_r))
                            ? 0xffffffffU : (VL_SHIFTL_III(32,32,6, (IData)(1U), 
                                                           (0x3fU 
                                                            & ((IData)(1U) 
                                                               << (IData)(vlSelf->__PVT__lw_r)))) 
                                             - (IData)(1U)));
    vlSelf->__PVT__rs2 = (0x1fU & (vlSelf->__PVT__ir 
                                   >> 0x14U));
    vlSelf->__PVT__is_sys = (0x73U == (0x7fU & vlSelf->__PVT__ir));
    vlSelf->__PVT__opc = (0x7fU & vlSelf->__PVT__ir);
    __VdfgTmp_h2cd83c5b__0 = ((0x37U == (0x7fU & vlSelf->__PVT__ir)) 
                              | (0x17U == (0x7fU & vlSelf->__PVT__ir)));
    __Vtableidx26 = (((IData)(vlSelf->__PVT__f_eq) 
                      << 5U) | (((IData)(vlSelf->__PVT__f_lt) 
                                 << 4U) | (((IData)(vlSelf->__PVT__f_ltu) 
                                            << 3U) 
                                           | (7U & 
                                              (vlSelf->__PVT__ir 
                                               >> 0xcU)))));
    __PVT__cond = Vtb_sys3__ConstPool__TABLE_h2a0441a0_0
        [__Vtableidx26];
    __VdfgTmp_hd9b60348__0 = ((2U == (7U & (vlSelf->__PVT__ir 
                                            >> 0xcU))) 
                              | (3U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))));
    __VdfgTmp_h18c46dac__0 = ((0x13U == (0x7fU & vlSelf->__PVT__ir)) 
                              | (0x33U == (0x7fU & vlSelf->__PVT__ir)));
    __VdfgTmp_he83b8d53__0 = ((1U == (7U & (vlSelf->__PVT__ir 
                                            >> 0xcU))) 
                              | (5U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))));
    vlSelf->__PVT__pc_rot = (vlSelf->__VdfgTmp_he4828306__0 
                             | VL_SHIFTL_III(32,32,6, vlSelf->__PVT__pc, 
                                             (0x3fU 
                                              & ((IData)(0x20U) 
                                                 - 
                                                 ((IData)(1U) 
                                                  << (IData)(vlSelf->__PVT__lw_r))))));
    __PVT__pc_d = (vlSelf->__PVT__pc & vlSelf->__PVT__mask);
    __PVT__imm_d = (vlSelf->__PVT__imm_sr & vlSelf->__PVT__mask);
    __PVT__c4_d = (VL_SHIFTR_III(32,32,6, 4U, (0x3fU 
                                               & ((IData)(vlSelf->__PVT__k) 
                                                  * 
                                                  (0x3fU 
                                                   & ((IData)(1U) 
                                                      << (IData)(vlSelf->__PVT__lw_r)))))) 
                   & vlSelf->__PVT__mask);
    vlSelf->__PVT__imm = ((IData)(__VdfgTmp_h2cd83c5b__0)
                           ? (0xfffff000U & vlSelf->__PVT__ir)
                           : ((0x6fU == (0x7fU & vlSelf->__PVT__ir))
                               ? (((- (IData)((vlSelf->__PVT__ir 
                                               >> 0x1fU))) 
                                   << 0x15U) | ((0x100000U 
                                                 & (vlSelf->__PVT__ir 
                                                    >> 0xbU)) 
                                                | ((0xff000U 
                                                    & vlSelf->__PVT__ir) 
                                                   | ((0x800U 
                                                       & (vlSelf->__PVT__ir 
                                                          >> 9U)) 
                                                      | (0x7feU 
                                                         & (vlSelf->__PVT__ir 
                                                            >> 0x14U))))))
                               : ((0x63U == (0x7fU 
                                             & vlSelf->__PVT__ir))
                                   ? (((- (IData)((vlSelf->__PVT__ir 
                                                   >> 0x1fU))) 
                                       << 0xdU) | (
                                                   (0x1000U 
                                                    & (vlSelf->__PVT__ir 
                                                       >> 0x13U)) 
                                                   | ((0x800U 
                                                       & (vlSelf->__PVT__ir 
                                                          << 4U)) 
                                                      | ((0x7e0U 
                                                          & (vlSelf->__PVT__ir 
                                                             >> 0x14U)) 
                                                         | (0x1eU 
                                                            & (vlSelf->__PVT__ir 
                                                               >> 7U))))))
                                   : ((0x23U == (0x7fU 
                                                 & vlSelf->__PVT__ir))
                                       ? (((- (IData)(
                                                      (vlSelf->__PVT__ir 
                                                       >> 0x1fU))) 
                                           << 0xcU) 
                                          | ((0xfe0U 
                                              & (vlSelf->__PVT__ir 
                                                 >> 0x14U)) 
                                             | (0x1fU 
                                                & (vlSelf->__PVT__ir 
                                                   >> 7U))))
                                       : (((- (IData)(
                                                      (vlSelf->__PVT__ir 
                                                       >> 0x1fU))) 
                                           << 0xcU) 
                                          | (vlSelf->__PVT__ir 
                                             >> 0x14U))))));
    __VdfgExtracted_h62388771__0 = ((IData)(__VdfgTmp_h2cd83c5b__0) 
                                    | (0x6fU == (0x7fU 
                                                 & vlSelf->__PVT__ir)));
    vlSelf->__PVT__is_cmp = ((0x63U == (0x7fU & vlSelf->__PVT__ir)) 
                             | ((IData)(__VdfgTmp_h18c46dac__0) 
                                & (IData)(__VdfgTmp_hd9b60348__0)));
    vlSelf->__PVT__sh_i = ((0x13U == (0x7fU & vlSelf->__PVT__ir)) 
                           & (IData)(__VdfgTmp_he83b8d53__0));
    vlSelf->__PVT__bad = (1U & ((~ ((IData)(__VdfgExtracted_h62388771__0) 
                                    | ((0x67U == (0x7fU 
                                                  & vlSelf->__PVT__ir)) 
                                       | ((0x63U == 
                                           (0x7fU & vlSelf->__PVT__ir)) 
                                          | ((3U == 
                                              (0x7fU 
                                               & vlSelf->__PVT__ir)) 
                                             | ((0x23U 
                                                 == 
                                                 (0x7fU 
                                                  & vlSelf->__PVT__ir)) 
                                                | ((0x13U 
                                                    == 
                                                    (0x7fU 
                                                     & vlSelf->__PVT__ir)) 
                                                   | ((0x33U 
                                                       == 
                                                       (0x7fU 
                                                        & vlSelf->__PVT__ir)) 
                                                      | (0x73U 
                                                         == 
                                                         (0x7fU 
                                                          & vlSelf->__PVT__ir)))))))))) 
                                | (((0x67U == (0x7fU 
                                               & vlSelf->__PVT__ir)) 
                                    & (0U != (7U & 
                                              (vlSelf->__PVT__ir 
                                               >> 0xcU)))) 
                                   | (((0x63U == (0x7fU 
                                                  & vlSelf->__PVT__ir)) 
                                       & (IData)(__VdfgTmp_hd9b60348__0)) 
                                      | ((((3U == (0x7fU 
                                                   & vlSelf->__PVT__ir)) 
                                           | (0x23U 
                                              == (0x7fU 
                                                  & vlSelf->__PVT__ir))) 
                                          & (2U != 
                                             (7U & 
                                              (vlSelf->__PVT__ir 
                                               >> 0xcU)))) 
                                         | ((IData)(
                                                    ((0x1013U 
                                                      == 
                                                      (0x707fU 
                                                       & vlSelf->__PVT__ir)) 
                                                     & (0U 
                                                        != 
                                                        (vlSelf->__PVT__ir 
                                                         >> 0x19U)))) 
                                            | ((IData)(
                                                       ((0x5013U 
                                                         == 
                                                         (0x707fU 
                                                          & vlSelf->__PVT__ir)) 
                                                        & ((0U 
                                                            != 
                                                            (vlSelf->__PVT__ir 
                                                             >> 0x19U)) 
                                                           & (0x20U 
                                                              != 
                                                              (vlSelf->__PVT__ir 
                                                               >> 0x19U))))) 
                                               | ((0x33U 
                                                   == 
                                                   (0x7fU 
                                                    & vlSelf->__PVT__ir)) 
                                                  & ((~ 
                                                      ((0x20U 
                                                        == 
                                                        (vlSelf->__PVT__ir 
                                                         >> 0x19U)) 
                                                       & ((0U 
                                                           == 
                                                           (7U 
                                                            & (vlSelf->__PVT__ir 
                                                               >> 0xcU))) 
                                                          | (5U 
                                                             == 
                                                             (7U 
                                                              & (vlSelf->__PVT__ir 
                                                                 >> 0xcU)))))) 
                                                     & (0U 
                                                        != 
                                                        (vlSelf->__PVT__ir 
                                                         >> 0x19U)))))))))));
    vlSelf->__PVT__is_slt = ((0x63U != (0x7fU & vlSelf->__PVT__ir)) 
                             & (IData)(vlSelf->__PVT__is_cmp));
    __PVT__inv = 0U;
    vlSelf->__PVT__is_shift = ((IData)(vlSelf->__PVT__sh_i) 
                               | ((0x33U == (0x7fU 
                                             & vlSelf->__PVT__ir)) 
                                  & (IData)(__VdfgTmp_he83b8d53__0)));
    vlSelf->__PVT__we = 0U;
    __PVT__fill = (((IData)(vlSelf->__PVT__is_shift) 
                    & (IData)(((0x40005000U == (0x40007000U 
                                                & vlSelf->__PVT__ir)) 
                               & (IData)(vlSelf->__PVT__sgn))))
                    ? vlSelf->__PVT__mask : 0U);
    __PVT__shx = ((3U == (IData)(vlSelf->__PVT__state)) 
                  & (IData)(vlSelf->__PVT__is_shift));
    vlSelf->__PVT__is_sll = ((IData)(vlSelf->__PVT__is_shift) 
                             & (0x1000U == (0x7000U 
                                            & vlSelf->__PVT__ir)));
    if (vlSelf->__PVT__is_sll) {
        vlSelf->__PVT__exec_done = (0U == (IData)(vlSelf->__PVT__k));
        __PVT__ia = (0x1ffU & ((IData)(vlSelf->__PVT__k) 
                               - (IData)(__PVT__qs)));
        __VdfgTmp_h41a48239__0 = ((VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__k)) 
                                   - VL_EXTENDS_II(32,9, (IData)(__PVT__qs))) 
                                  - (IData)(1U));
    } else {
        vlSelf->__PVT__exec_done = vlSelf->__PVT__last_up;
        __PVT__ia = (0x1ffU & ((IData)(vlSelf->__PVT__k) 
                               + (IData)(__PVT__qs)));
        __VdfgTmp_h41a48239__0 = ((IData)(1U) + (VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__k)) 
                                                 + 
                                                 VL_EXTENDS_II(32,9, (IData)(__PVT__qs))));
    }
    __PVT__va = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, (IData)(__PVT__ia))) 
                 & VL_LTES_III(9, (IData)(__PVT__ia), 
                               (0x1ffU & ((0x3fU & 
                                           (0x20U >> (IData)(vlSelf->__PVT__lw_r))) 
                                          - (IData)(1U)))));
    vlSelf->__PVT__a_val = ((0U == (0x1fU & (vlSelf->__PVT__ir 
                                             >> 0xfU)))
                             ? 0U : (vlSymsp->TOP.tb_sys3__DOT__dut__DOT__slot__BRA__25__KET____DOT__rf
                                     [((0x3e0U & (vlSelf->__PVT__ir 
                                                  >> 0xaU)) 
                                       | (0x1fU & (
                                                   (2U 
                                                    == (IData)(vlSelf->__PVT__state))
                                                    ? 
                                                   ((0x3fU 
                                                     & (0x20U 
                                                        >> (IData)(vlSelf->__PVT__lw_r))) 
                                                    - (IData)(1U))
                                                    : 
                                                   ((IData)(__PVT__shx)
                                                     ? (IData)(__PVT__ia)
                                                     : (IData)(vlSelf->__PVT__k)))))] 
                                     & vlSelf->__PVT__mask));
    __PVT__vb = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, 
                                                   (0x1ffU 
                                                    & __VdfgTmp_h41a48239__0))) 
                 & VL_LTES_III(9, (0x1ffU & __VdfgTmp_h41a48239__0), 
                               (0x1ffU & ((0x3fU & 
                                           (0x20U >> (IData)(vlSelf->__PVT__lw_r))) 
                                          - (IData)(1U)))));
    vlSelf->d_wdata = (((IData)(__PVT__shx) ? (0U == 
                                               (0x1fU 
                                                & (vlSelf->__PVT__ir 
                                                   >> 0xfU)))
                         : (0U == (0x1fU & (vlSelf->__PVT__ir 
                                            >> 0x14U))))
                        ? 0U : (vlSymsp->TOP.tb_sys3__DOT__dut__DOT__slot__BRA__25__KET____DOT__rf
                                [((0x3e0U & (((IData)(__PVT__shx)
                                               ? (vlSelf->__PVT__ir 
                                                  >> 0xfU)
                                               : (vlSelf->__PVT__ir 
                                                  >> 0x14U)) 
                                             << 5U)) 
                                  | (0x1fU & ((2U == (IData)(vlSelf->__PVT__state))
                                               ? (IData)(vlSelf->__PVT__j)
                                               : ((IData)(__PVT__shx)
                                                   ? __VdfgTmp_h41a48239__0
                                                   : (IData)(vlSelf->__PVT__k)))))] 
                                & vlSelf->__PVT__mask));
    __PVT__X = vlSelf->__PVT__a_val;
    __PVT__Yr = (((0x33U == (0x7fU & vlSelf->__PVT__ir)) 
                  | (0x63U == (0x7fU & vlSelf->__PVT__ir)))
                  ? vlSelf->d_wdata : __PVT__imm_d);
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if ((0x37U != (0x7fU & vlSelf->__PVT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->__PVT__ir))) {
                if ((0x6fU != (0x7fU & vlSelf->__PVT__ir))) {
                    if (((IData)((0x40000033U == (0x4000707fU 
                                                  & vlSelf->__PVT__ir))) 
                         | (IData)(vlSelf->__PVT__is_cmp))) {
                        __PVT__inv = 1U;
                    }
                }
            }
        }
        if (vlSelf->__PVT__is_shift) {
            vlSelf->__PVT__we = 1U;
        } else if (__VdfgExtracted_h62388771__0) {
            vlSelf->__PVT__we = 1U;
        } else if (((~ (IData)(vlSelf->__PVT__is_cmp)) 
                    & (IData)(__VdfgTmp_h18c46dac__0))) {
            vlSelf->__PVT__we = 1U;
        }
        if ((0x37U == (0x7fU & vlSelf->__PVT__ir))) {
            __PVT__X = 0U;
        } else if ((0x17U == (0x7fU & vlSelf->__PVT__ir))) {
            __PVT__X = __PVT__pc_d;
        } else if ((0x6fU == (0x7fU & vlSelf->__PVT__ir))) {
            __PVT__X = __PVT__pc_d;
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        if ((3U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__we = 1U;
        } else if (vlSelf->__PVT__is_slt) {
            vlSelf->__PVT__we = 1U;
        } else if ((0x67U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__we = 1U;
        }
        __PVT__X = __PVT__pc_d;
    } else if ((5U == (IData)(vlSelf->__PVT__state))) {
        __PVT__X = __PVT__pc_d;
    }
    vlSelf->__PVT__xsh = VL_SHIFTR_III(32,32,6, __PVT__X, 
                                       (0x3fU & (((IData)(1U) 
                                                  << (IData)(vlSelf->__PVT__lw_r)) 
                                                 - (IData)(1U))));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if ((0x37U != (0x7fU & vlSelf->__PVT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->__PVT__ir))) {
                if ((0x6fU == (0x7fU & vlSelf->__PVT__ir))) {
                    __PVT__Yr = __PVT__c4_d;
                }
            }
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        __PVT__Yr = __PVT__c4_d;
    } else if ((5U == (IData)(vlSelf->__PVT__state))) {
        __PVT__Yr = (((0x6fU == (0x7fU & vlSelf->__PVT__ir)) 
                      | ((0x63U == (0x7fU & vlSelf->__PVT__ir)) 
                         & (IData)(__PVT__cond))) ? __PVT__imm_d
                      : __PVT__c4_d);
    }
    vlSelf->__PVT__ysh = VL_SHIFTR_III(32,32,6, __PVT__Yr, 
                                       (0x3fU & (((IData)(1U) 
                                                  << (IData)(vlSelf->__PVT__lw_r)) 
                                                 - (IData)(1U))));
    __PVT__sum_full = (0x1ffffffffULL & ((QData)((IData)(__PVT__X)) 
                                         + ((QData)((IData)(
                                                            ((IData)(__PVT__inv)
                                                              ? 
                                                             ((~ __PVT__Yr) 
                                                              & vlSelf->__PVT__mask)
                                                              : __PVT__Yr))) 
                                            + (QData)((IData)(
                                                              ((0U 
                                                                == (IData)(vlSelf->__PVT__k))
                                                                ? (IData)(__PVT__inv)
                                                                : (IData)(vlSelf->__PVT__cy)))))));
    vlSelf->__PVT__cout = (1U & (IData)((0x1ffffffffULL 
                                         & (__PVT__sum_full 
                                            >> (0x3fU 
                                                & ((IData)(1U) 
                                                   << (IData)(vlSelf->__PVT__lw_r)))))));
    __PVT__sum_d = ((IData)(__PVT__sum_full) & vlSelf->__PVT__mask);
    vlSelf->__PVT__nz_n = (((0U != (IData)(vlSelf->__PVT__k)) 
                            & (IData)(vlSelf->__PVT__nz)) 
                           | (0U != __PVT__sum_d));
    vlSelf->__VdfgTmp_h7980eff3__0 = VL_SHIFTL_III(32,32,6, __PVT__sum_d, 
                                                   (0x3fU 
                                                    & ((IData)(0x20U) 
                                                       - 
                                                       ((IData)(1U) 
                                                        << (IData)(vlSelf->__PVT__lw_r)))));
    vlSelf->__PVT__wd = (((IData)(__VdfgTmp_h18c46dac__0) 
                          & ((4U == (7U & (vlSelf->__PVT__ir 
                                           >> 0xcU))) 
                             | ((6U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))) 
                                | (7U == (7U & (vlSelf->__PVT__ir 
                                                >> 0xcU))))))
                          ? ((4U == (7U & (vlSelf->__PVT__ir 
                                           >> 0xcU)))
                              ? (__PVT__X ^ __PVT__Yr)
                              : ((6U == (7U & (vlSelf->__PVT__ir 
                                               >> 0xcU)))
                                  ? (__PVT__X | __PVT__Yr)
                                  : (__PVT__X & __PVT__Yr)))
                          : __PVT__sum_d);
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if (vlSelf->__PVT__is_shift) {
            vlSelf->__PVT__wd = ((IData)(((((QData)((IData)(
                                                            ((IData)(vlSelf->__PVT__is_sll)
                                                              ? 
                                                             ((IData)(__PVT__va)
                                                               ? vlSelf->__PVT__a_val
                                                               : 0U)
                                                              : 
                                                             ((IData)(__PVT__vb)
                                                               ? vlSelf->d_wdata
                                                               : __PVT__fill)))) 
                                            << (0x3fU 
                                                & ((IData)(1U) 
                                                   << (IData)(vlSelf->__PVT__lw_r)))) 
                                           | (QData)((IData)(
                                                             ((IData)(vlSelf->__PVT__is_sll)
                                                               ? 
                                                              ((IData)(__PVT__vb)
                                                                ? vlSelf->d_wdata
                                                                : 0U)
                                                               : 
                                                              ((IData)(__PVT__va)
                                                                ? vlSelf->__PVT__a_val
                                                                : __PVT__fill))))) 
                                          >> (0x3fU 
                                              & ((IData)(vlSelf->__PVT__is_sll)
                                                  ? 
                                                 (((IData)(1U) 
                                                   << (IData)(vlSelf->__PVT__lw_r)) 
                                                  - (IData)(__VdfgTmp_h933689ae__0))
                                                  : (IData)(__VdfgTmp_h933689ae__0))))) 
                                 & vlSelf->__PVT__mask);
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        if ((3U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__wd = (vlSymsp->TOP.tb_sys3__DOT__dut__DOT__slot__BRA__25__KET____DOT__dm
                                 [(0x7fffU & (IData)(vlSelf->d_addr))] 
                                 & vlSelf->__PVT__mask);
        } else if (vlSelf->__PVT__is_slt) {
            vlSelf->__PVT__wd = 0U;
            vlSelf->__PVT__wd = ((0xfffffffeU & vlSelf->__PVT__wd) 
                                 | ((0U == (IData)(vlSelf->__PVT__k)) 
                                    & ((2U == (7U & 
                                               (vlSelf->__PVT__ir 
                                                >> 0xcU)))
                                        ? (IData)(vlSelf->__PVT__f_lt)
                                        : (IData)(vlSelf->__PVT__f_ltu))));
        } else if ((0x67U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__wd = __PVT__sum_d;
        }
    }
    vlSelf->__PVT__addr_ins = (VL_SHIFTR_III(32,32,6, vlSelf->__PVT__addr, 
                                             (0x3fU 
                                              & ((IData)(1U) 
                                                 << (IData)(vlSelf->__PVT__lw_r)))) 
                               | vlSelf->__VdfgTmp_h7980eff3__0);
}

VL_INLINE_OPT void Vtb_sys3_uc_core_rw___nba_sequent__TOP__tb_sys3__DOT__dut__DOT__slot__BRA__26__KET____DOT__core__0(Vtb_sys3_uc_core_rw* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_sys3__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+          Vtb_sys3_uc_core_rw___nba_sequent__TOP__tb_sys3__DOT__dut__DOT__slot__BRA__26__KET____DOT__core__0\n"); );
    // Init
    CData/*0:0*/ __PVT__shx;
    __PVT__shx = 0;
    IData/*31:0*/ __PVT__pc_d;
    __PVT__pc_d = 0;
    IData/*31:0*/ __PVT__imm_d;
    __PVT__imm_d = 0;
    IData/*31:0*/ __PVT__c4_d;
    __PVT__c4_d = 0;
    SData/*8:0*/ __PVT__qs;
    __PVT__qs = 0;
    SData/*8:0*/ __PVT__ia;
    __PVT__ia = 0;
    CData/*0:0*/ __PVT__va;
    __PVT__va = 0;
    CData/*0:0*/ __PVT__vb;
    __PVT__vb = 0;
    IData/*31:0*/ __PVT__fill;
    __PVT__fill = 0;
    IData/*31:0*/ __PVT__X;
    __PVT__X = 0;
    IData/*31:0*/ __PVT__Yr;
    __PVT__Yr = 0;
    CData/*0:0*/ __PVT__inv;
    __PVT__inv = 0;
    QData/*32:0*/ __PVT__sum_full;
    __PVT__sum_full = 0;
    IData/*31:0*/ __PVT__sum_d;
    __PVT__sum_d = 0;
    CData/*0:0*/ __PVT__cond;
    __PVT__cond = 0;
    CData/*0:0*/ __VdfgExtracted_h62388771__0;
    __VdfgExtracted_h62388771__0 = 0;
    IData/*31:0*/ __VdfgTmp_h41a48239__0;
    __VdfgTmp_h41a48239__0 = 0;
    CData/*0:0*/ __VdfgTmp_h2cd83c5b__0;
    __VdfgTmp_h2cd83c5b__0 = 0;
    CData/*0:0*/ __VdfgTmp_he83b8d53__0;
    __VdfgTmp_he83b8d53__0 = 0;
    CData/*0:0*/ __VdfgTmp_h18c46dac__0;
    __VdfgTmp_h18c46dac__0 = 0;
    CData/*0:0*/ __VdfgTmp_hd9b60348__0;
    __VdfgTmp_hd9b60348__0 = 0;
    CData/*5:0*/ __VdfgTmp_h933689ae__0;
    __VdfgTmp_h933689ae__0 = 0;
    CData/*5:0*/ __Vtableidx27;
    __Vtableidx27 = 0;
    CData/*2:0*/ __Vdly__state;
    __Vdly__state = 0;
    IData/*31:0*/ __Vdly__addr;
    __Vdly__addr = 0;
    IData/*31:0*/ __Vdly__shamt_w;
    __Vdly__shamt_w = 0;
    CData/*4:0*/ __Vdly__k;
    __Vdly__k = 0;
    CData/*2:0*/ __Vdly__j;
    __Vdly__j = 0;
    // Body
    __Vdly__addr = vlSelf->__PVT__addr;
    __Vdly__j = vlSelf->__PVT__j;
    __Vdly__shamt_w = vlSelf->__PVT__shamt_w;
    __Vdly__state = vlSelf->__PVT__state;
    __Vdly__k = vlSelf->__PVT__k;
    if (vlSymsp->TOP.tb_sys3__DOT__rst) {
        __Vdly__state = 6U;
        vlSelf->__PVT__pc = 0U;
        vlSelf->__PVT__ir = 0U;
        __Vdly__addr = 0U;
        vlSelf->__PVT__imm_sr = 0U;
        __Vdly__shamt_w = 0U;
        __Vdly__k = 0U;
        __Vdly__j = 0U;
        vlSelf->__PVT__lw_r = 0U;
        vlSelf->__PVT__cy = 0U;
        vlSelf->__PVT__nz = 0U;
        vlSelf->__PVT__f_eq = 0U;
        vlSelf->__PVT__f_lt = 0U;
        vlSelf->__PVT__f_ltu = 0U;
        vlSelf->__PVT__sgn = 0U;
        vlSelf->__PVT__halted_r = 1U;
        vlSelf->__PVT__trap_r = 0U;
    } else if (((vlSymsp->TOP.tb_sys3__DOT__dut__DOT__start_v 
                 >> 0x1aU) & (6U == (IData)(vlSelf->__PVT__state)))) {
        vlSelf->__PVT__pc = vlSymsp->TOP.tb_sys3__DOT__dut__DOT__launch_entry;
        vlSelf->__PVT__lw_r = vlSymsp->TOP.tb_sys3__DOT__dut__DOT__launch_lw;
        __Vdly__k = 0U;
        vlSelf->__PVT__halted_r = 0U;
        vlSelf->__PVT__trap_r = 0U;
        __Vdly__state = 0U;
    } else if ((4U & (IData)(vlSelf->__PVT__state))) {
        if ((1U & (~ ((IData)(vlSelf->__PVT__state) 
                      >> 1U)))) {
            if ((1U & (IData)(vlSelf->__PVT__state))) {
                if ((0x67U == (IData)(vlSelf->__PVT__opc))) {
                    vlSelf->__PVT__pc = (0xfffffffeU 
                                         & vlSelf->__PVT__addr);
                    __Vdly__state = 0U;
                } else {
                    vlSelf->__PVT__pc = (vlSelf->__VdfgTmp_he4828306__0 
                                         | vlSelf->__VdfgTmp_h7980eff3__0);
                    vlSelf->__PVT__imm_sr = vlSelf->__PVT__imm_rot;
                    vlSelf->__PVT__cy = vlSelf->__PVT__cout;
                    if (vlSelf->__PVT__last_up) {
                        __Vdly__k = 0U;
                        __Vdly__state = 0U;
                    } else {
                        __Vdly__k = (0x1fU & ((IData)(1U) 
                                              + (IData)(vlSelf->__PVT__k)));
                    }
                }
            } else {
                vlSelf->__PVT__cy = vlSelf->__PVT__cout;
                vlSelf->__PVT__pc = vlSelf->__PVT__pc_rot;
                if (vlSelf->__PVT__last_up) {
                    __Vdly__k = 0U;
                    __Vdly__state = 5U;
                } else {
                    __Vdly__k = (0x1fU & ((IData)(1U) 
                                          + (IData)(vlSelf->__PVT__k)));
                }
            }
        }
    } else if ((2U & (IData)(vlSelf->__PVT__state))) {
        if ((1U & (IData)(vlSelf->__PVT__state))) {
            vlSelf->__PVT__cy = vlSelf->__PVT__cout;
            if (vlSelf->__PVT__is_cmp) {
                vlSelf->__PVT__nz = vlSelf->__PVT__nz_n;
                if (vlSelf->__PVT__last_up) {
                    vlSelf->__PVT__f_eq = (1U & (~ (IData)(vlSelf->__PVT__nz_n)));
                    vlSelf->__PVT__f_ltu = (1U & (~ (IData)(vlSelf->__PVT__cout)));
                    vlSelf->__PVT__f_lt = (1U & (((1U 
                                                   & vlSelf->__PVT__xsh) 
                                                  != 
                                                  (1U 
                                                   & vlSelf->__PVT__ysh))
                                                  ? vlSelf->__PVT__xsh
                                                  : 
                                                 (~ (IData)(vlSelf->__PVT__cout))));
                }
            }
            if ((((3U == (IData)(vlSelf->__PVT__opc)) 
                  | (0x23U == (IData)(vlSelf->__PVT__opc))) 
                 | (0x67U == (IData)(vlSelf->__PVT__opc)))) {
                __Vdly__addr = vlSelf->__PVT__addr_ins;
            }
            vlSelf->__PVT__pc = vlSelf->__PVT__pc_rot;
            vlSelf->__PVT__imm_sr = vlSelf->__PVT__imm_rot;
            if (vlSelf->__PVT__exec_done) {
                __Vdly__k = 0U;
                __Vdly__state = (((((3U == (IData)(vlSelf->__PVT__opc)) 
                                    | (0x23U == (IData)(vlSelf->__PVT__opc))) 
                                   | (0x67U == (IData)(vlSelf->__PVT__opc))) 
                                  | (IData)(vlSelf->__PVT__is_slt))
                                  ? 4U : 5U);
            } else {
                __Vdly__k = (0x1fU & ((IData)(vlSelf->__PVT__is_sll)
                                       ? ((IData)(vlSelf->__PVT__k) 
                                          - (IData)(1U))
                                       : ((IData)(1U) 
                                          + (IData)(vlSelf->__PVT__k))));
            }
        } else {
            if ((0x33U == (IData)(vlSelf->__PVT__opc))) {
                __Vdly__shamt_w = ((vlSelf->__PVT__shamt_w 
                                    & (~ VL_SHIFTL_III(32,32,6, vlSelf->__PVT__mask, (IData)(vlSelf->__PVT__jw)))) 
                                   | VL_SHIFTL_III(32,32,6, vlSelf->d_wdata, (IData)(vlSelf->__PVT__jw)));
            }
            vlSelf->__PVT__sgn = (1U & (vlSelf->__PVT__a_val 
                                        >> (0x1fU & (IData)(vlSelf->__PVT__wm1))));
            if (((IData)(vlSelf->__PVT__j) == ((0x33U 
                                                == (IData)(vlSelf->__PVT__opc))
                                                ? (IData)(vlSelf->__PVT__mlast)
                                                : 0U))) {
                __Vdly__state = 3U;
                __Vdly__k = ((IData)(vlSelf->__PVT__is_sll)
                              ? (0x1fU & ((IData)(vlSelf->__PVT__nd) 
                                          - (IData)(1U)))
                              : 0U);
            } else {
                __Vdly__j = (7U & ((IData)(1U) + (IData)(vlSelf->__PVT__j)));
            }
        }
    } else if ((1U & (IData)(vlSelf->__PVT__state))) {
        __Vdly__j = 0U;
        vlSelf->__PVT__imm_sr = vlSelf->__PVT__imm;
        __Vdly__shamt_w = ((IData)(vlSelf->__PVT__sh_i)
                            ? (IData)(vlSelf->__PVT__rs2)
                            : 0U);
        if (vlSelf->__PVT__bad) {
            vlSelf->__PVT__trap_r = 1U;
            vlSelf->__PVT__halted_r = 1U;
            __Vdly__state = 6U;
        } else if (vlSelf->__PVT__is_sys) {
            vlSelf->__PVT__halted_r = 1U;
            __Vdly__state = 6U;
        } else if (vlSelf->__PVT__is_shift) {
            __Vdly__state = 2U;
        } else {
            __Vdly__k = 0U;
            __Vdly__state = 3U;
        }
    } else {
        vlSelf->__PVT__ir = vlSymsp->TOP.tb_sys3__DOT__dut__DOT__slot__BRA__26__KET____DOT__id;
        __Vdly__state = 1U;
    }
    vlSelf->__PVT__addr = __Vdly__addr;
    vlSelf->__PVT__j = __Vdly__j;
    vlSelf->__PVT__shamt_w = __Vdly__shamt_w;
    vlSelf->__PVT__state = __Vdly__state;
    vlSelf->__PVT__k = __Vdly__k;
    vlSelf->d_addr = (((QData)((IData)((vlSelf->__PVT__addr 
                                        >> 2U))) << 5U) 
                      | (QData)((IData)(vlSelf->__PVT__k)));
    vlSelf->__PVT__wm1 = (0x3fU & (((IData)(1U) << (IData)(vlSelf->__PVT__lw_r)) 
                                   - (IData)(1U)));
    vlSelf->__PVT__mlast = (0x3fU & (VL_DIV_III(6, 
                                                (0x3fU 
                                                 & ((IData)(4U) 
                                                    + 
                                                    ((IData)(1U) 
                                                     << (IData)(vlSelf->__PVT__lw_r)))), 
                                                (0x3fU 
                                                 & ((IData)(1U) 
                                                    << (IData)(vlSelf->__PVT__lw_r)))) 
                                     - (IData)(1U)));
    vlSelf->__PVT__nd = (0x3fU & (0x20U >> (IData)(vlSelf->__PVT__lw_r)));
    vlSelf->__PVT__jw = (0x3fU & ((IData)(vlSelf->__PVT__j) 
                                  * (0x3fU & ((IData)(1U) 
                                              << (IData)(vlSelf->__PVT__lw_r)))));
    vlSelf->__PVT__imm_rot = (VL_SHIFTR_III(32,32,6, vlSelf->__PVT__imm_sr, 
                                            (0x3fU 
                                             & ((IData)(1U) 
                                                << (IData)(vlSelf->__PVT__lw_r)))) 
                              | VL_SHIFTL_III(32,32,6, vlSelf->__PVT__imm_sr, 
                                              (0x3fU 
                                               & ((IData)(0x20U) 
                                                  - 
                                                  ((IData)(1U) 
                                                   << (IData)(vlSelf->__PVT__lw_r))))));
    vlSelf->__PVT__last_up = ((IData)(vlSelf->__PVT__k) 
                              == (0x1fU & ((0x3fU & 
                                            (0x20U 
                                             >> (IData)(vlSelf->__PVT__lw_r))) 
                                           - (IData)(1U))));
    vlSelf->__VdfgTmp_he4828306__0 = VL_SHIFTR_III(32,32,6, vlSelf->__PVT__pc, 
                                                   (0x3fU 
                                                    & ((IData)(1U) 
                                                       << (IData)(vlSelf->__PVT__lw_r))));
    __VdfgTmp_h933689ae__0 = (0x1fU & (vlSelf->__PVT__shamt_w 
                                       & ((0x3fU & 
                                           ((IData)(1U) 
                                            << (IData)(vlSelf->__PVT__lw_r))) 
                                          - (IData)(1U))));
    __PVT__qs = (0x1fU & ((0x1fU & vlSelf->__PVT__shamt_w) 
                          >> (IData)(vlSelf->__PVT__lw_r)));
    vlSelf->__PVT__mask = ((5U == (IData)(vlSelf->__PVT__lw_r))
                            ? 0xffffffffU : (VL_SHIFTL_III(32,32,6, (IData)(1U), 
                                                           (0x3fU 
                                                            & ((IData)(1U) 
                                                               << (IData)(vlSelf->__PVT__lw_r)))) 
                                             - (IData)(1U)));
    vlSelf->__PVT__rs2 = (0x1fU & (vlSelf->__PVT__ir 
                                   >> 0x14U));
    vlSelf->__PVT__is_sys = (0x73U == (0x7fU & vlSelf->__PVT__ir));
    vlSelf->__PVT__opc = (0x7fU & vlSelf->__PVT__ir);
    __VdfgTmp_h2cd83c5b__0 = ((0x37U == (0x7fU & vlSelf->__PVT__ir)) 
                              | (0x17U == (0x7fU & vlSelf->__PVT__ir)));
    __Vtableidx27 = (((IData)(vlSelf->__PVT__f_eq) 
                      << 5U) | (((IData)(vlSelf->__PVT__f_lt) 
                                 << 4U) | (((IData)(vlSelf->__PVT__f_ltu) 
                                            << 3U) 
                                           | (7U & 
                                              (vlSelf->__PVT__ir 
                                               >> 0xcU)))));
    __PVT__cond = Vtb_sys3__ConstPool__TABLE_h2a0441a0_0
        [__Vtableidx27];
    __VdfgTmp_hd9b60348__0 = ((2U == (7U & (vlSelf->__PVT__ir 
                                            >> 0xcU))) 
                              | (3U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))));
    __VdfgTmp_h18c46dac__0 = ((0x13U == (0x7fU & vlSelf->__PVT__ir)) 
                              | (0x33U == (0x7fU & vlSelf->__PVT__ir)));
    __VdfgTmp_he83b8d53__0 = ((1U == (7U & (vlSelf->__PVT__ir 
                                            >> 0xcU))) 
                              | (5U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))));
    vlSelf->__PVT__pc_rot = (vlSelf->__VdfgTmp_he4828306__0 
                             | VL_SHIFTL_III(32,32,6, vlSelf->__PVT__pc, 
                                             (0x3fU 
                                              & ((IData)(0x20U) 
                                                 - 
                                                 ((IData)(1U) 
                                                  << (IData)(vlSelf->__PVT__lw_r))))));
    __PVT__pc_d = (vlSelf->__PVT__pc & vlSelf->__PVT__mask);
    __PVT__imm_d = (vlSelf->__PVT__imm_sr & vlSelf->__PVT__mask);
    __PVT__c4_d = (VL_SHIFTR_III(32,32,6, 4U, (0x3fU 
                                               & ((IData)(vlSelf->__PVT__k) 
                                                  * 
                                                  (0x3fU 
                                                   & ((IData)(1U) 
                                                      << (IData)(vlSelf->__PVT__lw_r)))))) 
                   & vlSelf->__PVT__mask);
    vlSelf->__PVT__imm = ((IData)(__VdfgTmp_h2cd83c5b__0)
                           ? (0xfffff000U & vlSelf->__PVT__ir)
                           : ((0x6fU == (0x7fU & vlSelf->__PVT__ir))
                               ? (((- (IData)((vlSelf->__PVT__ir 
                                               >> 0x1fU))) 
                                   << 0x15U) | ((0x100000U 
                                                 & (vlSelf->__PVT__ir 
                                                    >> 0xbU)) 
                                                | ((0xff000U 
                                                    & vlSelf->__PVT__ir) 
                                                   | ((0x800U 
                                                       & (vlSelf->__PVT__ir 
                                                          >> 9U)) 
                                                      | (0x7feU 
                                                         & (vlSelf->__PVT__ir 
                                                            >> 0x14U))))))
                               : ((0x63U == (0x7fU 
                                             & vlSelf->__PVT__ir))
                                   ? (((- (IData)((vlSelf->__PVT__ir 
                                                   >> 0x1fU))) 
                                       << 0xdU) | (
                                                   (0x1000U 
                                                    & (vlSelf->__PVT__ir 
                                                       >> 0x13U)) 
                                                   | ((0x800U 
                                                       & (vlSelf->__PVT__ir 
                                                          << 4U)) 
                                                      | ((0x7e0U 
                                                          & (vlSelf->__PVT__ir 
                                                             >> 0x14U)) 
                                                         | (0x1eU 
                                                            & (vlSelf->__PVT__ir 
                                                               >> 7U))))))
                                   : ((0x23U == (0x7fU 
                                                 & vlSelf->__PVT__ir))
                                       ? (((- (IData)(
                                                      (vlSelf->__PVT__ir 
                                                       >> 0x1fU))) 
                                           << 0xcU) 
                                          | ((0xfe0U 
                                              & (vlSelf->__PVT__ir 
                                                 >> 0x14U)) 
                                             | (0x1fU 
                                                & (vlSelf->__PVT__ir 
                                                   >> 7U))))
                                       : (((- (IData)(
                                                      (vlSelf->__PVT__ir 
                                                       >> 0x1fU))) 
                                           << 0xcU) 
                                          | (vlSelf->__PVT__ir 
                                             >> 0x14U))))));
    __VdfgExtracted_h62388771__0 = ((IData)(__VdfgTmp_h2cd83c5b__0) 
                                    | (0x6fU == (0x7fU 
                                                 & vlSelf->__PVT__ir)));
    vlSelf->__PVT__is_cmp = ((0x63U == (0x7fU & vlSelf->__PVT__ir)) 
                             | ((IData)(__VdfgTmp_h18c46dac__0) 
                                & (IData)(__VdfgTmp_hd9b60348__0)));
    vlSelf->__PVT__sh_i = ((0x13U == (0x7fU & vlSelf->__PVT__ir)) 
                           & (IData)(__VdfgTmp_he83b8d53__0));
    vlSelf->__PVT__bad = (1U & ((~ ((IData)(__VdfgExtracted_h62388771__0) 
                                    | ((0x67U == (0x7fU 
                                                  & vlSelf->__PVT__ir)) 
                                       | ((0x63U == 
                                           (0x7fU & vlSelf->__PVT__ir)) 
                                          | ((3U == 
                                              (0x7fU 
                                               & vlSelf->__PVT__ir)) 
                                             | ((0x23U 
                                                 == 
                                                 (0x7fU 
                                                  & vlSelf->__PVT__ir)) 
                                                | ((0x13U 
                                                    == 
                                                    (0x7fU 
                                                     & vlSelf->__PVT__ir)) 
                                                   | ((0x33U 
                                                       == 
                                                       (0x7fU 
                                                        & vlSelf->__PVT__ir)) 
                                                      | (0x73U 
                                                         == 
                                                         (0x7fU 
                                                          & vlSelf->__PVT__ir)))))))))) 
                                | (((0x67U == (0x7fU 
                                               & vlSelf->__PVT__ir)) 
                                    & (0U != (7U & 
                                              (vlSelf->__PVT__ir 
                                               >> 0xcU)))) 
                                   | (((0x63U == (0x7fU 
                                                  & vlSelf->__PVT__ir)) 
                                       & (IData)(__VdfgTmp_hd9b60348__0)) 
                                      | ((((3U == (0x7fU 
                                                   & vlSelf->__PVT__ir)) 
                                           | (0x23U 
                                              == (0x7fU 
                                                  & vlSelf->__PVT__ir))) 
                                          & (2U != 
                                             (7U & 
                                              (vlSelf->__PVT__ir 
                                               >> 0xcU)))) 
                                         | ((IData)(
                                                    ((0x1013U 
                                                      == 
                                                      (0x707fU 
                                                       & vlSelf->__PVT__ir)) 
                                                     & (0U 
                                                        != 
                                                        (vlSelf->__PVT__ir 
                                                         >> 0x19U)))) 
                                            | ((IData)(
                                                       ((0x5013U 
                                                         == 
                                                         (0x707fU 
                                                          & vlSelf->__PVT__ir)) 
                                                        & ((0U 
                                                            != 
                                                            (vlSelf->__PVT__ir 
                                                             >> 0x19U)) 
                                                           & (0x20U 
                                                              != 
                                                              (vlSelf->__PVT__ir 
                                                               >> 0x19U))))) 
                                               | ((0x33U 
                                                   == 
                                                   (0x7fU 
                                                    & vlSelf->__PVT__ir)) 
                                                  & ((~ 
                                                      ((0x20U 
                                                        == 
                                                        (vlSelf->__PVT__ir 
                                                         >> 0x19U)) 
                                                       & ((0U 
                                                           == 
                                                           (7U 
                                                            & (vlSelf->__PVT__ir 
                                                               >> 0xcU))) 
                                                          | (5U 
                                                             == 
                                                             (7U 
                                                              & (vlSelf->__PVT__ir 
                                                                 >> 0xcU)))))) 
                                                     & (0U 
                                                        != 
                                                        (vlSelf->__PVT__ir 
                                                         >> 0x19U)))))))))));
    vlSelf->__PVT__is_slt = ((0x63U != (0x7fU & vlSelf->__PVT__ir)) 
                             & (IData)(vlSelf->__PVT__is_cmp));
    __PVT__inv = 0U;
    vlSelf->__PVT__is_shift = ((IData)(vlSelf->__PVT__sh_i) 
                               | ((0x33U == (0x7fU 
                                             & vlSelf->__PVT__ir)) 
                                  & (IData)(__VdfgTmp_he83b8d53__0)));
    vlSelf->__PVT__we = 0U;
    __PVT__fill = (((IData)(vlSelf->__PVT__is_shift) 
                    & (IData)(((0x40005000U == (0x40007000U 
                                                & vlSelf->__PVT__ir)) 
                               & (IData)(vlSelf->__PVT__sgn))))
                    ? vlSelf->__PVT__mask : 0U);
    __PVT__shx = ((3U == (IData)(vlSelf->__PVT__state)) 
                  & (IData)(vlSelf->__PVT__is_shift));
    vlSelf->__PVT__is_sll = ((IData)(vlSelf->__PVT__is_shift) 
                             & (0x1000U == (0x7000U 
                                            & vlSelf->__PVT__ir)));
    if (vlSelf->__PVT__is_sll) {
        vlSelf->__PVT__exec_done = (0U == (IData)(vlSelf->__PVT__k));
        __PVT__ia = (0x1ffU & ((IData)(vlSelf->__PVT__k) 
                               - (IData)(__PVT__qs)));
        __VdfgTmp_h41a48239__0 = ((VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__k)) 
                                   - VL_EXTENDS_II(32,9, (IData)(__PVT__qs))) 
                                  - (IData)(1U));
    } else {
        vlSelf->__PVT__exec_done = vlSelf->__PVT__last_up;
        __PVT__ia = (0x1ffU & ((IData)(vlSelf->__PVT__k) 
                               + (IData)(__PVT__qs)));
        __VdfgTmp_h41a48239__0 = ((IData)(1U) + (VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__k)) 
                                                 + 
                                                 VL_EXTENDS_II(32,9, (IData)(__PVT__qs))));
    }
    __PVT__va = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, (IData)(__PVT__ia))) 
                 & VL_LTES_III(9, (IData)(__PVT__ia), 
                               (0x1ffU & ((0x3fU & 
                                           (0x20U >> (IData)(vlSelf->__PVT__lw_r))) 
                                          - (IData)(1U)))));
    vlSelf->__PVT__a_val = ((0U == (0x1fU & (vlSelf->__PVT__ir 
                                             >> 0xfU)))
                             ? 0U : (vlSymsp->TOP.tb_sys3__DOT__dut__DOT__slot__BRA__26__KET____DOT__rf
                                     [((0x3e0U & (vlSelf->__PVT__ir 
                                                  >> 0xaU)) 
                                       | (0x1fU & (
                                                   (2U 
                                                    == (IData)(vlSelf->__PVT__state))
                                                    ? 
                                                   ((0x3fU 
                                                     & (0x20U 
                                                        >> (IData)(vlSelf->__PVT__lw_r))) 
                                                    - (IData)(1U))
                                                    : 
                                                   ((IData)(__PVT__shx)
                                                     ? (IData)(__PVT__ia)
                                                     : (IData)(vlSelf->__PVT__k)))))] 
                                     & vlSelf->__PVT__mask));
    __PVT__vb = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, 
                                                   (0x1ffU 
                                                    & __VdfgTmp_h41a48239__0))) 
                 & VL_LTES_III(9, (0x1ffU & __VdfgTmp_h41a48239__0), 
                               (0x1ffU & ((0x3fU & 
                                           (0x20U >> (IData)(vlSelf->__PVT__lw_r))) 
                                          - (IData)(1U)))));
    vlSelf->d_wdata = (((IData)(__PVT__shx) ? (0U == 
                                               (0x1fU 
                                                & (vlSelf->__PVT__ir 
                                                   >> 0xfU)))
                         : (0U == (0x1fU & (vlSelf->__PVT__ir 
                                            >> 0x14U))))
                        ? 0U : (vlSymsp->TOP.tb_sys3__DOT__dut__DOT__slot__BRA__26__KET____DOT__rf
                                [((0x3e0U & (((IData)(__PVT__shx)
                                               ? (vlSelf->__PVT__ir 
                                                  >> 0xfU)
                                               : (vlSelf->__PVT__ir 
                                                  >> 0x14U)) 
                                             << 5U)) 
                                  | (0x1fU & ((2U == (IData)(vlSelf->__PVT__state))
                                               ? (IData)(vlSelf->__PVT__j)
                                               : ((IData)(__PVT__shx)
                                                   ? __VdfgTmp_h41a48239__0
                                                   : (IData)(vlSelf->__PVT__k)))))] 
                                & vlSelf->__PVT__mask));
    __PVT__X = vlSelf->__PVT__a_val;
    __PVT__Yr = (((0x33U == (0x7fU & vlSelf->__PVT__ir)) 
                  | (0x63U == (0x7fU & vlSelf->__PVT__ir)))
                  ? vlSelf->d_wdata : __PVT__imm_d);
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if ((0x37U != (0x7fU & vlSelf->__PVT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->__PVT__ir))) {
                if ((0x6fU != (0x7fU & vlSelf->__PVT__ir))) {
                    if (((IData)((0x40000033U == (0x4000707fU 
                                                  & vlSelf->__PVT__ir))) 
                         | (IData)(vlSelf->__PVT__is_cmp))) {
                        __PVT__inv = 1U;
                    }
                }
            }
        }
        if (vlSelf->__PVT__is_shift) {
            vlSelf->__PVT__we = 1U;
        } else if (__VdfgExtracted_h62388771__0) {
            vlSelf->__PVT__we = 1U;
        } else if (((~ (IData)(vlSelf->__PVT__is_cmp)) 
                    & (IData)(__VdfgTmp_h18c46dac__0))) {
            vlSelf->__PVT__we = 1U;
        }
        if ((0x37U == (0x7fU & vlSelf->__PVT__ir))) {
            __PVT__X = 0U;
        } else if ((0x17U == (0x7fU & vlSelf->__PVT__ir))) {
            __PVT__X = __PVT__pc_d;
        } else if ((0x6fU == (0x7fU & vlSelf->__PVT__ir))) {
            __PVT__X = __PVT__pc_d;
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        if ((3U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__we = 1U;
        } else if (vlSelf->__PVT__is_slt) {
            vlSelf->__PVT__we = 1U;
        } else if ((0x67U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__we = 1U;
        }
        __PVT__X = __PVT__pc_d;
    } else if ((5U == (IData)(vlSelf->__PVT__state))) {
        __PVT__X = __PVT__pc_d;
    }
    vlSelf->__PVT__xsh = VL_SHIFTR_III(32,32,6, __PVT__X, 
                                       (0x3fU & (((IData)(1U) 
                                                  << (IData)(vlSelf->__PVT__lw_r)) 
                                                 - (IData)(1U))));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if ((0x37U != (0x7fU & vlSelf->__PVT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->__PVT__ir))) {
                if ((0x6fU == (0x7fU & vlSelf->__PVT__ir))) {
                    __PVT__Yr = __PVT__c4_d;
                }
            }
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        __PVT__Yr = __PVT__c4_d;
    } else if ((5U == (IData)(vlSelf->__PVT__state))) {
        __PVT__Yr = (((0x6fU == (0x7fU & vlSelf->__PVT__ir)) 
                      | ((0x63U == (0x7fU & vlSelf->__PVT__ir)) 
                         & (IData)(__PVT__cond))) ? __PVT__imm_d
                      : __PVT__c4_d);
    }
    vlSelf->__PVT__ysh = VL_SHIFTR_III(32,32,6, __PVT__Yr, 
                                       (0x3fU & (((IData)(1U) 
                                                  << (IData)(vlSelf->__PVT__lw_r)) 
                                                 - (IData)(1U))));
    __PVT__sum_full = (0x1ffffffffULL & ((QData)((IData)(__PVT__X)) 
                                         + ((QData)((IData)(
                                                            ((IData)(__PVT__inv)
                                                              ? 
                                                             ((~ __PVT__Yr) 
                                                              & vlSelf->__PVT__mask)
                                                              : __PVT__Yr))) 
                                            + (QData)((IData)(
                                                              ((0U 
                                                                == (IData)(vlSelf->__PVT__k))
                                                                ? (IData)(__PVT__inv)
                                                                : (IData)(vlSelf->__PVT__cy)))))));
    vlSelf->__PVT__cout = (1U & (IData)((0x1ffffffffULL 
                                         & (__PVT__sum_full 
                                            >> (0x3fU 
                                                & ((IData)(1U) 
                                                   << (IData)(vlSelf->__PVT__lw_r)))))));
    __PVT__sum_d = ((IData)(__PVT__sum_full) & vlSelf->__PVT__mask);
    vlSelf->__PVT__nz_n = (((0U != (IData)(vlSelf->__PVT__k)) 
                            & (IData)(vlSelf->__PVT__nz)) 
                           | (0U != __PVT__sum_d));
    vlSelf->__VdfgTmp_h7980eff3__0 = VL_SHIFTL_III(32,32,6, __PVT__sum_d, 
                                                   (0x3fU 
                                                    & ((IData)(0x20U) 
                                                       - 
                                                       ((IData)(1U) 
                                                        << (IData)(vlSelf->__PVT__lw_r)))));
    vlSelf->__PVT__wd = (((IData)(__VdfgTmp_h18c46dac__0) 
                          & ((4U == (7U & (vlSelf->__PVT__ir 
                                           >> 0xcU))) 
                             | ((6U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))) 
                                | (7U == (7U & (vlSelf->__PVT__ir 
                                                >> 0xcU))))))
                          ? ((4U == (7U & (vlSelf->__PVT__ir 
                                           >> 0xcU)))
                              ? (__PVT__X ^ __PVT__Yr)
                              : ((6U == (7U & (vlSelf->__PVT__ir 
                                               >> 0xcU)))
                                  ? (__PVT__X | __PVT__Yr)
                                  : (__PVT__X & __PVT__Yr)))
                          : __PVT__sum_d);
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if (vlSelf->__PVT__is_shift) {
            vlSelf->__PVT__wd = ((IData)(((((QData)((IData)(
                                                            ((IData)(vlSelf->__PVT__is_sll)
                                                              ? 
                                                             ((IData)(__PVT__va)
                                                               ? vlSelf->__PVT__a_val
                                                               : 0U)
                                                              : 
                                                             ((IData)(__PVT__vb)
                                                               ? vlSelf->d_wdata
                                                               : __PVT__fill)))) 
                                            << (0x3fU 
                                                & ((IData)(1U) 
                                                   << (IData)(vlSelf->__PVT__lw_r)))) 
                                           | (QData)((IData)(
                                                             ((IData)(vlSelf->__PVT__is_sll)
                                                               ? 
                                                              ((IData)(__PVT__vb)
                                                                ? vlSelf->d_wdata
                                                                : 0U)
                                                               : 
                                                              ((IData)(__PVT__va)
                                                                ? vlSelf->__PVT__a_val
                                                                : __PVT__fill))))) 
                                          >> (0x3fU 
                                              & ((IData)(vlSelf->__PVT__is_sll)
                                                  ? 
                                                 (((IData)(1U) 
                                                   << (IData)(vlSelf->__PVT__lw_r)) 
                                                  - (IData)(__VdfgTmp_h933689ae__0))
                                                  : (IData)(__VdfgTmp_h933689ae__0))))) 
                                 & vlSelf->__PVT__mask);
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        if ((3U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__wd = (vlSymsp->TOP.tb_sys3__DOT__dut__DOT__slot__BRA__26__KET____DOT__dm
                                 [(0x7fffU & (IData)(vlSelf->d_addr))] 
                                 & vlSelf->__PVT__mask);
        } else if (vlSelf->__PVT__is_slt) {
            vlSelf->__PVT__wd = 0U;
            vlSelf->__PVT__wd = ((0xfffffffeU & vlSelf->__PVT__wd) 
                                 | ((0U == (IData)(vlSelf->__PVT__k)) 
                                    & ((2U == (7U & 
                                               (vlSelf->__PVT__ir 
                                                >> 0xcU)))
                                        ? (IData)(vlSelf->__PVT__f_lt)
                                        : (IData)(vlSelf->__PVT__f_ltu))));
        } else if ((0x67U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__wd = __PVT__sum_d;
        }
    }
    vlSelf->__PVT__addr_ins = (VL_SHIFTR_III(32,32,6, vlSelf->__PVT__addr, 
                                             (0x3fU 
                                              & ((IData)(1U) 
                                                 << (IData)(vlSelf->__PVT__lw_r)))) 
                               | vlSelf->__VdfgTmp_h7980eff3__0);
}

VL_INLINE_OPT void Vtb_sys3_uc_core_rw___nba_sequent__TOP__tb_sys3__DOT__dut__DOT__slot__BRA__27__KET____DOT__core__0(Vtb_sys3_uc_core_rw* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_sys3__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+          Vtb_sys3_uc_core_rw___nba_sequent__TOP__tb_sys3__DOT__dut__DOT__slot__BRA__27__KET____DOT__core__0\n"); );
    // Init
    CData/*0:0*/ __PVT__shx;
    __PVT__shx = 0;
    IData/*31:0*/ __PVT__pc_d;
    __PVT__pc_d = 0;
    IData/*31:0*/ __PVT__imm_d;
    __PVT__imm_d = 0;
    IData/*31:0*/ __PVT__c4_d;
    __PVT__c4_d = 0;
    SData/*8:0*/ __PVT__qs;
    __PVT__qs = 0;
    SData/*8:0*/ __PVT__ia;
    __PVT__ia = 0;
    CData/*0:0*/ __PVT__va;
    __PVT__va = 0;
    CData/*0:0*/ __PVT__vb;
    __PVT__vb = 0;
    IData/*31:0*/ __PVT__fill;
    __PVT__fill = 0;
    IData/*31:0*/ __PVT__X;
    __PVT__X = 0;
    IData/*31:0*/ __PVT__Yr;
    __PVT__Yr = 0;
    CData/*0:0*/ __PVT__inv;
    __PVT__inv = 0;
    QData/*32:0*/ __PVT__sum_full;
    __PVT__sum_full = 0;
    IData/*31:0*/ __PVT__sum_d;
    __PVT__sum_d = 0;
    CData/*0:0*/ __PVT__cond;
    __PVT__cond = 0;
    CData/*0:0*/ __VdfgExtracted_h62388771__0;
    __VdfgExtracted_h62388771__0 = 0;
    IData/*31:0*/ __VdfgTmp_h41a48239__0;
    __VdfgTmp_h41a48239__0 = 0;
    CData/*0:0*/ __VdfgTmp_h2cd83c5b__0;
    __VdfgTmp_h2cd83c5b__0 = 0;
    CData/*0:0*/ __VdfgTmp_he83b8d53__0;
    __VdfgTmp_he83b8d53__0 = 0;
    CData/*0:0*/ __VdfgTmp_h18c46dac__0;
    __VdfgTmp_h18c46dac__0 = 0;
    CData/*0:0*/ __VdfgTmp_hd9b60348__0;
    __VdfgTmp_hd9b60348__0 = 0;
    CData/*5:0*/ __VdfgTmp_h933689ae__0;
    __VdfgTmp_h933689ae__0 = 0;
    CData/*5:0*/ __Vtableidx28;
    __Vtableidx28 = 0;
    CData/*2:0*/ __Vdly__state;
    __Vdly__state = 0;
    IData/*31:0*/ __Vdly__addr;
    __Vdly__addr = 0;
    IData/*31:0*/ __Vdly__shamt_w;
    __Vdly__shamt_w = 0;
    CData/*4:0*/ __Vdly__k;
    __Vdly__k = 0;
    CData/*2:0*/ __Vdly__j;
    __Vdly__j = 0;
    // Body
    __Vdly__addr = vlSelf->__PVT__addr;
    __Vdly__j = vlSelf->__PVT__j;
    __Vdly__shamt_w = vlSelf->__PVT__shamt_w;
    __Vdly__state = vlSelf->__PVT__state;
    __Vdly__k = vlSelf->__PVT__k;
    if (vlSymsp->TOP.tb_sys3__DOT__rst) {
        __Vdly__state = 6U;
        vlSelf->__PVT__pc = 0U;
        vlSelf->__PVT__ir = 0U;
        __Vdly__addr = 0U;
        vlSelf->__PVT__imm_sr = 0U;
        __Vdly__shamt_w = 0U;
        __Vdly__k = 0U;
        __Vdly__j = 0U;
        vlSelf->__PVT__lw_r = 0U;
        vlSelf->__PVT__cy = 0U;
        vlSelf->__PVT__nz = 0U;
        vlSelf->__PVT__f_eq = 0U;
        vlSelf->__PVT__f_lt = 0U;
        vlSelf->__PVT__f_ltu = 0U;
        vlSelf->__PVT__sgn = 0U;
        vlSelf->__PVT__halted_r = 1U;
        vlSelf->__PVT__trap_r = 0U;
    } else if (((vlSymsp->TOP.tb_sys3__DOT__dut__DOT__start_v 
                 >> 0x1bU) & (6U == (IData)(vlSelf->__PVT__state)))) {
        vlSelf->__PVT__pc = vlSymsp->TOP.tb_sys3__DOT__dut__DOT__launch_entry;
        vlSelf->__PVT__lw_r = vlSymsp->TOP.tb_sys3__DOT__dut__DOT__launch_lw;
        __Vdly__k = 0U;
        vlSelf->__PVT__halted_r = 0U;
        vlSelf->__PVT__trap_r = 0U;
        __Vdly__state = 0U;
    } else if ((4U & (IData)(vlSelf->__PVT__state))) {
        if ((1U & (~ ((IData)(vlSelf->__PVT__state) 
                      >> 1U)))) {
            if ((1U & (IData)(vlSelf->__PVT__state))) {
                if ((0x67U == (IData)(vlSelf->__PVT__opc))) {
                    vlSelf->__PVT__pc = (0xfffffffeU 
                                         & vlSelf->__PVT__addr);
                    __Vdly__state = 0U;
                } else {
                    vlSelf->__PVT__pc = (vlSelf->__VdfgTmp_he4828306__0 
                                         | vlSelf->__VdfgTmp_h7980eff3__0);
                    vlSelf->__PVT__imm_sr = vlSelf->__PVT__imm_rot;
                    vlSelf->__PVT__cy = vlSelf->__PVT__cout;
                    if (vlSelf->__PVT__last_up) {
                        __Vdly__k = 0U;
                        __Vdly__state = 0U;
                    } else {
                        __Vdly__k = (0x1fU & ((IData)(1U) 
                                              + (IData)(vlSelf->__PVT__k)));
                    }
                }
            } else {
                vlSelf->__PVT__cy = vlSelf->__PVT__cout;
                vlSelf->__PVT__pc = vlSelf->__PVT__pc_rot;
                if (vlSelf->__PVT__last_up) {
                    __Vdly__k = 0U;
                    __Vdly__state = 5U;
                } else {
                    __Vdly__k = (0x1fU & ((IData)(1U) 
                                          + (IData)(vlSelf->__PVT__k)));
                }
            }
        }
    } else if ((2U & (IData)(vlSelf->__PVT__state))) {
        if ((1U & (IData)(vlSelf->__PVT__state))) {
            vlSelf->__PVT__cy = vlSelf->__PVT__cout;
            if (vlSelf->__PVT__is_cmp) {
                vlSelf->__PVT__nz = vlSelf->__PVT__nz_n;
                if (vlSelf->__PVT__last_up) {
                    vlSelf->__PVT__f_eq = (1U & (~ (IData)(vlSelf->__PVT__nz_n)));
                    vlSelf->__PVT__f_ltu = (1U & (~ (IData)(vlSelf->__PVT__cout)));
                    vlSelf->__PVT__f_lt = (1U & (((1U 
                                                   & vlSelf->__PVT__xsh) 
                                                  != 
                                                  (1U 
                                                   & vlSelf->__PVT__ysh))
                                                  ? vlSelf->__PVT__xsh
                                                  : 
                                                 (~ (IData)(vlSelf->__PVT__cout))));
                }
            }
            if ((((3U == (IData)(vlSelf->__PVT__opc)) 
                  | (0x23U == (IData)(vlSelf->__PVT__opc))) 
                 | (0x67U == (IData)(vlSelf->__PVT__opc)))) {
                __Vdly__addr = vlSelf->__PVT__addr_ins;
            }
            vlSelf->__PVT__pc = vlSelf->__PVT__pc_rot;
            vlSelf->__PVT__imm_sr = vlSelf->__PVT__imm_rot;
            if (vlSelf->__PVT__exec_done) {
                __Vdly__k = 0U;
                __Vdly__state = (((((3U == (IData)(vlSelf->__PVT__opc)) 
                                    | (0x23U == (IData)(vlSelf->__PVT__opc))) 
                                   | (0x67U == (IData)(vlSelf->__PVT__opc))) 
                                  | (IData)(vlSelf->__PVT__is_slt))
                                  ? 4U : 5U);
            } else {
                __Vdly__k = (0x1fU & ((IData)(vlSelf->__PVT__is_sll)
                                       ? ((IData)(vlSelf->__PVT__k) 
                                          - (IData)(1U))
                                       : ((IData)(1U) 
                                          + (IData)(vlSelf->__PVT__k))));
            }
        } else {
            if ((0x33U == (IData)(vlSelf->__PVT__opc))) {
                __Vdly__shamt_w = ((vlSelf->__PVT__shamt_w 
                                    & (~ VL_SHIFTL_III(32,32,6, vlSelf->__PVT__mask, (IData)(vlSelf->__PVT__jw)))) 
                                   | VL_SHIFTL_III(32,32,6, vlSelf->d_wdata, (IData)(vlSelf->__PVT__jw)));
            }
            vlSelf->__PVT__sgn = (1U & (vlSelf->__PVT__a_val 
                                        >> (0x1fU & (IData)(vlSelf->__PVT__wm1))));
            if (((IData)(vlSelf->__PVT__j) == ((0x33U 
                                                == (IData)(vlSelf->__PVT__opc))
                                                ? (IData)(vlSelf->__PVT__mlast)
                                                : 0U))) {
                __Vdly__state = 3U;
                __Vdly__k = ((IData)(vlSelf->__PVT__is_sll)
                              ? (0x1fU & ((IData)(vlSelf->__PVT__nd) 
                                          - (IData)(1U)))
                              : 0U);
            } else {
                __Vdly__j = (7U & ((IData)(1U) + (IData)(vlSelf->__PVT__j)));
            }
        }
    } else if ((1U & (IData)(vlSelf->__PVT__state))) {
        __Vdly__j = 0U;
        vlSelf->__PVT__imm_sr = vlSelf->__PVT__imm;
        __Vdly__shamt_w = ((IData)(vlSelf->__PVT__sh_i)
                            ? (IData)(vlSelf->__PVT__rs2)
                            : 0U);
        if (vlSelf->__PVT__bad) {
            vlSelf->__PVT__trap_r = 1U;
            vlSelf->__PVT__halted_r = 1U;
            __Vdly__state = 6U;
        } else if (vlSelf->__PVT__is_sys) {
            vlSelf->__PVT__halted_r = 1U;
            __Vdly__state = 6U;
        } else if (vlSelf->__PVT__is_shift) {
            __Vdly__state = 2U;
        } else {
            __Vdly__k = 0U;
            __Vdly__state = 3U;
        }
    } else {
        vlSelf->__PVT__ir = vlSymsp->TOP.tb_sys3__DOT__dut__DOT__slot__BRA__27__KET____DOT__id;
        __Vdly__state = 1U;
    }
    vlSelf->__PVT__addr = __Vdly__addr;
    vlSelf->__PVT__j = __Vdly__j;
    vlSelf->__PVT__shamt_w = __Vdly__shamt_w;
    vlSelf->__PVT__state = __Vdly__state;
    vlSelf->__PVT__k = __Vdly__k;
    vlSelf->d_addr = (((QData)((IData)((vlSelf->__PVT__addr 
                                        >> 2U))) << 5U) 
                      | (QData)((IData)(vlSelf->__PVT__k)));
    vlSelf->__PVT__wm1 = (0x3fU & (((IData)(1U) << (IData)(vlSelf->__PVT__lw_r)) 
                                   - (IData)(1U)));
    vlSelf->__PVT__mlast = (0x3fU & (VL_DIV_III(6, 
                                                (0x3fU 
                                                 & ((IData)(4U) 
                                                    + 
                                                    ((IData)(1U) 
                                                     << (IData)(vlSelf->__PVT__lw_r)))), 
                                                (0x3fU 
                                                 & ((IData)(1U) 
                                                    << (IData)(vlSelf->__PVT__lw_r)))) 
                                     - (IData)(1U)));
    vlSelf->__PVT__nd = (0x3fU & (0x20U >> (IData)(vlSelf->__PVT__lw_r)));
    vlSelf->__PVT__jw = (0x3fU & ((IData)(vlSelf->__PVT__j) 
                                  * (0x3fU & ((IData)(1U) 
                                              << (IData)(vlSelf->__PVT__lw_r)))));
    vlSelf->__PVT__imm_rot = (VL_SHIFTR_III(32,32,6, vlSelf->__PVT__imm_sr, 
                                            (0x3fU 
                                             & ((IData)(1U) 
                                                << (IData)(vlSelf->__PVT__lw_r)))) 
                              | VL_SHIFTL_III(32,32,6, vlSelf->__PVT__imm_sr, 
                                              (0x3fU 
                                               & ((IData)(0x20U) 
                                                  - 
                                                  ((IData)(1U) 
                                                   << (IData)(vlSelf->__PVT__lw_r))))));
    vlSelf->__PVT__last_up = ((IData)(vlSelf->__PVT__k) 
                              == (0x1fU & ((0x3fU & 
                                            (0x20U 
                                             >> (IData)(vlSelf->__PVT__lw_r))) 
                                           - (IData)(1U))));
    vlSelf->__VdfgTmp_he4828306__0 = VL_SHIFTR_III(32,32,6, vlSelf->__PVT__pc, 
                                                   (0x3fU 
                                                    & ((IData)(1U) 
                                                       << (IData)(vlSelf->__PVT__lw_r))));
    __VdfgTmp_h933689ae__0 = (0x1fU & (vlSelf->__PVT__shamt_w 
                                       & ((0x3fU & 
                                           ((IData)(1U) 
                                            << (IData)(vlSelf->__PVT__lw_r))) 
                                          - (IData)(1U))));
    __PVT__qs = (0x1fU & ((0x1fU & vlSelf->__PVT__shamt_w) 
                          >> (IData)(vlSelf->__PVT__lw_r)));
    vlSelf->__PVT__mask = ((5U == (IData)(vlSelf->__PVT__lw_r))
                            ? 0xffffffffU : (VL_SHIFTL_III(32,32,6, (IData)(1U), 
                                                           (0x3fU 
                                                            & ((IData)(1U) 
                                                               << (IData)(vlSelf->__PVT__lw_r)))) 
                                             - (IData)(1U)));
    vlSelf->__PVT__rs2 = (0x1fU & (vlSelf->__PVT__ir 
                                   >> 0x14U));
    vlSelf->__PVT__is_sys = (0x73U == (0x7fU & vlSelf->__PVT__ir));
    vlSelf->__PVT__opc = (0x7fU & vlSelf->__PVT__ir);
    __VdfgTmp_h2cd83c5b__0 = ((0x37U == (0x7fU & vlSelf->__PVT__ir)) 
                              | (0x17U == (0x7fU & vlSelf->__PVT__ir)));
    __Vtableidx28 = (((IData)(vlSelf->__PVT__f_eq) 
                      << 5U) | (((IData)(vlSelf->__PVT__f_lt) 
                                 << 4U) | (((IData)(vlSelf->__PVT__f_ltu) 
                                            << 3U) 
                                           | (7U & 
                                              (vlSelf->__PVT__ir 
                                               >> 0xcU)))));
    __PVT__cond = Vtb_sys3__ConstPool__TABLE_h2a0441a0_0
        [__Vtableidx28];
    __VdfgTmp_hd9b60348__0 = ((2U == (7U & (vlSelf->__PVT__ir 
                                            >> 0xcU))) 
                              | (3U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))));
    __VdfgTmp_h18c46dac__0 = ((0x13U == (0x7fU & vlSelf->__PVT__ir)) 
                              | (0x33U == (0x7fU & vlSelf->__PVT__ir)));
    __VdfgTmp_he83b8d53__0 = ((1U == (7U & (vlSelf->__PVT__ir 
                                            >> 0xcU))) 
                              | (5U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))));
    vlSelf->__PVT__pc_rot = (vlSelf->__VdfgTmp_he4828306__0 
                             | VL_SHIFTL_III(32,32,6, vlSelf->__PVT__pc, 
                                             (0x3fU 
                                              & ((IData)(0x20U) 
                                                 - 
                                                 ((IData)(1U) 
                                                  << (IData)(vlSelf->__PVT__lw_r))))));
    __PVT__pc_d = (vlSelf->__PVT__pc & vlSelf->__PVT__mask);
    __PVT__imm_d = (vlSelf->__PVT__imm_sr & vlSelf->__PVT__mask);
    __PVT__c4_d = (VL_SHIFTR_III(32,32,6, 4U, (0x3fU 
                                               & ((IData)(vlSelf->__PVT__k) 
                                                  * 
                                                  (0x3fU 
                                                   & ((IData)(1U) 
                                                      << (IData)(vlSelf->__PVT__lw_r)))))) 
                   & vlSelf->__PVT__mask);
    vlSelf->__PVT__imm = ((IData)(__VdfgTmp_h2cd83c5b__0)
                           ? (0xfffff000U & vlSelf->__PVT__ir)
                           : ((0x6fU == (0x7fU & vlSelf->__PVT__ir))
                               ? (((- (IData)((vlSelf->__PVT__ir 
                                               >> 0x1fU))) 
                                   << 0x15U) | ((0x100000U 
                                                 & (vlSelf->__PVT__ir 
                                                    >> 0xbU)) 
                                                | ((0xff000U 
                                                    & vlSelf->__PVT__ir) 
                                                   | ((0x800U 
                                                       & (vlSelf->__PVT__ir 
                                                          >> 9U)) 
                                                      | (0x7feU 
                                                         & (vlSelf->__PVT__ir 
                                                            >> 0x14U))))))
                               : ((0x63U == (0x7fU 
                                             & vlSelf->__PVT__ir))
                                   ? (((- (IData)((vlSelf->__PVT__ir 
                                                   >> 0x1fU))) 
                                       << 0xdU) | (
                                                   (0x1000U 
                                                    & (vlSelf->__PVT__ir 
                                                       >> 0x13U)) 
                                                   | ((0x800U 
                                                       & (vlSelf->__PVT__ir 
                                                          << 4U)) 
                                                      | ((0x7e0U 
                                                          & (vlSelf->__PVT__ir 
                                                             >> 0x14U)) 
                                                         | (0x1eU 
                                                            & (vlSelf->__PVT__ir 
                                                               >> 7U))))))
                                   : ((0x23U == (0x7fU 
                                                 & vlSelf->__PVT__ir))
                                       ? (((- (IData)(
                                                      (vlSelf->__PVT__ir 
                                                       >> 0x1fU))) 
                                           << 0xcU) 
                                          | ((0xfe0U 
                                              & (vlSelf->__PVT__ir 
                                                 >> 0x14U)) 
                                             | (0x1fU 
                                                & (vlSelf->__PVT__ir 
                                                   >> 7U))))
                                       : (((- (IData)(
                                                      (vlSelf->__PVT__ir 
                                                       >> 0x1fU))) 
                                           << 0xcU) 
                                          | (vlSelf->__PVT__ir 
                                             >> 0x14U))))));
    __VdfgExtracted_h62388771__0 = ((IData)(__VdfgTmp_h2cd83c5b__0) 
                                    | (0x6fU == (0x7fU 
                                                 & vlSelf->__PVT__ir)));
    vlSelf->__PVT__is_cmp = ((0x63U == (0x7fU & vlSelf->__PVT__ir)) 
                             | ((IData)(__VdfgTmp_h18c46dac__0) 
                                & (IData)(__VdfgTmp_hd9b60348__0)));
    vlSelf->__PVT__sh_i = ((0x13U == (0x7fU & vlSelf->__PVT__ir)) 
                           & (IData)(__VdfgTmp_he83b8d53__0));
    vlSelf->__PVT__bad = (1U & ((~ ((IData)(__VdfgExtracted_h62388771__0) 
                                    | ((0x67U == (0x7fU 
                                                  & vlSelf->__PVT__ir)) 
                                       | ((0x63U == 
                                           (0x7fU & vlSelf->__PVT__ir)) 
                                          | ((3U == 
                                              (0x7fU 
                                               & vlSelf->__PVT__ir)) 
                                             | ((0x23U 
                                                 == 
                                                 (0x7fU 
                                                  & vlSelf->__PVT__ir)) 
                                                | ((0x13U 
                                                    == 
                                                    (0x7fU 
                                                     & vlSelf->__PVT__ir)) 
                                                   | ((0x33U 
                                                       == 
                                                       (0x7fU 
                                                        & vlSelf->__PVT__ir)) 
                                                      | (0x73U 
                                                         == 
                                                         (0x7fU 
                                                          & vlSelf->__PVT__ir)))))))))) 
                                | (((0x67U == (0x7fU 
                                               & vlSelf->__PVT__ir)) 
                                    & (0U != (7U & 
                                              (vlSelf->__PVT__ir 
                                               >> 0xcU)))) 
                                   | (((0x63U == (0x7fU 
                                                  & vlSelf->__PVT__ir)) 
                                       & (IData)(__VdfgTmp_hd9b60348__0)) 
                                      | ((((3U == (0x7fU 
                                                   & vlSelf->__PVT__ir)) 
                                           | (0x23U 
                                              == (0x7fU 
                                                  & vlSelf->__PVT__ir))) 
                                          & (2U != 
                                             (7U & 
                                              (vlSelf->__PVT__ir 
                                               >> 0xcU)))) 
                                         | ((IData)(
                                                    ((0x1013U 
                                                      == 
                                                      (0x707fU 
                                                       & vlSelf->__PVT__ir)) 
                                                     & (0U 
                                                        != 
                                                        (vlSelf->__PVT__ir 
                                                         >> 0x19U)))) 
                                            | ((IData)(
                                                       ((0x5013U 
                                                         == 
                                                         (0x707fU 
                                                          & vlSelf->__PVT__ir)) 
                                                        & ((0U 
                                                            != 
                                                            (vlSelf->__PVT__ir 
                                                             >> 0x19U)) 
                                                           & (0x20U 
                                                              != 
                                                              (vlSelf->__PVT__ir 
                                                               >> 0x19U))))) 
                                               | ((0x33U 
                                                   == 
                                                   (0x7fU 
                                                    & vlSelf->__PVT__ir)) 
                                                  & ((~ 
                                                      ((0x20U 
                                                        == 
                                                        (vlSelf->__PVT__ir 
                                                         >> 0x19U)) 
                                                       & ((0U 
                                                           == 
                                                           (7U 
                                                            & (vlSelf->__PVT__ir 
                                                               >> 0xcU))) 
                                                          | (5U 
                                                             == 
                                                             (7U 
                                                              & (vlSelf->__PVT__ir 
                                                                 >> 0xcU)))))) 
                                                     & (0U 
                                                        != 
                                                        (vlSelf->__PVT__ir 
                                                         >> 0x19U)))))))))));
    vlSelf->__PVT__is_slt = ((0x63U != (0x7fU & vlSelf->__PVT__ir)) 
                             & (IData)(vlSelf->__PVT__is_cmp));
    __PVT__inv = 0U;
    vlSelf->__PVT__is_shift = ((IData)(vlSelf->__PVT__sh_i) 
                               | ((0x33U == (0x7fU 
                                             & vlSelf->__PVT__ir)) 
                                  & (IData)(__VdfgTmp_he83b8d53__0)));
    vlSelf->__PVT__we = 0U;
    __PVT__fill = (((IData)(vlSelf->__PVT__is_shift) 
                    & (IData)(((0x40005000U == (0x40007000U 
                                                & vlSelf->__PVT__ir)) 
                               & (IData)(vlSelf->__PVT__sgn))))
                    ? vlSelf->__PVT__mask : 0U);
    __PVT__shx = ((3U == (IData)(vlSelf->__PVT__state)) 
                  & (IData)(vlSelf->__PVT__is_shift));
    vlSelf->__PVT__is_sll = ((IData)(vlSelf->__PVT__is_shift) 
                             & (0x1000U == (0x7000U 
                                            & vlSelf->__PVT__ir)));
    if (vlSelf->__PVT__is_sll) {
        vlSelf->__PVT__exec_done = (0U == (IData)(vlSelf->__PVT__k));
        __PVT__ia = (0x1ffU & ((IData)(vlSelf->__PVT__k) 
                               - (IData)(__PVT__qs)));
        __VdfgTmp_h41a48239__0 = ((VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__k)) 
                                   - VL_EXTENDS_II(32,9, (IData)(__PVT__qs))) 
                                  - (IData)(1U));
    } else {
        vlSelf->__PVT__exec_done = vlSelf->__PVT__last_up;
        __PVT__ia = (0x1ffU & ((IData)(vlSelf->__PVT__k) 
                               + (IData)(__PVT__qs)));
        __VdfgTmp_h41a48239__0 = ((IData)(1U) + (VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__k)) 
                                                 + 
                                                 VL_EXTENDS_II(32,9, (IData)(__PVT__qs))));
    }
    __PVT__va = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, (IData)(__PVT__ia))) 
                 & VL_LTES_III(9, (IData)(__PVT__ia), 
                               (0x1ffU & ((0x3fU & 
                                           (0x20U >> (IData)(vlSelf->__PVT__lw_r))) 
                                          - (IData)(1U)))));
    vlSelf->__PVT__a_val = ((0U == (0x1fU & (vlSelf->__PVT__ir 
                                             >> 0xfU)))
                             ? 0U : (vlSymsp->TOP.tb_sys3__DOT__dut__DOT__slot__BRA__27__KET____DOT__rf
                                     [((0x3e0U & (vlSelf->__PVT__ir 
                                                  >> 0xaU)) 
                                       | (0x1fU & (
                                                   (2U 
                                                    == (IData)(vlSelf->__PVT__state))
                                                    ? 
                                                   ((0x3fU 
                                                     & (0x20U 
                                                        >> (IData)(vlSelf->__PVT__lw_r))) 
                                                    - (IData)(1U))
                                                    : 
                                                   ((IData)(__PVT__shx)
                                                     ? (IData)(__PVT__ia)
                                                     : (IData)(vlSelf->__PVT__k)))))] 
                                     & vlSelf->__PVT__mask));
    __PVT__vb = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, 
                                                   (0x1ffU 
                                                    & __VdfgTmp_h41a48239__0))) 
                 & VL_LTES_III(9, (0x1ffU & __VdfgTmp_h41a48239__0), 
                               (0x1ffU & ((0x3fU & 
                                           (0x20U >> (IData)(vlSelf->__PVT__lw_r))) 
                                          - (IData)(1U)))));
    vlSelf->d_wdata = (((IData)(__PVT__shx) ? (0U == 
                                               (0x1fU 
                                                & (vlSelf->__PVT__ir 
                                                   >> 0xfU)))
                         : (0U == (0x1fU & (vlSelf->__PVT__ir 
                                            >> 0x14U))))
                        ? 0U : (vlSymsp->TOP.tb_sys3__DOT__dut__DOT__slot__BRA__27__KET____DOT__rf
                                [((0x3e0U & (((IData)(__PVT__shx)
                                               ? (vlSelf->__PVT__ir 
                                                  >> 0xfU)
                                               : (vlSelf->__PVT__ir 
                                                  >> 0x14U)) 
                                             << 5U)) 
                                  | (0x1fU & ((2U == (IData)(vlSelf->__PVT__state))
                                               ? (IData)(vlSelf->__PVT__j)
                                               : ((IData)(__PVT__shx)
                                                   ? __VdfgTmp_h41a48239__0
                                                   : (IData)(vlSelf->__PVT__k)))))] 
                                & vlSelf->__PVT__mask));
    __PVT__X = vlSelf->__PVT__a_val;
    __PVT__Yr = (((0x33U == (0x7fU & vlSelf->__PVT__ir)) 
                  | (0x63U == (0x7fU & vlSelf->__PVT__ir)))
                  ? vlSelf->d_wdata : __PVT__imm_d);
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if ((0x37U != (0x7fU & vlSelf->__PVT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->__PVT__ir))) {
                if ((0x6fU != (0x7fU & vlSelf->__PVT__ir))) {
                    if (((IData)((0x40000033U == (0x4000707fU 
                                                  & vlSelf->__PVT__ir))) 
                         | (IData)(vlSelf->__PVT__is_cmp))) {
                        __PVT__inv = 1U;
                    }
                }
            }
        }
        if (vlSelf->__PVT__is_shift) {
            vlSelf->__PVT__we = 1U;
        } else if (__VdfgExtracted_h62388771__0) {
            vlSelf->__PVT__we = 1U;
        } else if (((~ (IData)(vlSelf->__PVT__is_cmp)) 
                    & (IData)(__VdfgTmp_h18c46dac__0))) {
            vlSelf->__PVT__we = 1U;
        }
        if ((0x37U == (0x7fU & vlSelf->__PVT__ir))) {
            __PVT__X = 0U;
        } else if ((0x17U == (0x7fU & vlSelf->__PVT__ir))) {
            __PVT__X = __PVT__pc_d;
        } else if ((0x6fU == (0x7fU & vlSelf->__PVT__ir))) {
            __PVT__X = __PVT__pc_d;
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        if ((3U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__we = 1U;
        } else if (vlSelf->__PVT__is_slt) {
            vlSelf->__PVT__we = 1U;
        } else if ((0x67U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__we = 1U;
        }
        __PVT__X = __PVT__pc_d;
    } else if ((5U == (IData)(vlSelf->__PVT__state))) {
        __PVT__X = __PVT__pc_d;
    }
    vlSelf->__PVT__xsh = VL_SHIFTR_III(32,32,6, __PVT__X, 
                                       (0x3fU & (((IData)(1U) 
                                                  << (IData)(vlSelf->__PVT__lw_r)) 
                                                 - (IData)(1U))));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if ((0x37U != (0x7fU & vlSelf->__PVT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->__PVT__ir))) {
                if ((0x6fU == (0x7fU & vlSelf->__PVT__ir))) {
                    __PVT__Yr = __PVT__c4_d;
                }
            }
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        __PVT__Yr = __PVT__c4_d;
    } else if ((5U == (IData)(vlSelf->__PVT__state))) {
        __PVT__Yr = (((0x6fU == (0x7fU & vlSelf->__PVT__ir)) 
                      | ((0x63U == (0x7fU & vlSelf->__PVT__ir)) 
                         & (IData)(__PVT__cond))) ? __PVT__imm_d
                      : __PVT__c4_d);
    }
    vlSelf->__PVT__ysh = VL_SHIFTR_III(32,32,6, __PVT__Yr, 
                                       (0x3fU & (((IData)(1U) 
                                                  << (IData)(vlSelf->__PVT__lw_r)) 
                                                 - (IData)(1U))));
    __PVT__sum_full = (0x1ffffffffULL & ((QData)((IData)(__PVT__X)) 
                                         + ((QData)((IData)(
                                                            ((IData)(__PVT__inv)
                                                              ? 
                                                             ((~ __PVT__Yr) 
                                                              & vlSelf->__PVT__mask)
                                                              : __PVT__Yr))) 
                                            + (QData)((IData)(
                                                              ((0U 
                                                                == (IData)(vlSelf->__PVT__k))
                                                                ? (IData)(__PVT__inv)
                                                                : (IData)(vlSelf->__PVT__cy)))))));
    vlSelf->__PVT__cout = (1U & (IData)((0x1ffffffffULL 
                                         & (__PVT__sum_full 
                                            >> (0x3fU 
                                                & ((IData)(1U) 
                                                   << (IData)(vlSelf->__PVT__lw_r)))))));
    __PVT__sum_d = ((IData)(__PVT__sum_full) & vlSelf->__PVT__mask);
    vlSelf->__PVT__nz_n = (((0U != (IData)(vlSelf->__PVT__k)) 
                            & (IData)(vlSelf->__PVT__nz)) 
                           | (0U != __PVT__sum_d));
    vlSelf->__VdfgTmp_h7980eff3__0 = VL_SHIFTL_III(32,32,6, __PVT__sum_d, 
                                                   (0x3fU 
                                                    & ((IData)(0x20U) 
                                                       - 
                                                       ((IData)(1U) 
                                                        << (IData)(vlSelf->__PVT__lw_r)))));
    vlSelf->__PVT__wd = (((IData)(__VdfgTmp_h18c46dac__0) 
                          & ((4U == (7U & (vlSelf->__PVT__ir 
                                           >> 0xcU))) 
                             | ((6U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))) 
                                | (7U == (7U & (vlSelf->__PVT__ir 
                                                >> 0xcU))))))
                          ? ((4U == (7U & (vlSelf->__PVT__ir 
                                           >> 0xcU)))
                              ? (__PVT__X ^ __PVT__Yr)
                              : ((6U == (7U & (vlSelf->__PVT__ir 
                                               >> 0xcU)))
                                  ? (__PVT__X | __PVT__Yr)
                                  : (__PVT__X & __PVT__Yr)))
                          : __PVT__sum_d);
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if (vlSelf->__PVT__is_shift) {
            vlSelf->__PVT__wd = ((IData)(((((QData)((IData)(
                                                            ((IData)(vlSelf->__PVT__is_sll)
                                                              ? 
                                                             ((IData)(__PVT__va)
                                                               ? vlSelf->__PVT__a_val
                                                               : 0U)
                                                              : 
                                                             ((IData)(__PVT__vb)
                                                               ? vlSelf->d_wdata
                                                               : __PVT__fill)))) 
                                            << (0x3fU 
                                                & ((IData)(1U) 
                                                   << (IData)(vlSelf->__PVT__lw_r)))) 
                                           | (QData)((IData)(
                                                             ((IData)(vlSelf->__PVT__is_sll)
                                                               ? 
                                                              ((IData)(__PVT__vb)
                                                                ? vlSelf->d_wdata
                                                                : 0U)
                                                               : 
                                                              ((IData)(__PVT__va)
                                                                ? vlSelf->__PVT__a_val
                                                                : __PVT__fill))))) 
                                          >> (0x3fU 
                                              & ((IData)(vlSelf->__PVT__is_sll)
                                                  ? 
                                                 (((IData)(1U) 
                                                   << (IData)(vlSelf->__PVT__lw_r)) 
                                                  - (IData)(__VdfgTmp_h933689ae__0))
                                                  : (IData)(__VdfgTmp_h933689ae__0))))) 
                                 & vlSelf->__PVT__mask);
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        if ((3U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__wd = (vlSymsp->TOP.tb_sys3__DOT__dut__DOT__slot__BRA__27__KET____DOT__dm
                                 [(0x7fffU & (IData)(vlSelf->d_addr))] 
                                 & vlSelf->__PVT__mask);
        } else if (vlSelf->__PVT__is_slt) {
            vlSelf->__PVT__wd = 0U;
            vlSelf->__PVT__wd = ((0xfffffffeU & vlSelf->__PVT__wd) 
                                 | ((0U == (IData)(vlSelf->__PVT__k)) 
                                    & ((2U == (7U & 
                                               (vlSelf->__PVT__ir 
                                                >> 0xcU)))
                                        ? (IData)(vlSelf->__PVT__f_lt)
                                        : (IData)(vlSelf->__PVT__f_ltu))));
        } else if ((0x67U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__wd = __PVT__sum_d;
        }
    }
    vlSelf->__PVT__addr_ins = (VL_SHIFTR_III(32,32,6, vlSelf->__PVT__addr, 
                                             (0x3fU 
                                              & ((IData)(1U) 
                                                 << (IData)(vlSelf->__PVT__lw_r)))) 
                               | vlSelf->__VdfgTmp_h7980eff3__0);
}

VL_INLINE_OPT void Vtb_sys3_uc_core_rw___nba_sequent__TOP__tb_sys3__DOT__dut__DOT__slot__BRA__28__KET____DOT__core__0(Vtb_sys3_uc_core_rw* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_sys3__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+          Vtb_sys3_uc_core_rw___nba_sequent__TOP__tb_sys3__DOT__dut__DOT__slot__BRA__28__KET____DOT__core__0\n"); );
    // Init
    CData/*0:0*/ __PVT__shx;
    __PVT__shx = 0;
    IData/*31:0*/ __PVT__pc_d;
    __PVT__pc_d = 0;
    IData/*31:0*/ __PVT__imm_d;
    __PVT__imm_d = 0;
    IData/*31:0*/ __PVT__c4_d;
    __PVT__c4_d = 0;
    SData/*8:0*/ __PVT__qs;
    __PVT__qs = 0;
    SData/*8:0*/ __PVT__ia;
    __PVT__ia = 0;
    CData/*0:0*/ __PVT__va;
    __PVT__va = 0;
    CData/*0:0*/ __PVT__vb;
    __PVT__vb = 0;
    IData/*31:0*/ __PVT__fill;
    __PVT__fill = 0;
    IData/*31:0*/ __PVT__X;
    __PVT__X = 0;
    IData/*31:0*/ __PVT__Yr;
    __PVT__Yr = 0;
    CData/*0:0*/ __PVT__inv;
    __PVT__inv = 0;
    QData/*32:0*/ __PVT__sum_full;
    __PVT__sum_full = 0;
    IData/*31:0*/ __PVT__sum_d;
    __PVT__sum_d = 0;
    CData/*0:0*/ __PVT__cond;
    __PVT__cond = 0;
    CData/*0:0*/ __VdfgExtracted_h62388771__0;
    __VdfgExtracted_h62388771__0 = 0;
    IData/*31:0*/ __VdfgTmp_h41a48239__0;
    __VdfgTmp_h41a48239__0 = 0;
    CData/*0:0*/ __VdfgTmp_h2cd83c5b__0;
    __VdfgTmp_h2cd83c5b__0 = 0;
    CData/*0:0*/ __VdfgTmp_he83b8d53__0;
    __VdfgTmp_he83b8d53__0 = 0;
    CData/*0:0*/ __VdfgTmp_h18c46dac__0;
    __VdfgTmp_h18c46dac__0 = 0;
    CData/*0:0*/ __VdfgTmp_hd9b60348__0;
    __VdfgTmp_hd9b60348__0 = 0;
    CData/*5:0*/ __VdfgTmp_h933689ae__0;
    __VdfgTmp_h933689ae__0 = 0;
    CData/*5:0*/ __Vtableidx29;
    __Vtableidx29 = 0;
    CData/*2:0*/ __Vdly__state;
    __Vdly__state = 0;
    IData/*31:0*/ __Vdly__addr;
    __Vdly__addr = 0;
    IData/*31:0*/ __Vdly__shamt_w;
    __Vdly__shamt_w = 0;
    CData/*4:0*/ __Vdly__k;
    __Vdly__k = 0;
    CData/*2:0*/ __Vdly__j;
    __Vdly__j = 0;
    // Body
    __Vdly__addr = vlSelf->__PVT__addr;
    __Vdly__j = vlSelf->__PVT__j;
    __Vdly__shamt_w = vlSelf->__PVT__shamt_w;
    __Vdly__state = vlSelf->__PVT__state;
    __Vdly__k = vlSelf->__PVT__k;
    if (vlSymsp->TOP.tb_sys3__DOT__rst) {
        __Vdly__state = 6U;
        vlSelf->__PVT__pc = 0U;
        vlSelf->__PVT__ir = 0U;
        __Vdly__addr = 0U;
        vlSelf->__PVT__imm_sr = 0U;
        __Vdly__shamt_w = 0U;
        __Vdly__k = 0U;
        __Vdly__j = 0U;
        vlSelf->__PVT__lw_r = 0U;
        vlSelf->__PVT__cy = 0U;
        vlSelf->__PVT__nz = 0U;
        vlSelf->__PVT__f_eq = 0U;
        vlSelf->__PVT__f_lt = 0U;
        vlSelf->__PVT__f_ltu = 0U;
        vlSelf->__PVT__sgn = 0U;
        vlSelf->__PVT__halted_r = 1U;
        vlSelf->__PVT__trap_r = 0U;
    } else if (((vlSymsp->TOP.tb_sys3__DOT__dut__DOT__start_v 
                 >> 0x1cU) & (6U == (IData)(vlSelf->__PVT__state)))) {
        vlSelf->__PVT__pc = vlSymsp->TOP.tb_sys3__DOT__dut__DOT__launch_entry;
        vlSelf->__PVT__lw_r = vlSymsp->TOP.tb_sys3__DOT__dut__DOT__launch_lw;
        __Vdly__k = 0U;
        vlSelf->__PVT__halted_r = 0U;
        vlSelf->__PVT__trap_r = 0U;
        __Vdly__state = 0U;
    } else if ((4U & (IData)(vlSelf->__PVT__state))) {
        if ((1U & (~ ((IData)(vlSelf->__PVT__state) 
                      >> 1U)))) {
            if ((1U & (IData)(vlSelf->__PVT__state))) {
                if ((0x67U == (IData)(vlSelf->__PVT__opc))) {
                    vlSelf->__PVT__pc = (0xfffffffeU 
                                         & vlSelf->__PVT__addr);
                    __Vdly__state = 0U;
                } else {
                    vlSelf->__PVT__pc = (vlSelf->__VdfgTmp_he4828306__0 
                                         | vlSelf->__VdfgTmp_h7980eff3__0);
                    vlSelf->__PVT__imm_sr = vlSelf->__PVT__imm_rot;
                    vlSelf->__PVT__cy = vlSelf->__PVT__cout;
                    if (vlSelf->__PVT__last_up) {
                        __Vdly__k = 0U;
                        __Vdly__state = 0U;
                    } else {
                        __Vdly__k = (0x1fU & ((IData)(1U) 
                                              + (IData)(vlSelf->__PVT__k)));
                    }
                }
            } else {
                vlSelf->__PVT__cy = vlSelf->__PVT__cout;
                vlSelf->__PVT__pc = vlSelf->__PVT__pc_rot;
                if (vlSelf->__PVT__last_up) {
                    __Vdly__k = 0U;
                    __Vdly__state = 5U;
                } else {
                    __Vdly__k = (0x1fU & ((IData)(1U) 
                                          + (IData)(vlSelf->__PVT__k)));
                }
            }
        }
    } else if ((2U & (IData)(vlSelf->__PVT__state))) {
        if ((1U & (IData)(vlSelf->__PVT__state))) {
            vlSelf->__PVT__cy = vlSelf->__PVT__cout;
            if (vlSelf->__PVT__is_cmp) {
                vlSelf->__PVT__nz = vlSelf->__PVT__nz_n;
                if (vlSelf->__PVT__last_up) {
                    vlSelf->__PVT__f_eq = (1U & (~ (IData)(vlSelf->__PVT__nz_n)));
                    vlSelf->__PVT__f_ltu = (1U & (~ (IData)(vlSelf->__PVT__cout)));
                    vlSelf->__PVT__f_lt = (1U & (((1U 
                                                   & vlSelf->__PVT__xsh) 
                                                  != 
                                                  (1U 
                                                   & vlSelf->__PVT__ysh))
                                                  ? vlSelf->__PVT__xsh
                                                  : 
                                                 (~ (IData)(vlSelf->__PVT__cout))));
                }
            }
            if ((((3U == (IData)(vlSelf->__PVT__opc)) 
                  | (0x23U == (IData)(vlSelf->__PVT__opc))) 
                 | (0x67U == (IData)(vlSelf->__PVT__opc)))) {
                __Vdly__addr = vlSelf->__PVT__addr_ins;
            }
            vlSelf->__PVT__pc = vlSelf->__PVT__pc_rot;
            vlSelf->__PVT__imm_sr = vlSelf->__PVT__imm_rot;
            if (vlSelf->__PVT__exec_done) {
                __Vdly__k = 0U;
                __Vdly__state = (((((3U == (IData)(vlSelf->__PVT__opc)) 
                                    | (0x23U == (IData)(vlSelf->__PVT__opc))) 
                                   | (0x67U == (IData)(vlSelf->__PVT__opc))) 
                                  | (IData)(vlSelf->__PVT__is_slt))
                                  ? 4U : 5U);
            } else {
                __Vdly__k = (0x1fU & ((IData)(vlSelf->__PVT__is_sll)
                                       ? ((IData)(vlSelf->__PVT__k) 
                                          - (IData)(1U))
                                       : ((IData)(1U) 
                                          + (IData)(vlSelf->__PVT__k))));
            }
        } else {
            if ((0x33U == (IData)(vlSelf->__PVT__opc))) {
                __Vdly__shamt_w = ((vlSelf->__PVT__shamt_w 
                                    & (~ VL_SHIFTL_III(32,32,6, vlSelf->__PVT__mask, (IData)(vlSelf->__PVT__jw)))) 
                                   | VL_SHIFTL_III(32,32,6, vlSelf->d_wdata, (IData)(vlSelf->__PVT__jw)));
            }
            vlSelf->__PVT__sgn = (1U & (vlSelf->__PVT__a_val 
                                        >> (0x1fU & (IData)(vlSelf->__PVT__wm1))));
            if (((IData)(vlSelf->__PVT__j) == ((0x33U 
                                                == (IData)(vlSelf->__PVT__opc))
                                                ? (IData)(vlSelf->__PVT__mlast)
                                                : 0U))) {
                __Vdly__state = 3U;
                __Vdly__k = ((IData)(vlSelf->__PVT__is_sll)
                              ? (0x1fU & ((IData)(vlSelf->__PVT__nd) 
                                          - (IData)(1U)))
                              : 0U);
            } else {
                __Vdly__j = (7U & ((IData)(1U) + (IData)(vlSelf->__PVT__j)));
            }
        }
    } else if ((1U & (IData)(vlSelf->__PVT__state))) {
        __Vdly__j = 0U;
        vlSelf->__PVT__imm_sr = vlSelf->__PVT__imm;
        __Vdly__shamt_w = ((IData)(vlSelf->__PVT__sh_i)
                            ? (IData)(vlSelf->__PVT__rs2)
                            : 0U);
        if (vlSelf->__PVT__bad) {
            vlSelf->__PVT__trap_r = 1U;
            vlSelf->__PVT__halted_r = 1U;
            __Vdly__state = 6U;
        } else if (vlSelf->__PVT__is_sys) {
            vlSelf->__PVT__halted_r = 1U;
            __Vdly__state = 6U;
        } else if (vlSelf->__PVT__is_shift) {
            __Vdly__state = 2U;
        } else {
            __Vdly__k = 0U;
            __Vdly__state = 3U;
        }
    } else {
        vlSelf->__PVT__ir = vlSymsp->TOP.tb_sys3__DOT__dut__DOT__slot__BRA__28__KET____DOT__id;
        __Vdly__state = 1U;
    }
    vlSelf->__PVT__addr = __Vdly__addr;
    vlSelf->__PVT__j = __Vdly__j;
    vlSelf->__PVT__shamt_w = __Vdly__shamt_w;
    vlSelf->__PVT__state = __Vdly__state;
    vlSelf->__PVT__k = __Vdly__k;
    vlSelf->d_addr = (((QData)((IData)((vlSelf->__PVT__addr 
                                        >> 2U))) << 5U) 
                      | (QData)((IData)(vlSelf->__PVT__k)));
    vlSelf->__PVT__wm1 = (0x3fU & (((IData)(1U) << (IData)(vlSelf->__PVT__lw_r)) 
                                   - (IData)(1U)));
    vlSelf->__PVT__mlast = (0x3fU & (VL_DIV_III(6, 
                                                (0x3fU 
                                                 & ((IData)(4U) 
                                                    + 
                                                    ((IData)(1U) 
                                                     << (IData)(vlSelf->__PVT__lw_r)))), 
                                                (0x3fU 
                                                 & ((IData)(1U) 
                                                    << (IData)(vlSelf->__PVT__lw_r)))) 
                                     - (IData)(1U)));
    vlSelf->__PVT__nd = (0x3fU & (0x20U >> (IData)(vlSelf->__PVT__lw_r)));
    vlSelf->__PVT__jw = (0x3fU & ((IData)(vlSelf->__PVT__j) 
                                  * (0x3fU & ((IData)(1U) 
                                              << (IData)(vlSelf->__PVT__lw_r)))));
    vlSelf->__PVT__imm_rot = (VL_SHIFTR_III(32,32,6, vlSelf->__PVT__imm_sr, 
                                            (0x3fU 
                                             & ((IData)(1U) 
                                                << (IData)(vlSelf->__PVT__lw_r)))) 
                              | VL_SHIFTL_III(32,32,6, vlSelf->__PVT__imm_sr, 
                                              (0x3fU 
                                               & ((IData)(0x20U) 
                                                  - 
                                                  ((IData)(1U) 
                                                   << (IData)(vlSelf->__PVT__lw_r))))));
    vlSelf->__PVT__last_up = ((IData)(vlSelf->__PVT__k) 
                              == (0x1fU & ((0x3fU & 
                                            (0x20U 
                                             >> (IData)(vlSelf->__PVT__lw_r))) 
                                           - (IData)(1U))));
    vlSelf->__VdfgTmp_he4828306__0 = VL_SHIFTR_III(32,32,6, vlSelf->__PVT__pc, 
                                                   (0x3fU 
                                                    & ((IData)(1U) 
                                                       << (IData)(vlSelf->__PVT__lw_r))));
    __VdfgTmp_h933689ae__0 = (0x1fU & (vlSelf->__PVT__shamt_w 
                                       & ((0x3fU & 
                                           ((IData)(1U) 
                                            << (IData)(vlSelf->__PVT__lw_r))) 
                                          - (IData)(1U))));
    __PVT__qs = (0x1fU & ((0x1fU & vlSelf->__PVT__shamt_w) 
                          >> (IData)(vlSelf->__PVT__lw_r)));
    vlSelf->__PVT__mask = ((5U == (IData)(vlSelf->__PVT__lw_r))
                            ? 0xffffffffU : (VL_SHIFTL_III(32,32,6, (IData)(1U), 
                                                           (0x3fU 
                                                            & ((IData)(1U) 
                                                               << (IData)(vlSelf->__PVT__lw_r)))) 
                                             - (IData)(1U)));
    vlSelf->__PVT__rs2 = (0x1fU & (vlSelf->__PVT__ir 
                                   >> 0x14U));
    vlSelf->__PVT__is_sys = (0x73U == (0x7fU & vlSelf->__PVT__ir));
    vlSelf->__PVT__opc = (0x7fU & vlSelf->__PVT__ir);
    __VdfgTmp_h2cd83c5b__0 = ((0x37U == (0x7fU & vlSelf->__PVT__ir)) 
                              | (0x17U == (0x7fU & vlSelf->__PVT__ir)));
    __Vtableidx29 = (((IData)(vlSelf->__PVT__f_eq) 
                      << 5U) | (((IData)(vlSelf->__PVT__f_lt) 
                                 << 4U) | (((IData)(vlSelf->__PVT__f_ltu) 
                                            << 3U) 
                                           | (7U & 
                                              (vlSelf->__PVT__ir 
                                               >> 0xcU)))));
    __PVT__cond = Vtb_sys3__ConstPool__TABLE_h2a0441a0_0
        [__Vtableidx29];
    __VdfgTmp_hd9b60348__0 = ((2U == (7U & (vlSelf->__PVT__ir 
                                            >> 0xcU))) 
                              | (3U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))));
    __VdfgTmp_h18c46dac__0 = ((0x13U == (0x7fU & vlSelf->__PVT__ir)) 
                              | (0x33U == (0x7fU & vlSelf->__PVT__ir)));
    __VdfgTmp_he83b8d53__0 = ((1U == (7U & (vlSelf->__PVT__ir 
                                            >> 0xcU))) 
                              | (5U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))));
    vlSelf->__PVT__pc_rot = (vlSelf->__VdfgTmp_he4828306__0 
                             | VL_SHIFTL_III(32,32,6, vlSelf->__PVT__pc, 
                                             (0x3fU 
                                              & ((IData)(0x20U) 
                                                 - 
                                                 ((IData)(1U) 
                                                  << (IData)(vlSelf->__PVT__lw_r))))));
    __PVT__pc_d = (vlSelf->__PVT__pc & vlSelf->__PVT__mask);
    __PVT__imm_d = (vlSelf->__PVT__imm_sr & vlSelf->__PVT__mask);
    __PVT__c4_d = (VL_SHIFTR_III(32,32,6, 4U, (0x3fU 
                                               & ((IData)(vlSelf->__PVT__k) 
                                                  * 
                                                  (0x3fU 
                                                   & ((IData)(1U) 
                                                      << (IData)(vlSelf->__PVT__lw_r)))))) 
                   & vlSelf->__PVT__mask);
    vlSelf->__PVT__imm = ((IData)(__VdfgTmp_h2cd83c5b__0)
                           ? (0xfffff000U & vlSelf->__PVT__ir)
                           : ((0x6fU == (0x7fU & vlSelf->__PVT__ir))
                               ? (((- (IData)((vlSelf->__PVT__ir 
                                               >> 0x1fU))) 
                                   << 0x15U) | ((0x100000U 
                                                 & (vlSelf->__PVT__ir 
                                                    >> 0xbU)) 
                                                | ((0xff000U 
                                                    & vlSelf->__PVT__ir) 
                                                   | ((0x800U 
                                                       & (vlSelf->__PVT__ir 
                                                          >> 9U)) 
                                                      | (0x7feU 
                                                         & (vlSelf->__PVT__ir 
                                                            >> 0x14U))))))
                               : ((0x63U == (0x7fU 
                                             & vlSelf->__PVT__ir))
                                   ? (((- (IData)((vlSelf->__PVT__ir 
                                                   >> 0x1fU))) 
                                       << 0xdU) | (
                                                   (0x1000U 
                                                    & (vlSelf->__PVT__ir 
                                                       >> 0x13U)) 
                                                   | ((0x800U 
                                                       & (vlSelf->__PVT__ir 
                                                          << 4U)) 
                                                      | ((0x7e0U 
                                                          & (vlSelf->__PVT__ir 
                                                             >> 0x14U)) 
                                                         | (0x1eU 
                                                            & (vlSelf->__PVT__ir 
                                                               >> 7U))))))
                                   : ((0x23U == (0x7fU 
                                                 & vlSelf->__PVT__ir))
                                       ? (((- (IData)(
                                                      (vlSelf->__PVT__ir 
                                                       >> 0x1fU))) 
                                           << 0xcU) 
                                          | ((0xfe0U 
                                              & (vlSelf->__PVT__ir 
                                                 >> 0x14U)) 
                                             | (0x1fU 
                                                & (vlSelf->__PVT__ir 
                                                   >> 7U))))
                                       : (((- (IData)(
                                                      (vlSelf->__PVT__ir 
                                                       >> 0x1fU))) 
                                           << 0xcU) 
                                          | (vlSelf->__PVT__ir 
                                             >> 0x14U))))));
    __VdfgExtracted_h62388771__0 = ((IData)(__VdfgTmp_h2cd83c5b__0) 
                                    | (0x6fU == (0x7fU 
                                                 & vlSelf->__PVT__ir)));
    vlSelf->__PVT__is_cmp = ((0x63U == (0x7fU & vlSelf->__PVT__ir)) 
                             | ((IData)(__VdfgTmp_h18c46dac__0) 
                                & (IData)(__VdfgTmp_hd9b60348__0)));
    vlSelf->__PVT__sh_i = ((0x13U == (0x7fU & vlSelf->__PVT__ir)) 
                           & (IData)(__VdfgTmp_he83b8d53__0));
    vlSelf->__PVT__bad = (1U & ((~ ((IData)(__VdfgExtracted_h62388771__0) 
                                    | ((0x67U == (0x7fU 
                                                  & vlSelf->__PVT__ir)) 
                                       | ((0x63U == 
                                           (0x7fU & vlSelf->__PVT__ir)) 
                                          | ((3U == 
                                              (0x7fU 
                                               & vlSelf->__PVT__ir)) 
                                             | ((0x23U 
                                                 == 
                                                 (0x7fU 
                                                  & vlSelf->__PVT__ir)) 
                                                | ((0x13U 
                                                    == 
                                                    (0x7fU 
                                                     & vlSelf->__PVT__ir)) 
                                                   | ((0x33U 
                                                       == 
                                                       (0x7fU 
                                                        & vlSelf->__PVT__ir)) 
                                                      | (0x73U 
                                                         == 
                                                         (0x7fU 
                                                          & vlSelf->__PVT__ir)))))))))) 
                                | (((0x67U == (0x7fU 
                                               & vlSelf->__PVT__ir)) 
                                    & (0U != (7U & 
                                              (vlSelf->__PVT__ir 
                                               >> 0xcU)))) 
                                   | (((0x63U == (0x7fU 
                                                  & vlSelf->__PVT__ir)) 
                                       & (IData)(__VdfgTmp_hd9b60348__0)) 
                                      | ((((3U == (0x7fU 
                                                   & vlSelf->__PVT__ir)) 
                                           | (0x23U 
                                              == (0x7fU 
                                                  & vlSelf->__PVT__ir))) 
                                          & (2U != 
                                             (7U & 
                                              (vlSelf->__PVT__ir 
                                               >> 0xcU)))) 
                                         | ((IData)(
                                                    ((0x1013U 
                                                      == 
                                                      (0x707fU 
                                                       & vlSelf->__PVT__ir)) 
                                                     & (0U 
                                                        != 
                                                        (vlSelf->__PVT__ir 
                                                         >> 0x19U)))) 
                                            | ((IData)(
                                                       ((0x5013U 
                                                         == 
                                                         (0x707fU 
                                                          & vlSelf->__PVT__ir)) 
                                                        & ((0U 
                                                            != 
                                                            (vlSelf->__PVT__ir 
                                                             >> 0x19U)) 
                                                           & (0x20U 
                                                              != 
                                                              (vlSelf->__PVT__ir 
                                                               >> 0x19U))))) 
                                               | ((0x33U 
                                                   == 
                                                   (0x7fU 
                                                    & vlSelf->__PVT__ir)) 
                                                  & ((~ 
                                                      ((0x20U 
                                                        == 
                                                        (vlSelf->__PVT__ir 
                                                         >> 0x19U)) 
                                                       & ((0U 
                                                           == 
                                                           (7U 
                                                            & (vlSelf->__PVT__ir 
                                                               >> 0xcU))) 
                                                          | (5U 
                                                             == 
                                                             (7U 
                                                              & (vlSelf->__PVT__ir 
                                                                 >> 0xcU)))))) 
                                                     & (0U 
                                                        != 
                                                        (vlSelf->__PVT__ir 
                                                         >> 0x19U)))))))))));
    vlSelf->__PVT__is_slt = ((0x63U != (0x7fU & vlSelf->__PVT__ir)) 
                             & (IData)(vlSelf->__PVT__is_cmp));
    __PVT__inv = 0U;
    vlSelf->__PVT__is_shift = ((IData)(vlSelf->__PVT__sh_i) 
                               | ((0x33U == (0x7fU 
                                             & vlSelf->__PVT__ir)) 
                                  & (IData)(__VdfgTmp_he83b8d53__0)));
    vlSelf->__PVT__we = 0U;
    __PVT__fill = (((IData)(vlSelf->__PVT__is_shift) 
                    & (IData)(((0x40005000U == (0x40007000U 
                                                & vlSelf->__PVT__ir)) 
                               & (IData)(vlSelf->__PVT__sgn))))
                    ? vlSelf->__PVT__mask : 0U);
    __PVT__shx = ((3U == (IData)(vlSelf->__PVT__state)) 
                  & (IData)(vlSelf->__PVT__is_shift));
    vlSelf->__PVT__is_sll = ((IData)(vlSelf->__PVT__is_shift) 
                             & (0x1000U == (0x7000U 
                                            & vlSelf->__PVT__ir)));
    if (vlSelf->__PVT__is_sll) {
        vlSelf->__PVT__exec_done = (0U == (IData)(vlSelf->__PVT__k));
        __PVT__ia = (0x1ffU & ((IData)(vlSelf->__PVT__k) 
                               - (IData)(__PVT__qs)));
        __VdfgTmp_h41a48239__0 = ((VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__k)) 
                                   - VL_EXTENDS_II(32,9, (IData)(__PVT__qs))) 
                                  - (IData)(1U));
    } else {
        vlSelf->__PVT__exec_done = vlSelf->__PVT__last_up;
        __PVT__ia = (0x1ffU & ((IData)(vlSelf->__PVT__k) 
                               + (IData)(__PVT__qs)));
        __VdfgTmp_h41a48239__0 = ((IData)(1U) + (VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__k)) 
                                                 + 
                                                 VL_EXTENDS_II(32,9, (IData)(__PVT__qs))));
    }
    __PVT__va = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, (IData)(__PVT__ia))) 
                 & VL_LTES_III(9, (IData)(__PVT__ia), 
                               (0x1ffU & ((0x3fU & 
                                           (0x20U >> (IData)(vlSelf->__PVT__lw_r))) 
                                          - (IData)(1U)))));
    vlSelf->__PVT__a_val = ((0U == (0x1fU & (vlSelf->__PVT__ir 
                                             >> 0xfU)))
                             ? 0U : (vlSymsp->TOP.tb_sys3__DOT__dut__DOT__slot__BRA__28__KET____DOT__rf
                                     [((0x3e0U & (vlSelf->__PVT__ir 
                                                  >> 0xaU)) 
                                       | (0x1fU & (
                                                   (2U 
                                                    == (IData)(vlSelf->__PVT__state))
                                                    ? 
                                                   ((0x3fU 
                                                     & (0x20U 
                                                        >> (IData)(vlSelf->__PVT__lw_r))) 
                                                    - (IData)(1U))
                                                    : 
                                                   ((IData)(__PVT__shx)
                                                     ? (IData)(__PVT__ia)
                                                     : (IData)(vlSelf->__PVT__k)))))] 
                                     & vlSelf->__PVT__mask));
    __PVT__vb = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, 
                                                   (0x1ffU 
                                                    & __VdfgTmp_h41a48239__0))) 
                 & VL_LTES_III(9, (0x1ffU & __VdfgTmp_h41a48239__0), 
                               (0x1ffU & ((0x3fU & 
                                           (0x20U >> (IData)(vlSelf->__PVT__lw_r))) 
                                          - (IData)(1U)))));
    vlSelf->d_wdata = (((IData)(__PVT__shx) ? (0U == 
                                               (0x1fU 
                                                & (vlSelf->__PVT__ir 
                                                   >> 0xfU)))
                         : (0U == (0x1fU & (vlSelf->__PVT__ir 
                                            >> 0x14U))))
                        ? 0U : (vlSymsp->TOP.tb_sys3__DOT__dut__DOT__slot__BRA__28__KET____DOT__rf
                                [((0x3e0U & (((IData)(__PVT__shx)
                                               ? (vlSelf->__PVT__ir 
                                                  >> 0xfU)
                                               : (vlSelf->__PVT__ir 
                                                  >> 0x14U)) 
                                             << 5U)) 
                                  | (0x1fU & ((2U == (IData)(vlSelf->__PVT__state))
                                               ? (IData)(vlSelf->__PVT__j)
                                               : ((IData)(__PVT__shx)
                                                   ? __VdfgTmp_h41a48239__0
                                                   : (IData)(vlSelf->__PVT__k)))))] 
                                & vlSelf->__PVT__mask));
    __PVT__X = vlSelf->__PVT__a_val;
    __PVT__Yr = (((0x33U == (0x7fU & vlSelf->__PVT__ir)) 
                  | (0x63U == (0x7fU & vlSelf->__PVT__ir)))
                  ? vlSelf->d_wdata : __PVT__imm_d);
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if ((0x37U != (0x7fU & vlSelf->__PVT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->__PVT__ir))) {
                if ((0x6fU != (0x7fU & vlSelf->__PVT__ir))) {
                    if (((IData)((0x40000033U == (0x4000707fU 
                                                  & vlSelf->__PVT__ir))) 
                         | (IData)(vlSelf->__PVT__is_cmp))) {
                        __PVT__inv = 1U;
                    }
                }
            }
        }
        if (vlSelf->__PVT__is_shift) {
            vlSelf->__PVT__we = 1U;
        } else if (__VdfgExtracted_h62388771__0) {
            vlSelf->__PVT__we = 1U;
        } else if (((~ (IData)(vlSelf->__PVT__is_cmp)) 
                    & (IData)(__VdfgTmp_h18c46dac__0))) {
            vlSelf->__PVT__we = 1U;
        }
        if ((0x37U == (0x7fU & vlSelf->__PVT__ir))) {
            __PVT__X = 0U;
        } else if ((0x17U == (0x7fU & vlSelf->__PVT__ir))) {
            __PVT__X = __PVT__pc_d;
        } else if ((0x6fU == (0x7fU & vlSelf->__PVT__ir))) {
            __PVT__X = __PVT__pc_d;
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        if ((3U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__we = 1U;
        } else if (vlSelf->__PVT__is_slt) {
            vlSelf->__PVT__we = 1U;
        } else if ((0x67U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__we = 1U;
        }
        __PVT__X = __PVT__pc_d;
    } else if ((5U == (IData)(vlSelf->__PVT__state))) {
        __PVT__X = __PVT__pc_d;
    }
    vlSelf->__PVT__xsh = VL_SHIFTR_III(32,32,6, __PVT__X, 
                                       (0x3fU & (((IData)(1U) 
                                                  << (IData)(vlSelf->__PVT__lw_r)) 
                                                 - (IData)(1U))));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if ((0x37U != (0x7fU & vlSelf->__PVT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->__PVT__ir))) {
                if ((0x6fU == (0x7fU & vlSelf->__PVT__ir))) {
                    __PVT__Yr = __PVT__c4_d;
                }
            }
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        __PVT__Yr = __PVT__c4_d;
    } else if ((5U == (IData)(vlSelf->__PVT__state))) {
        __PVT__Yr = (((0x6fU == (0x7fU & vlSelf->__PVT__ir)) 
                      | ((0x63U == (0x7fU & vlSelf->__PVT__ir)) 
                         & (IData)(__PVT__cond))) ? __PVT__imm_d
                      : __PVT__c4_d);
    }
    vlSelf->__PVT__ysh = VL_SHIFTR_III(32,32,6, __PVT__Yr, 
                                       (0x3fU & (((IData)(1U) 
                                                  << (IData)(vlSelf->__PVT__lw_r)) 
                                                 - (IData)(1U))));
    __PVT__sum_full = (0x1ffffffffULL & ((QData)((IData)(__PVT__X)) 
                                         + ((QData)((IData)(
                                                            ((IData)(__PVT__inv)
                                                              ? 
                                                             ((~ __PVT__Yr) 
                                                              & vlSelf->__PVT__mask)
                                                              : __PVT__Yr))) 
                                            + (QData)((IData)(
                                                              ((0U 
                                                                == (IData)(vlSelf->__PVT__k))
                                                                ? (IData)(__PVT__inv)
                                                                : (IData)(vlSelf->__PVT__cy)))))));
    vlSelf->__PVT__cout = (1U & (IData)((0x1ffffffffULL 
                                         & (__PVT__sum_full 
                                            >> (0x3fU 
                                                & ((IData)(1U) 
                                                   << (IData)(vlSelf->__PVT__lw_r)))))));
    __PVT__sum_d = ((IData)(__PVT__sum_full) & vlSelf->__PVT__mask);
    vlSelf->__PVT__nz_n = (((0U != (IData)(vlSelf->__PVT__k)) 
                            & (IData)(vlSelf->__PVT__nz)) 
                           | (0U != __PVT__sum_d));
    vlSelf->__VdfgTmp_h7980eff3__0 = VL_SHIFTL_III(32,32,6, __PVT__sum_d, 
                                                   (0x3fU 
                                                    & ((IData)(0x20U) 
                                                       - 
                                                       ((IData)(1U) 
                                                        << (IData)(vlSelf->__PVT__lw_r)))));
    vlSelf->__PVT__wd = (((IData)(__VdfgTmp_h18c46dac__0) 
                          & ((4U == (7U & (vlSelf->__PVT__ir 
                                           >> 0xcU))) 
                             | ((6U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))) 
                                | (7U == (7U & (vlSelf->__PVT__ir 
                                                >> 0xcU))))))
                          ? ((4U == (7U & (vlSelf->__PVT__ir 
                                           >> 0xcU)))
                              ? (__PVT__X ^ __PVT__Yr)
                              : ((6U == (7U & (vlSelf->__PVT__ir 
                                               >> 0xcU)))
                                  ? (__PVT__X | __PVT__Yr)
                                  : (__PVT__X & __PVT__Yr)))
                          : __PVT__sum_d);
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if (vlSelf->__PVT__is_shift) {
            vlSelf->__PVT__wd = ((IData)(((((QData)((IData)(
                                                            ((IData)(vlSelf->__PVT__is_sll)
                                                              ? 
                                                             ((IData)(__PVT__va)
                                                               ? vlSelf->__PVT__a_val
                                                               : 0U)
                                                              : 
                                                             ((IData)(__PVT__vb)
                                                               ? vlSelf->d_wdata
                                                               : __PVT__fill)))) 
                                            << (0x3fU 
                                                & ((IData)(1U) 
                                                   << (IData)(vlSelf->__PVT__lw_r)))) 
                                           | (QData)((IData)(
                                                             ((IData)(vlSelf->__PVT__is_sll)
                                                               ? 
                                                              ((IData)(__PVT__vb)
                                                                ? vlSelf->d_wdata
                                                                : 0U)
                                                               : 
                                                              ((IData)(__PVT__va)
                                                                ? vlSelf->__PVT__a_val
                                                                : __PVT__fill))))) 
                                          >> (0x3fU 
                                              & ((IData)(vlSelf->__PVT__is_sll)
                                                  ? 
                                                 (((IData)(1U) 
                                                   << (IData)(vlSelf->__PVT__lw_r)) 
                                                  - (IData)(__VdfgTmp_h933689ae__0))
                                                  : (IData)(__VdfgTmp_h933689ae__0))))) 
                                 & vlSelf->__PVT__mask);
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        if ((3U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__wd = (vlSymsp->TOP.tb_sys3__DOT__dut__DOT__slot__BRA__28__KET____DOT__dm
                                 [(0x7fffU & (IData)(vlSelf->d_addr))] 
                                 & vlSelf->__PVT__mask);
        } else if (vlSelf->__PVT__is_slt) {
            vlSelf->__PVT__wd = 0U;
            vlSelf->__PVT__wd = ((0xfffffffeU & vlSelf->__PVT__wd) 
                                 | ((0U == (IData)(vlSelf->__PVT__k)) 
                                    & ((2U == (7U & 
                                               (vlSelf->__PVT__ir 
                                                >> 0xcU)))
                                        ? (IData)(vlSelf->__PVT__f_lt)
                                        : (IData)(vlSelf->__PVT__f_ltu))));
        } else if ((0x67U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__wd = __PVT__sum_d;
        }
    }
    vlSelf->__PVT__addr_ins = (VL_SHIFTR_III(32,32,6, vlSelf->__PVT__addr, 
                                             (0x3fU 
                                              & ((IData)(1U) 
                                                 << (IData)(vlSelf->__PVT__lw_r)))) 
                               | vlSelf->__VdfgTmp_h7980eff3__0);
}

VL_INLINE_OPT void Vtb_sys3_uc_core_rw___nba_sequent__TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core__0(Vtb_sys3_uc_core_rw* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_sys3__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+          Vtb_sys3_uc_core_rw___nba_sequent__TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core__0\n"); );
    // Init
    CData/*0:0*/ __PVT__shx;
    __PVT__shx = 0;
    IData/*31:0*/ __PVT__pc_d;
    __PVT__pc_d = 0;
    IData/*31:0*/ __PVT__imm_d;
    __PVT__imm_d = 0;
    IData/*31:0*/ __PVT__c4_d;
    __PVT__c4_d = 0;
    SData/*8:0*/ __PVT__qs;
    __PVT__qs = 0;
    SData/*8:0*/ __PVT__ia;
    __PVT__ia = 0;
    CData/*0:0*/ __PVT__va;
    __PVT__va = 0;
    CData/*0:0*/ __PVT__vb;
    __PVT__vb = 0;
    IData/*31:0*/ __PVT__fill;
    __PVT__fill = 0;
    IData/*31:0*/ __PVT__X;
    __PVT__X = 0;
    IData/*31:0*/ __PVT__Yr;
    __PVT__Yr = 0;
    CData/*0:0*/ __PVT__inv;
    __PVT__inv = 0;
    QData/*32:0*/ __PVT__sum_full;
    __PVT__sum_full = 0;
    IData/*31:0*/ __PVT__sum_d;
    __PVT__sum_d = 0;
    CData/*0:0*/ __PVT__cond;
    __PVT__cond = 0;
    CData/*0:0*/ __VdfgExtracted_h62388771__0;
    __VdfgExtracted_h62388771__0 = 0;
    IData/*31:0*/ __VdfgTmp_h41a48239__0;
    __VdfgTmp_h41a48239__0 = 0;
    CData/*0:0*/ __VdfgTmp_h2cd83c5b__0;
    __VdfgTmp_h2cd83c5b__0 = 0;
    CData/*0:0*/ __VdfgTmp_he83b8d53__0;
    __VdfgTmp_he83b8d53__0 = 0;
    CData/*0:0*/ __VdfgTmp_h18c46dac__0;
    __VdfgTmp_h18c46dac__0 = 0;
    CData/*0:0*/ __VdfgTmp_hd9b60348__0;
    __VdfgTmp_hd9b60348__0 = 0;
    CData/*5:0*/ __VdfgTmp_h933689ae__0;
    __VdfgTmp_h933689ae__0 = 0;
    CData/*5:0*/ __Vtableidx30;
    __Vtableidx30 = 0;
    CData/*2:0*/ __Vdly__state;
    __Vdly__state = 0;
    IData/*31:0*/ __Vdly__addr;
    __Vdly__addr = 0;
    IData/*31:0*/ __Vdly__shamt_w;
    __Vdly__shamt_w = 0;
    CData/*4:0*/ __Vdly__k;
    __Vdly__k = 0;
    CData/*2:0*/ __Vdly__j;
    __Vdly__j = 0;
    // Body
    __Vdly__addr = vlSelf->__PVT__addr;
    __Vdly__j = vlSelf->__PVT__j;
    __Vdly__shamt_w = vlSelf->__PVT__shamt_w;
    __Vdly__state = vlSelf->__PVT__state;
    __Vdly__k = vlSelf->__PVT__k;
    if (vlSymsp->TOP.tb_sys3__DOT__rst) {
        __Vdly__state = 6U;
        vlSelf->__PVT__pc = 0U;
        vlSelf->__PVT__ir = 0U;
        __Vdly__addr = 0U;
        vlSelf->__PVT__imm_sr = 0U;
        __Vdly__shamt_w = 0U;
        __Vdly__k = 0U;
        __Vdly__j = 0U;
        vlSelf->__PVT__lw_r = 0U;
        vlSelf->__PVT__cy = 0U;
        vlSelf->__PVT__nz = 0U;
        vlSelf->__PVT__f_eq = 0U;
        vlSelf->__PVT__f_lt = 0U;
        vlSelf->__PVT__f_ltu = 0U;
        vlSelf->__PVT__sgn = 0U;
        vlSelf->__PVT__halted_r = 1U;
        vlSelf->__PVT__trap_r = 0U;
    } else if (((vlSymsp->TOP.tb_sys3__DOT__dut__DOT__start_v 
                 >> 0x1dU) & (6U == (IData)(vlSelf->__PVT__state)))) {
        vlSelf->__PVT__pc = vlSymsp->TOP.tb_sys3__DOT__dut__DOT__launch_entry;
        vlSelf->__PVT__lw_r = vlSymsp->TOP.tb_sys3__DOT__dut__DOT__launch_lw;
        __Vdly__k = 0U;
        vlSelf->__PVT__halted_r = 0U;
        vlSelf->__PVT__trap_r = 0U;
        __Vdly__state = 0U;
    } else if ((4U & (IData)(vlSelf->__PVT__state))) {
        if ((1U & (~ ((IData)(vlSelf->__PVT__state) 
                      >> 1U)))) {
            if ((1U & (IData)(vlSelf->__PVT__state))) {
                if ((0x67U == (IData)(vlSelf->__PVT__opc))) {
                    vlSelf->__PVT__pc = (0xfffffffeU 
                                         & vlSelf->__PVT__addr);
                    __Vdly__state = 0U;
                } else {
                    vlSelf->__PVT__pc = (vlSelf->__VdfgTmp_he4828306__0 
                                         | vlSelf->__VdfgTmp_h7980eff3__0);
                    vlSelf->__PVT__imm_sr = vlSelf->__PVT__imm_rot;
                    vlSelf->__PVT__cy = vlSelf->__PVT__cout;
                    if (vlSelf->__PVT__last_up) {
                        __Vdly__k = 0U;
                        __Vdly__state = 0U;
                    } else {
                        __Vdly__k = (0x1fU & ((IData)(1U) 
                                              + (IData)(vlSelf->__PVT__k)));
                    }
                }
            } else {
                vlSelf->__PVT__cy = vlSelf->__PVT__cout;
                vlSelf->__PVT__pc = vlSelf->__PVT__pc_rot;
                if (vlSelf->__PVT__last_up) {
                    __Vdly__k = 0U;
                    __Vdly__state = 5U;
                } else {
                    __Vdly__k = (0x1fU & ((IData)(1U) 
                                          + (IData)(vlSelf->__PVT__k)));
                }
            }
        }
    } else if ((2U & (IData)(vlSelf->__PVT__state))) {
        if ((1U & (IData)(vlSelf->__PVT__state))) {
            vlSelf->__PVT__cy = vlSelf->__PVT__cout;
            if (vlSelf->__PVT__is_cmp) {
                vlSelf->__PVT__nz = vlSelf->__PVT__nz_n;
                if (vlSelf->__PVT__last_up) {
                    vlSelf->__PVT__f_eq = (1U & (~ (IData)(vlSelf->__PVT__nz_n)));
                    vlSelf->__PVT__f_ltu = (1U & (~ (IData)(vlSelf->__PVT__cout)));
                    vlSelf->__PVT__f_lt = (1U & (((1U 
                                                   & vlSelf->__PVT__xsh) 
                                                  != 
                                                  (1U 
                                                   & vlSelf->__PVT__ysh))
                                                  ? vlSelf->__PVT__xsh
                                                  : 
                                                 (~ (IData)(vlSelf->__PVT__cout))));
                }
            }
            if ((((3U == (IData)(vlSelf->__PVT__opc)) 
                  | (0x23U == (IData)(vlSelf->__PVT__opc))) 
                 | (0x67U == (IData)(vlSelf->__PVT__opc)))) {
                __Vdly__addr = vlSelf->__PVT__addr_ins;
            }
            vlSelf->__PVT__pc = vlSelf->__PVT__pc_rot;
            vlSelf->__PVT__imm_sr = vlSelf->__PVT__imm_rot;
            if (vlSelf->__PVT__exec_done) {
                __Vdly__k = 0U;
                __Vdly__state = (((((3U == (IData)(vlSelf->__PVT__opc)) 
                                    | (0x23U == (IData)(vlSelf->__PVT__opc))) 
                                   | (0x67U == (IData)(vlSelf->__PVT__opc))) 
                                  | (IData)(vlSelf->__PVT__is_slt))
                                  ? 4U : 5U);
            } else {
                __Vdly__k = (0x1fU & ((IData)(vlSelf->__PVT__is_sll)
                                       ? ((IData)(vlSelf->__PVT__k) 
                                          - (IData)(1U))
                                       : ((IData)(1U) 
                                          + (IData)(vlSelf->__PVT__k))));
            }
        } else {
            if ((0x33U == (IData)(vlSelf->__PVT__opc))) {
                __Vdly__shamt_w = ((vlSelf->__PVT__shamt_w 
                                    & (~ VL_SHIFTL_III(32,32,6, vlSelf->__PVT__mask, (IData)(vlSelf->__PVT__jw)))) 
                                   | VL_SHIFTL_III(32,32,6, vlSelf->d_wdata, (IData)(vlSelf->__PVT__jw)));
            }
            vlSelf->__PVT__sgn = (1U & (vlSelf->__PVT__a_val 
                                        >> (0x1fU & (IData)(vlSelf->__PVT__wm1))));
            if (((IData)(vlSelf->__PVT__j) == ((0x33U 
                                                == (IData)(vlSelf->__PVT__opc))
                                                ? (IData)(vlSelf->__PVT__mlast)
                                                : 0U))) {
                __Vdly__state = 3U;
                __Vdly__k = ((IData)(vlSelf->__PVT__is_sll)
                              ? (0x1fU & ((IData)(vlSelf->__PVT__nd) 
                                          - (IData)(1U)))
                              : 0U);
            } else {
                __Vdly__j = (7U & ((IData)(1U) + (IData)(vlSelf->__PVT__j)));
            }
        }
    } else if ((1U & (IData)(vlSelf->__PVT__state))) {
        __Vdly__j = 0U;
        vlSelf->__PVT__imm_sr = vlSelf->__PVT__imm;
        __Vdly__shamt_w = ((IData)(vlSelf->__PVT__sh_i)
                            ? (IData)(vlSelf->__PVT__rs2)
                            : 0U);
        if (vlSelf->__PVT__bad) {
            vlSelf->__PVT__trap_r = 1U;
            vlSelf->__PVT__halted_r = 1U;
            __Vdly__state = 6U;
        } else if (vlSelf->__PVT__is_sys) {
            vlSelf->__PVT__halted_r = 1U;
            __Vdly__state = 6U;
        } else if (vlSelf->__PVT__is_shift) {
            __Vdly__state = 2U;
        } else {
            __Vdly__k = 0U;
            __Vdly__state = 3U;
        }
    } else {
        vlSelf->__PVT__ir = vlSymsp->TOP.tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__id;
        __Vdly__state = 1U;
    }
    vlSelf->__PVT__addr = __Vdly__addr;
    vlSelf->__PVT__j = __Vdly__j;
    vlSelf->__PVT__shamt_w = __Vdly__shamt_w;
    vlSelf->__PVT__state = __Vdly__state;
    vlSelf->__PVT__k = __Vdly__k;
    vlSelf->d_addr = (((QData)((IData)((vlSelf->__PVT__addr 
                                        >> 2U))) << 5U) 
                      | (QData)((IData)(vlSelf->__PVT__k)));
    vlSelf->__PVT__wm1 = (0x3fU & (((IData)(1U) << (IData)(vlSelf->__PVT__lw_r)) 
                                   - (IData)(1U)));
    vlSelf->__PVT__mlast = (0x3fU & (VL_DIV_III(6, 
                                                (0x3fU 
                                                 & ((IData)(4U) 
                                                    + 
                                                    ((IData)(1U) 
                                                     << (IData)(vlSelf->__PVT__lw_r)))), 
                                                (0x3fU 
                                                 & ((IData)(1U) 
                                                    << (IData)(vlSelf->__PVT__lw_r)))) 
                                     - (IData)(1U)));
    vlSelf->__PVT__nd = (0x3fU & (0x20U >> (IData)(vlSelf->__PVT__lw_r)));
    vlSelf->__PVT__jw = (0x3fU & ((IData)(vlSelf->__PVT__j) 
                                  * (0x3fU & ((IData)(1U) 
                                              << (IData)(vlSelf->__PVT__lw_r)))));
    vlSelf->__PVT__imm_rot = (VL_SHIFTR_III(32,32,6, vlSelf->__PVT__imm_sr, 
                                            (0x3fU 
                                             & ((IData)(1U) 
                                                << (IData)(vlSelf->__PVT__lw_r)))) 
                              | VL_SHIFTL_III(32,32,6, vlSelf->__PVT__imm_sr, 
                                              (0x3fU 
                                               & ((IData)(0x20U) 
                                                  - 
                                                  ((IData)(1U) 
                                                   << (IData)(vlSelf->__PVT__lw_r))))));
    vlSelf->__PVT__last_up = ((IData)(vlSelf->__PVT__k) 
                              == (0x1fU & ((0x3fU & 
                                            (0x20U 
                                             >> (IData)(vlSelf->__PVT__lw_r))) 
                                           - (IData)(1U))));
    vlSelf->__VdfgTmp_he4828306__0 = VL_SHIFTR_III(32,32,6, vlSelf->__PVT__pc, 
                                                   (0x3fU 
                                                    & ((IData)(1U) 
                                                       << (IData)(vlSelf->__PVT__lw_r))));
    __VdfgTmp_h933689ae__0 = (0x1fU & (vlSelf->__PVT__shamt_w 
                                       & ((0x3fU & 
                                           ((IData)(1U) 
                                            << (IData)(vlSelf->__PVT__lw_r))) 
                                          - (IData)(1U))));
    __PVT__qs = (0x1fU & ((0x1fU & vlSelf->__PVT__shamt_w) 
                          >> (IData)(vlSelf->__PVT__lw_r)));
    vlSelf->__PVT__mask = ((5U == (IData)(vlSelf->__PVT__lw_r))
                            ? 0xffffffffU : (VL_SHIFTL_III(32,32,6, (IData)(1U), 
                                                           (0x3fU 
                                                            & ((IData)(1U) 
                                                               << (IData)(vlSelf->__PVT__lw_r)))) 
                                             - (IData)(1U)));
    vlSelf->__PVT__rs2 = (0x1fU & (vlSelf->__PVT__ir 
                                   >> 0x14U));
    vlSelf->__PVT__is_sys = (0x73U == (0x7fU & vlSelf->__PVT__ir));
    vlSelf->__PVT__opc = (0x7fU & vlSelf->__PVT__ir);
    __VdfgTmp_h2cd83c5b__0 = ((0x37U == (0x7fU & vlSelf->__PVT__ir)) 
                              | (0x17U == (0x7fU & vlSelf->__PVT__ir)));
    __Vtableidx30 = (((IData)(vlSelf->__PVT__f_eq) 
                      << 5U) | (((IData)(vlSelf->__PVT__f_lt) 
                                 << 4U) | (((IData)(vlSelf->__PVT__f_ltu) 
                                            << 3U) 
                                           | (7U & 
                                              (vlSelf->__PVT__ir 
                                               >> 0xcU)))));
    __PVT__cond = Vtb_sys3__ConstPool__TABLE_h2a0441a0_0
        [__Vtableidx30];
    __VdfgTmp_hd9b60348__0 = ((2U == (7U & (vlSelf->__PVT__ir 
                                            >> 0xcU))) 
                              | (3U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))));
    __VdfgTmp_h18c46dac__0 = ((0x13U == (0x7fU & vlSelf->__PVT__ir)) 
                              | (0x33U == (0x7fU & vlSelf->__PVT__ir)));
    __VdfgTmp_he83b8d53__0 = ((1U == (7U & (vlSelf->__PVT__ir 
                                            >> 0xcU))) 
                              | (5U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))));
    vlSelf->__PVT__pc_rot = (vlSelf->__VdfgTmp_he4828306__0 
                             | VL_SHIFTL_III(32,32,6, vlSelf->__PVT__pc, 
                                             (0x3fU 
                                              & ((IData)(0x20U) 
                                                 - 
                                                 ((IData)(1U) 
                                                  << (IData)(vlSelf->__PVT__lw_r))))));
    __PVT__pc_d = (vlSelf->__PVT__pc & vlSelf->__PVT__mask);
    __PVT__imm_d = (vlSelf->__PVT__imm_sr & vlSelf->__PVT__mask);
    __PVT__c4_d = (VL_SHIFTR_III(32,32,6, 4U, (0x3fU 
                                               & ((IData)(vlSelf->__PVT__k) 
                                                  * 
                                                  (0x3fU 
                                                   & ((IData)(1U) 
                                                      << (IData)(vlSelf->__PVT__lw_r)))))) 
                   & vlSelf->__PVT__mask);
    vlSelf->__PVT__imm = ((IData)(__VdfgTmp_h2cd83c5b__0)
                           ? (0xfffff000U & vlSelf->__PVT__ir)
                           : ((0x6fU == (0x7fU & vlSelf->__PVT__ir))
                               ? (((- (IData)((vlSelf->__PVT__ir 
                                               >> 0x1fU))) 
                                   << 0x15U) | ((0x100000U 
                                                 & (vlSelf->__PVT__ir 
                                                    >> 0xbU)) 
                                                | ((0xff000U 
                                                    & vlSelf->__PVT__ir) 
                                                   | ((0x800U 
                                                       & (vlSelf->__PVT__ir 
                                                          >> 9U)) 
                                                      | (0x7feU 
                                                         & (vlSelf->__PVT__ir 
                                                            >> 0x14U))))))
                               : ((0x63U == (0x7fU 
                                             & vlSelf->__PVT__ir))
                                   ? (((- (IData)((vlSelf->__PVT__ir 
                                                   >> 0x1fU))) 
                                       << 0xdU) | (
                                                   (0x1000U 
                                                    & (vlSelf->__PVT__ir 
                                                       >> 0x13U)) 
                                                   | ((0x800U 
                                                       & (vlSelf->__PVT__ir 
                                                          << 4U)) 
                                                      | ((0x7e0U 
                                                          & (vlSelf->__PVT__ir 
                                                             >> 0x14U)) 
                                                         | (0x1eU 
                                                            & (vlSelf->__PVT__ir 
                                                               >> 7U))))))
                                   : ((0x23U == (0x7fU 
                                                 & vlSelf->__PVT__ir))
                                       ? (((- (IData)(
                                                      (vlSelf->__PVT__ir 
                                                       >> 0x1fU))) 
                                           << 0xcU) 
                                          | ((0xfe0U 
                                              & (vlSelf->__PVT__ir 
                                                 >> 0x14U)) 
                                             | (0x1fU 
                                                & (vlSelf->__PVT__ir 
                                                   >> 7U))))
                                       : (((- (IData)(
                                                      (vlSelf->__PVT__ir 
                                                       >> 0x1fU))) 
                                           << 0xcU) 
                                          | (vlSelf->__PVT__ir 
                                             >> 0x14U))))));
    __VdfgExtracted_h62388771__0 = ((IData)(__VdfgTmp_h2cd83c5b__0) 
                                    | (0x6fU == (0x7fU 
                                                 & vlSelf->__PVT__ir)));
    vlSelf->__PVT__is_cmp = ((0x63U == (0x7fU & vlSelf->__PVT__ir)) 
                             | ((IData)(__VdfgTmp_h18c46dac__0) 
                                & (IData)(__VdfgTmp_hd9b60348__0)));
    vlSelf->__PVT__sh_i = ((0x13U == (0x7fU & vlSelf->__PVT__ir)) 
                           & (IData)(__VdfgTmp_he83b8d53__0));
    vlSelf->__PVT__bad = (1U & ((~ ((IData)(__VdfgExtracted_h62388771__0) 
                                    | ((0x67U == (0x7fU 
                                                  & vlSelf->__PVT__ir)) 
                                       | ((0x63U == 
                                           (0x7fU & vlSelf->__PVT__ir)) 
                                          | ((3U == 
                                              (0x7fU 
                                               & vlSelf->__PVT__ir)) 
                                             | ((0x23U 
                                                 == 
                                                 (0x7fU 
                                                  & vlSelf->__PVT__ir)) 
                                                | ((0x13U 
                                                    == 
                                                    (0x7fU 
                                                     & vlSelf->__PVT__ir)) 
                                                   | ((0x33U 
                                                       == 
                                                       (0x7fU 
                                                        & vlSelf->__PVT__ir)) 
                                                      | (0x73U 
                                                         == 
                                                         (0x7fU 
                                                          & vlSelf->__PVT__ir)))))))))) 
                                | (((0x67U == (0x7fU 
                                               & vlSelf->__PVT__ir)) 
                                    & (0U != (7U & 
                                              (vlSelf->__PVT__ir 
                                               >> 0xcU)))) 
                                   | (((0x63U == (0x7fU 
                                                  & vlSelf->__PVT__ir)) 
                                       & (IData)(__VdfgTmp_hd9b60348__0)) 
                                      | ((((3U == (0x7fU 
                                                   & vlSelf->__PVT__ir)) 
                                           | (0x23U 
                                              == (0x7fU 
                                                  & vlSelf->__PVT__ir))) 
                                          & (2U != 
                                             (7U & 
                                              (vlSelf->__PVT__ir 
                                               >> 0xcU)))) 
                                         | ((IData)(
                                                    ((0x1013U 
                                                      == 
                                                      (0x707fU 
                                                       & vlSelf->__PVT__ir)) 
                                                     & (0U 
                                                        != 
                                                        (vlSelf->__PVT__ir 
                                                         >> 0x19U)))) 
                                            | ((IData)(
                                                       ((0x5013U 
                                                         == 
                                                         (0x707fU 
                                                          & vlSelf->__PVT__ir)) 
                                                        & ((0U 
                                                            != 
                                                            (vlSelf->__PVT__ir 
                                                             >> 0x19U)) 
                                                           & (0x20U 
                                                              != 
                                                              (vlSelf->__PVT__ir 
                                                               >> 0x19U))))) 
                                               | ((0x33U 
                                                   == 
                                                   (0x7fU 
                                                    & vlSelf->__PVT__ir)) 
                                                  & ((~ 
                                                      ((0x20U 
                                                        == 
                                                        (vlSelf->__PVT__ir 
                                                         >> 0x19U)) 
                                                       & ((0U 
                                                           == 
                                                           (7U 
                                                            & (vlSelf->__PVT__ir 
                                                               >> 0xcU))) 
                                                          | (5U 
                                                             == 
                                                             (7U 
                                                              & (vlSelf->__PVT__ir 
                                                                 >> 0xcU)))))) 
                                                     & (0U 
                                                        != 
                                                        (vlSelf->__PVT__ir 
                                                         >> 0x19U)))))))))));
    vlSelf->__PVT__is_slt = ((0x63U != (0x7fU & vlSelf->__PVT__ir)) 
                             & (IData)(vlSelf->__PVT__is_cmp));
    __PVT__inv = 0U;
    vlSelf->__PVT__is_shift = ((IData)(vlSelf->__PVT__sh_i) 
                               | ((0x33U == (0x7fU 
                                             & vlSelf->__PVT__ir)) 
                                  & (IData)(__VdfgTmp_he83b8d53__0)));
    vlSelf->__PVT__we = 0U;
    __PVT__fill = (((IData)(vlSelf->__PVT__is_shift) 
                    & (IData)(((0x40005000U == (0x40007000U 
                                                & vlSelf->__PVT__ir)) 
                               & (IData)(vlSelf->__PVT__sgn))))
                    ? vlSelf->__PVT__mask : 0U);
    __PVT__shx = ((3U == (IData)(vlSelf->__PVT__state)) 
                  & (IData)(vlSelf->__PVT__is_shift));
    vlSelf->__PVT__is_sll = ((IData)(vlSelf->__PVT__is_shift) 
                             & (0x1000U == (0x7000U 
                                            & vlSelf->__PVT__ir)));
    if (vlSelf->__PVT__is_sll) {
        vlSelf->__PVT__exec_done = (0U == (IData)(vlSelf->__PVT__k));
        __PVT__ia = (0x1ffU & ((IData)(vlSelf->__PVT__k) 
                               - (IData)(__PVT__qs)));
        __VdfgTmp_h41a48239__0 = ((VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__k)) 
                                   - VL_EXTENDS_II(32,9, (IData)(__PVT__qs))) 
                                  - (IData)(1U));
    } else {
        vlSelf->__PVT__exec_done = vlSelf->__PVT__last_up;
        __PVT__ia = (0x1ffU & ((IData)(vlSelf->__PVT__k) 
                               + (IData)(__PVT__qs)));
        __VdfgTmp_h41a48239__0 = ((IData)(1U) + (VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__k)) 
                                                 + 
                                                 VL_EXTENDS_II(32,9, (IData)(__PVT__qs))));
    }
    __PVT__va = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, (IData)(__PVT__ia))) 
                 & VL_LTES_III(9, (IData)(__PVT__ia), 
                               (0x1ffU & ((0x3fU & 
                                           (0x20U >> (IData)(vlSelf->__PVT__lw_r))) 
                                          - (IData)(1U)))));
    vlSelf->__PVT__a_val = ((0U == (0x1fU & (vlSelf->__PVT__ir 
                                             >> 0xfU)))
                             ? 0U : (vlSymsp->TOP.tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__rf
                                     [((0x3e0U & (vlSelf->__PVT__ir 
                                                  >> 0xaU)) 
                                       | (0x1fU & (
                                                   (2U 
                                                    == (IData)(vlSelf->__PVT__state))
                                                    ? 
                                                   ((0x3fU 
                                                     & (0x20U 
                                                        >> (IData)(vlSelf->__PVT__lw_r))) 
                                                    - (IData)(1U))
                                                    : 
                                                   ((IData)(__PVT__shx)
                                                     ? (IData)(__PVT__ia)
                                                     : (IData)(vlSelf->__PVT__k)))))] 
                                     & vlSelf->__PVT__mask));
    __PVT__vb = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, 
                                                   (0x1ffU 
                                                    & __VdfgTmp_h41a48239__0))) 
                 & VL_LTES_III(9, (0x1ffU & __VdfgTmp_h41a48239__0), 
                               (0x1ffU & ((0x3fU & 
                                           (0x20U >> (IData)(vlSelf->__PVT__lw_r))) 
                                          - (IData)(1U)))));
    vlSelf->d_wdata = (((IData)(__PVT__shx) ? (0U == 
                                               (0x1fU 
                                                & (vlSelf->__PVT__ir 
                                                   >> 0xfU)))
                         : (0U == (0x1fU & (vlSelf->__PVT__ir 
                                            >> 0x14U))))
                        ? 0U : (vlSymsp->TOP.tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__rf
                                [((0x3e0U & (((IData)(__PVT__shx)
                                               ? (vlSelf->__PVT__ir 
                                                  >> 0xfU)
                                               : (vlSelf->__PVT__ir 
                                                  >> 0x14U)) 
                                             << 5U)) 
                                  | (0x1fU & ((2U == (IData)(vlSelf->__PVT__state))
                                               ? (IData)(vlSelf->__PVT__j)
                                               : ((IData)(__PVT__shx)
                                                   ? __VdfgTmp_h41a48239__0
                                                   : (IData)(vlSelf->__PVT__k)))))] 
                                & vlSelf->__PVT__mask));
    __PVT__X = vlSelf->__PVT__a_val;
    __PVT__Yr = (((0x33U == (0x7fU & vlSelf->__PVT__ir)) 
                  | (0x63U == (0x7fU & vlSelf->__PVT__ir)))
                  ? vlSelf->d_wdata : __PVT__imm_d);
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if ((0x37U != (0x7fU & vlSelf->__PVT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->__PVT__ir))) {
                if ((0x6fU != (0x7fU & vlSelf->__PVT__ir))) {
                    if (((IData)((0x40000033U == (0x4000707fU 
                                                  & vlSelf->__PVT__ir))) 
                         | (IData)(vlSelf->__PVT__is_cmp))) {
                        __PVT__inv = 1U;
                    }
                }
            }
        }
        if (vlSelf->__PVT__is_shift) {
            vlSelf->__PVT__we = 1U;
        } else if (__VdfgExtracted_h62388771__0) {
            vlSelf->__PVT__we = 1U;
        } else if (((~ (IData)(vlSelf->__PVT__is_cmp)) 
                    & (IData)(__VdfgTmp_h18c46dac__0))) {
            vlSelf->__PVT__we = 1U;
        }
        if ((0x37U == (0x7fU & vlSelf->__PVT__ir))) {
            __PVT__X = 0U;
        } else if ((0x17U == (0x7fU & vlSelf->__PVT__ir))) {
            __PVT__X = __PVT__pc_d;
        } else if ((0x6fU == (0x7fU & vlSelf->__PVT__ir))) {
            __PVT__X = __PVT__pc_d;
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        if ((3U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__we = 1U;
        } else if (vlSelf->__PVT__is_slt) {
            vlSelf->__PVT__we = 1U;
        } else if ((0x67U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__we = 1U;
        }
        __PVT__X = __PVT__pc_d;
    } else if ((5U == (IData)(vlSelf->__PVT__state))) {
        __PVT__X = __PVT__pc_d;
    }
    vlSelf->__PVT__xsh = VL_SHIFTR_III(32,32,6, __PVT__X, 
                                       (0x3fU & (((IData)(1U) 
                                                  << (IData)(vlSelf->__PVT__lw_r)) 
                                                 - (IData)(1U))));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if ((0x37U != (0x7fU & vlSelf->__PVT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->__PVT__ir))) {
                if ((0x6fU == (0x7fU & vlSelf->__PVT__ir))) {
                    __PVT__Yr = __PVT__c4_d;
                }
            }
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        __PVT__Yr = __PVT__c4_d;
    } else if ((5U == (IData)(vlSelf->__PVT__state))) {
        __PVT__Yr = (((0x6fU == (0x7fU & vlSelf->__PVT__ir)) 
                      | ((0x63U == (0x7fU & vlSelf->__PVT__ir)) 
                         & (IData)(__PVT__cond))) ? __PVT__imm_d
                      : __PVT__c4_d);
    }
    vlSelf->__PVT__ysh = VL_SHIFTR_III(32,32,6, __PVT__Yr, 
                                       (0x3fU & (((IData)(1U) 
                                                  << (IData)(vlSelf->__PVT__lw_r)) 
                                                 - (IData)(1U))));
    __PVT__sum_full = (0x1ffffffffULL & ((QData)((IData)(__PVT__X)) 
                                         + ((QData)((IData)(
                                                            ((IData)(__PVT__inv)
                                                              ? 
                                                             ((~ __PVT__Yr) 
                                                              & vlSelf->__PVT__mask)
                                                              : __PVT__Yr))) 
                                            + (QData)((IData)(
                                                              ((0U 
                                                                == (IData)(vlSelf->__PVT__k))
                                                                ? (IData)(__PVT__inv)
                                                                : (IData)(vlSelf->__PVT__cy)))))));
    vlSelf->__PVT__cout = (1U & (IData)((0x1ffffffffULL 
                                         & (__PVT__sum_full 
                                            >> (0x3fU 
                                                & ((IData)(1U) 
                                                   << (IData)(vlSelf->__PVT__lw_r)))))));
    __PVT__sum_d = ((IData)(__PVT__sum_full) & vlSelf->__PVT__mask);
    vlSelf->__PVT__nz_n = (((0U != (IData)(vlSelf->__PVT__k)) 
                            & (IData)(vlSelf->__PVT__nz)) 
                           | (0U != __PVT__sum_d));
    vlSelf->__VdfgTmp_h7980eff3__0 = VL_SHIFTL_III(32,32,6, __PVT__sum_d, 
                                                   (0x3fU 
                                                    & ((IData)(0x20U) 
                                                       - 
                                                       ((IData)(1U) 
                                                        << (IData)(vlSelf->__PVT__lw_r)))));
    vlSelf->__PVT__wd = (((IData)(__VdfgTmp_h18c46dac__0) 
                          & ((4U == (7U & (vlSelf->__PVT__ir 
                                           >> 0xcU))) 
                             | ((6U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))) 
                                | (7U == (7U & (vlSelf->__PVT__ir 
                                                >> 0xcU))))))
                          ? ((4U == (7U & (vlSelf->__PVT__ir 
                                           >> 0xcU)))
                              ? (__PVT__X ^ __PVT__Yr)
                              : ((6U == (7U & (vlSelf->__PVT__ir 
                                               >> 0xcU)))
                                  ? (__PVT__X | __PVT__Yr)
                                  : (__PVT__X & __PVT__Yr)))
                          : __PVT__sum_d);
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if (vlSelf->__PVT__is_shift) {
            vlSelf->__PVT__wd = ((IData)(((((QData)((IData)(
                                                            ((IData)(vlSelf->__PVT__is_sll)
                                                              ? 
                                                             ((IData)(__PVT__va)
                                                               ? vlSelf->__PVT__a_val
                                                               : 0U)
                                                              : 
                                                             ((IData)(__PVT__vb)
                                                               ? vlSelf->d_wdata
                                                               : __PVT__fill)))) 
                                            << (0x3fU 
                                                & ((IData)(1U) 
                                                   << (IData)(vlSelf->__PVT__lw_r)))) 
                                           | (QData)((IData)(
                                                             ((IData)(vlSelf->__PVT__is_sll)
                                                               ? 
                                                              ((IData)(__PVT__vb)
                                                                ? vlSelf->d_wdata
                                                                : 0U)
                                                               : 
                                                              ((IData)(__PVT__va)
                                                                ? vlSelf->__PVT__a_val
                                                                : __PVT__fill))))) 
                                          >> (0x3fU 
                                              & ((IData)(vlSelf->__PVT__is_sll)
                                                  ? 
                                                 (((IData)(1U) 
                                                   << (IData)(vlSelf->__PVT__lw_r)) 
                                                  - (IData)(__VdfgTmp_h933689ae__0))
                                                  : (IData)(__VdfgTmp_h933689ae__0))))) 
                                 & vlSelf->__PVT__mask);
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        if ((3U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__wd = (vlSymsp->TOP.tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__dm
                                 [(0x7fffU & (IData)(vlSelf->d_addr))] 
                                 & vlSelf->__PVT__mask);
        } else if (vlSelf->__PVT__is_slt) {
            vlSelf->__PVT__wd = 0U;
            vlSelf->__PVT__wd = ((0xfffffffeU & vlSelf->__PVT__wd) 
                                 | ((0U == (IData)(vlSelf->__PVT__k)) 
                                    & ((2U == (7U & 
                                               (vlSelf->__PVT__ir 
                                                >> 0xcU)))
                                        ? (IData)(vlSelf->__PVT__f_lt)
                                        : (IData)(vlSelf->__PVT__f_ltu))));
        } else if ((0x67U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__wd = __PVT__sum_d;
        }
    }
    vlSelf->__PVT__addr_ins = (VL_SHIFTR_III(32,32,6, vlSelf->__PVT__addr, 
                                             (0x3fU 
                                              & ((IData)(1U) 
                                                 << (IData)(vlSelf->__PVT__lw_r)))) 
                               | vlSelf->__VdfgTmp_h7980eff3__0);
}

VL_INLINE_OPT void Vtb_sys3_uc_core_rw___nba_sequent__TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core__0(Vtb_sys3_uc_core_rw* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_sys3__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+          Vtb_sys3_uc_core_rw___nba_sequent__TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core__0\n"); );
    // Init
    CData/*0:0*/ __PVT__shx;
    __PVT__shx = 0;
    IData/*31:0*/ __PVT__pc_d;
    __PVT__pc_d = 0;
    IData/*31:0*/ __PVT__imm_d;
    __PVT__imm_d = 0;
    IData/*31:0*/ __PVT__c4_d;
    __PVT__c4_d = 0;
    SData/*8:0*/ __PVT__qs;
    __PVT__qs = 0;
    SData/*8:0*/ __PVT__ia;
    __PVT__ia = 0;
    CData/*0:0*/ __PVT__va;
    __PVT__va = 0;
    CData/*0:0*/ __PVT__vb;
    __PVT__vb = 0;
    IData/*31:0*/ __PVT__fill;
    __PVT__fill = 0;
    IData/*31:0*/ __PVT__X;
    __PVT__X = 0;
    IData/*31:0*/ __PVT__Yr;
    __PVT__Yr = 0;
    CData/*0:0*/ __PVT__inv;
    __PVT__inv = 0;
    QData/*32:0*/ __PVT__sum_full;
    __PVT__sum_full = 0;
    IData/*31:0*/ __PVT__sum_d;
    __PVT__sum_d = 0;
    CData/*0:0*/ __PVT__cond;
    __PVT__cond = 0;
    CData/*0:0*/ __VdfgExtracted_h62388771__0;
    __VdfgExtracted_h62388771__0 = 0;
    IData/*31:0*/ __VdfgTmp_h41a48239__0;
    __VdfgTmp_h41a48239__0 = 0;
    CData/*0:0*/ __VdfgTmp_h2cd83c5b__0;
    __VdfgTmp_h2cd83c5b__0 = 0;
    CData/*0:0*/ __VdfgTmp_he83b8d53__0;
    __VdfgTmp_he83b8d53__0 = 0;
    CData/*0:0*/ __VdfgTmp_h18c46dac__0;
    __VdfgTmp_h18c46dac__0 = 0;
    CData/*0:0*/ __VdfgTmp_hd9b60348__0;
    __VdfgTmp_hd9b60348__0 = 0;
    CData/*5:0*/ __VdfgTmp_h933689ae__0;
    __VdfgTmp_h933689ae__0 = 0;
    CData/*5:0*/ __Vtableidx31;
    __Vtableidx31 = 0;
    CData/*2:0*/ __Vdly__state;
    __Vdly__state = 0;
    IData/*31:0*/ __Vdly__addr;
    __Vdly__addr = 0;
    IData/*31:0*/ __Vdly__shamt_w;
    __Vdly__shamt_w = 0;
    CData/*4:0*/ __Vdly__k;
    __Vdly__k = 0;
    CData/*2:0*/ __Vdly__j;
    __Vdly__j = 0;
    // Body
    __Vdly__addr = vlSelf->__PVT__addr;
    __Vdly__j = vlSelf->__PVT__j;
    __Vdly__shamt_w = vlSelf->__PVT__shamt_w;
    __Vdly__state = vlSelf->__PVT__state;
    __Vdly__k = vlSelf->__PVT__k;
    if (vlSymsp->TOP.tb_sys3__DOT__rst) {
        __Vdly__state = 6U;
        vlSelf->__PVT__pc = 0U;
        vlSelf->__PVT__ir = 0U;
        __Vdly__addr = 0U;
        vlSelf->__PVT__imm_sr = 0U;
        __Vdly__shamt_w = 0U;
        __Vdly__k = 0U;
        __Vdly__j = 0U;
        vlSelf->__PVT__lw_r = 0U;
        vlSelf->__PVT__cy = 0U;
        vlSelf->__PVT__nz = 0U;
        vlSelf->__PVT__f_eq = 0U;
        vlSelf->__PVT__f_lt = 0U;
        vlSelf->__PVT__f_ltu = 0U;
        vlSelf->__PVT__sgn = 0U;
        vlSelf->__PVT__halted_r = 1U;
        vlSelf->__PVT__trap_r = 0U;
    } else if (((vlSymsp->TOP.tb_sys3__DOT__dut__DOT__start_v 
                 >> 0x1eU) & (6U == (IData)(vlSelf->__PVT__state)))) {
        vlSelf->__PVT__pc = vlSymsp->TOP.tb_sys3__DOT__dut__DOT__launch_entry;
        vlSelf->__PVT__lw_r = vlSymsp->TOP.tb_sys3__DOT__dut__DOT__launch_lw;
        __Vdly__k = 0U;
        vlSelf->__PVT__halted_r = 0U;
        vlSelf->__PVT__trap_r = 0U;
        __Vdly__state = 0U;
    } else if ((4U & (IData)(vlSelf->__PVT__state))) {
        if ((1U & (~ ((IData)(vlSelf->__PVT__state) 
                      >> 1U)))) {
            if ((1U & (IData)(vlSelf->__PVT__state))) {
                if ((0x67U == (IData)(vlSelf->__PVT__opc))) {
                    vlSelf->__PVT__pc = (0xfffffffeU 
                                         & vlSelf->__PVT__addr);
                    __Vdly__state = 0U;
                } else {
                    vlSelf->__PVT__pc = (vlSelf->__VdfgTmp_he4828306__0 
                                         | vlSelf->__VdfgTmp_h7980eff3__0);
                    vlSelf->__PVT__imm_sr = vlSelf->__PVT__imm_rot;
                    vlSelf->__PVT__cy = vlSelf->__PVT__cout;
                    if (vlSelf->__PVT__last_up) {
                        __Vdly__k = 0U;
                        __Vdly__state = 0U;
                    } else {
                        __Vdly__k = (0x1fU & ((IData)(1U) 
                                              + (IData)(vlSelf->__PVT__k)));
                    }
                }
            } else {
                vlSelf->__PVT__cy = vlSelf->__PVT__cout;
                vlSelf->__PVT__pc = vlSelf->__PVT__pc_rot;
                if (vlSelf->__PVT__last_up) {
                    __Vdly__k = 0U;
                    __Vdly__state = 5U;
                } else {
                    __Vdly__k = (0x1fU & ((IData)(1U) 
                                          + (IData)(vlSelf->__PVT__k)));
                }
            }
        }
    } else if ((2U & (IData)(vlSelf->__PVT__state))) {
        if ((1U & (IData)(vlSelf->__PVT__state))) {
            vlSelf->__PVT__cy = vlSelf->__PVT__cout;
            if (vlSelf->__PVT__is_cmp) {
                vlSelf->__PVT__nz = vlSelf->__PVT__nz_n;
                if (vlSelf->__PVT__last_up) {
                    vlSelf->__PVT__f_eq = (1U & (~ (IData)(vlSelf->__PVT__nz_n)));
                    vlSelf->__PVT__f_ltu = (1U & (~ (IData)(vlSelf->__PVT__cout)));
                    vlSelf->__PVT__f_lt = (1U & (((1U 
                                                   & vlSelf->__PVT__xsh) 
                                                  != 
                                                  (1U 
                                                   & vlSelf->__PVT__ysh))
                                                  ? vlSelf->__PVT__xsh
                                                  : 
                                                 (~ (IData)(vlSelf->__PVT__cout))));
                }
            }
            if ((((3U == (IData)(vlSelf->__PVT__opc)) 
                  | (0x23U == (IData)(vlSelf->__PVT__opc))) 
                 | (0x67U == (IData)(vlSelf->__PVT__opc)))) {
                __Vdly__addr = vlSelf->__PVT__addr_ins;
            }
            vlSelf->__PVT__pc = vlSelf->__PVT__pc_rot;
            vlSelf->__PVT__imm_sr = vlSelf->__PVT__imm_rot;
            if (vlSelf->__PVT__exec_done) {
                __Vdly__k = 0U;
                __Vdly__state = (((((3U == (IData)(vlSelf->__PVT__opc)) 
                                    | (0x23U == (IData)(vlSelf->__PVT__opc))) 
                                   | (0x67U == (IData)(vlSelf->__PVT__opc))) 
                                  | (IData)(vlSelf->__PVT__is_slt))
                                  ? 4U : 5U);
            } else {
                __Vdly__k = (0x1fU & ((IData)(vlSelf->__PVT__is_sll)
                                       ? ((IData)(vlSelf->__PVT__k) 
                                          - (IData)(1U))
                                       : ((IData)(1U) 
                                          + (IData)(vlSelf->__PVT__k))));
            }
        } else {
            if ((0x33U == (IData)(vlSelf->__PVT__opc))) {
                __Vdly__shamt_w = ((vlSelf->__PVT__shamt_w 
                                    & (~ VL_SHIFTL_III(32,32,6, vlSelf->__PVT__mask, (IData)(vlSelf->__PVT__jw)))) 
                                   | VL_SHIFTL_III(32,32,6, vlSelf->d_wdata, (IData)(vlSelf->__PVT__jw)));
            }
            vlSelf->__PVT__sgn = (1U & (vlSelf->__PVT__a_val 
                                        >> (0x1fU & (IData)(vlSelf->__PVT__wm1))));
            if (((IData)(vlSelf->__PVT__j) == ((0x33U 
                                                == (IData)(vlSelf->__PVT__opc))
                                                ? (IData)(vlSelf->__PVT__mlast)
                                                : 0U))) {
                __Vdly__state = 3U;
                __Vdly__k = ((IData)(vlSelf->__PVT__is_sll)
                              ? (0x1fU & ((IData)(vlSelf->__PVT__nd) 
                                          - (IData)(1U)))
                              : 0U);
            } else {
                __Vdly__j = (7U & ((IData)(1U) + (IData)(vlSelf->__PVT__j)));
            }
        }
    } else if ((1U & (IData)(vlSelf->__PVT__state))) {
        __Vdly__j = 0U;
        vlSelf->__PVT__imm_sr = vlSelf->__PVT__imm;
        __Vdly__shamt_w = ((IData)(vlSelf->__PVT__sh_i)
                            ? (IData)(vlSelf->__PVT__rs2)
                            : 0U);
        if (vlSelf->__PVT__bad) {
            vlSelf->__PVT__trap_r = 1U;
            vlSelf->__PVT__halted_r = 1U;
            __Vdly__state = 6U;
        } else if (vlSelf->__PVT__is_sys) {
            vlSelf->__PVT__halted_r = 1U;
            __Vdly__state = 6U;
        } else if (vlSelf->__PVT__is_shift) {
            __Vdly__state = 2U;
        } else {
            __Vdly__k = 0U;
            __Vdly__state = 3U;
        }
    } else {
        vlSelf->__PVT__ir = vlSymsp->TOP.tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__id;
        __Vdly__state = 1U;
    }
    vlSelf->__PVT__addr = __Vdly__addr;
    vlSelf->__PVT__j = __Vdly__j;
    vlSelf->__PVT__shamt_w = __Vdly__shamt_w;
    vlSelf->__PVT__state = __Vdly__state;
    vlSelf->__PVT__k = __Vdly__k;
    vlSelf->d_addr = (((QData)((IData)((vlSelf->__PVT__addr 
                                        >> 2U))) << 5U) 
                      | (QData)((IData)(vlSelf->__PVT__k)));
    vlSelf->__PVT__wm1 = (0x3fU & (((IData)(1U) << (IData)(vlSelf->__PVT__lw_r)) 
                                   - (IData)(1U)));
    vlSelf->__PVT__mlast = (0x3fU & (VL_DIV_III(6, 
                                                (0x3fU 
                                                 & ((IData)(4U) 
                                                    + 
                                                    ((IData)(1U) 
                                                     << (IData)(vlSelf->__PVT__lw_r)))), 
                                                (0x3fU 
                                                 & ((IData)(1U) 
                                                    << (IData)(vlSelf->__PVT__lw_r)))) 
                                     - (IData)(1U)));
    vlSelf->__PVT__nd = (0x3fU & (0x20U >> (IData)(vlSelf->__PVT__lw_r)));
    vlSelf->__PVT__jw = (0x3fU & ((IData)(vlSelf->__PVT__j) 
                                  * (0x3fU & ((IData)(1U) 
                                              << (IData)(vlSelf->__PVT__lw_r)))));
    vlSelf->__PVT__imm_rot = (VL_SHIFTR_III(32,32,6, vlSelf->__PVT__imm_sr, 
                                            (0x3fU 
                                             & ((IData)(1U) 
                                                << (IData)(vlSelf->__PVT__lw_r)))) 
                              | VL_SHIFTL_III(32,32,6, vlSelf->__PVT__imm_sr, 
                                              (0x3fU 
                                               & ((IData)(0x20U) 
                                                  - 
                                                  ((IData)(1U) 
                                                   << (IData)(vlSelf->__PVT__lw_r))))));
    vlSelf->__PVT__last_up = ((IData)(vlSelf->__PVT__k) 
                              == (0x1fU & ((0x3fU & 
                                            (0x20U 
                                             >> (IData)(vlSelf->__PVT__lw_r))) 
                                           - (IData)(1U))));
    vlSelf->__VdfgTmp_he4828306__0 = VL_SHIFTR_III(32,32,6, vlSelf->__PVT__pc, 
                                                   (0x3fU 
                                                    & ((IData)(1U) 
                                                       << (IData)(vlSelf->__PVT__lw_r))));
    __VdfgTmp_h933689ae__0 = (0x1fU & (vlSelf->__PVT__shamt_w 
                                       & ((0x3fU & 
                                           ((IData)(1U) 
                                            << (IData)(vlSelf->__PVT__lw_r))) 
                                          - (IData)(1U))));
    __PVT__qs = (0x1fU & ((0x1fU & vlSelf->__PVT__shamt_w) 
                          >> (IData)(vlSelf->__PVT__lw_r)));
    vlSelf->__PVT__mask = ((5U == (IData)(vlSelf->__PVT__lw_r))
                            ? 0xffffffffU : (VL_SHIFTL_III(32,32,6, (IData)(1U), 
                                                           (0x3fU 
                                                            & ((IData)(1U) 
                                                               << (IData)(vlSelf->__PVT__lw_r)))) 
                                             - (IData)(1U)));
    vlSelf->__PVT__rs2 = (0x1fU & (vlSelf->__PVT__ir 
                                   >> 0x14U));
    vlSelf->__PVT__is_sys = (0x73U == (0x7fU & vlSelf->__PVT__ir));
    vlSelf->__PVT__opc = (0x7fU & vlSelf->__PVT__ir);
    __VdfgTmp_h2cd83c5b__0 = ((0x37U == (0x7fU & vlSelf->__PVT__ir)) 
                              | (0x17U == (0x7fU & vlSelf->__PVT__ir)));
    __Vtableidx31 = (((IData)(vlSelf->__PVT__f_eq) 
                      << 5U) | (((IData)(vlSelf->__PVT__f_lt) 
                                 << 4U) | (((IData)(vlSelf->__PVT__f_ltu) 
                                            << 3U) 
                                           | (7U & 
                                              (vlSelf->__PVT__ir 
                                               >> 0xcU)))));
    __PVT__cond = Vtb_sys3__ConstPool__TABLE_h2a0441a0_0
        [__Vtableidx31];
    __VdfgTmp_hd9b60348__0 = ((2U == (7U & (vlSelf->__PVT__ir 
                                            >> 0xcU))) 
                              | (3U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))));
    __VdfgTmp_h18c46dac__0 = ((0x13U == (0x7fU & vlSelf->__PVT__ir)) 
                              | (0x33U == (0x7fU & vlSelf->__PVT__ir)));
    __VdfgTmp_he83b8d53__0 = ((1U == (7U & (vlSelf->__PVT__ir 
                                            >> 0xcU))) 
                              | (5U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))));
    vlSelf->__PVT__pc_rot = (vlSelf->__VdfgTmp_he4828306__0 
                             | VL_SHIFTL_III(32,32,6, vlSelf->__PVT__pc, 
                                             (0x3fU 
                                              & ((IData)(0x20U) 
                                                 - 
                                                 ((IData)(1U) 
                                                  << (IData)(vlSelf->__PVT__lw_r))))));
    __PVT__pc_d = (vlSelf->__PVT__pc & vlSelf->__PVT__mask);
    __PVT__imm_d = (vlSelf->__PVT__imm_sr & vlSelf->__PVT__mask);
    __PVT__c4_d = (VL_SHIFTR_III(32,32,6, 4U, (0x3fU 
                                               & ((IData)(vlSelf->__PVT__k) 
                                                  * 
                                                  (0x3fU 
                                                   & ((IData)(1U) 
                                                      << (IData)(vlSelf->__PVT__lw_r)))))) 
                   & vlSelf->__PVT__mask);
    vlSelf->__PVT__imm = ((IData)(__VdfgTmp_h2cd83c5b__0)
                           ? (0xfffff000U & vlSelf->__PVT__ir)
                           : ((0x6fU == (0x7fU & vlSelf->__PVT__ir))
                               ? (((- (IData)((vlSelf->__PVT__ir 
                                               >> 0x1fU))) 
                                   << 0x15U) | ((0x100000U 
                                                 & (vlSelf->__PVT__ir 
                                                    >> 0xbU)) 
                                                | ((0xff000U 
                                                    & vlSelf->__PVT__ir) 
                                                   | ((0x800U 
                                                       & (vlSelf->__PVT__ir 
                                                          >> 9U)) 
                                                      | (0x7feU 
                                                         & (vlSelf->__PVT__ir 
                                                            >> 0x14U))))))
                               : ((0x63U == (0x7fU 
                                             & vlSelf->__PVT__ir))
                                   ? (((- (IData)((vlSelf->__PVT__ir 
                                                   >> 0x1fU))) 
                                       << 0xdU) | (
                                                   (0x1000U 
                                                    & (vlSelf->__PVT__ir 
                                                       >> 0x13U)) 
                                                   | ((0x800U 
                                                       & (vlSelf->__PVT__ir 
                                                          << 4U)) 
                                                      | ((0x7e0U 
                                                          & (vlSelf->__PVT__ir 
                                                             >> 0x14U)) 
                                                         | (0x1eU 
                                                            & (vlSelf->__PVT__ir 
                                                               >> 7U))))))
                                   : ((0x23U == (0x7fU 
                                                 & vlSelf->__PVT__ir))
                                       ? (((- (IData)(
                                                      (vlSelf->__PVT__ir 
                                                       >> 0x1fU))) 
                                           << 0xcU) 
                                          | ((0xfe0U 
                                              & (vlSelf->__PVT__ir 
                                                 >> 0x14U)) 
                                             | (0x1fU 
                                                & (vlSelf->__PVT__ir 
                                                   >> 7U))))
                                       : (((- (IData)(
                                                      (vlSelf->__PVT__ir 
                                                       >> 0x1fU))) 
                                           << 0xcU) 
                                          | (vlSelf->__PVT__ir 
                                             >> 0x14U))))));
    __VdfgExtracted_h62388771__0 = ((IData)(__VdfgTmp_h2cd83c5b__0) 
                                    | (0x6fU == (0x7fU 
                                                 & vlSelf->__PVT__ir)));
    vlSelf->__PVT__is_cmp = ((0x63U == (0x7fU & vlSelf->__PVT__ir)) 
                             | ((IData)(__VdfgTmp_h18c46dac__0) 
                                & (IData)(__VdfgTmp_hd9b60348__0)));
    vlSelf->__PVT__sh_i = ((0x13U == (0x7fU & vlSelf->__PVT__ir)) 
                           & (IData)(__VdfgTmp_he83b8d53__0));
    vlSelf->__PVT__bad = (1U & ((~ ((IData)(__VdfgExtracted_h62388771__0) 
                                    | ((0x67U == (0x7fU 
                                                  & vlSelf->__PVT__ir)) 
                                       | ((0x63U == 
                                           (0x7fU & vlSelf->__PVT__ir)) 
                                          | ((3U == 
                                              (0x7fU 
                                               & vlSelf->__PVT__ir)) 
                                             | ((0x23U 
                                                 == 
                                                 (0x7fU 
                                                  & vlSelf->__PVT__ir)) 
                                                | ((0x13U 
                                                    == 
                                                    (0x7fU 
                                                     & vlSelf->__PVT__ir)) 
                                                   | ((0x33U 
                                                       == 
                                                       (0x7fU 
                                                        & vlSelf->__PVT__ir)) 
                                                      | (0x73U 
                                                         == 
                                                         (0x7fU 
                                                          & vlSelf->__PVT__ir)))))))))) 
                                | (((0x67U == (0x7fU 
                                               & vlSelf->__PVT__ir)) 
                                    & (0U != (7U & 
                                              (vlSelf->__PVT__ir 
                                               >> 0xcU)))) 
                                   | (((0x63U == (0x7fU 
                                                  & vlSelf->__PVT__ir)) 
                                       & (IData)(__VdfgTmp_hd9b60348__0)) 
                                      | ((((3U == (0x7fU 
                                                   & vlSelf->__PVT__ir)) 
                                           | (0x23U 
                                              == (0x7fU 
                                                  & vlSelf->__PVT__ir))) 
                                          & (2U != 
                                             (7U & 
                                              (vlSelf->__PVT__ir 
                                               >> 0xcU)))) 
                                         | ((IData)(
                                                    ((0x1013U 
                                                      == 
                                                      (0x707fU 
                                                       & vlSelf->__PVT__ir)) 
                                                     & (0U 
                                                        != 
                                                        (vlSelf->__PVT__ir 
                                                         >> 0x19U)))) 
                                            | ((IData)(
                                                       ((0x5013U 
                                                         == 
                                                         (0x707fU 
                                                          & vlSelf->__PVT__ir)) 
                                                        & ((0U 
                                                            != 
                                                            (vlSelf->__PVT__ir 
                                                             >> 0x19U)) 
                                                           & (0x20U 
                                                              != 
                                                              (vlSelf->__PVT__ir 
                                                               >> 0x19U))))) 
                                               | ((0x33U 
                                                   == 
                                                   (0x7fU 
                                                    & vlSelf->__PVT__ir)) 
                                                  & ((~ 
                                                      ((0x20U 
                                                        == 
                                                        (vlSelf->__PVT__ir 
                                                         >> 0x19U)) 
                                                       & ((0U 
                                                           == 
                                                           (7U 
                                                            & (vlSelf->__PVT__ir 
                                                               >> 0xcU))) 
                                                          | (5U 
                                                             == 
                                                             (7U 
                                                              & (vlSelf->__PVT__ir 
                                                                 >> 0xcU)))))) 
                                                     & (0U 
                                                        != 
                                                        (vlSelf->__PVT__ir 
                                                         >> 0x19U)))))))))));
    vlSelf->__PVT__is_slt = ((0x63U != (0x7fU & vlSelf->__PVT__ir)) 
                             & (IData)(vlSelf->__PVT__is_cmp));
    __PVT__inv = 0U;
    vlSelf->__PVT__is_shift = ((IData)(vlSelf->__PVT__sh_i) 
                               | ((0x33U == (0x7fU 
                                             & vlSelf->__PVT__ir)) 
                                  & (IData)(__VdfgTmp_he83b8d53__0)));
    vlSelf->__PVT__we = 0U;
    __PVT__fill = (((IData)(vlSelf->__PVT__is_shift) 
                    & (IData)(((0x40005000U == (0x40007000U 
                                                & vlSelf->__PVT__ir)) 
                               & (IData)(vlSelf->__PVT__sgn))))
                    ? vlSelf->__PVT__mask : 0U);
    __PVT__shx = ((3U == (IData)(vlSelf->__PVT__state)) 
                  & (IData)(vlSelf->__PVT__is_shift));
    vlSelf->__PVT__is_sll = ((IData)(vlSelf->__PVT__is_shift) 
                             & (0x1000U == (0x7000U 
                                            & vlSelf->__PVT__ir)));
    if (vlSelf->__PVT__is_sll) {
        vlSelf->__PVT__exec_done = (0U == (IData)(vlSelf->__PVT__k));
        __PVT__ia = (0x1ffU & ((IData)(vlSelf->__PVT__k) 
                               - (IData)(__PVT__qs)));
        __VdfgTmp_h41a48239__0 = ((VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__k)) 
                                   - VL_EXTENDS_II(32,9, (IData)(__PVT__qs))) 
                                  - (IData)(1U));
    } else {
        vlSelf->__PVT__exec_done = vlSelf->__PVT__last_up;
        __PVT__ia = (0x1ffU & ((IData)(vlSelf->__PVT__k) 
                               + (IData)(__PVT__qs)));
        __VdfgTmp_h41a48239__0 = ((IData)(1U) + (VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__k)) 
                                                 + 
                                                 VL_EXTENDS_II(32,9, (IData)(__PVT__qs))));
    }
    __PVT__va = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, (IData)(__PVT__ia))) 
                 & VL_LTES_III(9, (IData)(__PVT__ia), 
                               (0x1ffU & ((0x3fU & 
                                           (0x20U >> (IData)(vlSelf->__PVT__lw_r))) 
                                          - (IData)(1U)))));
    vlSelf->__PVT__a_val = ((0U == (0x1fU & (vlSelf->__PVT__ir 
                                             >> 0xfU)))
                             ? 0U : (vlSymsp->TOP.tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__rf
                                     [((0x3e0U & (vlSelf->__PVT__ir 
                                                  >> 0xaU)) 
                                       | (0x1fU & (
                                                   (2U 
                                                    == (IData)(vlSelf->__PVT__state))
                                                    ? 
                                                   ((0x3fU 
                                                     & (0x20U 
                                                        >> (IData)(vlSelf->__PVT__lw_r))) 
                                                    - (IData)(1U))
                                                    : 
                                                   ((IData)(__PVT__shx)
                                                     ? (IData)(__PVT__ia)
                                                     : (IData)(vlSelf->__PVT__k)))))] 
                                     & vlSelf->__PVT__mask));
    __PVT__vb = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, 
                                                   (0x1ffU 
                                                    & __VdfgTmp_h41a48239__0))) 
                 & VL_LTES_III(9, (0x1ffU & __VdfgTmp_h41a48239__0), 
                               (0x1ffU & ((0x3fU & 
                                           (0x20U >> (IData)(vlSelf->__PVT__lw_r))) 
                                          - (IData)(1U)))));
    vlSelf->d_wdata = (((IData)(__PVT__shx) ? (0U == 
                                               (0x1fU 
                                                & (vlSelf->__PVT__ir 
                                                   >> 0xfU)))
                         : (0U == (0x1fU & (vlSelf->__PVT__ir 
                                            >> 0x14U))))
                        ? 0U : (vlSymsp->TOP.tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__rf
                                [((0x3e0U & (((IData)(__PVT__shx)
                                               ? (vlSelf->__PVT__ir 
                                                  >> 0xfU)
                                               : (vlSelf->__PVT__ir 
                                                  >> 0x14U)) 
                                             << 5U)) 
                                  | (0x1fU & ((2U == (IData)(vlSelf->__PVT__state))
                                               ? (IData)(vlSelf->__PVT__j)
                                               : ((IData)(__PVT__shx)
                                                   ? __VdfgTmp_h41a48239__0
                                                   : (IData)(vlSelf->__PVT__k)))))] 
                                & vlSelf->__PVT__mask));
    __PVT__X = vlSelf->__PVT__a_val;
    __PVT__Yr = (((0x33U == (0x7fU & vlSelf->__PVT__ir)) 
                  | (0x63U == (0x7fU & vlSelf->__PVT__ir)))
                  ? vlSelf->d_wdata : __PVT__imm_d);
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if ((0x37U != (0x7fU & vlSelf->__PVT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->__PVT__ir))) {
                if ((0x6fU != (0x7fU & vlSelf->__PVT__ir))) {
                    if (((IData)((0x40000033U == (0x4000707fU 
                                                  & vlSelf->__PVT__ir))) 
                         | (IData)(vlSelf->__PVT__is_cmp))) {
                        __PVT__inv = 1U;
                    }
                }
            }
        }
        if (vlSelf->__PVT__is_shift) {
            vlSelf->__PVT__we = 1U;
        } else if (__VdfgExtracted_h62388771__0) {
            vlSelf->__PVT__we = 1U;
        } else if (((~ (IData)(vlSelf->__PVT__is_cmp)) 
                    & (IData)(__VdfgTmp_h18c46dac__0))) {
            vlSelf->__PVT__we = 1U;
        }
        if ((0x37U == (0x7fU & vlSelf->__PVT__ir))) {
            __PVT__X = 0U;
        } else if ((0x17U == (0x7fU & vlSelf->__PVT__ir))) {
            __PVT__X = __PVT__pc_d;
        } else if ((0x6fU == (0x7fU & vlSelf->__PVT__ir))) {
            __PVT__X = __PVT__pc_d;
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        if ((3U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__we = 1U;
        } else if (vlSelf->__PVT__is_slt) {
            vlSelf->__PVT__we = 1U;
        } else if ((0x67U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__we = 1U;
        }
        __PVT__X = __PVT__pc_d;
    } else if ((5U == (IData)(vlSelf->__PVT__state))) {
        __PVT__X = __PVT__pc_d;
    }
    vlSelf->__PVT__xsh = VL_SHIFTR_III(32,32,6, __PVT__X, 
                                       (0x3fU & (((IData)(1U) 
                                                  << (IData)(vlSelf->__PVT__lw_r)) 
                                                 - (IData)(1U))));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if ((0x37U != (0x7fU & vlSelf->__PVT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->__PVT__ir))) {
                if ((0x6fU == (0x7fU & vlSelf->__PVT__ir))) {
                    __PVT__Yr = __PVT__c4_d;
                }
            }
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        __PVT__Yr = __PVT__c4_d;
    } else if ((5U == (IData)(vlSelf->__PVT__state))) {
        __PVT__Yr = (((0x6fU == (0x7fU & vlSelf->__PVT__ir)) 
                      | ((0x63U == (0x7fU & vlSelf->__PVT__ir)) 
                         & (IData)(__PVT__cond))) ? __PVT__imm_d
                      : __PVT__c4_d);
    }
    vlSelf->__PVT__ysh = VL_SHIFTR_III(32,32,6, __PVT__Yr, 
                                       (0x3fU & (((IData)(1U) 
                                                  << (IData)(vlSelf->__PVT__lw_r)) 
                                                 - (IData)(1U))));
    __PVT__sum_full = (0x1ffffffffULL & ((QData)((IData)(__PVT__X)) 
                                         + ((QData)((IData)(
                                                            ((IData)(__PVT__inv)
                                                              ? 
                                                             ((~ __PVT__Yr) 
                                                              & vlSelf->__PVT__mask)
                                                              : __PVT__Yr))) 
                                            + (QData)((IData)(
                                                              ((0U 
                                                                == (IData)(vlSelf->__PVT__k))
                                                                ? (IData)(__PVT__inv)
                                                                : (IData)(vlSelf->__PVT__cy)))))));
    vlSelf->__PVT__cout = (1U & (IData)((0x1ffffffffULL 
                                         & (__PVT__sum_full 
                                            >> (0x3fU 
                                                & ((IData)(1U) 
                                                   << (IData)(vlSelf->__PVT__lw_r)))))));
    __PVT__sum_d = ((IData)(__PVT__sum_full) & vlSelf->__PVT__mask);
    vlSelf->__PVT__nz_n = (((0U != (IData)(vlSelf->__PVT__k)) 
                            & (IData)(vlSelf->__PVT__nz)) 
                           | (0U != __PVT__sum_d));
    vlSelf->__VdfgTmp_h7980eff3__0 = VL_SHIFTL_III(32,32,6, __PVT__sum_d, 
                                                   (0x3fU 
                                                    & ((IData)(0x20U) 
                                                       - 
                                                       ((IData)(1U) 
                                                        << (IData)(vlSelf->__PVT__lw_r)))));
    vlSelf->__PVT__wd = (((IData)(__VdfgTmp_h18c46dac__0) 
                          & ((4U == (7U & (vlSelf->__PVT__ir 
                                           >> 0xcU))) 
                             | ((6U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))) 
                                | (7U == (7U & (vlSelf->__PVT__ir 
                                                >> 0xcU))))))
                          ? ((4U == (7U & (vlSelf->__PVT__ir 
                                           >> 0xcU)))
                              ? (__PVT__X ^ __PVT__Yr)
                              : ((6U == (7U & (vlSelf->__PVT__ir 
                                               >> 0xcU)))
                                  ? (__PVT__X | __PVT__Yr)
                                  : (__PVT__X & __PVT__Yr)))
                          : __PVT__sum_d);
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if (vlSelf->__PVT__is_shift) {
            vlSelf->__PVT__wd = ((IData)(((((QData)((IData)(
                                                            ((IData)(vlSelf->__PVT__is_sll)
                                                              ? 
                                                             ((IData)(__PVT__va)
                                                               ? vlSelf->__PVT__a_val
                                                               : 0U)
                                                              : 
                                                             ((IData)(__PVT__vb)
                                                               ? vlSelf->d_wdata
                                                               : __PVT__fill)))) 
                                            << (0x3fU 
                                                & ((IData)(1U) 
                                                   << (IData)(vlSelf->__PVT__lw_r)))) 
                                           | (QData)((IData)(
                                                             ((IData)(vlSelf->__PVT__is_sll)
                                                               ? 
                                                              ((IData)(__PVT__vb)
                                                                ? vlSelf->d_wdata
                                                                : 0U)
                                                               : 
                                                              ((IData)(__PVT__va)
                                                                ? vlSelf->__PVT__a_val
                                                                : __PVT__fill))))) 
                                          >> (0x3fU 
                                              & ((IData)(vlSelf->__PVT__is_sll)
                                                  ? 
                                                 (((IData)(1U) 
                                                   << (IData)(vlSelf->__PVT__lw_r)) 
                                                  - (IData)(__VdfgTmp_h933689ae__0))
                                                  : (IData)(__VdfgTmp_h933689ae__0))))) 
                                 & vlSelf->__PVT__mask);
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        if ((3U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__wd = (vlSymsp->TOP.tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__dm
                                 [(0x7fffU & (IData)(vlSelf->d_addr))] 
                                 & vlSelf->__PVT__mask);
        } else if (vlSelf->__PVT__is_slt) {
            vlSelf->__PVT__wd = 0U;
            vlSelf->__PVT__wd = ((0xfffffffeU & vlSelf->__PVT__wd) 
                                 | ((0U == (IData)(vlSelf->__PVT__k)) 
                                    & ((2U == (7U & 
                                               (vlSelf->__PVT__ir 
                                                >> 0xcU)))
                                        ? (IData)(vlSelf->__PVT__f_lt)
                                        : (IData)(vlSelf->__PVT__f_ltu))));
        } else if ((0x67U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__wd = __PVT__sum_d;
        }
    }
    vlSelf->__PVT__addr_ins = (VL_SHIFTR_III(32,32,6, vlSelf->__PVT__addr, 
                                             (0x3fU 
                                              & ((IData)(1U) 
                                                 << (IData)(vlSelf->__PVT__lw_r)))) 
                               | vlSelf->__VdfgTmp_h7980eff3__0);
}

VL_INLINE_OPT void Vtb_sys3_uc_core_rw___nba_sequent__TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core__0(Vtb_sys3_uc_core_rw* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_sys3__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+          Vtb_sys3_uc_core_rw___nba_sequent__TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core__0\n"); );
    // Init
    CData/*0:0*/ __PVT__shx;
    __PVT__shx = 0;
    IData/*31:0*/ __PVT__pc_d;
    __PVT__pc_d = 0;
    IData/*31:0*/ __PVT__imm_d;
    __PVT__imm_d = 0;
    IData/*31:0*/ __PVT__c4_d;
    __PVT__c4_d = 0;
    SData/*8:0*/ __PVT__qs;
    __PVT__qs = 0;
    SData/*8:0*/ __PVT__ia;
    __PVT__ia = 0;
    CData/*0:0*/ __PVT__va;
    __PVT__va = 0;
    CData/*0:0*/ __PVT__vb;
    __PVT__vb = 0;
    IData/*31:0*/ __PVT__fill;
    __PVT__fill = 0;
    IData/*31:0*/ __PVT__X;
    __PVT__X = 0;
    IData/*31:0*/ __PVT__Yr;
    __PVT__Yr = 0;
    CData/*0:0*/ __PVT__inv;
    __PVT__inv = 0;
    QData/*32:0*/ __PVT__sum_full;
    __PVT__sum_full = 0;
    IData/*31:0*/ __PVT__sum_d;
    __PVT__sum_d = 0;
    CData/*0:0*/ __PVT__cond;
    __PVT__cond = 0;
    CData/*0:0*/ __VdfgExtracted_h62388771__0;
    __VdfgExtracted_h62388771__0 = 0;
    IData/*31:0*/ __VdfgTmp_h41a48239__0;
    __VdfgTmp_h41a48239__0 = 0;
    CData/*0:0*/ __VdfgTmp_h2cd83c5b__0;
    __VdfgTmp_h2cd83c5b__0 = 0;
    CData/*0:0*/ __VdfgTmp_he83b8d53__0;
    __VdfgTmp_he83b8d53__0 = 0;
    CData/*0:0*/ __VdfgTmp_h18c46dac__0;
    __VdfgTmp_h18c46dac__0 = 0;
    CData/*0:0*/ __VdfgTmp_hd9b60348__0;
    __VdfgTmp_hd9b60348__0 = 0;
    CData/*5:0*/ __VdfgTmp_h933689ae__0;
    __VdfgTmp_h933689ae__0 = 0;
    CData/*5:0*/ __Vtableidx32;
    __Vtableidx32 = 0;
    CData/*2:0*/ __Vdly__state;
    __Vdly__state = 0;
    IData/*31:0*/ __Vdly__addr;
    __Vdly__addr = 0;
    IData/*31:0*/ __Vdly__shamt_w;
    __Vdly__shamt_w = 0;
    CData/*4:0*/ __Vdly__k;
    __Vdly__k = 0;
    CData/*2:0*/ __Vdly__j;
    __Vdly__j = 0;
    // Body
    __Vdly__addr = vlSelf->__PVT__addr;
    __Vdly__j = vlSelf->__PVT__j;
    __Vdly__shamt_w = vlSelf->__PVT__shamt_w;
    __Vdly__state = vlSelf->__PVT__state;
    __Vdly__k = vlSelf->__PVT__k;
    if (vlSymsp->TOP.tb_sys3__DOT__rst) {
        __Vdly__state = 6U;
        vlSelf->__PVT__pc = 0U;
        vlSelf->__PVT__ir = 0U;
        __Vdly__addr = 0U;
        vlSelf->__PVT__imm_sr = 0U;
        __Vdly__shamt_w = 0U;
        __Vdly__k = 0U;
        __Vdly__j = 0U;
        vlSelf->__PVT__lw_r = 0U;
        vlSelf->__PVT__cy = 0U;
        vlSelf->__PVT__nz = 0U;
        vlSelf->__PVT__f_eq = 0U;
        vlSelf->__PVT__f_lt = 0U;
        vlSelf->__PVT__f_ltu = 0U;
        vlSelf->__PVT__sgn = 0U;
        vlSelf->__PVT__halted_r = 1U;
        vlSelf->__PVT__trap_r = 0U;
    } else if (((vlSymsp->TOP.tb_sys3__DOT__dut__DOT__start_v 
                 >> 0x1fU) & (6U == (IData)(vlSelf->__PVT__state)))) {
        vlSelf->__PVT__pc = vlSymsp->TOP.tb_sys3__DOT__dut__DOT__launch_entry;
        vlSelf->__PVT__lw_r = vlSymsp->TOP.tb_sys3__DOT__dut__DOT__launch_lw;
        __Vdly__k = 0U;
        vlSelf->__PVT__halted_r = 0U;
        vlSelf->__PVT__trap_r = 0U;
        __Vdly__state = 0U;
    } else if ((4U & (IData)(vlSelf->__PVT__state))) {
        if ((1U & (~ ((IData)(vlSelf->__PVT__state) 
                      >> 1U)))) {
            if ((1U & (IData)(vlSelf->__PVT__state))) {
                if ((0x67U == (IData)(vlSelf->__PVT__opc))) {
                    vlSelf->__PVT__pc = (0xfffffffeU 
                                         & vlSelf->__PVT__addr);
                    __Vdly__state = 0U;
                } else {
                    vlSelf->__PVT__pc = (vlSelf->__VdfgTmp_he4828306__0 
                                         | vlSelf->__VdfgTmp_h7980eff3__0);
                    vlSelf->__PVT__imm_sr = vlSelf->__PVT__imm_rot;
                    vlSelf->__PVT__cy = vlSelf->__PVT__cout;
                    if (vlSelf->__PVT__last_up) {
                        __Vdly__k = 0U;
                        __Vdly__state = 0U;
                    } else {
                        __Vdly__k = (0x1fU & ((IData)(1U) 
                                              + (IData)(vlSelf->__PVT__k)));
                    }
                }
            } else {
                vlSelf->__PVT__cy = vlSelf->__PVT__cout;
                vlSelf->__PVT__pc = vlSelf->__PVT__pc_rot;
                if (vlSelf->__PVT__last_up) {
                    __Vdly__k = 0U;
                    __Vdly__state = 5U;
                } else {
                    __Vdly__k = (0x1fU & ((IData)(1U) 
                                          + (IData)(vlSelf->__PVT__k)));
                }
            }
        }
    } else if ((2U & (IData)(vlSelf->__PVT__state))) {
        if ((1U & (IData)(vlSelf->__PVT__state))) {
            vlSelf->__PVT__cy = vlSelf->__PVT__cout;
            if (vlSelf->__PVT__is_cmp) {
                vlSelf->__PVT__nz = vlSelf->__PVT__nz_n;
                if (vlSelf->__PVT__last_up) {
                    vlSelf->__PVT__f_eq = (1U & (~ (IData)(vlSelf->__PVT__nz_n)));
                    vlSelf->__PVT__f_ltu = (1U & (~ (IData)(vlSelf->__PVT__cout)));
                    vlSelf->__PVT__f_lt = (1U & (((1U 
                                                   & vlSelf->__PVT__xsh) 
                                                  != 
                                                  (1U 
                                                   & vlSelf->__PVT__ysh))
                                                  ? vlSelf->__PVT__xsh
                                                  : 
                                                 (~ (IData)(vlSelf->__PVT__cout))));
                }
            }
            if ((((3U == (IData)(vlSelf->__PVT__opc)) 
                  | (0x23U == (IData)(vlSelf->__PVT__opc))) 
                 | (0x67U == (IData)(vlSelf->__PVT__opc)))) {
                __Vdly__addr = vlSelf->__PVT__addr_ins;
            }
            vlSelf->__PVT__pc = vlSelf->__PVT__pc_rot;
            vlSelf->__PVT__imm_sr = vlSelf->__PVT__imm_rot;
            if (vlSelf->__PVT__exec_done) {
                __Vdly__k = 0U;
                __Vdly__state = (((((3U == (IData)(vlSelf->__PVT__opc)) 
                                    | (0x23U == (IData)(vlSelf->__PVT__opc))) 
                                   | (0x67U == (IData)(vlSelf->__PVT__opc))) 
                                  | (IData)(vlSelf->__PVT__is_slt))
                                  ? 4U : 5U);
            } else {
                __Vdly__k = (0x1fU & ((IData)(vlSelf->__PVT__is_sll)
                                       ? ((IData)(vlSelf->__PVT__k) 
                                          - (IData)(1U))
                                       : ((IData)(1U) 
                                          + (IData)(vlSelf->__PVT__k))));
            }
        } else {
            if ((0x33U == (IData)(vlSelf->__PVT__opc))) {
                __Vdly__shamt_w = ((vlSelf->__PVT__shamt_w 
                                    & (~ VL_SHIFTL_III(32,32,6, vlSelf->__PVT__mask, (IData)(vlSelf->__PVT__jw)))) 
                                   | VL_SHIFTL_III(32,32,6, vlSelf->d_wdata, (IData)(vlSelf->__PVT__jw)));
            }
            vlSelf->__PVT__sgn = (1U & (vlSelf->__PVT__a_val 
                                        >> (0x1fU & (IData)(vlSelf->__PVT__wm1))));
            if (((IData)(vlSelf->__PVT__j) == ((0x33U 
                                                == (IData)(vlSelf->__PVT__opc))
                                                ? (IData)(vlSelf->__PVT__mlast)
                                                : 0U))) {
                __Vdly__state = 3U;
                __Vdly__k = ((IData)(vlSelf->__PVT__is_sll)
                              ? (0x1fU & ((IData)(vlSelf->__PVT__nd) 
                                          - (IData)(1U)))
                              : 0U);
            } else {
                __Vdly__j = (7U & ((IData)(1U) + (IData)(vlSelf->__PVT__j)));
            }
        }
    } else if ((1U & (IData)(vlSelf->__PVT__state))) {
        __Vdly__j = 0U;
        vlSelf->__PVT__imm_sr = vlSelf->__PVT__imm;
        __Vdly__shamt_w = ((IData)(vlSelf->__PVT__sh_i)
                            ? (IData)(vlSelf->__PVT__rs2)
                            : 0U);
        if (vlSelf->__PVT__bad) {
            vlSelf->__PVT__trap_r = 1U;
            vlSelf->__PVT__halted_r = 1U;
            __Vdly__state = 6U;
        } else if (vlSelf->__PVT__is_sys) {
            vlSelf->__PVT__halted_r = 1U;
            __Vdly__state = 6U;
        } else if (vlSelf->__PVT__is_shift) {
            __Vdly__state = 2U;
        } else {
            __Vdly__k = 0U;
            __Vdly__state = 3U;
        }
    } else {
        vlSelf->__PVT__ir = vlSymsp->TOP.tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__id;
        __Vdly__state = 1U;
    }
    vlSelf->__PVT__addr = __Vdly__addr;
    vlSelf->__PVT__j = __Vdly__j;
    vlSelf->__PVT__shamt_w = __Vdly__shamt_w;
    vlSelf->__PVT__state = __Vdly__state;
    vlSelf->__PVT__k = __Vdly__k;
    vlSelf->d_addr = (((QData)((IData)((vlSelf->__PVT__addr 
                                        >> 2U))) << 5U) 
                      | (QData)((IData)(vlSelf->__PVT__k)));
    vlSelf->__PVT__wm1 = (0x3fU & (((IData)(1U) << (IData)(vlSelf->__PVT__lw_r)) 
                                   - (IData)(1U)));
    vlSelf->__PVT__mlast = (0x3fU & (VL_DIV_III(6, 
                                                (0x3fU 
                                                 & ((IData)(4U) 
                                                    + 
                                                    ((IData)(1U) 
                                                     << (IData)(vlSelf->__PVT__lw_r)))), 
                                                (0x3fU 
                                                 & ((IData)(1U) 
                                                    << (IData)(vlSelf->__PVT__lw_r)))) 
                                     - (IData)(1U)));
    vlSelf->__PVT__nd = (0x3fU & (0x20U >> (IData)(vlSelf->__PVT__lw_r)));
    vlSelf->__PVT__jw = (0x3fU & ((IData)(vlSelf->__PVT__j) 
                                  * (0x3fU & ((IData)(1U) 
                                              << (IData)(vlSelf->__PVT__lw_r)))));
    vlSelf->__PVT__imm_rot = (VL_SHIFTR_III(32,32,6, vlSelf->__PVT__imm_sr, 
                                            (0x3fU 
                                             & ((IData)(1U) 
                                                << (IData)(vlSelf->__PVT__lw_r)))) 
                              | VL_SHIFTL_III(32,32,6, vlSelf->__PVT__imm_sr, 
                                              (0x3fU 
                                               & ((IData)(0x20U) 
                                                  - 
                                                  ((IData)(1U) 
                                                   << (IData)(vlSelf->__PVT__lw_r))))));
    vlSelf->__PVT__last_up = ((IData)(vlSelf->__PVT__k) 
                              == (0x1fU & ((0x3fU & 
                                            (0x20U 
                                             >> (IData)(vlSelf->__PVT__lw_r))) 
                                           - (IData)(1U))));
    vlSelf->__VdfgTmp_he4828306__0 = VL_SHIFTR_III(32,32,6, vlSelf->__PVT__pc, 
                                                   (0x3fU 
                                                    & ((IData)(1U) 
                                                       << (IData)(vlSelf->__PVT__lw_r))));
    __VdfgTmp_h933689ae__0 = (0x1fU & (vlSelf->__PVT__shamt_w 
                                       & ((0x3fU & 
                                           ((IData)(1U) 
                                            << (IData)(vlSelf->__PVT__lw_r))) 
                                          - (IData)(1U))));
    __PVT__qs = (0x1fU & ((0x1fU & vlSelf->__PVT__shamt_w) 
                          >> (IData)(vlSelf->__PVT__lw_r)));
    vlSelf->__PVT__mask = ((5U == (IData)(vlSelf->__PVT__lw_r))
                            ? 0xffffffffU : (VL_SHIFTL_III(32,32,6, (IData)(1U), 
                                                           (0x3fU 
                                                            & ((IData)(1U) 
                                                               << (IData)(vlSelf->__PVT__lw_r)))) 
                                             - (IData)(1U)));
    vlSelf->__PVT__rs2 = (0x1fU & (vlSelf->__PVT__ir 
                                   >> 0x14U));
    vlSelf->__PVT__is_sys = (0x73U == (0x7fU & vlSelf->__PVT__ir));
    vlSelf->__PVT__opc = (0x7fU & vlSelf->__PVT__ir);
    __VdfgTmp_h2cd83c5b__0 = ((0x37U == (0x7fU & vlSelf->__PVT__ir)) 
                              | (0x17U == (0x7fU & vlSelf->__PVT__ir)));
    __Vtableidx32 = (((IData)(vlSelf->__PVT__f_eq) 
                      << 5U) | (((IData)(vlSelf->__PVT__f_lt) 
                                 << 4U) | (((IData)(vlSelf->__PVT__f_ltu) 
                                            << 3U) 
                                           | (7U & 
                                              (vlSelf->__PVT__ir 
                                               >> 0xcU)))));
    __PVT__cond = Vtb_sys3__ConstPool__TABLE_h2a0441a0_0
        [__Vtableidx32];
    __VdfgTmp_hd9b60348__0 = ((2U == (7U & (vlSelf->__PVT__ir 
                                            >> 0xcU))) 
                              | (3U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))));
    __VdfgTmp_h18c46dac__0 = ((0x13U == (0x7fU & vlSelf->__PVT__ir)) 
                              | (0x33U == (0x7fU & vlSelf->__PVT__ir)));
    __VdfgTmp_he83b8d53__0 = ((1U == (7U & (vlSelf->__PVT__ir 
                                            >> 0xcU))) 
                              | (5U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))));
    vlSelf->__PVT__pc_rot = (vlSelf->__VdfgTmp_he4828306__0 
                             | VL_SHIFTL_III(32,32,6, vlSelf->__PVT__pc, 
                                             (0x3fU 
                                              & ((IData)(0x20U) 
                                                 - 
                                                 ((IData)(1U) 
                                                  << (IData)(vlSelf->__PVT__lw_r))))));
    __PVT__pc_d = (vlSelf->__PVT__pc & vlSelf->__PVT__mask);
    __PVT__imm_d = (vlSelf->__PVT__imm_sr & vlSelf->__PVT__mask);
    __PVT__c4_d = (VL_SHIFTR_III(32,32,6, 4U, (0x3fU 
                                               & ((IData)(vlSelf->__PVT__k) 
                                                  * 
                                                  (0x3fU 
                                                   & ((IData)(1U) 
                                                      << (IData)(vlSelf->__PVT__lw_r)))))) 
                   & vlSelf->__PVT__mask);
    vlSelf->__PVT__imm = ((IData)(__VdfgTmp_h2cd83c5b__0)
                           ? (0xfffff000U & vlSelf->__PVT__ir)
                           : ((0x6fU == (0x7fU & vlSelf->__PVT__ir))
                               ? (((- (IData)((vlSelf->__PVT__ir 
                                               >> 0x1fU))) 
                                   << 0x15U) | ((0x100000U 
                                                 & (vlSelf->__PVT__ir 
                                                    >> 0xbU)) 
                                                | ((0xff000U 
                                                    & vlSelf->__PVT__ir) 
                                                   | ((0x800U 
                                                       & (vlSelf->__PVT__ir 
                                                          >> 9U)) 
                                                      | (0x7feU 
                                                         & (vlSelf->__PVT__ir 
                                                            >> 0x14U))))))
                               : ((0x63U == (0x7fU 
                                             & vlSelf->__PVT__ir))
                                   ? (((- (IData)((vlSelf->__PVT__ir 
                                                   >> 0x1fU))) 
                                       << 0xdU) | (
                                                   (0x1000U 
                                                    & (vlSelf->__PVT__ir 
                                                       >> 0x13U)) 
                                                   | ((0x800U 
                                                       & (vlSelf->__PVT__ir 
                                                          << 4U)) 
                                                      | ((0x7e0U 
                                                          & (vlSelf->__PVT__ir 
                                                             >> 0x14U)) 
                                                         | (0x1eU 
                                                            & (vlSelf->__PVT__ir 
                                                               >> 7U))))))
                                   : ((0x23U == (0x7fU 
                                                 & vlSelf->__PVT__ir))
                                       ? (((- (IData)(
                                                      (vlSelf->__PVT__ir 
                                                       >> 0x1fU))) 
                                           << 0xcU) 
                                          | ((0xfe0U 
                                              & (vlSelf->__PVT__ir 
                                                 >> 0x14U)) 
                                             | (0x1fU 
                                                & (vlSelf->__PVT__ir 
                                                   >> 7U))))
                                       : (((- (IData)(
                                                      (vlSelf->__PVT__ir 
                                                       >> 0x1fU))) 
                                           << 0xcU) 
                                          | (vlSelf->__PVT__ir 
                                             >> 0x14U))))));
    __VdfgExtracted_h62388771__0 = ((IData)(__VdfgTmp_h2cd83c5b__0) 
                                    | (0x6fU == (0x7fU 
                                                 & vlSelf->__PVT__ir)));
    vlSelf->__PVT__is_cmp = ((0x63U == (0x7fU & vlSelf->__PVT__ir)) 
                             | ((IData)(__VdfgTmp_h18c46dac__0) 
                                & (IData)(__VdfgTmp_hd9b60348__0)));
    vlSelf->__PVT__sh_i = ((0x13U == (0x7fU & vlSelf->__PVT__ir)) 
                           & (IData)(__VdfgTmp_he83b8d53__0));
    vlSelf->__PVT__bad = (1U & ((~ ((IData)(__VdfgExtracted_h62388771__0) 
                                    | ((0x67U == (0x7fU 
                                                  & vlSelf->__PVT__ir)) 
                                       | ((0x63U == 
                                           (0x7fU & vlSelf->__PVT__ir)) 
                                          | ((3U == 
                                              (0x7fU 
                                               & vlSelf->__PVT__ir)) 
                                             | ((0x23U 
                                                 == 
                                                 (0x7fU 
                                                  & vlSelf->__PVT__ir)) 
                                                | ((0x13U 
                                                    == 
                                                    (0x7fU 
                                                     & vlSelf->__PVT__ir)) 
                                                   | ((0x33U 
                                                       == 
                                                       (0x7fU 
                                                        & vlSelf->__PVT__ir)) 
                                                      | (0x73U 
                                                         == 
                                                         (0x7fU 
                                                          & vlSelf->__PVT__ir)))))))))) 
                                | (((0x67U == (0x7fU 
                                               & vlSelf->__PVT__ir)) 
                                    & (0U != (7U & 
                                              (vlSelf->__PVT__ir 
                                               >> 0xcU)))) 
                                   | (((0x63U == (0x7fU 
                                                  & vlSelf->__PVT__ir)) 
                                       & (IData)(__VdfgTmp_hd9b60348__0)) 
                                      | ((((3U == (0x7fU 
                                                   & vlSelf->__PVT__ir)) 
                                           | (0x23U 
                                              == (0x7fU 
                                                  & vlSelf->__PVT__ir))) 
                                          & (2U != 
                                             (7U & 
                                              (vlSelf->__PVT__ir 
                                               >> 0xcU)))) 
                                         | ((IData)(
                                                    ((0x1013U 
                                                      == 
                                                      (0x707fU 
                                                       & vlSelf->__PVT__ir)) 
                                                     & (0U 
                                                        != 
                                                        (vlSelf->__PVT__ir 
                                                         >> 0x19U)))) 
                                            | ((IData)(
                                                       ((0x5013U 
                                                         == 
                                                         (0x707fU 
                                                          & vlSelf->__PVT__ir)) 
                                                        & ((0U 
                                                            != 
                                                            (vlSelf->__PVT__ir 
                                                             >> 0x19U)) 
                                                           & (0x20U 
                                                              != 
                                                              (vlSelf->__PVT__ir 
                                                               >> 0x19U))))) 
                                               | ((0x33U 
                                                   == 
                                                   (0x7fU 
                                                    & vlSelf->__PVT__ir)) 
                                                  & ((~ 
                                                      ((0x20U 
                                                        == 
                                                        (vlSelf->__PVT__ir 
                                                         >> 0x19U)) 
                                                       & ((0U 
                                                           == 
                                                           (7U 
                                                            & (vlSelf->__PVT__ir 
                                                               >> 0xcU))) 
                                                          | (5U 
                                                             == 
                                                             (7U 
                                                              & (vlSelf->__PVT__ir 
                                                                 >> 0xcU)))))) 
                                                     & (0U 
                                                        != 
                                                        (vlSelf->__PVT__ir 
                                                         >> 0x19U)))))))))));
    vlSelf->__PVT__is_slt = ((0x63U != (0x7fU & vlSelf->__PVT__ir)) 
                             & (IData)(vlSelf->__PVT__is_cmp));
    __PVT__inv = 0U;
    vlSelf->__PVT__is_shift = ((IData)(vlSelf->__PVT__sh_i) 
                               | ((0x33U == (0x7fU 
                                             & vlSelf->__PVT__ir)) 
                                  & (IData)(__VdfgTmp_he83b8d53__0)));
    vlSelf->__PVT__we = 0U;
    __PVT__fill = (((IData)(vlSelf->__PVT__is_shift) 
                    & (IData)(((0x40005000U == (0x40007000U 
                                                & vlSelf->__PVT__ir)) 
                               & (IData)(vlSelf->__PVT__sgn))))
                    ? vlSelf->__PVT__mask : 0U);
    __PVT__shx = ((3U == (IData)(vlSelf->__PVT__state)) 
                  & (IData)(vlSelf->__PVT__is_shift));
    vlSelf->__PVT__is_sll = ((IData)(vlSelf->__PVT__is_shift) 
                             & (0x1000U == (0x7000U 
                                            & vlSelf->__PVT__ir)));
    if (vlSelf->__PVT__is_sll) {
        vlSelf->__PVT__exec_done = (0U == (IData)(vlSelf->__PVT__k));
        __PVT__ia = (0x1ffU & ((IData)(vlSelf->__PVT__k) 
                               - (IData)(__PVT__qs)));
        __VdfgTmp_h41a48239__0 = ((VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__k)) 
                                   - VL_EXTENDS_II(32,9, (IData)(__PVT__qs))) 
                                  - (IData)(1U));
    } else {
        vlSelf->__PVT__exec_done = vlSelf->__PVT__last_up;
        __PVT__ia = (0x1ffU & ((IData)(vlSelf->__PVT__k) 
                               + (IData)(__PVT__qs)));
        __VdfgTmp_h41a48239__0 = ((IData)(1U) + (VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__k)) 
                                                 + 
                                                 VL_EXTENDS_II(32,9, (IData)(__PVT__qs))));
    }
    __PVT__va = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, (IData)(__PVT__ia))) 
                 & VL_LTES_III(9, (IData)(__PVT__ia), 
                               (0x1ffU & ((0x3fU & 
                                           (0x20U >> (IData)(vlSelf->__PVT__lw_r))) 
                                          - (IData)(1U)))));
    vlSelf->__PVT__a_val = ((0U == (0x1fU & (vlSelf->__PVT__ir 
                                             >> 0xfU)))
                             ? 0U : (vlSymsp->TOP.tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__rf
                                     [((0x3e0U & (vlSelf->__PVT__ir 
                                                  >> 0xaU)) 
                                       | (0x1fU & (
                                                   (2U 
                                                    == (IData)(vlSelf->__PVT__state))
                                                    ? 
                                                   ((0x3fU 
                                                     & (0x20U 
                                                        >> (IData)(vlSelf->__PVT__lw_r))) 
                                                    - (IData)(1U))
                                                    : 
                                                   ((IData)(__PVT__shx)
                                                     ? (IData)(__PVT__ia)
                                                     : (IData)(vlSelf->__PVT__k)))))] 
                                     & vlSelf->__PVT__mask));
    __PVT__vb = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, 
                                                   (0x1ffU 
                                                    & __VdfgTmp_h41a48239__0))) 
                 & VL_LTES_III(9, (0x1ffU & __VdfgTmp_h41a48239__0), 
                               (0x1ffU & ((0x3fU & 
                                           (0x20U >> (IData)(vlSelf->__PVT__lw_r))) 
                                          - (IData)(1U)))));
    vlSelf->d_wdata = (((IData)(__PVT__shx) ? (0U == 
                                               (0x1fU 
                                                & (vlSelf->__PVT__ir 
                                                   >> 0xfU)))
                         : (0U == (0x1fU & (vlSelf->__PVT__ir 
                                            >> 0x14U))))
                        ? 0U : (vlSymsp->TOP.tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__rf
                                [((0x3e0U & (((IData)(__PVT__shx)
                                               ? (vlSelf->__PVT__ir 
                                                  >> 0xfU)
                                               : (vlSelf->__PVT__ir 
                                                  >> 0x14U)) 
                                             << 5U)) 
                                  | (0x1fU & ((2U == (IData)(vlSelf->__PVT__state))
                                               ? (IData)(vlSelf->__PVT__j)
                                               : ((IData)(__PVT__shx)
                                                   ? __VdfgTmp_h41a48239__0
                                                   : (IData)(vlSelf->__PVT__k)))))] 
                                & vlSelf->__PVT__mask));
    __PVT__X = vlSelf->__PVT__a_val;
    __PVT__Yr = (((0x33U == (0x7fU & vlSelf->__PVT__ir)) 
                  | (0x63U == (0x7fU & vlSelf->__PVT__ir)))
                  ? vlSelf->d_wdata : __PVT__imm_d);
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if ((0x37U != (0x7fU & vlSelf->__PVT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->__PVT__ir))) {
                if ((0x6fU != (0x7fU & vlSelf->__PVT__ir))) {
                    if (((IData)((0x40000033U == (0x4000707fU 
                                                  & vlSelf->__PVT__ir))) 
                         | (IData)(vlSelf->__PVT__is_cmp))) {
                        __PVT__inv = 1U;
                    }
                }
            }
        }
        if (vlSelf->__PVT__is_shift) {
            vlSelf->__PVT__we = 1U;
        } else if (__VdfgExtracted_h62388771__0) {
            vlSelf->__PVT__we = 1U;
        } else if (((~ (IData)(vlSelf->__PVT__is_cmp)) 
                    & (IData)(__VdfgTmp_h18c46dac__0))) {
            vlSelf->__PVT__we = 1U;
        }
        if ((0x37U == (0x7fU & vlSelf->__PVT__ir))) {
            __PVT__X = 0U;
        } else if ((0x17U == (0x7fU & vlSelf->__PVT__ir))) {
            __PVT__X = __PVT__pc_d;
        } else if ((0x6fU == (0x7fU & vlSelf->__PVT__ir))) {
            __PVT__X = __PVT__pc_d;
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        if ((3U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__we = 1U;
        } else if (vlSelf->__PVT__is_slt) {
            vlSelf->__PVT__we = 1U;
        } else if ((0x67U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__we = 1U;
        }
        __PVT__X = __PVT__pc_d;
    } else if ((5U == (IData)(vlSelf->__PVT__state))) {
        __PVT__X = __PVT__pc_d;
    }
    vlSelf->__PVT__xsh = VL_SHIFTR_III(32,32,6, __PVT__X, 
                                       (0x3fU & (((IData)(1U) 
                                                  << (IData)(vlSelf->__PVT__lw_r)) 
                                                 - (IData)(1U))));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if ((0x37U != (0x7fU & vlSelf->__PVT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->__PVT__ir))) {
                if ((0x6fU == (0x7fU & vlSelf->__PVT__ir))) {
                    __PVT__Yr = __PVT__c4_d;
                }
            }
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        __PVT__Yr = __PVT__c4_d;
    } else if ((5U == (IData)(vlSelf->__PVT__state))) {
        __PVT__Yr = (((0x6fU == (0x7fU & vlSelf->__PVT__ir)) 
                      | ((0x63U == (0x7fU & vlSelf->__PVT__ir)) 
                         & (IData)(__PVT__cond))) ? __PVT__imm_d
                      : __PVT__c4_d);
    }
    vlSelf->__PVT__ysh = VL_SHIFTR_III(32,32,6, __PVT__Yr, 
                                       (0x3fU & (((IData)(1U) 
                                                  << (IData)(vlSelf->__PVT__lw_r)) 
                                                 - (IData)(1U))));
    __PVT__sum_full = (0x1ffffffffULL & ((QData)((IData)(__PVT__X)) 
                                         + ((QData)((IData)(
                                                            ((IData)(__PVT__inv)
                                                              ? 
                                                             ((~ __PVT__Yr) 
                                                              & vlSelf->__PVT__mask)
                                                              : __PVT__Yr))) 
                                            + (QData)((IData)(
                                                              ((0U 
                                                                == (IData)(vlSelf->__PVT__k))
                                                                ? (IData)(__PVT__inv)
                                                                : (IData)(vlSelf->__PVT__cy)))))));
    vlSelf->__PVT__cout = (1U & (IData)((0x1ffffffffULL 
                                         & (__PVT__sum_full 
                                            >> (0x3fU 
                                                & ((IData)(1U) 
                                                   << (IData)(vlSelf->__PVT__lw_r)))))));
    __PVT__sum_d = ((IData)(__PVT__sum_full) & vlSelf->__PVT__mask);
    vlSelf->__PVT__nz_n = (((0U != (IData)(vlSelf->__PVT__k)) 
                            & (IData)(vlSelf->__PVT__nz)) 
                           | (0U != __PVT__sum_d));
    vlSelf->__VdfgTmp_h7980eff3__0 = VL_SHIFTL_III(32,32,6, __PVT__sum_d, 
                                                   (0x3fU 
                                                    & ((IData)(0x20U) 
                                                       - 
                                                       ((IData)(1U) 
                                                        << (IData)(vlSelf->__PVT__lw_r)))));
    vlSelf->__PVT__wd = (((IData)(__VdfgTmp_h18c46dac__0) 
                          & ((4U == (7U & (vlSelf->__PVT__ir 
                                           >> 0xcU))) 
                             | ((6U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))) 
                                | (7U == (7U & (vlSelf->__PVT__ir 
                                                >> 0xcU))))))
                          ? ((4U == (7U & (vlSelf->__PVT__ir 
                                           >> 0xcU)))
                              ? (__PVT__X ^ __PVT__Yr)
                              : ((6U == (7U & (vlSelf->__PVT__ir 
                                               >> 0xcU)))
                                  ? (__PVT__X | __PVT__Yr)
                                  : (__PVT__X & __PVT__Yr)))
                          : __PVT__sum_d);
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if (vlSelf->__PVT__is_shift) {
            vlSelf->__PVT__wd = ((IData)(((((QData)((IData)(
                                                            ((IData)(vlSelf->__PVT__is_sll)
                                                              ? 
                                                             ((IData)(__PVT__va)
                                                               ? vlSelf->__PVT__a_val
                                                               : 0U)
                                                              : 
                                                             ((IData)(__PVT__vb)
                                                               ? vlSelf->d_wdata
                                                               : __PVT__fill)))) 
                                            << (0x3fU 
                                                & ((IData)(1U) 
                                                   << (IData)(vlSelf->__PVT__lw_r)))) 
                                           | (QData)((IData)(
                                                             ((IData)(vlSelf->__PVT__is_sll)
                                                               ? 
                                                              ((IData)(__PVT__vb)
                                                                ? vlSelf->d_wdata
                                                                : 0U)
                                                               : 
                                                              ((IData)(__PVT__va)
                                                                ? vlSelf->__PVT__a_val
                                                                : __PVT__fill))))) 
                                          >> (0x3fU 
                                              & ((IData)(vlSelf->__PVT__is_sll)
                                                  ? 
                                                 (((IData)(1U) 
                                                   << (IData)(vlSelf->__PVT__lw_r)) 
                                                  - (IData)(__VdfgTmp_h933689ae__0))
                                                  : (IData)(__VdfgTmp_h933689ae__0))))) 
                                 & vlSelf->__PVT__mask);
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        if ((3U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__wd = (vlSymsp->TOP.tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__dm
                                 [(0x7fffU & (IData)(vlSelf->d_addr))] 
                                 & vlSelf->__PVT__mask);
        } else if (vlSelf->__PVT__is_slt) {
            vlSelf->__PVT__wd = 0U;
            vlSelf->__PVT__wd = ((0xfffffffeU & vlSelf->__PVT__wd) 
                                 | ((0U == (IData)(vlSelf->__PVT__k)) 
                                    & ((2U == (7U & 
                                               (vlSelf->__PVT__ir 
                                                >> 0xcU)))
                                        ? (IData)(vlSelf->__PVT__f_lt)
                                        : (IData)(vlSelf->__PVT__f_ltu))));
        } else if ((0x67U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__wd = __PVT__sum_d;
        }
    }
    vlSelf->__PVT__addr_ins = (VL_SHIFTR_III(32,32,6, vlSelf->__PVT__addr, 
                                             (0x3fU 
                                              & ((IData)(1U) 
                                                 << (IData)(vlSelf->__PVT__lw_r)))) 
                               | vlSelf->__VdfgTmp_h7980eff3__0);
}
