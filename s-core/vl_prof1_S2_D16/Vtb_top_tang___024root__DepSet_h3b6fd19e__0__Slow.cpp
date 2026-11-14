// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design implementation internals
// See Vtb_top_tang.h for the primary calling header

#include "Vtb_top_tang__pch.h"
#include "Vtb_top_tang___024root.h"

VL_ATTR_COLD void Vtb_top_tang___024root___eval_static__TOP(Vtb_top_tang___024root* vlSelf);

VL_ATTR_COLD void Vtb_top_tang___024root___eval_static(Vtb_top_tang___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_top_tang__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtb_top_tang___024root___eval_static\n"); );
    // Body
    Vtb_top_tang___024root___eval_static__TOP(vlSelf);
}

VL_ATTR_COLD void Vtb_top_tang___024root___eval_static__TOP(Vtb_top_tang___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_top_tang__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtb_top_tang___024root___eval_static__TOP\n"); );
    // Body
    vlSelf->tb_top_tang__DOT__clk = 0U;
    vlSelf->tb_top_tang__DOT__rx = 1U;
    vlSelf->tb_top_tang__DOT__rcount = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__por = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__br__DOT__tb = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__br__DOT__tsend = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__br__DOT__st = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__br__DOT__cmd = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__br__DOT__need = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__br__DOT__got = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__br__DOT__rlen = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__br__DOT__ridx = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__br__DOT__cyc_s = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__br__DOT__rstcnt = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__br__DOT__stx = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__br__DOT__urx__DOT__sync = 3U;
    vlSelf->tb_top_tang__DOT__dut__DOT__br__DOT__urx__DOT__cnt = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__br__DOT__urx__DOT__nbit = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__br__DOT__urx__DOT__busy = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__br__DOT__urx__DOT__sh = 0U;
    vlSelf->tb_top_tang__DOT__tx = 1U;
    vlSelf->tb_top_tang__DOT__dut__DOT__br__DOT__utx__DOT__cnt = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__br__DOT__utx__DOT__nbit = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__br__DOT__utx__DOT__sh = 0x3ffU;
    vlSelf->tb_top_tang__DOT__dut__DOT__br__DOT__utx__DOT__act = 0U;
}

VL_ATTR_COLD void Vtb_top_tang___024root___eval_initial__TOP(Vtb_top_tang___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_top_tang__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtb_top_tang___024root___eval_initial__TOP\n"); );
    // Init
    IData/*31:0*/ __Vilp;
    // Body
    vlSelf->tb_top_tang__DOT__dut__DOT__h_push = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__imem_we = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__soft_rst = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__q_tid = 0U;
    __Vilp = 0U;
    while ((__Vilp <= 0x3fU)) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__prof[__Vilp] = 0U;
        __Vilp = ((IData)(1U) + __Vilp);
    }
    __Vilp = 0U;
    while ((__Vilp <= 0x3fU)) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__imem_s[__Vilp] = 0U;
        __Vilp = ((IData)(1U) + __Vilp);
    }
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__a0s = 0U;
    __Vilp = 0U;
    while ((__Vilp <= 0x3fU)) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__imem_s[__Vilp] = 0U;
        __Vilp = ((IData)(1U) + __Vilp);
    }
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__a0s = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__0__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__0__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__0__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__0__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__0__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__0__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__0__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__0__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__0__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__0__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__0__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__0__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__0__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__0__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__0__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__0__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__1__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__1__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__1__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__1__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__1__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__1__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__1__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__1__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__1__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__1__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__1__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__1__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__1__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__1__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__1__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__1__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__2__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__2__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__2__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__2__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__2__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__2__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__2__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__2__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__2__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__2__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__2__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__2__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__2__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__2__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__2__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__2__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__3__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__3__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__3__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__3__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__3__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__3__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__3__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__3__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__3__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__3__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__3__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__3__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__3__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__3__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__3__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__3__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__4__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__4__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__4__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__4__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__4__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__4__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__4__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__4__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__4__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__4__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__4__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__4__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__4__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__4__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__4__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__4__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__5__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__5__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__5__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__5__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__5__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__5__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__5__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__5__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__5__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__5__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__5__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__5__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__5__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__5__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__5__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__5__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__6__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__6__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__6__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__6__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__6__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__6__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__6__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__6__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__6__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__6__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__6__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__6__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__6__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__6__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__6__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__6__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__7__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__7__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__7__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__7__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__7__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__7__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__7__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__7__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__7__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__7__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__7__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__7__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__7__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__7__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__7__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__7__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__8__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__8__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__8__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__8__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__8__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__8__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__8__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__8__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__8__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__8__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__8__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__8__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__8__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__8__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__8__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__8__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__9__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__9__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__9__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__9__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__9__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__9__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__9__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__9__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__9__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__9__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__9__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__9__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__9__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__9__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__9__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__9__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__10__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__10__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__10__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__10__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__10__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__10__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__10__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__10__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__10__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__10__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__10__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__10__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__10__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__10__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__10__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__10__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__11__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__11__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__11__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__11__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__11__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__11__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__11__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__11__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__11__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__11__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__11__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__11__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__11__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__11__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__11__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__11__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__12__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__12__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__12__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__12__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__12__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__12__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__12__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__12__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__12__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__12__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__12__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__12__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__12__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__12__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__12__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__12__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__13__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__13__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__13__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__13__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__13__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__13__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__13__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__13__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__13__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__13__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__13__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__13__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__13__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__13__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__13__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__13__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__14__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__14__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__14__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__14__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__14__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__14__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__14__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__14__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__14__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__14__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__14__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__14__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__14__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__14__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__14__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__14__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__15__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__15__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__15__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__15__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__15__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__15__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__15__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__15__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__15__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__15__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__15__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__15__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__15__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__15__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__15__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__15__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__16__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__16__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__16__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__16__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__16__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__16__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__16__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__16__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__16__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__16__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__16__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__16__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__16__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__16__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__16__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__16__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__17__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__17__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__17__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__17__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__17__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__17__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__17__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__17__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__17__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__17__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__17__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__17__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__17__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__17__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__17__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__17__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__18__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__18__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__18__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__18__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__18__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__18__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__18__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__18__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__18__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__18__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__18__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__18__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__18__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__18__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__18__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__18__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__19__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__19__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__19__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__19__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__19__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__19__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__19__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__19__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__19__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__19__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__19__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__19__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__19__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__19__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__19__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__19__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__20__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__20__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__20__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__20__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__20__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__20__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__20__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__20__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__20__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__20__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__20__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__20__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__20__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__20__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__20__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__20__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__21__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__21__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__21__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__21__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__21__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__21__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__21__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__21__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__21__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__21__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__21__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__21__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__21__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__21__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__21__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__21__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__22__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__22__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__22__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__22__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__22__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__22__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__22__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__22__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__22__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__22__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__22__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__22__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__22__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__22__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__22__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__22__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__23__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__23__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__23__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__23__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__23__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__23__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__23__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__23__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__23__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__23__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__23__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__23__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__23__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__23__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__23__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__23__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__24__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__24__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__24__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__24__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__24__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__24__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__24__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__24__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__24__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__24__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__24__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__24__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__24__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__24__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__24__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__24__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__25__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__25__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__25__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__25__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__25__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__25__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__25__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__25__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__25__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__25__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__25__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__25__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__25__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__25__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__25__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__25__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__26__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__26__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__26__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__26__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__26__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__26__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__26__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__26__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__26__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__26__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__26__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__26__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__26__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__26__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__26__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__26__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__27__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__27__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__27__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__27__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__27__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__27__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__27__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__27__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__27__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__27__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__27__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__27__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__27__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__27__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__27__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__27__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__28__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__28__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__28__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__28__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__28__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__28__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__28__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__28__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__28__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__28__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__28__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__28__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__28__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__28__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__28__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__28__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__29__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__29__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__29__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__29__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__29__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__29__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__29__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__29__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__29__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__29__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__29__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__29__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__29__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__29__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__29__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__29__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__30__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__30__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__30__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__30__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__30__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__30__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__30__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__30__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__30__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__30__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__30__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__30__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__30__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__30__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__30__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__30__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__31__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__31__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__31__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__31__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__31__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__31__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__31__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__31__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__31__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__31__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__31__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__31__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__31__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__31__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__31__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__31__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__0__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__0__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__0__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__0__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__0__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__0__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__0__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__0__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__0__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__0__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__0__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__0__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__0__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__0__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__0__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__0__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__1__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__1__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__1__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__1__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__1__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__1__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__1__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__1__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__1__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__1__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__1__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__1__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__1__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__1__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__1__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__1__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__2__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__2__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__2__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__2__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__2__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__2__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__2__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__2__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__2__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__2__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__2__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__2__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__2__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__2__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__2__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__2__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__3__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__3__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__3__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__3__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__3__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__3__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__3__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__3__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__3__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__3__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__3__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__3__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__3__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__3__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__3__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__3__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__4__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__4__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__4__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__4__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__4__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__4__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__4__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__4__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__4__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__4__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__4__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__4__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__4__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__4__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__4__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__4__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__5__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__5__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__5__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__5__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__5__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__5__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__5__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__5__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__5__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__5__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__5__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__5__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__5__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__5__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__5__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__5__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__6__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__6__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__6__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__6__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__6__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__6__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__6__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__6__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__6__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__6__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__6__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__6__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__6__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__6__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__6__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__6__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__7__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__7__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__7__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__7__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__7__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__7__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__7__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__7__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__7__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__7__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__7__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__7__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__7__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__7__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__7__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__7__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__8__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__8__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__8__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__8__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__8__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__8__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__8__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__8__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__8__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__8__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__8__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__8__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__8__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__8__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__8__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__8__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__9__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__9__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__9__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__9__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__9__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__9__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__9__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__9__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__9__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__9__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__9__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__9__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__9__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__9__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__9__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__9__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__10__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__10__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__10__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__10__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__10__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__10__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__10__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__10__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__10__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__10__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__10__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__10__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__10__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__10__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__10__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__10__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__11__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__11__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__11__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__11__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__11__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__11__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__11__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__11__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__11__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__11__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__11__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__11__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__11__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__11__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__11__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__11__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__12__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__12__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__12__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__12__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__12__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__12__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__12__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__12__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__12__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__12__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__12__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__12__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__12__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__12__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__12__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__12__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__13__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__13__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__13__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__13__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__13__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__13__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__13__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__13__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__13__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__13__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__13__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__13__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__13__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__13__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__13__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__13__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__14__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__14__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__14__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__14__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__14__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__14__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__14__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__14__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__14__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__14__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__14__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__14__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__14__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__14__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__14__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__14__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__15__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__15__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__15__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__15__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__15__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__15__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__15__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__15__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__15__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__15__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__15__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__15__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__15__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__15__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__15__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__15__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__16__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__16__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__16__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__16__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__16__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__16__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__16__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__16__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__16__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__16__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__16__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__16__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__16__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__16__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__16__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__16__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__17__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__17__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__17__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__17__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__17__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__17__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__17__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__17__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__17__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__17__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__17__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__17__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__17__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__17__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__17__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__17__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__18__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__18__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__18__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__18__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__18__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__18__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__18__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__18__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__18__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__18__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__18__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__18__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__18__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__18__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__18__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__18__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__19__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__19__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__19__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__19__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__19__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__19__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__19__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__19__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__19__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__19__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__19__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__19__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__19__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__19__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__19__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__19__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__20__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__20__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__20__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__20__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__20__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__20__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__20__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__20__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__20__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__20__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__20__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__20__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__20__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__20__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__20__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__20__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__21__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__21__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__21__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__21__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__21__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__21__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__21__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__21__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__21__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__21__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__21__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__21__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__21__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__21__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__21__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__21__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__22__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__22__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__22__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__22__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__22__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__22__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__22__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__22__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__22__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__22__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__22__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__22__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__22__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__22__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__22__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__22__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__23__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__23__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__23__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__23__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__23__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__23__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__23__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__23__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__23__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__23__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__23__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__23__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__23__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__23__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__23__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__23__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__24__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__24__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__24__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__24__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__24__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__24__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__24__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__24__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__24__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__24__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__24__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__24__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__24__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__24__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__24__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__24__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__25__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__25__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__25__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__25__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__25__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__25__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__25__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__25__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__25__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__25__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__25__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__25__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__25__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__25__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__25__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__25__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__26__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__26__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__26__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__26__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__26__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__26__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__26__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__26__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__26__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__26__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__26__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__26__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__26__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__26__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__26__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__26__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__27__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__27__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__27__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__27__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__27__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__27__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__27__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__27__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__27__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__27__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__27__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__27__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__27__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__27__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__27__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__27__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__28__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__28__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__28__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__28__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__28__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__28__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__28__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__28__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__28__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__28__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__28__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__28__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__28__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__28__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__28__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__28__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__29__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__29__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__29__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__29__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__29__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__29__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__29__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__29__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__29__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__29__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__29__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__29__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__29__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__29__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__29__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__29__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__30__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__30__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__30__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__30__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__30__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__30__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__30__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__30__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__30__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__30__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__30__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__30__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__30__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__30__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__30__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__30__KET____DOT__m[0xfU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__31__KET____DOT__m[0U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__31__KET____DOT__m[1U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__31__KET____DOT__m[2U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__31__KET____DOT__m[3U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__31__KET____DOT__m[4U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__31__KET____DOT__m[5U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__31__KET____DOT__m[6U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__31__KET____DOT__m[7U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__31__KET____DOT__m[8U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__31__KET____DOT__m[9U] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__31__KET____DOT__m[0xaU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__31__KET____DOT__m[0xbU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__31__KET____DOT__m[0xcU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__31__KET____DOT__m[0xdU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__31__KET____DOT__m[0xeU] = 0U;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__31__KET____DOT__m[0xfU] = 0U;
}

VL_ATTR_COLD void Vtb_top_tang___024root___eval_final(Vtb_top_tang___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_top_tang__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtb_top_tang___024root___eval_final\n"); );
}

#ifdef VL_DEBUG
VL_ATTR_COLD void Vtb_top_tang___024root___dump_triggers__stl(Vtb_top_tang___024root* vlSelf);
#endif  // VL_DEBUG
VL_ATTR_COLD bool Vtb_top_tang___024root___eval_phase__stl(Vtb_top_tang___024root* vlSelf);

VL_ATTR_COLD void Vtb_top_tang___024root___eval_settle(Vtb_top_tang___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_top_tang__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtb_top_tang___024root___eval_settle\n"); );
    // Init
    IData/*31:0*/ __VstlIterCount;
    CData/*0:0*/ __VstlContinue;
    // Body
    __VstlIterCount = 0U;
    vlSelf->__VstlFirstIteration = 1U;
    __VstlContinue = 1U;
    while (__VstlContinue) {
        if (VL_UNLIKELY((0x64U < __VstlIterCount))) {
#ifdef VL_DEBUG
            Vtb_top_tang___024root___dump_triggers__stl(vlSelf);
#endif
            VL_FATAL_MT("/home/claude/imago-unicell/s-core/fpga/tb_top_tang.v", 5, "", "Settle region did not converge.");
        }
        __VstlIterCount = ((IData)(1U) + __VstlIterCount);
        __VstlContinue = 0U;
        if (Vtb_top_tang___024root___eval_phase__stl(vlSelf)) {
            __VstlContinue = 1U;
        }
        vlSelf->__VstlFirstIteration = 0U;
    }
}

#ifdef VL_DEBUG
VL_ATTR_COLD void Vtb_top_tang___024root___dump_triggers__stl(Vtb_top_tang___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_top_tang__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtb_top_tang___024root___dump_triggers__stl\n"); );
    // Body
    if ((1U & (~ (IData)(vlSelf->__VstlTriggered.any())))) {
        VL_DBG_MSGF("         No triggers active\n");
    }
    if ((1ULL & vlSelf->__VstlTriggered.word(0U))) {
        VL_DBG_MSGF("         'stl' region trigger index 0 is active: Internal 'stl' trigger - first iteration\n");
    }
}
#endif  // VL_DEBUG

VL_ATTR_COLD void Vtb_top_tang___024root___stl_sequent__TOP__0(Vtb_top_tang___024root* vlSelf);

VL_ATTR_COLD void Vtb_top_tang___024root___eval_stl(Vtb_top_tang___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_top_tang__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtb_top_tang___024root___eval_stl\n"); );
    // Body
    if ((1ULL & vlSelf->__VstlTriggered.word(0U))) {
        Vtb_top_tang___024root___stl_sequent__TOP__0(vlSelf);
    }
}

VL_ATTR_COLD void Vtb_top_tang___024root___eval_triggers__stl(Vtb_top_tang___024root* vlSelf);

VL_ATTR_COLD bool Vtb_top_tang___024root___eval_phase__stl(Vtb_top_tang___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_top_tang__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtb_top_tang___024root___eval_phase__stl\n"); );
    // Init
    CData/*0:0*/ __VstlExecute;
    // Body
    Vtb_top_tang___024root___eval_triggers__stl(vlSelf);
    __VstlExecute = vlSelf->__VstlTriggered.any();
    if (__VstlExecute) {
        Vtb_top_tang___024root___eval_stl(vlSelf);
    }
    return (__VstlExecute);
}

#ifdef VL_DEBUG
VL_ATTR_COLD void Vtb_top_tang___024root___dump_triggers__act(Vtb_top_tang___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_top_tang__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtb_top_tang___024root___dump_triggers__act\n"); );
    // Body
    if ((1U & (~ (IData)(vlSelf->__VactTriggered.any())))) {
        VL_DBG_MSGF("         No triggers active\n");
    }
    if ((1ULL & vlSelf->__VactTriggered.word(0U))) {
        VL_DBG_MSGF("         'act' region trigger index 0 is active: @(posedge tb_top_tang.clk)\n");
    }
    if ((2ULL & vlSelf->__VactTriggered.word(0U))) {
        VL_DBG_MSGF("         'act' region trigger index 1 is active: @(negedge tb_top_tang.tx)\n");
    }
    if ((4ULL & vlSelf->__VactTriggered.word(0U))) {
        VL_DBG_MSGF("         'act' region trigger index 2 is active: @([true] __VdlySched.awaitingCurrentTime())\n");
    }
}
#endif  // VL_DEBUG

#ifdef VL_DEBUG
VL_ATTR_COLD void Vtb_top_tang___024root___dump_triggers__nba(Vtb_top_tang___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_top_tang__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtb_top_tang___024root___dump_triggers__nba\n"); );
    // Body
    if ((1U & (~ (IData)(vlSelf->__VnbaTriggered.any())))) {
        VL_DBG_MSGF("         No triggers active\n");
    }
    if ((1ULL & vlSelf->__VnbaTriggered.word(0U))) {
        VL_DBG_MSGF("         'nba' region trigger index 0 is active: @(posedge tb_top_tang.clk)\n");
    }
    if ((2ULL & vlSelf->__VnbaTriggered.word(0U))) {
        VL_DBG_MSGF("         'nba' region trigger index 1 is active: @(negedge tb_top_tang.tx)\n");
    }
    if ((4ULL & vlSelf->__VnbaTriggered.word(0U))) {
        VL_DBG_MSGF("         'nba' region trigger index 2 is active: @([true] __VdlySched.awaitingCurrentTime())\n");
    }
}
#endif  // VL_DEBUG

VL_ATTR_COLD void Vtb_top_tang___024root___ctor_var_reset(Vtb_top_tang___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_top_tang__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtb_top_tang___024root___ctor_var_reset\n"); );
    // Body
    vlSelf->tb_top_tang__DOT__clk = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__rx = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__tx = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__fo = 0;
    VL_RAND_RESET_W(1024, vlSelf->tb_top_tang__DOT__cmdname);
    VL_RAND_RESET_W(1024, vlSelf->tb_top_tang__DOT__outname);
    vlSelf->tb_top_tang__DOT__rcount = VL_RAND_RESET_I(32);
    vlSelf->tb_top_tang__DOT__r = VL_RAND_RESET_I(32);
    vlSelf->tb_top_tang__DOT__n = VL_RAND_RESET_I(32);
    vlSelf->tb_top_tang__DOT__tag = VL_RAND_RESET_I(8);
    vlSelf->tb_top_tang__DOT__rxb__DOT__v = VL_RAND_RESET_I(8);
    vlSelf->tb_top_tang__DOT__dut__DOT__por = VL_RAND_RESET_I(8);
    vlSelf->tb_top_tang__DOT__dut__DOT__por_done = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__soft_rst = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__rst = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__h_push = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__h_crit = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__imem_we = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__q_trap = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__h_tid = VL_RAND_RESET_I(16);
    vlSelf->tb_top_tang__DOT__dut__DOT__h_code = VL_RAND_RESET_I(16);
    vlSelf->tb_top_tang__DOT__dut__DOT__imem_wa = VL_RAND_RESET_I(16);
    vlSelf->tb_top_tang__DOT__dut__DOT__q_tid = VL_RAND_RESET_I(16);
    vlSelf->tb_top_tang__DOT__dut__DOT__h_lw = VL_RAND_RESET_I(3);
    vlSelf->tb_top_tang__DOT__dut__DOT__h_prog = VL_RAND_RESET_I(6);
    vlSelf->tb_top_tang__DOT__dut__DOT__q_slot = VL_RAND_RESET_I(6);
    vlSelf->tb_top_tang__DOT__dut__DOT__imem_wd = VL_RAND_RESET_I(32);
    vlSelf->tb_top_tang__DOT__dut__DOT__q_start = VL_RAND_RESET_I(32);
    vlSelf->tb_top_tang__DOT__dut__DOT__q_end = VL_RAND_RESET_I(32);
    vlSelf->tb_top_tang__DOT__dut__DOT__q_a0 = VL_RAND_RESET_I(32);
    vlSelf->tb_top_tang__DOT__dut__DOT__q_arr = VL_RAND_RESET_I(32);
    vlSelf->tb_top_tang__DOT__dut__DOT__q_state = VL_RAND_RESET_I(2);
    vlSelf->tb_top_tang__DOT__dut__DOT__q_pred = VL_RAND_RESET_I(25);
    vlSelf->tb_top_tang__DOT__dut__DOT__br__DOT__rb = VL_RAND_RESET_I(8);
    vlSelf->tb_top_tang__DOT__dut__DOT__br__DOT__rv = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__br__DOT__tb = VL_RAND_RESET_I(8);
    vlSelf->tb_top_tang__DOT__dut__DOT__br__DOT__tsend = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__br__DOT__st = VL_RAND_RESET_I(2);
    vlSelf->tb_top_tang__DOT__dut__DOT__br__DOT__cmd = VL_RAND_RESET_I(8);
    vlSelf->tb_top_tang__DOT__dut__DOT__br__DOT__need = VL_RAND_RESET_I(4);
    vlSelf->tb_top_tang__DOT__dut__DOT__br__DOT__got = VL_RAND_RESET_I(4);
    for (int __Vi0 = 0; __Vi0 < 7; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__br__DOT__a[__Vi0] = VL_RAND_RESET_I(8);
    }
    vlSelf->tb_top_tang__DOT__dut__DOT__br__DOT__rlen = VL_RAND_RESET_I(7);
    vlSelf->tb_top_tang__DOT__dut__DOT__br__DOT__ridx = VL_RAND_RESET_I(7);
    vlSelf->tb_top_tang__DOT__dut__DOT__br__DOT__cyc_s = VL_RAND_RESET_I(32);
    vlSelf->tb_top_tang__DOT__dut__DOT__br__DOT__rstcnt = VL_RAND_RESET_I(4);
    vlSelf->tb_top_tang__DOT__dut__DOT__br__DOT__stx = VL_RAND_RESET_I(24);
    vlSelf->tb_top_tang__DOT__dut__DOT__br__DOT__rbyte__Vstatic__w = VL_RAND_RESET_Q(64);
    vlSelf->tb_top_tang__DOT__dut__DOT__br__DOT____Vlvbound_h696a2bd5__0 = VL_RAND_RESET_I(8);
    vlSelf->tb_top_tang__DOT__dut__DOT__br__DOT__urx__DOT__sync = VL_RAND_RESET_I(2);
    vlSelf->tb_top_tang__DOT__dut__DOT__br__DOT__urx__DOT__cnt = VL_RAND_RESET_I(16);
    vlSelf->tb_top_tang__DOT__dut__DOT__br__DOT__urx__DOT__nbit = VL_RAND_RESET_I(4);
    vlSelf->tb_top_tang__DOT__dut__DOT__br__DOT__urx__DOT__busy = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__br__DOT__urx__DOT__sh = VL_RAND_RESET_I(8);
    vlSelf->tb_top_tang__DOT__dut__DOT__br__DOT__utx__DOT__cnt = VL_RAND_RESET_I(16);
    vlSelf->tb_top_tang__DOT__dut__DOT__br__DOT__utx__DOT__nbit = VL_RAND_RESET_I(4);
    vlSelf->tb_top_tang__DOT__dut__DOT__br__DOT__utx__DOT__sh = VL_RAND_RESET_I(10);
    vlSelf->tb_top_tang__DOT__dut__DOT__br__DOT__utx__DOT__act = VL_RAND_RESET_I(1);
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__t_code[__Vi0] = VL_RAND_RESET_I(16);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__t_lw[__Vi0] = VL_RAND_RESET_I(3);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__t_arr[__Vi0] = VL_RAND_RESET_I(32);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__t_start[__Vi0] = VL_RAND_RESET_I(32);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__t_end[__Vi0] = VL_RAND_RESET_I(32);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__t_a0[__Vi0] = VL_RAND_RESET_I(32);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__t_trap[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__t_state[__Vi0] = VL_RAND_RESET_I(2);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__t_slot[__Vi0] = VL_RAND_RESET_I(6);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__t_prog[__Vi0] = VL_RAND_RESET_I(6);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__t_pred[__Vi0] = VL_RAND_RESET_I(25);
    }
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__done_count = VL_RAND_RESET_I(32);
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__qc[__Vi0] = VL_RAND_RESET_I(16);
    }
    for (int __Vi0 = 0; __Vi0 < 256; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__qk[__Vi0] = VL_RAND_RESET_I(16);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__kwr[__Vi0] = VL_RAND_RESET_I(32);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__krd[__Vi0] = VL_RAND_RESET_I(32);
    }
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__qc_wr = VL_RAND_RESET_I(32);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__qc_rd = VL_RAND_RESET_I(32);
    for (int __Vi0 = 0; __Vi0 < 64; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__prof[__Vi0] = VL_RAND_RESET_I(25);
    }
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__bucket_of__Vstatic__d = VL_RAND_RESET_I(24);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__bucket_of__Vstatic__lg = VL_RAND_RESET_I(5);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__bucket_of__Vstatic__ix = VL_RAND_RESET_I(6);
    VL_RAND_RESET_W(256, vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__req_tab);
    for (int __Vi0 = 0; __Vi0 < 8; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__ev_pl[__Vi0] = VL_RAND_RESET_I(32);
    }
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__ev_cnt = VL_RAND_RESET_I(32);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__start_v = VL_RAND_RESET_I(2);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__halted_q = VL_RAND_RESET_I(2);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__fin_sent = VL_RAND_RESET_I(2);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__pend_v = VL_RAND_RESET_I(2);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__cph = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__halted_v = VL_RAND_RESET_I(2);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__launch_entry = VL_RAND_RESET_I(32);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__launch_lw = VL_RAND_RESET_I(3);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slice_busy = VL_RAND_RESET_Q(64);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__busy_l = VL_RAND_RESET_I(2);
    for (int __Vi0 = 0; __Vi0 < 2; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__own_tid[__Vi0] = VL_RAND_RESET_I(16);
    }
    for (int __Vi0 = 0; __Vi0 < 2; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__own_lw[__Vi0] = VL_RAND_RESET_I(3);
    }
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__cyc = VL_RAND_RESET_I(32);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__busy_slice_cycles = VL_RAND_RESET_Q(64);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__waste_blocked = VL_RAND_RESET_Q(64);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__waste_tail = VL_RAND_RESET_Q(64);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__search_cycles = VL_RAND_RESET_Q(64);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__launch_err = VL_RAND_RESET_I(32);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__dispatches = VL_RAND_RESET_I(32);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__dstate = VL_RAND_RESET_I(2);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__rescan = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__ph = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__cur_is_crit = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__cur_tid = VL_RAND_RESET_I(16);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__cur_code = VL_RAND_RESET_I(16);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__cur_lw = VL_RAND_RESET_I(3);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__cand = VL_RAND_RESET_I(6);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__crit_streak = VL_RAND_RESET_I(32);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__bulk_pass = VL_RAND_RESET_I(32);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__pend_c = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__pend_b = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__hb = VL_RAND_RESET_I(4);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__bhead = VL_RAND_RESET_I(16);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__cur_bk = VL_RAND_RESET_I(4);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__cur_w = VL_RAND_RESET_I(6);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__cur_gm = VL_RAND_RESET_Q(64);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__fit_found = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__fit_base = VL_RAND_RESET_I(6);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__row_any = VL_RAND_RESET_I(16);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__w_found = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__w_id = VL_RAND_RESET_I(8);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__nb = VL_RAND_RESET_Q(64);
    VL_RAND_RESET_W(256, vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__rq);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__rs = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__wfree = VL_RAND_RESET_I(6);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__wb = VL_RAND_RESET_I(6);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__pb = VL_RAND_RESET_I(4);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__pk = VL_RAND_RESET_I(9);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__dur = VL_RAND_RESET_I(24);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__davg = VL_RAND_RESET_I(25);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__pcnt = VL_RAND_RESET_I(32);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__first_crit = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__second_crit = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__second_avail = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__second_ok = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__rwe = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dwd = VL_RAND_RESET_I(32);
    for (int __Vi0 = 0; __Vi0 < 64; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__imem_s[__Vi0] = VL_RAND_RESET_I(32);
    }
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__id_q = VL_RAND_RESET_I(32);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__rdat = VL_RAND_RESET_I(32);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__ren = VL_RAND_RESET_I(32);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dq = VL_RAND_RESET_I(32);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT____Vcellinp__slot__BRA__0__KET____DOT__rfa__we = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT____Vcellinp__slot__BRA__0__KET____DOT__rfb__ra = VL_RAND_RESET_I(5);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__ddat = VL_RAND_RESET_I(32);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT____Vcellinp__slot__BRA__0__KET____DOT__dmm__we = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__pend = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__ent_q = VL_RAND_RESET_I(32);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__lw_q = VL_RAND_RESET_I(3);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__a0s = VL_RAND_RESET_I(32);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__rwe = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dwd = VL_RAND_RESET_I(32);
    for (int __Vi0 = 0; __Vi0 < 64; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__imem_s[__Vi0] = VL_RAND_RESET_I(32);
    }
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__id_q = VL_RAND_RESET_I(32);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__rdat = VL_RAND_RESET_I(32);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__ren = VL_RAND_RESET_I(32);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dq = VL_RAND_RESET_I(32);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT____Vcellinp__slot__BRA__1__KET____DOT__rfa__we = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT____Vcellinp__slot__BRA__1__KET____DOT__rfb__ra = VL_RAND_RESET_I(5);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__ddat = VL_RAND_RESET_I(32);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT____Vcellinp__slot__BRA__1__KET____DOT__dmm__we = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__pend = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__ent_q = VL_RAND_RESET_I(32);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__lw_q = VL_RAND_RESET_I(3);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__a0s = VL_RAND_RESET_I(32);
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__0__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__1__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__2__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__3__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__4__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__5__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__6__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__7__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__8__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__9__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__10__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__11__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__12__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__13__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__14__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__15__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__16__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__17__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__18__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__19__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__20__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__21__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__22__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__23__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__24__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__25__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__26__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__27__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__28__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__29__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__30__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__dmm__DOT__lane__BRA__31__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__state = VL_RAND_RESET_I(3);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__pc = VL_RAND_RESET_I(32);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ir = VL_RAND_RESET_I(32);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__addr = VL_RAND_RESET_I(32);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__imm_sr = VL_RAND_RESET_I(32);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__shamt_w = VL_RAND_RESET_I(32);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__k = VL_RAND_RESET_I(5);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__j = VL_RAND_RESET_I(3);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__lw_r = VL_RAND_RESET_I(3);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__cy = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__nz = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__f_eq = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__f_lt = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__f_ltu = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__sgn = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__halted_r = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__trap_r = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__wm1 = VL_RAND_RESET_I(6);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__mask = VL_RAND_RESET_I(32);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__kmax = VL_RAND_RESET_I(5);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__opc = VL_RAND_RESET_I(7);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__rs2 = VL_RAND_RESET_I(5);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__is_sys = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__imm = VL_RAND_RESET_I(32);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__sh_i = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__is_shift = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__is_sll = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__is_cmp = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__is_slt = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__bad = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__last_up = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__a_val = VL_RAND_RESET_I(32);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__cout = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__pc_rot = VL_RAND_RESET_I(32);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__imm_rot = VL_RAND_RESET_I(32);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__addr_ins = VL_RAND_RESET_I(32);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__nz_n = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__xsh = VL_RAND_RESET_I(32);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__ysh = VL_RAND_RESET_I(32);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__exec_done = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__mlast = VL_RAND_RESET_I(6);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__jw = VL_RAND_RESET_I(6);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT____VdfgTmp_he4828306__0 = 0;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT____VdfgTmp_h7980eff3__0 = 0;
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__0__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__1__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__2__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__3__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__4__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__5__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__6__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__7__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__8__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__9__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__10__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__11__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__12__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__13__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__14__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__15__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__16__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__17__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__18__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__19__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__20__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__21__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__22__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__23__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__24__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__25__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__26__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__27__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__28__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__29__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__30__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__dmm__DOT__lane__BRA__31__KET____DOT__m[__Vi0] = VL_RAND_RESET_I(1);
    }
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__state = VL_RAND_RESET_I(3);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__pc = VL_RAND_RESET_I(32);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ir = VL_RAND_RESET_I(32);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__addr = VL_RAND_RESET_I(32);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__imm_sr = VL_RAND_RESET_I(32);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__shamt_w = VL_RAND_RESET_I(32);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__k = VL_RAND_RESET_I(5);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__j = VL_RAND_RESET_I(3);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__lw_r = VL_RAND_RESET_I(3);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__cy = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__nz = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__f_eq = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__f_lt = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__f_ltu = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__sgn = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__halted_r = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__trap_r = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__wm1 = VL_RAND_RESET_I(6);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__mask = VL_RAND_RESET_I(32);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__kmax = VL_RAND_RESET_I(5);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__opc = VL_RAND_RESET_I(7);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__rs2 = VL_RAND_RESET_I(5);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__is_sys = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__imm = VL_RAND_RESET_I(32);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__sh_i = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__is_shift = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__is_sll = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__is_cmp = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__is_slt = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__bad = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__last_up = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__a_val = VL_RAND_RESET_I(32);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__cout = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__pc_rot = VL_RAND_RESET_I(32);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__imm_rot = VL_RAND_RESET_I(32);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__addr_ins = VL_RAND_RESET_I(32);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__nz_n = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__xsh = VL_RAND_RESET_I(32);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__ysh = VL_RAND_RESET_I(32);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__exec_done = VL_RAND_RESET_I(1);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__mlast = VL_RAND_RESET_I(6);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__jw = VL_RAND_RESET_I(6);
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT____VdfgTmp_he4828306__0 = 0;
    vlSelf->tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT____VdfgTmp_h7980eff3__0 = 0;
    vlSelf->__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__gmask__2__Vfuncout = VL_RAND_RESET_Q(64);
    vlSelf->__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__gmask__2__w = VL_RAND_RESET_I(7);
    vlSelf->__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__4__Vfuncout = VL_RAND_RESET_I(4);
    vlSelf->__Vfunc_tb_top_tang__DOT__dut__DOT__sys__DOT__pe16__4__x = VL_RAND_RESET_I(16);
    vlSelf->__Vdlyvdim0__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__imem_s__v0 = 0;
    vlSelf->__Vdlyvval__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__imem_s__v0 = VL_RAND_RESET_I(32);
    vlSelf->__Vdlyvset__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__imem_s__v0 = 0;
    vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__lw_q = VL_RAND_RESET_I(3);
    vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__pend = VL_RAND_RESET_I(1);
    vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__ent_q = VL_RAND_RESET_I(32);
    vlSelf->__Vdlyvdim0__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__imem_s__v0 = 0;
    vlSelf->__Vdlyvval__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__imem_s__v0 = VL_RAND_RESET_I(32);
    vlSelf->__Vdlyvset__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__imem_s__v0 = 0;
    vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__lw_q = VL_RAND_RESET_I(3);
    vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__pend = VL_RAND_RESET_I(1);
    vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__ent_q = VL_RAND_RESET_I(32);
    vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__cph = VL_RAND_RESET_I(1);
    vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__state = VL_RAND_RESET_I(3);
    vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__pc = VL_RAND_RESET_I(32);
    vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__addr = VL_RAND_RESET_I(32);
    vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__shamt_w = VL_RAND_RESET_I(32);
    vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__k = VL_RAND_RESET_I(5);
    vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__core__DOT__j = VL_RAND_RESET_I(3);
    vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__state = VL_RAND_RESET_I(3);
    vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__pc = VL_RAND_RESET_I(32);
    vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__addr = VL_RAND_RESET_I(32);
    vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__shamt_w = VL_RAND_RESET_I(32);
    vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__k = VL_RAND_RESET_I(5);
    vlSelf->__Vdly__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__core__DOT__j = VL_RAND_RESET_I(3);
    vlSelf->__Vtrigprevexpr___TOP__tb_top_tang__DOT__clk__0 = VL_RAND_RESET_I(1);
    vlSelf->__Vtrigprevexpr___TOP__tb_top_tang__DOT__tx__0 = VL_RAND_RESET_I(1);
}
