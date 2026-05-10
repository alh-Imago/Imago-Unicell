# LLVM and Open Source Language Portability

Any language with an LLVM frontend compiles to UniCell `.icm` programs.

---

## The Path

```
C / C++ / Rust / Swift / Zig / Julia / ...
              │
              │ language frontend (clang, rustc, swiftc, ...)
              ▼
           LLVM IR
              │
              │ llvm_ir_mapper.py
              ▼
        CellMapRecord list
              │
              │ controller.load_map()
              ▼
         .icm program
```

No new compiler backend needed. LLVM IR is the intermediate representation
that hundreds of language frontends already produce. `llvm_ir_mapper.py`
maps LLVM IR operations directly to UniCell tile placements.

---

## Setup

```bash
pip install imago-vm[llvm]
# or: pip install llvmlite
```

`llvmlite` requires LLVM shared libraries on the host. If not installed,
the LLVM frontend disables itself with a clear error message. Everything
else in the system continues to work.

**Verify:**

```bash
imago info
# llvmlite  0.40.x  (LLVM frontend available)
# or:
# llvmlite  not installed  (pip install llvmlite for C/C++/Rust support)
```

---

## From C

```c
// add.c
int add(int a, int b) {
    return a + b;
}
```

```bash
# Compile to LLVM IR
clang -O1 -emit-llvm -S -o add.ll add.c

# Map to .icm
python3 -c "
from llvm_ir_mapper import LLVMIRMapper
mapper = LLVMIRMapper()
icm = mapper.compile_file('add.ll', 'add')
import json
with open('add.icm', 'w') as f:
    json.dump(icm, f, indent=2)
print('Written add.icm')
"
```

```bash
imago run add.icm a=5 b=3
# result = 8
```

---

## From Rust

```rust
// add.rs
#[no_mangle]
pub fn add(a: i32, b: i32) -> i32 {
    a + b
}
```

```bash
rustc --emit=llvm-ir -O -o add.ll add.rs
python3 -c "
from llvm_ir_mapper import LLVMIRMapper
mapper = LLVMIRMapper()
icm = mapper.compile_file('add.ll', 'add')
import json
open('add.icm','w').write(json.dumps(icm, indent=2))
"
imago run add.icm a=5 b=3
```

---

## Supported LLVM IR Operations

| Operation | Tile used | Notes |
|-----------|-----------|-------|
| `add` (i32) | INT32_ADD | Kogge-Stone, 482 cells depth 2 |
| `sub` (i32) | INT32_SUB | 517 cells depth 12 |
| `icmp eq` (i32) | INT32_EQ | 95 cells |
| `select` | INT32_MUX | 128 cells |
| `fadd` (float) | FP32_ADD | 1,253 cells depth 85 |
| `fmul` (float) | FP32_MUL | 3,066 cells depth 89 |
| `fcmp oeq` (float) | FP32_CMP_EQ | 95 cells |
| `not` / `xor` | NOT / XOR | 1 cell |
| `and` / `or` | AND / OR | 1 cell |

**Not yet supported:** `mul` (i32), division, `i64` arithmetic, memory
operations (`load`/`store`), branches with complex control flow.

`mul` (integer multiply) maps to INT32_MUL_DADDA (23,924 cells) — too large
for most FPGA targets, requires a dedicated pond. Planned for a future session.

---

## Limitations

**No memory model.** UniCell cells don't access memory in the LLVM sense.
There are no load/store operations — data flows through the cell network as
bus values. Functions that access arrays or pointers cannot be compiled
directly; only pure arithmetic functions are supported today.

**No control flow across tiles.** Conditional branches inside a single
function work (the compiler uses MUX cells). Function calls across tile
boundaries require the COMPANION sequencer — not yet wired in the LLVM path.

**32-bit only.** The tile library is built for 32-bit integers and 32-bit
floats. LLVM `i64` operations are not yet supported.

**These are current limitations, not architectural ones.** The cell model
supports arbitrary precision via multi-cell word layouts (the type system's
complement cell model). The LLVM mapper will be extended as tiles are built.

---

## Why This Matters

LLVM is the compiler infrastructure that powers C, C++, Rust, Swift, Zig,
Julia, Kotlin Native, and many other languages. Every one of those languages
becomes a UniCell frontend once LLVM IR is the bridge.

This means the UniCell ecosystem inherits decades of language tooling,
optimisation passes, and community libraries — without writing a single new
language frontend. Programs written in any LLVM language today are
potentially UniCell programs once the tile library covers their operation mix.

The portability story is not just "the same `.icm` runs on VM, FPGA, ASIC" —
it is also "the same program written in C or Rust today runs on silicon that
does not exist yet, via a path that already exists."
