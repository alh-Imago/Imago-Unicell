// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design implementation internals
// See Vtb_top_tang.h for the primary calling header

#include "Vtb_top_tang__pch.h"
#include "Vtb_top_tang__Syms.h"
#include "Vtb_top_tang___024root.h"

#ifdef VL_DEBUG
VL_ATTR_COLD void Vtb_top_tang___024root___dump_triggers__stl(Vtb_top_tang___024root* vlSelf);
#endif  // VL_DEBUG

VL_ATTR_COLD void Vtb_top_tang___024root___eval_triggers__stl(Vtb_top_tang___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_top_tang__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtb_top_tang___024root___eval_triggers__stl\n"); );
    // Body
    vlSelf->__VstlTriggered.set(0U, (IData)(vlSelf->__VstlFirstIteration));
#ifdef VL_DEBUG
    if (VL_UNLIKELY(vlSymsp->_vm_contextp__->debug())) {
        Vtb_top_tang___024root___dump_triggers__stl(vlSelf);
    }
#endif
}

extern const VlUnpacked<CData/*0:0*/, 64> Vtb_top_tang__ConstPool__TABLE_h2a0441a0_0;

VL_ATTR_COLD void Vtb_top_tang___024root___stl_sequent__TOP__0(Vtb_top_tang___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_top_tang__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtb_top_tang___024root___stl_sequent__TOP__0\n"); );
    // Init
    CData/*6:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__best_sz;
    tb_top_tang__DOT__dut__DOT__sys__DOT__best_sz = 0;
    CData/*6:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__bsz;
    tb_top_tang__DOT__dut__DOT__sys__DOT__bsz = 0;
    CData/*6:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__blk;
    tb_top_tang__DOT__dut__DOT__sys__DOT__blk = 0;
    CData/*5:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__bbase;
    tb_top_tang__DOT__dut__DOT__sys__DOT__bbase = 0;
    CData/*0:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__Vstatic__b3;
    tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__Vstatic__b3 = 0;
    CData/*0:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__Vstatic__b2;
    tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__Vstatic__b2 = 0;
    CData/*0:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__Vstatic__b1;
    tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__Vstatic__b1 = 0;
    CData/*7:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__Vstatic__x8;
    tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__Vstatic__x8 = 0;
    CData/*3:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__Vstatic__x4;
    tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__Vstatic__x4 = 0;
    CData/*1:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__Vstatic__x2;
    tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__Vstatic__x2 = 0;
    CData/*3:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__w_row;
    tb_top_tang__DOT__dut__DOT__sys__DOT__w_row = 0;
    IData/*31:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__mk;
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__mk = 0;
    CData/*4:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dko;
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dko = 0;
    IData/*31:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__mk;
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__mk = 0;
    CData/*4:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dko;
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dko = 0;
    CData/*0:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__shx;
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__shx = 0;
    IData/*31:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__pc_d;
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__pc_d = 0;
    IData/*31:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__imm_d;
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__imm_d = 0;
    IData/*31:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__c4_d;
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__c4_d = 0;
    SData/*8:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__qs;
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__qs = 0;
    SData/*8:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ia;
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ia = 0;
    CData/*0:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__va;
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__va = 0;
    CData/*0:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__vb;
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__vb = 0;
    IData/*31:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__fill;
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__fill = 0;
    IData/*31:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__X;
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__X = 0;
    IData/*31:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__Yr;
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__Yr = 0;
    CData/*0:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__inv;
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__inv = 0;
    QData/*32:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__sum_full;
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__sum_full = 0;
    IData/*31:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__sum_d;
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__sum_d = 0;
    CData/*0:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__cond;
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__cond = 0;
    CData/*0:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__we;
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__we = 0;
    IData/*31:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__wd;
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__wd = 0;
    CData/*0:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT____VdfgExtracted_h62388771__0;
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT____VdfgExtracted_h62388771__0 = 0;
    IData/*31:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT____VdfgTmp_h41a48239__0;
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT____VdfgTmp_h41a48239__0 = 0;
    CData/*0:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT____VdfgTmp_h2cd83c5b__0;
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT____VdfgTmp_h2cd83c5b__0 = 0;
    CData/*0:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT____VdfgTmp_he83b8d53__0;
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT____VdfgTmp_he83b8d53__0 = 0;
    CData/*0:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT____VdfgTmp_h18c46dac__0;
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT____VdfgTmp_h18c46dac__0 = 0;
    CData/*0:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT____VdfgTmp_hd9b60348__0;
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT____VdfgTmp_hd9b60348__0 = 0;
    CData/*5:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT____VdfgTmp_h933689ae__0;
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT____VdfgTmp_h933689ae__0 = 0;
    CData/*0:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__shx;
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__shx = 0;
    IData/*31:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__pc_d;
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__pc_d = 0;
    IData/*31:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__imm_d;
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__imm_d = 0;
    IData/*31:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__c4_d;
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__c4_d = 0;
    SData/*8:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__qs;
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__qs = 0;
    SData/*8:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ia;
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ia = 0;
    CData/*0:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__va;
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__va = 0;
    CData/*0:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__vb;
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__vb = 0;
    IData/*31:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__fill;
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__fill = 0;
    IData/*31:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__X;
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__X = 0;
    IData/*31:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__Yr;
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__Yr = 0;
    CData/*0:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__inv;
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__inv = 0;
    QData/*32:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__sum_full;
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__sum_full = 0;
    IData/*31:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__sum_d;
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__sum_d = 0;
    CData/*0:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__cond;
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__cond = 0;
    CData/*0:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__we;
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__we = 0;
    IData/*31:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__wd;
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__wd = 0;
    CData/*0:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT____VdfgExtracted_h62388771__0;
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT____VdfgExtracted_h62388771__0 = 0;
    IData/*31:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT____VdfgTmp_h41a48239__0;
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT____VdfgTmp_h41a48239__0 = 0;
    CData/*0:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT____VdfgTmp_h2cd83c5b__0;
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT____VdfgTmp_h2cd83c5b__0 = 0;
    CData/*0:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT____VdfgTmp_he83b8d53__0;
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT____VdfgTmp_he83b8d53__0 = 0;
    CData/*0:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT____VdfgTmp_h18c46dac__0;
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT____VdfgTmp_h18c46dac__0 = 0;
    CData/*0:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT____VdfgTmp_hd9b60348__0;
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT____VdfgTmp_hd9b60348__0 = 0;
    CData/*5:0*/ tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT____VdfgTmp_h933689ae__0;
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT____VdfgTmp_h933689ae__0 = 0;
    CData/*3:0*/ __Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__3__Vfuncout;
    __Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__3__Vfuncout = 0;
    SData/*15:0*/ __Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__3__x;
    __Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__3__x = 0;
    CData/*5:0*/ __Vtableidx1;
    __Vtableidx1 = 0;
    CData/*5:0*/ __Vtableidx2;
    __Vtableidx2 = 0;
    // Body
    vlSelf->tb_top_tang__DOT__dut__DOT__por_done = 
        (0xffU == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__por));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__rs2 
        = (0x1fU & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir 
                    >> 0x14U));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__is_sys 
        = (0x73U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__wm1 
        = (0x3fU & (((IData)(1U) << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__lw_r)) 
                    - (IData)(1U)));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__mlast 
        = (0x3fU & (VL_DIV_III(6, (0x3fU & ((IData)(4U) 
                                            + ((IData)(1U) 
                                               << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__lw_r)))), 
                               (0x3fU & ((IData)(1U) 
                                         << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__lw_r)))) 
                    - (IData)(1U)));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__kmax 
        = (0x1fU & ((0x3fU & (0x20U >> (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__lw_r))) 
                    - (IData)(1U)));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__opc 
        = (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__rs2 
        = (0x1fU & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir 
                    >> 0x14U));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__is_sys 
        = (0x73U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__wm1 
        = (0x3fU & (((IData)(1U) << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__lw_r)) 
                    - (IData)(1U)));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__mlast 
        = (0x3fU & (VL_DIV_III(6, (0x3fU & ((IData)(4U) 
                                            + ((IData)(1U) 
                                               << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__lw_r)))), 
                               (0x3fU & ((IData)(1U) 
                                         << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__lw_r)))) 
                    - (IData)(1U)));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__kmax 
        = (0x1fU & ((0x3fU & (0x20U >> (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__lw_r))) 
                    - (IData)(1U)));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__opc 
        = (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__cur_w 
        = (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__cur_lw)));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__cur_gm 
        = ((1ULL << (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__cur_lw)))) 
           - 1ULL);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__pend_b = 0U;
    if ((vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__kwr
         [0U] != vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__krd
         [0U])) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__pend_b = 1U;
    }
    if ((vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__kwr
         [1U] != vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__krd
         [1U])) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__pend_b = 1U;
    }
    if ((vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__kwr
         [2U] != vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__krd
         [2U])) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__pend_b = 1U;
    }
    if ((vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__kwr
         [3U] != vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__krd
         [3U])) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__pend_b = 1U;
    }
    if ((vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__kwr
         [4U] != vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__krd
         [4U])) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__pend_b = 1U;
    }
    if ((vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__kwr
         [5U] != vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__krd
         [5U])) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__pend_b = 1U;
    }
    if ((vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__kwr
         [6U] != vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__krd
         [6U])) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__pend_b = 1U;
    }
    if ((vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__kwr
         [7U] != vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__krd
         [7U])) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__pend_b = 1U;
    }
    if ((vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__kwr
         [8U] != vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__krd
         [8U])) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__pend_b = 1U;
    }
    if ((vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__kwr
         [9U] != vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__krd
         [9U])) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__pend_b = 1U;
    }
    if ((vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__kwr
         [0xaU] != vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__krd
         [0xaU])) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__pend_b = 1U;
    }
    if ((vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__kwr
         [0xbU] != vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__krd
         [0xbU])) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__pend_b = 1U;
    }
    if ((vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__kwr
         [0xcU] != vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__krd
         [0xcU])) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__pend_b = 1U;
    }
    if ((vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__kwr
         [0xdU] != vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__krd
         [0xdU])) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__pend_b = 1U;
    }
    if ((vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__kwr
         [0xeU] != vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__krd
         [0xeU])) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__pend_b = 1U;
    }
    vlSelf->tb_top_tang__DOT__dut__DOT__rst = ((0xffU 
                                                != (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__por)) 
                                               | (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__soft_rst));
    vlSelf->tb_top_tang__DOT__dut__DOT__q_start = vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__t_start
        [(0xfU & (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__q_tid))];
    vlSelf->tb_top_tang__DOT__dut__DOT__q_end = vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__t_end
        [(0xfU & (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__q_tid))];
    vlSelf->tb_top_tang__DOT__dut__DOT__q_a0 = vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__t_a0
        [(0xfU & (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__q_tid))];
    vlSelf->tb_top_tang__DOT__dut__DOT__q_arr = vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__t_arr
        [(0xfU & (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__q_tid))];
    vlSelf->tb_top_tang__DOT__dut__DOT__q_trap = vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__t_trap
        [(0xfU & (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__q_tid))];
    vlSelf->tb_top_tang__DOT__dut__DOT__q_state = vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__t_state
        [(0xfU & (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__q_tid))];
    vlSelf->tb_top_tang__DOT__dut__DOT__q_slot = vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__t_slot
        [(0xfU & (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__q_tid))];
    vlSelf->tb_top_tang__DOT__dut__DOT__q_pred = vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__t_pred
        [(0xfU & (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__q_tid))];
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__halted_v 
        = (((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__halted_r) 
            << 1U) | (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__halted_r));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__jw 
        = (0x3fU & ((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__j) 
                    * (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__lw_r)))));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__imm_rot 
        = (VL_SHIFTR_III(32,32,6, vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__imm_sr, 
                         (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__lw_r)))) 
           | VL_SHIFTL_III(32,32,6, vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__imm_sr, 
                           (0x3fU & ((IData)(0x20U) 
                                     - ((IData)(1U) 
                                        << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__lw_r))))));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__jw 
        = (0x3fU & ((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__j) 
                    * (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__lw_r)))));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__imm_rot 
        = (VL_SHIFTR_III(32,32,6, vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__imm_sr, 
                         (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__lw_r)))) 
           | VL_SHIFTL_III(32,32,6, vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__imm_sr, 
                           (0x3fU & ((IData)(0x20U) 
                                     - ((IData)(1U) 
                                        << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__lw_r))))));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__pend_v 
        = (((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__pend) 
            << 1U) | (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__pend));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__pend_c 
        = (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__qc_wr 
           != vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__qc_rd);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT____Vcellinp__slot__BRA__0__KET____DOT__dmm__we 
        = ((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__cph) 
           & ((4U == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__state)) 
              & (0x23U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir))));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT____Vcellinp__slot__BRA__1__KET____DOT__dmm__we 
        = ((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__cph) 
           & ((4U == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__state)) 
              & (0x23U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir))));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__hb = 0U;
    if ((vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__kwr
         [0U] != vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__krd
         [0U])) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__hb = 0U;
    }
    if ((vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__kwr
         [1U] != vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__krd
         [1U])) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__hb = 1U;
    }
    if ((vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__kwr
         [2U] != vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__krd
         [2U])) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__hb = 2U;
    }
    if ((vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__kwr
         [3U] != vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__krd
         [3U])) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__hb = 3U;
    }
    if ((vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__kwr
         [4U] != vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__krd
         [4U])) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__hb = 4U;
    }
    if ((vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__kwr
         [5U] != vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__krd
         [5U])) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__hb = 5U;
    }
    if ((vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__kwr
         [6U] != vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__krd
         [6U])) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__hb = 6U;
    }
    if ((vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__kwr
         [7U] != vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__krd
         [7U])) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__hb = 7U;
    }
    if ((vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__kwr
         [8U] != vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__krd
         [8U])) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__hb = 8U;
    }
    if ((vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__kwr
         [9U] != vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__krd
         [9U])) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__hb = 9U;
    }
    if ((vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__kwr
         [0xaU] != vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__krd
         [0xaU])) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__hb = 0xaU;
    }
    if ((vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__kwr
         [0xbU] != vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__krd
         [0xbU])) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__hb = 0xbU;
    }
    if ((vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__kwr
         [0xcU] != vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__krd
         [0xcU])) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__hb = 0xcU;
    }
    if ((vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__kwr
         [0xdU] != vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__krd
         [0xdU])) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__hb = 0xdU;
    }
    if ((vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__kwr
         [0xeU] != vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__krd
         [0xeU])) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__hb = 0xeU;
    }
    if ((vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__kwr
         [0xfU] != vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__krd
         [0xfU])) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__pend_b = 1U;
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__hb = 0xfU;
    }
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__last_up 
        = ((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__k) 
           == (0x1fU & ((0x3fU & (0x20U >> (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__lw_r))) 
                        - (IData)(1U))));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT____VdfgTmp_he4828306__0 
        = VL_SHIFTR_III(32,32,6, vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__pc, 
                        (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__lw_r))));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__last_up 
        = ((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__k) 
           == (0x1fU & ((0x3fU & (0x20U >> (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__lw_r))) 
                        - (IData)(1U))));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT____VdfgTmp_he4828306__0 
        = VL_SHIFTR_III(32,32,6, vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__pc, 
                        (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__lw_r))));
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__mk 
        = ((0x20U == (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__lw_r))))
            ? 0xffffffffU : (VL_SHIFTL_III(32,32,6, (IData)(1U), 
                                           (0x3fU & 
                                            ((IData)(1U) 
                                             << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__lw_r)))) 
                             - (IData)(1U)));
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__mk 
        = ((0x20U == (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__lw_r))))
            ? 0xffffffffU : (VL_SHIFTL_III(32,32,6, (IData)(1U), 
                                           (0x3fU & 
                                            ((IData)(1U) 
                                             << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__lw_r)))) 
                             - (IData)(1U)));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__fit_found = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__fit_base = 0U;
    tb_top_tang__DOT__dut__DOT__sys__DOT__best_sz = 0x7fU;
    tb_top_tang__DOT__dut__DOT__sys__DOT__bsz = 0U;
    tb_top_tang__DOT__dut__DOT__sys__DOT__blk = 0U;
    tb_top_tang__DOT__dut__DOT__sys__DOT__bbase = 0U;
    if (((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__cur_lw)))) 
         & (0ULL == (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slice_busy 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_top_tang__DOT__dut__DOT__sys__DOT__bsz = 
            (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__cur_lw)));
        tb_top_tang__DOT__dut__DOT__sys__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__cur_lw))))) {
            tb_top_tang__DOT__dut__DOT__sys__DOT__bbase = 0U;
            if (((2U >= (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__blk)) 
                 & (0ULL == (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slice_busy 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__gmask__2__w 
                                        = tb_top_tang__DOT__dut__DOT__sys__DOT__blk;
                                    vlSelf->__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__gmask__2__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__gmask__2__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__gmask__2__Vfuncout))))) {
                tb_top_tang__DOT__dut__DOT__sys__DOT__bsz 
                    = tb_top_tang__DOT__dut__DOT__sys__DOT__blk;
            }
        }
        tb_top_tang__DOT__dut__DOT__sys__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__cur_lw))))) {
            tb_top_tang__DOT__dut__DOT__sys__DOT__bbase = 0U;
            if (((2U >= (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__blk)) 
                 & (0ULL == (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slice_busy 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__gmask__2__w 
                                        = tb_top_tang__DOT__dut__DOT__sys__DOT__blk;
                                    vlSelf->__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__gmask__2__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__gmask__2__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__gmask__2__Vfuncout))))) {
                tb_top_tang__DOT__dut__DOT__sys__DOT__bsz 
                    = tb_top_tang__DOT__dut__DOT__sys__DOT__blk;
            }
        }
        tb_top_tang__DOT__dut__DOT__sys__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__cur_lw))))) {
            tb_top_tang__DOT__dut__DOT__sys__DOT__bbase = 0U;
            if (((2U >= (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__blk)) 
                 & (0ULL == (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slice_busy 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__gmask__2__w 
                                        = tb_top_tang__DOT__dut__DOT__sys__DOT__blk;
                                    vlSelf->__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__gmask__2__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__gmask__2__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__gmask__2__Vfuncout))))) {
                tb_top_tang__DOT__dut__DOT__sys__DOT__bsz 
                    = tb_top_tang__DOT__dut__DOT__sys__DOT__blk;
            }
        }
        tb_top_tang__DOT__dut__DOT__sys__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__cur_lw))))) {
            tb_top_tang__DOT__dut__DOT__sys__DOT__bbase = 0U;
            if (((2U >= (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__blk)) 
                 & (0ULL == (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slice_busy 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__gmask__2__w 
                                        = tb_top_tang__DOT__dut__DOT__sys__DOT__blk;
                                    vlSelf->__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__gmask__2__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__gmask__2__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__gmask__2__Vfuncout))))) {
                tb_top_tang__DOT__dut__DOT__sys__DOT__bsz 
                    = tb_top_tang__DOT__dut__DOT__sys__DOT__blk;
            }
        }
        tb_top_tang__DOT__dut__DOT__sys__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__cur_lw))))) {
            tb_top_tang__DOT__dut__DOT__sys__DOT__bbase = 0U;
            if (((2U >= (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__blk)) 
                 & (0ULL == (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slice_busy 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__gmask__2__w 
                                        = tb_top_tang__DOT__dut__DOT__sys__DOT__blk;
                                    vlSelf->__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__gmask__2__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__gmask__2__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__gmask__2__Vfuncout))))) {
                tb_top_tang__DOT__dut__DOT__sys__DOT__bsz 
                    = tb_top_tang__DOT__dut__DOT__sys__DOT__blk;
            }
        }
        tb_top_tang__DOT__dut__DOT__sys__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__cur_lw))))) {
            tb_top_tang__DOT__dut__DOT__sys__DOT__bbase = 0U;
            if (((2U >= (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__blk)) 
                 & (0ULL == (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slice_busy 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__gmask__2__w 
                                        = tb_top_tang__DOT__dut__DOT__sys__DOT__blk;
                                    vlSelf->__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__gmask__2__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__gmask__2__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__gmask__2__Vfuncout))))) {
                tb_top_tang__DOT__dut__DOT__sys__DOT__bsz 
                    = tb_top_tang__DOT__dut__DOT__sys__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__fit_found)) 
                   | ((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__bsz) 
                      < (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__best_sz))))) {
            vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__fit_found = 1U;
            vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__fit_base = 0U;
            tb_top_tang__DOT__dut__DOT__sys__DOT__best_sz 
                = tb_top_tang__DOT__dut__DOT__sys__DOT__bsz;
        }
    }
    if ((((0U == (1U & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__cur_lw))) 
                        - (IData)(1U)))) & (2U >= ((IData)(1U) 
                                                   + 
                                                   (0x3fU 
                                                    & ((IData)(1U) 
                                                       << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slice_busy, 1U) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_top_tang__DOT__dut__DOT__sys__DOT__bsz = 
            (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__cur_lw)));
        tb_top_tang__DOT__dut__DOT__sys__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__cur_lw))))) {
            tb_top_tang__DOT__dut__DOT__sys__DOT__bbase 
                = (1U & (~ ((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__blk) 
                            - (IData)(1U))));
            if (((2U >= ((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__bbase) 
                         + (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slice_busy 
                              >> (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__gmask__2__w 
                                        = tb_top_tang__DOT__dut__DOT__sys__DOT__blk;
                                    vlSelf->__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__gmask__2__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__gmask__2__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__gmask__2__Vfuncout))))) {
                tb_top_tang__DOT__dut__DOT__sys__DOT__bsz 
                    = tb_top_tang__DOT__dut__DOT__sys__DOT__blk;
            }
        }
        tb_top_tang__DOT__dut__DOT__sys__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__cur_lw))))) {
            tb_top_tang__DOT__dut__DOT__sys__DOT__bbase 
                = (1U & (~ ((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__blk) 
                            - (IData)(1U))));
            if (((2U >= ((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__bbase) 
                         + (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slice_busy 
                              >> (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__gmask__2__w 
                                        = tb_top_tang__DOT__dut__DOT__sys__DOT__blk;
                                    vlSelf->__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__gmask__2__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__gmask__2__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__gmask__2__Vfuncout))))) {
                tb_top_tang__DOT__dut__DOT__sys__DOT__bsz 
                    = tb_top_tang__DOT__dut__DOT__sys__DOT__blk;
            }
        }
        tb_top_tang__DOT__dut__DOT__sys__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__cur_lw))))) {
            tb_top_tang__DOT__dut__DOT__sys__DOT__bbase 
                = (1U & (~ ((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__blk) 
                            - (IData)(1U))));
            if (((2U >= ((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__bbase) 
                         + (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slice_busy 
                              >> (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__gmask__2__w 
                                        = tb_top_tang__DOT__dut__DOT__sys__DOT__blk;
                                    vlSelf->__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__gmask__2__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__gmask__2__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__gmask__2__Vfuncout))))) {
                tb_top_tang__DOT__dut__DOT__sys__DOT__bsz 
                    = tb_top_tang__DOT__dut__DOT__sys__DOT__blk;
            }
        }
        tb_top_tang__DOT__dut__DOT__sys__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__cur_lw))))) {
            tb_top_tang__DOT__dut__DOT__sys__DOT__bbase 
                = (1U & (~ ((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__blk) 
                            - (IData)(1U))));
            if (((2U >= ((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__bbase) 
                         + (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slice_busy 
                              >> (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__gmask__2__w 
                                        = tb_top_tang__DOT__dut__DOT__sys__DOT__blk;
                                    vlSelf->__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__gmask__2__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__gmask__2__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__gmask__2__Vfuncout))))) {
                tb_top_tang__DOT__dut__DOT__sys__DOT__bsz 
                    = tb_top_tang__DOT__dut__DOT__sys__DOT__blk;
            }
        }
        tb_top_tang__DOT__dut__DOT__sys__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__cur_lw))))) {
            tb_top_tang__DOT__dut__DOT__sys__DOT__bbase 
                = (1U & (~ ((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__blk) 
                            - (IData)(1U))));
            if (((2U >= ((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__bbase) 
                         + (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slice_busy 
                              >> (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__gmask__2__w 
                                        = tb_top_tang__DOT__dut__DOT__sys__DOT__blk;
                                    vlSelf->__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__gmask__2__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__gmask__2__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__gmask__2__Vfuncout))))) {
                tb_top_tang__DOT__dut__DOT__sys__DOT__bsz 
                    = tb_top_tang__DOT__dut__DOT__sys__DOT__blk;
            }
        }
        tb_top_tang__DOT__dut__DOT__sys__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__cur_lw))))) {
            tb_top_tang__DOT__dut__DOT__sys__DOT__bbase 
                = (1U & (~ ((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__blk) 
                            - (IData)(1U))));
            if (((2U >= ((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__bbase) 
                         + (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slice_busy 
                              >> (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__gmask__2__w 
                                        = tb_top_tang__DOT__dut__DOT__sys__DOT__blk;
                                    vlSelf->__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__gmask__2__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__gmask__2__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__gmask__2__Vfuncout))))) {
                tb_top_tang__DOT__dut__DOT__sys__DOT__bsz 
                    = tb_top_tang__DOT__dut__DOT__sys__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__fit_found)) 
                   | ((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__bsz) 
                      < (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__best_sz))))) {
            vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__fit_found = 1U;
            vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__fit_base = 1U;
            tb_top_tang__DOT__dut__DOT__sys__DOT__best_sz 
                = tb_top_tang__DOT__dut__DOT__sys__DOT__bsz;
        }
    }
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__row_any 
        = ((0xfffcU & (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__row_any)) 
           | (((IData)((0U != (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__req_tab[0U] 
                               >> 0x10U))) << 1U) | 
              (0U != (0xffffU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__req_tab[0U]))));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__row_any 
        = ((0xfff3U & (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__row_any)) 
           | ((((IData)((0U != (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__req_tab[1U] 
                                >> 0x10U))) << 1U) 
               | (0U != (0xffffU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__req_tab[1U]))) 
              << 2U));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__row_any 
        = ((0xffcfU & (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__row_any)) 
           | ((((IData)((0U != (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__req_tab[2U] 
                                >> 0x10U))) << 1U) 
               | (0U != (0xffffU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__req_tab[2U]))) 
              << 4U));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__row_any 
        = ((0xff3fU & (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__row_any)) 
           | ((((IData)((0U != (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__req_tab[3U] 
                                >> 0x10U))) << 1U) 
               | (0U != (0xffffU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__req_tab[3U]))) 
              << 6U));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__row_any 
        = ((0xfcffU & (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__row_any)) 
           | ((((IData)((0U != (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__req_tab[4U] 
                                >> 0x10U))) << 1U) 
               | (0U != (0xffffU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__req_tab[4U]))) 
              << 8U));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__row_any 
        = ((0xf3ffU & (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__row_any)) 
           | ((((IData)((0U != (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__req_tab[5U] 
                                >> 0x10U))) << 1U) 
               | (0U != (0xffffU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__req_tab[5U]))) 
              << 0xaU));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__row_any 
        = ((0xcfffU & (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__row_any)) 
           | ((((IData)((0U != (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__req_tab[6U] 
                                >> 0x10U))) << 1U) 
               | (0U != (0xffffU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__req_tab[6U]))) 
              << 0xcU));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__row_any 
        = ((0x3fffU & (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__row_any)) 
           | ((((IData)((0U != (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__req_tab[7U] 
                                >> 0x10U))) << 1U) 
               | (0U != (0xffffU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__req_tab[7U]))) 
              << 0xeU));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__w_found 
        = (0U != (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__row_any));
    __Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__3__x 
        = vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__row_any;
    tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__Vstatic__b3 
        = (1U & (~ (IData)((0U != (0xffU & (IData)(__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__3__x))))));
    tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__Vstatic__x8 
        = (0xffU & ((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__Vstatic__b3)
                     ? ((IData)(__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__3__x) 
                        >> 8U) : (IData)(__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__3__x)));
    tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__Vstatic__b2 
        = (1U & (~ (IData)((0U != (0xfU & (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__Vstatic__x8))))));
    tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__Vstatic__x4 
        = (0xfU & ((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__Vstatic__b2)
                    ? ((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__Vstatic__x8) 
                       >> 4U) : (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__Vstatic__x8)));
    tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__Vstatic__b1 
        = (1U & (~ (IData)((0U != (3U & (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__Vstatic__x4))))));
    tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__Vstatic__x2 
        = (3U & ((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__Vstatic__b1)
                  ? ((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__Vstatic__x4) 
                     >> 2U) : (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__Vstatic__x4)));
    __Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__3__Vfuncout 
        = (((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__Vstatic__b3) 
            << 3U) | (((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__Vstatic__b2) 
                       << 2U) | (((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__Vstatic__b1) 
                                  << 1U) | (1U & (~ (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__Vstatic__x2))))));
    tb_top_tang__DOT__dut__DOT__sys__DOT__w_row = __Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__3__Vfuncout;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__w_id 
        = (((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__w_row) 
            << 4U) | ([&]() {
                vlSelf->__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__4__x 
                    = (0xffffU & (((0U == (0x1fU & 
                                           VL_SHIFTL_III(8,32,32, (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__w_row), 4U)))
                                    ? 0U : (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__req_tab[
                                            (((IData)(0xfU) 
                                              + (0xffU 
                                                 & VL_SHIFTL_III(8,32,32, (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__w_row), 4U))) 
                                             >> 5U)] 
                                            << ((IData)(0x20U) 
                                                - (0x1fU 
                                                   & VL_SHIFTL_III(8,32,32, (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__w_row), 4U))))) 
                                  | (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__req_tab[
                                     (7U & (VL_SHIFTL_III(8,32,32, (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__w_row), 4U) 
                                            >> 5U))] 
                                     >> (0x1fU & VL_SHIFTL_III(8,32,32, (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__w_row), 4U)))));
                tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__Vstatic__b3 
                    = (1U & (~ (IData)((0U != (0xffU 
                                               & (IData)(vlSelf->__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__4__x))))));
                tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__Vstatic__x8 
                    = (0xffU & ((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__Vstatic__b3)
                                 ? ((IData)(vlSelf->__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__4__x) 
                                    >> 8U) : (IData)(vlSelf->__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__4__x)));
                tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__Vstatic__b2 
                    = (1U & (~ (IData)((0U != (0xfU 
                                               & (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__Vstatic__x8))))));
                tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__Vstatic__x4 
                    = (0xfU & ((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__Vstatic__b2)
                                ? ((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__Vstatic__x8) 
                                   >> 4U) : (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__Vstatic__x8)));
                tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__Vstatic__b1 
                    = (1U & (~ (IData)((0U != (3U & (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__Vstatic__x4))))));
                tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__Vstatic__x2 
                    = (3U & ((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__Vstatic__b1)
                              ? ((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__Vstatic__x4) 
                                 >> 2U) : (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__Vstatic__x4)));
                vlSelf->__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__4__Vfuncout 
                    = (((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__Vstatic__b3) 
                        << 3U) | (((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__Vstatic__b2) 
                                   << 2U) | (((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__Vstatic__b1) 
                                              << 1U) 
                                             | (1U 
                                                & (~ (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__Vstatic__x2))))));
            }(), (IData)(vlSelf->__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__4__Vfuncout)));
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT____VdfgTmp_h933689ae__0 
        = (0x1fU & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__shamt_w 
                    & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__lw_r))) 
                       - (IData)(1U))));
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT____VdfgTmp_h933689ae__0 
        = (0x1fU & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__shamt_w 
                    & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__lw_r))) 
                       - (IData)(1U))));
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT____VdfgTmp_h2cd83c5b__0 
        = ((0x37U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir)) 
           | (0x17U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir)));
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT____VdfgTmp_h2cd83c5b__0 
        = ((0x37U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir)) 
           | (0x17U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir)));
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dko 
        = (0x1fU & ((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__k) 
                    << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__lw_r)));
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dko 
        = (0x1fU & ((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__k) 
                    << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__lw_r)));
    __Vtableidx1 = (((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__f_eq) 
                     << 5U) | (((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__f_lt) 
                                << 4U) | (((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__f_ltu) 
                                           << 3U) | 
                                          (7U & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir 
                                                 >> 0xcU)))));
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__cond 
        = Vtb_top_tang__ConstPool__TABLE_h2a0441a0_0
        [__Vtableidx1];
    __Vtableidx2 = (((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__f_eq) 
                     << 5U) | (((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__f_lt) 
                                << 4U) | (((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__f_ltu) 
                                           << 3U) | 
                                          (7U & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir 
                                                 >> 0xcU)))));
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__cond 
        = Vtb_top_tang__ConstPool__TABLE_h2a0441a0_0
        [__Vtableidx2];
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT____VdfgTmp_hd9b60348__0 
        = ((2U == (7U & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir 
                         >> 0xcU))) | (3U == (7U & 
                                              (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir 
                                               >> 0xcU))));
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT____VdfgTmp_hd9b60348__0 
        = ((2U == (7U & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir 
                         >> 0xcU))) | (3U == (7U & 
                                              (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir 
                                               >> 0xcU))));
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT____VdfgTmp_h18c46dac__0 
        = ((0x13U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir)) 
           | (0x33U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir)));
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT____VdfgTmp_h18c46dac__0 
        = ((0x13U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir)) 
           | (0x33U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir)));
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__qs 
        = (0x1fU & ((0x1fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__shamt_w) 
                    >> (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__lw_r)));
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__qs 
        = (0x1fU & ((0x1fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__shamt_w) 
                    >> (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__lw_r)));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__mask 
        = ((5U == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__lw_r))
            ? 0xffffffffU : (VL_SHIFTL_III(32,32,6, (IData)(1U), 
                                           (0x3fU & 
                                            ((IData)(1U) 
                                             << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__lw_r)))) 
                             - (IData)(1U)));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__mask 
        = ((5U == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__lw_r))
            ? 0xffffffffU : (VL_SHIFTL_III(32,32,6, (IData)(1U), 
                                           (0x3fU & 
                                            ((IData)(1U) 
                                             << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__lw_r)))) 
                             - (IData)(1U)));
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT____VdfgTmp_he83b8d53__0 
        = ((1U == (7U & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir 
                         >> 0xcU))) | (5U == (7U & 
                                              (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir 
                                               >> 0xcU))));
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT____VdfgTmp_he83b8d53__0 
        = ((1U == (7U & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir 
                         >> 0xcU))) | (5U == (7U & 
                                              (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir 
                                               >> 0xcU))));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__bhead 
        = vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__qk
        [(0xffU & (VL_SHIFTL_III(8,8,32, (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__hb), 4U) 
                   + (0xfU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__krd
                      [vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__hb])))];
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__pc_rot 
        = (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT____VdfgTmp_he4828306__0 
           | VL_SHIFTL_III(32,32,6, vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__pc, 
                           (0x3fU & ((IData)(0x20U) 
                                     - ((IData)(1U) 
                                        << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__lw_r))))));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__pc_rot 
        = (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT____VdfgTmp_he4828306__0 
           | VL_SHIFTL_III(32,32,6, vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__pc, 
                           (0x3fU & ((IData)(0x20U) 
                                     - ((IData)(1U) 
                                        << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__lw_r))))));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__imm 
        = ((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT____VdfgTmp_h2cd83c5b__0)
            ? (0xfffff000U & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir)
            : ((0x6fU == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir))
                ? (((- (IData)((vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir 
                                >> 0x1fU))) << 0x15U) 
                   | ((0x100000U & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir 
                                    >> 0xbU)) | ((0xff000U 
                                                  & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir) 
                                                 | ((0x800U 
                                                     & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir 
                                                        >> 9U)) 
                                                    | (0x7feU 
                                                       & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir 
                                                          >> 0x14U))))))
                : ((0x63U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir))
                    ? (((- (IData)((vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir 
                                    >> 0x1fU))) << 0xdU) 
                       | ((0x1000U & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir 
                                      >> 0x13U)) | 
                          ((0x800U & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir 
                                      << 4U)) | ((0x7e0U 
                                                  & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir 
                                                     >> 0x14U)) 
                                                 | (0x1eU 
                                                    & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir 
                                                       >> 7U))))))
                    : ((0x23U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir))
                        ? (((- (IData)((vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir 
                                        >> 0x1fU))) 
                            << 0xcU) | ((0xfe0U & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir 
                                                   >> 0x14U)) 
                                        | (0x1fU & 
                                           (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir 
                                            >> 7U))))
                        : (((- (IData)((vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir 
                                        >> 0x1fU))) 
                            << 0xcU) | (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir 
                                        >> 0x14U))))));
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT____VdfgExtracted_h62388771__0 
        = ((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT____VdfgTmp_h2cd83c5b__0) 
           | (0x6fU == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir)));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__imm 
        = ((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT____VdfgTmp_h2cd83c5b__0)
            ? (0xfffff000U & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir)
            : ((0x6fU == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir))
                ? (((- (IData)((vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir 
                                >> 0x1fU))) << 0x15U) 
                   | ((0x100000U & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir 
                                    >> 0xbU)) | ((0xff000U 
                                                  & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir) 
                                                 | ((0x800U 
                                                     & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir 
                                                        >> 9U)) 
                                                    | (0x7feU 
                                                       & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir 
                                                          >> 0x14U))))))
                : ((0x63U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir))
                    ? (((- (IData)((vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir 
                                    >> 0x1fU))) << 0xdU) 
                       | ((0x1000U & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir 
                                      >> 0x13U)) | 
                          ((0x800U & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir 
                                      << 4U)) | ((0x7e0U 
                                                  & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir 
                                                     >> 0x14U)) 
                                                 | (0x1eU 
                                                    & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir 
                                                       >> 7U))))))
                    : ((0x23U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir))
                        ? (((- (IData)((vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir 
                                        >> 0x1fU))) 
                            << 0xcU) | ((0xfe0U & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir 
                                                   >> 0x14U)) 
                                        | (0x1fU & 
                                           (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir 
                                            >> 7U))))
                        : (((- (IData)((vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir 
                                        >> 0x1fU))) 
                            << 0xcU) | (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir 
                                        >> 0x14U))))));
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT____VdfgExtracted_h62388771__0 
        = ((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT____VdfgTmp_h2cd83c5b__0) 
           | (0x6fU == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir)));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__ren 
        = (tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__mk 
           << (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dko));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__ren 
        = (tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__mk 
           << (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dko));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__is_cmp 
        = ((0x63U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir)) 
           | ((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT____VdfgTmp_h18c46dac__0) 
              & (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT____VdfgTmp_hd9b60348__0)));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__is_cmp 
        = ((0x63U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir)) 
           | ((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT____VdfgTmp_h18c46dac__0) 
              & (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT____VdfgTmp_hd9b60348__0)));
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__pc_d 
        = (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__pc 
           & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__mask);
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__imm_d 
        = (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__imm_sr 
           & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__mask);
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__c4_d 
        = (VL_SHIFTR_III(32,32,6, 4U, (0x3fU & ((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__k) 
                                                * (0x3fU 
                                                   & ((IData)(1U) 
                                                      << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__lw_r)))))) 
           & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__mask);
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__pc_d 
        = (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__pc 
           & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__mask);
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__imm_d 
        = (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__imm_sr 
           & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__mask);
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__c4_d 
        = (VL_SHIFTR_III(32,32,6, 4U, (0x3fU & ((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__k) 
                                                * (0x3fU 
                                                   & ((IData)(1U) 
                                                      << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__lw_r)))))) 
           & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__mask);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__sh_i 
        = ((0x13U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir)) 
           & (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT____VdfgTmp_he83b8d53__0));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__sh_i 
        = ((0x13U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir)) 
           & (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT____VdfgTmp_he83b8d53__0));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__bad 
        = (1U & ((~ ((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT____VdfgExtracted_h62388771__0) 
                     | ((0x67U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir)) 
                        | ((0x63U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir)) 
                           | ((3U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir)) 
                              | ((0x23U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir)) 
                                 | ((0x13U == (0x7fU 
                                               & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir)) 
                                    | ((0x33U == (0x7fU 
                                                  & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir)) 
                                       | (0x73U == 
                                          (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir)))))))))) 
                 | (((0x67U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir)) 
                     & (0U != (7U & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir 
                                     >> 0xcU)))) | 
                    (((0x63U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir)) 
                      & (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT____VdfgTmp_hd9b60348__0)) 
                     | ((((3U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir)) 
                          | (0x23U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir))) 
                         & (2U != (7U & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir 
                                         >> 0xcU)))) 
                        | ((IData)(((0x1013U == (0x707fU 
                                                 & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir)) 
                                    & (0U != (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir 
                                              >> 0x19U)))) 
                           | ((IData)(((0x5013U == 
                                        (0x707fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir)) 
                                       & ((0U != (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir 
                                                  >> 0x19U)) 
                                          & (0x20U 
                                             != (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir 
                                                 >> 0x19U))))) 
                              | ((0x33U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir)) 
                                 & ((~ ((0x20U == (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir 
                                                   >> 0x19U)) 
                                        & ((0U == (7U 
                                                   & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir 
                                                      >> 0xcU))) 
                                           | (5U == 
                                              (7U & 
                                               (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir 
                                                >> 0xcU)))))) 
                                    & (0U != (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir 
                                              >> 0x19U)))))))))));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__bad 
        = (1U & ((~ ((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT____VdfgExtracted_h62388771__0) 
                     | ((0x67U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir)) 
                        | ((0x63U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir)) 
                           | ((3U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir)) 
                              | ((0x23U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir)) 
                                 | ((0x13U == (0x7fU 
                                               & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir)) 
                                    | ((0x33U == (0x7fU 
                                                  & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir)) 
                                       | (0x73U == 
                                          (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir)))))))))) 
                 | (((0x67U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir)) 
                     & (0U != (7U & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir 
                                     >> 0xcU)))) | 
                    (((0x63U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir)) 
                      & (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT____VdfgTmp_hd9b60348__0)) 
                     | ((((3U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir)) 
                          | (0x23U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir))) 
                         & (2U != (7U & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir 
                                         >> 0xcU)))) 
                        | ((IData)(((0x1013U == (0x707fU 
                                                 & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir)) 
                                    & (0U != (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir 
                                              >> 0x19U)))) 
                           | ((IData)(((0x5013U == 
                                        (0x707fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir)) 
                                       & ((0U != (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir 
                                                  >> 0x19U)) 
                                          & (0x20U 
                                             != (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir 
                                                 >> 0x19U))))) 
                              | ((0x33U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir)) 
                                 & ((~ ((0x20U == (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir 
                                                   >> 0x19U)) 
                                        & ((0U == (7U 
                                                   & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir 
                                                      >> 0xcU))) 
                                           | (5U == 
                                              (7U & 
                                               (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir 
                                                >> 0xcU)))))) 
                                    & (0U != (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir 
                                              >> 0x19U)))))))))));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__is_slt 
        = ((0x63U != (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir)) 
           & (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__is_cmp));
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__inv = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__is_slt 
        = ((0x63U != (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir)) 
           & (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__is_cmp));
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__inv = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__is_shift 
        = ((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__sh_i) 
           | ((0x33U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir)) 
              & (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT____VdfgTmp_he83b8d53__0)));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__is_shift 
        = ((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__sh_i) 
           | ((0x33U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir)) 
              & (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT____VdfgTmp_he83b8d53__0)));
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__we = 0U;
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__fill 
        = (((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__is_shift) 
            & (IData)(((0x40005000U == (0x40007000U 
                                        & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir)) 
                       & (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__sgn))))
            ? vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__mask
            : 0U);
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__shx 
        = ((3U == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__state)) 
           & (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__is_shift));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__is_sll 
        = ((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__is_shift) 
           & (0x1000U == (0x7000U & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir)));
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__we = 0U;
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__fill 
        = (((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__is_shift) 
            & (IData)(((0x40005000U == (0x40007000U 
                                        & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir)) 
                       & (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__sgn))))
            ? vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__mask
            : 0U);
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__shx 
        = ((3U == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__state)) 
           & (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__is_shift));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__is_sll 
        = ((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__is_shift) 
           & (0x1000U == (0x7000U & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir)));
    if ((3U == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__state))) {
        if ((0x37U != (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir))) {
                if ((0x6fU != (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir))) {
                    if (((IData)((0x40000033U == (0x4000707fU 
                                                  & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir))) 
                         | (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__is_cmp))) {
                        tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__inv = 1U;
                    }
                }
            }
        }
        if (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__is_shift) {
            tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__we = 1U;
        } else if (tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT____VdfgExtracted_h62388771__0) {
            tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__we = 1U;
        } else if (((~ (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__is_cmp)) 
                    & (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT____VdfgTmp_h18c46dac__0))) {
            tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__we = 1U;
        }
    } else if ((4U == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__state))) {
        if ((3U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir))) {
            tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__we = 1U;
        } else if (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__is_slt) {
            tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__we = 1U;
        } else if ((0x67U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir))) {
            tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__we = 1U;
        }
    }
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__rwe 
        = ((~ ((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__halted_r) 
               | (0U == (0x1fU & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir 
                                  >> 7U))))) & (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__we));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT____Vcellinp__slot__BRA__0__KET____DOT__rfb__ra 
        = (0x1fU & ((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__shx)
                     ? (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir 
                        >> 0xfU) : (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir 
                                    >> 0x14U)));
    if (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__is_sll) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__exec_done 
            = (0U == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__k));
        tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ia 
            = (0x1ffU & ((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__k) 
                         - (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__qs)));
        tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT____VdfgTmp_h41a48239__0 
            = ((VL_EXTENDS_II(32,9, (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__k)) 
                - VL_EXTENDS_II(32,9, (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__qs))) 
               - (IData)(1U));
    } else {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__exec_done 
            = vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__last_up;
        tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ia 
            = (0x1ffU & ((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__k) 
                         + (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__qs)));
        tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT____VdfgTmp_h41a48239__0 
            = ((IData)(1U) + (VL_EXTENDS_II(32,9, (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__k)) 
                              + VL_EXTENDS_II(32,9, (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__qs))));
    }
    if ((3U == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__state))) {
        if ((0x37U != (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir))) {
                if ((0x6fU != (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir))) {
                    if (((IData)((0x40000033U == (0x4000707fU 
                                                  & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir))) 
                         | (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__is_cmp))) {
                        tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__inv = 1U;
                    }
                }
            }
        }
        if (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__is_shift) {
            tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__we = 1U;
        } else if (tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT____VdfgExtracted_h62388771__0) {
            tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__we = 1U;
        } else if (((~ (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__is_cmp)) 
                    & (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT____VdfgTmp_h18c46dac__0))) {
            tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__we = 1U;
        }
    } else if ((4U == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__state))) {
        if ((3U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir))) {
            tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__we = 1U;
        } else if (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__is_slt) {
            tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__we = 1U;
        } else if ((0x67U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir))) {
            tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__we = 1U;
        }
    }
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__rwe 
        = ((~ ((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__halted_r) 
               | (0U == (0x1fU & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir 
                                  >> 7U))))) & (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__we));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT____Vcellinp__slot__BRA__1__KET____DOT__rfb__ra 
        = (0x1fU & ((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__shx)
                     ? (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir 
                        >> 0xfU) : (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir 
                                    >> 0x14U)));
    if (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__is_sll) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__exec_done 
            = (0U == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__k));
        tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ia 
            = (0x1ffU & ((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__k) 
                         - (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__qs)));
        tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT____VdfgTmp_h41a48239__0 
            = ((VL_EXTENDS_II(32,9, (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__k)) 
                - VL_EXTENDS_II(32,9, (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__qs))) 
               - (IData)(1U));
    } else {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__exec_done 
            = vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__last_up;
        tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ia 
            = (0x1ffU & ((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__k) 
                         + (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__qs)));
        tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT____VdfgTmp_h41a48239__0 
            = ((IData)(1U) + (VL_EXTENDS_II(32,9, (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__k)) 
                              + VL_EXTENDS_II(32,9, (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__qs))));
    }
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT____Vcellinp__slot__BRA__0__KET____DOT__rfa__we 
        = ((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__cph) 
           & (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__rwe));
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__va 
        = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ia))) 
           & VL_LTES_III(9, (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ia), 
                         (0x1ffU & ((0x3fU & (0x20U 
                                              >> (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__lw_r))) 
                                    - (IData)(1U)))));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__a_val 
        = ((0U == (0x1fU & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir 
                            >> 0xfU))) ? 0U : ((vlSymsp->TOP__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__rfa.rq 
                                                >> 
                                                (0x1fU 
                                                 & (((2U 
                                                      == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__state))
                                                      ? 
                                                     ((0x3fU 
                                                       & (0x20U 
                                                          >> (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__lw_r))) 
                                                      - (IData)(1U))
                                                      : 
                                                     ((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__shx)
                                                       ? (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ia)
                                                       : (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__k))) 
                                                    << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__lw_r)))) 
                                               & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__mask));
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__vb 
        = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, 
                                             (0x1ffU 
                                              & tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT____VdfgTmp_h41a48239__0))) 
           & VL_LTES_III(9, (0x1ffU & tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT____VdfgTmp_h41a48239__0), 
                         (0x1ffU & ((0x3fU & (0x20U 
                                              >> (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__lw_r))) 
                                    - (IData)(1U)))));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dwd 
        = (((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__shx)
             ? (0U == (0x1fU & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir 
                                >> 0xfU))) : (0U == 
                                              (0x1fU 
                                               & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir 
                                                  >> 0x14U))))
            ? 0U : ((vlSymsp->TOP__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__rfb.rq 
                     >> (0x1fU & (((2U == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__state))
                                    ? (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__j)
                                    : ((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__shx)
                                        ? tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT____VdfgTmp_h41a48239__0
                                        : (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__k))) 
                                  << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__lw_r)))) 
                    & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__mask));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT____Vcellinp__slot__BRA__1__KET____DOT__rfa__we 
        = ((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__cph) 
           & (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__rwe));
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__va 
        = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ia))) 
           & VL_LTES_III(9, (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ia), 
                         (0x1ffU & ((0x3fU & (0x20U 
                                              >> (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__lw_r))) 
                                    - (IData)(1U)))));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__a_val 
        = ((0U == (0x1fU & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir 
                            >> 0xfU))) ? 0U : ((vlSymsp->TOP__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__rfa.rq 
                                                >> 
                                                (0x1fU 
                                                 & (((2U 
                                                      == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__state))
                                                      ? 
                                                     ((0x3fU 
                                                       & (0x20U 
                                                          >> (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__lw_r))) 
                                                      - (IData)(1U))
                                                      : 
                                                     ((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__shx)
                                                       ? (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ia)
                                                       : (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__k))) 
                                                    << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__lw_r)))) 
                                               & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__mask));
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__vb 
        = (VL_LTES_III(32, 0U, VL_EXTENDS_II(32,9, 
                                             (0x1ffU 
                                              & tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT____VdfgTmp_h41a48239__0))) 
           & VL_LTES_III(9, (0x1ffU & tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT____VdfgTmp_h41a48239__0), 
                         (0x1ffU & ((0x3fU & (0x20U 
                                              >> (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__lw_r))) 
                                    - (IData)(1U)))));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dwd 
        = (((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__shx)
             ? (0U == (0x1fU & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir 
                                >> 0xfU))) : (0U == 
                                              (0x1fU 
                                               & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir 
                                                  >> 0x14U))))
            ? 0U : ((vlSymsp->TOP__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__rfb.rq 
                     >> (0x1fU & (((2U == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__state))
                                    ? (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__j)
                                    : ((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__shx)
                                        ? tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT____VdfgTmp_h41a48239__0
                                        : (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__k))) 
                                  << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__lw_r)))) 
                    & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__mask));
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__X 
        = vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__a_val;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__ddat 
        = ((vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dwd 
            & tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__mk) 
           << (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dko));
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__Yr 
        = (((0x33U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir)) 
            | (0x63U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir)))
            ? vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dwd
            : tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__imm_d);
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__X 
        = vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__a_val;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__ddat 
        = ((vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dwd 
            & tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__mk) 
           << (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dko));
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__Yr 
        = (((0x33U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir)) 
            | (0x63U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir)))
            ? vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dwd
            : tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__imm_d);
    if ((3U == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__state))) {
        if ((0x37U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir))) {
            tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__X = 0U;
        } else if ((0x17U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir))) {
            tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__X 
                = tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__pc_d;
        } else if ((0x6fU == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir))) {
            tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__X 
                = tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__pc_d;
        }
    } else if ((4U == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__state))) {
        tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__X 
            = tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__pc_d;
    } else if ((5U == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__state))) {
        tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__X 
            = tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__pc_d;
    }
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__xsh 
        = VL_SHIFTR_III(32,32,6, tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__X, 
                        (0x3fU & (((IData)(1U) << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__lw_r)) 
                                  - (IData)(1U))));
    if ((3U == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__state))) {
        if ((0x37U != (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir))) {
                if ((0x6fU == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir))) {
                    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__Yr 
                        = tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__c4_d;
                }
            }
        }
    } else if ((4U == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__state))) {
        tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__Yr 
            = tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__c4_d;
    } else if ((5U == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__state))) {
        tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__Yr 
            = (((0x6fU == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir)) 
                | ((0x63U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir)) 
                   & (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__cond)))
                ? tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__imm_d
                : tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__c4_d);
    }
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ysh 
        = VL_SHIFTR_III(32,32,6, tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__Yr, 
                        (0x3fU & (((IData)(1U) << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__lw_r)) 
                                  - (IData)(1U))));
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__sum_full 
        = (0x1ffffffffULL & ((QData)((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__X)) 
                             + ((QData)((IData)(((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__inv)
                                                  ? 
                                                 ((~ tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__Yr) 
                                                  & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__mask)
                                                  : tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__Yr))) 
                                + (QData)((IData)((
                                                   (0U 
                                                    == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__k))
                                                    ? (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__inv)
                                                    : (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__cy)))))));
    if ((3U == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__state))) {
        if ((0x37U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir))) {
            tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__X = 0U;
        } else if ((0x17U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir))) {
            tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__X 
                = tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__pc_d;
        } else if ((0x6fU == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir))) {
            tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__X 
                = tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__pc_d;
        }
    } else if ((4U == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__state))) {
        tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__X 
            = tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__pc_d;
    } else if ((5U == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__state))) {
        tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__X 
            = tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__pc_d;
    }
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__xsh 
        = VL_SHIFTR_III(32,32,6, tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__X, 
                        (0x3fU & (((IData)(1U) << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__lw_r)) 
                                  - (IData)(1U))));
    if ((3U == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__state))) {
        if ((0x37U != (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir))) {
            if ((0x17U != (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir))) {
                if ((0x6fU == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir))) {
                    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__Yr 
                        = tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__c4_d;
                }
            }
        }
    } else if ((4U == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__state))) {
        tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__Yr 
            = tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__c4_d;
    } else if ((5U == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__state))) {
        tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__Yr 
            = (((0x6fU == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir)) 
                | ((0x63U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir)) 
                   & (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__cond)))
                ? tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__imm_d
                : tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__c4_d);
    }
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ysh 
        = VL_SHIFTR_III(32,32,6, tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__Yr, 
                        (0x3fU & (((IData)(1U) << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__lw_r)) 
                                  - (IData)(1U))));
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__sum_full 
        = (0x1ffffffffULL & ((QData)((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__X)) 
                             + ((QData)((IData)(((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__inv)
                                                  ? 
                                                 ((~ tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__Yr) 
                                                  & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__mask)
                                                  : tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__Yr))) 
                                + (QData)((IData)((
                                                   (0U 
                                                    == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__k))
                                                    ? (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__inv)
                                                    : (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__cy)))))));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__cout 
        = (1U & (IData)((0x1ffffffffULL & (tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__sum_full 
                                           >> (0x3fU 
                                               & ((IData)(1U) 
                                                  << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__lw_r)))))));
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__sum_d 
        = ((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__sum_full) 
           & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__mask);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__cout 
        = (1U & (IData)((0x1ffffffffULL & (tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__sum_full 
                                           >> (0x3fU 
                                               & ((IData)(1U) 
                                                  << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__lw_r)))))));
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__sum_d 
        = ((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__sum_full) 
           & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__mask);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__nz_n 
        = (((0U != (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__k)) 
            & (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__nz)) 
           | (0U != tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__sum_d));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT____VdfgTmp_h7980eff3__0 
        = VL_SHIFTL_III(32,32,6, tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__sum_d, 
                        (0x3fU & ((IData)(0x20U) - 
                                  ((IData)(1U) << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__lw_r)))));
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__wd 
        = (((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT____VdfgTmp_h18c46dac__0) 
            & ((4U == (7U & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir 
                             >> 0xcU))) | ((6U == (7U 
                                                   & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir 
                                                      >> 0xcU))) 
                                           | (7U == 
                                              (7U & 
                                               (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir 
                                                >> 0xcU))))))
            ? ((4U == (7U & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir 
                             >> 0xcU))) ? (tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__X 
                                           ^ tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__Yr)
                : ((6U == (7U & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir 
                                 >> 0xcU))) ? (tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__X 
                                               | tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__Yr)
                    : (tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__X 
                       & tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__Yr)))
            : tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__sum_d);
    if ((3U == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__state))) {
        if (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__is_shift) {
            tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__wd 
                = ((IData)(((((QData)((IData)(((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__is_sll)
                                                ? ((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__va)
                                                    ? vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__a_val
                                                    : 0U)
                                                : ((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__vb)
                                                    ? vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dwd
                                                    : tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__fill)))) 
                              << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__lw_r)))) 
                             | (QData)((IData)(((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__is_sll)
                                                 ? 
                                                ((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__vb)
                                                  ? vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dwd
                                                  : 0U)
                                                 : 
                                                ((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__va)
                                                  ? vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__a_val
                                                  : tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__fill))))) 
                            >> (0x3fU & ((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__is_sll)
                                          ? (((IData)(1U) 
                                              << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__lw_r)) 
                                             - (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT____VdfgTmp_h933689ae__0))
                                          : (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT____VdfgTmp_h933689ae__0))))) 
                   & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__mask);
        }
    } else if ((4U == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__state))) {
        if ((3U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir))) {
            tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__wd 
                = ((vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dq 
                    >> (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dko)) 
                   & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__mask);
        } else if (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__is_slt) {
            tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__wd = 0U;
            tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__wd 
                = ((0xfffffffeU & tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__wd) 
                   | ((0U == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__k)) 
                      & ((2U == (7U & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir 
                                       >> 0xcU))) ? (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__f_lt)
                          : (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__f_ltu))));
        } else if ((0x67U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir))) {
            tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__wd 
                = tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__sum_d;
        }
    }
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__nz_n 
        = (((0U != (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__k)) 
            & (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__nz)) 
           | (0U != tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__sum_d));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT____VdfgTmp_h7980eff3__0 
        = VL_SHIFTL_III(32,32,6, tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__sum_d, 
                        (0x3fU & ((IData)(0x20U) - 
                                  ((IData)(1U) << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__lw_r)))));
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__wd 
        = (((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT____VdfgTmp_h18c46dac__0) 
            & ((4U == (7U & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir 
                             >> 0xcU))) | ((6U == (7U 
                                                   & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir 
                                                      >> 0xcU))) 
                                           | (7U == 
                                              (7U & 
                                               (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir 
                                                >> 0xcU))))))
            ? ((4U == (7U & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir 
                             >> 0xcU))) ? (tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__X 
                                           ^ tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__Yr)
                : ((6U == (7U & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir 
                                 >> 0xcU))) ? (tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__X 
                                               | tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__Yr)
                    : (tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__X 
                       & tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__Yr)))
            : tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__sum_d);
    if ((3U == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__state))) {
        if (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__is_shift) {
            tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__wd 
                = ((IData)(((((QData)((IData)(((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__is_sll)
                                                ? ((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__va)
                                                    ? vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__a_val
                                                    : 0U)
                                                : ((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__vb)
                                                    ? vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dwd
                                                    : tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__fill)))) 
                              << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__lw_r)))) 
                             | (QData)((IData)(((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__is_sll)
                                                 ? 
                                                ((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__vb)
                                                  ? vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dwd
                                                  : 0U)
                                                 : 
                                                ((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__va)
                                                  ? vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__a_val
                                                  : tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__fill))))) 
                            >> (0x3fU & ((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__is_sll)
                                          ? (((IData)(1U) 
                                              << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__lw_r)) 
                                             - (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT____VdfgTmp_h933689ae__0))
                                          : (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT____VdfgTmp_h933689ae__0))))) 
                   & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__mask);
        }
    } else if ((4U == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__state))) {
        if ((3U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir))) {
            tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__wd 
                = ((vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dq 
                    >> (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dko)) 
                   & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__mask);
        } else if (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__is_slt) {
            tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__wd = 0U;
            tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__wd 
                = ((0xfffffffeU & tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__wd) 
                   | ((0U == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__k)) 
                      & ((2U == (7U & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir 
                                       >> 0xcU))) ? (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__f_lt)
                          : (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__f_ltu))));
        } else if ((0x67U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir))) {
            tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__wd 
                = tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__sum_d;
        }
    }
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__addr_ins 
        = (VL_SHIFTR_III(32,32,6, vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__addr, 
                         (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__lw_r)))) 
           | vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT____VdfgTmp_h7980eff3__0);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__rdat 
        = ((tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__wd 
            & tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__mk) 
           << (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dko));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__addr_ins 
        = (VL_SHIFTR_III(32,32,6, vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__addr, 
                         (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__lw_r)))) 
           | vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT____VdfgTmp_h7980eff3__0);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__rdat 
        = ((tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__wd 
            & tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__mk) 
           << (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dko));
}
