// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design implementation internals
// See Vtb_top_tang.h for the primary calling header

#include "Vtb_top_tang__pch.h"
#include "Vtb_top_tang__Syms.h"
#include "Vtb_top_tang___024root.h"

VL_ATTR_COLD void Vtb_top_tang___024root___eval_initial__TOP(Vtb_top_tang___024root* vlSelf);
VlCoroutine Vtb_top_tang___024root___eval_initial__TOP__Vtiming__0(Vtb_top_tang___024root* vlSelf);
VlCoroutine Vtb_top_tang___024root___eval_initial__TOP__Vtiming__1(Vtb_top_tang___024root* vlSelf);
VlCoroutine Vtb_top_tang___024root___eval_initial__TOP__Vtiming__2(Vtb_top_tang___024root* vlSelf);
VlCoroutine Vtb_top_tang___024root___eval_initial__TOP__Vtiming__3(Vtb_top_tang___024root* vlSelf);
void Vtb_top_tang_pk_ram___eval_initial__TOP__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__rfa(Vtb_top_tang_pk_ram* vlSelf);

void Vtb_top_tang___024root___eval_initial(Vtb_top_tang___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_top_tang__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtb_top_tang___024root___eval_initial\n"); );
    // Body
    Vtb_top_tang___024root___eval_initial__TOP(vlSelf);
    Vtb_top_tang___024root___eval_initial__TOP__Vtiming__0(vlSelf);
    Vtb_top_tang___024root___eval_initial__TOP__Vtiming__1(vlSelf);
    Vtb_top_tang___024root___eval_initial__TOP__Vtiming__2(vlSelf);
    Vtb_top_tang___024root___eval_initial__TOP__Vtiming__3(vlSelf);
    Vtb_top_tang_pk_ram___eval_initial__TOP__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__rfa((&vlSymsp->TOP__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__rfa));
    Vtb_top_tang_pk_ram___eval_initial__TOP__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__rfa((&vlSymsp->TOP__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__rfb));
    Vtb_top_tang_pk_ram___eval_initial__TOP__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__rfa((&vlSymsp->TOP__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__rfa));
    Vtb_top_tang_pk_ram___eval_initial__TOP__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__rfa((&vlSymsp->TOP__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__rfb));
    vlSelf->__Vtrigprevexpr___TOP__tb_top_tang__DOT__clk__0 
        = vlSelf->tb_top_tang__DOT__clk;
    vlSelf->__Vtrigprevexpr___TOP__tb_top_tang__DOT__tx__0 
        = vlSelf->tb_top_tang__DOT__tx;
}

#ifdef VL_DEBUG
VL_ATTR_COLD void Vtb_top_tang___024root___dump_triggers__act(Vtb_top_tang___024root* vlSelf);
#endif  // VL_DEBUG

void Vtb_top_tang___024root___eval_triggers__act(Vtb_top_tang___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_top_tang__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtb_top_tang___024root___eval_triggers__act\n"); );
    // Body
    vlSelf->__VactTriggered.set(0U, ((IData)(vlSelf->tb_top_tang__DOT__clk) 
                                     & (~ (IData)(vlSelf->__Vtrigprevexpr___TOP__tb_top_tang__DOT__clk__0))));
    vlSelf->__VactTriggered.set(1U, ((~ (IData)(vlSelf->tb_top_tang__DOT__tx)) 
                                     & (IData)(vlSelf->__Vtrigprevexpr___TOP__tb_top_tang__DOT__tx__0)));
    vlSelf->__VactTriggered.set(2U, vlSelf->__VdlySched.awaitingCurrentTime());
    vlSelf->__Vtrigprevexpr___TOP__tb_top_tang__DOT__clk__0 
        = vlSelf->tb_top_tang__DOT__clk;
    vlSelf->__Vtrigprevexpr___TOP__tb_top_tang__DOT__tx__0 
        = vlSelf->tb_top_tang__DOT__tx;
#ifdef VL_DEBUG
    if (VL_UNLIKELY(vlSymsp->_vm_contextp__->debug())) {
        Vtb_top_tang___024root___dump_triggers__act(vlSelf);
    }
#endif
}

extern const VlUnpacked<CData/*0:0*/, 64> Vtb_top_tang__ConstPool__TABLE_h2a0441a0_0;

VL_INLINE_OPT void Vtb_top_tang___024root___nba_sequent__TOP__1(Vtb_top_tang___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_top_tang__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtb_top_tang___024root___nba_sequent__TOP__1\n"); );
    // Init
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
    CData/*5:0*/ __Vtableidx1;
    __Vtableidx1 = 0;
    CData/*5:0*/ __Vtableidx2;
    __Vtableidx2 = 0;
    // Body
    if (vlSelf->tb_top_tang__DOT__dut__DOT__rst) {
        vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__state = 6U;
        vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__pc = 0U;
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir = 0U;
        vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__addr = 0U;
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__imm_sr = 0U;
        vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__shamt_w = 0U;
        vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__k = 0U;
        vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__j = 0U;
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__lw_r = 0U;
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__cy = 0U;
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__nz = 0U;
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__f_eq = 0U;
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__f_lt = 0U;
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__f_ltu = 0U;
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__sgn = 0U;
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__halted_r = 1U;
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__trap_r = 0U;
        vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__state = 6U;
        vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__pc = 0U;
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir = 0U;
        vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__addr = 0U;
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__imm_sr = 0U;
        vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__shamt_w = 0U;
        vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__k = 0U;
        vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__j = 0U;
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__lw_r = 0U;
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__cy = 0U;
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__nz = 0U;
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__f_eq = 0U;
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__f_lt = 0U;
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__f_ltu = 0U;
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__sgn = 0U;
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__halted_r = 1U;
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__trap_r = 0U;
    } else {
        if ((((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__cph) 
              & (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__pend)) 
             & (6U == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__state)))) {
            vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__pc 
                = vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__ent_q;
            vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__lw_r 
                = vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__lw_q;
            vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__k = 0U;
            vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__halted_r = 0U;
            vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__trap_r = 0U;
            vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__state = 0U;
        } else if (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__cph) {
            if ((4U & (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__state))) {
                if ((1U & (~ ((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__state) 
                              >> 1U)))) {
                    if ((1U & (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__state))) {
                        if ((0x67U == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__opc))) {
                            vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__pc 
                                = (0xfffffffeU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__addr);
                            vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__state = 0U;
                        } else {
                            vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__pc 
                                = (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT____VdfgTmp_he4828306__0 
                                   | vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT____VdfgTmp_h7980eff3__0);
                            vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__imm_sr 
                                = vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__imm_rot;
                            vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__cy 
                                = vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__cout;
                            if (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__last_up) {
                                vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__k = 0U;
                                vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__state = 0U;
                            } else {
                                vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__k 
                                    = (0x1fU & ((IData)(1U) 
                                                + (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__k)));
                            }
                        }
                    } else {
                        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__cy 
                            = vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__cout;
                        vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__pc 
                            = vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__pc_rot;
                        if (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__last_up) {
                            vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__k = 0U;
                            vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__state = 5U;
                        } else {
                            vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__k 
                                = (0x1fU & ((IData)(1U) 
                                            + (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__k)));
                        }
                    }
                }
            } else if ((2U & (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__state))) {
                if ((1U & (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__state))) {
                    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__cy 
                        = vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__cout;
                    if (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__is_cmp) {
                        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__nz 
                            = vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__nz_n;
                        if (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__last_up) {
                            vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__f_eq 
                                = (1U & (~ (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__nz_n)));
                            vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__f_ltu 
                                = (1U & (~ (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__cout)));
                            vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__f_lt 
                                = (1U & (((1U & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__xsh) 
                                          != (1U & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ysh))
                                          ? vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__xsh
                                          : (~ (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__cout))));
                        }
                    }
                    if ((((3U == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__opc)) 
                          | (0x23U == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__opc))) 
                         | (0x67U == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__opc)))) {
                        vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__addr 
                            = vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__addr_ins;
                    }
                    vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__pc 
                        = vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__pc_rot;
                    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__imm_sr 
                        = vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__imm_rot;
                    if (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__exec_done) {
                        vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__k = 0U;
                        vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__state 
                            = (((((3U == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__opc)) 
                                  | (0x23U == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__opc))) 
                                 | (0x67U == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__opc))) 
                                | (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__is_slt))
                                ? 4U : 5U);
                    } else {
                        vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__k 
                            = (0x1fU & ((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__is_sll)
                                         ? ((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__k) 
                                            - (IData)(1U))
                                         : ((IData)(1U) 
                                            + (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__k))));
                    }
                } else {
                    if ((0x33U == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__opc))) {
                        vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__shamt_w 
                            = ((vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__shamt_w 
                                & (~ VL_SHIFTL_III(32,32,6, vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__mask, (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__jw)))) 
                               | VL_SHIFTL_III(32,32,6, vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dwd, (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__jw)));
                    }
                    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__sgn 
                        = (1U & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__a_val 
                                 >> (0x1fU & (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__wm1))));
                    if (((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__j) 
                         == ((0x33U == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__opc))
                              ? (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__mlast)
                              : 0U))) {
                        vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__state = 3U;
                        vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__k 
                            = ((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__is_sll)
                                ? (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__kmax)
                                : 0U);
                    } else {
                        vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__j 
                            = (7U & ((IData)(1U) + (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__j)));
                    }
                }
            } else if ((1U & (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__state))) {
                vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__j = 0U;
                vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__imm_sr 
                    = vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__imm;
                vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__shamt_w 
                    = ((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__sh_i)
                        ? (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__rs2)
                        : 0U);
                if (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__bad) {
                    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__trap_r = 1U;
                    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__halted_r = 1U;
                    vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__state = 6U;
                } else if (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__is_sys) {
                    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__halted_r = 1U;
                    vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__state = 6U;
                } else if (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__is_shift) {
                    vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__state = 2U;
                } else {
                    vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__k = 0U;
                    vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__state = 3U;
                }
            } else {
                vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir 
                    = vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__id_q;
                vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__state = 1U;
            }
        }
        if ((((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__cph) 
              & (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__pend)) 
             & (6U == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__state)))) {
            vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__pc 
                = vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__ent_q;
            vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__lw_r 
                = vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__lw_q;
            vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__k = 0U;
            vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__halted_r = 0U;
            vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__trap_r = 0U;
            vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__state = 0U;
        } else if (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__cph) {
            if ((4U & (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__state))) {
                if ((1U & (~ ((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__state) 
                              >> 1U)))) {
                    if ((1U & (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__state))) {
                        if ((0x67U == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__opc))) {
                            vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__pc 
                                = (0xfffffffeU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__addr);
                            vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__state = 0U;
                        } else {
                            vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__pc 
                                = (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT____VdfgTmp_he4828306__0 
                                   | vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT____VdfgTmp_h7980eff3__0);
                            vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__imm_sr 
                                = vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__imm_rot;
                            vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__cy 
                                = vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__cout;
                            if (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__last_up) {
                                vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__k = 0U;
                                vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__state = 0U;
                            } else {
                                vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__k 
                                    = (0x1fU & ((IData)(1U) 
                                                + (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__k)));
                            }
                        }
                    } else {
                        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__cy 
                            = vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__cout;
                        vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__pc 
                            = vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__pc_rot;
                        if (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__last_up) {
                            vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__k = 0U;
                            vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__state = 5U;
                        } else {
                            vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__k 
                                = (0x1fU & ((IData)(1U) 
                                            + (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__k)));
                        }
                    }
                }
            } else if ((2U & (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__state))) {
                if ((1U & (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__state))) {
                    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__cy 
                        = vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__cout;
                    if (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__is_cmp) {
                        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__nz 
                            = vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__nz_n;
                        if (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__last_up) {
                            vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__f_eq 
                                = (1U & (~ (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__nz_n)));
                            vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__f_ltu 
                                = (1U & (~ (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__cout)));
                            vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__f_lt 
                                = (1U & (((1U & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__xsh) 
                                          != (1U & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ysh))
                                          ? vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__xsh
                                          : (~ (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__cout))));
                        }
                    }
                    if ((((3U == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__opc)) 
                          | (0x23U == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__opc))) 
                         | (0x67U == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__opc)))) {
                        vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__addr 
                            = vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__addr_ins;
                    }
                    vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__pc 
                        = vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__pc_rot;
                    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__imm_sr 
                        = vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__imm_rot;
                    if (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__exec_done) {
                        vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__k = 0U;
                        vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__state 
                            = (((((3U == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__opc)) 
                                  | (0x23U == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__opc))) 
                                 | (0x67U == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__opc))) 
                                | (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__is_slt))
                                ? 4U : 5U);
                    } else {
                        vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__k 
                            = (0x1fU & ((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__is_sll)
                                         ? ((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__k) 
                                            - (IData)(1U))
                                         : ((IData)(1U) 
                                            + (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__k))));
                    }
                } else {
                    if ((0x33U == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__opc))) {
                        vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__shamt_w 
                            = ((vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__shamt_w 
                                & (~ VL_SHIFTL_III(32,32,6, vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__mask, (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__jw)))) 
                               | VL_SHIFTL_III(32,32,6, vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dwd, (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__jw)));
                    }
                    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__sgn 
                        = (1U & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__a_val 
                                 >> (0x1fU & (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__wm1))));
                    if (((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__j) 
                         == ((0x33U == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__opc))
                              ? (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__mlast)
                              : 0U))) {
                        vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__state = 3U;
                        vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__k 
                            = ((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__is_sll)
                                ? (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__kmax)
                                : 0U);
                    } else {
                        vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__j 
                            = (7U & ((IData)(1U) + (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__j)));
                    }
                }
            } else if ((1U & (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__state))) {
                vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__j = 0U;
                vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__imm_sr 
                    = vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__imm;
                vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__shamt_w 
                    = ((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__sh_i)
                        ? (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__rs2)
                        : 0U);
                if (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__bad) {
                    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__trap_r = 1U;
                    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__halted_r = 1U;
                    vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__state = 6U;
                } else if (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__is_sys) {
                    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__halted_r = 1U;
                    vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__state = 6U;
                } else if (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__is_shift) {
                    vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__state = 2U;
                } else {
                    vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__k = 0U;
                    vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__state = 3U;
                }
            } else {
                vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir 
                    = vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__id_q;
                vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__state = 1U;
            }
        }
    }
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__ent_q 
        = vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__ent_q;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__lw_q 
        = vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__lw_q;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__pend 
        = vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__pend;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__addr 
        = vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__addr;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__j 
        = vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__j;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__shamt_w 
        = vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__shamt_w;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__state 
        = vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__state;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__k 
        = vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__k;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__ent_q 
        = vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__ent_q;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__lw_q 
        = vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__lw_q;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__pend 
        = vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__pend;
    vlSelf->tb_top_tang__DOT__dut__DOT__rst = ((0xffU 
                                                != (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__por)) 
                                               | (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__soft_rst));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__cph 
        = vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__cph;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__addr 
        = vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__addr;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__j 
        = vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__j;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__shamt_w 
        = vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__shamt_w;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__state 
        = vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__state;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__k 
        = vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__k;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__id_q 
        = vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__imem_s
        [(0x3fU & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__pc 
                   >> 2U))];
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
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__last_up 
        = ((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__k) 
           == (0x1fU & ((0x3fU & (0x20U >> (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__lw_r))) 
                        - (IData)(1U))));
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__mk 
        = ((0x20U == (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__lw_r))))
            ? 0xffffffffU : (VL_SHIFTL_III(32,32,6, (IData)(1U), 
                                           (0x3fU & 
                                            ((IData)(1U) 
                                             << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__lw_r)))) 
                             - (IData)(1U)));
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT____VdfgTmp_h933689ae__0 
        = (0x1fU & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__shamt_w 
                    & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__lw_r))) 
                       - (IData)(1U))));
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dko 
        = (0x1fU & ((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__k) 
                    << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__lw_r)));
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__qs 
        = (0x1fU & ((0x1fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__shamt_w) 
                    >> (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__lw_r)));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__mask 
        = ((5U == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__lw_r))
            ? 0xffffffffU : (VL_SHIFTL_III(32,32,6, (IData)(1U), 
                                           (0x3fU & 
                                            ((IData)(1U) 
                                             << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__lw_r)))) 
                             - (IData)(1U)));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__rs2 
        = (0x1fU & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir 
                    >> 0x14U));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__is_sys 
        = (0x73U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__opc 
        = (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir);
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT____VdfgTmp_h2cd83c5b__0 
        = ((0x37U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir)) 
           | (0x17U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir)));
    __Vtableidx1 = (((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__f_eq) 
                     << 5U) | (((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__f_lt) 
                                << 4U) | (((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__f_ltu) 
                                           << 3U) | 
                                          (7U & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir 
                                                 >> 0xcU)))));
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__cond 
        = Vtb_top_tang__ConstPool__TABLE_h2a0441a0_0
        [__Vtableidx1];
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT____VdfgTmp_hd9b60348__0 
        = ((2U == (7U & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir 
                         >> 0xcU))) | (3U == (7U & 
                                              (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir 
                                               >> 0xcU))));
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT____VdfgTmp_h18c46dac__0 
        = ((0x13U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir)) 
           | (0x33U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir)));
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT____VdfgTmp_he83b8d53__0 
        = ((1U == (7U & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir 
                         >> 0xcU))) | (5U == (7U & 
                                              (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir 
                                               >> 0xcU))));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__pend_v 
        = (((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__pend) 
            << 1U) | (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__pend));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__halted_v 
        = (((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__halted_r) 
            << 1U) | (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__halted_r));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT____Vcellinp__slot__BRA__0__KET____DOT__dmm__we 
        = ((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__cph) 
           & ((4U == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__state)) 
              & (0x23U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir))));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__id_q 
        = vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__imem_s
        [(0x3fU & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__pc 
                   >> 2U))];
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
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__last_up 
        = ((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__k) 
           == (0x1fU & ((0x3fU & (0x20U >> (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__lw_r))) 
                        - (IData)(1U))));
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__mk 
        = ((0x20U == (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__lw_r))))
            ? 0xffffffffU : (VL_SHIFTL_III(32,32,6, (IData)(1U), 
                                           (0x3fU & 
                                            ((IData)(1U) 
                                             << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__lw_r)))) 
                             - (IData)(1U)));
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT____VdfgTmp_h933689ae__0 
        = (0x1fU & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__shamt_w 
                    & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__lw_r))) 
                       - (IData)(1U))));
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dko 
        = (0x1fU & ((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__k) 
                    << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__lw_r)));
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__qs 
        = (0x1fU & ((0x1fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__shamt_w) 
                    >> (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__lw_r)));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__mask 
        = ((5U == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__lw_r))
            ? 0xffffffffU : (VL_SHIFTL_III(32,32,6, (IData)(1U), 
                                           (0x3fU & 
                                            ((IData)(1U) 
                                             << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__lw_r)))) 
                             - (IData)(1U)));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__rs2 
        = (0x1fU & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir 
                    >> 0x14U));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__is_sys 
        = (0x73U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__opc 
        = (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT____Vcellinp__slot__BRA__1__KET____DOT__dmm__we 
        = ((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__cph) 
           & ((4U == (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__state)) 
              & (0x23U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir))));
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT____VdfgTmp_h2cd83c5b__0 
        = ((0x37U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir)) 
           | (0x17U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir)));
    __Vtableidx2 = (((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__f_eq) 
                     << 5U) | (((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__f_lt) 
                                << 4U) | (((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__f_ltu) 
                                           << 3U) | 
                                          (7U & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir 
                                                 >> 0xcU)))));
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__cond 
        = Vtb_top_tang__ConstPool__TABLE_h2a0441a0_0
        [__Vtableidx2];
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT____VdfgTmp_hd9b60348__0 
        = ((2U == (7U & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir 
                         >> 0xcU))) | (3U == (7U & 
                                              (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir 
                                               >> 0xcU))));
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT____VdfgTmp_h18c46dac__0 
        = ((0x13U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir)) 
           | (0x33U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir)));
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT____VdfgTmp_he83b8d53__0 
        = ((1U == (7U & (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir 
                         >> 0xcU))) | (5U == (7U & 
                                              (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir 
                                               >> 0xcU))));
    if (vlSelf->__Vdlyvset__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__imem_s__v0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__imem_s[vlSelf->__Vdlyvdim0__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__imem_s__v0] 
            = vlSelf->__Vdlyvval__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__imem_s__v0;
    }
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__pc 
        = vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__pc;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__ren 
        = (tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__mk 
           << (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dko));
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__imm_d 
        = (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__imm_sr 
           & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__mask);
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__c4_d 
        = (VL_SHIFTR_III(32,32,6, 4U, (0x3fU & ((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__k) 
                                                * (0x3fU 
                                                   & ((IData)(1U) 
                                                      << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__lw_r)))))) 
           & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__mask);
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
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__is_cmp 
        = ((0x63U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir)) 
           | ((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT____VdfgTmp_h18c46dac__0) 
              & (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT____VdfgTmp_hd9b60348__0)));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__sh_i 
        = ((0x13U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir)) 
           & (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT____VdfgTmp_he83b8d53__0));
    if (vlSelf->__Vdlyvset__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__imem_s__v0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__imem_s[vlSelf->__Vdlyvdim0__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__imem_s__v0] 
            = vlSelf->__Vdlyvval__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__imem_s__v0;
    }
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__pc 
        = vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__pc;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__ren 
        = (tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__mk 
           << (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dko));
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__imm_d 
        = (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__imm_sr 
           & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__mask);
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__c4_d 
        = (VL_SHIFTR_III(32,32,6, 4U, (0x3fU & ((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__k) 
                                                * (0x3fU 
                                                   & ((IData)(1U) 
                                                      << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__lw_r)))))) 
           & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__mask);
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
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__is_cmp 
        = ((0x63U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir)) 
           | ((IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT____VdfgTmp_h18c46dac__0) 
              & (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT____VdfgTmp_hd9b60348__0)));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__sh_i 
        = ((0x13U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir)) 
           & (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT____VdfgTmp_he83b8d53__0));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT____VdfgTmp_he4828306__0 
        = VL_SHIFTR_III(32,32,6, vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__pc, 
                        (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__lw_r))));
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__pc_d 
        = (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__pc 
           & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__mask);
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
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__is_slt 
        = ((0x63U != (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir)) 
           & (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__is_cmp));
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__inv = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__is_shift 
        = ((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__sh_i) 
           | ((0x33U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir)) 
              & (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT____VdfgTmp_he83b8d53__0)));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT____VdfgTmp_he4828306__0 
        = VL_SHIFTR_III(32,32,6, vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__pc, 
                        (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__lw_r))));
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__pc_d 
        = (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__pc 
           & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__mask);
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
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__is_slt 
        = ((0x63U != (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir)) 
           & (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__is_cmp));
    tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__inv = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__is_shift 
        = ((IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__sh_i) 
           | ((0x33U == (0x7fU & vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir)) 
              & (IData)(tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT____VdfgTmp_he83b8d53__0)));
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__pc_rot 
        = (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT____VdfgTmp_he4828306__0 
           | VL_SHIFTL_III(32,32,6, vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__pc, 
                           (0x3fU & ((IData)(0x20U) 
                                     - ((IData)(1U) 
                                        << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__lw_r))))));
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
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__pc_rot 
        = (vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT____VdfgTmp_he4828306__0 
           | VL_SHIFTL_III(32,32,6, vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__pc, 
                           (0x3fU & ((IData)(0x20U) 
                                     - ((IData)(1U) 
                                        << (IData)(vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__lw_r))))));
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

void Vtb_top_tang___024root___nba_sequent__TOP__0(Vtb_top_tang___024root* vlSelf);
void Vtb_top_tang_pk_ram___nba_sequent__TOP__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__rfa__0(Vtb_top_tang_pk_ram* vlSelf);
void Vtb_top_tang_pk_ram___nba_sequent__TOP__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__rfb__0(Vtb_top_tang_pk_ram* vlSelf);
void Vtb_top_tang_pk_ram___nba_sequent__TOP__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__rfa__0(Vtb_top_tang_pk_ram* vlSelf);
void Vtb_top_tang_pk_ram___nba_sequent__TOP__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__rfb__0(Vtb_top_tang_pk_ram* vlSelf);

void Vtb_top_tang___024root___eval_nba(Vtb_top_tang___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_top_tang__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtb_top_tang___024root___eval_nba\n"); );
    // Body
    if ((1ULL & vlSelf->__VnbaTriggered.word(0U))) {
        Vtb_top_tang___024root___nba_sequent__TOP__0(vlSelf);
        Vtb_top_tang_pk_ram___nba_sequent__TOP__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__rfa__0((&vlSymsp->TOP__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__rfa));
        Vtb_top_tang_pk_ram___nba_sequent__TOP__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__rfb__0((&vlSymsp->TOP__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__rfb));
        Vtb_top_tang_pk_ram___nba_sequent__TOP__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__rfa__0((&vlSymsp->TOP__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__rfa));
        Vtb_top_tang_pk_ram___nba_sequent__TOP__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__rfb__0((&vlSymsp->TOP__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__rfb));
        Vtb_top_tang___024root___nba_sequent__TOP__1(vlSelf);
    }
}
