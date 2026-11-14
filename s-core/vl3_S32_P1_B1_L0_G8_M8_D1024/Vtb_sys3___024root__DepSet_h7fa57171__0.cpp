// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design implementation internals
// See Vtb_sys3.h for the primary calling header

#include "Vtb_sys3__pch.h"
#include "Vtb_sys3__Syms.h"
#include "Vtb_sys3___024root.h"

#ifdef VL_DEBUG
VL_ATTR_COLD void Vtb_sys3___024root___dump_triggers__act(Vtb_sys3___024root* vlSelf);
#endif  // VL_DEBUG

void Vtb_sys3___024root___eval_triggers__act(Vtb_sys3___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_sys3__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtb_sys3___024root___eval_triggers__act\n"); );
    // Body
    vlSelf->__VactTriggered.set(0U, ((IData)(vlSelf->tb_sys3__DOT__clk) 
                                     & (~ (IData)(vlSelf->__Vtrigprevexpr___TOP__tb_sys3__DOT__clk__0))));
    vlSelf->__VactTriggered.set(1U, ((~ (IData)(vlSelf->tb_sys3__DOT__clk)) 
                                     & (IData)(vlSelf->__Vtrigprevexpr___TOP__tb_sys3__DOT__clk__0)));
    vlSelf->__VactTriggered.set(2U, vlSelf->__VdlySched.awaitingCurrentTime());
    vlSelf->__Vtrigprevexpr___TOP__tb_sys3__DOT__clk__0 
        = vlSelf->tb_sys3__DOT__clk;
#ifdef VL_DEBUG
    if (VL_UNLIKELY(vlSymsp->_vm_contextp__->debug())) {
        Vtb_sys3___024root___dump_triggers__act(vlSelf);
    }
#endif
}

VL_INLINE_OPT void Vtb_sys3___024root___act_comb__TOP__0(Vtb_sys3___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_sys3__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtb_sys3___024root___act_comb__TOP__0\n"); );
    // Body
    vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__0__KET____DOT__id 
        = vlSelf->tb_sys3__DOT__dut__DOT__imem[(0x1fffU 
                                                & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__0__KET____DOT__core.__PVT__pc 
                                                   >> 2U))];
    vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__1__KET____DOT__id 
        = vlSelf->tb_sys3__DOT__dut__DOT__imem[(0x1fffU 
                                                & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__1__KET____DOT__core.__PVT__pc 
                                                   >> 2U))];
    vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__2__KET____DOT__id 
        = vlSelf->tb_sys3__DOT__dut__DOT__imem[(0x1fffU 
                                                & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__2__KET____DOT__core.__PVT__pc 
                                                   >> 2U))];
    vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__3__KET____DOT__id 
        = vlSelf->tb_sys3__DOT__dut__DOT__imem[(0x1fffU 
                                                & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__3__KET____DOT__core.__PVT__pc 
                                                   >> 2U))];
    vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__4__KET____DOT__id 
        = vlSelf->tb_sys3__DOT__dut__DOT__imem[(0x1fffU 
                                                & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__4__KET____DOT__core.__PVT__pc 
                                                   >> 2U))];
    vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__5__KET____DOT__id 
        = vlSelf->tb_sys3__DOT__dut__DOT__imem[(0x1fffU 
                                                & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__5__KET____DOT__core.__PVT__pc 
                                                   >> 2U))];
    vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__6__KET____DOT__id 
        = vlSelf->tb_sys3__DOT__dut__DOT__imem[(0x1fffU 
                                                & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__6__KET____DOT__core.__PVT__pc 
                                                   >> 2U))];
    vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__7__KET____DOT__id 
        = vlSelf->tb_sys3__DOT__dut__DOT__imem[(0x1fffU 
                                                & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__7__KET____DOT__core.__PVT__pc 
                                                   >> 2U))];
    vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__8__KET____DOT__id 
        = vlSelf->tb_sys3__DOT__dut__DOT__imem[(0x1fffU 
                                                & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__8__KET____DOT__core.__PVT__pc 
                                                   >> 2U))];
    vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__9__KET____DOT__id 
        = vlSelf->tb_sys3__DOT__dut__DOT__imem[(0x1fffU 
                                                & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__9__KET____DOT__core.__PVT__pc 
                                                   >> 2U))];
    vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__10__KET____DOT__id 
        = vlSelf->tb_sys3__DOT__dut__DOT__imem[(0x1fffU 
                                                & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__10__KET____DOT__core.__PVT__pc 
                                                   >> 2U))];
    vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__11__KET____DOT__id 
        = vlSelf->tb_sys3__DOT__dut__DOT__imem[(0x1fffU 
                                                & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__11__KET____DOT__core.__PVT__pc 
                                                   >> 2U))];
    vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__12__KET____DOT__id 
        = vlSelf->tb_sys3__DOT__dut__DOT__imem[(0x1fffU 
                                                & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__12__KET____DOT__core.__PVT__pc 
                                                   >> 2U))];
    vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__13__KET____DOT__id 
        = vlSelf->tb_sys3__DOT__dut__DOT__imem[(0x1fffU 
                                                & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__13__KET____DOT__core.__PVT__pc 
                                                   >> 2U))];
    vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__14__KET____DOT__id 
        = vlSelf->tb_sys3__DOT__dut__DOT__imem[(0x1fffU 
                                                & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__14__KET____DOT__core.__PVT__pc 
                                                   >> 2U))];
    vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__15__KET____DOT__id 
        = vlSelf->tb_sys3__DOT__dut__DOT__imem[(0x1fffU 
                                                & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__15__KET____DOT__core.__PVT__pc 
                                                   >> 2U))];
    vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__16__KET____DOT__id 
        = vlSelf->tb_sys3__DOT__dut__DOT__imem[(0x1fffU 
                                                & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__16__KET____DOT__core.__PVT__pc 
                                                   >> 2U))];
    vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__17__KET____DOT__id 
        = vlSelf->tb_sys3__DOT__dut__DOT__imem[(0x1fffU 
                                                & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__17__KET____DOT__core.__PVT__pc 
                                                   >> 2U))];
    vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__18__KET____DOT__id 
        = vlSelf->tb_sys3__DOT__dut__DOT__imem[(0x1fffU 
                                                & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__18__KET____DOT__core.__PVT__pc 
                                                   >> 2U))];
    vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__19__KET____DOT__id 
        = vlSelf->tb_sys3__DOT__dut__DOT__imem[(0x1fffU 
                                                & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__19__KET____DOT__core.__PVT__pc 
                                                   >> 2U))];
    vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__20__KET____DOT__id 
        = vlSelf->tb_sys3__DOT__dut__DOT__imem[(0x1fffU 
                                                & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__20__KET____DOT__core.__PVT__pc 
                                                   >> 2U))];
    vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__21__KET____DOT__id 
        = vlSelf->tb_sys3__DOT__dut__DOT__imem[(0x1fffU 
                                                & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__21__KET____DOT__core.__PVT__pc 
                                                   >> 2U))];
    vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__22__KET____DOT__id 
        = vlSelf->tb_sys3__DOT__dut__DOT__imem[(0x1fffU 
                                                & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__22__KET____DOT__core.__PVT__pc 
                                                   >> 2U))];
    vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__23__KET____DOT__id 
        = vlSelf->tb_sys3__DOT__dut__DOT__imem[(0x1fffU 
                                                & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__23__KET____DOT__core.__PVT__pc 
                                                   >> 2U))];
    vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__24__KET____DOT__id 
        = vlSelf->tb_sys3__DOT__dut__DOT__imem[(0x1fffU 
                                                & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__24__KET____DOT__core.__PVT__pc 
                                                   >> 2U))];
    vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__25__KET____DOT__id 
        = vlSelf->tb_sys3__DOT__dut__DOT__imem[(0x1fffU 
                                                & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__25__KET____DOT__core.__PVT__pc 
                                                   >> 2U))];
    vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__26__KET____DOT__id 
        = vlSelf->tb_sys3__DOT__dut__DOT__imem[(0x1fffU 
                                                & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__26__KET____DOT__core.__PVT__pc 
                                                   >> 2U))];
    vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__27__KET____DOT__id 
        = vlSelf->tb_sys3__DOT__dut__DOT__imem[(0x1fffU 
                                                & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__27__KET____DOT__core.__PVT__pc 
                                                   >> 2U))];
    vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__28__KET____DOT__id 
        = vlSelf->tb_sys3__DOT__dut__DOT__imem[(0x1fffU 
                                                & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__28__KET____DOT__core.__PVT__pc 
                                                   >> 2U))];
    vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__id 
        = vlSelf->tb_sys3__DOT__dut__DOT__imem[(0x1fffU 
                                                & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__pc 
                                                   >> 2U))];
    vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__id 
        = vlSelf->tb_sys3__DOT__dut__DOT__imem[(0x1fffU 
                                                & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__pc 
                                                   >> 2U))];
    vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__id 
        = vlSelf->tb_sys3__DOT__dut__DOT__imem[(0x1fffU 
                                                & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__pc 
                                                   >> 2U))];
}

extern const VlWide<8>/*255:0*/ Vtb_sys3__ConstPool__CONST_h9e67c271_0;

VL_INLINE_OPT void Vtb_sys3___024root___nba_sequent__TOP__0(Vtb_sys3___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_sys3__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtb_sys3___024root___nba_sequent__TOP__0\n"); );
    // Init
    CData/*6:0*/ tb_sys3__DOT__dut__DOT__best_sz;
    tb_sys3__DOT__dut__DOT__best_sz = 0;
    CData/*6:0*/ tb_sys3__DOT__dut__DOT__bsz;
    tb_sys3__DOT__dut__DOT__bsz = 0;
    CData/*6:0*/ tb_sys3__DOT__dut__DOT__blk;
    tb_sys3__DOT__dut__DOT__blk = 0;
    CData/*5:0*/ tb_sys3__DOT__dut__DOT__bbase;
    tb_sys3__DOT__dut__DOT__bbase = 0;
    IData/*31:0*/ tb_sys3__DOT__dut__DOT__wi;
    tb_sys3__DOT__dut__DOT__wi = 0;
    SData/*8:0*/ __Vfunc_tb_sys3__DOT__dut__DOT__pkey__1__Vfuncout;
    __Vfunc_tb_sys3__DOT__dut__DOT__pkey__1__Vfuncout = 0;
    CData/*5:0*/ __Vfunc_tb_sys3__DOT__dut__DOT__pkey__1__prog;
    __Vfunc_tb_sys3__DOT__dut__DOT__pkey__1__prog = 0;
    CData/*2:0*/ __Vfunc_tb_sys3__DOT__dut__DOT__pkey__1__lw;
    __Vfunc_tb_sys3__DOT__dut__DOT__pkey__1__lw = 0;
    QData/*63:0*/ __Vfunc_tb_sys3__DOT__dut__DOT__gmask__2__Vfuncout;
    __Vfunc_tb_sys3__DOT__dut__DOT__gmask__2__Vfuncout = 0;
    CData/*6:0*/ __Vfunc_tb_sys3__DOT__dut__DOT__gmask__2__w;
    __Vfunc_tb_sys3__DOT__dut__DOT__gmask__2__w = 0;
    SData/*8:0*/ __Vfunc_tb_sys3__DOT__dut__DOT__pkey__3__Vfuncout;
    __Vfunc_tb_sys3__DOT__dut__DOT__pkey__3__Vfuncout = 0;
    CData/*5:0*/ __Vfunc_tb_sys3__DOT__dut__DOT__pkey__3__prog;
    __Vfunc_tb_sys3__DOT__dut__DOT__pkey__3__prog = 0;
    CData/*2:0*/ __Vfunc_tb_sys3__DOT__dut__DOT__pkey__3__lw;
    __Vfunc_tb_sys3__DOT__dut__DOT__pkey__3__lw = 0;
    SData/*14:0*/ __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__0__KET____DOT__dm__v0;
    __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__0__KET____DOT__dm__v0 = 0;
    IData/*31:0*/ __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__0__KET____DOT__dm__v0;
    __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__0__KET____DOT__dm__v0 = 0;
    CData/*0:0*/ __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__0__KET____DOT__dm__v0;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__0__KET____DOT__dm__v0 = 0;
    SData/*14:0*/ __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__1__KET____DOT__dm__v0;
    __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__1__KET____DOT__dm__v0 = 0;
    IData/*31:0*/ __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__1__KET____DOT__dm__v0;
    __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__1__KET____DOT__dm__v0 = 0;
    CData/*0:0*/ __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__1__KET____DOT__dm__v0;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__1__KET____DOT__dm__v0 = 0;
    SData/*14:0*/ __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__2__KET____DOT__dm__v0;
    __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__2__KET____DOT__dm__v0 = 0;
    IData/*31:0*/ __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__2__KET____DOT__dm__v0;
    __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__2__KET____DOT__dm__v0 = 0;
    CData/*0:0*/ __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__2__KET____DOT__dm__v0;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__2__KET____DOT__dm__v0 = 0;
    SData/*14:0*/ __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__3__KET____DOT__dm__v0;
    __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__3__KET____DOT__dm__v0 = 0;
    IData/*31:0*/ __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__3__KET____DOT__dm__v0;
    __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__3__KET____DOT__dm__v0 = 0;
    CData/*0:0*/ __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__3__KET____DOT__dm__v0;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__3__KET____DOT__dm__v0 = 0;
    SData/*14:0*/ __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__4__KET____DOT__dm__v0;
    __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__4__KET____DOT__dm__v0 = 0;
    IData/*31:0*/ __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__4__KET____DOT__dm__v0;
    __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__4__KET____DOT__dm__v0 = 0;
    CData/*0:0*/ __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__4__KET____DOT__dm__v0;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__4__KET____DOT__dm__v0 = 0;
    SData/*14:0*/ __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__5__KET____DOT__dm__v0;
    __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__5__KET____DOT__dm__v0 = 0;
    IData/*31:0*/ __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__5__KET____DOT__dm__v0;
    __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__5__KET____DOT__dm__v0 = 0;
    CData/*0:0*/ __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__5__KET____DOT__dm__v0;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__5__KET____DOT__dm__v0 = 0;
    SData/*14:0*/ __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__6__KET____DOT__dm__v0;
    __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__6__KET____DOT__dm__v0 = 0;
    IData/*31:0*/ __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__6__KET____DOT__dm__v0;
    __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__6__KET____DOT__dm__v0 = 0;
    CData/*0:0*/ __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__6__KET____DOT__dm__v0;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__6__KET____DOT__dm__v0 = 0;
    SData/*14:0*/ __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__7__KET____DOT__dm__v0;
    __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__7__KET____DOT__dm__v0 = 0;
    IData/*31:0*/ __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__7__KET____DOT__dm__v0;
    __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__7__KET____DOT__dm__v0 = 0;
    CData/*0:0*/ __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__7__KET____DOT__dm__v0;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__7__KET____DOT__dm__v0 = 0;
    SData/*14:0*/ __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__8__KET____DOT__dm__v0;
    __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__8__KET____DOT__dm__v0 = 0;
    IData/*31:0*/ __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__8__KET____DOT__dm__v0;
    __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__8__KET____DOT__dm__v0 = 0;
    CData/*0:0*/ __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__8__KET____DOT__dm__v0;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__8__KET____DOT__dm__v0 = 0;
    SData/*14:0*/ __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__9__KET____DOT__dm__v0;
    __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__9__KET____DOT__dm__v0 = 0;
    IData/*31:0*/ __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__9__KET____DOT__dm__v0;
    __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__9__KET____DOT__dm__v0 = 0;
    CData/*0:0*/ __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__9__KET____DOT__dm__v0;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__9__KET____DOT__dm__v0 = 0;
    SData/*14:0*/ __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__10__KET____DOT__dm__v0;
    __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__10__KET____DOT__dm__v0 = 0;
    IData/*31:0*/ __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__10__KET____DOT__dm__v0;
    __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__10__KET____DOT__dm__v0 = 0;
    CData/*0:0*/ __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__10__KET____DOT__dm__v0;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__10__KET____DOT__dm__v0 = 0;
    SData/*14:0*/ __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__11__KET____DOT__dm__v0;
    __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__11__KET____DOT__dm__v0 = 0;
    IData/*31:0*/ __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__11__KET____DOT__dm__v0;
    __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__11__KET____DOT__dm__v0 = 0;
    CData/*0:0*/ __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__11__KET____DOT__dm__v0;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__11__KET____DOT__dm__v0 = 0;
    SData/*14:0*/ __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__12__KET____DOT__dm__v0;
    __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__12__KET____DOT__dm__v0 = 0;
    IData/*31:0*/ __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__12__KET____DOT__dm__v0;
    __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__12__KET____DOT__dm__v0 = 0;
    CData/*0:0*/ __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__12__KET____DOT__dm__v0;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__12__KET____DOT__dm__v0 = 0;
    SData/*14:0*/ __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__13__KET____DOT__dm__v0;
    __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__13__KET____DOT__dm__v0 = 0;
    IData/*31:0*/ __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__13__KET____DOT__dm__v0;
    __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__13__KET____DOT__dm__v0 = 0;
    CData/*0:0*/ __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__13__KET____DOT__dm__v0;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__13__KET____DOT__dm__v0 = 0;
    SData/*14:0*/ __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__14__KET____DOT__dm__v0;
    __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__14__KET____DOT__dm__v0 = 0;
    IData/*31:0*/ __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__14__KET____DOT__dm__v0;
    __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__14__KET____DOT__dm__v0 = 0;
    CData/*0:0*/ __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__14__KET____DOT__dm__v0;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__14__KET____DOT__dm__v0 = 0;
    SData/*14:0*/ __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__15__KET____DOT__dm__v0;
    __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__15__KET____DOT__dm__v0 = 0;
    IData/*31:0*/ __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__15__KET____DOT__dm__v0;
    __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__15__KET____DOT__dm__v0 = 0;
    CData/*0:0*/ __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__15__KET____DOT__dm__v0;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__15__KET____DOT__dm__v0 = 0;
    SData/*14:0*/ __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__16__KET____DOT__dm__v0;
    __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__16__KET____DOT__dm__v0 = 0;
    IData/*31:0*/ __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__16__KET____DOT__dm__v0;
    __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__16__KET____DOT__dm__v0 = 0;
    CData/*0:0*/ __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__16__KET____DOT__dm__v0;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__16__KET____DOT__dm__v0 = 0;
    SData/*14:0*/ __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__17__KET____DOT__dm__v0;
    __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__17__KET____DOT__dm__v0 = 0;
    IData/*31:0*/ __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__17__KET____DOT__dm__v0;
    __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__17__KET____DOT__dm__v0 = 0;
    CData/*0:0*/ __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__17__KET____DOT__dm__v0;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__17__KET____DOT__dm__v0 = 0;
    SData/*14:0*/ __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__18__KET____DOT__dm__v0;
    __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__18__KET____DOT__dm__v0 = 0;
    IData/*31:0*/ __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__18__KET____DOT__dm__v0;
    __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__18__KET____DOT__dm__v0 = 0;
    CData/*0:0*/ __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__18__KET____DOT__dm__v0;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__18__KET____DOT__dm__v0 = 0;
    SData/*14:0*/ __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__19__KET____DOT__dm__v0;
    __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__19__KET____DOT__dm__v0 = 0;
    IData/*31:0*/ __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__19__KET____DOT__dm__v0;
    __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__19__KET____DOT__dm__v0 = 0;
    CData/*0:0*/ __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__19__KET____DOT__dm__v0;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__19__KET____DOT__dm__v0 = 0;
    SData/*14:0*/ __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__20__KET____DOT__dm__v0;
    __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__20__KET____DOT__dm__v0 = 0;
    IData/*31:0*/ __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__20__KET____DOT__dm__v0;
    __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__20__KET____DOT__dm__v0 = 0;
    CData/*0:0*/ __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__20__KET____DOT__dm__v0;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__20__KET____DOT__dm__v0 = 0;
    SData/*14:0*/ __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__21__KET____DOT__dm__v0;
    __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__21__KET____DOT__dm__v0 = 0;
    IData/*31:0*/ __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__21__KET____DOT__dm__v0;
    __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__21__KET____DOT__dm__v0 = 0;
    CData/*0:0*/ __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__21__KET____DOT__dm__v0;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__21__KET____DOT__dm__v0 = 0;
    SData/*14:0*/ __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__22__KET____DOT__dm__v0;
    __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__22__KET____DOT__dm__v0 = 0;
    IData/*31:0*/ __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__22__KET____DOT__dm__v0;
    __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__22__KET____DOT__dm__v0 = 0;
    CData/*0:0*/ __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__22__KET____DOT__dm__v0;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__22__KET____DOT__dm__v0 = 0;
    SData/*14:0*/ __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__23__KET____DOT__dm__v0;
    __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__23__KET____DOT__dm__v0 = 0;
    IData/*31:0*/ __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__23__KET____DOT__dm__v0;
    __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__23__KET____DOT__dm__v0 = 0;
    CData/*0:0*/ __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__23__KET____DOT__dm__v0;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__23__KET____DOT__dm__v0 = 0;
    SData/*14:0*/ __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__24__KET____DOT__dm__v0;
    __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__24__KET____DOT__dm__v0 = 0;
    IData/*31:0*/ __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__24__KET____DOT__dm__v0;
    __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__24__KET____DOT__dm__v0 = 0;
    CData/*0:0*/ __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__24__KET____DOT__dm__v0;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__24__KET____DOT__dm__v0 = 0;
    SData/*14:0*/ __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__25__KET____DOT__dm__v0;
    __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__25__KET____DOT__dm__v0 = 0;
    IData/*31:0*/ __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__25__KET____DOT__dm__v0;
    __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__25__KET____DOT__dm__v0 = 0;
    CData/*0:0*/ __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__25__KET____DOT__dm__v0;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__25__KET____DOT__dm__v0 = 0;
    SData/*14:0*/ __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__26__KET____DOT__dm__v0;
    __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__26__KET____DOT__dm__v0 = 0;
    IData/*31:0*/ __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__26__KET____DOT__dm__v0;
    __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__26__KET____DOT__dm__v0 = 0;
    CData/*0:0*/ __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__26__KET____DOT__dm__v0;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__26__KET____DOT__dm__v0 = 0;
    SData/*14:0*/ __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__27__KET____DOT__dm__v0;
    __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__27__KET____DOT__dm__v0 = 0;
    IData/*31:0*/ __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__27__KET____DOT__dm__v0;
    __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__27__KET____DOT__dm__v0 = 0;
    CData/*0:0*/ __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__27__KET____DOT__dm__v0;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__27__KET____DOT__dm__v0 = 0;
    SData/*14:0*/ __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__28__KET____DOT__dm__v0;
    __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__28__KET____DOT__dm__v0 = 0;
    IData/*31:0*/ __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__28__KET____DOT__dm__v0;
    __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__28__KET____DOT__dm__v0 = 0;
    CData/*0:0*/ __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__28__KET____DOT__dm__v0;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__28__KET____DOT__dm__v0 = 0;
    SData/*14:0*/ __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__dm__v0;
    __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__dm__v0 = 0;
    IData/*31:0*/ __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__dm__v0;
    __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__dm__v0 = 0;
    CData/*0:0*/ __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__dm__v0;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__dm__v0 = 0;
    SData/*14:0*/ __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__dm__v0;
    __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__dm__v0 = 0;
    IData/*31:0*/ __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__dm__v0;
    __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__dm__v0 = 0;
    CData/*0:0*/ __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__dm__v0;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__dm__v0 = 0;
    SData/*14:0*/ __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__dm__v0;
    __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__dm__v0 = 0;
    IData/*31:0*/ __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__dm__v0;
    __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__dm__v0 = 0;
    CData/*0:0*/ __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__dm__v0;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__dm__v0 = 0;
    QData/*63:0*/ __Vdly__tb_sys3__DOT__dut__DOT__slice_busy;
    __Vdly__tb_sys3__DOT__dut__DOT__slice_busy = 0;
    IData/*31:0*/ __Vdly__tb_sys3__DOT__dut__DOT__busy_l;
    __Vdly__tb_sys3__DOT__dut__DOT__busy_l = 0;
    VlWide<8>/*255:0*/ __Vdly__tb_sys3__DOT__dut__DOT__req_tab;
    VL_ZERO_W(256, __Vdly__tb_sys3__DOT__dut__DOT__req_tab);
    IData/*31:0*/ __Vdly__tb_sys3__DOT__dut__DOT__fin_sent;
    __Vdly__tb_sys3__DOT__dut__DOT__fin_sent = 0;
    IData/*31:0*/ __Vdly__tb_sys3__DOT__dut__DOT__qc_wr;
    __Vdly__tb_sys3__DOT__dut__DOT__qc_wr = 0;
    IData/*31:0*/ __Vdly__tb_sys3__DOT__dut__DOT__qc_rd;
    __Vdly__tb_sys3__DOT__dut__DOT__qc_rd = 0;
    IData/*31:0*/ __Vdly__tb_sys3__DOT__dut__DOT__done_count;
    __Vdly__tb_sys3__DOT__dut__DOT__done_count = 0;
    IData/*31:0*/ __Vdly__tb_sys3__DOT__dut__DOT__ev_cnt;
    __Vdly__tb_sys3__DOT__dut__DOT__ev_cnt = 0;
    QData/*63:0*/ __Vdly__tb_sys3__DOT__dut__DOT__busy_slice_cycles;
    __Vdly__tb_sys3__DOT__dut__DOT__busy_slice_cycles = 0;
    QData/*63:0*/ __Vdly__tb_sys3__DOT__dut__DOT__waste_blocked;
    __Vdly__tb_sys3__DOT__dut__DOT__waste_blocked = 0;
    QData/*63:0*/ __Vdly__tb_sys3__DOT__dut__DOT__waste_tail;
    __Vdly__tb_sys3__DOT__dut__DOT__waste_tail = 0;
    QData/*63:0*/ __Vdly__tb_sys3__DOT__dut__DOT__search_cycles;
    __Vdly__tb_sys3__DOT__dut__DOT__search_cycles = 0;
    IData/*31:0*/ __Vdly__tb_sys3__DOT__dut__DOT__launch_err;
    __Vdly__tb_sys3__DOT__dut__DOT__launch_err = 0;
    IData/*31:0*/ __Vdly__tb_sys3__DOT__dut__DOT__dispatches;
    __Vdly__tb_sys3__DOT__dut__DOT__dispatches = 0;
    CData/*1:0*/ __Vdly__tb_sys3__DOT__dut__DOT__dstate;
    __Vdly__tb_sys3__DOT__dut__DOT__dstate = 0;
    CData/*0:0*/ __Vdly__tb_sys3__DOT__dut__DOT__rescan;
    __Vdly__tb_sys3__DOT__dut__DOT__rescan = 0;
    CData/*0:0*/ __Vdly__tb_sys3__DOT__dut__DOT__ph;
    __Vdly__tb_sys3__DOT__dut__DOT__ph = 0;
    CData/*5:0*/ __Vdly__tb_sys3__DOT__dut__DOT__cand;
    __Vdly__tb_sys3__DOT__dut__DOT__cand = 0;
    IData/*31:0*/ __Vdly__tb_sys3__DOT__dut__DOT__halted_q;
    __Vdly__tb_sys3__DOT__dut__DOT__halted_q = 0;
    CData/*0:0*/ __Vdly__tb_sys3__DOT__dut__DOT__cur_is_crit;
    __Vdly__tb_sys3__DOT__dut__DOT__cur_is_crit = 0;
    SData/*15:0*/ __Vdly__tb_sys3__DOT__dut__DOT__cur_tid;
    __Vdly__tb_sys3__DOT__dut__DOT__cur_tid = 0;
    SData/*15:0*/ __Vdly__tb_sys3__DOT__dut__DOT__cur_code;
    __Vdly__tb_sys3__DOT__dut__DOT__cur_code = 0;
    CData/*2:0*/ __Vdly__tb_sys3__DOT__dut__DOT__cur_lw;
    __Vdly__tb_sys3__DOT__dut__DOT__cur_lw = 0;
    IData/*31:0*/ __Vdly__tb_sys3__DOT__dut__DOT__crit_streak;
    __Vdly__tb_sys3__DOT__dut__DOT__crit_streak = 0;
    IData/*31:0*/ __Vdly__tb_sys3__DOT__dut__DOT__bulk_pass;
    __Vdly__tb_sys3__DOT__dut__DOT__bulk_pass = 0;
    CData/*3:0*/ __Vdly__tb_sys3__DOT__dut__DOT__cur_bk;
    __Vdly__tb_sys3__DOT__dut__DOT__cur_bk = 0;
    CData/*0:0*/ __Vdlyvset__tb_sys3__DOT__dut__DOT__kwr__v0;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__kwr__v0 = 0;
    CData/*0:0*/ __Vdlyvset__tb_sys3__DOT__dut__DOT__kwr__v1;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__kwr__v1 = 0;
    CData/*2:0*/ __Vdlyvdim0__tb_sys3__DOT__dut__DOT__krd__v8;
    __Vdlyvdim0__tb_sys3__DOT__dut__DOT__krd__v8 = 0;
    IData/*31:0*/ __Vdlyvval__tb_sys3__DOT__dut__DOT__krd__v8;
    __Vdlyvval__tb_sys3__DOT__dut__DOT__krd__v8 = 0;
    CData/*0:0*/ __Vdlyvset__tb_sys3__DOT__dut__DOT__krd__v8;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__krd__v8 = 0;
    CData/*4:0*/ __Vdlyvdim0__tb_sys3__DOT__dut__DOT__own_tid__v0;
    __Vdlyvdim0__tb_sys3__DOT__dut__DOT__own_tid__v0 = 0;
    SData/*15:0*/ __Vdlyvval__tb_sys3__DOT__dut__DOT__own_tid__v0;
    __Vdlyvval__tb_sys3__DOT__dut__DOT__own_tid__v0 = 0;
    CData/*0:0*/ __Vdlyvset__tb_sys3__DOT__dut__DOT__own_tid__v0;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__own_tid__v0 = 0;
    CData/*4:0*/ __Vdlyvdim0__tb_sys3__DOT__dut__DOT__own_lw__v0;
    __Vdlyvdim0__tb_sys3__DOT__dut__DOT__own_lw__v0 = 0;
    CData/*2:0*/ __Vdlyvval__tb_sys3__DOT__dut__DOT__own_lw__v0;
    __Vdlyvval__tb_sys3__DOT__dut__DOT__own_lw__v0 = 0;
    CData/*7:0*/ __Vdlyvdim0__tb_sys3__DOT__dut__DOT__t_start__v0;
    __Vdlyvdim0__tb_sys3__DOT__dut__DOT__t_start__v0 = 0;
    IData/*31:0*/ __Vdlyvval__tb_sys3__DOT__dut__DOT__t_start__v0;
    __Vdlyvval__tb_sys3__DOT__dut__DOT__t_start__v0 = 0;
    CData/*7:0*/ __Vdlyvdim0__tb_sys3__DOT__dut__DOT__t_state__v0;
    __Vdlyvdim0__tb_sys3__DOT__dut__DOT__t_state__v0 = 0;
    CData/*7:0*/ __Vdlyvdim0__tb_sys3__DOT__dut__DOT__t_slot__v0;
    __Vdlyvdim0__tb_sys3__DOT__dut__DOT__t_slot__v0 = 0;
    CData/*5:0*/ __Vdlyvval__tb_sys3__DOT__dut__DOT__t_slot__v0;
    __Vdlyvval__tb_sys3__DOT__dut__DOT__t_slot__v0 = 0;
    CData/*7:0*/ __Vdlyvdim0__tb_sys3__DOT__dut__DOT__t_code__v0;
    __Vdlyvdim0__tb_sys3__DOT__dut__DOT__t_code__v0 = 0;
    SData/*15:0*/ __Vdlyvval__tb_sys3__DOT__dut__DOT__t_code__v0;
    __Vdlyvval__tb_sys3__DOT__dut__DOT__t_code__v0 = 0;
    CData/*0:0*/ __Vdlyvset__tb_sys3__DOT__dut__DOT__t_code__v0;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__t_code__v0 = 0;
    CData/*7:0*/ __Vdlyvdim0__tb_sys3__DOT__dut__DOT__t_lw__v0;
    __Vdlyvdim0__tb_sys3__DOT__dut__DOT__t_lw__v0 = 0;
    CData/*2:0*/ __Vdlyvval__tb_sys3__DOT__dut__DOT__t_lw__v0;
    __Vdlyvval__tb_sys3__DOT__dut__DOT__t_lw__v0 = 0;
    CData/*7:0*/ __Vdlyvdim0__tb_sys3__DOT__dut__DOT__t_crit__v0;
    __Vdlyvdim0__tb_sys3__DOT__dut__DOT__t_crit__v0 = 0;
    CData/*0:0*/ __Vdlyvval__tb_sys3__DOT__dut__DOT__t_crit__v0;
    __Vdlyvval__tb_sys3__DOT__dut__DOT__t_crit__v0 = 0;
    CData/*7:0*/ __Vdlyvdim0__tb_sys3__DOT__dut__DOT__t_arr__v0;
    __Vdlyvdim0__tb_sys3__DOT__dut__DOT__t_arr__v0 = 0;
    IData/*31:0*/ __Vdlyvval__tb_sys3__DOT__dut__DOT__t_arr__v0;
    __Vdlyvval__tb_sys3__DOT__dut__DOT__t_arr__v0 = 0;
    CData/*7:0*/ __Vdlyvdim0__tb_sys3__DOT__dut__DOT__t_state__v1;
    __Vdlyvdim0__tb_sys3__DOT__dut__DOT__t_state__v1 = 0;
    CData/*7:0*/ __Vdlyvdim0__tb_sys3__DOT__dut__DOT__qc__v0;
    __Vdlyvdim0__tb_sys3__DOT__dut__DOT__qc__v0 = 0;
    SData/*15:0*/ __Vdlyvval__tb_sys3__DOT__dut__DOT__qc__v0;
    __Vdlyvval__tb_sys3__DOT__dut__DOT__qc__v0 = 0;
    CData/*0:0*/ __Vdlyvset__tb_sys3__DOT__dut__DOT__qc__v0;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__qc__v0 = 0;
    SData/*10:0*/ __Vdlyvdim0__tb_sys3__DOT__dut__DOT__qk__v0;
    __Vdlyvdim0__tb_sys3__DOT__dut__DOT__qk__v0 = 0;
    SData/*15:0*/ __Vdlyvval__tb_sys3__DOT__dut__DOT__qk__v0;
    __Vdlyvval__tb_sys3__DOT__dut__DOT__qk__v0 = 0;
    CData/*0:0*/ __Vdlyvset__tb_sys3__DOT__dut__DOT__qk__v0;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__qk__v0 = 0;
    CData/*2:0*/ __Vdlyvdim0__tb_sys3__DOT__dut__DOT__kwr__v8;
    __Vdlyvdim0__tb_sys3__DOT__dut__DOT__kwr__v8 = 0;
    IData/*31:0*/ __Vdlyvval__tb_sys3__DOT__dut__DOT__kwr__v8;
    __Vdlyvval__tb_sys3__DOT__dut__DOT__kwr__v8 = 0;
    CData/*7:0*/ __Vdlyvdim0__tb_sys3__DOT__dut__DOT__t_pred__v0;
    __Vdlyvdim0__tb_sys3__DOT__dut__DOT__t_pred__v0 = 0;
    IData/*24:0*/ __Vdlyvval__tb_sys3__DOT__dut__DOT__t_pred__v0;
    __Vdlyvval__tb_sys3__DOT__dut__DOT__t_pred__v0 = 0;
    CData/*0:0*/ __Vdlyvset__tb_sys3__DOT__dut__DOT__t_pred__v0;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__t_pred__v0 = 0;
    CData/*7:0*/ __Vdlyvdim0__tb_sys3__DOT__dut__DOT__t_prog__v0;
    __Vdlyvdim0__tb_sys3__DOT__dut__DOT__t_prog__v0 = 0;
    CData/*5:0*/ __Vdlyvval__tb_sys3__DOT__dut__DOT__t_prog__v0;
    __Vdlyvval__tb_sys3__DOT__dut__DOT__t_prog__v0 = 0;
    CData/*7:0*/ __Vdlyvdim0__tb_sys3__DOT__dut__DOT__t_end__v0;
    __Vdlyvdim0__tb_sys3__DOT__dut__DOT__t_end__v0 = 0;
    IData/*31:0*/ __Vdlyvval__tb_sys3__DOT__dut__DOT__t_end__v0;
    __Vdlyvval__tb_sys3__DOT__dut__DOT__t_end__v0 = 0;
    CData/*0:0*/ __Vdlyvset__tb_sys3__DOT__dut__DOT__t_end__v0;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__t_end__v0 = 0;
    CData/*7:0*/ __Vdlyvdim0__tb_sys3__DOT__dut__DOT__t_a0__v0;
    __Vdlyvdim0__tb_sys3__DOT__dut__DOT__t_a0__v0 = 0;
    IData/*31:0*/ __Vdlyvval__tb_sys3__DOT__dut__DOT__t_a0__v0;
    __Vdlyvval__tb_sys3__DOT__dut__DOT__t_a0__v0 = 0;
    CData/*7:0*/ __Vdlyvdim0__tb_sys3__DOT__dut__DOT__t_trap__v0;
    __Vdlyvdim0__tb_sys3__DOT__dut__DOT__t_trap__v0 = 0;
    CData/*0:0*/ __Vdlyvval__tb_sys3__DOT__dut__DOT__t_trap__v0;
    __Vdlyvval__tb_sys3__DOT__dut__DOT__t_trap__v0 = 0;
    CData/*7:0*/ __Vdlyvdim0__tb_sys3__DOT__dut__DOT__t_state__v2;
    __Vdlyvdim0__tb_sys3__DOT__dut__DOT__t_state__v2 = 0;
    SData/*8:0*/ __Vdlyvdim0__tb_sys3__DOT__dut__DOT__prof__v0;
    __Vdlyvdim0__tb_sys3__DOT__dut__DOT__prof__v0 = 0;
    IData/*24:0*/ __Vdlyvval__tb_sys3__DOT__dut__DOT__prof__v0;
    __Vdlyvval__tb_sys3__DOT__dut__DOT__prof__v0 = 0;
    CData/*0:0*/ __Vdlyvset__tb_sys3__DOT__dut__DOT__prof__v0;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__prof__v0 = 0;
    CData/*7:0*/ __Vdlyvdim0__tb_sys3__DOT__dut__DOT__ev_id__v0;
    __Vdlyvdim0__tb_sys3__DOT__dut__DOT__ev_id__v0 = 0;
    CData/*7:0*/ __Vdlyvval__tb_sys3__DOT__dut__DOT__ev_id__v0;
    __Vdlyvval__tb_sys3__DOT__dut__DOT__ev_id__v0 = 0;
    CData/*0:0*/ __Vdlyvset__tb_sys3__DOT__dut__DOT__ev_id__v0;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__ev_id__v0 = 0;
    CData/*7:0*/ __Vdlyvdim0__tb_sys3__DOT__dut__DOT__ev_data__v0;
    __Vdlyvdim0__tb_sys3__DOT__dut__DOT__ev_data__v0 = 0;
    IData/*31:0*/ __Vdlyvval__tb_sys3__DOT__dut__DOT__ev_data__v0;
    __Vdlyvval__tb_sys3__DOT__dut__DOT__ev_data__v0 = 0;
    CData/*7:0*/ __Vdlyvdim0__tb_sys3__DOT__dut__DOT__ev_cyc__v0;
    __Vdlyvdim0__tb_sys3__DOT__dut__DOT__ev_cyc__v0 = 0;
    IData/*31:0*/ __Vdlyvval__tb_sys3__DOT__dut__DOT__ev_cyc__v0;
    __Vdlyvval__tb_sys3__DOT__dut__DOT__ev_cyc__v0 = 0;
    CData/*7:0*/ __Vdlyvdim0__tb_sys3__DOT__dut__DOT__ev_pl__v0;
    __Vdlyvdim0__tb_sys3__DOT__dut__DOT__ev_pl__v0 = 0;
    IData/*31:0*/ __Vdlyvval__tb_sys3__DOT__dut__DOT__ev_pl__v0;
    __Vdlyvval__tb_sys3__DOT__dut__DOT__ev_pl__v0 = 0;
    CData/*0:0*/ __Vdlyvset__tb_sys3__DOT__dut__DOT__ev_pl__v0;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__ev_pl__v0 = 0;
    QData/*63:0*/ __Vtemp_66;
    VlWide<32>/*1023:0*/ __Vtemp_96;
    // Body
    vlSelf->__Vdly__tb_sys3__DOT__ecur = vlSelf->tb_sys3__DOT__ecur;
    vlSelf->__Vdly__tb_sys3__DOT__epend_id = vlSelf->tb_sys3__DOT__epend_id;
    vlSelf->__Vdly__tb_sys3__DOT__epend = vlSelf->tb_sys3__DOT__epend;
    vlSelf->__Vdlyvset__tb_sys3__DOT__evt_setcyc__v0 = 0U;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__dm__v0 = 0U;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__dm__v0 = 0U;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__dm__v0 = 0U;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__28__KET____DOT__dm__v0 = 0U;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__27__KET____DOT__dm__v0 = 0U;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__26__KET____DOT__dm__v0 = 0U;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__25__KET____DOT__dm__v0 = 0U;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__24__KET____DOT__dm__v0 = 0U;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__23__KET____DOT__dm__v0 = 0U;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__22__KET____DOT__dm__v0 = 0U;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__21__KET____DOT__dm__v0 = 0U;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__20__KET____DOT__dm__v0 = 0U;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__19__KET____DOT__dm__v0 = 0U;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__18__KET____DOT__dm__v0 = 0U;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__17__KET____DOT__dm__v0 = 0U;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__16__KET____DOT__dm__v0 = 0U;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__15__KET____DOT__dm__v0 = 0U;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__14__KET____DOT__dm__v0 = 0U;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__13__KET____DOT__dm__v0 = 0U;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__12__KET____DOT__dm__v0 = 0U;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__11__KET____DOT__dm__v0 = 0U;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__10__KET____DOT__dm__v0 = 0U;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__9__KET____DOT__dm__v0 = 0U;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__8__KET____DOT__dm__v0 = 0U;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__7__KET____DOT__dm__v0 = 0U;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__6__KET____DOT__dm__v0 = 0U;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__5__KET____DOT__dm__v0 = 0U;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__4__KET____DOT__dm__v0 = 0U;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__3__KET____DOT__dm__v0 = 0U;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__2__KET____DOT__dm__v0 = 0U;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__1__KET____DOT__dm__v0 = 0U;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__0__KET____DOT__dm__v0 = 0U;
    vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__rf__v0 = 0U;
    vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__rf__v0 = 0U;
    vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__rf__v0 = 0U;
    vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__28__KET____DOT__rf__v0 = 0U;
    vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__27__KET____DOT__rf__v0 = 0U;
    vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__26__KET____DOT__rf__v0 = 0U;
    vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__25__KET____DOT__rf__v0 = 0U;
    vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__24__KET____DOT__rf__v0 = 0U;
    vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__23__KET____DOT__rf__v0 = 0U;
    vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__22__KET____DOT__rf__v0 = 0U;
    vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__21__KET____DOT__rf__v0 = 0U;
    vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__20__KET____DOT__rf__v0 = 0U;
    vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__19__KET____DOT__rf__v0 = 0U;
    vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__18__KET____DOT__rf__v0 = 0U;
    vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__17__KET____DOT__rf__v0 = 0U;
    vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__16__KET____DOT__rf__v0 = 0U;
    vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__15__KET____DOT__rf__v0 = 0U;
    vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__14__KET____DOT__rf__v0 = 0U;
    vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__13__KET____DOT__rf__v0 = 0U;
    vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__12__KET____DOT__rf__v0 = 0U;
    vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__11__KET____DOT__rf__v0 = 0U;
    vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__10__KET____DOT__rf__v0 = 0U;
    vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__9__KET____DOT__rf__v0 = 0U;
    vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__8__KET____DOT__rf__v0 = 0U;
    vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__7__KET____DOT__rf__v0 = 0U;
    vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__6__KET____DOT__rf__v0 = 0U;
    vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__5__KET____DOT__rf__v0 = 0U;
    vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__4__KET____DOT__rf__v0 = 0U;
    vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__3__KET____DOT__rf__v0 = 0U;
    vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__2__KET____DOT__rf__v0 = 0U;
    vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__1__KET____DOT__rf__v0 = 0U;
    vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__0__KET____DOT__rf__v0 = 0U;
    __Vdly__tb_sys3__DOT__dut__DOT__cur_bk = vlSelf->tb_sys3__DOT__dut__DOT__cur_bk;
    __Vdly__tb_sys3__DOT__dut__DOT__bulk_pass = vlSelf->tb_sys3__DOT__dut__DOT__bulk_pass;
    __Vdly__tb_sys3__DOT__dut__DOT__crit_streak = vlSelf->tb_sys3__DOT__dut__DOT__crit_streak;
    __Vdly__tb_sys3__DOT__dut__DOT__cur_code = vlSelf->tb_sys3__DOT__dut__DOT__cur_code;
    __Vdly__tb_sys3__DOT__dut__DOT__cur_tid = vlSelf->tb_sys3__DOT__dut__DOT__cur_tid;
    __Vdly__tb_sys3__DOT__dut__DOT__cur_is_crit = vlSelf->tb_sys3__DOT__dut__DOT__cur_is_crit;
    vlSelf->__Vdly__tb_sys3__DOT__dut__DOT__launch_lw 
        = vlSelf->tb_sys3__DOT__dut__DOT__launch_lw;
    vlSelf->__Vdly__tb_sys3__DOT__dut__DOT__launch_entry 
        = vlSelf->tb_sys3__DOT__dut__DOT__launch_entry;
    __Vdly__tb_sys3__DOT__dut__DOT__halted_q = vlSelf->tb_sys3__DOT__dut__DOT__halted_q;
    vlSelf->__Vdly__tb_sys3__DOT__dut__DOT__start_v 
        = vlSelf->tb_sys3__DOT__dut__DOT__start_v;
    __Vdly__tb_sys3__DOT__dut__DOT__cand = vlSelf->tb_sys3__DOT__dut__DOT__cand;
    __Vdly__tb_sys3__DOT__dut__DOT__ph = vlSelf->tb_sys3__DOT__dut__DOT__ph;
    __Vdly__tb_sys3__DOT__dut__DOT__rescan = vlSelf->tb_sys3__DOT__dut__DOT__rescan;
    __Vdly__tb_sys3__DOT__dut__DOT__dstate = vlSelf->tb_sys3__DOT__dut__DOT__dstate;
    __Vdly__tb_sys3__DOT__dut__DOT__dispatches = vlSelf->tb_sys3__DOT__dut__DOT__dispatches;
    __Vdly__tb_sys3__DOT__dut__DOT__launch_err = vlSelf->tb_sys3__DOT__dut__DOT__launch_err;
    __Vdly__tb_sys3__DOT__dut__DOT__search_cycles = vlSelf->tb_sys3__DOT__dut__DOT__search_cycles;
    __Vdly__tb_sys3__DOT__dut__DOT__waste_tail = vlSelf->tb_sys3__DOT__dut__DOT__waste_tail;
    __Vdly__tb_sys3__DOT__dut__DOT__waste_blocked = vlSelf->tb_sys3__DOT__dut__DOT__waste_blocked;
    __Vdly__tb_sys3__DOT__dut__DOT__busy_slice_cycles 
        = vlSelf->tb_sys3__DOT__dut__DOT__busy_slice_cycles;
    vlSelf->__Vdly__tb_sys3__DOT__dut__DOT__cyc = vlSelf->tb_sys3__DOT__dut__DOT__cyc;
    __Vdly__tb_sys3__DOT__dut__DOT__ev_cnt = vlSelf->tb_sys3__DOT__dut__DOT__ev_cnt;
    __Vdly__tb_sys3__DOT__dut__DOT__done_count = vlSelf->tb_sys3__DOT__dut__DOT__done_count;
    __Vdly__tb_sys3__DOT__dut__DOT__fin_sent = vlSelf->tb_sys3__DOT__dut__DOT__fin_sent;
    __Vdly__tb_sys3__DOT__dut__DOT__busy_l = vlSelf->tb_sys3__DOT__dut__DOT__busy_l;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__ev_pl__v0 = 0U;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__qc__v0 = 0U;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__prof__v0 = 0U;
    __Vdly__tb_sys3__DOT__dut__DOT__qc_rd = vlSelf->tb_sys3__DOT__dut__DOT__qc_rd;
    __Vdly__tb_sys3__DOT__dut__DOT__qc_wr = vlSelf->tb_sys3__DOT__dut__DOT__qc_wr;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__t_pred__v0 = 0U;
    __Vdly__tb_sys3__DOT__dut__DOT__req_tab[0U] = vlSelf->tb_sys3__DOT__dut__DOT__req_tab[0U];
    __Vdly__tb_sys3__DOT__dut__DOT__req_tab[1U] = vlSelf->tb_sys3__DOT__dut__DOT__req_tab[1U];
    __Vdly__tb_sys3__DOT__dut__DOT__req_tab[2U] = vlSelf->tb_sys3__DOT__dut__DOT__req_tab[2U];
    __Vdly__tb_sys3__DOT__dut__DOT__req_tab[3U] = vlSelf->tb_sys3__DOT__dut__DOT__req_tab[3U];
    __Vdly__tb_sys3__DOT__dut__DOT__req_tab[4U] = vlSelf->tb_sys3__DOT__dut__DOT__req_tab[4U];
    __Vdly__tb_sys3__DOT__dut__DOT__req_tab[5U] = vlSelf->tb_sys3__DOT__dut__DOT__req_tab[5U];
    __Vdly__tb_sys3__DOT__dut__DOT__req_tab[6U] = vlSelf->tb_sys3__DOT__dut__DOT__req_tab[6U];
    __Vdly__tb_sys3__DOT__dut__DOT__req_tab[7U] = vlSelf->tb_sys3__DOT__dut__DOT__req_tab[7U];
    __Vdlyvset__tb_sys3__DOT__dut__DOT__ev_id__v0 = 0U;
    __Vdly__tb_sys3__DOT__dut__DOT__slice_busy = vlSelf->tb_sys3__DOT__dut__DOT__slice_busy;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__t_end__v0 = 0U;
    __Vdly__tb_sys3__DOT__dut__DOT__cur_lw = vlSelf->tb_sys3__DOT__dut__DOT__cur_lw;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__krd__v8 = 0U;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__t_code__v0 = 0U;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__own_tid__v0 = 0U;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__qk__v0 = 0U;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__kwr__v0 = 0U;
    __Vdlyvset__tb_sys3__DOT__dut__DOT__kwr__v1 = 0U;
    if (((4U == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__state)) 
         & (0x23U == (0x7fU & vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__ir)))) {
        __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__dm__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.d_wdata;
        __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__dm__v0 = 1U;
        __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__dm__v0 
            = (0x7fffU & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.d_addr));
    }
    if (((4U == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__state)) 
         & (0x23U == (0x7fU & vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__ir)))) {
        __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__dm__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.d_wdata;
        __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__dm__v0 = 1U;
        __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__dm__v0 
            = (0x7fffU & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.d_addr));
    }
    if (((4U == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__state)) 
         & (0x23U == (0x7fU & vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__ir)))) {
        __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__dm__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.d_wdata;
        __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__dm__v0 = 1U;
        __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__dm__v0 
            = (0x7fffU & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.d_addr));
    }
    if (((4U == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__28__KET____DOT__core.__PVT__state)) 
         & (0x23U == (0x7fU & vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__28__KET____DOT__core.__PVT__ir)))) {
        __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__28__KET____DOT__dm__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__28__KET____DOT__core.d_wdata;
        __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__28__KET____DOT__dm__v0 = 1U;
        __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__28__KET____DOT__dm__v0 
            = (0x7fffU & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__28__KET____DOT__core.d_addr));
    }
    if (((4U == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__27__KET____DOT__core.__PVT__state)) 
         & (0x23U == (0x7fU & vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__27__KET____DOT__core.__PVT__ir)))) {
        __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__27__KET____DOT__dm__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__27__KET____DOT__core.d_wdata;
        __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__27__KET____DOT__dm__v0 = 1U;
        __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__27__KET____DOT__dm__v0 
            = (0x7fffU & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__27__KET____DOT__core.d_addr));
    }
    if (((4U == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__26__KET____DOT__core.__PVT__state)) 
         & (0x23U == (0x7fU & vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__26__KET____DOT__core.__PVT__ir)))) {
        __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__26__KET____DOT__dm__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__26__KET____DOT__core.d_wdata;
        __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__26__KET____DOT__dm__v0 = 1U;
        __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__26__KET____DOT__dm__v0 
            = (0x7fffU & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__26__KET____DOT__core.d_addr));
    }
    if (((4U == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__25__KET____DOT__core.__PVT__state)) 
         & (0x23U == (0x7fU & vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__25__KET____DOT__core.__PVT__ir)))) {
        __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__25__KET____DOT__dm__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__25__KET____DOT__core.d_wdata;
        __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__25__KET____DOT__dm__v0 = 1U;
        __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__25__KET____DOT__dm__v0 
            = (0x7fffU & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__25__KET____DOT__core.d_addr));
    }
    if (((4U == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__24__KET____DOT__core.__PVT__state)) 
         & (0x23U == (0x7fU & vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__24__KET____DOT__core.__PVT__ir)))) {
        __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__24__KET____DOT__dm__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__24__KET____DOT__core.d_wdata;
        __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__24__KET____DOT__dm__v0 = 1U;
        __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__24__KET____DOT__dm__v0 
            = (0x7fffU & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__24__KET____DOT__core.d_addr));
    }
    if (((4U == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__23__KET____DOT__core.__PVT__state)) 
         & (0x23U == (0x7fU & vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__23__KET____DOT__core.__PVT__ir)))) {
        __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__23__KET____DOT__dm__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__23__KET____DOT__core.d_wdata;
        __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__23__KET____DOT__dm__v0 = 1U;
        __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__23__KET____DOT__dm__v0 
            = (0x7fffU & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__23__KET____DOT__core.d_addr));
    }
    if (((4U == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__22__KET____DOT__core.__PVT__state)) 
         & (0x23U == (0x7fU & vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__22__KET____DOT__core.__PVT__ir)))) {
        __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__22__KET____DOT__dm__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__22__KET____DOT__core.d_wdata;
        __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__22__KET____DOT__dm__v0 = 1U;
        __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__22__KET____DOT__dm__v0 
            = (0x7fffU & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__22__KET____DOT__core.d_addr));
    }
    if (((4U == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__21__KET____DOT__core.__PVT__state)) 
         & (0x23U == (0x7fU & vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__21__KET____DOT__core.__PVT__ir)))) {
        __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__21__KET____DOT__dm__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__21__KET____DOT__core.d_wdata;
        __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__21__KET____DOT__dm__v0 = 1U;
        __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__21__KET____DOT__dm__v0 
            = (0x7fffU & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__21__KET____DOT__core.d_addr));
    }
    if (((4U == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__20__KET____DOT__core.__PVT__state)) 
         & (0x23U == (0x7fU & vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__20__KET____DOT__core.__PVT__ir)))) {
        __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__20__KET____DOT__dm__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__20__KET____DOT__core.d_wdata;
        __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__20__KET____DOT__dm__v0 = 1U;
        __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__20__KET____DOT__dm__v0 
            = (0x7fffU & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__20__KET____DOT__core.d_addr));
    }
    if (((4U == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__19__KET____DOT__core.__PVT__state)) 
         & (0x23U == (0x7fU & vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__19__KET____DOT__core.__PVT__ir)))) {
        __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__19__KET____DOT__dm__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__19__KET____DOT__core.d_wdata;
        __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__19__KET____DOT__dm__v0 = 1U;
        __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__19__KET____DOT__dm__v0 
            = (0x7fffU & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__19__KET____DOT__core.d_addr));
    }
    if (((4U == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__18__KET____DOT__core.__PVT__state)) 
         & (0x23U == (0x7fU & vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__18__KET____DOT__core.__PVT__ir)))) {
        __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__18__KET____DOT__dm__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__18__KET____DOT__core.d_wdata;
        __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__18__KET____DOT__dm__v0 = 1U;
        __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__18__KET____DOT__dm__v0 
            = (0x7fffU & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__18__KET____DOT__core.d_addr));
    }
    if (((4U == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__17__KET____DOT__core.__PVT__state)) 
         & (0x23U == (0x7fU & vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__17__KET____DOT__core.__PVT__ir)))) {
        __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__17__KET____DOT__dm__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__17__KET____DOT__core.d_wdata;
        __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__17__KET____DOT__dm__v0 = 1U;
        __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__17__KET____DOT__dm__v0 
            = (0x7fffU & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__17__KET____DOT__core.d_addr));
    }
    if (((4U == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__16__KET____DOT__core.__PVT__state)) 
         & (0x23U == (0x7fU & vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__16__KET____DOT__core.__PVT__ir)))) {
        __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__16__KET____DOT__dm__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__16__KET____DOT__core.d_wdata;
        __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__16__KET____DOT__dm__v0 = 1U;
        __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__16__KET____DOT__dm__v0 
            = (0x7fffU & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__16__KET____DOT__core.d_addr));
    }
    if (((4U == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__15__KET____DOT__core.__PVT__state)) 
         & (0x23U == (0x7fU & vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__15__KET____DOT__core.__PVT__ir)))) {
        __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__15__KET____DOT__dm__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__15__KET____DOT__core.d_wdata;
        __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__15__KET____DOT__dm__v0 = 1U;
        __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__15__KET____DOT__dm__v0 
            = (0x7fffU & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__15__KET____DOT__core.d_addr));
    }
    if (((4U == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__14__KET____DOT__core.__PVT__state)) 
         & (0x23U == (0x7fU & vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__14__KET____DOT__core.__PVT__ir)))) {
        __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__14__KET____DOT__dm__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__14__KET____DOT__core.d_wdata;
        __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__14__KET____DOT__dm__v0 = 1U;
        __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__14__KET____DOT__dm__v0 
            = (0x7fffU & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__14__KET____DOT__core.d_addr));
    }
    if (((4U == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__13__KET____DOT__core.__PVT__state)) 
         & (0x23U == (0x7fU & vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__13__KET____DOT__core.__PVT__ir)))) {
        __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__13__KET____DOT__dm__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__13__KET____DOT__core.d_wdata;
        __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__13__KET____DOT__dm__v0 = 1U;
        __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__13__KET____DOT__dm__v0 
            = (0x7fffU & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__13__KET____DOT__core.d_addr));
    }
    if (((4U == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__12__KET____DOT__core.__PVT__state)) 
         & (0x23U == (0x7fU & vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__12__KET____DOT__core.__PVT__ir)))) {
        __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__12__KET____DOT__dm__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__12__KET____DOT__core.d_wdata;
        __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__12__KET____DOT__dm__v0 = 1U;
        __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__12__KET____DOT__dm__v0 
            = (0x7fffU & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__12__KET____DOT__core.d_addr));
    }
    if (((4U == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__11__KET____DOT__core.__PVT__state)) 
         & (0x23U == (0x7fU & vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__11__KET____DOT__core.__PVT__ir)))) {
        __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__11__KET____DOT__dm__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__11__KET____DOT__core.d_wdata;
        __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__11__KET____DOT__dm__v0 = 1U;
        __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__11__KET____DOT__dm__v0 
            = (0x7fffU & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__11__KET____DOT__core.d_addr));
    }
    if (((4U == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__10__KET____DOT__core.__PVT__state)) 
         & (0x23U == (0x7fU & vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__10__KET____DOT__core.__PVT__ir)))) {
        __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__10__KET____DOT__dm__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__10__KET____DOT__core.d_wdata;
        __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__10__KET____DOT__dm__v0 = 1U;
        __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__10__KET____DOT__dm__v0 
            = (0x7fffU & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__10__KET____DOT__core.d_addr));
    }
    if (((4U == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__9__KET____DOT__core.__PVT__state)) 
         & (0x23U == (0x7fU & vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__9__KET____DOT__core.__PVT__ir)))) {
        __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__9__KET____DOT__dm__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__9__KET____DOT__core.d_wdata;
        __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__9__KET____DOT__dm__v0 = 1U;
        __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__9__KET____DOT__dm__v0 
            = (0x7fffU & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__9__KET____DOT__core.d_addr));
    }
    if (((4U == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__8__KET____DOT__core.__PVT__state)) 
         & (0x23U == (0x7fU & vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__8__KET____DOT__core.__PVT__ir)))) {
        __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__8__KET____DOT__dm__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__8__KET____DOT__core.d_wdata;
        __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__8__KET____DOT__dm__v0 = 1U;
        __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__8__KET____DOT__dm__v0 
            = (0x7fffU & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__8__KET____DOT__core.d_addr));
    }
    if (((4U == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__7__KET____DOT__core.__PVT__state)) 
         & (0x23U == (0x7fU & vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__7__KET____DOT__core.__PVT__ir)))) {
        __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__7__KET____DOT__dm__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__7__KET____DOT__core.d_wdata;
        __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__7__KET____DOT__dm__v0 = 1U;
        __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__7__KET____DOT__dm__v0 
            = (0x7fffU & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__7__KET____DOT__core.d_addr));
    }
    if (((4U == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__6__KET____DOT__core.__PVT__state)) 
         & (0x23U == (0x7fU & vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__6__KET____DOT__core.__PVT__ir)))) {
        __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__6__KET____DOT__dm__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__6__KET____DOT__core.d_wdata;
        __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__6__KET____DOT__dm__v0 = 1U;
        __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__6__KET____DOT__dm__v0 
            = (0x7fffU & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__6__KET____DOT__core.d_addr));
    }
    if (((4U == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__5__KET____DOT__core.__PVT__state)) 
         & (0x23U == (0x7fU & vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__5__KET____DOT__core.__PVT__ir)))) {
        __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__5__KET____DOT__dm__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__5__KET____DOT__core.d_wdata;
        __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__5__KET____DOT__dm__v0 = 1U;
        __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__5__KET____DOT__dm__v0 
            = (0x7fffU & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__5__KET____DOT__core.d_addr));
    }
    if (((4U == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__4__KET____DOT__core.__PVT__state)) 
         & (0x23U == (0x7fU & vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__4__KET____DOT__core.__PVT__ir)))) {
        __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__4__KET____DOT__dm__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__4__KET____DOT__core.d_wdata;
        __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__4__KET____DOT__dm__v0 = 1U;
        __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__4__KET____DOT__dm__v0 
            = (0x7fffU & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__4__KET____DOT__core.d_addr));
    }
    if (((4U == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__3__KET____DOT__core.__PVT__state)) 
         & (0x23U == (0x7fU & vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__3__KET____DOT__core.__PVT__ir)))) {
        __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__3__KET____DOT__dm__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__3__KET____DOT__core.d_wdata;
        __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__3__KET____DOT__dm__v0 = 1U;
        __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__3__KET____DOT__dm__v0 
            = (0x7fffU & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__3__KET____DOT__core.d_addr));
    }
    if (((4U == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__2__KET____DOT__core.__PVT__state)) 
         & (0x23U == (0x7fU & vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__2__KET____DOT__core.__PVT__ir)))) {
        __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__2__KET____DOT__dm__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__2__KET____DOT__core.d_wdata;
        __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__2__KET____DOT__dm__v0 = 1U;
        __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__2__KET____DOT__dm__v0 
            = (0x7fffU & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__2__KET____DOT__core.d_addr));
    }
    if (((4U == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__1__KET____DOT__core.__PVT__state)) 
         & (0x23U == (0x7fU & vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__1__KET____DOT__core.__PVT__ir)))) {
        __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__1__KET____DOT__dm__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__1__KET____DOT__core.d_wdata;
        __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__1__KET____DOT__dm__v0 = 1U;
        __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__1__KET____DOT__dm__v0 
            = (0x7fffU & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__1__KET____DOT__core.d_addr));
    }
    if (((4U == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__0__KET____DOT__core.__PVT__state)) 
         & (0x23U == (0x7fU & vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__0__KET____DOT__core.__PVT__ir)))) {
        __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__0__KET____DOT__dm__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__0__KET____DOT__core.d_wdata;
        __Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__0__KET____DOT__dm__v0 = 1U;
        __Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__0__KET____DOT__dm__v0 
            = (0x7fffU & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__0__KET____DOT__core.d_addr));
    }
    if (((~ ((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__halted_r) 
             | (0U == (0x1fU & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__ir 
                                >> 7U))))) & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__we))) {
        vlSelf->__Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__rf__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__wd;
        vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__rf__v0 = 1U;
        vlSelf->__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__rf__v0 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__ir 
                          >> 2U)) | (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__k));
    }
    if (((~ ((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__halted_r) 
             | (0U == (0x1fU & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__ir 
                                >> 7U))))) & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__we))) {
        vlSelf->__Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__rf__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__wd;
        vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__rf__v0 = 1U;
        vlSelf->__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__rf__v0 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__ir 
                          >> 2U)) | (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__k));
    }
    if (((~ ((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__halted_r) 
             | (0U == (0x1fU & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__ir 
                                >> 7U))))) & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__we))) {
        vlSelf->__Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__rf__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__wd;
        vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__rf__v0 = 1U;
        vlSelf->__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__rf__v0 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__ir 
                          >> 2U)) | (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__k));
    }
    if (((~ ((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__28__KET____DOT__core.__PVT__halted_r) 
             | (0U == (0x1fU & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__28__KET____DOT__core.__PVT__ir 
                                >> 7U))))) & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__28__KET____DOT__core.__PVT__we))) {
        vlSelf->__Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__28__KET____DOT__rf__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__28__KET____DOT__core.__PVT__wd;
        vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__28__KET____DOT__rf__v0 = 1U;
        vlSelf->__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__28__KET____DOT__rf__v0 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__28__KET____DOT__core.__PVT__ir 
                          >> 2U)) | (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__28__KET____DOT__core.__PVT__k));
    }
    if (((~ ((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__27__KET____DOT__core.__PVT__halted_r) 
             | (0U == (0x1fU & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__27__KET____DOT__core.__PVT__ir 
                                >> 7U))))) & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__27__KET____DOT__core.__PVT__we))) {
        vlSelf->__Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__27__KET____DOT__rf__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__27__KET____DOT__core.__PVT__wd;
        vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__27__KET____DOT__rf__v0 = 1U;
        vlSelf->__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__27__KET____DOT__rf__v0 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__27__KET____DOT__core.__PVT__ir 
                          >> 2U)) | (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__27__KET____DOT__core.__PVT__k));
    }
    if (((~ ((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__26__KET____DOT__core.__PVT__halted_r) 
             | (0U == (0x1fU & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__26__KET____DOT__core.__PVT__ir 
                                >> 7U))))) & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__26__KET____DOT__core.__PVT__we))) {
        vlSelf->__Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__26__KET____DOT__rf__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__26__KET____DOT__core.__PVT__wd;
        vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__26__KET____DOT__rf__v0 = 1U;
        vlSelf->__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__26__KET____DOT__rf__v0 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__26__KET____DOT__core.__PVT__ir 
                          >> 2U)) | (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__26__KET____DOT__core.__PVT__k));
    }
    if (((~ ((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__25__KET____DOT__core.__PVT__halted_r) 
             | (0U == (0x1fU & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__25__KET____DOT__core.__PVT__ir 
                                >> 7U))))) & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__25__KET____DOT__core.__PVT__we))) {
        vlSelf->__Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__25__KET____DOT__rf__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__25__KET____DOT__core.__PVT__wd;
        vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__25__KET____DOT__rf__v0 = 1U;
        vlSelf->__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__25__KET____DOT__rf__v0 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__25__KET____DOT__core.__PVT__ir 
                          >> 2U)) | (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__25__KET____DOT__core.__PVT__k));
    }
    if (((~ ((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__24__KET____DOT__core.__PVT__halted_r) 
             | (0U == (0x1fU & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__24__KET____DOT__core.__PVT__ir 
                                >> 7U))))) & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__24__KET____DOT__core.__PVT__we))) {
        vlSelf->__Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__24__KET____DOT__rf__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__24__KET____DOT__core.__PVT__wd;
        vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__24__KET____DOT__rf__v0 = 1U;
        vlSelf->__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__24__KET____DOT__rf__v0 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__24__KET____DOT__core.__PVT__ir 
                          >> 2U)) | (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__24__KET____DOT__core.__PVT__k));
    }
    if (((~ ((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__23__KET____DOT__core.__PVT__halted_r) 
             | (0U == (0x1fU & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__23__KET____DOT__core.__PVT__ir 
                                >> 7U))))) & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__23__KET____DOT__core.__PVT__we))) {
        vlSelf->__Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__23__KET____DOT__rf__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__23__KET____DOT__core.__PVT__wd;
        vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__23__KET____DOT__rf__v0 = 1U;
        vlSelf->__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__23__KET____DOT__rf__v0 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__23__KET____DOT__core.__PVT__ir 
                          >> 2U)) | (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__23__KET____DOT__core.__PVT__k));
    }
    if (((~ ((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__22__KET____DOT__core.__PVT__halted_r) 
             | (0U == (0x1fU & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__22__KET____DOT__core.__PVT__ir 
                                >> 7U))))) & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__22__KET____DOT__core.__PVT__we))) {
        vlSelf->__Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__22__KET____DOT__rf__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__22__KET____DOT__core.__PVT__wd;
        vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__22__KET____DOT__rf__v0 = 1U;
        vlSelf->__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__22__KET____DOT__rf__v0 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__22__KET____DOT__core.__PVT__ir 
                          >> 2U)) | (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__22__KET____DOT__core.__PVT__k));
    }
    if (((~ ((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__21__KET____DOT__core.__PVT__halted_r) 
             | (0U == (0x1fU & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__21__KET____DOT__core.__PVT__ir 
                                >> 7U))))) & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__21__KET____DOT__core.__PVT__we))) {
        vlSelf->__Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__21__KET____DOT__rf__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__21__KET____DOT__core.__PVT__wd;
        vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__21__KET____DOT__rf__v0 = 1U;
        vlSelf->__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__21__KET____DOT__rf__v0 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__21__KET____DOT__core.__PVT__ir 
                          >> 2U)) | (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__21__KET____DOT__core.__PVT__k));
    }
    if (((~ ((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__20__KET____DOT__core.__PVT__halted_r) 
             | (0U == (0x1fU & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__20__KET____DOT__core.__PVT__ir 
                                >> 7U))))) & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__20__KET____DOT__core.__PVT__we))) {
        vlSelf->__Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__20__KET____DOT__rf__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__20__KET____DOT__core.__PVT__wd;
        vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__20__KET____DOT__rf__v0 = 1U;
        vlSelf->__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__20__KET____DOT__rf__v0 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__20__KET____DOT__core.__PVT__ir 
                          >> 2U)) | (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__20__KET____DOT__core.__PVT__k));
    }
    if (((~ ((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__19__KET____DOT__core.__PVT__halted_r) 
             | (0U == (0x1fU & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__19__KET____DOT__core.__PVT__ir 
                                >> 7U))))) & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__19__KET____DOT__core.__PVT__we))) {
        vlSelf->__Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__19__KET____DOT__rf__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__19__KET____DOT__core.__PVT__wd;
        vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__19__KET____DOT__rf__v0 = 1U;
        vlSelf->__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__19__KET____DOT__rf__v0 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__19__KET____DOT__core.__PVT__ir 
                          >> 2U)) | (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__19__KET____DOT__core.__PVT__k));
    }
    if (((~ ((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__18__KET____DOT__core.__PVT__halted_r) 
             | (0U == (0x1fU & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__18__KET____DOT__core.__PVT__ir 
                                >> 7U))))) & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__18__KET____DOT__core.__PVT__we))) {
        vlSelf->__Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__18__KET____DOT__rf__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__18__KET____DOT__core.__PVT__wd;
        vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__18__KET____DOT__rf__v0 = 1U;
        vlSelf->__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__18__KET____DOT__rf__v0 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__18__KET____DOT__core.__PVT__ir 
                          >> 2U)) | (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__18__KET____DOT__core.__PVT__k));
    }
    if (((~ ((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__17__KET____DOT__core.__PVT__halted_r) 
             | (0U == (0x1fU & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__17__KET____DOT__core.__PVT__ir 
                                >> 7U))))) & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__17__KET____DOT__core.__PVT__we))) {
        vlSelf->__Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__17__KET____DOT__rf__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__17__KET____DOT__core.__PVT__wd;
        vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__17__KET____DOT__rf__v0 = 1U;
        vlSelf->__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__17__KET____DOT__rf__v0 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__17__KET____DOT__core.__PVT__ir 
                          >> 2U)) | (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__17__KET____DOT__core.__PVT__k));
    }
    if (((~ ((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__16__KET____DOT__core.__PVT__halted_r) 
             | (0U == (0x1fU & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__16__KET____DOT__core.__PVT__ir 
                                >> 7U))))) & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__16__KET____DOT__core.__PVT__we))) {
        vlSelf->__Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__16__KET____DOT__rf__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__16__KET____DOT__core.__PVT__wd;
        vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__16__KET____DOT__rf__v0 = 1U;
        vlSelf->__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__16__KET____DOT__rf__v0 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__16__KET____DOT__core.__PVT__ir 
                          >> 2U)) | (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__16__KET____DOT__core.__PVT__k));
    }
    if (((~ ((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__15__KET____DOT__core.__PVT__halted_r) 
             | (0U == (0x1fU & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__15__KET____DOT__core.__PVT__ir 
                                >> 7U))))) & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__15__KET____DOT__core.__PVT__we))) {
        vlSelf->__Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__15__KET____DOT__rf__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__15__KET____DOT__core.__PVT__wd;
        vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__15__KET____DOT__rf__v0 = 1U;
        vlSelf->__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__15__KET____DOT__rf__v0 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__15__KET____DOT__core.__PVT__ir 
                          >> 2U)) | (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__15__KET____DOT__core.__PVT__k));
    }
    if (((~ ((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__14__KET____DOT__core.__PVT__halted_r) 
             | (0U == (0x1fU & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__14__KET____DOT__core.__PVT__ir 
                                >> 7U))))) & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__14__KET____DOT__core.__PVT__we))) {
        vlSelf->__Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__14__KET____DOT__rf__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__14__KET____DOT__core.__PVT__wd;
        vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__14__KET____DOT__rf__v0 = 1U;
        vlSelf->__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__14__KET____DOT__rf__v0 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__14__KET____DOT__core.__PVT__ir 
                          >> 2U)) | (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__14__KET____DOT__core.__PVT__k));
    }
    if (((~ ((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__13__KET____DOT__core.__PVT__halted_r) 
             | (0U == (0x1fU & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__13__KET____DOT__core.__PVT__ir 
                                >> 7U))))) & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__13__KET____DOT__core.__PVT__we))) {
        vlSelf->__Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__13__KET____DOT__rf__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__13__KET____DOT__core.__PVT__wd;
        vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__13__KET____DOT__rf__v0 = 1U;
        vlSelf->__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__13__KET____DOT__rf__v0 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__13__KET____DOT__core.__PVT__ir 
                          >> 2U)) | (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__13__KET____DOT__core.__PVT__k));
    }
    if (((~ ((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__12__KET____DOT__core.__PVT__halted_r) 
             | (0U == (0x1fU & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__12__KET____DOT__core.__PVT__ir 
                                >> 7U))))) & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__12__KET____DOT__core.__PVT__we))) {
        vlSelf->__Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__12__KET____DOT__rf__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__12__KET____DOT__core.__PVT__wd;
        vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__12__KET____DOT__rf__v0 = 1U;
        vlSelf->__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__12__KET____DOT__rf__v0 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__12__KET____DOT__core.__PVT__ir 
                          >> 2U)) | (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__12__KET____DOT__core.__PVT__k));
    }
    if (((~ ((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__11__KET____DOT__core.__PVT__halted_r) 
             | (0U == (0x1fU & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__11__KET____DOT__core.__PVT__ir 
                                >> 7U))))) & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__11__KET____DOT__core.__PVT__we))) {
        vlSelf->__Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__11__KET____DOT__rf__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__11__KET____DOT__core.__PVT__wd;
        vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__11__KET____DOT__rf__v0 = 1U;
        vlSelf->__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__11__KET____DOT__rf__v0 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__11__KET____DOT__core.__PVT__ir 
                          >> 2U)) | (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__11__KET____DOT__core.__PVT__k));
    }
    if (((~ ((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__10__KET____DOT__core.__PVT__halted_r) 
             | (0U == (0x1fU & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__10__KET____DOT__core.__PVT__ir 
                                >> 7U))))) & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__10__KET____DOT__core.__PVT__we))) {
        vlSelf->__Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__10__KET____DOT__rf__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__10__KET____DOT__core.__PVT__wd;
        vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__10__KET____DOT__rf__v0 = 1U;
        vlSelf->__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__10__KET____DOT__rf__v0 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__10__KET____DOT__core.__PVT__ir 
                          >> 2U)) | (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__10__KET____DOT__core.__PVT__k));
    }
    if (((~ ((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__9__KET____DOT__core.__PVT__halted_r) 
             | (0U == (0x1fU & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__9__KET____DOT__core.__PVT__ir 
                                >> 7U))))) & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__9__KET____DOT__core.__PVT__we))) {
        vlSelf->__Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__9__KET____DOT__rf__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__9__KET____DOT__core.__PVT__wd;
        vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__9__KET____DOT__rf__v0 = 1U;
        vlSelf->__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__9__KET____DOT__rf__v0 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__9__KET____DOT__core.__PVT__ir 
                          >> 2U)) | (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__9__KET____DOT__core.__PVT__k));
    }
    if (((~ ((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__8__KET____DOT__core.__PVT__halted_r) 
             | (0U == (0x1fU & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__8__KET____DOT__core.__PVT__ir 
                                >> 7U))))) & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__8__KET____DOT__core.__PVT__we))) {
        vlSelf->__Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__8__KET____DOT__rf__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__8__KET____DOT__core.__PVT__wd;
        vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__8__KET____DOT__rf__v0 = 1U;
        vlSelf->__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__8__KET____DOT__rf__v0 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__8__KET____DOT__core.__PVT__ir 
                          >> 2U)) | (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__8__KET____DOT__core.__PVT__k));
    }
    if (((~ ((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__7__KET____DOT__core.__PVT__halted_r) 
             | (0U == (0x1fU & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__7__KET____DOT__core.__PVT__ir 
                                >> 7U))))) & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__7__KET____DOT__core.__PVT__we))) {
        vlSelf->__Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__7__KET____DOT__rf__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__7__KET____DOT__core.__PVT__wd;
        vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__7__KET____DOT__rf__v0 = 1U;
        vlSelf->__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__7__KET____DOT__rf__v0 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__7__KET____DOT__core.__PVT__ir 
                          >> 2U)) | (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__7__KET____DOT__core.__PVT__k));
    }
    if (((~ ((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__6__KET____DOT__core.__PVT__halted_r) 
             | (0U == (0x1fU & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__6__KET____DOT__core.__PVT__ir 
                                >> 7U))))) & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__6__KET____DOT__core.__PVT__we))) {
        vlSelf->__Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__6__KET____DOT__rf__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__6__KET____DOT__core.__PVT__wd;
        vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__6__KET____DOT__rf__v0 = 1U;
        vlSelf->__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__6__KET____DOT__rf__v0 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__6__KET____DOT__core.__PVT__ir 
                          >> 2U)) | (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__6__KET____DOT__core.__PVT__k));
    }
    if (((~ ((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__5__KET____DOT__core.__PVT__halted_r) 
             | (0U == (0x1fU & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__5__KET____DOT__core.__PVT__ir 
                                >> 7U))))) & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__5__KET____DOT__core.__PVT__we))) {
        vlSelf->__Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__5__KET____DOT__rf__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__5__KET____DOT__core.__PVT__wd;
        vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__5__KET____DOT__rf__v0 = 1U;
        vlSelf->__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__5__KET____DOT__rf__v0 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__5__KET____DOT__core.__PVT__ir 
                          >> 2U)) | (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__5__KET____DOT__core.__PVT__k));
    }
    if (((~ ((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__4__KET____DOT__core.__PVT__halted_r) 
             | (0U == (0x1fU & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__4__KET____DOT__core.__PVT__ir 
                                >> 7U))))) & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__4__KET____DOT__core.__PVT__we))) {
        vlSelf->__Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__4__KET____DOT__rf__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__4__KET____DOT__core.__PVT__wd;
        vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__4__KET____DOT__rf__v0 = 1U;
        vlSelf->__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__4__KET____DOT__rf__v0 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__4__KET____DOT__core.__PVT__ir 
                          >> 2U)) | (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__4__KET____DOT__core.__PVT__k));
    }
    if (((~ ((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__3__KET____DOT__core.__PVT__halted_r) 
             | (0U == (0x1fU & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__3__KET____DOT__core.__PVT__ir 
                                >> 7U))))) & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__3__KET____DOT__core.__PVT__we))) {
        vlSelf->__Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__3__KET____DOT__rf__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__3__KET____DOT__core.__PVT__wd;
        vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__3__KET____DOT__rf__v0 = 1U;
        vlSelf->__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__3__KET____DOT__rf__v0 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__3__KET____DOT__core.__PVT__ir 
                          >> 2U)) | (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__3__KET____DOT__core.__PVT__k));
    }
    if (((~ ((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__2__KET____DOT__core.__PVT__halted_r) 
             | (0U == (0x1fU & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__2__KET____DOT__core.__PVT__ir 
                                >> 7U))))) & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__2__KET____DOT__core.__PVT__we))) {
        vlSelf->__Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__2__KET____DOT__rf__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__2__KET____DOT__core.__PVT__wd;
        vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__2__KET____DOT__rf__v0 = 1U;
        vlSelf->__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__2__KET____DOT__rf__v0 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__2__KET____DOT__core.__PVT__ir 
                          >> 2U)) | (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__2__KET____DOT__core.__PVT__k));
    }
    if (((~ ((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__1__KET____DOT__core.__PVT__halted_r) 
             | (0U == (0x1fU & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__1__KET____DOT__core.__PVT__ir 
                                >> 7U))))) & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__1__KET____DOT__core.__PVT__we))) {
        vlSelf->__Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__1__KET____DOT__rf__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__1__KET____DOT__core.__PVT__wd;
        vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__1__KET____DOT__rf__v0 = 1U;
        vlSelf->__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__1__KET____DOT__rf__v0 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__1__KET____DOT__core.__PVT__ir 
                          >> 2U)) | (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__1__KET____DOT__core.__PVT__k));
    }
    if (((~ ((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__0__KET____DOT__core.__PVT__halted_r) 
             | (0U == (0x1fU & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__0__KET____DOT__core.__PVT__ir 
                                >> 7U))))) & (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__0__KET____DOT__core.__PVT__we))) {
        vlSelf->__Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__0__KET____DOT__rf__v0 
            = vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__0__KET____DOT__core.__PVT__wd;
        vlSelf->__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__0__KET____DOT__rf__v0 = 1U;
        vlSelf->__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__0__KET____DOT__rf__v0 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__0__KET____DOT__core.__PVT__ir 
                          >> 2U)) | (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__0__KET____DOT__core.__PVT__k));
    }
    if (vlSelf->tb_sys3__DOT__rst) {
        vlSelf->tb_sys3__DOT__dut__DOT__fi = 0U;
        __Vdly__tb_sys3__DOT__dut__DOT__slice_busy = 0ULL;
        __Vdly__tb_sys3__DOT__dut__DOT__busy_l = 0U;
        __Vdly__tb_sys3__DOT__dut__DOT__req_tab[0U] 
            = Vtb_sys3__ConstPool__CONST_h9e67c271_0[0U];
        __Vdly__tb_sys3__DOT__dut__DOT__req_tab[1U] 
            = Vtb_sys3__ConstPool__CONST_h9e67c271_0[1U];
        __Vdly__tb_sys3__DOT__dut__DOT__req_tab[2U] 
            = Vtb_sys3__ConstPool__CONST_h9e67c271_0[2U];
        __Vdly__tb_sys3__DOT__dut__DOT__req_tab[3U] 
            = Vtb_sys3__ConstPool__CONST_h9e67c271_0[3U];
        __Vdly__tb_sys3__DOT__dut__DOT__req_tab[4U] 
            = Vtb_sys3__ConstPool__CONST_h9e67c271_0[4U];
        __Vdly__tb_sys3__DOT__dut__DOT__req_tab[5U] 
            = Vtb_sys3__ConstPool__CONST_h9e67c271_0[5U];
        __Vdly__tb_sys3__DOT__dut__DOT__req_tab[6U] 
            = Vtb_sys3__ConstPool__CONST_h9e67c271_0[6U];
        __Vdly__tb_sys3__DOT__dut__DOT__req_tab[7U] 
            = Vtb_sys3__ConstPool__CONST_h9e67c271_0[7U];
        __Vdly__tb_sys3__DOT__dut__DOT__fin_sent = 0U;
        __Vdly__tb_sys3__DOT__dut__DOT__qc_wr = 0U;
        __Vdly__tb_sys3__DOT__dut__DOT__qc_rd = 0U;
        __Vdly__tb_sys3__DOT__dut__DOT__done_count = 0U;
        __Vdly__tb_sys3__DOT__dut__DOT__ev_cnt = 0U;
        vlSelf->__Vdly__tb_sys3__DOT__dut__DOT__cyc = 0U;
        __Vdly__tb_sys3__DOT__dut__DOT__busy_slice_cycles = 0ULL;
        __Vdly__tb_sys3__DOT__dut__DOT__waste_blocked = 0ULL;
        __Vdly__tb_sys3__DOT__dut__DOT__waste_tail = 0ULL;
        __Vdly__tb_sys3__DOT__dut__DOT__search_cycles = 0ULL;
        __Vdly__tb_sys3__DOT__dut__DOT__launch_err = 0U;
        __Vdly__tb_sys3__DOT__dut__DOT__dispatches = 0U;
        __Vdly__tb_sys3__DOT__dut__DOT__dstate = 0U;
        __Vdly__tb_sys3__DOT__dut__DOT__rescan = 0U;
        __Vdly__tb_sys3__DOT__dut__DOT__ph = 0U;
        __Vdly__tb_sys3__DOT__dut__DOT__cand = 0U;
        vlSelf->__Vdly__tb_sys3__DOT__dut__DOT__start_v = 0U;
        __Vdly__tb_sys3__DOT__dut__DOT__halted_q = 0xffffffffU;
        vlSelf->__Vdly__tb_sys3__DOT__dut__DOT__launch_entry = 0U;
        vlSelf->__Vdly__tb_sys3__DOT__dut__DOT__launch_lw = 0U;
        __Vdly__tb_sys3__DOT__dut__DOT__cur_is_crit = 0U;
        __Vdly__tb_sys3__DOT__dut__DOT__cur_tid = 0U;
        __Vdly__tb_sys3__DOT__dut__DOT__cur_code = 0U;
        __Vdly__tb_sys3__DOT__dut__DOT__cur_lw = 0U;
        __Vdly__tb_sys3__DOT__dut__DOT__crit_streak = 0U;
        __Vdly__tb_sys3__DOT__dut__DOT__bulk_pass = 0U;
        __Vdly__tb_sys3__DOT__dut__DOT__cur_bk = 0U;
        __Vdlyvset__tb_sys3__DOT__dut__DOT__kwr__v0 = 1U;
        while (VL_GTS_III(32, 0x200U, vlSelf->tb_sys3__DOT__dut__DOT__fi)) {
            vlSelf->tb_sys3__DOT__dut__DOT__prof[(0x1ffU 
                                                  & vlSelf->tb_sys3__DOT__dut__DOT__fi)] = 0U;
            vlSelf->tb_sys3__DOT__dut__DOT__fi = ((IData)(1U) 
                                                  + vlSelf->tb_sys3__DOT__dut__DOT__fi);
        }
        __Vdlyvset__tb_sys3__DOT__dut__DOT__kwr__v1 = 1U;
    } else {
        vlSelf->tb_sys3__DOT__dut__DOT__fi = 0x20U;
        vlSelf->__Vdly__tb_sys3__DOT__dut__DOT__cyc 
            = ((IData)(1U) + vlSelf->tb_sys3__DOT__dut__DOT__cyc);
        vlSelf->__Vdly__tb_sys3__DOT__dut__DOT__start_v = 0U;
        vlSelf->tb_sys3__DOT__dut__DOT__nb = vlSelf->tb_sys3__DOT__dut__DOT__slice_busy;
        vlSelf->tb_sys3__DOT__dut__DOT__rq[0U] = vlSelf->tb_sys3__DOT__dut__DOT__req_tab[0U];
        vlSelf->tb_sys3__DOT__dut__DOT__rq[1U] = vlSelf->tb_sys3__DOT__dut__DOT__req_tab[1U];
        vlSelf->tb_sys3__DOT__dut__DOT__rq[2U] = vlSelf->tb_sys3__DOT__dut__DOT__req_tab[2U];
        vlSelf->tb_sys3__DOT__dut__DOT__rq[3U] = vlSelf->tb_sys3__DOT__dut__DOT__req_tab[3U];
        vlSelf->tb_sys3__DOT__dut__DOT__rq[4U] = vlSelf->tb_sys3__DOT__dut__DOT__req_tab[4U];
        vlSelf->tb_sys3__DOT__dut__DOT__rq[5U] = vlSelf->tb_sys3__DOT__dut__DOT__req_tab[5U];
        vlSelf->tb_sys3__DOT__dut__DOT__rq[6U] = vlSelf->tb_sys3__DOT__dut__DOT__req_tab[6U];
        vlSelf->tb_sys3__DOT__dut__DOT__rq[7U] = vlSelf->tb_sys3__DOT__dut__DOT__req_tab[7U];
        vlSelf->tb_sys3__DOT__dut__DOT__rs = vlSelf->tb_sys3__DOT__dut__DOT__rescan;
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (1U 
                                                & (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slice_busy));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 1U))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 2U))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 3U))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 4U))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 5U))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 6U))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 7U))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 8U))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 9U))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 0xaU))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 0xbU))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 0xcU))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 0xdU))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 0xeU))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 0xfU))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 0x10U))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 0x11U))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 0x12U))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 0x13U))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 0x14U))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 0x15U))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 0x16U))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 0x17U))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 0x18U))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 0x19U))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 0x1aU))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 0x1bU))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 0x1cU))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 0x1dU))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 0x1eU))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 0x1fU))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 0x20U))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 0x21U))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 0x22U))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 0x23U))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 0x24U))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 0x25U))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 0x26U))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 0x27U))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 0x28U))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 0x29U))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 0x2aU))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 0x2bU))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 0x2cU))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 0x2dU))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 0x2eU))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 0x2fU))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 0x30U))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 0x31U))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 0x32U))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 0x33U))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 0x34U))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 0x35U))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 0x36U))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 0x37U))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 0x38U))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 0x39U))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 0x3aU))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 0x3bU))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 0x3cU))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 0x3dU))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 0x3eU))));
        vlSelf->tb_sys3__DOT__dut__DOT__pcnt = (vlSelf->tb_sys3__DOT__dut__DOT__pcnt 
                                                + (1U 
                                                   & (IData)(
                                                             (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                                                              >> 0x3fU))));
        __Vdly__tb_sys3__DOT__dut__DOT__busy_slice_cycles 
            = (vlSelf->tb_sys3__DOT__dut__DOT__busy_slice_cycles 
               + (QData)((IData)(vlSelf->tb_sys3__DOT__dut__DOT__pcnt)));
        if (((IData)(vlSelf->tb_sys3__DOT__dut__DOT__pend_c) 
             | (IData)(vlSelf->tb_sys3__DOT__dut__DOT__pend_b))) {
            __Vdly__tb_sys3__DOT__dut__DOT__waste_blocked 
                = (vlSelf->tb_sys3__DOT__dut__DOT__waste_blocked 
                   + (0x20ULL - (QData)((IData)(vlSelf->tb_sys3__DOT__dut__DOT__pcnt))));
        } else if ((0U != vlSelf->tb_sys3__DOT__dut__DOT__pcnt)) {
            __Vdly__tb_sys3__DOT__dut__DOT__waste_tail 
                = (vlSelf->tb_sys3__DOT__dut__DOT__waste_tail 
                   + (0x20ULL - (QData)((IData)(vlSelf->tb_sys3__DOT__dut__DOT__pcnt))));
        }
        if ((0U != (IData)(vlSelf->tb_sys3__DOT__dut__DOT__dstate))) {
            __Vdly__tb_sys3__DOT__dut__DOT__search_cycles 
                = (1ULL + vlSelf->tb_sys3__DOT__dut__DOT__search_cycles);
        }
        vlSelf->tb_sys3__DOT__dut__DOT__first_crit 
            = ((IData)(vlSelf->tb_sys3__DOT__dut__DOT__pend_c) 
               & (~ ((IData)(vlSelf->tb_sys3__DOT__dut__DOT__pend_b) 
                     & (8U <= vlSelf->tb_sys3__DOT__dut__DOT__crit_streak))));
        if ((0U == (IData)(vlSelf->tb_sys3__DOT__dut__DOT__dstate))) {
            if (((IData)(vlSelf->tb_sys3__DOT__dut__DOT__rs) 
                 & ((IData)(vlSelf->tb_sys3__DOT__dut__DOT__pend_c) 
                    | (IData)(vlSelf->tb_sys3__DOT__dut__DOT__pend_b)))) {
                vlSelf->tb_sys3__DOT__dut__DOT__rs = 0U;
                __Vdly__tb_sys3__DOT__dut__DOT__cur_is_crit 
                    = vlSelf->tb_sys3__DOT__dut__DOT__first_crit;
                __Vdly__tb_sys3__DOT__dut__DOT__cur_bk 
                    = vlSelf->tb_sys3__DOT__dut__DOT__hb;
                __Vdly__tb_sys3__DOT__dut__DOT__ph = 0U;
                __Vdly__tb_sys3__DOT__dut__DOT__dstate = 1U;
                __Vdly__tb_sys3__DOT__dut__DOT__cur_tid 
                    = ((IData)(vlSelf->tb_sys3__DOT__dut__DOT__first_crit)
                        ? vlSelf->tb_sys3__DOT__dut__DOT__qc
                       [(0xffU & vlSelf->tb_sys3__DOT__dut__DOT__qc_rd)]
                        : (IData)(vlSelf->tb_sys3__DOT__dut__DOT__bhead));
                __Vdly__tb_sys3__DOT__dut__DOT__cur_code 
                    = vlSelf->tb_sys3__DOT__dut__DOT__t_code
                    [(0xffU & ((IData)(vlSelf->tb_sys3__DOT__dut__DOT__first_crit)
                                ? vlSelf->tb_sys3__DOT__dut__DOT__qc
                               [(0xffU & vlSelf->tb_sys3__DOT__dut__DOT__qc_rd)]
                                : (IData)(vlSelf->tb_sys3__DOT__dut__DOT__bhead)))];
                __Vdly__tb_sys3__DOT__dut__DOT__cur_lw 
                    = vlSelf->tb_sys3__DOT__dut__DOT__t_lw
                    [(0xffU & ((IData)(vlSelf->tb_sys3__DOT__dut__DOT__first_crit)
                                ? vlSelf->tb_sys3__DOT__dut__DOT__qc
                               [(0xffU & vlSelf->tb_sys3__DOT__dut__DOT__qc_rd)]
                                : (IData)(vlSelf->tb_sys3__DOT__dut__DOT__bhead)))];
            }
        } else if ((1U == (IData)(vlSelf->tb_sys3__DOT__dut__DOT__dstate))) {
            if (vlSelf->tb_sys3__DOT__dut__DOT__fit_found) {
                __Vdly__tb_sys3__DOT__dut__DOT__cand 
                    = vlSelf->tb_sys3__DOT__dut__DOT__fit_base;
                __Vdly__tb_sys3__DOT__dut__DOT__dstate = 2U;
            } else {
                vlSelf->tb_sys3__DOT__dut__DOT__second_crit 
                    = (1U & (~ (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_is_crit)));
                vlSelf->tb_sys3__DOT__dut__DOT__second_avail 
                    = ((IData)(vlSelf->tb_sys3__DOT__dut__DOT__second_crit)
                        ? (IData)(vlSelf->tb_sys3__DOT__dut__DOT__pend_c)
                        : (IData)(vlSelf->tb_sys3__DOT__dut__DOT__pend_b));
                vlSelf->tb_sys3__DOT__dut__DOT__second_ok 
                    = ((IData)(vlSelf->tb_sys3__DOT__dut__DOT__second_crit) 
                       | (8U > vlSelf->tb_sys3__DOT__dut__DOT__bulk_pass));
                if ((((~ (IData)(vlSelf->tb_sys3__DOT__dut__DOT__ph)) 
                      & (IData)(vlSelf->tb_sys3__DOT__dut__DOT__second_avail)) 
                     & (IData)(vlSelf->tb_sys3__DOT__dut__DOT__second_ok))) {
                    if (vlSelf->tb_sys3__DOT__dut__DOT__second_crit) {
                        __Vdly__tb_sys3__DOT__dut__DOT__cur_is_crit = 1U;
                        __Vdly__tb_sys3__DOT__dut__DOT__cur_bk 
                            = vlSelf->tb_sys3__DOT__dut__DOT__hb;
                        __Vdly__tb_sys3__DOT__dut__DOT__ph = 1U;
                        __Vdly__tb_sys3__DOT__dut__DOT__cur_tid 
                            = vlSelf->tb_sys3__DOT__dut__DOT__qc
                            [(0xffU & vlSelf->tb_sys3__DOT__dut__DOT__qc_rd)];
                    } else {
                        __Vdly__tb_sys3__DOT__dut__DOT__cur_is_crit = 0U;
                        __Vdly__tb_sys3__DOT__dut__DOT__cur_bk 
                            = vlSelf->tb_sys3__DOT__dut__DOT__hb;
                        __Vdly__tb_sys3__DOT__dut__DOT__ph = 1U;
                        __Vdly__tb_sys3__DOT__dut__DOT__cur_tid 
                            = vlSelf->tb_sys3__DOT__dut__DOT__bhead;
                    }
                    __Vdly__tb_sys3__DOT__dut__DOT__cur_code 
                        = vlSelf->tb_sys3__DOT__dut__DOT__t_code
                        [(0xffU & ((IData)(vlSelf->tb_sys3__DOT__dut__DOT__second_crit)
                                    ? vlSelf->tb_sys3__DOT__dut__DOT__qc
                                   [(0xffU & vlSelf->tb_sys3__DOT__dut__DOT__qc_rd)]
                                    : (IData)(vlSelf->tb_sys3__DOT__dut__DOT__bhead)))];
                    __Vdly__tb_sys3__DOT__dut__DOT__cur_lw 
                        = vlSelf->tb_sys3__DOT__dut__DOT__t_lw
                        [(0xffU & ((IData)(vlSelf->tb_sys3__DOT__dut__DOT__second_crit)
                                    ? vlSelf->tb_sys3__DOT__dut__DOT__qc
                                   [(0xffU & vlSelf->tb_sys3__DOT__dut__DOT__qc_rd)]
                                    : (IData)(vlSelf->tb_sys3__DOT__dut__DOT__bhead)))];
                } else {
                    __Vdly__tb_sys3__DOT__dut__DOT__dstate = 0U;
                }
            }
        } else if ((2U == (IData)(vlSelf->tb_sys3__DOT__dut__DOT__dstate))) {
            if ((((0ULL != (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                            & (((1ULL << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_w)) 
                                - 1ULL) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cand)))) 
                  | (0U != ((IData)(vlSelf->tb_sys3__DOT__dut__DOT__cand) 
                            & ((IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_w) 
                               - (IData)(1U))))) | 
                 (0x20U < ((IData)(vlSelf->tb_sys3__DOT__dut__DOT__cand) 
                           + (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_w))))) {
                __Vdly__tb_sys3__DOT__dut__DOT__launch_err 
                    = ((IData)(1U) + vlSelf->tb_sys3__DOT__dut__DOT__launch_err);
            }
            if (vlSelf->tb_sys3__DOT__dut__DOT__cur_is_crit) {
                __Vdly__tb_sys3__DOT__dut__DOT__qc_rd 
                    = ((IData)(1U) + vlSelf->tb_sys3__DOT__dut__DOT__qc_rd);
                __Vdly__tb_sys3__DOT__dut__DOT__crit_streak 
                    = ((IData)(vlSelf->tb_sys3__DOT__dut__DOT__pend_b)
                        ? ((IData)(1U) + vlSelf->tb_sys3__DOT__dut__DOT__crit_streak)
                        : 0U);
                __Vdly__tb_sys3__DOT__dut__DOT__bulk_pass = 0U;
            } else {
                __Vdlyvval__tb_sys3__DOT__dut__DOT__krd__v8 
                    = ((IData)(1U) + vlSelf->tb_sys3__DOT__dut__DOT__krd
                       [(7U & (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_bk))]);
                __Vdlyvset__tb_sys3__DOT__dut__DOT__krd__v8 = 1U;
                __Vdlyvdim0__tb_sys3__DOT__dut__DOT__krd__v8 
                    = (7U & (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_bk));
                __Vdly__tb_sys3__DOT__dut__DOT__bulk_pass 
                    = ((IData)(vlSelf->tb_sys3__DOT__dut__DOT__pend_c)
                        ? ((IData)(1U) + vlSelf->tb_sys3__DOT__dut__DOT__bulk_pass)
                        : 0U);
                __Vdly__tb_sys3__DOT__dut__DOT__crit_streak = 0U;
            }
            __Vdly__tb_sys3__DOT__dut__DOT__dispatches 
                = ((IData)(1U) + vlSelf->tb_sys3__DOT__dut__DOT__dispatches);
            vlSelf->tb_sys3__DOT__dut__DOT__nb = (vlSelf->tb_sys3__DOT__dut__DOT__nb 
                                                  | (((1ULL 
                                                       << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_w)) 
                                                      - 1ULL) 
                                                     << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cand)));
            vlSelf->tb_sys3__DOT__dut__DOT__rs = 1U;
            __Vdly__tb_sys3__DOT__dut__DOT__busy_l 
                = (__Vdly__tb_sys3__DOT__dut__DOT__busy_l 
                   | (0xffffffffULL & ((IData)(1U) 
                                       << (0x1fU & (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cand)))));
            vlSelf->__Vdly__tb_sys3__DOT__dut__DOT__launch_entry 
                = ((IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_code) 
                   << 2U);
            __Vdly__tb_sys3__DOT__dut__DOT__dstate = 0U;
            __Vdlyvval__tb_sys3__DOT__dut__DOT__own_tid__v0 
                = vlSelf->tb_sys3__DOT__dut__DOT__cur_tid;
            __Vdlyvset__tb_sys3__DOT__dut__DOT__own_tid__v0 = 1U;
            __Vdlyvdim0__tb_sys3__DOT__dut__DOT__own_tid__v0 
                = (0x1fU & (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cand));
            __Vdlyvval__tb_sys3__DOT__dut__DOT__own_lw__v0 
                = vlSelf->tb_sys3__DOT__dut__DOT__cur_lw;
            __Vdlyvdim0__tb_sys3__DOT__dut__DOT__own_lw__v0 
                = (0x1fU & (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cand));
            __Vdlyvval__tb_sys3__DOT__dut__DOT__t_start__v0 
                = vlSelf->tb_sys3__DOT__dut__DOT__cyc;
            __Vdlyvdim0__tb_sys3__DOT__dut__DOT__t_start__v0 
                = (0xffU & (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_tid));
            __Vdlyvdim0__tb_sys3__DOT__dut__DOT__t_state__v0 
                = (0xffU & (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_tid));
            __Vdlyvval__tb_sys3__DOT__dut__DOT__t_slot__v0 
                = vlSelf->tb_sys3__DOT__dut__DOT__cand;
            __Vdlyvdim0__tb_sys3__DOT__dut__DOT__t_slot__v0 
                = (0xffU & (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_tid));
            vlSelf->__Vdly__tb_sys3__DOT__dut__DOT__start_v 
                = (vlSelf->__Vdly__tb_sys3__DOT__dut__DOT__start_v 
                   | (0xffffffffULL & ((IData)(1U) 
                                       << (0x1fU & (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cand)))));
            vlSelf->__Vdly__tb_sys3__DOT__dut__DOT__launch_lw 
                = vlSelf->tb_sys3__DOT__dut__DOT__cur_lw;
        } else {
            __Vdly__tb_sys3__DOT__dut__DOT__dstate = 0U;
        }
        if (vlSelf->tb_sys3__DOT__h_push) {
            vlSelf->tb_sys3__DOT__dut__DOT__pb = 0U;
            vlSelf->tb_sys3__DOT__dut__DOT__rs = 1U;
            __Vdlyvval__tb_sys3__DOT__dut__DOT__t_code__v0 
                = vlSelf->tb_sys3__DOT__h_code;
            __Vdlyvset__tb_sys3__DOT__dut__DOT__t_code__v0 = 1U;
            __Vdlyvdim0__tb_sys3__DOT__dut__DOT__t_code__v0 
                = (0xffU & (IData)(vlSelf->tb_sys3__DOT__h_tid));
            __Vdlyvval__tb_sys3__DOT__dut__DOT__t_lw__v0 
                = vlSelf->tb_sys3__DOT__h_lw;
            __Vdlyvdim0__tb_sys3__DOT__dut__DOT__t_lw__v0 
                = (0xffU & (IData)(vlSelf->tb_sys3__DOT__h_tid));
            __Vdlyvval__tb_sys3__DOT__dut__DOT__t_crit__v0 
                = vlSelf->tb_sys3__DOT__h_crit;
            __Vdlyvdim0__tb_sys3__DOT__dut__DOT__t_crit__v0 
                = (0xffU & (IData)(vlSelf->tb_sys3__DOT__h_tid));
            __Vdlyvval__tb_sys3__DOT__dut__DOT__t_arr__v0 
                = vlSelf->tb_sys3__DOT__dut__DOT__cyc;
            __Vdlyvdim0__tb_sys3__DOT__dut__DOT__t_arr__v0 
                = (0xffU & (IData)(vlSelf->tb_sys3__DOT__h_tid));
            __Vdlyvdim0__tb_sys3__DOT__dut__DOT__t_state__v1 
                = (0xffU & (IData)(vlSelf->tb_sys3__DOT__h_tid));
            if (vlSelf->tb_sys3__DOT__h_crit) {
                __Vdlyvval__tb_sys3__DOT__dut__DOT__qc__v0 
                    = vlSelf->tb_sys3__DOT__h_tid;
                __Vdlyvset__tb_sys3__DOT__dut__DOT__qc__v0 = 1U;
                __Vdlyvdim0__tb_sys3__DOT__dut__DOT__qc__v0 
                    = (0xffU & vlSelf->tb_sys3__DOT__dut__DOT__qc_wr);
                __Vdly__tb_sys3__DOT__dut__DOT__qc_wr 
                    = ((IData)(1U) + vlSelf->tb_sys3__DOT__dut__DOT__qc_wr);
            } else {
                __Vdlyvval__tb_sys3__DOT__dut__DOT__qk__v0 
                    = vlSelf->tb_sys3__DOT__h_tid;
                __Vdlyvset__tb_sys3__DOT__dut__DOT__qk__v0 = 1U;
                __Vdlyvdim0__tb_sys3__DOT__dut__DOT__qk__v0 
                    = (0x7ffU & (VL_SHIFTL_III(11,32,32, (IData)(vlSelf->tb_sys3__DOT__dut__DOT__pb), 8U) 
                                 + (0xffU & vlSelf->tb_sys3__DOT__dut__DOT__kwr
                                    [(7U & (IData)(vlSelf->tb_sys3__DOT__dut__DOT__pb))])));
                __Vdlyvval__tb_sys3__DOT__dut__DOT__kwr__v8 
                    = ((IData)(1U) + vlSelf->tb_sys3__DOT__dut__DOT__kwr
                       [(7U & (IData)(vlSelf->tb_sys3__DOT__dut__DOT__pb))]);
                __Vdlyvdim0__tb_sys3__DOT__dut__DOT__kwr__v8 
                    = (7U & (IData)(vlSelf->tb_sys3__DOT__dut__DOT__pb));
            }
            __Vdlyvval__tb_sys3__DOT__dut__DOT__t_pred__v0 
                = vlSelf->tb_sys3__DOT__dut__DOT__prof
                [([&]() {
                    __Vfunc_tb_sys3__DOT__dut__DOT__pkey__1__lw 
                        = vlSelf->tb_sys3__DOT__h_lw;
                    __Vfunc_tb_sys3__DOT__dut__DOT__pkey__1__prog 
                        = vlSelf->tb_sys3__DOT__h_prog;
                    __Vfunc_tb_sys3__DOT__dut__DOT__pkey__1__Vfuncout 
                        = (((IData)(__Vfunc_tb_sys3__DOT__dut__DOT__pkey__1__prog) 
                            << 3U) | (IData)(__Vfunc_tb_sys3__DOT__dut__DOT__pkey__1__lw));
                }(), (IData)(__Vfunc_tb_sys3__DOT__dut__DOT__pkey__1__Vfuncout))];
            __Vdlyvset__tb_sys3__DOT__dut__DOT__t_pred__v0 = 1U;
            __Vdlyvdim0__tb_sys3__DOT__dut__DOT__t_pred__v0 
                = (0xffU & (IData)(vlSelf->tb_sys3__DOT__h_tid));
            __Vdlyvval__tb_sys3__DOT__dut__DOT__t_prog__v0 
                = vlSelf->tb_sys3__DOT__h_prog;
            __Vdlyvdim0__tb_sys3__DOT__dut__DOT__t_prog__v0 
                = (0xffU & (IData)(vlSelf->tb_sys3__DOT__h_tid));
        }
        if (vlSelf->tb_sys3__DOT__dut__DOT__w_found) {
            vlSelf->tb_sys3__DOT__dut__DOT__rq[((IData)(vlSelf->tb_sys3__DOT__dut__DOT__w_id) 
                                                >> 5U)] 
                = ((~ ((IData)(1U) << (0x1fU & (IData)(vlSelf->tb_sys3__DOT__dut__DOT__w_id)))) 
                   & vlSelf->tb_sys3__DOT__dut__DOT__rq[
                   ((IData)(vlSelf->tb_sys3__DOT__dut__DOT__w_id) 
                    >> 5U)]);
            if ((0x40U > (IData)(vlSelf->tb_sys3__DOT__dut__DOT__w_id))) {
                __Vdly__tb_sys3__DOT__dut__DOT__done_count 
                    = ((IData)(1U) + vlSelf->tb_sys3__DOT__dut__DOT__done_count);
                vlSelf->tb_sys3__DOT__dut__DOT__wb 
                    = (0x3fU & (IData)(vlSelf->tb_sys3__DOT__dut__DOT__w_id));
                vlSelf->tb_sys3__DOT__dut__DOT__rs = 1U;
                vlSelf->tb_sys3__DOT__dut__DOT__wfree 
                    = (0x3fU & ((IData)(1U) << vlSelf->tb_sys3__DOT__dut__DOT__own_lw
                                [(0x1fU & (IData)(vlSelf->tb_sys3__DOT__dut__DOT__wb))]));
                __Vtemp_66 = (vlSelf->tb_sys3__DOT__dut__DOT__nb 
                              & (~ (([&]() {
                                    __Vfunc_tb_sys3__DOT__dut__DOT__gmask__2__w 
                                        = vlSelf->tb_sys3__DOT__dut__DOT__wfree;
                                    __Vfunc_tb_sys3__DOT__dut__DOT__gmask__2__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(__Vfunc_tb_sys3__DOT__dut__DOT__gmask__2__w)) 
                                           - 1ULL);
                                }(), __Vfunc_tb_sys3__DOT__dut__DOT__gmask__2__Vfuncout) 
                                    << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__wb))));
                vlSelf->tb_sys3__DOT__dut__DOT__nb 
                    = __Vtemp_66;
                __Vdly__tb_sys3__DOT__dut__DOT__busy_l 
                    = ((~ ((IData)(1U) << (0x1fU & (IData)(vlSelf->tb_sys3__DOT__dut__DOT__wb)))) 
                       & __Vdly__tb_sys3__DOT__dut__DOT__busy_l);
                __Vdly__tb_sys3__DOT__dut__DOT__fin_sent 
                    = ((~ ((IData)(1U) << (0x1fU & (IData)(vlSelf->tb_sys3__DOT__dut__DOT__wb)))) 
                       & __Vdly__tb_sys3__DOT__dut__DOT__fin_sent);
                __Vdlyvval__tb_sys3__DOT__dut__DOT__t_end__v0 
                    = vlSelf->tb_sys3__DOT__dut__DOT__cyc;
                __Vdlyvset__tb_sys3__DOT__dut__DOT__t_end__v0 = 1U;
                __Vdlyvdim0__tb_sys3__DOT__dut__DOT__t_end__v0 
                    = (0xffU & vlSelf->tb_sys3__DOT__dut__DOT__own_tid
                       [(0x1fU & (IData)(vlSelf->tb_sys3__DOT__dut__DOT__wb))]);
                __Vtemp_96[0U] = vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__0__KET____DOT__a0s;
                __Vtemp_96[1U] = vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__1__KET____DOT__a0s;
                __Vtemp_96[2U] = vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__2__KET____DOT__a0s;
                __Vtemp_96[3U] = vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__3__KET____DOT__a0s;
                __Vtemp_96[4U] = vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__4__KET____DOT__a0s;
                __Vtemp_96[5U] = vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__5__KET____DOT__a0s;
                __Vtemp_96[6U] = vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__6__KET____DOT__a0s;
                __Vtemp_96[7U] = vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__7__KET____DOT__a0s;
                __Vtemp_96[8U] = vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__8__KET____DOT__a0s;
                __Vtemp_96[9U] = vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__9__KET____DOT__a0s;
                __Vtemp_96[0xaU] = vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__10__KET____DOT__a0s;
                __Vtemp_96[0xbU] = vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__11__KET____DOT__a0s;
                __Vtemp_96[0xcU] = vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__12__KET____DOT__a0s;
                __Vtemp_96[0xdU] = vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__13__KET____DOT__a0s;
                __Vtemp_96[0xeU] = vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__14__KET____DOT__a0s;
                __Vtemp_96[0xfU] = vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__15__KET____DOT__a0s;
                __Vtemp_96[0x10U] = vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__16__KET____DOT__a0s;
                __Vtemp_96[0x11U] = vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__17__KET____DOT__a0s;
                __Vtemp_96[0x12U] = vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__18__KET____DOT__a0s;
                __Vtemp_96[0x13U] = vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__19__KET____DOT__a0s;
                __Vtemp_96[0x14U] = vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__20__KET____DOT__a0s;
                __Vtemp_96[0x15U] = vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__21__KET____DOT__a0s;
                __Vtemp_96[0x16U] = vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__22__KET____DOT__a0s;
                __Vtemp_96[0x17U] = vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__23__KET____DOT__a0s;
                __Vtemp_96[0x18U] = vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__24__KET____DOT__a0s;
                __Vtemp_96[0x19U] = vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__25__KET____DOT__a0s;
                __Vtemp_96[0x1aU] = vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__26__KET____DOT__a0s;
                __Vtemp_96[0x1bU] = vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__27__KET____DOT__a0s;
                __Vtemp_96[0x1cU] = vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__28__KET____DOT__a0s;
                __Vtemp_96[0x1dU] = vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__a0s;
                __Vtemp_96[0x1eU] = (IData)((((QData)((IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__a0s)) 
                                              << 0x20U) 
                                             | (QData)((IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__a0s))));
                __Vtemp_96[0x1fU] = (IData)(((((QData)((IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__a0s)) 
                                               << 0x20U) 
                                              | (QData)((IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__a0s))) 
                                             >> 0x20U));
                __Vdlyvval__tb_sys3__DOT__dut__DOT__t_a0__v0 
                    = (((0U == (0x1fU & VL_SHIFTL_III(10,32,32, (IData)(vlSelf->tb_sys3__DOT__dut__DOT__wb), 5U)))
                         ? 0U : (__Vtemp_96[(((IData)(0x1fU) 
                                              + (0x3ffU 
                                                 & VL_SHIFTL_III(10,32,32, (IData)(vlSelf->tb_sys3__DOT__dut__DOT__wb), 5U))) 
                                             >> 5U)] 
                                 << ((IData)(0x20U) 
                                     - (0x1fU & VL_SHIFTL_III(10,32,32, (IData)(vlSelf->tb_sys3__DOT__dut__DOT__wb), 5U))))) 
                       | (__Vtemp_96[(0x1fU & (VL_SHIFTL_III(10,32,32, (IData)(vlSelf->tb_sys3__DOT__dut__DOT__wb), 5U) 
                                               >> 5U))] 
                          >> (0x1fU & VL_SHIFTL_III(10,32,32, (IData)(vlSelf->tb_sys3__DOT__dut__DOT__wb), 5U))));
                __Vdlyvdim0__tb_sys3__DOT__dut__DOT__t_a0__v0 
                    = (0xffU & vlSelf->tb_sys3__DOT__dut__DOT__own_tid
                       [(0x1fU & (IData)(vlSelf->tb_sys3__DOT__dut__DOT__wb))]);
                __Vdlyvval__tb_sys3__DOT__dut__DOT__t_trap__v0 
                    = (1U & ((((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__trap_r) 
                               << 0x1fU) | (((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__trap_r) 
                                             << 0x1eU) 
                                            | (((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__trap_r) 
                                                << 0x1dU) 
                                               | (((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__28__KET____DOT__core.__PVT__trap_r) 
                                                   << 0x1cU) 
                                                  | (((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__27__KET____DOT__core.__PVT__trap_r) 
                                                      << 0x1bU) 
                                                     | (((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__26__KET____DOT__core.__PVT__trap_r) 
                                                         << 0x1aU) 
                                                        | (((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__25__KET____DOT__core.__PVT__trap_r) 
                                                            << 0x19U) 
                                                           | (((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__24__KET____DOT__core.__PVT__trap_r) 
                                                               << 0x18U) 
                                                              | (((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__23__KET____DOT__core.__PVT__trap_r) 
                                                                  << 0x17U) 
                                                                 | (((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__22__KET____DOT__core.__PVT__trap_r) 
                                                                     << 0x16U) 
                                                                    | (((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__21__KET____DOT__core.__PVT__trap_r) 
                                                                        << 0x15U) 
                                                                       | (((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__20__KET____DOT__core.__PVT__trap_r) 
                                                                           << 0x14U) 
                                                                          | (((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__19__KET____DOT__core.__PVT__trap_r) 
                                                                              << 0x13U) 
                                                                             | (((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__18__KET____DOT__core.__PVT__trap_r) 
                                                                                << 0x12U) 
                                                                                | (((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__17__KET____DOT__core.__PVT__trap_r) 
                                                                                << 0x11U) 
                                                                                | (((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__16__KET____DOT__core.__PVT__trap_r) 
                                                                                << 0x10U) 
                                                                                | (((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__15__KET____DOT__core.__PVT__trap_r) 
                                                                                << 0xfU) 
                                                                                | (((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__14__KET____DOT__core.__PVT__trap_r) 
                                                                                << 0xeU) 
                                                                                | (((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__13__KET____DOT__core.__PVT__trap_r) 
                                                                                << 0xdU) 
                                                                                | (((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__12__KET____DOT__core.__PVT__trap_r) 
                                                                                << 0xcU) 
                                                                                | (((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__11__KET____DOT__core.__PVT__trap_r) 
                                                                                << 0xbU) 
                                                                                | (((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__10__KET____DOT__core.__PVT__trap_r) 
                                                                                << 0xaU) 
                                                                                | (((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__9__KET____DOT__core.__PVT__trap_r) 
                                                                                << 9U) 
                                                                                | (((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__8__KET____DOT__core.__PVT__trap_r) 
                                                                                << 8U) 
                                                                                | (((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__7__KET____DOT__core.__PVT__trap_r) 
                                                                                << 7U) 
                                                                                | (((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__6__KET____DOT__core.__PVT__trap_r) 
                                                                                << 6U) 
                                                                                | (((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__5__KET____DOT__core.__PVT__trap_r) 
                                                                                << 5U) 
                                                                                | (((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__4__KET____DOT__core.__PVT__trap_r) 
                                                                                << 4U) 
                                                                                | (((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__3__KET____DOT__core.__PVT__trap_r) 
                                                                                << 3U) 
                                                                                | (((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__2__KET____DOT__core.__PVT__trap_r) 
                                                                                << 2U) 
                                                                                | (((IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__1__KET____DOT__core.__PVT__trap_r) 
                                                                                << 1U) 
                                                                                | (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__0__KET____DOT__core.__PVT__trap_r)))))))))))))))))))))))))))))))) 
                             >> (0x1fU & (IData)(vlSelf->tb_sys3__DOT__dut__DOT__wb))));
                __Vdlyvdim0__tb_sys3__DOT__dut__DOT__t_trap__v0 
                    = (0xffU & vlSelf->tb_sys3__DOT__dut__DOT__own_tid
                       [(0x1fU & (IData)(vlSelf->tb_sys3__DOT__dut__DOT__wb))]);
                __Vdlyvdim0__tb_sys3__DOT__dut__DOT__t_state__v2 
                    = (0xffU & vlSelf->tb_sys3__DOT__dut__DOT__own_tid
                       [(0x1fU & (IData)(vlSelf->tb_sys3__DOT__dut__DOT__wb))]);
                __Vfunc_tb_sys3__DOT__dut__DOT__pkey__3__lw 
                    = vlSelf->tb_sys3__DOT__dut__DOT__t_lw
                    [(0xffU & vlSelf->tb_sys3__DOT__dut__DOT__own_tid
                      [(0x1fU & (IData)(vlSelf->tb_sys3__DOT__dut__DOT__wb))])];
                __Vfunc_tb_sys3__DOT__dut__DOT__pkey__3__prog 
                    = vlSelf->tb_sys3__DOT__dut__DOT__t_prog
                    [(0xffU & vlSelf->tb_sys3__DOT__dut__DOT__own_tid
                      [(0x1fU & (IData)(vlSelf->tb_sys3__DOT__dut__DOT__wb))])];
                __Vfunc_tb_sys3__DOT__dut__DOT__pkey__3__Vfuncout 
                    = (((IData)(__Vfunc_tb_sys3__DOT__dut__DOT__pkey__3__prog) 
                        << 3U) | (IData)(__Vfunc_tb_sys3__DOT__dut__DOT__pkey__3__lw));
                vlSelf->tb_sys3__DOT__dut__DOT__pk 
                    = __Vfunc_tb_sys3__DOT__dut__DOT__pkey__3__Vfuncout;
                vlSelf->tb_sys3__DOT__dut__DOT__dur 
                    = (0xffffffU & (vlSelf->tb_sys3__DOT__dut__DOT__cyc 
                                    - vlSelf->tb_sys3__DOT__dut__DOT__t_start
                                    [(0xffU & vlSelf->tb_sys3__DOT__dut__DOT__own_tid
                                      [(0x1fU & (IData)(vlSelf->tb_sys3__DOT__dut__DOT__wb))])]));
                vlSelf->tb_sys3__DOT__dut__DOT__davg 
                    = (0x1ffffffU & VL_SHIFTR_III(25,25,32, 
                                                  (0x1ffffffU 
                                                   & ((0xffffffU 
                                                       & vlSelf->tb_sys3__DOT__dut__DOT__prof
                                                       [vlSelf->tb_sys3__DOT__dut__DOT__pk]) 
                                                      + vlSelf->tb_sys3__DOT__dut__DOT__dur)), 1U));
                __Vdlyvval__tb_sys3__DOT__dut__DOT__prof__v0 
                    = ((0x1000000U & vlSelf->tb_sys3__DOT__dut__DOT__prof
                        [vlSelf->tb_sys3__DOT__dut__DOT__pk])
                        ? (0x1000000U | (0xffffffU 
                                         & vlSelf->tb_sys3__DOT__dut__DOT__davg))
                        : (0x1000000U | vlSelf->tb_sys3__DOT__dut__DOT__dur));
                __Vdlyvset__tb_sys3__DOT__dut__DOT__prof__v0 = 1U;
                __Vdlyvdim0__tb_sys3__DOT__dut__DOT__prof__v0 
                    = vlSelf->tb_sys3__DOT__dut__DOT__pk;
            } else {
                __Vdlyvval__tb_sys3__DOT__dut__DOT__ev_id__v0 
                    = vlSelf->tb_sys3__DOT__dut__DOT__w_id;
                __Vdlyvset__tb_sys3__DOT__dut__DOT__ev_id__v0 = 1U;
                __Vdlyvdim0__tb_sys3__DOT__dut__DOT__ev_id__v0 
                    = (0xffU & vlSelf->tb_sys3__DOT__dut__DOT__ev_cnt);
                __Vdlyvval__tb_sys3__DOT__dut__DOT__ev_data__v0 
                    = vlSelf->tb_sys3__DOT__dut__DOT__ev_pl
                    [vlSelf->tb_sys3__DOT__dut__DOT__w_id];
                __Vdlyvdim0__tb_sys3__DOT__dut__DOT__ev_data__v0 
                    = (0xffU & vlSelf->tb_sys3__DOT__dut__DOT__ev_cnt);
                __Vdlyvval__tb_sys3__DOT__dut__DOT__ev_cyc__v0 
                    = vlSelf->tb_sys3__DOT__dut__DOT__cyc;
                __Vdlyvdim0__tb_sys3__DOT__dut__DOT__ev_cyc__v0 
                    = (0xffU & vlSelf->tb_sys3__DOT__dut__DOT__ev_cnt);
                __Vdly__tb_sys3__DOT__dut__DOT__ev_cnt 
                    = ((IData)(1U) + vlSelf->tb_sys3__DOT__dut__DOT__ev_cnt);
            }
        }
        if ((1U & ((((vlSelf->tb_sys3__DOT__dut__DOT__busy_l 
                      & vlSelf->tb_sys3__DOT__dut__DOT__halted_v) 
                     & vlSelf->tb_sys3__DOT__dut__DOT__halted_q) 
                    & (~ vlSelf->tb_sys3__DOT__dut__DOT__start_v)) 
                   & (~ vlSelf->tb_sys3__DOT__dut__DOT__fin_sent)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__rq[0U] 
                = (1U | vlSelf->tb_sys3__DOT__dut__DOT__rq[0U]);
            __Vdly__tb_sys3__DOT__dut__DOT__fin_sent 
                = (1U | __Vdly__tb_sys3__DOT__dut__DOT__fin_sent);
        }
        if ((1U & (((((vlSelf->tb_sys3__DOT__dut__DOT__busy_l 
                       & vlSelf->tb_sys3__DOT__dut__DOT__halted_v) 
                      & vlSelf->tb_sys3__DOT__dut__DOT__halted_q) 
                     >> 1U) & (~ (vlSelf->tb_sys3__DOT__dut__DOT__start_v 
                                  >> 1U))) & (~ (vlSelf->tb_sys3__DOT__dut__DOT__fin_sent 
                                                 >> 1U))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__rq[0U] 
                = (2U | vlSelf->tb_sys3__DOT__dut__DOT__rq[0U]);
            __Vdly__tb_sys3__DOT__dut__DOT__fin_sent 
                = (2U | __Vdly__tb_sys3__DOT__dut__DOT__fin_sent);
        }
        if ((1U & (((((vlSelf->tb_sys3__DOT__dut__DOT__busy_l 
                       & vlSelf->tb_sys3__DOT__dut__DOT__halted_v) 
                      & vlSelf->tb_sys3__DOT__dut__DOT__halted_q) 
                     >> 2U) & (~ (vlSelf->tb_sys3__DOT__dut__DOT__start_v 
                                  >> 2U))) & (~ (vlSelf->tb_sys3__DOT__dut__DOT__fin_sent 
                                                 >> 2U))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__rq[0U] 
                = (4U | vlSelf->tb_sys3__DOT__dut__DOT__rq[0U]);
            __Vdly__tb_sys3__DOT__dut__DOT__fin_sent 
                = (4U | __Vdly__tb_sys3__DOT__dut__DOT__fin_sent);
        }
        if (vlSelf->tb_sys3__DOT__ev_pl_we) {
            __Vdlyvval__tb_sys3__DOT__dut__DOT__ev_pl__v0 
                = vlSelf->tb_sys3__DOT__ev_pl_data;
            __Vdlyvset__tb_sys3__DOT__dut__DOT__ev_pl__v0 = 1U;
            __Vdlyvdim0__tb_sys3__DOT__dut__DOT__ev_pl__v0 
                = vlSelf->tb_sys3__DOT__ev_pl_id;
        }
        if ((1U & (((((vlSelf->tb_sys3__DOT__dut__DOT__busy_l 
                       & vlSelf->tb_sys3__DOT__dut__DOT__halted_v) 
                      & vlSelf->tb_sys3__DOT__dut__DOT__halted_q) 
                     >> 3U) & (~ (vlSelf->tb_sys3__DOT__dut__DOT__start_v 
                                  >> 3U))) & (~ (vlSelf->tb_sys3__DOT__dut__DOT__fin_sent 
                                                 >> 3U))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__rq[0U] 
                = (8U | vlSelf->tb_sys3__DOT__dut__DOT__rq[0U]);
            __Vdly__tb_sys3__DOT__dut__DOT__fin_sent 
                = (8U | __Vdly__tb_sys3__DOT__dut__DOT__fin_sent);
        }
        if ((1U & (((((vlSelf->tb_sys3__DOT__dut__DOT__busy_l 
                       & vlSelf->tb_sys3__DOT__dut__DOT__halted_v) 
                      & vlSelf->tb_sys3__DOT__dut__DOT__halted_q) 
                     >> 4U) & (~ (vlSelf->tb_sys3__DOT__dut__DOT__start_v 
                                  >> 4U))) & (~ (vlSelf->tb_sys3__DOT__dut__DOT__fin_sent 
                                                 >> 4U))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__rq[0U] 
                = (0x10U | vlSelf->tb_sys3__DOT__dut__DOT__rq[0U]);
            __Vdly__tb_sys3__DOT__dut__DOT__fin_sent 
                = (0x10U | __Vdly__tb_sys3__DOT__dut__DOT__fin_sent);
        }
        if ((1U & (((((vlSelf->tb_sys3__DOT__dut__DOT__busy_l 
                       & vlSelf->tb_sys3__DOT__dut__DOT__halted_v) 
                      & vlSelf->tb_sys3__DOT__dut__DOT__halted_q) 
                     >> 5U) & (~ (vlSelf->tb_sys3__DOT__dut__DOT__start_v 
                                  >> 5U))) & (~ (vlSelf->tb_sys3__DOT__dut__DOT__fin_sent 
                                                 >> 5U))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__rq[0U] 
                = (0x20U | vlSelf->tb_sys3__DOT__dut__DOT__rq[0U]);
            __Vdly__tb_sys3__DOT__dut__DOT__fin_sent 
                = (0x20U | __Vdly__tb_sys3__DOT__dut__DOT__fin_sent);
        }
        if ((1U & (((((vlSelf->tb_sys3__DOT__dut__DOT__busy_l 
                       & vlSelf->tb_sys3__DOT__dut__DOT__halted_v) 
                      & vlSelf->tb_sys3__DOT__dut__DOT__halted_q) 
                     >> 6U) & (~ (vlSelf->tb_sys3__DOT__dut__DOT__start_v 
                                  >> 6U))) & (~ (vlSelf->tb_sys3__DOT__dut__DOT__fin_sent 
                                                 >> 6U))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__rq[0U] 
                = (0x40U | vlSelf->tb_sys3__DOT__dut__DOT__rq[0U]);
            __Vdly__tb_sys3__DOT__dut__DOT__fin_sent 
                = (0x40U | __Vdly__tb_sys3__DOT__dut__DOT__fin_sent);
        }
        if ((1U & (((((vlSelf->tb_sys3__DOT__dut__DOT__busy_l 
                       & vlSelf->tb_sys3__DOT__dut__DOT__halted_v) 
                      & vlSelf->tb_sys3__DOT__dut__DOT__halted_q) 
                     >> 7U) & (~ (vlSelf->tb_sys3__DOT__dut__DOT__start_v 
                                  >> 7U))) & (~ (vlSelf->tb_sys3__DOT__dut__DOT__fin_sent 
                                                 >> 7U))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__rq[0U] 
                = (0x80U | vlSelf->tb_sys3__DOT__dut__DOT__rq[0U]);
            __Vdly__tb_sys3__DOT__dut__DOT__fin_sent 
                = (0x80U | __Vdly__tb_sys3__DOT__dut__DOT__fin_sent);
        }
        if ((1U & (((((vlSelf->tb_sys3__DOT__dut__DOT__busy_l 
                       & vlSelf->tb_sys3__DOT__dut__DOT__halted_v) 
                      & vlSelf->tb_sys3__DOT__dut__DOT__halted_q) 
                     >> 8U) & (~ (vlSelf->tb_sys3__DOT__dut__DOT__start_v 
                                  >> 8U))) & (~ (vlSelf->tb_sys3__DOT__dut__DOT__fin_sent 
                                                 >> 8U))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__rq[0U] 
                = (0x100U | vlSelf->tb_sys3__DOT__dut__DOT__rq[0U]);
            __Vdly__tb_sys3__DOT__dut__DOT__fin_sent 
                = (0x100U | __Vdly__tb_sys3__DOT__dut__DOT__fin_sent);
        }
        if ((1U & (((((vlSelf->tb_sys3__DOT__dut__DOT__busy_l 
                       & vlSelf->tb_sys3__DOT__dut__DOT__halted_v) 
                      & vlSelf->tb_sys3__DOT__dut__DOT__halted_q) 
                     >> 9U) & (~ (vlSelf->tb_sys3__DOT__dut__DOT__start_v 
                                  >> 9U))) & (~ (vlSelf->tb_sys3__DOT__dut__DOT__fin_sent 
                                                 >> 9U))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__rq[0U] 
                = (0x200U | vlSelf->tb_sys3__DOT__dut__DOT__rq[0U]);
            __Vdly__tb_sys3__DOT__dut__DOT__fin_sent 
                = (0x200U | __Vdly__tb_sys3__DOT__dut__DOT__fin_sent);
        }
        if ((1U & (((((vlSelf->tb_sys3__DOT__dut__DOT__busy_l 
                       & vlSelf->tb_sys3__DOT__dut__DOT__halted_v) 
                      & vlSelf->tb_sys3__DOT__dut__DOT__halted_q) 
                     >> 0xaU) & (~ (vlSelf->tb_sys3__DOT__dut__DOT__start_v 
                                    >> 0xaU))) & (~ 
                                                  (vlSelf->tb_sys3__DOT__dut__DOT__fin_sent 
                                                   >> 0xaU))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__rq[0U] 
                = (0x400U | vlSelf->tb_sys3__DOT__dut__DOT__rq[0U]);
            __Vdly__tb_sys3__DOT__dut__DOT__fin_sent 
                = (0x400U | __Vdly__tb_sys3__DOT__dut__DOT__fin_sent);
        }
        if ((1U & (((((vlSelf->tb_sys3__DOT__dut__DOT__busy_l 
                       & vlSelf->tb_sys3__DOT__dut__DOT__halted_v) 
                      & vlSelf->tb_sys3__DOT__dut__DOT__halted_q) 
                     >> 0xbU) & (~ (vlSelf->tb_sys3__DOT__dut__DOT__start_v 
                                    >> 0xbU))) & (~ 
                                                  (vlSelf->tb_sys3__DOT__dut__DOT__fin_sent 
                                                   >> 0xbU))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__rq[0U] 
                = (0x800U | vlSelf->tb_sys3__DOT__dut__DOT__rq[0U]);
            __Vdly__tb_sys3__DOT__dut__DOT__fin_sent 
                = (0x800U | __Vdly__tb_sys3__DOT__dut__DOT__fin_sent);
        }
        if ((1U & (((((vlSelf->tb_sys3__DOT__dut__DOT__busy_l 
                       & vlSelf->tb_sys3__DOT__dut__DOT__halted_v) 
                      & vlSelf->tb_sys3__DOT__dut__DOT__halted_q) 
                     >> 0xcU) & (~ (vlSelf->tb_sys3__DOT__dut__DOT__start_v 
                                    >> 0xcU))) & (~ 
                                                  (vlSelf->tb_sys3__DOT__dut__DOT__fin_sent 
                                                   >> 0xcU))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__rq[0U] 
                = (0x1000U | vlSelf->tb_sys3__DOT__dut__DOT__rq[0U]);
            __Vdly__tb_sys3__DOT__dut__DOT__fin_sent 
                = (0x1000U | __Vdly__tb_sys3__DOT__dut__DOT__fin_sent);
        }
        if ((1U & (((((vlSelf->tb_sys3__DOT__dut__DOT__busy_l 
                       & vlSelf->tb_sys3__DOT__dut__DOT__halted_v) 
                      & vlSelf->tb_sys3__DOT__dut__DOT__halted_q) 
                     >> 0xdU) & (~ (vlSelf->tb_sys3__DOT__dut__DOT__start_v 
                                    >> 0xdU))) & (~ 
                                                  (vlSelf->tb_sys3__DOT__dut__DOT__fin_sent 
                                                   >> 0xdU))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__rq[0U] 
                = (0x2000U | vlSelf->tb_sys3__DOT__dut__DOT__rq[0U]);
            __Vdly__tb_sys3__DOT__dut__DOT__fin_sent 
                = (0x2000U | __Vdly__tb_sys3__DOT__dut__DOT__fin_sent);
        }
        if ((1U & (((((vlSelf->tb_sys3__DOT__dut__DOT__busy_l 
                       & vlSelf->tb_sys3__DOT__dut__DOT__halted_v) 
                      & vlSelf->tb_sys3__DOT__dut__DOT__halted_q) 
                     >> 0xeU) & (~ (vlSelf->tb_sys3__DOT__dut__DOT__start_v 
                                    >> 0xeU))) & (~ 
                                                  (vlSelf->tb_sys3__DOT__dut__DOT__fin_sent 
                                                   >> 0xeU))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__rq[0U] 
                = (0x4000U | vlSelf->tb_sys3__DOT__dut__DOT__rq[0U]);
            __Vdly__tb_sys3__DOT__dut__DOT__fin_sent 
                = (0x4000U | __Vdly__tb_sys3__DOT__dut__DOT__fin_sent);
        }
        if ((1U & (((((vlSelf->tb_sys3__DOT__dut__DOT__busy_l 
                       & vlSelf->tb_sys3__DOT__dut__DOT__halted_v) 
                      & vlSelf->tb_sys3__DOT__dut__DOT__halted_q) 
                     >> 0xfU) & (~ (vlSelf->tb_sys3__DOT__dut__DOT__start_v 
                                    >> 0xfU))) & (~ 
                                                  (vlSelf->tb_sys3__DOT__dut__DOT__fin_sent 
                                                   >> 0xfU))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__rq[0U] 
                = (0x8000U | vlSelf->tb_sys3__DOT__dut__DOT__rq[0U]);
            __Vdly__tb_sys3__DOT__dut__DOT__fin_sent 
                = (0x8000U | __Vdly__tb_sys3__DOT__dut__DOT__fin_sent);
        }
        if ((1U & (((((vlSelf->tb_sys3__DOT__dut__DOT__busy_l 
                       & vlSelf->tb_sys3__DOT__dut__DOT__halted_v) 
                      & vlSelf->tb_sys3__DOT__dut__DOT__halted_q) 
                     >> 0x10U) & (~ (vlSelf->tb_sys3__DOT__dut__DOT__start_v 
                                     >> 0x10U))) & 
                   (~ (vlSelf->tb_sys3__DOT__dut__DOT__fin_sent 
                       >> 0x10U))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__rq[0U] 
                = (0x10000U | vlSelf->tb_sys3__DOT__dut__DOT__rq[0U]);
            __Vdly__tb_sys3__DOT__dut__DOT__fin_sent 
                = (0x10000U | __Vdly__tb_sys3__DOT__dut__DOT__fin_sent);
        }
        if ((1U & (((((vlSelf->tb_sys3__DOT__dut__DOT__busy_l 
                       & vlSelf->tb_sys3__DOT__dut__DOT__halted_v) 
                      & vlSelf->tb_sys3__DOT__dut__DOT__halted_q) 
                     >> 0x11U) & (~ (vlSelf->tb_sys3__DOT__dut__DOT__start_v 
                                     >> 0x11U))) & 
                   (~ (vlSelf->tb_sys3__DOT__dut__DOT__fin_sent 
                       >> 0x11U))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__rq[0U] 
                = (0x20000U | vlSelf->tb_sys3__DOT__dut__DOT__rq[0U]);
            __Vdly__tb_sys3__DOT__dut__DOT__fin_sent 
                = (0x20000U | __Vdly__tb_sys3__DOT__dut__DOT__fin_sent);
        }
        if ((1U & (((((vlSelf->tb_sys3__DOT__dut__DOT__busy_l 
                       & vlSelf->tb_sys3__DOT__dut__DOT__halted_v) 
                      & vlSelf->tb_sys3__DOT__dut__DOT__halted_q) 
                     >> 0x12U) & (~ (vlSelf->tb_sys3__DOT__dut__DOT__start_v 
                                     >> 0x12U))) & 
                   (~ (vlSelf->tb_sys3__DOT__dut__DOT__fin_sent 
                       >> 0x12U))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__rq[0U] 
                = (0x40000U | vlSelf->tb_sys3__DOT__dut__DOT__rq[0U]);
            __Vdly__tb_sys3__DOT__dut__DOT__fin_sent 
                = (0x40000U | __Vdly__tb_sys3__DOT__dut__DOT__fin_sent);
        }
        if ((1U & (((((vlSelf->tb_sys3__DOT__dut__DOT__busy_l 
                       & vlSelf->tb_sys3__DOT__dut__DOT__halted_v) 
                      & vlSelf->tb_sys3__DOT__dut__DOT__halted_q) 
                     >> 0x13U) & (~ (vlSelf->tb_sys3__DOT__dut__DOT__start_v 
                                     >> 0x13U))) & 
                   (~ (vlSelf->tb_sys3__DOT__dut__DOT__fin_sent 
                       >> 0x13U))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__rq[0U] 
                = (0x80000U | vlSelf->tb_sys3__DOT__dut__DOT__rq[0U]);
            __Vdly__tb_sys3__DOT__dut__DOT__fin_sent 
                = (0x80000U | __Vdly__tb_sys3__DOT__dut__DOT__fin_sent);
        }
        if ((1U & (((((vlSelf->tb_sys3__DOT__dut__DOT__busy_l 
                       & vlSelf->tb_sys3__DOT__dut__DOT__halted_v) 
                      & vlSelf->tb_sys3__DOT__dut__DOT__halted_q) 
                     >> 0x14U) & (~ (vlSelf->tb_sys3__DOT__dut__DOT__start_v 
                                     >> 0x14U))) & 
                   (~ (vlSelf->tb_sys3__DOT__dut__DOT__fin_sent 
                       >> 0x14U))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__rq[0U] 
                = (0x100000U | vlSelf->tb_sys3__DOT__dut__DOT__rq[0U]);
            __Vdly__tb_sys3__DOT__dut__DOT__fin_sent 
                = (0x100000U | __Vdly__tb_sys3__DOT__dut__DOT__fin_sent);
        }
        if ((1U & (((((vlSelf->tb_sys3__DOT__dut__DOT__busy_l 
                       & vlSelf->tb_sys3__DOT__dut__DOT__halted_v) 
                      & vlSelf->tb_sys3__DOT__dut__DOT__halted_q) 
                     >> 0x15U) & (~ (vlSelf->tb_sys3__DOT__dut__DOT__start_v 
                                     >> 0x15U))) & 
                   (~ (vlSelf->tb_sys3__DOT__dut__DOT__fin_sent 
                       >> 0x15U))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__rq[0U] 
                = (0x200000U | vlSelf->tb_sys3__DOT__dut__DOT__rq[0U]);
            __Vdly__tb_sys3__DOT__dut__DOT__fin_sent 
                = (0x200000U | __Vdly__tb_sys3__DOT__dut__DOT__fin_sent);
        }
        if ((1U & (((((vlSelf->tb_sys3__DOT__dut__DOT__busy_l 
                       & vlSelf->tb_sys3__DOT__dut__DOT__halted_v) 
                      & vlSelf->tb_sys3__DOT__dut__DOT__halted_q) 
                     >> 0x16U) & (~ (vlSelf->tb_sys3__DOT__dut__DOT__start_v 
                                     >> 0x16U))) & 
                   (~ (vlSelf->tb_sys3__DOT__dut__DOT__fin_sent 
                       >> 0x16U))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__rq[0U] 
                = (0x400000U | vlSelf->tb_sys3__DOT__dut__DOT__rq[0U]);
            __Vdly__tb_sys3__DOT__dut__DOT__fin_sent 
                = (0x400000U | __Vdly__tb_sys3__DOT__dut__DOT__fin_sent);
        }
        if ((1U & (((((vlSelf->tb_sys3__DOT__dut__DOT__busy_l 
                       & vlSelf->tb_sys3__DOT__dut__DOT__halted_v) 
                      & vlSelf->tb_sys3__DOT__dut__DOT__halted_q) 
                     >> 0x17U) & (~ (vlSelf->tb_sys3__DOT__dut__DOT__start_v 
                                     >> 0x17U))) & 
                   (~ (vlSelf->tb_sys3__DOT__dut__DOT__fin_sent 
                       >> 0x17U))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__rq[0U] 
                = (0x800000U | vlSelf->tb_sys3__DOT__dut__DOT__rq[0U]);
            __Vdly__tb_sys3__DOT__dut__DOT__fin_sent 
                = (0x800000U | __Vdly__tb_sys3__DOT__dut__DOT__fin_sent);
        }
        if ((1U & (((((vlSelf->tb_sys3__DOT__dut__DOT__busy_l 
                       & vlSelf->tb_sys3__DOT__dut__DOT__halted_v) 
                      & vlSelf->tb_sys3__DOT__dut__DOT__halted_q) 
                     >> 0x18U) & (~ (vlSelf->tb_sys3__DOT__dut__DOT__start_v 
                                     >> 0x18U))) & 
                   (~ (vlSelf->tb_sys3__DOT__dut__DOT__fin_sent 
                       >> 0x18U))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__rq[0U] 
                = (0x1000000U | vlSelf->tb_sys3__DOT__dut__DOT__rq[0U]);
            __Vdly__tb_sys3__DOT__dut__DOT__fin_sent 
                = (0x1000000U | __Vdly__tb_sys3__DOT__dut__DOT__fin_sent);
        }
        if ((1U & (((((vlSelf->tb_sys3__DOT__dut__DOT__busy_l 
                       & vlSelf->tb_sys3__DOT__dut__DOT__halted_v) 
                      & vlSelf->tb_sys3__DOT__dut__DOT__halted_q) 
                     >> 0x19U) & (~ (vlSelf->tb_sys3__DOT__dut__DOT__start_v 
                                     >> 0x19U))) & 
                   (~ (vlSelf->tb_sys3__DOT__dut__DOT__fin_sent 
                       >> 0x19U))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__rq[0U] 
                = (0x2000000U | vlSelf->tb_sys3__DOT__dut__DOT__rq[0U]);
            __Vdly__tb_sys3__DOT__dut__DOT__fin_sent 
                = (0x2000000U | __Vdly__tb_sys3__DOT__dut__DOT__fin_sent);
        }
        if ((1U & (((((vlSelf->tb_sys3__DOT__dut__DOT__busy_l 
                       & vlSelf->tb_sys3__DOT__dut__DOT__halted_v) 
                      & vlSelf->tb_sys3__DOT__dut__DOT__halted_q) 
                     >> 0x1aU) & (~ (vlSelf->tb_sys3__DOT__dut__DOT__start_v 
                                     >> 0x1aU))) & 
                   (~ (vlSelf->tb_sys3__DOT__dut__DOT__fin_sent 
                       >> 0x1aU))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__rq[0U] 
                = (0x4000000U | vlSelf->tb_sys3__DOT__dut__DOT__rq[0U]);
            __Vdly__tb_sys3__DOT__dut__DOT__fin_sent 
                = (0x4000000U | __Vdly__tb_sys3__DOT__dut__DOT__fin_sent);
        }
        if ((1U & (((((vlSelf->tb_sys3__DOT__dut__DOT__busy_l 
                       & vlSelf->tb_sys3__DOT__dut__DOT__halted_v) 
                      & vlSelf->tb_sys3__DOT__dut__DOT__halted_q) 
                     >> 0x1bU) & (~ (vlSelf->tb_sys3__DOT__dut__DOT__start_v 
                                     >> 0x1bU))) & 
                   (~ (vlSelf->tb_sys3__DOT__dut__DOT__fin_sent 
                       >> 0x1bU))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__rq[0U] 
                = (0x8000000U | vlSelf->tb_sys3__DOT__dut__DOT__rq[0U]);
            __Vdly__tb_sys3__DOT__dut__DOT__fin_sent 
                = (0x8000000U | __Vdly__tb_sys3__DOT__dut__DOT__fin_sent);
        }
        if ((1U & (((((vlSelf->tb_sys3__DOT__dut__DOT__busy_l 
                       & vlSelf->tb_sys3__DOT__dut__DOT__halted_v) 
                      & vlSelf->tb_sys3__DOT__dut__DOT__halted_q) 
                     >> 0x1cU) & (~ (vlSelf->tb_sys3__DOT__dut__DOT__start_v 
                                     >> 0x1cU))) & 
                   (~ (vlSelf->tb_sys3__DOT__dut__DOT__fin_sent 
                       >> 0x1cU))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__rq[0U] 
                = (0x10000000U | vlSelf->tb_sys3__DOT__dut__DOT__rq[0U]);
            __Vdly__tb_sys3__DOT__dut__DOT__fin_sent 
                = (0x10000000U | __Vdly__tb_sys3__DOT__dut__DOT__fin_sent);
        }
        if ((1U & (((((vlSelf->tb_sys3__DOT__dut__DOT__busy_l 
                       & vlSelf->tb_sys3__DOT__dut__DOT__halted_v) 
                      & vlSelf->tb_sys3__DOT__dut__DOT__halted_q) 
                     >> 0x1dU) & (~ (vlSelf->tb_sys3__DOT__dut__DOT__start_v 
                                     >> 0x1dU))) & 
                   (~ (vlSelf->tb_sys3__DOT__dut__DOT__fin_sent 
                       >> 0x1dU))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__rq[0U] 
                = (0x20000000U | vlSelf->tb_sys3__DOT__dut__DOT__rq[0U]);
            __Vdly__tb_sys3__DOT__dut__DOT__fin_sent 
                = (0x20000000U | __Vdly__tb_sys3__DOT__dut__DOT__fin_sent);
        }
        if ((1U & (((((vlSelf->tb_sys3__DOT__dut__DOT__busy_l 
                       & vlSelf->tb_sys3__DOT__dut__DOT__halted_v) 
                      & vlSelf->tb_sys3__DOT__dut__DOT__halted_q) 
                     >> 0x1eU) & (~ (vlSelf->tb_sys3__DOT__dut__DOT__start_v 
                                     >> 0x1eU))) & 
                   (~ (vlSelf->tb_sys3__DOT__dut__DOT__fin_sent 
                       >> 0x1eU))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__rq[0U] 
                = (0x40000000U | vlSelf->tb_sys3__DOT__dut__DOT__rq[0U]);
            __Vdly__tb_sys3__DOT__dut__DOT__fin_sent 
                = (0x40000000U | __Vdly__tb_sys3__DOT__dut__DOT__fin_sent);
        }
        if ((1U & (((((vlSelf->tb_sys3__DOT__dut__DOT__busy_l 
                       & vlSelf->tb_sys3__DOT__dut__DOT__halted_v) 
                      & vlSelf->tb_sys3__DOT__dut__DOT__halted_q) 
                     >> 0x1fU) & (~ (vlSelf->tb_sys3__DOT__dut__DOT__start_v 
                                     >> 0x1fU))) & 
                   (~ (vlSelf->tb_sys3__DOT__dut__DOT__fin_sent 
                       >> 0x1fU))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__rq[0U] 
                = (0x80000000U | vlSelf->tb_sys3__DOT__dut__DOT__rq[0U]);
            __Vdly__tb_sys3__DOT__dut__DOT__fin_sent 
                = (0x80000000U | __Vdly__tb_sys3__DOT__dut__DOT__fin_sent);
        }
        if (((IData)(vlSelf->tb_sys3__DOT__ev_set) 
             & (0x40U <= (IData)(vlSelf->tb_sys3__DOT__ev_set_id)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__rq[((IData)(vlSelf->tb_sys3__DOT__ev_set_id) 
                                                >> 5U)] 
                = (vlSelf->tb_sys3__DOT__dut__DOT__rq[
                   ((IData)(vlSelf->tb_sys3__DOT__ev_set_id) 
                    >> 5U)] | ((IData)(1U) << (0x1fU 
                                               & (IData)(vlSelf->tb_sys3__DOT__ev_set_id))));
        }
        __Vdly__tb_sys3__DOT__dut__DOT__req_tab[0U] 
            = vlSelf->tb_sys3__DOT__dut__DOT__rq[0U];
        __Vdly__tb_sys3__DOT__dut__DOT__req_tab[1U] 
            = vlSelf->tb_sys3__DOT__dut__DOT__rq[1U];
        __Vdly__tb_sys3__DOT__dut__DOT__req_tab[2U] 
            = vlSelf->tb_sys3__DOT__dut__DOT__rq[2U];
        __Vdly__tb_sys3__DOT__dut__DOT__req_tab[3U] 
            = vlSelf->tb_sys3__DOT__dut__DOT__rq[3U];
        __Vdly__tb_sys3__DOT__dut__DOT__req_tab[4U] 
            = vlSelf->tb_sys3__DOT__dut__DOT__rq[4U];
        __Vdly__tb_sys3__DOT__dut__DOT__req_tab[5U] 
            = vlSelf->tb_sys3__DOT__dut__DOT__rq[5U];
        __Vdly__tb_sys3__DOT__dut__DOT__req_tab[6U] 
            = vlSelf->tb_sys3__DOT__dut__DOT__rq[6U];
        __Vdly__tb_sys3__DOT__dut__DOT__req_tab[7U] 
            = vlSelf->tb_sys3__DOT__dut__DOT__rq[7U];
        __Vdly__tb_sys3__DOT__dut__DOT__halted_q = vlSelf->tb_sys3__DOT__dut__DOT__halted_v;
        __Vdly__tb_sys3__DOT__dut__DOT__slice_busy 
            = vlSelf->tb_sys3__DOT__dut__DOT__nb;
        __Vdly__tb_sys3__DOT__dut__DOT__rescan = vlSelf->tb_sys3__DOT__dut__DOT__rs;
    }
    if (__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__dm__v0) {
        vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__dm[__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__dm__v0] 
            = __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__dm__v0;
    }
    if (__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__dm__v0) {
        vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__dm[__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__dm__v0] 
            = __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__dm__v0;
    }
    if (__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__dm__v0) {
        vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__dm[__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__dm__v0] 
            = __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__dm__v0;
    }
    if (__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__28__KET____DOT__dm__v0) {
        vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__28__KET____DOT__dm[__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__28__KET____DOT__dm__v0] 
            = __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__28__KET____DOT__dm__v0;
    }
    if (__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__27__KET____DOT__dm__v0) {
        vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__27__KET____DOT__dm[__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__27__KET____DOT__dm__v0] 
            = __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__27__KET____DOT__dm__v0;
    }
    if (__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__26__KET____DOT__dm__v0) {
        vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__26__KET____DOT__dm[__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__26__KET____DOT__dm__v0] 
            = __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__26__KET____DOT__dm__v0;
    }
    if (__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__25__KET____DOT__dm__v0) {
        vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__25__KET____DOT__dm[__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__25__KET____DOT__dm__v0] 
            = __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__25__KET____DOT__dm__v0;
    }
    if (__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__24__KET____DOT__dm__v0) {
        vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__24__KET____DOT__dm[__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__24__KET____DOT__dm__v0] 
            = __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__24__KET____DOT__dm__v0;
    }
    if (__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__23__KET____DOT__dm__v0) {
        vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__23__KET____DOT__dm[__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__23__KET____DOT__dm__v0] 
            = __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__23__KET____DOT__dm__v0;
    }
    if (__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__22__KET____DOT__dm__v0) {
        vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__22__KET____DOT__dm[__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__22__KET____DOT__dm__v0] 
            = __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__22__KET____DOT__dm__v0;
    }
    if (__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__21__KET____DOT__dm__v0) {
        vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__21__KET____DOT__dm[__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__21__KET____DOT__dm__v0] 
            = __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__21__KET____DOT__dm__v0;
    }
    if (__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__20__KET____DOT__dm__v0) {
        vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__20__KET____DOT__dm[__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__20__KET____DOT__dm__v0] 
            = __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__20__KET____DOT__dm__v0;
    }
    if (__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__19__KET____DOT__dm__v0) {
        vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__19__KET____DOT__dm[__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__19__KET____DOT__dm__v0] 
            = __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__19__KET____DOT__dm__v0;
    }
    if (__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__18__KET____DOT__dm__v0) {
        vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__18__KET____DOT__dm[__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__18__KET____DOT__dm__v0] 
            = __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__18__KET____DOT__dm__v0;
    }
    if (__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__17__KET____DOT__dm__v0) {
        vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__17__KET____DOT__dm[__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__17__KET____DOT__dm__v0] 
            = __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__17__KET____DOT__dm__v0;
    }
    if (__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__16__KET____DOT__dm__v0) {
        vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__16__KET____DOT__dm[__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__16__KET____DOT__dm__v0] 
            = __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__16__KET____DOT__dm__v0;
    }
    if (__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__15__KET____DOT__dm__v0) {
        vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__15__KET____DOT__dm[__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__15__KET____DOT__dm__v0] 
            = __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__15__KET____DOT__dm__v0;
    }
    if (__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__14__KET____DOT__dm__v0) {
        vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__14__KET____DOT__dm[__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__14__KET____DOT__dm__v0] 
            = __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__14__KET____DOT__dm__v0;
    }
    if (__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__13__KET____DOT__dm__v0) {
        vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__13__KET____DOT__dm[__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__13__KET____DOT__dm__v0] 
            = __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__13__KET____DOT__dm__v0;
    }
    if (__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__12__KET____DOT__dm__v0) {
        vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__12__KET____DOT__dm[__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__12__KET____DOT__dm__v0] 
            = __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__12__KET____DOT__dm__v0;
    }
    if (__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__11__KET____DOT__dm__v0) {
        vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__11__KET____DOT__dm[__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__11__KET____DOT__dm__v0] 
            = __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__11__KET____DOT__dm__v0;
    }
    if (__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__10__KET____DOT__dm__v0) {
        vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__10__KET____DOT__dm[__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__10__KET____DOT__dm__v0] 
            = __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__10__KET____DOT__dm__v0;
    }
    if (__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__9__KET____DOT__dm__v0) {
        vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__9__KET____DOT__dm[__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__9__KET____DOT__dm__v0] 
            = __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__9__KET____DOT__dm__v0;
    }
    if (__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__8__KET____DOT__dm__v0) {
        vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__8__KET____DOT__dm[__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__8__KET____DOT__dm__v0] 
            = __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__8__KET____DOT__dm__v0;
    }
    if (__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__7__KET____DOT__dm__v0) {
        vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__7__KET____DOT__dm[__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__7__KET____DOT__dm__v0] 
            = __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__7__KET____DOT__dm__v0;
    }
    if (__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__6__KET____DOT__dm__v0) {
        vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__6__KET____DOT__dm[__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__6__KET____DOT__dm__v0] 
            = __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__6__KET____DOT__dm__v0;
    }
    if (__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__5__KET____DOT__dm__v0) {
        vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__5__KET____DOT__dm[__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__5__KET____DOT__dm__v0] 
            = __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__5__KET____DOT__dm__v0;
    }
    if (__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__4__KET____DOT__dm__v0) {
        vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__4__KET____DOT__dm[__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__4__KET____DOT__dm__v0] 
            = __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__4__KET____DOT__dm__v0;
    }
    if (__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__3__KET____DOT__dm__v0) {
        vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__3__KET____DOT__dm[__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__3__KET____DOT__dm__v0] 
            = __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__3__KET____DOT__dm__v0;
    }
    if (__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__2__KET____DOT__dm__v0) {
        vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__2__KET____DOT__dm[__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__2__KET____DOT__dm__v0] 
            = __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__2__KET____DOT__dm__v0;
    }
    if (__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__1__KET____DOT__dm__v0) {
        vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__1__KET____DOT__dm[__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__1__KET____DOT__dm__v0] 
            = __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__1__KET____DOT__dm__v0;
    }
    if (__Vdlyvset__tb_sys3__DOT__dut__DOT__slot__BRA__0__KET____DOT__dm__v0) {
        vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__0__KET____DOT__dm[__Vdlyvdim0__tb_sys3__DOT__dut__DOT__slot__BRA__0__KET____DOT__dm__v0] 
            = __Vdlyvval__tb_sys3__DOT__dut__DOT__slot__BRA__0__KET____DOT__dm__v0;
    }
    vlSelf->tb_sys3__DOT__dut__DOT__busy_l = __Vdly__tb_sys3__DOT__dut__DOT__busy_l;
    vlSelf->tb_sys3__DOT__dut__DOT__fin_sent = __Vdly__tb_sys3__DOT__dut__DOT__fin_sent;
    vlSelf->tb_sys3__DOT__dut__DOT__done_count = __Vdly__tb_sys3__DOT__dut__DOT__done_count;
    vlSelf->tb_sys3__DOT__dut__DOT__ev_cnt = __Vdly__tb_sys3__DOT__dut__DOT__ev_cnt;
    vlSelf->tb_sys3__DOT__dut__DOT__busy_slice_cycles 
        = __Vdly__tb_sys3__DOT__dut__DOT__busy_slice_cycles;
    vlSelf->tb_sys3__DOT__dut__DOT__waste_blocked = __Vdly__tb_sys3__DOT__dut__DOT__waste_blocked;
    vlSelf->tb_sys3__DOT__dut__DOT__waste_tail = __Vdly__tb_sys3__DOT__dut__DOT__waste_tail;
    vlSelf->tb_sys3__DOT__dut__DOT__search_cycles = __Vdly__tb_sys3__DOT__dut__DOT__search_cycles;
    vlSelf->tb_sys3__DOT__dut__DOT__launch_err = __Vdly__tb_sys3__DOT__dut__DOT__launch_err;
    vlSelf->tb_sys3__DOT__dut__DOT__dispatches = __Vdly__tb_sys3__DOT__dut__DOT__dispatches;
    vlSelf->tb_sys3__DOT__dut__DOT__dstate = __Vdly__tb_sys3__DOT__dut__DOT__dstate;
    vlSelf->tb_sys3__DOT__dut__DOT__rescan = __Vdly__tb_sys3__DOT__dut__DOT__rescan;
    vlSelf->tb_sys3__DOT__dut__DOT__ph = __Vdly__tb_sys3__DOT__dut__DOT__ph;
    vlSelf->tb_sys3__DOT__dut__DOT__cand = __Vdly__tb_sys3__DOT__dut__DOT__cand;
    vlSelf->tb_sys3__DOT__dut__DOT__halted_q = __Vdly__tb_sys3__DOT__dut__DOT__halted_q;
    vlSelf->tb_sys3__DOT__dut__DOT__cur_is_crit = __Vdly__tb_sys3__DOT__dut__DOT__cur_is_crit;
    vlSelf->tb_sys3__DOT__dut__DOT__cur_tid = __Vdly__tb_sys3__DOT__dut__DOT__cur_tid;
    vlSelf->tb_sys3__DOT__dut__DOT__cur_code = __Vdly__tb_sys3__DOT__dut__DOT__cur_code;
    vlSelf->tb_sys3__DOT__dut__DOT__crit_streak = __Vdly__tb_sys3__DOT__dut__DOT__crit_streak;
    vlSelf->tb_sys3__DOT__dut__DOT__bulk_pass = __Vdly__tb_sys3__DOT__dut__DOT__bulk_pass;
    vlSelf->tb_sys3__DOT__dut__DOT__cur_bk = __Vdly__tb_sys3__DOT__dut__DOT__cur_bk;
    if (__Vdlyvset__tb_sys3__DOT__dut__DOT__qc__v0) {
        vlSelf->tb_sys3__DOT__dut__DOT__qc[__Vdlyvdim0__tb_sys3__DOT__dut__DOT__qc__v0] 
            = __Vdlyvval__tb_sys3__DOT__dut__DOT__qc__v0;
    }
    if (__Vdlyvset__tb_sys3__DOT__dut__DOT__ev_pl__v0) {
        vlSelf->tb_sys3__DOT__dut__DOT__ev_pl[__Vdlyvdim0__tb_sys3__DOT__dut__DOT__ev_pl__v0] 
            = __Vdlyvval__tb_sys3__DOT__dut__DOT__ev_pl__v0;
    }
    if (__Vdlyvset__tb_sys3__DOT__dut__DOT__prof__v0) {
        vlSelf->tb_sys3__DOT__dut__DOT__prof[__Vdlyvdim0__tb_sys3__DOT__dut__DOT__prof__v0] 
            = __Vdlyvval__tb_sys3__DOT__dut__DOT__prof__v0;
    }
    vlSelf->tb_sys3__DOT__dut__DOT__qc_wr = __Vdly__tb_sys3__DOT__dut__DOT__qc_wr;
    vlSelf->tb_sys3__DOT__dut__DOT__qc_rd = __Vdly__tb_sys3__DOT__dut__DOT__qc_rd;
    vlSelf->tb_sys3__DOT__dut__DOT__req_tab[0U] = __Vdly__tb_sys3__DOT__dut__DOT__req_tab[0U];
    vlSelf->tb_sys3__DOT__dut__DOT__req_tab[1U] = __Vdly__tb_sys3__DOT__dut__DOT__req_tab[1U];
    vlSelf->tb_sys3__DOT__dut__DOT__req_tab[2U] = __Vdly__tb_sys3__DOT__dut__DOT__req_tab[2U];
    vlSelf->tb_sys3__DOT__dut__DOT__req_tab[3U] = __Vdly__tb_sys3__DOT__dut__DOT__req_tab[3U];
    vlSelf->tb_sys3__DOT__dut__DOT__req_tab[4U] = __Vdly__tb_sys3__DOT__dut__DOT__req_tab[4U];
    vlSelf->tb_sys3__DOT__dut__DOT__req_tab[5U] = __Vdly__tb_sys3__DOT__dut__DOT__req_tab[5U];
    vlSelf->tb_sys3__DOT__dut__DOT__req_tab[6U] = __Vdly__tb_sys3__DOT__dut__DOT__req_tab[6U];
    vlSelf->tb_sys3__DOT__dut__DOT__req_tab[7U] = __Vdly__tb_sys3__DOT__dut__DOT__req_tab[7U];
    if (__Vdlyvset__tb_sys3__DOT__dut__DOT__t_pred__v0) {
        vlSelf->tb_sys3__DOT__dut__DOT__t_prog[__Vdlyvdim0__tb_sys3__DOT__dut__DOT__t_prog__v0] 
            = __Vdlyvval__tb_sys3__DOT__dut__DOT__t_prog__v0;
        vlSelf->tb_sys3__DOT__dut__DOT__t_pred[__Vdlyvdim0__tb_sys3__DOT__dut__DOT__t_pred__v0] 
            = __Vdlyvval__tb_sys3__DOT__dut__DOT__t_pred__v0;
    }
    if (__Vdlyvset__tb_sys3__DOT__dut__DOT__ev_id__v0) {
        vlSelf->tb_sys3__DOT__dut__DOT__ev_cyc[__Vdlyvdim0__tb_sys3__DOT__dut__DOT__ev_cyc__v0] 
            = __Vdlyvval__tb_sys3__DOT__dut__DOT__ev_cyc__v0;
        vlSelf->tb_sys3__DOT__dut__DOT__ev_data[__Vdlyvdim0__tb_sys3__DOT__dut__DOT__ev_data__v0] 
            = __Vdlyvval__tb_sys3__DOT__dut__DOT__ev_data__v0;
        vlSelf->tb_sys3__DOT__dut__DOT__ev_id[__Vdlyvdim0__tb_sys3__DOT__dut__DOT__ev_id__v0] 
            = __Vdlyvval__tb_sys3__DOT__dut__DOT__ev_id__v0;
    }
    vlSelf->tb_sys3__DOT__dut__DOT__slice_busy = __Vdly__tb_sys3__DOT__dut__DOT__slice_busy;
    vlSelf->tb_sys3__DOT__dut__DOT__cur_lw = __Vdly__tb_sys3__DOT__dut__DOT__cur_lw;
    if (__Vdlyvset__tb_sys3__DOT__dut__DOT__own_tid__v0) {
        vlSelf->tb_sys3__DOT__dut__DOT__t_slot[__Vdlyvdim0__tb_sys3__DOT__dut__DOT__t_slot__v0] 
            = __Vdlyvval__tb_sys3__DOT__dut__DOT__t_slot__v0;
        vlSelf->tb_sys3__DOT__dut__DOT__t_start[__Vdlyvdim0__tb_sys3__DOT__dut__DOT__t_start__v0] 
            = __Vdlyvval__tb_sys3__DOT__dut__DOT__t_start__v0;
        vlSelf->tb_sys3__DOT__dut__DOT__own_lw[__Vdlyvdim0__tb_sys3__DOT__dut__DOT__own_lw__v0] 
            = __Vdlyvval__tb_sys3__DOT__dut__DOT__own_lw__v0;
        vlSelf->tb_sys3__DOT__dut__DOT__own_tid[__Vdlyvdim0__tb_sys3__DOT__dut__DOT__own_tid__v0] 
            = __Vdlyvval__tb_sys3__DOT__dut__DOT__own_tid__v0;
        vlSelf->tb_sys3__DOT__dut__DOT__t_state[__Vdlyvdim0__tb_sys3__DOT__dut__DOT__t_state__v0] = 2U;
    }
    if (__Vdlyvset__tb_sys3__DOT__dut__DOT__t_code__v0) {
        vlSelf->tb_sys3__DOT__dut__DOT__t_arr[__Vdlyvdim0__tb_sys3__DOT__dut__DOT__t_arr__v0] 
            = __Vdlyvval__tb_sys3__DOT__dut__DOT__t_arr__v0;
        vlSelf->tb_sys3__DOT__dut__DOT__t_crit[__Vdlyvdim0__tb_sys3__DOT__dut__DOT__t_crit__v0] 
            = __Vdlyvval__tb_sys3__DOT__dut__DOT__t_crit__v0;
        vlSelf->tb_sys3__DOT__dut__DOT__t_lw[__Vdlyvdim0__tb_sys3__DOT__dut__DOT__t_lw__v0] 
            = __Vdlyvval__tb_sys3__DOT__dut__DOT__t_lw__v0;
        vlSelf->tb_sys3__DOT__dut__DOT__t_code[__Vdlyvdim0__tb_sys3__DOT__dut__DOT__t_code__v0] 
            = __Vdlyvval__tb_sys3__DOT__dut__DOT__t_code__v0;
        vlSelf->tb_sys3__DOT__dut__DOT__t_state[__Vdlyvdim0__tb_sys3__DOT__dut__DOT__t_state__v1] = 1U;
    }
    if (__Vdlyvset__tb_sys3__DOT__dut__DOT__t_end__v0) {
        vlSelf->tb_sys3__DOT__dut__DOT__t_trap[__Vdlyvdim0__tb_sys3__DOT__dut__DOT__t_trap__v0] 
            = __Vdlyvval__tb_sys3__DOT__dut__DOT__t_trap__v0;
        vlSelf->tb_sys3__DOT__dut__DOT__t_a0[__Vdlyvdim0__tb_sys3__DOT__dut__DOT__t_a0__v0] 
            = __Vdlyvval__tb_sys3__DOT__dut__DOT__t_a0__v0;
        vlSelf->tb_sys3__DOT__dut__DOT__t_end[__Vdlyvdim0__tb_sys3__DOT__dut__DOT__t_end__v0] 
            = __Vdlyvval__tb_sys3__DOT__dut__DOT__t_end__v0;
        vlSelf->tb_sys3__DOT__dut__DOT__t_state[__Vdlyvdim0__tb_sys3__DOT__dut__DOT__t_state__v2] = 3U;
    }
    if (__Vdlyvset__tb_sys3__DOT__dut__DOT__kwr__v0) {
        vlSelf->tb_sys3__DOT__dut__DOT__kwr[0U] = 0U;
        vlSelf->tb_sys3__DOT__dut__DOT__krd[0U] = 0U;
    }
    if (__Vdlyvset__tb_sys3__DOT__dut__DOT__kwr__v1) {
        vlSelf->tb_sys3__DOT__dut__DOT__kwr[1U] = 0U;
        vlSelf->tb_sys3__DOT__dut__DOT__kwr[2U] = 0U;
        vlSelf->tb_sys3__DOT__dut__DOT__kwr[3U] = 0U;
        vlSelf->tb_sys3__DOT__dut__DOT__kwr[4U] = 0U;
        vlSelf->tb_sys3__DOT__dut__DOT__kwr[5U] = 0U;
        vlSelf->tb_sys3__DOT__dut__DOT__kwr[6U] = 0U;
        vlSelf->tb_sys3__DOT__dut__DOT__kwr[7U] = 0U;
        vlSelf->tb_sys3__DOT__dut__DOT__krd[1U] = 0U;
        vlSelf->tb_sys3__DOT__dut__DOT__krd[2U] = 0U;
        vlSelf->tb_sys3__DOT__dut__DOT__krd[3U] = 0U;
        vlSelf->tb_sys3__DOT__dut__DOT__krd[4U] = 0U;
        vlSelf->tb_sys3__DOT__dut__DOT__krd[5U] = 0U;
        vlSelf->tb_sys3__DOT__dut__DOT__krd[6U] = 0U;
        vlSelf->tb_sys3__DOT__dut__DOT__krd[7U] = 0U;
    }
    if (__Vdlyvset__tb_sys3__DOT__dut__DOT__qk__v0) {
        vlSelf->tb_sys3__DOT__dut__DOT__qk[__Vdlyvdim0__tb_sys3__DOT__dut__DOT__qk__v0] 
            = __Vdlyvval__tb_sys3__DOT__dut__DOT__qk__v0;
        vlSelf->tb_sys3__DOT__dut__DOT__kwr[__Vdlyvdim0__tb_sys3__DOT__dut__DOT__kwr__v8] 
            = __Vdlyvval__tb_sys3__DOT__dut__DOT__kwr__v8;
    }
    if (__Vdlyvset__tb_sys3__DOT__dut__DOT__krd__v8) {
        vlSelf->tb_sys3__DOT__dut__DOT__krd[__Vdlyvdim0__tb_sys3__DOT__dut__DOT__krd__v8] 
            = __Vdlyvval__tb_sys3__DOT__dut__DOT__krd__v8;
    }
    vlSelf->tb_sys3__DOT__dut__DOT__pend_c = (vlSelf->tb_sys3__DOT__dut__DOT__qc_wr 
                                              != vlSelf->tb_sys3__DOT__dut__DOT__qc_rd);
    vlSelf->tb_sys3__DOT__dut__DOT__w_found = 0U;
    vlSelf->tb_sys3__DOT__dut__DOT__w_id = 0U;
    tb_sys3__DOT__dut__DOT__wi = 0xffU;
    while (VL_LTES_III(32, 0U, tb_sys3__DOT__dut__DOT__wi)) {
        if ((1U & (vlSelf->tb_sys3__DOT__dut__DOT__req_tab[
                   (7U & (tb_sys3__DOT__dut__DOT__wi 
                          >> 5U))] >> (0x1fU & tb_sys3__DOT__dut__DOT__wi)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__w_found = 1U;
            vlSelf->tb_sys3__DOT__dut__DOT__w_id = 
                (0xffU & tb_sys3__DOT__dut__DOT__wi);
        }
        tb_sys3__DOT__dut__DOT__wi = (tb_sys3__DOT__dut__DOT__wi 
                                      - (IData)(1U));
    }
    vlSelf->tb_sys3__DOT__dut__DOT__cur_w = (0x3fU 
                                             & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)));
    vlSelf->tb_sys3__DOT__dut__DOT__fit_found = 0U;
    vlSelf->tb_sys3__DOT__dut__DOT__fit_base = 0U;
    tb_sys3__DOT__dut__DOT__best_sz = 0x7fU;
    tb_sys3__DOT__dut__DOT__bsz = 0U;
    tb_sys3__DOT__dut__DOT__blk = 0U;
    tb_sys3__DOT__dut__DOT__bbase = 0U;
    if (((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))) 
         & (0ULL == (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys3__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)));
        tb_sys3__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = 0U;
            if (((0x20U >= (IData)(tb_sys3__DOT__dut__DOT__blk)) 
                 & (0ULL == (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = 0U;
            if (((0x20U >= (IData)(tb_sys3__DOT__dut__DOT__blk)) 
                 & (0ULL == (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = 0U;
            if (((0x20U >= (IData)(tb_sys3__DOT__dut__DOT__blk)) 
                 & (0ULL == (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = 0U;
            if (((0x20U >= (IData)(tb_sys3__DOT__dut__DOT__blk)) 
                 & (0ULL == (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = 0U;
            if (((0x20U >= (IData)(tb_sys3__DOT__dut__DOT__blk)) 
                 & (0ULL == (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = 0U;
            if (((0x20U >= (IData)(tb_sys3__DOT__dut__DOT__blk)) 
                 & (0ULL == (vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys3__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys3__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys3__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys3__DOT__dut__DOT__fit_base = 0U;
            tb_sys3__DOT__dut__DOT__best_sz = tb_sys3__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (1U & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))) 
                        - (IData)(1U)))) & (0x20U >= 
                                            ((IData)(1U) 
                                             + (0x3fU 
                                                & ((IData)(1U) 
                                                   << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys3__DOT__dut__DOT__slice_busy, 1U) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys3__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)));
        tb_sys3__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (1U & (~ 
                                                   ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (1U & (~ 
                                                   ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (1U & (~ 
                                                   ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (1U & (~ 
                                                   ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (1U & (~ 
                                                   ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (1U & (~ 
                                                   ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys3__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys3__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys3__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys3__DOT__dut__DOT__fit_base = 1U;
            tb_sys3__DOT__dut__DOT__best_sz = tb_sys3__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (2U & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))) 
                        - (IData)(1U)))) & (0x20U >= 
                                            ((IData)(2U) 
                                             + (0x3fU 
                                                & ((IData)(1U) 
                                                   << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys3__DOT__dut__DOT__slice_busy, 2U) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys3__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)));
        tb_sys3__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (2U & (~ 
                                                   ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (2U & (~ 
                                                   ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (2U & (~ 
                                                   ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (2U & (~ 
                                                   ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (2U & (~ 
                                                   ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (2U & (~ 
                                                   ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys3__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys3__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys3__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys3__DOT__dut__DOT__fit_base = 2U;
            tb_sys3__DOT__dut__DOT__best_sz = tb_sys3__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (3U & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))) 
                        - (IData)(1U)))) & (0x20U >= 
                                            ((IData)(3U) 
                                             + (0x3fU 
                                                & ((IData)(1U) 
                                                   << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys3__DOT__dut__DOT__slice_busy, 3U) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys3__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)));
        tb_sys3__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (3U & (~ 
                                                   ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (3U & (~ 
                                                   ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (3U & (~ 
                                                   ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (3U & (~ 
                                                   ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (3U & (~ 
                                                   ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (3U & (~ 
                                                   ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys3__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys3__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys3__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys3__DOT__dut__DOT__fit_base = 3U;
            tb_sys3__DOT__dut__DOT__best_sz = tb_sys3__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (4U & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))) 
                        - (IData)(1U)))) & (0x20U >= 
                                            ((IData)(4U) 
                                             + (0x3fU 
                                                & ((IData)(1U) 
                                                   << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys3__DOT__dut__DOT__slice_busy, 4U) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys3__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)));
        tb_sys3__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (4U & (~ 
                                                   ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (4U & (~ 
                                                   ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (4U & (~ 
                                                   ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (4U & (~ 
                                                   ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (4U & (~ 
                                                   ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (4U & (~ 
                                                   ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys3__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys3__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys3__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys3__DOT__dut__DOT__fit_base = 4U;
            tb_sys3__DOT__dut__DOT__best_sz = tb_sys3__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (5U & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))) 
                        - (IData)(1U)))) & (0x20U >= 
                                            ((IData)(5U) 
                                             + (0x3fU 
                                                & ((IData)(1U) 
                                                   << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys3__DOT__dut__DOT__slice_busy, 5U) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys3__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)));
        tb_sys3__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (5U & (~ 
                                                   ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (5U & (~ 
                                                   ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (5U & (~ 
                                                   ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (5U & (~ 
                                                   ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (5U & (~ 
                                                   ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (5U & (~ 
                                                   ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys3__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys3__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys3__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys3__DOT__dut__DOT__fit_base = 5U;
            tb_sys3__DOT__dut__DOT__best_sz = tb_sys3__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (6U & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))) 
                        - (IData)(1U)))) & (0x20U >= 
                                            ((IData)(6U) 
                                             + (0x3fU 
                                                & ((IData)(1U) 
                                                   << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys3__DOT__dut__DOT__slice_busy, 6U) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys3__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)));
        tb_sys3__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (6U & (~ 
                                                   ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (6U & (~ 
                                                   ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (6U & (~ 
                                                   ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (6U & (~ 
                                                   ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (6U & (~ 
                                                   ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (6U & (~ 
                                                   ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys3__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys3__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys3__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys3__DOT__dut__DOT__fit_base = 6U;
            tb_sys3__DOT__dut__DOT__best_sz = tb_sys3__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (7U & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))) 
                        - (IData)(1U)))) & (0x20U >= 
                                            ((IData)(7U) 
                                             + (0x3fU 
                                                & ((IData)(1U) 
                                                   << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys3__DOT__dut__DOT__slice_busy, 7U) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys3__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)));
        tb_sys3__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (7U & (~ 
                                                   ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (7U & (~ 
                                                   ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (7U & (~ 
                                                   ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (7U & (~ 
                                                   ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (7U & (~ 
                                                   ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (7U & (~ 
                                                   ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys3__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys3__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys3__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys3__DOT__dut__DOT__fit_base = 7U;
            tb_sys3__DOT__dut__DOT__best_sz = tb_sys3__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (8U & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))) 
                        - (IData)(1U)))) & (0x20U >= 
                                            ((IData)(8U) 
                                             + (0x3fU 
                                                & ((IData)(1U) 
                                                   << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys3__DOT__dut__DOT__slice_busy, 8U) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys3__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)));
        tb_sys3__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (8U & (~ 
                                                   ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (8U & (~ 
                                                   ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (8U & (~ 
                                                   ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (8U & (~ 
                                                   ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (8U & (~ 
                                                   ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (8U & (~ 
                                                   ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys3__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys3__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys3__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys3__DOT__dut__DOT__fit_base = 8U;
            tb_sys3__DOT__dut__DOT__best_sz = tb_sys3__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (9U & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))) 
                        - (IData)(1U)))) & (0x20U >= 
                                            ((IData)(9U) 
                                             + (0x3fU 
                                                & ((IData)(1U) 
                                                   << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys3__DOT__dut__DOT__slice_busy, 9U) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys3__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)));
        tb_sys3__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (9U & (~ 
                                                   ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (9U & (~ 
                                                   ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (9U & (~ 
                                                   ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (9U & (~ 
                                                   ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (9U & (~ 
                                                   ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (9U & (~ 
                                                   ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys3__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys3__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys3__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys3__DOT__dut__DOT__fit_base = 9U;
            tb_sys3__DOT__dut__DOT__best_sz = tb_sys3__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (0xaU & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))) 
                          - (IData)(1U)))) & (0x20U 
                                              >= ((IData)(0xaU) 
                                                  + 
                                                  (0x3fU 
                                                   & ((IData)(1U) 
                                                      << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys3__DOT__dut__DOT__slice_busy, 0xaU) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys3__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)));
        tb_sys3__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0xaU & 
                                             (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0xaU & 
                                             (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0xaU & 
                                             (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0xaU & 
                                             (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0xaU & 
                                             (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0xaU & 
                                             (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys3__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys3__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys3__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys3__DOT__dut__DOT__fit_base = 0xaU;
            tb_sys3__DOT__dut__DOT__best_sz = tb_sys3__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (0xbU & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))) 
                          - (IData)(1U)))) & (0x20U 
                                              >= ((IData)(0xbU) 
                                                  + 
                                                  (0x3fU 
                                                   & ((IData)(1U) 
                                                      << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys3__DOT__dut__DOT__slice_busy, 0xbU) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys3__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)));
        tb_sys3__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0xbU & 
                                             (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0xbU & 
                                             (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0xbU & 
                                             (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0xbU & 
                                             (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0xbU & 
                                             (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0xbU & 
                                             (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys3__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys3__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys3__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys3__DOT__dut__DOT__fit_base = 0xbU;
            tb_sys3__DOT__dut__DOT__best_sz = tb_sys3__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (0xcU & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))) 
                          - (IData)(1U)))) & (0x20U 
                                              >= ((IData)(0xcU) 
                                                  + 
                                                  (0x3fU 
                                                   & ((IData)(1U) 
                                                      << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys3__DOT__dut__DOT__slice_busy, 0xcU) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys3__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)));
        tb_sys3__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0xcU & 
                                             (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0xcU & 
                                             (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0xcU & 
                                             (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0xcU & 
                                             (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0xcU & 
                                             (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0xcU & 
                                             (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys3__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys3__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys3__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys3__DOT__dut__DOT__fit_base = 0xcU;
            tb_sys3__DOT__dut__DOT__best_sz = tb_sys3__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (0xdU & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))) 
                          - (IData)(1U)))) & (0x20U 
                                              >= ((IData)(0xdU) 
                                                  + 
                                                  (0x3fU 
                                                   & ((IData)(1U) 
                                                      << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys3__DOT__dut__DOT__slice_busy, 0xdU) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys3__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)));
        tb_sys3__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0xdU & 
                                             (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0xdU & 
                                             (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0xdU & 
                                             (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0xdU & 
                                             (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0xdU & 
                                             (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0xdU & 
                                             (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys3__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys3__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys3__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys3__DOT__dut__DOT__fit_base = 0xdU;
            tb_sys3__DOT__dut__DOT__best_sz = tb_sys3__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (0xeU & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))) 
                          - (IData)(1U)))) & (0x20U 
                                              >= ((IData)(0xeU) 
                                                  + 
                                                  (0x3fU 
                                                   & ((IData)(1U) 
                                                      << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys3__DOT__dut__DOT__slice_busy, 0xeU) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys3__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)));
        tb_sys3__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0xeU & 
                                             (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0xeU & 
                                             (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0xeU & 
                                             (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0xeU & 
                                             (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0xeU & 
                                             (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0xeU & 
                                             (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys3__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys3__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys3__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys3__DOT__dut__DOT__fit_base = 0xeU;
            tb_sys3__DOT__dut__DOT__best_sz = tb_sys3__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (0xfU & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))) 
                          - (IData)(1U)))) & (0x20U 
                                              >= ((IData)(0xfU) 
                                                  + 
                                                  (0x3fU 
                                                   & ((IData)(1U) 
                                                      << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys3__DOT__dut__DOT__slice_busy, 0xfU) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys3__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)));
        tb_sys3__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0xfU & 
                                             (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0xfU & 
                                             (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0xfU & 
                                             (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0xfU & 
                                             (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0xfU & 
                                             (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0xfU & 
                                             (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys3__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys3__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys3__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys3__DOT__dut__DOT__fit_base = 0xfU;
            tb_sys3__DOT__dut__DOT__best_sz = tb_sys3__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (0x10U & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))) 
                           - (IData)(1U)))) & (0x20U 
                                               >= ((IData)(0x10U) 
                                                   + 
                                                   (0x3fU 
                                                    & ((IData)(1U) 
                                                       << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys3__DOT__dut__DOT__slice_busy, 0x10U) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys3__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)));
        tb_sys3__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x10U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x10U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x10U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x10U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x10U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x10U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys3__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys3__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys3__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys3__DOT__dut__DOT__fit_base = 0x10U;
            tb_sys3__DOT__dut__DOT__best_sz = tb_sys3__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (0x11U & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))) 
                           - (IData)(1U)))) & (0x20U 
                                               >= ((IData)(0x11U) 
                                                   + 
                                                   (0x3fU 
                                                    & ((IData)(1U) 
                                                       << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys3__DOT__dut__DOT__slice_busy, 0x11U) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys3__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)));
        tb_sys3__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x11U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x11U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x11U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x11U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x11U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x11U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys3__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys3__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys3__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys3__DOT__dut__DOT__fit_base = 0x11U;
            tb_sys3__DOT__dut__DOT__best_sz = tb_sys3__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (0x12U & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))) 
                           - (IData)(1U)))) & (0x20U 
                                               >= ((IData)(0x12U) 
                                                   + 
                                                   (0x3fU 
                                                    & ((IData)(1U) 
                                                       << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys3__DOT__dut__DOT__slice_busy, 0x12U) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys3__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)));
        tb_sys3__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x12U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x12U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x12U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x12U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x12U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x12U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys3__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys3__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys3__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys3__DOT__dut__DOT__fit_base = 0x12U;
            tb_sys3__DOT__dut__DOT__best_sz = tb_sys3__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (0x13U & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))) 
                           - (IData)(1U)))) & (0x20U 
                                               >= ((IData)(0x13U) 
                                                   + 
                                                   (0x3fU 
                                                    & ((IData)(1U) 
                                                       << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys3__DOT__dut__DOT__slice_busy, 0x13U) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys3__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)));
        tb_sys3__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x13U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x13U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x13U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x13U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x13U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x13U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys3__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys3__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys3__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys3__DOT__dut__DOT__fit_base = 0x13U;
            tb_sys3__DOT__dut__DOT__best_sz = tb_sys3__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (0x14U & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))) 
                           - (IData)(1U)))) & (0x20U 
                                               >= ((IData)(0x14U) 
                                                   + 
                                                   (0x3fU 
                                                    & ((IData)(1U) 
                                                       << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys3__DOT__dut__DOT__slice_busy, 0x14U) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys3__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)));
        tb_sys3__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x14U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x14U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x14U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x14U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x14U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x14U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys3__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys3__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys3__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys3__DOT__dut__DOT__fit_base = 0x14U;
            tb_sys3__DOT__dut__DOT__best_sz = tb_sys3__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (0x15U & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))) 
                           - (IData)(1U)))) & (0x20U 
                                               >= ((IData)(0x15U) 
                                                   + 
                                                   (0x3fU 
                                                    & ((IData)(1U) 
                                                       << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys3__DOT__dut__DOT__slice_busy, 0x15U) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys3__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)));
        tb_sys3__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x15U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x15U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x15U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x15U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x15U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x15U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys3__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys3__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys3__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys3__DOT__dut__DOT__fit_base = 0x15U;
            tb_sys3__DOT__dut__DOT__best_sz = tb_sys3__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (0x16U & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))) 
                           - (IData)(1U)))) & (0x20U 
                                               >= ((IData)(0x16U) 
                                                   + 
                                                   (0x3fU 
                                                    & ((IData)(1U) 
                                                       << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys3__DOT__dut__DOT__slice_busy, 0x16U) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys3__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)));
        tb_sys3__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x16U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x16U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x16U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x16U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x16U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x16U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys3__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys3__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys3__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys3__DOT__dut__DOT__fit_base = 0x16U;
            tb_sys3__DOT__dut__DOT__best_sz = tb_sys3__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (0x17U & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))) 
                           - (IData)(1U)))) & (0x20U 
                                               >= ((IData)(0x17U) 
                                                   + 
                                                   (0x3fU 
                                                    & ((IData)(1U) 
                                                       << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys3__DOT__dut__DOT__slice_busy, 0x17U) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys3__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)));
        tb_sys3__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x17U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x17U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x17U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x17U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x17U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x17U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys3__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys3__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys3__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys3__DOT__dut__DOT__fit_base = 0x17U;
            tb_sys3__DOT__dut__DOT__best_sz = tb_sys3__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (0x18U & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))) 
                           - (IData)(1U)))) & (0x20U 
                                               >= ((IData)(0x18U) 
                                                   + 
                                                   (0x3fU 
                                                    & ((IData)(1U) 
                                                       << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys3__DOT__dut__DOT__slice_busy, 0x18U) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys3__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)));
        tb_sys3__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x18U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x18U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x18U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x18U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x18U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x18U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys3__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys3__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys3__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys3__DOT__dut__DOT__fit_base = 0x18U;
            tb_sys3__DOT__dut__DOT__best_sz = tb_sys3__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (0x19U & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))) 
                           - (IData)(1U)))) & (0x20U 
                                               >= ((IData)(0x19U) 
                                                   + 
                                                   (0x3fU 
                                                    & ((IData)(1U) 
                                                       << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys3__DOT__dut__DOT__slice_busy, 0x19U) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys3__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)));
        tb_sys3__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x19U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x19U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x19U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x19U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x19U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x19U 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys3__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys3__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys3__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys3__DOT__dut__DOT__fit_base = 0x19U;
            tb_sys3__DOT__dut__DOT__best_sz = tb_sys3__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (0x1aU & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))) 
                           - (IData)(1U)))) & (0x20U 
                                               >= ((IData)(0x1aU) 
                                                   + 
                                                   (0x3fU 
                                                    & ((IData)(1U) 
                                                       << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys3__DOT__dut__DOT__slice_busy, 0x1aU) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys3__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)));
        tb_sys3__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x1aU 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x1aU 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x1aU 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x1aU 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x1aU 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x1aU 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys3__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys3__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys3__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys3__DOT__dut__DOT__fit_base = 0x1aU;
            tb_sys3__DOT__dut__DOT__best_sz = tb_sys3__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (0x1bU & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))) 
                           - (IData)(1U)))) & (0x20U 
                                               >= ((IData)(0x1bU) 
                                                   + 
                                                   (0x3fU 
                                                    & ((IData)(1U) 
                                                       << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys3__DOT__dut__DOT__slice_busy, 0x1bU) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys3__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)));
        tb_sys3__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x1bU 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x1bU 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x1bU 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x1bU 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x1bU 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x1bU 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys3__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys3__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys3__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys3__DOT__dut__DOT__fit_base = 0x1bU;
            tb_sys3__DOT__dut__DOT__best_sz = tb_sys3__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (0x1cU & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))) 
                           - (IData)(1U)))) & (0x20U 
                                               >= ((IData)(0x1cU) 
                                                   + 
                                                   (0x3fU 
                                                    & ((IData)(1U) 
                                                       << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys3__DOT__dut__DOT__slice_busy, 0x1cU) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys3__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)));
        tb_sys3__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x1cU 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x1cU 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x1cU 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x1cU 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x1cU 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x1cU 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys3__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys3__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys3__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys3__DOT__dut__DOT__fit_base = 0x1cU;
            tb_sys3__DOT__dut__DOT__best_sz = tb_sys3__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (0x1dU & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))) 
                           - (IData)(1U)))) & (0x20U 
                                               >= ((IData)(0x1dU) 
                                                   + 
                                                   (0x3fU 
                                                    & ((IData)(1U) 
                                                       << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys3__DOT__dut__DOT__slice_busy, 0x1dU) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys3__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)));
        tb_sys3__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x1dU 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x1dU 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x1dU 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x1dU 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x1dU 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x1dU 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys3__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys3__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys3__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys3__DOT__dut__DOT__fit_base = 0x1dU;
            tb_sys3__DOT__dut__DOT__best_sz = tb_sys3__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (0x1eU & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))) 
                           - (IData)(1U)))) & (0x20U 
                                               >= ((IData)(0x1eU) 
                                                   + 
                                                   (0x3fU 
                                                    & ((IData)(1U) 
                                                       << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys3__DOT__dut__DOT__slice_busy, 0x1eU) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys3__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)));
        tb_sys3__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x1eU 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x1eU 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x1eU 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x1eU 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x1eU 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x1eU 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys3__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys3__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys3__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys3__DOT__dut__DOT__fit_base = 0x1eU;
            tb_sys3__DOT__dut__DOT__best_sz = tb_sys3__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (0x1fU & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))) 
                           - (IData)(1U)))) & (0x20U 
                                               >= ((IData)(0x1fU) 
                                                   + 
                                                   (0x3fU 
                                                    & ((IData)(1U) 
                                                       << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys3__DOT__dut__DOT__slice_busy, 0x1fU) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys3__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw)));
        tb_sys3__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x1fU 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x1fU 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x1fU 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x1fU 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x1fU 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        tb_sys3__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys3__DOT__dut__DOT__cur_lw))))) {
            tb_sys3__DOT__dut__DOT__bbase = (0x1fU 
                                             & (~ ((IData)(tb_sys3__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys3__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys3__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys3__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys3__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys3__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys3__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys3__DOT__dut__DOT__bsz = tb_sys3__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys3__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys3__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys3__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys3__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys3__DOT__dut__DOT__fit_base = 0x1fU;
            tb_sys3__DOT__dut__DOT__best_sz = tb_sys3__DOT__dut__DOT__bsz;
        }
    }
    vlSelf->tb_sys3__DOT__dut__DOT__pend_b = 0U;
    if ((vlSelf->tb_sys3__DOT__dut__DOT__kwr[0U] != 
         vlSelf->tb_sys3__DOT__dut__DOT__krd[0U])) {
        vlSelf->tb_sys3__DOT__dut__DOT__pend_b = 1U;
    }
    if ((vlSelf->tb_sys3__DOT__dut__DOT__kwr[1U] != 
         vlSelf->tb_sys3__DOT__dut__DOT__krd[1U])) {
        vlSelf->tb_sys3__DOT__dut__DOT__pend_b = 1U;
    }
    if ((vlSelf->tb_sys3__DOT__dut__DOT__kwr[2U] != 
         vlSelf->tb_sys3__DOT__dut__DOT__krd[2U])) {
        vlSelf->tb_sys3__DOT__dut__DOT__pend_b = 1U;
    }
    if ((vlSelf->tb_sys3__DOT__dut__DOT__kwr[3U] != 
         vlSelf->tb_sys3__DOT__dut__DOT__krd[3U])) {
        vlSelf->tb_sys3__DOT__dut__DOT__pend_b = 1U;
    }
    if ((vlSelf->tb_sys3__DOT__dut__DOT__kwr[4U] != 
         vlSelf->tb_sys3__DOT__dut__DOT__krd[4U])) {
        vlSelf->tb_sys3__DOT__dut__DOT__pend_b = 1U;
    }
    if ((vlSelf->tb_sys3__DOT__dut__DOT__kwr[5U] != 
         vlSelf->tb_sys3__DOT__dut__DOT__krd[5U])) {
        vlSelf->tb_sys3__DOT__dut__DOT__pend_b = 1U;
    }
    if ((vlSelf->tb_sys3__DOT__dut__DOT__kwr[6U] != 
         vlSelf->tb_sys3__DOT__dut__DOT__krd[6U])) {
        vlSelf->tb_sys3__DOT__dut__DOT__pend_b = 1U;
    }
    vlSelf->tb_sys3__DOT__dut__DOT__hb = 0U;
    if ((vlSelf->tb_sys3__DOT__dut__DOT__kwr[0U] != 
         vlSelf->tb_sys3__DOT__dut__DOT__krd[0U])) {
        vlSelf->tb_sys3__DOT__dut__DOT__hb = 0U;
    }
    if ((vlSelf->tb_sys3__DOT__dut__DOT__kwr[1U] != 
         vlSelf->tb_sys3__DOT__dut__DOT__krd[1U])) {
        vlSelf->tb_sys3__DOT__dut__DOT__hb = 1U;
    }
    if ((vlSelf->tb_sys3__DOT__dut__DOT__kwr[2U] != 
         vlSelf->tb_sys3__DOT__dut__DOT__krd[2U])) {
        vlSelf->tb_sys3__DOT__dut__DOT__hb = 2U;
    }
    if ((vlSelf->tb_sys3__DOT__dut__DOT__kwr[3U] != 
         vlSelf->tb_sys3__DOT__dut__DOT__krd[3U])) {
        vlSelf->tb_sys3__DOT__dut__DOT__hb = 3U;
    }
    if ((vlSelf->tb_sys3__DOT__dut__DOT__kwr[4U] != 
         vlSelf->tb_sys3__DOT__dut__DOT__krd[4U])) {
        vlSelf->tb_sys3__DOT__dut__DOT__hb = 4U;
    }
    if ((vlSelf->tb_sys3__DOT__dut__DOT__kwr[5U] != 
         vlSelf->tb_sys3__DOT__dut__DOT__krd[5U])) {
        vlSelf->tb_sys3__DOT__dut__DOT__hb = 5U;
    }
    if ((vlSelf->tb_sys3__DOT__dut__DOT__kwr[6U] != 
         vlSelf->tb_sys3__DOT__dut__DOT__krd[6U])) {
        vlSelf->tb_sys3__DOT__dut__DOT__hb = 6U;
    }
    if ((vlSelf->tb_sys3__DOT__dut__DOT__kwr[7U] != 
         vlSelf->tb_sys3__DOT__dut__DOT__krd[7U])) {
        vlSelf->tb_sys3__DOT__dut__DOT__pend_b = 1U;
        vlSelf->tb_sys3__DOT__dut__DOT__hb = 7U;
    }
    if ((1U & (~ (IData)(vlSelf->tb_sys3__DOT__rst)))) {
        vlSelf->tb_sys3__DOT__h_push = 0U;
        if ((VL_LTS_III(32, vlSelf->tb_sys3__DOT__nxt, vlSelf->tb_sys3__DOT__NT) 
             & (((0x2ffU >= (0x3ffU & VL_MULS_III(32, (IData)(3U), vlSelf->tb_sys3__DOT__nxt)))
                  ? vlSelf->tb_sys3__DOT__tl[(0x3ffU 
                                              & VL_MULS_III(32, (IData)(3U), vlSelf->tb_sys3__DOT__nxt))]
                  : 0U) <= vlSelf->tb_sys3__DOT__dut__DOT__cyc))) {
            vlSelf->tb_sys3__DOT__h_push = 1U;
            vlSelf->tb_sys3__DOT__h_tid = (0xffffU 
                                           & vlSelf->tb_sys3__DOT__nxt);
            vlSelf->tb_sys3__DOT__h_code = ((0x2ffU 
                                             >= (0x3ffU 
                                                 & ((IData)(1U) 
                                                    + 
                                                    VL_MULS_III(32, (IData)(3U), vlSelf->tb_sys3__DOT__nxt))))
                                             ? (0xffffU 
                                                & vlSelf->tb_sys3__DOT__tl
                                                [(0x3ffU 
                                                  & ((IData)(1U) 
                                                     + 
                                                     VL_MULS_III(32, (IData)(3U), vlSelf->tb_sys3__DOT__nxt)))])
                                             : 0U);
            vlSelf->tb_sys3__DOT__h_lw = ((0x2ffU >= 
                                           (0x3ffU 
                                            & ((IData)(2U) 
                                               + VL_MULS_III(32, (IData)(3U), vlSelf->tb_sys3__DOT__nxt))))
                                           ? (7U & 
                                              vlSelf->tb_sys3__DOT__tl
                                              [(0x3ffU 
                                                & ((IData)(2U) 
                                                   + 
                                                   VL_MULS_III(32, (IData)(3U), vlSelf->tb_sys3__DOT__nxt)))])
                                           : 0U);
            vlSelf->tb_sys3__DOT__h_crit = (1U & ((
                                                   (0x2ffU 
                                                    >= 
                                                    (0x3ffU 
                                                     & ((IData)(2U) 
                                                        + 
                                                        VL_MULS_III(32, (IData)(3U), vlSelf->tb_sys3__DOT__nxt))))
                                                    ? 
                                                   vlSelf->tb_sys3__DOT__tl
                                                   [
                                                   (0x3ffU 
                                                    & ((IData)(2U) 
                                                       + 
                                                       VL_MULS_III(32, (IData)(3U), vlSelf->tb_sys3__DOT__nxt)))]
                                                    : 0U) 
                                                  >> 8U));
            vlSelf->tb_sys3__DOT__h_prog = (0x3fU & 
                                            (((0x2ffU 
                                               >= (0x3ffU 
                                                   & ((IData)(2U) 
                                                      + 
                                                      VL_MULS_III(32, (IData)(3U), vlSelf->tb_sys3__DOT__nxt))))
                                               ? vlSelf->tb_sys3__DOT__tl
                                              [(0x3ffU 
                                                & ((IData)(2U) 
                                                   + 
                                                   VL_MULS_III(32, (IData)(3U), vlSelf->tb_sys3__DOT__nxt)))]
                                               : 0U) 
                                             >> 9U));
            vlSelf->tb_sys3__DOT__nxt = ((IData)(1U) 
                                         + vlSelf->tb_sys3__DOT__nxt);
        }
        vlSelf->tb_sys3__DOT__ev_pl_we = 0U;
        vlSelf->tb_sys3__DOT__ev_set = 0U;
        if ((VL_LTS_III(32, vlSelf->tb_sys3__DOT__en, vlSelf->tb_sys3__DOT__NE) 
             & (vlSelf->tb_sys3__DOT__dut__DOT__cyc 
                >= vlSelf->tb_sys3__DOT__evt_time[(0xffU 
                                                   & vlSelf->tb_sys3__DOT__en)]))) {
            vlSelf->tb_sys3__DOT__ev_pl_we = 1U;
            vlSelf->tb_sys3__DOT__ev_pl_id = vlSelf->tb_sys3__DOT__evt_line
                [(0xffU & vlSelf->tb_sys3__DOT__en)];
            vlSelf->__Vdly__tb_sys3__DOT__epend = 1U;
            vlSelf->tb_sys3__DOT__ev_pl_data = vlSelf->tb_sys3__DOT__evt_data
                [(0xffU & vlSelf->tb_sys3__DOT__en)];
            vlSelf->__Vdly__tb_sys3__DOT__epend_id 
                = vlSelf->tb_sys3__DOT__evt_line[(0xffU 
                                                  & vlSelf->tb_sys3__DOT__en)];
            vlSelf->__Vdly__tb_sys3__DOT__ecur = vlSelf->tb_sys3__DOT__en;
            vlSelf->tb_sys3__DOT__en = ((IData)(1U) 
                                        + vlSelf->tb_sys3__DOT__en);
        } else if (vlSelf->tb_sys3__DOT__epend) {
            vlSelf->tb_sys3__DOT__ev_set = 1U;
            vlSelf->tb_sys3__DOT__ev_set_id = vlSelf->tb_sys3__DOT__epend_id;
            vlSelf->__Vdlyvval__tb_sys3__DOT__evt_setcyc__v0 
                = vlSelf->tb_sys3__DOT__dut__DOT__cyc;
            vlSelf->__Vdlyvset__tb_sys3__DOT__evt_setcyc__v0 = 1U;
            vlSelf->__Vdlyvdim0__tb_sys3__DOT__evt_setcyc__v0 
                = (0xffU & vlSelf->tb_sys3__DOT__ecur);
            vlSelf->__Vdly__tb_sys3__DOT__epend = 0U;
        }
    }
    if (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__halted_r) {
        vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits 
            = (0x3fU & ((IData)(1U) << (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r)));
        vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc = 0U;
        if (VL_LTS_III(32, 0U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                   | (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__rf
                      [0x140U] & ((5U == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r))
                                   ? 0xffffffffU : 
                                  (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits)) 
                                   - (IData)(1U)))));
        }
        if (VL_LTS_III(32, 1U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__rf
                                              [0x141U] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits)));
        }
        if (VL_LTS_III(32, 2U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__rf
                                              [0x142U] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   VL_SHIFTL_III(32,32,32, (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits), 1U)));
        }
        if (VL_LTS_III(32, 3U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__rf
                                              [0x143U] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(3U) * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 4U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__rf
                                              [0x144U] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   VL_SHIFTL_III(32,32,32, (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits), 2U)));
        }
        if (VL_LTS_III(32, 5U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__rf
                                              [0x145U] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(5U) * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 6U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__rf
                                              [0x146U] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(6U) * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 7U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__rf
                                              [0x147U] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(7U) * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 8U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__rf
                                              [0x148U] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   VL_SHIFTL_III(32,32,32, (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits), 3U)));
        }
        if (VL_LTS_III(32, 9U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__rf
                                              [0x149U] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(9U) * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0xaU, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__rf
                                              [0x14aU] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0xaU) * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0xbU, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__rf
                                              [0x14bU] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0xbU) * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0xcU, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__rf
                                              [0x14cU] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0xcU) * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0xdU, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__rf
                                              [0x14dU] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0xdU) * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0xeU, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__rf
                                              [0x14eU] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0xeU) * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0xfU, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__rf
                                              [0x14fU] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0xfU) * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0x10U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__rf
                                              [0x150U] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   VL_SHIFTL_III(32,32,32, (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits), 4U)));
        }
        if (VL_LTS_III(32, 0x11U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__rf
                                              [0x151U] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0x11U) 
                                    * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0x12U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__rf
                                              [0x152U] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0x12U) 
                                    * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0x13U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__rf
                                              [0x153U] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0x13U) 
                                    * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0x14U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__rf
                                              [0x154U] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0x14U) 
                                    * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0x15U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__rf
                                              [0x155U] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0x15U) 
                                    * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0x16U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__rf
                                              [0x156U] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0x16U) 
                                    * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0x17U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__rf
                                              [0x157U] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0x17U) 
                                    * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0x18U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__rf
                                              [0x158U] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0x18U) 
                                    * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0x19U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__rf
                                              [0x159U] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0x19U) 
                                    * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0x1aU, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__rf
                                              [0x15aU] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0x1aU) 
                                    * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0x1bU, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__rf
                                              [0x15bU] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0x1bU) 
                                    * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0x1cU, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__rf
                                              [0x15cU] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0x1cU) 
                                    * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0x1dU, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__rf
                                              [0x15dU] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0x1dU) 
                                    * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0x1eU, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__rf
                                              [0x15eU] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0x1eU) 
                                    * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0x1fU, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__rf
                                              [0x15fU] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0x1fU) 
                                    * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__wbits))));
        }
        vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__a0s 
            = vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__acc;
    }
    if (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__halted_r) {
        vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits 
            = (0x3fU & ((IData)(1U) << (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r)));
        vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc = 0U;
        if (VL_LTS_III(32, 0U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                   | (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__rf
                      [0x140U] & ((5U == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r))
                                   ? 0xffffffffU : 
                                  (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits)) 
                                   - (IData)(1U)))));
        }
        if (VL_LTS_III(32, 1U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__rf
                                              [0x141U] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits)));
        }
        if (VL_LTS_III(32, 2U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__rf
                                              [0x142U] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   VL_SHIFTL_III(32,32,32, (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits), 1U)));
        }
        if (VL_LTS_III(32, 3U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__rf
                                              [0x143U] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(3U) * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 4U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__rf
                                              [0x144U] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   VL_SHIFTL_III(32,32,32, (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits), 2U)));
        }
        if (VL_LTS_III(32, 5U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__rf
                                              [0x145U] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(5U) * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 6U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__rf
                                              [0x146U] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(6U) * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 7U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__rf
                                              [0x147U] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(7U) * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 8U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__rf
                                              [0x148U] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   VL_SHIFTL_III(32,32,32, (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits), 3U)));
        }
        if (VL_LTS_III(32, 9U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__rf
                                              [0x149U] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(9U) * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0xaU, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__rf
                                              [0x14aU] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0xaU) * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0xbU, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__rf
                                              [0x14bU] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0xbU) * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0xcU, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__rf
                                              [0x14cU] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0xcU) * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0xdU, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__rf
                                              [0x14dU] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0xdU) * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0xeU, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__rf
                                              [0x14eU] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0xeU) * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0xfU, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__rf
                                              [0x14fU] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0xfU) * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0x10U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__rf
                                              [0x150U] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   VL_SHIFTL_III(32,32,32, (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits), 4U)));
        }
        if (VL_LTS_III(32, 0x11U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__rf
                                              [0x151U] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0x11U) 
                                    * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0x12U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__rf
                                              [0x152U] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0x12U) 
                                    * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0x13U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__rf
                                              [0x153U] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0x13U) 
                                    * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0x14U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__rf
                                              [0x154U] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0x14U) 
                                    * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0x15U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__rf
                                              [0x155U] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0x15U) 
                                    * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0x16U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__rf
                                              [0x156U] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0x16U) 
                                    * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0x17U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__rf
                                              [0x157U] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0x17U) 
                                    * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0x18U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__rf
                                              [0x158U] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0x18U) 
                                    * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0x19U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__rf
                                              [0x159U] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0x19U) 
                                    * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0x1aU, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__rf
                                              [0x15aU] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0x1aU) 
                                    * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0x1bU, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__rf
                                              [0x15bU] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0x1bU) 
                                    * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0x1cU, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__rf
                                              [0x15cU] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0x1cU) 
                                    * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0x1dU, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__rf
                                              [0x15dU] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0x1dU) 
                                    * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0x1eU, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__rf
                                              [0x15eU] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0x1eU) 
                                    * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0x1fU, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__rf
                                              [0x15fU] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0x1fU) 
                                    * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__wbits))));
        }
        vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__a0s 
            = vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__acc;
    }
    if (vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__halted_r) {
        vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits 
            = (0x3fU & ((IData)(1U) << (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r)));
        vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc = 0U;
        if (VL_LTS_III(32, 0U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                   | (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__rf
                      [0x140U] & ((5U == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r))
                                   ? 0xffffffffU : 
                                  (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits)) 
                                   - (IData)(1U)))));
        }
        if (VL_LTS_III(32, 1U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__rf
                                              [0x141U] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits)));
        }
        if (VL_LTS_III(32, 2U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__rf
                                              [0x142U] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   VL_SHIFTL_III(32,32,32, (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits), 1U)));
        }
        if (VL_LTS_III(32, 3U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__rf
                                              [0x143U] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(3U) * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 4U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__rf
                                              [0x144U] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   VL_SHIFTL_III(32,32,32, (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits), 2U)));
        }
        if (VL_LTS_III(32, 5U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__rf
                                              [0x145U] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(5U) * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 6U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__rf
                                              [0x146U] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(6U) * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 7U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__rf
                                              [0x147U] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(7U) * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 8U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__rf
                                              [0x148U] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   VL_SHIFTL_III(32,32,32, (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits), 3U)));
        }
        if (VL_LTS_III(32, 9U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__rf
                                              [0x149U] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(9U) * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0xaU, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__rf
                                              [0x14aU] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0xaU) * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0xbU, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__rf
                                              [0x14bU] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0xbU) * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0xcU, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__rf
                                              [0x14cU] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0xcU) * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0xdU, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__rf
                                              [0x14dU] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0xdU) * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0xeU, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__rf
                                              [0x14eU] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0xeU) * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0xfU, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__rf
                                              [0x14fU] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0xfU) * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0x10U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__rf
                                              [0x150U] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   VL_SHIFTL_III(32,32,32, (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits), 4U)));
        }
        if (VL_LTS_III(32, 0x11U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__rf
                                              [0x151U] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0x11U) 
                                    * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0x12U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__rf
                                              [0x152U] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0x12U) 
                                    * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0x13U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__rf
                                              [0x153U] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0x13U) 
                                    * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0x14U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__rf
                                              [0x154U] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0x14U) 
                                    * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0x15U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__rf
                                              [0x155U] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0x15U) 
                                    * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0x16U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__rf
                                              [0x156U] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0x16U) 
                                    * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0x17U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__rf
                                              [0x157U] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0x17U) 
                                    * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0x18U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__rf
                                              [0x158U] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0x18U) 
                                    * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0x19U, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__rf
                                              [0x159U] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0x19U) 
                                    * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0x1aU, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__rf
                                              [0x15aU] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0x1aU) 
                                    * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0x1bU, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__rf
                                              [0x15bU] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0x1bU) 
                                    * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0x1cU, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__rf
                                              [0x15cU] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0x1cU) 
                                    * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0x1dU, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__rf
                                              [0x15dU] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0x1dU) 
                                    * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0x1eU, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__rf
                                              [0x15eU] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0x1eU) 
                                    * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits))));
        }
        if (VL_LTS_III(32, 0x1fU, (0x20U >> (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r)))) {
            vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                = (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc 
                   | VL_SHIFTL_III(32,32,32, (vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__rf
                                              [0x15fU] 
                                              & ((5U 
                                                  == (IData)(vlSymsp->TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__lw_r))
                                                  ? 0xffffffffU
                                                  : 
                                                 (VL_SHIFTL_III(32,32,6, (IData)(1U), (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits)) 
                                                  - (IData)(1U)))), 
                                   ((IData)(0x1fU) 
                                    * (IData)(vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__wbits))));
        }
        vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__a0s 
            = vlSelf->tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__acc;
    }
}
