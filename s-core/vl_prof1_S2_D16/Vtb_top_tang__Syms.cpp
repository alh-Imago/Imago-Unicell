// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Symbol table implementation internals

#include "Vtb_top_tang__pch.h"
#include "Vtb_top_tang.h"
#include "Vtb_top_tang___024root.h"
#include "Vtb_top_tang_pk_ram.h"

// FUNCTIONS
Vtb_top_tang__Syms::~Vtb_top_tang__Syms()
{
}

Vtb_top_tang__Syms::Vtb_top_tang__Syms(VerilatedContext* contextp, const char* namep, Vtb_top_tang* modelp)
    : VerilatedSyms{contextp}
    // Setup internal state of the Syms class
    , __Vm_modelp{modelp}
    // Setup module instances
    , TOP{this, namep}
    , TOP__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__rfa{this, Verilated::catName(namep, "tb_top_tang.dut.sys.slot[0].rfa")}
    , TOP__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__rfb{this, Verilated::catName(namep, "tb_top_tang.dut.sys.slot[0].rfb")}
    , TOP__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__rfa{this, Verilated::catName(namep, "tb_top_tang.dut.sys.slot[1].rfa")}
    , TOP__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__rfb{this, Verilated::catName(namep, "tb_top_tang.dut.sys.slot[1].rfb")}
{
    // Configure time unit / time precision
    _vm_contextp__->timeunit(-9);
    _vm_contextp__->timeprecision(-12);
    // Setup each module's pointers to their submodules
    TOP.__PVT__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__rfa = &TOP__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__rfa;
    TOP.__PVT__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__rfb = &TOP__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__rfb;
    TOP.__PVT__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__rfa = &TOP__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__rfa;
    TOP.__PVT__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__rfb = &TOP__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__rfb;
    // Setup each module's pointer back to symbol table (for public functions)
    TOP.__Vconfigure(true);
    TOP__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__rfa.__Vconfigure(true);
    TOP__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__0__KET____DOT__rfb.__Vconfigure(false);
    TOP__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__rfa.__Vconfigure(false);
    TOP__tb_top_tang__DOT__dut__DOT__sys__DOT__slot__BRA__1__KET____DOT__rfb.__Vconfigure(false);
}
