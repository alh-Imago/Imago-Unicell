// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design implementation internals
// See Vtb_top_tang.h for the primary calling header

#include "Vtb_top_tang__pch.h"
#include "Vtb_top_tang__Syms.h"
#include "Vtb_top_tang___024root.h"

void Vtb_top_tang___024root___ctor_var_reset(Vtb_top_tang___024root* vlSelf);

Vtb_top_tang___024root::Vtb_top_tang___024root(Vtb_top_tang__Syms* symsp, const char* v__name)
    : VerilatedModule{v__name}
    , __VdlySched{*symsp->_vm_contextp__}
    , vlSymsp{symsp}
 {
    // Reset structure values
    Vtb_top_tang___024root___ctor_var_reset(this);
}

void Vtb_top_tang___024root::__Vconfigure(bool first) {
    if (false && first) {}  // Prevent unused
}

Vtb_top_tang___024root::~Vtb_top_tang___024root() {
}
