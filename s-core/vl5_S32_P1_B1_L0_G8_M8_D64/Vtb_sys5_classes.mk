# Verilated -*- Makefile -*-
# DESCRIPTION: Verilator output: Make include file with class lists
#
# This file lists generated Verilated files, for including in higher level makefiles.
# See Vtb_sys5.mk for the caller.

### Switches...
# C11 constructs required?  0/1 (always on now)
VM_C11 = 1
# Timing enabled?  0/1
VM_TIMING = 1
# Coverage output mode?  0/1 (from --coverage)
VM_COVERAGE = 0
# Parallel builds?  0/1 (from --output-split)
VM_PARALLEL_BUILDS = 1
# Tracing output mode?  0/1 (from --trace/--trace-fst)
VM_TRACE = 0
# Tracing output mode in VCD format?  0/1 (from --trace)
VM_TRACE_VCD = 0
# Tracing output mode in FST format?  0/1 (from --trace-fst)
VM_TRACE_FST = 0

### Object file lists...
# Generated module classes, fast-path, compile with highest optimization
VM_CLASSES_FAST += \
	Vtb_sys5 \
	Vtb_sys5___024root__DepSet_h8a88d757__0 \
	Vtb_sys5___024root__DepSet_h8a88d757__1 \
	Vtb_sys5___024root__DepSet_h99b417e8__0 \
	Vtb_sys5_uc_core_v2s__W1__DepSet_h7da6ff42__0 \
	Vtb_sys5_uc_core_v2s__W1__DepSet_h7da6ff42__1 \
	Vtb_sys5_uc_core_v2s__W1__DepSet_h7da6ff42__2 \
	Vtb_sys5__main \

# Generated module classes, non-fast-path, compile with low/medium optimization
VM_CLASSES_SLOW += \
	Vtb_sys5__ConstPool_0 \
	Vtb_sys5___024root__Slow \
	Vtb_sys5___024root__DepSet_h8a88d757__0__Slow \
	Vtb_sys5___024root__DepSet_h99b417e8__0__Slow \
	Vtb_sys5_uc_core_v2s__W1__Slow \
	Vtb_sys5_uc_core_v2s__W1__DepSet_h7da6ff42__0__Slow \
	Vtb_sys5_uc_core_v2s__W1__DepSet_h7da6ff42__1__Slow \
	Vtb_sys5_uc_core_v2s__W1__DepSet_he889eff5__0__Slow \

# Generated support classes, fast-path, compile with highest optimization
VM_SUPPORT_FAST += \

# Generated support classes, non-fast-path, compile with low/medium optimization
VM_SUPPORT_SLOW += \
	Vtb_sys5__Syms \

# Global classes, need linked once per executable, fast-path, compile with highest optimization
VM_GLOBAL_FAST += \
	verilated \
	verilated_timing \
	verilated_threads \

# Global classes, need linked once per executable, non-fast-path, compile with low/medium optimization
VM_GLOBAL_SLOW += \


# Verilated -*- Makefile -*-
