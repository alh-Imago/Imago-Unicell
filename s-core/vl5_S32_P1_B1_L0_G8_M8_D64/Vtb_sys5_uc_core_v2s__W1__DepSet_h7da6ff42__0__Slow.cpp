// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design implementation internals
// See Vtb_sys5.h for the primary calling header

#include "Vtb_sys5__pch.h"
#include "Vtb_sys5__Syms.h"
#include "Vtb_sys5_uc_core_v2s__W1.h"

extern const VlUnpacked<CData/*0:0*/, 64> Vtb_sys5__ConstPool__TABLE_h2a0441a0_0;

VL_ATTR_COLD void Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__0__KET____DOT__core__0(Vtb_sys5_uc_core_v2s__W1* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_sys5__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+          Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__0__KET____DOT__core__0\n"); );
    // Init
    CData/*0:0*/ __PVT__cond;
    __PVT__cond = 0;
    CData/*0:0*/ __PVT__we;
    __PVT__we = 0;
    CData/*0:0*/ __VdfgExtracted_h62388771__0;
    __VdfgExtracted_h62388771__0 = 0;
    CData/*0:0*/ __VdfgTmp_h2cd83c5b__0;
    __VdfgTmp_h2cd83c5b__0 = 0;
    CData/*0:0*/ __VdfgTmp_he83b8d53__0;
    __VdfgTmp_he83b8d53__0 = 0;
    CData/*0:0*/ __VdfgTmp_hd9b60348__0;
    __VdfgTmp_hd9b60348__0 = 0;
    CData/*5:0*/ __Vtableidx1;
    __Vtableidx1 = 0;
    // Body
    vlSelf->__PVT__rs2 = (0x1fU & (vlSelf->__PVT__ir 
                                   >> 0x14U));
    vlSelf->__PVT__is_sys = (0x73U == (0x7fU & vlSelf->__PVT__ir));
    vlSelf->__PVT__last_up = (0x1fU == (IData)(vlSelf->__PVT__k));
    vlSelf->__PVT__pc_rot = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__pc, 1U) 
                             | VL_SHIFTL_III(32,32,32, vlSelf->__PVT__pc, 0x1fU));
    vlSelf->__PVT__imm_rot = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__imm_sr, 1U) 
                              | VL_SHIFTL_III(32,32,32, vlSelf->__PVT__imm_sr, 0x1fU));
    vlSelf->__PVT__opc = (0x7fU & vlSelf->__PVT__ir);
    vlSelf->d_addr = (((QData)((IData)((vlSelf->__PVT__addr 
                                        >> 2U))) << 5U) 
                      | (QData)((IData)(vlSelf->__PVT__k)));
    vlSelf->rw_addr = ((0x3e0U & (vlSelf->__PVT__ir 
                                  >> 2U)) | (IData)(vlSelf->__PVT__k));
    __VdfgTmp_h2cd83c5b__0 = ((0x37U == (0x7fU & vlSelf->__PVT__ir)) 
                              | (0x17U == (0x7fU & vlSelf->__PVT__ir)));
    __Vtableidx1 = (((IData)(vlSelf->__PVT__f_eq) << 5U) 
                    | (((IData)(vlSelf->__PVT__f_lt) 
                        << 4U) | (((IData)(vlSelf->__PVT__f_ltu) 
                                   << 3U) | (7U & (vlSelf->__PVT__ir 
                                                   >> 0xcU)))));
    __PVT__cond = Vtb_sys5__ConstPool__TABLE_h2a0441a0_0
        [__Vtableidx1];
    vlSelf->__PVT__a_val = ((0U != (0x1fU & (vlSelf->__PVT__ir 
                                             >> 0xfU))) 
                            & (IData)(vlSymsp->TOP.tb_sys5__DOT__dut__DOT__slot__BRA__0__KET____DOT__rqa_b));
    __VdfgTmp_hd9b60348__0 = ((2U == (7U & (vlSelf->__PVT__ir 
                                            >> 0xcU))) 
                              | (3U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))));
    vlSelf->__VdfgTmp_h18c46dac__0 = ((0x13U == (0x7fU 
                                                 & vlSelf->__PVT__ir)) 
                                      | (0x33U == (0x7fU 
                                                   & vlSelf->__PVT__ir)));
    __VdfgTmp_he83b8d53__0 = ((1U == (7U & (vlSelf->__PVT__ir 
                                            >> 0xcU))) 
                              | (5U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))));
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
    vlSelf->__PVT__X = vlSelf->__PVT__a_val;
    vlSelf->__PVT__is_cmp = ((0x63U == (0x7fU & vlSelf->__PVT__ir)) 
                             | ((IData)(vlSelf->__VdfgTmp_h18c46dac__0) 
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
    vlSelf->__PVT__inv = 0U;
    vlSelf->__PVT__is_shift = ((IData)(vlSelf->__PVT__sh_i) 
                               | ((0x33U == (0x7fU 
                                             & vlSelf->__PVT__ir)) 
                                  & (IData)(__VdfgTmp_he83b8d53__0)));
    __PVT__we = 0U;
    vlSelf->__PVT__fill = ((IData)(vlSelf->__PVT__is_shift) 
                           & (IData)(((0x40005000U 
                                       == (0x40007000U 
                                           & vlSelf->__PVT__ir)) 
                                      & (IData)(vlSelf->__PVT__sgn))));
    vlSelf->__PVT__is_sll = ((IData)(vlSelf->__PVT__is_shift) 
                             & (0x1000U == (0x7000U 
                                            & vlSelf->__PVT__ir)));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        vlSelf->__PVT__shx = vlSelf->__PVT__is_shift;
        if ((0x37U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__X = 0U;
        } else if ((0x17U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
        } else if ((0x6fU == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
        }
        if ((0x37U != (0x7fU & vlSelf->__PVT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->__PVT__ir))) {
                if ((0x6fU != (0x7fU & vlSelf->__PVT__ir))) {
                    if (((IData)((0x40000033U == (0x4000707fU 
                                                  & vlSelf->__PVT__ir))) 
                         | (IData)(vlSelf->__PVT__is_cmp))) {
                        vlSelf->__PVT__inv = 1U;
                    }
                }
            }
        }
        if (vlSelf->__PVT__is_shift) {
            __PVT__we = 1U;
        } else if (__VdfgExtracted_h62388771__0) {
            __PVT__we = 1U;
        } else if (((~ (IData)(vlSelf->__PVT__is_cmp)) 
                    & (IData)(vlSelf->__VdfgTmp_h18c46dac__0))) {
            __PVT__we = 1U;
        }
    } else {
        vlSelf->__PVT__shx = 0U;
        if ((4U == (IData)(vlSelf->__PVT__state))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
            if ((3U == (0x7fU & vlSelf->__PVT__ir))) {
                __PVT__we = 1U;
            } else if (vlSelf->__PVT__is_slt) {
                __PVT__we = 1U;
            } else if ((0x67U == (0x7fU & vlSelf->__PVT__ir))) {
                __PVT__we = 1U;
            }
        } else if ((5U == (IData)(vlSelf->__PVT__state))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
        }
    }
    vlSelf->rw_en = ((IData)(__PVT__we) & (0U != (0x1fU 
                                                  & (vlSelf->__PVT__ir 
                                                     >> 7U))));
    if (vlSelf->__PVT__is_sll) {
        vlSelf->__PVT__sll_dir = vlSelf->__PVT__is_shift;
        vlSelf->__PVT__ia = (0x1ffU & ((IData)(vlSelf->__PVT__k) 
                                       - (IData)(vlSelf->__PVT__shamt_w)));
        vlSelf->__VdfgTmp_h586768a0__0 = ((VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__k)) 
                                           - VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__shamt_w))) 
                                          - (IData)(1U));
    } else {
        vlSelf->__PVT__sll_dir = 0U;
        vlSelf->__PVT__ia = (0x1ffU & ((IData)(vlSelf->__PVT__k) 
                                       + (IData)(vlSelf->__PVT__shamt_w)));
        vlSelf->__VdfgTmp_h586768a0__0 = ((IData)(1U) 
                                          + (VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__k)) 
                                             + VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__shamt_w))));
    }
    vlSelf->d_wdata = ((~ ((IData)(vlSelf->__PVT__shx)
                            ? (0U == (0x1fU & (vlSelf->__PVT__ir 
                                               >> 0xfU)))
                            : (0U == (0x1fU & (vlSelf->__PVT__ir 
                                               >> 0x14U))))) 
                       & (IData)(vlSymsp->TOP.tb_sys5__DOT__dut__DOT__slot__BRA__0__KET____DOT__rqb_b));
    vlSelf->__PVT__exec_done = ((IData)(vlSelf->__PVT__sll_dir)
                                 ? (0U == (IData)(vlSelf->__PVT__k))
                                 : (0x1fU == (IData)(vlSelf->__PVT__k)));
    vlSelf->__PVT__va = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__ia))) 
                         & VL_GTES_III(32, 0x1fU, VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__ia))));
    vlSelf->__PVT__vb = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, 
                                                           (0x1ffU 
                                                            & vlSelf->__VdfgTmp_h586768a0__0))) 
                         & VL_GTES_III(32, 0x1fU, VL_EXTENDS_II(32,9, 
                                                                (0x1ffU 
                                                                 & vlSelf->__VdfgTmp_h586768a0__0))));
    vlSelf->__PVT__Yr = (1U & (((0x33U == (0x7fU & vlSelf->__PVT__ir)) 
                                | (0x63U == (0x7fU 
                                             & vlSelf->__PVT__ir)))
                                ? (IData)(vlSelf->d_wdata)
                                : vlSelf->__PVT__imm_sr));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if ((0x37U != (0x7fU & vlSelf->__PVT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->__PVT__ir))) {
                if ((0x6fU == (0x7fU & vlSelf->__PVT__ir))) {
                    vlSelf->__PVT__Yr = (1U & (4U >> (IData)(vlSelf->__PVT__k)));
                }
            }
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        vlSelf->__PVT__Yr = (1U & (4U >> (IData)(vlSelf->__PVT__k)));
    } else if ((5U == (IData)(vlSelf->__PVT__state))) {
        vlSelf->__PVT__Yr = (1U & (((0x6fU == (0x7fU 
                                               & vlSelf->__PVT__ir)) 
                                    | ((0x63U == (0x7fU 
                                                  & vlSelf->__PVT__ir)) 
                                       & (IData)(__PVT__cond)))
                                    ? vlSelf->__PVT__imm_sr
                                    : (4U >> (IData)(vlSelf->__PVT__k))));
    }
    vlSelf->__PVT__sum_c = (3U & ((IData)(vlSelf->__PVT__X) 
                                  + ((1U & ((IData)(vlSelf->__PVT__inv)
                                             ? (~ (IData)(vlSelf->__PVT__Yr))
                                             : (IData)(vlSelf->__PVT__Yr))) 
                                     + ((0U == (IData)(vlSelf->__PVT__k))
                                         ? (IData)(vlSelf->__PVT__inv)
                                         : (IData)(vlSelf->__PVT__cy)))));
    vlSelf->__PVT__addr_ins = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__addr, 1U) 
                               | VL_SHIFTL_III(32,32,32, 
                                               (1U 
                                                & (IData)(vlSelf->__PVT__sum_c)), 0x1fU));
    vlSelf->__PVT__pc_ins = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__pc, 1U) 
                             | VL_SHIFTL_III(32,32,32, 
                                             (1U & (IData)(vlSelf->__PVT__sum_c)), 0x1fU));
    vlSelf->__PVT__nz_n = (1U & (((0U != (IData)(vlSelf->__PVT__k)) 
                                  & (IData)(vlSelf->__PVT__nz)) 
                                 | (IData)(vlSelf->__PVT__sum_c)));
    vlSelf->__PVT__wd = (1U & (((IData)(vlSelf->__VdfgTmp_h18c46dac__0) 
                                & ((4U == (7U & (vlSelf->__PVT__ir 
                                                 >> 0xcU))) 
                                   | ((6U == (7U & 
                                              (vlSelf->__PVT__ir 
                                               >> 0xcU))) 
                                      | (7U == (7U 
                                                & (vlSelf->__PVT__ir 
                                                   >> 0xcU))))))
                                ? ((4U == (7U & (vlSelf->__PVT__ir 
                                                 >> 0xcU)))
                                    ? ((IData)(vlSelf->__PVT__X) 
                                       ^ (IData)(vlSelf->__PVT__Yr))
                                    : ((6U == (7U & 
                                               (vlSelf->__PVT__ir 
                                                >> 0xcU)))
                                        ? ((IData)(vlSelf->__PVT__X) 
                                           | (IData)(vlSelf->__PVT__Yr))
                                        : ((IData)(vlSelf->__PVT__X) 
                                           & (IData)(vlSelf->__PVT__Yr))))
                                : (IData)(vlSelf->__PVT__sum_c)));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if (vlSelf->__PVT__is_shift) {
            vlSelf->__PVT__wd = (1U & VL_SHIFTR_III(2,2,6, 
                                                    ((((IData)(vlSelf->__PVT__is_sll)
                                                        ? 
                                                       ((IData)(vlSelf->__PVT__va) 
                                                        & (IData)(vlSelf->__PVT__a_val))
                                                        : 
                                                       ((IData)(vlSelf->__PVT__vb)
                                                         ? (IData)(vlSelf->d_wdata)
                                                         : (IData)(vlSelf->__PVT__fill))) 
                                                      << 1U) 
                                                     | ((IData)(vlSelf->__PVT__is_sll)
                                                         ? 
                                                        ((IData)(vlSelf->__PVT__vb) 
                                                         & (IData)(vlSelf->d_wdata))
                                                         : 
                                                        ((IData)(vlSelf->__PVT__va)
                                                          ? (IData)(vlSelf->__PVT__a_val)
                                                          : (IData)(vlSelf->__PVT__fill)))), 
                                                    ((IData)(vlSelf->__PVT__is_sll)
                                                      ? 1U
                                                      : 0U)));
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        if ((3U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__wd = vlSymsp->TOP.tb_sys5__DOT__dut__DOT__slot__BRA__0__KET____DOT__dq_b;
        } else if (vlSelf->__PVT__is_slt) {
            vlSelf->__PVT__wd = ((0U == (IData)(vlSelf->__PVT__k)) 
                                 & ((2U == (7U & (vlSelf->__PVT__ir 
                                                  >> 0xcU)))
                                     ? (IData)(vlSelf->__PVT__f_lt)
                                     : (IData)(vlSelf->__PVT__f_ltu)));
        } else if ((0x67U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__wd = (1U & (IData)(vlSelf->__PVT__sum_c));
        }
    }
}

VL_ATTR_COLD void Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__1__KET____DOT__core__0(Vtb_sys5_uc_core_v2s__W1* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_sys5__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+          Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__1__KET____DOT__core__0\n"); );
    // Init
    CData/*0:0*/ __PVT__cond;
    __PVT__cond = 0;
    CData/*0:0*/ __PVT__we;
    __PVT__we = 0;
    CData/*0:0*/ __VdfgExtracted_h62388771__0;
    __VdfgExtracted_h62388771__0 = 0;
    CData/*0:0*/ __VdfgTmp_h2cd83c5b__0;
    __VdfgTmp_h2cd83c5b__0 = 0;
    CData/*0:0*/ __VdfgTmp_he83b8d53__0;
    __VdfgTmp_he83b8d53__0 = 0;
    CData/*0:0*/ __VdfgTmp_hd9b60348__0;
    __VdfgTmp_hd9b60348__0 = 0;
    CData/*5:0*/ __Vtableidx2;
    __Vtableidx2 = 0;
    // Body
    vlSelf->__PVT__rs2 = (0x1fU & (vlSelf->__PVT__ir 
                                   >> 0x14U));
    vlSelf->__PVT__is_sys = (0x73U == (0x7fU & vlSelf->__PVT__ir));
    vlSelf->__PVT__last_up = (0x1fU == (IData)(vlSelf->__PVT__k));
    vlSelf->__PVT__pc_rot = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__pc, 1U) 
                             | VL_SHIFTL_III(32,32,32, vlSelf->__PVT__pc, 0x1fU));
    vlSelf->__PVT__imm_rot = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__imm_sr, 1U) 
                              | VL_SHIFTL_III(32,32,32, vlSelf->__PVT__imm_sr, 0x1fU));
    vlSelf->__PVT__opc = (0x7fU & vlSelf->__PVT__ir);
    vlSelf->d_addr = (((QData)((IData)((vlSelf->__PVT__addr 
                                        >> 2U))) << 5U) 
                      | (QData)((IData)(vlSelf->__PVT__k)));
    vlSelf->rw_addr = ((0x3e0U & (vlSelf->__PVT__ir 
                                  >> 2U)) | (IData)(vlSelf->__PVT__k));
    __VdfgTmp_h2cd83c5b__0 = ((0x37U == (0x7fU & vlSelf->__PVT__ir)) 
                              | (0x17U == (0x7fU & vlSelf->__PVT__ir)));
    __Vtableidx2 = (((IData)(vlSelf->__PVT__f_eq) << 5U) 
                    | (((IData)(vlSelf->__PVT__f_lt) 
                        << 4U) | (((IData)(vlSelf->__PVT__f_ltu) 
                                   << 3U) | (7U & (vlSelf->__PVT__ir 
                                                   >> 0xcU)))));
    __PVT__cond = Vtb_sys5__ConstPool__TABLE_h2a0441a0_0
        [__Vtableidx2];
    vlSelf->__PVT__a_val = ((0U != (0x1fU & (vlSelf->__PVT__ir 
                                             >> 0xfU))) 
                            & (IData)(vlSymsp->TOP.tb_sys5__DOT__dut__DOT__slot__BRA__1__KET____DOT__rqa_b));
    __VdfgTmp_hd9b60348__0 = ((2U == (7U & (vlSelf->__PVT__ir 
                                            >> 0xcU))) 
                              | (3U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))));
    vlSelf->__VdfgTmp_h18c46dac__0 = ((0x13U == (0x7fU 
                                                 & vlSelf->__PVT__ir)) 
                                      | (0x33U == (0x7fU 
                                                   & vlSelf->__PVT__ir)));
    __VdfgTmp_he83b8d53__0 = ((1U == (7U & (vlSelf->__PVT__ir 
                                            >> 0xcU))) 
                              | (5U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))));
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
    vlSelf->__PVT__X = vlSelf->__PVT__a_val;
    vlSelf->__PVT__is_cmp = ((0x63U == (0x7fU & vlSelf->__PVT__ir)) 
                             | ((IData)(vlSelf->__VdfgTmp_h18c46dac__0) 
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
    vlSelf->__PVT__inv = 0U;
    vlSelf->__PVT__is_shift = ((IData)(vlSelf->__PVT__sh_i) 
                               | ((0x33U == (0x7fU 
                                             & vlSelf->__PVT__ir)) 
                                  & (IData)(__VdfgTmp_he83b8d53__0)));
    __PVT__we = 0U;
    vlSelf->__PVT__fill = ((IData)(vlSelf->__PVT__is_shift) 
                           & (IData)(((0x40005000U 
                                       == (0x40007000U 
                                           & vlSelf->__PVT__ir)) 
                                      & (IData)(vlSelf->__PVT__sgn))));
    vlSelf->__PVT__is_sll = ((IData)(vlSelf->__PVT__is_shift) 
                             & (0x1000U == (0x7000U 
                                            & vlSelf->__PVT__ir)));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        vlSelf->__PVT__shx = vlSelf->__PVT__is_shift;
        if ((0x37U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__X = 0U;
        } else if ((0x17U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
        } else if ((0x6fU == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
        }
        if ((0x37U != (0x7fU & vlSelf->__PVT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->__PVT__ir))) {
                if ((0x6fU != (0x7fU & vlSelf->__PVT__ir))) {
                    if (((IData)((0x40000033U == (0x4000707fU 
                                                  & vlSelf->__PVT__ir))) 
                         | (IData)(vlSelf->__PVT__is_cmp))) {
                        vlSelf->__PVT__inv = 1U;
                    }
                }
            }
        }
        if (vlSelf->__PVT__is_shift) {
            __PVT__we = 1U;
        } else if (__VdfgExtracted_h62388771__0) {
            __PVT__we = 1U;
        } else if (((~ (IData)(vlSelf->__PVT__is_cmp)) 
                    & (IData)(vlSelf->__VdfgTmp_h18c46dac__0))) {
            __PVT__we = 1U;
        }
    } else {
        vlSelf->__PVT__shx = 0U;
        if ((4U == (IData)(vlSelf->__PVT__state))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
            if ((3U == (0x7fU & vlSelf->__PVT__ir))) {
                __PVT__we = 1U;
            } else if (vlSelf->__PVT__is_slt) {
                __PVT__we = 1U;
            } else if ((0x67U == (0x7fU & vlSelf->__PVT__ir))) {
                __PVT__we = 1U;
            }
        } else if ((5U == (IData)(vlSelf->__PVT__state))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
        }
    }
    vlSelf->rw_en = ((IData)(__PVT__we) & (0U != (0x1fU 
                                                  & (vlSelf->__PVT__ir 
                                                     >> 7U))));
    if (vlSelf->__PVT__is_sll) {
        vlSelf->__PVT__sll_dir = vlSelf->__PVT__is_shift;
        vlSelf->__PVT__ia = (0x1ffU & ((IData)(vlSelf->__PVT__k) 
                                       - (IData)(vlSelf->__PVT__shamt_w)));
        vlSelf->__VdfgTmp_h586768a0__0 = ((VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__k)) 
                                           - VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__shamt_w))) 
                                          - (IData)(1U));
    } else {
        vlSelf->__PVT__sll_dir = 0U;
        vlSelf->__PVT__ia = (0x1ffU & ((IData)(vlSelf->__PVT__k) 
                                       + (IData)(vlSelf->__PVT__shamt_w)));
        vlSelf->__VdfgTmp_h586768a0__0 = ((IData)(1U) 
                                          + (VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__k)) 
                                             + VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__shamt_w))));
    }
    vlSelf->d_wdata = ((~ ((IData)(vlSelf->__PVT__shx)
                            ? (0U == (0x1fU & (vlSelf->__PVT__ir 
                                               >> 0xfU)))
                            : (0U == (0x1fU & (vlSelf->__PVT__ir 
                                               >> 0x14U))))) 
                       & (IData)(vlSymsp->TOP.tb_sys5__DOT__dut__DOT__slot__BRA__1__KET____DOT__rqb_b));
    vlSelf->__PVT__exec_done = ((IData)(vlSelf->__PVT__sll_dir)
                                 ? (0U == (IData)(vlSelf->__PVT__k))
                                 : (0x1fU == (IData)(vlSelf->__PVT__k)));
    vlSelf->__PVT__va = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__ia))) 
                         & VL_GTES_III(32, 0x1fU, VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__ia))));
    vlSelf->__PVT__vb = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, 
                                                           (0x1ffU 
                                                            & vlSelf->__VdfgTmp_h586768a0__0))) 
                         & VL_GTES_III(32, 0x1fU, VL_EXTENDS_II(32,9, 
                                                                (0x1ffU 
                                                                 & vlSelf->__VdfgTmp_h586768a0__0))));
    vlSelf->__PVT__Yr = (1U & (((0x33U == (0x7fU & vlSelf->__PVT__ir)) 
                                | (0x63U == (0x7fU 
                                             & vlSelf->__PVT__ir)))
                                ? (IData)(vlSelf->d_wdata)
                                : vlSelf->__PVT__imm_sr));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if ((0x37U != (0x7fU & vlSelf->__PVT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->__PVT__ir))) {
                if ((0x6fU == (0x7fU & vlSelf->__PVT__ir))) {
                    vlSelf->__PVT__Yr = (1U & (4U >> (IData)(vlSelf->__PVT__k)));
                }
            }
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        vlSelf->__PVT__Yr = (1U & (4U >> (IData)(vlSelf->__PVT__k)));
    } else if ((5U == (IData)(vlSelf->__PVT__state))) {
        vlSelf->__PVT__Yr = (1U & (((0x6fU == (0x7fU 
                                               & vlSelf->__PVT__ir)) 
                                    | ((0x63U == (0x7fU 
                                                  & vlSelf->__PVT__ir)) 
                                       & (IData)(__PVT__cond)))
                                    ? vlSelf->__PVT__imm_sr
                                    : (4U >> (IData)(vlSelf->__PVT__k))));
    }
    vlSelf->__PVT__sum_c = (3U & ((IData)(vlSelf->__PVT__X) 
                                  + ((1U & ((IData)(vlSelf->__PVT__inv)
                                             ? (~ (IData)(vlSelf->__PVT__Yr))
                                             : (IData)(vlSelf->__PVT__Yr))) 
                                     + ((0U == (IData)(vlSelf->__PVT__k))
                                         ? (IData)(vlSelf->__PVT__inv)
                                         : (IData)(vlSelf->__PVT__cy)))));
    vlSelf->__PVT__addr_ins = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__addr, 1U) 
                               | VL_SHIFTL_III(32,32,32, 
                                               (1U 
                                                & (IData)(vlSelf->__PVT__sum_c)), 0x1fU));
    vlSelf->__PVT__pc_ins = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__pc, 1U) 
                             | VL_SHIFTL_III(32,32,32, 
                                             (1U & (IData)(vlSelf->__PVT__sum_c)), 0x1fU));
    vlSelf->__PVT__nz_n = (1U & (((0U != (IData)(vlSelf->__PVT__k)) 
                                  & (IData)(vlSelf->__PVT__nz)) 
                                 | (IData)(vlSelf->__PVT__sum_c)));
    vlSelf->__PVT__wd = (1U & (((IData)(vlSelf->__VdfgTmp_h18c46dac__0) 
                                & ((4U == (7U & (vlSelf->__PVT__ir 
                                                 >> 0xcU))) 
                                   | ((6U == (7U & 
                                              (vlSelf->__PVT__ir 
                                               >> 0xcU))) 
                                      | (7U == (7U 
                                                & (vlSelf->__PVT__ir 
                                                   >> 0xcU))))))
                                ? ((4U == (7U & (vlSelf->__PVT__ir 
                                                 >> 0xcU)))
                                    ? ((IData)(vlSelf->__PVT__X) 
                                       ^ (IData)(vlSelf->__PVT__Yr))
                                    : ((6U == (7U & 
                                               (vlSelf->__PVT__ir 
                                                >> 0xcU)))
                                        ? ((IData)(vlSelf->__PVT__X) 
                                           | (IData)(vlSelf->__PVT__Yr))
                                        : ((IData)(vlSelf->__PVT__X) 
                                           & (IData)(vlSelf->__PVT__Yr))))
                                : (IData)(vlSelf->__PVT__sum_c)));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if (vlSelf->__PVT__is_shift) {
            vlSelf->__PVT__wd = (1U & VL_SHIFTR_III(2,2,6, 
                                                    ((((IData)(vlSelf->__PVT__is_sll)
                                                        ? 
                                                       ((IData)(vlSelf->__PVT__va) 
                                                        & (IData)(vlSelf->__PVT__a_val))
                                                        : 
                                                       ((IData)(vlSelf->__PVT__vb)
                                                         ? (IData)(vlSelf->d_wdata)
                                                         : (IData)(vlSelf->__PVT__fill))) 
                                                      << 1U) 
                                                     | ((IData)(vlSelf->__PVT__is_sll)
                                                         ? 
                                                        ((IData)(vlSelf->__PVT__vb) 
                                                         & (IData)(vlSelf->d_wdata))
                                                         : 
                                                        ((IData)(vlSelf->__PVT__va)
                                                          ? (IData)(vlSelf->__PVT__a_val)
                                                          : (IData)(vlSelf->__PVT__fill)))), 
                                                    ((IData)(vlSelf->__PVT__is_sll)
                                                      ? 1U
                                                      : 0U)));
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        if ((3U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__wd = vlSymsp->TOP.tb_sys5__DOT__dut__DOT__slot__BRA__1__KET____DOT__dq_b;
        } else if (vlSelf->__PVT__is_slt) {
            vlSelf->__PVT__wd = ((0U == (IData)(vlSelf->__PVT__k)) 
                                 & ((2U == (7U & (vlSelf->__PVT__ir 
                                                  >> 0xcU)))
                                     ? (IData)(vlSelf->__PVT__f_lt)
                                     : (IData)(vlSelf->__PVT__f_ltu)));
        } else if ((0x67U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__wd = (1U & (IData)(vlSelf->__PVT__sum_c));
        }
    }
}

VL_ATTR_COLD void Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__2__KET____DOT__core__0(Vtb_sys5_uc_core_v2s__W1* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_sys5__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+          Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__2__KET____DOT__core__0\n"); );
    // Init
    CData/*0:0*/ __PVT__cond;
    __PVT__cond = 0;
    CData/*0:0*/ __PVT__we;
    __PVT__we = 0;
    CData/*0:0*/ __VdfgExtracted_h62388771__0;
    __VdfgExtracted_h62388771__0 = 0;
    CData/*0:0*/ __VdfgTmp_h2cd83c5b__0;
    __VdfgTmp_h2cd83c5b__0 = 0;
    CData/*0:0*/ __VdfgTmp_he83b8d53__0;
    __VdfgTmp_he83b8d53__0 = 0;
    CData/*0:0*/ __VdfgTmp_hd9b60348__0;
    __VdfgTmp_hd9b60348__0 = 0;
    CData/*5:0*/ __Vtableidx3;
    __Vtableidx3 = 0;
    // Body
    vlSelf->__PVT__rs2 = (0x1fU & (vlSelf->__PVT__ir 
                                   >> 0x14U));
    vlSelf->__PVT__is_sys = (0x73U == (0x7fU & vlSelf->__PVT__ir));
    vlSelf->__PVT__last_up = (0x1fU == (IData)(vlSelf->__PVT__k));
    vlSelf->__PVT__pc_rot = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__pc, 1U) 
                             | VL_SHIFTL_III(32,32,32, vlSelf->__PVT__pc, 0x1fU));
    vlSelf->__PVT__imm_rot = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__imm_sr, 1U) 
                              | VL_SHIFTL_III(32,32,32, vlSelf->__PVT__imm_sr, 0x1fU));
    vlSelf->__PVT__opc = (0x7fU & vlSelf->__PVT__ir);
    vlSelf->d_addr = (((QData)((IData)((vlSelf->__PVT__addr 
                                        >> 2U))) << 5U) 
                      | (QData)((IData)(vlSelf->__PVT__k)));
    vlSelf->rw_addr = ((0x3e0U & (vlSelf->__PVT__ir 
                                  >> 2U)) | (IData)(vlSelf->__PVT__k));
    __VdfgTmp_h2cd83c5b__0 = ((0x37U == (0x7fU & vlSelf->__PVT__ir)) 
                              | (0x17U == (0x7fU & vlSelf->__PVT__ir)));
    __Vtableidx3 = (((IData)(vlSelf->__PVT__f_eq) << 5U) 
                    | (((IData)(vlSelf->__PVT__f_lt) 
                        << 4U) | (((IData)(vlSelf->__PVT__f_ltu) 
                                   << 3U) | (7U & (vlSelf->__PVT__ir 
                                                   >> 0xcU)))));
    __PVT__cond = Vtb_sys5__ConstPool__TABLE_h2a0441a0_0
        [__Vtableidx3];
    vlSelf->__PVT__a_val = ((0U != (0x1fU & (vlSelf->__PVT__ir 
                                             >> 0xfU))) 
                            & (IData)(vlSymsp->TOP.tb_sys5__DOT__dut__DOT__slot__BRA__2__KET____DOT__rqa_b));
    __VdfgTmp_hd9b60348__0 = ((2U == (7U & (vlSelf->__PVT__ir 
                                            >> 0xcU))) 
                              | (3U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))));
    vlSelf->__VdfgTmp_h18c46dac__0 = ((0x13U == (0x7fU 
                                                 & vlSelf->__PVT__ir)) 
                                      | (0x33U == (0x7fU 
                                                   & vlSelf->__PVT__ir)));
    __VdfgTmp_he83b8d53__0 = ((1U == (7U & (vlSelf->__PVT__ir 
                                            >> 0xcU))) 
                              | (5U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))));
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
    vlSelf->__PVT__X = vlSelf->__PVT__a_val;
    vlSelf->__PVT__is_cmp = ((0x63U == (0x7fU & vlSelf->__PVT__ir)) 
                             | ((IData)(vlSelf->__VdfgTmp_h18c46dac__0) 
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
    vlSelf->__PVT__inv = 0U;
    vlSelf->__PVT__is_shift = ((IData)(vlSelf->__PVT__sh_i) 
                               | ((0x33U == (0x7fU 
                                             & vlSelf->__PVT__ir)) 
                                  & (IData)(__VdfgTmp_he83b8d53__0)));
    __PVT__we = 0U;
    vlSelf->__PVT__fill = ((IData)(vlSelf->__PVT__is_shift) 
                           & (IData)(((0x40005000U 
                                       == (0x40007000U 
                                           & vlSelf->__PVT__ir)) 
                                      & (IData)(vlSelf->__PVT__sgn))));
    vlSelf->__PVT__is_sll = ((IData)(vlSelf->__PVT__is_shift) 
                             & (0x1000U == (0x7000U 
                                            & vlSelf->__PVT__ir)));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        vlSelf->__PVT__shx = vlSelf->__PVT__is_shift;
        if ((0x37U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__X = 0U;
        } else if ((0x17U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
        } else if ((0x6fU == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
        }
        if ((0x37U != (0x7fU & vlSelf->__PVT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->__PVT__ir))) {
                if ((0x6fU != (0x7fU & vlSelf->__PVT__ir))) {
                    if (((IData)((0x40000033U == (0x4000707fU 
                                                  & vlSelf->__PVT__ir))) 
                         | (IData)(vlSelf->__PVT__is_cmp))) {
                        vlSelf->__PVT__inv = 1U;
                    }
                }
            }
        }
        if (vlSelf->__PVT__is_shift) {
            __PVT__we = 1U;
        } else if (__VdfgExtracted_h62388771__0) {
            __PVT__we = 1U;
        } else if (((~ (IData)(vlSelf->__PVT__is_cmp)) 
                    & (IData)(vlSelf->__VdfgTmp_h18c46dac__0))) {
            __PVT__we = 1U;
        }
    } else {
        vlSelf->__PVT__shx = 0U;
        if ((4U == (IData)(vlSelf->__PVT__state))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
            if ((3U == (0x7fU & vlSelf->__PVT__ir))) {
                __PVT__we = 1U;
            } else if (vlSelf->__PVT__is_slt) {
                __PVT__we = 1U;
            } else if ((0x67U == (0x7fU & vlSelf->__PVT__ir))) {
                __PVT__we = 1U;
            }
        } else if ((5U == (IData)(vlSelf->__PVT__state))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
        }
    }
    vlSelf->rw_en = ((IData)(__PVT__we) & (0U != (0x1fU 
                                                  & (vlSelf->__PVT__ir 
                                                     >> 7U))));
    if (vlSelf->__PVT__is_sll) {
        vlSelf->__PVT__sll_dir = vlSelf->__PVT__is_shift;
        vlSelf->__PVT__ia = (0x1ffU & ((IData)(vlSelf->__PVT__k) 
                                       - (IData)(vlSelf->__PVT__shamt_w)));
        vlSelf->__VdfgTmp_h586768a0__0 = ((VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__k)) 
                                           - VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__shamt_w))) 
                                          - (IData)(1U));
    } else {
        vlSelf->__PVT__sll_dir = 0U;
        vlSelf->__PVT__ia = (0x1ffU & ((IData)(vlSelf->__PVT__k) 
                                       + (IData)(vlSelf->__PVT__shamt_w)));
        vlSelf->__VdfgTmp_h586768a0__0 = ((IData)(1U) 
                                          + (VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__k)) 
                                             + VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__shamt_w))));
    }
    vlSelf->d_wdata = ((~ ((IData)(vlSelf->__PVT__shx)
                            ? (0U == (0x1fU & (vlSelf->__PVT__ir 
                                               >> 0xfU)))
                            : (0U == (0x1fU & (vlSelf->__PVT__ir 
                                               >> 0x14U))))) 
                       & (IData)(vlSymsp->TOP.tb_sys5__DOT__dut__DOT__slot__BRA__2__KET____DOT__rqb_b));
    vlSelf->__PVT__exec_done = ((IData)(vlSelf->__PVT__sll_dir)
                                 ? (0U == (IData)(vlSelf->__PVT__k))
                                 : (0x1fU == (IData)(vlSelf->__PVT__k)));
    vlSelf->__PVT__va = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__ia))) 
                         & VL_GTES_III(32, 0x1fU, VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__ia))));
    vlSelf->__PVT__vb = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, 
                                                           (0x1ffU 
                                                            & vlSelf->__VdfgTmp_h586768a0__0))) 
                         & VL_GTES_III(32, 0x1fU, VL_EXTENDS_II(32,9, 
                                                                (0x1ffU 
                                                                 & vlSelf->__VdfgTmp_h586768a0__0))));
    vlSelf->__PVT__Yr = (1U & (((0x33U == (0x7fU & vlSelf->__PVT__ir)) 
                                | (0x63U == (0x7fU 
                                             & vlSelf->__PVT__ir)))
                                ? (IData)(vlSelf->d_wdata)
                                : vlSelf->__PVT__imm_sr));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if ((0x37U != (0x7fU & vlSelf->__PVT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->__PVT__ir))) {
                if ((0x6fU == (0x7fU & vlSelf->__PVT__ir))) {
                    vlSelf->__PVT__Yr = (1U & (4U >> (IData)(vlSelf->__PVT__k)));
                }
            }
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        vlSelf->__PVT__Yr = (1U & (4U >> (IData)(vlSelf->__PVT__k)));
    } else if ((5U == (IData)(vlSelf->__PVT__state))) {
        vlSelf->__PVT__Yr = (1U & (((0x6fU == (0x7fU 
                                               & vlSelf->__PVT__ir)) 
                                    | ((0x63U == (0x7fU 
                                                  & vlSelf->__PVT__ir)) 
                                       & (IData)(__PVT__cond)))
                                    ? vlSelf->__PVT__imm_sr
                                    : (4U >> (IData)(vlSelf->__PVT__k))));
    }
    vlSelf->__PVT__sum_c = (3U & ((IData)(vlSelf->__PVT__X) 
                                  + ((1U & ((IData)(vlSelf->__PVT__inv)
                                             ? (~ (IData)(vlSelf->__PVT__Yr))
                                             : (IData)(vlSelf->__PVT__Yr))) 
                                     + ((0U == (IData)(vlSelf->__PVT__k))
                                         ? (IData)(vlSelf->__PVT__inv)
                                         : (IData)(vlSelf->__PVT__cy)))));
    vlSelf->__PVT__addr_ins = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__addr, 1U) 
                               | VL_SHIFTL_III(32,32,32, 
                                               (1U 
                                                & (IData)(vlSelf->__PVT__sum_c)), 0x1fU));
    vlSelf->__PVT__pc_ins = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__pc, 1U) 
                             | VL_SHIFTL_III(32,32,32, 
                                             (1U & (IData)(vlSelf->__PVT__sum_c)), 0x1fU));
    vlSelf->__PVT__nz_n = (1U & (((0U != (IData)(vlSelf->__PVT__k)) 
                                  & (IData)(vlSelf->__PVT__nz)) 
                                 | (IData)(vlSelf->__PVT__sum_c)));
    vlSelf->__PVT__wd = (1U & (((IData)(vlSelf->__VdfgTmp_h18c46dac__0) 
                                & ((4U == (7U & (vlSelf->__PVT__ir 
                                                 >> 0xcU))) 
                                   | ((6U == (7U & 
                                              (vlSelf->__PVT__ir 
                                               >> 0xcU))) 
                                      | (7U == (7U 
                                                & (vlSelf->__PVT__ir 
                                                   >> 0xcU))))))
                                ? ((4U == (7U & (vlSelf->__PVT__ir 
                                                 >> 0xcU)))
                                    ? ((IData)(vlSelf->__PVT__X) 
                                       ^ (IData)(vlSelf->__PVT__Yr))
                                    : ((6U == (7U & 
                                               (vlSelf->__PVT__ir 
                                                >> 0xcU)))
                                        ? ((IData)(vlSelf->__PVT__X) 
                                           | (IData)(vlSelf->__PVT__Yr))
                                        : ((IData)(vlSelf->__PVT__X) 
                                           & (IData)(vlSelf->__PVT__Yr))))
                                : (IData)(vlSelf->__PVT__sum_c)));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if (vlSelf->__PVT__is_shift) {
            vlSelf->__PVT__wd = (1U & VL_SHIFTR_III(2,2,6, 
                                                    ((((IData)(vlSelf->__PVT__is_sll)
                                                        ? 
                                                       ((IData)(vlSelf->__PVT__va) 
                                                        & (IData)(vlSelf->__PVT__a_val))
                                                        : 
                                                       ((IData)(vlSelf->__PVT__vb)
                                                         ? (IData)(vlSelf->d_wdata)
                                                         : (IData)(vlSelf->__PVT__fill))) 
                                                      << 1U) 
                                                     | ((IData)(vlSelf->__PVT__is_sll)
                                                         ? 
                                                        ((IData)(vlSelf->__PVT__vb) 
                                                         & (IData)(vlSelf->d_wdata))
                                                         : 
                                                        ((IData)(vlSelf->__PVT__va)
                                                          ? (IData)(vlSelf->__PVT__a_val)
                                                          : (IData)(vlSelf->__PVT__fill)))), 
                                                    ((IData)(vlSelf->__PVT__is_sll)
                                                      ? 1U
                                                      : 0U)));
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        if ((3U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__wd = vlSymsp->TOP.tb_sys5__DOT__dut__DOT__slot__BRA__2__KET____DOT__dq_b;
        } else if (vlSelf->__PVT__is_slt) {
            vlSelf->__PVT__wd = ((0U == (IData)(vlSelf->__PVT__k)) 
                                 & ((2U == (7U & (vlSelf->__PVT__ir 
                                                  >> 0xcU)))
                                     ? (IData)(vlSelf->__PVT__f_lt)
                                     : (IData)(vlSelf->__PVT__f_ltu)));
        } else if ((0x67U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__wd = (1U & (IData)(vlSelf->__PVT__sum_c));
        }
    }
}

VL_ATTR_COLD void Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__3__KET____DOT__core__0(Vtb_sys5_uc_core_v2s__W1* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_sys5__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+          Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__3__KET____DOT__core__0\n"); );
    // Init
    CData/*0:0*/ __PVT__cond;
    __PVT__cond = 0;
    CData/*0:0*/ __PVT__we;
    __PVT__we = 0;
    CData/*0:0*/ __VdfgExtracted_h62388771__0;
    __VdfgExtracted_h62388771__0 = 0;
    CData/*0:0*/ __VdfgTmp_h2cd83c5b__0;
    __VdfgTmp_h2cd83c5b__0 = 0;
    CData/*0:0*/ __VdfgTmp_he83b8d53__0;
    __VdfgTmp_he83b8d53__0 = 0;
    CData/*0:0*/ __VdfgTmp_hd9b60348__0;
    __VdfgTmp_hd9b60348__0 = 0;
    CData/*5:0*/ __Vtableidx4;
    __Vtableidx4 = 0;
    // Body
    vlSelf->__PVT__rs2 = (0x1fU & (vlSelf->__PVT__ir 
                                   >> 0x14U));
    vlSelf->__PVT__is_sys = (0x73U == (0x7fU & vlSelf->__PVT__ir));
    vlSelf->__PVT__last_up = (0x1fU == (IData)(vlSelf->__PVT__k));
    vlSelf->__PVT__pc_rot = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__pc, 1U) 
                             | VL_SHIFTL_III(32,32,32, vlSelf->__PVT__pc, 0x1fU));
    vlSelf->__PVT__imm_rot = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__imm_sr, 1U) 
                              | VL_SHIFTL_III(32,32,32, vlSelf->__PVT__imm_sr, 0x1fU));
    vlSelf->__PVT__opc = (0x7fU & vlSelf->__PVT__ir);
    vlSelf->d_addr = (((QData)((IData)((vlSelf->__PVT__addr 
                                        >> 2U))) << 5U) 
                      | (QData)((IData)(vlSelf->__PVT__k)));
    vlSelf->rw_addr = ((0x3e0U & (vlSelf->__PVT__ir 
                                  >> 2U)) | (IData)(vlSelf->__PVT__k));
    __VdfgTmp_h2cd83c5b__0 = ((0x37U == (0x7fU & vlSelf->__PVT__ir)) 
                              | (0x17U == (0x7fU & vlSelf->__PVT__ir)));
    __Vtableidx4 = (((IData)(vlSelf->__PVT__f_eq) << 5U) 
                    | (((IData)(vlSelf->__PVT__f_lt) 
                        << 4U) | (((IData)(vlSelf->__PVT__f_ltu) 
                                   << 3U) | (7U & (vlSelf->__PVT__ir 
                                                   >> 0xcU)))));
    __PVT__cond = Vtb_sys5__ConstPool__TABLE_h2a0441a0_0
        [__Vtableidx4];
    vlSelf->__PVT__a_val = ((0U != (0x1fU & (vlSelf->__PVT__ir 
                                             >> 0xfU))) 
                            & (IData)(vlSymsp->TOP.tb_sys5__DOT__dut__DOT__slot__BRA__3__KET____DOT__rqa_b));
    __VdfgTmp_hd9b60348__0 = ((2U == (7U & (vlSelf->__PVT__ir 
                                            >> 0xcU))) 
                              | (3U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))));
    vlSelf->__VdfgTmp_h18c46dac__0 = ((0x13U == (0x7fU 
                                                 & vlSelf->__PVT__ir)) 
                                      | (0x33U == (0x7fU 
                                                   & vlSelf->__PVT__ir)));
    __VdfgTmp_he83b8d53__0 = ((1U == (7U & (vlSelf->__PVT__ir 
                                            >> 0xcU))) 
                              | (5U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))));
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
    vlSelf->__PVT__X = vlSelf->__PVT__a_val;
    vlSelf->__PVT__is_cmp = ((0x63U == (0x7fU & vlSelf->__PVT__ir)) 
                             | ((IData)(vlSelf->__VdfgTmp_h18c46dac__0) 
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
    vlSelf->__PVT__inv = 0U;
    vlSelf->__PVT__is_shift = ((IData)(vlSelf->__PVT__sh_i) 
                               | ((0x33U == (0x7fU 
                                             & vlSelf->__PVT__ir)) 
                                  & (IData)(__VdfgTmp_he83b8d53__0)));
    __PVT__we = 0U;
    vlSelf->__PVT__fill = ((IData)(vlSelf->__PVT__is_shift) 
                           & (IData)(((0x40005000U 
                                       == (0x40007000U 
                                           & vlSelf->__PVT__ir)) 
                                      & (IData)(vlSelf->__PVT__sgn))));
    vlSelf->__PVT__is_sll = ((IData)(vlSelf->__PVT__is_shift) 
                             & (0x1000U == (0x7000U 
                                            & vlSelf->__PVT__ir)));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        vlSelf->__PVT__shx = vlSelf->__PVT__is_shift;
        if ((0x37U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__X = 0U;
        } else if ((0x17U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
        } else if ((0x6fU == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
        }
        if ((0x37U != (0x7fU & vlSelf->__PVT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->__PVT__ir))) {
                if ((0x6fU != (0x7fU & vlSelf->__PVT__ir))) {
                    if (((IData)((0x40000033U == (0x4000707fU 
                                                  & vlSelf->__PVT__ir))) 
                         | (IData)(vlSelf->__PVT__is_cmp))) {
                        vlSelf->__PVT__inv = 1U;
                    }
                }
            }
        }
        if (vlSelf->__PVT__is_shift) {
            __PVT__we = 1U;
        } else if (__VdfgExtracted_h62388771__0) {
            __PVT__we = 1U;
        } else if (((~ (IData)(vlSelf->__PVT__is_cmp)) 
                    & (IData)(vlSelf->__VdfgTmp_h18c46dac__0))) {
            __PVT__we = 1U;
        }
    } else {
        vlSelf->__PVT__shx = 0U;
        if ((4U == (IData)(vlSelf->__PVT__state))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
            if ((3U == (0x7fU & vlSelf->__PVT__ir))) {
                __PVT__we = 1U;
            } else if (vlSelf->__PVT__is_slt) {
                __PVT__we = 1U;
            } else if ((0x67U == (0x7fU & vlSelf->__PVT__ir))) {
                __PVT__we = 1U;
            }
        } else if ((5U == (IData)(vlSelf->__PVT__state))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
        }
    }
    vlSelf->rw_en = ((IData)(__PVT__we) & (0U != (0x1fU 
                                                  & (vlSelf->__PVT__ir 
                                                     >> 7U))));
    if (vlSelf->__PVT__is_sll) {
        vlSelf->__PVT__sll_dir = vlSelf->__PVT__is_shift;
        vlSelf->__PVT__ia = (0x1ffU & ((IData)(vlSelf->__PVT__k) 
                                       - (IData)(vlSelf->__PVT__shamt_w)));
        vlSelf->__VdfgTmp_h586768a0__0 = ((VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__k)) 
                                           - VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__shamt_w))) 
                                          - (IData)(1U));
    } else {
        vlSelf->__PVT__sll_dir = 0U;
        vlSelf->__PVT__ia = (0x1ffU & ((IData)(vlSelf->__PVT__k) 
                                       + (IData)(vlSelf->__PVT__shamt_w)));
        vlSelf->__VdfgTmp_h586768a0__0 = ((IData)(1U) 
                                          + (VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__k)) 
                                             + VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__shamt_w))));
    }
    vlSelf->d_wdata = ((~ ((IData)(vlSelf->__PVT__shx)
                            ? (0U == (0x1fU & (vlSelf->__PVT__ir 
                                               >> 0xfU)))
                            : (0U == (0x1fU & (vlSelf->__PVT__ir 
                                               >> 0x14U))))) 
                       & (IData)(vlSymsp->TOP.tb_sys5__DOT__dut__DOT__slot__BRA__3__KET____DOT__rqb_b));
    vlSelf->__PVT__exec_done = ((IData)(vlSelf->__PVT__sll_dir)
                                 ? (0U == (IData)(vlSelf->__PVT__k))
                                 : (0x1fU == (IData)(vlSelf->__PVT__k)));
    vlSelf->__PVT__va = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__ia))) 
                         & VL_GTES_III(32, 0x1fU, VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__ia))));
    vlSelf->__PVT__vb = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, 
                                                           (0x1ffU 
                                                            & vlSelf->__VdfgTmp_h586768a0__0))) 
                         & VL_GTES_III(32, 0x1fU, VL_EXTENDS_II(32,9, 
                                                                (0x1ffU 
                                                                 & vlSelf->__VdfgTmp_h586768a0__0))));
    vlSelf->__PVT__Yr = (1U & (((0x33U == (0x7fU & vlSelf->__PVT__ir)) 
                                | (0x63U == (0x7fU 
                                             & vlSelf->__PVT__ir)))
                                ? (IData)(vlSelf->d_wdata)
                                : vlSelf->__PVT__imm_sr));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if ((0x37U != (0x7fU & vlSelf->__PVT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->__PVT__ir))) {
                if ((0x6fU == (0x7fU & vlSelf->__PVT__ir))) {
                    vlSelf->__PVT__Yr = (1U & (4U >> (IData)(vlSelf->__PVT__k)));
                }
            }
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        vlSelf->__PVT__Yr = (1U & (4U >> (IData)(vlSelf->__PVT__k)));
    } else if ((5U == (IData)(vlSelf->__PVT__state))) {
        vlSelf->__PVT__Yr = (1U & (((0x6fU == (0x7fU 
                                               & vlSelf->__PVT__ir)) 
                                    | ((0x63U == (0x7fU 
                                                  & vlSelf->__PVT__ir)) 
                                       & (IData)(__PVT__cond)))
                                    ? vlSelf->__PVT__imm_sr
                                    : (4U >> (IData)(vlSelf->__PVT__k))));
    }
    vlSelf->__PVT__sum_c = (3U & ((IData)(vlSelf->__PVT__X) 
                                  + ((1U & ((IData)(vlSelf->__PVT__inv)
                                             ? (~ (IData)(vlSelf->__PVT__Yr))
                                             : (IData)(vlSelf->__PVT__Yr))) 
                                     + ((0U == (IData)(vlSelf->__PVT__k))
                                         ? (IData)(vlSelf->__PVT__inv)
                                         : (IData)(vlSelf->__PVT__cy)))));
    vlSelf->__PVT__addr_ins = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__addr, 1U) 
                               | VL_SHIFTL_III(32,32,32, 
                                               (1U 
                                                & (IData)(vlSelf->__PVT__sum_c)), 0x1fU));
    vlSelf->__PVT__pc_ins = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__pc, 1U) 
                             | VL_SHIFTL_III(32,32,32, 
                                             (1U & (IData)(vlSelf->__PVT__sum_c)), 0x1fU));
    vlSelf->__PVT__nz_n = (1U & (((0U != (IData)(vlSelf->__PVT__k)) 
                                  & (IData)(vlSelf->__PVT__nz)) 
                                 | (IData)(vlSelf->__PVT__sum_c)));
    vlSelf->__PVT__wd = (1U & (((IData)(vlSelf->__VdfgTmp_h18c46dac__0) 
                                & ((4U == (7U & (vlSelf->__PVT__ir 
                                                 >> 0xcU))) 
                                   | ((6U == (7U & 
                                              (vlSelf->__PVT__ir 
                                               >> 0xcU))) 
                                      | (7U == (7U 
                                                & (vlSelf->__PVT__ir 
                                                   >> 0xcU))))))
                                ? ((4U == (7U & (vlSelf->__PVT__ir 
                                                 >> 0xcU)))
                                    ? ((IData)(vlSelf->__PVT__X) 
                                       ^ (IData)(vlSelf->__PVT__Yr))
                                    : ((6U == (7U & 
                                               (vlSelf->__PVT__ir 
                                                >> 0xcU)))
                                        ? ((IData)(vlSelf->__PVT__X) 
                                           | (IData)(vlSelf->__PVT__Yr))
                                        : ((IData)(vlSelf->__PVT__X) 
                                           & (IData)(vlSelf->__PVT__Yr))))
                                : (IData)(vlSelf->__PVT__sum_c)));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if (vlSelf->__PVT__is_shift) {
            vlSelf->__PVT__wd = (1U & VL_SHIFTR_III(2,2,6, 
                                                    ((((IData)(vlSelf->__PVT__is_sll)
                                                        ? 
                                                       ((IData)(vlSelf->__PVT__va) 
                                                        & (IData)(vlSelf->__PVT__a_val))
                                                        : 
                                                       ((IData)(vlSelf->__PVT__vb)
                                                         ? (IData)(vlSelf->d_wdata)
                                                         : (IData)(vlSelf->__PVT__fill))) 
                                                      << 1U) 
                                                     | ((IData)(vlSelf->__PVT__is_sll)
                                                         ? 
                                                        ((IData)(vlSelf->__PVT__vb) 
                                                         & (IData)(vlSelf->d_wdata))
                                                         : 
                                                        ((IData)(vlSelf->__PVT__va)
                                                          ? (IData)(vlSelf->__PVT__a_val)
                                                          : (IData)(vlSelf->__PVT__fill)))), 
                                                    ((IData)(vlSelf->__PVT__is_sll)
                                                      ? 1U
                                                      : 0U)));
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        if ((3U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__wd = vlSymsp->TOP.tb_sys5__DOT__dut__DOT__slot__BRA__3__KET____DOT__dq_b;
        } else if (vlSelf->__PVT__is_slt) {
            vlSelf->__PVT__wd = ((0U == (IData)(vlSelf->__PVT__k)) 
                                 & ((2U == (7U & (vlSelf->__PVT__ir 
                                                  >> 0xcU)))
                                     ? (IData)(vlSelf->__PVT__f_lt)
                                     : (IData)(vlSelf->__PVT__f_ltu)));
        } else if ((0x67U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__wd = (1U & (IData)(vlSelf->__PVT__sum_c));
        }
    }
}

VL_ATTR_COLD void Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__4__KET____DOT__core__0(Vtb_sys5_uc_core_v2s__W1* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_sys5__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+          Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__4__KET____DOT__core__0\n"); );
    // Init
    CData/*0:0*/ __PVT__cond;
    __PVT__cond = 0;
    CData/*0:0*/ __PVT__we;
    __PVT__we = 0;
    CData/*0:0*/ __VdfgExtracted_h62388771__0;
    __VdfgExtracted_h62388771__0 = 0;
    CData/*0:0*/ __VdfgTmp_h2cd83c5b__0;
    __VdfgTmp_h2cd83c5b__0 = 0;
    CData/*0:0*/ __VdfgTmp_he83b8d53__0;
    __VdfgTmp_he83b8d53__0 = 0;
    CData/*0:0*/ __VdfgTmp_hd9b60348__0;
    __VdfgTmp_hd9b60348__0 = 0;
    CData/*5:0*/ __Vtableidx5;
    __Vtableidx5 = 0;
    // Body
    vlSelf->__PVT__rs2 = (0x1fU & (vlSelf->__PVT__ir 
                                   >> 0x14U));
    vlSelf->__PVT__is_sys = (0x73U == (0x7fU & vlSelf->__PVT__ir));
    vlSelf->__PVT__last_up = (0x1fU == (IData)(vlSelf->__PVT__k));
    vlSelf->__PVT__pc_rot = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__pc, 1U) 
                             | VL_SHIFTL_III(32,32,32, vlSelf->__PVT__pc, 0x1fU));
    vlSelf->__PVT__imm_rot = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__imm_sr, 1U) 
                              | VL_SHIFTL_III(32,32,32, vlSelf->__PVT__imm_sr, 0x1fU));
    vlSelf->__PVT__opc = (0x7fU & vlSelf->__PVT__ir);
    vlSelf->d_addr = (((QData)((IData)((vlSelf->__PVT__addr 
                                        >> 2U))) << 5U) 
                      | (QData)((IData)(vlSelf->__PVT__k)));
    vlSelf->rw_addr = ((0x3e0U & (vlSelf->__PVT__ir 
                                  >> 2U)) | (IData)(vlSelf->__PVT__k));
    __VdfgTmp_h2cd83c5b__0 = ((0x37U == (0x7fU & vlSelf->__PVT__ir)) 
                              | (0x17U == (0x7fU & vlSelf->__PVT__ir)));
    __Vtableidx5 = (((IData)(vlSelf->__PVT__f_eq) << 5U) 
                    | (((IData)(vlSelf->__PVT__f_lt) 
                        << 4U) | (((IData)(vlSelf->__PVT__f_ltu) 
                                   << 3U) | (7U & (vlSelf->__PVT__ir 
                                                   >> 0xcU)))));
    __PVT__cond = Vtb_sys5__ConstPool__TABLE_h2a0441a0_0
        [__Vtableidx5];
    vlSelf->__PVT__a_val = ((0U != (0x1fU & (vlSelf->__PVT__ir 
                                             >> 0xfU))) 
                            & (IData)(vlSymsp->TOP.tb_sys5__DOT__dut__DOT__slot__BRA__4__KET____DOT__rqa_b));
    __VdfgTmp_hd9b60348__0 = ((2U == (7U & (vlSelf->__PVT__ir 
                                            >> 0xcU))) 
                              | (3U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))));
    vlSelf->__VdfgTmp_h18c46dac__0 = ((0x13U == (0x7fU 
                                                 & vlSelf->__PVT__ir)) 
                                      | (0x33U == (0x7fU 
                                                   & vlSelf->__PVT__ir)));
    __VdfgTmp_he83b8d53__0 = ((1U == (7U & (vlSelf->__PVT__ir 
                                            >> 0xcU))) 
                              | (5U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))));
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
    vlSelf->__PVT__X = vlSelf->__PVT__a_val;
    vlSelf->__PVT__is_cmp = ((0x63U == (0x7fU & vlSelf->__PVT__ir)) 
                             | ((IData)(vlSelf->__VdfgTmp_h18c46dac__0) 
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
    vlSelf->__PVT__inv = 0U;
    vlSelf->__PVT__is_shift = ((IData)(vlSelf->__PVT__sh_i) 
                               | ((0x33U == (0x7fU 
                                             & vlSelf->__PVT__ir)) 
                                  & (IData)(__VdfgTmp_he83b8d53__0)));
    __PVT__we = 0U;
    vlSelf->__PVT__fill = ((IData)(vlSelf->__PVT__is_shift) 
                           & (IData)(((0x40005000U 
                                       == (0x40007000U 
                                           & vlSelf->__PVT__ir)) 
                                      & (IData)(vlSelf->__PVT__sgn))));
    vlSelf->__PVT__is_sll = ((IData)(vlSelf->__PVT__is_shift) 
                             & (0x1000U == (0x7000U 
                                            & vlSelf->__PVT__ir)));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        vlSelf->__PVT__shx = vlSelf->__PVT__is_shift;
        if ((0x37U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__X = 0U;
        } else if ((0x17U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
        } else if ((0x6fU == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
        }
        if ((0x37U != (0x7fU & vlSelf->__PVT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->__PVT__ir))) {
                if ((0x6fU != (0x7fU & vlSelf->__PVT__ir))) {
                    if (((IData)((0x40000033U == (0x4000707fU 
                                                  & vlSelf->__PVT__ir))) 
                         | (IData)(vlSelf->__PVT__is_cmp))) {
                        vlSelf->__PVT__inv = 1U;
                    }
                }
            }
        }
        if (vlSelf->__PVT__is_shift) {
            __PVT__we = 1U;
        } else if (__VdfgExtracted_h62388771__0) {
            __PVT__we = 1U;
        } else if (((~ (IData)(vlSelf->__PVT__is_cmp)) 
                    & (IData)(vlSelf->__VdfgTmp_h18c46dac__0))) {
            __PVT__we = 1U;
        }
    } else {
        vlSelf->__PVT__shx = 0U;
        if ((4U == (IData)(vlSelf->__PVT__state))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
            if ((3U == (0x7fU & vlSelf->__PVT__ir))) {
                __PVT__we = 1U;
            } else if (vlSelf->__PVT__is_slt) {
                __PVT__we = 1U;
            } else if ((0x67U == (0x7fU & vlSelf->__PVT__ir))) {
                __PVT__we = 1U;
            }
        } else if ((5U == (IData)(vlSelf->__PVT__state))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
        }
    }
    vlSelf->rw_en = ((IData)(__PVT__we) & (0U != (0x1fU 
                                                  & (vlSelf->__PVT__ir 
                                                     >> 7U))));
    if (vlSelf->__PVT__is_sll) {
        vlSelf->__PVT__sll_dir = vlSelf->__PVT__is_shift;
        vlSelf->__PVT__ia = (0x1ffU & ((IData)(vlSelf->__PVT__k) 
                                       - (IData)(vlSelf->__PVT__shamt_w)));
        vlSelf->__VdfgTmp_h586768a0__0 = ((VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__k)) 
                                           - VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__shamt_w))) 
                                          - (IData)(1U));
    } else {
        vlSelf->__PVT__sll_dir = 0U;
        vlSelf->__PVT__ia = (0x1ffU & ((IData)(vlSelf->__PVT__k) 
                                       + (IData)(vlSelf->__PVT__shamt_w)));
        vlSelf->__VdfgTmp_h586768a0__0 = ((IData)(1U) 
                                          + (VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__k)) 
                                             + VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__shamt_w))));
    }
    vlSelf->d_wdata = ((~ ((IData)(vlSelf->__PVT__shx)
                            ? (0U == (0x1fU & (vlSelf->__PVT__ir 
                                               >> 0xfU)))
                            : (0U == (0x1fU & (vlSelf->__PVT__ir 
                                               >> 0x14U))))) 
                       & (IData)(vlSymsp->TOP.tb_sys5__DOT__dut__DOT__slot__BRA__4__KET____DOT__rqb_b));
    vlSelf->__PVT__exec_done = ((IData)(vlSelf->__PVT__sll_dir)
                                 ? (0U == (IData)(vlSelf->__PVT__k))
                                 : (0x1fU == (IData)(vlSelf->__PVT__k)));
    vlSelf->__PVT__va = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__ia))) 
                         & VL_GTES_III(32, 0x1fU, VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__ia))));
    vlSelf->__PVT__vb = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, 
                                                           (0x1ffU 
                                                            & vlSelf->__VdfgTmp_h586768a0__0))) 
                         & VL_GTES_III(32, 0x1fU, VL_EXTENDS_II(32,9, 
                                                                (0x1ffU 
                                                                 & vlSelf->__VdfgTmp_h586768a0__0))));
    vlSelf->__PVT__Yr = (1U & (((0x33U == (0x7fU & vlSelf->__PVT__ir)) 
                                | (0x63U == (0x7fU 
                                             & vlSelf->__PVT__ir)))
                                ? (IData)(vlSelf->d_wdata)
                                : vlSelf->__PVT__imm_sr));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if ((0x37U != (0x7fU & vlSelf->__PVT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->__PVT__ir))) {
                if ((0x6fU == (0x7fU & vlSelf->__PVT__ir))) {
                    vlSelf->__PVT__Yr = (1U & (4U >> (IData)(vlSelf->__PVT__k)));
                }
            }
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        vlSelf->__PVT__Yr = (1U & (4U >> (IData)(vlSelf->__PVT__k)));
    } else if ((5U == (IData)(vlSelf->__PVT__state))) {
        vlSelf->__PVT__Yr = (1U & (((0x6fU == (0x7fU 
                                               & vlSelf->__PVT__ir)) 
                                    | ((0x63U == (0x7fU 
                                                  & vlSelf->__PVT__ir)) 
                                       & (IData)(__PVT__cond)))
                                    ? vlSelf->__PVT__imm_sr
                                    : (4U >> (IData)(vlSelf->__PVT__k))));
    }
    vlSelf->__PVT__sum_c = (3U & ((IData)(vlSelf->__PVT__X) 
                                  + ((1U & ((IData)(vlSelf->__PVT__inv)
                                             ? (~ (IData)(vlSelf->__PVT__Yr))
                                             : (IData)(vlSelf->__PVT__Yr))) 
                                     + ((0U == (IData)(vlSelf->__PVT__k))
                                         ? (IData)(vlSelf->__PVT__inv)
                                         : (IData)(vlSelf->__PVT__cy)))));
    vlSelf->__PVT__addr_ins = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__addr, 1U) 
                               | VL_SHIFTL_III(32,32,32, 
                                               (1U 
                                                & (IData)(vlSelf->__PVT__sum_c)), 0x1fU));
    vlSelf->__PVT__pc_ins = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__pc, 1U) 
                             | VL_SHIFTL_III(32,32,32, 
                                             (1U & (IData)(vlSelf->__PVT__sum_c)), 0x1fU));
    vlSelf->__PVT__nz_n = (1U & (((0U != (IData)(vlSelf->__PVT__k)) 
                                  & (IData)(vlSelf->__PVT__nz)) 
                                 | (IData)(vlSelf->__PVT__sum_c)));
    vlSelf->__PVT__wd = (1U & (((IData)(vlSelf->__VdfgTmp_h18c46dac__0) 
                                & ((4U == (7U & (vlSelf->__PVT__ir 
                                                 >> 0xcU))) 
                                   | ((6U == (7U & 
                                              (vlSelf->__PVT__ir 
                                               >> 0xcU))) 
                                      | (7U == (7U 
                                                & (vlSelf->__PVT__ir 
                                                   >> 0xcU))))))
                                ? ((4U == (7U & (vlSelf->__PVT__ir 
                                                 >> 0xcU)))
                                    ? ((IData)(vlSelf->__PVT__X) 
                                       ^ (IData)(vlSelf->__PVT__Yr))
                                    : ((6U == (7U & 
                                               (vlSelf->__PVT__ir 
                                                >> 0xcU)))
                                        ? ((IData)(vlSelf->__PVT__X) 
                                           | (IData)(vlSelf->__PVT__Yr))
                                        : ((IData)(vlSelf->__PVT__X) 
                                           & (IData)(vlSelf->__PVT__Yr))))
                                : (IData)(vlSelf->__PVT__sum_c)));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if (vlSelf->__PVT__is_shift) {
            vlSelf->__PVT__wd = (1U & VL_SHIFTR_III(2,2,6, 
                                                    ((((IData)(vlSelf->__PVT__is_sll)
                                                        ? 
                                                       ((IData)(vlSelf->__PVT__va) 
                                                        & (IData)(vlSelf->__PVT__a_val))
                                                        : 
                                                       ((IData)(vlSelf->__PVT__vb)
                                                         ? (IData)(vlSelf->d_wdata)
                                                         : (IData)(vlSelf->__PVT__fill))) 
                                                      << 1U) 
                                                     | ((IData)(vlSelf->__PVT__is_sll)
                                                         ? 
                                                        ((IData)(vlSelf->__PVT__vb) 
                                                         & (IData)(vlSelf->d_wdata))
                                                         : 
                                                        ((IData)(vlSelf->__PVT__va)
                                                          ? (IData)(vlSelf->__PVT__a_val)
                                                          : (IData)(vlSelf->__PVT__fill)))), 
                                                    ((IData)(vlSelf->__PVT__is_sll)
                                                      ? 1U
                                                      : 0U)));
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        if ((3U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__wd = vlSymsp->TOP.tb_sys5__DOT__dut__DOT__slot__BRA__4__KET____DOT__dq_b;
        } else if (vlSelf->__PVT__is_slt) {
            vlSelf->__PVT__wd = ((0U == (IData)(vlSelf->__PVT__k)) 
                                 & ((2U == (7U & (vlSelf->__PVT__ir 
                                                  >> 0xcU)))
                                     ? (IData)(vlSelf->__PVT__f_lt)
                                     : (IData)(vlSelf->__PVT__f_ltu)));
        } else if ((0x67U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__wd = (1U & (IData)(vlSelf->__PVT__sum_c));
        }
    }
}

VL_ATTR_COLD void Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__5__KET____DOT__core__0(Vtb_sys5_uc_core_v2s__W1* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_sys5__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+          Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__5__KET____DOT__core__0\n"); );
    // Init
    CData/*0:0*/ __PVT__cond;
    __PVT__cond = 0;
    CData/*0:0*/ __PVT__we;
    __PVT__we = 0;
    CData/*0:0*/ __VdfgExtracted_h62388771__0;
    __VdfgExtracted_h62388771__0 = 0;
    CData/*0:0*/ __VdfgTmp_h2cd83c5b__0;
    __VdfgTmp_h2cd83c5b__0 = 0;
    CData/*0:0*/ __VdfgTmp_he83b8d53__0;
    __VdfgTmp_he83b8d53__0 = 0;
    CData/*0:0*/ __VdfgTmp_hd9b60348__0;
    __VdfgTmp_hd9b60348__0 = 0;
    CData/*5:0*/ __Vtableidx6;
    __Vtableidx6 = 0;
    // Body
    vlSelf->__PVT__rs2 = (0x1fU & (vlSelf->__PVT__ir 
                                   >> 0x14U));
    vlSelf->__PVT__is_sys = (0x73U == (0x7fU & vlSelf->__PVT__ir));
    vlSelf->__PVT__last_up = (0x1fU == (IData)(vlSelf->__PVT__k));
    vlSelf->__PVT__pc_rot = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__pc, 1U) 
                             | VL_SHIFTL_III(32,32,32, vlSelf->__PVT__pc, 0x1fU));
    vlSelf->__PVT__imm_rot = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__imm_sr, 1U) 
                              | VL_SHIFTL_III(32,32,32, vlSelf->__PVT__imm_sr, 0x1fU));
    vlSelf->__PVT__opc = (0x7fU & vlSelf->__PVT__ir);
    vlSelf->d_addr = (((QData)((IData)((vlSelf->__PVT__addr 
                                        >> 2U))) << 5U) 
                      | (QData)((IData)(vlSelf->__PVT__k)));
    vlSelf->rw_addr = ((0x3e0U & (vlSelf->__PVT__ir 
                                  >> 2U)) | (IData)(vlSelf->__PVT__k));
    __VdfgTmp_h2cd83c5b__0 = ((0x37U == (0x7fU & vlSelf->__PVT__ir)) 
                              | (0x17U == (0x7fU & vlSelf->__PVT__ir)));
    __Vtableidx6 = (((IData)(vlSelf->__PVT__f_eq) << 5U) 
                    | (((IData)(vlSelf->__PVT__f_lt) 
                        << 4U) | (((IData)(vlSelf->__PVT__f_ltu) 
                                   << 3U) | (7U & (vlSelf->__PVT__ir 
                                                   >> 0xcU)))));
    __PVT__cond = Vtb_sys5__ConstPool__TABLE_h2a0441a0_0
        [__Vtableidx6];
    vlSelf->__PVT__a_val = ((0U != (0x1fU & (vlSelf->__PVT__ir 
                                             >> 0xfU))) 
                            & (IData)(vlSymsp->TOP.tb_sys5__DOT__dut__DOT__slot__BRA__5__KET____DOT__rqa_b));
    __VdfgTmp_hd9b60348__0 = ((2U == (7U & (vlSelf->__PVT__ir 
                                            >> 0xcU))) 
                              | (3U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))));
    vlSelf->__VdfgTmp_h18c46dac__0 = ((0x13U == (0x7fU 
                                                 & vlSelf->__PVT__ir)) 
                                      | (0x33U == (0x7fU 
                                                   & vlSelf->__PVT__ir)));
    __VdfgTmp_he83b8d53__0 = ((1U == (7U & (vlSelf->__PVT__ir 
                                            >> 0xcU))) 
                              | (5U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))));
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
    vlSelf->__PVT__X = vlSelf->__PVT__a_val;
    vlSelf->__PVT__is_cmp = ((0x63U == (0x7fU & vlSelf->__PVT__ir)) 
                             | ((IData)(vlSelf->__VdfgTmp_h18c46dac__0) 
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
    vlSelf->__PVT__inv = 0U;
    vlSelf->__PVT__is_shift = ((IData)(vlSelf->__PVT__sh_i) 
                               | ((0x33U == (0x7fU 
                                             & vlSelf->__PVT__ir)) 
                                  & (IData)(__VdfgTmp_he83b8d53__0)));
    __PVT__we = 0U;
    vlSelf->__PVT__fill = ((IData)(vlSelf->__PVT__is_shift) 
                           & (IData)(((0x40005000U 
                                       == (0x40007000U 
                                           & vlSelf->__PVT__ir)) 
                                      & (IData)(vlSelf->__PVT__sgn))));
    vlSelf->__PVT__is_sll = ((IData)(vlSelf->__PVT__is_shift) 
                             & (0x1000U == (0x7000U 
                                            & vlSelf->__PVT__ir)));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        vlSelf->__PVT__shx = vlSelf->__PVT__is_shift;
        if ((0x37U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__X = 0U;
        } else if ((0x17U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
        } else if ((0x6fU == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
        }
        if ((0x37U != (0x7fU & vlSelf->__PVT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->__PVT__ir))) {
                if ((0x6fU != (0x7fU & vlSelf->__PVT__ir))) {
                    if (((IData)((0x40000033U == (0x4000707fU 
                                                  & vlSelf->__PVT__ir))) 
                         | (IData)(vlSelf->__PVT__is_cmp))) {
                        vlSelf->__PVT__inv = 1U;
                    }
                }
            }
        }
        if (vlSelf->__PVT__is_shift) {
            __PVT__we = 1U;
        } else if (__VdfgExtracted_h62388771__0) {
            __PVT__we = 1U;
        } else if (((~ (IData)(vlSelf->__PVT__is_cmp)) 
                    & (IData)(vlSelf->__VdfgTmp_h18c46dac__0))) {
            __PVT__we = 1U;
        }
    } else {
        vlSelf->__PVT__shx = 0U;
        if ((4U == (IData)(vlSelf->__PVT__state))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
            if ((3U == (0x7fU & vlSelf->__PVT__ir))) {
                __PVT__we = 1U;
            } else if (vlSelf->__PVT__is_slt) {
                __PVT__we = 1U;
            } else if ((0x67U == (0x7fU & vlSelf->__PVT__ir))) {
                __PVT__we = 1U;
            }
        } else if ((5U == (IData)(vlSelf->__PVT__state))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
        }
    }
    vlSelf->rw_en = ((IData)(__PVT__we) & (0U != (0x1fU 
                                                  & (vlSelf->__PVT__ir 
                                                     >> 7U))));
    if (vlSelf->__PVT__is_sll) {
        vlSelf->__PVT__sll_dir = vlSelf->__PVT__is_shift;
        vlSelf->__PVT__ia = (0x1ffU & ((IData)(vlSelf->__PVT__k) 
                                       - (IData)(vlSelf->__PVT__shamt_w)));
        vlSelf->__VdfgTmp_h586768a0__0 = ((VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__k)) 
                                           - VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__shamt_w))) 
                                          - (IData)(1U));
    } else {
        vlSelf->__PVT__sll_dir = 0U;
        vlSelf->__PVT__ia = (0x1ffU & ((IData)(vlSelf->__PVT__k) 
                                       + (IData)(vlSelf->__PVT__shamt_w)));
        vlSelf->__VdfgTmp_h586768a0__0 = ((IData)(1U) 
                                          + (VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__k)) 
                                             + VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__shamt_w))));
    }
    vlSelf->d_wdata = ((~ ((IData)(vlSelf->__PVT__shx)
                            ? (0U == (0x1fU & (vlSelf->__PVT__ir 
                                               >> 0xfU)))
                            : (0U == (0x1fU & (vlSelf->__PVT__ir 
                                               >> 0x14U))))) 
                       & (IData)(vlSymsp->TOP.tb_sys5__DOT__dut__DOT__slot__BRA__5__KET____DOT__rqb_b));
    vlSelf->__PVT__exec_done = ((IData)(vlSelf->__PVT__sll_dir)
                                 ? (0U == (IData)(vlSelf->__PVT__k))
                                 : (0x1fU == (IData)(vlSelf->__PVT__k)));
    vlSelf->__PVT__va = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__ia))) 
                         & VL_GTES_III(32, 0x1fU, VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__ia))));
    vlSelf->__PVT__vb = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, 
                                                           (0x1ffU 
                                                            & vlSelf->__VdfgTmp_h586768a0__0))) 
                         & VL_GTES_III(32, 0x1fU, VL_EXTENDS_II(32,9, 
                                                                (0x1ffU 
                                                                 & vlSelf->__VdfgTmp_h586768a0__0))));
    vlSelf->__PVT__Yr = (1U & (((0x33U == (0x7fU & vlSelf->__PVT__ir)) 
                                | (0x63U == (0x7fU 
                                             & vlSelf->__PVT__ir)))
                                ? (IData)(vlSelf->d_wdata)
                                : vlSelf->__PVT__imm_sr));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if ((0x37U != (0x7fU & vlSelf->__PVT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->__PVT__ir))) {
                if ((0x6fU == (0x7fU & vlSelf->__PVT__ir))) {
                    vlSelf->__PVT__Yr = (1U & (4U >> (IData)(vlSelf->__PVT__k)));
                }
            }
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        vlSelf->__PVT__Yr = (1U & (4U >> (IData)(vlSelf->__PVT__k)));
    } else if ((5U == (IData)(vlSelf->__PVT__state))) {
        vlSelf->__PVT__Yr = (1U & (((0x6fU == (0x7fU 
                                               & vlSelf->__PVT__ir)) 
                                    | ((0x63U == (0x7fU 
                                                  & vlSelf->__PVT__ir)) 
                                       & (IData)(__PVT__cond)))
                                    ? vlSelf->__PVT__imm_sr
                                    : (4U >> (IData)(vlSelf->__PVT__k))));
    }
    vlSelf->__PVT__sum_c = (3U & ((IData)(vlSelf->__PVT__X) 
                                  + ((1U & ((IData)(vlSelf->__PVT__inv)
                                             ? (~ (IData)(vlSelf->__PVT__Yr))
                                             : (IData)(vlSelf->__PVT__Yr))) 
                                     + ((0U == (IData)(vlSelf->__PVT__k))
                                         ? (IData)(vlSelf->__PVT__inv)
                                         : (IData)(vlSelf->__PVT__cy)))));
    vlSelf->__PVT__addr_ins = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__addr, 1U) 
                               | VL_SHIFTL_III(32,32,32, 
                                               (1U 
                                                & (IData)(vlSelf->__PVT__sum_c)), 0x1fU));
    vlSelf->__PVT__pc_ins = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__pc, 1U) 
                             | VL_SHIFTL_III(32,32,32, 
                                             (1U & (IData)(vlSelf->__PVT__sum_c)), 0x1fU));
    vlSelf->__PVT__nz_n = (1U & (((0U != (IData)(vlSelf->__PVT__k)) 
                                  & (IData)(vlSelf->__PVT__nz)) 
                                 | (IData)(vlSelf->__PVT__sum_c)));
    vlSelf->__PVT__wd = (1U & (((IData)(vlSelf->__VdfgTmp_h18c46dac__0) 
                                & ((4U == (7U & (vlSelf->__PVT__ir 
                                                 >> 0xcU))) 
                                   | ((6U == (7U & 
                                              (vlSelf->__PVT__ir 
                                               >> 0xcU))) 
                                      | (7U == (7U 
                                                & (vlSelf->__PVT__ir 
                                                   >> 0xcU))))))
                                ? ((4U == (7U & (vlSelf->__PVT__ir 
                                                 >> 0xcU)))
                                    ? ((IData)(vlSelf->__PVT__X) 
                                       ^ (IData)(vlSelf->__PVT__Yr))
                                    : ((6U == (7U & 
                                               (vlSelf->__PVT__ir 
                                                >> 0xcU)))
                                        ? ((IData)(vlSelf->__PVT__X) 
                                           | (IData)(vlSelf->__PVT__Yr))
                                        : ((IData)(vlSelf->__PVT__X) 
                                           & (IData)(vlSelf->__PVT__Yr))))
                                : (IData)(vlSelf->__PVT__sum_c)));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if (vlSelf->__PVT__is_shift) {
            vlSelf->__PVT__wd = (1U & VL_SHIFTR_III(2,2,6, 
                                                    ((((IData)(vlSelf->__PVT__is_sll)
                                                        ? 
                                                       ((IData)(vlSelf->__PVT__va) 
                                                        & (IData)(vlSelf->__PVT__a_val))
                                                        : 
                                                       ((IData)(vlSelf->__PVT__vb)
                                                         ? (IData)(vlSelf->d_wdata)
                                                         : (IData)(vlSelf->__PVT__fill))) 
                                                      << 1U) 
                                                     | ((IData)(vlSelf->__PVT__is_sll)
                                                         ? 
                                                        ((IData)(vlSelf->__PVT__vb) 
                                                         & (IData)(vlSelf->d_wdata))
                                                         : 
                                                        ((IData)(vlSelf->__PVT__va)
                                                          ? (IData)(vlSelf->__PVT__a_val)
                                                          : (IData)(vlSelf->__PVT__fill)))), 
                                                    ((IData)(vlSelf->__PVT__is_sll)
                                                      ? 1U
                                                      : 0U)));
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        if ((3U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__wd = vlSymsp->TOP.tb_sys5__DOT__dut__DOT__slot__BRA__5__KET____DOT__dq_b;
        } else if (vlSelf->__PVT__is_slt) {
            vlSelf->__PVT__wd = ((0U == (IData)(vlSelf->__PVT__k)) 
                                 & ((2U == (7U & (vlSelf->__PVT__ir 
                                                  >> 0xcU)))
                                     ? (IData)(vlSelf->__PVT__f_lt)
                                     : (IData)(vlSelf->__PVT__f_ltu)));
        } else if ((0x67U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__wd = (1U & (IData)(vlSelf->__PVT__sum_c));
        }
    }
}

VL_ATTR_COLD void Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__6__KET____DOT__core__0(Vtb_sys5_uc_core_v2s__W1* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_sys5__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+          Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__6__KET____DOT__core__0\n"); );
    // Init
    CData/*0:0*/ __PVT__cond;
    __PVT__cond = 0;
    CData/*0:0*/ __PVT__we;
    __PVT__we = 0;
    CData/*0:0*/ __VdfgExtracted_h62388771__0;
    __VdfgExtracted_h62388771__0 = 0;
    CData/*0:0*/ __VdfgTmp_h2cd83c5b__0;
    __VdfgTmp_h2cd83c5b__0 = 0;
    CData/*0:0*/ __VdfgTmp_he83b8d53__0;
    __VdfgTmp_he83b8d53__0 = 0;
    CData/*0:0*/ __VdfgTmp_hd9b60348__0;
    __VdfgTmp_hd9b60348__0 = 0;
    CData/*5:0*/ __Vtableidx7;
    __Vtableidx7 = 0;
    // Body
    vlSelf->__PVT__rs2 = (0x1fU & (vlSelf->__PVT__ir 
                                   >> 0x14U));
    vlSelf->__PVT__is_sys = (0x73U == (0x7fU & vlSelf->__PVT__ir));
    vlSelf->__PVT__last_up = (0x1fU == (IData)(vlSelf->__PVT__k));
    vlSelf->__PVT__pc_rot = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__pc, 1U) 
                             | VL_SHIFTL_III(32,32,32, vlSelf->__PVT__pc, 0x1fU));
    vlSelf->__PVT__imm_rot = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__imm_sr, 1U) 
                              | VL_SHIFTL_III(32,32,32, vlSelf->__PVT__imm_sr, 0x1fU));
    vlSelf->__PVT__opc = (0x7fU & vlSelf->__PVT__ir);
    vlSelf->d_addr = (((QData)((IData)((vlSelf->__PVT__addr 
                                        >> 2U))) << 5U) 
                      | (QData)((IData)(vlSelf->__PVT__k)));
    vlSelf->rw_addr = ((0x3e0U & (vlSelf->__PVT__ir 
                                  >> 2U)) | (IData)(vlSelf->__PVT__k));
    __VdfgTmp_h2cd83c5b__0 = ((0x37U == (0x7fU & vlSelf->__PVT__ir)) 
                              | (0x17U == (0x7fU & vlSelf->__PVT__ir)));
    __Vtableidx7 = (((IData)(vlSelf->__PVT__f_eq) << 5U) 
                    | (((IData)(vlSelf->__PVT__f_lt) 
                        << 4U) | (((IData)(vlSelf->__PVT__f_ltu) 
                                   << 3U) | (7U & (vlSelf->__PVT__ir 
                                                   >> 0xcU)))));
    __PVT__cond = Vtb_sys5__ConstPool__TABLE_h2a0441a0_0
        [__Vtableidx7];
    vlSelf->__PVT__a_val = ((0U != (0x1fU & (vlSelf->__PVT__ir 
                                             >> 0xfU))) 
                            & (IData)(vlSymsp->TOP.tb_sys5__DOT__dut__DOT__slot__BRA__6__KET____DOT__rqa_b));
    __VdfgTmp_hd9b60348__0 = ((2U == (7U & (vlSelf->__PVT__ir 
                                            >> 0xcU))) 
                              | (3U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))));
    vlSelf->__VdfgTmp_h18c46dac__0 = ((0x13U == (0x7fU 
                                                 & vlSelf->__PVT__ir)) 
                                      | (0x33U == (0x7fU 
                                                   & vlSelf->__PVT__ir)));
    __VdfgTmp_he83b8d53__0 = ((1U == (7U & (vlSelf->__PVT__ir 
                                            >> 0xcU))) 
                              | (5U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))));
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
    vlSelf->__PVT__X = vlSelf->__PVT__a_val;
    vlSelf->__PVT__is_cmp = ((0x63U == (0x7fU & vlSelf->__PVT__ir)) 
                             | ((IData)(vlSelf->__VdfgTmp_h18c46dac__0) 
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
    vlSelf->__PVT__inv = 0U;
    vlSelf->__PVT__is_shift = ((IData)(vlSelf->__PVT__sh_i) 
                               | ((0x33U == (0x7fU 
                                             & vlSelf->__PVT__ir)) 
                                  & (IData)(__VdfgTmp_he83b8d53__0)));
    __PVT__we = 0U;
    vlSelf->__PVT__fill = ((IData)(vlSelf->__PVT__is_shift) 
                           & (IData)(((0x40005000U 
                                       == (0x40007000U 
                                           & vlSelf->__PVT__ir)) 
                                      & (IData)(vlSelf->__PVT__sgn))));
    vlSelf->__PVT__is_sll = ((IData)(vlSelf->__PVT__is_shift) 
                             & (0x1000U == (0x7000U 
                                            & vlSelf->__PVT__ir)));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        vlSelf->__PVT__shx = vlSelf->__PVT__is_shift;
        if ((0x37U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__X = 0U;
        } else if ((0x17U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
        } else if ((0x6fU == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
        }
        if ((0x37U != (0x7fU & vlSelf->__PVT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->__PVT__ir))) {
                if ((0x6fU != (0x7fU & vlSelf->__PVT__ir))) {
                    if (((IData)((0x40000033U == (0x4000707fU 
                                                  & vlSelf->__PVT__ir))) 
                         | (IData)(vlSelf->__PVT__is_cmp))) {
                        vlSelf->__PVT__inv = 1U;
                    }
                }
            }
        }
        if (vlSelf->__PVT__is_shift) {
            __PVT__we = 1U;
        } else if (__VdfgExtracted_h62388771__0) {
            __PVT__we = 1U;
        } else if (((~ (IData)(vlSelf->__PVT__is_cmp)) 
                    & (IData)(vlSelf->__VdfgTmp_h18c46dac__0))) {
            __PVT__we = 1U;
        }
    } else {
        vlSelf->__PVT__shx = 0U;
        if ((4U == (IData)(vlSelf->__PVT__state))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
            if ((3U == (0x7fU & vlSelf->__PVT__ir))) {
                __PVT__we = 1U;
            } else if (vlSelf->__PVT__is_slt) {
                __PVT__we = 1U;
            } else if ((0x67U == (0x7fU & vlSelf->__PVT__ir))) {
                __PVT__we = 1U;
            }
        } else if ((5U == (IData)(vlSelf->__PVT__state))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
        }
    }
    vlSelf->rw_en = ((IData)(__PVT__we) & (0U != (0x1fU 
                                                  & (vlSelf->__PVT__ir 
                                                     >> 7U))));
    if (vlSelf->__PVT__is_sll) {
        vlSelf->__PVT__sll_dir = vlSelf->__PVT__is_shift;
        vlSelf->__PVT__ia = (0x1ffU & ((IData)(vlSelf->__PVT__k) 
                                       - (IData)(vlSelf->__PVT__shamt_w)));
        vlSelf->__VdfgTmp_h586768a0__0 = ((VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__k)) 
                                           - VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__shamt_w))) 
                                          - (IData)(1U));
    } else {
        vlSelf->__PVT__sll_dir = 0U;
        vlSelf->__PVT__ia = (0x1ffU & ((IData)(vlSelf->__PVT__k) 
                                       + (IData)(vlSelf->__PVT__shamt_w)));
        vlSelf->__VdfgTmp_h586768a0__0 = ((IData)(1U) 
                                          + (VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__k)) 
                                             + VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__shamt_w))));
    }
    vlSelf->d_wdata = ((~ ((IData)(vlSelf->__PVT__shx)
                            ? (0U == (0x1fU & (vlSelf->__PVT__ir 
                                               >> 0xfU)))
                            : (0U == (0x1fU & (vlSelf->__PVT__ir 
                                               >> 0x14U))))) 
                       & (IData)(vlSymsp->TOP.tb_sys5__DOT__dut__DOT__slot__BRA__6__KET____DOT__rqb_b));
    vlSelf->__PVT__exec_done = ((IData)(vlSelf->__PVT__sll_dir)
                                 ? (0U == (IData)(vlSelf->__PVT__k))
                                 : (0x1fU == (IData)(vlSelf->__PVT__k)));
    vlSelf->__PVT__va = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__ia))) 
                         & VL_GTES_III(32, 0x1fU, VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__ia))));
    vlSelf->__PVT__vb = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, 
                                                           (0x1ffU 
                                                            & vlSelf->__VdfgTmp_h586768a0__0))) 
                         & VL_GTES_III(32, 0x1fU, VL_EXTENDS_II(32,9, 
                                                                (0x1ffU 
                                                                 & vlSelf->__VdfgTmp_h586768a0__0))));
    vlSelf->__PVT__Yr = (1U & (((0x33U == (0x7fU & vlSelf->__PVT__ir)) 
                                | (0x63U == (0x7fU 
                                             & vlSelf->__PVT__ir)))
                                ? (IData)(vlSelf->d_wdata)
                                : vlSelf->__PVT__imm_sr));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if ((0x37U != (0x7fU & vlSelf->__PVT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->__PVT__ir))) {
                if ((0x6fU == (0x7fU & vlSelf->__PVT__ir))) {
                    vlSelf->__PVT__Yr = (1U & (4U >> (IData)(vlSelf->__PVT__k)));
                }
            }
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        vlSelf->__PVT__Yr = (1U & (4U >> (IData)(vlSelf->__PVT__k)));
    } else if ((5U == (IData)(vlSelf->__PVT__state))) {
        vlSelf->__PVT__Yr = (1U & (((0x6fU == (0x7fU 
                                               & vlSelf->__PVT__ir)) 
                                    | ((0x63U == (0x7fU 
                                                  & vlSelf->__PVT__ir)) 
                                       & (IData)(__PVT__cond)))
                                    ? vlSelf->__PVT__imm_sr
                                    : (4U >> (IData)(vlSelf->__PVT__k))));
    }
    vlSelf->__PVT__sum_c = (3U & ((IData)(vlSelf->__PVT__X) 
                                  + ((1U & ((IData)(vlSelf->__PVT__inv)
                                             ? (~ (IData)(vlSelf->__PVT__Yr))
                                             : (IData)(vlSelf->__PVT__Yr))) 
                                     + ((0U == (IData)(vlSelf->__PVT__k))
                                         ? (IData)(vlSelf->__PVT__inv)
                                         : (IData)(vlSelf->__PVT__cy)))));
    vlSelf->__PVT__addr_ins = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__addr, 1U) 
                               | VL_SHIFTL_III(32,32,32, 
                                               (1U 
                                                & (IData)(vlSelf->__PVT__sum_c)), 0x1fU));
    vlSelf->__PVT__pc_ins = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__pc, 1U) 
                             | VL_SHIFTL_III(32,32,32, 
                                             (1U & (IData)(vlSelf->__PVT__sum_c)), 0x1fU));
    vlSelf->__PVT__nz_n = (1U & (((0U != (IData)(vlSelf->__PVT__k)) 
                                  & (IData)(vlSelf->__PVT__nz)) 
                                 | (IData)(vlSelf->__PVT__sum_c)));
    vlSelf->__PVT__wd = (1U & (((IData)(vlSelf->__VdfgTmp_h18c46dac__0) 
                                & ((4U == (7U & (vlSelf->__PVT__ir 
                                                 >> 0xcU))) 
                                   | ((6U == (7U & 
                                              (vlSelf->__PVT__ir 
                                               >> 0xcU))) 
                                      | (7U == (7U 
                                                & (vlSelf->__PVT__ir 
                                                   >> 0xcU))))))
                                ? ((4U == (7U & (vlSelf->__PVT__ir 
                                                 >> 0xcU)))
                                    ? ((IData)(vlSelf->__PVT__X) 
                                       ^ (IData)(vlSelf->__PVT__Yr))
                                    : ((6U == (7U & 
                                               (vlSelf->__PVT__ir 
                                                >> 0xcU)))
                                        ? ((IData)(vlSelf->__PVT__X) 
                                           | (IData)(vlSelf->__PVT__Yr))
                                        : ((IData)(vlSelf->__PVT__X) 
                                           & (IData)(vlSelf->__PVT__Yr))))
                                : (IData)(vlSelf->__PVT__sum_c)));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if (vlSelf->__PVT__is_shift) {
            vlSelf->__PVT__wd = (1U & VL_SHIFTR_III(2,2,6, 
                                                    ((((IData)(vlSelf->__PVT__is_sll)
                                                        ? 
                                                       ((IData)(vlSelf->__PVT__va) 
                                                        & (IData)(vlSelf->__PVT__a_val))
                                                        : 
                                                       ((IData)(vlSelf->__PVT__vb)
                                                         ? (IData)(vlSelf->d_wdata)
                                                         : (IData)(vlSelf->__PVT__fill))) 
                                                      << 1U) 
                                                     | ((IData)(vlSelf->__PVT__is_sll)
                                                         ? 
                                                        ((IData)(vlSelf->__PVT__vb) 
                                                         & (IData)(vlSelf->d_wdata))
                                                         : 
                                                        ((IData)(vlSelf->__PVT__va)
                                                          ? (IData)(vlSelf->__PVT__a_val)
                                                          : (IData)(vlSelf->__PVT__fill)))), 
                                                    ((IData)(vlSelf->__PVT__is_sll)
                                                      ? 1U
                                                      : 0U)));
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        if ((3U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__wd = vlSymsp->TOP.tb_sys5__DOT__dut__DOT__slot__BRA__6__KET____DOT__dq_b;
        } else if (vlSelf->__PVT__is_slt) {
            vlSelf->__PVT__wd = ((0U == (IData)(vlSelf->__PVT__k)) 
                                 & ((2U == (7U & (vlSelf->__PVT__ir 
                                                  >> 0xcU)))
                                     ? (IData)(vlSelf->__PVT__f_lt)
                                     : (IData)(vlSelf->__PVT__f_ltu)));
        } else if ((0x67U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__wd = (1U & (IData)(vlSelf->__PVT__sum_c));
        }
    }
}

VL_ATTR_COLD void Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__7__KET____DOT__core__0(Vtb_sys5_uc_core_v2s__W1* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_sys5__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+          Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__7__KET____DOT__core__0\n"); );
    // Init
    CData/*0:0*/ __PVT__cond;
    __PVT__cond = 0;
    CData/*0:0*/ __PVT__we;
    __PVT__we = 0;
    CData/*0:0*/ __VdfgExtracted_h62388771__0;
    __VdfgExtracted_h62388771__0 = 0;
    CData/*0:0*/ __VdfgTmp_h2cd83c5b__0;
    __VdfgTmp_h2cd83c5b__0 = 0;
    CData/*0:0*/ __VdfgTmp_he83b8d53__0;
    __VdfgTmp_he83b8d53__0 = 0;
    CData/*0:0*/ __VdfgTmp_hd9b60348__0;
    __VdfgTmp_hd9b60348__0 = 0;
    CData/*5:0*/ __Vtableidx8;
    __Vtableidx8 = 0;
    // Body
    vlSelf->__PVT__rs2 = (0x1fU & (vlSelf->__PVT__ir 
                                   >> 0x14U));
    vlSelf->__PVT__is_sys = (0x73U == (0x7fU & vlSelf->__PVT__ir));
    vlSelf->__PVT__last_up = (0x1fU == (IData)(vlSelf->__PVT__k));
    vlSelf->__PVT__pc_rot = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__pc, 1U) 
                             | VL_SHIFTL_III(32,32,32, vlSelf->__PVT__pc, 0x1fU));
    vlSelf->__PVT__imm_rot = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__imm_sr, 1U) 
                              | VL_SHIFTL_III(32,32,32, vlSelf->__PVT__imm_sr, 0x1fU));
    vlSelf->__PVT__opc = (0x7fU & vlSelf->__PVT__ir);
    vlSelf->d_addr = (((QData)((IData)((vlSelf->__PVT__addr 
                                        >> 2U))) << 5U) 
                      | (QData)((IData)(vlSelf->__PVT__k)));
    vlSelf->rw_addr = ((0x3e0U & (vlSelf->__PVT__ir 
                                  >> 2U)) | (IData)(vlSelf->__PVT__k));
    __VdfgTmp_h2cd83c5b__0 = ((0x37U == (0x7fU & vlSelf->__PVT__ir)) 
                              | (0x17U == (0x7fU & vlSelf->__PVT__ir)));
    __Vtableidx8 = (((IData)(vlSelf->__PVT__f_eq) << 5U) 
                    | (((IData)(vlSelf->__PVT__f_lt) 
                        << 4U) | (((IData)(vlSelf->__PVT__f_ltu) 
                                   << 3U) | (7U & (vlSelf->__PVT__ir 
                                                   >> 0xcU)))));
    __PVT__cond = Vtb_sys5__ConstPool__TABLE_h2a0441a0_0
        [__Vtableidx8];
    vlSelf->__PVT__a_val = ((0U != (0x1fU & (vlSelf->__PVT__ir 
                                             >> 0xfU))) 
                            & (IData)(vlSymsp->TOP.tb_sys5__DOT__dut__DOT__slot__BRA__7__KET____DOT__rqa_b));
    __VdfgTmp_hd9b60348__0 = ((2U == (7U & (vlSelf->__PVT__ir 
                                            >> 0xcU))) 
                              | (3U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))));
    vlSelf->__VdfgTmp_h18c46dac__0 = ((0x13U == (0x7fU 
                                                 & vlSelf->__PVT__ir)) 
                                      | (0x33U == (0x7fU 
                                                   & vlSelf->__PVT__ir)));
    __VdfgTmp_he83b8d53__0 = ((1U == (7U & (vlSelf->__PVT__ir 
                                            >> 0xcU))) 
                              | (5U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))));
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
    vlSelf->__PVT__X = vlSelf->__PVT__a_val;
    vlSelf->__PVT__is_cmp = ((0x63U == (0x7fU & vlSelf->__PVT__ir)) 
                             | ((IData)(vlSelf->__VdfgTmp_h18c46dac__0) 
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
    vlSelf->__PVT__inv = 0U;
    vlSelf->__PVT__is_shift = ((IData)(vlSelf->__PVT__sh_i) 
                               | ((0x33U == (0x7fU 
                                             & vlSelf->__PVT__ir)) 
                                  & (IData)(__VdfgTmp_he83b8d53__0)));
    __PVT__we = 0U;
    vlSelf->__PVT__fill = ((IData)(vlSelf->__PVT__is_shift) 
                           & (IData)(((0x40005000U 
                                       == (0x40007000U 
                                           & vlSelf->__PVT__ir)) 
                                      & (IData)(vlSelf->__PVT__sgn))));
    vlSelf->__PVT__is_sll = ((IData)(vlSelf->__PVT__is_shift) 
                             & (0x1000U == (0x7000U 
                                            & vlSelf->__PVT__ir)));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        vlSelf->__PVT__shx = vlSelf->__PVT__is_shift;
        if ((0x37U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__X = 0U;
        } else if ((0x17U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
        } else if ((0x6fU == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
        }
        if ((0x37U != (0x7fU & vlSelf->__PVT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->__PVT__ir))) {
                if ((0x6fU != (0x7fU & vlSelf->__PVT__ir))) {
                    if (((IData)((0x40000033U == (0x4000707fU 
                                                  & vlSelf->__PVT__ir))) 
                         | (IData)(vlSelf->__PVT__is_cmp))) {
                        vlSelf->__PVT__inv = 1U;
                    }
                }
            }
        }
        if (vlSelf->__PVT__is_shift) {
            __PVT__we = 1U;
        } else if (__VdfgExtracted_h62388771__0) {
            __PVT__we = 1U;
        } else if (((~ (IData)(vlSelf->__PVT__is_cmp)) 
                    & (IData)(vlSelf->__VdfgTmp_h18c46dac__0))) {
            __PVT__we = 1U;
        }
    } else {
        vlSelf->__PVT__shx = 0U;
        if ((4U == (IData)(vlSelf->__PVT__state))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
            if ((3U == (0x7fU & vlSelf->__PVT__ir))) {
                __PVT__we = 1U;
            } else if (vlSelf->__PVT__is_slt) {
                __PVT__we = 1U;
            } else if ((0x67U == (0x7fU & vlSelf->__PVT__ir))) {
                __PVT__we = 1U;
            }
        } else if ((5U == (IData)(vlSelf->__PVT__state))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
        }
    }
    vlSelf->rw_en = ((IData)(__PVT__we) & (0U != (0x1fU 
                                                  & (vlSelf->__PVT__ir 
                                                     >> 7U))));
    if (vlSelf->__PVT__is_sll) {
        vlSelf->__PVT__sll_dir = vlSelf->__PVT__is_shift;
        vlSelf->__PVT__ia = (0x1ffU & ((IData)(vlSelf->__PVT__k) 
                                       - (IData)(vlSelf->__PVT__shamt_w)));
        vlSelf->__VdfgTmp_h586768a0__0 = ((VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__k)) 
                                           - VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__shamt_w))) 
                                          - (IData)(1U));
    } else {
        vlSelf->__PVT__sll_dir = 0U;
        vlSelf->__PVT__ia = (0x1ffU & ((IData)(vlSelf->__PVT__k) 
                                       + (IData)(vlSelf->__PVT__shamt_w)));
        vlSelf->__VdfgTmp_h586768a0__0 = ((IData)(1U) 
                                          + (VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__k)) 
                                             + VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__shamt_w))));
    }
    vlSelf->d_wdata = ((~ ((IData)(vlSelf->__PVT__shx)
                            ? (0U == (0x1fU & (vlSelf->__PVT__ir 
                                               >> 0xfU)))
                            : (0U == (0x1fU & (vlSelf->__PVT__ir 
                                               >> 0x14U))))) 
                       & (IData)(vlSymsp->TOP.tb_sys5__DOT__dut__DOT__slot__BRA__7__KET____DOT__rqb_b));
    vlSelf->__PVT__exec_done = ((IData)(vlSelf->__PVT__sll_dir)
                                 ? (0U == (IData)(vlSelf->__PVT__k))
                                 : (0x1fU == (IData)(vlSelf->__PVT__k)));
    vlSelf->__PVT__va = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__ia))) 
                         & VL_GTES_III(32, 0x1fU, VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__ia))));
    vlSelf->__PVT__vb = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, 
                                                           (0x1ffU 
                                                            & vlSelf->__VdfgTmp_h586768a0__0))) 
                         & VL_GTES_III(32, 0x1fU, VL_EXTENDS_II(32,9, 
                                                                (0x1ffU 
                                                                 & vlSelf->__VdfgTmp_h586768a0__0))));
    vlSelf->__PVT__Yr = (1U & (((0x33U == (0x7fU & vlSelf->__PVT__ir)) 
                                | (0x63U == (0x7fU 
                                             & vlSelf->__PVT__ir)))
                                ? (IData)(vlSelf->d_wdata)
                                : vlSelf->__PVT__imm_sr));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if ((0x37U != (0x7fU & vlSelf->__PVT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->__PVT__ir))) {
                if ((0x6fU == (0x7fU & vlSelf->__PVT__ir))) {
                    vlSelf->__PVT__Yr = (1U & (4U >> (IData)(vlSelf->__PVT__k)));
                }
            }
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        vlSelf->__PVT__Yr = (1U & (4U >> (IData)(vlSelf->__PVT__k)));
    } else if ((5U == (IData)(vlSelf->__PVT__state))) {
        vlSelf->__PVT__Yr = (1U & (((0x6fU == (0x7fU 
                                               & vlSelf->__PVT__ir)) 
                                    | ((0x63U == (0x7fU 
                                                  & vlSelf->__PVT__ir)) 
                                       & (IData)(__PVT__cond)))
                                    ? vlSelf->__PVT__imm_sr
                                    : (4U >> (IData)(vlSelf->__PVT__k))));
    }
    vlSelf->__PVT__sum_c = (3U & ((IData)(vlSelf->__PVT__X) 
                                  + ((1U & ((IData)(vlSelf->__PVT__inv)
                                             ? (~ (IData)(vlSelf->__PVT__Yr))
                                             : (IData)(vlSelf->__PVT__Yr))) 
                                     + ((0U == (IData)(vlSelf->__PVT__k))
                                         ? (IData)(vlSelf->__PVT__inv)
                                         : (IData)(vlSelf->__PVT__cy)))));
    vlSelf->__PVT__addr_ins = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__addr, 1U) 
                               | VL_SHIFTL_III(32,32,32, 
                                               (1U 
                                                & (IData)(vlSelf->__PVT__sum_c)), 0x1fU));
    vlSelf->__PVT__pc_ins = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__pc, 1U) 
                             | VL_SHIFTL_III(32,32,32, 
                                             (1U & (IData)(vlSelf->__PVT__sum_c)), 0x1fU));
    vlSelf->__PVT__nz_n = (1U & (((0U != (IData)(vlSelf->__PVT__k)) 
                                  & (IData)(vlSelf->__PVT__nz)) 
                                 | (IData)(vlSelf->__PVT__sum_c)));
    vlSelf->__PVT__wd = (1U & (((IData)(vlSelf->__VdfgTmp_h18c46dac__0) 
                                & ((4U == (7U & (vlSelf->__PVT__ir 
                                                 >> 0xcU))) 
                                   | ((6U == (7U & 
                                              (vlSelf->__PVT__ir 
                                               >> 0xcU))) 
                                      | (7U == (7U 
                                                & (vlSelf->__PVT__ir 
                                                   >> 0xcU))))))
                                ? ((4U == (7U & (vlSelf->__PVT__ir 
                                                 >> 0xcU)))
                                    ? ((IData)(vlSelf->__PVT__X) 
                                       ^ (IData)(vlSelf->__PVT__Yr))
                                    : ((6U == (7U & 
                                               (vlSelf->__PVT__ir 
                                                >> 0xcU)))
                                        ? ((IData)(vlSelf->__PVT__X) 
                                           | (IData)(vlSelf->__PVT__Yr))
                                        : ((IData)(vlSelf->__PVT__X) 
                                           & (IData)(vlSelf->__PVT__Yr))))
                                : (IData)(vlSelf->__PVT__sum_c)));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if (vlSelf->__PVT__is_shift) {
            vlSelf->__PVT__wd = (1U & VL_SHIFTR_III(2,2,6, 
                                                    ((((IData)(vlSelf->__PVT__is_sll)
                                                        ? 
                                                       ((IData)(vlSelf->__PVT__va) 
                                                        & (IData)(vlSelf->__PVT__a_val))
                                                        : 
                                                       ((IData)(vlSelf->__PVT__vb)
                                                         ? (IData)(vlSelf->d_wdata)
                                                         : (IData)(vlSelf->__PVT__fill))) 
                                                      << 1U) 
                                                     | ((IData)(vlSelf->__PVT__is_sll)
                                                         ? 
                                                        ((IData)(vlSelf->__PVT__vb) 
                                                         & (IData)(vlSelf->d_wdata))
                                                         : 
                                                        ((IData)(vlSelf->__PVT__va)
                                                          ? (IData)(vlSelf->__PVT__a_val)
                                                          : (IData)(vlSelf->__PVT__fill)))), 
                                                    ((IData)(vlSelf->__PVT__is_sll)
                                                      ? 1U
                                                      : 0U)));
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        if ((3U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__wd = vlSymsp->TOP.tb_sys5__DOT__dut__DOT__slot__BRA__7__KET____DOT__dq_b;
        } else if (vlSelf->__PVT__is_slt) {
            vlSelf->__PVT__wd = ((0U == (IData)(vlSelf->__PVT__k)) 
                                 & ((2U == (7U & (vlSelf->__PVT__ir 
                                                  >> 0xcU)))
                                     ? (IData)(vlSelf->__PVT__f_lt)
                                     : (IData)(vlSelf->__PVT__f_ltu)));
        } else if ((0x67U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__wd = (1U & (IData)(vlSelf->__PVT__sum_c));
        }
    }
}

VL_ATTR_COLD void Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__8__KET____DOT__core__0(Vtb_sys5_uc_core_v2s__W1* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_sys5__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+          Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__8__KET____DOT__core__0\n"); );
    // Init
    CData/*0:0*/ __PVT__cond;
    __PVT__cond = 0;
    CData/*0:0*/ __PVT__we;
    __PVT__we = 0;
    CData/*0:0*/ __VdfgExtracted_h62388771__0;
    __VdfgExtracted_h62388771__0 = 0;
    CData/*0:0*/ __VdfgTmp_h2cd83c5b__0;
    __VdfgTmp_h2cd83c5b__0 = 0;
    CData/*0:0*/ __VdfgTmp_he83b8d53__0;
    __VdfgTmp_he83b8d53__0 = 0;
    CData/*0:0*/ __VdfgTmp_hd9b60348__0;
    __VdfgTmp_hd9b60348__0 = 0;
    CData/*5:0*/ __Vtableidx9;
    __Vtableidx9 = 0;
    // Body
    vlSelf->__PVT__rs2 = (0x1fU & (vlSelf->__PVT__ir 
                                   >> 0x14U));
    vlSelf->__PVT__is_sys = (0x73U == (0x7fU & vlSelf->__PVT__ir));
    vlSelf->__PVT__last_up = (0x1fU == (IData)(vlSelf->__PVT__k));
    vlSelf->__PVT__pc_rot = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__pc, 1U) 
                             | VL_SHIFTL_III(32,32,32, vlSelf->__PVT__pc, 0x1fU));
    vlSelf->__PVT__imm_rot = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__imm_sr, 1U) 
                              | VL_SHIFTL_III(32,32,32, vlSelf->__PVT__imm_sr, 0x1fU));
    vlSelf->__PVT__opc = (0x7fU & vlSelf->__PVT__ir);
    vlSelf->d_addr = (((QData)((IData)((vlSelf->__PVT__addr 
                                        >> 2U))) << 5U) 
                      | (QData)((IData)(vlSelf->__PVT__k)));
    vlSelf->rw_addr = ((0x3e0U & (vlSelf->__PVT__ir 
                                  >> 2U)) | (IData)(vlSelf->__PVT__k));
    __VdfgTmp_h2cd83c5b__0 = ((0x37U == (0x7fU & vlSelf->__PVT__ir)) 
                              | (0x17U == (0x7fU & vlSelf->__PVT__ir)));
    __Vtableidx9 = (((IData)(vlSelf->__PVT__f_eq) << 5U) 
                    | (((IData)(vlSelf->__PVT__f_lt) 
                        << 4U) | (((IData)(vlSelf->__PVT__f_ltu) 
                                   << 3U) | (7U & (vlSelf->__PVT__ir 
                                                   >> 0xcU)))));
    __PVT__cond = Vtb_sys5__ConstPool__TABLE_h2a0441a0_0
        [__Vtableidx9];
    vlSelf->__PVT__a_val = ((0U != (0x1fU & (vlSelf->__PVT__ir 
                                             >> 0xfU))) 
                            & (IData)(vlSymsp->TOP.tb_sys5__DOT__dut__DOT__slot__BRA__8__KET____DOT__rqa_b));
    __VdfgTmp_hd9b60348__0 = ((2U == (7U & (vlSelf->__PVT__ir 
                                            >> 0xcU))) 
                              | (3U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))));
    vlSelf->__VdfgTmp_h18c46dac__0 = ((0x13U == (0x7fU 
                                                 & vlSelf->__PVT__ir)) 
                                      | (0x33U == (0x7fU 
                                                   & vlSelf->__PVT__ir)));
    __VdfgTmp_he83b8d53__0 = ((1U == (7U & (vlSelf->__PVT__ir 
                                            >> 0xcU))) 
                              | (5U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))));
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
    vlSelf->__PVT__X = vlSelf->__PVT__a_val;
    vlSelf->__PVT__is_cmp = ((0x63U == (0x7fU & vlSelf->__PVT__ir)) 
                             | ((IData)(vlSelf->__VdfgTmp_h18c46dac__0) 
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
    vlSelf->__PVT__inv = 0U;
    vlSelf->__PVT__is_shift = ((IData)(vlSelf->__PVT__sh_i) 
                               | ((0x33U == (0x7fU 
                                             & vlSelf->__PVT__ir)) 
                                  & (IData)(__VdfgTmp_he83b8d53__0)));
    __PVT__we = 0U;
    vlSelf->__PVT__fill = ((IData)(vlSelf->__PVT__is_shift) 
                           & (IData)(((0x40005000U 
                                       == (0x40007000U 
                                           & vlSelf->__PVT__ir)) 
                                      & (IData)(vlSelf->__PVT__sgn))));
    vlSelf->__PVT__is_sll = ((IData)(vlSelf->__PVT__is_shift) 
                             & (0x1000U == (0x7000U 
                                            & vlSelf->__PVT__ir)));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        vlSelf->__PVT__shx = vlSelf->__PVT__is_shift;
        if ((0x37U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__X = 0U;
        } else if ((0x17U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
        } else if ((0x6fU == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
        }
        if ((0x37U != (0x7fU & vlSelf->__PVT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->__PVT__ir))) {
                if ((0x6fU != (0x7fU & vlSelf->__PVT__ir))) {
                    if (((IData)((0x40000033U == (0x4000707fU 
                                                  & vlSelf->__PVT__ir))) 
                         | (IData)(vlSelf->__PVT__is_cmp))) {
                        vlSelf->__PVT__inv = 1U;
                    }
                }
            }
        }
        if (vlSelf->__PVT__is_shift) {
            __PVT__we = 1U;
        } else if (__VdfgExtracted_h62388771__0) {
            __PVT__we = 1U;
        } else if (((~ (IData)(vlSelf->__PVT__is_cmp)) 
                    & (IData)(vlSelf->__VdfgTmp_h18c46dac__0))) {
            __PVT__we = 1U;
        }
    } else {
        vlSelf->__PVT__shx = 0U;
        if ((4U == (IData)(vlSelf->__PVT__state))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
            if ((3U == (0x7fU & vlSelf->__PVT__ir))) {
                __PVT__we = 1U;
            } else if (vlSelf->__PVT__is_slt) {
                __PVT__we = 1U;
            } else if ((0x67U == (0x7fU & vlSelf->__PVT__ir))) {
                __PVT__we = 1U;
            }
        } else if ((5U == (IData)(vlSelf->__PVT__state))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
        }
    }
    vlSelf->rw_en = ((IData)(__PVT__we) & (0U != (0x1fU 
                                                  & (vlSelf->__PVT__ir 
                                                     >> 7U))));
    if (vlSelf->__PVT__is_sll) {
        vlSelf->__PVT__sll_dir = vlSelf->__PVT__is_shift;
        vlSelf->__PVT__ia = (0x1ffU & ((IData)(vlSelf->__PVT__k) 
                                       - (IData)(vlSelf->__PVT__shamt_w)));
        vlSelf->__VdfgTmp_h586768a0__0 = ((VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__k)) 
                                           - VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__shamt_w))) 
                                          - (IData)(1U));
    } else {
        vlSelf->__PVT__sll_dir = 0U;
        vlSelf->__PVT__ia = (0x1ffU & ((IData)(vlSelf->__PVT__k) 
                                       + (IData)(vlSelf->__PVT__shamt_w)));
        vlSelf->__VdfgTmp_h586768a0__0 = ((IData)(1U) 
                                          + (VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__k)) 
                                             + VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__shamt_w))));
    }
    vlSelf->d_wdata = ((~ ((IData)(vlSelf->__PVT__shx)
                            ? (0U == (0x1fU & (vlSelf->__PVT__ir 
                                               >> 0xfU)))
                            : (0U == (0x1fU & (vlSelf->__PVT__ir 
                                               >> 0x14U))))) 
                       & (IData)(vlSymsp->TOP.tb_sys5__DOT__dut__DOT__slot__BRA__8__KET____DOT__rqb_b));
    vlSelf->__PVT__exec_done = ((IData)(vlSelf->__PVT__sll_dir)
                                 ? (0U == (IData)(vlSelf->__PVT__k))
                                 : (0x1fU == (IData)(vlSelf->__PVT__k)));
    vlSelf->__PVT__va = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__ia))) 
                         & VL_GTES_III(32, 0x1fU, VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__ia))));
    vlSelf->__PVT__vb = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, 
                                                           (0x1ffU 
                                                            & vlSelf->__VdfgTmp_h586768a0__0))) 
                         & VL_GTES_III(32, 0x1fU, VL_EXTENDS_II(32,9, 
                                                                (0x1ffU 
                                                                 & vlSelf->__VdfgTmp_h586768a0__0))));
    vlSelf->__PVT__Yr = (1U & (((0x33U == (0x7fU & vlSelf->__PVT__ir)) 
                                | (0x63U == (0x7fU 
                                             & vlSelf->__PVT__ir)))
                                ? (IData)(vlSelf->d_wdata)
                                : vlSelf->__PVT__imm_sr));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if ((0x37U != (0x7fU & vlSelf->__PVT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->__PVT__ir))) {
                if ((0x6fU == (0x7fU & vlSelf->__PVT__ir))) {
                    vlSelf->__PVT__Yr = (1U & (4U >> (IData)(vlSelf->__PVT__k)));
                }
            }
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        vlSelf->__PVT__Yr = (1U & (4U >> (IData)(vlSelf->__PVT__k)));
    } else if ((5U == (IData)(vlSelf->__PVT__state))) {
        vlSelf->__PVT__Yr = (1U & (((0x6fU == (0x7fU 
                                               & vlSelf->__PVT__ir)) 
                                    | ((0x63U == (0x7fU 
                                                  & vlSelf->__PVT__ir)) 
                                       & (IData)(__PVT__cond)))
                                    ? vlSelf->__PVT__imm_sr
                                    : (4U >> (IData)(vlSelf->__PVT__k))));
    }
    vlSelf->__PVT__sum_c = (3U & ((IData)(vlSelf->__PVT__X) 
                                  + ((1U & ((IData)(vlSelf->__PVT__inv)
                                             ? (~ (IData)(vlSelf->__PVT__Yr))
                                             : (IData)(vlSelf->__PVT__Yr))) 
                                     + ((0U == (IData)(vlSelf->__PVT__k))
                                         ? (IData)(vlSelf->__PVT__inv)
                                         : (IData)(vlSelf->__PVT__cy)))));
    vlSelf->__PVT__addr_ins = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__addr, 1U) 
                               | VL_SHIFTL_III(32,32,32, 
                                               (1U 
                                                & (IData)(vlSelf->__PVT__sum_c)), 0x1fU));
    vlSelf->__PVT__pc_ins = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__pc, 1U) 
                             | VL_SHIFTL_III(32,32,32, 
                                             (1U & (IData)(vlSelf->__PVT__sum_c)), 0x1fU));
    vlSelf->__PVT__nz_n = (1U & (((0U != (IData)(vlSelf->__PVT__k)) 
                                  & (IData)(vlSelf->__PVT__nz)) 
                                 | (IData)(vlSelf->__PVT__sum_c)));
    vlSelf->__PVT__wd = (1U & (((IData)(vlSelf->__VdfgTmp_h18c46dac__0) 
                                & ((4U == (7U & (vlSelf->__PVT__ir 
                                                 >> 0xcU))) 
                                   | ((6U == (7U & 
                                              (vlSelf->__PVT__ir 
                                               >> 0xcU))) 
                                      | (7U == (7U 
                                                & (vlSelf->__PVT__ir 
                                                   >> 0xcU))))))
                                ? ((4U == (7U & (vlSelf->__PVT__ir 
                                                 >> 0xcU)))
                                    ? ((IData)(vlSelf->__PVT__X) 
                                       ^ (IData)(vlSelf->__PVT__Yr))
                                    : ((6U == (7U & 
                                               (vlSelf->__PVT__ir 
                                                >> 0xcU)))
                                        ? ((IData)(vlSelf->__PVT__X) 
                                           | (IData)(vlSelf->__PVT__Yr))
                                        : ((IData)(vlSelf->__PVT__X) 
                                           & (IData)(vlSelf->__PVT__Yr))))
                                : (IData)(vlSelf->__PVT__sum_c)));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if (vlSelf->__PVT__is_shift) {
            vlSelf->__PVT__wd = (1U & VL_SHIFTR_III(2,2,6, 
                                                    ((((IData)(vlSelf->__PVT__is_sll)
                                                        ? 
                                                       ((IData)(vlSelf->__PVT__va) 
                                                        & (IData)(vlSelf->__PVT__a_val))
                                                        : 
                                                       ((IData)(vlSelf->__PVT__vb)
                                                         ? (IData)(vlSelf->d_wdata)
                                                         : (IData)(vlSelf->__PVT__fill))) 
                                                      << 1U) 
                                                     | ((IData)(vlSelf->__PVT__is_sll)
                                                         ? 
                                                        ((IData)(vlSelf->__PVT__vb) 
                                                         & (IData)(vlSelf->d_wdata))
                                                         : 
                                                        ((IData)(vlSelf->__PVT__va)
                                                          ? (IData)(vlSelf->__PVT__a_val)
                                                          : (IData)(vlSelf->__PVT__fill)))), 
                                                    ((IData)(vlSelf->__PVT__is_sll)
                                                      ? 1U
                                                      : 0U)));
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        if ((3U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__wd = vlSymsp->TOP.tb_sys5__DOT__dut__DOT__slot__BRA__8__KET____DOT__dq_b;
        } else if (vlSelf->__PVT__is_slt) {
            vlSelf->__PVT__wd = ((0U == (IData)(vlSelf->__PVT__k)) 
                                 & ((2U == (7U & (vlSelf->__PVT__ir 
                                                  >> 0xcU)))
                                     ? (IData)(vlSelf->__PVT__f_lt)
                                     : (IData)(vlSelf->__PVT__f_ltu)));
        } else if ((0x67U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__wd = (1U & (IData)(vlSelf->__PVT__sum_c));
        }
    }
}

VL_ATTR_COLD void Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__9__KET____DOT__core__0(Vtb_sys5_uc_core_v2s__W1* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_sys5__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+          Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__9__KET____DOT__core__0\n"); );
    // Init
    CData/*0:0*/ __PVT__cond;
    __PVT__cond = 0;
    CData/*0:0*/ __PVT__we;
    __PVT__we = 0;
    CData/*0:0*/ __VdfgExtracted_h62388771__0;
    __VdfgExtracted_h62388771__0 = 0;
    CData/*0:0*/ __VdfgTmp_h2cd83c5b__0;
    __VdfgTmp_h2cd83c5b__0 = 0;
    CData/*0:0*/ __VdfgTmp_he83b8d53__0;
    __VdfgTmp_he83b8d53__0 = 0;
    CData/*0:0*/ __VdfgTmp_hd9b60348__0;
    __VdfgTmp_hd9b60348__0 = 0;
    CData/*5:0*/ __Vtableidx10;
    __Vtableidx10 = 0;
    // Body
    vlSelf->__PVT__rs2 = (0x1fU & (vlSelf->__PVT__ir 
                                   >> 0x14U));
    vlSelf->__PVT__is_sys = (0x73U == (0x7fU & vlSelf->__PVT__ir));
    vlSelf->__PVT__last_up = (0x1fU == (IData)(vlSelf->__PVT__k));
    vlSelf->__PVT__pc_rot = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__pc, 1U) 
                             | VL_SHIFTL_III(32,32,32, vlSelf->__PVT__pc, 0x1fU));
    vlSelf->__PVT__imm_rot = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__imm_sr, 1U) 
                              | VL_SHIFTL_III(32,32,32, vlSelf->__PVT__imm_sr, 0x1fU));
    vlSelf->__PVT__opc = (0x7fU & vlSelf->__PVT__ir);
    vlSelf->d_addr = (((QData)((IData)((vlSelf->__PVT__addr 
                                        >> 2U))) << 5U) 
                      | (QData)((IData)(vlSelf->__PVT__k)));
    vlSelf->rw_addr = ((0x3e0U & (vlSelf->__PVT__ir 
                                  >> 2U)) | (IData)(vlSelf->__PVT__k));
    __VdfgTmp_h2cd83c5b__0 = ((0x37U == (0x7fU & vlSelf->__PVT__ir)) 
                              | (0x17U == (0x7fU & vlSelf->__PVT__ir)));
    __Vtableidx10 = (((IData)(vlSelf->__PVT__f_eq) 
                      << 5U) | (((IData)(vlSelf->__PVT__f_lt) 
                                 << 4U) | (((IData)(vlSelf->__PVT__f_ltu) 
                                            << 3U) 
                                           | (7U & 
                                              (vlSelf->__PVT__ir 
                                               >> 0xcU)))));
    __PVT__cond = Vtb_sys5__ConstPool__TABLE_h2a0441a0_0
        [__Vtableidx10];
    vlSelf->__PVT__a_val = ((0U != (0x1fU & (vlSelf->__PVT__ir 
                                             >> 0xfU))) 
                            & (IData)(vlSymsp->TOP.tb_sys5__DOT__dut__DOT__slot__BRA__9__KET____DOT__rqa_b));
    __VdfgTmp_hd9b60348__0 = ((2U == (7U & (vlSelf->__PVT__ir 
                                            >> 0xcU))) 
                              | (3U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))));
    vlSelf->__VdfgTmp_h18c46dac__0 = ((0x13U == (0x7fU 
                                                 & vlSelf->__PVT__ir)) 
                                      | (0x33U == (0x7fU 
                                                   & vlSelf->__PVT__ir)));
    __VdfgTmp_he83b8d53__0 = ((1U == (7U & (vlSelf->__PVT__ir 
                                            >> 0xcU))) 
                              | (5U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))));
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
    vlSelf->__PVT__X = vlSelf->__PVT__a_val;
    vlSelf->__PVT__is_cmp = ((0x63U == (0x7fU & vlSelf->__PVT__ir)) 
                             | ((IData)(vlSelf->__VdfgTmp_h18c46dac__0) 
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
    vlSelf->__PVT__inv = 0U;
    vlSelf->__PVT__is_shift = ((IData)(vlSelf->__PVT__sh_i) 
                               | ((0x33U == (0x7fU 
                                             & vlSelf->__PVT__ir)) 
                                  & (IData)(__VdfgTmp_he83b8d53__0)));
    __PVT__we = 0U;
    vlSelf->__PVT__fill = ((IData)(vlSelf->__PVT__is_shift) 
                           & (IData)(((0x40005000U 
                                       == (0x40007000U 
                                           & vlSelf->__PVT__ir)) 
                                      & (IData)(vlSelf->__PVT__sgn))));
    vlSelf->__PVT__is_sll = ((IData)(vlSelf->__PVT__is_shift) 
                             & (0x1000U == (0x7000U 
                                            & vlSelf->__PVT__ir)));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        vlSelf->__PVT__shx = vlSelf->__PVT__is_shift;
        if ((0x37U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__X = 0U;
        } else if ((0x17U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
        } else if ((0x6fU == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
        }
        if ((0x37U != (0x7fU & vlSelf->__PVT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->__PVT__ir))) {
                if ((0x6fU != (0x7fU & vlSelf->__PVT__ir))) {
                    if (((IData)((0x40000033U == (0x4000707fU 
                                                  & vlSelf->__PVT__ir))) 
                         | (IData)(vlSelf->__PVT__is_cmp))) {
                        vlSelf->__PVT__inv = 1U;
                    }
                }
            }
        }
        if (vlSelf->__PVT__is_shift) {
            __PVT__we = 1U;
        } else if (__VdfgExtracted_h62388771__0) {
            __PVT__we = 1U;
        } else if (((~ (IData)(vlSelf->__PVT__is_cmp)) 
                    & (IData)(vlSelf->__VdfgTmp_h18c46dac__0))) {
            __PVT__we = 1U;
        }
    } else {
        vlSelf->__PVT__shx = 0U;
        if ((4U == (IData)(vlSelf->__PVT__state))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
            if ((3U == (0x7fU & vlSelf->__PVT__ir))) {
                __PVT__we = 1U;
            } else if (vlSelf->__PVT__is_slt) {
                __PVT__we = 1U;
            } else if ((0x67U == (0x7fU & vlSelf->__PVT__ir))) {
                __PVT__we = 1U;
            }
        } else if ((5U == (IData)(vlSelf->__PVT__state))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
        }
    }
    vlSelf->rw_en = ((IData)(__PVT__we) & (0U != (0x1fU 
                                                  & (vlSelf->__PVT__ir 
                                                     >> 7U))));
    if (vlSelf->__PVT__is_sll) {
        vlSelf->__PVT__sll_dir = vlSelf->__PVT__is_shift;
        vlSelf->__PVT__ia = (0x1ffU & ((IData)(vlSelf->__PVT__k) 
                                       - (IData)(vlSelf->__PVT__shamt_w)));
        vlSelf->__VdfgTmp_h586768a0__0 = ((VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__k)) 
                                           - VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__shamt_w))) 
                                          - (IData)(1U));
    } else {
        vlSelf->__PVT__sll_dir = 0U;
        vlSelf->__PVT__ia = (0x1ffU & ((IData)(vlSelf->__PVT__k) 
                                       + (IData)(vlSelf->__PVT__shamt_w)));
        vlSelf->__VdfgTmp_h586768a0__0 = ((IData)(1U) 
                                          + (VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__k)) 
                                             + VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__shamt_w))));
    }
    vlSelf->d_wdata = ((~ ((IData)(vlSelf->__PVT__shx)
                            ? (0U == (0x1fU & (vlSelf->__PVT__ir 
                                               >> 0xfU)))
                            : (0U == (0x1fU & (vlSelf->__PVT__ir 
                                               >> 0x14U))))) 
                       & (IData)(vlSymsp->TOP.tb_sys5__DOT__dut__DOT__slot__BRA__9__KET____DOT__rqb_b));
    vlSelf->__PVT__exec_done = ((IData)(vlSelf->__PVT__sll_dir)
                                 ? (0U == (IData)(vlSelf->__PVT__k))
                                 : (0x1fU == (IData)(vlSelf->__PVT__k)));
    vlSelf->__PVT__va = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__ia))) 
                         & VL_GTES_III(32, 0x1fU, VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__ia))));
    vlSelf->__PVT__vb = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, 
                                                           (0x1ffU 
                                                            & vlSelf->__VdfgTmp_h586768a0__0))) 
                         & VL_GTES_III(32, 0x1fU, VL_EXTENDS_II(32,9, 
                                                                (0x1ffU 
                                                                 & vlSelf->__VdfgTmp_h586768a0__0))));
    vlSelf->__PVT__Yr = (1U & (((0x33U == (0x7fU & vlSelf->__PVT__ir)) 
                                | (0x63U == (0x7fU 
                                             & vlSelf->__PVT__ir)))
                                ? (IData)(vlSelf->d_wdata)
                                : vlSelf->__PVT__imm_sr));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if ((0x37U != (0x7fU & vlSelf->__PVT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->__PVT__ir))) {
                if ((0x6fU == (0x7fU & vlSelf->__PVT__ir))) {
                    vlSelf->__PVT__Yr = (1U & (4U >> (IData)(vlSelf->__PVT__k)));
                }
            }
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        vlSelf->__PVT__Yr = (1U & (4U >> (IData)(vlSelf->__PVT__k)));
    } else if ((5U == (IData)(vlSelf->__PVT__state))) {
        vlSelf->__PVT__Yr = (1U & (((0x6fU == (0x7fU 
                                               & vlSelf->__PVT__ir)) 
                                    | ((0x63U == (0x7fU 
                                                  & vlSelf->__PVT__ir)) 
                                       & (IData)(__PVT__cond)))
                                    ? vlSelf->__PVT__imm_sr
                                    : (4U >> (IData)(vlSelf->__PVT__k))));
    }
    vlSelf->__PVT__sum_c = (3U & ((IData)(vlSelf->__PVT__X) 
                                  + ((1U & ((IData)(vlSelf->__PVT__inv)
                                             ? (~ (IData)(vlSelf->__PVT__Yr))
                                             : (IData)(vlSelf->__PVT__Yr))) 
                                     + ((0U == (IData)(vlSelf->__PVT__k))
                                         ? (IData)(vlSelf->__PVT__inv)
                                         : (IData)(vlSelf->__PVT__cy)))));
    vlSelf->__PVT__addr_ins = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__addr, 1U) 
                               | VL_SHIFTL_III(32,32,32, 
                                               (1U 
                                                & (IData)(vlSelf->__PVT__sum_c)), 0x1fU));
    vlSelf->__PVT__pc_ins = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__pc, 1U) 
                             | VL_SHIFTL_III(32,32,32, 
                                             (1U & (IData)(vlSelf->__PVT__sum_c)), 0x1fU));
    vlSelf->__PVT__nz_n = (1U & (((0U != (IData)(vlSelf->__PVT__k)) 
                                  & (IData)(vlSelf->__PVT__nz)) 
                                 | (IData)(vlSelf->__PVT__sum_c)));
    vlSelf->__PVT__wd = (1U & (((IData)(vlSelf->__VdfgTmp_h18c46dac__0) 
                                & ((4U == (7U & (vlSelf->__PVT__ir 
                                                 >> 0xcU))) 
                                   | ((6U == (7U & 
                                              (vlSelf->__PVT__ir 
                                               >> 0xcU))) 
                                      | (7U == (7U 
                                                & (vlSelf->__PVT__ir 
                                                   >> 0xcU))))))
                                ? ((4U == (7U & (vlSelf->__PVT__ir 
                                                 >> 0xcU)))
                                    ? ((IData)(vlSelf->__PVT__X) 
                                       ^ (IData)(vlSelf->__PVT__Yr))
                                    : ((6U == (7U & 
                                               (vlSelf->__PVT__ir 
                                                >> 0xcU)))
                                        ? ((IData)(vlSelf->__PVT__X) 
                                           | (IData)(vlSelf->__PVT__Yr))
                                        : ((IData)(vlSelf->__PVT__X) 
                                           & (IData)(vlSelf->__PVT__Yr))))
                                : (IData)(vlSelf->__PVT__sum_c)));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if (vlSelf->__PVT__is_shift) {
            vlSelf->__PVT__wd = (1U & VL_SHIFTR_III(2,2,6, 
                                                    ((((IData)(vlSelf->__PVT__is_sll)
                                                        ? 
                                                       ((IData)(vlSelf->__PVT__va) 
                                                        & (IData)(vlSelf->__PVT__a_val))
                                                        : 
                                                       ((IData)(vlSelf->__PVT__vb)
                                                         ? (IData)(vlSelf->d_wdata)
                                                         : (IData)(vlSelf->__PVT__fill))) 
                                                      << 1U) 
                                                     | ((IData)(vlSelf->__PVT__is_sll)
                                                         ? 
                                                        ((IData)(vlSelf->__PVT__vb) 
                                                         & (IData)(vlSelf->d_wdata))
                                                         : 
                                                        ((IData)(vlSelf->__PVT__va)
                                                          ? (IData)(vlSelf->__PVT__a_val)
                                                          : (IData)(vlSelf->__PVT__fill)))), 
                                                    ((IData)(vlSelf->__PVT__is_sll)
                                                      ? 1U
                                                      : 0U)));
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        if ((3U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__wd = vlSymsp->TOP.tb_sys5__DOT__dut__DOT__slot__BRA__9__KET____DOT__dq_b;
        } else if (vlSelf->__PVT__is_slt) {
            vlSelf->__PVT__wd = ((0U == (IData)(vlSelf->__PVT__k)) 
                                 & ((2U == (7U & (vlSelf->__PVT__ir 
                                                  >> 0xcU)))
                                     ? (IData)(vlSelf->__PVT__f_lt)
                                     : (IData)(vlSelf->__PVT__f_ltu)));
        } else if ((0x67U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__wd = (1U & (IData)(vlSelf->__PVT__sum_c));
        }
    }
}

VL_ATTR_COLD void Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__10__KET____DOT__core__0(Vtb_sys5_uc_core_v2s__W1* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_sys5__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+          Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__10__KET____DOT__core__0\n"); );
    // Init
    CData/*0:0*/ __PVT__cond;
    __PVT__cond = 0;
    CData/*0:0*/ __PVT__we;
    __PVT__we = 0;
    CData/*0:0*/ __VdfgExtracted_h62388771__0;
    __VdfgExtracted_h62388771__0 = 0;
    CData/*0:0*/ __VdfgTmp_h2cd83c5b__0;
    __VdfgTmp_h2cd83c5b__0 = 0;
    CData/*0:0*/ __VdfgTmp_he83b8d53__0;
    __VdfgTmp_he83b8d53__0 = 0;
    CData/*0:0*/ __VdfgTmp_hd9b60348__0;
    __VdfgTmp_hd9b60348__0 = 0;
    CData/*5:0*/ __Vtableidx11;
    __Vtableidx11 = 0;
    // Body
    vlSelf->__PVT__rs2 = (0x1fU & (vlSelf->__PVT__ir 
                                   >> 0x14U));
    vlSelf->__PVT__is_sys = (0x73U == (0x7fU & vlSelf->__PVT__ir));
    vlSelf->__PVT__last_up = (0x1fU == (IData)(vlSelf->__PVT__k));
    vlSelf->__PVT__pc_rot = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__pc, 1U) 
                             | VL_SHIFTL_III(32,32,32, vlSelf->__PVT__pc, 0x1fU));
    vlSelf->__PVT__imm_rot = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__imm_sr, 1U) 
                              | VL_SHIFTL_III(32,32,32, vlSelf->__PVT__imm_sr, 0x1fU));
    vlSelf->__PVT__opc = (0x7fU & vlSelf->__PVT__ir);
    vlSelf->d_addr = (((QData)((IData)((vlSelf->__PVT__addr 
                                        >> 2U))) << 5U) 
                      | (QData)((IData)(vlSelf->__PVT__k)));
    vlSelf->rw_addr = ((0x3e0U & (vlSelf->__PVT__ir 
                                  >> 2U)) | (IData)(vlSelf->__PVT__k));
    __VdfgTmp_h2cd83c5b__0 = ((0x37U == (0x7fU & vlSelf->__PVT__ir)) 
                              | (0x17U == (0x7fU & vlSelf->__PVT__ir)));
    __Vtableidx11 = (((IData)(vlSelf->__PVT__f_eq) 
                      << 5U) | (((IData)(vlSelf->__PVT__f_lt) 
                                 << 4U) | (((IData)(vlSelf->__PVT__f_ltu) 
                                            << 3U) 
                                           | (7U & 
                                              (vlSelf->__PVT__ir 
                                               >> 0xcU)))));
    __PVT__cond = Vtb_sys5__ConstPool__TABLE_h2a0441a0_0
        [__Vtableidx11];
    vlSelf->__PVT__a_val = ((0U != (0x1fU & (vlSelf->__PVT__ir 
                                             >> 0xfU))) 
                            & (IData)(vlSymsp->TOP.tb_sys5__DOT__dut__DOT__slot__BRA__10__KET____DOT__rqa_b));
    __VdfgTmp_hd9b60348__0 = ((2U == (7U & (vlSelf->__PVT__ir 
                                            >> 0xcU))) 
                              | (3U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))));
    vlSelf->__VdfgTmp_h18c46dac__0 = ((0x13U == (0x7fU 
                                                 & vlSelf->__PVT__ir)) 
                                      | (0x33U == (0x7fU 
                                                   & vlSelf->__PVT__ir)));
    __VdfgTmp_he83b8d53__0 = ((1U == (7U & (vlSelf->__PVT__ir 
                                            >> 0xcU))) 
                              | (5U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))));
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
    vlSelf->__PVT__X = vlSelf->__PVT__a_val;
    vlSelf->__PVT__is_cmp = ((0x63U == (0x7fU & vlSelf->__PVT__ir)) 
                             | ((IData)(vlSelf->__VdfgTmp_h18c46dac__0) 
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
    vlSelf->__PVT__inv = 0U;
    vlSelf->__PVT__is_shift = ((IData)(vlSelf->__PVT__sh_i) 
                               | ((0x33U == (0x7fU 
                                             & vlSelf->__PVT__ir)) 
                                  & (IData)(__VdfgTmp_he83b8d53__0)));
    __PVT__we = 0U;
    vlSelf->__PVT__fill = ((IData)(vlSelf->__PVT__is_shift) 
                           & (IData)(((0x40005000U 
                                       == (0x40007000U 
                                           & vlSelf->__PVT__ir)) 
                                      & (IData)(vlSelf->__PVT__sgn))));
    vlSelf->__PVT__is_sll = ((IData)(vlSelf->__PVT__is_shift) 
                             & (0x1000U == (0x7000U 
                                            & vlSelf->__PVT__ir)));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        vlSelf->__PVT__shx = vlSelf->__PVT__is_shift;
        if ((0x37U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__X = 0U;
        } else if ((0x17U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
        } else if ((0x6fU == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
        }
        if ((0x37U != (0x7fU & vlSelf->__PVT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->__PVT__ir))) {
                if ((0x6fU != (0x7fU & vlSelf->__PVT__ir))) {
                    if (((IData)((0x40000033U == (0x4000707fU 
                                                  & vlSelf->__PVT__ir))) 
                         | (IData)(vlSelf->__PVT__is_cmp))) {
                        vlSelf->__PVT__inv = 1U;
                    }
                }
            }
        }
        if (vlSelf->__PVT__is_shift) {
            __PVT__we = 1U;
        } else if (__VdfgExtracted_h62388771__0) {
            __PVT__we = 1U;
        } else if (((~ (IData)(vlSelf->__PVT__is_cmp)) 
                    & (IData)(vlSelf->__VdfgTmp_h18c46dac__0))) {
            __PVT__we = 1U;
        }
    } else {
        vlSelf->__PVT__shx = 0U;
        if ((4U == (IData)(vlSelf->__PVT__state))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
            if ((3U == (0x7fU & vlSelf->__PVT__ir))) {
                __PVT__we = 1U;
            } else if (vlSelf->__PVT__is_slt) {
                __PVT__we = 1U;
            } else if ((0x67U == (0x7fU & vlSelf->__PVT__ir))) {
                __PVT__we = 1U;
            }
        } else if ((5U == (IData)(vlSelf->__PVT__state))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
        }
    }
    vlSelf->rw_en = ((IData)(__PVT__we) & (0U != (0x1fU 
                                                  & (vlSelf->__PVT__ir 
                                                     >> 7U))));
    if (vlSelf->__PVT__is_sll) {
        vlSelf->__PVT__sll_dir = vlSelf->__PVT__is_shift;
        vlSelf->__PVT__ia = (0x1ffU & ((IData)(vlSelf->__PVT__k) 
                                       - (IData)(vlSelf->__PVT__shamt_w)));
        vlSelf->__VdfgTmp_h586768a0__0 = ((VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__k)) 
                                           - VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__shamt_w))) 
                                          - (IData)(1U));
    } else {
        vlSelf->__PVT__sll_dir = 0U;
        vlSelf->__PVT__ia = (0x1ffU & ((IData)(vlSelf->__PVT__k) 
                                       + (IData)(vlSelf->__PVT__shamt_w)));
        vlSelf->__VdfgTmp_h586768a0__0 = ((IData)(1U) 
                                          + (VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__k)) 
                                             + VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__shamt_w))));
    }
    vlSelf->d_wdata = ((~ ((IData)(vlSelf->__PVT__shx)
                            ? (0U == (0x1fU & (vlSelf->__PVT__ir 
                                               >> 0xfU)))
                            : (0U == (0x1fU & (vlSelf->__PVT__ir 
                                               >> 0x14U))))) 
                       & (IData)(vlSymsp->TOP.tb_sys5__DOT__dut__DOT__slot__BRA__10__KET____DOT__rqb_b));
    vlSelf->__PVT__exec_done = ((IData)(vlSelf->__PVT__sll_dir)
                                 ? (0U == (IData)(vlSelf->__PVT__k))
                                 : (0x1fU == (IData)(vlSelf->__PVT__k)));
    vlSelf->__PVT__va = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__ia))) 
                         & VL_GTES_III(32, 0x1fU, VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__ia))));
    vlSelf->__PVT__vb = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, 
                                                           (0x1ffU 
                                                            & vlSelf->__VdfgTmp_h586768a0__0))) 
                         & VL_GTES_III(32, 0x1fU, VL_EXTENDS_II(32,9, 
                                                                (0x1ffU 
                                                                 & vlSelf->__VdfgTmp_h586768a0__0))));
    vlSelf->__PVT__Yr = (1U & (((0x33U == (0x7fU & vlSelf->__PVT__ir)) 
                                | (0x63U == (0x7fU 
                                             & vlSelf->__PVT__ir)))
                                ? (IData)(vlSelf->d_wdata)
                                : vlSelf->__PVT__imm_sr));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if ((0x37U != (0x7fU & vlSelf->__PVT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->__PVT__ir))) {
                if ((0x6fU == (0x7fU & vlSelf->__PVT__ir))) {
                    vlSelf->__PVT__Yr = (1U & (4U >> (IData)(vlSelf->__PVT__k)));
                }
            }
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        vlSelf->__PVT__Yr = (1U & (4U >> (IData)(vlSelf->__PVT__k)));
    } else if ((5U == (IData)(vlSelf->__PVT__state))) {
        vlSelf->__PVT__Yr = (1U & (((0x6fU == (0x7fU 
                                               & vlSelf->__PVT__ir)) 
                                    | ((0x63U == (0x7fU 
                                                  & vlSelf->__PVT__ir)) 
                                       & (IData)(__PVT__cond)))
                                    ? vlSelf->__PVT__imm_sr
                                    : (4U >> (IData)(vlSelf->__PVT__k))));
    }
    vlSelf->__PVT__sum_c = (3U & ((IData)(vlSelf->__PVT__X) 
                                  + ((1U & ((IData)(vlSelf->__PVT__inv)
                                             ? (~ (IData)(vlSelf->__PVT__Yr))
                                             : (IData)(vlSelf->__PVT__Yr))) 
                                     + ((0U == (IData)(vlSelf->__PVT__k))
                                         ? (IData)(vlSelf->__PVT__inv)
                                         : (IData)(vlSelf->__PVT__cy)))));
    vlSelf->__PVT__addr_ins = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__addr, 1U) 
                               | VL_SHIFTL_III(32,32,32, 
                                               (1U 
                                                & (IData)(vlSelf->__PVT__sum_c)), 0x1fU));
    vlSelf->__PVT__pc_ins = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__pc, 1U) 
                             | VL_SHIFTL_III(32,32,32, 
                                             (1U & (IData)(vlSelf->__PVT__sum_c)), 0x1fU));
    vlSelf->__PVT__nz_n = (1U & (((0U != (IData)(vlSelf->__PVT__k)) 
                                  & (IData)(vlSelf->__PVT__nz)) 
                                 | (IData)(vlSelf->__PVT__sum_c)));
    vlSelf->__PVT__wd = (1U & (((IData)(vlSelf->__VdfgTmp_h18c46dac__0) 
                                & ((4U == (7U & (vlSelf->__PVT__ir 
                                                 >> 0xcU))) 
                                   | ((6U == (7U & 
                                              (vlSelf->__PVT__ir 
                                               >> 0xcU))) 
                                      | (7U == (7U 
                                                & (vlSelf->__PVT__ir 
                                                   >> 0xcU))))))
                                ? ((4U == (7U & (vlSelf->__PVT__ir 
                                                 >> 0xcU)))
                                    ? ((IData)(vlSelf->__PVT__X) 
                                       ^ (IData)(vlSelf->__PVT__Yr))
                                    : ((6U == (7U & 
                                               (vlSelf->__PVT__ir 
                                                >> 0xcU)))
                                        ? ((IData)(vlSelf->__PVT__X) 
                                           | (IData)(vlSelf->__PVT__Yr))
                                        : ((IData)(vlSelf->__PVT__X) 
                                           & (IData)(vlSelf->__PVT__Yr))))
                                : (IData)(vlSelf->__PVT__sum_c)));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if (vlSelf->__PVT__is_shift) {
            vlSelf->__PVT__wd = (1U & VL_SHIFTR_III(2,2,6, 
                                                    ((((IData)(vlSelf->__PVT__is_sll)
                                                        ? 
                                                       ((IData)(vlSelf->__PVT__va) 
                                                        & (IData)(vlSelf->__PVT__a_val))
                                                        : 
                                                       ((IData)(vlSelf->__PVT__vb)
                                                         ? (IData)(vlSelf->d_wdata)
                                                         : (IData)(vlSelf->__PVT__fill))) 
                                                      << 1U) 
                                                     | ((IData)(vlSelf->__PVT__is_sll)
                                                         ? 
                                                        ((IData)(vlSelf->__PVT__vb) 
                                                         & (IData)(vlSelf->d_wdata))
                                                         : 
                                                        ((IData)(vlSelf->__PVT__va)
                                                          ? (IData)(vlSelf->__PVT__a_val)
                                                          : (IData)(vlSelf->__PVT__fill)))), 
                                                    ((IData)(vlSelf->__PVT__is_sll)
                                                      ? 1U
                                                      : 0U)));
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        if ((3U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__wd = vlSymsp->TOP.tb_sys5__DOT__dut__DOT__slot__BRA__10__KET____DOT__dq_b;
        } else if (vlSelf->__PVT__is_slt) {
            vlSelf->__PVT__wd = ((0U == (IData)(vlSelf->__PVT__k)) 
                                 & ((2U == (7U & (vlSelf->__PVT__ir 
                                                  >> 0xcU)))
                                     ? (IData)(vlSelf->__PVT__f_lt)
                                     : (IData)(vlSelf->__PVT__f_ltu)));
        } else if ((0x67U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__wd = (1U & (IData)(vlSelf->__PVT__sum_c));
        }
    }
}

VL_ATTR_COLD void Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__11__KET____DOT__core__0(Vtb_sys5_uc_core_v2s__W1* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_sys5__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+          Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__11__KET____DOT__core__0\n"); );
    // Init
    CData/*0:0*/ __PVT__cond;
    __PVT__cond = 0;
    CData/*0:0*/ __PVT__we;
    __PVT__we = 0;
    CData/*0:0*/ __VdfgExtracted_h62388771__0;
    __VdfgExtracted_h62388771__0 = 0;
    CData/*0:0*/ __VdfgTmp_h2cd83c5b__0;
    __VdfgTmp_h2cd83c5b__0 = 0;
    CData/*0:0*/ __VdfgTmp_he83b8d53__0;
    __VdfgTmp_he83b8d53__0 = 0;
    CData/*0:0*/ __VdfgTmp_hd9b60348__0;
    __VdfgTmp_hd9b60348__0 = 0;
    CData/*5:0*/ __Vtableidx12;
    __Vtableidx12 = 0;
    // Body
    vlSelf->__PVT__rs2 = (0x1fU & (vlSelf->__PVT__ir 
                                   >> 0x14U));
    vlSelf->__PVT__is_sys = (0x73U == (0x7fU & vlSelf->__PVT__ir));
    vlSelf->__PVT__last_up = (0x1fU == (IData)(vlSelf->__PVT__k));
    vlSelf->__PVT__pc_rot = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__pc, 1U) 
                             | VL_SHIFTL_III(32,32,32, vlSelf->__PVT__pc, 0x1fU));
    vlSelf->__PVT__imm_rot = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__imm_sr, 1U) 
                              | VL_SHIFTL_III(32,32,32, vlSelf->__PVT__imm_sr, 0x1fU));
    vlSelf->__PVT__opc = (0x7fU & vlSelf->__PVT__ir);
    vlSelf->d_addr = (((QData)((IData)((vlSelf->__PVT__addr 
                                        >> 2U))) << 5U) 
                      | (QData)((IData)(vlSelf->__PVT__k)));
    vlSelf->rw_addr = ((0x3e0U & (vlSelf->__PVT__ir 
                                  >> 2U)) | (IData)(vlSelf->__PVT__k));
    __VdfgTmp_h2cd83c5b__0 = ((0x37U == (0x7fU & vlSelf->__PVT__ir)) 
                              | (0x17U == (0x7fU & vlSelf->__PVT__ir)));
    __Vtableidx12 = (((IData)(vlSelf->__PVT__f_eq) 
                      << 5U) | (((IData)(vlSelf->__PVT__f_lt) 
                                 << 4U) | (((IData)(vlSelf->__PVT__f_ltu) 
                                            << 3U) 
                                           | (7U & 
                                              (vlSelf->__PVT__ir 
                                               >> 0xcU)))));
    __PVT__cond = Vtb_sys5__ConstPool__TABLE_h2a0441a0_0
        [__Vtableidx12];
    vlSelf->__PVT__a_val = ((0U != (0x1fU & (vlSelf->__PVT__ir 
                                             >> 0xfU))) 
                            & (IData)(vlSymsp->TOP.tb_sys5__DOT__dut__DOT__slot__BRA__11__KET____DOT__rqa_b));
    __VdfgTmp_hd9b60348__0 = ((2U == (7U & (vlSelf->__PVT__ir 
                                            >> 0xcU))) 
                              | (3U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))));
    vlSelf->__VdfgTmp_h18c46dac__0 = ((0x13U == (0x7fU 
                                                 & vlSelf->__PVT__ir)) 
                                      | (0x33U == (0x7fU 
                                                   & vlSelf->__PVT__ir)));
    __VdfgTmp_he83b8d53__0 = ((1U == (7U & (vlSelf->__PVT__ir 
                                            >> 0xcU))) 
                              | (5U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))));
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
    vlSelf->__PVT__X = vlSelf->__PVT__a_val;
    vlSelf->__PVT__is_cmp = ((0x63U == (0x7fU & vlSelf->__PVT__ir)) 
                             | ((IData)(vlSelf->__VdfgTmp_h18c46dac__0) 
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
    vlSelf->__PVT__inv = 0U;
    vlSelf->__PVT__is_shift = ((IData)(vlSelf->__PVT__sh_i) 
                               | ((0x33U == (0x7fU 
                                             & vlSelf->__PVT__ir)) 
                                  & (IData)(__VdfgTmp_he83b8d53__0)));
    __PVT__we = 0U;
    vlSelf->__PVT__fill = ((IData)(vlSelf->__PVT__is_shift) 
                           & (IData)(((0x40005000U 
                                       == (0x40007000U 
                                           & vlSelf->__PVT__ir)) 
                                      & (IData)(vlSelf->__PVT__sgn))));
    vlSelf->__PVT__is_sll = ((IData)(vlSelf->__PVT__is_shift) 
                             & (0x1000U == (0x7000U 
                                            & vlSelf->__PVT__ir)));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        vlSelf->__PVT__shx = vlSelf->__PVT__is_shift;
        if ((0x37U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__X = 0U;
        } else if ((0x17U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
        } else if ((0x6fU == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
        }
        if ((0x37U != (0x7fU & vlSelf->__PVT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->__PVT__ir))) {
                if ((0x6fU != (0x7fU & vlSelf->__PVT__ir))) {
                    if (((IData)((0x40000033U == (0x4000707fU 
                                                  & vlSelf->__PVT__ir))) 
                         | (IData)(vlSelf->__PVT__is_cmp))) {
                        vlSelf->__PVT__inv = 1U;
                    }
                }
            }
        }
        if (vlSelf->__PVT__is_shift) {
            __PVT__we = 1U;
        } else if (__VdfgExtracted_h62388771__0) {
            __PVT__we = 1U;
        } else if (((~ (IData)(vlSelf->__PVT__is_cmp)) 
                    & (IData)(vlSelf->__VdfgTmp_h18c46dac__0))) {
            __PVT__we = 1U;
        }
    } else {
        vlSelf->__PVT__shx = 0U;
        if ((4U == (IData)(vlSelf->__PVT__state))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
            if ((3U == (0x7fU & vlSelf->__PVT__ir))) {
                __PVT__we = 1U;
            } else if (vlSelf->__PVT__is_slt) {
                __PVT__we = 1U;
            } else if ((0x67U == (0x7fU & vlSelf->__PVT__ir))) {
                __PVT__we = 1U;
            }
        } else if ((5U == (IData)(vlSelf->__PVT__state))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
        }
    }
    vlSelf->rw_en = ((IData)(__PVT__we) & (0U != (0x1fU 
                                                  & (vlSelf->__PVT__ir 
                                                     >> 7U))));
    if (vlSelf->__PVT__is_sll) {
        vlSelf->__PVT__sll_dir = vlSelf->__PVT__is_shift;
        vlSelf->__PVT__ia = (0x1ffU & ((IData)(vlSelf->__PVT__k) 
                                       - (IData)(vlSelf->__PVT__shamt_w)));
        vlSelf->__VdfgTmp_h586768a0__0 = ((VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__k)) 
                                           - VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__shamt_w))) 
                                          - (IData)(1U));
    } else {
        vlSelf->__PVT__sll_dir = 0U;
        vlSelf->__PVT__ia = (0x1ffU & ((IData)(vlSelf->__PVT__k) 
                                       + (IData)(vlSelf->__PVT__shamt_w)));
        vlSelf->__VdfgTmp_h586768a0__0 = ((IData)(1U) 
                                          + (VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__k)) 
                                             + VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__shamt_w))));
    }
    vlSelf->d_wdata = ((~ ((IData)(vlSelf->__PVT__shx)
                            ? (0U == (0x1fU & (vlSelf->__PVT__ir 
                                               >> 0xfU)))
                            : (0U == (0x1fU & (vlSelf->__PVT__ir 
                                               >> 0x14U))))) 
                       & (IData)(vlSymsp->TOP.tb_sys5__DOT__dut__DOT__slot__BRA__11__KET____DOT__rqb_b));
    vlSelf->__PVT__exec_done = ((IData)(vlSelf->__PVT__sll_dir)
                                 ? (0U == (IData)(vlSelf->__PVT__k))
                                 : (0x1fU == (IData)(vlSelf->__PVT__k)));
    vlSelf->__PVT__va = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__ia))) 
                         & VL_GTES_III(32, 0x1fU, VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__ia))));
    vlSelf->__PVT__vb = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, 
                                                           (0x1ffU 
                                                            & vlSelf->__VdfgTmp_h586768a0__0))) 
                         & VL_GTES_III(32, 0x1fU, VL_EXTENDS_II(32,9, 
                                                                (0x1ffU 
                                                                 & vlSelf->__VdfgTmp_h586768a0__0))));
    vlSelf->__PVT__Yr = (1U & (((0x33U == (0x7fU & vlSelf->__PVT__ir)) 
                                | (0x63U == (0x7fU 
                                             & vlSelf->__PVT__ir)))
                                ? (IData)(vlSelf->d_wdata)
                                : vlSelf->__PVT__imm_sr));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if ((0x37U != (0x7fU & vlSelf->__PVT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->__PVT__ir))) {
                if ((0x6fU == (0x7fU & vlSelf->__PVT__ir))) {
                    vlSelf->__PVT__Yr = (1U & (4U >> (IData)(vlSelf->__PVT__k)));
                }
            }
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        vlSelf->__PVT__Yr = (1U & (4U >> (IData)(vlSelf->__PVT__k)));
    } else if ((5U == (IData)(vlSelf->__PVT__state))) {
        vlSelf->__PVT__Yr = (1U & (((0x6fU == (0x7fU 
                                               & vlSelf->__PVT__ir)) 
                                    | ((0x63U == (0x7fU 
                                                  & vlSelf->__PVT__ir)) 
                                       & (IData)(__PVT__cond)))
                                    ? vlSelf->__PVT__imm_sr
                                    : (4U >> (IData)(vlSelf->__PVT__k))));
    }
    vlSelf->__PVT__sum_c = (3U & ((IData)(vlSelf->__PVT__X) 
                                  + ((1U & ((IData)(vlSelf->__PVT__inv)
                                             ? (~ (IData)(vlSelf->__PVT__Yr))
                                             : (IData)(vlSelf->__PVT__Yr))) 
                                     + ((0U == (IData)(vlSelf->__PVT__k))
                                         ? (IData)(vlSelf->__PVT__inv)
                                         : (IData)(vlSelf->__PVT__cy)))));
    vlSelf->__PVT__addr_ins = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__addr, 1U) 
                               | VL_SHIFTL_III(32,32,32, 
                                               (1U 
                                                & (IData)(vlSelf->__PVT__sum_c)), 0x1fU));
    vlSelf->__PVT__pc_ins = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__pc, 1U) 
                             | VL_SHIFTL_III(32,32,32, 
                                             (1U & (IData)(vlSelf->__PVT__sum_c)), 0x1fU));
    vlSelf->__PVT__nz_n = (1U & (((0U != (IData)(vlSelf->__PVT__k)) 
                                  & (IData)(vlSelf->__PVT__nz)) 
                                 | (IData)(vlSelf->__PVT__sum_c)));
    vlSelf->__PVT__wd = (1U & (((IData)(vlSelf->__VdfgTmp_h18c46dac__0) 
                                & ((4U == (7U & (vlSelf->__PVT__ir 
                                                 >> 0xcU))) 
                                   | ((6U == (7U & 
                                              (vlSelf->__PVT__ir 
                                               >> 0xcU))) 
                                      | (7U == (7U 
                                                & (vlSelf->__PVT__ir 
                                                   >> 0xcU))))))
                                ? ((4U == (7U & (vlSelf->__PVT__ir 
                                                 >> 0xcU)))
                                    ? ((IData)(vlSelf->__PVT__X) 
                                       ^ (IData)(vlSelf->__PVT__Yr))
                                    : ((6U == (7U & 
                                               (vlSelf->__PVT__ir 
                                                >> 0xcU)))
                                        ? ((IData)(vlSelf->__PVT__X) 
                                           | (IData)(vlSelf->__PVT__Yr))
                                        : ((IData)(vlSelf->__PVT__X) 
                                           & (IData)(vlSelf->__PVT__Yr))))
                                : (IData)(vlSelf->__PVT__sum_c)));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if (vlSelf->__PVT__is_shift) {
            vlSelf->__PVT__wd = (1U & VL_SHIFTR_III(2,2,6, 
                                                    ((((IData)(vlSelf->__PVT__is_sll)
                                                        ? 
                                                       ((IData)(vlSelf->__PVT__va) 
                                                        & (IData)(vlSelf->__PVT__a_val))
                                                        : 
                                                       ((IData)(vlSelf->__PVT__vb)
                                                         ? (IData)(vlSelf->d_wdata)
                                                         : (IData)(vlSelf->__PVT__fill))) 
                                                      << 1U) 
                                                     | ((IData)(vlSelf->__PVT__is_sll)
                                                         ? 
                                                        ((IData)(vlSelf->__PVT__vb) 
                                                         & (IData)(vlSelf->d_wdata))
                                                         : 
                                                        ((IData)(vlSelf->__PVT__va)
                                                          ? (IData)(vlSelf->__PVT__a_val)
                                                          : (IData)(vlSelf->__PVT__fill)))), 
                                                    ((IData)(vlSelf->__PVT__is_sll)
                                                      ? 1U
                                                      : 0U)));
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        if ((3U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__wd = vlSymsp->TOP.tb_sys5__DOT__dut__DOT__slot__BRA__11__KET____DOT__dq_b;
        } else if (vlSelf->__PVT__is_slt) {
            vlSelf->__PVT__wd = ((0U == (IData)(vlSelf->__PVT__k)) 
                                 & ((2U == (7U & (vlSelf->__PVT__ir 
                                                  >> 0xcU)))
                                     ? (IData)(vlSelf->__PVT__f_lt)
                                     : (IData)(vlSelf->__PVT__f_ltu)));
        } else if ((0x67U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__wd = (1U & (IData)(vlSelf->__PVT__sum_c));
        }
    }
}

VL_ATTR_COLD void Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__12__KET____DOT__core__0(Vtb_sys5_uc_core_v2s__W1* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_sys5__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+          Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__12__KET____DOT__core__0\n"); );
    // Init
    CData/*0:0*/ __PVT__cond;
    __PVT__cond = 0;
    CData/*0:0*/ __PVT__we;
    __PVT__we = 0;
    CData/*0:0*/ __VdfgExtracted_h62388771__0;
    __VdfgExtracted_h62388771__0 = 0;
    CData/*0:0*/ __VdfgTmp_h2cd83c5b__0;
    __VdfgTmp_h2cd83c5b__0 = 0;
    CData/*0:0*/ __VdfgTmp_he83b8d53__0;
    __VdfgTmp_he83b8d53__0 = 0;
    CData/*0:0*/ __VdfgTmp_hd9b60348__0;
    __VdfgTmp_hd9b60348__0 = 0;
    CData/*5:0*/ __Vtableidx13;
    __Vtableidx13 = 0;
    // Body
    vlSelf->__PVT__rs2 = (0x1fU & (vlSelf->__PVT__ir 
                                   >> 0x14U));
    vlSelf->__PVT__is_sys = (0x73U == (0x7fU & vlSelf->__PVT__ir));
    vlSelf->__PVT__last_up = (0x1fU == (IData)(vlSelf->__PVT__k));
    vlSelf->__PVT__pc_rot = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__pc, 1U) 
                             | VL_SHIFTL_III(32,32,32, vlSelf->__PVT__pc, 0x1fU));
    vlSelf->__PVT__imm_rot = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__imm_sr, 1U) 
                              | VL_SHIFTL_III(32,32,32, vlSelf->__PVT__imm_sr, 0x1fU));
    vlSelf->__PVT__opc = (0x7fU & vlSelf->__PVT__ir);
    vlSelf->d_addr = (((QData)((IData)((vlSelf->__PVT__addr 
                                        >> 2U))) << 5U) 
                      | (QData)((IData)(vlSelf->__PVT__k)));
    vlSelf->rw_addr = ((0x3e0U & (vlSelf->__PVT__ir 
                                  >> 2U)) | (IData)(vlSelf->__PVT__k));
    __VdfgTmp_h2cd83c5b__0 = ((0x37U == (0x7fU & vlSelf->__PVT__ir)) 
                              | (0x17U == (0x7fU & vlSelf->__PVT__ir)));
    __Vtableidx13 = (((IData)(vlSelf->__PVT__f_eq) 
                      << 5U) | (((IData)(vlSelf->__PVT__f_lt) 
                                 << 4U) | (((IData)(vlSelf->__PVT__f_ltu) 
                                            << 3U) 
                                           | (7U & 
                                              (vlSelf->__PVT__ir 
                                               >> 0xcU)))));
    __PVT__cond = Vtb_sys5__ConstPool__TABLE_h2a0441a0_0
        [__Vtableidx13];
    vlSelf->__PVT__a_val = ((0U != (0x1fU & (vlSelf->__PVT__ir 
                                             >> 0xfU))) 
                            & (IData)(vlSymsp->TOP.tb_sys5__DOT__dut__DOT__slot__BRA__12__KET____DOT__rqa_b));
    __VdfgTmp_hd9b60348__0 = ((2U == (7U & (vlSelf->__PVT__ir 
                                            >> 0xcU))) 
                              | (3U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))));
    vlSelf->__VdfgTmp_h18c46dac__0 = ((0x13U == (0x7fU 
                                                 & vlSelf->__PVT__ir)) 
                                      | (0x33U == (0x7fU 
                                                   & vlSelf->__PVT__ir)));
    __VdfgTmp_he83b8d53__0 = ((1U == (7U & (vlSelf->__PVT__ir 
                                            >> 0xcU))) 
                              | (5U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))));
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
    vlSelf->__PVT__X = vlSelf->__PVT__a_val;
    vlSelf->__PVT__is_cmp = ((0x63U == (0x7fU & vlSelf->__PVT__ir)) 
                             | ((IData)(vlSelf->__VdfgTmp_h18c46dac__0) 
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
    vlSelf->__PVT__inv = 0U;
    vlSelf->__PVT__is_shift = ((IData)(vlSelf->__PVT__sh_i) 
                               | ((0x33U == (0x7fU 
                                             & vlSelf->__PVT__ir)) 
                                  & (IData)(__VdfgTmp_he83b8d53__0)));
    __PVT__we = 0U;
    vlSelf->__PVT__fill = ((IData)(vlSelf->__PVT__is_shift) 
                           & (IData)(((0x40005000U 
                                       == (0x40007000U 
                                           & vlSelf->__PVT__ir)) 
                                      & (IData)(vlSelf->__PVT__sgn))));
    vlSelf->__PVT__is_sll = ((IData)(vlSelf->__PVT__is_shift) 
                             & (0x1000U == (0x7000U 
                                            & vlSelf->__PVT__ir)));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        vlSelf->__PVT__shx = vlSelf->__PVT__is_shift;
        if ((0x37U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__X = 0U;
        } else if ((0x17U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
        } else if ((0x6fU == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
        }
        if ((0x37U != (0x7fU & vlSelf->__PVT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->__PVT__ir))) {
                if ((0x6fU != (0x7fU & vlSelf->__PVT__ir))) {
                    if (((IData)((0x40000033U == (0x4000707fU 
                                                  & vlSelf->__PVT__ir))) 
                         | (IData)(vlSelf->__PVT__is_cmp))) {
                        vlSelf->__PVT__inv = 1U;
                    }
                }
            }
        }
        if (vlSelf->__PVT__is_shift) {
            __PVT__we = 1U;
        } else if (__VdfgExtracted_h62388771__0) {
            __PVT__we = 1U;
        } else if (((~ (IData)(vlSelf->__PVT__is_cmp)) 
                    & (IData)(vlSelf->__VdfgTmp_h18c46dac__0))) {
            __PVT__we = 1U;
        }
    } else {
        vlSelf->__PVT__shx = 0U;
        if ((4U == (IData)(vlSelf->__PVT__state))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
            if ((3U == (0x7fU & vlSelf->__PVT__ir))) {
                __PVT__we = 1U;
            } else if (vlSelf->__PVT__is_slt) {
                __PVT__we = 1U;
            } else if ((0x67U == (0x7fU & vlSelf->__PVT__ir))) {
                __PVT__we = 1U;
            }
        } else if ((5U == (IData)(vlSelf->__PVT__state))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
        }
    }
    vlSelf->rw_en = ((IData)(__PVT__we) & (0U != (0x1fU 
                                                  & (vlSelf->__PVT__ir 
                                                     >> 7U))));
    if (vlSelf->__PVT__is_sll) {
        vlSelf->__PVT__sll_dir = vlSelf->__PVT__is_shift;
        vlSelf->__PVT__ia = (0x1ffU & ((IData)(vlSelf->__PVT__k) 
                                       - (IData)(vlSelf->__PVT__shamt_w)));
        vlSelf->__VdfgTmp_h586768a0__0 = ((VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__k)) 
                                           - VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__shamt_w))) 
                                          - (IData)(1U));
    } else {
        vlSelf->__PVT__sll_dir = 0U;
        vlSelf->__PVT__ia = (0x1ffU & ((IData)(vlSelf->__PVT__k) 
                                       + (IData)(vlSelf->__PVT__shamt_w)));
        vlSelf->__VdfgTmp_h586768a0__0 = ((IData)(1U) 
                                          + (VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__k)) 
                                             + VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__shamt_w))));
    }
    vlSelf->d_wdata = ((~ ((IData)(vlSelf->__PVT__shx)
                            ? (0U == (0x1fU & (vlSelf->__PVT__ir 
                                               >> 0xfU)))
                            : (0U == (0x1fU & (vlSelf->__PVT__ir 
                                               >> 0x14U))))) 
                       & (IData)(vlSymsp->TOP.tb_sys5__DOT__dut__DOT__slot__BRA__12__KET____DOT__rqb_b));
    vlSelf->__PVT__exec_done = ((IData)(vlSelf->__PVT__sll_dir)
                                 ? (0U == (IData)(vlSelf->__PVT__k))
                                 : (0x1fU == (IData)(vlSelf->__PVT__k)));
    vlSelf->__PVT__va = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__ia))) 
                         & VL_GTES_III(32, 0x1fU, VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__ia))));
    vlSelf->__PVT__vb = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, 
                                                           (0x1ffU 
                                                            & vlSelf->__VdfgTmp_h586768a0__0))) 
                         & VL_GTES_III(32, 0x1fU, VL_EXTENDS_II(32,9, 
                                                                (0x1ffU 
                                                                 & vlSelf->__VdfgTmp_h586768a0__0))));
    vlSelf->__PVT__Yr = (1U & (((0x33U == (0x7fU & vlSelf->__PVT__ir)) 
                                | (0x63U == (0x7fU 
                                             & vlSelf->__PVT__ir)))
                                ? (IData)(vlSelf->d_wdata)
                                : vlSelf->__PVT__imm_sr));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if ((0x37U != (0x7fU & vlSelf->__PVT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->__PVT__ir))) {
                if ((0x6fU == (0x7fU & vlSelf->__PVT__ir))) {
                    vlSelf->__PVT__Yr = (1U & (4U >> (IData)(vlSelf->__PVT__k)));
                }
            }
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        vlSelf->__PVT__Yr = (1U & (4U >> (IData)(vlSelf->__PVT__k)));
    } else if ((5U == (IData)(vlSelf->__PVT__state))) {
        vlSelf->__PVT__Yr = (1U & (((0x6fU == (0x7fU 
                                               & vlSelf->__PVT__ir)) 
                                    | ((0x63U == (0x7fU 
                                                  & vlSelf->__PVT__ir)) 
                                       & (IData)(__PVT__cond)))
                                    ? vlSelf->__PVT__imm_sr
                                    : (4U >> (IData)(vlSelf->__PVT__k))));
    }
    vlSelf->__PVT__sum_c = (3U & ((IData)(vlSelf->__PVT__X) 
                                  + ((1U & ((IData)(vlSelf->__PVT__inv)
                                             ? (~ (IData)(vlSelf->__PVT__Yr))
                                             : (IData)(vlSelf->__PVT__Yr))) 
                                     + ((0U == (IData)(vlSelf->__PVT__k))
                                         ? (IData)(vlSelf->__PVT__inv)
                                         : (IData)(vlSelf->__PVT__cy)))));
    vlSelf->__PVT__addr_ins = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__addr, 1U) 
                               | VL_SHIFTL_III(32,32,32, 
                                               (1U 
                                                & (IData)(vlSelf->__PVT__sum_c)), 0x1fU));
    vlSelf->__PVT__pc_ins = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__pc, 1U) 
                             | VL_SHIFTL_III(32,32,32, 
                                             (1U & (IData)(vlSelf->__PVT__sum_c)), 0x1fU));
    vlSelf->__PVT__nz_n = (1U & (((0U != (IData)(vlSelf->__PVT__k)) 
                                  & (IData)(vlSelf->__PVT__nz)) 
                                 | (IData)(vlSelf->__PVT__sum_c)));
    vlSelf->__PVT__wd = (1U & (((IData)(vlSelf->__VdfgTmp_h18c46dac__0) 
                                & ((4U == (7U & (vlSelf->__PVT__ir 
                                                 >> 0xcU))) 
                                   | ((6U == (7U & 
                                              (vlSelf->__PVT__ir 
                                               >> 0xcU))) 
                                      | (7U == (7U 
                                                & (vlSelf->__PVT__ir 
                                                   >> 0xcU))))))
                                ? ((4U == (7U & (vlSelf->__PVT__ir 
                                                 >> 0xcU)))
                                    ? ((IData)(vlSelf->__PVT__X) 
                                       ^ (IData)(vlSelf->__PVT__Yr))
                                    : ((6U == (7U & 
                                               (vlSelf->__PVT__ir 
                                                >> 0xcU)))
                                        ? ((IData)(vlSelf->__PVT__X) 
                                           | (IData)(vlSelf->__PVT__Yr))
                                        : ((IData)(vlSelf->__PVT__X) 
                                           & (IData)(vlSelf->__PVT__Yr))))
                                : (IData)(vlSelf->__PVT__sum_c)));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if (vlSelf->__PVT__is_shift) {
            vlSelf->__PVT__wd = (1U & VL_SHIFTR_III(2,2,6, 
                                                    ((((IData)(vlSelf->__PVT__is_sll)
                                                        ? 
                                                       ((IData)(vlSelf->__PVT__va) 
                                                        & (IData)(vlSelf->__PVT__a_val))
                                                        : 
                                                       ((IData)(vlSelf->__PVT__vb)
                                                         ? (IData)(vlSelf->d_wdata)
                                                         : (IData)(vlSelf->__PVT__fill))) 
                                                      << 1U) 
                                                     | ((IData)(vlSelf->__PVT__is_sll)
                                                         ? 
                                                        ((IData)(vlSelf->__PVT__vb) 
                                                         & (IData)(vlSelf->d_wdata))
                                                         : 
                                                        ((IData)(vlSelf->__PVT__va)
                                                          ? (IData)(vlSelf->__PVT__a_val)
                                                          : (IData)(vlSelf->__PVT__fill)))), 
                                                    ((IData)(vlSelf->__PVT__is_sll)
                                                      ? 1U
                                                      : 0U)));
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        if ((3U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__wd = vlSymsp->TOP.tb_sys5__DOT__dut__DOT__slot__BRA__12__KET____DOT__dq_b;
        } else if (vlSelf->__PVT__is_slt) {
            vlSelf->__PVT__wd = ((0U == (IData)(vlSelf->__PVT__k)) 
                                 & ((2U == (7U & (vlSelf->__PVT__ir 
                                                  >> 0xcU)))
                                     ? (IData)(vlSelf->__PVT__f_lt)
                                     : (IData)(vlSelf->__PVT__f_ltu)));
        } else if ((0x67U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__wd = (1U & (IData)(vlSelf->__PVT__sum_c));
        }
    }
}

VL_ATTR_COLD void Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__13__KET____DOT__core__0(Vtb_sys5_uc_core_v2s__W1* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_sys5__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+          Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__13__KET____DOT__core__0\n"); );
    // Init
    CData/*0:0*/ __PVT__cond;
    __PVT__cond = 0;
    CData/*0:0*/ __PVT__we;
    __PVT__we = 0;
    CData/*0:0*/ __VdfgExtracted_h62388771__0;
    __VdfgExtracted_h62388771__0 = 0;
    CData/*0:0*/ __VdfgTmp_h2cd83c5b__0;
    __VdfgTmp_h2cd83c5b__0 = 0;
    CData/*0:0*/ __VdfgTmp_he83b8d53__0;
    __VdfgTmp_he83b8d53__0 = 0;
    CData/*0:0*/ __VdfgTmp_hd9b60348__0;
    __VdfgTmp_hd9b60348__0 = 0;
    CData/*5:0*/ __Vtableidx14;
    __Vtableidx14 = 0;
    // Body
    vlSelf->__PVT__rs2 = (0x1fU & (vlSelf->__PVT__ir 
                                   >> 0x14U));
    vlSelf->__PVT__is_sys = (0x73U == (0x7fU & vlSelf->__PVT__ir));
    vlSelf->__PVT__last_up = (0x1fU == (IData)(vlSelf->__PVT__k));
    vlSelf->__PVT__pc_rot = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__pc, 1U) 
                             | VL_SHIFTL_III(32,32,32, vlSelf->__PVT__pc, 0x1fU));
    vlSelf->__PVT__imm_rot = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__imm_sr, 1U) 
                              | VL_SHIFTL_III(32,32,32, vlSelf->__PVT__imm_sr, 0x1fU));
    vlSelf->__PVT__opc = (0x7fU & vlSelf->__PVT__ir);
    vlSelf->d_addr = (((QData)((IData)((vlSelf->__PVT__addr 
                                        >> 2U))) << 5U) 
                      | (QData)((IData)(vlSelf->__PVT__k)));
    vlSelf->rw_addr = ((0x3e0U & (vlSelf->__PVT__ir 
                                  >> 2U)) | (IData)(vlSelf->__PVT__k));
    __VdfgTmp_h2cd83c5b__0 = ((0x37U == (0x7fU & vlSelf->__PVT__ir)) 
                              | (0x17U == (0x7fU & vlSelf->__PVT__ir)));
    __Vtableidx14 = (((IData)(vlSelf->__PVT__f_eq) 
                      << 5U) | (((IData)(vlSelf->__PVT__f_lt) 
                                 << 4U) | (((IData)(vlSelf->__PVT__f_ltu) 
                                            << 3U) 
                                           | (7U & 
                                              (vlSelf->__PVT__ir 
                                               >> 0xcU)))));
    __PVT__cond = Vtb_sys5__ConstPool__TABLE_h2a0441a0_0
        [__Vtableidx14];
    vlSelf->__PVT__a_val = ((0U != (0x1fU & (vlSelf->__PVT__ir 
                                             >> 0xfU))) 
                            & (IData)(vlSymsp->TOP.tb_sys5__DOT__dut__DOT__slot__BRA__13__KET____DOT__rqa_b));
    __VdfgTmp_hd9b60348__0 = ((2U == (7U & (vlSelf->__PVT__ir 
                                            >> 0xcU))) 
                              | (3U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))));
    vlSelf->__VdfgTmp_h18c46dac__0 = ((0x13U == (0x7fU 
                                                 & vlSelf->__PVT__ir)) 
                                      | (0x33U == (0x7fU 
                                                   & vlSelf->__PVT__ir)));
    __VdfgTmp_he83b8d53__0 = ((1U == (7U & (vlSelf->__PVT__ir 
                                            >> 0xcU))) 
                              | (5U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))));
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
    vlSelf->__PVT__X = vlSelf->__PVT__a_val;
    vlSelf->__PVT__is_cmp = ((0x63U == (0x7fU & vlSelf->__PVT__ir)) 
                             | ((IData)(vlSelf->__VdfgTmp_h18c46dac__0) 
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
    vlSelf->__PVT__inv = 0U;
    vlSelf->__PVT__is_shift = ((IData)(vlSelf->__PVT__sh_i) 
                               | ((0x33U == (0x7fU 
                                             & vlSelf->__PVT__ir)) 
                                  & (IData)(__VdfgTmp_he83b8d53__0)));
    __PVT__we = 0U;
    vlSelf->__PVT__fill = ((IData)(vlSelf->__PVT__is_shift) 
                           & (IData)(((0x40005000U 
                                       == (0x40007000U 
                                           & vlSelf->__PVT__ir)) 
                                      & (IData)(vlSelf->__PVT__sgn))));
    vlSelf->__PVT__is_sll = ((IData)(vlSelf->__PVT__is_shift) 
                             & (0x1000U == (0x7000U 
                                            & vlSelf->__PVT__ir)));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        vlSelf->__PVT__shx = vlSelf->__PVT__is_shift;
        if ((0x37U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__X = 0U;
        } else if ((0x17U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
        } else if ((0x6fU == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
        }
        if ((0x37U != (0x7fU & vlSelf->__PVT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->__PVT__ir))) {
                if ((0x6fU != (0x7fU & vlSelf->__PVT__ir))) {
                    if (((IData)((0x40000033U == (0x4000707fU 
                                                  & vlSelf->__PVT__ir))) 
                         | (IData)(vlSelf->__PVT__is_cmp))) {
                        vlSelf->__PVT__inv = 1U;
                    }
                }
            }
        }
        if (vlSelf->__PVT__is_shift) {
            __PVT__we = 1U;
        } else if (__VdfgExtracted_h62388771__0) {
            __PVT__we = 1U;
        } else if (((~ (IData)(vlSelf->__PVT__is_cmp)) 
                    & (IData)(vlSelf->__VdfgTmp_h18c46dac__0))) {
            __PVT__we = 1U;
        }
    } else {
        vlSelf->__PVT__shx = 0U;
        if ((4U == (IData)(vlSelf->__PVT__state))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
            if ((3U == (0x7fU & vlSelf->__PVT__ir))) {
                __PVT__we = 1U;
            } else if (vlSelf->__PVT__is_slt) {
                __PVT__we = 1U;
            } else if ((0x67U == (0x7fU & vlSelf->__PVT__ir))) {
                __PVT__we = 1U;
            }
        } else if ((5U == (IData)(vlSelf->__PVT__state))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
        }
    }
    vlSelf->rw_en = ((IData)(__PVT__we) & (0U != (0x1fU 
                                                  & (vlSelf->__PVT__ir 
                                                     >> 7U))));
    if (vlSelf->__PVT__is_sll) {
        vlSelf->__PVT__sll_dir = vlSelf->__PVT__is_shift;
        vlSelf->__PVT__ia = (0x1ffU & ((IData)(vlSelf->__PVT__k) 
                                       - (IData)(vlSelf->__PVT__shamt_w)));
        vlSelf->__VdfgTmp_h586768a0__0 = ((VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__k)) 
                                           - VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__shamt_w))) 
                                          - (IData)(1U));
    } else {
        vlSelf->__PVT__sll_dir = 0U;
        vlSelf->__PVT__ia = (0x1ffU & ((IData)(vlSelf->__PVT__k) 
                                       + (IData)(vlSelf->__PVT__shamt_w)));
        vlSelf->__VdfgTmp_h586768a0__0 = ((IData)(1U) 
                                          + (VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__k)) 
                                             + VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__shamt_w))));
    }
    vlSelf->d_wdata = ((~ ((IData)(vlSelf->__PVT__shx)
                            ? (0U == (0x1fU & (vlSelf->__PVT__ir 
                                               >> 0xfU)))
                            : (0U == (0x1fU & (vlSelf->__PVT__ir 
                                               >> 0x14U))))) 
                       & (IData)(vlSymsp->TOP.tb_sys5__DOT__dut__DOT__slot__BRA__13__KET____DOT__rqb_b));
    vlSelf->__PVT__exec_done = ((IData)(vlSelf->__PVT__sll_dir)
                                 ? (0U == (IData)(vlSelf->__PVT__k))
                                 : (0x1fU == (IData)(vlSelf->__PVT__k)));
    vlSelf->__PVT__va = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__ia))) 
                         & VL_GTES_III(32, 0x1fU, VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__ia))));
    vlSelf->__PVT__vb = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, 
                                                           (0x1ffU 
                                                            & vlSelf->__VdfgTmp_h586768a0__0))) 
                         & VL_GTES_III(32, 0x1fU, VL_EXTENDS_II(32,9, 
                                                                (0x1ffU 
                                                                 & vlSelf->__VdfgTmp_h586768a0__0))));
    vlSelf->__PVT__Yr = (1U & (((0x33U == (0x7fU & vlSelf->__PVT__ir)) 
                                | (0x63U == (0x7fU 
                                             & vlSelf->__PVT__ir)))
                                ? (IData)(vlSelf->d_wdata)
                                : vlSelf->__PVT__imm_sr));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if ((0x37U != (0x7fU & vlSelf->__PVT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->__PVT__ir))) {
                if ((0x6fU == (0x7fU & vlSelf->__PVT__ir))) {
                    vlSelf->__PVT__Yr = (1U & (4U >> (IData)(vlSelf->__PVT__k)));
                }
            }
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        vlSelf->__PVT__Yr = (1U & (4U >> (IData)(vlSelf->__PVT__k)));
    } else if ((5U == (IData)(vlSelf->__PVT__state))) {
        vlSelf->__PVT__Yr = (1U & (((0x6fU == (0x7fU 
                                               & vlSelf->__PVT__ir)) 
                                    | ((0x63U == (0x7fU 
                                                  & vlSelf->__PVT__ir)) 
                                       & (IData)(__PVT__cond)))
                                    ? vlSelf->__PVT__imm_sr
                                    : (4U >> (IData)(vlSelf->__PVT__k))));
    }
    vlSelf->__PVT__sum_c = (3U & ((IData)(vlSelf->__PVT__X) 
                                  + ((1U & ((IData)(vlSelf->__PVT__inv)
                                             ? (~ (IData)(vlSelf->__PVT__Yr))
                                             : (IData)(vlSelf->__PVT__Yr))) 
                                     + ((0U == (IData)(vlSelf->__PVT__k))
                                         ? (IData)(vlSelf->__PVT__inv)
                                         : (IData)(vlSelf->__PVT__cy)))));
    vlSelf->__PVT__addr_ins = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__addr, 1U) 
                               | VL_SHIFTL_III(32,32,32, 
                                               (1U 
                                                & (IData)(vlSelf->__PVT__sum_c)), 0x1fU));
    vlSelf->__PVT__pc_ins = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__pc, 1U) 
                             | VL_SHIFTL_III(32,32,32, 
                                             (1U & (IData)(vlSelf->__PVT__sum_c)), 0x1fU));
    vlSelf->__PVT__nz_n = (1U & (((0U != (IData)(vlSelf->__PVT__k)) 
                                  & (IData)(vlSelf->__PVT__nz)) 
                                 | (IData)(vlSelf->__PVT__sum_c)));
    vlSelf->__PVT__wd = (1U & (((IData)(vlSelf->__VdfgTmp_h18c46dac__0) 
                                & ((4U == (7U & (vlSelf->__PVT__ir 
                                                 >> 0xcU))) 
                                   | ((6U == (7U & 
                                              (vlSelf->__PVT__ir 
                                               >> 0xcU))) 
                                      | (7U == (7U 
                                                & (vlSelf->__PVT__ir 
                                                   >> 0xcU))))))
                                ? ((4U == (7U & (vlSelf->__PVT__ir 
                                                 >> 0xcU)))
                                    ? ((IData)(vlSelf->__PVT__X) 
                                       ^ (IData)(vlSelf->__PVT__Yr))
                                    : ((6U == (7U & 
                                               (vlSelf->__PVT__ir 
                                                >> 0xcU)))
                                        ? ((IData)(vlSelf->__PVT__X) 
                                           | (IData)(vlSelf->__PVT__Yr))
                                        : ((IData)(vlSelf->__PVT__X) 
                                           & (IData)(vlSelf->__PVT__Yr))))
                                : (IData)(vlSelf->__PVT__sum_c)));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if (vlSelf->__PVT__is_shift) {
            vlSelf->__PVT__wd = (1U & VL_SHIFTR_III(2,2,6, 
                                                    ((((IData)(vlSelf->__PVT__is_sll)
                                                        ? 
                                                       ((IData)(vlSelf->__PVT__va) 
                                                        & (IData)(vlSelf->__PVT__a_val))
                                                        : 
                                                       ((IData)(vlSelf->__PVT__vb)
                                                         ? (IData)(vlSelf->d_wdata)
                                                         : (IData)(vlSelf->__PVT__fill))) 
                                                      << 1U) 
                                                     | ((IData)(vlSelf->__PVT__is_sll)
                                                         ? 
                                                        ((IData)(vlSelf->__PVT__vb) 
                                                         & (IData)(vlSelf->d_wdata))
                                                         : 
                                                        ((IData)(vlSelf->__PVT__va)
                                                          ? (IData)(vlSelf->__PVT__a_val)
                                                          : (IData)(vlSelf->__PVT__fill)))), 
                                                    ((IData)(vlSelf->__PVT__is_sll)
                                                      ? 1U
                                                      : 0U)));
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        if ((3U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__wd = vlSymsp->TOP.tb_sys5__DOT__dut__DOT__slot__BRA__13__KET____DOT__dq_b;
        } else if (vlSelf->__PVT__is_slt) {
            vlSelf->__PVT__wd = ((0U == (IData)(vlSelf->__PVT__k)) 
                                 & ((2U == (7U & (vlSelf->__PVT__ir 
                                                  >> 0xcU)))
                                     ? (IData)(vlSelf->__PVT__f_lt)
                                     : (IData)(vlSelf->__PVT__f_ltu)));
        } else if ((0x67U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__wd = (1U & (IData)(vlSelf->__PVT__sum_c));
        }
    }
}

VL_ATTR_COLD void Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__14__KET____DOT__core__0(Vtb_sys5_uc_core_v2s__W1* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_sys5__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+          Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__14__KET____DOT__core__0\n"); );
    // Init
    CData/*0:0*/ __PVT__cond;
    __PVT__cond = 0;
    CData/*0:0*/ __PVT__we;
    __PVT__we = 0;
    CData/*0:0*/ __VdfgExtracted_h62388771__0;
    __VdfgExtracted_h62388771__0 = 0;
    CData/*0:0*/ __VdfgTmp_h2cd83c5b__0;
    __VdfgTmp_h2cd83c5b__0 = 0;
    CData/*0:0*/ __VdfgTmp_he83b8d53__0;
    __VdfgTmp_he83b8d53__0 = 0;
    CData/*0:0*/ __VdfgTmp_hd9b60348__0;
    __VdfgTmp_hd9b60348__0 = 0;
    CData/*5:0*/ __Vtableidx15;
    __Vtableidx15 = 0;
    // Body
    vlSelf->__PVT__rs2 = (0x1fU & (vlSelf->__PVT__ir 
                                   >> 0x14U));
    vlSelf->__PVT__is_sys = (0x73U == (0x7fU & vlSelf->__PVT__ir));
    vlSelf->__PVT__last_up = (0x1fU == (IData)(vlSelf->__PVT__k));
    vlSelf->__PVT__pc_rot = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__pc, 1U) 
                             | VL_SHIFTL_III(32,32,32, vlSelf->__PVT__pc, 0x1fU));
    vlSelf->__PVT__imm_rot = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__imm_sr, 1U) 
                              | VL_SHIFTL_III(32,32,32, vlSelf->__PVT__imm_sr, 0x1fU));
    vlSelf->__PVT__opc = (0x7fU & vlSelf->__PVT__ir);
    vlSelf->d_addr = (((QData)((IData)((vlSelf->__PVT__addr 
                                        >> 2U))) << 5U) 
                      | (QData)((IData)(vlSelf->__PVT__k)));
    vlSelf->rw_addr = ((0x3e0U & (vlSelf->__PVT__ir 
                                  >> 2U)) | (IData)(vlSelf->__PVT__k));
    __VdfgTmp_h2cd83c5b__0 = ((0x37U == (0x7fU & vlSelf->__PVT__ir)) 
                              | (0x17U == (0x7fU & vlSelf->__PVT__ir)));
    __Vtableidx15 = (((IData)(vlSelf->__PVT__f_eq) 
                      << 5U) | (((IData)(vlSelf->__PVT__f_lt) 
                                 << 4U) | (((IData)(vlSelf->__PVT__f_ltu) 
                                            << 3U) 
                                           | (7U & 
                                              (vlSelf->__PVT__ir 
                                               >> 0xcU)))));
    __PVT__cond = Vtb_sys5__ConstPool__TABLE_h2a0441a0_0
        [__Vtableidx15];
    vlSelf->__PVT__a_val = ((0U != (0x1fU & (vlSelf->__PVT__ir 
                                             >> 0xfU))) 
                            & (IData)(vlSymsp->TOP.tb_sys5__DOT__dut__DOT__slot__BRA__14__KET____DOT__rqa_b));
    __VdfgTmp_hd9b60348__0 = ((2U == (7U & (vlSelf->__PVT__ir 
                                            >> 0xcU))) 
                              | (3U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))));
    vlSelf->__VdfgTmp_h18c46dac__0 = ((0x13U == (0x7fU 
                                                 & vlSelf->__PVT__ir)) 
                                      | (0x33U == (0x7fU 
                                                   & vlSelf->__PVT__ir)));
    __VdfgTmp_he83b8d53__0 = ((1U == (7U & (vlSelf->__PVT__ir 
                                            >> 0xcU))) 
                              | (5U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))));
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
    vlSelf->__PVT__X = vlSelf->__PVT__a_val;
    vlSelf->__PVT__is_cmp = ((0x63U == (0x7fU & vlSelf->__PVT__ir)) 
                             | ((IData)(vlSelf->__VdfgTmp_h18c46dac__0) 
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
    vlSelf->__PVT__inv = 0U;
    vlSelf->__PVT__is_shift = ((IData)(vlSelf->__PVT__sh_i) 
                               | ((0x33U == (0x7fU 
                                             & vlSelf->__PVT__ir)) 
                                  & (IData)(__VdfgTmp_he83b8d53__0)));
    __PVT__we = 0U;
    vlSelf->__PVT__fill = ((IData)(vlSelf->__PVT__is_shift) 
                           & (IData)(((0x40005000U 
                                       == (0x40007000U 
                                           & vlSelf->__PVT__ir)) 
                                      & (IData)(vlSelf->__PVT__sgn))));
    vlSelf->__PVT__is_sll = ((IData)(vlSelf->__PVT__is_shift) 
                             & (0x1000U == (0x7000U 
                                            & vlSelf->__PVT__ir)));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        vlSelf->__PVT__shx = vlSelf->__PVT__is_shift;
        if ((0x37U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__X = 0U;
        } else if ((0x17U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
        } else if ((0x6fU == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
        }
        if ((0x37U != (0x7fU & vlSelf->__PVT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->__PVT__ir))) {
                if ((0x6fU != (0x7fU & vlSelf->__PVT__ir))) {
                    if (((IData)((0x40000033U == (0x4000707fU 
                                                  & vlSelf->__PVT__ir))) 
                         | (IData)(vlSelf->__PVT__is_cmp))) {
                        vlSelf->__PVT__inv = 1U;
                    }
                }
            }
        }
        if (vlSelf->__PVT__is_shift) {
            __PVT__we = 1U;
        } else if (__VdfgExtracted_h62388771__0) {
            __PVT__we = 1U;
        } else if (((~ (IData)(vlSelf->__PVT__is_cmp)) 
                    & (IData)(vlSelf->__VdfgTmp_h18c46dac__0))) {
            __PVT__we = 1U;
        }
    } else {
        vlSelf->__PVT__shx = 0U;
        if ((4U == (IData)(vlSelf->__PVT__state))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
            if ((3U == (0x7fU & vlSelf->__PVT__ir))) {
                __PVT__we = 1U;
            } else if (vlSelf->__PVT__is_slt) {
                __PVT__we = 1U;
            } else if ((0x67U == (0x7fU & vlSelf->__PVT__ir))) {
                __PVT__we = 1U;
            }
        } else if ((5U == (IData)(vlSelf->__PVT__state))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
        }
    }
    vlSelf->rw_en = ((IData)(__PVT__we) & (0U != (0x1fU 
                                                  & (vlSelf->__PVT__ir 
                                                     >> 7U))));
    if (vlSelf->__PVT__is_sll) {
        vlSelf->__PVT__sll_dir = vlSelf->__PVT__is_shift;
        vlSelf->__PVT__ia = (0x1ffU & ((IData)(vlSelf->__PVT__k) 
                                       - (IData)(vlSelf->__PVT__shamt_w)));
        vlSelf->__VdfgTmp_h586768a0__0 = ((VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__k)) 
                                           - VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__shamt_w))) 
                                          - (IData)(1U));
    } else {
        vlSelf->__PVT__sll_dir = 0U;
        vlSelf->__PVT__ia = (0x1ffU & ((IData)(vlSelf->__PVT__k) 
                                       + (IData)(vlSelf->__PVT__shamt_w)));
        vlSelf->__VdfgTmp_h586768a0__0 = ((IData)(1U) 
                                          + (VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__k)) 
                                             + VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__shamt_w))));
    }
    vlSelf->d_wdata = ((~ ((IData)(vlSelf->__PVT__shx)
                            ? (0U == (0x1fU & (vlSelf->__PVT__ir 
                                               >> 0xfU)))
                            : (0U == (0x1fU & (vlSelf->__PVT__ir 
                                               >> 0x14U))))) 
                       & (IData)(vlSymsp->TOP.tb_sys5__DOT__dut__DOT__slot__BRA__14__KET____DOT__rqb_b));
    vlSelf->__PVT__exec_done = ((IData)(vlSelf->__PVT__sll_dir)
                                 ? (0U == (IData)(vlSelf->__PVT__k))
                                 : (0x1fU == (IData)(vlSelf->__PVT__k)));
    vlSelf->__PVT__va = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__ia))) 
                         & VL_GTES_III(32, 0x1fU, VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__ia))));
    vlSelf->__PVT__vb = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, 
                                                           (0x1ffU 
                                                            & vlSelf->__VdfgTmp_h586768a0__0))) 
                         & VL_GTES_III(32, 0x1fU, VL_EXTENDS_II(32,9, 
                                                                (0x1ffU 
                                                                 & vlSelf->__VdfgTmp_h586768a0__0))));
    vlSelf->__PVT__Yr = (1U & (((0x33U == (0x7fU & vlSelf->__PVT__ir)) 
                                | (0x63U == (0x7fU 
                                             & vlSelf->__PVT__ir)))
                                ? (IData)(vlSelf->d_wdata)
                                : vlSelf->__PVT__imm_sr));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if ((0x37U != (0x7fU & vlSelf->__PVT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->__PVT__ir))) {
                if ((0x6fU == (0x7fU & vlSelf->__PVT__ir))) {
                    vlSelf->__PVT__Yr = (1U & (4U >> (IData)(vlSelf->__PVT__k)));
                }
            }
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        vlSelf->__PVT__Yr = (1U & (4U >> (IData)(vlSelf->__PVT__k)));
    } else if ((5U == (IData)(vlSelf->__PVT__state))) {
        vlSelf->__PVT__Yr = (1U & (((0x6fU == (0x7fU 
                                               & vlSelf->__PVT__ir)) 
                                    | ((0x63U == (0x7fU 
                                                  & vlSelf->__PVT__ir)) 
                                       & (IData)(__PVT__cond)))
                                    ? vlSelf->__PVT__imm_sr
                                    : (4U >> (IData)(vlSelf->__PVT__k))));
    }
    vlSelf->__PVT__sum_c = (3U & ((IData)(vlSelf->__PVT__X) 
                                  + ((1U & ((IData)(vlSelf->__PVT__inv)
                                             ? (~ (IData)(vlSelf->__PVT__Yr))
                                             : (IData)(vlSelf->__PVT__Yr))) 
                                     + ((0U == (IData)(vlSelf->__PVT__k))
                                         ? (IData)(vlSelf->__PVT__inv)
                                         : (IData)(vlSelf->__PVT__cy)))));
    vlSelf->__PVT__addr_ins = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__addr, 1U) 
                               | VL_SHIFTL_III(32,32,32, 
                                               (1U 
                                                & (IData)(vlSelf->__PVT__sum_c)), 0x1fU));
    vlSelf->__PVT__pc_ins = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__pc, 1U) 
                             | VL_SHIFTL_III(32,32,32, 
                                             (1U & (IData)(vlSelf->__PVT__sum_c)), 0x1fU));
    vlSelf->__PVT__nz_n = (1U & (((0U != (IData)(vlSelf->__PVT__k)) 
                                  & (IData)(vlSelf->__PVT__nz)) 
                                 | (IData)(vlSelf->__PVT__sum_c)));
    vlSelf->__PVT__wd = (1U & (((IData)(vlSelf->__VdfgTmp_h18c46dac__0) 
                                & ((4U == (7U & (vlSelf->__PVT__ir 
                                                 >> 0xcU))) 
                                   | ((6U == (7U & 
                                              (vlSelf->__PVT__ir 
                                               >> 0xcU))) 
                                      | (7U == (7U 
                                                & (vlSelf->__PVT__ir 
                                                   >> 0xcU))))))
                                ? ((4U == (7U & (vlSelf->__PVT__ir 
                                                 >> 0xcU)))
                                    ? ((IData)(vlSelf->__PVT__X) 
                                       ^ (IData)(vlSelf->__PVT__Yr))
                                    : ((6U == (7U & 
                                               (vlSelf->__PVT__ir 
                                                >> 0xcU)))
                                        ? ((IData)(vlSelf->__PVT__X) 
                                           | (IData)(vlSelf->__PVT__Yr))
                                        : ((IData)(vlSelf->__PVT__X) 
                                           & (IData)(vlSelf->__PVT__Yr))))
                                : (IData)(vlSelf->__PVT__sum_c)));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if (vlSelf->__PVT__is_shift) {
            vlSelf->__PVT__wd = (1U & VL_SHIFTR_III(2,2,6, 
                                                    ((((IData)(vlSelf->__PVT__is_sll)
                                                        ? 
                                                       ((IData)(vlSelf->__PVT__va) 
                                                        & (IData)(vlSelf->__PVT__a_val))
                                                        : 
                                                       ((IData)(vlSelf->__PVT__vb)
                                                         ? (IData)(vlSelf->d_wdata)
                                                         : (IData)(vlSelf->__PVT__fill))) 
                                                      << 1U) 
                                                     | ((IData)(vlSelf->__PVT__is_sll)
                                                         ? 
                                                        ((IData)(vlSelf->__PVT__vb) 
                                                         & (IData)(vlSelf->d_wdata))
                                                         : 
                                                        ((IData)(vlSelf->__PVT__va)
                                                          ? (IData)(vlSelf->__PVT__a_val)
                                                          : (IData)(vlSelf->__PVT__fill)))), 
                                                    ((IData)(vlSelf->__PVT__is_sll)
                                                      ? 1U
                                                      : 0U)));
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        if ((3U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__wd = vlSymsp->TOP.tb_sys5__DOT__dut__DOT__slot__BRA__14__KET____DOT__dq_b;
        } else if (vlSelf->__PVT__is_slt) {
            vlSelf->__PVT__wd = ((0U == (IData)(vlSelf->__PVT__k)) 
                                 & ((2U == (7U & (vlSelf->__PVT__ir 
                                                  >> 0xcU)))
                                     ? (IData)(vlSelf->__PVT__f_lt)
                                     : (IData)(vlSelf->__PVT__f_ltu)));
        } else if ((0x67U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__wd = (1U & (IData)(vlSelf->__PVT__sum_c));
        }
    }
}

VL_ATTR_COLD void Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__15__KET____DOT__core__0(Vtb_sys5_uc_core_v2s__W1* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_sys5__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+          Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__15__KET____DOT__core__0\n"); );
    // Init
    CData/*0:0*/ __PVT__cond;
    __PVT__cond = 0;
    CData/*0:0*/ __PVT__we;
    __PVT__we = 0;
    CData/*0:0*/ __VdfgExtracted_h62388771__0;
    __VdfgExtracted_h62388771__0 = 0;
    CData/*0:0*/ __VdfgTmp_h2cd83c5b__0;
    __VdfgTmp_h2cd83c5b__0 = 0;
    CData/*0:0*/ __VdfgTmp_he83b8d53__0;
    __VdfgTmp_he83b8d53__0 = 0;
    CData/*0:0*/ __VdfgTmp_hd9b60348__0;
    __VdfgTmp_hd9b60348__0 = 0;
    CData/*5:0*/ __Vtableidx16;
    __Vtableidx16 = 0;
    // Body
    vlSelf->__PVT__rs2 = (0x1fU & (vlSelf->__PVT__ir 
                                   >> 0x14U));
    vlSelf->__PVT__is_sys = (0x73U == (0x7fU & vlSelf->__PVT__ir));
    vlSelf->__PVT__last_up = (0x1fU == (IData)(vlSelf->__PVT__k));
    vlSelf->__PVT__pc_rot = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__pc, 1U) 
                             | VL_SHIFTL_III(32,32,32, vlSelf->__PVT__pc, 0x1fU));
    vlSelf->__PVT__imm_rot = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__imm_sr, 1U) 
                              | VL_SHIFTL_III(32,32,32, vlSelf->__PVT__imm_sr, 0x1fU));
    vlSelf->__PVT__opc = (0x7fU & vlSelf->__PVT__ir);
    vlSelf->d_addr = (((QData)((IData)((vlSelf->__PVT__addr 
                                        >> 2U))) << 5U) 
                      | (QData)((IData)(vlSelf->__PVT__k)));
    vlSelf->rw_addr = ((0x3e0U & (vlSelf->__PVT__ir 
                                  >> 2U)) | (IData)(vlSelf->__PVT__k));
    __VdfgTmp_h2cd83c5b__0 = ((0x37U == (0x7fU & vlSelf->__PVT__ir)) 
                              | (0x17U == (0x7fU & vlSelf->__PVT__ir)));
    __Vtableidx16 = (((IData)(vlSelf->__PVT__f_eq) 
                      << 5U) | (((IData)(vlSelf->__PVT__f_lt) 
                                 << 4U) | (((IData)(vlSelf->__PVT__f_ltu) 
                                            << 3U) 
                                           | (7U & 
                                              (vlSelf->__PVT__ir 
                                               >> 0xcU)))));
    __PVT__cond = Vtb_sys5__ConstPool__TABLE_h2a0441a0_0
        [__Vtableidx16];
    vlSelf->__PVT__a_val = ((0U != (0x1fU & (vlSelf->__PVT__ir 
                                             >> 0xfU))) 
                            & (IData)(vlSymsp->TOP.tb_sys5__DOT__dut__DOT__slot__BRA__15__KET____DOT__rqa_b));
    __VdfgTmp_hd9b60348__0 = ((2U == (7U & (vlSelf->__PVT__ir 
                                            >> 0xcU))) 
                              | (3U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))));
    vlSelf->__VdfgTmp_h18c46dac__0 = ((0x13U == (0x7fU 
                                                 & vlSelf->__PVT__ir)) 
                                      | (0x33U == (0x7fU 
                                                   & vlSelf->__PVT__ir)));
    __VdfgTmp_he83b8d53__0 = ((1U == (7U & (vlSelf->__PVT__ir 
                                            >> 0xcU))) 
                              | (5U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))));
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
    vlSelf->__PVT__X = vlSelf->__PVT__a_val;
    vlSelf->__PVT__is_cmp = ((0x63U == (0x7fU & vlSelf->__PVT__ir)) 
                             | ((IData)(vlSelf->__VdfgTmp_h18c46dac__0) 
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
    vlSelf->__PVT__inv = 0U;
    vlSelf->__PVT__is_shift = ((IData)(vlSelf->__PVT__sh_i) 
                               | ((0x33U == (0x7fU 
                                             & vlSelf->__PVT__ir)) 
                                  & (IData)(__VdfgTmp_he83b8d53__0)));
    __PVT__we = 0U;
    vlSelf->__PVT__fill = ((IData)(vlSelf->__PVT__is_shift) 
                           & (IData)(((0x40005000U 
                                       == (0x40007000U 
                                           & vlSelf->__PVT__ir)) 
                                      & (IData)(vlSelf->__PVT__sgn))));
    vlSelf->__PVT__is_sll = ((IData)(vlSelf->__PVT__is_shift) 
                             & (0x1000U == (0x7000U 
                                            & vlSelf->__PVT__ir)));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        vlSelf->__PVT__shx = vlSelf->__PVT__is_shift;
        if ((0x37U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__X = 0U;
        } else if ((0x17U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
        } else if ((0x6fU == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
        }
        if ((0x37U != (0x7fU & vlSelf->__PVT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->__PVT__ir))) {
                if ((0x6fU != (0x7fU & vlSelf->__PVT__ir))) {
                    if (((IData)((0x40000033U == (0x4000707fU 
                                                  & vlSelf->__PVT__ir))) 
                         | (IData)(vlSelf->__PVT__is_cmp))) {
                        vlSelf->__PVT__inv = 1U;
                    }
                }
            }
        }
        if (vlSelf->__PVT__is_shift) {
            __PVT__we = 1U;
        } else if (__VdfgExtracted_h62388771__0) {
            __PVT__we = 1U;
        } else if (((~ (IData)(vlSelf->__PVT__is_cmp)) 
                    & (IData)(vlSelf->__VdfgTmp_h18c46dac__0))) {
            __PVT__we = 1U;
        }
    } else {
        vlSelf->__PVT__shx = 0U;
        if ((4U == (IData)(vlSelf->__PVT__state))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
            if ((3U == (0x7fU & vlSelf->__PVT__ir))) {
                __PVT__we = 1U;
            } else if (vlSelf->__PVT__is_slt) {
                __PVT__we = 1U;
            } else if ((0x67U == (0x7fU & vlSelf->__PVT__ir))) {
                __PVT__we = 1U;
            }
        } else if ((5U == (IData)(vlSelf->__PVT__state))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
        }
    }
    vlSelf->rw_en = ((IData)(__PVT__we) & (0U != (0x1fU 
                                                  & (vlSelf->__PVT__ir 
                                                     >> 7U))));
    if (vlSelf->__PVT__is_sll) {
        vlSelf->__PVT__sll_dir = vlSelf->__PVT__is_shift;
        vlSelf->__PVT__ia = (0x1ffU & ((IData)(vlSelf->__PVT__k) 
                                       - (IData)(vlSelf->__PVT__shamt_w)));
        vlSelf->__VdfgTmp_h586768a0__0 = ((VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__k)) 
                                           - VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__shamt_w))) 
                                          - (IData)(1U));
    } else {
        vlSelf->__PVT__sll_dir = 0U;
        vlSelf->__PVT__ia = (0x1ffU & ((IData)(vlSelf->__PVT__k) 
                                       + (IData)(vlSelf->__PVT__shamt_w)));
        vlSelf->__VdfgTmp_h586768a0__0 = ((IData)(1U) 
                                          + (VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__k)) 
                                             + VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__shamt_w))));
    }
    vlSelf->d_wdata = ((~ ((IData)(vlSelf->__PVT__shx)
                            ? (0U == (0x1fU & (vlSelf->__PVT__ir 
                                               >> 0xfU)))
                            : (0U == (0x1fU & (vlSelf->__PVT__ir 
                                               >> 0x14U))))) 
                       & (IData)(vlSymsp->TOP.tb_sys5__DOT__dut__DOT__slot__BRA__15__KET____DOT__rqb_b));
    vlSelf->__PVT__exec_done = ((IData)(vlSelf->__PVT__sll_dir)
                                 ? (0U == (IData)(vlSelf->__PVT__k))
                                 : (0x1fU == (IData)(vlSelf->__PVT__k)));
    vlSelf->__PVT__va = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__ia))) 
                         & VL_GTES_III(32, 0x1fU, VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__ia))));
    vlSelf->__PVT__vb = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, 
                                                           (0x1ffU 
                                                            & vlSelf->__VdfgTmp_h586768a0__0))) 
                         & VL_GTES_III(32, 0x1fU, VL_EXTENDS_II(32,9, 
                                                                (0x1ffU 
                                                                 & vlSelf->__VdfgTmp_h586768a0__0))));
    vlSelf->__PVT__Yr = (1U & (((0x33U == (0x7fU & vlSelf->__PVT__ir)) 
                                | (0x63U == (0x7fU 
                                             & vlSelf->__PVT__ir)))
                                ? (IData)(vlSelf->d_wdata)
                                : vlSelf->__PVT__imm_sr));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if ((0x37U != (0x7fU & vlSelf->__PVT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->__PVT__ir))) {
                if ((0x6fU == (0x7fU & vlSelf->__PVT__ir))) {
                    vlSelf->__PVT__Yr = (1U & (4U >> (IData)(vlSelf->__PVT__k)));
                }
            }
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        vlSelf->__PVT__Yr = (1U & (4U >> (IData)(vlSelf->__PVT__k)));
    } else if ((5U == (IData)(vlSelf->__PVT__state))) {
        vlSelf->__PVT__Yr = (1U & (((0x6fU == (0x7fU 
                                               & vlSelf->__PVT__ir)) 
                                    | ((0x63U == (0x7fU 
                                                  & vlSelf->__PVT__ir)) 
                                       & (IData)(__PVT__cond)))
                                    ? vlSelf->__PVT__imm_sr
                                    : (4U >> (IData)(vlSelf->__PVT__k))));
    }
    vlSelf->__PVT__sum_c = (3U & ((IData)(vlSelf->__PVT__X) 
                                  + ((1U & ((IData)(vlSelf->__PVT__inv)
                                             ? (~ (IData)(vlSelf->__PVT__Yr))
                                             : (IData)(vlSelf->__PVT__Yr))) 
                                     + ((0U == (IData)(vlSelf->__PVT__k))
                                         ? (IData)(vlSelf->__PVT__inv)
                                         : (IData)(vlSelf->__PVT__cy)))));
    vlSelf->__PVT__addr_ins = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__addr, 1U) 
                               | VL_SHIFTL_III(32,32,32, 
                                               (1U 
                                                & (IData)(vlSelf->__PVT__sum_c)), 0x1fU));
    vlSelf->__PVT__pc_ins = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__pc, 1U) 
                             | VL_SHIFTL_III(32,32,32, 
                                             (1U & (IData)(vlSelf->__PVT__sum_c)), 0x1fU));
    vlSelf->__PVT__nz_n = (1U & (((0U != (IData)(vlSelf->__PVT__k)) 
                                  & (IData)(vlSelf->__PVT__nz)) 
                                 | (IData)(vlSelf->__PVT__sum_c)));
    vlSelf->__PVT__wd = (1U & (((IData)(vlSelf->__VdfgTmp_h18c46dac__0) 
                                & ((4U == (7U & (vlSelf->__PVT__ir 
                                                 >> 0xcU))) 
                                   | ((6U == (7U & 
                                              (vlSelf->__PVT__ir 
                                               >> 0xcU))) 
                                      | (7U == (7U 
                                                & (vlSelf->__PVT__ir 
                                                   >> 0xcU))))))
                                ? ((4U == (7U & (vlSelf->__PVT__ir 
                                                 >> 0xcU)))
                                    ? ((IData)(vlSelf->__PVT__X) 
                                       ^ (IData)(vlSelf->__PVT__Yr))
                                    : ((6U == (7U & 
                                               (vlSelf->__PVT__ir 
                                                >> 0xcU)))
                                        ? ((IData)(vlSelf->__PVT__X) 
                                           | (IData)(vlSelf->__PVT__Yr))
                                        : ((IData)(vlSelf->__PVT__X) 
                                           & (IData)(vlSelf->__PVT__Yr))))
                                : (IData)(vlSelf->__PVT__sum_c)));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if (vlSelf->__PVT__is_shift) {
            vlSelf->__PVT__wd = (1U & VL_SHIFTR_III(2,2,6, 
                                                    ((((IData)(vlSelf->__PVT__is_sll)
                                                        ? 
                                                       ((IData)(vlSelf->__PVT__va) 
                                                        & (IData)(vlSelf->__PVT__a_val))
                                                        : 
                                                       ((IData)(vlSelf->__PVT__vb)
                                                         ? (IData)(vlSelf->d_wdata)
                                                         : (IData)(vlSelf->__PVT__fill))) 
                                                      << 1U) 
                                                     | ((IData)(vlSelf->__PVT__is_sll)
                                                         ? 
                                                        ((IData)(vlSelf->__PVT__vb) 
                                                         & (IData)(vlSelf->d_wdata))
                                                         : 
                                                        ((IData)(vlSelf->__PVT__va)
                                                          ? (IData)(vlSelf->__PVT__a_val)
                                                          : (IData)(vlSelf->__PVT__fill)))), 
                                                    ((IData)(vlSelf->__PVT__is_sll)
                                                      ? 1U
                                                      : 0U)));
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        if ((3U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__wd = vlSymsp->TOP.tb_sys5__DOT__dut__DOT__slot__BRA__15__KET____DOT__dq_b;
        } else if (vlSelf->__PVT__is_slt) {
            vlSelf->__PVT__wd = ((0U == (IData)(vlSelf->__PVT__k)) 
                                 & ((2U == (7U & (vlSelf->__PVT__ir 
                                                  >> 0xcU)))
                                     ? (IData)(vlSelf->__PVT__f_lt)
                                     : (IData)(vlSelf->__PVT__f_ltu)));
        } else if ((0x67U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__wd = (1U & (IData)(vlSelf->__PVT__sum_c));
        }
    }
}

VL_ATTR_COLD void Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__16__KET____DOT__core__0(Vtb_sys5_uc_core_v2s__W1* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_sys5__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+          Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__16__KET____DOT__core__0\n"); );
    // Init
    CData/*0:0*/ __PVT__cond;
    __PVT__cond = 0;
    CData/*0:0*/ __PVT__we;
    __PVT__we = 0;
    CData/*0:0*/ __VdfgExtracted_h62388771__0;
    __VdfgExtracted_h62388771__0 = 0;
    CData/*0:0*/ __VdfgTmp_h2cd83c5b__0;
    __VdfgTmp_h2cd83c5b__0 = 0;
    CData/*0:0*/ __VdfgTmp_he83b8d53__0;
    __VdfgTmp_he83b8d53__0 = 0;
    CData/*0:0*/ __VdfgTmp_hd9b60348__0;
    __VdfgTmp_hd9b60348__0 = 0;
    CData/*5:0*/ __Vtableidx17;
    __Vtableidx17 = 0;
    // Body
    vlSelf->__PVT__rs2 = (0x1fU & (vlSelf->__PVT__ir 
                                   >> 0x14U));
    vlSelf->__PVT__is_sys = (0x73U == (0x7fU & vlSelf->__PVT__ir));
    vlSelf->__PVT__last_up = (0x1fU == (IData)(vlSelf->__PVT__k));
    vlSelf->__PVT__pc_rot = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__pc, 1U) 
                             | VL_SHIFTL_III(32,32,32, vlSelf->__PVT__pc, 0x1fU));
    vlSelf->__PVT__imm_rot = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__imm_sr, 1U) 
                              | VL_SHIFTL_III(32,32,32, vlSelf->__PVT__imm_sr, 0x1fU));
    vlSelf->__PVT__opc = (0x7fU & vlSelf->__PVT__ir);
    vlSelf->d_addr = (((QData)((IData)((vlSelf->__PVT__addr 
                                        >> 2U))) << 5U) 
                      | (QData)((IData)(vlSelf->__PVT__k)));
    vlSelf->rw_addr = ((0x3e0U & (vlSelf->__PVT__ir 
                                  >> 2U)) | (IData)(vlSelf->__PVT__k));
    __VdfgTmp_h2cd83c5b__0 = ((0x37U == (0x7fU & vlSelf->__PVT__ir)) 
                              | (0x17U == (0x7fU & vlSelf->__PVT__ir)));
    __Vtableidx17 = (((IData)(vlSelf->__PVT__f_eq) 
                      << 5U) | (((IData)(vlSelf->__PVT__f_lt) 
                                 << 4U) | (((IData)(vlSelf->__PVT__f_ltu) 
                                            << 3U) 
                                           | (7U & 
                                              (vlSelf->__PVT__ir 
                                               >> 0xcU)))));
    __PVT__cond = Vtb_sys5__ConstPool__TABLE_h2a0441a0_0
        [__Vtableidx17];
    vlSelf->__PVT__a_val = ((0U != (0x1fU & (vlSelf->__PVT__ir 
                                             >> 0xfU))) 
                            & (IData)(vlSymsp->TOP.tb_sys5__DOT__dut__DOT__slot__BRA__16__KET____DOT__rqa_b));
    __VdfgTmp_hd9b60348__0 = ((2U == (7U & (vlSelf->__PVT__ir 
                                            >> 0xcU))) 
                              | (3U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))));
    vlSelf->__VdfgTmp_h18c46dac__0 = ((0x13U == (0x7fU 
                                                 & vlSelf->__PVT__ir)) 
                                      | (0x33U == (0x7fU 
                                                   & vlSelf->__PVT__ir)));
    __VdfgTmp_he83b8d53__0 = ((1U == (7U & (vlSelf->__PVT__ir 
                                            >> 0xcU))) 
                              | (5U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))));
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
    vlSelf->__PVT__X = vlSelf->__PVT__a_val;
    vlSelf->__PVT__is_cmp = ((0x63U == (0x7fU & vlSelf->__PVT__ir)) 
                             | ((IData)(vlSelf->__VdfgTmp_h18c46dac__0) 
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
    vlSelf->__PVT__inv = 0U;
    vlSelf->__PVT__is_shift = ((IData)(vlSelf->__PVT__sh_i) 
                               | ((0x33U == (0x7fU 
                                             & vlSelf->__PVT__ir)) 
                                  & (IData)(__VdfgTmp_he83b8d53__0)));
    __PVT__we = 0U;
    vlSelf->__PVT__fill = ((IData)(vlSelf->__PVT__is_shift) 
                           & (IData)(((0x40005000U 
                                       == (0x40007000U 
                                           & vlSelf->__PVT__ir)) 
                                      & (IData)(vlSelf->__PVT__sgn))));
    vlSelf->__PVT__is_sll = ((IData)(vlSelf->__PVT__is_shift) 
                             & (0x1000U == (0x7000U 
                                            & vlSelf->__PVT__ir)));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        vlSelf->__PVT__shx = vlSelf->__PVT__is_shift;
        if ((0x37U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__X = 0U;
        } else if ((0x17U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
        } else if ((0x6fU == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
        }
        if ((0x37U != (0x7fU & vlSelf->__PVT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->__PVT__ir))) {
                if ((0x6fU != (0x7fU & vlSelf->__PVT__ir))) {
                    if (((IData)((0x40000033U == (0x4000707fU 
                                                  & vlSelf->__PVT__ir))) 
                         | (IData)(vlSelf->__PVT__is_cmp))) {
                        vlSelf->__PVT__inv = 1U;
                    }
                }
            }
        }
        if (vlSelf->__PVT__is_shift) {
            __PVT__we = 1U;
        } else if (__VdfgExtracted_h62388771__0) {
            __PVT__we = 1U;
        } else if (((~ (IData)(vlSelf->__PVT__is_cmp)) 
                    & (IData)(vlSelf->__VdfgTmp_h18c46dac__0))) {
            __PVT__we = 1U;
        }
    } else {
        vlSelf->__PVT__shx = 0U;
        if ((4U == (IData)(vlSelf->__PVT__state))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
            if ((3U == (0x7fU & vlSelf->__PVT__ir))) {
                __PVT__we = 1U;
            } else if (vlSelf->__PVT__is_slt) {
                __PVT__we = 1U;
            } else if ((0x67U == (0x7fU & vlSelf->__PVT__ir))) {
                __PVT__we = 1U;
            }
        } else if ((5U == (IData)(vlSelf->__PVT__state))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
        }
    }
    vlSelf->rw_en = ((IData)(__PVT__we) & (0U != (0x1fU 
                                                  & (vlSelf->__PVT__ir 
                                                     >> 7U))));
    if (vlSelf->__PVT__is_sll) {
        vlSelf->__PVT__sll_dir = vlSelf->__PVT__is_shift;
        vlSelf->__PVT__ia = (0x1ffU & ((IData)(vlSelf->__PVT__k) 
                                       - (IData)(vlSelf->__PVT__shamt_w)));
        vlSelf->__VdfgTmp_h586768a0__0 = ((VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__k)) 
                                           - VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__shamt_w))) 
                                          - (IData)(1U));
    } else {
        vlSelf->__PVT__sll_dir = 0U;
        vlSelf->__PVT__ia = (0x1ffU & ((IData)(vlSelf->__PVT__k) 
                                       + (IData)(vlSelf->__PVT__shamt_w)));
        vlSelf->__VdfgTmp_h586768a0__0 = ((IData)(1U) 
                                          + (VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__k)) 
                                             + VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__shamt_w))));
    }
    vlSelf->d_wdata = ((~ ((IData)(vlSelf->__PVT__shx)
                            ? (0U == (0x1fU & (vlSelf->__PVT__ir 
                                               >> 0xfU)))
                            : (0U == (0x1fU & (vlSelf->__PVT__ir 
                                               >> 0x14U))))) 
                       & (IData)(vlSymsp->TOP.tb_sys5__DOT__dut__DOT__slot__BRA__16__KET____DOT__rqb_b));
    vlSelf->__PVT__exec_done = ((IData)(vlSelf->__PVT__sll_dir)
                                 ? (0U == (IData)(vlSelf->__PVT__k))
                                 : (0x1fU == (IData)(vlSelf->__PVT__k)));
    vlSelf->__PVT__va = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__ia))) 
                         & VL_GTES_III(32, 0x1fU, VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__ia))));
    vlSelf->__PVT__vb = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, 
                                                           (0x1ffU 
                                                            & vlSelf->__VdfgTmp_h586768a0__0))) 
                         & VL_GTES_III(32, 0x1fU, VL_EXTENDS_II(32,9, 
                                                                (0x1ffU 
                                                                 & vlSelf->__VdfgTmp_h586768a0__0))));
    vlSelf->__PVT__Yr = (1U & (((0x33U == (0x7fU & vlSelf->__PVT__ir)) 
                                | (0x63U == (0x7fU 
                                             & vlSelf->__PVT__ir)))
                                ? (IData)(vlSelf->d_wdata)
                                : vlSelf->__PVT__imm_sr));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if ((0x37U != (0x7fU & vlSelf->__PVT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->__PVT__ir))) {
                if ((0x6fU == (0x7fU & vlSelf->__PVT__ir))) {
                    vlSelf->__PVT__Yr = (1U & (4U >> (IData)(vlSelf->__PVT__k)));
                }
            }
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        vlSelf->__PVT__Yr = (1U & (4U >> (IData)(vlSelf->__PVT__k)));
    } else if ((5U == (IData)(vlSelf->__PVT__state))) {
        vlSelf->__PVT__Yr = (1U & (((0x6fU == (0x7fU 
                                               & vlSelf->__PVT__ir)) 
                                    | ((0x63U == (0x7fU 
                                                  & vlSelf->__PVT__ir)) 
                                       & (IData)(__PVT__cond)))
                                    ? vlSelf->__PVT__imm_sr
                                    : (4U >> (IData)(vlSelf->__PVT__k))));
    }
    vlSelf->__PVT__sum_c = (3U & ((IData)(vlSelf->__PVT__X) 
                                  + ((1U & ((IData)(vlSelf->__PVT__inv)
                                             ? (~ (IData)(vlSelf->__PVT__Yr))
                                             : (IData)(vlSelf->__PVT__Yr))) 
                                     + ((0U == (IData)(vlSelf->__PVT__k))
                                         ? (IData)(vlSelf->__PVT__inv)
                                         : (IData)(vlSelf->__PVT__cy)))));
    vlSelf->__PVT__addr_ins = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__addr, 1U) 
                               | VL_SHIFTL_III(32,32,32, 
                                               (1U 
                                                & (IData)(vlSelf->__PVT__sum_c)), 0x1fU));
    vlSelf->__PVT__pc_ins = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__pc, 1U) 
                             | VL_SHIFTL_III(32,32,32, 
                                             (1U & (IData)(vlSelf->__PVT__sum_c)), 0x1fU));
    vlSelf->__PVT__nz_n = (1U & (((0U != (IData)(vlSelf->__PVT__k)) 
                                  & (IData)(vlSelf->__PVT__nz)) 
                                 | (IData)(vlSelf->__PVT__sum_c)));
    vlSelf->__PVT__wd = (1U & (((IData)(vlSelf->__VdfgTmp_h18c46dac__0) 
                                & ((4U == (7U & (vlSelf->__PVT__ir 
                                                 >> 0xcU))) 
                                   | ((6U == (7U & 
                                              (vlSelf->__PVT__ir 
                                               >> 0xcU))) 
                                      | (7U == (7U 
                                                & (vlSelf->__PVT__ir 
                                                   >> 0xcU))))))
                                ? ((4U == (7U & (vlSelf->__PVT__ir 
                                                 >> 0xcU)))
                                    ? ((IData)(vlSelf->__PVT__X) 
                                       ^ (IData)(vlSelf->__PVT__Yr))
                                    : ((6U == (7U & 
                                               (vlSelf->__PVT__ir 
                                                >> 0xcU)))
                                        ? ((IData)(vlSelf->__PVT__X) 
                                           | (IData)(vlSelf->__PVT__Yr))
                                        : ((IData)(vlSelf->__PVT__X) 
                                           & (IData)(vlSelf->__PVT__Yr))))
                                : (IData)(vlSelf->__PVT__sum_c)));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if (vlSelf->__PVT__is_shift) {
            vlSelf->__PVT__wd = (1U & VL_SHIFTR_III(2,2,6, 
                                                    ((((IData)(vlSelf->__PVT__is_sll)
                                                        ? 
                                                       ((IData)(vlSelf->__PVT__va) 
                                                        & (IData)(vlSelf->__PVT__a_val))
                                                        : 
                                                       ((IData)(vlSelf->__PVT__vb)
                                                         ? (IData)(vlSelf->d_wdata)
                                                         : (IData)(vlSelf->__PVT__fill))) 
                                                      << 1U) 
                                                     | ((IData)(vlSelf->__PVT__is_sll)
                                                         ? 
                                                        ((IData)(vlSelf->__PVT__vb) 
                                                         & (IData)(vlSelf->d_wdata))
                                                         : 
                                                        ((IData)(vlSelf->__PVT__va)
                                                          ? (IData)(vlSelf->__PVT__a_val)
                                                          : (IData)(vlSelf->__PVT__fill)))), 
                                                    ((IData)(vlSelf->__PVT__is_sll)
                                                      ? 1U
                                                      : 0U)));
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        if ((3U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__wd = vlSymsp->TOP.tb_sys5__DOT__dut__DOT__slot__BRA__16__KET____DOT__dq_b;
        } else if (vlSelf->__PVT__is_slt) {
            vlSelf->__PVT__wd = ((0U == (IData)(vlSelf->__PVT__k)) 
                                 & ((2U == (7U & (vlSelf->__PVT__ir 
                                                  >> 0xcU)))
                                     ? (IData)(vlSelf->__PVT__f_lt)
                                     : (IData)(vlSelf->__PVT__f_ltu)));
        } else if ((0x67U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__wd = (1U & (IData)(vlSelf->__PVT__sum_c));
        }
    }
}

VL_ATTR_COLD void Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__17__KET____DOT__core__0(Vtb_sys5_uc_core_v2s__W1* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_sys5__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+          Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__17__KET____DOT__core__0\n"); );
    // Init
    CData/*0:0*/ __PVT__cond;
    __PVT__cond = 0;
    CData/*0:0*/ __PVT__we;
    __PVT__we = 0;
    CData/*0:0*/ __VdfgExtracted_h62388771__0;
    __VdfgExtracted_h62388771__0 = 0;
    CData/*0:0*/ __VdfgTmp_h2cd83c5b__0;
    __VdfgTmp_h2cd83c5b__0 = 0;
    CData/*0:0*/ __VdfgTmp_he83b8d53__0;
    __VdfgTmp_he83b8d53__0 = 0;
    CData/*0:0*/ __VdfgTmp_hd9b60348__0;
    __VdfgTmp_hd9b60348__0 = 0;
    CData/*5:0*/ __Vtableidx18;
    __Vtableidx18 = 0;
    // Body
    vlSelf->__PVT__rs2 = (0x1fU & (vlSelf->__PVT__ir 
                                   >> 0x14U));
    vlSelf->__PVT__is_sys = (0x73U == (0x7fU & vlSelf->__PVT__ir));
    vlSelf->__PVT__last_up = (0x1fU == (IData)(vlSelf->__PVT__k));
    vlSelf->__PVT__pc_rot = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__pc, 1U) 
                             | VL_SHIFTL_III(32,32,32, vlSelf->__PVT__pc, 0x1fU));
    vlSelf->__PVT__imm_rot = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__imm_sr, 1U) 
                              | VL_SHIFTL_III(32,32,32, vlSelf->__PVT__imm_sr, 0x1fU));
    vlSelf->__PVT__opc = (0x7fU & vlSelf->__PVT__ir);
    vlSelf->d_addr = (((QData)((IData)((vlSelf->__PVT__addr 
                                        >> 2U))) << 5U) 
                      | (QData)((IData)(vlSelf->__PVT__k)));
    vlSelf->rw_addr = ((0x3e0U & (vlSelf->__PVT__ir 
                                  >> 2U)) | (IData)(vlSelf->__PVT__k));
    __VdfgTmp_h2cd83c5b__0 = ((0x37U == (0x7fU & vlSelf->__PVT__ir)) 
                              | (0x17U == (0x7fU & vlSelf->__PVT__ir)));
    __Vtableidx18 = (((IData)(vlSelf->__PVT__f_eq) 
                      << 5U) | (((IData)(vlSelf->__PVT__f_lt) 
                                 << 4U) | (((IData)(vlSelf->__PVT__f_ltu) 
                                            << 3U) 
                                           | (7U & 
                                              (vlSelf->__PVT__ir 
                                               >> 0xcU)))));
    __PVT__cond = Vtb_sys5__ConstPool__TABLE_h2a0441a0_0
        [__Vtableidx18];
    vlSelf->__PVT__a_val = ((0U != (0x1fU & (vlSelf->__PVT__ir 
                                             >> 0xfU))) 
                            & (IData)(vlSymsp->TOP.tb_sys5__DOT__dut__DOT__slot__BRA__17__KET____DOT__rqa_b));
    __VdfgTmp_hd9b60348__0 = ((2U == (7U & (vlSelf->__PVT__ir 
                                            >> 0xcU))) 
                              | (3U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))));
    vlSelf->__VdfgTmp_h18c46dac__0 = ((0x13U == (0x7fU 
                                                 & vlSelf->__PVT__ir)) 
                                      | (0x33U == (0x7fU 
                                                   & vlSelf->__PVT__ir)));
    __VdfgTmp_he83b8d53__0 = ((1U == (7U & (vlSelf->__PVT__ir 
                                            >> 0xcU))) 
                              | (5U == (7U & (vlSelf->__PVT__ir 
                                              >> 0xcU))));
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
    vlSelf->__PVT__X = vlSelf->__PVT__a_val;
    vlSelf->__PVT__is_cmp = ((0x63U == (0x7fU & vlSelf->__PVT__ir)) 
                             | ((IData)(vlSelf->__VdfgTmp_h18c46dac__0) 
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
    vlSelf->__PVT__inv = 0U;
    vlSelf->__PVT__is_shift = ((IData)(vlSelf->__PVT__sh_i) 
                               | ((0x33U == (0x7fU 
                                             & vlSelf->__PVT__ir)) 
                                  & (IData)(__VdfgTmp_he83b8d53__0)));
    __PVT__we = 0U;
    vlSelf->__PVT__fill = ((IData)(vlSelf->__PVT__is_shift) 
                           & (IData)(((0x40005000U 
                                       == (0x40007000U 
                                           & vlSelf->__PVT__ir)) 
                                      & (IData)(vlSelf->__PVT__sgn))));
    vlSelf->__PVT__is_sll = ((IData)(vlSelf->__PVT__is_shift) 
                             & (0x1000U == (0x7000U 
                                            & vlSelf->__PVT__ir)));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        vlSelf->__PVT__shx = vlSelf->__PVT__is_shift;
        if ((0x37U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__X = 0U;
        } else if ((0x17U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
        } else if ((0x6fU == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
        }
        if ((0x37U != (0x7fU & vlSelf->__PVT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->__PVT__ir))) {
                if ((0x6fU != (0x7fU & vlSelf->__PVT__ir))) {
                    if (((IData)((0x40000033U == (0x4000707fU 
                                                  & vlSelf->__PVT__ir))) 
                         | (IData)(vlSelf->__PVT__is_cmp))) {
                        vlSelf->__PVT__inv = 1U;
                    }
                }
            }
        }
        if (vlSelf->__PVT__is_shift) {
            __PVT__we = 1U;
        } else if (__VdfgExtracted_h62388771__0) {
            __PVT__we = 1U;
        } else if (((~ (IData)(vlSelf->__PVT__is_cmp)) 
                    & (IData)(vlSelf->__VdfgTmp_h18c46dac__0))) {
            __PVT__we = 1U;
        }
    } else {
        vlSelf->__PVT__shx = 0U;
        if ((4U == (IData)(vlSelf->__PVT__state))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
            if ((3U == (0x7fU & vlSelf->__PVT__ir))) {
                __PVT__we = 1U;
            } else if (vlSelf->__PVT__is_slt) {
                __PVT__we = 1U;
            } else if ((0x67U == (0x7fU & vlSelf->__PVT__ir))) {
                __PVT__we = 1U;
            }
        } else if ((5U == (IData)(vlSelf->__PVT__state))) {
            vlSelf->__PVT__X = (1U & vlSelf->__PVT__pc);
        }
    }
    vlSelf->rw_en = ((IData)(__PVT__we) & (0U != (0x1fU 
                                                  & (vlSelf->__PVT__ir 
                                                     >> 7U))));
    if (vlSelf->__PVT__is_sll) {
        vlSelf->__PVT__sll_dir = vlSelf->__PVT__is_shift;
        vlSelf->__PVT__ia = (0x1ffU & ((IData)(vlSelf->__PVT__k) 
                                       - (IData)(vlSelf->__PVT__shamt_w)));
        vlSelf->__VdfgTmp_h586768a0__0 = ((VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__k)) 
                                           - VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__shamt_w))) 
                                          - (IData)(1U));
    } else {
        vlSelf->__PVT__sll_dir = 0U;
        vlSelf->__PVT__ia = (0x1ffU & ((IData)(vlSelf->__PVT__k) 
                                       + (IData)(vlSelf->__PVT__shamt_w)));
        vlSelf->__VdfgTmp_h586768a0__0 = ((IData)(1U) 
                                          + (VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__k)) 
                                             + VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__shamt_w))));
    }
    vlSelf->d_wdata = ((~ ((IData)(vlSelf->__PVT__shx)
                            ? (0U == (0x1fU & (vlSelf->__PVT__ir 
                                               >> 0xfU)))
                            : (0U == (0x1fU & (vlSelf->__PVT__ir 
                                               >> 0x14U))))) 
                       & (IData)(vlSymsp->TOP.tb_sys5__DOT__dut__DOT__slot__BRA__17__KET____DOT__rqb_b));
    vlSelf->__PVT__exec_done = ((IData)(vlSelf->__PVT__sll_dir)
                                 ? (0U == (IData)(vlSelf->__PVT__k))
                                 : (0x1fU == (IData)(vlSelf->__PVT__k)));
    vlSelf->__PVT__va = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__ia))) 
                         & VL_GTES_III(32, 0x1fU, VL_EXTENDS_II(32,9, (IData)(vlSelf->__PVT__ia))));
    vlSelf->__PVT__vb = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, 
                                                           (0x1ffU 
                                                            & vlSelf->__VdfgTmp_h586768a0__0))) 
                         & VL_GTES_III(32, 0x1fU, VL_EXTENDS_II(32,9, 
                                                                (0x1ffU 
                                                                 & vlSelf->__VdfgTmp_h586768a0__0))));
    vlSelf->__PVT__Yr = (1U & (((0x33U == (0x7fU & vlSelf->__PVT__ir)) 
                                | (0x63U == (0x7fU 
                                             & vlSelf->__PVT__ir)))
                                ? (IData)(vlSelf->d_wdata)
                                : vlSelf->__PVT__imm_sr));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if ((0x37U != (0x7fU & vlSelf->__PVT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->__PVT__ir))) {
                if ((0x6fU == (0x7fU & vlSelf->__PVT__ir))) {
                    vlSelf->__PVT__Yr = (1U & (4U >> (IData)(vlSelf->__PVT__k)));
                }
            }
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        vlSelf->__PVT__Yr = (1U & (4U >> (IData)(vlSelf->__PVT__k)));
    } else if ((5U == (IData)(vlSelf->__PVT__state))) {
        vlSelf->__PVT__Yr = (1U & (((0x6fU == (0x7fU 
                                               & vlSelf->__PVT__ir)) 
                                    | ((0x63U == (0x7fU 
                                                  & vlSelf->__PVT__ir)) 
                                       & (IData)(__PVT__cond)))
                                    ? vlSelf->__PVT__imm_sr
                                    : (4U >> (IData)(vlSelf->__PVT__k))));
    }
    vlSelf->__PVT__sum_c = (3U & ((IData)(vlSelf->__PVT__X) 
                                  + ((1U & ((IData)(vlSelf->__PVT__inv)
                                             ? (~ (IData)(vlSelf->__PVT__Yr))
                                             : (IData)(vlSelf->__PVT__Yr))) 
                                     + ((0U == (IData)(vlSelf->__PVT__k))
                                         ? (IData)(vlSelf->__PVT__inv)
                                         : (IData)(vlSelf->__PVT__cy)))));
    vlSelf->__PVT__addr_ins = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__addr, 1U) 
                               | VL_SHIFTL_III(32,32,32, 
                                               (1U 
                                                & (IData)(vlSelf->__PVT__sum_c)), 0x1fU));
    vlSelf->__PVT__pc_ins = (VL_SHIFTR_III(32,32,32, vlSelf->__PVT__pc, 1U) 
                             | VL_SHIFTL_III(32,32,32, 
                                             (1U & (IData)(vlSelf->__PVT__sum_c)), 0x1fU));
    vlSelf->__PVT__nz_n = (1U & (((0U != (IData)(vlSelf->__PVT__k)) 
                                  & (IData)(vlSelf->__PVT__nz)) 
                                 | (IData)(vlSelf->__PVT__sum_c)));
    vlSelf->__PVT__wd = (1U & (((IData)(vlSelf->__VdfgTmp_h18c46dac__0) 
                                & ((4U == (7U & (vlSelf->__PVT__ir 
                                                 >> 0xcU))) 
                                   | ((6U == (7U & 
                                              (vlSelf->__PVT__ir 
                                               >> 0xcU))) 
                                      | (7U == (7U 
                                                & (vlSelf->__PVT__ir 
                                                   >> 0xcU))))))
                                ? ((4U == (7U & (vlSelf->__PVT__ir 
                                                 >> 0xcU)))
                                    ? ((IData)(vlSelf->__PVT__X) 
                                       ^ (IData)(vlSelf->__PVT__Yr))
                                    : ((6U == (7U & 
                                               (vlSelf->__PVT__ir 
                                                >> 0xcU)))
                                        ? ((IData)(vlSelf->__PVT__X) 
                                           | (IData)(vlSelf->__PVT__Yr))
                                        : ((IData)(vlSelf->__PVT__X) 
                                           & (IData)(vlSelf->__PVT__Yr))))
                                : (IData)(vlSelf->__PVT__sum_c)));
    if ((3U == (IData)(vlSelf->__PVT__state))) {
        if (vlSelf->__PVT__is_shift) {
            vlSelf->__PVT__wd = (1U & VL_SHIFTR_III(2,2,6, 
                                                    ((((IData)(vlSelf->__PVT__is_sll)
                                                        ? 
                                                       ((IData)(vlSelf->__PVT__va) 
                                                        & (IData)(vlSelf->__PVT__a_val))
                                                        : 
                                                       ((IData)(vlSelf->__PVT__vb)
                                                         ? (IData)(vlSelf->d_wdata)
                                                         : (IData)(vlSelf->__PVT__fill))) 
                                                      << 1U) 
                                                     | ((IData)(vlSelf->__PVT__is_sll)
                                                         ? 
                                                        ((IData)(vlSelf->__PVT__vb) 
                                                         & (IData)(vlSelf->d_wdata))
                                                         : 
                                                        ((IData)(vlSelf->__PVT__va)
                                                          ? (IData)(vlSelf->__PVT__a_val)
                                                          : (IData)(vlSelf->__PVT__fill)))), 
                                                    ((IData)(vlSelf->__PVT__is_sll)
                                                      ? 1U
                                                      : 0U)));
        }
    } else if ((4U == (IData)(vlSelf->__PVT__state))) {
        if ((3U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__wd = vlSymsp->TOP.tb_sys5__DOT__dut__DOT__slot__BRA__17__KET____DOT__dq_b;
        } else if (vlSelf->__PVT__is_slt) {
            vlSelf->__PVT__wd = ((0U == (IData)(vlSelf->__PVT__k)) 
                                 & ((2U == (7U & (vlSelf->__PVT__ir 
                                                  >> 0xcU)))
                                     ? (IData)(vlSelf->__PVT__f_lt)
                                     : (IData)(vlSelf->__PVT__f_ltu)));
        } else if ((0x67U == (0x7fU & vlSelf->__PVT__ir))) {
            vlSelf->__PVT__wd = (1U & (IData)(vlSelf->__PVT__sum_c));
        }
    }
}
