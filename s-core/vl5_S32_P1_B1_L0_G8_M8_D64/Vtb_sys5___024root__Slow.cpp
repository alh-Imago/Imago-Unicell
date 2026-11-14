// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design implementation internals
// See Vtb_sys5.h for the primary calling header

#include "Vtb_sys5__pch.h"
#include "Vtb_sys5__Syms.h"
#include "Vtb_sys5___024root.h"

void Vtb_sys5___024root___ctor_var_reset(Vtb_sys5___024root* vlSelf);

Vtb_sys5___024root::Vtb_sys5___024root(Vtb_sys5__Syms* symsp, const char* v__name)
    : VerilatedModule{v__name}
    , __VdlySched{*symsp->_vm_contextp__}
    , vlSymsp{symsp}
 {
    // Reset structure values
    Vtb_sys5___024root___ctor_var_reset(this);
}

void Vtb_sys5___024root::__Vconfigure(bool first) {
    if (false && first) {}  // Prevent unused
}

Vtb_sys5___024root::~Vtb_sys5___024root() {
}
