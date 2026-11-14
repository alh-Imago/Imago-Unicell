// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design implementation internals
// See Vtb_sys3.h for the primary calling header

#include "Vtb_sys3__pch.h"
#include "Vtb_sys3__Syms.h"
#include "Vtb_sys3___024root.h"

void Vtb_sys3___024root___ctor_var_reset(Vtb_sys3___024root* vlSelf);

Vtb_sys3___024root::Vtb_sys3___024root(Vtb_sys3__Syms* symsp, const char* v__name)
    : VerilatedModule{v__name}
    , __VdlySched{*symsp->_vm_contextp__}
    , vlSymsp{symsp}
 {
    // Reset structure values
    Vtb_sys3___024root___ctor_var_reset(this);
}

void Vtb_sys3___024root::__Vconfigure(bool first) {
    if (false && first) {}  // Prevent unused
}

Vtb_sys3___024root::~Vtb_sys3___024root() {
}
