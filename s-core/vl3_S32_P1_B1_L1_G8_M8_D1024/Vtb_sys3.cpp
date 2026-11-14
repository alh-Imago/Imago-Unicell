// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Model implementation (design independent parts)

#include "Vtb_sys3__pch.h"

//============================================================
// Constructors

Vtb_sys3::Vtb_sys3(VerilatedContext* _vcontextp__, const char* _vcname__)
    : VerilatedModel{*_vcontextp__}
    , vlSymsp{new Vtb_sys3__Syms(contextp(), _vcname__, this)}
    , __PVT__tb_sys3__DOT__dut__DOT__slot__BRA__0__KET____DOT__core{vlSymsp->TOP.__PVT__tb_sys3__DOT__dut__DOT__slot__BRA__0__KET____DOT__core}
    , __PVT__tb_sys3__DOT__dut__DOT__slot__BRA__1__KET____DOT__core{vlSymsp->TOP.__PVT__tb_sys3__DOT__dut__DOT__slot__BRA__1__KET____DOT__core}
    , __PVT__tb_sys3__DOT__dut__DOT__slot__BRA__2__KET____DOT__core{vlSymsp->TOP.__PVT__tb_sys3__DOT__dut__DOT__slot__BRA__2__KET____DOT__core}
    , __PVT__tb_sys3__DOT__dut__DOT__slot__BRA__3__KET____DOT__core{vlSymsp->TOP.__PVT__tb_sys3__DOT__dut__DOT__slot__BRA__3__KET____DOT__core}
    , __PVT__tb_sys3__DOT__dut__DOT__slot__BRA__4__KET____DOT__core{vlSymsp->TOP.__PVT__tb_sys3__DOT__dut__DOT__slot__BRA__4__KET____DOT__core}
    , __PVT__tb_sys3__DOT__dut__DOT__slot__BRA__5__KET____DOT__core{vlSymsp->TOP.__PVT__tb_sys3__DOT__dut__DOT__slot__BRA__5__KET____DOT__core}
    , __PVT__tb_sys3__DOT__dut__DOT__slot__BRA__6__KET____DOT__core{vlSymsp->TOP.__PVT__tb_sys3__DOT__dut__DOT__slot__BRA__6__KET____DOT__core}
    , __PVT__tb_sys3__DOT__dut__DOT__slot__BRA__7__KET____DOT__core{vlSymsp->TOP.__PVT__tb_sys3__DOT__dut__DOT__slot__BRA__7__KET____DOT__core}
    , __PVT__tb_sys3__DOT__dut__DOT__slot__BRA__8__KET____DOT__core{vlSymsp->TOP.__PVT__tb_sys3__DOT__dut__DOT__slot__BRA__8__KET____DOT__core}
    , __PVT__tb_sys3__DOT__dut__DOT__slot__BRA__9__KET____DOT__core{vlSymsp->TOP.__PVT__tb_sys3__DOT__dut__DOT__slot__BRA__9__KET____DOT__core}
    , __PVT__tb_sys3__DOT__dut__DOT__slot__BRA__10__KET____DOT__core{vlSymsp->TOP.__PVT__tb_sys3__DOT__dut__DOT__slot__BRA__10__KET____DOT__core}
    , __PVT__tb_sys3__DOT__dut__DOT__slot__BRA__11__KET____DOT__core{vlSymsp->TOP.__PVT__tb_sys3__DOT__dut__DOT__slot__BRA__11__KET____DOT__core}
    , __PVT__tb_sys3__DOT__dut__DOT__slot__BRA__12__KET____DOT__core{vlSymsp->TOP.__PVT__tb_sys3__DOT__dut__DOT__slot__BRA__12__KET____DOT__core}
    , __PVT__tb_sys3__DOT__dut__DOT__slot__BRA__13__KET____DOT__core{vlSymsp->TOP.__PVT__tb_sys3__DOT__dut__DOT__slot__BRA__13__KET____DOT__core}
    , __PVT__tb_sys3__DOT__dut__DOT__slot__BRA__14__KET____DOT__core{vlSymsp->TOP.__PVT__tb_sys3__DOT__dut__DOT__slot__BRA__14__KET____DOT__core}
    , __PVT__tb_sys3__DOT__dut__DOT__slot__BRA__15__KET____DOT__core{vlSymsp->TOP.__PVT__tb_sys3__DOT__dut__DOT__slot__BRA__15__KET____DOT__core}
    , __PVT__tb_sys3__DOT__dut__DOT__slot__BRA__16__KET____DOT__core{vlSymsp->TOP.__PVT__tb_sys3__DOT__dut__DOT__slot__BRA__16__KET____DOT__core}
    , __PVT__tb_sys3__DOT__dut__DOT__slot__BRA__17__KET____DOT__core{vlSymsp->TOP.__PVT__tb_sys3__DOT__dut__DOT__slot__BRA__17__KET____DOT__core}
    , __PVT__tb_sys3__DOT__dut__DOT__slot__BRA__18__KET____DOT__core{vlSymsp->TOP.__PVT__tb_sys3__DOT__dut__DOT__slot__BRA__18__KET____DOT__core}
    , __PVT__tb_sys3__DOT__dut__DOT__slot__BRA__19__KET____DOT__core{vlSymsp->TOP.__PVT__tb_sys3__DOT__dut__DOT__slot__BRA__19__KET____DOT__core}
    , __PVT__tb_sys3__DOT__dut__DOT__slot__BRA__20__KET____DOT__core{vlSymsp->TOP.__PVT__tb_sys3__DOT__dut__DOT__slot__BRA__20__KET____DOT__core}
    , __PVT__tb_sys3__DOT__dut__DOT__slot__BRA__21__KET____DOT__core{vlSymsp->TOP.__PVT__tb_sys3__DOT__dut__DOT__slot__BRA__21__KET____DOT__core}
    , __PVT__tb_sys3__DOT__dut__DOT__slot__BRA__22__KET____DOT__core{vlSymsp->TOP.__PVT__tb_sys3__DOT__dut__DOT__slot__BRA__22__KET____DOT__core}
    , __PVT__tb_sys3__DOT__dut__DOT__slot__BRA__23__KET____DOT__core{vlSymsp->TOP.__PVT__tb_sys3__DOT__dut__DOT__slot__BRA__23__KET____DOT__core}
    , __PVT__tb_sys3__DOT__dut__DOT__slot__BRA__24__KET____DOT__core{vlSymsp->TOP.__PVT__tb_sys3__DOT__dut__DOT__slot__BRA__24__KET____DOT__core}
    , __PVT__tb_sys3__DOT__dut__DOT__slot__BRA__25__KET____DOT__core{vlSymsp->TOP.__PVT__tb_sys3__DOT__dut__DOT__slot__BRA__25__KET____DOT__core}
    , __PVT__tb_sys3__DOT__dut__DOT__slot__BRA__26__KET____DOT__core{vlSymsp->TOP.__PVT__tb_sys3__DOT__dut__DOT__slot__BRA__26__KET____DOT__core}
    , __PVT__tb_sys3__DOT__dut__DOT__slot__BRA__27__KET____DOT__core{vlSymsp->TOP.__PVT__tb_sys3__DOT__dut__DOT__slot__BRA__27__KET____DOT__core}
    , __PVT__tb_sys3__DOT__dut__DOT__slot__BRA__28__KET____DOT__core{vlSymsp->TOP.__PVT__tb_sys3__DOT__dut__DOT__slot__BRA__28__KET____DOT__core}
    , __PVT__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core{vlSymsp->TOP.__PVT__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core}
    , __PVT__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core{vlSymsp->TOP.__PVT__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core}
    , __PVT__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core{vlSymsp->TOP.__PVT__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core}
    , rootp{&(vlSymsp->TOP)}
{
    // Register model with the context
    contextp()->addModel(this);
}

Vtb_sys3::Vtb_sys3(const char* _vcname__)
    : Vtb_sys3(Verilated::threadContextp(), _vcname__)
{
}

//============================================================
// Destructor

Vtb_sys3::~Vtb_sys3() {
    delete vlSymsp;
}

//============================================================
// Evaluation function

#ifdef VL_DEBUG
void Vtb_sys3___024root___eval_debug_assertions(Vtb_sys3___024root* vlSelf);
#endif  // VL_DEBUG
void Vtb_sys3___024root___eval_static(Vtb_sys3___024root* vlSelf);
void Vtb_sys3___024root___eval_initial(Vtb_sys3___024root* vlSelf);
void Vtb_sys3___024root___eval_settle(Vtb_sys3___024root* vlSelf);
void Vtb_sys3___024root___eval(Vtb_sys3___024root* vlSelf);

void Vtb_sys3::eval_step() {
    VL_DEBUG_IF(VL_DBG_MSGF("+++++TOP Evaluate Vtb_sys3::eval_step\n"); );
#ifdef VL_DEBUG
    // Debug assertions
    Vtb_sys3___024root___eval_debug_assertions(&(vlSymsp->TOP));
#endif  // VL_DEBUG
    vlSymsp->__Vm_deleter.deleteAll();
    if (VL_UNLIKELY(!vlSymsp->__Vm_didInit)) {
        vlSymsp->__Vm_didInit = true;
        VL_DEBUG_IF(VL_DBG_MSGF("+ Initial\n"););
        Vtb_sys3___024root___eval_static(&(vlSymsp->TOP));
        Vtb_sys3___024root___eval_initial(&(vlSymsp->TOP));
        Vtb_sys3___024root___eval_settle(&(vlSymsp->TOP));
    }
    VL_DEBUG_IF(VL_DBG_MSGF("+ Eval\n"););
    Vtb_sys3___024root___eval(&(vlSymsp->TOP));
    // Evaluate cleanup
    Verilated::endOfEval(vlSymsp->__Vm_evalMsgQp);
}

//============================================================
// Events and timing
bool Vtb_sys3::eventsPending() { return !vlSymsp->TOP.__VdlySched.empty(); }

uint64_t Vtb_sys3::nextTimeSlot() { return vlSymsp->TOP.__VdlySched.nextTimeSlot(); }

//============================================================
// Utilities

const char* Vtb_sys3::name() const {
    return vlSymsp->name();
}

//============================================================
// Invoke final blocks

void Vtb_sys3___024root___eval_final(Vtb_sys3___024root* vlSelf);

VL_ATTR_COLD void Vtb_sys3::final() {
    Vtb_sys3___024root___eval_final(&(vlSymsp->TOP));
}

//============================================================
// Implementations of abstract methods from VerilatedModel

const char* Vtb_sys3::hierName() const { return vlSymsp->name(); }
const char* Vtb_sys3::modelName() const { return "Vtb_sys3"; }
unsigned Vtb_sys3::threads() const { return 1; }
void Vtb_sys3::prepareClone() const { contextp()->prepareClone(); }
void Vtb_sys3::atClone() const {
    contextp()->threadPoolpOnClone();
}

//============================================================
// Trace configuration

VL_ATTR_COLD void Vtb_sys3::trace(VerilatedVcdC* tfp, int levels, int options) {
    vl_fatal(__FILE__, __LINE__, __FILE__,"'Vtb_sys3::trace()' called on model that was Verilated without --trace option");
}
