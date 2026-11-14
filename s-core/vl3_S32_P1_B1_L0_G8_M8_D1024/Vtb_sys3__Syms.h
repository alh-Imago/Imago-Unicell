// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Symbol table internal header
//
// Internal details; most calling programs do not need this header,
// unless using verilator public meta comments.

#ifndef VERILATED_VTB_SYS3__SYMS_H_
#define VERILATED_VTB_SYS3__SYMS_H_  // guard

#include "verilated.h"

// INCLUDE MODEL CLASS

#include "Vtb_sys3.h"

// INCLUDE MODULE CLASSES
#include "Vtb_sys3___024root.h"
#include "Vtb_sys3_uc_core_rw.h"

// SYMS CLASS (contains all model state)
class alignas(VL_CACHE_LINE_BYTES)Vtb_sys3__Syms final : public VerilatedSyms {
  public:
    // INTERNAL STATE
    Vtb_sys3* const __Vm_modelp;
    VlDeleter __Vm_deleter;
    bool __Vm_didInit = false;

    // MODULE INSTANCE STATE
    Vtb_sys3___024root             TOP;
    Vtb_sys3_uc_core_rw            TOP__tb_sys3__DOT__dut__DOT__slot__BRA__0__KET____DOT__core;
    Vtb_sys3_uc_core_rw            TOP__tb_sys3__DOT__dut__DOT__slot__BRA__10__KET____DOT__core;
    Vtb_sys3_uc_core_rw            TOP__tb_sys3__DOT__dut__DOT__slot__BRA__11__KET____DOT__core;
    Vtb_sys3_uc_core_rw            TOP__tb_sys3__DOT__dut__DOT__slot__BRA__12__KET____DOT__core;
    Vtb_sys3_uc_core_rw            TOP__tb_sys3__DOT__dut__DOT__slot__BRA__13__KET____DOT__core;
    Vtb_sys3_uc_core_rw            TOP__tb_sys3__DOT__dut__DOT__slot__BRA__14__KET____DOT__core;
    Vtb_sys3_uc_core_rw            TOP__tb_sys3__DOT__dut__DOT__slot__BRA__15__KET____DOT__core;
    Vtb_sys3_uc_core_rw            TOP__tb_sys3__DOT__dut__DOT__slot__BRA__16__KET____DOT__core;
    Vtb_sys3_uc_core_rw            TOP__tb_sys3__DOT__dut__DOT__slot__BRA__17__KET____DOT__core;
    Vtb_sys3_uc_core_rw            TOP__tb_sys3__DOT__dut__DOT__slot__BRA__18__KET____DOT__core;
    Vtb_sys3_uc_core_rw            TOP__tb_sys3__DOT__dut__DOT__slot__BRA__19__KET____DOT__core;
    Vtb_sys3_uc_core_rw            TOP__tb_sys3__DOT__dut__DOT__slot__BRA__1__KET____DOT__core;
    Vtb_sys3_uc_core_rw            TOP__tb_sys3__DOT__dut__DOT__slot__BRA__20__KET____DOT__core;
    Vtb_sys3_uc_core_rw            TOP__tb_sys3__DOT__dut__DOT__slot__BRA__21__KET____DOT__core;
    Vtb_sys3_uc_core_rw            TOP__tb_sys3__DOT__dut__DOT__slot__BRA__22__KET____DOT__core;
    Vtb_sys3_uc_core_rw            TOP__tb_sys3__DOT__dut__DOT__slot__BRA__23__KET____DOT__core;
    Vtb_sys3_uc_core_rw            TOP__tb_sys3__DOT__dut__DOT__slot__BRA__24__KET____DOT__core;
    Vtb_sys3_uc_core_rw            TOP__tb_sys3__DOT__dut__DOT__slot__BRA__25__KET____DOT__core;
    Vtb_sys3_uc_core_rw            TOP__tb_sys3__DOT__dut__DOT__slot__BRA__26__KET____DOT__core;
    Vtb_sys3_uc_core_rw            TOP__tb_sys3__DOT__dut__DOT__slot__BRA__27__KET____DOT__core;
    Vtb_sys3_uc_core_rw            TOP__tb_sys3__DOT__dut__DOT__slot__BRA__28__KET____DOT__core;
    Vtb_sys3_uc_core_rw            TOP__tb_sys3__DOT__dut__DOT__slot__BRA__29__KET____DOT__core;
    Vtb_sys3_uc_core_rw            TOP__tb_sys3__DOT__dut__DOT__slot__BRA__2__KET____DOT__core;
    Vtb_sys3_uc_core_rw            TOP__tb_sys3__DOT__dut__DOT__slot__BRA__30__KET____DOT__core;
    Vtb_sys3_uc_core_rw            TOP__tb_sys3__DOT__dut__DOT__slot__BRA__31__KET____DOT__core;
    Vtb_sys3_uc_core_rw            TOP__tb_sys3__DOT__dut__DOT__slot__BRA__3__KET____DOT__core;
    Vtb_sys3_uc_core_rw            TOP__tb_sys3__DOT__dut__DOT__slot__BRA__4__KET____DOT__core;
    Vtb_sys3_uc_core_rw            TOP__tb_sys3__DOT__dut__DOT__slot__BRA__5__KET____DOT__core;
    Vtb_sys3_uc_core_rw            TOP__tb_sys3__DOT__dut__DOT__slot__BRA__6__KET____DOT__core;
    Vtb_sys3_uc_core_rw            TOP__tb_sys3__DOT__dut__DOT__slot__BRA__7__KET____DOT__core;
    Vtb_sys3_uc_core_rw            TOP__tb_sys3__DOT__dut__DOT__slot__BRA__8__KET____DOT__core;
    Vtb_sys3_uc_core_rw            TOP__tb_sys3__DOT__dut__DOT__slot__BRA__9__KET____DOT__core;

    // CONSTRUCTORS
    Vtb_sys3__Syms(VerilatedContext* contextp, const char* namep, Vtb_sys3* modelp);
    ~Vtb_sys3__Syms();

    // METHODS
    const char* name() { return TOP.name(); }
};

#endif  // guard
