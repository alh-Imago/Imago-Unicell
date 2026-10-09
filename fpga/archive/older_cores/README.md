# Archived older cores (9 Oct 2026, ledger #1036 addendum 20)

Moved out of `fpga/verilog/` because nothing in the repository (no test, tool, build file, Quartus project, shape file or other Verilog) names them any more, and each has a newer replacement:

| File | Replaced by |
|---|---|
| `corner_shell_v1.v` | `corner_shell_v1c.v` |
| `cross_shell_v1.v` | `cross_shell_v1c.v` |
| `merge_shell_v1.v` | `merge_shell_v1c.v` |

Kept byte-for-byte (git history also has them). Everything else that is an "older version" is still named by a live Quartus project or test and was **not** moved: see `fpga/verilog/VERSIONS.md` for the list and what still uses each one.
