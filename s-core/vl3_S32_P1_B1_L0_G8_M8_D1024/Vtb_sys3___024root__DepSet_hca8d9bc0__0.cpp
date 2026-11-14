// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design implementation internals
// See Vtb_sys3.h for the primary calling header

#include "Vtb_sys3__pch.h"
#include "Vtb_sys3___024root.h"

VL_ATTR_COLD void Vtb_sys3___024root___eval_initial__TOP(Vtb_sys3___024root* vlSelf);
VlCoroutine Vtb_sys3___024root___eval_initial__TOP__Vtiming__0(Vtb_sys3___024root* vlSelf);
VlCoroutine Vtb_sys3___024root___eval_initial__TOP__Vtiming__1(Vtb_sys3___024root* vlSelf);

void Vtb_sys3___024root___eval_initial(Vtb_sys3___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_sys3__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtb_sys3___024root___eval_initial\n"); );
    // Body
    Vtb_sys3___024root___eval_initial__TOP(vlSelf);
    Vtb_sys3___024root___eval_initial__TOP__Vtiming__0(vlSelf);
    Vtb_sys3___024root___eval_initial__TOP__Vtiming__1(vlSelf);
    vlSelf->__Vtrigprevexpr___TOP__tb_sys3__DOT__clk__0 
        = vlSelf->tb_sys3__DOT__clk;
}

VL_INLINE_OPT VlCoroutine Vtb_sys3___024root___eval_initial__TOP__Vtiming__0(Vtb_sys3___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_sys3__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtb_sys3___024root___eval_initial__TOP__Vtiming__0\n"); );
    // Init
    IData/*31:0*/ tb_sys3__DOT__i;
    tb_sys3__DOT__i = 0;
    IData/*31:0*/ tb_sys3__DOT__fd;
    tb_sys3__DOT__fd = 0;
    VlWide<3>/*95:0*/ __Vtemp_1;
    VlWide<3>/*95:0*/ __Vtemp_2;
    VlWide<3>/*95:0*/ __Vtemp_5;
    // Body
    vlSelf->tb_sys3__DOT__nxt = 0U;
    vlSelf->tb_sys3__DOT__en = 0U;
    vlSelf->tb_sys3__DOT__epend = 0U;
    vlSelf->tb_sys3__DOT__ecur = 0U;
    vlSelf->tb_sys3__DOT__NE = 0U;
    if (VL_UNLIKELY((! VL_VALUEPLUSARGS_INW(1024, std::string{"prog=%s"}, 
                                            vlSelf->tb_sys3__DOT__progname)))) {
        VL_WRITEF("need +prog\n");
        VL_FINISH_MT("/home/claude/imago-unicell/s-core/tb_sys3.v", 61, "");
    }
    if (VL_UNLIKELY((! VL_VALUEPLUSARGS_INW(1024, std::string{"tasks=%s"}, 
                                            vlSelf->tb_sys3__DOT__taskname)))) {
        VL_WRITEF("need +tasks\n");
        VL_FINISH_MT("/home/claude/imago-unicell/s-core/tb_sys3.v", 62, "");
    }
    __Vtemp_1[0U] = 0x733d2564U;
    __Vtemp_1[1U] = 0x7461736bU;
    __Vtemp_1[2U] = 0x6eU;
    if (VL_UNLIKELY((! VL_VALUEPLUSARGS_INI(32, VL_CVT_PACK_STR_NW(3, __Vtemp_1), 
                                            vlSelf->tb_sys3__DOT__NT)))) {
        VL_WRITEF("need +ntasks\n");
        VL_FINISH_MT("/home/claude/imago-unicell/s-core/tb_sys3.v", 63, "");
    }
    if (VL_UNLIKELY((! VL_VALUEPLUSARGS_INW(1024, std::string{"out=%s"}, 
                                            vlSelf->tb_sys3__DOT__outname)))) {
        VL_WRITEF("need +out\n");
        VL_FINISH_MT("/home/claude/imago-unicell/s-core/tb_sys3.v", 64, "");
    }
    __Vtemp_2[0U] = 0x733d2564U;
    __Vtemp_2[1U] = 0x76656e74U;
    __Vtemp_2[2U] = 0x6e65U;
    (void)VL_VALUEPLUSARGS_INI(32, VL_CVT_PACK_STR_NW(3, __Vtemp_2), 
                               vlSelf->tb_sys3__DOT__NE);
    tb_sys3__DOT__i = 0U;
    while (VL_LTS_III(32, tb_sys3__DOT__i, vlSelf->tb_sys3__DOT__NE)) {
        vlSelf->tb_sys3__DOT__evt_time[(0xffU & tb_sys3__DOT__i)] 
            = ((IData)(0x190U) + VL_MULS_III(32, (IData)(0x2ddU), tb_sys3__DOT__i));
        vlSelf->tb_sys3__DOT__evt_line[(0xffU & tb_sys3__DOT__i)] 
            = (0xffU & ((IData)(0x40U) + VL_MODDIVS_III(32, 
                                                        VL_MULS_III(32, (IData)(0x25U), tb_sys3__DOT__i), (IData)(0xc0U))));
        vlSelf->tb_sys3__DOT__evt_data[(0xffU & tb_sys3__DOT__i)] 
            = ((IData)(0xa5a50000U) + ((IData)(0x11U) 
                                       * tb_sys3__DOT__i));
        tb_sys3__DOT__i = ((IData)(1U) + tb_sys3__DOT__i);
    }
    tb_sys3__DOT__i = 0U;
    while (VL_GTS_III(32, 0x2000U, tb_sys3__DOT__i)) {
        vlSelf->tb_sys3__DOT__dut__DOT__imem[(0x1fffU 
                                              & tb_sys3__DOT__i)] = 0U;
        tb_sys3__DOT__i = ((IData)(1U) + tb_sys3__DOT__i);
    }
    VL_READMEM_N(true, 32, 8192, 0, VL_CVT_PACK_STR_NW(32, vlSelf->tb_sys3__DOT__progname)
                 ,  &(vlSelf->tb_sys3__DOT__dut__DOT__imem)
                 , 0, ~0ULL);
    VL_READMEM_N(true, 32, 768, 0, VL_CVT_PACK_STR_NW(32, vlSelf->tb_sys3__DOT__taskname)
                 ,  &(vlSelf->tb_sys3__DOT__tl), 0, ~0ULL);
    co_await vlSelf->__VtrigSched_h38036357__0.trigger(0U, 
                                                       nullptr, 
                                                       "@(posedge tb_sys3.clk)", 
                                                       "/home/claude/imago-unicell/s-core/tb_sys3.v", 
                                                       74);
    co_await vlSelf->__VtrigSched_h38036357__0.trigger(0U, 
                                                       nullptr, 
                                                       "@(posedge tb_sys3.clk)", 
                                                       "/home/claude/imago-unicell/s-core/tb_sys3.v", 
                                                       74);
    co_await vlSelf->__VtrigSched_h38036357__0.trigger(0U, 
                                                       nullptr, 
                                                       "@(posedge tb_sys3.clk)", 
                                                       "/home/claude/imago-unicell/s-core/tb_sys3.v", 
                                                       74);
    co_await vlSelf->__VtrigSched_h38036357__0.trigger(0U, 
                                                       nullptr, 
                                                       "@(posedge tb_sys3.clk)", 
                                                       "/home/claude/imago-unicell/s-core/tb_sys3.v", 
                                                       74);
    vlSelf->tb_sys3__DOT__rst = 0U;
    __Vtemp_5[0U] = 0x6e3d2573U;
    __Vtemp_5[1U] = 0x726f6669U;
    __Vtemp_5[2U] = 0x70U;
    if (VL_UNLIKELY(VL_VALUEPLUSARGS_INW(1024, VL_CVT_PACK_STR_NW(3, __Vtemp_5), 
                                         vlSelf->tb_sys3__DOT__profname))) {
        co_await vlSelf->__VtrigSched_h3803650a__0.trigger(0U, 
                                                           nullptr, 
                                                           "@(negedge tb_sys3.clk)", 
                                                           "/home/claude/imago-unicell/s-core/tb_sys3.v", 
                                                           77);
        VL_READMEM_N(true, 25, 512, 0, VL_CVT_PACK_STR_NW(32, vlSelf->tb_sys3__DOT__profname)
                     ,  &(vlSelf->tb_sys3__DOT__proftmp)
                     , 0, ~0ULL);
        tb_sys3__DOT__i = 0U;
        while (VL_GTS_III(32, 0x200U, tb_sys3__DOT__i)) {
            vlSelf->tb_sys3__DOT__dut__DOT__prof[(0x1ffU 
                                                  & tb_sys3__DOT__i)] 
                = vlSelf->tb_sys3__DOT__proftmp[(0x1ffU 
                                                 & tb_sys3__DOT__i)];
            tb_sys3__DOT__i = ((IData)(1U) + tb_sys3__DOT__i);
        }
    }
    while ((((vlSelf->tb_sys3__DOT__dut__DOT__done_count 
              < vlSelf->tb_sys3__DOT__NT) | (vlSelf->tb_sys3__DOT__dut__DOT__ev_cnt 
                                             < vlSelf->tb_sys3__DOT__NE)) 
            & (0x2faf080U > vlSelf->tb_sys3__DOT__dut__DOT__cyc))) {
        co_await vlSelf->__VtrigSched_h38036357__0.trigger(0U, 
                                                           nullptr, 
                                                           "@(posedge tb_sys3.clk)", 
                                                           "/home/claude/imago-unicell/s-core/tb_sys3.v", 
                                                           81);
    }
    co_await vlSelf->__VtrigSched_h38036357__0.trigger(0U, 
                                                       nullptr, 
                                                       "@(posedge tb_sys3.clk)", 
                                                       "/home/claude/imago-unicell/s-core/tb_sys3.v", 
                                                       82);
    co_await vlSelf->__VtrigSched_h38036357__0.trigger(0U, 
                                                       nullptr, 
                                                       "@(posedge tb_sys3.clk)", 
                                                       "/home/claude/imago-unicell/s-core/tb_sys3.v", 
                                                       82);
    tb_sys3__DOT__fd = VL_FOPEN_NN(VL_CVT_PACK_STR_NW(32, vlSelf->tb_sys3__DOT__outname)
                                   , std::string{"w"});
    ;
    VL_FWRITEF(tb_sys3__DOT__fd,"total_cycles %0#\nbusy_slice_cycles %0#\nwaste_blocked %0#\nwaste_tail %0#\nsearch_cycles %0#\nlaunch_err %0#\ndispatches %0#\nS 32\ncompleted %0#\nevents %0#\n",
               32,vlSelf->tb_sys3__DOT__dut__DOT__cyc,
               64,vlSelf->tb_sys3__DOT__dut__DOT__busy_slice_cycles,
               64,vlSelf->tb_sys3__DOT__dut__DOT__waste_blocked,
               64,vlSelf->tb_sys3__DOT__dut__DOT__waste_tail,
               64,vlSelf->tb_sys3__DOT__dut__DOT__search_cycles,
               32,vlSelf->tb_sys3__DOT__dut__DOT__launch_err,
               32,vlSelf->tb_sys3__DOT__dut__DOT__dispatches,
               32,vlSelf->tb_sys3__DOT__dut__DOT__done_count,
               32,vlSelf->tb_sys3__DOT__dut__DOT__ev_cnt);
    tb_sys3__DOT__i = 0U;
    while (VL_LTS_III(32, tb_sys3__DOT__i, vlSelf->tb_sys3__DOT__NT)) {
        VL_FWRITEF(tb_sys3__DOT__fd,"c %0d %0# %0# %0# %0# %0# %0# %0# %0# %0# %0#\n",
                   32,tb_sys3__DOT__i,3,vlSelf->tb_sys3__DOT__dut__DOT__t_lw
                   [(0xffU & tb_sys3__DOT__i)],1,vlSelf->tb_sys3__DOT__dut__DOT__t_crit
                   [(0xffU & tb_sys3__DOT__i)],32,vlSelf->tb_sys3__DOT__dut__DOT__t_arr
                   [(0xffU & tb_sys3__DOT__i)],32,vlSelf->tb_sys3__DOT__dut__DOT__t_start
                   [(0xffU & tb_sys3__DOT__i)],32,vlSelf->tb_sys3__DOT__dut__DOT__t_end
                   [(0xffU & tb_sys3__DOT__i)],32,vlSelf->tb_sys3__DOT__dut__DOT__t_a0
                   [(0xffU & tb_sys3__DOT__i)],1,vlSelf->tb_sys3__DOT__dut__DOT__t_trap
                   [(0xffU & tb_sys3__DOT__i)],2,vlSelf->tb_sys3__DOT__dut__DOT__t_state
                   [(0xffU & tb_sys3__DOT__i)],6,vlSelf->tb_sys3__DOT__dut__DOT__t_slot
                   [(0xffU & tb_sys3__DOT__i)],25,vlSelf->tb_sys3__DOT__dut__DOT__t_pred
                   [(0xffU & tb_sys3__DOT__i)]);
        tb_sys3__DOT__i = ((IData)(1U) + tb_sys3__DOT__i);
    }
    tb_sys3__DOT__i = 0U;
    while ((tb_sys3__DOT__i < vlSelf->tb_sys3__DOT__dut__DOT__ev_cnt)) {
        VL_FWRITEF(tb_sys3__DOT__fd,"e %0# %0# %0#\n",
                   8,vlSelf->tb_sys3__DOT__dut__DOT__ev_id
                   [(0xffU & tb_sys3__DOT__i)],32,vlSelf->tb_sys3__DOT__dut__DOT__ev_data
                   [(0xffU & tb_sys3__DOT__i)],32,vlSelf->tb_sys3__DOT__dut__DOT__ev_cyc
                   [(0xffU & tb_sys3__DOT__i)]);
        tb_sys3__DOT__i = ((IData)(1U) + tb_sys3__DOT__i);
    }
    tb_sys3__DOT__i = 0U;
    while (VL_LTS_III(32, tb_sys3__DOT__i, vlSelf->tb_sys3__DOT__NE)) {
        VL_FWRITEF(tb_sys3__DOT__fd,"x %0# %0# %0#\n",
                   8,vlSelf->tb_sys3__DOT__evt_line
                   [(0xffU & tb_sys3__DOT__i)],32,vlSelf->tb_sys3__DOT__evt_data
                   [(0xffU & tb_sys3__DOT__i)],32,vlSelf->tb_sys3__DOT__evt_setcyc
                   [(0xffU & tb_sys3__DOT__i)]);
        tb_sys3__DOT__i = ((IData)(1U) + tb_sys3__DOT__i);
    }
    tb_sys3__DOT__i = 0U;
    while (VL_GTS_III(32, 0x200U, tb_sys3__DOT__i)) {
        VL_FWRITEF(tb_sys3__DOT__fd,"p %0d %0#\n",32,
                   tb_sys3__DOT__i,25,vlSelf->tb_sys3__DOT__dut__DOT__prof
                   [(0x1ffU & tb_sys3__DOT__i)]);
        tb_sys3__DOT__i = ((IData)(1U) + tb_sys3__DOT__i);
    }
    VL_FCLOSE_I(tb_sys3__DOT__fd); VL_FINISH_MT("/home/claude/imago-unicell/s-core/tb_sys3.v", 103, "");
}

VL_INLINE_OPT VlCoroutine Vtb_sys3___024root___eval_initial__TOP__Vtiming__1(Vtb_sys3___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_sys3__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtb_sys3___024root___eval_initial__TOP__Vtiming__1\n"); );
    // Body
    while (1U) {
        co_await vlSelf->__VdlySched.delay(0x1388ULL, 
                                           nullptr, 
                                           "/home/claude/imago-unicell/s-core/tb_sys3.v", 
                                           13);
        vlSelf->tb_sys3__DOT__clk = (1U & (~ (IData)(vlSelf->tb_sys3__DOT__clk)));
    }
}

void Vtb_sys3___024root___act_comb__TOP__0(Vtb_sys3___024root* vlSelf);

void Vtb_sys3___024root___eval_act(Vtb_sys3___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_sys3__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtb_sys3___024root___eval_act\n"); );
    // Body
    if ((3ULL & vlSelf->__VactTriggered.word(0U))) {
        Vtb_sys3___024root___act_comb__TOP__0(vlSelf);
    }
}

void Vtb_sys3___024root___timing_resume(Vtb_sys3___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_sys3__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtb_sys3___024root___timing_resume\n"); );
    // Body
    if ((1ULL & vlSelf->__VactTriggered.word(0U))) {
        vlSelf->__VtrigSched_h38036357__0.resume("@(posedge tb_sys3.clk)");
    }
    if ((2ULL & vlSelf->__VactTriggered.word(0U))) {
        vlSelf->__VtrigSched_h3803650a__0.resume("@(negedge tb_sys3.clk)");
    }
    if ((4ULL & vlSelf->__VactTriggered.word(0U))) {
        vlSelf->__VdlySched.resume();
    }
}

void Vtb_sys3___024root___timing_commit(Vtb_sys3___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_sys3__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtb_sys3___024root___timing_commit\n"); );
    // Body
    if ((! (1ULL & vlSelf->__VactTriggered.word(0U)))) {
        vlSelf->__VtrigSched_h38036357__0.commit("@(posedge tb_sys3.clk)");
    }
    if ((! (2ULL & vlSelf->__VactTriggered.word(0U)))) {
        vlSelf->__VtrigSched_h3803650a__0.commit("@(negedge tb_sys3.clk)");
    }
}

void Vtb_sys3___024root___eval_triggers__act(Vtb_sys3___024root* vlSelf);

bool Vtb_sys3___024root___eval_phase__act(Vtb_sys3___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_sys3__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtb_sys3___024root___eval_phase__act\n"); );
    // Init
    VlTriggerVec<3> __VpreTriggered;
    CData/*0:0*/ __VactExecute;
    // Body
    Vtb_sys3___024root___eval_triggers__act(vlSelf);
    Vtb_sys3___024root___timing_commit(vlSelf);
    __VactExecute = vlSelf->__VactTriggered.any();
    if (__VactExecute) {
        __VpreTriggered.andNot(vlSelf->__VactTriggered, vlSelf->__VnbaTriggered);
        vlSelf->__VnbaTriggered.thisOr(vlSelf->__VactTriggered);
        Vtb_sys3___024root___timing_resume(vlSelf);
        Vtb_sys3___024root___eval_act(vlSelf);
    }
    return (__VactExecute);
}

void Vtb_sys3___024root___eval_nba(Vtb_sys3___024root* vlSelf);

bool Vtb_sys3___024root___eval_phase__nba(Vtb_sys3___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_sys3__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtb_sys3___024root___eval_phase__nba\n"); );
    // Init
    CData/*0:0*/ __VnbaExecute;
    // Body
    __VnbaExecute = vlSelf->__VnbaTriggered.any();
    if (__VnbaExecute) {
        Vtb_sys3___024root___eval_nba(vlSelf);
        vlSelf->__VnbaTriggered.clear();
    }
    return (__VnbaExecute);
}

#ifdef VL_DEBUG
VL_ATTR_COLD void Vtb_sys3___024root___dump_triggers__nba(Vtb_sys3___024root* vlSelf);
#endif  // VL_DEBUG
#ifdef VL_DEBUG
VL_ATTR_COLD void Vtb_sys3___024root___dump_triggers__act(Vtb_sys3___024root* vlSelf);
#endif  // VL_DEBUG

void Vtb_sys3___024root___eval(Vtb_sys3___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_sys3__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtb_sys3___024root___eval\n"); );
    // Init
    IData/*31:0*/ __VnbaIterCount;
    CData/*0:0*/ __VnbaContinue;
    // Body
    __VnbaIterCount = 0U;
    __VnbaContinue = 1U;
    while (__VnbaContinue) {
        if (VL_UNLIKELY((0x64U < __VnbaIterCount))) {
#ifdef VL_DEBUG
            Vtb_sys3___024root___dump_triggers__nba(vlSelf);
#endif
            VL_FATAL_MT("/home/claude/imago-unicell/s-core/tb_sys3.v", 4, "", "NBA region did not converge.");
        }
        __VnbaIterCount = ((IData)(1U) + __VnbaIterCount);
        __VnbaContinue = 0U;
        vlSelf->__VactIterCount = 0U;
        vlSelf->__VactContinue = 1U;
        while (vlSelf->__VactContinue) {
            if (VL_UNLIKELY((0x64U < vlSelf->__VactIterCount))) {
#ifdef VL_DEBUG
                Vtb_sys3___024root___dump_triggers__act(vlSelf);
#endif
                VL_FATAL_MT("/home/claude/imago-unicell/s-core/tb_sys3.v", 4, "", "Active region did not converge.");
            }
            vlSelf->__VactIterCount = ((IData)(1U) 
                                       + vlSelf->__VactIterCount);
            vlSelf->__VactContinue = 0U;
            if (Vtb_sys3___024root___eval_phase__act(vlSelf)) {
                vlSelf->__VactContinue = 1U;
            }
        }
        if (Vtb_sys3___024root___eval_phase__nba(vlSelf)) {
            __VnbaContinue = 1U;
        }
    }
}

#ifdef VL_DEBUG
void Vtb_sys3___024root___eval_debug_assertions(Vtb_sys3___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    Vtb_sys3__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtb_sys3___024root___eval_debug_assertions\n"); );
}
#endif  // VL_DEBUG
