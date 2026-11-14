// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design implementation internals
// See Vtb_sys5.h for the primary calling header

#include "Vtb_sys5__pch.h"
#include "Vtb_sys5__Syms.h"
#include "Vtb_sys5___024root.h"

#ifdef VL_DEBUG
VL_ATTR_COLD void Vtb_sys5___024root___dump_triggers__stl(Vtb_sys5___024root* vlSelf);
#endif  // VL_DEBUG

VL_ATTR_COLD void Vtb_sys5___024root___eval_triggers__stl(Vtb_sys5___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_sys5__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtb_sys5___024root___eval_triggers__stl\n"); );
    // Body
    vlSelf->__VstlTriggered.set(0U, (IData)(vlSelf->__VstlFirstIteration));
#ifdef VL_DEBUG
    if (VL_UNLIKELY(vlSymsp->_vm_contextp__->debug())) {
        Vtb_sys5___024root___dump_triggers__stl(vlSelf);
    }
#endif
}

VL_ATTR_COLD void Vtb_sys5___024root___stl_sequent__TOP__0(Vtb_sys5___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_sys5__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtb_sys5___024root___stl_sequent__TOP__0\n"); );
    // Init
    CData/*6:0*/ tb_sys5__DOT__dut__DOT__best_sz;
    tb_sys5__DOT__dut__DOT__best_sz = 0;
    CData/*6:0*/ tb_sys5__DOT__dut__DOT__bsz;
    tb_sys5__DOT__dut__DOT__bsz = 0;
    CData/*6:0*/ tb_sys5__DOT__dut__DOT__blk;
    tb_sys5__DOT__dut__DOT__blk = 0;
    CData/*5:0*/ tb_sys5__DOT__dut__DOT__bbase;
    tb_sys5__DOT__dut__DOT__bbase = 0;
    CData/*0:0*/ tb_sys5__DOT__dut__DOT__pe16__Vstatic__b3;
    tb_sys5__DOT__dut__DOT__pe16__Vstatic__b3 = 0;
    CData/*0:0*/ tb_sys5__DOT__dut__DOT__pe16__Vstatic__b2;
    tb_sys5__DOT__dut__DOT__pe16__Vstatic__b2 = 0;
    CData/*0:0*/ tb_sys5__DOT__dut__DOT__pe16__Vstatic__b1;
    tb_sys5__DOT__dut__DOT__pe16__Vstatic__b1 = 0;
    CData/*7:0*/ tb_sys5__DOT__dut__DOT__pe16__Vstatic__x8;
    tb_sys5__DOT__dut__DOT__pe16__Vstatic__x8 = 0;
    CData/*3:0*/ tb_sys5__DOT__dut__DOT__pe16__Vstatic__x4;
    tb_sys5__DOT__dut__DOT__pe16__Vstatic__x4 = 0;
    CData/*1:0*/ tb_sys5__DOT__dut__DOT__pe16__Vstatic__x2;
    tb_sys5__DOT__dut__DOT__pe16__Vstatic__x2 = 0;
    CData/*3:0*/ tb_sys5__DOT__dut__DOT__w_row;
    tb_sys5__DOT__dut__DOT__w_row = 0;
    CData/*3:0*/ __Vfunc_tb_sys5__DOT__dut__DOT__pe16__1__Vfuncout;
    __Vfunc_tb_sys5__DOT__dut__DOT__pe16__1__Vfuncout = 0;
    SData/*15:0*/ __Vfunc_tb_sys5__DOT__dut__DOT__pe16__1__x;
    __Vfunc_tb_sys5__DOT__dut__DOT__pe16__1__x = 0;
    // Body
    vlSelf->tb_sys5__DOT__dut__DOT__cur_w = (0x3fU 
                                             & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)));
    vlSelf->tb_sys5__DOT__dut__DOT__pend_b = 0U;
    if ((vlSelf->tb_sys5__DOT__dut__DOT__kwr[0U] != 
         vlSelf->tb_sys5__DOT__dut__DOT__krd[0U])) {
        vlSelf->tb_sys5__DOT__dut__DOT__pend_b = 1U;
    }
    if ((vlSelf->tb_sys5__DOT__dut__DOT__kwr[1U] != 
         vlSelf->tb_sys5__DOT__dut__DOT__krd[1U])) {
        vlSelf->tb_sys5__DOT__dut__DOT__pend_b = 1U;
    }
    if ((vlSelf->tb_sys5__DOT__dut__DOT__kwr[2U] != 
         vlSelf->tb_sys5__DOT__dut__DOT__krd[2U])) {
        vlSelf->tb_sys5__DOT__dut__DOT__pend_b = 1U;
    }
    if ((vlSelf->tb_sys5__DOT__dut__DOT__kwr[3U] != 
         vlSelf->tb_sys5__DOT__dut__DOT__krd[3U])) {
        vlSelf->tb_sys5__DOT__dut__DOT__pend_b = 1U;
    }
    if ((vlSelf->tb_sys5__DOT__dut__DOT__kwr[4U] != 
         vlSelf->tb_sys5__DOT__dut__DOT__krd[4U])) {
        vlSelf->tb_sys5__DOT__dut__DOT__pend_b = 1U;
    }
    if ((vlSelf->tb_sys5__DOT__dut__DOT__kwr[5U] != 
         vlSelf->tb_sys5__DOT__dut__DOT__krd[5U])) {
        vlSelf->tb_sys5__DOT__dut__DOT__pend_b = 1U;
    }
    if ((vlSelf->tb_sys5__DOT__dut__DOT__kwr[6U] != 
         vlSelf->tb_sys5__DOT__dut__DOT__krd[6U])) {
        vlSelf->tb_sys5__DOT__dut__DOT__pend_b = 1U;
    }
    vlSelf->tb_sys5__DOT__dut__DOT__pend_c = (vlSelf->tb_sys5__DOT__dut__DOT__qc_wr 
                                              != vlSelf->tb_sys5__DOT__dut__DOT__qc_rd);
    vlSelf->tb_sys5__DOT__dut__DOT__hb = 0U;
    if ((vlSelf->tb_sys5__DOT__dut__DOT__kwr[0U] != 
         vlSelf->tb_sys5__DOT__dut__DOT__krd[0U])) {
        vlSelf->tb_sys5__DOT__dut__DOT__hb = 0U;
    }
    if ((vlSelf->tb_sys5__DOT__dut__DOT__kwr[1U] != 
         vlSelf->tb_sys5__DOT__dut__DOT__krd[1U])) {
        vlSelf->tb_sys5__DOT__dut__DOT__hb = 1U;
    }
    if ((vlSelf->tb_sys5__DOT__dut__DOT__kwr[2U] != 
         vlSelf->tb_sys5__DOT__dut__DOT__krd[2U])) {
        vlSelf->tb_sys5__DOT__dut__DOT__hb = 2U;
    }
    if ((vlSelf->tb_sys5__DOT__dut__DOT__kwr[3U] != 
         vlSelf->tb_sys5__DOT__dut__DOT__krd[3U])) {
        vlSelf->tb_sys5__DOT__dut__DOT__hb = 3U;
    }
    if ((vlSelf->tb_sys5__DOT__dut__DOT__kwr[4U] != 
         vlSelf->tb_sys5__DOT__dut__DOT__krd[4U])) {
        vlSelf->tb_sys5__DOT__dut__DOT__hb = 4U;
    }
    if ((vlSelf->tb_sys5__DOT__dut__DOT__kwr[5U] != 
         vlSelf->tb_sys5__DOT__dut__DOT__krd[5U])) {
        vlSelf->tb_sys5__DOT__dut__DOT__hb = 5U;
    }
    if ((vlSelf->tb_sys5__DOT__dut__DOT__kwr[6U] != 
         vlSelf->tb_sys5__DOT__dut__DOT__krd[6U])) {
        vlSelf->tb_sys5__DOT__dut__DOT__hb = 6U;
    }
    if ((vlSelf->tb_sys5__DOT__dut__DOT__kwr[7U] != 
         vlSelf->tb_sys5__DOT__dut__DOT__krd[7U])) {
        vlSelf->tb_sys5__DOT__dut__DOT__pend_b = 1U;
        vlSelf->tb_sys5__DOT__dut__DOT__hb = 7U;
    }
    vlSelf->tb_sys5__DOT__dut__DOT__fit_found = 0U;
    vlSelf->tb_sys5__DOT__dut__DOT__fit_base = 0U;
    tb_sys5__DOT__dut__DOT__best_sz = 0x7fU;
    tb_sys5__DOT__dut__DOT__bsz = 0U;
    tb_sys5__DOT__dut__DOT__blk = 0U;
    tb_sys5__DOT__dut__DOT__bbase = 0U;
    if (((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))) 
         & (0ULL == (vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys5__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)));
        tb_sys5__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = 0U;
            if (((0x20U >= (IData)(tb_sys5__DOT__dut__DOT__blk)) 
                 & (0ULL == (vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = 0U;
            if (((0x20U >= (IData)(tb_sys5__DOT__dut__DOT__blk)) 
                 & (0ULL == (vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = 0U;
            if (((0x20U >= (IData)(tb_sys5__DOT__dut__DOT__blk)) 
                 & (0ULL == (vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = 0U;
            if (((0x20U >= (IData)(tb_sys5__DOT__dut__DOT__blk)) 
                 & (0ULL == (vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = 0U;
            if (((0x20U >= (IData)(tb_sys5__DOT__dut__DOT__blk)) 
                 & (0ULL == (vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = 0U;
            if (((0x20U >= (IData)(tb_sys5__DOT__dut__DOT__blk)) 
                 & (0ULL == (vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys5__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys5__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys5__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys5__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys5__DOT__dut__DOT__fit_base = 0U;
            tb_sys5__DOT__dut__DOT__best_sz = tb_sys5__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (1U & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))) 
                        - (IData)(1U)))) & (0x20U >= 
                                            ((IData)(1U) 
                                             + (0x3fU 
                                                & ((IData)(1U) 
                                                   << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys5__DOT__dut__DOT__slice_busy, 1U) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys5__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)));
        tb_sys5__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (1U & (~ 
                                                   ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (1U & (~ 
                                                   ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (1U & (~ 
                                                   ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (1U & (~ 
                                                   ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (1U & (~ 
                                                   ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (1U & (~ 
                                                   ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys5__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys5__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys5__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys5__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys5__DOT__dut__DOT__fit_base = 1U;
            tb_sys5__DOT__dut__DOT__best_sz = tb_sys5__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (2U & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))) 
                        - (IData)(1U)))) & (0x20U >= 
                                            ((IData)(2U) 
                                             + (0x3fU 
                                                & ((IData)(1U) 
                                                   << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys5__DOT__dut__DOT__slice_busy, 2U) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys5__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)));
        tb_sys5__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (2U & (~ 
                                                   ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (2U & (~ 
                                                   ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (2U & (~ 
                                                   ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (2U & (~ 
                                                   ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (2U & (~ 
                                                   ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (2U & (~ 
                                                   ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys5__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys5__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys5__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys5__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys5__DOT__dut__DOT__fit_base = 2U;
            tb_sys5__DOT__dut__DOT__best_sz = tb_sys5__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (3U & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))) 
                        - (IData)(1U)))) & (0x20U >= 
                                            ((IData)(3U) 
                                             + (0x3fU 
                                                & ((IData)(1U) 
                                                   << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys5__DOT__dut__DOT__slice_busy, 3U) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys5__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)));
        tb_sys5__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (3U & (~ 
                                                   ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (3U & (~ 
                                                   ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (3U & (~ 
                                                   ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (3U & (~ 
                                                   ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (3U & (~ 
                                                   ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (3U & (~ 
                                                   ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys5__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys5__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys5__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys5__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys5__DOT__dut__DOT__fit_base = 3U;
            tb_sys5__DOT__dut__DOT__best_sz = tb_sys5__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (4U & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))) 
                        - (IData)(1U)))) & (0x20U >= 
                                            ((IData)(4U) 
                                             + (0x3fU 
                                                & ((IData)(1U) 
                                                   << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys5__DOT__dut__DOT__slice_busy, 4U) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys5__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)));
        tb_sys5__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (4U & (~ 
                                                   ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (4U & (~ 
                                                   ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (4U & (~ 
                                                   ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (4U & (~ 
                                                   ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (4U & (~ 
                                                   ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (4U & (~ 
                                                   ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys5__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys5__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys5__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys5__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys5__DOT__dut__DOT__fit_base = 4U;
            tb_sys5__DOT__dut__DOT__best_sz = tb_sys5__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (5U & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))) 
                        - (IData)(1U)))) & (0x20U >= 
                                            ((IData)(5U) 
                                             + (0x3fU 
                                                & ((IData)(1U) 
                                                   << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys5__DOT__dut__DOT__slice_busy, 5U) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys5__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)));
        tb_sys5__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (5U & (~ 
                                                   ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (5U & (~ 
                                                   ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (5U & (~ 
                                                   ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (5U & (~ 
                                                   ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (5U & (~ 
                                                   ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (5U & (~ 
                                                   ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys5__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys5__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys5__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys5__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys5__DOT__dut__DOT__fit_base = 5U;
            tb_sys5__DOT__dut__DOT__best_sz = tb_sys5__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (6U & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))) 
                        - (IData)(1U)))) & (0x20U >= 
                                            ((IData)(6U) 
                                             + (0x3fU 
                                                & ((IData)(1U) 
                                                   << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys5__DOT__dut__DOT__slice_busy, 6U) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys5__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)));
        tb_sys5__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (6U & (~ 
                                                   ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (6U & (~ 
                                                   ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (6U & (~ 
                                                   ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (6U & (~ 
                                                   ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (6U & (~ 
                                                   ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (6U & (~ 
                                                   ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys5__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys5__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys5__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys5__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys5__DOT__dut__DOT__fit_base = 6U;
            tb_sys5__DOT__dut__DOT__best_sz = tb_sys5__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (7U & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))) 
                        - (IData)(1U)))) & (0x20U >= 
                                            ((IData)(7U) 
                                             + (0x3fU 
                                                & ((IData)(1U) 
                                                   << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys5__DOT__dut__DOT__slice_busy, 7U) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys5__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)));
        tb_sys5__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (7U & (~ 
                                                   ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (7U & (~ 
                                                   ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (7U & (~ 
                                                   ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (7U & (~ 
                                                   ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (7U & (~ 
                                                   ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (7U & (~ 
                                                   ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys5__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys5__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys5__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys5__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys5__DOT__dut__DOT__fit_base = 7U;
            tb_sys5__DOT__dut__DOT__best_sz = tb_sys5__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (8U & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))) 
                        - (IData)(1U)))) & (0x20U >= 
                                            ((IData)(8U) 
                                             + (0x3fU 
                                                & ((IData)(1U) 
                                                   << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys5__DOT__dut__DOT__slice_busy, 8U) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys5__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)));
        tb_sys5__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (8U & (~ 
                                                   ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (8U & (~ 
                                                   ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (8U & (~ 
                                                   ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (8U & (~ 
                                                   ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (8U & (~ 
                                                   ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (8U & (~ 
                                                   ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys5__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys5__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys5__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys5__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys5__DOT__dut__DOT__fit_base = 8U;
            tb_sys5__DOT__dut__DOT__best_sz = tb_sys5__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (9U & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))) 
                        - (IData)(1U)))) & (0x20U >= 
                                            ((IData)(9U) 
                                             + (0x3fU 
                                                & ((IData)(1U) 
                                                   << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys5__DOT__dut__DOT__slice_busy, 9U) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys5__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)));
        tb_sys5__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (9U & (~ 
                                                   ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (9U & (~ 
                                                   ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (9U & (~ 
                                                   ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (9U & (~ 
                                                   ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (9U & (~ 
                                                   ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (9U & (~ 
                                                   ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                    - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys5__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys5__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys5__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys5__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys5__DOT__dut__DOT__fit_base = 9U;
            tb_sys5__DOT__dut__DOT__best_sz = tb_sys5__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (0xaU & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))) 
                          - (IData)(1U)))) & (0x20U 
                                              >= ((IData)(0xaU) 
                                                  + 
                                                  (0x3fU 
                                                   & ((IData)(1U) 
                                                      << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys5__DOT__dut__DOT__slice_busy, 0xaU) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys5__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)));
        tb_sys5__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0xaU & 
                                             (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0xaU & 
                                             (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0xaU & 
                                             (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0xaU & 
                                             (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0xaU & 
                                             (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0xaU & 
                                             (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys5__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys5__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys5__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys5__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys5__DOT__dut__DOT__fit_base = 0xaU;
            tb_sys5__DOT__dut__DOT__best_sz = tb_sys5__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (0xbU & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))) 
                          - (IData)(1U)))) & (0x20U 
                                              >= ((IData)(0xbU) 
                                                  + 
                                                  (0x3fU 
                                                   & ((IData)(1U) 
                                                      << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys5__DOT__dut__DOT__slice_busy, 0xbU) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys5__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)));
        tb_sys5__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0xbU & 
                                             (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0xbU & 
                                             (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0xbU & 
                                             (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0xbU & 
                                             (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0xbU & 
                                             (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0xbU & 
                                             (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys5__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys5__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys5__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys5__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys5__DOT__dut__DOT__fit_base = 0xbU;
            tb_sys5__DOT__dut__DOT__best_sz = tb_sys5__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (0xcU & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))) 
                          - (IData)(1U)))) & (0x20U 
                                              >= ((IData)(0xcU) 
                                                  + 
                                                  (0x3fU 
                                                   & ((IData)(1U) 
                                                      << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys5__DOT__dut__DOT__slice_busy, 0xcU) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys5__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)));
        tb_sys5__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0xcU & 
                                             (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0xcU & 
                                             (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0xcU & 
                                             (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0xcU & 
                                             (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0xcU & 
                                             (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0xcU & 
                                             (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys5__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys5__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys5__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys5__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys5__DOT__dut__DOT__fit_base = 0xcU;
            tb_sys5__DOT__dut__DOT__best_sz = tb_sys5__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (0xdU & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))) 
                          - (IData)(1U)))) & (0x20U 
                                              >= ((IData)(0xdU) 
                                                  + 
                                                  (0x3fU 
                                                   & ((IData)(1U) 
                                                      << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys5__DOT__dut__DOT__slice_busy, 0xdU) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys5__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)));
        tb_sys5__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0xdU & 
                                             (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0xdU & 
                                             (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0xdU & 
                                             (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0xdU & 
                                             (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0xdU & 
                                             (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0xdU & 
                                             (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys5__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys5__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys5__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys5__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys5__DOT__dut__DOT__fit_base = 0xdU;
            tb_sys5__DOT__dut__DOT__best_sz = tb_sys5__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (0xeU & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))) 
                          - (IData)(1U)))) & (0x20U 
                                              >= ((IData)(0xeU) 
                                                  + 
                                                  (0x3fU 
                                                   & ((IData)(1U) 
                                                      << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys5__DOT__dut__DOT__slice_busy, 0xeU) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys5__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)));
        tb_sys5__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0xeU & 
                                             (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0xeU & 
                                             (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0xeU & 
                                             (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0xeU & 
                                             (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0xeU & 
                                             (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0xeU & 
                                             (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys5__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys5__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys5__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys5__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys5__DOT__dut__DOT__fit_base = 0xeU;
            tb_sys5__DOT__dut__DOT__best_sz = tb_sys5__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (0xfU & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))) 
                          - (IData)(1U)))) & (0x20U 
                                              >= ((IData)(0xfU) 
                                                  + 
                                                  (0x3fU 
                                                   & ((IData)(1U) 
                                                      << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys5__DOT__dut__DOT__slice_busy, 0xfU) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys5__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)));
        tb_sys5__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0xfU & 
                                             (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0xfU & 
                                             (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0xfU & 
                                             (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0xfU & 
                                             (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0xfU & 
                                             (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0xfU & 
                                             (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                 - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys5__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys5__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys5__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys5__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys5__DOT__dut__DOT__fit_base = 0xfU;
            tb_sys5__DOT__dut__DOT__best_sz = tb_sys5__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (0x10U & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))) 
                           - (IData)(1U)))) & (0x20U 
                                               >= ((IData)(0x10U) 
                                                   + 
                                                   (0x3fU 
                                                    & ((IData)(1U) 
                                                       << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys5__DOT__dut__DOT__slice_busy, 0x10U) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys5__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)));
        tb_sys5__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x10U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x10U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x10U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x10U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x10U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x10U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys5__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys5__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys5__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys5__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys5__DOT__dut__DOT__fit_base = 0x10U;
            tb_sys5__DOT__dut__DOT__best_sz = tb_sys5__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (0x11U & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))) 
                           - (IData)(1U)))) & (0x20U 
                                               >= ((IData)(0x11U) 
                                                   + 
                                                   (0x3fU 
                                                    & ((IData)(1U) 
                                                       << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys5__DOT__dut__DOT__slice_busy, 0x11U) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys5__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)));
        tb_sys5__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x11U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x11U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x11U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x11U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x11U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x11U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys5__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys5__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys5__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys5__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys5__DOT__dut__DOT__fit_base = 0x11U;
            tb_sys5__DOT__dut__DOT__best_sz = tb_sys5__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (0x12U & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))) 
                           - (IData)(1U)))) & (0x20U 
                                               >= ((IData)(0x12U) 
                                                   + 
                                                   (0x3fU 
                                                    & ((IData)(1U) 
                                                       << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys5__DOT__dut__DOT__slice_busy, 0x12U) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys5__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)));
        tb_sys5__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x12U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x12U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x12U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x12U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x12U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x12U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys5__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys5__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys5__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys5__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys5__DOT__dut__DOT__fit_base = 0x12U;
            tb_sys5__DOT__dut__DOT__best_sz = tb_sys5__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (0x13U & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))) 
                           - (IData)(1U)))) & (0x20U 
                                               >= ((IData)(0x13U) 
                                                   + 
                                                   (0x3fU 
                                                    & ((IData)(1U) 
                                                       << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys5__DOT__dut__DOT__slice_busy, 0x13U) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys5__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)));
        tb_sys5__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x13U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x13U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x13U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x13U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x13U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x13U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys5__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys5__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys5__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys5__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys5__DOT__dut__DOT__fit_base = 0x13U;
            tb_sys5__DOT__dut__DOT__best_sz = tb_sys5__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (0x14U & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))) 
                           - (IData)(1U)))) & (0x20U 
                                               >= ((IData)(0x14U) 
                                                   + 
                                                   (0x3fU 
                                                    & ((IData)(1U) 
                                                       << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys5__DOT__dut__DOT__slice_busy, 0x14U) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys5__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)));
        tb_sys5__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x14U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x14U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x14U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x14U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x14U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x14U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys5__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys5__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys5__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys5__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys5__DOT__dut__DOT__fit_base = 0x14U;
            tb_sys5__DOT__dut__DOT__best_sz = tb_sys5__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (0x15U & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))) 
                           - (IData)(1U)))) & (0x20U 
                                               >= ((IData)(0x15U) 
                                                   + 
                                                   (0x3fU 
                                                    & ((IData)(1U) 
                                                       << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys5__DOT__dut__DOT__slice_busy, 0x15U) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys5__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)));
        tb_sys5__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x15U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x15U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x15U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x15U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x15U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x15U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys5__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys5__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys5__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys5__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys5__DOT__dut__DOT__fit_base = 0x15U;
            tb_sys5__DOT__dut__DOT__best_sz = tb_sys5__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (0x16U & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))) 
                           - (IData)(1U)))) & (0x20U 
                                               >= ((IData)(0x16U) 
                                                   + 
                                                   (0x3fU 
                                                    & ((IData)(1U) 
                                                       << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys5__DOT__dut__DOT__slice_busy, 0x16U) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys5__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)));
        tb_sys5__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x16U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x16U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x16U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x16U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x16U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x16U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys5__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys5__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys5__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys5__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys5__DOT__dut__DOT__fit_base = 0x16U;
            tb_sys5__DOT__dut__DOT__best_sz = tb_sys5__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (0x17U & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))) 
                           - (IData)(1U)))) & (0x20U 
                                               >= ((IData)(0x17U) 
                                                   + 
                                                   (0x3fU 
                                                    & ((IData)(1U) 
                                                       << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys5__DOT__dut__DOT__slice_busy, 0x17U) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys5__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)));
        tb_sys5__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x17U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x17U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x17U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x17U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x17U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x17U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys5__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys5__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys5__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys5__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys5__DOT__dut__DOT__fit_base = 0x17U;
            tb_sys5__DOT__dut__DOT__best_sz = tb_sys5__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (0x18U & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))) 
                           - (IData)(1U)))) & (0x20U 
                                               >= ((IData)(0x18U) 
                                                   + 
                                                   (0x3fU 
                                                    & ((IData)(1U) 
                                                       << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys5__DOT__dut__DOT__slice_busy, 0x18U) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys5__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)));
        tb_sys5__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x18U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x18U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x18U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x18U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x18U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x18U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys5__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys5__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys5__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys5__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys5__DOT__dut__DOT__fit_base = 0x18U;
            tb_sys5__DOT__dut__DOT__best_sz = tb_sys5__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (0x19U & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))) 
                           - (IData)(1U)))) & (0x20U 
                                               >= ((IData)(0x19U) 
                                                   + 
                                                   (0x3fU 
                                                    & ((IData)(1U) 
                                                       << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys5__DOT__dut__DOT__slice_busy, 0x19U) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys5__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)));
        tb_sys5__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x19U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x19U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x19U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x19U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x19U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x19U 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys5__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys5__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys5__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys5__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys5__DOT__dut__DOT__fit_base = 0x19U;
            tb_sys5__DOT__dut__DOT__best_sz = tb_sys5__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (0x1aU & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))) 
                           - (IData)(1U)))) & (0x20U 
                                               >= ((IData)(0x1aU) 
                                                   + 
                                                   (0x3fU 
                                                    & ((IData)(1U) 
                                                       << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys5__DOT__dut__DOT__slice_busy, 0x1aU) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys5__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)));
        tb_sys5__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x1aU 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x1aU 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x1aU 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x1aU 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x1aU 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x1aU 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys5__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys5__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys5__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys5__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys5__DOT__dut__DOT__fit_base = 0x1aU;
            tb_sys5__DOT__dut__DOT__best_sz = tb_sys5__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (0x1bU & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))) 
                           - (IData)(1U)))) & (0x20U 
                                               >= ((IData)(0x1bU) 
                                                   + 
                                                   (0x3fU 
                                                    & ((IData)(1U) 
                                                       << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys5__DOT__dut__DOT__slice_busy, 0x1bU) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys5__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)));
        tb_sys5__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x1bU 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x1bU 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x1bU 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x1bU 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x1bU 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x1bU 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys5__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys5__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys5__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys5__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys5__DOT__dut__DOT__fit_base = 0x1bU;
            tb_sys5__DOT__dut__DOT__best_sz = tb_sys5__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (0x1cU & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))) 
                           - (IData)(1U)))) & (0x20U 
                                               >= ((IData)(0x1cU) 
                                                   + 
                                                   (0x3fU 
                                                    & ((IData)(1U) 
                                                       << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys5__DOT__dut__DOT__slice_busy, 0x1cU) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys5__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)));
        tb_sys5__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x1cU 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x1cU 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x1cU 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x1cU 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x1cU 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x1cU 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys5__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys5__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys5__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys5__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys5__DOT__dut__DOT__fit_base = 0x1cU;
            tb_sys5__DOT__dut__DOT__best_sz = tb_sys5__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (0x1dU & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))) 
                           - (IData)(1U)))) & (0x20U 
                                               >= ((IData)(0x1dU) 
                                                   + 
                                                   (0x3fU 
                                                    & ((IData)(1U) 
                                                       << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys5__DOT__dut__DOT__slice_busy, 0x1dU) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys5__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)));
        tb_sys5__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x1dU 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x1dU 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x1dU 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x1dU 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x1dU 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x1dU 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys5__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys5__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys5__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys5__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys5__DOT__dut__DOT__fit_base = 0x1dU;
            tb_sys5__DOT__dut__DOT__best_sz = tb_sys5__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (0x1eU & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))) 
                           - (IData)(1U)))) & (0x20U 
                                               >= ((IData)(0x1eU) 
                                                   + 
                                                   (0x3fU 
                                                    & ((IData)(1U) 
                                                       << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys5__DOT__dut__DOT__slice_busy, 0x1eU) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys5__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)));
        tb_sys5__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x1eU 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x1eU 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x1eU 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x1eU 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x1eU 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x1eU 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys5__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys5__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys5__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys5__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys5__DOT__dut__DOT__fit_base = 0x1eU;
            tb_sys5__DOT__dut__DOT__best_sz = tb_sys5__DOT__dut__DOT__bsz;
        }
    }
    if ((((0U == (0x1fU & ((0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))) 
                           - (IData)(1U)))) & (0x20U 
                                               >= ((IData)(0x1fU) 
                                                   + 
                                                   (0x3fU 
                                                    & ((IData)(1U) 
                                                       << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))))) 
         & (0ULL == (VL_SHIFTR_QQI(64,64,32, vlSelf->tb_sys5__DOT__dut__DOT__slice_busy, 0x1fU) 
                     & ((1ULL << (0x3fU & ((IData)(1U) 
                                           << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)))) 
                        - 1ULL))))) {
        tb_sys5__DOT__dut__DOT__bsz = (0x3fU & ((IData)(1U) 
                                                << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw)));
        tb_sys5__DOT__dut__DOT__blk = 1U;
        if ((1U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x1fU 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 2U;
        if ((2U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x1fU 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 4U;
        if ((4U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x1fU 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 8U;
        if ((8U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x1fU 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x10U;
        if ((0x10U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x1fU 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        tb_sys5__DOT__dut__DOT__blk = 0x20U;
        if ((0x20U >= (0x3fU & ((IData)(1U) << (IData)(vlSelf->tb_sys5__DOT__dut__DOT__cur_lw))))) {
            tb_sys5__DOT__dut__DOT__bbase = (0x1fU 
                                             & (~ ((IData)(tb_sys5__DOT__dut__DOT__blk) 
                                                   - (IData)(1U))));
            if (((0x20U >= ((IData)(tb_sys5__DOT__dut__DOT__bbase) 
                            + (IData)(tb_sys5__DOT__dut__DOT__blk))) 
                 & (0ULL == ((vlSelf->tb_sys5__DOT__dut__DOT__slice_busy 
                              >> (IData)(tb_sys5__DOT__dut__DOT__bbase)) 
                             & ([&]() {
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w 
                                        = tb_sys5__DOT__dut__DOT__blk;
                                    vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout 
                                        = (VL_SHIFTL_QQI(64,64,7, 1ULL, (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__w)) 
                                           - 1ULL);
                                }(), vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__gmask__0__Vfuncout))))) {
                tb_sys5__DOT__dut__DOT__bsz = tb_sys5__DOT__dut__DOT__blk;
            }
        }
        if ((1U & ((~ (IData)(vlSelf->tb_sys5__DOT__dut__DOT__fit_found)) 
                   | ((IData)(tb_sys5__DOT__dut__DOT__bsz) 
                      < (IData)(tb_sys5__DOT__dut__DOT__best_sz))))) {
            vlSelf->tb_sys5__DOT__dut__DOT__fit_found = 1U;
            vlSelf->tb_sys5__DOT__dut__DOT__fit_base = 0x1fU;
            tb_sys5__DOT__dut__DOT__best_sz = tb_sys5__DOT__dut__DOT__bsz;
        }
    }
    vlSelf->tb_sys5__DOT__dut__DOT__row_any = ((0xfffcU 
                                                & (IData)(vlSelf->tb_sys5__DOT__dut__DOT__row_any)) 
                                               | (((IData)(
                                                           (0U 
                                                            != 
                                                            (vlSelf->tb_sys5__DOT__dut__DOT__req_tab[0U] 
                                                             >> 0x10U))) 
                                                   << 1U) 
                                                  | (0U 
                                                     != 
                                                     (0xffffU 
                                                      & vlSelf->tb_sys5__DOT__dut__DOT__req_tab[0U]))));
    vlSelf->tb_sys5__DOT__dut__DOT__row_any = ((0xfff3U 
                                                & (IData)(vlSelf->tb_sys5__DOT__dut__DOT__row_any)) 
                                               | ((((IData)(
                                                            (0U 
                                                             != 
                                                             (vlSelf->tb_sys5__DOT__dut__DOT__req_tab[1U] 
                                                              >> 0x10U))) 
                                                    << 1U) 
                                                   | (0U 
                                                      != 
                                                      (0xffffU 
                                                       & vlSelf->tb_sys5__DOT__dut__DOT__req_tab[1U]))) 
                                                  << 2U));
    vlSelf->tb_sys5__DOT__dut__DOT__row_any = ((0xffcfU 
                                                & (IData)(vlSelf->tb_sys5__DOT__dut__DOT__row_any)) 
                                               | ((((IData)(
                                                            (0U 
                                                             != 
                                                             (vlSelf->tb_sys5__DOT__dut__DOT__req_tab[2U] 
                                                              >> 0x10U))) 
                                                    << 1U) 
                                                   | (0U 
                                                      != 
                                                      (0xffffU 
                                                       & vlSelf->tb_sys5__DOT__dut__DOT__req_tab[2U]))) 
                                                  << 4U));
    vlSelf->tb_sys5__DOT__dut__DOT__row_any = ((0xff3fU 
                                                & (IData)(vlSelf->tb_sys5__DOT__dut__DOT__row_any)) 
                                               | ((((IData)(
                                                            (0U 
                                                             != 
                                                             (vlSelf->tb_sys5__DOT__dut__DOT__req_tab[3U] 
                                                              >> 0x10U))) 
                                                    << 1U) 
                                                   | (0U 
                                                      != 
                                                      (0xffffU 
                                                       & vlSelf->tb_sys5__DOT__dut__DOT__req_tab[3U]))) 
                                                  << 6U));
    vlSelf->tb_sys5__DOT__dut__DOT__row_any = ((0xfcffU 
                                                & (IData)(vlSelf->tb_sys5__DOT__dut__DOT__row_any)) 
                                               | ((((IData)(
                                                            (0U 
                                                             != 
                                                             (vlSelf->tb_sys5__DOT__dut__DOT__req_tab[4U] 
                                                              >> 0x10U))) 
                                                    << 1U) 
                                                   | (0U 
                                                      != 
                                                      (0xffffU 
                                                       & vlSelf->tb_sys5__DOT__dut__DOT__req_tab[4U]))) 
                                                  << 8U));
    vlSelf->tb_sys5__DOT__dut__DOT__row_any = ((0xf3ffU 
                                                & (IData)(vlSelf->tb_sys5__DOT__dut__DOT__row_any)) 
                                               | ((((IData)(
                                                            (0U 
                                                             != 
                                                             (vlSelf->tb_sys5__DOT__dut__DOT__req_tab[5U] 
                                                              >> 0x10U))) 
                                                    << 1U) 
                                                   | (0U 
                                                      != 
                                                      (0xffffU 
                                                       & vlSelf->tb_sys5__DOT__dut__DOT__req_tab[5U]))) 
                                                  << 0xaU));
    vlSelf->tb_sys5__DOT__dut__DOT__row_any = ((0xcfffU 
                                                & (IData)(vlSelf->tb_sys5__DOT__dut__DOT__row_any)) 
                                               | ((((IData)(
                                                            (0U 
                                                             != 
                                                             (vlSelf->tb_sys5__DOT__dut__DOT__req_tab[6U] 
                                                              >> 0x10U))) 
                                                    << 1U) 
                                                   | (0U 
                                                      != 
                                                      (0xffffU 
                                                       & vlSelf->tb_sys5__DOT__dut__DOT__req_tab[6U]))) 
                                                  << 0xcU));
    vlSelf->tb_sys5__DOT__dut__DOT__row_any = ((0x3fffU 
                                                & (IData)(vlSelf->tb_sys5__DOT__dut__DOT__row_any)) 
                                               | ((((IData)(
                                                            (0U 
                                                             != 
                                                             (vlSelf->tb_sys5__DOT__dut__DOT__req_tab[7U] 
                                                              >> 0x10U))) 
                                                    << 1U) 
                                                   | (0U 
                                                      != 
                                                      (0xffffU 
                                                       & vlSelf->tb_sys5__DOT__dut__DOT__req_tab[7U]))) 
                                                  << 0xeU));
    vlSelf->tb_sys5__DOT__dut__DOT__w_found = (0U != (IData)(vlSelf->tb_sys5__DOT__dut__DOT__row_any));
    __Vfunc_tb_sys5__DOT__dut__DOT__pe16__1__x = vlSelf->tb_sys5__DOT__dut__DOT__row_any;
    tb_sys5__DOT__dut__DOT__pe16__Vstatic__b3 = (1U 
                                                 & (~ (IData)(
                                                              (0U 
                                                               != 
                                                               (0xffU 
                                                                & (IData)(__Vfunc_tb_sys5__DOT__dut__DOT__pe16__1__x))))));
    tb_sys5__DOT__dut__DOT__pe16__Vstatic__x8 = (0xffU 
                                                 & ((IData)(tb_sys5__DOT__dut__DOT__pe16__Vstatic__b3)
                                                     ? 
                                                    ((IData)(__Vfunc_tb_sys5__DOT__dut__DOT__pe16__1__x) 
                                                     >> 8U)
                                                     : (IData)(__Vfunc_tb_sys5__DOT__dut__DOT__pe16__1__x)));
    tb_sys5__DOT__dut__DOT__pe16__Vstatic__b2 = (1U 
                                                 & (~ (IData)(
                                                              (0U 
                                                               != 
                                                               (0xfU 
                                                                & (IData)(tb_sys5__DOT__dut__DOT__pe16__Vstatic__x8))))));
    tb_sys5__DOT__dut__DOT__pe16__Vstatic__x4 = (0xfU 
                                                 & ((IData)(tb_sys5__DOT__dut__DOT__pe16__Vstatic__b2)
                                                     ? 
                                                    ((IData)(tb_sys5__DOT__dut__DOT__pe16__Vstatic__x8) 
                                                     >> 4U)
                                                     : (IData)(tb_sys5__DOT__dut__DOT__pe16__Vstatic__x8)));
    tb_sys5__DOT__dut__DOT__pe16__Vstatic__b1 = (1U 
                                                 & (~ (IData)(
                                                              (0U 
                                                               != 
                                                               (3U 
                                                                & (IData)(tb_sys5__DOT__dut__DOT__pe16__Vstatic__x4))))));
    tb_sys5__DOT__dut__DOT__pe16__Vstatic__x2 = (3U 
                                                 & ((IData)(tb_sys5__DOT__dut__DOT__pe16__Vstatic__b1)
                                                     ? 
                                                    ((IData)(tb_sys5__DOT__dut__DOT__pe16__Vstatic__x4) 
                                                     >> 2U)
                                                     : (IData)(tb_sys5__DOT__dut__DOT__pe16__Vstatic__x4)));
    __Vfunc_tb_sys5__DOT__dut__DOT__pe16__1__Vfuncout 
        = (((IData)(tb_sys5__DOT__dut__DOT__pe16__Vstatic__b3) 
            << 3U) | (((IData)(tb_sys5__DOT__dut__DOT__pe16__Vstatic__b2) 
                       << 2U) | (((IData)(tb_sys5__DOT__dut__DOT__pe16__Vstatic__b1) 
                                  << 1U) | (1U & (~ (IData)(tb_sys5__DOT__dut__DOT__pe16__Vstatic__x2))))));
    tb_sys5__DOT__dut__DOT__w_row = __Vfunc_tb_sys5__DOT__dut__DOT__pe16__1__Vfuncout;
    vlSelf->tb_sys5__DOT__dut__DOT__w_id = (((IData)(tb_sys5__DOT__dut__DOT__w_row) 
                                             << 4U) 
                                            | ([&]() {
                vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__pe16__2__x 
                    = (0xffffU & (((0U == (0x1fU & 
                                           VL_SHIFTL_III(8,32,32, (IData)(tb_sys5__DOT__dut__DOT__w_row), 4U)))
                                    ? 0U : (vlSelf->tb_sys5__DOT__dut__DOT__req_tab[
                                            (((IData)(0xfU) 
                                              + (0xffU 
                                                 & VL_SHIFTL_III(8,32,32, (IData)(tb_sys5__DOT__dut__DOT__w_row), 4U))) 
                                             >> 5U)] 
                                            << ((IData)(0x20U) 
                                                - (0x1fU 
                                                   & VL_SHIFTL_III(8,32,32, (IData)(tb_sys5__DOT__dut__DOT__w_row), 4U))))) 
                                  | (vlSelf->tb_sys5__DOT__dut__DOT__req_tab[
                                     (7U & (VL_SHIFTL_III(8,32,32, (IData)(tb_sys5__DOT__dut__DOT__w_row), 4U) 
                                            >> 5U))] 
                                     >> (0x1fU & VL_SHIFTL_III(8,32,32, (IData)(tb_sys5__DOT__dut__DOT__w_row), 4U)))));
                tb_sys5__DOT__dut__DOT__pe16__Vstatic__b3 
                    = (1U & (~ (IData)((0U != (0xffU 
                                               & (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__pe16__2__x))))));
                tb_sys5__DOT__dut__DOT__pe16__Vstatic__x8 
                    = (0xffU & ((IData)(tb_sys5__DOT__dut__DOT__pe16__Vstatic__b3)
                                 ? ((IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__pe16__2__x) 
                                    >> 8U) : (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__pe16__2__x)));
                tb_sys5__DOT__dut__DOT__pe16__Vstatic__b2 
                    = (1U & (~ (IData)((0U != (0xfU 
                                               & (IData)(tb_sys5__DOT__dut__DOT__pe16__Vstatic__x8))))));
                tb_sys5__DOT__dut__DOT__pe16__Vstatic__x4 
                    = (0xfU & ((IData)(tb_sys5__DOT__dut__DOT__pe16__Vstatic__b2)
                                ? ((IData)(tb_sys5__DOT__dut__DOT__pe16__Vstatic__x8) 
                                   >> 4U) : (IData)(tb_sys5__DOT__dut__DOT__pe16__Vstatic__x8)));
                tb_sys5__DOT__dut__DOT__pe16__Vstatic__b1 
                    = (1U & (~ (IData)((0U != (3U & (IData)(tb_sys5__DOT__dut__DOT__pe16__Vstatic__x4))))));
                tb_sys5__DOT__dut__DOT__pe16__Vstatic__x2 
                    = (3U & ((IData)(tb_sys5__DOT__dut__DOT__pe16__Vstatic__b1)
                              ? ((IData)(tb_sys5__DOT__dut__DOT__pe16__Vstatic__x4) 
                                 >> 2U) : (IData)(tb_sys5__DOT__dut__DOT__pe16__Vstatic__x4)));
                vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__pe16__2__Vfuncout 
                    = (((IData)(tb_sys5__DOT__dut__DOT__pe16__Vstatic__b3) 
                        << 3U) | (((IData)(tb_sys5__DOT__dut__DOT__pe16__Vstatic__b2) 
                                   << 2U) | (((IData)(tb_sys5__DOT__dut__DOT__pe16__Vstatic__b1) 
                                              << 1U) 
                                             | (1U 
                                                & (~ (IData)(tb_sys5__DOT__dut__DOT__pe16__Vstatic__x2))))));
            }(), (IData)(vlSelf->__Vfunc_tb_sys5__DOT__dut__DOT__pe16__2__Vfuncout)));
    vlSelf->tb_sys5__DOT__dut__DOT__pend_v = (((IData)(vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__31__KET____DOT__pend) 
                                               << 0x1fU) 
                                              | (((IData)(vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__30__KET____DOT__pend) 
                                                  << 0x1eU) 
                                                 | (((IData)(vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__29__KET____DOT__pend) 
                                                     << 0x1dU) 
                                                    | (((IData)(vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__28__KET____DOT__pend) 
                                                        << 0x1cU) 
                                                       | (((IData)(vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__27__KET____DOT__pend) 
                                                           << 0x1bU) 
                                                          | (((IData)(vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__26__KET____DOT__pend) 
                                                              << 0x1aU) 
                                                             | (((IData)(vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__25__KET____DOT__pend) 
                                                                 << 0x19U) 
                                                                | (((IData)(vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__24__KET____DOT__pend) 
                                                                    << 0x18U) 
                                                                   | (((IData)(vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__23__KET____DOT__pend) 
                                                                       << 0x17U) 
                                                                      | (((IData)(vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__22__KET____DOT__pend) 
                                                                          << 0x16U) 
                                                                         | (((IData)(vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__21__KET____DOT__pend) 
                                                                             << 0x15U) 
                                                                            | (((IData)(vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__20__KET____DOT__pend) 
                                                                                << 0x14U) 
                                                                               | (((IData)(vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__19__KET____DOT__pend) 
                                                                                << 0x13U) 
                                                                                | (((IData)(vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__18__KET____DOT__pend) 
                                                                                << 0x12U) 
                                                                                | (((IData)(vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__17__KET____DOT__pend) 
                                                                                << 0x11U) 
                                                                                | (((IData)(vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__16__KET____DOT__pend) 
                                                                                << 0x10U) 
                                                                                | (((IData)(vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__15__KET____DOT__pend) 
                                                                                << 0xfU) 
                                                                                | (((IData)(vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__14__KET____DOT__pend) 
                                                                                << 0xeU) 
                                                                                | (((IData)(vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__13__KET____DOT__pend) 
                                                                                << 0xdU) 
                                                                                | (((IData)(vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__12__KET____DOT__pend) 
                                                                                << 0xcU) 
                                                                                | (((IData)(vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__11__KET____DOT__pend) 
                                                                                << 0xbU) 
                                                                                | (((IData)(vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__10__KET____DOT__pend) 
                                                                                << 0xaU) 
                                                                                | (((IData)(vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__9__KET____DOT__pend) 
                                                                                << 9U) 
                                                                                | (((IData)(vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__8__KET____DOT__pend) 
                                                                                << 8U) 
                                                                                | (((IData)(vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__7__KET____DOT__pend) 
                                                                                << 7U) 
                                                                                | (((IData)(vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__6__KET____DOT__pend) 
                                                                                << 6U) 
                                                                                | (((IData)(vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__5__KET____DOT__pend) 
                                                                                << 5U) 
                                                                                | (((IData)(vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__4__KET____DOT__pend) 
                                                                                << 4U) 
                                                                                | (((IData)(vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__3__KET____DOT__pend) 
                                                                                << 3U) 
                                                                                | (((IData)(vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__2__KET____DOT__pend) 
                                                                                << 2U) 
                                                                                | (((IData)(vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__1__KET____DOT__pend) 
                                                                                << 1U) 
                                                                                | (IData)(vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__0__KET____DOT__pend))))))))))))))))))))))))))))))));
    vlSelf->tb_sys5__DOT__dut__DOT__halted_v = (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__halted_r) 
                                                 << 0x1fU) 
                                                | (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__halted_r) 
                                                    << 0x1eU) 
                                                   | (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__halted_r) 
                                                       << 0x1dU) 
                                                      | (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__28__KET____DOT__core.__PVT__halted_r) 
                                                          << 0x1cU) 
                                                         | (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__27__KET____DOT__core.__PVT__halted_r) 
                                                             << 0x1bU) 
                                                            | (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__26__KET____DOT__core.__PVT__halted_r) 
                                                                << 0x1aU) 
                                                               | (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__25__KET____DOT__core.__PVT__halted_r) 
                                                                   << 0x19U) 
                                                                  | (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__24__KET____DOT__core.__PVT__halted_r) 
                                                                      << 0x18U) 
                                                                     | (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__23__KET____DOT__core.__PVT__halted_r) 
                                                                         << 0x17U) 
                                                                        | (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__22__KET____DOT__core.__PVT__halted_r) 
                                                                            << 0x16U) 
                                                                           | (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__21__KET____DOT__core.__PVT__halted_r) 
                                                                               << 0x15U) 
                                                                              | (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__20__KET____DOT__core.__PVT__halted_r) 
                                                                                << 0x14U) 
                                                                                | (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__19__KET____DOT__core.__PVT__halted_r) 
                                                                                << 0x13U) 
                                                                                | (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__18__KET____DOT__core.__PVT__halted_r) 
                                                                                << 0x12U) 
                                                                                | (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__17__KET____DOT__core.__PVT__halted_r) 
                                                                                << 0x11U) 
                                                                                | (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__16__KET____DOT__core.__PVT__halted_r) 
                                                                                << 0x10U) 
                                                                                | (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__15__KET____DOT__core.__PVT__halted_r) 
                                                                                << 0xfU) 
                                                                                | (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__14__KET____DOT__core.__PVT__halted_r) 
                                                                                << 0xeU) 
                                                                                | (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__13__KET____DOT__core.__PVT__halted_r) 
                                                                                << 0xdU) 
                                                                                | (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__12__KET____DOT__core.__PVT__halted_r) 
                                                                                << 0xcU) 
                                                                                | (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__11__KET____DOT__core.__PVT__halted_r) 
                                                                                << 0xbU) 
                                                                                | (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__10__KET____DOT__core.__PVT__halted_r) 
                                                                                << 0xaU) 
                                                                                | (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__9__KET____DOT__core.__PVT__halted_r) 
                                                                                << 9U) 
                                                                                | (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__8__KET____DOT__core.__PVT__halted_r) 
                                                                                << 8U) 
                                                                                | (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__7__KET____DOT__core.__PVT__halted_r) 
                                                                                << 7U) 
                                                                                | (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__6__KET____DOT__core.__PVT__halted_r) 
                                                                                << 6U) 
                                                                                | (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__5__KET____DOT__core.__PVT__halted_r) 
                                                                                << 5U) 
                                                                                | (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__4__KET____DOT__core.__PVT__halted_r) 
                                                                                << 4U) 
                                                                                | (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__3__KET____DOT__core.__PVT__halted_r) 
                                                                                << 3U) 
                                                                                | (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__2__KET____DOT__core.__PVT__halted_r) 
                                                                                << 2U) 
                                                                                | (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__1__KET____DOT__core.__PVT__halted_r) 
                                                                                << 1U) 
                                                                                | (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__0__KET____DOT__core.__PVT__halted_r))))))))))))))))))))))))))))))));
    vlSelf->tb_sys5__DOT__dut__DOT__bhead = vlSelf->tb_sys5__DOT__dut__DOT__qk
        [(0x7ffU & (VL_SHIFTL_III(11,11,32, (IData)(vlSelf->tb_sys5__DOT__dut__DOT__hb), 8U) 
                    + (0xffU & vlSelf->tb_sys5__DOT__dut__DOT__krd
                       [(7U & (IData)(vlSelf->tb_sys5__DOT__dut__DOT__hb))])))];
}

VL_ATTR_COLD void Vtb_sys5___024root___stl_sequent__TOP__1(Vtb_sys5___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_sys5__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtb_sys5___024root___stl_sequent__TOP__1\n"); );
    // Body
    if (vlSelf->tb_sys5__DOT__dut__DOT__cph) {
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__0__KET____DOT__rf_aa 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__0__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__0__KET____DOT__rf_ba 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__0__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__1__KET____DOT__rf_aa 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__1__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__1__KET____DOT__rf_ba 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__1__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__2__KET____DOT__rf_aa 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__2__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__2__KET____DOT__rf_ba 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__2__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__3__KET____DOT__rf_aa 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__3__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__3__KET____DOT__rf_ba 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__3__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__4__KET____DOT__rf_aa 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__4__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__4__KET____DOT__rf_ba 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__4__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__5__KET____DOT__rf_aa 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__5__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__5__KET____DOT__rf_ba 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__5__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__6__KET____DOT__rf_aa 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__6__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__6__KET____DOT__rf_ba 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__6__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__7__KET____DOT__rf_aa 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__7__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__7__KET____DOT__rf_ba 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__7__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__8__KET____DOT__rf_aa 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__8__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__8__KET____DOT__rf_ba 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__8__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__9__KET____DOT__rf_aa 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__9__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__9__KET____DOT__rf_ba 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__9__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__10__KET____DOT__rf_aa 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__10__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__10__KET____DOT__rf_ba 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__10__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__11__KET____DOT__rf_aa 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__11__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__11__KET____DOT__rf_ba 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__11__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__12__KET____DOT__rf_aa 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__12__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__12__KET____DOT__rf_ba 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__12__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__13__KET____DOT__rf_aa 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__13__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__13__KET____DOT__rf_ba 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__13__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__14__KET____DOT__rf_aa 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__14__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__14__KET____DOT__rf_ba 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__14__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__15__KET____DOT__rf_aa 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__15__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__15__KET____DOT__rf_ba 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__15__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__16__KET____DOT__rf_aa 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__16__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__16__KET____DOT__rf_ba 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__16__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__17__KET____DOT__rf_aa 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__17__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__17__KET____DOT__rf_ba 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__17__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__18__KET____DOT__rf_aa 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__18__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__18__KET____DOT__rf_ba 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__18__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__19__KET____DOT__rf_aa 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__19__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__19__KET____DOT__rf_ba 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__19__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__20__KET____DOT__rf_aa 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__20__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__20__KET____DOT__rf_ba 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__20__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__21__KET____DOT__rf_aa 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__21__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__21__KET____DOT__rf_ba 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__21__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__22__KET____DOT__rf_aa 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__22__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__22__KET____DOT__rf_ba 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__22__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__23__KET____DOT__rf_aa 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__23__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__23__KET____DOT__rf_ba 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__23__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__24__KET____DOT__rf_aa 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__24__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__24__KET____DOT__rf_ba 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__24__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__25__KET____DOT__rf_aa 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__25__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__25__KET____DOT__rf_ba 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__25__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__26__KET____DOT__rf_aa 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__26__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__26__KET____DOT__rf_ba 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__26__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__27__KET____DOT__rf_aa 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__27__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__27__KET____DOT__rf_ba 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__27__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__28__KET____DOT__rf_aa 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__28__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__28__KET____DOT__rf_ba 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__28__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__29__KET____DOT__rf_aa 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__29__KET____DOT__rf_ba 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__30__KET____DOT__rf_aa 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__30__KET____DOT__rf_ba 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__31__KET____DOT__rf_aa 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.rw_addr;
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__31__KET____DOT__rf_ba 
            = vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.rw_addr;
    } else {
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__0__KET____DOT__rf_aa 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__0__KET____DOT__core.__PVT__ir 
                          >> 0xaU)) | ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__0__KET____DOT__core.__PVT__state))
                                        ? 0x1fU : (0x1fU 
                                                   & ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__0__KET____DOT__core.__PVT__shx)
                                                       ? 
                                                      (0x1fU 
                                                       & (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__0__KET____DOT__core.__PVT__ia))
                                                       : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__0__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__0__KET____DOT__rf_ba 
            = ((0x3e0U & (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__0__KET____DOT__core.__PVT__shx)
                            ? (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__0__KET____DOT__core.__PVT__ir 
                               >> 0xfU) : (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__0__KET____DOT__core.__PVT__ir 
                                           >> 0x14U)) 
                          << 5U)) | (0x1fU & ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__0__KET____DOT__core.__PVT__state))
                                               ? (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__0__KET____DOT__core.__PVT__j)
                                               : ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__0__KET____DOT__core.__PVT__shx)
                                                   ? vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__0__KET____DOT__core.__VdfgTmp_h586768a0__0
                                                   : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__0__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__1__KET____DOT__rf_aa 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__1__KET____DOT__core.__PVT__ir 
                          >> 0xaU)) | ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__1__KET____DOT__core.__PVT__state))
                                        ? 0x1fU : (0x1fU 
                                                   & ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__1__KET____DOT__core.__PVT__shx)
                                                       ? 
                                                      (0x1fU 
                                                       & (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__1__KET____DOT__core.__PVT__ia))
                                                       : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__1__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__1__KET____DOT__rf_ba 
            = ((0x3e0U & (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__1__KET____DOT__core.__PVT__shx)
                            ? (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__1__KET____DOT__core.__PVT__ir 
                               >> 0xfU) : (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__1__KET____DOT__core.__PVT__ir 
                                           >> 0x14U)) 
                          << 5U)) | (0x1fU & ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__1__KET____DOT__core.__PVT__state))
                                               ? (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__1__KET____DOT__core.__PVT__j)
                                               : ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__1__KET____DOT__core.__PVT__shx)
                                                   ? vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__1__KET____DOT__core.__VdfgTmp_h586768a0__0
                                                   : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__1__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__2__KET____DOT__rf_aa 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__2__KET____DOT__core.__PVT__ir 
                          >> 0xaU)) | ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__2__KET____DOT__core.__PVT__state))
                                        ? 0x1fU : (0x1fU 
                                                   & ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__2__KET____DOT__core.__PVT__shx)
                                                       ? 
                                                      (0x1fU 
                                                       & (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__2__KET____DOT__core.__PVT__ia))
                                                       : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__2__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__2__KET____DOT__rf_ba 
            = ((0x3e0U & (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__2__KET____DOT__core.__PVT__shx)
                            ? (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__2__KET____DOT__core.__PVT__ir 
                               >> 0xfU) : (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__2__KET____DOT__core.__PVT__ir 
                                           >> 0x14U)) 
                          << 5U)) | (0x1fU & ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__2__KET____DOT__core.__PVT__state))
                                               ? (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__2__KET____DOT__core.__PVT__j)
                                               : ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__2__KET____DOT__core.__PVT__shx)
                                                   ? vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__2__KET____DOT__core.__VdfgTmp_h586768a0__0
                                                   : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__2__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__3__KET____DOT__rf_aa 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__3__KET____DOT__core.__PVT__ir 
                          >> 0xaU)) | ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__3__KET____DOT__core.__PVT__state))
                                        ? 0x1fU : (0x1fU 
                                                   & ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__3__KET____DOT__core.__PVT__shx)
                                                       ? 
                                                      (0x1fU 
                                                       & (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__3__KET____DOT__core.__PVT__ia))
                                                       : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__3__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__3__KET____DOT__rf_ba 
            = ((0x3e0U & (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__3__KET____DOT__core.__PVT__shx)
                            ? (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__3__KET____DOT__core.__PVT__ir 
                               >> 0xfU) : (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__3__KET____DOT__core.__PVT__ir 
                                           >> 0x14U)) 
                          << 5U)) | (0x1fU & ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__3__KET____DOT__core.__PVT__state))
                                               ? (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__3__KET____DOT__core.__PVT__j)
                                               : ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__3__KET____DOT__core.__PVT__shx)
                                                   ? vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__3__KET____DOT__core.__VdfgTmp_h586768a0__0
                                                   : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__3__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__4__KET____DOT__rf_aa 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__4__KET____DOT__core.__PVT__ir 
                          >> 0xaU)) | ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__4__KET____DOT__core.__PVT__state))
                                        ? 0x1fU : (0x1fU 
                                                   & ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__4__KET____DOT__core.__PVT__shx)
                                                       ? 
                                                      (0x1fU 
                                                       & (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__4__KET____DOT__core.__PVT__ia))
                                                       : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__4__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__4__KET____DOT__rf_ba 
            = ((0x3e0U & (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__4__KET____DOT__core.__PVT__shx)
                            ? (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__4__KET____DOT__core.__PVT__ir 
                               >> 0xfU) : (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__4__KET____DOT__core.__PVT__ir 
                                           >> 0x14U)) 
                          << 5U)) | (0x1fU & ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__4__KET____DOT__core.__PVT__state))
                                               ? (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__4__KET____DOT__core.__PVT__j)
                                               : ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__4__KET____DOT__core.__PVT__shx)
                                                   ? vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__4__KET____DOT__core.__VdfgTmp_h586768a0__0
                                                   : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__4__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__5__KET____DOT__rf_aa 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__5__KET____DOT__core.__PVT__ir 
                          >> 0xaU)) | ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__5__KET____DOT__core.__PVT__state))
                                        ? 0x1fU : (0x1fU 
                                                   & ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__5__KET____DOT__core.__PVT__shx)
                                                       ? 
                                                      (0x1fU 
                                                       & (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__5__KET____DOT__core.__PVT__ia))
                                                       : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__5__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__5__KET____DOT__rf_ba 
            = ((0x3e0U & (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__5__KET____DOT__core.__PVT__shx)
                            ? (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__5__KET____DOT__core.__PVT__ir 
                               >> 0xfU) : (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__5__KET____DOT__core.__PVT__ir 
                                           >> 0x14U)) 
                          << 5U)) | (0x1fU & ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__5__KET____DOT__core.__PVT__state))
                                               ? (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__5__KET____DOT__core.__PVT__j)
                                               : ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__5__KET____DOT__core.__PVT__shx)
                                                   ? vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__5__KET____DOT__core.__VdfgTmp_h586768a0__0
                                                   : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__5__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__6__KET____DOT__rf_aa 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__6__KET____DOT__core.__PVT__ir 
                          >> 0xaU)) | ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__6__KET____DOT__core.__PVT__state))
                                        ? 0x1fU : (0x1fU 
                                                   & ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__6__KET____DOT__core.__PVT__shx)
                                                       ? 
                                                      (0x1fU 
                                                       & (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__6__KET____DOT__core.__PVT__ia))
                                                       : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__6__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__6__KET____DOT__rf_ba 
            = ((0x3e0U & (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__6__KET____DOT__core.__PVT__shx)
                            ? (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__6__KET____DOT__core.__PVT__ir 
                               >> 0xfU) : (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__6__KET____DOT__core.__PVT__ir 
                                           >> 0x14U)) 
                          << 5U)) | (0x1fU & ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__6__KET____DOT__core.__PVT__state))
                                               ? (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__6__KET____DOT__core.__PVT__j)
                                               : ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__6__KET____DOT__core.__PVT__shx)
                                                   ? vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__6__KET____DOT__core.__VdfgTmp_h586768a0__0
                                                   : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__6__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__7__KET____DOT__rf_aa 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__7__KET____DOT__core.__PVT__ir 
                          >> 0xaU)) | ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__7__KET____DOT__core.__PVT__state))
                                        ? 0x1fU : (0x1fU 
                                                   & ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__7__KET____DOT__core.__PVT__shx)
                                                       ? 
                                                      (0x1fU 
                                                       & (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__7__KET____DOT__core.__PVT__ia))
                                                       : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__7__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__7__KET____DOT__rf_ba 
            = ((0x3e0U & (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__7__KET____DOT__core.__PVT__shx)
                            ? (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__7__KET____DOT__core.__PVT__ir 
                               >> 0xfU) : (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__7__KET____DOT__core.__PVT__ir 
                                           >> 0x14U)) 
                          << 5U)) | (0x1fU & ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__7__KET____DOT__core.__PVT__state))
                                               ? (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__7__KET____DOT__core.__PVT__j)
                                               : ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__7__KET____DOT__core.__PVT__shx)
                                                   ? vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__7__KET____DOT__core.__VdfgTmp_h586768a0__0
                                                   : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__7__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__8__KET____DOT__rf_aa 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__8__KET____DOT__core.__PVT__ir 
                          >> 0xaU)) | ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__8__KET____DOT__core.__PVT__state))
                                        ? 0x1fU : (0x1fU 
                                                   & ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__8__KET____DOT__core.__PVT__shx)
                                                       ? 
                                                      (0x1fU 
                                                       & (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__8__KET____DOT__core.__PVT__ia))
                                                       : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__8__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__8__KET____DOT__rf_ba 
            = ((0x3e0U & (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__8__KET____DOT__core.__PVT__shx)
                            ? (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__8__KET____DOT__core.__PVT__ir 
                               >> 0xfU) : (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__8__KET____DOT__core.__PVT__ir 
                                           >> 0x14U)) 
                          << 5U)) | (0x1fU & ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__8__KET____DOT__core.__PVT__state))
                                               ? (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__8__KET____DOT__core.__PVT__j)
                                               : ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__8__KET____DOT__core.__PVT__shx)
                                                   ? vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__8__KET____DOT__core.__VdfgTmp_h586768a0__0
                                                   : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__8__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__9__KET____DOT__rf_aa 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__9__KET____DOT__core.__PVT__ir 
                          >> 0xaU)) | ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__9__KET____DOT__core.__PVT__state))
                                        ? 0x1fU : (0x1fU 
                                                   & ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__9__KET____DOT__core.__PVT__shx)
                                                       ? 
                                                      (0x1fU 
                                                       & (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__9__KET____DOT__core.__PVT__ia))
                                                       : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__9__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__9__KET____DOT__rf_ba 
            = ((0x3e0U & (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__9__KET____DOT__core.__PVT__shx)
                            ? (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__9__KET____DOT__core.__PVT__ir 
                               >> 0xfU) : (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__9__KET____DOT__core.__PVT__ir 
                                           >> 0x14U)) 
                          << 5U)) | (0x1fU & ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__9__KET____DOT__core.__PVT__state))
                                               ? (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__9__KET____DOT__core.__PVT__j)
                                               : ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__9__KET____DOT__core.__PVT__shx)
                                                   ? vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__9__KET____DOT__core.__VdfgTmp_h586768a0__0
                                                   : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__9__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__10__KET____DOT__rf_aa 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__10__KET____DOT__core.__PVT__ir 
                          >> 0xaU)) | ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__10__KET____DOT__core.__PVT__state))
                                        ? 0x1fU : (0x1fU 
                                                   & ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__10__KET____DOT__core.__PVT__shx)
                                                       ? 
                                                      (0x1fU 
                                                       & (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__10__KET____DOT__core.__PVT__ia))
                                                       : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__10__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__10__KET____DOT__rf_ba 
            = ((0x3e0U & (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__10__KET____DOT__core.__PVT__shx)
                            ? (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__10__KET____DOT__core.__PVT__ir 
                               >> 0xfU) : (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__10__KET____DOT__core.__PVT__ir 
                                           >> 0x14U)) 
                          << 5U)) | (0x1fU & ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__10__KET____DOT__core.__PVT__state))
                                               ? (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__10__KET____DOT__core.__PVT__j)
                                               : ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__10__KET____DOT__core.__PVT__shx)
                                                   ? vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__10__KET____DOT__core.__VdfgTmp_h586768a0__0
                                                   : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__10__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__11__KET____DOT__rf_aa 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__11__KET____DOT__core.__PVT__ir 
                          >> 0xaU)) | ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__11__KET____DOT__core.__PVT__state))
                                        ? 0x1fU : (0x1fU 
                                                   & ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__11__KET____DOT__core.__PVT__shx)
                                                       ? 
                                                      (0x1fU 
                                                       & (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__11__KET____DOT__core.__PVT__ia))
                                                       : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__11__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__11__KET____DOT__rf_ba 
            = ((0x3e0U & (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__11__KET____DOT__core.__PVT__shx)
                            ? (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__11__KET____DOT__core.__PVT__ir 
                               >> 0xfU) : (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__11__KET____DOT__core.__PVT__ir 
                                           >> 0x14U)) 
                          << 5U)) | (0x1fU & ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__11__KET____DOT__core.__PVT__state))
                                               ? (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__11__KET____DOT__core.__PVT__j)
                                               : ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__11__KET____DOT__core.__PVT__shx)
                                                   ? vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__11__KET____DOT__core.__VdfgTmp_h586768a0__0
                                                   : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__11__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__12__KET____DOT__rf_aa 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__12__KET____DOT__core.__PVT__ir 
                          >> 0xaU)) | ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__12__KET____DOT__core.__PVT__state))
                                        ? 0x1fU : (0x1fU 
                                                   & ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__12__KET____DOT__core.__PVT__shx)
                                                       ? 
                                                      (0x1fU 
                                                       & (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__12__KET____DOT__core.__PVT__ia))
                                                       : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__12__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__12__KET____DOT__rf_ba 
            = ((0x3e0U & (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__12__KET____DOT__core.__PVT__shx)
                            ? (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__12__KET____DOT__core.__PVT__ir 
                               >> 0xfU) : (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__12__KET____DOT__core.__PVT__ir 
                                           >> 0x14U)) 
                          << 5U)) | (0x1fU & ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__12__KET____DOT__core.__PVT__state))
                                               ? (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__12__KET____DOT__core.__PVT__j)
                                               : ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__12__KET____DOT__core.__PVT__shx)
                                                   ? vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__12__KET____DOT__core.__VdfgTmp_h586768a0__0
                                                   : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__12__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__13__KET____DOT__rf_aa 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__13__KET____DOT__core.__PVT__ir 
                          >> 0xaU)) | ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__13__KET____DOT__core.__PVT__state))
                                        ? 0x1fU : (0x1fU 
                                                   & ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__13__KET____DOT__core.__PVT__shx)
                                                       ? 
                                                      (0x1fU 
                                                       & (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__13__KET____DOT__core.__PVT__ia))
                                                       : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__13__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__13__KET____DOT__rf_ba 
            = ((0x3e0U & (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__13__KET____DOT__core.__PVT__shx)
                            ? (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__13__KET____DOT__core.__PVT__ir 
                               >> 0xfU) : (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__13__KET____DOT__core.__PVT__ir 
                                           >> 0x14U)) 
                          << 5U)) | (0x1fU & ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__13__KET____DOT__core.__PVT__state))
                                               ? (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__13__KET____DOT__core.__PVT__j)
                                               : ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__13__KET____DOT__core.__PVT__shx)
                                                   ? vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__13__KET____DOT__core.__VdfgTmp_h586768a0__0
                                                   : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__13__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__14__KET____DOT__rf_aa 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__14__KET____DOT__core.__PVT__ir 
                          >> 0xaU)) | ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__14__KET____DOT__core.__PVT__state))
                                        ? 0x1fU : (0x1fU 
                                                   & ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__14__KET____DOT__core.__PVT__shx)
                                                       ? 
                                                      (0x1fU 
                                                       & (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__14__KET____DOT__core.__PVT__ia))
                                                       : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__14__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__14__KET____DOT__rf_ba 
            = ((0x3e0U & (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__14__KET____DOT__core.__PVT__shx)
                            ? (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__14__KET____DOT__core.__PVT__ir 
                               >> 0xfU) : (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__14__KET____DOT__core.__PVT__ir 
                                           >> 0x14U)) 
                          << 5U)) | (0x1fU & ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__14__KET____DOT__core.__PVT__state))
                                               ? (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__14__KET____DOT__core.__PVT__j)
                                               : ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__14__KET____DOT__core.__PVT__shx)
                                                   ? vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__14__KET____DOT__core.__VdfgTmp_h586768a0__0
                                                   : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__14__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__15__KET____DOT__rf_aa 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__15__KET____DOT__core.__PVT__ir 
                          >> 0xaU)) | ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__15__KET____DOT__core.__PVT__state))
                                        ? 0x1fU : (0x1fU 
                                                   & ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__15__KET____DOT__core.__PVT__shx)
                                                       ? 
                                                      (0x1fU 
                                                       & (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__15__KET____DOT__core.__PVT__ia))
                                                       : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__15__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__15__KET____DOT__rf_ba 
            = ((0x3e0U & (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__15__KET____DOT__core.__PVT__shx)
                            ? (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__15__KET____DOT__core.__PVT__ir 
                               >> 0xfU) : (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__15__KET____DOT__core.__PVT__ir 
                                           >> 0x14U)) 
                          << 5U)) | (0x1fU & ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__15__KET____DOT__core.__PVT__state))
                                               ? (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__15__KET____DOT__core.__PVT__j)
                                               : ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__15__KET____DOT__core.__PVT__shx)
                                                   ? vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__15__KET____DOT__core.__VdfgTmp_h586768a0__0
                                                   : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__15__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__16__KET____DOT__rf_aa 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__16__KET____DOT__core.__PVT__ir 
                          >> 0xaU)) | ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__16__KET____DOT__core.__PVT__state))
                                        ? 0x1fU : (0x1fU 
                                                   & ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__16__KET____DOT__core.__PVT__shx)
                                                       ? 
                                                      (0x1fU 
                                                       & (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__16__KET____DOT__core.__PVT__ia))
                                                       : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__16__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__16__KET____DOT__rf_ba 
            = ((0x3e0U & (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__16__KET____DOT__core.__PVT__shx)
                            ? (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__16__KET____DOT__core.__PVT__ir 
                               >> 0xfU) : (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__16__KET____DOT__core.__PVT__ir 
                                           >> 0x14U)) 
                          << 5U)) | (0x1fU & ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__16__KET____DOT__core.__PVT__state))
                                               ? (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__16__KET____DOT__core.__PVT__j)
                                               : ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__16__KET____DOT__core.__PVT__shx)
                                                   ? vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__16__KET____DOT__core.__VdfgTmp_h586768a0__0
                                                   : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__16__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__17__KET____DOT__rf_aa 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__17__KET____DOT__core.__PVT__ir 
                          >> 0xaU)) | ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__17__KET____DOT__core.__PVT__state))
                                        ? 0x1fU : (0x1fU 
                                                   & ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__17__KET____DOT__core.__PVT__shx)
                                                       ? 
                                                      (0x1fU 
                                                       & (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__17__KET____DOT__core.__PVT__ia))
                                                       : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__17__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__17__KET____DOT__rf_ba 
            = ((0x3e0U & (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__17__KET____DOT__core.__PVT__shx)
                            ? (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__17__KET____DOT__core.__PVT__ir 
                               >> 0xfU) : (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__17__KET____DOT__core.__PVT__ir 
                                           >> 0x14U)) 
                          << 5U)) | (0x1fU & ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__17__KET____DOT__core.__PVT__state))
                                               ? (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__17__KET____DOT__core.__PVT__j)
                                               : ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__17__KET____DOT__core.__PVT__shx)
                                                   ? vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__17__KET____DOT__core.__VdfgTmp_h586768a0__0
                                                   : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__17__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__18__KET____DOT__rf_aa 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__18__KET____DOT__core.__PVT__ir 
                          >> 0xaU)) | ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__18__KET____DOT__core.__PVT__state))
                                        ? 0x1fU : (0x1fU 
                                                   & ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__18__KET____DOT__core.__PVT__shx)
                                                       ? 
                                                      (0x1fU 
                                                       & (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__18__KET____DOT__core.__PVT__ia))
                                                       : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__18__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__18__KET____DOT__rf_ba 
            = ((0x3e0U & (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__18__KET____DOT__core.__PVT__shx)
                            ? (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__18__KET____DOT__core.__PVT__ir 
                               >> 0xfU) : (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__18__KET____DOT__core.__PVT__ir 
                                           >> 0x14U)) 
                          << 5U)) | (0x1fU & ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__18__KET____DOT__core.__PVT__state))
                                               ? (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__18__KET____DOT__core.__PVT__j)
                                               : ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__18__KET____DOT__core.__PVT__shx)
                                                   ? vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__18__KET____DOT__core.__VdfgTmp_h586768a0__0
                                                   : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__18__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__19__KET____DOT__rf_aa 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__19__KET____DOT__core.__PVT__ir 
                          >> 0xaU)) | ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__19__KET____DOT__core.__PVT__state))
                                        ? 0x1fU : (0x1fU 
                                                   & ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__19__KET____DOT__core.__PVT__shx)
                                                       ? 
                                                      (0x1fU 
                                                       & (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__19__KET____DOT__core.__PVT__ia))
                                                       : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__19__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__19__KET____DOT__rf_ba 
            = ((0x3e0U & (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__19__KET____DOT__core.__PVT__shx)
                            ? (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__19__KET____DOT__core.__PVT__ir 
                               >> 0xfU) : (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__19__KET____DOT__core.__PVT__ir 
                                           >> 0x14U)) 
                          << 5U)) | (0x1fU & ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__19__KET____DOT__core.__PVT__state))
                                               ? (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__19__KET____DOT__core.__PVT__j)
                                               : ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__19__KET____DOT__core.__PVT__shx)
                                                   ? vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__19__KET____DOT__core.__VdfgTmp_h586768a0__0
                                                   : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__19__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__20__KET____DOT__rf_aa 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__20__KET____DOT__core.__PVT__ir 
                          >> 0xaU)) | ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__20__KET____DOT__core.__PVT__state))
                                        ? 0x1fU : (0x1fU 
                                                   & ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__20__KET____DOT__core.__PVT__shx)
                                                       ? 
                                                      (0x1fU 
                                                       & (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__20__KET____DOT__core.__PVT__ia))
                                                       : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__20__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__20__KET____DOT__rf_ba 
            = ((0x3e0U & (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__20__KET____DOT__core.__PVT__shx)
                            ? (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__20__KET____DOT__core.__PVT__ir 
                               >> 0xfU) : (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__20__KET____DOT__core.__PVT__ir 
                                           >> 0x14U)) 
                          << 5U)) | (0x1fU & ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__20__KET____DOT__core.__PVT__state))
                                               ? (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__20__KET____DOT__core.__PVT__j)
                                               : ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__20__KET____DOT__core.__PVT__shx)
                                                   ? vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__20__KET____DOT__core.__VdfgTmp_h586768a0__0
                                                   : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__20__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__21__KET____DOT__rf_aa 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__21__KET____DOT__core.__PVT__ir 
                          >> 0xaU)) | ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__21__KET____DOT__core.__PVT__state))
                                        ? 0x1fU : (0x1fU 
                                                   & ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__21__KET____DOT__core.__PVT__shx)
                                                       ? 
                                                      (0x1fU 
                                                       & (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__21__KET____DOT__core.__PVT__ia))
                                                       : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__21__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__21__KET____DOT__rf_ba 
            = ((0x3e0U & (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__21__KET____DOT__core.__PVT__shx)
                            ? (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__21__KET____DOT__core.__PVT__ir 
                               >> 0xfU) : (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__21__KET____DOT__core.__PVT__ir 
                                           >> 0x14U)) 
                          << 5U)) | (0x1fU & ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__21__KET____DOT__core.__PVT__state))
                                               ? (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__21__KET____DOT__core.__PVT__j)
                                               : ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__21__KET____DOT__core.__PVT__shx)
                                                   ? vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__21__KET____DOT__core.__VdfgTmp_h586768a0__0
                                                   : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__21__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__22__KET____DOT__rf_aa 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__22__KET____DOT__core.__PVT__ir 
                          >> 0xaU)) | ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__22__KET____DOT__core.__PVT__state))
                                        ? 0x1fU : (0x1fU 
                                                   & ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__22__KET____DOT__core.__PVT__shx)
                                                       ? 
                                                      (0x1fU 
                                                       & (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__22__KET____DOT__core.__PVT__ia))
                                                       : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__22__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__22__KET____DOT__rf_ba 
            = ((0x3e0U & (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__22__KET____DOT__core.__PVT__shx)
                            ? (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__22__KET____DOT__core.__PVT__ir 
                               >> 0xfU) : (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__22__KET____DOT__core.__PVT__ir 
                                           >> 0x14U)) 
                          << 5U)) | (0x1fU & ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__22__KET____DOT__core.__PVT__state))
                                               ? (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__22__KET____DOT__core.__PVT__j)
                                               : ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__22__KET____DOT__core.__PVT__shx)
                                                   ? vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__22__KET____DOT__core.__VdfgTmp_h586768a0__0
                                                   : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__22__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__23__KET____DOT__rf_aa 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__23__KET____DOT__core.__PVT__ir 
                          >> 0xaU)) | ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__23__KET____DOT__core.__PVT__state))
                                        ? 0x1fU : (0x1fU 
                                                   & ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__23__KET____DOT__core.__PVT__shx)
                                                       ? 
                                                      (0x1fU 
                                                       & (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__23__KET____DOT__core.__PVT__ia))
                                                       : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__23__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__23__KET____DOT__rf_ba 
            = ((0x3e0U & (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__23__KET____DOT__core.__PVT__shx)
                            ? (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__23__KET____DOT__core.__PVT__ir 
                               >> 0xfU) : (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__23__KET____DOT__core.__PVT__ir 
                                           >> 0x14U)) 
                          << 5U)) | (0x1fU & ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__23__KET____DOT__core.__PVT__state))
                                               ? (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__23__KET____DOT__core.__PVT__j)
                                               : ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__23__KET____DOT__core.__PVT__shx)
                                                   ? vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__23__KET____DOT__core.__VdfgTmp_h586768a0__0
                                                   : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__23__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__24__KET____DOT__rf_aa 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__24__KET____DOT__core.__PVT__ir 
                          >> 0xaU)) | ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__24__KET____DOT__core.__PVT__state))
                                        ? 0x1fU : (0x1fU 
                                                   & ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__24__KET____DOT__core.__PVT__shx)
                                                       ? 
                                                      (0x1fU 
                                                       & (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__24__KET____DOT__core.__PVT__ia))
                                                       : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__24__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__24__KET____DOT__rf_ba 
            = ((0x3e0U & (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__24__KET____DOT__core.__PVT__shx)
                            ? (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__24__KET____DOT__core.__PVT__ir 
                               >> 0xfU) : (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__24__KET____DOT__core.__PVT__ir 
                                           >> 0x14U)) 
                          << 5U)) | (0x1fU & ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__24__KET____DOT__core.__PVT__state))
                                               ? (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__24__KET____DOT__core.__PVT__j)
                                               : ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__24__KET____DOT__core.__PVT__shx)
                                                   ? vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__24__KET____DOT__core.__VdfgTmp_h586768a0__0
                                                   : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__24__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__25__KET____DOT__rf_aa 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__25__KET____DOT__core.__PVT__ir 
                          >> 0xaU)) | ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__25__KET____DOT__core.__PVT__state))
                                        ? 0x1fU : (0x1fU 
                                                   & ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__25__KET____DOT__core.__PVT__shx)
                                                       ? 
                                                      (0x1fU 
                                                       & (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__25__KET____DOT__core.__PVT__ia))
                                                       : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__25__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__25__KET____DOT__rf_ba 
            = ((0x3e0U & (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__25__KET____DOT__core.__PVT__shx)
                            ? (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__25__KET____DOT__core.__PVT__ir 
                               >> 0xfU) : (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__25__KET____DOT__core.__PVT__ir 
                                           >> 0x14U)) 
                          << 5U)) | (0x1fU & ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__25__KET____DOT__core.__PVT__state))
                                               ? (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__25__KET____DOT__core.__PVT__j)
                                               : ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__25__KET____DOT__core.__PVT__shx)
                                                   ? vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__25__KET____DOT__core.__VdfgTmp_h586768a0__0
                                                   : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__25__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__26__KET____DOT__rf_aa 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__26__KET____DOT__core.__PVT__ir 
                          >> 0xaU)) | ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__26__KET____DOT__core.__PVT__state))
                                        ? 0x1fU : (0x1fU 
                                                   & ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__26__KET____DOT__core.__PVT__shx)
                                                       ? 
                                                      (0x1fU 
                                                       & (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__26__KET____DOT__core.__PVT__ia))
                                                       : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__26__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__26__KET____DOT__rf_ba 
            = ((0x3e0U & (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__26__KET____DOT__core.__PVT__shx)
                            ? (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__26__KET____DOT__core.__PVT__ir 
                               >> 0xfU) : (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__26__KET____DOT__core.__PVT__ir 
                                           >> 0x14U)) 
                          << 5U)) | (0x1fU & ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__26__KET____DOT__core.__PVT__state))
                                               ? (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__26__KET____DOT__core.__PVT__j)
                                               : ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__26__KET____DOT__core.__PVT__shx)
                                                   ? vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__26__KET____DOT__core.__VdfgTmp_h586768a0__0
                                                   : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__26__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__27__KET____DOT__rf_aa 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__27__KET____DOT__core.__PVT__ir 
                          >> 0xaU)) | ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__27__KET____DOT__core.__PVT__state))
                                        ? 0x1fU : (0x1fU 
                                                   & ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__27__KET____DOT__core.__PVT__shx)
                                                       ? 
                                                      (0x1fU 
                                                       & (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__27__KET____DOT__core.__PVT__ia))
                                                       : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__27__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__27__KET____DOT__rf_ba 
            = ((0x3e0U & (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__27__KET____DOT__core.__PVT__shx)
                            ? (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__27__KET____DOT__core.__PVT__ir 
                               >> 0xfU) : (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__27__KET____DOT__core.__PVT__ir 
                                           >> 0x14U)) 
                          << 5U)) | (0x1fU & ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__27__KET____DOT__core.__PVT__state))
                                               ? (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__27__KET____DOT__core.__PVT__j)
                                               : ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__27__KET____DOT__core.__PVT__shx)
                                                   ? vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__27__KET____DOT__core.__VdfgTmp_h586768a0__0
                                                   : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__27__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__28__KET____DOT__rf_aa 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__28__KET____DOT__core.__PVT__ir 
                          >> 0xaU)) | ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__28__KET____DOT__core.__PVT__state))
                                        ? 0x1fU : (0x1fU 
                                                   & ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__28__KET____DOT__core.__PVT__shx)
                                                       ? 
                                                      (0x1fU 
                                                       & (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__28__KET____DOT__core.__PVT__ia))
                                                       : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__28__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__28__KET____DOT__rf_ba 
            = ((0x3e0U & (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__28__KET____DOT__core.__PVT__shx)
                            ? (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__28__KET____DOT__core.__PVT__ir 
                               >> 0xfU) : (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__28__KET____DOT__core.__PVT__ir 
                                           >> 0x14U)) 
                          << 5U)) | (0x1fU & ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__28__KET____DOT__core.__PVT__state))
                                               ? (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__28__KET____DOT__core.__PVT__j)
                                               : ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__28__KET____DOT__core.__PVT__shx)
                                                   ? vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__28__KET____DOT__core.__VdfgTmp_h586768a0__0
                                                   : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__28__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__29__KET____DOT__rf_aa 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__ir 
                          >> 0xaU)) | ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__state))
                                        ? 0x1fU : (0x1fU 
                                                   & ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__shx)
                                                       ? 
                                                      (0x1fU 
                                                       & (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__ia))
                                                       : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__29__KET____DOT__rf_ba 
            = ((0x3e0U & (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__shx)
                            ? (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__ir 
                               >> 0xfU) : (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__ir 
                                           >> 0x14U)) 
                          << 5U)) | (0x1fU & ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__state))
                                               ? (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__j)
                                               : ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__shx)
                                                   ? vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__VdfgTmp_h586768a0__0
                                                   : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__29__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__30__KET____DOT__rf_aa 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__ir 
                          >> 0xaU)) | ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__state))
                                        ? 0x1fU : (0x1fU 
                                                   & ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__shx)
                                                       ? 
                                                      (0x1fU 
                                                       & (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__ia))
                                                       : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__30__KET____DOT__rf_ba 
            = ((0x3e0U & (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__shx)
                            ? (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__ir 
                               >> 0xfU) : (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__ir 
                                           >> 0x14U)) 
                          << 5U)) | (0x1fU & ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__state))
                                               ? (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__j)
                                               : ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__shx)
                                                   ? vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__VdfgTmp_h586768a0__0
                                                   : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__30__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__31__KET____DOT__rf_aa 
            = ((0x3e0U & (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__ir 
                          >> 0xaU)) | ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__state))
                                        ? 0x1fU : (0x1fU 
                                                   & ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__shx)
                                                       ? 
                                                      (0x1fU 
                                                       & (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__ia))
                                                       : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__k)))));
        vlSelf->tb_sys5__DOT__dut__DOT__slot__BRA__31__KET____DOT__rf_ba 
            = ((0x3e0U & (((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__shx)
                            ? (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__ir 
                               >> 0xfU) : (vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__ir 
                                           >> 0x14U)) 
                          << 5U)) | (0x1fU & ((2U == (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__state))
                                               ? (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__j)
                                               : ((IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__shx)
                                                   ? vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__VdfgTmp_h586768a0__0
                                                   : (IData)(vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__31__KET____DOT__core.__PVT__k)))));
    }
}

VL_ATTR_COLD void Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__0__KET____DOT__core__0(Vtb_sys5_uc_core_v2s__W1* vlSelf);
VL_ATTR_COLD void Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__1__KET____DOT__core__0(Vtb_sys5_uc_core_v2s__W1* vlSelf);
VL_ATTR_COLD void Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__2__KET____DOT__core__0(Vtb_sys5_uc_core_v2s__W1* vlSelf);
VL_ATTR_COLD void Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__3__KET____DOT__core__0(Vtb_sys5_uc_core_v2s__W1* vlSelf);
VL_ATTR_COLD void Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__4__KET____DOT__core__0(Vtb_sys5_uc_core_v2s__W1* vlSelf);
VL_ATTR_COLD void Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__5__KET____DOT__core__0(Vtb_sys5_uc_core_v2s__W1* vlSelf);
VL_ATTR_COLD void Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__6__KET____DOT__core__0(Vtb_sys5_uc_core_v2s__W1* vlSelf);
VL_ATTR_COLD void Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__7__KET____DOT__core__0(Vtb_sys5_uc_core_v2s__W1* vlSelf);
VL_ATTR_COLD void Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__8__KET____DOT__core__0(Vtb_sys5_uc_core_v2s__W1* vlSelf);
VL_ATTR_COLD void Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__9__KET____DOT__core__0(Vtb_sys5_uc_core_v2s__W1* vlSelf);
VL_ATTR_COLD void Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__10__KET____DOT__core__0(Vtb_sys5_uc_core_v2s__W1* vlSelf);
VL_ATTR_COLD void Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__11__KET____DOT__core__0(Vtb_sys5_uc_core_v2s__W1* vlSelf);
VL_ATTR_COLD void Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__12__KET____DOT__core__0(Vtb_sys5_uc_core_v2s__W1* vlSelf);
VL_ATTR_COLD void Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__13__KET____DOT__core__0(Vtb_sys5_uc_core_v2s__W1* vlSelf);
VL_ATTR_COLD void Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__14__KET____DOT__core__0(Vtb_sys5_uc_core_v2s__W1* vlSelf);
VL_ATTR_COLD void Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__15__KET____DOT__core__0(Vtb_sys5_uc_core_v2s__W1* vlSelf);
VL_ATTR_COLD void Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__16__KET____DOT__core__0(Vtb_sys5_uc_core_v2s__W1* vlSelf);
VL_ATTR_COLD void Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__17__KET____DOT__core__0(Vtb_sys5_uc_core_v2s__W1* vlSelf);
VL_ATTR_COLD void Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__18__KET____DOT__core__0(Vtb_sys5_uc_core_v2s__W1* vlSelf);
VL_ATTR_COLD void Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__19__KET____DOT__core__0(Vtb_sys5_uc_core_v2s__W1* vlSelf);
VL_ATTR_COLD void Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__20__KET____DOT__core__0(Vtb_sys5_uc_core_v2s__W1* vlSelf);
VL_ATTR_COLD void Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__21__KET____DOT__core__0(Vtb_sys5_uc_core_v2s__W1* vlSelf);
VL_ATTR_COLD void Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__22__KET____DOT__core__0(Vtb_sys5_uc_core_v2s__W1* vlSelf);
VL_ATTR_COLD void Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__23__KET____DOT__core__0(Vtb_sys5_uc_core_v2s__W1* vlSelf);
VL_ATTR_COLD void Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__24__KET____DOT__core__0(Vtb_sys5_uc_core_v2s__W1* vlSelf);
VL_ATTR_COLD void Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__25__KET____DOT__core__0(Vtb_sys5_uc_core_v2s__W1* vlSelf);
VL_ATTR_COLD void Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__26__KET____DOT__core__0(Vtb_sys5_uc_core_v2s__W1* vlSelf);
VL_ATTR_COLD void Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__27__KET____DOT__core__0(Vtb_sys5_uc_core_v2s__W1* vlSelf);
VL_ATTR_COLD void Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__28__KET____DOT__core__0(Vtb_sys5_uc_core_v2s__W1* vlSelf);
VL_ATTR_COLD void Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__29__KET____DOT__core__0(Vtb_sys5_uc_core_v2s__W1* vlSelf);
VL_ATTR_COLD void Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__30__KET____DOT__core__0(Vtb_sys5_uc_core_v2s__W1* vlSelf);
VL_ATTR_COLD void Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__31__KET____DOT__core__0(Vtb_sys5_uc_core_v2s__W1* vlSelf);

VL_ATTR_COLD void Vtb_sys5___024root___eval_stl(Vtb_sys5___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_sys5__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtb_sys5___024root___eval_stl\n"); );
    // Body
    if ((1ULL & vlSelf->__VstlTriggered.word(0U))) {
        Vtb_sys5___024root___stl_sequent__TOP__0(vlSelf);
        Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__0__KET____DOT__core__0((&vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__0__KET____DOT__core));
        Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__1__KET____DOT__core__0((&vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__1__KET____DOT__core));
        Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__2__KET____DOT__core__0((&vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__2__KET____DOT__core));
        Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__3__KET____DOT__core__0((&vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__3__KET____DOT__core));
        Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__4__KET____DOT__core__0((&vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__4__KET____DOT__core));
        Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__5__KET____DOT__core__0((&vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__5__KET____DOT__core));
        Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__6__KET____DOT__core__0((&vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__6__KET____DOT__core));
        Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__7__KET____DOT__core__0((&vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__7__KET____DOT__core));
        Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__8__KET____DOT__core__0((&vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__8__KET____DOT__core));
        Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__9__KET____DOT__core__0((&vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__9__KET____DOT__core));
        Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__10__KET____DOT__core__0((&vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__10__KET____DOT__core));
        Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__11__KET____DOT__core__0((&vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__11__KET____DOT__core));
        Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__12__KET____DOT__core__0((&vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__12__KET____DOT__core));
        Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__13__KET____DOT__core__0((&vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__13__KET____DOT__core));
        Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__14__KET____DOT__core__0((&vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__14__KET____DOT__core));
        Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__15__KET____DOT__core__0((&vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__15__KET____DOT__core));
        Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__16__KET____DOT__core__0((&vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__16__KET____DOT__core));
        Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__17__KET____DOT__core__0((&vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__17__KET____DOT__core));
        Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__18__KET____DOT__core__0((&vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__18__KET____DOT__core));
        Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__19__KET____DOT__core__0((&vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__19__KET____DOT__core));
        Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__20__KET____DOT__core__0((&vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__20__KET____DOT__core));
        Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__21__KET____DOT__core__0((&vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__21__KET____DOT__core));
        Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__22__KET____DOT__core__0((&vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__22__KET____DOT__core));
        Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__23__KET____DOT__core__0((&vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__23__KET____DOT__core));
        Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__24__KET____DOT__core__0((&vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__24__KET____DOT__core));
        Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__25__KET____DOT__core__0((&vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__25__KET____DOT__core));
        Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__26__KET____DOT__core__0((&vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__26__KET____DOT__core));
        Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__27__KET____DOT__core__0((&vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__27__KET____DOT__core));
        Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__28__KET____DOT__core__0((&vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__28__KET____DOT__core));
        Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__29__KET____DOT__core__0((&vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__29__KET____DOT__core));
        Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__30__KET____DOT__core__0((&vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__30__KET____DOT__core));
        Vtb_sys5_uc_core_v2s__W1___stl_sequent__TOP__tb_sys5__DOT__dut__DOT__slot__BRA__31__KET____DOT__core__0((&vlSymsp->TOP__tb_sys5__DOT__dut__DOT__slot__BRA__31__KET____DOT__core));
        Vtb_sys5___024root___stl_sequent__TOP__1(vlSelf);
    }
}
