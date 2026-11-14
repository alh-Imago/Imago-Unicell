// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Symbol table internal header
//
// Internal details; most calling programs do not need this header,
// unless using verilator public meta comments.

#ifndef VERILATED_VTB_TOP_TANG__SYMS_H_
#define VERILATED_VTB_TOP_TANG__SYMS_H_  // guard

#include "verilated.h"

// INCLUDE MODEL CLASS

#include "Vtb_top_tang.h"

// INCLUDE MODULE CLASSES
#include "Vtb_top_tang___024root.h"
#include "Vtb_top_tang_pk_ram.h"

// SYMS CLASS (contains all model state)
class alignas(VL_CACHE_LINE_BYTES)Vtb_top_tang__Syms final : public VerilatedSyms {
  public:
    // INTERNAL STATE
    Vtb_top_tang* const __Vm_modelp;
    VlDeleter __Vm_deleter;
    bool __Vm_didInit = false;

    // MODULE INSTANCE STATE
    Vtb_top_tang___024root         TOP;
    Vtb_top_tang_pk_ram            TOP__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__rfa;
    Vtb_top_tang_pk_ram            TOP__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__rfb;
    Vtb_top_tang_pk_ram            TOP__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__rfa;
    Vtb_top_tang_pk_ram            TOP__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__rfb;

    // CONSTRUCTORS
    Vtb_top_tang__Syms(VerilatedContext* contextp, const char* namep, Vtb_top_tang* modelp);
    ~Vtb_top_tang__Syms();

    // METHODS
    const char* name() { return TOP.name(); }
};

#endif  // guard
